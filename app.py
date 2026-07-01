from __future__ import annotations

import base64
import html
import io
import socket
import zipfile
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
CSS_FILE = ASSETS_DIR / "styles.css"
WORKOUTS_FILE = DATA_DIR / "workouts.csv"
LOG_FILE = DATA_DIR / "workout_log.csv"
PR_FILE = DATA_DIR / "personal_records.csv"
PROFILE_FILE = DATA_DIR / "profile.csv"
BACKUP_DIR = DATA_DIR / "backups"

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
LOG_COLS = ["date", "saved_at", "week", "day", "workout", "muscle_group", "exercise", "set_number", "weight_lbs", "reps", "pain", "notes", "volume"]

st.set_page_config(page_title="Brian Fitness Tracker v15.2", page_icon="🏋️", layout="wide", initial_sidebar_state="expanded")
if CSS_FILE.exists():
    st.markdown(f"<style>{CSS_FILE.read_text()}</style>", unsafe_allow_html=True)


def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


def read_csv(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    if path.exists():
        try:
            df = pd.read_csv(path)
            df = normalize_cols(df)
        except Exception:
            df = pd.DataFrame(columns=columns or [])
    else:
        df = pd.DataFrame(columns=columns or [])
    if columns:
        for col in columns:
            if col not in df.columns:
                df[col] = None
        df = df[columns]
    return df


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def ensure_files() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)
    if not LOG_FILE.exists():
        save_csv(pd.DataFrame(columns=LOG_COLS), LOG_FILE)
    if not PR_FILE.exists():
        save_csv(pd.DataFrame(columns=["exercise", "best_weight_lbs", "best_reps", "best_volume", "date", "saved_at"]), PR_FILE)
    if not PROFILE_FILE.exists():
        save_csv(pd.DataFrame([{"key":"current_weight","value":0},{"key":"goal_weight","value":0},{"key":"week","value":1}]), PROFILE_FILE)


def workouts_df() -> pd.DataFrame:
    df = read_csv(WORKOUTS_FILE)
    required = ["day", "workout", "muscle_group", "exercise", "target_sets", "target_reps", "starting_weight_lbs", "notes"]
    for col in required:
        if col not in df.columns:
            df[col] = ""
    df["target_sets"] = pd.to_numeric(df["target_sets"], errors="coerce").fillna(3).astype(int)
    df["starting_weight_lbs"] = pd.to_numeric(df["starting_weight_lbs"], errors="coerce").fillna(0.0)
    return df[required]


