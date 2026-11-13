# CIVITAS continuation checkpoint

## Latest verified scientific robustness checkpoint — 2026-11-13

- **Branch:** `feature/v0.2-capital-accounting`; `main` remains frozen at v0.1.0 commit `85d9671978df6ce40a58e895aee5cb1d2a938a58`. Development version remains `0.2.0.dev0` (NOT a released v0.2).
- **New executable components:** `src/civitas/normalization.py` (exact rational initial firm-density/cash/capital/resource normalization); `research/run_population_normalized.py` and `research/run_market_partition_control.py`; 12 explicit normalized scenarios; randomized invariant and restoration tests; initial int64-state and transfer-credit overflow guards.
- **Execution evidence:** `PYTHONPATH=src python -m pytest -q` gave **45 passed** on Linux x86_64, Python 3.13.5, NumPy 2.3.5, pytest 9.0.2. The 72-case randomized conservation/checkpoint tests passed. 6 scenarios × 30 seeds × 24 periods at both 1,000 and 10,000 agents = **360 executed simulations / 8,640 audited period states**. Additional ten-community control: 2 scenarios × 30 seeds × 10 independent 1,000-agent communities × 24 periods = **600 executed simulations / 14,400 audited internal periods**. No monetary, resource, finished-goods, capital, household-flow, or firm-flow discrepancy was reported in those runs.
- **Critical research finding:** even when 1,000 and 10,000 agents start with exactly equivalent cash, capital, resources and firms *per person*, the synthetic saving/ownership outcomes are **not invariant to population**. An integrated 10,000-agent market differs sharply from ten independent 1,000-agent markets using the same total initial money, firms, natural resources and capital. See `research/v02_population_normalization_experiment.md`. Earlier broad interpretations of a universal savings effect do not survive this test.
- **Scientific limitations:** ownership share 3% is rounded to 3.2% in 1,000-agent case; larger integrated market has more cross-community seller competition; logistic physical-resource rounding and behavioral decision rules are still size-dependent; model uncalibrated. Approximate MC intervals describe seed variability under fixed assumptions, not reality.
- **Highest-priority next task:** isolate *which* market mechanisms (consumer seller-choice, posted-price updates, inventory rationing, hiring feedback) drive population/topology dependence. Test market-partition fixed pools as a reference. Separately implement cost-of-goods-sold/inventory valuation and correct two-sided borrowing/equity funding before claiming accounting-complete v0.2.
- **Preservation:** all new source, tests, scenarios, report and per-period evidence are under version control on the development branch; keep `main` unchanged. Do not label v0.2 complete or economically validated.

---

## Preserved versions and status — 2026-11-13

- **Stable release:** v0.1.0 on GitHub `main` at commit `85d9671978df6ce40a58e895aee5cb1d2a938a58` (unchanged).
- **Active branch:** `feature/v0.2-capital-accounting`. The preceding verified v0.2-dev checkpoint was commit `30493bc92233a81b96dc4ba6642a8631de6c7d72`. This document describes the next savings/firm-flow slice; commit verification is recorded in the GitHub commit itself after upload.
- **Development version:** `0.2.0.dev0`, NOT a completed v0.2 release. Do not promote to main until remaining gate review.
- **Environment:** Python 3.13.5, NumPy 2.3.5, pytest 9.0.2, Linux x86_64.

## Implemented and locally executed

- Original v0.1 population, employment, wage, tax, transfer, sector production, consumer market, resource, automation and full save/restore functionality retained.
- Original v0.2 physical capital, real-goods investment, depreciation, concentrated seeded owner claims, disposable income and equity-marked household net worth retained.
- Household cash and separate non-interest-bearing `household_savings` reserve accounts; income-based saving subject to liquid-cash floor; logged essential-sector savings withdrawals; **no savings-to-investment intermediation**.
- Firm capital-goods sales recognized as revenue of the supplier; purchases not charged as current operating expenses; noncash depreciation valued at posted capital quote. Defined **profit proxy**, not full inventory-adjusted net profit.
- Exact reconciliation of each household's money assets and each firm's cash movements and government cash; documented total-money, finished-goods, capital, and resource conservation. Reject invalid account IDs.
- Nonpickle checkpoint format 3 serializes household savings and all existing capital arrays; historical versions 1 and 2 are read with zero-initialized savings. Existing seeded RNG is retained.
- Six versioned configurations in `scenarios/savings_ownership/`, standalone reproducible factorial experiment runner in `research/run_savings_sensitivity.py`, generated reports and source result datasets in `research/v02_savings_results_*/`.

## Verified local evidence

- `PYTHONPATH=src pytest -q` reported **37 passed**, including new savings/flow tests and 28 previous tests.
- Exact behavioral compatibility check: original four v0.1 scenario configs, 12 periods, every one of the original 49 metrics per period unchanged when compared with the previous capital-development source archive.
- Real checkpoint test: previous v2 `capital_reinvestment` seed-7 archive restored and advanced one period with zero money, goods and firm cash-flow discrepancies.
- Savings/ownership factorial: **6 configurations × 30 seeds × 24 periods** at 1,000 agents, and again at 10,000 agents. **360 simulations = 8,640 tested period states**, zero per-period money, resource/goods/capital/household-flow/firm-flow reconciliation discrepancies (see research report for five asserted identities and seed-level final-period data).
- Capital-only earlier experimental results still preserved in `research/v02_capital_experiment.md`; original v0.1 experimental records still preserved.
- Experimental 10,000-agent (8% ownership) saving 0% → 30%: mean final production 1,944.7 → 1,576.6 units, disposable-income Gini 0.5369 → 0.5895. CONDITIONAL model evidence, NOT real-world inference.

## Important assumptions and unresolved defects

- Savings sit idle as reserved cash; firms do not borrow from them. This model can consequently exhibit lower spending, lower production and differing income inequality under high saving propensities.
- Ownership changes only the registered income/marked-equity recipient pool; it does not simulate all cooperative governance mechanisms or fully capitalized asset markets.
- Population scaling holds fixed six firms, firm endowments and resources: 1,000 vs 10,000 are not matched per-capita economic configurations. The saving effect differs across them. Normalize firm density/initial per-capita stocks before causal scaling claims.
- Firm profit is an accrual proxy, not net earnings: no inventory FIFO/COGS, loans, liabilities, market pricing of equity, comprehensive taxes or full national accounts.
- Total monetary stock is conserved by specified transfers, but extreme int64 overflow not formally ruled out. Consumption and wage behavior are deliberately stylized. No empirical calibration or external independent review.
- Factorial compact research data retain final-period seed observations, paired contrast summaries, scripts and scenario configs; no complete per-period trajectory files for this campaign.

## Next development objective and release gate

1. Implement **population-normalized endowment and firm-density controlled experiments**, verify whether apparent saving effects persist when per-capita endowments remain constant.
2. Add independently verified cost-of-goods-sold and inventory accounting or clearly retain current profit-proxy status. Do not model lending or household investment without two-sided ledger treatment.
3. Test longer horizons, alternate behavioral rules, and parameter sensitivity; audit extreme int64 configurations and randomized falsification cases.
4. Keep the stable v0.1 `main` unchanged. Commit tests and scientific evidence to the v0.2 development branch; only promote after the full v0.2 acceptance criteria are met.

**Scientific classification:** executable research model and code-verified experiments, **not** empirical predictions, proof of institutional superiority, or a finished v0.2 release.
