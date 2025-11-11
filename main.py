
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Any
import plotly.graph_objects as go

app = FastAPI(title="Downside Hedge Calculator")
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
    options: List[Dict[str, Any]] = []
    n = max(len(exp), len(strike), len(ask))
    for i in range(n):
        e = exp[i] if i < len(exp) else ""
        k = _to_float(strike[i]) if i < len(strike) else 0.0
        a = _to_float(ask[i]) if i < len(ask) else 0.0
        options.append({"expiry": e, "strike": k, "ask": a})
    return options

def compute_premiums(options: List[Dict[str, Any]], multiplier: float) -> None:
    for o in options:
        o["premium"] = round((_to_float(o.get("ask")) * multiplier), 6) if multiplier else 0.0

def calc_solutions(inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    notional = _to_float(inputs.get("notional"))
    spot = _to_float(inputs.get("spot"))
    multiplier = _to_float(inputs.get("multiplier"))
    for o in inputs["options"]:
        if not o.get("expiry") or not _to_float(o.get("strike")):
            continue
        strike = _to_float(o["strike"])
        premium = _to_float(o.get("premium"))
        per_contract_notional = strike * multiplier if multiplier else 0.0
        qty100 = (notional / per_contract_notional) if per_contract_notional else 0.0
        qty50 = qty100 * 0.5
        qty10 = qty100 * 0.1
        cost100 = premium * qty100
        cost50 = premium * qty50
        cost10 = premium * qty10
        atmPct = ((strike - spot) / spot * 100) if spot else 0.0
        out.append({
            "expiry": o["expiry"],
            "strike": strike,
            "ask": _to_float(o.get("ask")),
            "premium": premium,
            "per_contract_notional": per_contract_notional,
            "qty100": qty100, "qty50": qty50, "qty10": qty10,
            "qty100_floor": int(qty100 // 1),
            "qty100_ceil": int(qty100) + (0 if abs(qty100 - int(qty100)) < 1e-9 else 1),
            "cost100": cost100, "cost50": cost50, "cost10": cost10,
            "atmPct": atmPct,
        })
    out.sort(key=lambda x: x["expiry"])
    return out

def figure_html(inputs: Dict[str, Any], solutions: List[Dict[str, Any]]) -> str:
    fig = go.Figure()
    if solutions:
        x = [s["expiry"] for s in solutions]
        y = [s["strike"] for s in solutions]
        spot = _to_float(inputs.get("spot"))
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
        xaxis_title="Expiry", yaxis_title="Index Level",
        hovermode="closest",
        margin=dict(l=60, r=20, t=10, b=50),
        paper_bgcolor="white", plot_bgcolor="white",
    )
    return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displaylogo": False, "responsive": True})

def ctx_defaults():
    return {"currency": "", "index": "", "multiplier": "", "notional": "", "spot": "", "options": []}

def render_rows(request: Request, ctx: Dict[str, Any]):
    return templates.TemplateResponse("_options_rows.html", {"request": request, **ctx})

def render_results(request: Request, ctx: Dict[str, Any], solutions):
    chart_html = figure_html(ctx, solutions)
    return templates.TemplateResponse("_results.html", {"request": request, "inputs": ctx, "solutions": solutions, "chart_html": chart_html})

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
    compute_premiums(ctx["options"], _to_float(ctx["multiplier"]))

    if action == "add_row":
        ctx["options"].append({"expiry": "", "strike": 0.0, "ask": 0.0, "premium": 0.0})
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
