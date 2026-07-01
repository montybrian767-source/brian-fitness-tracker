from __future__ import annotations

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

WORKOUTS_FILE = DATA_DIR / "workouts.csv"          # workout template / plan
LOG_FILE = DATA_DIR / "workout_log.csv"            # completed workout history
PR_FILE = DATA_DIR / "personal_records.csv"
PROFILE_FILE = DATA_DIR / "profile.csv"
BACKUP_DIR = DATA_DIR / "backups"

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DO_NOT_DO = ["Leg Press", "Squats", "Lunges", "Running", "Stair Climber", "Smith Machine Squats", "Heavy Lower Body Loading"]

REQUIRED_LOG_COLS = [
    "date", "saved_at", "week", "day", "workout", "muscle_group", "exercise",
    "set_number", "weight_lbs", "reps", "pain", "notes", "volume"
]

st.set_page_config(
    page_title="Brian Fitness Tracker v14.5",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_CSS = """
:root{--bg:#f4f7fb;--navy:#0f2747;--blue:#2563eb;--teal:#0f766e;--gold:#d69e2e;--green:#16a34a;--red:#dc2626;--text:#1e293b;--muted:#64748b;--card:#ffffff;--line:#dbe3ef}.stApp{background:var(--bg);color:var(--text)}.block-container{padding-top:1rem;max-width:1180px}h1,h2,h3{color:var(--navy)!important}.hero{background:linear-gradient(135deg,#0f2747,#1d4ed8);padding:24px;border-radius:24px;color:white;margin-bottom:18px;box-shadow:0 12px 32px rgba(15,39,71,.18)}.hero h1{color:white!important;margin:0;font-size:2rem!important}.hero p{color:#dbeafe;margin:.35rem 0 0}.card{background:white;border:1px solid var(--line);border-radius:22px;padding:18px;margin:12px 0;box-shadow:0 8px 24px rgba(15,39,71,.07)}.day-card{background:white;border:1px solid var(--line);border-left:7px solid var(--blue);border-radius:20px;padding:16px;margin:10px 0}.day-title{font-size:1.1rem;font-weight:900;color:var(--navy)}.muted{color:var(--muted);font-weight:650}.badge{display:inline-block;border-radius:999px;padding:6px 11px;font-size:.8rem;font-weight:900;background:#e0edff;color:#174ea6;margin:3px}.badge-gold{background:#fff7db;color:#8a6100}.exercise-card{background:white;border:1px solid var(--line);border-radius:24px;padding:18px;margin:14px 0;border-left:8px solid var(--teal);box-shadow:0 8px 24px rgba(15,39,71,.08)}.exercise-name{font-size:1.45rem;font-weight:950;color:var(--navy);line-height:1.15}.volume-box{background:#f8fafc;border:1px solid var(--line);border-radius:16px;padding:12px;color:var(--navy);font-weight:900}.stButton>button{border-radius:14px;min-height:3rem;font-weight:900;border:1px solid var(--line)}.stNumberInput input{font-weight:900;text-align:center;color:#0f172a;background:#f8fafc}.stTextInput input{color:#0f172a;background:#f8fafc}.success-button button{background:var(--green)!important;color:white!important;border:none!important}[data-testid="stMetric"]{background:white;border:1px solid var(--line);border-radius:18px;padding:14px;box-shadow:0 5px 16px rgba(15,39,71,.06)}[data-testid="stMetricValue"]{color:var(--navy)!important;font-weight:950}.warning{background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;border-radius:18px;padding:14px;font-weight:850}.safe{background:#ecfdf5;border:1px solid #bbf7d0;color:#166534;border-radius:18px;padding:14px;font-weight:850}.danger{background:#fee2e2;border:1px solid #fecaca;color:#991b1b;border-radius:18px;padding:14px;font-weight:850}@media(max-width:700px){.block-container{padding-left:.6rem;padding-right:.6rem}.hero h1{font-size:1.45rem!important}.exercise-name{font-size:1.25rem}}
"""

st.markdown(f"<style>{CSS_FILE.read_text() if CSS_FILE.exists() else DEFAULT_CSS}</style>", unsafe_allow_html=True)


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


def get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "YOUR-COMPUTER-IP"


def workouts_df() -> pd.DataFrame:
    df = read_csv(WORKOUTS_FILE)
    required = ["day", "workout", "muscle_group", "exercise", "target_sets", "target_reps", "starting_weight_lbs", "notes"]
    for col in required:
        if col not in df.columns:
            df[col] = ""
    df["target_sets"] = pd.to_numeric(df["target_sets"], errors="coerce").fillna(3).astype(int)
    df["starting_weight_lbs"] = pd.to_numeric(df["starting_weight_lbs"], errors="coerce").fillna(0.0)
    return df


def log_df() -> pd.DataFrame:
    df = read_csv(LOG_FILE, REQUIRED_LOG_COLS)
    for col in ["week", "set_number", "reps", "pain"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    for col in ["weight_lbs", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def backup_data() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"workout_log_backup_{stamp}.csv"
    if LOG_FILE.exists():
        backup_file.write_bytes(LOG_FILE.read_bytes())
    else:
        save_csv(pd.DataFrame(columns=REQUIRED_LOG_COLS), backup_file)
    return backup_file


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
            records = pd.concat([records, pd.DataFrame([{
                "exercise": exercise, "best_weight_lbs": max_weight, "best_reps": best_reps,
                "best_volume": max_volume, "date": str(group.iloc[0]["date"]), "saved_at": datetime.now().isoformat(timespec="seconds")
            }])], ignore_index=True)
        else:
            idx = existing.index[0]
            old = float(records.loc[idx, "best_weight_lbs"] or 0)
            if max_weight > old:
                records.loc[idx, ["best_weight_lbs", "best_reps", "best_volume", "date", "saved_at"]] = [
                    max_weight, best_reps, max_volume, str(group.iloc[0]["date"]), datetime.now().isoformat(timespec="seconds")
                ]
    save_csv(records, PR_FILE)


def last_set_value(log: pd.DataFrame, exercise: str, set_number: int, fallback_weight: float) -> tuple[float, int]:
    if log.empty:
        return fallback_weight, 0
    ex = log[(log["exercise"] == exercise) & (log["set_number"] == set_number)].copy()
    if ex.empty:
        return fallback_weight, 0
    ex["_dt"] = pd.to_datetime(ex["saved_at"], errors="coerce")
    row = ex.sort_values("_dt").iloc[-1]
    return float(row["weight_lbs"]), int(row["reps"])


def make_export_zip() -> bytes:
    files = [WORKOUTS_FILE, LOG_FILE, PROFILE_FILE, PR_FILE, DATA_DIR / "nutrition_log.csv", DATA_DIR / "recovery_log.csv", DATA_DIR / "body_stats.csv"]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for path in files:
            if path.exists():
                z.write(path, arcname=f"data/{path.name}")
    buffer.seek(0)
    return buffer.getvalue()


ensure_data_files()
profile = load_profile()
workouts = workouts_df()
log = log_df()

st.sidebar.markdown("## 🏋️ Brian Fitness")
st.sidebar.caption("v14.5 Production Data Upgrade")
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Today Workout", "Weekly Plan", "Progress", "History", "Data Safety", "Profile", "Phone Setup"],
)

if page == "Dashboard":
    today = date.today().strftime("%A")
    today_plan = workouts[workouts["day"] == today]
    total_sessions = log["date"].nunique() if not log.empty else 0
    total_volume = log["volume"].sum() if not log.empty else 0
    avg_pain = log["pain"].mean() if not log.empty else 0

    st.markdown('<div class="hero"><h1>Brian Fitness Tracker v14.5</h1><p>Stable production base · workout plan separated from workout history</p></div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Weight", f"{profile.get('current_weight', 0):.1f} lbs")
    c2.metric("Goal Weight", f"{profile.get('goal_weight', 0):.1f} lbs")
    c3.metric("Gym Sessions", total_sessions)
    c4.metric("Total Volume", f"{total_volume:,.0f} lbs")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader(f"Today's Mission: {today}")
    if today_plan.empty:
        st.info("No workout scheduled today.")
    else:
        st.markdown(f"### {today_plan.iloc[0]['workout']}")
        st.markdown(f"<span class='badge'>{today_plan.iloc[0]['muscle_group']}</span> <span class='badge badge-gold'>{len(today_plan)} exercises</span>", unsafe_allow_html=True)
        st.write(", ".join(today_plan["exercise"].astype(str).tolist()))
    st.markdown('</div>', unsafe_allow_html=True)

    if avg_pain >= 5:
        st.markdown(f'<div class="danger">🦵 Knee pain average is {avg_pain:.1f}/10. Keep rehab conservative.</div>', unsafe_allow_html=True)
    elif total_sessions:
        st.markdown(f'<div class="safe">Average knee pain: {avg_pain:.1f}/10</div>', unsafe_allow_html=True)

elif page == "Today Workout":
    day = st.selectbox("Workout Day", DAYS, index=DAYS.index(date.today().strftime("%A")) if date.today().strftime("%A") in DAYS else 0)
    day_plan = workouts[workouts["day"] == day].reset_index(drop=True)
    workout_name = day_plan.iloc[0]["workout"] if not day_plan.empty else "Workout"
    muscle_group = day_plan.iloc[0]["muscle_group"] if not day_plan.empty else ""

    st.markdown(f'<div class="hero"><h1>{day}</h1><p>{workout_name} · {muscle_group}</p></div>', unsafe_allow_html=True)
    if day == "Thursday":
        st.markdown('<div class="warning">🦵 Leg Rehab Day: no downward loading. Stop anything that causes knee pain.</div>', unsafe_allow_html=True)
    if day == "Sunday":
        st.markdown('<div class="safe">Recovery Day: swimming, bike, sauna, mobility, and recovery.</div>', unsafe_allow_html=True)

    cdate, cweek = st.columns(2)
    workout_date = cdate.date_input("Date", value=date.today())
    week = cweek.number_input("Week", min_value=1, max_value=52, value=int(profile.get("week", 1)))

    pending_rows = []
    if day_plan.empty:
        st.warning("No exercises found for this day in data/workouts.csv")
    for i, row in day_plan.iterrows():
        exercise = str(row["exercise"])
        target_sets = int(row["target_sets"])
        target_reps = str(row["target_reps"])
        start_weight = float(row["starting_weight_lbs"])

        st.markdown('<div class="exercise-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="exercise-name">🏋️ {exercise}</div>', unsafe_allow_html=True)
        st.markdown(f"<span class='badge'>Target: {target_sets} × {target_reps}</span>", unsafe_allow_html=True)
        if str(row.get("notes", "")).strip():
            st.caption(str(row.get("notes", "")))

        top1, top2 = st.columns(2)
        sets = top1.number_input("Sets", min_value=1, max_value=8, value=target_sets, key=f"sets_{day}_{i}")
        pain = top2.number_input("Pain 0-10", min_value=0, max_value=10, value=0, key=f"pain_{day}_{i}")
        notes = st.text_input("Notes", value="", key=f"notes_{day}_{i}", placeholder="Example: felt good, knee okay, too heavy")

        for set_num in range(1, int(sets) + 1):
            last_w, last_r = last_set_value(log, exercise, set_num, start_weight)
            st.markdown(f"**Set {set_num}** · last: {last_w:g} lbs × {last_r} reps")
            c1, c2, c3 = st.columns([1, 1, 1])
            weight = c1.number_input("lbs", min_value=0.0, step=2.5, value=float(last_w), key=f"w_{day}_{i}_{set_num}")
            reps = c2.number_input("reps", min_value=0, step=1, value=int(last_r), key=f"r_{day}_{i}_{set_num}")
            volume = float(weight) * int(reps)
            c3.markdown(f'<div class="volume-box">Volume<br><span style="font-size:1.35rem">{volume:,.0f} lbs</span></div>', unsafe_allow_html=True)
            if reps > 0:
                pending_rows.append({
                    "date": str(workout_date),
                    "saved_at": datetime.now().isoformat(timespec="seconds"),
                    "week": int(week),
                    "day": day,
                    "workout": workout_name,
                    "muscle_group": muscle_group,
                    "exercise": exercise,
                    "set_number": int(set_num),
                    "weight_lbs": float(weight),
                    "reps": int(reps),
                    "pain": int(pain),
                    "notes": notes,
                    "volume": volume,
                })
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="success-button">', unsafe_allow_html=True)
    if st.button("💾 SAVE WORKOUT TO workout_log.csv"):
        if not pending_rows:
            st.warning("Enter reps for at least one set before saving.")
        else:
            backup_data()
            new_rows = pd.DataFrame(pending_rows)
            current_log = log_df()
            updated = pd.concat([current_log, new_rows], ignore_index=True)
            save_csv(updated, LOG_FILE)
            update_personal_records(new_rows)
            st.success(f"Saved {len(new_rows)} sets to data/workout_log.csv. Your workout plan file was not changed.")
            st.balloons()
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "Weekly Plan":
    st.markdown('<div class="hero"><h1>Weekly Plan</h1><p>Muscle groups and exercises from data/workouts.csv</p></div>', unsafe_allow_html=True)
    for day in DAYS:
        d = workouts[workouts["day"] == day]
        if d.empty:
            continue
        st.markdown(f'<div class="day-card"><div class="day-title">{day} — {d.iloc[0]["workout"]}</div><div class="muted">{d.iloc[0]["muscle_group"]} · {len(d)} exercises</div></div>', unsafe_allow_html=True)
        with st.expander(f"View {day} exercises"):
            st.dataframe(d[["exercise", "target_sets", "target_reps", "starting_weight_lbs", "notes"]], use_container_width=True, hide_index=True)

elif page == "Progress":
    st.markdown('<div class="hero"><h1>Progress</h1><p>Charts come from data/workout_log.csv</p></div>', unsafe_allow_html=True)
    if log.empty:
        st.info("No completed workouts saved yet.")
    else:
        daily = log.groupby("date", as_index=False).agg(volume=("volume", "sum"), sets=("set_number", "count"), avg_pain=("pain", "mean"))
        st.plotly_chart(px.line(daily, x="date", y="volume", title="Daily Training Volume"), use_container_width=True)
        best = log.groupby("exercise", as_index=False).agg(best_weight_lbs=("weight_lbs", "max"), total_volume=("volume", "sum"), total_sets=("set_number", "count")).sort_values("total_volume", ascending=False)
        st.subheader("Exercise Progress")
        st.dataframe(best, use_container_width=True, hide_index=True)

elif page == "History":
    st.markdown('<div class="hero"><h1>Workout History</h1><p>Completed workouts saved separately from your workout plan</p></div>', unsafe_allow_html=True)
    if log.empty:
        st.info("No workout history yet.")
    else:
        st.dataframe(log.sort_values(["date", "saved_at", "exercise", "set_number"], ascending=[False, False, True, True]), use_container_width=True, hide_index=True)
        st.download_button("Download workout_log.csv", log.to_csv(index=False).encode("utf-8"), "workout_log.csv", "text/csv")

elif page == "Data Safety":
    st.markdown('<div class="hero"><h1>Data Safety</h1><p>Protect workout history before every update</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("File Status")
    st.write(f"✅ Workout plan: `{WORKOUTS_FILE}`")
    st.write(f"✅ Workout history: `{LOG_FILE}`")
    st.write(f"✅ Backups folder: `{BACKUP_DIR}`")
    st.write(f"Saved workout rows: **{len(log)}**")
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    if c1.button("Create Backup Now"):
        path = backup_data()
        st.success(f"Backup created: {path.name}")
    c2.download_button("Export All Data ZIP", make_export_zip(), "brian_fitness_tracker_data_backup.zip", "application/zip")

    uploaded = st.file_uploader("Import workout_log.csv backup", type=["csv"])
    if uploaded is not None:
        imported = pd.read_csv(uploaded)
        imported = normalize_cols(imported)
        for col in REQUIRED_LOG_COLS:
            if col not in imported.columns:
                imported[col] = None
        if st.button("Import and Replace workout_log.csv"):
            backup_data()
            save_csv(imported[REQUIRED_LOG_COLS], LOG_FILE)
            st.success("Imported workout_log.csv. A backup of the previous file was created first.")

elif page == "Profile":
    st.markdown('<div class="hero"><h1>Profile</h1><p>Basic monthly scoreboard settings</p></div>', unsafe_allow_html=True)
    profile["current_weight"] = st.number_input("Current Weight", min_value=0.0, value=float(profile.get("current_weight", 0.0)), step=0.5)
    profile["goal_weight"] = st.number_input("Goal Weight", min_value=0.0, value=float(profile.get("goal_weight", 0.0)), step=0.5)
    profile["week"] = st.number_input("Week #", min_value=1, max_value=52, value=int(profile.get("week", 1)))
    if st.button("Save Profile"):
        save_profile(profile)
        st.success("Profile saved.")

elif page == "Phone Setup":
    st.markdown('<div class="hero"><h1>Phone Setup</h1><p>Use Streamlit Cloud for gym use outside your home Wi-Fi</p></div>', unsafe_allow_html=True)
    ip = get_lan_ip()
    st.write("Local Wi-Fi link:")
    st.code(f"http://{ip}:8501")
    st.write("For LA Fitness use, deploy this same GitHub repository on Streamlit Cloud and open the Streamlit URL on your phone.")
