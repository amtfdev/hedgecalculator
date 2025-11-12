
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Any
import plotly.graph_objects as go
import datetime as dt

app = FastAPI(title="Downside Hedge Calculator")

if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

def _to_float(x, default=0.0):
    try:
        if x in ("", None):
            return default
        return float(x)
    except Exception:
        return default

def parse_options(form: Any) -> List[Dict[str, Any]]:
    exp = form.getlist("expiry[]")
    strike = form.getlist("strike[]")
    ask = form.getlist("ask[]")
    fee_lot = form.getlist("fee_lot[]")
    options: List[Dict[str, Any]] = []
    n = max(len(exp), len(strike), len(ask), len(fee_lot))
    for i in range(n):
        e = exp[i] if i < len(exp) else ""
        k = _to_float(strike[i]) if i < len(strike) else 0.0
        a = _to_float(ask[i]) if i < len(ask) else 0.0
        f = _to_float(fee_lot[i]) if i < len(fee_lot) else 0.0
        options.append({"expiry": e, "strike": k, "ask": a, "fee_lot": f})
    return options

def _parse_expiry(exp_str: str):
    try:
        return dt.datetime.fromisoformat(exp_str).date()
    except Exception:
        try:
            return dt.datetime.strptime(exp_str, "%Y-%m-%d").date()
        except Exception:
            return None

def calc_solutions(inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    notional = _to_float(inputs.get("notional"))
    spot = _to_float(inputs.get("spot"))
    multiplier = _to_float(inputs.get("multiplier"))
    for o in inputs["options"]:
        if not o.get("expiry") or not _to_float(o.get("strike")):
            continue
        strike = _to_float(o["strike"])
        ask = _to_float(o["ask"])
        fee_lot = _to_float(o["fee_lot"])
        premium_contract = (ask * multiplier) if multiplier else 0.0
        per_contract_notional = strike * multiplier if multiplier else 0.0
        qty100 = (notional / per_contract_notional) if per_contract_notional else 0.0
        cost100 = qty100 * (premium_contract + fee_lot)
        atmPct = ((strike - spot) / spot * 100) if spot else 0.0
        out.append({
            "expiry": o["expiry"],
            "strike": strike,
            "ask": _to_float(o.get("ask")),
            "premium": premium_contract,
            "per_contract_notional": per_contract_notional,
            "qty100": qty100,
            "qty100_floor": int(qty100 // 1),
            "qty100_ceil": int(qty100) + (0 if abs(qty100 - int(qty100)) < 1e-9 else 1),
            "cost100": cost100,
            "atmPct": atmPct,
        })
    out.sort(key=lambda x: x["expiry"])
    return out

def figure_html(inputs: Dict[str, Any], solutions: List[Dict[str, Any]]) -> str:
    fig = go.Figure()
    if solutions:
        x_start = dt.date.today()
        x = [d for d in (_parse_expiry(s["expiry"]) for s in solutions)]
        x_end = max(x + [x_start])
        y = [s["strike"] for s in solutions]
        spot = _to_float(inputs.get("spot"))
        if y:
            y_min_strike = min(y)
            lower_pad = max(1.0, 0.01 * y_min_strike)
            upper_pad = max(1.0, 0.01 * (spot if spot else y_min_strike))
            if spot:
                y_min = y_min_strike - lower_pad
                y_max = spot + upper_pad
                if y_max <= y_min:
                    y_max = max(y) + upper_pad
            else:
                y_min = y_min_strike - lower_pad
                y_max = max(y) + upper_pad
            fig.update_yaxes(range=[y_min, y_max])
        if x:
            fig.add_trace(go.Scatter(x=[x[0], x[-1]], y=[spot, spot], mode="lines", name="Spot", hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="markers+text", name="Strikes",
            text=[f"{s['strike']:.0f}" for s in solutions], textposition="top center",
            hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>"
        ))
        for s in solutions:
            fig.add_shape(type="line", x0=s["expiry"], x1=s["expiry"],
                          y0=min([spot] + y) * 0.8 if y else 0,
                          y1=max([spot] + y) * 1.2 if y else 1,
                          line=dict(dash="dot", width=1))
            fig.add_annotation(x=s["expiry"], y=s["strike"],
                               text=f"{s['strike']:.0f} ({s['atmPct']:+.2f}%)",
                               showarrow=True, arrowhead=2, ax=0, ay=-30, font=dict(size=11))
    fig.update_layout(
        xaxis_title="Expiry", yaxis_title="Price",
        hovermode="closest",
        margin=dict(l=60, r=20, t=10, b=50),
        paper_bgcolor="white", plot_bgcolor="white",
    )
    return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displaylogo": False, "responsive": True})

def ctx_defaults():
    return {"currency": "", "index": "", "multiplier": "", "notional": "", "spot": "", "options": []}

def render_rows(request: Request, ctx: Dict[str, Any]):
    return templates.TemplateResponse("_options_rows.html", {"request": request, **ctx})

def render_results(request, inputs, solutions):
    chart_html = figure_html(inputs, solutions)
    return templates.TemplateResponse(
        "_results.html",
        {
            "request": request,
            "inputs": inputs,   # keep nested for future-proofing
            **inputs,           # <-- add this line to expose currency/notional/spot/etc. at top level
            "solutions": solutions,
            "chart_html": chart_html,
        },
    )

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    ctx = ctx_defaults()
    return templates.TemplateResponse("index.html", {"request": request, **ctx})

@app.post("/", response_class=HTMLResponse)
async def post_index(request: Request):
    form = await request.form()
    action = form.get("action", "rows")
    ctx = {
        "currency": form.get("currency", ""),
        "index": form.get("index", ""),
        "multiplier": form.get("multiplier", ""),
        "notional": form.get("notional", ""),
        "spot": form.get("spot", ""),
        "options": parse_options(form)
    }

    if action == "add_row":
        ctx["options"].append({"expiry": "", "strike": 0.0, "ask": 0.0, "fee_lot": 0.0})
        return render_rows(request, ctx)

    if action == "remove_row":
        idx_raw = form.get("row_index", "")
        try:
            idx = int(idx_raw)
            if 0 <= idx < len(ctx["options"]):
                ctx["options"].pop(idx)
        except Exception:
            pass
        return render_rows(request, ctx)

    if action == "calculate":
        solutions = calc_solutions(ctx)
        return render_results(request, ctx, solutions)

    return render_rows(request, ctx)
