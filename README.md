
# Downside Hedge Calculator — Python-First (single "/" route)

This version minimizes custom JavaScript:
- All calculations (premiums, quantities, costs) are in Python.
- The "auto-fill" premium is computed server-side via htmx-driven POST refreshes.
- Chart is generated in Python with `plotly` and embedded as HTML (loads Plotly from CDN).
- UI updates use **htmx** attributes; endpoints are consolidated into a single path: **"/"**.
  - `POST /` with `action=rows` (default): recompute premiums and re-render the options table
  - `POST /` with `action=add_row` / `remove_row`
  - `POST /` with `action=calculate`: compute quantities/costs and return results + chart

## Run locally
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
# open http://127.0.0.1:8000/
```

## Azure
Set the runtime to Python 3.11+ and start with:
```
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Notes
- Quantities are **notional** hedges (not delta).
- Options table uses server-side recalculation on input changes (`keyup changed delay:300ms` via htmx) to autofill premiums.
- Only put purchasing is modelled.
- To switch to fully offline Plotly (no CDN), change `include_plotlyjs="cdn"` to `True` in `figure_html()`.
