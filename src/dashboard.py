"""
BOX 5 — ACTION: the dashboard

Static HTML. No server, no cold start, no sleeping. Predictions are computed in a
batch, so nothing here needs a live Python process to answer a request.

The page leads with the honest headline, not with a fake opportunity number:

    "Your pricing data will lose you money if you trust it.
     Testing beats trusting — reliably.
     But you can only test what actually sells."

Most pricing dashboards open with a big confident £ figure. Ours opens with the
reason you shouldn't believe one.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

AUTHOR = "Feras Elghandour"
AUTHOR_LINK = "https://github.com/FerasElghandour"

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
background:#0f1216;color:#e8ecf1;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:32px 20px 80px}
header{border-bottom:1px solid #232a33;padding-bottom:22px;margin-bottom:26px}
h1{font-size:26px;font-weight:650;letter-spacing:-.01em}
.sub{color:#8b97a6;margin-top:8px;font-size:15px}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:#8b97a6;
margin:40px 0 14px;font-weight:700}
.step{display:inline-block;background:#232a33;color:#8b97a6;font-size:11px;font-weight:700;
padding:2px 8px;border-radius:4px;margin-right:8px;letter-spacing:.05em}
.hero{background:#151a21;border:1px solid #232a33;border-radius:10px;padding:26px 28px}
.headline{font-size:27px;font-weight:680;letter-spacing:-.02em;line-height:1.3}
.headline .bad{color:#f85149}.headline .good{color:#3fb950}
.hero p{color:#c3ccd7;font-size:15px;margin-top:14px}
.hero strong{color:#fff}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:22px}
.kpi{background:#0f1419;border:1px solid #232a33;border-radius:8px;padding:14px}
.kpi .v{font-size:24px;font-weight:680;letter-spacing:-.02em}
.kpi .l{font-size:12px;color:#8b97a6;margin-top:3px;line-height:1.35}
.good{color:#3fb950}.warn{color:#d29922}.bad{color:#f85149}.grey{color:#8b97a6}
.card{background:#151a21;border:1px solid #232a33;border-radius:10px;padding:20px 22px;
margin-bottom:12px;border-left:3px solid #2d3540}
.card.red{border-left-color:#f85149}.card.amber{border-left-color:#d29922}
.card.green{border-left-color:#3fb950}.card.blue{border-left-color:#4f81bd}
.card h3{font-size:17px;font-weight:640;margin-bottom:8px}
.card p{color:#c3ccd7;font-size:14.5px}
.card .ev{background:#0f1419;border:1px solid #232a33;border-radius:6px;padding:12px 14px;
margin-top:12px;font-size:13.5px;color:#8b97a6}
.card .ev b{color:#e8ecf1}
.tiers{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.tier{background:#151a21;border:1px solid #232a33;border-radius:10px;padding:16px;
border-left:3px solid #2d3540}
.tier.a{border-left-color:#3fb950}.tier.b{border-left-color:#4f81bd}
.tier.c{border-left-color:#d29922}.tier.d{border-left-color:#f85149}
.tier .n{font-size:26px;font-weight:680}
.tier .t{font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:#8b97a6;margin-top:2px}
.tier .d2{font-size:12.5px;color:#6e7a89;margin-top:8px;line-height:1.45}
.race{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.rc{background:#151a21;border:1px solid #232a33;border-radius:10px;padding:18px;text-align:center}
.rc.lose{border-color:rgba(248,81,73,.4)}.rc.win{border-color:rgba(63,185,80,.4)}
.rc .n{font-size:30px;font-weight:700;letter-spacing:-.02em}
.rc .t{font-size:13px;font-weight:600;margin-top:4px}
.rc .d2{font-size:12px;color:#8b97a6;margin-top:7px;line-height:1.45}
.tbl{width:100%;border-collapse:collapse;font-size:14px}
.tbl th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.07em;
color:#6e7a89;padding:10px;border-bottom:1px solid #232a33;font-weight:600}
.tbl td{padding:11px 10px;border-bottom:1px solid #1a2028}
.tbl tr:hover td{background:#151a21}
.tbl .num{text-align:right;font-variant-numeric:tabular-nums}
.pill{font-size:11px;font-weight:650;padding:3px 9px;border-radius:999px;white-space:nowrap}
.pill.a{background:rgba(63,185,80,.14);color:#3fb950}
.pill.b{background:rgba(79,129,189,.16);color:#7aa6d6}
.up{color:#3fb950}.dn{color:#f85149}
.note{color:#6e7a89;font-size:13px;margin-top:10px;line-height:1.6}
.split{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.box{background:#0f1419;border:1px solid #232a33;border-radius:8px;padding:16px}
.box .h{font-size:12px;letter-spacing:.07em;text-transform:uppercase;font-weight:700;margin-bottom:8px}
.box ul{margin:0;padding-left:18px;color:#c3ccd7;font-size:13.5px;line-height:1.7}
footer{margin-top:46px;padding-top:20px;border-top:1px solid #232a33;color:#6e7a89;font-size:13px}
footer a{color:#8b97a6}
@media(max-width:840px){
 .kpis,.tiers,.race,.split{grid-template-columns:1fr 1fr}
 .wrap{padding:22px 14px 60px}
 h1{font-size:21px}.headline{font-size:21px}
 .hide-sm{display:none}
 .tbl td,.tbl th{padding:9px 6px}
}
"""


