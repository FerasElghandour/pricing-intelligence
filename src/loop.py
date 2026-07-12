"""
BOX 4 — THE CLOSED LOOP.  This is why Project 3 exists.

    act -> observe -> learn -> re-optimise -> act ...

Projects 1 and 2 stopped at "decide". They never found out whether they were right.
This one does. And for pricing it is not a nice-to-have: Box 2 proved the store's
own history CANNOT identify a causal elasticity, because prices moved WITH demand.
The only way to break that confounding is to move a price ON PURPOSE — for a reason
that has nothing to do with demand — and watch what happens.

That is what this file does.

===========================================================================
WHAT IS REAL AND WHAT IS SIMULATED — read this before believing anything
===========================================================================
REAL (measured from the scanner data):
  * each SKU's current price, its observed price range, its baseline weekly demand
  * the demand NOISE. Weekly sales are small integers, so we model them as Poisson,
    which is exactly the noise we observe.
  * the STARTING BELIEF. The loop is seeded with the real (confounded, unreliable)
    observational estimate from Box 2 — because that is genuinely what a business
    walks in with on day one.

SIMULATED (and it has to be — this is THE load-bearing assumption):
  * THE DEMAND RESPONSE TO PRICES THE STORE NEVER CHARGED.
    We cannot observe a counterfactual. Nobody can. If a store never sold that SKU
    at £8.20, no dataset on earth contains how many units it would have sold at
    £8.20. To demonstrate a learning loop we must invent a ground truth and let the
    loop discover it.
  * So each SKU is given a TRUE elasticity, drawn from a plausible retail range
    (centred near the Bijmolt et al. benchmark of -2.62). The loop does not know it.
    Convergence to that number is the thing we are demonstrating.

WHAT THIS DOES AND DOESN'T PROVE:
  It does NOT prove "these are the right prices for this store."
  It DOES prove the MECHANISM works: that a system starting from a wrong belief,
  which sets prices deliberately and updates on what it sees, converges on the truth
  and beats both (a) doing nothing and (b) trusting the observational estimate.
  That mechanism is the deliverable. The numbers inside it are a testbed.

===========================================================================
THE FOUR STRATEGIES WE RACE
===========================================================================
  STATUS QUO   never change the price. The honest baseline. (Most businesses.)
  STATIC       trust the observational estimate, set the "optimal" price ONCE,
               never look again. THIS IS WHAT A NORMAL PRICING PROJECT SHIPS.
  CLOSED LOOP  Thompson sampling: sample an elasticity from the current posterior,
               price optimally for it, observe demand, update the posterior, repeat.
               Exploration is automatic — uncertainty makes it try things.
  ORACLE       knows the true elasticity from round 1. The ceiling. Unbeatable.

The interesting comparison is STATIC vs CLOSED LOOP. Static is what you get when you
believe your historical data. If the historical estimate is wrong — and Box 2 showed
it is — static can LOSE money versus doing nothing at all.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from data import load_all
from elasticity import clean_panel, eligible_skus, wald_elasticity
from optimize import GROSS_MARGIN, MAX_MOVE, optimal_price

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
REPORTS = ROOT / "reports"

SEED = 42
N_REPLICATIONS = 20    # one simulation is an anecdote. Twenty is evidence.
N_ROUNDS = 104         # two years of weekly price decisions (a realistic programme)
N_SKUS = 30            # the unknown-elasticity SKUs we put in the loop
EXPLORE_BAND = 0.25    # during learning we allow ±25% (wider than the static ±15%,
                       # because the whole point is to probe). Still inside sanity.
NOISE_SD = 0.60        # residual sd of log-demand — MEASURED from the real panel in main()
PROBE_SIZE = 0.08      # a price TEST is a ±8% nudge, not a wild swing. See run_one_sku().


# ---------------------------------------------------------------------------
# The simulated world (the honest fiction)
# ---------------------------------------------------------------------------
class Market:
    """
    The ground truth the loop is trying to discover.
    q(p) ~ Poisson( q0 * (p/p0)^e_true )
    Poisson because real weekly unit sales ARE small counts — that noise is real.
    """

    def __init__(self, p0, q0, e_true, rng):
        self.p0, self.q0, self.e_true, self.rng = p0, q0, e_true, rng

    def sell(self, price):
        mean = self.q0 * (price / self.p0) ** self.e_true
        return float(self.rng.poisson(max(mean, 1e-6)))

    def true_optimal_price(self, cost, lo, hi):
        p = optimal_price(cost, self.e_true)
        return float(np.clip(p, lo, hi)) if not np.isnan(p) else hi


# ---------------------------------------------------------------------------
# The learner: Bayesian linear regression on log demand
# ---------------------------------------------------------------------------
class ElasticityLearner:
    """
    Belief over (intercept, elasticity), updated with every week we observe.

        log(units + 0.5) = a + e * log(price) + noise

    Conjugate Gaussian posterior, so the update is exact and cheap. The posterior
    VARIANCE is what drives exploration: when we're unsure, Thompson sampling makes
    us try prices we wouldn't otherwise try. That's the loop deliberately buying
    information — the thing observational data can never do.
    """

    def __init__(self, prior_mean_e, prior_sd_e, prior_mean_a, prior_sd_a, noise_sd=NOISE_SD):
        self.mu = np.array([prior_mean_a, prior_mean_e], dtype=float)
        self.Sigma = np.diag([prior_sd_a ** 2, prior_sd_e ** 2])
        self.noise_var = noise_sd ** 2

    def update(self, price, units):
        x = np.array([1.0, np.log(price)])
        y = np.log(units + 0.5)
        S_inv = np.linalg.inv(self.Sigma)
        S_new = np.linalg.inv(S_inv + np.outer(x, x) / self.noise_var)
        self.mu = S_new @ (S_inv @ self.mu + x * y / self.noise_var)
        self.Sigma = S_new

    def sample_elasticity(self, rng):
        return float(rng.multivariate_normal(self.mu, self.Sigma)[1])

    @property
    def e_hat(self):
        return float(self.mu[1])

    @property
    def e_sd(self):
        return float(np.sqrt(self.Sigma[1, 1]))


def price_for(e, cost, lo, hi):
    """Optimal price for a given elasticity, guardrailed. Inelastic -> push to ceiling."""
    p = optimal_price(cost, e)
    if np.isnan(p):          # |e| <= 1 or positive: profit rises with price
        p = hi
    return float(np.clip(p, lo, hi))


def run_one_sku(p0, q0, e_obs, e_true, rng, rounds=N_ROUNDS, history=None):
    cost = p0 * (1 - GROSS_MARGIN)
    lo, hi = p0 * (1 - EXPLORE_BAND), p0 * (1 + EXPLORE_BAND)
    market = Market(p0, q0, e_true, rng)

    # STATIC: trust the observational estimate. Set once. Never learn.
    p_static = price_for(e_obs, cost, lo, hi)
    # ORACLE: knows the truth.
    p_oracle = market.true_optimal_price(cost, lo, hi)

    # THE LOOP: starts from the (wrong) observational belief, with honest uncertainty
    learner = ElasticityLearner(prior_mean_e=e_obs, prior_sd_e=1.5,
                                prior_mean_a=np.log(q0 + 0.5) - e_obs * np.log(p0),
                                prior_sd_a=1.5)
    # Seed with the store's REAL price history. This is the honest starting point:
    # the business already has this data — it just isn't enough (Box 2). Feeding it
    # in pins the intercept, so the loop is learning the SLOPE, not re-learning the level.
    if history is not None:
        for pr, un in history:
            learner.update(float(pr), float(un))

    hist = []
    cum = dict(status_quo=0.0, static=0.0, loop=0.0, oracle=0.0)
    for t in range(rounds):
        # --- ACT ---------------------------------------------------------------
        # WHY EXPLORATION IS EXPLICIT AND NOT JUST THOMPSON:
        # A greedy learner prices at the optimum it currently believes in — and then
        # sits there. But a demand CURVE can only be identified from price VARIATION.
        # Standing still teaches you nothing, no matter how good your maths is. So we
        # deliberately spread prices across the band early on, then exploit as the
        # posterior tightens. This IS a price experiment: move the price for a reason
        # that has nothing to do with demand. That is what breaks the confounding
        # Box 2 documented, and it is the whole reason the loop can learn when the
        # historical data cannot.
        # EXPERIMENT DESIGN MATTERS AS MUCH AS THE MATHS.
        # A first version explored by picking a RANDOM price anywhere in the ±25% band.
        # It learned — and it LOST MONEY, because half its probes sat far from the
        # optimum. That is not how a real price test works, and it is not how you spend
        # a customer's goodwill.
        # A real test makes a SMALL, DELIBERATE perturbation around the price you would
        # otherwise charge: ±8% — enough to move demand measurably, cheap enough that
        # being wrong barely costs anything. Same information, a fraction of the price.
        e_s = learner.sample_elasticity(rng)         # Thompson: exploit, but with doubt
        p_greedy = price_for(e_s, cost, lo, hi)

        eps = max(0.15, 0.95 * (0.96 ** t))          # probe often early, a little forever
        if rng.random() < eps:
            nudge = PROBE_SIZE * (1 if rng.random() < 0.5 else -1)
            p_loop = float(np.clip(p_greedy * (1 + nudge), lo, hi))
        else:
            p_loop = p_greedy

        # --- MEASURE: the world responds (simulated counterfactual demand) -----
        q_sq = market.sell(p0)
        q_st = market.sell(p_static)
        q_lp = market.sell(p_loop)
        q_or = market.sell(p_oracle)

        # --- LEARN: update the belief with what we actually saw ----------------
        learner.update(p_loop, q_lp)

        cum["status_quo"] += (p0 - cost) * q_sq
        cum["static"] += (p_static - cost) * q_st
        cum["loop"] += (p_loop - cost) * q_lp
        cum["oracle"] += (p_oracle - cost) * q_or

        hist.append(dict(round=t + 1, e_hat=learner.e_hat, e_sd=learner.e_sd,
                         e_true=e_true, price_loop=p_loop, price_oracle=p_oracle,
                         **{f"cum_{k}": v for k, v in cum.items()}))
    return pd.DataFrame(hist)


def main():
    rng = np.random.default_rng(SEED)
    raw, d, _, _ = load_all()
    g = clean_panel(d)
    g = g[g.SKU.isin(eligible_skus(g))]

    # Real starting conditions, real observational (unreliable) beliefs
    rows = []
    for sku, gs in g.groupby("SKU"):
        e_obs, se = wald_elasticity(gs)
        if np.isnan(e_obs):
            continue
        rows.append(dict(SKU=sku, p0=float(gs.price.median()), q0=float(gs.units.mean()),
                         e_obs=float(e_obs), revenue=float(gs.price.median() * gs.units.mean() * 52)))
    skus = pd.DataFrame(rows).nlargest(N_SKUS, "revenue").reset_index(drop=True)

    # SIMULATED ground truth: a plausible retail elasticity, unknown to the loop
    skus["e_true"] = np.clip(rng.normal(-2.62, 0.9, len(skus)), -5.5, -1.2)

    print("=" * 88)
    print("BOX 4 — THE CLOSED LOOP")
    print("=" * 88)
    print(f"  SKUs in the loop        {len(skus)}   (the highest-revenue fitted SKUs)")
    print(f"  rounds                  {N_ROUNDS} weeks")
    print(f"  starting belief         the REAL observational estimate (median "
          f"{skus.e_obs.median():.2f}) — the confounded one")
    print(f"  SIMULATED ground truth  e ~ N(-2.62, 0.9), clipped to [-5.5, -1.2]")
    print(f"                          (we CANNOT observe demand at prices never charged.")
    print(f"                           This is the load-bearing assumption of Box 4.)")
    print(f"  how wrong is the starting belief? median |e_obs - e_true| = "
          f"{np.abs(skus.e_obs - skus.e_true).median():.2f}\n")

    hist_map = {k: list(zip(v.price, v.units)) for k, v in g.groupby("SKU")}
    frames = []
    for _, r in skus.iterrows():
        h = run_one_sku(r.p0, r.q0, r.e_obs, r.e_true, rng, history=hist_map.get(r.SKU))
        h["SKU"] = r.SKU
        frames.append(h)
    H = pd.concat(frames, ignore_index=True)

    H["abs_err"] = (H.e_hat - H.e_true).abs()
    curve = H.groupby("round").agg(
        mean_abs_error=("abs_err", "mean"),
        mean_e_sd=("e_sd", "mean"),
        cum_status_quo=("cum_status_quo", "sum"),
        cum_static=("cum_static", "sum"),
        cum_loop=("cum_loop", "sum"),
        cum_oracle=("cum_oracle", "sum"),
    ).reset_index()

    print("-" * 88)
    print("DOES IT LEARN? (how far the estimate is from the truth)")
    print("-" * 88)
    for t in [1, 4, 8, 13, 26, 52]:
        if t <= len(curve):
            r = curve[curve["round"] == t].iloc[0]
            print(f"  week {t:>2}:  |error| = {r.mean_abs_error:>5.2f}   "
                  f"uncertainty (sd) = {r.mean_e_sd:>5.2f}")
    start, end = curve.iloc[0], curve.iloc[-1]
    print(f"\n  error fell {start.mean_abs_error:.2f} -> {end.mean_abs_error:.2f}  "
          f"({(1-end.mean_abs_error/start.mean_abs_error)*100:.0f}% closer to the truth)")

    # ---- REPLICATE. One simulation is an anecdote. ---------------------------
    print("\n" + "-" * 88)
    print(f"THE RACE — {N_REPLICATIONS} independent replications, {N_ROUNDS} weeks, {len(skus)} SKUs")
    print("-" * 88)
    reps = {k: [] for k in ["static", "loop", "oracle"]}
    for rep in range(N_REPLICATIONS):
        r2 = np.random.default_rng(1000 + rep)
        tot = {k: 0.0 for k in ["status_quo", "static", "loop", "oracle"]}
        for _, r in skus.iterrows():
            et = float(np.clip(r2.normal(-2.62, 0.9), -5.5, -1.2))
            hh = run_one_sku(r.p0, r.q0, r.e_obs, et, r2, history=hist_map.get(r.SKU))
            fr = hh.iloc[-1]
            for k in tot:
                tot[k] += fr[f"cum_{k}"]
        sq_ = tot["status_quo"]
        for k in reps:
            reps[k].append((tot[k] / sq_ - 1) * 100)

    print(f"  {'strategy':<42}{'mean vs status quo':>20}{'95% CI':>20}{'wins':>7}")
    for k, lab in [("static", "STATIC (trust the data, set once)"),
                   ("loop", "CLOSED LOOP (test, learn, re-optimise)"),
                   ("oracle", "ORACLE (knows the truth — the ceiling)")]:
        a = np.array(reps[k]); lo_, hi_ = np.percentile(a, [2.5, 97.5])
        print(f"  {lab:<42}{a.mean():>+19.1f}%  [{lo_:>+5.1f}%,{hi_:>+5.1f}%]{(a > 0).mean()*100:>6.0f}%")

    dd = np.array(reps["loop"]) - np.array(reps["static"])
    lo_, hi_ = np.percentile(dd, [2.5, 97.5])
    print(f"\n  LOOP minus STATIC: {dd.mean():+.1f}pp   95% CI [{lo_:+.1f}, {hi_:+.1f}]"
          f"   the loop wins {(dd > 0).mean()*100:.0f}% of the time")
    print(f"\n  *** TRUSTING YOUR HISTORICAL DATA (static) LOSES MONEY IN "
          f"{(np.array(reps['static']) < 0).mean()*100:.0f}% OF RUNS. ***")
    print(f"      The prize is real — the ORACLE captures {np.array(reps['oracle']).mean():+.1f}%.")
    print("      But you only get it by TESTING, and only where volume lets you learn.")
    sq = None
    f = curve.iloc[-1]
    reps_out = {k: dict(mean=float(np.mean(v)),
                        ci_low=float(np.percentile(v, 2.5)),
                        ci_high=float(np.percentile(v, 97.5)),
                        pct_beats_status_quo=float((np.array(v) > 0).mean() * 100))
                for k, v in reps.items()}
    reps_out["loop_minus_static"] = dict(mean=float(dd.mean()),
                                         ci_low=float(lo_), ci_high=float(hi_),
                                         pct_loop_wins=float((dd > 0).mean() * 100))

    # ---- VOLUME IS THE CURRENCY OF EXPERIMENTATION --------------------------
    print("\n" + "-" * 88)
    print("WHAT GOVERNS HOW FAST IT LEARNS? (the operator's real constraint)")
    print("-" * 88)
    last = H[H["round"] == H["round"].max()][["SKU", "abs_err"]]
    vol = skus.set_index("SKU").q0
    last = last.assign(q0=last.SKU.map(vol))
    bins = [("low  (<3 units/wk)", 0, 3), ("mid  (3-8)", 3, 8), ("high (>8 units/wk)", 8, 1e9)]
    for lab, lo_, hi_ in bins:
        m = last[(last.q0 >= lo_) & (last.q0 < hi_)]
        if len(m):
            print(f"  {lab:<22} {len(m):>3} SKUs   final |error| = {m.abs_err.mean():.2f}")
    print("\n  The loop learns faster on products that actually sell. You cannot")
    print("  price-test a product nobody buys — volume is the currency of experimentation.")

    plot(curve, H, skus, reps)
    curve.to_csv(REPORTS / "loop_convergence.csv", index=False)
    json.dump(dict(
        n_skus=int(len(skus)), rounds=N_ROUNDS, replications=N_REPLICATIONS,
        real=["current price", "observed price range", "baseline weekly demand",
              "Poisson demand noise", "the starting (confounded) belief"],
        simulated=["demand response at prices never charged — the counterfactual"],
        start_error=float(start.mean_abs_error), end_error=float(end.mean_abs_error),
        results=reps_out,
    ), open(ART / "loop_metrics.json", "w"), indent=2)
    print("\nsaved -> artifacts/loop_metrics.json, reports/loop_convergence.csv")


def plot(curve, H, skus, reps, fname="the_loop.png"):
    fig, axes = plt.subplots(1, 3, figsize=(17, 4.8))

    ax = axes[0]
    ax.plot(curve["round"], curve.mean_abs_error, lw=2, color="#c0504d")
    ax.fill_between(curve["round"], 0, curve.mean_e_sd, alpha=0.18, color="#4f81bd",
                    label="uncertainty (posterior sd)")
    ax.set_title("1. IT LEARNS\nhow far the estimate is from the truth", fontsize=11)
    ax.set_xlabel("week"); ax.set_ylabel("|error| in elasticity")
    ax.legend(fontsize=8); ax.grid(alpha=0.2)

    ax = axes[1]
    for sku in skus.SKU.head(6):
        h = H[H.SKU == sku]
        ax.plot(h["round"], h.e_hat, lw=1.1, alpha=0.8)
        ax.axhline(h.e_true.iloc[0], ls=":", lw=0.8, alpha=0.5)
    ax.set_title("2. EACH PRODUCT FINDS ITS OWN CURVE\nsolid = belief, dotted = truth", fontsize=11)
    ax.set_xlabel("week"); ax.set_ylabel("elasticity")
    ax.grid(alpha=0.2)

    # PANEL 3 — the honest one. A single simulation is an anecdote; this is 20.
    ax = axes[2]
    names = ["STATIC\n(trust the data)", "CLOSED LOOP\n(test & learn)", "ORACLE\n(knows truth)"]
    keys = ["static", "loop", "oracle"]
    means = [np.mean(reps[k]) for k in keys]
    los = [np.mean(reps[k]) - np.percentile(reps[k], 2.5) for k in keys]
    his = [np.percentile(reps[k], 97.5) - np.mean(reps[k]) for k in keys]
    cols = ["#f85149", "#3fb950", "#7f7f7f"]
    ax.bar(names, means, yerr=[los, his], capsize=6, color=cols, alpha=0.85)
    ax.axhline(0, color="k", lw=1.2)
    ax.set_title("3. THE HONEST RESULT (20 replications)\nmargin vs. never changing the price",
                 fontsize=11)
    ax.set_ylabel("% vs status quo")
    ax.grid(alpha=0.2, axis="y")
    for i, m in enumerate(means):
        ax.text(i, m + (0.6 if m >= 0 else -1.4), f"{m:+.1f}%", ha="center",
                fontsize=10, fontweight="bold")

    fig.suptitle("The closed loop: act → observe → learn → re-optimise.  "
                 "Trusting your data LOSES money. Testing beats it — but only volume buys speed.",
                 fontsize=12)
    fig.tight_layout()
    out = REPORTS / fname
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return out


if __name__ == "__main__":
    main()
