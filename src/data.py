"""
BOX 1 — DATA  (Reality -> Data)

Real retail scanner data. 131,706 line items, 64,682 baskets, 5,242 SKUs,
22,625 customers, 187 categories, one full year (Jan-Dec 2016).

THREE THINGS THIS FILE ESTABLISHES, ALL OF THEM LOAD-BEARING
=============================================================

1) THERE IS NO COST DATA. NONE.
   The dataset has exactly seven columns: Date, Customer_ID, Transaction_ID,
   SKU_Category, SKU, Quantity, Sales_Amount. No COGS, no wholesale price, no
   margin, not even a hint. So gross margin becomes an ASSUMED, ADJUSTABLE input
   (see optimize.py) — the load-bearing number a real brand supplies from its own
   P&L, exactly like the save rate in the churn project.

   WHY THIS DOESN'T INVALIDATE THE PROJECT — and this matters:
       The ELASTICITY is real. It comes from observed demand responding to
       observed price changes. So the DIRECTION of every recommendation
       ("raise this price 6%") is real.
       The MARGIN only SCALES the profit figure. "That's worth £42k" inherits
       the assumption; "raise the price" does not.
   State it, don't bury it.

2) PRICE MUST BE DERIVED — AND THAT IS DANGEROUS.
       unit_price = Sales_Amount / Quantity
   We then want to regress Quantity on price. But Quantity is in the denominator
   of price. **Quantity appears on both sides of the equation.** Any noise in
   Sales_Amount produces a MECHANICAL negative correlation between price and
   quantity — a fake elasticity conjured out of arithmetic. This is called
   division bias, and it is the single easiest way to ship a confident, wrong
   pricing model.

   How bad is it here? 78% of rows have Quantity == 1, where unit_price is just
   Sales_Amount and no division happens at all. The bias only bites on the
   remaining 22%.

   THE FIX: aggregate to a SKU-WEEK panel.
       price this week = MEDIAN unit price across that week's transactions
       units this week = TOTAL quantity sold
   Now price and quantity are computed from different statistics of a set of
   transactions, not from the same single row. It doesn't eliminate the bias, but
   it stops it being mechanical. We say so in the README rather than pretending.

3) MOST SKUs CANNOT YIELD AN ELASTICITY AT ALL.
   You cannot learn how demand responds to price from a product whose price never
   moved. 43% of SKUs have exactly ONE observed price. 56% have fewer than 10
   observations. This is the eligibility filter of this project — the same role
   the "active in 12 months" rule played in the churn build.

TRANSFERS: engine -> customer -> SKU. The skeleton is identical; only the nouns
and the failure modes change.
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

# ---- Eligibility thresholds (the decision, in one place) --------------------
MIN_WEEKS = 8          # need enough weeks to see a demand curve
MIN_DISTINCT_PRICES = 3  # need real price movement, not one price forever
MIN_PRICE_CV = 0.02    # and the movement must be more than rounding noise


def load_raw() -> pd.DataFrame:
    csv = RAW / "scanner_data.csv"
    if not csv.exists():
        raise FileNotFoundError(
            f"Missing {csv}\n"
            "Download 'Retail Store Sales Transactions (Scanner Data)' from Kaggle:\n"
            "  https://www.kaggle.com/datasets/marian447/retail-store-sales-transactions\n"
            "unzip it, and place scanner_data.csv in data/raw/."
        )
    df = pd.read_csv(csv)
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Derive unit price. Drop the impossible rows."""
    d = df[(df["Quantity"] > 0) & (df["Sales_Amount"] > 0)].copy()
    d["unit_price"] = d["Sales_Amount"] / d["Quantity"]
    # a handful of extreme unit prices are data errors, not products
    lo, hi = d["unit_price"].quantile([0.001, 0.999])
    d = d[(d["unit_price"] >= lo) & (d["unit_price"] <= hi)]
    d["week"] = d["Date"].dt.to_period("W").dt.start_time
    return d.reset_index(drop=True)