def money(x):
    return f"£{x:,.0f}"


def build():
    el = json.load(open(ART / "elasticity_findings.json"))
    op = json.load(open(ART / "optimizer_metrics.json"))
    lp = json.load(open(ART / "loop_metrics.json"))
    rec = pd.read_csv(ART / "recommendations.csv")

    conf = el["confounding"]
    est = el["estimates"]
    res = lp["results"]
    tiers = op["tiers"]
    a = op["assumptions"]

    bt = pd.DataFrame(el["baseline_test"])

    actioned = rec[rec.recommended_price.notna()].sort_values("projected_lift", ascending=False)
    rows = []
    for _, r in actioned.head(20).iterrows():
        cls = str(r.tier).lower()
        move = r.price_move_pct
        rows.append(f"""<tr>
<td><b>{r.SKU}</b></td>
<td><span class="pill {cls}">{r.tier}</span></td>
<td class="num">{r.elasticity:.2f}</td>
<td class="num hide-sm">{r.e_lo:.1f} to {r.e_hi:.1f}</td>
<td class="num">£{r.current_price:.2f}</td>
<td class="num">£{r.recommended_price:.2f}</td>
<td class="num {'up' if move>0 else 'dn'}">{move:+.1f}%</td>
<td class="num">{money(r.projected_lift)}</td>
<td class="num hide-sm grey">{money(r.lift_low)} to {money(r.lift_high)}</td>
</tr>""")

    bt_rows = "".join(
        f"<tr><td>{r.model.strip()}</td><td class='num'>{r.poisson_deviance:.3f}</td>"
        f"<td class='num' style='color:{'#3fb950' if r.beats_no_price_effect else '#f85149'}'>"
        f"{'beats it' if r.beats_no_price_effect else 'worse'}</td></tr>"
        for _, r in bt.iterrows())

    tier_defs = [
        ("a", "A", tiers.get("A", 0), "Confidently elastic", "We know the curve. Optimise properly."),
        ("b", "B", tiers.get("B", 0), "Confidently inelastic", "Price is too low. Raise toward the ceiling."),
        ("c", "C", tiers.get("C", 0), "Unknown", "Can't tell if raising price wins or loses."),
        ("d", "D", tiers.get("D", 0), "Broken", "Demand slopes UPWARD. Estimate refused."),
    ]
    tier_cards = "".join(
        f"""<div class="tier {c}"><div class="n">{n}</div><div class="t">Tier {t} · {lab}</div>
<div class="d2">{desc}</div></div>""" for c, t, n, lab, desc in tier_defs)

    unknown = tiers.get("C", 0) + tiers.get("D", 0)
    total_fitted = op["skus_fitted"]

    html = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pricing Intelligence — your pricing data is lying to you</title>
