# CIVITAS — Economic Model Completion Roadmap

Status: engineering plan, 2026-11-14. The project remains **0.2.0.dev0**; this plan is not a completed-feature claim. Stable `main` remains at v0.1; new economic development belongs on `feature/v0.2-capital-accounting`.

## Scope and completion criteria

CIVITAS is a local-first computational economics laboratory, not a promise to reproduce real societies. Distinguish three milestones:

1. **Accounting-complete core economy:** internally coherent household, firm and government balance sheets; material and monetary stock-flow conservation; reproducible price, labor, production and credit mechanisms.
2. **Research-ready economic laboratory:** falsification tests, controlled counterfactuals, sensitivity analysis, documented assumptions and at least limited external benchmarking.
3. **Extended artificial civilization:** demography, technology, spatial networks, institutions, environmental constraints and political interactions. This is a later modular roadmap, not a prerequisite for closing v0.2.

There is no objectively "finished economy" without choosing the domain and level of realism.

## What actually exists today

- Python agent-based simulation with households, firms, sectors, wages, hiring, posted-price consumption, goods inventories, renewable resources, a government tax/transfer account, and optional automation.
- Optional physical productive capital and depreciation; optional historical-cost inventory, COGS and firm book-equity reconciliations. The latter is explicitly simplified rather than full accounting standards compliance.
- Distinct household cash/savings balances and optional **bilateral savings-backed** investment credit, principal repayments and loss writeoffs; no endogenous money creation or modeled banks.
- Seller-choice, price and hiring feedback variants; region-restricted sales/hiring, partial price information, experimental affordability guard, and scenario-based sensitivity studies.
- World Genesis: configured, Hybrid (new-world default), and randomized **initial** states with explicit plans, independently seeded attribute substreams, full checkpoint/manifest, and deterministic verification. The generator is not empirically calibrated.
- CLI, CSV/JSONL/SQLite outputs, checkpoint/restart, independently audited experiments, and historical regression protection.

## Gate 1 — Core accounting closure and hardening (release-critical, highest priority)

Implement fully explicit, independently testable stock-flow accounts:
- Monetary: household cash, savings, firms, treasury; taxes, transfers, wages, dividends, purchases, extraction fees, loan principal and writeoffs.
- Real: raw-resource extraction, finished goods, purchased intermediate inputs, inventories, capital formation and depreciation. Avoid double-counting internally converted goods.
- Financial: assets and liabilities on **both** ends of each loan, debt servicing, bankruptcy recoveries, retained earnings and cost-basis valuation; define whether interest or loan losses have an income counterpart.
- Firm and household statements: beginning stocks + all period flows = ending stocks; reconciled balance sheets, income statement and cash-flow statement, with a separately documented simulation accounting convention.
- Explicit credit-market liquidity constraints; no phantom issuance or asset creation. If future banking or money creation is added, introduce a corresponding issuer liability by design.
- Signed-int64 overflow checks at intermediate operations, boundary scenarios, checkpoint schema migration and crash-safe replay. Every accounting path must be unit-tested and property-tested.

Acceptance: analytic two-agent/two-firm transaction examples, no unexplained conservation discrepancy across randomized stress cases, unchanged historical mode, deterministic restart equivalence, and an independent journal-based auditor.

## Gate 2 — Behavioral stability and identification (release-critical)

The 24-to-72-period experiments reveal late contraction strongly dependent on pricing and hiring rules. Do not choose a candidate solely because it raises output.

- Diagnose household affordability, accumulated firm liquidity, wage/profit distribution, goods stocks, shortage/surplus, capital maintenance and unemployment as **causal mechanisms**.
- Run matched-seed factorials of price adjustment, hiring expectations, cash endowments, consumption propensities, firm density and regional access with normalized per-capita starting assets.
- Expand beyond eight seeds; report paired uncertainty intervals, robust effect sizes, and negative or null results. Test 24/48/72/144+ periods, including initial burn-in and convergence/nonconvergence diagnostics.
- Separate structural shocks from chance with reproducible substreams. Verify that microstate changes preserve configured aggregate totals.
- Create adversarial tests for market starvation, no buyer/seller, bankruptcy, extreme inequality, credit defaults, empty sectors and resource scarcity.

Acceptance: no unexplained numerical instability; model outputs accompanied by mechanisms, conditional assumptions, uncertainty and sensitivity—not an assertion of realistic economic predictions.

## Gate 3 — Functional completeness of a closed economy (major development)

- **Firm lifecycle:** entry, exit, insolvency, investment, reinvestment and liquidation. Closing a firm must settle its inventory, loans, owner equity and employees without violating ledger identities.
- **Intermediate production:** input-output links between sectors, material procurement, capacity constraints, distinct per-sector technologies and input costs.
- **Labor market:** job search, separations, wage bargaining/adjustment, skills, training and occupational mobility; distinguish unemployment from nonparticipation.
- **Government:** budgeted spending/procurement, taxes, transfers and debt only if explicitly introduced; public services, transfers and public capital as separate stocks.
- **Household behavior:** budgets over multiple periods, heterogenous needs, income/savings decisions, debt/interest if modeled, and consumption under scarcity. Do not assume one behavioral rule fits every world.
- **Finance:** interest terms, collateral, lender concentration, liquidity stress, amortization, firm creditworthiness and default resolution; track risks and claims rather than only principal movement.
- **Markets:** price/quantity matching under regional access restrictions, competition/entry, inventories, rationing, information frictions and transaction costs.

Acceptance: a closed full-cycle example with wages, sales, taxes, public spending, savings, investment, debts, failures and goods flows that independently balances every period.

## Gate 4 — External credibility, performance and usability (research-ready milestone)

- Calibrate selected parameters against credible published demographic, input-output, employment, wealth and firm-size distributions for a **named** economy/time period; preserve uncalibrated synthetic presets separately.
- Compare emergent business cycles, firm size distributions, employment, prices, inequality and responses to shocks with real-world stylized facts. State where the model fails.
- Use out-of-sample prediction/validation, benchmark models, sensitivity/sobol or variance attribution, and independent methodological review where feasible.
- Retain precise provenance: code commit, scenario, world plan, seed, package versions, full intermediate checks, checkpoint and datasets.
- Profile 10k/100k/1m agent workloads before introducing compiled backends; verify numerical parity to Python.
- Build a local observatory with scenario/world editing, experiment comparison, balance-sheet audit trails and reproducible plots, after core integrity gates pass.

Acceptance: reproducible research bundle and independently executable validation with documented errors/limitations. Passing tests alone does **not** imply empirical validity.

## Gate 5 — Civilization expansion (optional and modular; not a v0.2 gate)

Endogenous technical change and invention, households' births/deaths/migration, geography and energy, multi-region trade/transport, social networks and trust, education, institutional rules and institutional evolution. Specify each mechanism, its ledger effects and test invariants before enabling it. Avoid hidden presets that determine ideological outcomes.

## Execution order

1. Publish and freeze the current World Genesis plus price/hiring intervention code and archives on the feature branch (without merging).
2. Gate 1: independent balance-sheet/journal auditor and overflow/replay hardening.
3. Gate 2: falsify late-period contraction mechanisms at standardized initial endowments.
4. Gate 3: close production chains, firm lifecycle, fiscal spending and financial contracts.
5. Gate 4: validation/scaling/observatory and a criteria-based reviewed release.
6. Gate 5: modular civilization enhancements.

**Release rule:** v0.2 can be marked stable only when its explicitly scoped core-accounting and behavioral-robustness requirements pass. A broader research-ready economy and a full artificial civilization are later independent milestones.
