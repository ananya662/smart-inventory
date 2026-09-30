# Bahi — Smart Inventory & Sales Decision Engine

AI-powered inventory insights for small retail shops: spike/drop/dead-stock/low-stock
detection (deterministic, pandas), Claude-generated plain-language explanations with a
rule-based fallback, full row-level traceability, a what-if price/stock simulator, and
human-approval workflow with an audit log.

## Run locally (no Node.js needed)

**Backend**
```
cd backend
pip install -r requirements.txt
python generate_data.py        # builds sample_sales.csv (optional, a copy is included)
python evaluate.py             # accuracy vs planted ground truth
copy .env.example .env         # Windows; use `cp` on Mac/Linux
# put your ANTHROPIC_API_KEY in .env
uvicorn main:app --reload
```
Backend runs at http://localhost:8000 (Swagger docs at /docs).

**Frontend**
Just double-click `frontend/index.html` (or right-click → Open with → Chrome). No
install, no build step. It talks to the backend at localhost:8000.

## Architecture
```
CSV upload → pandas detection engine (numbers, always deterministic)
           → Claude (explains + answers questions, never invents numbers)
           → dashboard (insights, trace, simulator, approve/reject, audit)
```

## Project structure
```
backend/
  generate_data.py   synthetic dataset with 9 planted scenarios
  detection.py        spike/drop/dead-stock/low-stock detection + confidence + $ impact
  llm.py              Claude explanations + "ask your data" chat, with safe fallback
  main.py              FastAPI app
  evaluate.py          accuracy check vs ground_truth.json
frontend/
  index.html           single-file dashboard (vanilla JS, no build step)
```
