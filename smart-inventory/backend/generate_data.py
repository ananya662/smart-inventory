"""Generate a synthetic retail dataset with PLANTED patterns + ground truth.
Run: python generate_data.py  ->  sample_sales.csv, ground_truth.json
"""
import json
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
DAYS = 180
end = pd.Timestamp("2026-09-27")
dates = pd.date_range(end - pd.Timedelta(days=DAYS - 1), end)

CATS = {"Grocery": ["Basmati Rice 5kg", "Atta 10kg", "Toor Dal 1kg", "Sunflower Oil 1L", "Sugar 1kg", "Tea 500g"],
        "Snacks": ["Namkeen 200g", "Biscuits Pack", "Chips Large", "Chocolate Bar", "Peanut Chikki"],
        "Beverages": ["Cold Drink 1.25L", "Packaged Juice 1L", "Energy Drink", "Mineral Water 1L", "Lassi 200ml"],
        "Household": ["Detergent 1kg", "Dishwash Liquid", "Floor Cleaner", "Toilet Cleaner", "Phenyl 1L"],
        "Personal Care": ["Shampoo 340ml", "Soap 4-Pack", "Toothpaste 200g", "Face Wash", "Hair Oil 200ml"],
        "Stationery": ["Notebook A4", "Ball Pens 10pk", "Geometry Box", "Glue Stick"]}

products = []
for cat, names in CATS.items():
    for n in names:
        products.append(dict(name=n, cat=cat, price=int(rng.integers(20, 450)),
                             base=float(rng.uniform(3, 18))))
for i, p in enumerate(products):
    p["id"] = f"P{i+1:03d}"

# planted scenarios: product name -> scenario
PLANT = {"Cold Drink 1.25L": "spike", "Notebook A4": "spike", "Energy Drink": "drop",
         "Hair Oil 200ml": "drop", "Peanut Chikki": "dead_stock", "Glue Stick": "dead_stock",
         "Basmati Rice 5kg": "low_stock", "Atta 10kg": "low_stock", "Mineral Water 1L": "stockout"}

rows, truth = [], []
for p in products:
    sc = PLANT.get(p["name"], "normal")
    stock = int(p["base"] * 25)
    for d_i, d in enumerate(dates):
        wk = 1.25 if d.dayofweek >= 5 else 1.0
        lam = p["base"] * wk
        last = DAYS - d_i  # days from end
        if sc == "spike" and last <= 10: lam *= 2.4
        if sc == "drop" and last <= 14: lam *= 0.35
        if sc == "dead_stock": lam = p["base"] * 0.08 if last <= 60 else lam
        units = int(min(rng.poisson(lam), stock))
        stock -= units
        # replenishment policy (skipped for planted stock problems near the end)
        restock_ok = not (sc in ("low_stock", "stockout") and last <= 25)
        if restock_ok and stock < p["base"] * 6:
            stock += int(p["base"] * 30)
        if sc == "dead_stock" and d_i == 100:
            stock += 400  # overbought
        if sc == "stockout" and last <= 3:
            stock = 0
        rows.append(dict(date=d.date().isoformat(), product_id=p["id"], product_name=p["name"],
                         category=p["cat"], units_sold=units, price=p["price"], stock_on_hand=stock))
    if sc != "normal":
        truth.append(dict(product_id=p["id"], product=p["name"], expected=sc))

pd.DataFrame(rows).to_csv("sample_sales.csv", index=False)
json.dump(truth, open("ground_truth.json", "w"), indent=2)
print(f"sample_sales.csv: {len(rows)} rows, {len(products)} products; planted {len(truth)} scenarios")
