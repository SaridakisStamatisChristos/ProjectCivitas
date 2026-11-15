# Latest continuation checkpoint — unified book-value balance sheets (2026-11-15)

- Version `0.2.0.dev0`; active development branch `feature/v0.2-capital-accounting`, stable `main` untouched. Previous verified development commit was `49683b324f2f36fdb91654bddc39ece8fa5a97f4`; this local checkpoint requires separately verifying GitHub publication.
- Added `src/civitas/balance_sheet.py`, `tests/test_balance_sheet.py`, `tests/test_book_research.py`, `research/run_book_balance_closure.py`, `docs/v02_book_balance_sheets.md`, `research/v02_book_balance_experiment.md`, source code changes to `engine.py`, `persistence.py`, `cli.py` and complete per-period verified research records.
- Fully traced periods now replay cash/principal and physical assets and check per-firm historical-cost earnings, per-household wealth flows, government/cash balances, owner-share attribution and consolidated book-net-worth non-double-counting. Trace-off historical metrics preserve their previous behavior. Checkpoint-based `balance-sheet` CLI exports compact/detailed book financial statements.
- Synthetic research: 18 main runs × 12 = 216 periods, 26,311 cash transfers and 11,858 physical events, no discrepancies. Standard credit settings originate **zero** loans; supplemental six seeded two-period credit boundary cases originate and default 1,200 cents total, all auditable. All research records checksum-verified and independently re-executed.
- These are **book costs and accounting residuals, not economic market values**. No automated bankruptcy, firm lifecycle, public debt, intermediary banking or intermediate-goods title accounting. No empirical calibration, not IFRS/GAAP, not a stable release. Tests/actual commit must be rechecked after publication.

---

# Verified local physical + monetary audit checkpoint — 2026-11-14

- Development branch: `feature/v0.2-capital-accounting`; stable `main` left unchanged; version remains `0.2.0.dev0`.
- Previous cash ledger published as `e8e9f26e7b09b2cb6d87693ceaef12fc58981549`.
- Latest physical ledger extension records per-firm production, cost basis, sales, depreciation, investment goods conversions and resource regeneration. It audits each firm and cross-checks corresponding posted prices and cash transfers. Historical scenarios remain default trace-off.
- Local regression suite **228 passed**. Independent execution/replay **20 synthetic runs, 240 periods, 14,116 physical events, 24,814 cash transfers**, all tracked identities zero. Research source and SHA-256 evidence in `research/run_physical_closure.py` and `research/v02_physical_ledger_20/summary.json`.
- Scope excludes full balance-sheet / GAAP compliance and intermediate-goods title accounting. Further release gates: comprehensive household/firm/government asset-liability statements, firm lifecycle, production chains, long-horizon robustness and external calibration. Do not merge into `main` or call v0.2 stable.
- **Published and remotely verified:** commit `49683b324f2f36fdb91654bddc39ece8fa5a97f4` (`12/12` changed files exact), feature branch only; stable `main` unchanged.

---

# 2026-11-14 v0.2 accounting closure checkpoint (local archive)

- Status: `0.2.0.dev0`, implementation only. Stable `main` intentionally untouched.
- Added independent per-account cash/credit event replay and explicit noncash writeoff tracing, opt-in with `transaction_trace=True` or CLI `--audit-ledger`; default scenarios preserve their histories.
- Audited 15 generated worlds ×12 periods: 180 periods, 69,425 cash transfers, 123,516,369 gross cents transferred, 0 identity failures; full suite **206 passed**.
- New files: `src/civitas/ledger_audit.py`, `tests/test_ledger_audit.py`, `research/run_ledger_closure.py`, `research/v02_transaction_ledger_15/summary.json`, `research/v02_transaction_ledger_audit_experiment.md`, `docs/v02_transaction_ledger_audit.md`.
- Remaining gate: extend event-level closure beyond monetary transfers and bilateral principal to physical inventory, historic-cost valuations and complete accounting statements. This is not scientific calibration.

---

# Current continuation checkpoint — World Genesis (2026-11-13)

