# CIVITAS v0.1 foundation + v0.2 experimental capital branch

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
