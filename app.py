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
REQUIRED_LOG_COLS = ["date", "saved_at", "week", "day", "workout", "muscle_group", "exercise", "set_number", "weight_lbs", "reps", "pain", "notes", "volume"]

st.set_page_config(page_title="Brian Fitness Tracker v15", page_icon="🏋️", layout="wide", initial_sidebar_state="expanded")

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


def ensure_data_files() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)
    if not LOG_FILE.exists():
        save_csv(pd.DataFrame(columns=REQUIRED_LOG_COLS), LOG_FILE)
    if not PR_FILE.exists():
        save_csv(pd.DataFrame(columns=["exercise", "best_weight_lbs", "best_reps", "best_volume", "date", "saved_at"]), PR_FILE)
    if not PROFILE_FILE.exists():
        save_csv(pd.DataFrame([
            {"key": "current_weight", "value": 0},
            {"key": "goal_weight", "value": 0},
            {"key": "week", "value": 1},
        ]), PROFILE_FILE)


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
    df = read_csv(LOG_FILE, REQUIRED_LOG_COLS)
    for col in ["week", "set_number", "reps", "pain"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    for col in ["weight_lbs", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def load_profile() -> dict:
    ensure_data_files()
    default = {"current_weight": 0.0, "goal_weight": 0.0, "week": 1}
    df = read_csv(PROFILE_FILE)
    if not df.empty and {"key", "value"}.issubset(df.columns):
        for _, row in df.iterrows():
            default[str(row["key"])] = row["value"]
    for k in ["current_weight", "goal_weight"]:
        try:
            default[k] = float(default[k])
        except Exception:
            default[k] = 0.0
    try:
        default["week"] = int(float(default["week"]))
    except Exception:
        default["week"] = 1
    return default


def save_profile(profile: dict) -> None:
    save_csv(pd.DataFrame([{"key": k, "value": v} for k, v in profile.items()]), PROFILE_FILE)


def backup_data() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"workout_log_backup_{stamp}.csv"
    if LOG_FILE.exists():
        backup_file.write_bytes(LOG_FILE.read_bytes())
    else:
        save_csv(pd.DataFrame(columns=REQUIRED_LOG_COLS), backup_file)
    return backup_file


def get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "YOUR-COMPUTER-IP"


def last_set_value(log: pd.DataFrame, exercise: str, set_number: int, fallback_weight: float) -> tuple[float, int]:
    if log.empty:
        return fallback_weight, 0
    ex = log[(log["exercise"] == exercise) & (log["set_number"] == set_number)].copy()
    if ex.empty:
        return fallback_weight, 0
    ex["_dt"] = pd.to_datetime(ex["saved_at"], errors="coerce")
    row = ex.sort_values("_dt").iloc[-1]
    return float(row["weight_lbs"]), int(row["reps"])


def best_weight(log: pd.DataFrame, exercise: str) -> float:
    if log.empty:
        return 0.0
    ex = log[log["exercise"] == exercise]
    return float(ex["weight_lbs"].max()) if not ex.empty else 0.0


def update_personal_records(new_rows: pd.DataFrame) -> None:
    if new_rows.empty:
        return
    records = read_csv(PR_FILE)
    if records.empty:
        records = pd.DataFrame(columns=["exercise", "best_weight_lbs", "best_reps", "best_volume", "date", "saved_at"])
    for exercise, group in new_rows.groupby("exercise"):
        max_weight = float(group["weight_lbs"].max())
        max_volume = float(group["volume"].max())
        best_reps = int(group.loc[group["weight_lbs"].idxmax(), "reps"])
        existing = records[records["exercise"] == exercise]
        if existing.empty:
            records = pd.concat([records, pd.DataFrame([{"exercise": exercise, "best_weight_lbs": max_weight, "best_reps": best_reps, "best_volume": max_volume, "date": str(group.iloc[0]["date"]), "saved_at": datetime.now().isoformat(timespec="seconds")}])], ignore_index=True)
        else:
            idx = existing.index[0]
            old = pd.to_numeric(pd.Series([records.loc[idx, "best_weight_lbs"]]), errors="coerce").fillna(0).iloc[0]
            if max_weight > old:
                records.loc[idx, ["best_weight_lbs", "best_reps", "best_volume", "date", "saved_at"]] = [max_weight, best_reps, max_volume, str(group.iloc[0]["date"]), datetime.now().isoformat(timespec="seconds")]
    save_csv(records, PR_FILE)


def make_export_zip() -> bytes:
    files = [WORKOUTS_FILE, LOG_FILE, PROFILE_FILE, PR_FILE, DATA_DIR / "nutrition_log.csv", DATA_DIR / "recovery_log.csv", DATA_DIR / "body_stats.csv", DATA_DIR / "exercise_library.csv", DATA_DIR / "block_templates.csv"]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for path in files:
            if path.exists():
                z.write(path, arcname=f"data/{path.name}")
    buffer.seek(0)
    return buffer.getvalue()


def svg_thumb(exercise: str, muscle: str) -> str:
    e = exercise.lower()
    color = "#1368e8"
    icon = "🏋️"
    if any(x in e for x in ["pulldown", "row", "back"]):
        color = "#0f766e"; icon = "↧"
    elif any(x in e for x in ["chest", "press", "fly", "pec"]):
        color = "#1368e8"; icon = "↔"
    elif any(x in e for x in ["curl", "bicep", "hammer"]):
        color = "#7c3aed"; icon = "💪"
    elif any(x in e for x in ["tricep", "pushdown", "extension"]):
        color = "#0ea5e9"; icon = "↓"
    elif any(x in e for x in ["shoulder", "lateral", "raise", "face pull", "shrug"]):
        color = "#d99b19"; icon = "△"
    elif any(x in e for x in ["hip", "hamstring", "calf", "knee", "glute"]):
        color = "#16a34a"; icon = "🦵"
    elif "ab" in e or "core" in e or "torso" in e:
        color = "#ef4444"; icon = "◎"
    title = html.escape(exercise[:20])
    muscle_txt = html.escape(muscle[:20])
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="244" height="172" viewBox="0 0 244 172">
    <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{color}"/><stop offset="1" stop-color="#071b33"/></linearGradient></defs>
    <rect width="244" height="172" rx="26" fill="#eef5ff"/>
    <circle cx="62" cy="66" r="38" fill="url(#g)"/>
    <text x="62" y="77" text-anchor="middle" font-size="32" font-family="Arial" fill="white" font-weight="800">{icon}</text>
    <rect x="112" y="44" width="92" height="12" rx="6" fill="{color}" opacity=".22"/>
    <rect x="112" y="66" width="74" height="12" rx="6" fill="{color}" opacity=".16"/>
    <rect x="112" y="88" width="55" height="12" rx="6" fill="{color}" opacity=".14"/>
    <text x="22" y="136" font-size="18" font-family="Arial" fill="#0b1f3a" font-weight="900">{title}</text>
    <text x="22" y="157" font-size="12" font-family="Arial" fill="#64748b" font-weight="700">{muscle_txt}</text>
    </svg>'''
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def page_header(title: str, subtitle: str = ""):
    st.markdown(f'<div class="hero"><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p><span class="pill">v15 Visual Exercise UI</span></div>', unsafe_allow_html=True)


ensure_data_files()
profile = load_profile()
workouts = workouts_df()
log = log_df()

st.sidebar.markdown("## 🏋️ BRIAN")
st.sidebar.markdown("**FITNESS TRACKER**")
st.sidebar.caption("v15 Visual Exercise UI")
page = st.sidebar.radio("Navigation", ["Dashboard", "Today Workout", "Weekly Plan", "Exercise Library", "Progress", "History", "Data Safety", "Profile", "Phone Setup"])

if page == "Dashboard":
    today = date.today().strftime("%A")
    today_plan = workouts[workouts["day"] == today]
    total_sessions = log["date"].nunique() if not log.empty else 0
    total_volume = log["volume"].sum() if not log.empty else 0
    avg_pain = log["pain"].mean() if not log.empty else 0
    page_header("Brian Fitness Tracker", "Professional visual tracker · workout images · safe workout history")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-card"><div class="label">Gym Sessions</div><div class="value">{total_sessions}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><div class="label">Total Volume</div><div class="value">{total_volume:,.0f}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><div class="label">Avg Knee Pain</div><div class="value">{avg_pain:.1f}/10</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><div class="label">Week</div><div class="value">{profile.get("week",1)}</div></div>', unsafe_allow_html=True)
    st.markdown("### Today's Mission")
    if not today_plan.empty:
        muscle = str(today_plan.iloc[0]["muscle_group"])
        workout = str(today_plan.iloc[0]["workout"])
        st.markdown(f'<div class="card"><h3>{today} — {html.escape(workout)}</h3><span class="badge">{html.escape(muscle)}</span><span class="badge green">{len(today_plan)} exercises</span><p class="small">Open Today Workout to track sets, weight, reps, pain, and notes.</p></div>', unsafe_allow_html=True)
    else:
        st.info("No workout plan found for today.")
    st.markdown("### This Week's Plan")
    for day in DAYS:
        d = workouts[workouts["day"] == day]
        if d.empty: continue
        cls = "week-card active" if day == today else "week-card"
        st.markdown(f'<div class="{cls}"><div class="dow">{day.upper()}</div><div class="muscle">{html.escape(str(d.iloc[0]["muscle_group"]))}</div><div class="small">{html.escape(str(d.iloc[0]["workout"]))} · {len(d)} exercises</div></div>', unsafe_allow_html=True)

elif page == "Today Workout":
    st.markdown("## Today's Workout")
    selected_day = st.selectbox("Workout Day", DAYS, index=DAYS.index(date.today().strftime("%A")) if date.today().strftime("%A") in DAYS else 0)
    day_df = workouts[workouts["day"] == selected_day].reset_index(drop=True)
    if day_df.empty:
        st.warning("No exercises found for this day.")
        st.stop()
    workout_name = str(day_df.iloc[0]["workout"])
    muscle_group = str(day_df.iloc[0]["muscle_group"])
    st.markdown(f'<div class="card"><h2>{selected_day} — {html.escape(workout_name)}</h2><span class="badge">{html.escape(muscle_group)}</span><span class="badge green">{len(day_df)} exercises</span><p class="small">Small exercise images are included so you can quickly recognize each movement. Replace them later with real photos in a future build.</p></div>', unsafe_allow_html=True)
    if selected_day == "Thursday":
        st.markdown('<div class="warn">🦵 Leg Rehab Day: no downward loading. Stop anything that causes knee pain.</div>', unsafe_allow_html=True)
    if selected_day == "Sunday":
        st.markdown('<div class="safe">Recovery day: swim, bike, sauna, mobility, and easy recovery work.</div>', unsafe_allow_html=True)
    cdate, cweek = st.columns(2)
    workout_date = cdate.date_input("Date", value=date.today())
    week_num = cweek.number_input("Week", min_value=1, max_value=52, value=int(profile.get("week", 1)), step=1)
    rows = []
    for i, row in day_df.iterrows():
        exercise = str(row["exercise"])
        target_sets = int(row["target_sets"])
        target_reps = str(row["target_reps"])
        default_weight = float(row["starting_weight_lbs"])
        notes = str(row.get("notes", ""))
        img = svg_thumb(exercise, muscle_group)
        best = best_weight(log, exercise)
        st.markdown('<div class="exercise-row">', unsafe_allow_html=True)
        col_img, col_info, col_stat = st.columns([1, 3, 1.3])
        with col_img:
            st.markdown(f'<img class="thumbnail" src="{img}" />', unsafe_allow_html=True)
        with col_info:
            st.markdown(f'<div class="ex-title">{i+1}. {html.escape(exercise)}</div>', unsafe_allow_html=True)
            st.markdown(f'<span class="badge">Target: {target_sets} × {html.escape(target_reps)}</span><span class="badge green">{html.escape(muscle_group)}</span>', unsafe_allow_html=True)
            if notes and notes != "nan":
                st.markdown(f'<div class="small">{html.escape(notes)}</div>', unsafe_allow_html=True)
            if best > 0:
                st.markdown(f'<span class="badge gold">🏆 PR {best:g} lbs</span>', unsafe_allow_html=True)
        with col_stat:
            st.markdown('<div class="volume"><div class="vlabel">Exercise Total</div><div class="vvalue">Auto</div></div>', unsafe_allow_html=True)
        with st.expander(f"Track {exercise}", expanded=(i == 0)):
            top1, top2, top3 = st.columns(3)
            sets = top1.number_input("Sets", min_value=1, max_value=8, value=target_sets, key=f"sets_{selected_day}_{i}")
            pain = top2.number_input("Pain 0-10", min_value=0, max_value=10, value=0, key=f"pain_{selected_day}_{i}")
            note = top3.text_input("Notes", value="", key=f"note_{selected_day}_{i}", placeholder="felt good, too heavy, knee okay")
            total_ex_vol = 0.0
            for s in range(1, sets + 1):
                last_w, last_r = last_set_value(log, exercise, s, default_weight)
                c1, c2, c3 = st.columns([1, 1, 1])
                weight = c1.number_input(f"Set {s} lbs", min_value=0.0, value=float(last_w), step=2.5, key=f"w_{selected_day}_{i}_{s}")
                reps = c2.number_input(f"Set {s} reps", min_value=0, value=int(last_r), step=1, key=f"r_{selected_day}_{i}_{s}")
                volume = weight * reps
                total_ex_vol += volume
                c3.markdown(f'<div class="volume"><div class="vlabel">Set {s} Volume</div><div class="vvalue">{volume:,.0f}</div></div>', unsafe_allow_html=True)
                if reps > 0:
                    rows.append({"date": str(workout_date), "saved_at": datetime.now().isoformat(timespec="seconds"), "week": int(week_num), "day": selected_day, "workout": workout_name, "muscle_group": muscle_group, "exercise": exercise, "set_number": s, "weight_lbs": weight, "reps": reps, "pain": pain, "notes": note, "volume": volume})
            st.markdown(f'**Exercise Volume:** {total_ex_vol:,.0f} lbs')
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="save">', unsafe_allow_html=True)
    if st.button("💾 SAVE TODAY'S WORKOUT"):
        if rows:
            new_rows = pd.DataFrame(rows)
            current = log_df()
            backup_data()
            combined = pd.concat([current, new_rows], ignore_index=True)
            save_csv(combined, LOG_FILE)
            update_personal_records(new_rows)
            st.success(f"Saved {len(new_rows)} completed sets to data/workout_log.csv")
            st.balloons()
        else:
            st.warning("Enter reps for at least one set before saving.")
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "Weekly Plan":
    st.markdown("## Weekly Plan")
    for day in DAYS:
        d = workouts[workouts["day"] == day]
        if d.empty: continue
        st.markdown(f'<div class="week-card"><div class="dow">{day.upper()}</div><div class="muscle">{html.escape(str(d.iloc[0]["muscle_group"]))}</div><div class="small">{html.escape(str(d.iloc[0]["workout"]))} · {len(d)} exercises</div></div>', unsafe_allow_html=True)
        cols = st.columns(3)
        for idx, (_, row) in enumerate(d.iterrows()):
            with cols[idx % 3]:
                st.markdown(f'<div class="card"><img class="thumbnail" src="{svg_thumb(str(row.exercise), str(row.muscle_group))}"/><div class="ex-title">{html.escape(str(row.exercise))}</div><span class="badge">{int(row.target_sets)} × {html.escape(str(row.target_reps))}</span></div>', unsafe_allow_html=True)

elif page == "Exercise Library":
    st.markdown("## Exercise Library")
    st.caption("Built-in thumbnails now show the exercise category. Real photos can be added in a future image pack.")
    search = st.text_input("Search exercise")
    df = workouts.copy()
    if search:
        df = df[df["exercise"].str.contains(search, case=False, na=False)]
    cols = st.columns(3)
    for idx, (_, row) in enumerate(df.iterrows()):
        with cols[idx % 3]:
            st.markdown(f'<div class="card"><img class="thumbnail" src="{svg_thumb(str(row.exercise), str(row.muscle_group))}"/><div class="ex-title">{html.escape(str(row.exercise))}</div><span class="badge">{html.escape(str(row.muscle_group))}</span><p class="small">{html.escape(str(row.day))} · {int(row.target_sets)} sets × {html.escape(str(row.target_reps))}</p></div>', unsafe_allow_html=True)

elif page == "Progress":
    st.markdown("## Progress")
    log = log_df()
    if log.empty:
        st.info("No completed workouts saved yet.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Sessions", log["date"].nunique())
        c2.metric("Total Volume", f"{log['volume'].sum():,.0f} lbs")
        c3.metric("Average Pain", f"{log['pain'].mean():.1f}/10")
        daily = log.groupby("date", as_index=False)["volume"].sum()
        st.plotly_chart(px.line(daily, x="date", y="volume", title="Workout Volume by Day"), use_container_width=True)
        ex = log.groupby("exercise", as_index=False).agg(best_weight=("weight_lbs", "max"), total_volume=("volume", "sum"), sets=("set_number", "count")).sort_values("total_volume", ascending=False)
        st.dataframe(ex, use_container_width=True)

elif page == "History":
    st.markdown("## Workout History")
    log = log_df()
    if log.empty:
        st.info("No saved workout history yet.")
    else:
        st.dataframe(log.sort_values(["date", "saved_at"], ascending=[False, False]), use_container_width=True)
        st.download_button("Download workout_log.csv", log.to_csv(index=False).encode("utf-8"), "workout_log.csv", "text/csv")

elif page == "Data Safety":
    st.markdown("## Data Safety")
    st.markdown('<div class="safe">Your workout plan is stored in data/workouts.csv. Your completed workout history is stored separately in data/workout_log.csv.</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Create Backup Now"):
            b = backup_data()
            st.success(f"Backup created: {b.name}")
    with c2:
        st.download_button("Export All Data ZIP", make_export_zip(), "brian_fitness_data_export.zip", "application/zip")
    st.write("Workout log rows:", len(log_df()))
    st.write("Backups folder:", str(BACKUP_DIR))

elif page == "Profile":
    st.markdown("## Profile")
    profile["current_weight"] = st.number_input("Current Weight", min_value=0.0, value=float(profile.get("current_weight", 0.0)), step=0.5)
    profile["goal_weight"] = st.number_input("Goal Weight", min_value=0.0, value=float(profile.get("goal_weight", 0.0)), step=0.5)
    profile["week"] = st.number_input("Week #", min_value=1, max_value=52, value=int(profile.get("week", 1)), step=1)
    if st.button("Save Profile"):
        save_profile(profile)
        st.success("Profile saved.")

elif page == "Phone Setup":
    st.markdown("## Phone Setup")
    ip = get_lan_ip()
    st.info("Local computer use works only when phone and computer are on the same Wi-Fi. For gym use, deploy through Streamlit Cloud.")
    st.code(f"http://{ip}:8501")
    st.markdown("Open your Streamlit Cloud app URL on your phone and add it to your Home Screen.")
