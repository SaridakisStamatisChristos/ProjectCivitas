# Changelog

## 0.1.0 — 2026-11-13

Initial foundational simulation kernel, integer-cent transaction ledger, households and agents, skill-dependent production and paid labor, renewable resource, sector inventory, posted-price consumer exchange, wage taxes and targeted transfers, firm owner dividends, fixed automation and scheduled shocks, four scenarios, deterministic checkpoint/replay, CSV/JSONL/SQLite outputs, replication CLI, tests and scientific documentation.

## 0.2.0.dev0 — 2026-11-13 (development branch, not released)

Added explicit physical productive capital and rounded depreciation; budget-limited purchase and conversion of finished goods into physical capital; conserved firm-to-firm investment payments; modeled household equity, net worth and after-tax disposable income; version-2 checkpointing and legacy-v1 loader; regression and new accounting tests; 3 model-comparison scenarios and replicate experiment support. No final v0.2 acceptance claim.

## 0.2.0.dev0 — continuing development (2026-11-13; savings/flow-reconciliation slice)

- Separate non-interest-bearing household savings reserves, with wage/transfer/dividend-funded bounded deposits and explicit essential-sector emergency withdrawals. No loans or interest implied.
- Current operating-profit proxy now recognizes external capital-goods receipts and a noncash posted-price depreciation estimate. External capital purchases are not double-counted as operating expenses.
- Independently reconciled every household and firm account, plus the government account, rather than relying solely on total-money conservation. Account IDs explicitly bounds checked.
- NPZ checkpoint schema v3 includes savings state, while legacy v1/v2 load remains supported; actual prior v2 file was resumed successfully.
- Reproducible 2×3 savings/ownership factorial with 30 seeds each at 1,000 and 10,000 agents (360 runs). Exact final-period seed-level data and exploratory paired estimates preserved in `research/`.
- The version remains a development preview. Structural model/real-world validation not claimed.

## 0.2.0.dev0 — continued normalization / randomized validation (development branch)

- Added `scale_population_exact` for integer-exact normalization of initial firm density, physical-capital, cash and resource stocks per person, with audit and explicit rejection of inexact scalings.
- Added 12 frozen configuration files and a 2×3 factorial scenario runner preserving all period-level observations.
- Added preflight signed-int64 guards for initial total money/resource/capital stocks and atomic transfer destination overflow prevention. Does not establish overflow safety for all extreme future trajectories.
- Added analytical normalization tests and bounded randomized-conservation/checkpoint-replay falsification cases.
- Initial owner share rounding, scale-dependent decision rules and physical-regeneration rounding remain documented limitations.
