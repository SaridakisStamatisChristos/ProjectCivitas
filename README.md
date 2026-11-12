# CIVITAS v0.1 — Foundational Economy

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