def log_df() -> pd.DataFrame:
    df = read_csv(LOG_FILE, LOG_COLS)
    for c in ["week", "set_number", "reps", "pain"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    for c in ["weight_lbs", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    return df


def load_profile() -> dict:
    default = {"current_weight": 0.0, "goal_weight": 0.0, "week": 1}
    df = read_csv(PROFILE_FILE)
    if not df.empty and {"key", "value"}.issubset(df.columns):
        for _, r in df.iterrows():
            default[str(r["key"])] = r["value"]
    for k in ["current_weight", "goal_weight"]:
        try: default[k] = float(default[k])
        except Exception: default[k] = 0.0
    try: default["week"] = int(float(default["week"]))
    except Exception: default["week"] = 1
    return default


def save_profile(profile: dict) -> None:
    save_csv(pd.DataFrame([{"key": k, "value": v} for k, v in profile.items()]), PROFILE_FILE)


def backup_data() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = BACKUP_DIR / f"workout_log_backup_{stamp}.csv"
    if LOG_FILE.exists(): out.write_bytes(LOG_FILE.read_bytes())
    else: save_csv(pd.DataFrame(columns=LOG_COLS), out)
    return out


def make_export_zip() -> bytes:
    buffer = io.BytesIO()
    files = [WORKOUTS_FILE, LOG_FILE, PR_FILE, PROFILE_FILE, DATA_DIR/"exercise_library.csv", DATA_DIR/"block_templates.csv", DATA_DIR/"nutrition_log.csv", DATA_DIR/"recovery_log.csv", DATA_DIR/"body_stats.csv"]
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            if p.exists(): z.write(p, arcname=f"data/{p.name}")
    buffer.seek(0)
    return buffer.getvalue()


def get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8",80)); ip=s.getsockname()[0]; s.close(); return ip
    except Exception:
        return "YOUR-COMPUTER-IP"


def last_set_value(log: pd.DataFrame, exercise: str, set_number: int, fallback_weight: float) -> tuple[float, int]:
    if log.empty: return fallback_weight, 0
    ex = log[(log.exercise == exercise) & (log.set_number == set_number)].copy()
    if ex.empty: return fallback_weight, 0
    ex["_dt"] = pd.to_datetime(ex.saved_at, errors="coerce")
    r = ex.sort_values("_dt").iloc[-1]
    return float(r.weight_lbs), int(r.reps)


def best_weight(log: pd.DataFrame, exercise: str) -> float:
    if log.empty: return 0.0
    ex = log[log.exercise == exercise]
    return float(ex.weight_lbs.max()) if not ex.empty else 0.0


def update_pr(new_rows: pd.DataFrame) -> None:
    if new_rows.empty: return
    prs = read_csv(PR_FILE)
    if prs.empty:
        prs = pd.DataFrame(columns=["exercise", "best_weight_lbs", "best_reps", "best_volume", "date", "saved_at"])
    for exercise, g in new_rows.groupby("exercise"):
        mx = float(g.weight_lbs.max())
        rep = int(g.loc[g.weight_lbs.idxmax(), "reps"])
        vol = float(g.volume.max())
        old = prs[prs.exercise == exercise]
        if old.empty:
            prs = pd.concat([prs, pd.DataFrame([{"exercise":exercise,"best_weight_lbs":mx,"best_reps":rep,"best_volume":vol,"date":str(g.iloc[0].date),"saved_at":datetime.now().isoformat(timespec="seconds")}])], ignore_index=True)
        else:
            idx = old.index[0]
            try: old_w = float(prs.loc[idx,"best_weight_lbs"])
            except Exception: old_w = 0.0
            if mx > old_w:
                prs.loc[idx, ["best_weight_lbs","best_reps","best_volume","date","saved_at"]] = [mx,rep,vol,str(g.iloc[0].date),datetime.now().isoformat(timespec="seconds")]
    save_csv(prs, PR_FILE)


def exercise_svg_data(exercise: str, muscle: str) -> str:
    e = exercise.lower()
    # different artwork by movement pattern; still lightweight SVG, no external image dependency
    if any(x in e for x in ["pulldown", "pull-up", "lat"]):
        icon = "pulldown"; bg1="#dff0ff"; bg2="#ffffff"; accent="#0d6efd"
        body = '<path d="M66 42c-20 12-33 32-33 58" stroke="#333" stroke-width="6" fill="none"/><path d="M178 42c20 12 33 32 33 58" stroke="#333" stroke-width="6" fill="none"/><path d="M42 40h160" stroke="#111" stroke-width="8"/><circle cx="122" cy="72" r="17" fill="#202a35"/><path d="M122 90v42M88 98c22 18 48 18 68 0M99 132h46" stroke="#202a35" stroke-width="10" stroke-linecap="round"/><rect x="87" y="137" width="70" height="16" rx="6" fill="#0d6efd" opacity=".35"/>'
    elif any(x in e for x in ["row"]):
        icon = "row"; bg1="#eaf8ef"; bg2="#ffffff"; accent="#087a2a"
        body = '<rect x="32" y="112" width="170" height="14" rx="7" fill="#333" opacity=".5"/><circle cx="78" cy="78" r="17" fill="#202a35"/><path d="M92 86c34 6 55 1 77-20M93 99h70M75 95l-20 38M98 99l20 35" stroke="#202a35" stroke-width="9" stroke-linecap="round"/><rect x="170" y="41" width="16" height="100" rx="5" fill="#0d6efd"/><path d="M164 67h-50" stroke="#111" stroke-width="5"/>'
    elif any(x in e for x in ["curl", "bicep", "hammer"]):
        icon = "curl"; bg1="#f2eaff"; bg2="#ffffff"; accent="#7c3aed"
        body = '<circle cx="122" cy="58" r="18" fill="#202a35"/><path d="M122 78v55M87 91c12 29 26 33 45 28M157 91c-12 29-26 33-45 28M92 120l-22 18M152 120l22 18" stroke="#202a35" stroke-width="11" stroke-linecap="round"/><circle cx="67" cy="140" r="10" fill="#111"/><circle cx="177" cy="140" r="10" fill="#111"/><path d="M62 140h32M150 140h32" stroke="#111" stroke-width="5"/>'
    elif any(x in e for x in ["chest", "press", "fly", "pec"]):
        icon = "press"; bg1="#edf5ff"; bg2="#ffffff"; accent="#0d6efd"
        body = '<rect x="48" y="123" width="150" height="14" rx="7" fill="#333" opacity=".45"/><circle cx="105" cy="92" r="15" fill="#202a35"/><path d="M121 97h56M110 107l32 18M91 104l-31 19" stroke="#202a35" stroke-width="10" stroke-linecap="round"/><path d="M42 62h160" stroke="#111" stroke-width="8"/><circle cx="36" cy="62" r="17" fill="#111"/><circle cx="208" cy="62" r="17" fill="#111"/><path d="M74 63v34M170 63v34" stroke="#202a35" stroke-width="7"/>'
    elif any(x in e for x in ["shoulder", "lateral", "raise", "face pull", "shrug"]):
        icon = "shoulder"; bg1="#fff6db"; bg2="#ffffff"; accent="#d99b19"
        body = '<circle cx="122" cy="67" r="17" fill="#202a35"/><path d="M122 85v50M85 88l-44 17M159 88l44 17M90 130h64" stroke="#202a35" stroke-width="10" stroke-linecap="round"/><circle cx="39" cy="106" r="11" fill="#111"/><circle cx="205" cy="106" r="11" fill="#111"/>'
    elif any(x in e for x in ["hip", "hamstring", "calf", "knee", "glute"]):
        icon = "leg"; bg1="#eaf8ef"; bg2="#ffffff"; accent="#16a34a"
        body = '<circle cx="122" cy="54" r="17" fill="#202a35"/><path d="M122 72v45M95 82h54M112 117l-18 45M132 117l24 43" stroke="#202a35" stroke-width="11" stroke-linecap="round"/><rect x="73" y="139" width="48" height="12" rx="6" fill="#16a34a"/><rect x="143" y="139" width="48" height="12" rx="6" fill="#16a34a"/><rect x="51" y="119" width="45" height="14" rx="6" fill="#111" opacity=".45"/>'
    else:
        icon = "core"; bg1="#fff0f0"; bg2="#ffffff"; accent="#ef4444"
        body = '<circle cx="122" cy="54" r="17" fill="#202a35"/><path d="M122 72v55M93 88h58M102 126h40" stroke="#202a35" stroke-width="11" stroke-linecap="round"/><path d="M109 82h26v53h-26z" fill="#ef4444" opacity=".35"/>'
    title = html.escape(exercise[:26])
    sub = html.escape(muscle[:24])
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="278" viewBox="0 0 420 278">
    <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{bg1}"/><stop offset="1" stop-color="{bg2}"/></linearGradient><filter id="sh" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="7" stdDeviation="8" flood-color="#071a33" flood-opacity=".18"/></filter></defs>
    <rect width="420" height="278" rx="24" fill="url(#bg)"/><rect x="22" y="22" width="376" height="170" rx="20" fill="#ffffff" opacity=".62" filter="url(#sh)"/>
    <g transform="translate(88,32) scale(1.05)">{body}</g>
    <rect x="22" y="212" width="376" height="44" rx="16" fill="#ffffff" opacity=".88"/>
    <circle cx="46" cy="234" r="12" fill="{accent}"/><text x="68" y="230" font-family="Inter,Arial" font-size="20" font-weight="900" fill="#071a33">{title}</text>
    <text x="68" y="249" font-family="Inter,Arial" font-size="12" font-weight="800" fill="#61718a">{sub}</text>
    </svg>'''
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def muscle_svg_data(muscle: str) -> str:
    # Simple muscle-group illustration for right sidebar
    back = "Back" in muscle or "Biceps" in muscle
    fill = "#0d6efd" if back else "#16a34a"
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="360" height="240" viewBox="0 0 360 240">
    <rect width="360" height="240" rx="18" fill="#f7fbff"/>
    <g transform="translate(44,20)"><circle cx="70" cy="36" r="17" fill="#c8ced6"/><path d="M70 55v94M38 76l-24 48M102 76l24 48M55 149l-16 58M85 149l16 58" stroke="#7d8795" stroke-width="13" stroke-linecap="round"/><path d="M44 70h52v70H44z" fill="{fill}" opacity=".72"/><path d="M38 78l-24 48M102 78l24 48" stroke="{fill}" stroke-width="15" stroke-linecap="round" opacity=".65"/></g>
    <g transform="translate(190,20)"><circle cx="70" cy="36" r="17" fill="#c8ced6"/><path d="M70 55v94M38 76l-24 48M102 76l24 48M55 149l-16 58M85 149l16 58" stroke="#7d8795" stroke-width="13" stroke-linecap="round"/><path d="M44 70h52v70H44z" fill="{fill}" opacity=".34"/><path d="M43 74c12 18 42 18 54 0M43 97c12 22 42 22 54 0" stroke="{fill}" stroke-width="12" opacity=".75" stroke-linecap="round"/></g>
    </svg>'''
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def sidebar(page_names: list[str]) -> str:
    st.sidebar.markdown('''<div class="sidebar-brand"><div class="brand-title">🏋️ BRIAN</div><div class="brand-sub">FITNESS TRACKER</div><div class="version-pill">v15.2 True Mockup Layout</div></div>''', unsafe_allow_html=True)
    page = st.sidebar.radio("NAVIGATION", page_names, index=1)
    st.sidebar.markdown('''<div class="side-panel"><h4>Data Status</h4><div class="status-row"><div class="check">✓</div><div><b>All data is safe</b><br><span style="color:#9fbbdc!important;font-size:13px;">workout_log.csv</span></div></div><div class="export-box">☁️ <b>EXPORT BACKUP</b><br><span style="color:#9fbbdc!important;font-size:13px;">Download your data</span></div></div>''', unsafe_allow_html=True)
    return page


def top_header(title: str, workout: str, exercise_count: int):
    st.markdown(f'''<div class="page-top"><div><h1>{html.escape(title)} ✎</h1><div class="subtitle-row"><span class="chip">{html.escape(workout)}</span><span class="chip green">{exercise_count} exercises</span></div></div><div class="finish-btn">✓ FINISH WORKOUT</div></div><div class="top-rule"></div>''', unsafe_allow_html=True)


ensure_files()
profile = load_profile()
workouts = workouts_df()
log = log_df()

PAGES = ["Dashboard", "Today's Workout", "Weekly Plan", "Exercise Library", "Progress", "History", "Data Safety", "Profile", "Phone Setup"]
page = sidebar(PAGES)

if page == "Dashboard":
    today = date.today().strftime("%A")
    day_df = workouts[workouts.day == today]
    total_sessions = log.date.nunique() if not log.empty else 0
    total_volume = log.volume.sum() if not log.empty else 0
    avg_pain = log.pain.mean() if not log.empty else 0
    top_header("Brian Fitness Tracker", "Dashboard", len(day_df))
    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f'<div class="stat-card"><div class="stat-icon">🔥</div><div class="label">Sessions</div><div class="stat-value">{total_sessions}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-card"><div class="stat-icon">📊</div><div class="label">Total Volume</div><div class="stat-value">{total_volume:,.0f}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-card"><div class="stat-icon">🦵</div><div class="label">Avg Pain</div><div class="stat-value">{avg_pain:.1f}/10</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="stat-card"><div class="stat-icon">📅</div><div class="label">Week</div><div class="stat-value">{profile.get("week",1)}</div></div>', unsafe_allow_html=True)
    st.markdown("### This Week's Plan")
    for d in DAYS:
        dd = workouts[workouts.day == d]
        if dd.empty: continue
        st.markdown(f'<div class="week-card"><span class="dow">{d[:3].upper()}</span><span class="muscle">{html.escape(str(dd.iloc[0].muscle_group))}</span><div class="small">{html.escape(str(dd.iloc[0].workout))} · {len(dd)} exercises</div></div>', unsafe_allow_html=True)

elif page == "Today's Workout":
    day = st.selectbox("Workout Day", DAYS, index=DAYS.index(date.today().strftime("%A")) if date.today().strftime("%A") in DAYS else 0, label_visibility="collapsed")
    active = workouts[workouts.day == day].reset_index(drop=True)
    if active.empty:
        st.warning("No workout found for this day."); st.stop()
    workout = str(active.iloc[0].workout)
    muscle = str(active.iloc[0].muscle_group)
    top_header(f"{day} — {workout}", muscle, len(active))
    if day == "Thursday": st.markdown('<div class="warn">🦵 Leg Rehab Day: no downward loading. Stop anything that causes knee pain.</div>', unsafe_allow_html=True)
    if day == "Sunday": st.markdown('<div class="safe">Recovery day: swimming, bike, sauna, mobility, and recovery.</div>', unsafe_allow_html=True)

    main, right = st.columns([3.5, .9], gap="large")
    rows = []
    display_totals = []

    with main:
        r1, r2, r3 = st.columns([1.1, 1.0, 1.35])
        workout_date = r1.date_input("Date", value=date.today())
        week_num = r2.number_input("Week", min_value=1, max_value=52, value=int(profile.get("week",1)), step=1)
        r3.markdown('<div class="stat-card"><div class="stat-icon">📊</div><div class="label">Exercise Total Volume</div><div class="stat-value live-total">Auto</div></div>', unsafe_allow_html=True)

        for i, row in active.iterrows():
            exercise = str(row.exercise)
            target_sets = int(row.target_sets)
            target_reps = str(row.target_reps)
            default_weight = float(row.starting_weight_lbs)
            note_text = str(row.notes) if str(row.notes) != "nan" else ""
            exercise_id = f"{day}_{i}"
            st.markdown(f'''<div class="mock-ex-card"><div class="mock-ex-head"><img class="mock-ex-img" src="{exercise_svg_data(exercise,muscle)}"/><div class="mock-ex-info"><div class="mock-ex-title">{i+1}. {html.escape(exercise)}</div><span class="chip">Target: {target_sets} × {html.escape(target_reps)}</span> <span class="chip green">{html.escape(muscle)}</span><div class="small" style="margin-top:10px;">{html.escape(note_text) if note_text else 'Week ' + str(int(week_num)) + ' · values auto-fill from last workout'}</div></div><div class="mock-actions"><span class="how-btn">▷ HOW TO DO IT</span><span class="dots">⋮</span></div></div>''', unsafe_allow_html=True)
            st.markdown('<div class="set-header"><span>SET</span><span>WEIGHT (LBS)</span><span>REPS</span><span>RPE / PAIN</span><span>NOTES</span><span>VOLUME</span></div>', unsafe_allow_html=True)
            exercise_total = 0.0
            for s_num in range(1, target_sets + 1):
                last_w, last_r = last_set_value(log, exercise, s_num, default_weight)
                c0, c1, c2, c3, c4, c5 = st.columns([.42, 1.0, .9, .9, 1.55, .9], gap="small")
                c0.markdown(f'<div class="set-num big">{s_num}</div>', unsafe_allow_html=True)
                wt = c1.number_input(f"{exercise} set {s_num} weight", min_value=0.0, value=float(last_w), step=2.5, key=f"wt_{exercise_id}_{s_num}", label_visibility="collapsed")
                reps = c2.number_input(f"{exercise} set {s_num} reps", min_value=0, value=int(last_r), step=1, key=f"reps_{exercise_id}_{s_num}", label_visibility="collapsed")
                pain = c3.number_input(f"{exercise} set {s_num} pain", min_value=0, max_value=10, value=0, step=1, key=f"pain_{exercise_id}_{s_num}", label_visibility="collapsed")
                notes = c4.text_input(f"{exercise} set {s_num} notes", value="", placeholder="felt good", key=f"notes_{exercise_id}_{s_num}", label_visibility="collapsed")
                vol = float(wt) * int(reps)
                exercise_total += vol
                c5.markdown(f'<div class="vol-pill">{vol:,.0f} lbs</div>', unsafe_allow_html=True)
                if int(reps) > 0:
                    rows.append({"date":str(workout_date),"saved_at":datetime.now().isoformat(timespec="seconds"),"week":int(week_num),"day":day,"workout":workout,"muscle_group":muscle,"exercise":exercise,"set_number":s_num,"weight_lbs":wt,"reps":reps,"pain":pain,"notes":notes,"volume":vol})
            display_totals.append(exercise_total)
            st.markdown(f'<div class="exercise-total-row"><span>EXERCISE VOLUME:</span><b>{exercise_total:,.0f} lbs</b></div></div>', unsafe_allow_html=True)

        st.markdown('<div class="save-wrap">', unsafe_allow_html=True)
        if st.button("✅ FINISH / SAVE WORKOUT", use_container_width=True):
            if rows:
                new = pd.DataFrame(rows)
                backup_data()
                save_csv(pd.concat([log_df(), new], ignore_index=True), LOG_FILE)
                update_pr(new)
                st.success(f"Saved {len(new)} completed sets to data/workout_log.csv")
                st.balloons()
            else:
                st.warning("Enter reps for at least one set before saving.")
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        total_volume = sum(display_totals)
        total_sets = sum(int(x.target_sets) for _, x in active.iterrows())
        st.markdown(f'''<div class="side-card"><h3>📋 Workout Summary</h3><div class="summary-row"><span>Exercises</span><b>{len(active)}</b></div><div class="summary-row"><span>Total Sets</span><b>{total_sets}</b></div><div class="summary-row"><span>Total Volume</span><b class="green-text">{total_volume:,.0f} lbs</b></div><div class="summary-row"><span>Workout Time</span><b>—</b></div><div class="summary-row"><span>Calories (Est.)</span><b>—</b></div></div>''', unsafe_allow_html=True)
        st.markdown(f'''<div class="side-card"><h3>Muscle Groups</h3><img src="{muscle_svg_data(muscle)}" style="width:100%;border-radius:12px;" /></div>''', unsafe_allow_html=True)
        st.markdown('''<div class="side-card"><h3>Quick Actions</h3><div class="quick-button">⊕ ADD EXERCISE</div><div class="quick-button">↕ REORDER EXERCISES</div><div class="quick-button red">🗑 CLEAR WORKOUT</div></div><div class="side-card"><h3>💡 Tips</h3><div class="small">Focus on controlled movements and mind-muscle connection for best results.</div></div>''', unsafe_allow_html=True)

elif page == "Weekly Plan":
    top_header("Weekly Plan", "Schedule", len(workouts))
    for d in DAYS:
        dd = workouts[workouts.day == d]
        if dd.empty: continue
        st.markdown(f'<div class="week-card"><span class="dow">{d[:3].upper()}</span><span class="muscle">{html.escape(str(dd.iloc[0].muscle_group))}</span><div class="small">{html.escape(str(dd.iloc[0].workout))} · {len(dd)} exercises</div></div>', unsafe_allow_html=True)

elif page == "Exercise Library":
    top_header("Exercise Library", "All Exercises", len(workouts))
    q = st.text_input("Search exercise")
    df = workouts.copy()
    if q: df = df[df.exercise.str.contains(q, case=False, na=False)]
    cols = st.columns(3)
    for idx, (_, r) in enumerate(df.iterrows()):
        with cols[idx % 3]:
            st.markdown(f'<div class="library-card" style="padding:14px;margin-bottom:14px;"><img class="thumbnail" src="{exercise_svg_data(str(r.exercise),str(r.muscle_group))}"/><div class="ex-title" style="font-size:17px;margin-top:10px;">{html.escape(str(r.exercise))}</div><span class="chip">{html.escape(str(r.muscle_group))}</span><div class="small" style="margin-top:8px;">{html.escape(str(r.day))} · {int(r.target_sets)} × {html.escape(str(r.target_reps))}</div></div>', unsafe_allow_html=True)

elif page == "Progress":
    top_header("Progress", "Analytics", 0)
    if log.empty:
        st.info("No workouts saved yet.")
    else:
        c1,c2,c3 = st.columns(3)
        c1.metric("Sessions", log.date.nunique())
        c2.metric("Total Volume", f"{log.volume.sum():,.0f} lbs")
        c3.metric("Avg Pain", f"{log.pain.mean():.1f}/10")
        daily = log.groupby("date", as_index=False).volume.sum()
        st.plotly_chart(px.line(daily, x="date", y="volume", title="Workout Volume by Day"), use_container_width=True)
        best = log.groupby("exercise", as_index=False).agg(best_weight=("weight_lbs","max"), total_volume=("volume","sum"), sets=("set_number","count")).sort_values("total_volume", ascending=False)
        st.dataframe(best, use_container_width=True)

elif page == "History":
    top_header("History", "Saved Workouts", 0)
    if log.empty: st.info("No saved history yet.")
    else:
        st.dataframe(log.sort_values(["date","saved_at"], ascending=[False, False]), use_container_width=True)
        st.download_button("Download workout_log.csv", log.to_csv(index=False).encode("utf-8"), "workout_log.csv", "text/csv")

elif page == "Data Safety":
    top_header("Data Safety", "Backups", 0)
    st.markdown('<div class="safe">workouts.csv is your plan. workout_log.csv is your completed workout history. Do not delete workout_log.csv.</div>', unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    if c1.button("Create Backup Now"):
        b = backup_data(); st.success(f"Backup created: {b.name}")
    c2.download_button("Export All Data ZIP", make_export_zip(), "brian_fitness_data_export.zip", "application/zip")
    st.write("Workout log rows:", len(log_df()))
    st.write("Backup folder:", str(BACKUP_DIR))

elif page == "Profile":
    top_header("Profile", "Settings", 0)
    profile["current_weight"] = st.number_input("Current Weight", min_value=0.0, value=float(profile.get("current_weight",0.0)), step=0.5)
    profile["goal_weight"] = st.number_input("Goal Weight", min_value=0.0, value=float(profile.get("goal_weight",0.0)), step=0.5)
    profile["week"] = st.number_input("Week #", min_value=1, max_value=52, value=int(profile.get("week",1)), step=1)
    if st.button("Save Profile"):
        save_profile(profile); st.success("Profile saved.")

elif page == "Phone Setup":
    top_header("Phone Setup", "Use on your phone", 0)
    st.info("Local use only works on the same Wi-Fi. For the gym, deploy through Streamlit Cloud and open the app URL on your phone.")
    st.code(f"http://{get_lan_ip()}:8501")
