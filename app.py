
from __future__ import annotations
import base64, json, os, re, shutil, zipfile
from datetime import date, datetime
from pathlib import Path
import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).parent
DATA = APP_DIR / "data"
ASSETS = APP_DIR / "assets"
EXDIR = ASSETS / "exercises"
LOG = DATA / "workout_log.csv"
WORKOUTS = DATA / "workouts.csv"
BACKUPS = DATA / "backups"
for p in [DATA, EXDIR, BACKUPS]: p.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Brian Fitness Tracker v15.3", page_icon="🏋️", layout="wide", initial_sidebar_state="expanded")
css_path = ASSETS / "styles.css"
if css_path.exists(): st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

LOG_COLS=['date','saved_at','week','day','workout','exercise','set_number','weight_lbs','reps','pain','notes','volume']
DAYS=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

def slug(s): return re.sub(r'[^a-z0-9]+','_',str(s).lower()).strip('_')
def read_workouts():
    df=pd.read_csv(WORKOUTS)
    df.columns=[c.strip().lower() for c in df.columns]
    if 'day' not in df.columns:
        df['day']='Monday'
    if 'workout' not in df.columns:
        df['workout']=df.get('muscle_group','Workout')
    return df

def read_log():
    if LOG.exists():
        try:
            df=pd.read_csv(LOG)
            for c in LOG_COLS:
                if c not in df.columns: df[c]=None
            return df[LOG_COLS]
        except Exception: pass
    df=pd.DataFrame(columns=LOG_COLS); df.to_csv(LOG,index=False); return df

def save_log(df):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(LOG,index=False)
    try:
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        shutil.copy2(LOG, BACKUPS / f'workout_log_backup_{stamp}.csv')
    except Exception: pass

def img_src(ex):
    # Robust image loader: never crash if an image/folder is missing on GitHub/Streamlit.
    fallback_svg = """<svg xmlns='http://www.w3.org/2000/svg' width='320' height='220' viewBox='0 0 320 220'>
      <rect width='320' height='220' rx='22' fill='#eef6ff'/>
      <circle cx='160' cy='68' r='24' fill='#0f5df4' opacity='.18'/>
      <path d='M72 130h176M98 105v50M222 105v50' stroke='#0b1f3f' stroke-width='10' stroke-linecap='round'/>
      <path d='M135 135c18 20 32 20 50 0' stroke='#0f5df4' stroke-width='8' stroke-linecap='round' fill='none'/>
      <text x='160' y='190' text-anchor='middle' font-family='Arial' font-size='20' font-weight='800' fill='#0b1f3f'>Exercise Image</text>
    </svg>"""
    try:
        p = EXDIR / f"{slug(ex)}.svg"
        if not p.exists():
            p = EXDIR / 'muscle_groups.svg'
        if p.exists():
            data = base64.b64encode(p.read_bytes()).decode()
        else:
            data = base64.b64encode(fallback_svg.encode('utf-8')).decode()
    except Exception:
        data = base64.b64encode(fallback_svg.encode('utf-8')).decode()
    return f"data:image/svg+xml;base64,{data}"

def last_note(df, ex):
    if df.empty: return ''
    x=df[df.exercise==ex]
    if x.empty: return ''
    return str(x.iloc[-1].get('notes','') or '')

def last_values(log, ex, sets, default):
    vals=[]
    for s in range(1,int(sets)+1):
        lw=default; lr=0
        if not log.empty:
            x=log[(log.exercise==ex)&(log.set_number==s)]
            if not x.empty:
                r=x.iloc[-1]; lw=float(r.weight_lbs or default); lr=int(r.reps or 0)
        vals.append((lw,lr))
    return vals

workouts=read_workouts(); log=read_log()

with st.sidebar:
    st.markdown("""
    <div style='font-size:28px;font-weight:950;margin:22px 0 0'>🏋️ BRIAN</div>
    <div style='font-size:17px;font-weight:900;margin-bottom:18px'>FITNESS TRACKER</div>
    <div style='display:inline-block;color:#51a7ff!important;border:1px solid rgba(81,167,255,.35);border-radius:999px;padding:7px 12px;font-weight:900;margin-bottom:20px'>v15.3 Pixel Style UI</div>
    <div style='font-weight:900;margin:18px 0 8px;color:#b9c7d8!important'>NAVIGATION</div>
    """, unsafe_allow_html=True)
    page=st.radio("",["Dashboard","Today's Workout","Weekly Plan","Exercise Library","Progress","History","Data Safety","Profile","Phone Setup"], index=1, label_visibility="collapsed")
    st.markdown("""
    <div class='data-box'><div style='font-weight:900;color:#b9c7d8!important;margin-bottom:12px'>DATA STATUS</div><div style='display:flex;gap:12px;align-items:center'><div style='background:#16a34a;border-radius:50%;width:32px;height:32px;text-align:center;line-height:32px'>✓</div><div><b>All data is safe</b><br><span style='color:#c7d4e3!important'>workout_log.csv</span></div></div><div style='margin-top:22px;border:1px solid rgba(255,255,255,.14);border-radius:12px;padding:12px'><b>☁ EXPORT BACKUP</b><br><span style='color:#c7d4e3!important'>Download your data</span></div></div>
    """, unsafe_allow_html=True)

