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

## 0.2.0.dev0 — market-mechanism falsification campaign (2026-11-13)

- Added bounded configurable buyer seller choice, adaptive versus stationary hiring targets, and seeded-random versus household-ID consumption order; retained all historical rules by default.
- Added price-spread, active-seller, and seller-sales concentration diagnostics without changing conservation identities.
- Independently verified 56 tests, 288 historical baseline records and 792 mechanism-level synthetic simulations, all internal accounts conserving for 19,008 simulated periods.
- Preserved 12-master-seed comparative research with six one-factor interventions and integrated-versus-isolated topology controls; documented that topology comparisons do not pair identical synthetic individuals.
- No promotion to `main`; scientific and full financial-accounting acceptance criteria remain open.

## 0.2.0.dev0 — Factorial mechanism research checkpoint (2026-11-13)

- Introduced executable 2×2×2 market mechanism factorial experiment runner, with resumable treatment-level execution and integrity-gated aggregation.
- Verified 64 automated tests and 704 synthetic simulation instances, 16,896 internally checked periods and archived full topology-level period records.
- Demonstrated strong nonadditive seller-search × pricing × hiring interactions under exact simulator rules, while retaining an explicit warning about unmatched agent initialization and labor/seller access confounds.
- `main` and the historical core engine remain unchanged. v0.2 is still development-only.

## 0.2.0.dev0 — matched-market access research (2026-11-13, development only)

- Added versioned `market_regions`, `restrict_household_sales` and `restrict_labor_hiring` scenario fields with fail-fast validation.
- Consumer-seller access and worker-to-firm hiring eligibility can now be restricted independently. Region labels are derived deterministically from existing household and firm IDs; old rules remain the default.
- Added copy-identical initial state/RNG 2×2 experimental runner, atomic checksum-verified seed shards, strict aggregate verifier and exploratory paired factorial intervals.
- Executed 120 matched-arm simulations (30 seeds, 24 periods), 2,880 audited period states. No monetary, finished-goods, resource, capital, household-flow or firm-flow discrepancy.
- Added dedicated checkpoint and regression tests, including zero agents, replay and legacy unconstrained behavior. Software remains experimental v0.2.0.dev0.

## 0.2.0.dev0 — regional assignment and quote-information study (development)

- Added deterministic balanced region assignment on a separate seeded RNG stream, preserving household counts by region.
- Added price-search information limitation (two eligible quotes vs complete observation), separated from trading eligibility and seller ranking.
- Recorded opportunities where affordable stock existed with an accessible but unquoted seller; metric is diagnostic rather than welfare.
- Added exact-initial-state 2 × 2 × 2 research runner, per-seed digest-verified datasets, checkpoint/replay and quote-access boundary tests.
- Historical mode remains default; no empirical validation or release promotion is claimed.


## 0.2.0.dev0 — firm-density and inventory-cost development gate (2026-11-13)

- Reproduced eight matched-seed 10,000-agent, 24-period buyer-information experiments at two firm densities with normalized aggregate starting capital, total firm cash, and resource stocks. Added a hash-verified, incomplete-shard-rejecting reproducible runner, new tests and full period-level evidence.
- Added opt-in pooled integer historical-cost inventory basis, consumer and capital-goods COGS, physical-capital carrying basis, depreciation cost, zero-production paid labor expenses and per-firm `Δbook_equity = cost_basis_earnings - dividends` verification.
- Preserved previous dividend behavior by default; cost-enabled runs deliberately base dividends on their specified cost-basis earnings. Published the behavioral sensitivity comparison and explicit limitations.
- Implemented checkpoint format 4 for cost-enabled runs; retain v1/v2/v3 loader for original accounting-disabled scenarios and refuse fabricated basis on invalid downgrades.
- Re-ran 109 automated tests and an exact byte-for-byte 96-period default-mode regression, preserving complete source and seed evidence. No stable release or empirical validation claimed.

## 0.2.0.dev0 — continuing development (2026-11-13; bilateral credit and resource-use costs)

- Opt-in household-savings-funded bilateral firm credit, with separately recorded lender claims, borrower obligations, exact money transfers, maturity repayment and symmetric principal writeoffs. **No credit money creation, interest, or automatic intermediary.**
- Opt-in resource extraction fee credited to the government and capitalized into inventory cost when physical production occurs. A production constraint prevents unaffordable input-fee commitments.
- Credit-aware historical-cost firm book equity, borrower debt-extinguishment gains and household financial claims, with multiple independently asserted invariants.
- Nonpickle NPZ checkpoint version 5 for credit contracts and accounts; historical checkpoint formats 1–4 still load into compatible scenarios with zero loans.
- Matched four-arm credit × resource-fee experiments at 1,000 and 10,000 agents, plus independent regression parity against the preceding development source; negative/null results and incomplete density campaign disclosed.
- Still a **development checkpoint**, not release-ready or empirically validated.
