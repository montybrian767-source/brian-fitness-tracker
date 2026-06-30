from __future__ import annotations
import json, socket
from datetime import date, datetime
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None

APP_DIR = Path(__file__).parent
WORKOUTS_FILE = APP_DIR / "workouts.csv"
LOG_FILE = APP_DIR / "workout_log.csv"
PROFILE_FILE = APP_DIR / "profile.json"
DAY_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
DO_NOT_DO = ["Leg Press", "Squats", "Lunges", "Running", "Stair Climber", "Smith Machine Squats", "Heavy Lower Body Loading"]

st.set_page_config(page_title="Brian Fitness Tracker Cloud v11", page_icon="🏋️", layout="wide", initial_sidebar_state="expanded")

st.markdown('''
<style>
:root{--navy:#061A33;--navy2:#0B2A4A;--blue:#2563EB;--sky:#EAF3FF;--green:#16A34A;--gold:#F59E0B;--red:#DC2626;--bg:#F4F7FB;--card:#FFFFFF;--text:#132033;--muted:#64748B;--line:#E2E8F0;}
[data-testid="stAppViewContainer"]{background:var(--bg);color:var(--text);} .block-container{padding-top:1rem;max-width:1350px;}
h1,h2,h3{color:var(--text)!important;font-weight:900!important}.subtle{color:var(--muted);font-weight:600}.hero{background:linear-gradient(135deg,#061A33,#0B3A6F);color:white;border-radius:24px;padding:24px 28px;margin-bottom:18px;box-shadow:0 12px 30px rgba(6,26,51,.18)}.hero h1{color:white!important;margin:0;font-size:2.1rem!important}.hero p{color:#BFD7FF;margin:.4rem 0 0 0}.top-card{background:white;border:1px solid var(--line);border-radius:18px;padding:16px;box-shadow:0 5px 18px rgba(15,23,42,.05)}.metric-label{font-size:.78rem;text-transform:uppercase;color:var(--muted);font-weight:900;letter-spacing:.05em}.metric-value{font-size:1.65rem;color:var(--navy);font-weight:950}.schedule-card{background:white;border:1px solid var(--line);border-radius:16px;padding:14px;margin:9px 0;box-shadow:0 4px 14px rgba(15,23,42,.04)}.schedule-active{border:2px solid var(--blue);background:#F8FBFF}.day-pill{display:inline-block;background:var(--navy);color:white;border-radius:10px;padding:6px 10px;font-weight:950;font-size:.78rem;margin-right:8px}.group-pill{display:inline-block;background:#DCFCE7;color:#166534;border:1px solid #BBF7D0;border-radius:999px;padding:5px 10px;font-weight:900;font-size:.8rem}.work-card{background:white;border:1px solid var(--line);border-radius:24px;padding:0;overflow:hidden;box-shadow:0 14px 35px rgba(15,23,42,.08);margin-bottom:16px}.work-head{background:linear-gradient(135deg,#061A33,#0B3A6F);color:white;padding:22px 26px}.work-head h2{color:white!important;margin:0}.badge{display:inline-block;background:#EAF3FF;color:#0757C2;border:1px solid #BFDBFE;border-radius:999px;padding:6px 12px;font-weight:900;margin-right:8px}.set-table{padding:20px 24px}.set-row{display:grid;grid-template-columns:.5fr 1.2fr 1.2fr 1.2fr 1fr;gap:12px;align-items:center;border-bottom:1px solid var(--line);padding:12px 0}.set-num{background:var(--blue);color:white;width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:950}.volume-box{background:#ECFDF5;border:1px solid #BBF7D0;color:#166534;border-radius:14px;padding:10px;text-align:center;font-weight:950}.volume-box b{font-size:1.25rem}.stButton>button{border-radius:14px;min-height:3rem;font-weight:900;border:1px solid var(--line)}.primary-btn button{background:var(--blue)!important;color:white!important}.save-btn button{background:var(--green)!important;color:white!important;border:none!important}.stNumberInput input{font-size:1.05rem!important;font-weight:900!important;text-align:center!important;color:#0F172A!important;background:#F8FAFC!important}.stTextInput input,.stTextArea textarea{background:#F8FAFC!important;color:#0F172A!important}.warn{background:#FFF7ED;border:1px solid #FED7AA;color:#9A3412;border-radius:16px;padding:14px;font-weight:850}.safe{background:#ECFDF5;border:1px solid #BBF7D0;color:#166534;border-radius:16px;padding:14px;font-weight:850}.info{background:#EAF3FF;border:1px solid #BFDBFE;color:#0757C2;border-radius:16px;padding:14px;font-weight:850}.progress-wrap{background:#E5E7EB;border-radius:99px;height:14px;overflow:hidden}.progress-fill{background:linear-gradient(90deg,#2563EB,#16A34A);height:14px}.sidebar-brand{background:linear-gradient(135deg,#061A33,#0B3A6F);color:white;border-radius:20px;padding:18px;margin-bottom:14px;text-align:center}.sidebar-brand h2{color:white!important;margin:0}.sidebar-brand small{color:#BFD7FF}.nav-note{background:#F8FAFC;border:1px solid var(--line);border-radius:14px;padding:12px;color:var(--muted);font-size:.9rem}.upnext{background:#F8FAFC;border:1px solid var(--line);border-radius:14px;padding:12px;margin:6px 0}.dataframe{font-size:.9rem}@media(max-width:850px){.set-row{grid-template-columns:1fr;gap:6px}.hero h1{font-size:1.55rem!important}.work-head{padding:18px}.set-table{padding:16px}.block-container{padding-left:.7rem;padding-right:.7rem}}
</style>
''', unsafe_allow_html=True)

