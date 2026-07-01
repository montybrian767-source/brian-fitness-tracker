# Brian Fitness Tracker 2.0 Beta 3 — Exercise Image Library Engine

This build focuses on the image library foundation.

## New in Beta 3

- Real `assets/exercises/` folder with categorized image subfolders
- `data/exercise_image_map.csv` maps workout exercises to image files
- Image Manager page shows which images are connected or missing
- Image Test page shows all image files Streamlit can find
- Today’s Workout cards load images automatically
- Missing images do not crash the app
- Saves completed workouts to `data/workout_log.csv`
- Automatic backup before saving workout history

## Required GitHub structure

```text
app.py
requirements.txt
README.md
assets/
  exercises/
    shoulders/
    back/
    chest/
    arms/
    legs/
    abs/
data/
  workouts.csv
  workout_log.csv
  exercise_image_map.csv
```

## Install

Upload everything inside this folder to GitHub, then reboot/redeploy Streamlit.

Do not delete `data/workout_log.csv` if you already have workout history.
