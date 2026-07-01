
from __future__ import annotations
import csv, json, re, socket
from datetime import date, datetime
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

st.set_page_config(page_title="Brian Fitness Tracker 2.0 Alpha", page_icon="🏋️", layout="wide", initial_sidebar_state="expanded")


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


def phone_ip() -> str:
    try:
        s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8",80)); ip=s.getsockname()[0]; s.close(); return ip
    except Exception: return "YOUR-COMPUTER-IP"


def sidebar(page_options):
    st.sidebar.markdown('<div class="brand"><div class="brand-title">BRIAN FITNESS<br/>TRACKER 2.0</div><div class="brand-sub">Commercial Alpha 1</div></div>', unsafe_allow_html=True)
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


def workout_page(workouts, log):
    st.markdown('<div class="hero"><h1>Today\'s Workout</h1><p>Premium workout cards, live volume, image system, and safe workout logging.</p></div>', unsafe_allow_html=True)
    cday, cdate, cweek = st.columns([2,1,1])
    today = date.today().strftime("%A")
    day = cday.selectbox("Workout Day", DAY_ORDER, index=DAY_ORDER.index(today) if today in DAY_ORDER else 0)
    wdate = cdate.date_input("Date", value=date.today())
    week = int(cweek.number_input("Week", min_value=1, max_value=52, value=1, step=1))
    active = workouts[workouts["day"] == day].reset_index(drop=True)
    if active.empty:
        st.warning("No workout found for this day."); return
    workout = str(active["workout"].iloc[0])
    muscle = str(active["muscle_group"].iloc[0])
    main, right = st.columns([3.4,1.15], gap="large")
    rows=[]
    with main:
        st.markdown(f"### {day} — {workout}")
        for i, row in active.iterrows():
            ex = str(row["exercise"])
            sets = int(float(row.get("target_sets", 3) or 3))
            target_reps = str(row.get("target_reps", "12"))
            start_w = float(row.get("starting_weight_lbs", 0) or 0)
            best = best_weight(log, ex)
            st.markdown('<div class="exercise-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="exercise-head"><div><div class="exercise-name">{ex}</div><div class="muted">Previous best: {best:g} lbs</div></div><div class="target-badge">{sets} × {target_reps}</div></div>', unsafe_allow_html=True)
            imgcol, formcol = st.columns([1.1,2.15], gap="medium")
            with imgcol:
                path = img_path(row)
                if path:
                    st.image(str(path), use_container_width=True)
                else:
                    st.markdown('<div class="card" style="height:230px;display:flex;align-items:center;justify-content:center;text-align:center"><b>Image coming soon</b></div>', unsafe_allow_html=True)
            with formcol:
                notes = st.text_input("Notes", key=f"note_{day}_{i}", placeholder="Form, difficulty, pain, etc.")
                pain = int(st.number_input("Pain", min_value=0, max_value=10, value=0, key=f"pain_{day}_{i}"))
                rpe = int(st.number_input("RPE", min_value=0, max_value=10, value=7, key=f"rpe_{day}_{i}"))
                for s in range(1, sets+1):
                    lw, lr = latest_set(log, ex, s, start_w)
                    a,b,c,d = st.columns([.75,1,1,1])
                    a.markdown(f"**Set {s}**  ")
                    weight = b.number_input("lbs", min_value=0.0, value=float(lw), step=2.5, key=f"w_{day}_{i}_{s}", label_visibility="collapsed")
                    reps = c.number_input("reps", min_value=0, value=int(lr or 0), step=1, key=f"r_{day}_{i}_{s}", label_visibility="collapsed")
                    vol = weight * reps
                    d.markdown(f"<b>{vol:,.0f} lbs</b><br/><span class='muted'>volume</span>", unsafe_allow_html=True)
                    if reps > 0:
                        rows.append({"date":str(wdate),"saved_at":datetime.now().isoformat(timespec="seconds"),"week":week,"day":day,"workout":workout,"muscle_group":muscle,"exercise":ex,"set_number":s,"weight_lbs":weight,"reps":reps,"pain":pain,"rpe":rpe,"notes":notes,"volume":vol})
            st.markdown('</div>', unsafe_allow_html=True)
        if st.button("💾 Save Workout", type="primary"):
            if rows:
                save_rows(rows)
                st.success(f"Saved {len(rows)} sets to data/workout_log.csv")
                st.balloons()
            else:
                st.warning("Enter reps before saving.")
    with right:
        st.markdown('<div class="summary-panel">', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><div class="card-title">Workout Summary</div><div class="muted">{day}</div><hr/><b>{len(active)}</b> exercises<br/><b>{sum(int(float(x or 0)) for x in active["target_sets"]):}</b> target sets<br/><b>{sum(r.get("volume",0) for r in rows):,.0f}</b> planned volume</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><div class="card-title">Muscle Focus</div><div class="pill">{muscle}</div><br/><br/><div class="muted">Stay controlled. Protect the knee. Progress slowly.</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="card-title">Quick Actions</div><a class="action-btn">Export Backup</a><a class="action-btn" style="background:#16a34a">Finish Workout</a><a class="action-btn" style="background:#f59e0b">Rest Timer</a></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="timer">⏱️ Rest Timer Ready • Alpha 1 Framework</div>', unsafe_allow_html=True)


def history_page(log):
    st.markdown('<div class="hero"><h1>History</h1><p>Your saved workouts from data/workout_log.csv.</p></div>', unsafe_allow_html=True)
    if log.empty:
        st.info("No workout history yet.")
    else:
        st.dataframe(log.sort_values(["date","saved_at"], ascending=False), use_container_width=True)
        st.download_button("Download workout_log.csv", log.to_csv(index=False).encode(), "workout_log.csv", "text/csv")


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
    page = sidebar(["Dashboard","Today’s Workout","Exercise Library","History","Data Safety"])
    if page == "Dashboard": dashboard(workouts, log)
    elif page == "Today’s Workout": workout_page(workouts, log)
    elif page == "Exercise Library": library_page(workouts)
    elif page == "History": history_page(log)
    elif page == "Data Safety": data_safety(log)

if __name__ == "__main__":
    main()
