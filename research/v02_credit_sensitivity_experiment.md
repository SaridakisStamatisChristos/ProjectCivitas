# CIVITAS v0.2 — Matched savings × firm-density × loan maturity research

**Status:** complete exploratory *synthetic* simulation campaign; local execution. **Not a real-economy forecast.**

- **Design:** 2 firm densities (10 or 20 firms/sector, 30 or 60 firms total) × 2 savings propensities (25%, 75%) × 3 financing settings (credit disabled, interest-free two-period principal contracts, interest-free six-period contracts).
- **Execution:** 8 seeds (1–8), 10,000 agents, 24 abstract economic periods: **96 complete simulations / 2,304 audited period states**.
- **Environment:** Python 3.13.5, NumPy 2.3.5, Linux x86_64. The runnable source and `research/v02_credit_sensitivity_10000/` preserve the analysis.
- **Control:** within each density/savings cell, three financing arms share a byte-level hash of all initial simulation state arrays and the RNG state. Across firm densities, total initial **firm cash** (1,200,000 cents), **physical capital** (1,200 units), 10,000 agents, and natural resources (5,000,000 units) are identical, but firm identities, ownership assignments, market interactions and per-firm endowments are not.
- **Credit mechanism:** only existing household cash reserves fund firm purchases of tangible goods. Repayments are bilateral monetary transfers; defaults extinguish matching claims/liabilities without minting or destroying money. Loan rates are zero by explicit simplifying assumption.

## Final-period sample means and total credit flows

Values in the production columns are *last-period production units per simulation*, averaged over the eight seeds. Loan flows are **total cents over all 8 seeds and 24 periods**, not averages.

| Total firms | Savings | No-credit production | 2-period production | 6-period production | No-credit originations | 2-period originations | 6-period originations | No-credit defaults | 2-period defaults | 6-period defaults |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 30 | 25% | 1,324.75 | 2,120.50 | 2,121.38 | 0 | 18,450,980 | 18,469,703 | 0 | 6,181,837 | 0 |
| 30 | 75% | 1,618.25 | 1,490.62 | 1,569.25 | 0 | 22,135,670 | 22,915,223 | 0 | 11,194,660 | 2,044,344 |
| 60 | 25% | 1,978.25 | 2,006.00 | 2,034.38 | 0 | 20,986,949 | 21,644,071 | 0 | 9,255,143 | 1,006,507 |
| 60 | 75% | 1,807.00 | 1,537.00 | 1,575.38 | 0 | 22,574,432 | 23,504,986 | 0 | 12,860,051 | 3,833,390 |

## Matched treatment differences (credit minus no credit)

The approximate intervals use `mean(paired differences) ± 1.96 × sample SD / sqrt(8)`; they describe random-seed Monte Carlo variability **conditional on one model specification**, not uncertainty about economic reality. They were not adjusted for multiple exploratory comparisons.

| Credit treatment minus its matching control | Production difference | Approximate 95% MC interval | Disposable-income Gini difference |
|---|---:|---:|---:|
| density10_savings25_term2_minus_control | +795.75 | [+762.52, +828.98] | -0.0770 |
| density10_savings25_term6_minus_control | +796.62 | [+764.08, +829.17] | -0.0771 |
| density10_savings75_term2_minus_control | -127.62 | [-170.23, -85.02] | +0.0401 |
| density10_savings75_term6_minus_control | -49.00 | [-88.76, -9.24] | +0.0312 |
| density20_savings25_term2_minus_control | +27.75 | [+10.08, +45.42] | +0.0145 |
| density20_savings25_term6_minus_control | +56.12 | [+33.96, +78.29] | +0.0106 |
| density20_savings75_term2_minus_control | -270.00 | [-287.22, -252.78] | +0.0502 |
| density20_savings75_term6_minus_control | -231.62 | [-265.74, -197.51] | +0.0450 |

## Findings and scientific interpretation

1. **Nonmonotonic and regime-dependent effects:** a 25%-saving rule combined with available credit yielded higher final production in both density settings. Under 75%-saving rules, credit was associated with *lower* production. The simulator has no empirically calibrated credit supply curve or lending rates. Results can arise from budget-constrained demand, loan funding diverted from household reserves, defaults, sector-specific capital inventory and the firm hiring rule. This experiment does not isolate those intermediate pathways independently.
2. **Loan maturity changes losses and outstanding claims:** two-period settings produced extensive defaults. Six-period settings generally had lower recorded defaults and higher final production, but different outstanding debt stock and horizon censoring matter. Direct policy inference would be inappropriate.
3. **The market structure effect remains large:** equal initial total firm capital and cash do not make 30- and 60-firm market structures equivalent. Per-firm scale, competition and ownership assignment differ. Cross-density comparisons must be called *structural sensitivity*, not an isolated firm-count causal effect.
4. **Eight seeds cannot validate a social-scientific claim.** These results are evidence that the program is executable and that the same parameter intervention has different signs under different implemented assumptions.

## Software correctness and limitations

- For each of the **2,304 recorded periods**, eight conservation/accounting discrepancy metrics were checked as exactly zero: money, resource, goods, capital, household cash flow, firm cash flow, historical-cost book equity and loan asset/liability matching.
- All **96 simulations** start deterministically from their seed and parameter definition; initial-state SHA-256 matching is recorded within treatment triples.
- Each seed shard is saved through atomic rename and content SHA-256, with an environment/source digest. Final aggregation rejects a missing seed, altered configuration, changed research source, broken period sequence or invalid accounting metric.
- **Important open limitations:** no interest, inflation-linked loans, banks, credit risk pricing, deposit insurance, endogenous interest-rate choice, calibrated bankruptcy proceedings, firm entry, inventory FIFO, population aging, historical calibration or long-run equilibrium proof. No formal proof eliminates all signed-int64 overflow risks under arbitrary extreme states.
- **Preservation:** all 8 seed files and `summary.json` belong under `research/v02_credit_sensitivity_10000/` and are included in the complete local archive. The stable v0.1 `main` branch is not modified.

## Reproduction

```bash
python -m pip install -e '.[test]'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q
for seed in 1 2 3 4 5 6 7 8; do
    PYTHONPATH=src:. python research/run_credit_sensitivity.py --seed "$seed" --population 10000 --steps 24 --output research/v02_credit_sensitivity_10000
done
PYTHONPATH=src:. python research/run_credit_sensitivity.py --finalize --seeds 1,2,3,4,5,6,7,8 --population 10000 --steps 24 --output research/v02_credit_sensitivity_10000
```

## Next falsification tests

Expand seed count, sweep firm capital-purchase budgets and lender availability independently, track endogenous outstanding loans and resource usage over longer horizons, and separately analyze firm matching/consumption feedback. Profile loan-contract growth with population scaling. Make **no** release claim for v0.2 until these and the remaining historical-cost/finance audits are addressed.
