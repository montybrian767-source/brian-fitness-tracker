from __future__ import annotations
import random, socket
from datetime import date, datetime
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR=Path(__file__).parent
DATA=APP_DIR/'data'
CSS=APP_DIR/'assets/css/styles.css'
WORKOUTS=DATA/'workouts.csv'
LIB=DATA/'exercise_library.csv'
BLOCKS=DATA/'block_templates.csv'
LOG=DATA/'workout_log.csv'
ACTIVE=DATA/'active_block.csv'
PROFILE=DATA/'profile.csv'
NUTRITION=DATA/'nutrition_log.csv'
RECOVERY=DATA/'recovery_log.csv'
BODY=DATA/'body_stats.csv'
DAYS=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
DO_NOT=['Leg Press','Squats','Lunges','Running','Stair Climber','Smith Machine Squats','Heavy Lower Body Loading']

st.set_page_config('Brian Fitness Tracker Pro v17','🏋️',layout='wide',initial_sidebar_state='expanded')
if CSS.exists(): st.markdown(f'<style>{CSS.read_text()}</style>', unsafe_allow_html=True)

def read_csv(path, cols=None):
    if path.exists(): return pd.read_csv(path)
    return pd.DataFrame(columns=cols or [])

def save_csv(df,path): path.parent.mkdir(parents=True,exist_ok=True); df.to_csv(path,index=False)

def lan_ip():
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('8.8.8.8',80)); ip=s.getsockname()[0]; s.close(); return ip
    except Exception: return 'YOUR-COMPUTER-IP'

def load_profile():
    df=read_csv(PROFILE)
    default={'current_weight':0.0,'goal_weight':0.0,'week':1,'active_block':1,'protein_days':0,'swims':0,'bike_miles':0.0,'daily_protein_goal':180,'daily_water_goal':100,'daily_calorie_goal':2200,'sleep_goal':7.5}
    if not df.empty:
        for _,r in df.iterrows():
            default[str(r['key'])]=r['value']
    for k in ['current_weight','goal_weight','bike_miles','daily_protein_goal','daily_water_goal','daily_calorie_goal','sleep_goal']:
        try: default[k]=float(default[k])
        except: default[k]=0.0
    for k in ['week','active_block','protein_days','swims']:
        try: default[k]=int(float(default[k]))
        except: default[k]=1 if k in ['week','active_block'] else 0
    return default

def save_profile(p): save_csv(pd.DataFrame([{'key':k,'value':v} for k,v in p.items()]), PROFILE)

def add_details(block_df, lib):
    if block_df.empty: return block_df
    m=block_df.merge(lib, on='exercise', how='left', suffixes=('','_lib'))
    for c in ['target_sets','target_reps','starting_weight_lbs','notes','equipment','knee_safe']:
        if c not in m.columns: m[c]=''
        libcol=c+'_lib'
        if libcol in m.columns: m[c]=m[c].fillna(m[libcol])
    return m

def get_active_workouts():
    prof=load_profile(); blocks=read_csv(BLOCKS); lib=read_csv(LIB)
    b=int(prof.get('active_block',1))
    df=blocks[blocks['block']==b].copy() if 'block' in blocks.columns else pd.DataFrame()
    if df.empty: df=read_csv(WORKOUTS).copy(); return df
    return add_details(df,lib).sort_values(['day','exercise_order'])

def best_weight(log, exercise):
    if log.empty or 'exercise' not in log: return 0
    ex=log[log.exercise==exercise]
    return float(ex.weight_lbs.max()) if not ex.empty and 'weight_lbs' in ex else 0

def last_set(log, exercise, set_number, fallback):
    if log.empty: return fallback,0
    ex=log[(log.exercise==exercise)&(log.set_number==set_number)].copy()
    if ex.empty: return fallback,0
    ex['saved_at_dt']=pd.to_datetime(ex.get('saved_at',ex['date']),errors='coerce')
    r=ex.sort_values('saved_at_dt').iloc[-1]
    return float(r.weight_lbs), int(r.reps)