def sidebar_cards(total_ex, total_sets, total_vol):
    muscle_img = img_src('muscle_groups')
    st.markdown(f"""
    <div class='side-card'><div class='side-title'>Workout Summary</div>
      <div class='summary-row'><span>Exercises</span><span>{total_ex}</span></div>
      <div class='summary-row'><span>Total Sets</span><span>{total_sets}</span></div>
      <div class='summary-row'><span>Total Volume</span><span style='color:#078a34'>{total_vol:,.0f} lbs</span></div>
      <div class='summary-row'><span>Workout Time</span><span>—</span></div>
      <div class='summary-row'><span>Calories (Est.)</span><span>—</span></div>
    </div>
    <div class='side-card'><div class='side-title'>Muscle Groups</div><img src='{muscle_img}' style='width:100%;border-radius:12px'></div>
    <div class='side-card'><div class='side-title'>Quick Actions</div><div class='action'>＋ ADD EXERCISE</div><div class='action'>↕ REORDER EXERCISES</div><div class='action danger'>🗑 CLEAR WORKOUT</div></div>
    <div class='side-card'><div class='side-title'>Tips</div><p style='color:#263a58;font-weight:700'>Focus on controlled movements and mind-muscle connection for best results.</p></div>
    """, unsafe_allow_html=True)

def page_workout():
    selected=st.selectbox('Workout Day', DAYS, index=DAYS.index(date.today().strftime('%A')) if date.today().strftime('%A') in DAYS else 1, label_visibility='collapsed')
    day_df=workouts[workouts.day.astype(str).str.lower()==selected.lower()].reset_index(drop=True)
    if day_df.empty:
        st.warning('No workout found for this day.'); return
    workout=day_df.workout.iloc[0]
    st.markdown(f"""
    <div class='header'><div><div class='title'>{selected} — {workout} ✎</div><div style='margin-top:10px'><span class='pill'>{workout}</span><span class='pill green'>{len(day_df)} exercises</span></div></div><div class='finish'>✓ FINISH WORKOUT</div></div>
    """, unsafe_allow_html=True)
    c1,c2,c3=st.columns([1,1,1.35])
    with c1: wdate=st.date_input('Date', value=date.today())
    with c2: week=st.number_input('Week', min_value=1, max_value=52, value=1, step=1)
    total_sets=int(pd.to_numeric(day_df.target_sets,errors='coerce').fillna(0).sum())
    with c3: st.markdown(f"<div class='statcard'><div class='label'>EXERCISE TOTAL VOLUME</div><div class='greenbig'>Auto Calculate</div></div>", unsafe_allow_html=True)
    st.markdown('<div class="layout"><div>', unsafe_allow_html=True)
    new_rows=[]; total_vol=0
    for idx,row in day_df.iterrows():
        ex=str(row.exercise); sets=int(row.target_sets); reps_target=str(row.target_reps); default=float(row.starting_weight_lbs or 0)
        vals=last_values(log, ex, sets, default)
        form_key=f"form_{selected}_{idx}_{ex}"
        st.markdown(f"""
        <div class='exercise-card'><div class='exercise-grid'>
        <div><img class='ex-img' src='{img_src(ex)}'></div><div><div class='how'>▷ HOW TO DO IT</div><div class='ex-title'>{idx+1}. {ex}</div><span class='pill'>Target: {sets} x {reps_target}</span><span class='pill green'>{workout}</span><div style='color:#53647d;font-weight:800;margin-top:10px'>{row.get('notes','')}</div>
        """, unsafe_allow_html=True)
        with st.form(form_key):
            # make compact grid with actual inputs
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            cols=st.columns([.55,1,1,.9,1.2,1])
            cols[0].markdown('**SET**'); cols[1].markdown('**WEIGHT (LBS)**'); cols[2].markdown('**REPS**'); cols[3].markdown('**RPE (0-10)**'); cols[4].markdown('**NOTES**'); cols[5].markdown('**VOLUME**')
            ex_vol=0; submitted=False
            for s,(lw,lr) in enumerate(vals, start=1):
                cols=st.columns([.55,1,1,.9,1.2,1])
                cols[0].markdown(f"<span class='setnum'>{s}</span>", unsafe_allow_html=True)
                weight=cols[1].number_input('w', value=float(lw), step=2.5, key=f'w_{idx}_{s}', label_visibility='collapsed')
                reps=cols[2].number_input('r', value=int(lr if lr>0 else 12 if str(reps_target).isdigit() else 0), step=1, min_value=0, key=f'r_{idx}_{s}', label_visibility='collapsed')
                pain=cols[3].number_input('p', value=0, min_value=0, max_value=10, step=1, key=f'p_{idx}_{s}', label_visibility='collapsed')
                note=cols[4].text_input('n', value='felt good' if s==1 else '', key=f'n_{idx}_{s}', label_visibility='collapsed')
                vol=weight*reps; ex_vol += vol
                cols[5].markdown(f"<span class='vol'>{vol:,.0f} lbs</span>", unsafe_allow_html=True)
                if reps>0:
                    new_rows.append({'date':str(wdate),'saved_at':datetime.now().isoformat(timespec='seconds'),'week':int(week),'day':selected,'workout':workout,'exercise':ex,'set_number':s,'weight_lbs':weight,'reps':reps,'pain':pain,'notes':note,'volume':vol})
            total_vol+=ex_vol
            save=st.form_submit_button(f'💾 Save {ex}', use_container_width=True)
            if save:
                prior=read_log(); all_rows=[r for r in new_rows if r['exercise']==ex]
                save_log(pd.concat([prior,pd.DataFrame(all_rows)], ignore_index=True))
                st.success(f'Saved {ex}')
        st.markdown(f"<div style='clear:both'><span class='totalbox'>{ex_vol:,.0f} lbs</span></div></div></div></div>", unsafe_allow_html=True)
    st.markdown('</div><div>', unsafe_allow_html=True)
    sidebar_cards(len(day_df), total_sets, total_vol)
    st.markdown('</div></div>', unsafe_allow_html=True)