def build_panel(d: pd.DataFrame) -> pd.DataFrame:
    """
    The SKU-WEEK panel. This is the unit of analysis for the whole project.

    price  = median unit price observed that week   (a "list price" for the week)
    units  = total quantity sold that week          (the demand response)

    Computing price as a median across transactions and units as a sum breaks the
    mechanical link that would exist if we used a single transaction's ratio.
    """
    panel = (d.groupby(["SKU", "SKU_Category", "week"], as_index=False)
               .agg(price=("unit_price", "median"),
                    units=("Quantity", "sum"),
                    revenue=("Sales_Amount", "sum"),
                    txns=("Quantity", "size")))
    return panel


def sku_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """One row per SKU: how much price variation do we actually have to learn from?"""
    g = panel.groupby(["SKU", "SKU_Category"])
    s = g.agg(weeks=("week", "nunique"),
              distinct_prices=("price", "nunique"),
              price_mean=("price", "mean"),
              price_std=("price", "std"),
              price_min=("price", "min"),
              price_max=("price", "max"),
              units=("units", "sum"),
              revenue=("revenue", "sum")).reset_index()
    s["price_std"] = s["price_std"].fillna(0.0)
    s["price_cv"] = s["price_std"] / s["price_mean"].clip(lower=0.01)
    s["price_swing_pct"] = (s["price_max"] / s["price_min"].clip(lower=0.01) - 1) * 100
    s["eligible"] = ((s["weeks"] >= MIN_WEEKS) &
                     (s["distinct_prices"] >= MIN_DISTINCT_PRICES) &
                     (s["price_cv"] >= MIN_PRICE_CV))
    return s


def load_all():
    raw = load_raw()
    d = clean(raw)
    panel = build_panel(d)
    summary = sku_summary(panel)
    return raw, d, panel, summary


if __name__ == "__main__":
    raw, d, panel, s = load_all()

    print("=" * 78)
    print("THE DATA")
    print("=" * 78)
    print(f"  line items       {len(raw):,}")
    print(f"  baskets          {raw.Transaction_ID.nunique():,}")
    print(f"  SKUs             {raw.SKU.nunique():,}")
    print(f"  categories       {raw.SKU_Category.nunique():,}")
    print(f"  customers        {raw.Customer_ID.nunique():,}")
    print(f"  span             {raw.Date.min().date()} -> {raw.Date.max().date()}")
    print(f"  total revenue    {raw.Sales_Amount.sum():,.0f}")

    print("\n" + "=" * 78)
    print("COST / COGS SITUATION")
    print("=" * 78)
    cost_cols = [c for c in raw.columns
                 if any(k in c.lower() for k in
                        ("cost", "cogs", "margin", "wholesale", "purchase", "supplier"))]
    print(f"  columns present: {list(raw.columns)}")
    print(f"  cost/COGS/margin fields: {cost_cols if cost_cols else 'NONE — there are none'}")
    print("  => gross margin must be an ASSUMED, ADJUSTABLE input.")
    print("     Elasticity (and therefore the DIRECTION of every price move) stays real.")
    print("     Only the absolute profit figure inherits the assumption.")

    print("\n" + "=" * 78)
    print("PRICE VARIATION — which SKUs can even yield an elasticity?")
    print("=" * 78)
    print(f"  SKUs total                        {len(s):,}")
    print(f"  ...with ONE price ever             {(s.distinct_prices == 1).sum():,}"
          f"  ({(s.distinct_prices == 1).mean()*100:.0f}%)  <- elasticity IMPOSSIBLE")
    print(f"  ...with < {MIN_WEEKS} weeks of sales        {(s.weeks < MIN_WEEKS).sum():,}"
          f"  ({(s.weeks < MIN_WEEKS).mean()*100:.0f}%)  <- too thin to fit a curve")
    print(f"\n  ELIGIBLE (>= {MIN_WEEKS} weeks, >= {MIN_DISTINCT_PRICES} prices, "
          f"CV >= {MIN_PRICE_CV:.0%}):  {s.eligible.sum():,} SKUs")
    print(f"  they carry {s.loc[s.eligible,'revenue'].sum()/s.revenue.sum()*100:.1f}% of revenue")
    print(f"  their median price swing (max/min): "
          f"{s.loc[s.eligible,'price_swing_pct'].median():.0f}%")

    print("\n  sample of eligible SKUs:")
    ex = (s[s.eligible].nlargest(6, "revenue")
          [["SKU", "SKU_Category", "weeks", "distinct_prices",
            "price_min", "price_mean", "price_max", "price_cv", "revenue"]])
    print(ex.round(2).to_string(index=False))
