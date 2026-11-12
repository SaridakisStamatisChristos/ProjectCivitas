# CIVITAS v0.1 — initial executed experiment report

**Date:** 2026-11-13. **Model version:** 0.1.0. **Engine:** Python 3.13.5 / NumPy 2.3.5 / Linux x86_64. **Agents:** 10,000 per simulation (2,500 households). **Periods:** 24. **Replicates:** 3 per scenario, seeds 7, 11 and 13. This is a small demonstration experiment, not a calibrated social-scientific result.

Command actually executed:

```bash
PYTHONPATH=src python -m civitas suite --scenarios scenarios/market.json scenarios/mixed_redistributive.json scenarios/automation_shock.json scenarios/resource_scarcity.json --seeds 7,11,13 --steps 24 --output results/initial_suite
```

## Final period observations (replication means)

| Scenario | Employment rate | Production units | Consumption units | Income Gini | Resource stock |
|---|---:|---:|---:|---:|---:|
| market | 0.220 | 2,147.667 | 2,077.667 | 0.519 | 408,255.000 |
| mixed_redistributive | 0.226 | 2,198.667 | 2,156.333 | 0.445 | 396,170.000 |
| automation_shock | 0.114 | 1,724.000 | 1,670.333 | 0.614 | 415,511.667 |
| resource_scarcity | 0.000 | 0.000 | 0.000 | undefined | 0.000 |

`income_gini` is **undefined** when household recorded income totals zero. For the scarcity scenario, this is a non-applicable statistic, not an observed Gini of zero. The values are means of the final (24th) period only, not 24-step averages. The sample standard deviations and valid n for each measurement are in `research/initial_summary.json`.

## Interpretation limited to the configured rules

- Taxation (15% of current wages, with 90% of collections returned to the 30% lowest gross-wage households) corresponded to lower recorded income Gini in the mixed configuration than in the baseline across these three seeds. Reported *gross income* includes transfers and is not net after wage tax.
- At step 12, the automation scenario adds 0.55 to each firm's labor-efficiency multiplier. Because hiring responds to expected output per worker, the final measured employment rate was lower than baseline. Output and consumption need not improve: financial demand, resource and reinvestment interactions matter.
- The low-resource scenario exhausted its one renewable input, after which zero stock is an absorbing state in the selected logistic regeneration equation. Final output and consumption were zero and income Gini could not be defined. This collapse reflects the chosen rules and parameters, not an ecological prediction.
- All 288 observed period records (4 × 3 × 24) show **0 cents monetary discrepancy**, **0 resource units discrepancy**, and **0 finished-good units discrepancy**. This verifies these invariants for these runs only.

## Executed reference CPU benchmarks

```
- 1,000 agents × 3 steps: 0.0106 s; NumPy state arrays 40,224 bytes; all recorded discrepancies zero
- 10,000 agents × 3 steps: 0.0750 s; NumPy state arrays 399,864 bytes; all recorded discrepancies zero
- 100,000 agents × 3 steps: 0.5511 s; NumPy state arrays 3,996,264 bytes; all recorded discrepancies zero
```

Measurements were collected with one invocation of `benchmarks/benchmark.py` using seed 7 and three periods per population; no warm-up, GPU, multiprocessing or memory profiler. `state_array_bytes` accounts only for explicitly stored NumPy state arrays, not Python runtime or total process RSS. These isolated times should not be used to claim industrial scale or high-fidelity million-agent performance.

## Uncertainty, controls and next experiment

Only three seeds were used per scenario. The suite reports sample SD but no confidence intervals or formal significance claims. Populations share seed-specific initialization under the same baseline configuration, but changes in trajectories and RNG consumption can weaken the common-random-numbers pairing. A later experiment should compare income *after tax*, decompose wages/transfer/dividends, assess steady-state transients, and sweep labor demand, ownership concentration, and initial money across at least 30 seeds. No external country or era is used for calibration.

**Raw data:** regenerate using the exact recorded CLI command; scenario JSON and executable engine are version-controlled, while raw run outputs are preserved in the downloadable release archive (not in the source Git history).