<meta name="description" content="Your sales history cannot tell you the right price. Here's the proof — and a closed-loop system that finds it by testing.">
<style>{CSS}</style>
</head><body><div class="wrap">

<header>
<h1>Pricing Intelligence — a closed-loop price optimiser</h1>
<div class="sub">Real retail scanner data · 131,706 transactions · 5,242 products · one year</div>
</header>

<div class="hero">
<div class="headline">Your pricing data will <span class="bad">lose you money</span> if you trust it.<br>
Testing <span class="good">beats trusting</span> — reliably.<br>
But you can only test <span class="good">what actually sells</span>.</div>

<p><strong>Every pricing project starts the same way:</strong> fit a demand curve to your sales
history, find the profit-maximising price, ship the dashboard. We did that. Then we checked
whether the answer was real — and it wasn't.</p>

<p>This system does the honest version instead: it proves the historical data is contaminated,
refuses to guess where it can't know, and then <strong>closes the loop</strong> — running deliberate
price experiments, measuring the response, updating its beliefs, and re-optimising.</p>

<div class="kpis">
<div class="kpi"><div class="v bad">{res['static']['mean']:+.1f}%</div>
<div class="l">Margin if you TRUST your data<br>(loses money in {100-res['static']['pct_beats_status_quo']:.0f}% of runs)</div></div>
<div class="kpi"><div class="v good">+{res['loop_minus_static']['mean']:.1f}pp</div>
<div class="l">The closed loop beats that<br>in {res['loop_minus_static']['pct_loop_wins']:.0f}% of replications</div></div>
<div class="kpi"><div class="v grey">{res['oracle']['mean']:+.1f}%</div>
<div class="l">The prize, if you knew the truth<br>(real, but volume-gated)</div></div>
<div class="kpi"><div class="v warn">{unknown}/{total_fitted}</div>
<div class="l">Products where the honest answer is<br>"I don't know — go test it"</div></div>
</div>
</div>

<h2><span class="step">STEP 1</span> Your sales data is confounded</h2>
<div class="card red">
<h3>Prices go UP when the store gets busy — so price and demand are tangled</h3>
<p>Umbrella prices rise when it rains. Umbrella sales rise when it rains. Your data now says
<em>"high price → high sales"</em>. The rain caused both, and <strong>"rain" is not a column in
the spreadsheet.</strong></p>
<div class="ev">
<b>Measured in this store:</b> across the full transaction base, prices are
<b>{conf['price_premium_full_book_pct']:+.1f}% higher in the busiest weeks</b> than the quietest —
exactly when demand peaks. (On the eligible panel — the products with the most price movement,
where the confounding is mildest — it is still <b>{conf['price_premium_in_busy_weeks_pct']:+.1f}%</b>.)
<b>{conf['pct_positive_corr']:.0f}%</b> of products have price positively correlated with store traffic
(random pricing would give ~50%).<br><br>
<b>And there's barely any demand to explain:</b> the median product sells
<b>{conf['median_units_per_sku_week']:.0f} units a week</b>;
<b>{conf['pct_sku_weeks_under_3_units']:.0f}%</b> of product-weeks sell 2 or fewer.
</div>
<div class="ev" style="margin-top:8px">
<b>The wreckage:</b> {est['pct_positive']:.0f}% of products come out with a <b>POSITIVE</b> elasticity —
customers apparently buying <em>more</em> as the price rises. Median estimate
<b>{est['median']:.2f}</b> against a published retail benchmark of <b>−2.62</b>
(Bijmolt, Van Heerde &amp; Pieters, 2005 — 1,851 elasticities, 81 studies).
</div>
</div>

