# Brian Fitness Tracker Cloud v11

This version is built for gym use from any network.

## Local use
1. Unzip the folder.
2. Double-click `run_app.bat`.

## Online use from the gym
Deploy the folder to Streamlit Community Cloud, Render, or another host.

### Recommended: Streamlit Cloud
Upload these files to GitHub:
- `app.py`
- `workouts.csv`
- `requirements.txt`
- `.streamlit/secrets.toml.example` only as an example, do not upload real private keys publicly.

Then deploy with main file:
`app.py`

## Saving workouts online
The app works locally with `workout_log.csv`.
For real cloud saving, add Google Sheets secrets in Streamlit Cloud.

1. Create a Google Sheet named `Brian Fitness Tracker Cloud`.
2. Add tabs named `workout_log` and `profile`.
3. Create a Google Cloud service account.
4. Share the Google Sheet with the service account email.
5. Add secrets in Streamlit Cloud using `.streamlit/secrets.toml.example` as the template.

When secrets are found, the app automatically uses Google Sheets.
When secrets are missing, it uses local CSV mode.
