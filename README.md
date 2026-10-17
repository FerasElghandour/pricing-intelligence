# Pricing Intelligence and Sequential Experimentation

**Feras Elghandour**

Assess whether transaction history supports useful price decisions, then compare static and sequential pricing strategies under explicit simulation assumptions.

**[Explore the evidence report](https://feraselghandour.github.io/pricing-intelligence/)** · [Simulation record](artifacts/loop_metrics.json) · [Elasticity analysis](artifacts/elasticity_findings.json) · [Operating scope](OPERATIONS.md)

[![Pricing strategy comparison](assets/demo-preview.png)](https://feraselghandour.github.io/pricing-intelligence/)

## Problem and implementation

Historical prices can move with demand conditions, making an observed price-sales association unreliable as a causal elasticity estimate. Sparse product sales also limit the information available for experimentation.

The implementation analyzes a transaction panel, compares elasticity baselines, withholds unsupported recommendations, and simulates sequential price experiments with updating beliefs and bounded price changes.

## Recorded findings

| Strategy | Mean margin vs unchanged prices |
|---|---:|
| Static estimated-price policy | −3.21% |
| Sequential experiment loop | −0.52% |
| Oracle with true simulated demand response | +10.24% |

The saved loop experiment contains **20 simulation replications**, 30 products and 104 weekly rounds. The loop improves on static by **2.69 percentage points on average** and wins the pairwise comparison in **20/20** recorded replications. It remains below unchanged pricing on average. The former “100/100” wording confused a percentage with the replication count and is corrected here.

An exploratory price-traffic association is consistent with confounding; it does not by itself prove a causal mechanism. Counterfactual demand at unobserved prices is simulated. The oracle has information the deployable policies do not possess. No real price experiment or client margin improvement is claimed.

## Reproduce

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

The original transaction input is acquired separately as described by the source loader. Use `python build_report.py` to rebuild the public report from retained aggregate findings. The report requires no server-side runtime and publishes no customer-level records.

## Practical relevance and operating limits

The project shows when to withhold a pricing recommendation and how to compare an experiment policy with an unchanged-price baseline. Deployment requires randomized testing with suitable volume, a justified causal design, approved constraints, monitored margin outcomes, and rollback. The public edition is an analysis and simulation, not an autonomous live-pricing service.

[Portfolio](https://feraselghandour.github.io/) · [Professional inquiries](https://www.linkedin.com/in/feras-elghandour/)
