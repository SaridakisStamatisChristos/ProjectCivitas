# CIVITAS v0.2 — Price/hiring interaction and 72-period contraction

**Research status:** executed within-model experiment, not empirical validation. 13 November 2026. Development version `0.2.0.dev0`.

## Questions and design

- **H1:** Restricting stockout price increases using an explicit end-of-period affordability threshold changes the magnitude of the simulated late contraction.
- **H2:** A hiring expectation that averages stationary and adaptive demand changes the late contraction.
- **H3:** Price and hiring interventions interact, so their combined effect need not equal the sum of single effects.
- **H4:** These results are sensitive to the population/endowment regime and may fail to transfer across model configurations.

A fully crossed **2 price rules × 3 hiring rules** factorial was executed with **eight matched seeds (1–8) at each of 2,000 and 10,000 agents**, each for **72 abstract periods**. Total: **96 completed simulations / 6,912 audited periods**. Within each population regime all six arms shared exact seed-specific initial agents, ownership, firm cash, capital, natural resources, and initial RNG state. The end RNG digest also matched across arms for every seed. The 2,000 versus 10,000 regimes are **not per-capita-normalized**; firms per sector and several initial quantities remain identical, so cross-regime differences cannot be interpreted as effects of population alone.

Each treatment has SHA-256-checked raw period-level records, a digest of all behavior-defining source files, configuration hashes, and verified conservation of money, goods, capital, resources, household flows, firm flows, firm book equity and loan claims. The independent recount does not reuse the runner's aggregation functions.

## Results: mean production units

| Rule configuration | 10,000 agents, t24 | t48 | t72 | 2,000 agents, t24 | t48 | t72 |
|---|---:|---:|---:|---:|---:|---:|
| Historical inventory + adaptive hiring | 1,324.75 | 661.38 | 160.00 | 310.88 | 160.38 | 110.00 |
| Historical inventory + blended hiring | 1,456.88 | 997.38 | 511.63 | 349.00 | 209.38 | 194.13 |
| Historical inventory + stationary hiring | 1,516.50 | 1,143.63 | 673.88 | 370.25 | 248.88 | 208.38 |
| Affordability guard + adaptive hiring | 1,402.38 | 701.63 | 210.00 | 309.00 | 150.63 | 117.75 |
| Affordability guard + blended hiring | 1,481.13 | 1,002.25 | 604.50 | 347.25 | 210.63 | 208.75 |
| Affordability guard + stationary hiring | 1,546.50 | 1,141.50 | 762.25 | 370.63 | 249.50 | 200.50 |

All six 10,000-agent configurations continued contracting between periods 24 and 72. Alternative feedback rules moderated the decline; **they did not eliminate it**. The 10,000-agent historical control mean production reached **160 units by t72**, while its mean budget-unmet share of attempted consumer purchases reached **96.6%**, even with abundant remaining natural-resource stock (mean **5.75 million** units). Under guarded pricing and stationary hiring the t72 production was **762.25 units**, with budget-unmet share **84.6%**. These are endpoints, not time averages and not real-world welfare scores.

## Paired effects and interaction at period 72

| Contrast (guard minus historical pricing, fixed hiring rule) | 10,000 mean [95% approximate seed-MC interval] | 2,000 mean [95% approximate seed-MC interval] |
|---|---|---|
| Adaptive | +50.00 [+31.90, +68.10] | +7.75 [+0.96, +14.54] |
| Blended | +92.88 [+64.79, +120.96] | +14.63 [+6.82, +22.43] |
| Stationary | +88.38 [+72.73, +104.02] | −7.88 [−16.13, +0.38] |

The **price×blended-hiring** interaction (change in the pricing effect relative to adaptive hiring) was **+42.88** units [17.86, 67.89] at 10,000 agents, but only **+6.88** units [−0.50, 14.25] at 2,000 agents. The **price×stationary-hiring** interaction was +38.38 [14.88, 61.87] at 10,000 agents and −15.63 [−25.14, −6.11] at 2,000 agents.

Intervals are approximate `mean ± 1.96 × sample_sd / √8` and quantify **Monte Carlo seed uncertainty conditional on one set of simulator rules**, not model uncertainty or historically calibrated policy effects. These are exploratory multiple comparisons with no correction for multiple testing; eight seeds are a small basis for inference.

## Reproducibility

```bash
python -m pip install -e '.[test]'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q
for seed in 1 2 3 4 5 6 7 8; do
  PYTHONPATH=src:. python research/run_price_hiring_stability.py --seed "$seed" --population 10000 --steps 72 --output research/v02_price_hiring_10000_72
done
PYTHONPATH=src:. python research/run_price_hiring_stability.py --finalize --population 10000 --steps 72 --seeds 1,2,3,4,5,6,7,8 --output research/v02_price_hiring_10000_72
PYTHONPATH=src:. python research/audit_price_hiring_stability.py research/v02_price_hiring_10000_72
```

Repeat with `--population 2000 --output research/v02_price_hiring_2000_72` for the other regime. `--verify-only` validates saved shards and recreates statistics without writing. The research folders are also preserved in compressed **`.tar.xz`** archives (`research/v02_price_hiring_10000_72_raw.tar.xz` and `research/v02_price_hiring_2000_72_raw.tar.xz`). These use solid compression of plain JSON records. Restore and verify them with:

```bash
PYTHONPATH=src:. python research/restore_price_hiring_stability.py research/v02_price_hiring_10000_72_raw.tar.xz results/restored_price_hiring_10000
```

The independent auditor runs during restoration; it fails closed if data are altered, missing, invalid, or from a different software revision. Existing output directories are never overwritten. A complete downloadable source+data archive is provided separately.

## What this experiment does **not** establish

This is not evidence for optimal pricing or public policy. No income elasticity model, household adaptive expectations, endogenous wage contracts, inflation targeting, balance sheet solvency study or empirical calibration has been added. Price affordability uses a coarse global end-period household statistic. Real trade frictions, search costs and firm entry remain absent. Model structure and seed uncertainty are distinct. The strong multi-period contraction under *all* rules suggests that additional labor/demand/finance mechanisms warrant separate falsification experiments rather than simply selecting the arm with the highest output.

**Next gate:** sensitivity to affordability threshold and initial cash distributions; test with normalized capital/firm density across populations and multiple price-adjustment magnitudes. Maintain historical default regression. Do not promote v0.2 to `main` before the financial, statistical and empirical-validation gates have been reviewed.