def generate_next_block(block_number:int, weeks:int=4):
    lib=read_csv(LIB)
    base=read_csv(WORKOUTS)
    rows=[]
    day_plan={
      'Monday':('Chest + Triceps + Abs',['Chest','Triceps','Abs'],[3,2,1]),
      'Tuesday':('Back + Biceps + Forearms',['Back','Biceps','Forearms'],[4,2,2]),
      'Wednesday':('Shoulders + Abs',['Shoulders','Abs'],[5,2]),
      'Thursday':('Leg Rehab Day',['Leg Rehab','Abs'],[5,1]),
      'Friday':('Chest + Triceps Heavy',['Chest','Triceps','Abs'],[4,2,1]),
      'Saturday':('Back + Shoulders + Arms',['Back','Shoulders','Biceps','Triceps','Forearms'],[2,2,2,1,1]),
      'Sunday':('Recovery',['Recovery'],[4]),
    }
    prior=set(read_csv(BLOCKS)['exercise'].astype(str).tolist()) if BLOCKS.exists() else set()
    for day,(workout,groups,counts) in day_plan.items():
        order=1
        for group,count in zip(groups,counts):
            gdf=lib[lib.muscle_group.eq(group)].copy()
            if day=='Thursday': gdf=gdf[gdf.knee_safe.astype(str).str.lower().eq('yes')]
            if gdf.empty: continue
            # Prefer exercises not already in current template, but allow repeats when needed.
            preferred=gdf[~gdf.exercise.astype(str).isin(prior)]
            pool=preferred if len(preferred)>=min(count,len(gdf)) else gdf
            chosen=pool.sample(n=min(count,len(pool)), random_state=block_number*17+order) if len(pool)>0 else pd.DataFrame()
            for _,r in chosen.iterrows():
                rows.append({'block':block_number,'week_start':(block_number-1)*weeks+1,'week_end':block_number*weeks,'day':day,'workout':workout,'muscle_group':' + '.join(groups),'exercise_order':order,'exercise':r.exercise})
                order+=1
    return pd.DataFrame(rows)

profile=load_profile(); log=read_csv(LOG)
st.sidebar.markdown('## 🏋️ Pro v17')
page=st.sidebar.radio('Navigation',['Dashboard','Today Workout','Weekly Plan','AI Rotation','Nutrition','Recovery','Progress','History','Profile','Phone Setup'])
st.sidebar.caption('Nutrition • Recovery • AI Rotation • LA Fitness')

if page=='Dashboard':
    st.markdown('<div class="hero"><h1>Brian Fitness Tracker Pro v17</h1><p>Nutrition + Recovery Dashboard · AI Workout Rotation Engine · 4-week blocks · investor-style dashboard</p></div>', unsafe_allow_html=True)
    active=get_active_workouts(); today=date.today().strftime('%A')
    today_df=active[active['day'].eq(today)] if 'day' in active else pd.DataFrame()
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Active Block', f"Block {profile.get('active_block',1)}")
    c2.metric('Current Week', profile.get('week',1))
    c3.metric('Gym Sessions', log['date'].nunique() if not log.empty and 'date' in log else 0)
    c4.metric('Total Volume', f"{log.volume.sum():,.0f} lbs" if not log.empty and 'volume' in log else '0 lbs')
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader(f"Today's Mission: {today}")
    if not today_df.empty:
        st.markdown(f"### {today_df.iloc[0].workout}")
        st.markdown(f"<span class='badge'>{today_df.iloc[0].muscle_group}</span> <span class='badge badge-gold'>{len(today_df)} exercises</span>", unsafe_allow_html=True)
        st.write(', '.join(today_df.exercise.astype(str).tolist()[:8]))
    else: st.info('No workout scheduled today.')
    st.markdown('</div>', unsafe_allow_html=True)
    st.subheader('Weekly Plan')
    for day in DAYS:
        d=active[active['day'].eq(day)] if 'day' in active else pd.DataFrame()
        if d.empty: continue
        st.markdown(f"<div class='day-card'><div class='day-title'>{day} — {d.iloc[0].workout}</div><div class='muted'>{d.iloc[0].muscle_group} · {len(d)} exercises</div></div>", unsafe_allow_html=True)

