# Brian Fitness Tracker 2.0 Alpha 3

Commercial UI foundation with workout intelligence.

## What's new in Alpha 3

- Progress Analytics page
- Coach Preview page
- Comeback Score
- Personal Records table
- Volume by day chart
- Volume by muscle group chart
- Improved rest timer workflow
- Keeps saving completed sets to `data/workout_log.csv`

## Run locally

Double-click `run_app.bat` or run:

```bash
python -m streamlit run app.py
```

## GitHub / Streamlit Cloud

Upload the contents of this folder to your existing GitHub repo. Do not upload the ZIP itself.

Protect your workout history: do not overwrite `data/workout_log.csv` if you already have saved workouts.
