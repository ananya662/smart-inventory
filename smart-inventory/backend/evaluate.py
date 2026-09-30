"""Evaluation vs planted ground truth. Run: python evaluate.py"""
import json, time, pandas as pd
import detection as det

truth = json.load(open("ground_truth.json"))
t0 = time.time()
df = det.load(pd.read_csv("sample_sales.csv"))
ins = det.analyze(df)
elapsed = time.time() - t0
found = {(i["product_id"], i["type"]) for i in ins}
alias = {"stockout": "low_stock"}
tp = sum((t["product_id"], alias.get(t["expected"], t["expected"])) in found for t in truth)
expected = {(t["product_id"], alias.get(t["expected"], t["expected"])) for t in truth}
fp = [i for i in ins if (i["product_id"], i["type"]) not in expected]
print(f"Planted scenarios: {len(truth)} | detected: {tp} | recall: {tp/len(truth):.0%}")
print(f"Flagged total: {len(ins)} | false positives: {len(fp)} | precision: {(len(ins)-len(fp))/max(len(ins),1):.0%}")
print(f"Time-to-insight: {elapsed:.2f}s")
for t in truth:
    ok = (t["product_id"], alias.get(t["expected"], t["expected"])) in found
    print(("  OK   " if ok else "  MISS ") + f"{t['product']} -> {t['expected']}")
for i in fp: print("  FALSE+", i["product"], i["type"])