- **Status:** CIVITAS remains `0.2.0.dev0`. Active branch `feature/v0.2-capital-accounting`. Stable `main` is not to be modified. Predecessor local checkpoint includes the price-and-hiring research (157 tests; that code was not previously pushed to GitHub).
- **Implemented:** separate `world_genesis.py` supporting configured, hybrid (new-world default) and randomized *initial* conditions. A generated scenario freezes once-drawn macro parameters; initialization samples household and firm cash, savings allocation, capital endowments, posted price multipliers, skills, and participation using independently seeded streams. Fixed-cost total allocation is exact in integer cents; all existing scenarios omit the Genesis field when disabled, preserving old config digests and trajectories.
- **CLI:** `civitas genesis --mode hybrid --name example --population 10000 --seed 42 --output results/world`, or `--plan scenarios/world_genesis/*.json`; `civitas verify-world --world results/world`; `run` and `resume` unchanged. Self-contained plan/scenario/checkpoint/manifest are generated together.
- **Verification:** `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q` must be rerun after implementation; `tests/test_world_genesis.py` tests seed replay, legacy parity, conserved initial money/capital/savings, malformed plan refusal, and altered-manifest detection. See `docs/v02_world_genesis.md`. The manifests are integrity digests, not cryptographic signatures.
- **Scientific limits:** no calibration, initial distribution choices are assumptions, randomized population/firm size changes scale-dependent market endowments unless explicitly normalized, ownership remains based on the existing fractional sampling rule, initial loan/inventory distributions are not injected. Test extreme integer cases before claiming general numerical safety.
- **Preservation:** publish price/hiring local source + Genesis additions to the existing feature branch, verify remote blob hashes and GitHub commit, then mark this checkpoint verified. Do not merge to `main` or declare a stable v0.2 release.

---

# Current continuation checkpoint — price and hiring interaction research (2026-11-13)

- **Active development:** `feature/v0.2-capital-accounting`, version `0.2.0.dev0`. Stable v0.1 `main` remains unchanged. Pre-change branch commit: `13c92d49fcaf185e1d65b78e049c44509cd7406a`.
- **Implemented:** optional `affordability_guard` price rule (`price_affordability_floor`, default 0.25), optional `blended` labor-demand expectation; no default behavior changes. Pure price/hiring formulas in `src/civitas/market_rules.py`, integrated with exact ledger and state checkpoints in `engine.py`, configuration/validation in `model.py`.
- **Execution evidence:** 2 populations × 8 seeds × 6 rule combinations × 72 periods = **96 completed simulations / 6,912 periods**, SHA-256 source/config-bound per-cell records and matched initial state/RNG. Research folders `research/v02_price_hiring_10000_72/` and `research/v02_price_hiring_2000_72/`, report `research/v02_price_hiring_stability_experiment.md`, independent auditor `research/audit_price_hiring_stability.py`. Eight accounting identities zero for every recorded period.
- **10,000-agent period-72 production:** default adaptive/inventory 160, guard/adaptive 210, inventory/blended 511.625, guard/blended 604.5, inventory/stationary 673.875, guard/stationary 762.25. All still contract from period 24. New price×hiring interaction is nonzero; real-economy inference unsupported.
- **2,000-agent sensitivity:** guard/stationary 200.5 vs inventory/stationary 208.375 (opposite sign), under a **different unnormalized population/endowment regime**.
- **Executed verification:** `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q` reported **157 passed** (Python 3.13.5, NumPy 2.3.5, pytest 9.0.2). Both compressed research archives were restored and independently audited, 48 runs / 3,456 periods each; source-bound dataset digest `7fcd60b536713884fe42cf74572c4f15e4c0ecaa45c1141e7d2e45478063df8e`. GitHub upload and remote integrity require separate confirmation.
- **Next scientific gate:** vary affordability threshold and initial cash distributions, normalized endowments and firm density; analyze persistent production contraction and check possible numerical/int64 extremes. Separate later economic calibration and release-readiness reviews; do not declare a stable v0.2 yet.

---

# CIVITAS continuation checkpoint — long-horizon demand-contraction diagnosis (2026-11-13)

