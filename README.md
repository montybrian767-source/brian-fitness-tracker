# Brian Exercise Image Database v1

This is the database structure for the exercise image library.

## Files

- `data/exercise_image_database.csv` — master list of exercises and expected image filenames.
- `data/exercise_image_aliases.csv` — maps your current workout exercise names to the image library.
- `data/exercise_image_database.sqlite` — same data in SQLite database format.
- `assets/exercises/` — put the real image files here.

## Required image folder

Your GitHub repo should contain:

```text
assets/
  exercises/
    shoulder_press_machine.jpg
    machine_lateral_raise.jpg
    wide_grip_lat_pulldown.jpg
    ...
```

## Important

This database does not contain the real image files yet. It tells the app what filenames to look for.
Once you generate or crop the real exercise images, place them inside `assets/exercises/` using the exact filenames.
