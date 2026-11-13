# CIVITAS v0.2 — Credit pathways: lending access, maturity and horizon

**Evidence classification:** executed, exploratory synthetic-model experiment; not a real-world economic forecast. 13 November 2026.

## Research contract

In a fixed 10,000-agent economy with 30 firms and one common resource pool, examine how changing *available savings for lending* (0%, 15%, 75% of household savings), household saving propensity (25% or 75% of disposable income), and nominal loan maturity (2 or 6 abstract periods) changes measured output. The 0%-lender configuration is a negative control with `credit_enabled=true` but no fundable transfers; no-credit is a separate independent baseline. Firms buy actual capital goods; credit neither creates money nor implies interest or formal banking. Historical-cost accounting is enabled in both treated and untreated cases.

**Design:** 2 saving propensities × (no-credit control, no-funding sham, 2 funding shares × 2 maturities) = 12 treatments × 6 seed values (1–6) × 48 periods = **72 simulations and 3,456 observed period states**. All 12 treatments under the same seed share the exact initial agent/firm arrays, ownership distribution, cash, resources and RNG state. We report outputs at both periods 24 and 48, without cherry-picking the earlier favorable horizon. Source code, exact configuration, initial-state fingerprints, all period data and signed-off file checksums are preserved.

## Results

**Final-period production (units, mean across six seeds)**

| Savings | Credit setting | Period 24 | Period 48 | Repayment total (cents) | Defaults total (cents) |
|---|---|---:|---:|---:|---:|
| 25% | No credit | 1,331.5 | 653.2 | 0 | 0 |
| 25% | Credit on, 0% lender funds | 1,331.5 | 653.2 | 0 | 0 |
| 25% | 15% lender funds, 2-period term | 2,125.7 | 634.7 | 10,480,794 | 5,000,765 |
| 25% | 15% lender funds, 6-period term | 2,126.8 | 682.2 | 15,841,778 | 48,436 |
| 25% | 75% lender funds, 2-period term | 2,123.2 | 673.3 | 10,544,139 | 4,992,844 |
| 25% | 75% lender funds, 6-period term | 2,124.0 | 652.3 | 15,677,419 | 42,950 |
| 75% | No credit | 1,612.2 | 709.7 | 0 | 0 |
| 75% | Credit on, 0% lender funds | 1,612.2 | 709.7 | 0 | 0 |
| 75% | 15% lender funds, 2-period term | 1,532.3 | 700.8 | 8,409,191 | 8,375,109 |
| 75% | 15% lender funds, 6-period term | 1,569.8 | 731.3 | 15,965,434 | 1,493,789 |
| 75% | 75% lender funds, 2-period term | 1,465.7 | 717.8 | 8,257,777 | 8,362,846 |
| 75% | 75% lender funds, 6-period term | 1,588.3 | 738.7 | 15,804,132 | 1,512,743 |

The credit-enabled **0% lendable** negative controls matched no-credit output, consumption, employment, distribution metrics and all other recorded per-period metrics exactly for every seed. This establishes that any differences under 15% or 75% lendable shares are not caused merely by toggling the `credit_enabled` flag.

**Paired credit effect on production (treatment − same-saving no-credit control)**

| Savings | Credit availability, term | Period 24 mean | Period 48 mean | 95% approximate MC interval at 48 |
|---|---|---:|---:|---|
| 25% | limited (2 periods) | +794.2 | -18.5 | [-68.5, +31.5] |
| 25% | limited (6 periods) | +795.3 | +29.0 | [-20.2, +78.2] |
| 25% | broad (2 periods) | +791.7 | +20.2 | [-13.5, +53.9] |
| 25% | broad (6 periods) | +792.5 | -0.8 | [-20.7, +19.0] |
| 75% | limited (2 periods) | -79.8 | -8.8 | [-58.0, +40.3] |
| 75% | limited (6 periods) | -42.3 | +21.7 | [+6.5, +36.8] |
| 75% | broad (2 periods) | -146.5 | +8.2 | [-9.5, +25.8] |
| 75% | broad (6 periods) | -23.8 | +29.0 | [-9.8, +67.8] |

