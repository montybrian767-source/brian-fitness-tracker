
from __future__ import annotations
import csv, json, re, socket
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
EXERCISE_IMG_DIR = ASSETS_DIR / "exercises"
STYLE_FILE = APP_DIR / "styles" / "theme.css"
WORKOUTS_FILE = DATA_DIR / "workouts.csv"
LOG_FILE = DATA_DIR / "workout_log.csv"
PROFILE_FILE = DATA_DIR / "profile.csv"

LOG_COLUMNS = ["date","saved_at","week","day","workout","muscle_group","exercise","set_number","weight_lbs","reps","pain","rpe","notes","volume"]
DAY_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

st.set_page_config(page_title="Brian Fitness Tracker 2.0 Alpha 3", page_icon="🏋️", layout="wide", initial_sidebar_state="expanded")


def load_css():
    if STYLE_FILE.exists():
        st.markdown(f"<style>{STYLE_FILE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def ensure_files():
    DATA_DIR.mkdir(exist_ok=True)
    EXERCISE_IMG_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        pd.DataFrame(columns=LOG_COLUMNS).to_csv(LOG_FILE, index=False)


def load_workouts() -> pd.DataFrame:
    df = pd.read_csv(WORKOUTS_FILE)
    df.columns = [c.strip().lower() for c in df.columns]
    required = ["day","workout","muscle_group","exercise","target_sets","target_reps"]
    for c in required:
        if c not in df.columns:
            df[c] = "" if c not in ["target_sets"] else 3
    if "image_file" not in df.columns:
        df["image_file"] = df["exercise"].map(lambda x: slug(x) + ".svg")
    return df


def load_log() -> pd.DataFrame:
    ensure_files()
    try:
        df = pd.read_csv(LOG_FILE)
    except Exception:
        df = pd.DataFrame(columns=LOG_COLUMNS)
    for c in LOG_COLUMNS:
        if c not in df.columns:
            df[c] = 0 if c in ["week","set_number","weight_lbs","reps","pain","rpe","volume"] else ""
    return df[LOG_COLUMNS]


def save_rows(rows: list[dict]):
    ensure_files()
    df = load_log()
    new = pd.DataFrame(rows)
    for c in LOG_COLUMNS:
        if c not in new.columns:
            new[c] = 0 if c in ["week","set_number","weight_lbs","reps","pain","rpe","volume"] else ""
    out = pd.concat([df, new[LOG_COLUMNS]], ignore_index=True)
    out.to_csv(LOG_FILE, index=False)


def load_profile() -> dict:
    profile = {"current_weight": 0, "goal_weight": 0, "week": 1}
    if PROFILE_FILE.exists():
        try:
            p = pd.read_csv(PROFILE_FILE)
            for _, r in p.iterrows():
                profile[str(r.get("key"))] = r.get("value")
        except Exception:
            pass
    return profile


def latest_set(log: pd.DataFrame, exercise: str, set_number: int, fallback_weight=0.0):
    if log.empty:
        return float(fallback_weight), 0
    ex = log[(log["exercise"].astype(str) == exercise) & (log["set_number"].astype(int) == set_number)].copy()
    if ex.empty:
        return float(fallback_weight), 0
    ex["saved_at_dt"] = pd.to_datetime(ex["saved_at"], errors="coerce")
    ex = ex.sort_values("saved_at_dt")
    r = ex.iloc[-1]
    return float(r.get("weight_lbs", fallback_weight) or fallback_weight), int(r.get("reps", 0) or 0)


def best_weight(log: pd.DataFrame, exercise: str) -> float:
    if log.empty: return 0.0
    ex = log[log["exercise"].astype(str) == exercise]
    if ex.empty: return 0.0
    return float(pd.to_numeric(ex["weight_lbs"], errors="coerce").max() or 0)


def img_path(row) -> Path | None:
    file = str(row.get("image_file", "") or "").strip()
    if not file:
        file = slug(str(row.get("exercise", "exercise"))) + ".svg"
    p = EXERCISE_IMG_DIR / file
    if p.exists():
        return p
    # fallback to slug
    p = EXERCISE_IMG_DIR / (slug(str(row.get("exercise", "exercise"))) + ".svg")
    return p if p.exists() else None


def exercise_cues(exercise: str) -> list[str]:
    e = exercise.lower()
    if "pulldown" in e:
        return ["Keep chest tall and shoulders down.", "Pull elbows toward your ribs.", "Control the weight on the way up."]
    if "row" in e:
        return ["Sit tall and brace your core.", "Pull with elbows, not hands.", "Squeeze shoulder blades together."]
    if "chest" in e or "press" in e:
        return ["Set shoulders back before pressing.", "Keep wrists stacked over elbows.", "Stop 1–2 reps before failure."]
    if "curl" in e:
        return ["Keep elbows still.", "Use full control, no swinging.", "Squeeze at the top."]
    if "tricep" in e or "pushdown" in e or "extension" in e:
        return ["Lock elbows near your sides.", "Move only at the elbow.", "Pause at the bottom."]
    if "leg" in e or "hip" in e or "hamstring" in e or "calf" in e:
        return ["Protect the right knee.", "Use pain-free range only.", "Slow and controlled reps."]
    return ["Use controlled form.", "Breathe through each rep.", "Stop if pain appears."]


def workout_totals(rows: list[dict]) -> dict:
    return {
        "sets": len(rows),
        "volume": sum(float(r.get("volume", 0) or 0) for r in rows),
        "exercises": len(set(r.get("exercise", "") for r in rows)),
        "avg_rpe": round(sum(float(r.get("rpe", 0) or 0) for r in rows) / len(rows), 1) if rows else 0,
    }


def phone_ip() -> str:
    try:
        s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8",80)); ip=s.getsockname()[0]; s.close(); return ip
    except Exception: return "YOUR-COMPUTER-IP"


def sidebar(page_options):
    st.sidebar.markdown('<div class="brand"><div class="brand-title">BRIAN FITNESS<br/>TRACKER 2.0</div><div class="brand-sub">Commercial Alpha 3</div></div>', unsafe_allow_html=True)
    page = st.sidebar.radio("Navigation", page_options, label_visibility="collapsed")
    st.sidebar.markdown('<div class="sidebar-card"><b>Data Status</b><br/><span style="color:#a8c7ff!important">Workout history saves to</span><br/><code>data/workout_log.csv</code></div>', unsafe_allow_html=True)
    with st.sidebar.expander("📱 Phone Link"):
        st.code(f"http://{phone_ip()}:8501")
    return page


def stat_cards(log):
    sessions = log["date"].nunique() if not log.empty else 0
    volume = pd.to_numeric(log["volume"], errors="coerce").sum() if not log.empty else 0
    sets = len(log) if not log.empty else 0
    prs = log.groupby("exercise")["weight_lbs"].max().shape[0] if not log.empty else 0
    cols = st.columns(4)
    cols[0].markdown(f'<div class="big-stat"><div class="label">Sessions</div><div class="value">{sessions}</div></div>', unsafe_allow_html=True)
    cols[1].markdown(f'<div class="big-stat"><div class="label">Total Volume</div><div class="value">{volume:,.0f}</div></div>', unsafe_allow_html=True)
    cols[2].markdown(f'<div class="big-stat"><div class="label">Sets Saved</div><div class="value">{sets}</div></div>', unsafe_allow_html=True)
    cols[3].markdown(f'<div class="big-stat"><div class="label">Tracked Lifts</div><div class="value">{prs}</div></div>', unsafe_allow_html=True)


def dashboard(workouts, log):
    today = date.today().strftime("%A")
    active = workouts[workouts["day"] == today]
    if active.empty:
        active = workouts[workouts["day"] == "Monday"]
        today = "Monday"
    workout = active["workout"].iloc[0] if not active.empty else "Workout"
    muscle = active["muscle_group"].iloc[0] if not active.empty else "Training"
    st.markdown(f'<div class="hero"><h1>Today\'s Mission</h1><p>{today} • {workout} • {muscle}</p></div>', unsafe_allow_html=True)
    stat_cards(log)
    score = alpha_score(log)
    st.markdown(f'<div class="coach-strip">🔥 Comeback Score: <b>{score}/100</b> • Alpha 3 tracks PRs, muscle volume, and coaching signals.</div>', unsafe_allow_html=True)
    st.markdown("### Weekly Plan")
    cols = st.columns(7)
    for i, day in enumerate(DAY_ORDER):
        d = workouts[workouts["day"]==day]
        if d.empty: continue
        wk = d["workout"].iloc[0]
        mg = d["muscle_group"].iloc[0]
        count = len(d)
        cols[i].markdown(f'<div class="card"><div class="pill">{day[:3]}</div><div class="card-title" style="margin-top:10px">{wk}</div><div class="muted">{mg}</div><br/><b>{count}</b> exercises</div>', unsafe_allow_html=True)
    if not log.empty:
        daily = log.groupby("date", as_index=False)["volume"].sum()
        st.plotly_chart(px.bar(daily, x="date", y="volume", title="Volume by Day"), use_container_width=True)



def personal_records(log: pd.DataFrame) -> pd.DataFrame:
    if log.empty:
        return pd.DataFrame(columns=["exercise", "best_weight", "best_reps", "best_volume"])
    x = log.copy()
    x["weight_lbs"] = pd.to_numeric(x["weight_lbs"], errors="coerce").fillna(0)
    x["reps"] = pd.to_numeric(x["reps"], errors="coerce").fillna(0)
    x["volume"] = pd.to_numeric(x["volume"], errors="coerce").fillna(0)
    best = x.sort_values(["weight_lbs", "reps"], ascending=False).groupby("exercise", as_index=False).first()
    out = best[["exercise", "weight_lbs", "reps", "volume"]].rename(columns={"weight_lbs":"best_weight", "reps":"best_reps", "volume":"best_volume"})
    return out.sort_values("best_weight", ascending=False)


def alpha_score(log: pd.DataFrame) -> int:
    if log.empty:
        return 0
    sessions = log["date"].nunique()
    total_sets = len(log)
    avg_pain = pd.to_numeric(log["pain"], errors="coerce").fillna(0).mean()
    score = min(100, int(sessions * 8 + min(total_sets, 120) * .35 - avg_pain * 3))
    return max(0, score)


def rest_timer_box(seconds: int):
    st.markdown('<div class="card"><div class="card-title">Rest Timer</div>', unsafe_allow_html=True)
    if "rest_end" not in st.session_state:
        st.session_state.rest_end = None
    c1, c2 = st.columns(2)
    if c1.button(f"Start {seconds}s Rest", key="start_rest_timer"):
        st.session_state.rest_end = datetime.now() + timedelta(seconds=int(seconds))
    if c2.button("Reset Timer", key="reset_rest_timer"):
        st.session_state.rest_end = None
    if st.session_state.rest_end:
        remaining = int((st.session_state.rest_end - datetime.now()).total_seconds())
        if remaining > 0:
            st.markdown(f'<div class="rest-number">{remaining}s</div><div class="muted">Refresh or interact to update.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="safe-note">Rest complete — ready for next set.</div>', unsafe_allow_html=True)
            st.session_state.rest_end = None
    else:
        st.markdown(f'<div class="rest-number">{seconds}s</div><div class="muted">Tap start after a hard set.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def workout_page(workouts, log):
    st.markdown('<div class="hero"><h1>Today’s Workout</h1><p>Alpha 3 adds analytics, PR tracking, smarter coaching cues, and an improved rest timer workflow.</p></div>', unsafe_allow_html=True)
    cday, cdate, cweek, crest = st.columns([2,1,1,1])
    today = date.today().strftime("%A")
    day = cday.selectbox("Workout Day", DAY_ORDER, index=DAY_ORDER.index(today) if today in DAY_ORDER else 0)
    wdate = cdate.date_input("Date", value=date.today())
    week = int(cweek.number_input("Week", min_value=1, max_value=52, value=1, step=1))
    rest_seconds = int(crest.selectbox("Rest Timer", [30, 45, 60, 75, 90, 120], index=2))
    active = workouts[workouts["day"] == day].reset_index(drop=True)
    if active.empty:
        st.warning("No workout found for this day."); return
    workout = str(active["workout"].iloc[0])
    muscle = str(active["muscle_group"].iloc[0])
    main, right = st.columns([3.4,1.15], gap="large")
    rows=[]
    completed_exercises = 0
    with main:
        st.markdown(f"### {day} — {workout}")
        st.markdown('<div class="coach-strip">🏋️ Gym Mode Tip: complete your sets left to right, tap the checkboxes as you finish, then save the whole workout at the bottom.</div>', unsafe_allow_html=True)
        for i, row in active.iterrows():
            ex = str(row["exercise"])
            sets = int(float(row.get("target_sets", 3) or 3))
            target_reps = str(row.get("target_reps", "12"))
            start_w = float(row.get("starting_weight_lbs", 0) or 0)
            best = best_weight(log, ex)
            st.markdown('<div class="exercise-card alpha2-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="exercise-head"><div><div class="exercise-name">{ex}</div><div class="muted">Previous best: {best:g} lbs • Target {sets} × {target_reps}</div></div><div class="target-badge">Alpha 3 Card</div></div>', unsafe_allow_html=True)
            imgcol, formcol, cuecol = st.columns([1.05,2.05,1.05], gap="medium")
            with imgcol:
                path = img_path(row)
                if path:
                    st.image(str(path), use_container_width=True)
                else:
                    st.markdown('<div class="image-fallback"><b>Image coming soon</b><br/><span>assets/exercises</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="mini-stat"><span>PR</span><b>{best:g} lbs</b></div>', unsafe_allow_html=True)
            entered_any = False
            with formcol:
                notes = st.text_input("Notes", key=f"note_{day}_{i}", placeholder="Form, difficulty, pain, etc.")
                pain, rpe = st.columns(2)
                pain_val = int(pain.number_input("Pain 0-10", min_value=0, max_value=10, value=0, key=f"pain_{day}_{i}"))
                rpe_val = int(rpe.number_input("Effort RPE", min_value=0, max_value=10, value=7, key=f"rpe_{day}_{i}"))
                st.markdown('<div class="set-table-head"><span>Set</span><span>Weight</span><span>Reps</span><span>Done</span><span>Volume</span></div>', unsafe_allow_html=True)
                for s in range(1, sets+1):
                    lw, lr = latest_set(log, ex, s, start_w)
                    a,b,c,d,e = st.columns([.45,1,1,.65,1])
                    a.markdown(f"**{s}**")
                    weight = b.number_input("lbs", min_value=0.0, value=float(lw), step=2.5, key=f"w_{day}_{i}_{s}", label_visibility="collapsed")
                    reps = c.number_input("reps", min_value=0, value=int(lr or 0), step=1, key=f"r_{day}_{i}_{s}", label_visibility="collapsed")
                    done = d.checkbox("", value=bool(reps > 0), key=f"done_{day}_{i}_{s}")
                    vol = weight * reps if done else 0
                    e.markdown(f"<b>{vol:,.0f}</b><br/><span class='muted'>lbs</span>", unsafe_allow_html=True)
                    if done and reps > 0:
                        entered_any = True
                        rows.append({"date":str(wdate),"saved_at":datetime.now().isoformat(timespec="seconds"),"week":week,"day":day,"workout":workout,"muscle_group":muscle,"exercise":ex,"set_number":s,"weight_lbs":weight,"reps":reps,"pain":pain_val,"rpe":rpe_val,"notes":notes,"volume":vol})
            with cuecol:
                st.markdown('<div class="cue-card"><div class="card-title">How To</div>', unsafe_allow_html=True)
                for cue in exercise_cues(ex):
                    st.markdown(f'<div class="cue">✓ {cue}</div>', unsafe_allow_html=True)
                if pain_val >= 4:
                    st.markdown('<div class="danger-note">Knee/pain warning: reduce load or stop.</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="safe-note">Pain check OK.</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            if entered_any:
                completed_exercises += 1
            st.markdown('</div>', unsafe_allow_html=True)
        totals = workout_totals(rows)
        st.markdown(f'<div class="finish-panel"><b>Workout Ready to Save</b><br/>{totals["sets"]} sets • {totals["volume"]:,.0f} lbs volume • Avg RPE {totals["avg_rpe"]}</div>', unsafe_allow_html=True)
        if st.button("💾 Save Full Workout", type="primary"):
            if rows:
                save_rows(rows)
                st.success(f"Saved {len(rows)} sets to data/workout_log.csv")
                st.balloons()
            else:
                st.warning("Enter reps and mark at least one set complete before saving.")
    with right:
        totals = workout_totals(rows)
        st.markdown('<div class="summary-panel">', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><div class="card-title">Live Summary</div><div class="muted">{day}</div><hr/><b>{completed_exercises} / {len(active)}</b> exercises started<br/><b>{totals["sets"]}</b> sets complete<br/><b>{totals["volume"]:,.0f}</b> lbs volume<br/><b>{totals["avg_rpe"]}</b> avg RPE</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><div class="card-title">Muscle Focus</div><div class="pill">{muscle}</div><br/><br/><div class="muted">Protect the right knee. Leave every workout feeling like you could do more.</div></div>', unsafe_allow_html=True)
        rest_timer_box(rest_seconds)
        st.markdown('<div class="card"><div class="card-title">Quick Actions</div><a class="action-btn">Export Backup</a><a class="action-btn" style="background:#16a34a">Finish Workout</a><a class="action-btn" style="background:#f59e0b">Add Note</a></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="timer">⏱️ Rest Timer: {rest_seconds}s • Alpha 3 Workout Intelligence</div>', unsafe_allow_html=True)


def gym_mode_page(workouts, log):
    st.markdown('<div class="hero"><h1>Gym Mode</h1><p>Simple one-exercise focus screen for phone use during workouts.</p></div>', unsafe_allow_html=True)
    today = date.today().strftime("%A")
    day = st.selectbox("Day", DAY_ORDER, index=DAY_ORDER.index(today) if today in DAY_ORDER else 0, key="gym_day")
    active = workouts[workouts["day"] == day].reset_index(drop=True)
    if active.empty:
        st.warning("No workout found."); return
    idx = int(st.number_input("Exercise #", min_value=1, max_value=len(active), value=1, step=1)) - 1
    row = active.iloc[idx]
    ex = str(row["exercise"])
    sets = int(float(row.get("target_sets", 3) or 3))
    target_reps = str(row.get("target_reps", "12"))
    st.markdown('<div class="gym-focus">', unsafe_allow_html=True)
    path = img_path(row)
    if path:
        st.image(str(path), use_container_width=True)
    st.markdown(f'<h1>{ex}</h1><div class="pill">Target {sets} × {target_reps}</div>', unsafe_allow_html=True)
    st.markdown('<div class="gym-actions"><span>⬅ Previous</span><span>Start Set</span><span>Next ➡</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def history_page(log):
    st.markdown('<div class="hero"><h1>History</h1><p>Your saved workouts from data/workout_log.csv.</p></div>', unsafe_allow_html=True)
    if log.empty:
        st.info("No workout history yet.")
    else:
        st.dataframe(log.sort_values(["date","saved_at"], ascending=False), use_container_width=True)
        st.download_button("Download workout_log.csv", log.to_csv(index=False).encode(), "workout_log.csv", "text/csv")



def progress_page(workouts, log):
    st.markdown('<div class="hero"><h1>Progress Analytics</h1><p>Alpha 3 turns your workout log into progress charts, PRs, and muscle group insights.</p></div>', unsafe_allow_html=True)
    if log.empty:
        st.info("No workout history yet. Save a workout first.")
        return
    x = log.copy()
    x["volume"] = pd.to_numeric(x["volume"], errors="coerce").fillna(0)
    x["weight_lbs"] = pd.to_numeric(x["weight_lbs"], errors="coerce").fillna(0)
    x["reps"] = pd.to_numeric(x["reps"], errors="coerce").fillna(0)
    x["pain"] = pd.to_numeric(x["pain"], errors="coerce").fillna(0)
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="big-stat"><div class="label">Comeback Score</div><div class="value">{alpha_score(x)}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="big-stat"><div class="label">Total Volume</div><div class="value">{x["volume"].sum():,.0f}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="big-stat"><div class="label">Avg Pain</div><div class="value">{x["pain"].mean():.1f}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="big-stat"><div class="label">Exercises</div><div class="value">{x["exercise"].nunique()}</div></div>', unsafe_allow_html=True)
    daily = x.groupby("date", as_index=False).agg(volume=("volume","sum"), sets=("exercise","count"), pain=("pain","mean"))
    st.plotly_chart(px.line(daily, x="date", y="volume", markers=True, title="Daily Training Volume"), use_container_width=True)
    muscle = x.groupby("muscle_group", as_index=False)["volume"].sum().sort_values("volume", ascending=False)
    st.plotly_chart(px.bar(muscle, x="muscle_group", y="volume", title="Volume by Muscle Group"), use_container_width=True)
    st.markdown("### Personal Records")
    st.dataframe(personal_records(x).head(20), use_container_width=True)


def coach_page(workouts, log):
    st.markdown('<div class="hero"><h1>AI Coach Preview</h1><p>Alpha 3 gives simple rule-based coaching recommendations from your saved workouts.</p></div>', unsafe_allow_html=True)
    if log.empty:
        st.info("Save a workout first and the coach will start making recommendations.")
        return
    x = log.copy()
    x["weight_lbs"] = pd.to_numeric(x["weight_lbs"], errors="coerce").fillna(0)
    x["reps"] = pd.to_numeric(x["reps"], errors="coerce").fillna(0)
    x["pain"] = pd.to_numeric(x["pain"], errors="coerce").fillna(0)
    x["rpe"] = pd.to_numeric(x["rpe"], errors="coerce").fillna(0)
    latest_date = x["date"].astype(str).max()
    latest = x[x["date"].astype(str) == latest_date]
    avg_pain = latest["pain"].mean() if not latest.empty else 0
    avg_rpe = latest["rpe"].mean() if not latest.empty else 0
    st.markdown(f'<div class="card"><div class="card-title">Latest Workout Review</div><b>Date:</b> {latest_date}<br/><b>Sets:</b> {len(latest)}<br/><b>Avg RPE:</b> {avg_rpe:.1f}<br/><b>Avg Pain:</b> {avg_pain:.1f}</div>', unsafe_allow_html=True)
    if avg_pain >= 4:
        st.markdown('<div class="danger-note">Recommendation: pain is elevated. Keep loads lighter and avoid lower-body stress until pain comes down.</div>', unsafe_allow_html=True)
    elif avg_rpe <= 7 and len(latest) > 0:
        st.markdown('<div class="safe-note">Recommendation: if all reps were completed comfortably, increase selected upper-body machine weights by 2.5–5 lb next time.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="coach-strip">Recommendation: hold the same weights next session and focus on clean reps.</div>', unsafe_allow_html=True)
    st.markdown("### Suggested Next Improvements")
    prs = personal_records(x).head(8)
    for _, r in prs.iterrows():
        ex = r["exercise"]
        bw = float(r["best_weight"] or 0)
        st.markdown(f'<div class="card"><div class="card-title">{ex}</div><div class="muted">Current best: {bw:g} lbs</div><b>Next target:</b> {bw + 2.5:g} lbs if pain-free and reps were completed.</div>', unsafe_allow_html=True)

def library_page(workouts):
    st.markdown('<div class="hero"><h1>Exercise Library</h1><p>Images are loaded from assets/exercises and mapped from workouts.csv.</p></div>', unsafe_allow_html=True)
    q = st.text_input("Search exercises", "")
    df = workouts.drop_duplicates("exercise")
    if q:
        df = df[df["exercise"].str.contains(q, case=False, na=False)]
    cols = st.columns(3)
    for idx, (_, row) in enumerate(df.iterrows()):
        with cols[idx % 3]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            path = img_path(row)
            if path: st.image(str(path), use_container_width=True)
            st.markdown(f'<div class="card-title">{row["exercise"]}</div><div class="muted">{row["muscle_group"]}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)


def data_safety(log):
    st.markdown('<div class="hero"><h1>Data Safety</h1><p>Keep workout_log.csv safe. Do not overwrite it during updates.</p></div>', unsafe_allow_html=True)
    st.success(f"Workout log location: {LOG_FILE}")
    st.metric("Rows saved", len(log))
    st.download_button("Export workout_log.csv", log.to_csv(index=False).encode(), "workout_log.csv", "text/csv")
    uploaded = st.file_uploader("Import workout_log.csv backup", type=["csv"])
    if uploaded and st.button("Replace workout log with uploaded backup"):
        df = pd.read_csv(uploaded)
        df.to_csv(LOG_FILE, index=False)
        st.success("Workout log restored.")


def main():
    ensure_files(); load_css()
    workouts = load_workouts()
    log = load_log()
    page = sidebar(["Dashboard","Today’s Workout","Gym Mode","Progress","Coach","Exercise Library","History","Data Safety"])
    if page == "Dashboard": dashboard(workouts, log)
    elif page == "Today’s Workout": workout_page(workouts, log)
    elif page == "Gym Mode": gym_mode_page(workouts, log)
    elif page == "Progress": progress_page(workouts, log)
    elif page == "Coach": coach_page(workouts, log)
    elif page == "Exercise Library": library_page(workouts)
    elif page == "History": history_page(log)
    elif page == "Data Safety": data_safety(log)

if __name__ == "__main__":
    main()
