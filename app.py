from __future__ import annotations
from datetime import date, datetime
import pandas as pd
import streamlit as st
from utils.database import load_workouts, load_log, load_profile, append_log, save_profile, storage_status
from utils.calculations import DAY_ORDER, total_volume, sessions, avg_pain, best_weight, last_values
from utils.helpers import today_day, lan_ip

st.set_page_config(page_title='Brian Fitness Tracker Pro v15', page_icon='🏋️', layout='wide', initial_sidebar_state='expanded')
css_path = 'assets/css/styles.css'
try:
    st.markdown(f'<style>{open(css_path, encoding="utf-8").read()}</style>', unsafe_allow_html=True)
except Exception:
    pass

workouts = load_workouts()
log = load_log()
profile = load_profile()
storage = storage_status()

def day_summary(df, day):
    d=df[df['day']==day]
    if d.empty: return ('Recovery', 'Recovery', 0)
    return d['workout'].iloc[0], d['muscle_group'].iloc[0], len(d)

with st.sidebar:
    st.markdown('## BFT Pro')
    st.caption('Cloud Save v15')
    nav = st.radio('Navigation', ['Dashboard','Today Workout','Weekly Plan','Progress','Adaptive Blocks','Settings'], label_visibility='collapsed')
    st.markdown('---')
    st.write('📱 Phone link')
    st.code(f'http://{lan_ip()}:8501')

