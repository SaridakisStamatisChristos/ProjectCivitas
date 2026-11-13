# CIVITAS v0.2 — matched region-allocation × price-information × sales-access experiment

**Date:** 2026-11-13. **Status:** executed, software-verified, model-only scientific evidence. **Version:** `0.2.0.dev0`; not an empirical result or released v0.2.

## Design and executed sample

- Factorial design: `2 region assignments × 2 quote-information settings × 2 sales-access settings`, 8 arms per seed.
- Population: **1,000 agents per run**; firms per sector 20; three sectors; five regions. Each region has four eligible sellers per sector in sales-local arms.
- **30 matched seeds**, 24 abstract periods, **240 complete runs / 5,760 engine-period observations**. All per-period money, finished-goods, resource, capital, household-flow and firm-flow discrepancy checks equal zero.
- The complete population, firm cash, assets, equity ownership, initial RNG and natural resources are deep-copied exactly across all arms of a seed; the post-run PCG64 random state also matches across all arms. Balanced label shuffle uses its own RNG.
- Another **16 complete 10,000-agent simulations** (two seeds, three periods each, 48 engine periods) passed as an implementation smoke test; these are NOT a long-horizon replication of the 1,000-agent results.
- Computer: Python 3.13.5 and NumPy 2.3.5 on Linux x86_64; refer to `metadata.json` for complete runtime and per-seed hashes.
- Total recorded simulation time of the 1,000-agent factorial seed shards: **72.00 seconds**, exclusive of test, archive, report and upload overhead.

## Observed final-period per-person means (30 seeds)

| Assignment | Seller access | Full quotes: production | Two quotes: production | Full quotes: consumption | Two quotes: consumption | Missed opportunities/agent (two quotes) |
|---|---|---:|---:|---:|---:|---:|
| modulo | open | 0.13347 | 0.12703 | 0.14000 | 0.12637 | 0.00607 |
| modulo | local | 0.11040 | 0.12787 | 0.11307 | 0.12693 | 0.00223 |
| balanced_shuffle | open | 0.13347 | 0.12703 | 0.14000 | 0.12637 | 0.00607 |
| balanced_shuffle | local | 0.11083 | 0.12750 | 0.11257 | 0.12760 | 0.00320 |

## Within-seed paired production effects

| Comparison | Production/agent difference | Approx. 95% seed Monte Carlo interval |
|---|---:|---:|
| `quotes_effect|modulo|open` | -0.00643 | [-0.01020, -0.00267] |
| `quotes_effect|modulo|local` | +0.01747 | [+0.01420, +0.02073] |
| `quotes_effect|balanced_shuffle|open` | -0.00643 | [-0.01020, -0.00267] |
| `quotes_effect|balanced_shuffle|local` | +0.01667 | [+0.01235, +0.02098] |
| `quote_access_interaction|modulo` | +0.02390 | [+0.01840, +0.02940] |
| `quote_access_interaction|balanced_shuffle` | +0.02310 | [+0.01837, +0.02783] |

An independently written CSV recount (rather than using the summary file) reproduced the paired production effects for all four quote contrasts exactly. The open-market assignment arm is behaviorally inert: `modulo` and `balanced_shuffle` had identical open-market production under each information policy.

## Interpretation (internal to the equations only)

In this synthetic market, restricting observed price quotes from the full eligible set to two reduces mean final output under unrestricted market access, but increases it when the legal seller pool is restricted to local firms. This occurs even when every arm starts from the same agents and money, reflecting the interaction of which inventories become visible, firm revenues, period-to-period hiring targets and endogenous posted prices. The design does **not** yet determine which dynamic is primary.

Household-label shuffling changes the local composition while preserving the exact region household counts. At this population and horizon, its aggregate effect was small relative to quote-access effects. This does **not** prove that region assignment is generally unimportant.

## Robustness, verification and limitations

- All seed shards and full per-period aggregate data were preserved. Each seed shard has a SHA-256 content digest and an initial-state and final RNG digest; finalization rejected missing or changed shards in automated tests.
- The 1,000-agent design has 20 firms per sector (a high firm density relative to the population); no extrapolation of effect sizes to the standard 10,000-agent configuration is supported. The 10,000-agent three-period smoke run tests operability and accounting only.
- Quotes are a deterministic rotating pair in the ID list, not costly search, calibrated knowledge, learning or transport. Failed affordable purchase attempts with unquoted stock are diagnostic, not a monetized welfare loss.
- Hiring and capital input procurement remain global, resources and government are shared, and firms continue to use global sector unmet-demand signals. No independent regional economic equilibrium is claimed.
- Approximate 95% intervals treat simulation seeds as independently sampled replicates *conditional on the fixed model*; they exclude parameter uncertainty and were not corrected for multiple exploratory comparisons.
- There is no historical calibration, human behavioral validation, externally observed prices, long-run convergence analysis, or causal statement about real societies.

## Reproduction commands

```bash
python -m pip install -e '.[test]'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q
for seed in $(seq 1 30); do
  PYTHONPATH=src:. python research/run_region_information.py --seed "$seed" --steps 24 --population 1000 --firms-per-sector 20 --regions 5 --output research/v02_region_information_1000
done
PYTHONPATH=src:. python research/run_region_information.py --finalize --seeds 30 --steps 24 --population 1000 --firms-per-sector 20 --regions 5 --output research/v02_region_information_1000
```

**Next gate:** repeat this matched experiment at 10,000 agents and vary firms per region; then add inventory cost-basis / cost-of-goods-sold accounting with independent ledger tests. Do not promote v0.2 to main.
