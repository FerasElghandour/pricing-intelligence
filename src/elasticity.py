"""
BOX 2 — UNDERSTANDING: the demand curve, and why this data can't give us one

THE HEADLINE OF THIS ENTIRE PROJECT LIVES IN THIS FILE.

We tried to estimate price elasticity six ways. All six failed the industry
benchmark. This file estimates the best number available AND proves it cannot be
trusted for pricing decisions. Both halves matter — the second one is the finding.

WHAT HAS TO BE TRUE (the benchmark, so we're not marking our own homework)
--------------------------------------------------------------------------
    Bijmolt, Van Heerde & Pieters (2005), Journal of Marketing Research
    Meta-analysis of 1,851 price elasticities across 81 studies:  MEAN = -2.62
    Tellis (1988), earlier meta-analysis:                          MEAN = -1.76

    So a credible retail elasticity is:
      (a) NEGATIVE          — demand slopes down. Obviously.
      (b) magnitude 1 to 5  — centred near -2.6
      (c) |e| > 1           — LOAD-BEARING: with constant-elasticity demand the
                              profit-maximising price is cost * e/(e+1). If
                              |e| <= 1 that formula EXPLODES. The optimizer would
                              tell you to charge infinity for a tin of beans.

WHAT WE ACTUALLY GOT
--------------------
    median elasticity   -0.61      (benchmark -2.62)
    negative               62%     (should be ~100%)
    POSITIVE               38%     <-- customers "buying more when it costs more"
    |e| > 1                41%     (the rest would break the optimizer)

WHY — and this is the finding, not an excuse
--------------------------------------------
1) THE PRICE VARIATION IS CONFOUNDED. Measured in this data:
       prices are +6.5% HIGHER in the store's BUSIEST weeks.
       62% of SKUs have price positively correlated with store-wide traffic
       (random pricing would give ~50%).
   The store raised prices when demand was strong. So the data contains:
       the real effect     : higher price -> fewer sales   (negative)
       the confounder      : busy week    -> higher price AND more sales (positive)
   They cancel. We weren't measuring a weak demand curve — we were measuring a
   real one with a fake one stacked on top of it.

   This is the umbrella problem. Umbrella prices rise when it rains. Umbrella
   sales rise when it rains. The data says "high price -> high sales". The rain
   caused both, and "rain" is not a column in the spreadsheet.

2) THERE IS ALMOST NO DEMAND TO EXPLAIN.
       median units per SKU per week = 2
       67% of SKU-weeks sold <= 2 units
   Even a perfect price signal cannot be detected inside a number that flickers
   between 1 and 2. The noise is larger than the effect.

3) MEASUREMENT ERROR IN PRICE attenuates any coefficient toward zero.

THE BASELINE TEST THAT SETTLED IT (see baseline_test())
-------------------------------------------------------
Held out the last 12 weeks. Asked each model: given the price actually charged in
a week you never saw, predict the units that actually sold.

    B1  no price effect (e=0)          Poisson deviance 1.158
    B2  literature elasticity (-2.62)                   2.266   <- TWICE AS BAD
    B3  pooled from our data (-0.42)                    1.132   <- best, by a whisker
        per-SKU raw                                     1.153
        per-SKU Bayesian (prior -2.62)                  1.263   <- WORSE than doing nothing

Two lessons, both painful:
  * The literature mean is a real number that is WRONG FOR THIS STORE. Applying it
    made predictions twice as bad as assuming price doesn't matter at all.
  * The Bayesian approach we proposed FAILED. The baseline test caught it. This is
    exactly why you build the dumb baseline first — the same lesson as the LSTM
    losing to a random forest in the jet-engine project.

THE DISTINCTION THAT KILLS OBSERVATIONAL PRICING
------------------------------------------------
The out-of-sample test validates a PREDICTIVE coefficient:
    "when the store charged £7, how many sold?"
Pricing decisions need a CAUSAL coefficient:
    "if I CHANGE the price to £7, how many WILL sell?"

Confounding and attenuation break the causal reading while leaving the predictive
one intact. They are different parameters. This dataset can only give us the one
we don't need.

    => YOU CANNOT LEARN A TRUSTWORTHY PRICE ELASTICITY FROM OBSERVATIONAL DATA.
       YOU HAVE TO RUN EXPERIMENTS.

That is not a limitation of this dataset. It is the normal condition of nearly
every business that has never deliberately tested a price — which is most of them.
And it is why Box 4 (the closed loop) is not a bonus feature. It is the answer.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from data import load_all

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
REPORTS = ROOT / "reports"
ART.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)

# ---- The benchmark we hold ourselves to ------------------------------------
BENCH_MEAN = -2.62      # Bijmolt, Van Heerde & Pieters (2005), JMR
BENCH_TELLIS = -1.76    # Tellis (1988)

# ---- Eligibility: which SKUs have enough sales AND price movement -----------
MIN_WEEKS = 20
MIN_PRICES = 3
MIN_CV = 0.05


def clean_panel(d: pd.DataFrame) -> pd.DataFrame:
    """
    price = median unit price among SINGLE-UNIT purchases only.
            No division, no bulk discount, no mix. A true shelf price.
    units = total quantity sold that week, all transactions.
    Measuring price and quantity from different subsets breaks the mechanical
    link that would otherwise manufacture a fake elasticity (division bias).
    """
    one = d[d["Quantity"] == 1]
    price = one.groupby(["SKU", "week"])["unit_price"].median().rename("price")
    units = d.groupby(["SKU", "week"])["Quantity"].sum().rename("units")
    g = pd.concat([price, units], axis=1).dropna().reset_index()
    return g.merge(d[["SKU", "SKU_Category"]].drop_duplicates(), on="SKU")


def eligible_skus(g: pd.DataFrame) -> pd.Index:
    st = g.groupby("SKU").agg(weeks=("price", "size"),
                              nprices=("price", "nunique"),
                              cv=("price", lambda x: x.std() / x.mean()))
    return st[(st.weeks >= MIN_WEEKS) &
              (st.nprices >= MIN_PRICES) &
              (st.cv >= MIN_CV)].index


def confounding_evidence(d: pd.DataFrame, g: pd.DataFrame) -> dict:
    """
    PROOF that the price variation is not usable: prices move WITH demand.
    This is the umbrella problem, measured.
    """
    traffic = d.groupby("week")["Transaction_ID"].nunique().rename("traffic")
    weekly_units = d.groupby("week")["Quantity"].sum().rename("store_units")
    gg = g.merge(traffic, on="week").merge(weekly_units, on="week")

    cors = []
    for _, gs in gg.groupby("SKU"):
        if len(gs) >= 20 and gs.price.nunique() >= 3:
            c = np.corrcoef(gs.price, gs.traffic)[0, 1]
            if not np.isnan(c):
                cors.append(c)
    cors = np.array(cors)

    hi = gg[gg.store_units >= gg.store_units.quantile(0.75)]
    lo = gg[gg.store_units <= gg.store_units.quantile(0.25)]

    # Same test on the FULL transaction base (every SKU, not just the eligible panel).
    # The eligible SKUs are the ones with the most price movement, so the confounding
    # looks milder there. Across the whole book it is stronger. We report BOTH — the
    # gap between them is itself informative, and quoting only the bigger one would be
    # exactly the kind of number-shopping this project exists to call out.
    one_all = d[d["Quantity"] == 1].copy()
    one_all["up"] = one_all["Sales_Amount"] / one_all["Quantity"]
    wk_all = d.groupby("week")["Quantity"].sum().rename("su")
    oa = one_all.merge(wk_all, on="week")
    hi_a = oa[oa.su >= oa.su.quantile(0.75)]
    lo_a = oa[oa.su <= oa.su.quantile(0.25)]
    full_premium = float((hi_a.up.mean() / lo_a.up.mean() - 1) * 100)

    return dict(
        price_premium_full_book_pct=full_premium,
        n_skus_tested=int(len(cors)),
        mean_corr_price_traffic=float(cors.mean()),
        pct_positive_corr=float((cors > 0).mean() * 100),
        avg_price_busiest_weeks=float(hi.price.mean()),
        avg_price_quietest_weeks=float(lo.price.mean()),
        price_premium_in_busy_weeks_pct=float((hi.price.mean() / lo.price.mean() - 1) * 100),
        median_units_per_sku_week=float(g.units.median()),
        pct_sku_weeks_under_3_units=float((g.units <= 2).mean() * 100),
    )


def wald_elasticity(gs: pd.DataFrame, nbins: int = 4):
    """
    Wald (1940) grouping estimator. Bin weeks by price, AVERAGE demand inside each
    bin, then fit the curve through the bin means. Averaging suppresses the Poisson
    noise in units; grouping suppresses the attenuation from noisy weekly prices.
    Returns (elasticity, standard error).
    """
    gs = gs.copy()
    try:
        gs["bin"] = pd.qcut(gs.price, nbins, duplicates="drop", labels=False)
    except Exception:
        return np.nan, np.nan
    a = gs.groupby("bin").agg(p=("price", "mean"), u=("units", "mean"), n=("units", "size"))
    a = a[a.u > 0]
    if len(a) < 3 or a.p.nunique() < 3:
        return np.nan, np.nan
    x, y, w = np.log(a.p.values), np.log(a.u.values), np.sqrt(a.n.values)
    b, a0 = np.polyfit(x, y, 1, w=w)
    r = y - (a0 + b * x)
    denom = max(((x - x.mean()) ** 2 * w).sum() / w.sum(), 1e-9)
    se = np.sqrt((w * r ** 2).sum() / w.sum() / max(len(a) - 2, 1) / denom)
    return float(b), float(max(se, 0.15))


def pooled_elasticity(g: pd.DataFrame) -> float:
    """One elasticity for the whole store, from within-SKU price variation only."""
    gg = g.copy()
    gg["lp"] = np.log(gg.price)
    gg["lq"] = np.log(gg.units)
    x = gg.lp - gg.groupby("SKU").lp.transform("mean")
    y = gg.lq - gg.groupby("SKU").lq.transform("mean")
    return float(np.polyfit(x, y, 1)[0])


def baseline_test(g: pd.DataFrame) -> pd.DataFrame:
    """
    THE TEST THAT DECIDES EVERYTHING.
    Hold out the last ~12 weeks. Given the price actually charged in a week the
    model never saw, predict the units that actually sold. Poisson deviance is the
    right loss for counts.
    """
    cut = g.week.quantile(0.77)
    tr, te = g[g.week <= cut], g[g.week > cut]

    base_u = tr.groupby("SKU").units.mean()
    base_p = tr.groupby("SKU").price.mean()
    e_pool = pooled_elasticity(tr)

    raw, post = {}, {}
    for k, gs in tr.groupby("SKU"):
        b, se = wald_elasticity(gs)
        raw[k] = 0.0 if np.isnan(b) else b
        if np.isnan(b):
            post[k] = BENCH_MEAN
        else:
            wp, wd = 1 / 1.20 ** 2, 1 / se ** 2
            post[k] = (wp * BENCH_MEAN + wd * b) / (wp + wd)
    raw, post = pd.Series(raw), pd.Series(post)

    def predict(e):
        b0, p0 = te.SKU.map(base_u), te.SKU.map(base_p)
        ee = te.SKU.map(e) if not np.isscalar(e) else pd.Series(e, index=te.index)
        return np.clip(b0 * (te.price / p0) ** ee, 0.01, None)

    def dev(pred):
        a = te.units.values
        return float(2 * (a * np.log(np.clip(a, 1e-9, None) / pred) - (a - pred)).mean())

    def mae(pred):
        return float(np.abs(pred - te.units.values).mean())

    rows = []
    for name, e in [("B1  no price effect (e=0)", 0.0),
                    (f"B2  literature elasticity ({BENCH_MEAN})", BENCH_MEAN),
                    (f"B3  pooled from our data ({e_pool:.2f})", e_pool),
                    ("    per-SKU raw estimate", raw),
                    ("    per-SKU Bayesian (prior -2.62)", post)]:
        p = predict(e)
        rows.append(dict(model=name, held_out_MAE=round(mae(p), 3),
                         poisson_deviance=round(dev(p), 3)))
    t = pd.DataFrame(rows)
    t["beats_no_price_effect"] = t.poisson_deviance < t.poisson_deviance.iloc[0]
    return t, e_pool


def plot_confounding(d, g, fname="why_the_data_lies.png"):
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))

    wu = d.groupby("week")["Quantity"].sum().rename("store_units").reset_index()
    gg = g.merge(wu, on="week")
    q = pd.qcut(gg["store_units"], 5, duplicates="drop", labels=False)
    m = gg.groupby(q).price.mean()
    axes[0].bar(range(len(m)), m.values, color="#c0504d")
    axes[0].set_title("Prices are HIGHER when the store is busiest\n"
                      "(if pricing were random this would be flat)", fontsize=10)
    axes[0].set_xlabel("store demand quintile (quiet → busy)")
    axes[0].set_ylabel("average price £")
    axes[0].set_ylim(m.min() * 0.95, m.max() * 1.02)
    axes[0].grid(alpha=0.2, axis="y")

    pct_thin = (g.units <= 2).mean() * 100
    axes[1].hist(g.units.clip(upper=12), bins=range(1, 14), color="#4f81bd", align="left")
    axes[1].set_title("There is almost no demand to explain\n"
                      f"{pct_thin:.0f}% of SKU-weeks sell ≤2 units", fontsize=10)
    axes[1].set_xlabel("units sold per SKU per week")
    axes[1].grid(alpha=0.2, axis="y")

    es = []
    for _, gs in g.groupby("SKU"):
        b, _ = wald_elasticity(gs)
        if not np.isnan(b):
            es.append(b)
    pct_pos = (np.array(es) > 0).mean() * 100
    es = np.clip(es, -8, 5)
    axes[2].hist(es, bins=30, color="#9bbb59")
    axes[2].axvline(0, color="k", lw=1.2)
    axes[2].axvline(BENCH_MEAN, color="#c0504d", ls="--", lw=1.6,
                    label=f"benchmark {BENCH_MEAN}")
    axes[2].set_title(f"The result: {pct_pos:.0f}% of SKUs say customers\nbuy MORE when price goes UP",
                      fontsize=10)
    axes[2].set_xlabel("estimated elasticity")
    axes[2].legend(fontsize=8)
    axes[2].grid(alpha=0.2, axis="y")

    fig.suptitle("Why this store's sales history cannot tell you the right price", fontsize=13)
    fig.tight_layout()
    out = REPORTS / fname
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return out


def main():
    raw, d, panel, s = load_all()
    g = clean_panel(d)
    keep = eligible_skus(g)
    g = g[g.SKU.isin(keep)].reset_index(drop=True)

    print("=" * 84)
    print("BOX 2 — CAN THIS DATA TELL US THE RIGHT PRICE?")
    print("=" * 84)
    print(f"  eligible SKUs (>={MIN_WEEKS} wks, >={MIN_PRICES} prices, CV>={MIN_CV:.0%}): "
          f"{g.SKU.nunique()}")
    print(f"  SKU-weeks: {len(g):,}")

    conf = confounding_evidence(d, g)
    print("\n" + "-" * 84)
    print("EVIDENCE 1 — the price variation is CONFOUNDED (the umbrella problem)")
    print("-" * 84)
    print(f"  average price in the BUSIEST weeks   £{conf['avg_price_busiest_weeks']:.2f}")
    print(f"  average price in the QUIETEST weeks  £{conf['avg_price_quietest_weeks']:.2f}")
    print(f"  => prices are {conf['price_premium_in_busy_weeks_pct']:+.1f}% higher exactly "
          f"when demand is highest")
    print(f"  {conf['pct_positive_corr']:.0f}% of SKUs have price positively correlated with "
          f"store traffic (random pricing => ~50%)")

    print("\n" + "-" * 84)
    print("EVIDENCE 2 — there is almost no demand to explain")
    print("-" * 84)
    print(f"  median units per SKU per week: {conf['median_units_per_sku_week']:.0f}")
    print(f"  {conf['pct_sku_weeks_under_3_units']:.0f}% of SKU-weeks sold <= 2 units")

    es = pd.Series({k: wald_elasticity(gs)[0] for k, gs in g.groupby("SKU")}).dropna()
    print("\n" + "-" * 84)
    print(f"THE ESTIMATES vs THE BENCHMARK ({BENCH_MEAN}, Bijmolt et al. 2005)")
    print("-" * 84)
    print(f"  median      {es.median():>6.2f}")
    print(f"  negative    {(es < 0).mean()*100:>5.0f}%   (should be ~100%)")
    print(f"  POSITIVE    {(es > 0).mean()*100:>5.0f}%   <- 'customers buy more when it costs more'")
    print(f"  |e| > 1     {(es < -1).mean()*100:>5.0f}%   (the rest would break the optimizer)")

    table, e_pool = baseline_test(g)
    print("\n" + "-" * 84)
    print("THE BASELINE TEST — held-out weeks, real prices, real demand")
    print("-" * 84)
    print(table.to_string(index=False))
    best = table.loc[table.poisson_deviance.idxmin(), "model"]
    print(f"\n  BEST: {best.strip()}")
    print("  The literature prior made things TWICE AS BAD. The Bayesian model we")
    print("  proposed was WORSE than assuming price doesn't matter. Baselines caught both.")

    print("\n" + "=" * 84)
    print("VERDICT")
    print("=" * 84)
    print("  Out-of-sample prediction validates a PREDICTIVE coefficient.")
    print("  Pricing decisions need a CAUSAL one. They are different parameters.")
    print("  Confounding + attenuation break the causal reading. This data cannot")
    print("  identify a trustworthy elasticity, and no cleverer model fixes that.")
    print("\n  => The only way to a number you'd stake margin on is to RUN THE EXPERIMENT.")
    print("     That is Box 4. The loop is not a bonus feature. It is the answer.")

    plot_confounding(d, g)
    json.dump(dict(
        benchmark=dict(bijmolt_2005=BENCH_MEAN, tellis_1988=BENCH_TELLIS),
        eligible_skus=int(g.SKU.nunique()), sku_weeks=int(len(g)),
        confounding=conf,
        estimates=dict(median=float(es.median()), pct_negative=float((es < 0).mean() * 100),
                       pct_positive=float((es > 0).mean() * 100),
                       pct_elastic=float((es < -1).mean() * 100)),
        baseline_test=table.to_dict("records"),
        pooled_elasticity=float(e_pool),
    ), open(ART / "elasticity_findings.json", "w"), indent=2)
    g.to_parquet(ART / "panel.parquet", index=False)
    es.rename("elasticity").to_frame().to_csv(REPORTS / "sku_elasticities.csv")
    print("\nsaved -> artifacts/elasticity_findings.json, artifacts/panel.parquet")
    print("plot  -> reports/why_the_data_lies.png")


if __name__ == "__main__":
    main()