def get_ip():
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(("8.8.8.8",80)); ip=s.getsockname()[0]; s.close(); return ip
    except Exception: return "YOUR-COMPUTER-IP"

LOG_COLS=["date","saved_at","week","day","workout","muscle_group","exercise","set_number","weight_lbs","reps","pain","rpe","notes","volume"]
PROFILE_DEFAULT={"current_weight":0.0,"goal_weight":0.0,"week":1,"swims":0,"bike_miles":0.0,"protein_days":0,"streak":0}

def load_workouts(): return pd.read_csv(WORKOUTS_FILE)

def cloud_enabled():
    return (gspread is not None and Credentials is not None and "gcp_service_account" in st.secrets and "google_sheets" in st.secrets)

@st.cache_resource(show_spinner=False)
def get_sheet_client():
    scopes=["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    creds=Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
    gc=gspread.authorize(creds)
    sheet_name=st.secrets["google_sheets"].get("sheet_name","Brian Fitness Tracker Cloud")
    return gc.open(sheet_name)

def get_or_create_tab(book, title, headers):
    try:
        ws=book.worksheet(title)
    except Exception:
        ws=book.add_worksheet(title=title, rows=1000, cols=max(20,len(headers)))
    existing=ws.row_values(1)
    if existing != headers:
        ws.clear()
        ws.append_row(headers)
    return ws

def load_log():
    if cloud_enabled():
        try:
            book=get_sheet_client()
            tab=st.secrets["google_sheets"].get("log_tab","workout_log")
            ws=get_or_create_tab(book, tab, LOG_COLS)
            records=ws.get_all_records()
            return pd.DataFrame(records, columns=LOG_COLS) if records else pd.DataFrame(columns=LOG_COLS)
        except Exception as e:
            st.warning(f"Cloud sync not available, using local storage. Reason: {e}")
    return pd.read_csv(LOG_FILE) if LOG_FILE.exists() else pd.DataFrame(columns=LOG_COLS)

def save_log(df):
    df=df.copy()
    for c in LOG_COLS:
        if c not in df.columns: df[c]=""
    df=df[LOG_COLS]
    if cloud_enabled():
        try:
            book=get_sheet_client()
            tab=st.secrets["google_sheets"].get("log_tab","workout_log")
            ws=get_or_create_tab(book, tab, LOG_COLS)
            values=[LOG_COLS]+df.astype(str).values.tolist()
            ws.clear(); ws.update(values)
            return
        except Exception as e:
            st.warning(f"Could not save to cloud, saved locally instead. Reason: {e}")
    df.to_csv(LOG_FILE,index=False)

def load_profile():
    d=PROFILE_DEFAULT.copy()
    if cloud_enabled():
        try:
            book=get_sheet_client()
            tab=st.secrets["google_sheets"].get("profile_tab","profile")
            ws=get_or_create_tab(book, tab, ["key","value"])
            for r in ws.get_all_records():
                k=str(r.get("key","")); v=r.get("value","")
                if k in d:
                    try:
                        d[k]=float(v) if k in ["current_weight","goal_weight","bike_miles"] else int(float(v))
                    except Exception:
                        d[k]=v
            return d
        except Exception:
            pass
    if PROFILE_FILE.exists():
        try: d.update(json.loads(PROFILE_FILE.read_text()))
        except Exception: pass
    return d

def save_profile(p):
    if cloud_enabled():
        try:
            book=get_sheet_client()
            tab=st.secrets["google_sheets"].get("profile_tab","profile")
            ws=get_or_create_tab(book, tab, ["key","value"])
            values=[["key","value"]]+[[k,str(v)] for k,v in p.items()]
            ws.clear(); ws.update(values)
            return
        except Exception as e:
            st.warning(f"Could not save profile to cloud, saved locally instead. Reason: {e}")
    PROFILE_FILE.write_text(json.dumps(p,indent=2))
def today_name(): return date.today().strftime("%A")
def best_weight(log, ex): return 0.0 if log.empty or log[log.exercise==ex].empty else float(log[log.exercise==ex].weight_lbs.max())
def last_vals(log, ex, setn, fallback):
    if log.empty: return fallback, 0
    d=log[(log.exercise==ex)&(log.set_number==setn)].copy()
    if d.empty: return fallback, 0
    d["date"]=pd.to_datetime(d["date"],errors="coerce"); d=d.sort_values(["date","saved_at"])
    r=d.iloc[-1]; return float(r.weight_lbs), int(r.reps)

workouts=load_workouts(); log=load_log(); profile=load_profile()

with st.sidebar:
    st.markdown('<div class="sidebar-brand"><h2>BRIAN</h2><small>FITNESS TRACKER CLOUD v11</small></div>', unsafe_allow_html=True)
    page=st.radio("Navigation",["Dashboard","Workout","Weekly Plan","Progress","History","Knee Safety","Profile","Cloud Setup"],label_visibility="collapsed")
    st.markdown('<div class="nav-note"><b>Knee Friendly</b><br>All exercises are selected with your right knee in mind. No ego lifting.</div>', unsafe_allow_html=True)
    mode = "☁️ Cloud Sync: Google Sheets" if cloud_enabled() else "💻 Local Storage Mode"
    st.markdown(f'<div class="nav-note"><b>{mode}</b><br>{"Works anywhere after Streamlit Cloud deploy." if cloud_enabled() else "Deploy online and add Google Sheets secrets for gym use from any network."}</div>', unsafe_allow_html=True)

sessions = log["date"].nunique() if not log.empty else 0
total_volume = float(log["volume"].sum()) if not log.empty else 0
prs = int(log.groupby("exercise")["weight_lbs"].max().count()) if not log.empty else 0
avg_pain = float(log["pain"].mean()) if not log.empty else 0

st.markdown('<div class="hero"><h1>🏋️ Brian Fitness Tracker Cloud v11</h1><p>Cloud-ready workout platform — weekly plan, one-exercise tracker, progress analytics, and knee-safe training.</p></div>', unsafe_allow_html=True)

c1,c2,c3,c4=st.columns(4)
for col,label,val in [(c1,"Day Streak",profile.get('streak',0)),(c2,"Total Workouts",sessions),(c3,"Total Volume",f"{total_volume:,.0f}"),(c4,"PR Exercises",prs)]:
    col.markdown(f'<div class="top-card"><div class="metric-label">{label}</div><div class="metric-value">{val}</div></div>', unsafe_allow_html=True)

if page=="Dashboard":
    st.subheader("This Week's Plan")
    today=today_name()
    cols=st.columns(2)
    for idx,day in enumerate(DAY_ORDER):
        d=workouts[workouts.day==day]
        group=d.muscle_group.iloc[0] if not d.empty else ""
        status="TODAY" if day==today else "PLAN"
        html=f'<div class="schedule-card {"schedule-active" if day==today else ""}"><span class="day-pill">{day[:3].upper()}</span><b>{group}</b><br><span class="subtle">{len(d)} exercises • {status}</span></div>'
        cols[idx%2].markdown(html, unsafe_allow_html=True)
    st.subheader("Today’s Focus")
    d=workouts[workouts.day==today]
    if not d.empty:
        st.markdown(f'<div class="top-card"><h3>{today} — {d.workout.iloc[0]}</h3><span class="group-pill">{d.muscle_group.iloc[0]}</span><p class="subtle">{len(d)} planned exercises. Open the Workout page to start tracking.</p></div>', unsafe_allow_html=True)

elif page=="Weekly Plan":
    st.subheader("Weekly Schedule by Muscle Group")
    for day in DAY_ORDER:
        d=workouts[workouts.day==day]
        st.markdown(f'<div class="schedule-card"><span class="day-pill">{day[:3].upper()}</span><b>{d.workout.iloc[0]}</b> <span class="group-pill">{d.muscle_group.iloc[0]}</span><br><span class="subtle">{", ".join(d.exercise.tolist()[:5])}{"..." if len(d)>5 else ""}</span></div>', unsafe_allow_html=True)

elif page=="Workout":
    st.subheader("Workout Tracker")
    day=st.selectbox("Workout day",DAY_ORDER,index=DAY_ORDER.index(today_name()) if today_name() in DAY_ORDER else 0)
    day_df=workouts[workouts.day==day].reset_index(drop=True)
    wname=day_df.workout.iloc[0] if not day_df.empty else ""
    group=day_df.muscle_group.iloc[0] if not day_df.empty else ""
    if day=="Thursday": st.markdown('<div class="warn">🦵 Leg Rehab Day: no downward loading. Stop anything that causes knee pain.</div>', unsafe_allow_html=True)
    if day=="Sunday": st.markdown('<div class="safe">Recovery day: swimming, bike, sauna, mobility, and recovery.</div>', unsafe_allow_html=True)
    dcol,wcol=st.columns(2); workout_date=dcol.date_input("Date",value=date.today()); week=int(wcol.number_input("Week",1,52,int(profile.get("week",1))))
    st.markdown('<div class="info">Use the plus/minus controls or tap the boxes. Save after finishing the exercise or the full workout.</div>', unsafe_allow_html=True)
    ex_names=day_df.exercise.tolist()
    ex_index=st.selectbox("Choose exercise", list(range(len(ex_names))), format_func=lambda i: f"{i+1}. {ex_names[i]}" if ex_names else "No exercise") if ex_names else 0
    row=day_df.iloc[int(ex_index)]
    exercise=str(row.exercise); target_sets=int(row.target_sets); target_reps=str(row.target_reps); default=float(row.starting_weight_lbs or 0); pb=best_weight(log,exercise)
    st.markdown(f'<div class="work-card"><div class="work-head"><h2>{exercise}</h2><span class="badge">Target: {target_sets} sets × {target_reps}</span><span class="badge">{group}</span><p style="color:#CFE2FF;margin-top:12px">{row.notes if isinstance(row.notes,str) else ""}</p></div><div class="set-table">', unsafe_allow_html=True)
    a,b,c,d=st.columns(4)
    a.metric("Target Sets", target_sets); b.metric("Pain 0-10", "Track below"); c.metric("Last Weight", f"{default:g} lbs"); d.metric("Personal Best", f"{pb:g} lbs")
    sets=int(st.number_input("Sets today",1,8,target_sets)); pain=int(st.number_input("Pain 0-10",0,10,0)); notes=st.text_area("Exercise notes",placeholder="Example: felt good, knee okay, too heavy")
    rows=[]; total_ex_vol=0
    st.markdown("#### Set Tracker")
    for s in range(1,sets+1):
        last_w,last_r=last_vals(log,exercise,s,default)
        cols=st.columns([.55,1.4,1.4,1.4,1])
        cols[0].markdown(f'<div class="set-num">{s}</div>', unsafe_allow_html=True)
        weight=cols[1].number_input(f"Set {s} Weight",0.0,value=float(last_w),step=2.5,key=f"w{day}{ex_index}{s}")
        reps=cols[2].number_input(f"Set {s} Reps",0,value=int(last_r),step=1,key=f"r{day}{ex_index}{s}")
        rpe=cols[3].number_input(f"Set {s} RPE",0,10,0,key=f"p{day}{ex_index}{s}")
        vol=weight*reps; total_ex_vol += vol
        cols[4].markdown(f'<div class="volume-box">VOLUME<br><b>{vol:,.0f}</b> lbs</div>', unsafe_allow_html=True)
        if reps>0:
            rows.append({"date":str(workout_date),"saved_at":datetime.now().isoformat(timespec="seconds"),"week":week,"day":day,"workout":wname,"muscle_group":group,"exercise":exercise,"set_number":s,"weight_lbs":weight,"reps":reps,"pain":pain,"rpe":rpe,"notes":notes,"volume":vol})
    st.markdown(f'<div class="top-card"><div class="metric-label">Exercise Total Volume</div><div class="metric-value">{total_ex_vol:,.0f} lbs</div></div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)
    s1,s2,s3=st.columns([1,1,1])
    with s1:
        st.markdown('<div class="save-btn">', unsafe_allow_html=True)
        if st.button("✅ Save Exercise"):
            if rows:
                save_log(pd.concat([load_log(),pd.DataFrame(rows)],ignore_index=True)); st.success(f"Saved {exercise}."); st.rerun()
            else: st.warning("Enter reps first.")
        st.markdown('</div>', unsafe_allow_html=True)
    with s2:
        if st.button("➡️ Next Exercise") and int(ex_index)+1 < len(ex_names): st.session_state["next_hint"] = int(ex_index)+1; st.info("Choose the next exercise from the dropdown above.")
    st.subheader("Up Next")
    for j in range(int(ex_index)+1,min(len(day_df),int(ex_index)+4)):
        r=day_df.iloc[j]; st.markdown(f'<div class="upnext"><b>{j+1}. {r.exercise}</b> <span class="subtle">{r.target_sets} × {r.target_reps}</span></div>', unsafe_allow_html=True)

elif page=="Progress":
    st.subheader("Progress Analytics")
    if log.empty: st.info("No workouts saved yet.")
    else:
        daily=log.groupby("date",as_index=False)["volume"].sum(); st.plotly_chart(px.line(daily,x="date",y="volume",title="Daily Training Volume"),use_container_width=True)
        best=log.groupby(["muscle_group","exercise"],as_index=False).agg(best_weight=("weight_lbs","max"),total_volume=("volume","sum"),avg_pain=("pain","mean")).sort_values("total_volume",ascending=False)
        st.dataframe(best,use_container_width=True)

elif page=="History":
    st.subheader("Workout History")
    if log.empty: st.info("No history yet.")
    else:
        st.dataframe(log.sort_values(["date","exercise","set_number"],ascending=[False,True,True]),use_container_width=True)
        st.download_button("Download workout_log.csv", log.to_csv(index=False).encode(), "workout_log.csv")

elif page=="Knee Safety":
    st.subheader("Knee Safety Rules")
    st.markdown('<div class="safe">✅ Protect right knee. ✅ Increase weight slowly. ✅ Stop if pain. ✅ Leave every workout feeling like you could do more.</div>', unsafe_allow_html=True)
    for item in DO_NOT_DO: st.error(f"❌ {item}")

elif page=="Profile":
    st.subheader("Profile / Monthly Scoreboard")
    profile["current_weight"]=st.number_input("Current Weight",0.0,value=float(profile.get("current_weight",0.0)),step=.5)
    profile["goal_weight"]=st.number_input("Goal Weight",0.0,value=float(profile.get("goal_weight",0.0)),step=.5)
    profile["week"]=st.number_input("Week #",1,52,value=int(profile.get("week",1)))
    profile["streak"]=st.number_input("Day Streak",0,value=int(profile.get("streak",0)))
    profile["swims"]=st.number_input("Swims Completed",0,value=int(profile.get("swims",0)))
    profile["bike_miles"]=st.number_input("Bike Miles",0.0,value=float(profile.get("bike_miles",0.0)),step=.5)
    profile["protein_days"]=st.number_input("Protein Goal Days",0,31,value=int(profile.get("protein_days",0)))
    if st.button("Save Profile"):
        save_profile(profile); st.success("Profile saved.")

elif page=="Cloud Setup":
    st.subheader("Cloud Setup for Gym Use")
    st.markdown("""
    This build can run online so you can open it from your phone at LA Fitness even when you are not on your home Wi‑Fi.

    **Fast path:** deploy this folder to Streamlit Community Cloud.

    **Saving data:** add Google Sheets secrets so your workout history saves permanently online.
    """)
    st.markdown(f'<div class="top-card"><div class="metric-label">Current Storage Mode</div><div class="metric-value">{"Cloud Sync" if cloud_enabled() else "Local CSV"}</div></div>', unsafe_allow_html=True)
    st.code("python -m streamlit run app.py")
    st.info("For Streamlit Cloud: upload app.py, workouts.csv, requirements.txt, then set main file to app.py. Add Google Sheets secrets when ready.")

with st.expander("📱 Phone Link"):
    st.write("Use this on your phone while your computer and phone are on the same Wi‑Fi:")
    st.code(f"http://{get_ip()}:8501")
