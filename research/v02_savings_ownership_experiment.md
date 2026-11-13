# CIVITAS v0.2 — Savings and ownership: executed factorial experiments

**Status:** reproducible synthetic experiments, 2026-11-13; not real-world economic forecasts or validated social science. The exact experimental rules, scenario JSON, analysis script, and output records are version controlled.

Six cases: ownership fractions 3% vs 8%, crossed with household savings propensities 0%, 15% and 30%. Thirty matched seeds per case at both 1,000 and 10,000 simulated agents, 24 abstract time periods per simulation. **360 complete runs, 8,640 verified periods**; the final period of each run is recorded and analyzed.

The savings balances are **non-interest-bearing, ring-fenced cash**; there is no bank and savings never automatically finance productive investment. Fixed baseline firm count, capital, company cash and resources are intentionally *not scaled* when the population changes, so inter-population comparisons are not structurally normalized.

## Final-period results (sample means)

### 1,000 agents

| Ownership | Saving rate | Employment | Production | Consumption | Disposable-income Gini | Modeled net-worth Gini | Savings stock (cents) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 3% | 0% | 11.41% | 108.9 | 105.2 | 0.7290 | 0.8253 | 0 |
| 3% | 15% | 11.70% | 111.7 | 104.3 | 0.7214 | 0.8229 | 641,362 |
| 3% | 30% | 11.38% | 109.0 | 105.5 | 0.7221 | 0.8206 | 1,039,737 |
| 8% | 0% | 11.94% | 113.9 | 108.4 | 0.7071 | 0.6636 | 0 |
| 8% | 15% | 12.36% | 118.3 | 111.8 | 0.6902 | 0.6616 | 634,346 |
| 8% | 30% | 12.09% | 115.8 | 110.6 | 0.6838 | 0.6599 | 1,021,798 |

**Executed runtime:** 10.92 seconds total for 180 simulations on Linux-6.18.57-x86_64-with-glibc2.41, Python 3.13.5, NumPy 2.3.5. Includes simulation compute only (no archive compression or GitHub transfer).

| Paired difference (treatment − baseline) | Production difference [95% approximate MC interval] | Disposable-income Gini difference [95% approximate MC interval] |
|---|---:|---:|
| savings_o03_s15 minus savings_o03_s00 | +2.8 [-2.9, +8.5] | -0.0076 [-0.0207, +0.0054] |
| savings_o03_s30 minus savings_o03_s00 | +0.0 [-6.1, +6.1] | -0.0069 [-0.0207, +0.0069] |
| savings_o08_s15 minus savings_o08_s00 | +4.4 [-0.4, +9.2] | -0.0169 [-0.0290, -0.0048] |
| savings_o08_s30 minus savings_o08_s00 | +1.9 [-2.6, +6.4] | -0.0233 [-0.0365, -0.0102] |
| savings_o03_s00 minus savings_o08_s00 | -4.9 [-10.5, +0.6] | +0.0219 [+0.0097, +0.0340] |
| savings_o03_s15 minus savings_o08_s15 | -6.6 [-10.5, -2.6] | +0.0312 [+0.0227, +0.0396] |
| savings_o03_s30 minus savings_o08_s30 | -6.8 [-10.9, -2.8] | +0.0383 [+0.0272, +0.0494] |

### 10,000 agents

| Ownership | Saving rate | Employment | Production | Consumption | Disposable-income Gini | Modeled net-worth Gini | Savings stock (cents) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 3% | 0% | 16.03% | 1559.5 | 1520.2 | 0.6595 | 0.8316 | 0 |
| 3% | 15% | 15.48% | 1506.0 | 1445.0 | 0.6714 | 0.8151 | 11,340,360 |
| 3% | 30% | 14.34% | 1394.8 | 1348.7 | 0.6803 | 0.8025 | 18,486,782 |
| 8% | 0% | 19.99% | 1944.7 | 1837.6 | 0.5369 | 0.6767 | 0 |
| 8% | 15% | 18.02% | 1753.6 | 1645.5 | 0.5689 | 0.6531 | 12,396,965 |
| 8% | 30% | 16.21% | 1576.6 | 1454.8 | 0.5895 | 0.6465 | 19,538,426 |

**Executed runtime:** 104.43 seconds total for 180 simulations on Linux-6.18.57-x86_64-with-glibc2.41, Python 3.13.5, NumPy 2.3.5. Includes simulation compute only (no archive compression or GitHub transfer).

