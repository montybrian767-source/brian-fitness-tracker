# Brian Fitness Tracker 2.0 Beta 1.1 — Image Wiring Fix

This build fixes the exercise image system.

## What changed
- Adds real image files into `assets/exercises/`
- Adds `data/exercise_image_map.csv`
- Updates `data/workouts.csv` with image filenames
- Adds an **Image Test** page so you can verify which images are found
- App no longer depends on `.svg` filenames only; it checks `.png`, `.svg`, `.jpg`, `.jpeg`, `.webp`
- Keeps workout history saved to `data/workout_log.csv`

## Install
Upload all files/folders inside this folder to GitHub, then Streamlit > Manage app > Reboot/Redeploy.

Important: if you already have workout history, do not overwrite your existing `data/workout_log.csv` with an empty file.