- **Release:** `0.2.0.dev0` experimental development; the stable `main` remains CIVITAS v0.1.0 at `85d9671978df6ce40a58e895aee5cb1d2a938a58`. The active branch is `feature/v0.2-capital-accounting`; preceding GitHub commit `ba54ff516c4d90616a6e54d3594537c10c99f108`. This is not a stable release or empirical economic validation.
- **Implemented (additive research layer, no engine equations changed):** `research/run_demand_diagnostics.py` records 48 periods of household spendable cash, savings, firm cash, unmet demand, price affordability, posted prices, employment, production, inventories, resources and physical capital; six controlled interventions share initial agent/firm state and random streams. Atomic checksum-protected treatment shards support restart. `research/audit_demand_diagnostics.py` independently recalculates summaries and validates each stock-flow record. `tests/test_demand_diagnostics.py` adds adversarial tests.
- **Execution:** Python 3.13.5 / NumPy 2.3.5 / Linux x86_64. `PYTHONPATH=src:. python -m pytest -q`: **144 passed** (136 previous + 8 new). Eight seeds × six treatments × 48 periods × 10,000 agents = **48 completed runs / 2,304 audited periods**, eight accounting discrepancy classes all zero. Independent standard-library auditor passed; matched initial-state/RNG hashes checked across treatment arms.
- **Control result:** final-period production declines 1,324.75 units at t24 to 661.375 at t48 while common renewable resource rises, unsold inventory rises and household spendable cash declines. Firm monetary share grows from ~34.1% to ~73.3%; budget-unmet fraction reaches ~86% of attempted purchases. This is **model-specific**, not a human economic prediction.
- **Counterfactuals:** fixed posted prices have mean production 1,502.125 at t48 (paired +840.75 relative to control); stationary hiring has 1,143.625 (+482.25). Eliminating depreciation alone has 679.625 (paired +18.25, Monte Carlo interval includes zero), showing capital depreciation is not sufficient. No-saving has 531.75; full dividends have 675.5. See `research/v02_demand_contraction_experiment.md` and `research/v02_demand_diagnostics_raw.zip` (full seed-level raw evidence), `research/v02_demand_diagnostics/summary.json` and research report for exact intervals and limitations.
- **Scientific caveats:** eight seeds are exploratory; the fixed-price result is a holistic simulator intervention with downstream effects, not proof that prices are the sole cause or that price controls work in real economies. The mean price falls between t24 and t48 in the historical trajectory; path-dependent liquidity and hiring feedback, not simple perpetual inflation, require further tests. Historical cost accounting is stylized, external model calibration absent, and full robust int64 overflow proofs absent.
- **Next objective:** experimentally isolate affordability-aware price adjustment and wage/hiring mechanisms with explicit alternative equations, longer horizons, multiple sizes and resource regimes; do not select mechanisms by desired output. Preserve data and all tests. Keep v0.2 on development branch until acceptance review.
- **Repro commands:** `PYTHONPATH=src:. python -m pytest -q`; `PYTHONPATH=src:. python research/run_demand_diagnostics.py --seed N --output research/v02_demand_diagnostics` for seeds 1–8; `--finalize --seeds 1,2,3,4,5,6,7,8`; `python research/audit_demand_diagnostics.py research/v02_demand_diagnostics`; to restore GitHub data run `PYTHONPATH=src:. python research/restore_demand_diagnostics.py research/v02_demand_diagnostics_raw.zip results/restored_demand`.
- **Preservation status:** GitHub commit and remote file hashes must be verified after publication; don't infer successful push from local archives alone.

---

# CIVITAS continuation checkpoint — credit mechanism/horizon falsification (2026-11-13)