def dashboard():
    st.markdown("<div class='header'><div class='title'>Dashboard</div><div class='finish'>Start Today's Workout</div></div>", unsafe_allow_html=True)
    log=read_log(); total_vol=pd.to_numeric(log.volume,errors='coerce').fillna(0).sum() if not log.empty else 0
    c1,c2,c3=st.columns(3)
    c1.metric('Saved Workouts', log.date.nunique() if not log.empty else 0)
    c2.metric('Total Volume', f'{total_vol:,.0f} lbs')
    c3.metric('Current Version', 'v15.3')
    st.dataframe(workouts[['day','workout','exercise','target_sets','target_reps']], use_container_width=True)

def library():
    st.markdown("<div class='header'><div class='title'>Exercise Library</div></div>", unsafe_allow_html=True)
    cols=st.columns(3)
    for i,row in workouts.iterrows():
        with cols[i%3]:
            st.markdown(f"<div class='exercise-card'><img src='{img_src(row.exercise)}' style='width:100%;border-radius:12px'><h3>{row.exercise}</h3><b>{row.workout}</b><p>{row.day} · {row.target_sets} x {row.target_reps}</p></div>", unsafe_allow_html=True)

def safety():
    st.markdown("<div class='header'><div class='title'>Data Safety</div></div>", unsafe_allow_html=True)
    log=read_log(); st.success(f'Workout log: {LOG}')
    st.download_button('Download workout_log.csv', log.to_csv(index=False).encode(), 'workout_log.csv')
    zpath=DATA/'backup_export.zip'
    with zipfile.ZipFile(zpath,'w') as z:
        for f in DATA.glob('*.csv'): z.write(f, arcname=f.name)
    st.download_button('Download full data backup ZIP', zpath.read_bytes(), 'brian_fitness_data_backup.zip')

if page=="Today's Workout": page_workout()
elif page=="Dashboard": dashboard()
elif page=="Exercise Library": library()
elif page=="History": st.dataframe(read_log(), use_container_width=True)
elif page=="Data Safety": safety()
elif page=="Weekly Plan": st.dataframe(workouts.groupby(['day','workout']).exercise.count().reset_index(name='exercises'), use_container_width=True)
elif page=="Progress": dashboard()
elif page=="Phone Setup": st.info('Deploy on Streamlit Cloud, then open this app link on your phone and add it to your home screen.')
else: st.info('Coming next in this section.')
