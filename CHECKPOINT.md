# CIVITAS continuation checkpoint

## Current branch and software status

- **Stable baseline:** v0.1.0 on GitHub `main`, checkpoint commit `85d9671978df6ce40a58e895aee5cb1d2a938a58` (2026-11-13).
- **Active target:** v0.2 — Economic Depth. Branch `feature/v0.2-capital-accounting`.
- **Current development version:** `0.2.0.dev0`. This is **not** a completed or released v0.2 milestone. Keep changes on development branch until acceptance and independent review.
- **Execution environment:** local container Python 3.13.5, NumPy 2.3.5, pytest 9.0.2, Linux x86_64.

## Implemented, executable functionality

- All v0.1 baseline features remain (10,000-agent standard, multi-sector production, resource regeneration, household demand, wages, taxes, transfers, dividends, seeded RNG, checkpointing, command-line tools, SQLite/CSV/JSONL, four legacy scenarios).
- Additional **after-tax disposable income** and income-flow accounting identity, separate from the legacy `income_gini` metric.
- Simple **firm capital stock** with per-period depreciation, productive capacity limit and integer inventory conversion.
- **Physical capital purchases** of actually produced goods, conserved interfirm cash transfers; same-firm conversion without fake money movement.
- **Household ownership claims** via registered equal-share firm owner sets; explicitly modeled/marked equity and household net-worth Gini (not a market valuation).
- Capital stock and completed-goods flow invariants, checkpoint v2, legacy checkpoint v1 migration support.
- Separate ownership RNG substream in capital-enabled scenarios to hold nonownership initial conditions constant.
- 3 paired experimental scenarios, analysis script and versioned report/summary.

## Verification evidence

- `pytest -q`: **28 tests passed** before packaging, covering old suite and new capital/financial/serialization/model experiments.
- Re-execution of 4 original v0.1 scenarios × 3 seeds × 24 periods: aggregate metric means reproduced previously recorded `research/initial_summary.json` values exactly for the original six comparison metrics.
- v0.2 comparison: 3 capital scenarios × 30 seeds × 24 periods = **90 simulations and 2,160 audited period records**; zero money, raw resource, finished inventory or capital-account discrepancies. Raw files in `results/v02_capital_suite/` (not committed by design); report `research/v02_capital_experiment.md`, machine-readable summaries and paired seed effects in `research/`.
- No empirical calibration, external reproduction, historical validation, or formal proof of arbitrary parameter behavior.

## Architectural decisions and limitations

- Capital endowment is initially exogenous; investment converts one finished bundle from designated sector into one capital unit, after household consumption.
- One unit of capital provides fixed physical production capacity per step; depreciation is floored to integer units (small-stock rounding artifacts).
- Neither capital installation costs nor capital depreciation are part of full audited firm profit (positive operating surplus remains a simplified dividend basis).
- Investment budget is a fraction of firm cash after consumption; self-conversion is imputed internally, not posted as a transfer.
- Equity is a posted-price book-value proxy, not tradable capital market wealth. There is no credit, leverage, firm entry or household portfolio trading.
- One global physical resource; no geographic heterogeneity. No empirical calibration. Int64 overflow under extreme inputs remains unproven.
- Policy comparisons are conditional on these modeling assumptions; seed-to-seed Monte Carlo intervals omit structural model uncertainty.

## Next objective and release gates

1. Audit and benchmark the new capital code with independent property-based and toy-model checks; inspect economic mechanisms and model sensitivities.
2. Add richer household saving decisions and productive firm investment accounting (capital replacement costs, depreciation expenses/profit decomposition), and a capital-producing-sector capacity constraint.
3. Sweep ownership concentration and investment rules over a broad parameter grid, identify counterexamples, and report robustness alongside descriptive Monte Carlo intervals.
4. Preserve original v0.1 stable release. Merge/promote to v0.2 only when acceptance checks and scientific specification are complete.

**Source of truth:** GitHub repository and this file. No completed v0.2 release or real-world inference is claimed.