- **Stable `main`:** v0.1.0 at `85d9671978df6ce40a58e895aee5cb1d2a938a58`, deliberately unchanged.
- **Active branch:** `feature/v0.2-capital-accounting`; development version `0.2.0.dev0` (NOT a v0.2 release). Previous branch head: `b0b14987c4f7656366e80b1e5dd1d0b84430bbdb`.
- **New implementation:** `research/run_credit_pathways.py` matches all initial agent/firm state and RNG within a seed, tests zero-lender sham versus no-credit negative control, and enforces period-by-period loan roll-forward in addition to eight physical/monetary accounting identities. Atomic treatment-level shards are resumable; saved seed-level reports verify checksums, configurations, source digest, period completeness and matched initial states.
- **New independent audit:** `research/audit_credit_pathways.py` (stdlib only) recomputes sha256, account identities, principal roll-forward, negative controls and reported production means from the raw recorded data. `research/restore_credit_pathways.py` reconstructs the compressed data from the GitHub repository and verifies original SHA-256 hashes. `tests/test_credit_pathways.py` covers maliciously modified data, interruptions, deterministic sham paths, and archive restoration.
- **Execution evidence:** `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q` => **136 tests passed** (Python 3.13.5, NumPy 2.3.5). Six matched seeds × 12 treatments × 48 periods × 10,000 agents = **72 actual simulations / 3,456 audited periods**, with zero discrepancies in all eight core accounting classes and zero principal roll-forward errors. Independent audit passed all six seeds. See `research/v02_credit_pathways_experiment.md`, `research/v02_credit_pathways_10000/summary.json` and six original gzip-compressed seed shards.
- **Scientific finding:** At period 24, credit effect reversals by saving rate appear large, but by period 48 production differences against no-credit controls are much smaller; nearly all approximate paired Monte Carlo intervals contain zero. Both no-credit and credit-enabled outputs also fall sharply at period 48 under the selected synthetic rules. These are six-seed *model* observations, NOT real-world forecasts or long-run convergence claims.
- **Known limitations:** No banks, interest, credit pricing, real cost of funds, loans beyond defined maturities, default recovery, empirically grounded behavioral functions, verified long-run stationarity or proof against all extreme int64 future-state overflows. Period 48 outstanding debt happens to be zero in the observed configurations; not a universal invariant. Six seeds insufficient for strong scientific conclusions. Detailed diagnosis of why overall output declines between periods 24 and 48 remains open.
- **Next work:** explicitly decompose the period 24–48 production decline through changes in household liquidity, firm hiring, prices, real capital, effective resource capacity, and goods market matching; then repeat robustness across multiple seeds/horizons and add further analytical checks. Keep branch development-only and do not merge until acceptance criteria and independent review are satisfied.
- **Preservation rule:** remote commit SHA and exact changed-file blob hashes must be verified after publish; do not claim upload merely from a local archive.

---

# Latest CIVITAS continuation checkpoint — resumption and financing sensitivity (2026-11-13)

- **Stable branch:** `main` remains v0.1.0; all new research belongs on `feature/v0.2-capital-accounting`. Software version `0.2.0.dev0` is NOT a complete release.
- **Recovery:** the prior fully tested credit/resource-cost extension was successfully committed to GitHub at `5c40bcb8e18280352161f99fd9663e62940fd78a`, preserving 24 files and closing the previous unpushed gap.
- **New code:** `research/run_credit_sensitivity.py` implements complete atomic per-seed recording, strict dataset digests, deterministic within-cell initial-state matching, multi-arm experimental design, and paired Monte Carlo intervals. `tests/test_credit_sensitivity.py` adds seven targeted adversarial/reproducibility tests.
- **Completed local evidence:** 96 full, 10,000-agent, 24-period simulations across 8 seeds and 12 cells = **2,304 audited periods**, with all eight configured discrepancy checks equal to zero. Data are in `research/v02_credit_sensitivity_10000/`; detailed report at `research/v02_credit_sensitivity_experiment.md`.
- **Executed tests:** `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q` => 128 passed (Python 3.13.5 / NumPy 2.3.5), including the 121 previously preserved tests.
- **Design caveat:** total initial money and capital are equal across the two firm-density settings, but firm IDs, ownership and market structures necessarily differ. Within each density/saving triple, financing arms have equal seeded initial state/RNG.
- **Main observation:** with 25% household savings, lending increased output in both firm-density cases. With 75% savings, it reduced output in both. Defaults and outstanding debt differ by contract maturity. These are *conditional in-model* observations from 8 seeds, not empirical policy predictions.
- **Publication gate:** the new sensitivity evidence remains a research/development result and must only be marked remotely preserved after independent GitHub tree/head verification. Do not merge to `main` or call v0.2 released.
- **Next objective:** investigate why the sign of credit's production effect flips with saving propensity: isolate demand reduction, credit funding, maturity/default rules, and firm investment decisions over longer horizons; address loan-contract scaling and signed-int64 boundary fuzzing.

