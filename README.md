
# Hedge Calculator – FastAPI + Frontend

Self-contained hedging calculator with a minimal web UI and a JSON API.

- UI served at `/`
- API endpoints: `GET /healthz`, `POST /calc`, `POST /export`, `GET /selftest`, `GET /indexes`
- Pure-Python business logic; parity with the provided sheet/JS app
- One-command run with Uvicorn

## Quickstart

```bash
python -m venv .venv && . .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit http://127.0.0.1:8000/ to use the UI.

## API

- **GET `/healthz`** → `{"ok": true}`
- **GET `/indexes`** → supported index metadata (name, multiplier, currency)
- **POST `/calc`** → body = `HedgeInputsModel`, returns summary + per-expiry rows
- **POST `/export`** → body = `{ "inputs": HedgeInputsModel, "notes": str }` returns export payload
- **GET `/selftest`** → runs lightweight self-tests for invariants and sample cases

### HedgeInputsModel

```jsonc
{
  "index": "FTSE100",      // "FTSE100" | "ES" | "SPX" | "Custom"
  "notional": 2000000,
  "marketPrice": 9400,
  "strike": 9000,
  "multiplier": 10,
  "feePerContract": 10,
  "rounding": "round",     // "round" | "ceil" | "floor"
  "options": [{ "expiry": "2025-12", "offerPts": 163.5 }],
  "currency": "£"          // "£" or "$"
}
```

### Formulas

- **breakeven** = `(strike - feePerContract) - offerPts`
- **contracts(raw)** = `notional / (price * multiplier)`
- **contracts(rounded)** = `round/ceil/floor(raw)`

## Frontend

- Vanilla HTML + JS for speed and zero extra dependencies
- Add multiple expiries, calculate instantly, and export a JSON snapshot

## Deploy

Use any ASGI host (Uvicorn/Gunicorn+Uvicorn workers, ecs, etc.). For example:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Notes & Edge Cases

- If `marketPrice` or `multiplier` ≤ 0, contract count becomes 0 (NaN-guard).
- Rounding mode materially changes notional coverage; check `ceil` vs `floor`.
- `feePerContract` reduces breakeven and is applied per contract in total cost.
- Currency symbol is display-only; calculations are unitless.
- `offerPts` * multiplier = premium per contract.
- Export payload embeds an ISO UTC timestamp.

---

© 2025 Hedge Calculator Example