**Credit × savings interaction:** at period 24 the difference in credit effects between 75% and 25% saving is large and negative for all four financing settings (−816 to −938 units); by period 48, the four interaction estimates range from −12 to +30 units with wide Monte Carlo intervals overlapping zero. This is evidence that the apparent reversal at 24 periods is horizon-dependent under these specific simulation rules.

## Verification evidence

- Historical baseline: the preexisting 128 tests passed before modification, and the expanded development suite passed **136 tests** after adding eight credit-pathways tests.
- Every recorded period was checked against **eight** exact accounting invariants: conserved money, physical resources, finished goods, productive capital, household cash flows, firm cash flows, historical-cost firm equity and lender-asset/borrower-liability agreement.
- A stronger per-period debt roll-forward was also checked: `debt(t) = debt(t−1) + originations(t) − repayments(t) − defaults(t)`.
- Each of the 72 treatments is saved in checksum-protected seed records; the new per-cell checkpoint format allows interrupted seeds to resume without invalidating completed results. Repeated writes verify original content; corrupt or mismatched shards are rejected.
- `research/audit_credit_pathways.py` is a separate standard-library-only auditor that independently recomputes seed checksums, initial-state matching, the zero-funding negative-control identity, period accounting, debt roll-forwards and saved summary production means. It passed against all six raw seed files.

## Interpretation and falsification

The earlier 24-period production effects do **not** persist at roughly their initial magnitudes through period 48. The late-horizon output in this model falls across both credited and uncredited cases, including no-credit controls. In one diagnostic no-credit seed, the modeled renewable resource stock *increased* from period 24 to period 48, so that particular output decline cannot be attributed simply to exhaustion of the shared resource stock. No complete mechanism attribution has yet been established; labor demand, prices, consumption and capital input markets require further diagnosis. All outstanding loan principal was zero in the recorded final period; this may reflect repayment/writeoff and stopped new lending, not debt-free prosperity.

All confidence intervals are simple paired mean ± 1.96 × sample SD / √6. They quantify **Monte Carlo seed variation only**, not parameter uncertainty, model uncertainty, or real-economy uncertainty. Sample size is small and multiple exploratory contrasts were not multiplicity corrected. Recorded periods are abstract, and there is no empirical calibration, bank sector, interest rate, credit pricing, firm entry, enforcement, or long-run equilibrium evidence. Cross-treatment trajectories diverge endogenously despite identical initial states and seed values.

## Reproduce

```bash
python -m pip install -e ".[test]"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q
for seed in 1 2 3 4 5 6; do
  PYTHONPATH=src:. python research/run_credit_pathways.py --seed "$seed" --population 10000 --steps 48 --output results/credit_pathways
done
PYTHONPATH=src:. python research/run_credit_pathways.py --finalize --seeds 1,2,3,4,5,6 --population 10000 --steps 48 --output results/credit_pathways
python research/audit_credit_pathways.py results/credit_pathways
```

To resume an interrupted seed, invoke `--seed` again. To complete an individual treatment first, use `--seed N --cell s25_limited_term2`. Archived `.json.gz` shards in the repository are losslessly recoverable with `python research/restore_credit_pathways.py research/v02_credit_pathways_10000 results/restored_credit_pathways`. The restore command verifies each shard's original canonical checksum before producing the original `.json` records; then invoke `--finalize` or `audit_credit_pathways.py`. Raw plain-JSON shards are also included in the complete downloadable archive.

## Next research gate

Investigate the decline in aggregate production between 24 and 48 periods using decomposed time series of **resource availability, labor demand, firm cash, price changes, inventory, household liquidity, and capital maintenance**. Stress-test repayment schedules and positive-interest loan contracts only after a bilateral, balanced interest-accounting specification has been written. Run at least 30 seeds and alternate horizon definitions before promoting scientific claims; do not merge v0.2 into `main`.