---

# Latest CIVITAS continuation checkpoint — bilateral credit and resource-input accounting (2026-11-13)

- **Stable:** `main` = v0.1.0, unchanged. **Development branch:** `feature/v0.2-capital-accounting` and version `0.2.0.dev0`. Prior verified checkpoint: `e5c59783a32946c828c95c7d43bcca46a0e56a30`. No merge authorized or performed.
- **Implemented locally:** optional direct savings-funded investment loans, lender and borrower balance-sheet accounts, integer-cent principal transfers, repayment and explicit noncash maturity default; opt-in physical resource-use fee transferred to government and included in historical inventory production cost; all original market, capital, labor and regional rules retained.
- **Files:** `src/civitas/finance.py` new; updated `model.py`, `state.py`, `engine.py`, `metrics.py`, `persistence.py`; `tests/test_financial_intermediation.py`; `research/run_credit_experiment.py`; `research/verify_legacy_parity.py`; `docs/v02_credit_resource_accounting.md`; four new scenario JSONs and base config; recorded evidence under `research/v02_credit_experiment_{1000,10000}/`.
- **Verification:** `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q` reported **121 passing tests**, including 109 historical ones plus 12 new credit, resource cost, joint-mechanism, checkpoint, and experiment-runner tests. Environment Python 3.13.5, NumPy 2.3.5, Linux x86_64.
- **Legacy behavior:** independent executable old/new comparisons of 6 scenarios × 3 seeds × 12 periods = **216 compared states / 15,768 historical metrics identical**, new mechanisms disabled. Evidence: `research/v02_credit_legacy_parity.json`; runner `research/verify_legacy_parity.py`.
- **Executed experiments:** four credit/resource-fee configurations × 30 seeds × 24 periods at 1,000 agents (120 runs, 2,880 audited periods) plus four configurations × 8 seeds × 24 periods at 10,000 agents (32 runs, 768 audited periods) = **152 complete runs / 3,648 checked periods**. Zero money, resource, goods, capital, household/firm cash-flow, historical book-equity and bilateral debt discrepancies. See report and period CSVs.
- **Result:** at 1,000 agents without resource fee, credit enabled changed final production from 136.30 to 127.53 mean units, with observed repayments and defaults. At 10,000 agents and just six low-capital firms, the configured economy originated zero loans; enabling credit was inert. **Not an endorsement or refutation of credit in real economies.**
- **Incomplete:** a larger 10,000-agent/60-firm, four-arm normalized campaign exceeded runtime limits and has **no complete dataset**; do not count it. A two-seed smoke showed loans can originate under that density but does not constitute effect measurement.
- **Acceptance gates remaining:** firm-density normalized long-horizon credit study; interest/loan-risk alternatives; full resource opportunity cost; comprehensive financial statements, default sensitivity and extreme-input overflow audit; independent scientific calibration. No stable v0.2 release.
- **Next engineering priority:** bounded, resumable normalized-density experiments and adversarial debt/accounting stress, then complete model-economy audit and release gate.
- **GitHub preservation:** this checkpoint must be paired with the actual verified new development commit; do not infer a remote commit from local completion.

---

# Latest CIVITAS continuation — firm-density robustness and historical-cost accounting (2026-11-13)

