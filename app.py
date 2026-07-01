from __future__ import annotations
import base64, socket
from datetime import date, datetime
from pathlib import Path
import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
ASSET_DIR = APP_DIR / "assets"
EXERCISE_IMG_DIR = ASSET_DIR / "exercises"
WORKOUTS_FILE = DATA_DIR / "workouts.csv"
LOG_FILE = DATA_DIR / "workout_log.csv"
IMAGE_MAP_FILE = DATA_DIR / "exercise_image_map.csv"
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

st.set_page_config(page_title="Brian Fitness Tracker 2.0", page_icon="🏋️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
:root{--muted:#9fb3cc;--blue:#1d6fff;--green:#4ade80;}
[data-testid="stAppViewContainer"]{background:linear-gradient(120deg,#07111f 0%,#0a1627 55%,#0d1b2f 100%);color:#f4f8ff;}
.block-container{padding:1.2rem 1.5rem 6rem 1.5rem;max-width:1450px;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#061225,#08203b)!important;border-right:1px solid #1d3557;}
[data-testid="stSidebar"] *{color:#f8fbff!important;}
h1{font-size:2.15rem!important;font-weight:950!important;letter-spacing:-.03em;color:#f8fbff!important;} h2,h3{font-weight:900!important;color:#f8fbff!important;}
.stButton>button{border-radius:12px!important;border:1px solid #294666!important;background:#101f36!important;color:#f8fbff!important;font-weight:850!important;min-height:42px;}
.stNumberInput input,.stTextInput input,.stDateInput input,.stSelectbox div[data-baseweb="select"]{background:#0b1728!important;color:#f8fbff!important;border:1px solid #263a58!important;border-radius:10px!important;}
[data-testid="stMetric"]{background:linear-gradient(180deg,#111f34,#0c1829);border:1px solid #283c5a;border-radius:16px;padding:14px 16px;box-shadow:0 10px 30px rgba(0,0,0,.22);}
[data-testid="stMetricLabel"]{color:#9fb3cc!important;font-weight:850!important;} [data-testid="stMetricValue"]{color:#f8fbff!important;font-weight:950!important;}
.nav-title{font-size:1.8rem;font-weight:950;line-height:1.0;margin:14px 0 2px 0;color:#fff}.nav-sub{font-weight:900;color:#57f26d!important;letter-spacing:.05em;margin-bottom:20px}.version-pill{display:inline-block;padding:8px 12px;border:1px solid #2454a6;border-radius:999px;background:#0b2a54;color:#74b6ff;font-weight:900;font-size:.9rem;margin-bottom:22px}.side-card{background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.12);border-radius:16px;padding:16px;margin-top:18px}.safe-dot{display:inline-flex;width:32px;height:32px;align-items:center;justify-content:center;border-radius:999px;background:#22c55e;color:white;font-weight:900;margin-right:10px}.muted{color:#9fb3cc}.hero-card{background:linear-gradient(180deg,#0f1d31,#0b1626);border:1px solid #263a58;border-radius:18px;padding:18px;box-shadow:0 15px 45px rgba(0,0,0,.22);margin-bottom:14px}.pill{display:inline-block;padding:7px 11px;border-radius:999px;border:1px solid #274766;background:#0b2545;color:#8fc4ff;font-weight:900;font-size:.8rem;margin-right:6px}.pill.green{background:#0b3820;border-color:#1e8a45;color:#7af49b}.exercise-card{background:linear-gradient(180deg,#101e33,#0b1626);border:1px solid #283c5a;border-radius:18px;margin-bottom:18px;overflow:hidden;box-shadow:0 18px 50px rgba(0,0,0,.24)}.exercise-body{display:grid;grid-template-columns:270px minmax(0,1fr);gap:18px;padding:16px}@media(max-width:850px){.exercise-body{grid-template-columns:1fr}.ex-img{height:220px!important}}.ex-img{width:100%;height:230px;object-fit:cover;border-radius:14px;border:1px solid #31435e;background:#0b1728}.ex-title{font-size:1.35rem;font-weight:950;color:#fff;margin-bottom:6px}.ex-top{display:flex;justify-content:space-between;align-items:start;gap:12px}.how-btn{border:1px solid #2c65c7;color:#9cc8ff;background:#0b2545;padding:10px 13px;border-radius:10px;font-weight:900;white-space:nowrap}.set-head{color:#9fb3cc;font-size:.78rem;font-weight:900;text-transform:uppercase;border-bottom:1px solid rgba(255,255,255,.1);padding-bottom:6px}.set-num{display:inline-flex;width:26px;height:26px;align-items:center;justify-content:center;border-radius:999px;background:#1d6fff;color:white;font-weight:900}.vol{font-weight:950;color:#4ade80}.summary-card{background:linear-gradient(180deg,#111f34,#0b1626);border:1px solid #283c5a;border-radius:18px;padding:18px;margin-bottom:16px;box-shadow:0 18px 50px rgba(0,0,0,.22)}.summary-title{font-weight:950;color:#fff;font-size:1.1rem;margin-bottom:12px}.summary-row{display:flex;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.08);padding:8px 0;color:#dbe8fb}.green-text{color:#4ade80!important;font-weight:950}.bottom-bar{position:fixed;left:0;right:0;bottom:0;z-index:999;background:linear-gradient(90deg,#061225,#0b1728);border-top:1px solid #263a58;padding:12px 20px;display:flex;gap:18px;align-items:center;justify-content:center;color:#fff;box-shadow:0 -10px 40px rgba(0,0,0,.35)}.progress-line{height:8px;background:#243855;border-radius:999px;overflow:hidden;min-width:260px;max-width:520px;flex:1}.progress-fill{height:100%;background:linear-gradient(90deg,#1d6fff,#4ade80);border-radius:999px}.catalog-card{background:#101e33;border:1px solid #283c5a;border-radius:16px;padding:12px;margin-bottom:16px}
</style>
""", unsafe_allow_html=True)

def normalize(s:str)->str:
    return ''.join(ch.lower() for ch in str(s) if ch.isalnum())

@st.cache_data
def load_workouts():
    df=pd.read_csv(WORKOUTS_FILE)
    df.columns=[c.strip() for c in df.columns]
    return df

@st.cache_data
def load_img_map():
    if IMAGE_MAP_FILE.exists():
        m=pd.read_csv(IMAGE_MAP_FILE)
        e_col='exercise_name' if 'exercise_name' in m.columns else m.columns[0]
        i_col='image_file' if 'image_file' in m.columns else m.columns[1]
        return {normalize(r[e_col]):str(r[i_col]) for _,r in m.iterrows()}
    return {}

def load_log():
    if LOG_FILE.exists(): return pd.read_csv(LOG_FILE)
    return pd.DataFrame(columns=['date','saved_at','day','workout','exercise','set_number','weight_lbs','reps','rpe','pain','notes','volume'])

def save_log(df):
    DATA_DIR.mkdir(exist_ok=True); df.to_csv(LOG_FILE,index=False)

def find_img(exercise):
    fname=load_img_map().get(normalize(exercise))
    if fname:
        p=EXERCISE_IMG_DIR/fname
        if p.exists(): return p
    for p in EXERCISE_IMG_DIR.glob('*'):
        if normalize(p.stem)==normalize(exercise): return p
    return None

def image_html(path:Path|None,title:str):
    if path and path.exists():
        b64=base64.b64encode(path.read_bytes()).decode()
        ext=path.suffix.lower().replace('.','') or 'png'
        mime='svg+xml' if ext=='svg' else ext
        return f'<img class="ex-img" src="data:image/{mime};base64,{b64}" />'
    safe=title.replace('<','').replace('>','')
    return f'<div class="ex-img" style="display:flex;align-items:center;justify-content:center;text-align:center;background:linear-gradient(135deg,#142842,#0b1728);"><div><div style="font-size:42px">🏋️</div><div style="font-weight:950;color:white">{safe}</div><div class="muted">image coming soon</div></div></div>'

def last_best(log, exercise):
    if log.empty or 'exercise' not in log.columns: return 0
    ex=log[log.exercise.astype(str)==exercise]
    if ex.empty: return 0
    return float(pd.to_numeric(ex.get('weight_lbs',0),errors='coerce').fillna(0).max())

workouts=load_workouts(); log=load_log()
with st.sidebar:
    st.markdown('<div class="nav-title">🏋️ BRIAN</div><div class="nav-sub">FITNESS TRACKER 2.0</div><div class="version-pill">Alpha Commercial</div>', unsafe_allow_html=True)
    page=st.radio('Navigation',['Dashboard','Today’s Workout','Gym Mode','Weekly Plan','Progress','History','Exercise Library','Image Test','Data & Export'], label_visibility='collapsed')
    st.markdown('<div class="side-card"><div><span class="safe-dot">✓</span><b>All data is safe</b></div><div class="muted" style="margin-top:8px">workout_log.csv</div></div>', unsafe_allow_html=True)
    if LOG_FILE.exists(): st.download_button('☁️ Export Backup', LOG_FILE.read_bytes(), 'workout_log_backup.csv','text/csv',use_container_width=True)

if page=='Dashboard':
    st.title('Dashboard')
    vol=pd.to_numeric(log.get('volume',0),errors='coerce').fillna(0).sum() if not log.empty else 0
    c1,c2,c3,c4=st.columns(4); c1.metric('Sessions', log['date'].nunique() if not log.empty and 'date' in log else 0); c2.metric('Total Volume',f'{vol:,.0f} lbs'); c3.metric('Build','2.0 Alpha'); c4.metric('Status','Ready')
    st.markdown('### Weekly Plan')
    cols=st.columns(7)
    for i,d in enumerate(DAY_ORDER):
        dd=workouts[workouts.day==d]; name=dd.workout.iloc[0] if not dd.empty else 'Recovery'
        cols[i].markdown(f'<div class="summary-card"><b>{d[:3].upper()}</b><br><span class="muted">{name}</span><br><span class="pill green">{len(dd)} exercises</span></div>',unsafe_allow_html=True)

elif page in ['Today’s Workout','Gym Mode']:
    st.title('Today’s Workout')
    top=st.columns([2,1,1,1])
    today=date.today().strftime('%A'); idx=DAY_ORDER.index(today) if today in DAY_ORDER else 0
    day=top[0].selectbox('Workout Day',DAY_ORDER,idx); workout_date=top[1].date_input('Date',date.today()); week=top[2].number_input('Week',min_value=1,value=1); rest=top[3].selectbox('Rest Timer',[45,60,75,90,120],index=1)
    active=workouts[workouts.day.astype(str).str.lower()==day.lower()].reset_index(drop=True); workout_name=active.workout.iloc[0] if not active.empty else 'Recovery'
    st.markdown(f'<div class="hero-card"><h2>{day} — {workout_name}</h2><span class="pill">{workout_name}</span><span class="pill green">{len(active)} exercises</span></div>',unsafe_allow_html=True)
    left,right=st.columns([3.15,1]); rows=[]; total_volume=0; completed=0
    with left:
        for i,row in active.iterrows():
            exercise=str(row.exercise); sets=int(row.target_sets); reps_target=str(row.target_reps); start_w=float(row.starting_weight_lbs) if pd.notna(row.starting_weight_lbs) else 0; best=last_best(log,exercise); img=find_img(exercise)
            st.markdown('<div class="exercise-card"><div class="exercise-body">',unsafe_allow_html=True); st.markdown(image_html(img,exercise),unsafe_allow_html=True)
            st.markdown(f'<div><div class="ex-top"><div><div class="ex-title">{i+1}. {exercise}</div><span class="pill">Target: {sets} x {reps_target}</span><span class="pill green">{workout_name}</span><p class="muted">Previous Best: {best:g} lbs</p></div><div class="how-btn">▷ HOW TO</div></div>',unsafe_allow_html=True)
            st.markdown('<div class="set-head">SET · WEIGHT · REPS · RPE · NOTES · VOLUME</div>',unsafe_allow_html=True)
            ex_started=False
            for s in range(1,sets+1):
                cols=st.columns([.45,1,.75,.75,1.1,.8])
                cols[0].markdown(f'<span class="set-num">{s}</span>',unsafe_allow_html=True)
                w=cols[1].number_input('weight',min_value=0.0,value=start_w if start_w>0 else best,step=5.0,key=f'w_{day}_{i}_{s}',label_visibility='collapsed')
                try: default_reps=int(str(reps_target).split('-')[0])
                except: default_reps=0
                r=cols[2].number_input('reps',min_value=0,value=default_reps,step=1,key=f'r_{day}_{i}_{s}',label_visibility='collapsed')
                rpe=cols[3].number_input('rpe',min_value=0.0,max_value=10.0,value=7.0,step=.5,key=f'rpe_{day}_{i}_{s}',label_visibility='collapsed')
                note=cols[4].text_input('note',value='felt good' if s==1 else '',key=f'n_{day}_{i}_{s}',label_visibility='collapsed')
                v=w*r; cols[5].markdown(f'<div class="vol">{v:,.0f} lbs</div>',unsafe_allow_html=True)
                if r>0:
                    ex_started=True; total_volume+=v; rows.append({'date':str(workout_date),'saved_at':datetime.now().isoformat(timespec='seconds'),'day':day,'workout':workout_name,'exercise':exercise,'set_number':s,'weight_lbs':w,'reps':r,'rpe':rpe,'pain':0,'notes':note,'volume':v})
            if ex_started: completed+=1
            st.markdown('</div></div></div>',unsafe_allow_html=True)
        if st.button('✅ Finish & Save Workout', type='primary', use_container_width=True):
            if rows:
                save_log(pd.concat([load_log(),pd.DataFrame(rows)],ignore_index=True)); st.success(f'Saved {len(rows)} sets to data/workout_log.csv'); st.balloons()
            else: st.warning('Enter reps before saving.')
    with right:
        st.markdown(f'<div class="summary-card"><div class="summary-title">📋 Workout Summary</div><div class="summary-row"><span>Exercises</span><b>{len(active)}</b></div><div class="summary-row"><span>Total Volume</span><b class="green-text">{total_volume:,.0f} lbs</b></div><div class="summary-row"><span>Rest Timer</span><b>{rest}s</b></div></div>',unsafe_allow_html=True)
        st.markdown(f'<div class="summary-card"><div class="summary-title">💪 Muscle Focus</div><h3>{workout_name}</h3><p class="muted">Protect the knee. Controlled form first.</p></div>',unsafe_allow_html=True)
    pct=int((completed/max(len(active),1))*100)
    st.markdown(f'<div class="bottom-bar"><b>⏱ Rest Timer {rest}s</b><span class="muted">Commercial Gym Mode</span><div class="progress-line"><div class="progress-fill" style="width:{pct}%"></div></div><b>{completed}/{len(active)} exercises</b></div>',unsafe_allow_html=True)

elif page=='Weekly Plan':
    st.title('Weekly Plan')
    for d in DAY_ORDER:
        dd=workouts[workouts.day==d]; name=dd.workout.iloc[0] if not dd.empty else 'Recovery'; st.markdown(f'<div class="summary-card"><h3>{d} — {name}</h3><span class="pill green">{len(dd)} exercises</span></div>',unsafe_allow_html=True)
elif page=='Exercise Library':
    st.title('Exercise Library')
    q=st.text_input('Search exercises')
    ex=workouts[['exercise','workout','day','target_sets','target_reps']].drop_duplicates()
    if q: ex=ex[ex.exercise.str.contains(q,case=False,na=False)]
    cols=st.columns(3)
    for i,(_,r) in enumerate(ex.iterrows()):
        with cols[i%3]:
            st.markdown('<div class="catalog-card">',unsafe_allow_html=True)
            img=find_img(r.exercise)
            if img: st.image(str(img),use_container_width=True)
            else: st.markdown(image_html(None,r.exercise),unsafe_allow_html=True)
            st.markdown(f'<b>{r.exercise}</b><br><span class="muted">{r.workout}</span><br><span class="pill">{r.day} · {r.target_sets} x {r.target_reps}</span>',unsafe_allow_html=True)
            st.markdown('</div>',unsafe_allow_html=True)
elif page=='Image Test':
    st.title('Image Test')
    rows=[]
    for ex in workouts.exercise.drop_duplicates():
        img=find_img(ex); rows.append({'exercise':ex,'status':'FOUND' if img else 'MISSING','file':img.name if img else ''})
    st.dataframe(pd.DataFrame(rows),use_container_width=True)
elif page=='History':
    st.title('History'); hist=load_log(); st.dataframe(hist.tail(500),use_container_width=True)
    if not hist.empty: st.download_button('Download workout_log.csv', hist.to_csv(index=False).encode(), 'workout_log.csv','text/csv')
elif page=='Progress':
    st.title('Progress'); hist=load_log()
    if hist.empty: st.info('No saved workouts yet.')
    else:
        hist['volume']=pd.to_numeric(hist['volume'],errors='coerce').fillna(0); st.bar_chart(hist.groupby('exercise')['volume'].sum().sort_values(ascending=False).head(15))
elif page=='Data & Export':
    st.title('Data & Export'); st.write('Workout history saves to data/workout_log.csv')
    if LOG_FILE.exists(): st.download_button('Export workout history', LOG_FILE.read_bytes(),'workout_log.csv','text/csv')
