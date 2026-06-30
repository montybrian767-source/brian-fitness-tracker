# Brian Fitness Tracker Pro v15 — Cloud Save Edition

This version keeps the v14 professional structure and adds optional Google Sheets cloud saving so you can use the app from your phone at the gym through Streamlit Cloud.

## Run locally

Double-click `run_app.bat`, or run:

```bash
python -m streamlit run app.py
```

## Upload to GitHub

Upload the full project, including these folders and files:

- `app.py`
- `requirements.txt`
- `README.md`
- `.gitignore`
- `.streamlit/secrets.toml.example`
- `assets/`
- `data/`
- `utils/`
- `pages/`

## Streamlit Cloud

Main file path:

```text
app.py
```

## Cloud saving

Without secrets, the app uses local CSV saving.

With Google Sheets secrets added in Streamlit Cloud, it saves to Google Sheets:

- `workout_log` worksheet
- `profile` worksheet

Use `.streamlit/secrets.toml.example` as the template for Streamlit Cloud secrets.

## Important

Create a Google Sheet named exactly what you put in `gsheet_name`, then share that Google Sheet with your Google service account email.
