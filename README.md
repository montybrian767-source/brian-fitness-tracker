# Brian Fitness Tracker 2.0 Beta 1

Beta 1 is the first daily-use stability build.

## Added in Beta 1
- Cleaner phone-focused Gym Mode
- Weekly Plan page
- Workout Complete summary page
- Automatic workout_log backup before saving
- Export latest workout
- Keeps Alpha 3 analytics, coach preview, exercise cards, and image system

## Data safety
Your completed workouts save to:

`data/workout_log.csv`

Backups are created in:

`data/backups/`

Do not delete or overwrite `data/workout_log.csv` when updating.

## Run locally
Double-click `run_app.bat` or run:

```bash
python -m streamlit run app.py
```

## GitHub / Streamlit
Upload everything inside this folder to your GitHub repo, then reboot/redeploy Streamlit.
