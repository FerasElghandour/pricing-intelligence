# Pricing Intelligence — Your Pricing Data Is Lying To You

### 🔗 **[View the live dashboard →](https://feraselghandour.github.io/pricing-intelligence/)**

---

> ## Your pricing data will lose you money if you trust it.
> ## Testing beats trusting — reliably.
> ## But you can only test what actually sells.

**The problem.** Every pricing project starts the same way: fit a demand curve to your sales history, find the profit-maximising price, ship the dashboard. **I did exactly that — and then checked whether the answer was real.** It wasn't.

**Why.** In this store, **prices are 6.3% higher in the busiest weeks.** The shop raised prices on things that were already selling. So the sales history contains a real effect (higher price → fewer sales) tangled with a fake one (busy week → higher price *and* more sales). They cancel. **38% of products come out saying customers buy *more* when the price goes up.**

**The honest result.** Across 20 independent replications:

| Strategy | Margin vs. never changing price |
|---|---|
| **STATIC** — trust your data, set the price once | **−3.2%** — *loses money in 75% of runs* |
| **CLOSED LOOP** — test, measure, learn, re-optimise | **−0.5%** — *beats STATIC by +2.7pp, winning **100/100** replications* |
| **ORACLE** — knows the true demand curve | **+10.2%** — *the prize is real, and volume-gated* |

**The system.** It proves the historical data is contaminated, **refuses to guess** where it cannot know (83% of products), and then **closes the loop** — running deliberate price experiments, measuring the response, updating its beliefs, and re-optimising. **Projects 1 and 2 stopped at "decide." This one finds out whether it was right.**

---

## The argument, in four steps

### 1. Your sales data is confounded

**Umbrella prices rise when it rains. Umbrella sales rise when it rains.** Your data says *"high price → high sales."* The rain caused both — and **"rain" is not a column in the spreadsheet.**

Measured in this store:

| Evidence | |
|---|---|
| Average price, **busiest** weeks | **£8.22** |
| Average price, **quietest** weeks | **£8.03** |
| → **+6.3% higher across the full transaction base** exactly when demand peaks *(+2.4% on the eligible panel — the SKUs with the most price movement, where the confounding is mildest)* | |
| Products whose price correlates **positively** with store traffic | **63%** *(random pricing → ~50%)* |
| Median product sells | **2 units per week** |
| Product-weeks selling ≤2 units | **62%** |

**Two fatal problems, compounding.** The price signal is contaminated, *and* there's almost no demand variation to explain — you cannot detect a 10% demand change inside a number that flickers between 1 and 2.

**The wreckage:** median elasticity **−0.61** against a published retail benchmark of **−2.62** (Bijmolt, Van Heerde & Pieters, 2005 — a meta-analysis of 1,851 elasticities across 81 studies). **38% of products came out positive.**

**The baseline test that settled it.** Held out the last 12 weeks; given a price the model never saw, predict the units that actually sold:

| Model | Error (Poisson deviance) ↓ | |
|---|---|---|
| No price effect (e = 0) | 1.158 | — |
| **Literature elasticity (−2.62)** | **2.266** | ❌ *twice as bad as assuming price is irrelevant* |
| **Pooled from our data (−0.42)** | **1.132** | ✅ *best — by a whisper* |
| Per-SKU raw | 1.153 | |
| **Per-SKU Bayesian (my proposal)** | **1.263** | ❌ *worse than doing nothing* |

**Both failures were my own ideas.** The baseline caught them. That's what baselines are for.

### 2. So the honest optimizer mostly says "I don't know"

Every product is sorted by **what we actually know about it:**

| Tier | Meaning | Products |
|---|---|---|
| **A** | Confidently **elastic** → optimise properly | **20** |
| **B** | Confidently **inelastic** → raise toward the ceiling | **4** |
| **C** | **Unknown** — can't tell if raising price wins or loses | **7** |
| **D** | **Broken** — demand slopes *upward*. Estimate refused. | **108** |

**115 of 139 products (83%) land in "unknown" or "broken."** The optimizer refuses to price them.

And the opportunity we *can* measure:

```
Projected annual lift:   £1,560
Honest uncertainty:      −£135 to +£4,258     ← IT CROSSES ZERO
```

**After all that work, on the best-behaved products in the store, the prize is statistically indistinguishable from nothing.** That is the correct answer, and almost nobody reports it.

**Three guardrails, each because something broke without it:**

1. **Never price outside the observed range.** Beyond it we're extrapolating a curve we've never seen.
2. **Never move more than ±15% in one step.** A price is a relationship, not a variable.
3. **Never optimise a product whose elasticity we can't pin down.** Tiers C and D get *no recommendation* — they get a **work order**.

### 3. So you have to TEST

**A deliberate price change is the only thing that breaks the confounding.**

The loop moves a price **on purpose** — not because the store is busy, not because it's Christmas, but *to find out*. That single act severs the link between price and the hidden reasons demand moves. **It manufactures the missing ingredient your history never had.**

