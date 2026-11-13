# Roadmap and acceptance gates

**v0.1 (current):** balanced household/firm/government monetary transfers; endogenous finite inventory; wages, production and labor; household budget constrained consumption; proportional resource allocation; configurable taxes/dividends; automation intensity; 4 reproducible scenarios; CSV/JSONL/SQLite outputs; checkpoint/replay; CLI/tests. Acceptance: actual executable run, determinism, zero accounting discrepancies, and documented assumptions. See `CHECKPOINT.md` for observed status.

**v0.2 — Economic depth:** implement capital stocks and depreciation, explicit savings/investment, investment funding and reinvestment vs dividends, improved firm finance, feasible credit/debt if desired, wage-market adjustment, richer household attributes. Acceptance: distinct closed-stock identities for capital, debt and money; independent toy cases; empirical benchmark comparisons against v0.1; upgrade checkpoint compatibility.

**v0.3 — Technology:** endogenous adoption costs and diffusion, capital substitution for labor, occupational composition and reskilling, energy demands. Acceptance: parameter boundary and stock-flow tests plus documented shock mechanism.

**v0.4 — Institutions:** compare explicit ownership, information, allocation and governance rules without single ideological labels. Acceptance: a matched cross-policy test harness.

**v0.5 — Networks:** sparse social graph, trust/information transmission and simple migration with observed mechanism-level metrics.

**v0.6 — Resources:** multiple resources/regions, spatial heterogeneity and interregional trade.

**v0.7 — Research:** parameter sweeps, paired-seed statistical analysis, sensitivity and uncertainty methods with runnable report recipes.

**v0.8 — Observatory:** local visualization only after results provenance and consistency are validated.

**v0.9 — Scale:** per-stage profiling, optional Numba/C++/CUDA backends with differential reference comparisons, stress test at 100k/1m.

**v1.0 — Integrated laboratory:** documented component validation, robustness, reproducible release and independently inspected scientific limitations.

### Verified normalization investigation — v0.2 development only

The experiment that held six firms fixed while scaling population failed comparability requirements. Exact per-capita initial stocks and firm density, signed-int64 initial-state and transfer-credit guards, and randomized restoration tests are implemented. The 360-run controlled replication campaign and 600-run disjoint-market counterfactual found continuing scale-sensitive output differences. **This is not a v0.2 acceptance pass:** the market interaction/seller-choice structure is still non-scale-invariant and uncalibrated. Next technical gate: mechanism-level market ablations under matched ownership fractions; next financial gate: inventory unit-cost/COGS and two-sided funding rules. Preserve legacy scenarios and complete release gates before promotion to main.


**v0.2 market-structure research gate (2026-11-13):** Completed configurable
seller-search, hiring-feedback, and rationing-order ablations, with fixed-price
control, 12 master seeds and period-level provenance. The pronounced
integrated-versus-isolated production difference is model-rule-dependent, and
its attribution is not yet causally isolated. Before v0.2 release, implement
interaction factorial controls, improve inventory cost accounting and
model two-sided credit/equity flows if such mechanisms are activated. Evidence
is in `research/v02_market_ablation_experiment.md` and `CHECKPOINT.md`.