<div class="card blue">
<h3>The baseline test that settled it</h3>
<p>Held out the last 12 weeks. Given the price actually charged in a week the model never saw,
predict the units that actually sold.</p>
<table class="tbl" style="max-width:520px;margin-top:12px">
<thead><tr><th>Model</th><th class="num">Error ↓</th><th class="num">vs "price doesn't matter"</th></tr></thead>
<tbody>{bt_rows}</tbody></table>
<div class="note">The literature benchmark made predictions <b>twice as bad</b> as assuming price is
irrelevant. A Bayesian model built on it was <b>worse than doing nothing</b>. Both were my ideas.
The baseline killed them.</div>
</div>

<h2><span class="step">STEP 2</span> So the honest optimizer mostly says "I don't know"</h2>
<div class="tiers">{tier_cards}</div>
<div class="note">
<b>{unknown} of {total_fitted} products ({unknown/total_fitted*100:.0f}%)</b> land in <em>unknown</em> or
<em>broken</em>. The optimizer refuses to price them — an unconstrained one would happily invent a
number and put it top of the list.
</div>

<div class="card amber" style="margin-top:12px">
<h3>And the opportunity we CAN measure is indistinguishable from zero</h3>
<div class="ev">
Projected annual lift across the {op['skus_actioned']} products we're willing to price:
<b>{money(op['projected_lift'])}</b><br>
Honest uncertainty band: <b>{money(op['lift_low'])} to {money(op['lift_high'])}</b>
— <b class="bad">it crosses zero.</b><br><br>
After all that work, on the best-behaved products in the store, we cannot statistically
distinguish the prize from nothing. <b>That is the correct answer, and almost nobody reports it.</b>
</div>
</div>

<h2>The prices we <em>are</em> willing to recommend</h2>
<table class="tbl">
<thead><tr>
<th>Product</th><th>Tier</th><th class="num">Elasticity</th><th class="num hide-sm">95% range</th>
<th class="num">Now</th><th class="num">Recommended</th><th class="num">Move</th>
<th class="num">Lift/yr</th><th class="num hide-sm">Honest range</th>
</tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<div class="note">Guardrails: never move a price more than <b>±{a['max_move']:.0%}</b>, and never outside
the range the product has actually been sold at. Gross margin is <b>ASSUMED at {a['gross_margin']:.0%}</b>
— the dataset has no cost data. The margin scales the £ figure; it does not choose the direction.</div>

<h2><span class="step">STEP 3</span> So you have to TEST</h2>
<div class="card green">
<h3>A deliberate price change is the only thing that breaks the confounding</h3>
<p>The loop moves a price <strong>on purpose</strong> — not because the store is busy, not because
it's Christmas, but <em>to find out</em>. That single act severs the link between price and the
hidden reasons demand moves. <strong>It manufactures the missing ingredient your history never had.</strong></p>
<p style="margin-top:10px">Then it observes what sold, updates its belief, re-optimises, and does
it again. <strong>Act → observe → learn → re-optimise.</strong> My first two projects stopped at
"decide" and never found out whether they were right. This one does.</p>
</div>

<h2><span class="step">STEP 4</span> What testing can and can't buy you</h2>
<div class="race">
<div class="rc lose"><div class="n bad">{res['static']['mean']:+.1f}%</div>
<div class="t">STATIC — trust your data</div>
<div class="d2">Set the "optimal" price once from history. Never look again.<br>
<b>Loses money in {100-res['static']['pct_beats_status_quo']:.0f}% of runs.</b><br>
This is what a normal pricing project ships.</div></div>