- **Status:** `0.2.0.dev0`, **development only**. Preserve `main` v0.1.0. Branch: `feature/v0.2-capital-accounting`. Predecessor verified GitHub commit: `25589844ab3495abcc97b7a093fb7cb3644188ce`.
- **New reproducible density study:** `research/run_region_density.py`, `research/v02_region_density_10000/` and `research/v02_market_density_10000_experiment.md`. Two densities (10 and 20 firms/sector) × four price-information/access arms × eight seed replicates × 24 periods at 10,000 agents. **64 simulations / 1,536 audited periods**; strict shard hashes and within-density exact-state/RNG controls. Initial firm cash and physical capital normalized in total between densities. Model trajectories differ substantially with seller density; comparison across densities is descriptive, not individually identical firm identity.
- **New opt-in cost-basis accounting:** `src/civitas/economy_costs.py` and modified model/state/engine/persistence. Historical-cost inventory carrying accounts, moving-average COGS with exact integer rounding, capital acquisition cost, noncash carrying-cost depreciation, zero-output labor expensing and **per-firm book-equity reconciliation**. The historical proxy remains observable; cost-mode dividends depend on synthetic cost-basis earnings. Does **not** claim comprehensive GAAP/IFRS financial statements.
- **Checkpoint compatibility:** old versions 1, 2 and 3 load with zero historical-cost ledger because the feature is disabled in old configurations. Cost-enabled runs serialize their carrying basis in new format 4. Old format-3 checkpoints claiming enabled historical-cost accounting are rejected; historical basis cannot be fabricated.
- **Cost-enabled experiment:** `research/run_cost_basis_comparison.py`, `research/v02_cost_basis_10000_8/`, `research/v02_cost_basis_experiment.md`. **16 simulations / 384 audited periods** at 10,000 agents, seeds 1–8, two dividend-policy arms, 24 periods. Conditional final production mean legacy proxy 1,950.50 versus historical-cost 1,926.13. Not an accounting-neutral policy comparison. A 30-seed attempt exceeded execution capacity before a complete dataset was persisted; not counted.
- **Software checks:** `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q` observed **109 passed** with Python 3.13.5 / NumPy 2.3.5 / pytest 9.0.2 (Linux x86_64). Added independent unit-cost allocation tests, firm cost-book identities, v4 replay, v3 refusal, randomized cost-enabled scenarios, and evidence-runner regression. **96 historical seed-period records** match byte-for-byte with cost mode disabled. All checked periods in the completed new experiments have zero monetary, goods, resource, physical-capital, household-flow and firm-flow discrepancies; all cost-enabled periods additionally have zero individual firm book-equity discrepancy.
- **Preservation gate:** publish all changed source/test/docs and recorded seed data to development branch; verify resulting GitHub commit and blob hashes before claiming remote preservation. Stable `main` must remain unchanged.
- **Most urgent remaining work:** complete multi-seed/longer-horizon sensitivity at diverse firm densities/region counts, account for priced resource and input costs and overhead (or continue explicitly treating the historic cost model as incomplete), design two-sided savings-to-investment financing and liabilities, strengthen signed-int64 extreme-input guards and independent scientific review. **DO NOT** call v0.2 stable, empirically calibrated, or proof of social claims.

---

# Latest continuation checkpoint — regional assignment and price information (2026-11-13)

- **Status:** `0.2.0.dev0` experimental development. GitHub branch `feature/v0.2-capital-accounting`; stable `main` remains v0.1. Parent development commit before this extension: `3472357dab4b9c3e2f2b664deef25ce884cf9b10`.
- **Implemented:** separate RNG balanced region assignment, optional two-observed-price-quotes buyer information (independent of legal access), observation-level missed-opportunity diagnostic, strict validation, independently reproducible exact-state factorial runner and checkpointed scenario files.
- **Local tests executed:** 97 passed, including 82 earlier tests and 15 tests in `tests/test_region_information.py`.
- **Full replicated experiment:** 2 assignment rules × 2 price-information rules × 2 sales-access rules × 30 exact-matched seeds × 24 periods = **240 complete simulations, 5,760 audited engine periods** at 1,000 agents; all six accounting identity classes zero. Per-seed SHA-256 and identical post-run RNG verified; exact output retained in `research/v02_region_information_1000/`.
- **Standard-scale smoke:** 10,000 agents × 2 seeds × 8 arms × 3 periods = **16 complete runs, 48 checked periods**, without claiming a full long-horizon replicate.
- **Observed (1,000-agent):** modulo open production 0.13347/full vs 0.12703/two quotes; modulo sales-local 0.11040/full vs 0.12787/two quotes. The quote/access interaction is +0.02390 production units per person; this is internal-model evidence only. See `research/v02_region_information_experiment.md`.
- **Next scientific objective:** replicate at 10,000 agents with longer horizon and multiple per-region firm densities; then implement inventory cost-basis / COGS before adding realistic investment finance. The same unresolved external calibration, int64 extreme inputs and long-term convergence limitations remain.
- **Acceptance:** DO NOT release v0.2 or merge to `main`. Maintain the mathematical and software verification versus empirical-validation distinction. The latest GitHub commit and exact hashes must be verified following repository upload.

