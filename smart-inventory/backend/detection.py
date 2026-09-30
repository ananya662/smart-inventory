"""Deterministic detection engine (pandas). The LLM only EXPLAINS; numbers come from here."""
import math
import pandas as pd

REQUIRED = ["date", "product_id", "product_name", "units_sold", "price", "stock_on_hand"]
RECENT, BASE, LEAD = 14, 42, 5  # days: recent window, baseline window, restock lead time


def load(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}. Required: {REQUIRED}")
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    if "category" not in df.columns:
        df["category"] = "General"
    df = df.sort_values(["product_id", "date"]).reset_index(drop=True)
    df["row_id"] = df.index + 2  # matches spreadsheet row number (header = row 1)
    return df


def _confidence(n_days, z, consistency):
    volume = min(n_days / 90, 1)
    strength = min(abs(z) / 4, 1)
    score = 0.3 * volume + 0.4 * strength + 0.3 * consistency
    return round(score, 2), {"data_volume": round(volume, 2), "trend_strength": round(strength, 2),
                             "consistency": round(consistency, 2)}


def analyze(df: pd.DataFrame) -> list[dict]:
    insights = []
    for pid, g in df.groupby("product_id"):
        g = g.sort_values("date")
        if len(g) < RECENT + 14:
            continue
        rec, base = g.tail(RECENT), g.iloc[-(RECENT + BASE):-RECENT]
        name, price = g["product_name"].iloc[-1], float(g["price"].iloc[-1])
        stock = int(g["stock_on_hand"].iloc[-1])
        r_avg, b_avg = rec.units_sold.mean(), base.units_sold.mean()
        b_std = max(base.units_sold.std(ddof=0), 0.5)
        z = (r_avg - b_avg) / (b_std / math.sqrt(RECENT))
        ratio = r_avg / b_avg if b_avg else 1
        days_left = stock / r_avg if r_avg > 0.05 else 999
        side = (rec.units_sold > b_avg) if r_avg >= b_avg else (rec.units_sold < b_avg)
        consistency = float(side.mean())
        n = len(g)
        rows_rec = rec.row_id.tolist()
        last_row = int(g.row_id.iloc[-1])

        def add(kind, sev, headline, action, impact, conf_z, rows, metrics):
            conf, parts = _confidence(n, conf_z, consistency)
            insights.append(dict(
                id=f"{pid}-{kind}", product_id=pid, product=name, category=g["category"].iloc[-1],
                type=kind, severity=sev, headline=headline, recommended_action=action,
                impact_inr=int(max(impact, 0)), confidence=conf, confidence_breakdown=parts,
                trace={"rows": rows, "from": str(rec.date.min().date()), "to": str(rec.date.max().date())},
                metrics=metrics))

        m = dict(recent_avg_daily=round(r_avg, 1), baseline_avg_daily=round(b_avg, 1),
                 change_pct=round((ratio - 1) * 100), stock=stock,
                 days_of_stock=round(days_left, 1) if days_left < 999 else None, price=price)

        if stock == 0 or days_left <= 7:
            need = math.ceil(max(r_avg * (LEAD + 14) - stock, 0))
            at_risk = max(0, r_avg * 7 - stock) * price
            add("low_stock", "high" if days_left <= LEAD else "medium",
                f"{name} will run out in {days_left:.0f} days" if stock else f"{name} is OUT OF STOCK",
                f"Order {need} units now (covers {LEAD}-day lead time + 14 days of demand).",
                at_risk, max(z, 3) if stock == 0 else 2.5, [last_row] + rows_rec[-3:], m)
        if ratio >= 1.5 and z >= 3:
            add("spike", "medium", f"{name} demand up {m['change_pct']}% in {RECENT} days",
                f"Raise stock cover to {math.ceil(r_avg * 21)} units and consider a small price increase.",
                (r_avg - b_avg) * 14 * price, z, rows_rec, m)
        supply_limited = stock == 0 or days_left <= 7  # sales fell because we ran out, not demand
        if ratio <= 0.6 and z <= -3 and not supply_limited:
            add("drop", "medium", f"{name} sales down {abs(m['change_pct'])}% in {RECENT} days",
                "Run a 10% promotion for 2 weeks and pause reordering until sales recover.",
                (b_avg - r_avg) * 14 * price, z, rows_rec, m)
        r30, hist = g.tail(30).units_sold.mean(), g.iloc[:-30].units_sold.mean()
        dl30 = stock / r30 if r30 > 0.05 else 999
        if dl30 > 60 and r30 < 0.5 * hist and stock > 50:
            add("dead_stock", "medium", f"{name}: {stock} units, ~{min(dl30, 999):.0f} days of stock",
                "Bundle or discount 20% to clear stock; do not reorder.",
                stock * price * 0.7, max(abs(z), 3.5), g.tail(30).row_id.tolist(),
                {**m, "days_of_stock": round(min(dl30, 999), 1), "recent_avg_daily": round(r30, 1),
                 "baseline_avg_daily": round(hist, 1), "change_pct": round((r30 / hist - 1) * 100)})

    for i in insights:
        i["priority"] = round(i["impact_inr"] * i["confidence"])
    return sorted(insights, key=lambda x: x["priority"], reverse=True)


def kpis(df: pd.DataFrame, insights: list[dict]) -> dict:
    last30 = df[df.date > df.date.max() - pd.Timedelta(days=30)]
    return dict(products=int(df.product_id.nunique()),
                revenue_30d=int((last30.units_sold * last30.price).sum()),
                insights=len(insights), at_risk_inr=int(sum(i["impact_inr"] for i in insights)),
                high_severity=sum(i["severity"] == "high" for i in insights))


def simulate(df, product_id, price_change_pct=0.0, extra_stock=0, elasticity=-1.2, horizon=30):
    g = df[df.product_id == product_id].sort_values("date")
    if g.empty:
        raise ValueError("Unknown product_id")
    r_avg = g.tail(RECENT).units_sold.mean()
    price, stock = float(g.price.iloc[-1]), int(g.stock_on_hand.iloc[-1])
    new_price = price * (1 + price_change_pct / 100)
    new_demand = max(r_avg * (1 + elasticity * price_change_pct / 100), 0)
    avail = stock + extra_stock

    def project(demand, p, av):
        units = min(demand * horizon, av)
        return dict(daily_demand=round(demand, 1), price=round(p, 2), units_sold=round(units),
                    revenue=round(units * p), stockout_day=round(av / demand) if demand and av / demand < horizon else None)
    return dict(product=g.product_name.iloc[-1], horizon_days=horizon, elasticity_assumed=elasticity,
                current=project(r_avg, price, stock), projected=project(new_demand, new_price, avail))