elif page=='Today Workout':
    active=get_active_workouts(); lib=read_csv(LIB)
    day=st.selectbox('Workout Day',DAYS,index=DAYS.index(date.today().strftime('%A')) if date.today().strftime('%A') in DAYS else 0)
    d=active[active['day'].eq(day)].reset_index(drop=True)
    st.markdown(f'<div class="hero"><h1>{day}</h1><p>{d.iloc[0].workout if not d.empty else "Workout"}</p></div>', unsafe_allow_html=True)
    if day=='Thursday': st.markdown('<div class="warning">🦵 Leg Rehab Day: no downward loading. Stop anything that causes knee pain.</div>', unsafe_allow_html=True)
    wdate=st.date_input('Date', date.today()); week=st.number_input('Week',1,52,int(profile.get('week',1)))
    saved=[]
    for i,r in d.iterrows():
        ex=str(r.exercise); sets=int(float(r.get('target_sets',3) or 3)); default=float(r.get('starting_weight_lbs',0) or 0); reps_target=str(r.get('target_reps','12'))
        st.markdown('<div class="exercise-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="exercise-name">{i+1}. {ex}</div>', unsafe_allow_html=True)
        st.markdown(f"<span class='badge'>Target: {sets} × {reps_target}</span> <span class='badge badge-green'>{r.get('equipment','LA Fitness')}</span>", unsafe_allow_html=True)
        note=st.text_input('Notes',key=f'note_{day}_{i}',placeholder='felt strong, too easy, knee okay')
        pain=st.slider('Pain score',0,10,0,key=f'pain_{day}_{i}')
        for s in range(1,sets+1):
            lw,lr=last_set(log,ex,s,default)
            a,b,c=st.columns([1,1,1])
            wt=a.number_input(f'Set {s} lbs',min_value=0.0,value=float(lw),step=2.5,key=f'w_{day}_{i}_{s}')
            rp=b.number_input(f'Set {s} reps',min_value=0,value=int(lr or 0),step=1,key=f'r_{day}_{i}_{s}')
            c.markdown(f"<div class='volume-box'>Volume<br><span style='font-size:1.35rem'>{wt*rp:,.0f} lbs</span></div>", unsafe_allow_html=True)
            if rp>0: saved.append({'date':str(wdate),'saved_at':datetime.now().isoformat(timespec='seconds'),'week':int(week),'block':int(profile.get('active_block',1)),'day':day,'workout':r.workout,'muscle_group':r.muscle_group,'exercise':ex,'set_number':s,'weight_lbs':wt,'reps':rp,'pain':pain,'notes':note,'volume':wt*rp})
        bw=best_weight(log,ex)
        if bw: st.caption(f'Personal best: {bw:g} lbs')
        st.markdown('</div>', unsafe_allow_html=True)
    if st.button('💾 Save Workout', type='primary'):
        if saved:
            old=read_csv(LOG); save_csv(pd.concat([old,pd.DataFrame(saved)],ignore_index=True),LOG); st.success(f'Saved {len(saved)} sets. Great job.'); st.balloons()
        else: st.warning('Enter reps for at least one set first.')

