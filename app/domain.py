
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any

class Rounding(str, Enum):
    round = "round"
    ceil = "ceil"
    floor = "floor"

def apply_rounding(v: float, mode: Rounding) -> int:
    """Apply rounding mode to a float and return an int."""
    if v is None or v != v:  # NaN
        return 0
    if mode == Rounding.ceil:
        from math import ceil
        return int(ceil(v))
    if mode == Rounding.floor:
        from math import floor
        return int(floor(v))
    return int(round(v))

def compute_contracts(notional: float, price: float, multiplier: float, rounding: Rounding) -> Dict[str, float]:
    """Compute raw and rounded number of contracts."""
    n = float(notional) if isinstance(notional, (int, float)) else 0.0
    p = float(price) if isinstance(price, (int, float)) and price > 0 else float("nan")
    m = float(multiplier) if isinstance(multiplier, (int, float)) and multiplier > 0 else float("nan")
    base = (n / (p * m)) if (p == p and m == m) else float("nan")
    raw = base if base == base else 0.0
    rounded = apply_rounding(base, rounding) if base == base else 0
    return {"raw": raw, "rounded": rounded}

@dataclass
class OptionRow:
    expiry: str
    offerPts: float

@dataclass
class HedgeInputs:
    index: str  # "FTSE100" | "ES" | "SPX" | "Custom"
    notional: float
    marketPrice: float
    strike: float
    multiplier: float
    feePerContract: float
    rounding: Rounding
    options: List[OptionRow]
    currency: str  # "£" | "$"

INDEXES: Dict[str, Dict[str, Any]] = {
    "FTSE100": {"name": "FTSE 100 (ICE)", "multiplier": 10, "currency": "£"},
    "ES": {"name": "S&P 500 E-mini (CME)", "multiplier": 50, "currency": "$"},
    "SPX": {"name": "S&P 500 (SPX options)", "multiplier": 100, "currency": "$"},
    "Custom": {"name": "Custom Index", "multiplier": 1, "currency": "£"},
}

def compute_rows(inputs: HedgeInputs) -> Dict[str, Any]:
    ctr = compute_contracts(inputs.notional, inputs.marketPrice, inputs.multiplier, inputs.rounding)
    rows: List[Dict[str, Any]] = []
    for r in inputs.options:
        offer = float(r.offerPts)
        premium_per_contract = offer * inputs.multiplier
        total_cost = (premium_per_contract + inputs.feePerContract) * ctr["rounded"]
        breakeven_price = (inputs.strike - inputs.feePerContract) - offer
        pct_move = ((breakeven_price - inputs.marketPrice) / inputs.marketPrice) if inputs.marketPrice else float("nan")
        cost_pct = (total_cost / inputs.notional) if inputs.notional else float("nan")
        rows.append({
            "expiry": r.expiry,
            "offerPts": offer,
            "premiumPerContract": premium_per_contract,
            "totalCost": total_cost,
            "breakevenPrice": breakeven_price,
            "pctMove": pct_move,
            "costPct": cost_pct,
        })
    return {
        "summary": {
            "contracts": ctr["rounded"],
            "notionalCovered": ctr["rounded"] * inputs.marketPrice * inputs.multiplier,
        },
        "rows": rows,
    }

def export_payload(inputs: HedgeInputs, notes: str = "") -> Dict[str, Any]:
    calc = compute_rows(inputs)
    from datetime import datetime, timezone
    return {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "index": inputs.index,
        "indexName": INDEXES.get(inputs.index, {}).get("name", inputs.index),
        "currency": inputs.currency,
        "inputs": {
            "notional": inputs.notional,
            "marketPrice": inputs.marketPrice,
            "strike": inputs.strike,
            "multiplier": inputs.multiplier,
            "feePerContract": inputs.feePerContract,
            "rounding": inputs.rounding.value,
        },
        "summary": calc["summary"],
        "rows": calc["rows"],
        "notes": notes,
    }

def approx(a: float, b: float, tol: float = 1e-9) -> bool:
    import math
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)

def run_self_tests() -> Dict[str, Any]:
    results: List[str] = []
    ok = True

    # Contracts test (2,000,000 / (9,400 * 10))
    c = compute_contracts(2_000_000, 9400, 10, Rounding.round)
    ok &= approx(c["raw"], 2_000_000 / (9400 * 10))
    ok &= (c["rounded"] == 21)
    results.append(f"contracts raw={c['raw']:.6f} rounded={c['rounded']}")

    # Row calc test (parity with sheet example)
    inputs = HedgeInputs(
        index="FTSE100",
        notional=2_000_000,
        marketPrice=9400,
        strike=9000,
        multiplier=10,
        feePerContract=10,
        rounding=Rounding.round,
        options=[OptionRow(expiry="2025-12", offerPts=163.5)],
        currency="£",
    )
    result = compute_rows(inputs)
    row = result["rows"][0]
    ok &= approx(row["premiumPerContract"], 163.5 * 10)
    ok &= approx(row["totalCost"], (1635 + 10) * 21)
    ok &= approx(row["breakevenPrice"], (9000 - 10) - 163.5)
    ok &= approx(row["pctMove"], ((9000 - 10 - 163.5) - 9400) / 9400)
    ok &= approx(row["costPct"], 34545 / 2_000_000)
    results.append("row calc tests ok")

    # Extra rounding tests
    ok &= (apply_rounding(21.2, Rounding.ceil) == 22)
    ok &= (apply_rounding(21.8, Rounding.floor) == 21)
    results.append("rounding mode tests ok")

    # NaN/zero guards
    c2 = compute_contracts(1_000_000, float("nan"), 10, Rounding.round)
    ok &= approx(c2["raw"], 0.0) and c2["rounded"] == 0
    results.append("nan price contracts ok")

    # Custom index path + different rounding
    custom_inputs = HedgeInputs(
        index="Custom",
        notional=1_500_000,
        marketPrice=500.0,
        strike=480.0,
        multiplier=25.0,
        feePerContract=5.0,
        rounding=Rounding.ceil,
        options=[OptionRow(expiry="2026-03", offerPts=12.5)],
        currency="£",
    )
    r2 = compute_rows(custom_inputs)
    ok &= r2["summary"]["contracts"] == apply_rounding(1_500_000 / (500 * 25), Rounding.ceil)
    results.append("custom index + ceil rounding ok")

    # Export invariants
    payload = export_payload(inputs, notes="note")
    ok &= payload["summary"]["contracts"] == 21
    ok &= len(payload["rows"]) == 1
    ok &= payload["inputs"]["notional"] == 2_000_000
    ok &= payload["notes"] == "note"
    results.append("export payload tests ok")

    return {"ok": bool(ok), "results": results}

if __name__ == "__main__":
    import json
    print(json.dumps(run_self_tests(), indent=2))
