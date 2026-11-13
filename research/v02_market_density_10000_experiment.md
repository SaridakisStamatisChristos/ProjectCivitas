# CIVITAS v0.2 — Firm-density and buyer-information robustness

**Executed:** 2026-11-13. **Development version:** `0.2.0.dev0`. **Execution:** Python 3.13.5 / NumPy 2.3.5, Linux x86_64. **Design:** 10,000 agents, 24 abstract periods, 8 seeds (1–8), two firm densities (10 versus 20 firms per sector), four arms per density: unrestricted versus local purchases crossed with full price observation versus two price quotes. **64 simulations and 1,536 checked engine periods.**

Every density uses five regions and the same aggregate initial firm monetary capital, physical capital, population, household cash and natural resources. Per-firm cash and physical capital are divided by firm count. Within each seed **and density**, all four arms share the same initial agent, household, firm and RNG states; only sales eligibility and price information differ. **Between densities, firm identities, producer allocation and ownership structures necessarily differ:** this is a sensitivity experiment, not a pure causal estimate of changing firm count.

## Observed mean final-period statistics

| Firms per sector | Purchase access | Price quotes | Production/person | Consumption/person | Employment rate | Disposable-income Gini |
|---|---|---|---:|---:|---:|---:|
| 10 | open | full | 0.20600 | 0.20956 | 0.21293 | 0.47991 |
| 10 | open | 2 | 0.11716 | 0.11418 | 0.12202 | 0.69303 |
| 10 | local | full | 0.09643 | 0.09199 | 0.10056 | 0.73193 |
| 10 | local | 2 | 0.09643 | 0.09199 | 0.10056 | 0.73193 |
| 20 | open | full | 0.25284 | 0.25420 | 0.26194 | 0.41270 |
| 20 | open | 2 | 0.12851 | 0.12455 | 0.13497 | 0.65598 |
| 20 | local | full | 0.14953 | 0.14630 | 0.15620 | 0.56564 |
| 20 | local | 2 | 0.13064 | 0.12689 | 0.13726 | 0.64902 |

The **paired two-quote minus full-information production/person effect** at 10 firms/sector is `−0.08884` in open markets (approx. 95% seed interval `[−0.09515, −0.08253]`) and exactly `0` in local markets. At 20 firms/sector it is `−0.12433` in open markets (`[−0.12945, −0.11920]`) and `−0.01889` in local markets (`[−0.02123, −0.01655]`).

**Structural explanation:** when there are 10 firms per sector distributed over five regions, each local market offers exactly two sellers per sector. Restricting buyers to two quotes cannot reduce their already two-seller observation set; hence both local treatments are mathematically identical. With 20 firms per sector, there are four local firms and quote limitation becomes binding.

This observation **does not support extrapolating** the earlier 1,000-agent, six-firm seller-information result to larger scales. The earlier occasional positive quote-limit effect is not stable across the two firm-density regimes tested here. It is a mechanism-sensitivity result, not a forecast about markets or human preferences.

## Verification and provenance

- Runner: `research/run_region_density.py`; design/test suite: `tests/test_region_density.py`.
- Exact seed-level records: `research/v02_region_density_10000/shards/` (16 CSVs and matching JSON SHA-256 sidecars) and aggregate `summary.json`.
- Each run audits conservation of money, resource, physical goods, physical capital, household cash flows and firm cash flows every period. No violations in the completed runs.
- Every quartet of within-density arms begins from identical hashed state; end-of-run RNG hashes agree. `finalize()` rejects incomplete or tampered records. A separate historical regression check reproduced all 96 period records of the previous canonical 20-firm seed-1 experiment exactly in the unmodified default accounting mode.
- Approximate 95% intervals use paired seeds and the normal approximation. With only eight seeds, they quantify limited Monte Carlo precision, **not** uncertainty in model assumptions, parameter calibration or external social outcomes.

**Next:** perform longer horizons, explicitly vary region count and the number of sellers observed, and test whether outcomes remain stable under alternative demand and hiring rules. The cost-basis accounting slice is implemented separately and does not retroactively change these legacy-mode results.
