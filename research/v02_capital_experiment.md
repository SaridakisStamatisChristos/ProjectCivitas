# CIVITAS v0.2 capital and ownership experiment — executed research note

**Experiment date:** 2026-11-13. **Software:** `0.2.0.dev0` (development branch). **Python:** 3.13.5. **NumPy:** 2.3.5. **Platform:** Linux x86_64. **Model scope:** heterogeneous artificial agents, no calibration to a real society.

## Design and stated hypotheses

Three explicitly modeled treatments use 10,000 agents (2,500 households), six firms and three sectors, 24 abstract periods per simulation, and **30 seeds numbered 1–30**. Each period's agent skills, participation, household purchasing and firm decisions follow the documented core. Unlike an economy-wide policy inference, the actual research claim here is a controlled within-model rule comparison.

- **H1:** In a depreciating-capital economy, enabled productive reinvestment preserves more capital and output than forbidding investment, all other scenario inputs equal.
- **H2:** Concentrating dividend-receiving ownership in fewer households can change distributional and demand outcomes, under the same reinvestment rules.

**Controls:** All scenarios share model version, agents, periods, seeds, initial money and resource stocks, demand functions, wages, fixed technology, resource regeneration and initial capital units. For v0.2 capital-enabled configurations, ownership draws use a distinct RNG substream so changes in owner concentration do not change initial skills/participation or consume market RNG draws. Same seeds nevertheless cannot guarantee identical *subsequent* economic trajectories, since state transitions differ.

**Treatment definitions:**

| Parameter | No reinvestment | Reinvestment | Concentrated ownership |
|---|---:|---:|---:|
| Initial capital per firm | 450 | 450 | 450 |
| Output capacity per capital | 2 | 2 | 2 |
| Capital depreciation per period | 5% floored | 5% floored | 5% floored |
| Investment budget share | 0% | 40% | 40% |
| Household ownership fraction | 8% | 8% | 1% |
| Capital input sector | goods | goods | goods |

## Commands executed

```bash
PYTHONPATH=src python -m civitas suite \
  --scenarios scenarios/capital_depreciation_only.json scenarios/capital_reinvestment.json scenarios/capital_concentrated_ownership.json \
  --seeds 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30 \
  --steps 24 --output results/v02_capital_suite
python research/analyze_capital.py results/v02_capital_suite --output research/v02_capital_paired.json
```

## Observed final-period means (30 seeds each)

| Metric | No reinvestment | Reinvestment | Concentrated ownership |
|---|---:|---:|---:|
| Employment rate | 12.43% | 20.43% | 10.71% |
| Production units | 1,208.87 | 1,988.00 | 1,040.80 |
| Consumption units | 1,195.80 | 1,904.30 | 1,058.27 |
| Net disposable income Gini | 0.61705 | 0.53355 | 0.79298 |
| Modeled net-worth Gini | 0.65162 | 0.67982 | 0.92008 |
| Remaining capital units | 828.00 | 1,597.37 | 1,311.73 |

**Important:** Values are the means of the *final period's* statistic for each replication, not the total across 24 periods. The per-period `capital_added_units` can be zero at the final period even though cumulative investment was positive in earlier periods. Firm net worth is imputed using posted prices, not market valuation.

## Paired differences and Monte Carlo intervals

Across the same 30 seeds, **reinvestment minus no reinvestment** had mean paired differences:

- Production: **+779.13 units**, normal-approximate 95% Monte Carlo interval [763.38, 794.89].
- Consumption: **+708.50 units**, interval [695.41, 721.59].
- Employment rate: **+8.00 percentage points**, interval [7.84, 8.16].
- Disposable-income Gini: **−0.08351**, interval [−0.08666, −0.08035].
- Model-marked net-worth Gini: **+0.02821**, interval [+0.02669, +0.02973].

Under the same reinvestment settings, **concentrated ownership minus ordinary ownership** had mean paired differences:

- Production: **−947.20 units**, interval [−976.48, −917.92].
- Consumption: **−846.03 units**, interval [−866.85, −825.22].
- Employment rate: **−9.72 percentage points**, interval [−10.02, −9.42].
- Disposable-income Gini: **+0.25943**, interval [+0.25366, +0.26521].
- Model-marked net-worth Gini: **+0.24025**, interval [+0.23849, +0.24202].

Intervals use `mean(diff) ± 1.95996 * sample_sd(diff) / sqrt(30)` and quantify *within-model stochastic seed variability* only. They are not historical confidence intervals, evidence of a universal policy effect, or uncertainty bounds for untested model specifications.

## Accounting and software checks

The analysis script independently read and audited **2,160 period rows** (3 scenarios × 30 seeds × 24 periods). All rows showed zero money, source-resource, finished-goods, and capital-stock accounting discrepancies. Existing v0.1 comparison aggregate metrics were re-executed under unchanged legacy rules and matched their saved previous means exactly. The automated verification suite reported **28 passing tests** before the final documentation/build checkpoint.

## Interpretation and falsification plan

Under the present equations, productive investment draws on inventories of *already-produced* goods. It helps offset depreciation and permits additional labor hiring. When dividend ownership is concentrated, household purchasing power can become more uneven, lowering sales and the investment input available to firms. The ownership treatment affects who initially receives dividends, while consumer demand remains budget-constrained.

This does not establish any real-world theory of ownership or macroeconomic development. The observed outcomes depend strongly on **posted prices**, **one capital-goods conversion factor**, **no debt or financial intermediation**, **fixed wages**, **limited firms**, **zero household capital formation**, **simplified dividend policy**, **resource regeneration**, and **the uncalibrated initial distribution of cash**.

The next scientific test should sweep ownership fraction, dividend share, initial capital stock, capital depreciation, capital-good input/output ratios and household cash, with paired seeds. The aim is to search for counterexamples to H1/H2, map any phase transitions and identify effects robust across model rules. Until those tests, avoid causal stories beyond the exact simulator interventions.

## Reproducibility locations

- Source and capital semantics: `src/civitas/`, `docs/v02_capital_model.md`.
- Scenario JSON: `scenarios/capital_*.json`.
- Per-scenario final metrics, SDs: `research/v02_capital_summary.json`.
- Paired seed estimates and interval calculation: `research/v02_capital_paired.json`, `research/analyze_capital.py`.
- Full raw runs: local `results/v02_capital_suite` (ignored by Git by design; downloadable archive packaged separately). Regenerate by command above.