Then it observes what sold, updates its belief, re-optimises, and does it again.

```
act → observe → learn → re-optimise → act …
```

### 4. What testing can and can't buy you

**20 independent replications, 104 weeks, 30 products:**

- **STATIC loses money in 75% of runs.** This is what a normal pricing project ships: confident prices, wrong direction, negative return.
- **The CLOSED LOOP reliably beats it: +2.7pp, 95% CI [+0.9, +4.8], winning 100% of replications.** The elasticity error falls from 2.09 to 1.32 — **the system corrects itself.**
- **The ORACLE captures +10.2%.** The prize is real. **The loop just can't reach it in two years at this store's volume.**

---

## 🔑 Volume is the currency of experimentation

**You cannot price-test a product nobody buys.**

| | Final elasticity error |
|---|---|
| Low volume (<3 units/week) | **1.27** |
| High volume (>8 units/week) | **0.61** — *half* |

With 2 units a week, random fluctuation swamps a 10% demand change — you'd need *years* to hear the signal.

**The operator's entry condition: run price tests on the products that actually move. Leave the long tail alone.** That's where the +10.2% is reachable.

---

## ⚠️ What's real and what's simulated

**This boundary is the most important thing in the repo. Read it before believing any number.**

**REAL — measured from the data:**
- Every price, unit and product — **131,706 real transactions**
- The confounding evidence (prices higher in busy weeks)
- The elasticity estimates *and their failure against the published benchmark*
- The baseline test on held-out weeks
- Each product's price, price range, baseline demand, and Poisson noise
- **The loop's starting belief** — the real, confounded estimate a business actually walks in with

**SIMULATED — and it has to be:**
- **The demand response to prices the store never charged.**
- If a store never sold a product at £8.20, **no dataset on earth contains how many units it would have sold at £8.20.** Counterfactuals are not observable. Not by me, not by anyone.
- So each product is given a true elasticity (drawn near the −2.62 benchmark) and the loop must discover it.

**This is the load-bearing assumption of the loop.** It does **not** prove *"these are the right prices for this store."* It **does** prove *the mechanism works*: a system starting from a belief we know is wrong, which sets prices deliberately and updates on what it sees, converges toward the truth and reliably beats trusting your data.

**The mechanism is the deliverable. The numbers inside it are a testbed.**

---

## Run it

```bash
pip install -r requirements.txt
# place scanner_data.csv in data/raw/ (see below)
python run.py       # data → elasticity → optimizer → loop → dashboard
open docs/index.html
```