if nav == 'Dashboard':
    tday=today_day(); workout, muscle, count = day_summary(workouts, tday)
    st.markdown(f'<div class="hero"><h1>Brian Fitness Tracker Pro</h1><p>Welcome back, Brian. Today is <b>{tday}</b> — {muscle}<br><b>Storage:</b> {storage}</p></div>', unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Current Weight', f"{profile.get('current_weight',0):.1f} lbs")
    c2.metric('Goal Weight', f"{profile.get('goal_weight',0):.1f} lbs")
    c3.metric('Gym Sessions', f'{sessions(log)}')
    c4.metric('Total Volume', f'{total_volume(log):,.0f} lbs')
    st.markdown('<div class="card"><div class="card-title">Today\'s Mission</div>', unsafe_allow_html=True)
    st.markdown(f'### {workout}')
    st.markdown(f'<span class="badge">{muscle}</span><span class="badge badge-green">{count} exercises</span><span class="badge badge-gold">Block {profile.get("block",1)} · Week {profile.get("week",1)}</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('### Weekly Schedule')
    cols=st.columns(7)
    for i,day in enumerate(DAY_ORDER):
        w,m,n=day_summary(workouts, day)
        cls='rest' if day=='Sunday' else 'rehab' if day=='Thursday' else 'week-card'
        cols[i].markdown(f'<div class="mini-card {cls}"><b>{day[:3].upper()}</b><br><span class="muted">{m}</span><br><span class="badge">{n} exercises</span></div>', unsafe_allow_html=True)

elif nav == 'Today Workout':
    selected_day=st.selectbox('Workout day', DAY_ORDER, index=DAY_ORDER.index(today_day()) if today_day() in DAY_ORDER else 0)
    day_df=workouts[workouts['day']==selected_day].reset_index(drop=True)
    workout_name=day_df['workout'].iloc[0] if not day_df.empty else 'Recovery'
    muscle=day_df['muscle_group'].iloc[0] if not day_df.empty else 'Recovery'
    st.markdown(f'<div class="hero"><h1>{selected_day}: {workout_name}</h1><p>{muscle} · one clean workout at a time</p></div>', unsafe_allow_html=True)
    if selected_day=='Thursday': st.markdown('<div class="danger">🦵 Rehab rule: no downward loading. Stop anything that causes knee pain.</div>', unsafe_allow_html=True)
    workout_date=st.date_input('Date', value=date.today())
    week_num=st.number_input('Week', min_value=1, max_value=52, value=int(profile.get('week',1)))
    rows=[]
    if day_df.empty:
        st.info('Recovery day: swim, bike, sauna, mobility, and recovery.')
    for i,row in day_df.iterrows():
        ex=row['exercise']; sets=int(row['target_sets']); target=str(row['target_reps']); start=float(row.get('starting_weight_lbs',0) or 0)
        pr=best_weight(log, ex)
        with st.container():
            st.markdown(f'<div class="exercise-focus"><div class="card-title">Exercise {i+1} of {len(day_df)}</div><h2>{ex}</h2><span class="badge">Target: {sets} × {target}</span><span class="badge badge-gold">PR: {pr:g} lbs</span>', unsafe_allow_html=True)
            pain=st.slider('Pain level 0-10', 0, 10, 0, key=f'pain_{i}')
            notes=st.text_input('Notes', key=f'notes_{i}', placeholder='felt good, too heavy, knee okay')
            for s in range(1,sets+1):
                lw, lr=last_values(log, ex, s, start, 0)
                a,b,c=st.columns([1,1,1])
                w=a.number_input(f'Set {s} lbs', min_value=0.0, value=float(lw), step=2.5, key=f'w_{i}_{s}')
                r=b.number_input(f'Set {s} reps', min_value=0, value=int(lr), step=1, key=f'r_{i}_{s}')
                c.markdown(f'<div class="control-label">Volume</div><div class="big-number">{w*r:,.0f}</div>', unsafe_allow_html=True)
                if r>0:
                    rows.append({'date':str(workout_date),'saved_at':datetime.now().isoformat(timespec='seconds'),'week':int(week_num),'block':int(profile.get('block',1)),'day':selected_day,'workout':workout_name,'muscle_group':muscle,'exercise':ex,'set_number':s,'weight_lbs':w,'reps':r,'pain':pain,'notes':notes,'volume':w*r})
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="success">', unsafe_allow_html=True)
    if st.button('💾 Save Workout'):
        if rows:
            append_log(rows); st.success(f'Saved {len(rows)} sets. Great job.'); st.balloons()
        else: st.warning('Enter reps for at least one set before saving.')
    st.markdown('</div>', unsafe_allow_html=True)

elif nav == 'Weekly Plan':
    st.markdown('<div class="hero"><h1>Weekly Plan</h1><p>Days, muscle groups, and exercise count.</p></div>', unsafe_allow_html=True)
    for day in DAY_ORDER:
        w,m,n=day_summary(workouts, day)
        st.markdown(f'<div class="card"><div class="card-title">{day} — {m}</div><span class="badge">{w}</span><span class="badge badge-green">{n} exercises</span></div>', unsafe_allow_html=True)
        if n:
            st.dataframe(workouts[workouts['day']==day][['exercise','target_sets','target_reps','starting_weight_lbs']], use_container_width=True, hide_index=True)

elif nav == 'Progress':
    st.markdown('<div class="hero"><h1>Progress Analytics</h1><p>Investor-style performance dashboard.</p></div>', unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    c1.metric('Sessions', sessions(log)); c2.metric('Total Volume', f'{total_volume(log):,.0f} lbs'); c3.metric('Avg Knee Pain', f'{avg_pain(log):.1f}/10')
    if log.empty:
        st.info('No saved workouts yet.')
    else:
        daily=log.groupby('date',as_index=False)['volume'].sum()
        import plotly.express as px
        st.plotly_chart(px.line(daily,x='date',y='volume',title='Training Volume by Day'), use_container_width=True)
        best=log.groupby('exercise',as_index=False).agg(best_weight=('weight_lbs','max'),total_volume=('volume','sum')).sort_values('total_volume', ascending=False)
        st.dataframe(best, use_container_width=True, hide_index=True)
        st.download_button('Download Workout Log', log.to_csv(index=False), 'workout_log.csv')

elif nav == 'Adaptive Blocks':
    st.markdown('<div class="hero"><h1>Adaptive Training Blocks</h1><p>Rotate exercises every 4 weeks while keeping the same muscle groups.</p></div>', unsafe_allow_html=True)
    blocks=pd.read_csv('data/block_templates.csv')
    block_choice=st.selectbox('Training block', sorted(blocks['block'].unique()))
    bdf=blocks[blocks['block']==block_choice]
    st.markdown(f'<div class="card"><div class="card-title">Block {block_choice}</div><span class="badge badge-gold">Weeks {bdf.week_start.min()}-{bdf.week_end.max()}</span><span class="badge">LA Fitness exercise rotation</span></div>', unsafe_allow_html=True)
    for day in DAY_ORDER:
        d=bdf[bdf['day']==day]
        if not d.empty:
            st.markdown(f'### {day} — {d.muscle_group.iloc[0]}')
            st.dataframe(d[['exercise_order','exercise']], hide_index=True, use_container_width=True)

elif nav == 'Settings':
    st.markdown('<div class="hero"><h1>Settings</h1><p>Profile and monthly scoreboard.</p></div>', unsafe_allow_html=True)
    profile['current_weight']=st.number_input('Current Weight', value=float(profile.get('current_weight',0)), step=.5)
    profile['goal_weight']=st.number_input('Goal Weight', value=float(profile.get('goal_weight',0)), step=.5)
    profile['week']=st.number_input('Week #', min_value=1, max_value=52, value=int(profile.get('week',1)))
    profile['block']=st.number_input('Training Block', min_value=1, max_value=12, value=int(profile.get('block',1)))
    profile['swims']=st.number_input('Swims Completed', min_value=0, value=int(profile.get('swims',0)))
    profile['bike_miles']=st.number_input('Bike Miles', min_value=0.0, value=float(profile.get('bike_miles',0)), step=.5)
    profile['protein_days']=st.number_input('Protein Goal Days', min_value=0, max_value=31, value=int(profile.get('protein_days',0)))
    if st.button('Save Settings'):
        save_profile(profile); st.success('Settings saved.')
