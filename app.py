from __future__ import annotations
import base64, io, re, json, zipfile
from pathlib import Path
from datetime import date, datetime

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / 'data'
ASSETS_DIR = APP_DIR / 'assets'
EX_DIR = ASSETS_DIR / 'exercises'
MUSCLE_IMG = ASSETS_DIR / 'muscle' / 'muscle_groups.png'
WORKOUTS_FILE = DATA_DIR / 'workouts.csv'
LOG_FILE = DATA_DIR / 'workout_log.csv'
BACKUP_DIR = DATA_DIR / 'backups'
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

DAY_ORDER = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
LOG_COLS = ['date','saved_at','week','day','workout','muscle_group','exercise','set_number','weight_lbs','reps','rpe','pain','notes','volume']

st.set_page_config(page_title='Brian Fitness Tracker v16.1', page_icon='🏋️', layout='wide', initial_sidebar_state='expanded')

def slug_base(s): return re.sub(r'[^a-z0-9]+','_',str(s).lower()).strip('_')
def slug(s): return slug_base(s) + '.png'

def read_csv_safe(path, cols=None):
    if path.exists():
        try: return pd.read_csv(path)
        except Exception: pass
    return pd.DataFrame(columns=cols or [])

def ensure_data():
    DATA_DIR.mkdir(exist_ok=True)
    if not LOG_FILE.exists(): pd.DataFrame(columns=LOG_COLS).to_csv(LOG_FILE, index=False)
ensure_data()

@st.cache_data(show_spinner=False)
def img_src(path_str):
    p = Path(path_str)
    if p.exists():
        ext = p.suffix.lower()
        mime = 'image/svg+xml' if ext == '.svg' else 'image/png'
        return f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode()
    return ''

def ex_img(exercise):
    """Return a real exercise visual when available. Never crashes if missing."""
    base = slug_base(exercise)
    candidates = [EX_DIR / f'{base}.png', EX_DIR / f'{base}.jpg', EX_DIR / f'{base}.jpeg', EX_DIR / f'{base}.svg']
    for p in candidates:
        if p.exists():
            return img_src(str(p))
    safe_name = str(exercise).replace('&','and')[:32]
    svg = f"""
    <svg xmlns='http://www.w3.org/2000/svg' width='360' height='240' viewBox='0 0 360 240'>
      <rect width='360' height='240' rx='24' fill='#f8fafc' stroke='#dbe7f5'/>
      <rect x='24' y='24' width='312' height='136' rx='18' fill='#eef6ff' stroke='#dbeafe'/>
      <circle cx='180' cy='84' r='34' fill='#dbeafe'/>
      <path d='M112 132 H248' stroke='#0b1f3a' stroke-width='12' stroke-linecap='round'/>
      <path d='M130 120 C150 150, 210 150, 230 120' stroke='#0b5cff' stroke-width='10' fill='none' stroke-linecap='round'/>
      <text x='180' y='195' text-anchor='middle' font-size='19' font-family='Arial' font-weight='900' fill='#0b1b34'>Image Coming Soon</text>
      <text x='180' y='219' text-anchor='middle' font-size='12' font-family='Arial' fill='#64748b'>{safe_name}</text>
    </svg>"""
    return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()

def backup_log():
    if LOG_FILE.exists():
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        (BACKUP_DIR / f'workout_log_backup_{stamp}.csv').write_bytes(LOG_FILE.read_bytes())

def save_rows(rows):
    if not rows: return False
    log = read_csv_safe(LOG_FILE, LOG_COLS)
    new = pd.concat([log, pd.DataFrame(rows)], ignore_index=True)
    new.to_csv(LOG_FILE, index=False)
    backup_log()
    return True

def load_workouts():
    df = read_csv_safe(WORKOUTS_FILE)
    # Normalize common issues
    df.columns = [str(c).strip().lower().replace(' ','_') for c in df.columns]
    for c in ['day','workout','muscle_group','exercise','target_sets','target_reps','starting_weight_lbs']:
        if c not in df.columns:
            df[c] = '' if c not in ['target_sets','starting_weight_lbs'] else 0
    return df