| Paired difference (treatment − baseline) | Production difference [95% approximate MC interval] | Disposable-income Gini difference [95% approximate MC interval] |
|---|---:|---:|
| savings_o03_s15 minus savings_o03_s00 | -53.4 [-72.4, -34.4] | +0.0119 [+0.0066, +0.0171] |
| savings_o03_s30 minus savings_o03_s00 | -164.6 [-188.7, -140.5] | +0.0208 [+0.0150, +0.0265] |
| savings_o08_s15 minus savings_o08_s00 | -191.1 [-207.8, -174.3] | +0.0320 [+0.0290, +0.0351] |
| savings_o08_s30 minus savings_o08_s00 | -368.1 [-385.7, -350.5] | +0.0526 [+0.0489, +0.0564] |
| savings_o03_s00 minus savings_o08_s00 | -385.2 [-410.1, -360.3] | +0.1226 [+0.1165, +0.1288] |
| savings_o03_s15 minus savings_o08_s15 | -247.6 [-268.8, -226.3] | +0.1025 [+0.0968, +0.1081] |
| savings_o03_s30 minus savings_o08_s30 | -181.7 [-199.8, -163.7] | +0.0908 [+0.0861, +0.0954] |

## Scientific interpretation and limitations

- In the **10,000-agent** simulation with 8% ownership participation, increasing savings from 0% to 30% corresponded to about 368 fewer production units in the final period, and a 0.0526 higher disposable-income Gini. With 3% ownership participation, the same treatment corresponded to about 165 fewer units and a 0.0208 higher Gini. These outcomes depend on the assumed saving and hiring mechanisms.
- Concentrating firm ownership in a smaller 3% household subset is associated with lower simulated production and higher disposable-income inequality at each saving setting in this particular model, despite identical seed-specific nonownership initialization. This is **not** evidence for a universal causal social relationship.
- Net-worth Gini and disposable-income Gini are not interchangeable: in these runs increasing cash reserves reduces the *modeled* net-worth Gini while disposable-income Gini increases. Equity is valued using a simple posted-price rule; household net worth is not externally validated.
- **Population-dependent reversal:** at 1,000 agents the saving-rate treatment has small and sometimes positive mean production effects; at 10,000 the same nominal saving percentages show negative mean production effects. Crucially, the model holds six firms and their initial capital/money stocks and resource endowment fixed while changing population tenfold. Per-capita endowments and productive sector concentration therefore change; these are *different structural parameter regimes*, not a controlled population-only scalability study.
- Reported 95% intervals are paired `mean_difference ± 1.96 * sample_sd / sqrt(30)` from 30 random seeds. They assess Monte Carlo error for these rules, **not parameter uncertainty or model validity**. Multiple exploratory contrasts were not corrected for multiple testing. The 24-step horizon does not establish convergence or long-run welfare.
- All included runs met five implemented invariants in every period: zero money, goods, capital, household money-flow and firm money-flow discrepancies. No external empirical calibration or independent replication was attempted.

## Reproducibility

```bash
python -m pip install -e ".[test]"
pytest -q
PYTHONPATH=src python research/run_savings_sensitivity.py --population 1000 --seeds 30 --steps 24 --output results/savings_ownership_1000_30seed
for scenario in savings_o03_s00 savings_o03_s15 savings_o03_s30 savings_o08_s00 savings_o08_s15 savings_o08_s30; do
  PYTHONPATH=src python research/run_savings_sensitivity.py --only "$scenario" --population 10000 --seeds 30 --steps 24 --output results/savings_ownership_10000_30seed
done
PYTHONPATH=src python research/run_savings_sensitivity.py --finalize --population 10000 --seeds 30 --steps 24 --output results/savings_ownership_10000_30seed
```

Under `research/v02_savings_results_1000/` and `research/v02_savings_results_10000/`, `final_period.csv` contains all seed-level final observations, `summary.json` contains means/SDs, `paired_contrasts.json` contains paired effect estimates, and `metadata.json` records the run environment and digests. **Full per-period traces were not retained** for this factorial campaign, unlike the earlier detailed runs. They can be regenerated with the engine and CLI when required.

## Research gates that remain open

1. Normalize firm density and per-capita endowments and rerun matched population sweeps.
2. Add explicit capital valuation/inventory-cost bases before calling results economic net profit.
3. Consider real household financial intermediation (loans/equity with counterparty liabilities) only once accounting is modeled.
4. Test alternative saving rules, wages, ownership concentration, resource regeneration and much longer horizons.

