import io, json, os
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import detection as det
import llm

load_dotenv()

app = FastAPI(title="Smart Inventory & Sales Decision Engine")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

STATE = {"df": None, "insights": []}
APPROVALS_FILE = "approvals.json"
APPROVALS = json.load(open(APPROVALS_FILE)) if os.path.exists(APPROVALS_FILE) else {}


def _set(df_raw):
    df = det.load(df_raw)
    STATE["df"], STATE["insights"] = df, det.analyze(df)


if os.path.exists("sample_sales.csv"):
    _set(pd.read_csv("sample_sales.csv"))


def _need_data():
    if STATE["df"] is None:
        raise HTTPException(400, "No data loaded. POST a CSV to /upload first.")


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        _set(pd.read_csv(io.BytesIO(await file.read())))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"rows": len(STATE["df"]), "insights": len(STATE["insights"])}


@app.get("/insights")
def insights():
    _need_data()
    out = [{**i, "status": APPROVALS.get(i["id"], {}).get("status", "pending")} for i in STATE["insights"]]
    return {"kpis": det.kpis(STATE["df"], STATE["insights"]), "insights": out}


@app.get("/trace/{insight_id}")
def trace(insight_id: str):
    """Return the exact source rows behind an insight."""
    _need_data()
    ins = next((i for i in STATE["insights"] if i["id"] == insight_id), None)
    if not ins:
        raise HTTPException(404, "Insight not found")
    rows = STATE["df"][STATE["df"].row_id.isin(ins["trace"]["rows"])]
    return {"insight": ins["headline"], "rows": json.loads(rows.assign(date=rows.date.dt.date.astype(str)).to_json(orient="records"))}


@app.get("/products/{product_id}/history")
def history(product_id: str, days: int = 90):
    _need_data()
    g = STATE["df"][STATE["df"].product_id == product_id].tail(days)
    return json.loads(g.assign(date=g.date.dt.date.astype(str))[["date", "units_sold", "stock_on_hand", "price"]].to_json(orient="records"))


class SimReq(BaseModel):
    product_id: str
    price_change_pct: float = 0
    extra_stock: int = 0


@app.post("/simulate")
def simulate(r: SimReq):
    _need_data()
    try:
        return det.simulate(STATE["df"], r.product_id, r.price_change_pct, r.extra_stock)
    except ValueError as e:
        raise HTTPException(404, str(e))


class ApproveReq(BaseModel):
    insight_id: str
    decision: str  # approved | rejected


@app.post("/approve")
def approve(r: ApproveReq):
    if r.decision not in ("approved", "rejected"):
        raise HTTPException(400, "decision must be approved or rejected")
    from datetime import datetime
    APPROVALS[r.insight_id] = {"status": r.decision, "at": datetime.now().isoformat(timespec="seconds")}
    json.dump(APPROVALS, open(APPROVALS_FILE, "w"), indent=2)
    return APPROVALS[r.insight_id]


@app.get("/audit")
def audit():
    return APPROVALS


@app.get("/explain/{insight_id}")
def explain(insight_id: str):
    _need_data()
    ins = next((i for i in STATE["insights"] if i["id"] == insight_id), None)
    if not ins:
        raise HTTPException(404, "Insight not found")
    return llm.explain_insight(ins)


class AskReq(BaseModel):
    question: str


@app.post("/ask")
def ask(r: AskReq):
    _need_data()
    return llm.answer_question(r.question, det.kpis(STATE["df"], STATE["insights"]), STATE["insights"])


@app.get("/health")
def health():
    return {"status": "ok", "data_loaded": STATE["df"] is not None,
             "ai_enabled": bool(os.environ.get("ANTHROPIC_API_KEY"))}