---

# Latest continuation checkpoint — matched-agent access (2026-11-13)

- **Status:** v0.2.0.dev0, development. Stable v0.1 on `main` remains unchanged. Previous verified development ref: `96703d9dfa39e5e753ae7a710bb398876496ec78`. The matched-market patch is not a release; commit SHA must be verified from GitHub after writing.
- **Files:** `src/civitas/model.py`, `src/civitas/engine.py`, `tests/test_matched_market_access.py`, `research/run_matched_market_access.py`, `docs/v02_matched_market_access.md`, `research/v02_matched_market_access_experiment.md`, and all files in `research/v02_matched_market_30/`.
- **Verified local tests:** `PYTHONPATH=src:. python -m pytest -q`, **82 passed** (Python 3.13.5, NumPy 2.3.5, pytest 9.0.2; Linux x86_64). The 64 prior tests remain; 18 additional parameter, state-matching, replay, journal and data-integrity tests have been added.
- **Executed paired experiments:** 4 access treatment arms × 30 exact-matched seeds × 24 periods at 10,000 agents, **120 simulations / 2,880 complete period states**; six accounting discrepancy classes zero. Exact common initial state and RNG confirmed per seed and RNG matches after each full run. See `research/v02_matched_market_access_experiment.md`.
- **Key observation:** mean final-period production/person open 0.251247, sales-limited 0.121157, labor-limited 0.264697, both 0.121650. Sales/labor interaction -0.012957, approximate 95% seed Monte Carlo interval [-0.016608, -0.009306]. This tests **only simulator mechanisms**.
- **Important limitation:** only consumer seller pools and worker hire pools are gated. Resource allocation, government transfers, capital procurement and the global unmet-demand signal remain shared; not full isolation or calibrated economic behavior. Initial regions use deterministic ID modulo and may introduce assignment artifacts.
- **Remaining v0.2 release gates:** sensitivity to region assignment, information flows and price mechanisms; independently verified inventory/COGS and profit accounting; explicit two-sided savings-investment funding; multi-horizon stress and externally validated claims. Never label v0.2 finished or merge into stable `main` without review.
- **Reproduction:** `PYTHONPATH=src:. python -m pytest -q`; use `--seed 1...30` then `--finalize` and `--verify-only` with `research/run_matched_market_access.py`. Data hashes and experiment scenario in the research folder.

---

# CIVITAS continuation checkpoint

## Latest verified factorial interaction checkpoint — 2026-11-13

