
# Downside Hedge Calculator — Bulma + Python-first

- Styling: **Bulma** (CDN).
- No auto-populated inputs or option rows.
- Add/Delete rows fully server-driven via **htmx**.
- Premium auto-fills on the server as `ask × multiplier` on any change.
- Calculate posts to "/" and returns quantities/costs + Plotly chart.

## Run
```
pip install -r requirements.txt
uvicorn main:app --reload
# http://127.0.0.1:8000/
```

## Deploy (Azure)
- Startup: `uvicorn main:app --host 0.0.0.0 --port 8000`
- Ensure `SCM_DO_BUILD_DURING_DEPLOYMENT=true`
- Python 3.11 or 3.12
