from __future__ import annotations
import json, socket
from datetime import date, datetime
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).parent
LIB_FILE = APP_DIR / 'exercise_library.csv'
BLOCK_FILE = APP_DIR / 'block_templates.csv'
LOG_FILE = APP_DIR / 'workout_log.csv'
PROFILE_FILE = APP_DIR / 'profile.json'
DAY_ORDER = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
LOG_COLS = ['date','saved_at','week','block','day','workout','muscle_group','exercise','set_number','weight_lbs','reps','pain','notes','volume']
DO_NOT_DO = ['Leg Press','Squats','Lunges','Running','Stair Climber','Smith Machine Squats','Heavy Lower Body Loading']

st.set_page_config(page_title='Brian Fitness Tracker Pro v13', page_icon='🏋️', layout='wide', initial_sidebar_state='expanded')

st.markdown('''
<style>
:root{--navy:#071A33;--blue:#2563EB;--teal:#14B8A6;--gold:#F59E0B;--green:#16A34A;--red:#DC2626;--bg:#F4F7FB;--card:#FFFFFF;--text:#111827;--muted:#64748B;--line:#E2E8F0;}
[data-testid="stAppViewContainer"]{background:var(--bg);color:var(--text)}.block-container{padding-top:1rem;max-width:1320px}h1,h2,h3{color:var(--text)!important;font-weight:950!important}.hero{background:linear-gradient(135deg,#071A33,#0E3A67);color:white;border-radius:26px;padding:24px 28px;margin-bottom:18px;box-shadow:0 14px 35px rgba(7,26,51,.18)}.hero h1{color:white!important;margin:0;font-size:2rem!important}.hero p{color:#CFE2FF;margin:6px 0 0 0}.card{background:white;border:1px solid var(--line);border-radius:20px;padding:18px;box-shadow:0 6px 18px rgba(15,23,42,.05);margin-bottom:14px}.metric-label{font-size:.75rem;text-transform:uppercase;color:var(--muted);font-weight:950;letter-spacing:.06em}.metric-value{font-size:1.7rem;color:var(--navy);font-weight:950}.day-card{background:white;border:1px solid var(--line);border-radius:18px;padding:16px;margin:8px 0;box-shadow:0 4px 14px rgba(15,23,42,.04)}.today{border:2px solid var(--blue);background:#F8FBFF}.pill{display:inline-block;border-radius:999px;padding:6px 10px;font-size:.78rem;font-weight:950;margin-right:6px}.pill-navy{background:var(--navy);color:white}.pill-blue{background:#DBEAFE;color:#1D4ED8;border:1px solid #BFDBFE}.pill-green{background:#DCFCE7;color:#166534;border:1px solid #BBF7D0}.pill-gold{background:#FEF3C7;color:#92400E;border:1px solid #FDE68A}.work-card{background:white;border:1px solid var(--line);border-radius:24px;overflow:hidden;box-shadow:0 16px 38px rgba(15,23,42,.08);margin-bottom:18px}.work-head{background:linear-gradient(135deg,#071A33,#0E3A67);padding:22px 26px;color:white}.work-head h2{color:white!important;margin:0}.work-body{padding:20px 24px}.volume{background:#ECFDF5;border:1px solid #BBF7D0;border-radius:16px;padding:12px;text-align:center;color:#166534;font-weight:950}.setnum{background:var(--blue);color:white;border-radius:50%;height:36px;width:36px;display:flex;align-items:center;justify-content:center;font-weight:950}.warn{background:#FFF7ED;border:1px solid #FED7AA;color:#9A3412;border-radius:16px;padding:14px;font-weight:850}.safe{background:#ECFDF5;border:1px solid #BBF7D0;color:#166534;border-radius:16px;padding:14px;font-weight:850}.info{background:#EFF6FF;border:1px solid #BFDBFE;color:#1D4ED8;border-radius:16px;padding:14px;font-weight:850}.stButton>button{border-radius:14px;min-height:3rem;font-weight:950;border:1px solid var(--line)}.stNumberInput input{font-size:1.05rem!important;font-weight:900!important;text-align:center!important;color:#111827!important;background:#F8FAFC!important}.stTextInput input,.stTextArea textarea{background:#F8FAFC!important;color:#111827!important}.sidebar-brand{background:linear-gradient(135deg,#071A33,#0E3A67);color:white;border-radius:20px;padding:18px;text-align:center;margin-bottom:14px}.sidebar-brand h2{color:white!important;margin:0}.sidebar-brand small{color:#CFE2FF}.nav-note{background:#F8FAFC;border:1px solid var(--line);border-radius:14px;padding:12px;color:var(--muted);font-size:.9rem}.exercise-list{line-height:1.8;color:#334155}.small{color:var(--muted);font-weight:650}@media(max-width:850px){.hero h1{font-size:1.45rem!important}.block-container{padding-left:.7rem;padding-right:.7rem}.work-body{padding:16px}.work-head{padding:18px}}
</style>
''', unsafe_allow_html=True)