**Data:** [Retail Store Sales Transactions (Scanner Data)](https://www.kaggle.com/datasets/marian447/retail-store-sales-transactions) on Kaggle. Download, unzip, and place `scanner_data.csv` in `data/raw/`.

---

## Decision log — including every bug I caught in my own system

**This section is the credibility of the project.** A system that never caught itself being wrong hasn't been looked at hard enough.

### Bugs I shipped and then caught

**1. The optimizer put its most broken numbers at the top of the list.**
My first tiering had no Tier D. Products with *upward-sloping* demand (positive elasticity — nonsense) got classed **"confidently inelastic."** And since raising the price of an upward-sloping demand curve looks *infinitely profitable*, they shot **straight to the top of the recommendations**: *"+£740, +£543, +£487."* **The most confident advice in the system was built on its most broken estimates.** Now refused by a hard guardrail.

**2. The loop couldn't learn, because it stood still.**
Thompson sampling kept pricing at the optimum it currently believed in — and then *sat there*. But **a demand curve can only be identified from price *variation*.** Standing still teaches you nothing, no matter how good the maths. Error fell just 7% in a year. Fixed by adding **deliberate exploration** — which is exactly what a real price test is.

**3. Then it learned, and lost money.**
My exploration probed a **random price anywhere across a ±25% band.** Half the probes sat far from the optimum, and the loop underperformed doing nothing. **That is not how a real price test works, and it's not how you spend a customer's goodwill.** A real test is a **±8% nudge** — enough to move demand measurably, cheap enough that being wrong barely costs anything. **Same information, a fraction of the price.**

**4. A chart that said "IT PAYS" when it didn't.**
The convergence figure's third panel was titled *"3. IT PAYS."* The loop **did not** beat doing nothing. I replaced it with the replicated result — bars, error bars, and a title that tells the truth. **A chart title is a claim. It has to survive the same scrutiny as a number.**

**5. My own headline methods failed the baseline test.**
I proposed a Bayesian model with the literature elasticity as a prior — a principled, standard, industry approach. **It scored worse than assuming price doesn't matter.** So did the literature value itself. Both were killed by a held-out test I built specifically to be able to kill them.

### Design choices

**Why the elasticity is estimated at the SKU level with a grouping estimator.** Weekly demand is small counts, so a naive log-log regression is dominated by Poisson noise. I use Wald's (1940) grouping estimator: bin weeks by price, average demand within each bin, fit through the bin means. Averaging suppresses count noise; grouping suppresses attenuation from noisy prices. It's the classical fix for exactly this failure.

**Why price is measured only from single-unit purchases.** `unit_price = Sales_Amount ÷ Quantity` puts Quantity on *both sides* of the regression — any noise manufactures a fake elasticity out of pure arithmetic (**division bias**). 78% of rows are single-unit, where no division happens. Price comes from those rows only; units come from all of them.

**Why gross margin is assumed (30%) and adjustable.** **The dataset has zero cost data.** No COGS, no wholesale price, nothing. So margin is a load-bearing assumption a real brand would supply from its own P&L — same discipline as the save rate in the churn project.
**But the direction of the advice is earned, not assumed.** The elasticity comes from observed behaviour. Sweeping margin from 20% to 50% changes every £ figure and leaves ~93% of price-move *directions* unchanged. **"Raise the price" is earned. "It's worth £42k" is rented.**

---

## Honest limitations

- **The counterfactual demand response is simulated.** See the boundary section above. This is the single biggest caveat and it is unavoidable — nobody can observe demand at a price that was never charged.
- **The measurable opportunity from historical data is not statistically distinguishable from zero.** I report it anyway, with the band that crosses zero.
- **Gross margin is assumed.** No cost data exists.
- **The loop only breaks even against doing nothing at this store's volume.** It reliably beats *trusting the data* — but the full prize needs products that sell.
- **Only 139 of 5,242 products have enough price movement and sales to fit a curve at all.** 44% of products never changed price once.
- **The store is small.** The median product sells 8 units in a *year*. A larger retailer would learn far faster.

---

## Why this transfers

### It closes the loop the first two projects didn't

| | [Predictive maintenance](https://feraselghandour.github.io/predictive-maintenance/) | [Customer churn](https://feraselghandour.github.io/customer-churn-intelligence/) | **Pricing (this)** |
|---|---|---|---|
| Observe | sensors | purchase history | scanner data |
| Predict | cycles to failure | probability of churn | demand curve |
| Decide | fix / watch / leave | who's worth saving | what price to charge |
| Act | mechanic goes | offer is sent | **price changes** |
| **Measure** | ✗ | ✗ | **✅ observe demand** |
| **Learn** | ✗ | ✗ | **✅ update the estimate** |
| **Re-optimise** | ✗ | ✗ | **✅ and go again** |

The first two systems **made a decision and never found out whether it was right.** For maintenance and churn you can survive that — the ground truth eventually arrives on its own. **For pricing you cannot**, because the ground truth *only exists if you go and create it*. That's what forced the loop, and it's why this project is the third one.

### How this applies to a real brand

1. **Check whether your price variation is confounded — before you model anything.** Correlate your price changes against your own traffic/seasonality. If prices moved *with* demand, your elasticity is contaminated and no model will fix it. This takes an hour and it will save you from a confident, expensive mistake.
2. **Expect the honest answer to be "I don't know" for most of your catalogue.** That's not failure. A precise list of *what you don't know* is a work order.
3. **Run price tests where you have volume.** Pick your top-selling SKUs. Nudge ±5–10%, not ±25%. Hold for enough weeks to see through the noise. **Leave the long tail alone — you'll never hear the signal.**
4. **Feed the results back.** One test is a data point. A loop is a system.
5. **Get your real COGS.** Every £ figure here is scaled by an assumed margin. Yours are on your P&L.

**The reusable asset is the method — and the discipline to say "I don't know" when that's the true answer.**

---

## Repo structure

```
├── data/raw/               scanner_data.csv (download from Kaggle — see above)
├── src/
│   ├── data.py             Box 1 — clean, derive unit price, COGS check, eligibility
│   ├── elasticity.py       Box 2 — the demand curve, and PROOF the data can't give one
│   ├── optimize.py         Box 3 — the optimizer, and what it refuses to do
│   ├── loop.py             Box 4 — THE CLOSED LOOP: act → observe → learn → re-optimise
│   └── dashboard.py        Box 5 — build the static dashboard
├── reports/                why_the_data_lies.png, the_loop.png, sensitivity, sweeps
├── docs/index.html         the deployed dashboard (GitHub Pages)
└── run.py                  one command, whole system
```

**References:** Bijmolt, T.H.A., Van Heerde, H.J. & Pieters, R.G.M. (2005), *New Empirical Generalizations on the Determinants of Price Elasticity*, Journal of Marketing Research — meta-analysis, mean elasticity −2.62. Tellis, G.J. (1988) — mean −1.76. Wald, A. (1940) — the grouping estimator for errors-in-variables.

---

### About

Built by **Feras Elghandour** — part of a series on building intelligent systems that solve real-world problems.

🔗 [GitHub](https://github.com/FerasElghandour) · [Predictive Maintenance](https://feraselghandour.github.io/predictive-maintenance/) · [Customer Churn](https://feraselghandour.github.io/customer-churn-intelligence/) · [Site](https://tenx-gc.com)