<div class="rc win"><div class="n good">{res['loop']['mean']:+.1f}%</div>
<div class="t">CLOSED LOOP — test &amp; learn</div>
<div class="d2">Beats STATIC by <b>+{res['loop_minus_static']['mean']:.1f}pp</b>,
95% CI [{res['loop_minus_static']['ci_low']:+.1f}, {res['loop_minus_static']['ci_high']:+.1f}] —
<b>winning {res['loop_minus_static']['pct_loop_wins']:.0f}% of replications.</b><br>
But roughly break-even vs doing nothing, at this store's volume.</div></div>

<div class="rc"><div class="n grey">{res['oracle']['mean']:+.1f}%</div>
<div class="t">ORACLE — knows the truth</div>
<div class="d2">The ceiling. <b>The prize is real.</b><br>
The loop just can't reach it in two years when products sell 2 units a week.</div></div>
</div>
<div class="note">{lp['replications']} independent replications, {lp['rounds']} weeks,
{lp['n_skus']} products. Elasticity error fell from <b>{lp['start_error']:.2f}</b> to
<b>{lp['end_error']:.2f}</b> — the system corrects itself.</div>

<div class="card amber" style="margin-top:12px">
<h3>Volume is the currency of experimentation</h3>
<p><strong>You cannot price-test a product nobody buys.</strong> With 2 units a week, random
fluctuation swamps a 10% demand change — you'd need years to hear the signal.</p>
<div class="ev">
low volume (&lt;3 units/wk): final elasticity error <b>1.27</b><br>
high volume (&gt;8 units/wk): final elasticity error <b>0.61</b> — <b>half</b><br><br>
<b>The operator's entry condition:</b> run price tests on the products that actually move.
Leave the long tail alone. That is where the {res['oracle']['mean']:+.1f}% prize is reachable.
</div>
</div>

<h2>What's real and what's simulated</h2>
<div class="split">
<div class="box"><div class="h good">REAL — measured from the data</div>
<ul>
<li>Every price, unit and product — 131,706 real transactions</li>
<li>The confounding evidence (prices +{conf['price_premium_in_busy_weeks_pct']:.1f}% in busy weeks)</li>
<li>The elasticity estimates and their failure against benchmark</li>
<li>The baseline test on held-out weeks</li>
<li>Each product's price, price range, baseline demand and Poisson noise</li>
<li>The loop's <em>starting belief</em> — the real, confounded estimate a business walks in with</li>
</ul></div>
<div class="box"><div class="h warn">SIMULATED — and it has to be</div>
<ul>
<li><b>The demand response to prices never charged.</b></li>
<li>If a store never sold that product at £8.20, <em>no dataset on earth</em> contains how many
units it would have sold at £8.20. Counterfactuals aren't observable.</li>
<li>So each product is given a true elasticity (drawn near the −2.62 benchmark) and the loop
must discover it.</li>
<li><b>This is the load-bearing assumption of the loop.</b> It does not prove "these are the right
prices." It proves <em>the mechanism works</em>: a system starting from a wrong belief converges on
the truth and beats trusting your data.</li>
</ul></div>
</div>

<footer>
Built by <a href="{AUTHOR_LINK}">{AUTHOR}</a> — part of a series on building intelligent systems
that solve real-world problems.<br>
Data: <b>Retail Store Sales Transactions (Scanner Data)</b>, Kaggle — 131,706 real line items,
5,242 SKUs, 2016. Gross margin is assumed ({a['gross_margin']:.0%}); the dataset has no cost field.<br>
Third in a series. <a href="https://feraselghandour.github.io/predictive-maintenance/">Predictive
maintenance</a> and <a href="https://feraselghandour.github.io/customer-churn-intelligence/">customer
churn</a> stopped at "decide". <b>This one closes the loop.</b>
</footer>

</div></body></html>"""

    out = DOCS / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}  ({len(html)/1024:.0f} KB, self-contained)")
    print(f"static {res['static']['mean']:+.1f}% | loop {res['loop']['mean']:+.1f}% | "
          f"oracle {res['oracle']['mean']:+.1f}% | unknown {unknown}/{total_fitted}")
    return out


if __name__ == "__main__":
    build()