elif page=='Weekly Plan':
    active=get_active_workouts(); st.markdown('<div class="hero"><h1>Weekly Training Plan</h1><p>Same muscle groups, current 4-week block exercises.</p></div>', unsafe_allow_html=True)
    for day in DAYS:
        d=active[active['day'].eq(day)] if 'day' in active else pd.DataFrame()
        if d.empty: continue
        st.markdown(f"<div class='card'><h3>{day} — {d.iloc[0].workout}</h3><span class='badge'>{d.iloc[0].muscle_group}</span>", unsafe_allow_html=True)
        st.dataframe(d[['exercise_order','exercise','equipment','target_sets','target_reps','knee_safe']].rename(columns={'exercise_order':'#','target_sets':'sets','target_reps':'reps'}),hide_index=True,use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

elif page=='AI Rotation':
    st.markdown('<div class="hero"><h1>AI Workout Rotation Engine</h1><p>Create a fresh 4-week block using LA Fitness exercises while keeping your muscle-group schedule.</p></div>', unsafe_allow_html=True)
    blocks=read_csv(BLOCKS); max_block=int(blocks.block.max()) if not blocks.empty and 'block' in blocks else 1
    c1,c2=st.columns(2); c1.metric('Available Blocks',max_block); c2.metric('Active Block',profile.get('active_block',1))
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader('Generate Next 4-Week Block')
    st.write('This keeps Monday chest/triceps, Tuesday back/biceps, Thursday rehab, etc., but rotates exercises from your LA Fitness library.')
    if st.button('⚡ Generate Next Block', type='primary'):
        nb=max_block+1; new=generate_next_block(nb); save_csv(pd.concat([blocks,new],ignore_index=True),BLOCKS); st.success(f'Generated Block {nb}. Go to Profile to make it active, or use the button below.'); st.dataframe(new,hide_index=True,use_container_width=True)
    if st.button('✅ Make Newest Block Active'):
        blocks=read_csv(BLOCKS); profile['active_block']=int(blocks.block.max()); save_profile(profile); st.success(f"Active block is now Block {profile['active_block']}.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.subheader('Block Preview')
    chosen=st.selectbox('Choose block to preview', sorted(blocks.block.unique()) if not blocks.empty else [1], index=0)
    prev=add_details(blocks[blocks.block.eq(chosen)], read_csv(LIB)) if not blocks.empty else pd.DataFrame()
    if not prev.empty: st.dataframe(prev[['day','workout','muscle_group','exercise_order','exercise','equipment','target_sets','target_reps','knee_safe']],hide_index=True,use_container_width=True)


elif page=='Nutrition':
    st.markdown('<div class="hero"><h1>Nutrition Tracker</h1><p>Track protein, calories, water, and daily notes.</p></div>', unsafe_allow_html=True)
    nlog=read_csv(NUTRITION)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader('Today\'s Nutrition')
    ndate=st.date_input('Nutrition Date', date.today(), key='nutrition_date')
    c1,c2,c3=st.columns(3)
    protein=c1.number_input('Protein grams',0,400,int(float(profile.get('daily_protein_goal',180))),step=5)
    calories=c2.number_input('Calories',0,6000,int(float(profile.get('daily_calorie_goal',2200))),step=50)
    water=c3.number_input('Water ounces',0,300,int(float(profile.get('daily_water_goal',100))),step=5)
    nnotes=st.text_input('Nutrition notes',placeholder='Example: hit protein, low appetite, meal prep')
    if st.button('Save Nutrition', type='primary'):
        row=pd.DataFrame([{'date':str(ndate),'saved_at':datetime.now().isoformat(timespec='seconds'),'protein_g':protein,'calories':calories,'water_oz':water,'notes':nnotes}])
        save_csv(pd.concat([nlog,row],ignore_index=True),NUTRITION); st.success('Nutrition saved.')
    st.markdown('</div>', unsafe_allow_html=True)
    nlog=read_csv(NUTRITION)
    if not nlog.empty:
        c1,c2,c3=st.columns(3)
        c1.metric('Avg Protein', f"{nlog.protein_g.mean():.0f} g")
        c2.metric('Avg Water', f"{nlog.water_oz.mean():.0f} oz")
        c3.metric('Days Logged', len(nlog.date.unique()))
        daily=nlog.groupby('date',as_index=False).agg(protein_g=('protein_g','sum'),water_oz=('water_oz','sum'),calories=('calories','sum'))
        st.plotly_chart(px.line(daily,x='date',y=['protein_g','water_oz'],title='Protein and Water Trend'),use_container_width=True)
        st.dataframe(nlog.sort_values('date',ascending=False),hide_index=True,use_container_width=True)
    else:
        st.info('No nutrition logs yet.')

elif page=='Recovery':
    st.markdown('<div class="hero"><h1>Recovery & Knee Tracker</h1><p>Track sleep, soreness, knee pain, swims, bike miles, sauna, and recovery quality.</p></div>', unsafe_allow_html=True)
    rlog=read_csv(RECOVERY)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader('Today\'s Recovery')
    rdate=st.date_input('Recovery Date', date.today(), key='recovery_date')
    c1,c2,c3=st.columns(3)
    sleep=c1.number_input('Sleep hours',0.0,16.0,float(profile.get('sleep_goal',7.5)),step=.25)
    knee=c2.slider('Knee pain 0-10',0,10,0)
    soreness=c3.slider('Body soreness 0-10',0,10,3)
    c4,c5,c6=st.columns(3)
    swim=c4.number_input('Swim distance',0.0,10000.0,0.0,step=50.0)
    bike=c5.number_input('Bike miles',0.0,200.0,0.0,step=.5)
    sauna=c6.checkbox('Sauna completed')
    rnotes=st.text_input('Recovery notes',placeholder='Example: knee felt good, used sauna, easy swim')
    if st.button('Save Recovery', type='primary'):
        row=pd.DataFrame([{'date':str(rdate),'saved_at':datetime.now().isoformat(timespec='seconds'),'sleep_hours':sleep,'knee_pain':knee,'soreness':soreness,'swim_distance':swim,'bike_miles':bike,'sauna':sauna,'notes':rnotes}])
        save_csv(pd.concat([rlog,row],ignore_index=True),RECOVERY); st.success('Recovery saved.')
    st.markdown('</div>', unsafe_allow_html=True)
    rlog=read_csv(RECOVERY)
    if not rlog.empty:
        c1,c2,c3=st.columns(3)
        c1.metric('Avg Sleep', f"{rlog.sleep_hours.mean():.1f} hrs")
        c2.metric('Avg Knee Pain', f"{rlog.knee_pain.mean():.1f}/10")
        c3.metric('Bike Miles', f"{rlog.bike_miles.sum():.1f}")
        daily=rlog.groupby('date',as_index=False).agg(sleep_hours=('sleep_hours','mean'),knee_pain=('knee_pain','mean'),soreness=('soreness','mean'))
        st.plotly_chart(px.line(daily,x='date',y=['sleep_hours','knee_pain','soreness'],title='Recovery Trend'),use_container_width=True)
        st.dataframe(rlog.sort_values('date',ascending=False),hide_index=True,use_container_width=True)
    else:
        st.info('No recovery logs yet.')

elif page=='Progress':
    st.markdown('<div class="hero"><h1>Progress Analytics</h1><p>Volume, personal records, knee pain, and consistency.</p></div>', unsafe_allow_html=True)
    if log.empty: st.info('No saved workouts yet.')
    else:
        c1,c2,c3=st.columns(3); c1.metric('Sessions',log['date'].nunique()); c2.metric('Sets',len(log)); c3.metric('Avg Pain',f"{log.pain.mean():.1f}/10")
        daily=log.groupby('date',as_index=False)['volume'].sum(); st.plotly_chart(px.line(daily,x='date',y='volume',title='Daily Training Volume'),use_container_width=True)
        best=log.groupby('exercise',as_index=False).agg(best_weight=('weight_lbs','max'),total_volume=('volume','sum')).sort_values('total_volume',ascending=False)
        st.dataframe(best,hide_index=True,use_container_width=True)

elif page=='History':
    st.markdown('<div class="hero"><h1>Workout History</h1><p>Saved workout sets and export.</p></div>', unsafe_allow_html=True)
    if log.empty: st.info('No history yet.')
    else:
        st.dataframe(log.sort_values(['date','saved_at'],ascending=False),hide_index=True,use_container_width=True)
        st.download_button('Download workout_log.csv',log.to_csv(index=False).encode(),file_name='workout_log.csv')

elif page=='Profile':
    st.markdown('<div class="hero"><h1>Profile & Settings</h1><p>Body goals, active block, and monthly scoreboard.</p></div>', unsafe_allow_html=True)
    blocks=read_csv(BLOCKS); maxb=int(blocks.block.max()) if not blocks.empty and 'block' in blocks else 1
    profile['current_weight']=st.number_input('Current Weight',0.0,600.0,float(profile.get('current_weight',0)),step=.5)
    profile['goal_weight']=st.number_input('Goal Weight',0.0,600.0,float(profile.get('goal_weight',0)),step=.5)
    profile['week']=st.number_input('Current Week',1,52,int(profile.get('week',1)))
    profile['active_block']=st.number_input('Active Training Block',1,maxb,int(profile.get('active_block',1)))
    profile['swims']=st.number_input('Swims Completed',0,100,int(profile.get('swims',0)))
    profile['bike_miles']=st.number_input('Bike Miles',0.0,10000.0,float(profile.get('bike_miles',0)),step=.5)
    profile['protein_days']=st.number_input('Protein Goal Days',0,31,int(profile.get('protein_days',0)))
    profile['daily_protein_goal']=st.number_input('Daily Protein Goal (g)',0.0,400.0,float(profile.get('daily_protein_goal',180)),step=5.0)
    profile['daily_water_goal']=st.number_input('Daily Water Goal (oz)',0.0,300.0,float(profile.get('daily_water_goal',100)),step=5.0)
    profile['daily_calorie_goal']=st.number_input('Daily Calorie Goal',0.0,6000.0,float(profile.get('daily_calorie_goal',2200)),step=50.0)
    profile['sleep_goal']=st.number_input('Sleep Goal (hours)',0.0,16.0,float(profile.get('sleep_goal',7.5)),step=.25)
    if st.button('Save Profile', type='primary'): save_profile(profile); st.success('Profile saved.')
    st.subheader('Knee Safety')
    for x in DO_NOT: st.markdown(f"<span class='badge badge-red'>Do not: {x}</span>", unsafe_allow_html=True)

elif page=='Phone Setup':
    st.markdown('<div class="hero"><h1>Phone Setup</h1><p>Use locally on Wi-Fi or online through Streamlit Cloud.</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader('Local same Wi-Fi link')
    st.code(f'http://{lan_ip()}:8501')
    st.write('For gym use away from home, upload this v16 folder to GitHub and redeploy on Streamlit Cloud.')
    st.markdown('</div>', unsafe_allow_html=True)
