"""
BOX 3 — DECISION: the price optimizer

    elasticity  ->  "raise this price 6%. Projected margin lift £1,240/yr.
                     CONFIDENCE: LOW. This is a hypothesis. Go test it."

Box 2 proved this store's history cannot identify a trustworthy causal elasticity.
So this box does NOT pretend to hand you optimal prices. It hands you the best
available hypothesis, with the uncertainty made visible and the guardrails hard.

THE MATHS
---------
Constant-elasticity demand:      q(p) = q0 * (p/p0)^e
Contribution:                    C(p) = (p - cost) * q(p)
Maximise:                        dC/dp = 0  =>  p* = cost * e/(e+1)

That formula has a trapdoor in it. If |e| <= 1 the denominator (e+1) goes to zero
or flips sign and p* EXPLODES — the optimizer will cheerfully tell you to charge
£900 for a tin of beans. 59% of our SKUs have |e| <= 1. This is not a hypothetical.

THE THREE GUARDRAILS (each one exists because something would otherwise break)
-----------------------------------------------------------------------------
1. NEVER RECOMMEND OUTSIDE THE OBSERVED PRICE RANGE.
   Our demand curve is fitted between (say) £5.70 and £7.40. Beyond that we are
   extrapolating a curve we have never seen. This is the pricing version of the
   ghost-whale bug from the churn project: an unconstrained optimizer will happily
   invent a number from thin data and put it top of the list.

2. NEVER MOVE MORE THAN ±MAX_MOVE IN ONE STEP.
   Even if the maths says +40%, you don't do that to a real customer base. A price
   is a relationship, not a variable.

3. NEVER OPTIMISE A SKU WHOSE ELASTICITY WE CANNOT PIN DOWN.
   We build a 95% interval around each elasticity and sort every SKU into:

     TIER A  interval entirely below -1  -> confidently elastic. Optimise properly.
     TIER B  interval in (-1, 0)         -> confidently inelastic but still a real
                                            (downward) demand curve. Raise toward
                                            the guardrail ceiling.
     TIER C  interval STRADDLES -1       -> we do not know whether raising the price
                                            makes or loses money. NO RECOMMENDATION.
     TIER D  elasticity is NON-NEGATIVE  -> demand slopes UPWARD. This is not a
                                            product with pricing power, it is a
                                            BROKEN ESTIMATE. REFUSED.

   TIERS C AND D ARE THE POINT OF THIS BOX. 115 of our 139 SKUs (83%) land there.
   The optimizer's most valuable output is an honest "I don't know" plus a precise
   list of which products must be experimented on. That list is Box 4's input.

   A BUG WE SHIPPED AND THEN CAUGHT: the first version of this file had no Tier D.
   Upward-sloping SKUs were classed "confidently inelastic", and since raising the
   price of an upward-sloping demand curve looks infinitely profitable, they went
   STRAIGHT TO THE TOP of the recommendation list (+£740, +£543, +£487...). The
   most confident advice in the system was built on its most broken numbers. Exactly
   the ghost-whale bug from the churn project, in a different costume.

COST — THE LOAD-BEARING ASSUMPTION
----------------------------------
This dataset has NO cost data. None. So:

    cost = price * (1 - GROSS_MARGIN)     with GROSS_MARGIN assumed and adjustable

WHY THIS DOESN'T INVALIDATE THE DIRECTION OF THE ADVICE:
    The elasticity comes from observed behaviour, so "this SKU looks elastic /
    inelastic" is data, not assumption. The margin only SCALES the £ figure.
    Change GROSS_MARGIN from 30% to 40% and every £ number moves; almost no
    recommendation flips direction. We show that explicitly in the sensitivity run.
    "Raise the price" is earned. "It's worth £42k" is rented.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd

from data import load_all
from elasticity import clean_panel, eligible_skus, wald_elasticity, BENCH_MEAN

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
REPORTS = ROOT / "reports"

# =============================================================================
# THE ASSUMPTIONS A REAL BRAND WOULD REPLACE
# =============================================================================
GROSS_MARGIN = 0.30      # 30% — typical grocery/convenience retail. ASSUMED.
MAX_MOVE = 0.15          # never move a price more than ±15% in one step
WEEKS_PER_YEAR = 52
CONF_Z = 1.96            # 95% interval on the elasticity
# =============================================================================


def optimal_price(cost, e):
    """p* = cost * e/(e+1). Only valid for e < -1; NaN otherwise (by design)."""
    e = np.asarray(e, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = cost * e / (e + 1.0)
    return np.where(e < -1.0, p, np.nan)


def contribution(price, cost, q0, p0, e):
    """Weekly contribution at `price`, given demand q0 at reference price p0."""
    q = q0 * (price / p0) ** e
    return (price - cost) * q


def build_recommendations(panel: pd.DataFrame,
                          gross_margin: float = GROSS_MARGIN,
                          max_move: float = MAX_MOVE) -> pd.DataFrame:
    rows = []
    for sku, gs in panel.groupby("SKU"):
        e, se = wald_elasticity(gs)
        if np.isnan(e):
            continue

        p0 = float(gs.price.median())          # current price
        q0 = float(gs.units.mean())            # current weekly demand
        pmin, pmax = float(gs.price.min()), float(gs.price.max())
        cost = p0 * (1 - gross_margin)

        e_lo, e_hi = e - CONF_Z * se, e + CONF_Z * se   # 95% interval (e_lo more negative)

        # ---- TIERING: what do we actually know? ----------------------------
        # GUARDRAIL 0 (the one that nearly got away):
        # A NON-NEGATIVE ELASTICITY IS NOT "INELASTIC" — IT IS BROKEN.
        # It says demand slopes UPWARD: customers buy MORE as the price rises.
        # That is not a product with pricing power, it is a failed estimate — and
        # it is precisely the confounding Box 2 documented (the store raised prices
        # on things that were already selling).
        # An earlier version of this file classed these as "confidently inelastic"
        # and put them at the TOP of the recommendation list, because raising the
        # price of an upward-sloping demand curve looks infinitely profitable.
        # They are now REFUSED and sent to Box 4 to be tested.
        if e >= 0 or e_hi >= 0:
            tier, conf = "D", "BROKEN — demand slopes upward. Untrustworthy."
        elif e_hi < -1.0:
            tier, conf = "A", "elastic (confident)"
        elif e_lo > -1.0:
            tier, conf = "B", "inelastic (confident)"
        else:
            tier, conf = "C", "UNKNOWN — must be tested"

        # ---- the raw optimum, then the guardrails --------------------------
        if tier == "A":
            p_raw = float(optimal_price(cost, e))
        elif tier == "B":
            # genuinely inelastic (downward but shallow): profit rises with price.
            p_raw = p0 * (1 + max_move)
        else:
            p_raw = np.nan   # tiers C and D get NO recommendation

        if np.isnan(p_raw):
            p_rec = np.nan
            capped_by = "no recommendation"
        else:
            lo_band = max(p0 * (1 - max_move), pmin)   # GUARDRAIL 1 + 2
            hi_band = min(p0 * (1 + max_move), pmax)
            p_rec = float(np.clip(p_raw, lo_band, hi_band))
            if p_raw > hi_band:
                capped_by = "observed max" if hi_band == pmax else f"±{max_move:.0%} band"
            elif p_raw < lo_band:
                capped_by = "observed min" if lo_band == pmin else f"±{max_move:.0%} band"
            else:
                capped_by = "none (interior optimum)"

        cur_c = contribution(p0, cost, q0, p0, e) * WEEKS_PER_YEAR
        if np.isnan(p_rec):
            new_c = cur_c
            lift = 0.0
            lift_lo = lift_hi = 0.0
        else:
            new_c = contribution(p_rec, cost, q0, p0, e) * WEEKS_PER_YEAR
            lift = new_c - cur_c
            # propagate elasticity uncertainty into the £ lift
            lo = contribution(p_rec, cost, q0, p0, e_lo) * WEEKS_PER_YEAR - cur_c
            hi = contribution(p_rec, cost, q0, p0, e_hi) * WEEKS_PER_YEAR - cur_c
            lift_lo, lift_hi = float(min(lo, hi)), float(max(lo, hi))

        rows.append(dict(
            SKU=sku, category=gs.SKU_Category.iloc[0],
            elasticity=round(e, 2), elasticity_se=round(se, 2),
            e_lo=round(e_lo, 2), e_hi=round(e_hi, 2),
            tier=tier, confidence=conf,
            current_price=round(p0, 2), recommended_price=round(p_rec, 2) if not np.isnan(p_rec) else np.nan,
            price_move_pct=round((p_rec / p0 - 1) * 100, 1) if not np.isnan(p_rec) else np.nan,
            observed_min=round(pmin, 2), observed_max=round(pmax, 2),
            capped_by=capped_by,
            weekly_units=round(q0, 1),
            current_contribution=round(cur_c, 0),
            projected_lift=round(lift, 0),
            lift_low=round(lift_lo, 0), lift_high=round(lift_hi, 0),
            annual_revenue=round(p0 * q0 * WEEKS_PER_YEAR, 0),
        ))
    return pd.DataFrame(rows).sort_values("projected_lift", ascending=False).reset_index(drop=True)


def margin_sensitivity(panel):
    """Does the ADVICE change when the assumed margin changes? (It mostly doesn't.)"""
    out = []
    base = build_recommendations(panel, gross_margin=GROSS_MARGIN)
    base_dir = base.set_index("SKU")["price_move_pct"]
    for gm in [0.20, 0.25, 0.30, 0.35, 0.40, 0.50]:
        r = build_recommendations(panel, gross_margin=gm)
        d = r.set_index("SKU")["price_move_pct"]
        common = base_dir.dropna().index.intersection(d.dropna().index)
        same_dir = (np.sign(base_dir[common]) == np.sign(d[common])).mean() * 100
        out.append(dict(gross_margin=f"{gm:.0%}",
                        total_lift=round(r.projected_lift.sum()),
                        skus_actioned=int(r.recommended_price.notna().sum()),
                        pct_same_direction=round(same_dir, 0)))
    return pd.DataFrame(out)


def main():
    raw, d, _, _ = load_all()
    g = clean_panel(d)
    g = g[g.SKU.isin(eligible_skus(g))].reset_index(drop=True)

    rec = build_recommendations(g)
    rec.to_csv(ART / "recommendations.csv", index=False)

    tiers = rec.groupby("tier").agg(
        skus=("SKU", "size"),
        revenue=("annual_revenue", "sum"),
        lift=("projected_lift", "sum"))

    print("=" * 88)
    print("BOX 3 — THE OPTIMIZER (and what it refuses to do)")
    print("=" * 88)
    print(f"  SKUs with a fitted demand curve: {len(rec)}")
    print(f"  ASSUMED gross margin: {GROSS_MARGIN:.0%}  (no cost data exists — see docstring)")
    print(f"  Guardrails: price move capped at ±{MAX_MOVE:.0%} AND inside the observed range\n")

    print("WHAT WE ACTUALLY KNOW, PER SKU")
    print("-" * 88)
    labels = {"A": "A  confidently ELASTIC   -> optimise",
              "B": "B  confidently INELASTIC -> raise toward ceiling",
              "C": "C  UNKNOWN               -> NO recommendation. Test it.",
              "D": "D  BROKEN (upward demand) -> REFUSED. Test it."}
    for t in ["A", "B", "C", "D"]:
        if t in tiers.index:
            r = tiers.loc[t]
            print(f"  {labels[t]:<52} {int(r.skus):>4} SKUs   "
                  f"£{r.revenue:>10,.0f} revenue   lift £{r.lift:>9,.0f}")

    actioned = rec[rec.recommended_price.notna()]
    print("\n" + "-" * 88)
    print("THE OPPORTUNITY (best current estimate — a HYPOTHESIS, not an answer)")
    print("-" * 88)
    print(f"  SKUs with a recommendation      {len(actioned)}")
    print(f"  current annual contribution     £{rec.current_contribution.sum():,.0f}")
    print(f"  projected annual lift           £{rec.projected_lift.sum():,.0f}"
          f"   ({rec.projected_lift.sum()/max(rec.current_contribution.sum(),1)*100:.1f}%)")
    print(f"  uncertainty on that lift        £{actioned.lift_low.sum():,.0f} "
          f"to £{actioned.lift_high.sum():,.0f}")
    print("  ^ that band is the honest width. It is wide because the elasticity is weak.")

    print("\n  GUARDRAIL BITES (how often the maths wanted to go too far):")
    print(rec[rec.recommended_price.notna()].capped_by.value_counts().to_string())

    print("\n" + "-" * 88)
    print("TOP 10 BY PROJECTED LIFT")
    print("-" * 88)
    show = actioned.head(10)[["SKU", "tier", "elasticity", "e_lo", "e_hi",
                              "current_price", "recommended_price", "price_move_pct",
                              "projected_lift", "lift_low", "lift_high"]]
    print(show.to_string(index=False))

    print("\n" + "-" * 88)
    print("DOES THE ASSUMED MARGIN CHANGE THE ADVICE? (the honesty check)")
    print("-" * 88)
    ms = margin_sensitivity(g)
    print(ms.to_string(index=False))
    print("\n  'pct_same_direction' = share of SKUs where the price move points the SAME WAY")
    print("  as under our 30% assumption. The £ figure moves; the DIRECTION barely does.")
    print("  => the margin assumption scales the prize. It does not choose the action.")

    ms.to_csv(REPORTS / "margin_sensitivity.csv", index=False)
    json.dump(dict(
        assumptions=dict(gross_margin=GROSS_MARGIN, max_move=MAX_MOVE,
                         weeks_per_year=WEEKS_PER_YEAR),
        skus_fitted=int(len(rec)),
        tiers={t: int(tiers.loc[t, "skus"]) for t in tiers.index},
        current_contribution=float(rec.current_contribution.sum()),
        projected_lift=float(rec.projected_lift.sum()),
        lift_low=float(actioned.lift_low.sum()), lift_high=float(actioned.lift_high.sum()),
        skus_actioned=int(len(actioned)),
        skus_to_test=int(rec.tier.isin(["C", "D"]).sum()),
        skus_broken=int((rec.tier == "D").sum()),
        margin_sensitivity=ms.to_dict("records"),
    ), open(ART / "optimizer_metrics.json", "w"), indent=2)
    print("\nsaved -> artifacts/recommendations.csv, artifacts/optimizer_metrics.json")


if __name__ == "__main__":
    main()
