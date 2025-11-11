
# Downside Hedge Calculator (FastAPI)

Single-page web app to model protective put hedges for an index exposure.
- One route: `/`.
- Add any number of put option candidates (expiry, strike, ask).
- Premium is auto-filled as `ask × multiplier`.
- Click **Calculate** to see quantity needed for 100% / 50% / 10% coverage and total cost.
- Interactive Plotly chart shows time on the x‑axis and price on the y‑axis with vertical expiry markers and strike labels with the % from spot.
- **Reset** restores a clean starting state and repopulates example rows.

## Run locally

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
# Open http://127.0.0.1:8000/
```

## Azure App Service

Use either **Procfile** (included) or configure the startup command to:
```
uvicorn main:app --host 0.0.0.0 --port 8000
```
Ensure `requirements.txt` is deployed. The app is static and requires only outbound internet to load Plotly from a CDN.

## Notes & Assumptions

- Quantities target a *notional hedge* (not delta): `Qty(100%) = Notional / (Strike × Multiplier)`.
  - Also shown: `ceil` and `floor` integer contract counts.
- Costs use premium-per-contract = `ask × multiplier` (currency).
- **% from spot** = `(strike − spot) / spot`.
- Only buying puts is modeled.
- Edge cases to be aware of:
  - Very deep OTM strikes produce large decimal quantities; use ceil/floor guidance.
  - Near‑dated expiries may under‑hedge tail moves; costs can read low vs realized protection.
  - Stale/bad ask quotes will misstate premium/costs.
  - A different exchange multiplier will change premiums & quantities immediately.
  - Chart axis is autoscaled; manually widen with more rows if labels overlap.
```