def last_values(log, exercise, setnum, default_w):
    if log.empty or 'exercise' not in log.columns:
        return float(default_w or 0), 0
    ex = log[(log['exercise'].astype(str)==str(exercise)) & (pd.to_numeric(log.get('set_number'), errors='coerce')==setnum)]
    if ex.empty: return float(default_w or 0), 0
    row = ex.iloc[-1]
    return float(row.get('weight_lbs', default_w) or 0), int(row.get('reps', 0) or 0)

CSS = r"""
<style>
:root{--navy:#071d38;--navy2:#092849;--blue:#0b5cff;--green:#078a35;--bg:#f3f6fb;--card:#fff;--text:#071a35;--muted:#64748b;--line:#dfe7f2;}
html,body,[data-testid="stAppViewContainer"]{background:var(--bg);color:var(--text);}
.block-container{padding-top:1.1rem;padding-left:1.5rem;padding-right:1.5rem;max-width:1500px;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#061a33 0%,#07274a 100%);border-right:1px solid #0d3a66;min-width:250px;}
[data-testid="stSidebar"] *{color:white!important;}
[data-testid="stSidebar"] .stRadio label{background:rgba(255,255,255,.06);border-radius:12px;padding:7px 10px;margin:3px 0;}
[data-testid="stSidebar"] .stRadio label:has(input:checked){background:linear-gradient(90deg,#0b5cff,#1d72ff);}
.sidebar-title{font-size:30px;font-weight:950;line-height:1.0;margin-top:45px;letter-spacing:.5px}.sidebar-sub{font-size:15px;font-weight:800;margin-top:6px}.version-pill{display:inline-block;border:1px solid rgba(96,165,250,.55);border-radius:999px;padding:8px 13px;margin:20px 0;color:#60a5fa!important;font-weight:900;background:rgba(11,92,255,.15)}
.side-card{border:1px solid rgba(148,163,184,.24);background:rgba(255,255,255,.04);border-radius:18px;padding:18px;margin-top:18px}.safe-dot{width:34px;height:34px;border-radius:50%;background:#16a34a;display:inline-flex;align-items:center;justify-content:center;font-weight:900;margin-right:12px}.backup{border:1px solid rgba(148,163,184,.28);border-radius:14px;padding:14px;margin-top:15px}
h1{font-size:36px!important;line-height:1.1;color:#071a35!important;margin:0 0 4px}.subtle{color:#64748b;font-weight:700}.badge{display:inline-block;background:#eaf2ff;border:1px solid #cfe0ff;color:#0757d6;border-radius:999px;padding:6px 12px;font-weight:900;font-size:13px;margin-right:8px}.badge-green{background:#eafaf0;border-color:#bfeecf;color:#04752d}.topbar{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:18px}.finish{background:#0b5cff;color:white;border-radius:10px;padding:13px 22px;font-weight:950;box-shadow:0 8px 18px rgba(11,92,255,.22)}
.input-card{background:white;border:1px solid var(--line);border-radius:14px;padding:14px 16px;box-shadow:0 3px 14px rgba(15,23,42,.04)}.metric-card{background:white;border:1px solid var(--line);border-radius:14px;padding:16px 18px;box-shadow:0 4px 16px rgba(15,23,42,.05);height:92px}.metric-label{font-weight:800;color:#64748b;font-size:13px}.metric-value{font-weight:950;color:#078a35;font-size:22px;margin-top:4px}
.exercise-card{background:white;border:1px solid var(--line);border-radius:18px;padding:16px;margin-bottom:18px;box-shadow:0 8px 28px rgba(15,23,42,.06)}.exercise-grid{display:grid;grid-template-columns:230px 1fr;gap:18px;align-items:start}.ex-img{width:230px;height:155px;border-radius:12px;object-fit:contain;background:#f8fbff;border:1px solid #dce5f0;box-shadow:0 2px 9px rgba(2,8,23,.08)}.ex-title{font-size:23px;font-weight:950;color:#071a35;margin:0 0 8px}.how-btn{float:right;border:1px solid #cad8ed;color:#0757d6;padding:10px 15px;border-radius:10px;font-weight:950;background:#fff}.kebab{float:right;font-size:26px;margin:4px 0 0 14px;color:#0b1b34}.prev{font-weight:800;color:#475569;margin:10px 0 12px}.set-table{width:100%;border-collapse:collapse;font-size:14px}.set-table th{color:#64748b;font-size:12px;text-align:left;border-bottom:1px solid #e5ebf3;padding:8px;font-weight:950}.set-table td{border-bottom:1px solid #eef2f7;padding:8px;font-weight:800}.set-dot{display:inline-flex;width:24px;height:24px;border-radius:50%;align-items:center;justify-content:center;background:#dbeafe;color:#0b5cff;font-weight:950}.vol{color:#078a35;font-weight:950}.ex-total{float:right;background:#eafaf0;border:1px solid #bfeecf;border-radius:9px;padding:8px 20px;color:#078a35;font-weight:950;font-size:18px}.save-row{margin-top:12px}.stButton>button{border-radius:10px;font-weight:900;border:1px solid #cbd8e7;background:white}.stNumberInput input{text-align:center;font-weight:900}.stTextInput input{font-weight:700}.right-card{background:white;border:1px solid var(--line);border-radius:16px;padding:18px;margin-bottom:14px;box-shadow:0 6px 20px rgba(15,23,42,.06)}.right-title{font-weight:950;color:#0b5cff;margin-bottom:12px}.summary-row{display:flex;justify-content:space-between;padding:8px 0;font-weight:800}.summary-row span:last-child{font-weight:950}.muscle-img{width:100%;border-radius:12px;border:1px solid #e5eaf2}.quick{border:1px solid #dce5f0;border-radius:10px;padding:12px;margin:8px 0;font-weight:950;color:#0757d6}.danger{color:#dc2626!important}.small-note{color:#64748b;font-weight:700;line-height:1.45}.stTabs [data-baseweb="tab-list"]{display:none!important} footer{visibility:hidden}.viewerBadge_container__1QSob{display:none!important}
@media(max-width:900px){.exercise-grid{grid-template-columns:1fr}.ex-img{width:100%;height:210px}.topbar{display:block}.finish{display:inline-block;margin-top:12px}.block-container{padding-left:.75rem;padding-right:.75rem}.right-col{display:none}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("<div class='sidebar-title'>🏋️ BRIAN</div><div class='sidebar-sub'>FITNESS TRACKER</div><div class='version-pill'>v16.1 Exercise Image Library</div>", unsafe_allow_html=True)
st.sidebar.markdown("<b>NAVIGATION</b>", unsafe_allow_html=True)
page = st.sidebar.radio('', ['Dashboard','Today\'s Workout','Weekly Plan','Exercise Library','Progress','History','Data Safety','Profile','Phone Setup'], index=1)
st.sidebar.markdown("<div class='side-card'><b>DATA STATUS</b><br><br><span class='safe-dot'>✓</span><b>All data is safe</b><br><span style='margin-left:47px;color:#cbd5e1!important'>workout_log.csv</span><div class='backup'>☁️ <b>EXPORT BACKUP</b><br><span style='color:#cbd5e1!important'>Download your data</span></div></div>", unsafe_allow_html=True)

workouts = load_workouts()
log = read_csv_safe(LOG_FILE, LOG_COLS)

def render_workout():
    day = st.selectbox('Workout Day', DAY_ORDER, index=DAY_ORDER.index(date.today().strftime('%A')) if date.today().strftime('%A') in DAY_ORDER else 0)
    active = workouts[workouts['day'].astype(str).str.lower() == day.lower()].reset_index(drop=True)
    if active.empty:
        st.warning('No workout loaded for this day.')
        return
    workout = str(active.loc[0,'workout'])
    muscle = str(active.loc[0,'muscle_group'])
    total_ex = len(active)
    left_main, right_panel = st.columns([4.6,1.4], gap='large')
    with left_main:
        st.markdown(f"<div class='topbar'><div><h1>{day} — {workout} ✎</h1><span class='badge'>{muscle}</span><span class='badge badge-green'>{total_ex} exercises</span></div><div class='finish'>✓ FINISH WORKOUT</div></div>", unsafe_allow_html=True)
        c1,c2,c3 = st.columns([1.1,1.2,1.5])
        workout_date = c1.date_input('Date', value=date.today())
        week = c2.number_input('Week', min_value=1, value=1, step=1)
        # computed from current inputs below display static for UI
        c3.markdown("<div class='metric-card'><div class='metric-label'>EXERCISE TOTAL VOLUME</div><div class='metric-value'>Auto Calculate</div></div>", unsafe_allow_html=True)
        rows_to_save=[]; total_volume_all=0; total_sets=0
        for idx,row in active.iterrows():
            exercise=str(row['exercise']); sets=int(row.get('target_sets',4) or 4); default_w=float(row.get('starting_weight_lbs',0) or 0); reps_target=str(row.get('target_reps','12'))
            img=ex_img(exercise)
            st.markdown("<div class='exercise-card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='exercise-grid'><div><img class='ex-img' src='{img}'></div><div><span class='kebab'>⋮</span><span class='how-btn'>▷ HOW TO DO IT</span><div class='ex-title'>{idx+1}. {exercise}</div><span class='badge'>Target: {sets} x {reps_target}</span><span class='badge badge-green'>{muscle}</span><div class='prev'>Week 1: {default_w:g} lb • 12,12,12,12</div>", unsafe_allow_html=True)
            st.markdown("<table class='set-table'><thead><tr><th>SET</th><th>WEIGHT (LBS)</th><th>REPS</th><th>RPE (0-10)</th><th>NOTES</th><th>VOLUME</th></tr></thead></table>", unsafe_allow_html=True)
            ex_volume=0; ex_rows=[]
            for s in range(1, sets+1):
                last_w,last_r = last_values(log, exercise, s, default_w)
                a,b,c,d,e,f = st.columns([.45,1.15,1.0,1.0,1.5,.9])
                a.markdown(f"<span class='set-dot'>{s}</span>", unsafe_allow_html=True)
                w = b.number_input(' ', min_value=0.0, value=float(last_w), step=2.5, key=f'w_{day}_{idx}_{s}', label_visibility='collapsed')
                reps = c.number_input(' ', min_value=0, value=int(last_r) if int(last_r)>0 else 12, step=1, key=f'r_{day}_{idx}_{s}', label_visibility='collapsed')
                rpe = d.number_input(' ', min_value=0, max_value=10, value=0, step=1, key=f'rpe_{day}_{idx}_{s}', label_visibility='collapsed')
                note = e.text_input(' ', value='felt good' if s==1 else '', key=f'n_{day}_{idx}_{s}', label_visibility='collapsed')
                vol = float(w)*int(reps); ex_volume += vol
                f.markdown(f"<div class='vol'>{vol:,.0f} lbs</div>", unsafe_allow_html=True)
                if reps>0:
                    ex_rows.append({'date':str(workout_date),'saved_at':datetime.now().isoformat(timespec='seconds'),'week':int(week),'day':day,'workout':workout,'muscle_group':muscle,'exercise':exercise,'set_number':s,'weight_lbs':w,'reps':reps,'rpe':rpe,'pain':0,'notes':note,'volume':vol})
            st.markdown(f"<div class='ex-total'>{ex_volume:,.0f} lbs</div><div style='clear:both'></div>", unsafe_allow_html=True)
            if st.button(f'💾 Save {exercise}', key=f'save_{day}_{idx}'):
                save_rows(ex_rows); st.success(f'Saved {exercise}.')
            st.markdown("</div></div></div>", unsafe_allow_html=True)
            rows_to_save += ex_rows; total_volume_all += ex_volume; total_sets += sets
        if st.button('✅ SAVE FULL WORKOUT', type='primary'):
            save_rows(rows_to_save); st.success(f'Saved full {day} workout: {len(rows_to_save)} sets.')
            st.balloons()
    with right_panel:
        st.markdown(f"<div class='right-card'><div class='right-title'>📋 WORKOUT SUMMARY</div><div class='summary-row'><span>Exercises</span><span>{total_ex}</span></div><div class='summary-row'><span>Total Sets</span><span>{int(active['target_sets'].sum())}</span></div><div class='summary-row'><span>Total Volume</span><span style='color:#078a35'>Auto</span></div><div class='summary-row'><span>Workout Time</span><span>—</span></div><div class='summary-row'><span>Calories (Est.)</span><span>—</span></div></div>", unsafe_allow_html=True)
        msrc=img_src(str(MUSCLE_IMG))
        st.markdown(f"<div class='right-card'><div class='right-title'>MUSCLE GROUPS</div><img class='muscle-img' src='{msrc}'></div>", unsafe_allow_html=True)
        st.markdown("<div class='right-card'><div class='right-title'>QUICK ACTIONS</div><div class='quick'>＋ ADD EXERCISE</div><div class='quick'>↕ REORDER EXERCISES</div><div class='quick danger'>🗑 CLEAR WORKOUT</div></div>", unsafe_allow_html=True)
        st.markdown("<div class='right-card'><div class='right-title'>💡 TIPS</div><div class='small-note'>Focus on controlled movements and mind-muscle connection. Keep knee rehab pain-free.</div></div>", unsafe_allow_html=True)

def simple_dashboard():
    st.markdown("<h1>Dashboard</h1>", unsafe_allow_html=True)
    log=read_csv_safe(LOG_FILE, LOG_COLS)
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Saved Sets', len(log))
    c2.metric('Workout Days', log['date'].nunique() if not log.empty and 'date' in log else 0)
    c3.metric('Total Volume', f"{pd.to_numeric(log.get('volume',pd.Series(dtype=float)),errors='coerce').fillna(0).sum():,.0f} lbs")
    c4.metric('Exercises', workouts['exercise'].nunique())
    st.markdown('### Weekly Plan')
    plan=workouts.groupby(['day','workout']).size().reset_index(name='exercises')
    st.dataframe(plan, use_container_width=True, hide_index=True)

def library():
    st.markdown('<h1>Exercise Library</h1>', unsafe_allow_html=True)
    q=st.text_input('Search exercise')
    df=workouts.copy()
    if q: df=df[df['exercise'].str.contains(q, case=False, na=False)]
    cols=st.columns(3)
    for i,r in df.iterrows():
        with cols[i%3]:
            st.markdown(f"<div class='right-card'><img class='muscle-img' src='{ex_img(r['exercise'])}'><h3>{r['exercise']}</h3><b>{r['muscle_group']}</b><br><span class='subtle'>{r['day']} • {r['target_sets']} x {r['target_reps']}</span></div>", unsafe_allow_html=True)

def history():
    st.markdown('<h1>History</h1>', unsafe_allow_html=True)
    log=read_csv_safe(LOG_FILE, LOG_COLS)
    st.dataframe(log, use_container_width=True, hide_index=True)
    st.download_button('Download workout_log.csv', log.to_csv(index=False).encode(), 'workout_log.csv')

def data_safety():
    st.markdown('<h1>Data Safety</h1>', unsafe_allow_html=True)
    st.success('Your completed workouts save to data/workout_log.csv. Do not delete this file during updates.')
    files=list(DATA_DIR.glob('*.csv'))
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:
        for f in files: z.write(f, arcname=f.name)
    st.download_button('Export all CSV data', buf.getvalue(), 'brian_fitness_backup.zip')
    st.write('Files found:')
    st.write([f.name for f in files])

if page == "Today's Workout": render_workout()
elif page == 'Dashboard': simple_dashboard()
elif page == 'Exercise Library': library()
elif page == 'History': history()
elif page == 'Data Safety': data_safety()
elif page == 'Weekly Plan':
    st.markdown('<h1>Weekly Plan</h1>', unsafe_allow_html=True)
    st.dataframe(workouts[['day','workout','muscle_group','exercise','target_sets','target_reps']], use_container_width=True, hide_index=True)
elif page == 'Progress': simple_dashboard()
elif page == 'Profile':
    st.markdown('<h1>Profile</h1>', unsafe_allow_html=True)
    st.info('Profile goals will be expanded in the next build.')
elif page == 'Phone Setup':
    st.markdown('<h1>Phone Setup</h1>', unsafe_allow_html=True)
    st.write('Use your Streamlit Cloud link on your phone. Add it to your home screen for app-like access.')
else: simple_dashboard()