def get_ip():
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('8.8.8.8',80)); ip=s.getsockname()[0]; s.close(); return ip
    except Exception: return 'YOUR-COMPUTER-IP'

def load_lib(): return pd.read_csv(LIB_FILE)
def load_blocks(): return pd.read_csv(BLOCK_FILE)
def load_log(): return pd.read_csv(LOG_FILE) if LOG_FILE.exists() else pd.DataFrame(columns=LOG_COLS)
def save_log(df): df[LOG_COLS].to_csv(LOG_FILE,index=False)
def load_profile():
    d={'current_weight':0.0,'goal_weight':0.0,'week':1,'rotation_weeks':4,'gym':'LA Fitness'}
    if PROFILE_FILE.exists():
        try: d.update(json.loads(PROFILE_FILE.read_text()))
        except Exception: pass
    return d
def save_profile(p): PROFILE_FILE.write_text(json.dumps(p,indent=2))
def today_name(): return date.today().strftime('%A')
def current_block(week:int, rotation:int=4): return ((week-1)//rotation)+1
def template_for_week(blocks, week:int, rotation:int=4):
    blk=current_block(week,rotation)
    # only two templates included; after block 2 repeat block 2 as variation until more are added
    use_blk = blk if blk in set(blocks['block']) else 2
    return blocks[blocks.block==use_blk].copy(), blk, use_blk
def exercise_details(lib, name):
    hit=lib[lib.exercise==name]
    if hit.empty: return {'target_sets':3,'target_reps':'12','starting_weight_lbs':0,'equipment':'LA Fitness','notes':'Custom exercise','knee_safe':'yes'}
    return hit.iloc[0].to_dict()
def best_weight(log, ex): return 0.0 if log.empty or log[log.exercise==ex].empty else float(log[log.exercise==ex].weight_lbs.max())
def last_vals(log, ex, setn, fallback):
    if log.empty: return fallback,0
    d=log[(log.exercise==ex)&(log.set_number==setn)].copy()
    if d.empty: return fallback,0
    d['date']=pd.to_datetime(d['date'],errors='coerce'); d=d.sort_values(['date','saved_at'])
    r=d.iloc[-1]; return float(r.weight_lbs), int(r.reps)

lib=load_lib(); blocks=load_blocks(); log=load_log(); profile=load_profile()
week=int(profile.get('week',1)); rotation=int(profile.get('rotation_weeks',4))
plan, real_block, template_block = template_for_week(blocks, week, rotation)

with st.sidebar:
    st.markdown('<div class="sidebar-brand"><h2>BRIAN PRO</h2><small>Adaptive Training Engine v13</small></div>', unsafe_allow_html=True)
    page=st.radio('Navigation',['Dashboard','Today Workout','4-Week Blocks','Workout Builder','Exercise Library','Progress','History','Knee Safety','Profile'],label_visibility='collapsed')
    st.markdown(f'<div class="nav-note"><b>Current Block</b><br>Week {week} → Block {real_block}<br>Exercises rotate every {rotation} weeks.</div>', unsafe_allow_html=True)
    st.markdown('<div class="nav-note"><b>Gym Mode</b><br>Built around common LA Fitness machines, cables, Hammer Strength, Life Fitness, and knee-safe rehab choices.</div>', unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>🏋️ Brian Fitness Tracker Pro v13</h1><p>Adaptive 4-week training blocks — same muscle groups, new LA Fitness exercises, knee-safe progression.</p></div>', unsafe_allow_html=True)

sessions=log['date'].nunique() if not log.empty else 0
volume=float(log['volume'].sum()) if not log.empty else 0
avg_pain=float(log['pain'].mean()) if not log.empty else 0
c1,c2,c3,c4=st.columns(4)
for col,label,val in [(c1,'Current Week',week),(c2,'Training Block',real_block),(c3,'Workouts',sessions),(c4,'Total Volume',f'{volume:,.0f}')]:
    col.markdown(f'<div class="card"><div class="metric-label">{label}</div><div class="metric-value">{val}</div></div>', unsafe_allow_html=True)

if page=='Dashboard':
    st.subheader('Weekly Schedule — Muscle Groups Stay Consistent')
    today=today_name(); cols=st.columns(2)
    for idx,day in enumerate(DAY_ORDER):
        d=plan[plan.day==day].sort_values('exercise_order')
        if d.empty: continue
        exercises=d.exercise.tolist()
        html=f'<div class="day-card {"today" if day==today else ""}"><span class="pill pill-navy">{day[:3].upper()}</span><span class="pill pill-blue">{d.muscle_group.iloc[0]}</span><span class="pill pill-gold">Block {real_block}</span><h3>{d.workout.iloc[0]}</h3><div class="small">{len(exercises)} exercises</div><div class="exercise-list">' + '<br>'.join([f'• {e}' for e in exercises[:7]]) + ('<br>• ...' if len(exercises)>7 else '') + '</div></div>'
        cols[idx%2].markdown(html, unsafe_allow_html=True)
    st.markdown('<div class="info">When Week 5 starts, the app automatically switches to Block 2 exercises while keeping the same weekly muscle-group structure.</div>', unsafe_allow_html=True)

elif page=='Today Workout':
    st.subheader('Workout Tracker')
    dcol,wcol=st.columns(2)
    workout_date=dcol.date_input('Date',value=date.today())
    week_num=int(wcol.number_input('Week',1,52,week))
    day=st.selectbox('Workout day',DAY_ORDER,index=DAY_ORDER.index(today_name()) if today_name() in DAY_ORDER else 0)
    active_plan, active_block, used_template = template_for_week(blocks, week_num, rotation)
    day_df=active_plan[active_plan.day==day].sort_values('exercise_order').reset_index(drop=True)
    if day=='Thursday': st.markdown('<div class="warn">🦵 Leg Rehab Day: no downward loading. Stop any exercise that causes knee pain.</div>', unsafe_allow_html=True)
    if day=='Sunday': st.markdown('<div class="safe">Recovery day: swimming, bike, sauna, and recovery.</div>', unsafe_allow_html=True)
    if day_df.empty:
        st.warning('No exercises found for this day.')
    else:
        ex_index=st.selectbox('Choose exercise', list(range(len(day_df))), format_func=lambda i:f'{i+1}. {day_df.exercise.iloc[i]}')
        r=day_df.iloc[int(ex_index)]
        details=exercise_details(lib, r.exercise)
        target_sets=int(details.get('target_sets',3)); target_reps=str(details.get('target_reps','12')); default=float(details.get('starting_weight_lbs',0) or 0)
        pb=best_weight(log,r.exercise)
        st.markdown(f'<div class="work-card"><div class="work-head"><h2>{r.exercise}</h2><span class="pill pill-blue">{r.muscle_group}</span><span class="pill pill-green">{details.get("equipment","LA Fitness")}</span><span class="pill pill-gold">Block {active_block}</span><p>{details.get("notes","")}</p></div><div class="work-body">', unsafe_allow_html=True)
        a,b,c,d=st.columns(4)
        a.metric('Target',f'{target_sets} × {target_reps}')
        b.metric('Personal Best',f'{pb:g} lbs')
        c.metric('Knee Safe',str(details.get('knee_safe','yes')).upper())
        d.metric('Exercise',f'{int(ex_index)+1}/{len(day_df)}')
        sets=int(st.number_input('Sets today',1,8,target_sets))
        pain=int(st.number_input('Pain 0-10',0,10,0))
        notes=st.text_area('Notes',placeholder='Example: felt strong, knee okay, too heavy')
        rows=[]; total=0
        for s in range(1,sets+1):
            lw,lr=last_vals(log,r.exercise,s,default)
            cols=st.columns([.5,1.2,1.2,1.2])
            cols[0].markdown(f'<div class="setnum">{s}</div>', unsafe_allow_html=True)
            weight=cols[1].number_input(f'Set {s} lbs',0.0,value=float(lw),step=2.5,key=f'{day}_{ex_index}_{s}_w')
            reps=cols[2].number_input(f'Set {s} reps',0,value=int(lr),step=1,key=f'{day}_{ex_index}_{s}_r')
            vol=weight*reps; total+=vol
            cols[3].markdown(f'<div class="volume">VOLUME<br><b>{vol:,.0f}</b> lbs</div>', unsafe_allow_html=True)
            if reps>0:
                rows.append({'date':str(workout_date),'saved_at':datetime.now().isoformat(timespec='seconds'),'week':week_num,'block':active_block,'day':day,'workout':r.workout,'muscle_group':r.muscle_group,'exercise':r.exercise,'set_number':s,'weight_lbs':weight,'reps':reps,'pain':pain,'notes':notes,'volume':vol})
        st.markdown(f'<div class="card"><div class="metric-label">Exercise Volume</div><div class="metric-value">{total:,.0f} lbs</div></div>', unsafe_allow_html=True)
        if st.button('💾 Save Exercise',type='primary'):
            if rows:
                new=pd.concat([load_log(),pd.DataFrame(rows)],ignore_index=True)
                for col in LOG_COLS:
                    if col not in new.columns: new[col]=''
                save_log(new)
                st.success(f'Saved {r.exercise}.')
                st.rerun()
            else: st.warning('Enter reps before saving.')
        st.markdown('</div></div>', unsafe_allow_html=True)

elif page=='4-Week Blocks':
    st.subheader('Adaptive Training Blocks')
    st.markdown('<div class="info">Block 1 covers Weeks 1–4. Block 2 covers Weeks 5–8. After that, the app can repeat Block 2 or you can add more templates.</div>', unsafe_allow_html=True)
    for b in sorted(blocks.block.unique()):
        bd=blocks[blocks.block==b]
        st.markdown(f'### Block {b}: Weeks {bd.week_start.min()}–{bd.week_end.max()}')
        for day in DAY_ORDER:
            d=bd[bd.day==day].sort_values('exercise_order')
            if not d.empty:
                st.markdown(f'<div class="day-card"><span class="pill pill-navy">{day}</span><span class="pill pill-blue">{d.muscle_group.iloc[0]}</span><b>{d.workout.iloc[0]}</b><div class="exercise-list">' + '<br>'.join([f'• {e}' for e in d.exercise.tolist()]) + '</div></div>', unsafe_allow_html=True)

elif page=='Workout Builder':
    st.subheader('Create Next 4-Week Block')
    st.markdown('<div class="info">This page shows replacement choices by muscle group using LA Fitness-style equipment. Use it to plan Block 3 or customize future rotations.</div>', unsafe_allow_html=True)
    group=st.selectbox('Muscle group', sorted(lib.muscle_group.unique()))
    gd=lib[lib.muscle_group==group][['exercise','equipment','target_sets','target_reps','knee_safe','notes']]
    st.dataframe(gd,use_container_width=True,hide_index=True)
    st.download_button('Download Exercise Library', lib.to_csv(index=False).encode('utf-8'), 'exercise_library.csv','text/csv')

elif page=='Exercise Library':
    st.subheader('LA Fitness Exercise Library')
    st.dataframe(lib,use_container_width=True,hide_index=True)

elif page=='Progress':
    st.subheader('Progress Analytics')
    if log.empty: st.info('No workouts saved yet.')
    else:
        daily=log.groupby('date',as_index=False)['volume'].sum()
        st.plotly_chart(px.line(daily,x='date',y='volume',title='Daily Training Volume'),use_container_width=True)
        muscle=log.groupby('muscle_group',as_index=False)['volume'].sum().sort_values('volume',ascending=False)
        st.plotly_chart(px.bar(muscle,x='muscle_group',y='volume',title='Volume by Muscle Group'),use_container_width=True)
        best=log.groupby('exercise',as_index=False).agg(best_weight=('weight_lbs','max'),total_volume=('volume','sum')).sort_values('total_volume',ascending=False)
        st.dataframe(best,use_container_width=True,hide_index=True)

elif page=='History':
    st.subheader('Workout History')
    if log.empty: st.info('No history yet.')
    else:
        st.dataframe(log.sort_values(['date','exercise','set_number'],ascending=[False,True,True]),use_container_width=True,hide_index=True)
        st.download_button('Download workout_log.csv',log.to_csv(index=False).encode('utf-8'),'workout_log.csv','text/csv')

elif page=='Knee Safety':
    st.subheader('Knee Safety Rules')
    st.markdown('✅ Protect right knee.  \n✅ Increase weight slowly.  \n✅ Stop any exercise that causes knee pain.  \n✅ Leave every workout feeling like you could do more.  \n✅ Progress over perfection.')
    for item in DO_NOT_DO: st.error(f'❌ {item}')
    st.success('KEEP MOVING FORWARD. CONSISTENCY > PERFECTION. HEALING > EGO.')

elif page=='Profile':
    st.subheader('Profile Settings')
    profile['current_weight']=st.number_input('Current Weight',0.0,value=float(profile.get('current_weight',0)),step=.5)
    profile['goal_weight']=st.number_input('Goal Weight',0.0,value=float(profile.get('goal_weight',0)),step=.5)
    profile['week']=st.number_input('Current Week #',1,52,value=int(profile.get('week',1)),step=1)
    profile['rotation_weeks']=st.number_input('Rotate exercises every X weeks',2,8,value=int(profile.get('rotation_weeks',4)),step=1)
    profile['gym']=st.text_input('Gym',value=str(profile.get('gym','LA Fitness')))
    if st.button('Save Profile'):
        save_profile(profile); st.success('Profile saved. The dashboard will use the updated training block.')

with st.expander('📱 Phone / Online Use'):
    st.write('For same Wi‑Fi local use, open this address on your phone:')
    st.code(f'http://{get_ip()}:8501')
    st.write('For gym use away from home, deploy the folder to Streamlit Cloud.')
