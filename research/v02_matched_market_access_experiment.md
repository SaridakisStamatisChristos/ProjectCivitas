# CIVITAS v0.2 — matched-market access intervention (executed)

**Date:** 2026-11-13. **Status:** executed synthetic experiment, *not* empirical validation. **Software:** 0.2.0.dev0. **Primary question:** how much of the integrated-versus-partitioned difference survives when all agents and initial financial/physical states are exactly matched?

### Design and provenance

- **Replicates:** 30 seeds, 4 arms, 24 abstract periods, 10,000 agents, 60 firms, 10 access regions.
- **Executable period rows checked:** 2,880; all six monetary/physical/agent- and firm-ledger identities held in every run.
- **Common random numbers:** identical initialized agent/household/firm/ownership data and RNG state for each seed; all four final RNG states also matched. Initial and final RNG hashes are retained in `metadata.json`.
- **Reference baseline commit:** `96703d9dfa39e5e753ae7a710bb398876496ec78` on development branch.
- **Full specification:** `docs/v02_matched_market_access.md`. No monetary issuance, loans or external API calls.

### Mean final-period outcomes (30 paired seeds)

| Intervention | Production/person | Consumption/person | Employment rate | Disposable-income Gini |
|---|---:|---:|---:|---:|
| Unrestricted | 0.251247 | 0.252050 | 25.9808% | 0.4147 |
| Consumer sales restricted | 0.121157 | 0.118150 | 12.6527% | 0.6329 |
| Labor hiring restricted | 0.264697 | 0.265290 | 27.3688% | 0.4128 |
| Both restricted | 0.121650 | 0.118453 | 12.6989% | 0.6345 |

### Paired treatment effects, production units/person

| Contrast | Mean difference | Approx. 95% Monte Carlo interval |
|---|---:|---:|
| Sales-only minus unrestricted | -0.130090 | [-0.132678, -0.127502] |
| Labor-only minus unrestricted | +0.013450 | [+0.010964, +0.015936] |
| Both restricted minus unrestricted | -0.129597 | [-0.132378, -0.126815] |
| Combined interaction (both − sales − labor + open) | -0.012957 | [-0.016608, -0.009306] |

### Interpretation and attempts to falsify

The consumer-purchase access restriction explains the overwhelming majority of the observed final-period output difference under these particular rules. Labor-access restriction alone did not reproduce the decline; it slightly increased simulated output and employment in the unrestricted-sales treatment. Combined restrictions produced a non-additive interaction. These findings **correct an earlier ambiguity**: previous comparisons did not hold the entire initial individual state fixed across topologies.

The results are conditional, not evidence for a general economic law. Restricted household sales change which inventories can be purchased, leading indirectly to changed cash flow, firm production decisions, wages and price trajectories. Global resources, interfirm capital trades, dividend recipients and aggregate hiring signals remain shared; the restricted arms are **not** ten independent closed economies. The model does not represent realistic industrial organization, transport costs, search networks or bank financing.

Intervals use `mean ± 1.96 × sample_sd/sqrt(30)` on **seed-paired** outcomes. They are descriptive Monte Carlo intervals, without model uncertainty, multiplicity correction, calibration, or true randomization of real humans. Only 24 periods were observed, not long-run equilibrium.

### Evidence and exact reproduction

- Run `PYTHONPATH=src:. python -m pytest -q`, then the `--seed` and `--finalize` commands in `docs/v02_matched_market_access.md`.
- Raw final- and intermediate-period trajectories for every seed and treatment: `research/v02_matched_market_30/periods.csv`.
- Recorded source settings/initial-state hashes/random-stream hashes/checksums: `metadata.json`, `scenario_seed1.json`.
- Paired statistics and descriptive uncertainty: `summary.json`; code: `research/run_matched_market_access.py`.

**Highest-priority next falsification:** hold the same matched state but change the fraction of accessible sellers, localize unmet-demand information, and test whether the observed sales-access effect persists across ownership, saving, pricing and resource settings. Separately implement defensible cost-of-goods-sold accounting and financial claims before a v0.2 release.
