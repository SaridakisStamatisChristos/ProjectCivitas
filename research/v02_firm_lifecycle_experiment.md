# Firm lifecycle — controlled insolvency experiment

**Dataset:** `research/v02_firm_lifecycle_12seed_raw.tar.xz`, restored via `tar -xJf ...` into the project root (archive contains files under `research/v02_firm_lifecycle_12seed/`). Summary: `research/v02_firm_lifecycle_12seed/summary.json`.

## Research question

Does the opt-in lifecycle mechanism conserve accounts and produce reproducible, mechanically identifiable differences under a deliberately insolvent opening firm?

## Design

- 12 independent seeds; 2 matched treatment arms per seed; 24 periods; 120 agents, 30 households, 2 firms in 1 goods sector.
- Opening synthetic stress fixture: a 1,200-cent real-savings-backed loan to firm 0, followed by a 1,300-cent money transfer from firm 0 to firm 1 (including its 100 cents initial cash), plus an explicit inherited stock endowment of 3 inventory units with 70-cent cost basis. Prior output counters are initialized accordingly. This is an engineered initial world, **not** an endogenously observed credit or bankruptcy event.
- Each arm receives an identical deep copy of this opening state and exact RNG state. The control arm disables the lifecycle rules; the intervention arm enables liquidation and owner-funded 60-cent slot re-entry. All other scenario parameters are equal.
- Every period performs monetary replay, loan-principal audit, physical-event replay, cost-basis and book-equity reconciliation, and activity-transition replay. A per-seed JSON contains both arms and every period; a separate SHA-256 sidecar detects corruption.

## Observed results

Run `PYTHONPATH=src:. python research/run_firm_lifecycle.py --verify-only --seeds 12` to recheck the integrity-closed dataset. The observed completed campaign contained:

- **24 simulations**, **576 audited periods**;
- **8,467 cash transfers**, **4,850 physical events**, **24 firm transition events** independently replayed;
- **12 liquidations**, **12 owner-funded re-entries** in the intervention arm;
- **12,588 cents** of cumulative loan defaults in the intervention arm;
- Mean period-24 production without lifecycle: **7.833 units**; with lifecycle: **4.000 units**;
- Paired final-period production difference (lifecycle minus control): **−3.833 units**; approximate 95% seed Monte Carlo interval **[−4.054, −3.613]**.

All checked monetary, physical, loan, firm cash-flow and book-equity discrepancy classes were exactly zero. These are small-seed, model-conditional outcomes, **not** evidence that liquidation lowers real-world output. Initial failure was engineered to prove numerical and transaction semantics; no estimated realistic default probability can be inferred. The mechanism destroys all remaining physical capital and inventory on closure, so the negative output effect is highly sensitive to the zero-salvage rule. The 95% interval reflects only seed sampling and is not a robust empirical confidence interval for an economy.

## Reproduction

```bash
PYTHONPATH=src:. python -m pytest -q
for seed in $(seq 1 12); do PYTHONPATH=src:. python research/run_firm_lifecycle.py --seed "$seed"; done
PYTHONPATH=src:. python research/run_firm_lifecycle.py --finalize --seeds 12
PYTHONPATH=src:. python research/run_firm_lifecycle.py --verify-only --seeds 12
```

Legacy parity was separately verified against the previous published code using a five-period credit/capital/savings scenario: identical configuration digest, all metric values and metric schema (81 fields), and no new lifecycle event file when the feature was disabled. The complete test suite reported **260 passed**.
