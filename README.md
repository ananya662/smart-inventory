# Smart Inventory & Sales Decision Engine

AI Build Challenge 2026 | Problem Statement: PS-04

## Problem
Small shop owners spend hours on spreadsheets and still lose money through stock-outs and dead stock. They need fast, trustworthy decisions, not raw data.

## Solution
Upload a sales CSV and get ranked, explainable inventory decisions in seconds. A deterministic pandas engine does the detection, so the numbers are reliable. Nothing auto-executes: the owner approves every action.

## Key Features
- Detects demand spikes, sales drops, low stock, stock-outs and dead stock
- Each insight has a recommended action, estimated ₹ impact and a confidence score
- Traceability: every insight links to the exact source rows and dates
- What-if simulator: change price/quantity and see projected revenue and stock-out date
- Human-in-the-loop approval with an audit log
- Evaluation script that compares detections with ground truth

## Architecture
CSV upload -> FastAPI backend (pandas detection engine) -> insights, confidence and ₹ impact -> web dashboard (trace, what-if, approve/reject) -> audit log

## Tech Stack
Python, FastAPI, pandas, HTML/JS frontend, Render (backend), Netlify (frontend)

## API Endpoints
`/upload`, `/insights`, `/trace/{id}`, `/products/{id}/history`, `/simulate`, `/approve`, `/audit`

## Evaluation Results
| Metric | Result |
|---|---|
| Planted scenarios detected | 9 / 9 |
| Recall | 100% |
| Precision | 100% |
| Time to insight | 0.05 sec |

## Run Locally
```bash
cd backend
pip install -r requirements.txt
python generate_data.py
python evaluate.py
uvicorn main:app --reload
```
Open http://localhost:8000/docs to try every endpoint.

## Live Links
- Live app: https://cool-sprite-22c120.netlify.app
- Backend API docs: https://smart-inventory-yxra.onrender.com/docs


## Author
Ananya Patel
