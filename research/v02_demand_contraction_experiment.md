# CIVITAS v0.2 — Why does production decline from period 24 to 48?

**Evidence type:** executed, matched-seed within-model intervention study, 13 November 2026. Not an empirical forecast or a claim about institutional superiority.

## Executed design

- 48 real simulations, 2304 audited periods, 10,000 agents, 48 periods, 8 seeds.
- Six single-parameter treatments. All treatments in each seed share identical initial state and end RNG fingerprints.
- All eight accounting discrepancy fields equal zero throughout every recorded period; the independent auditor separately recomputes all summary statistics and checksums.
- The control exactly reproduces the previous six-seed credit-pathways no-credit means: production 1,331.5 at period 24 and 653.2 at period 48.

## Main observations

| Intervention | Production at 24 | Production at 48 | Budget-unmet fraction at 48 | Firm share of money at 48 |
|---|---:|---:|---:|---:|
| Control | 1,324.8 | 661.4 | 85.9% | 73.3% |
| No saving | 1,147.5 | 531.8 | 88.0% | 82.3% |
| Full dividends | 1,124.0 | 675.5 | 75.8% | 2.6% |
| Fixed prices | 1,273.9 | 1,502.1 | 68.8% | 30.1% |
| Stationary hiring | 1,516.5 | 1,143.6 | 77.0% | 55.8% |
| No depreciation | 2,080.6 | 679.6 | 85.6% | 73.1% |

**Within the control economy**, comparing period 24 to period 48:
- **Production:** 1,324.750 → 661.375.
- **Consumption:** 1,246.250 → 650.375.
- **Budget-unmet purchase attempts:** 2,991.375 → 3,975.625.
- **Renewable resource stock:** 5,351,537.750 → 5,580,931.250.
- **Productive capital stock:** 1,046.125 → 1,207.750.
- **Unsold finished-goods stock:** 314.375 → 939.250.
- **Household spendable cash (cents):** 8,152,157.875 → 2,319,706.875.
- **Household reserve cash (cents):** 17,344,209.625 → 7,999,814.000.
- **Firm cash (cents):** 13,203,632.500 → 28,380,479.125.
- **Nonfood affordability diagnostic:** 0.109 → 0.003.
- **Mean posted price (cents):** 3,638.596 → 3,218.317.

The fixed total money supply is not destroyed: cash migrates between account types. Price levels are **not** monotonically increasing over the entire horizon (the quoted price mean drops between these two endpoints); the test concerns the dynamic path of the price-adjustment rule and the resulting affordability feedback.

## Within-model paired production contrasts at period 48

| Intervention minus control | Mean difference (units) | Approx. 95% seed Monte Carlo interval |
|---|---:|---:|
| no saving | -129.62 | [-151.28, -107.97] |
| full dividends | +14.12 | [-16.14, +44.39] |
| fixed prices | +840.75 | [+800.06, +881.44] |
| stationary hiring | +482.25 | [+454.68, +509.82] |
| no depreciation | +18.25 | [-8.55, +45.05] |

## Interpretation and falsification

1. **Scarcity alone is falsified in this parameter regime:** renewable stock increases while output and household purchases decline; unsold inventory builds. This does not mean all resource restrictions are irrelevant under other parameters.
2. **An active nominal-demand feedback is supported:** the control shifts spendable cash toward firms and records many more budget failures. Fixing prices changes the trajectory substantially, and stationary hiring changes it materially as well. The diagnostic cannot isolate a single sufficient cause because treatment effects propagate through the whole economy.
3. **Capital depreciation is not sufficient to explain the contraction:** removing it creates a large temporary production advantage near period 24, but final production approaches the control.
4. **Simply eliminating savings is not a rescue:** final production falls more. Positive dividends raise household cash availability but also reduce firms’ productive capital investment; final output changes little, showing an important constraint interaction.
5. **Uncertainty is understated by seed intervals:** eight seeds and six exploratory interventions do not establish general equilibrium, causality beyond interventions within this exact simulator, or a real-world conclusion.

## Independent verification

- `PYTHONPATH=src:. python -m pytest -q`: **144 tests passed** on the actual Python execution environment.
- `python research/audit_demand_diagnostics.py research/v02_demand_diagnostics` independently audited **48 scenario trajectories, 2,304 period records**, checksums, money-stock partitions, all eight engine accounting fields, initial-state/RNG alignment, and every reported statistical value.
- No engine equations or default scenario behavior were changed: this research extension adds an observer, testable counterfactual runner, independent auditor and documentation.
- GitHub-preserved raw data: `research/v02_demand_diagnostics_raw.zip`, containing eight folders of six cell shards and `summary.json`. Restore with `PYTHONPATH=src:. python research/restore_demand_diagnostics.py research/v02_demand_diagnostics_raw.zip results/restored_demand` then run the independent auditor. Raw uncompressed working copies may also be present in `research/v02_demand_diagnostics/` in the downloadable project archive.

## Next engineering acceptance gate

Design explicit, separately switchable **affordability-aware price-setting** and **wage/hiring feedback** mechanisms and test them with matched-seed longer-horizon, parameter-sweep and adversarial invariants. Treat these as alternative candidate equations, never silent repairs chosen only because they increase output. Before a stable v0.2 release, validate money distribution, capital input costs, nonnegative stocks, extreme int64 cases, and report sensitivity to multiple populations and resource regimes.

**Source digest:** `1839bc23148d0be41a957dc29eb6d74a0bf45cef25b66aa8e638f0f7a7b596cb`. **Model version:** `0.2.0.dev0`. The stable `main` branch is unchanged.
