# CIVITAS v0.1 foundation + v0.2 experimental capital branch

> **Experimental v0.2 physical reconciliation:** trace mode now independently audits firm inventories, raw resources, capital and historical-cost flows against cash settlement. [Audit methodology](docs/v02_physical_ledger_audit.md) · [Reproducible 20-world evidence](research/v02_physical_ledger_experiment.md). This branch is not a stable v0.2 release.

> **Published development branch (2026-11-14):** World Genesis and price/hiring research are on `feature/v0.2-capital-accounting`, source [5a1faad](https://github.com/SaridakisStamatisChristos/ProjectCivitas/commit/5a1faad9656a922ffc4b27dbb1b4179ab2765e84). Stable `main` stays v0.1. Version `0.2.0.dev0` remains experimental. See the [economy completion roadmap](docs/economy_completion_roadmap.md).

**Release status:** v0.1 remains the stable foundational baseline on `main`. The `feature/v0.2-capital-accounting` branch introduces an **experimental, not yet final** v0.2 development slice.

**Computational Intelligence for Virtual Institutions, Technology, and Artificial Societies**

CIVITAS is an experimental, local-first artificial-society simulator. The v0.1 release simulates heterogeneous agents, households, posted-price firms, labor, physical production, consumption, taxes, income transfers, concentrated firm ownership and dividends, automation, and a finite renewable common resource. All economics are **explicit model assumptions**, not real-world forecasts. No LLM or paid API is required.

## Linux / macOS / Windows (Python 3.11+)

```bash
git clone https://github.com/SaridakisStamatisChristos/ProjectCivitas.git
cd ProjectCivitas
python3 -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
pytest -q
```

Run an experiment:

```bash
civitas run --scenario scenarios/market.json --steps 24 --seed 42 --output results/market_42
civitas resume --checkpoint results/market_42/checkpoint.npz --steps 12 --output results/market_42_continued
civitas suite --scenarios scenarios/*.json --seeds 7,11,13 --steps 24 --output results/comparison
```

Without installation, after installing NumPy: `PYTHONPATH=src python -m civitas run --scenario scenarios/market.json --output results/market`.

Outputs per run: `config.json` (exact scenario), `metrics.csv` (all periods), `journals.jsonl` (categorized transfers), `experiments.sqlite3` (experiment metadata), `metadata.json` (runtime, software and configuration digest), `checkpoint.npz` (exact agent and RNG state). Suite writes `summary.json`, with replicate means and sample standard deviations. `results/` is ignored by Git; preserve experiment directories separately when needed.

## Explicit model boundaries

- Time step is **an abstract economic period**, not a month/year.
- One household is up to four agents. **Demand is one sector-specific bundle per household per period**, not per individual.
- Labor participation, productivity and sector preferences are synthetic and not demographically calibrated; skills influence output, not wages.
- Firms have finite cash and inventory. Wage expenses precede production and sales. Prices adjust by mechanical shortage/surplus rules. No borrowing, credit, interest, firm entry, unemployment benefits, real-world macro calibration or commercial optimization.
- A firm is owned by a seeded subset of households, which receive a specified share of *positive current operating surplus* (revenue minus current wages), not a complete audited corporate profit measure.
- One renewable resource feeds all production sectors; no separate environmental emissions, housing or energy market yet. At zero stock logistic regeneration cannot restart.
- Automated productivity increases produced units per worker; it does not independently change demand, ownership, wages, or skills.
- Monetary totals are conserved; the model **does not** contain monetary issuance. Each money transfer has identified accounts. Physical inputs and outputs are integer units.
- Household *liquid wealth* is cash only; firm equity is not included, so it is **not** comprehensive household net worth.
- One stochastic outcome is not a robust conclusion; use multiple seeds and sensitivity checks.

See [docs/mathematical_model.md](docs/mathematical_model.md), [docs/scientific_assumptions.md](docs/scientific_assumptions.md), [docs/validation.md](docs/validation.md), and [CHECKPOINT.md](CHECKPOINT.md).

## What is implemented, not merely planned

- Deterministic NumPy RNG with exact NPZ checkpointing and replay
- 10,000-agent default; compact NumPy agent arrays; configurable population including zero
- Posted-price consumer markets with household cash constraints, rotating ration order, inventory and resource accounting
- Firms hire agents, pay wages, produce goods and receive sales proceeds
- Government levies configurable wage tax and sends transfers to lowest-wage households
- Firms return a fraction of positive period surplus to seeded household owners
- Four versioned examples: market, mixed redistributive, automation shock, resource scarcity
- Basic aggregate metrics including inequality, monetary/goods/resource discrepancy and wall time
- CLI, CSV/JSONL/SQLite outputs, replicated suite with means and standard deviations, correctness tests

**Not yet implemented:** endogenously evolving firm entry, interest/credit, capital depreciation, geographic migration, social networks, voting, multi-resource environment, automated empirical calibration, interactive dashboard, GPU computing, confidence intervals, or LLM research agents. These remain subsequent milestones.

## Development and reproduction

Before publishing a model-derived result, record the scenario JSON, software version, seed(s), execution platform, Python/NumPy versions, steps, and complete output. Reproducing a saved run requires matching software and NumPy RNG behavior, not just matching a seed. See [docs/validation.md](docs/validation.md) for software verification versus external scientific validation.

MIT License; see `LICENSE`.


## Experimental v0.2 capital branch

Activate the capital mechanism with `capital_enabled: true`, configure `initial_capital_units_per_firm`, `capital_output_per_unit`, `capital_depreciation_rate`, `capital_investment_budget_share`, and `capital_input_sector`. Produced goods in that sector can be bought by firms and converted into productive physical capital; cash trades remain ledger-conserved. Wage taxes are deducted in the new **net disposable income** metric, and firm ownership is reflected in a transparent, non-market-marked net-worth proxy. Legacy metrics have not been redefined.

```bash
civitas run --scenario scenarios/capital_reinvestment.json --steps 24 --seed 7 --output results/capital_demo
civitas suite --scenarios scenarios/capital_depreciation_only.json scenarios/capital_reinvestment.json scenarios/capital_concentrated_ownership.json --seeds 1,2,3 --steps 24 --output results/capital_compare
```

See [v0.2 capital mechanics](docs/v02_capital_model.md), [experimental analysis](research/v02_capital_experiment.md), and [CHECKPOINT.md](CHECKPOINT.md). These scenarios are *not* empirically calibrated forecasts. Experimental development outputs are subject to review; do not use a dev branch as a stable release.

## v0.2 ongoing development — savings, firm accounting and sensitivity research

The `feature/v0.2-capital-accounting` branch adds a second, **development-only** slice. Households may reserve current disposable income in separately accounted, non-interest-bearing savings balances; under a configured essential-sector rule they may make precisely logged emergency withdrawals. The simulation reconciles cash flows for **each household and firm**; suppliers recognize interfirm capital-good revenues and firms record noncash depreciation in an explicit **profit proxy**, not a full GAAP income statement. Existing scenarios have saving disabled by default and continue operating.

See [docs/v02_savings_profit.md](docs/v02_savings_profit.md) for the equations and limitations. `checkpoint_version=3` persists savings while loading historical v1/v2 checkpoints via explicitly defined migration. The latest experiments vary ownership and saving rates on a controlled 2×3 grid over 30 seeds at both 1,000 and 10,000 agents; see [research/v02_savings_ownership_experiment.md](research/v02_savings_ownership_experiment.md). Their recorded effects **do not** imply real-world outcomes, especially as reserves do not finance investment and fixed firm numbers make cross-population comparisons structurally different.

```bash
PYTHONPATH=src pytest -q
PYTHONPATH=src python research/run_savings_sensitivity.py --population 1000 --seeds 30 --steps 24
# For 10,000-agent studies, see the split/restartable commands in the research report.
```

The development branch is intentionally **not** promoted to `main` pending a broader economic-model and validation review.

## Population-normalized v0.2 experimental branch

`scale_population_exact()` preserves exact starting per-capita household money, firm money, firm density, physical capital, natural resources and resource capacity at feasible population multiples. It rejects noninteger firm/resource scaling rather than rounding. Twelve pinned scenarios and a runner allow 1,000/10,000-agent comparisons:

```bash
PYTHONPATH=src python research/run_population_normalized.py --population 1000 --seeds 30 --steps 24
PYTHONPATH=src python research/run_population_normalized.py --population 10000 --seeds 30 --steps 24
```

Initial economic ratios, local runtime and every period's accounting identities are recorded. This corrects an important experimental-design error, **not** the lack of empirical economic calibration or the other unimplemented v0.2 financial mechanisms. [Protocol and mathematical caveats](docs/v02_population_normalization.md).

## v0.2 experimental market-mechanism ablations

The development branch now exposes three rule controls for carefully documented
within-model experiments: `buyer_seller_rule` (`mixed`, `cheapest`, `favorite`),
`hiring_expectation_rule` (`adaptive`, `stationary`) and `rationing_order_rule`
(`random`, `household_id`). Defaults preserve all earlier scenarios. The
previous `price_adjustment=0` setting acts as the fixed-price control in the
new example configurations. These are **research interventions**, not normative
preferences or proven realistic economic behavior.

```bash
PYTHONPATH=src python research/run_market_ablation.py --seeds 12 --steps 24 --output results/market_ablation_12
PYTHONPATH=src python research/analyze_market_ablation.py --input results/market_ablation_12 --seeds 12 --steps 24
```

Six recorded treatments and raw period data are in
`research/v02_market_ablation_12/`. The executed report is
[market-mechanism experiment](research/v02_market_ablation_experiment.md),
and the formal research protocol and limitations are in
[market-mechanism documentation](docs/v02_market_mechanisms.md).
**Status:** 56 passing tests in the recorded environment; v0.2 is still not a
released or empirically validated economic model.

## Market mechanism factorial verification (v0.2 development)

The eight-way interaction study evaluates seller ranking, posted-price adaptation, and hiring expectations **jointly**, contrasting integrated and isolated markets with matched aggregate endowments (but not matched individual agent identities). Use:

```bash
PYTHONPATH=src:. python research/run_market_factorial.py --seeds 8 --steps 24 --output results/market_factorial
# or run --only b0p0h0 through b1p1h1 independently, followed by --finalize
```

See [factorial report](research/v02_market_factorial_experiment.md), [source and versioned period records](research/v02_market_factorial_8seed/), and [CHECKPOINT.md](CHECKPOINT.md). Interactions are conditional within-model results, **not calibrated real-world effects**.

## v0.2 matched-agent market-access experiments (development only)

Exact same initial 10,000-agent economy is replayed with four combinations of open/restricted household purchases and open/restricted labor hiring, using 10 access regions. This eliminates independent-agent-initialization confounding from the earlier integrated-versus-isolated comparison. Thirty seed-paired replications across 24 abstract periods are archived, with all six accounting discrepancies zero.

```bash
# Development branch: feature/v0.2-capital-accounting
PYTHONPATH=src:. python -m pytest -q
PYTHONPATH=src:. python research/run_matched_market_access.py --seed 1 --steps 24 --output research/v02_matched_market_30
# Repeat --seed for integers 2 through 30, then:
PYTHONPATH=src:. python research/run_matched_market_access.py --finalize --seeds 30 --steps 24 --output research/v02_matched_market_30
```

The default access configuration leaves legacy scenarios unchanged. The restricted experiments have a common government, natural resource pool, interfirm capital-goods trade and aggregated hiring information. They are **not ten independent economies**. Read [the mathematical mechanism](docs/v02_matched_market_access.md) and [the executed research report](research/v02_matched_market_access_experiment.md) before interpreting results. This does **not** establish external economic or social validity.


## Experimental v0.2 — regional assignment and price-quote information

The development branch now supports optional `household_region_assignment: "balanced_shuffle"` (balanced seeded regional labels, independent of simulation RNG), and `buyer_price_information: "two_quotes"` (buyers see two legal seller quotes per sector per period). Both default to original rules. `information_missed_purchase_opportunities` tracks failed purchases with an accessible but unquoted firm holding affordable stock. No external search price, behavioral learning or geography is implied.

See [equations and limitations](docs/v02_region_information.md), [executed research report](research/v02_region_information_experiment.md), and [latest checkpoint](CHECKPOINT.md). The stored research dataset includes 30 matched seeds, eight arms and 24 periods per arm at 1,000 agents, plus a short 10,000-agent smoke run. **The results are exploratory and should not be generalized.**

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
PYTHONPATH=src:. python research/run_region_information.py --seed 1 --population 1000 --steps 24 --output results/region_info
PYTHONPATH=src:. python -m civitas run --scenario scenarios/region_information_local_shuffled_2quotes.json --steps 24 --seed 7 --output results/region_shuffled
```


## v0.2 ongoing verification — firm density and historical-cost accounts

The latest development campaign adds **reproducible 10,000-agent firm-density experiments** and an **opt-in historical-cost firm ledger**. `cost_basis_accounting_enabled: true` activates pooled moving-average integer-cent inventory carrying basis, COGS on consumer and capital-goods sales, capital acquisition/depreciation book values, and exact per-firm balance-sheet reconciliation. This mode also bases dividends on its defined cost-basis earnings; it is **not** merely a reporting option. All historical scenarios default to the original profit-proxy rule.

New scenario and research commands:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q
PYTHONPATH=src:. python -m civitas run --scenario scenarios/cost_basis_reinvestment.json --seed 7 --steps 24 --output results/cost_basis_7
PYTHONPATH=src:. python research/run_cost_basis_comparison.py --population 10000 --seeds 8 --steps 24 --output results/cost_basis_comparison
# Sharded, deterministic density study; the repository already retains seed records 1–8:
PYTHONPATH=src:. python research/run_region_density.py --seed 1 --firms 10 --steps 24 --output results/region_density
PYTHONPATH=src:. python research/run_region_density.py --seed 1 --firms 20 --steps 24 --output results/region_density
# Repeat both commands for seeds 2–8, then:
PYTHONPATH=src:. python research/run_region_density.py --finalize --seeds 8 --steps 24 --output results/region_density
```

See [cost-basis specification](docs/v02_cost_basis_accounting.md), [new density results](research/v02_market_density_10000_experiment.md), [historical-cost experiment](research/v02_cost_basis_experiment.md) and [latest checkpoint](CHECKPOINT.md). Data are **conditional synthetic results**, not empirical predictions or full audited financial accounts. Historical-cost checkpoints use format 4; old v1/v2/v3 checkpoints still load when the new mechanism is disabled.

## v0.2 experimental bilateral credit and physical input fees (development branch)

This opt-in vertical slice finances actual interfirm purchases of productive goods with **existing household savings**. Loan claims and firm liabilities are registered bilaterally; principal repayments are cash transfers, and maturity defaults are matched noncash balance-sheet writeoffs. **No bank, credit-money creation, interest, or complete insolvency model** is implied. A separate opt-in resource extraction fee transfers cash from firms to government and capitalizes productive input cost in inventory. Historical rules remain the defaults. This feature is not yet part of the stable `main` release.

```bash
# Run a reproducible credit-enabled scenario locally.
civitas run --scenario scenarios/credit_1_resourcefee_0.json --steps 24 --seed 7 --output results/credit_demo

# Reproduce the 2×2 credit × resource-cost experiment (four arms).
PYTHONPATH=src:. python research/run_credit_experiment.py --population 1000 --seeds 30 --steps 24 --output results/credit_1000
PYTHONPATH=src:. python research/run_credit_experiment.py --population 10000 --seeds 8 --steps 24 --output results/credit_10000

# Scientific software verification
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q
```

See [complete equations and accounting invariants](docs/v02_credit_resource_accounting.md), [executed 2×2 experiment](research/v02_credit_resource_experiment.md) and [continuation checkpoint](CHECKPOINT.md). The 10,000-agent research configuration deliberately holds only six firms and is **not per-capita normalized** to the 1,000-agent study. Run results are synthetic model evidence, not predictions or support for policy claims.

### Fail-closed GitHub publication from the downloadable archive

If direct ChatGPT-to-GitHub transfer is unavailable in a session, the complete
verified source archive includes `scripts/publish_feature_branch.sh` for
publishing **only** `feature/v0.2-capital-accounting`. It checks that the remote
branch still points to the previously verified commit, clones it, copies the
source/evidence, installs the test environment, executes the full test suite,
and performs a normal non-force push. It never touches `main`.

```bash
unzip CIVITAS_v02_finance_complete.zip
cd CIVITAS
bash scripts/publish_feature_branch.sh
```

Requires Git credentials configured on the local machine, network access,
Python 3.11+, and Git. If the expected branch head has changed, the script
refuses to publish and requires manual reconciliation; **do not force-push**.

## Savings-backed credit sensitivity research (v0.2 development)

After running the normal test suite, reproduce the 10,000-agent, eight-seed 12-cell experiment using `research/run_credit_sensitivity.py`. Each `--seed N` invocation writes or verifies an atomic `seed_NNNN.json` shard, while `--finalize --seeds 1,2,3,4,5,6,7,8` checks every shard and builds `summary.json` with paired effects. See [research experiment](research/v02_credit_sensitivity_experiment.md); simulation evidence is not real-world policy evidence.

## New research checkpoint: credit pathway falsification (v0.2 development)

Use `research/run_credit_pathways.py` to compare **zero-credit, zero-funding sham, 15%-lendable and 75%-lendable savings**, two saving propensities and two loan maturities across matched initial states. Both 24-period and 48-period measurements are retained. All individual loan changes must balance via principal roll-forward. Saved per-treatment files survive interruptions and checked seed reports can be independently audited. See [executed research report](research/v02_credit_pathways_experiment.md).

```bash
PYTHONPATH=src:. python research/run_credit_pathways.py --seed 1 --population 10000 --steps 48 --output results/credit_pathways
# Repeat for seeds 2–6; use --seed N --cell s25_limited_term2 for shorter resumable batches.
PYTHONPATH=src:. python research/run_credit_pathways.py --finalize --seeds 1,2,3,4,5,6 --population 10000 --steps 48 --output results/credit_pathways
python research/audit_credit_pathways.py results/credit_pathways
# If working from the repository's compressed evidence:
python research/restore_credit_pathways.py research/v02_credit_pathways_10000 results/restored_credit_pathways
```

These are **six-seed synthetic experiments**, not empirical social-scientific predictions. v0.2 has not been released.

## Long-horizon demand contraction diagnostics (v0.2 development)

The reproducible [48-period experiment](research/v02_demand_contraction_experiment.md) examines why the earlier credit study experienced falling output even with credit off and growing natural-resource stocks. The six interventions vary saving propensity, dividends, price adjustments, hiring expectations and capital depreciation one at a time, with matched seeded initial states.

```bash
PYTHONPATH=src:. python research/run_demand_diagnostics.py --seed 1 --output results/demand_diagnostics
# Repeat for each seed 2, 3, 4, 5, 6, 7 and 8.
PYTHONPATH=src:. python research/run_demand_diagnostics.py --finalize --seeds 1,2,3,4,5,6,7,8 --output results/demand_diagnostics
python research/audit_demand_diagnostics.py results/demand_diagnostics
```

The observer adds no changes to simulator transition rules. All eight-seed records and statistics are preserved in `research/v02_demand_diagnostics_raw.zip` (restore using `PYTHONPATH=src:. python research/restore_demand_diagnostics.py research/v02_demand_diagnostics_raw.zip results/restored_demand`), with a readable summary in `research/v02_demand_diagnostics/summary.json`; the [mathematical specifications and limitations](docs/v02_demand_diagnostics.md) distinguish affordability diagnostics from measured welfare and model interventions from real-world evidence. v0.2 remains a development preview.


## Latest v0.2 experiment: alternative price and hiring feedback

Two opt-in rules are available in the development branch: `price_update_rule: "affordability_guard"` with `price_affordability_floor: 0.25` (end-period affordability threshold for **price increases only**), and `hiring_expectation_rule: "blended"` (50/50 mixture of prior-sales-adaptive and stationary expected sector demand). Defaults remain `inventory` and `adaptive`, preserving historical trajectories. The rules do not introduce external model calls.

The matched-seed 2×3 factorial ran at 2,000 and 10,000 agents for 72 periods, with eight seeds at each population. All six rule combinations still exhibit contraction at the 10,000-agent horizon, and price/hiring interactions differ across the two structural regimes. See [equations](docs/v02_price_hiring_rules.md), [recorded experiment](research/v02_price_hiring_stability_experiment.md), and `research/audit_price_hiring_stability.py`. The experiment is **not** a calibrated prediction or evidence of optimal economic policy.


## World Genesis — configurable or seeded civilizations (v0.2 experimental)

Create a new artificial civilization from a **configured**, **randomized**, or **hybrid** (recommended default) world plan. Existing scenario files and their original initialization behavior are unchanged. New worlds preserve their complete initialization specification, exact starting-state checkpoint, and hashes for reproducible verification:

```bash
PYTHONPATH=src python -m civitas genesis --mode hybrid --name example --population 10000 --seed 42 --output results/my_world
PYTHONPATH=src python -m civitas verify-world --world results/my_world
PYTHONPATH=src python -m civitas run --scenario results/my_world/scenario.json --steps 24 --output results/my_run
PYTHONPATH=src python -m civitas resume --checkpoint results/my_world/initial_checkpoint.npz --steps 24 --output results/from_initial_state
```

For user-defined worlds, edit the example plans in `scenarios/world_genesis/` and use `genesis --plan PATH --output DIR`. Starting wealth distributions preserve total currency by default; savings are an allocation of existing wealth, not newly created money. See [World Genesis specification](docs/v02_world_genesis.md). New worlds are **synthetic**, not predictions or empirically calibrated representations of societies.
