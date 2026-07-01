# Brian Fitness Tracker v14.5 — Production Data Upgrade

This version fixes the data foundation.

## Important data separation

- `data/workouts.csv` = workout plan / template
- `data/workout_log.csv` = completed workout history
- `data/profile.csv` = current weight, goal weight, week number
- `data/personal_records.csv` = best lifts
- `data/backups/` = automatic workout history backups

## How to run locally

Double-click:

```bat
run_app.bat
```

or run:

```bash
python -m streamlit run app.py
```

## GitHub / Streamlit Cloud

Upload the full project structure to GitHub:

```text
app.py
requirements.txt
README.md
run_app.bat
assets/styles.css
data/workouts.csv
data/workout_log.csv
data/profile.csv
data/personal_records.csv
```

Do not delete `data/workout_log.csv` after you start saving workouts.