- **Stable branch:** `main` remains v0.1.0; **active branch:** `feature/v0.2-capital-accounting`. Development release stays `0.2.0.dev0` and is **not** a completed v0.2.
- **Baseline commit before this study:** `5561d0f0716220dfe0948e2d041f00f50e96ce94`. This checkpoint is pending GitHub revision identification until remote publication is confirmed.
- **Implementation:** `research/run_market_factorial.py` performs a complete 2×2×2 factorial intervention of buyer seller search (mixed versus favorite), fixed/adaptive prices, and adaptive/stationary hiring. It records every topology-level period, audits conservation every engine step, uses atomic per-cell datasets and verifies dataset SHA-256, full row completeness, scenario digest and configuration before aggregation. `tests/test_market_factorial.py` exercises interaction arithmetic, invalid factors, a complete mini factorial, tamper detection and joint-intervention checkpoint replay.
- **Executed verification:** `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q` reported **64 passed** on Python 3.13.5 / NumPy 2.3.5. Eight cells × eight master seeds × 11 market instances × 24 periods = **704 completed simulations**, **16,896 internally checked periods**, **3,072 topology-period rows**; all six conservation/flow discrepancies were zero in the checked runs. All eight cell files were complete with recorded checksums. An independent CSV recount reproduced the three-way interaction mean exactly.
- **Scientific result:** the integrated-minus-isolated production gap depends nonadditively on seller ranking, pricing and hiring feedback. The gap's three-way interaction is −0.0664125 production units/person (approximate 95% Monte Carlo interval [−0.07111,−0.06172]), conditional on exactly these synthetic model assumptions and eight seeds. See `research/v02_market_factorial_experiment.md` and archived `research/v02_market_factorial_8seed/`.
- **Critical remaining confounding:** isolated communities and integrated market do not have *identical individual initial agents*; consumer firm access (60 vs 6) and employee matching pools differ simultaneously. Do not interpret topology contrast as a pure market-size effect. Small seed count, model and parameter uncertainty, no empirical calibration.
- **Highest priority next scientific engineering gate:** in the **same integrated 10,000-agent population**, experimentally restrict seller choice to six local firms, then independently restrict hiring to community labor pools, retaining initial agents and total endowments; audit paired counterfactuals. Next add inventory cost-of-goods-sold/asset basis and eventually correctly recorded two-sided financial intermediation.
- **Existing release gaps:** no fully accrual-compliant profit or complete balance sheets, no lending, no external scientific calibration, extreme-input overflow risks, incomplete longer-horizon sensitivity. Do not merge development branch to `main` until release criteria pass.

---

# CIVITAS continuation checkpoint

## Latest verified market-mechanism checkpoint — 2026-11-13

- **Branch:** `feature/v0.2-capital-accounting`. The stable `main` remains v0.1.0. Development version is still `0.2.0.dev0` and **not a released v0.2**.
- **Mechanisms implemented:** optional one-factor controls for buyer seller-search ranking (`mixed`, `cheapest`, `favorite`), hiring expectations (`adaptive`, `stationary`), and inventory ration order (`random`, `household_id`); `price_adjustment=0` provides a price-fixed control in the recorded scenarios. Default behavior and previous scenario rules remain unchanged.
- **Scientific observability:** market-sector price dispersion, sales concentration (raw seller HHI, not directly comparable across firm counts), and share of active sellers; all prior conserved financial and physical accounting metrics remain checked.
- **Latest executed evidence:** `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q`: **56 passed** on Python 3.13.5, NumPy 2.3.5. Market ablations: 6 rules × 12 master seeds × (one integrated 10,000-agent economy plus ten independent 1,000-agent communities) × 24 periods = **792 executable runs and 19,008 verified engine periods**; zero discrepancies in money, resource, finished-goods, capital, household account flows and firm account flows. **3,456 topology-level period rows** stored. Reference outputs matched **288 previous baseline seed-period records** on production, consumption, and employment.
- **Main within-model discovery:** integrated-minus-isolated final production/person gap changes from +0.1430 (original rules) to +0.2834 (all buyers cheapest-first), −0.0053 (all buyers favorite-first), +0.0323 (stationary hiring expectation), +0.0220 (fixed posted prices), +0.1396 (fixed household-ID ration order). One-factor effects interact; this is evidence of **model mechanism sensitivity**, not causal evidence about real-world society. Monte Carlo intervals include seed variability only.
- **Research and reproduction:** `research/run_market_ablation.py`, `research/analyze_market_ablation.py`, `research/v02_market_ablation_experiment.md`, `research/v02_market_ablation_12/`, and `docs/v02_market_mechanisms.md`.
- **Highest-priority next scientific test:** factorial interactions among seller ranking, adaptive posted prices and hiring feedback, while holding labor accessibility and seller pools separately fixed. This is needed to rule out direct/indirect mechanism confounding.
- **Unresolved v0.2 release gates:** missing inventory cost-of-goods-sold/full balance sheet; no two-sided savings-to-investment financial intermediation; no real-world calibration; longer horizons and more extensive seeds/sensitivity; remaining extreme-integer overflow possibilities. Do **not** promote to main on current evidence.

---

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
