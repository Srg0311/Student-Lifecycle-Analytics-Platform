# Streamlit Analytics Dashboard

This folder contains the interactive dashboard for the Student Lifecycle Analytics Platform.

## Contents
- `app.py`: Streamlit application connecting to PostgreSQL (with fallback to local CSVs if the database is offline).
- `styles.css`: Dashboard CSS stylesheet.

## Running the Application
From the repository root directory, run:
```bash
python -m streamlit run app/app.py
```
Open `http://localhost:8501` in your browser.
