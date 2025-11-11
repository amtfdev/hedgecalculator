
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Any
from datetime import date
import plotly.graph_objects as go

app = FastAPI(title="Downside Hedge Calculator (Python-First)")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def parse_options(form: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Expect arrays named expiry[], strike[], ask[]
    exp = form.getlist("expiry[]")
    strike = form.getlist("strike[]")
    ask = form.getlist("ask[]")
    options = []
    for i in range(max(len(exp), len(strike), len(ask))):
        try:
            e = exp[i]
        except IndexError:
            e = ""
        try:
            k = float(strike[i]) if strike[i] not in ("", None) else 0.0
        except (IndexError, ValueError):
            k = 0.0
        try:
            a = float(ask[i]) if ask[i] not in ("", None) else 0.0
        except (IndexError, ValueError):
            a = 0.0
        if e and k > 0:
            options.append({"expiry": e, "strike": k, "ask": a})
        else:
            # keep partially filled rows too (for editing)
            options.append({"expiry": e or "", "strike": k, "ask": a})
    return options

def compute_premiums(options: List[Dict[str, Any]], multiplier: float) -> None:
    for o in options:
        o["premium"] = round((o.get("ask") or 0.0) * (multiplier or 0.0), 6)

def calc_solutions(inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    res = []
    notional = float(inputs.get("notional") or 0.0)
    spot = float(inputs.get("spot") or 0.0)
    multiplier = float(inputs.get("multiplier") or 0.0)

    for o in inputs["options"]:
        if not o.get("expiry") or not o.get("strike"):
            continue
        per_contract_notional = o["strike"] * multiplier if multiplier else 0.0
        qty100 = (notional / per_contract_notional) if per_contract_notional else 0.0
        qty50 = qty100 * 0.5
        qty10 = qty100 * 0.1
        cost100 = o["premium"] * qty100
        cost50 = o["premium"] * qty50
        cost10 = o["premium"] * qty10
        atmPct = ((o["strike"] - spot) / spot * 100) if spot else 0.0
        res.append({
            **o,
            "per_contract_notional": per_contract_notional,
            "qty100": qty100, "qty50": qty50, "qty10": qty10,
            "qty100_floor": int(qty100 // 1),
            "qty100_ceil": int(qty100) + (0 if abs(qty100 - int(qty100)) < 1e-9 else 1),
            "cost100": cost100, "cost50": cost50, "cost10": cost10,
            "atmPct": atmPct
        })
    res.sort(key=lambda x: x["expiry"])
    return res

def figure_html(inputs: Dict[str, Any], solutions: List[Dict[str, Any]]) -> str:
    if not solutions:
        fig = go.Figure()
        fig.update_layout(
            xaxis_title="Expiry", yaxis_title="Index Level",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=60, r=20, t=10, b=50),
        )
        return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displaylogo": False, "responsive": True})
    x = [s["expiry"] for s in solutions]
    y = [s["strike"] for s in solutions]
    spot = float(inputs.get("spot") or 0.0)

    fig = go.Figure()

    # Spot line
    fig.add_trace(go.Scatter(
        x=[x[0], x[-1]], y=[spot, spot], mode="lines", name="Spot",
        hoverinfo="skip"
    ))

    # Strike markers
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="markers+text", name="Strikes",
        text=[f"{s['strike']:.0f}" for s in solutions],
        textposition="top center",
        hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>"
    ))

    # Expiry verticals
    for s in solutions:
        fig.add_shape(
            type="line",
            x0=s["expiry"], x1=s["expiry"],
            y0=min([spot] + y) * 0.8 if y else 0,
            y1=max([spot] + y) * 1.2 if y else 1,
            line=dict(dash="dot", width=1)
        )
        fig.add_annotation(
            x=s["expiry"], y=s["strike"],
            text=f"{s['strike']:.0f} ({s['atmPct']:+.2f}%)",
            showarrow=True, arrowhead=2, ax=0, ay=-30, font=dict(size=11)
        )

    fig.update_layout(
        xaxis_title="Expiry", yaxis_title="Index Level",
        hovermode="closest",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=60, r=20, t=10, b=50),
    )
    return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displaylogo": False, "responsive": True})

def render_options_rows(request: Request, inputs: Dict[str, Any]):
    return templates.TemplateResponse("_options_rows.html", {"request": request, **inputs})

def render_results(request: Request, inputs: Dict[str, Any], solutions: List[Dict[str, Any]]):
    chart_html = figure_html(inputs, solutions)
    return templates.TemplateResponse("_results.html", {"request": request, "inputs": inputs, "solutions": solutions, "chart_html": chart_html})

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    # Seed with 3 example rows
    defaults = {
        "currency": "£", "index": "FTSE 100",
        "multiplier": 10, "notional": 100000, "spot": 9500,
        "options": [
            {"expiry": date.today().isoformat(), "strike": 9000.0, "ask": 20.0},
            {"expiry": (date.today().replace(day=min(28, date.today().day)) ).isoformat(), "strike": 9200.0, "ask": 60.0},
            {"expiry": (date.today().replace(day=min(28, date.today().day)) ).isoformat(), "strike": 9300.0, "ask": 90.0},
        ]
    }
    compute_premiums(defaults["options"], defaults["multiplier"])
    return templates.TemplateResponse("index.html", {"request": request, **defaults})

@app.post("/", response_class=HTMLResponse)
async def post_index(request: Request):
    form = await request.form()
    action = form.get("action", "rows")
    inputs = {
        "currency": form.get("currency") or "£",
        "index": form.get("index") or "",
        "multiplier": float(form.get("multiplier") or 0.0),
        "notional": float(form.get("notional") or 0.0),
        "spot": float(form.get("spot") or 0.0),
        "options": parse_options(form),
    }
    compute_premiums(inputs["options"], inputs["multiplier"])

    if action == "add_row":
        inputs["options"].append({"expiry": "", "strike": 0.0, "ask": 0.0, "premium": 0.0})
        return render_options_rows(request, inputs)

    if action == "remove_row":
        idx = int(form.get("row_index") or -1)
        if 0 <= idx < len(inputs["options"]):
            inputs["options"].pop(idx)
        return render_options_rows(request, inputs)

    if action == "calculate":
        solutions = calc_solutions(inputs)
        return render_results(request, inputs, solutions)

    # action == "rows": recompute premiums / refresh the table
    return render_options_rows(request, inputs)
