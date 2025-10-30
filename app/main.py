
from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path

from .domain import (
    Rounding, OptionRow, HedgeInputs,
    compute_rows, export_payload, run_self_tests, INDEXES
)

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"

app = FastAPI(title="Hedge Calculator API", version="1.0.0")

# CORS (relaxed for local/demo). Tighten in production as needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static assets
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

class OptionRowModel(BaseModel):
    expiry: str
    offerPts: float

class HedgeInputsModel(BaseModel):
    index: str = Field(..., description="FTSE100 | ES | SPX | Custom")
    notional: float
    marketPrice: float
    strike: float
    multiplier: float
    feePerContract: float
    rounding: Rounding
    options: List[OptionRowModel]
    currency: str = Field(..., pattern=r"^[£$]$")

class ExportRequest(BaseModel):
    inputs: HedgeInputsModel
    notes: Optional[str] = ""

@app.get("/")
async def root():
    index_path = FRONTEND_DIR / "index.html"
    return FileResponse(index_path)

@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.get("/indexes")
async def indexes():
    return INDEXES

@app.post("/calc")
async def calc(payload: HedgeInputsModel):
    inp = HedgeInputs(**payload.model_dump())
    return compute_rows(inp)

@app.post("/export")
async def export(payload: ExportRequest):
    inp = HedgeInputs(**payload.inputs.model_dump())
    return export_payload(inp, notes=payload.notes or "")

@app.get("/selftest")
async def selftest():
    return run_self_tests()
