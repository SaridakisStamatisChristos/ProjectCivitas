# CIVITAS continuation checkpoint

- **Verified local software version:** 0.1.0, 2026-11-13.
- **Current objective:** v0.1 foundational economic simulation, core-code-first.
- **Verified implementation:** `src/civitas/model.py`, `state.py`, `engine.py`, `metrics.py`, `persistence.py`, `cli.py`; `scenarios/*.json`; automated tests; reproducible CLI/NPZ/CSV/JSONL/SQLite; docs and benchmark runner.
- **Test evidence:** `PYTHONPATH=src pytest -q` reported 15 passed on Python 3.13.5, NumPy 2.3.5, pytest 9.0.2 (local container). Includes checkpoint equivalence, financial and stock conservation, zero-population case, boundary checks, 10,000-agent smoke, and CLI integration.
- **Executed experiments:** 4 scenario types × 3 seeds × 24 abstract periods = 288 period records; the 288 records had zero monetary, physical resource, and finished-product accounting discrepancies. See `research/initial_experiment.md` and `research/initial_summary.json`.
- **Performance evidence:** `benchmarks/observed_2026_11_13.json`, three periods each at 1,000, 10,000, and 100,000 agents, measured and environment disclosed. No 1m-agent claim.
- **Source of truth:** this repository and checkpoint; local full source and raw experiment archives may also be provided separately.
- **Major design choices:** single threaded NumPy PCG64; integer cents; integer resource and bundles; 6 firms / 3 sectors; no money creation or debt; taxes only on wages; positive current-surplus dividends; per-household demand; end-step discrete repricing. See `docs/architecture.md`, `docs/mathematical_model.md`.
- **Known defects/open gaps:** scientific calibration absent; baseline demand and wages stylized; unweighted cash Gini omits equity; zero stock permanent in logistic model; int64 overflow guards absent for extreme configs; results not automatically embedded in checkpoint; matching random seeds does not guarantee perfectly matched stochastic histories across distinct policies; coarse market and unemployment mechanisms.
- **Next highest-priority verified step toward v0.2:** add explicit household net disposable income and multi-account equity/capital-flow tracking; then implement conserved firm physical capital with depreciation/investment, independently test analytical toy cases, and compare against v0.1 regression trajectories. Keep release version unchanged until its gates pass.
- **Release gate:** local execution and tests passed; empirical validity/publication readiness **not** claimed.
