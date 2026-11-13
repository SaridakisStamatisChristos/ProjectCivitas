# CIVITAS v0.2 — Long-horizon demand and liquidity diagnostics

**Status:** executed scientific-model instrumentation, not a calibrated macroeconomic theory. One step is an abstract simulation period. Results do not establish outcomes for human economies.

## Motivation and research questions

The credit-pathways experiment documented a large decline in production between periods 24 and 48 **even without lending**. Natural resource stock was not exhausted. The diagnostic suite tests which of the modeled mechanisms can account for that decline using the **same seeded population, firm assets, and RNG stream** for each treatment.

The purpose is **falsification**, not choosing a desired outcome. The experiment retains unchanged state-transition equations in `src/civitas/engine.py`: intervention inputs use existing declared scenario parameters. Diagnostics are computed *after* each step and never influence decisions.

## Formally defined measurements

Let `C_h(t)` be a household's spendable cash, `B_h(t)` its reserve cash, `F_f(t)` firm cash, `G(t)` government cash, `P_f(t)` posted selling price and `I_f(t)` physical inventory. For the fixed-money universe of this experiment:

`M = sum_h(C_h+B_h) + sum_f(F_f) + G`, unchanged each period.

The study records these independently computed measurements:

- **Household spendable cash**: `sum_h C_h`; **savings**: `sum_h B_h`; **household monetary assets**: their sum (never double count reserves).
- **Firm cash share**: `sum_f F_f / M` (not a measure of economic concentration, profitability, or household wealth).
- **Finished-goods inventory**: `sum_f I_f`.
- **Nonessential basket affordability diagnostic**: equal-weight mean, over households and nonfood sectors, of the indicator `C_h >= min(P_f in sector)`. It is a *post-step* observation; it does not account for seller quote availability, inventory shortages, preferences, or the time of an attempted purchase. It is not a welfare score.
- **Food affordability diagnostic**: post-step household cash plus separately accessible emergency reserve, compared with the lowest food quote; same limitations.
- **Budget unmet fraction**: `budget_unmet / (consumption + budget_unmet + stock_unmet)` using attempted one-bundle purchases, when the denominator is nonzero. Unlike a national consumption measure, this is a diagnostic of the simulator's decision rule. It depends on how the simulator classifies an unsuccessful attempt.
- **Endogenous observables**: period goods production, purchases, paid employment, aggregate capital, common renewable resource stock, quoted mean prices, wage/dividend/sales transfers and inventory balances.

All physical and financial conservation constraints are asserted each period. No counterfactual treatment introduces money, creates goods, or changes the initial endowment.

## Controls and intervention parameters

Use the exact 10,000-agent `s25_control` configuration from `research/run_credit_pathways.py`: 30 firms, three sectors, households save 25% of disposable income, historical-cost accounting enabled, credit off, initial common resource 5,000,000, resource capacity 6,000,000, 48 periods. Eight master seeds 1–8.

| Name | Single change against control | Mechanism probed |
|---|---|---|
| `control` | none | historical combination |
| `no_saving` | household saving propensity 25% → 0% | reserve segregation |
| `full_dividends` | distribute 100% rather than 65% of positive cost-basis earnings, subject to cash | profit-based cash distribution |
| `fixed_prices` | set posted-price adjustment 0 rather than 0.02 | endogenous price feedback |
| `stationary_hiring` | replace sales-responsive hiring expectations with stationary expected demand | hiring feedback |
| `no_depreciation` | remove physical capital depreciation | capital decay |

For each seed, all arms have the same initial-state fingerprint, and because the engine consumes fixed-shape random draws, the same end-of-run RNG fingerprint. **The downstream states diverge once interventions take effect**; these are matched *within-model* contrasts, not matched unit-level observations of real people.

## Reproduction and audits

```bash
python -m pip install -e '.[test]'
PYTHONPATH=src:. python -m pytest -q
for seed in 1 2 3 4 5 6 7 8; do
    PYTHONPATH=src:. python research/run_demand_diagnostics.py --seed "$seed" \
      --population 10000 --steps 48 --output results/demand_diagnostics
done
PYTHONPATH=src:. python research/run_demand_diagnostics.py --finalize \
    --seeds 1,2,3,4,5,6,7,8 --population 10000 --steps 48 \
    --output results/demand_diagnostics
python research/audit_demand_diagnostics.py results/demand_diagnostics
```

Each completed cell persists as deterministic gzip-wrapped canonical JSON with SHA-256 over the uncompressed record, source hash, initial state, end RNG, 48 period rows, model configuration digest and exact monetary/physical discrepancy fields. Cell-level saving allows safe resumption after interrupted runs. The independent auditor is standard-library only and separately recomputes conservation checks, stored averages and paired-effect arithmetic.

Approximate 95% Monte Carlo intervals equal `mean(paired difference) ± 1.96 * sample_SD / sqrt(n)` and capture **seed-level random variation under the specified equations**; they do not capture parameter uncertainty, structural model error, real-world forecasting error or multiple-testing corrections. Eight seeds are exploratory, not a power-justified research sample.

## Interpretation restrictions

An improved outcome under fixed prices does not make fixed pricing a proven solution. The intervention changes firms' revenue, capital procurement, hiring and household liquidity in subsequent periods. The posted price mean may decline later even after earlier inflation, because prices respond to unsold stock. A full mechanism decomposition would require additional path-specific interventions and micro-level event attribution, followed by robustness to alternative behavioral models. There is no real-world calibration.

The GitHub repository additionally preserves the full raw 48-cell experiment in `research/v02_demand_diagnostics_raw.zip` (ZIP members are individual checksum-protected `.json.gz` files and `summary.json`). Run:

```bash
PYTHONPATH=src:. python research/restore_demand_diagnostics.py research/v02_demand_diagnostics_raw.zip results/restored_demand
python research/audit_demand_diagnostics.py results/restored_demand
```

The restoration code checks expected member names, refuses overwrites, validates all archived checksums and recomputes every experiment statistic.
