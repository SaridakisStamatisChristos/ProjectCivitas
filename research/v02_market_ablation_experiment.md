# CIVITAS v0.2 — Market-mechanism ablation experiment

**Date:** 2026-11-13. **Status:** executed exploratory synthetic model experiment; not empirical evidence about actual economies.

## Executed design

Six one-factor treatments, 12 master seeds, 24 abstract periods, 10,000 agents total per topology. Each treatment compares one integrated 10,000-agent market to ten noninteracting 1,000-agent communities at exactly matched aggregate opening endowments and firm densities. The study contains **792 complete engine runs and 19,008 verified engine periods**; the stored topology-level CSV files contain **3,456 rows**. Six accounting/stock invariants were checked for every simulated period and all were zero in these runs.

The experiment uses 8% initial ownership participation and zero household saving; 60 firms and 2,500 households across 10,000 agents, with 3 sectors. Each treatment is compared to the same initial-condition reference. Exact source configuration, seed, and period observations are retained under `research/v02_market_ablation_12/`.

## Final-period comparisons (means over 12 master seeds)

| Intervention | Integrated production/person | Isolated production/person | Topology gap (integrated − isolated) | Change in gap relative to reference [approximate 95% MC interval] |
|---|---:|---:|---:|---:|
| Historical buyer / hiring / pricing / rationing | 0.25194 | 0.10896 | +0.14298 | +0.00000 [+0.00000, +0.00000] |
| All buyers choose cheapest first | 0.40433 | 0.12096 | +0.28337 | +0.14039 [+0.13406, +0.14673] |
| All buyers choose favorite first | 0.11010 | 0.11542 | -0.00532 | -0.14830 [-0.15290, -0.14370] |
| Constant mean-demand hiring targets | 0.28923 | 0.25689 | +0.03234 | -0.11064 [-0.11661, -0.10468] |
| Price adjustments disabled | 0.18167 | 0.15971 | +0.02196 | -0.12102 [-0.12469, -0.11736] |
| Household-index rationing | 0.25081 | 0.11119 | +0.13962 | -0.00337 [-0.00701, +0.00028] |

## Main observations

- In this model, **buyer choice is highly consequential**. Cheapest-first behavior increased the integrated-versus-isolated gap; favorite-first nearly eliminated it, largely by lowering integrated-market production. The treatment is a change to search order, not a welfare comparison.
- Suppressing **hiring-sales feedback** or **posted-price adjustment** reduced the gap substantially. Neither intervention uniquely explains the baseline because all model mechanisms interact across time.
- Replacing random household purchase order with fixed household-ID order barely changed the production gap. There may be distributional/fairness changes that are not assessed here.
- At 12 seeds, the estimated change in the topology gap under household-ID rationing includes zero in its approximate Monte Carlo interval. This is a negative result for claiming ration order explains the substantial baseline gap.

## Diagnostic outcomes (end period)

| Intervention | Integrated active-seller fraction | Isolated active-seller fraction | Integrated mean price spread (cents) | Isolated mean price spread (cents) |
|---|---:|---:|---:|---:|
| Historical buyer / hiring / pricing / rationing | 0.976 | 0.894 | 122.4 | 28.7 |
| All buyers choose cheapest first | 0.504 | 0.699 | 109.8 | 27.8 |
| All buyers choose favorite first | 0.994 | 0.987 | 177.9 | 73.2 |
| Constant mean-demand hiring targets | 0.987 | 0.994 | 101.9 | 25.0 |
| Price adjustments disabled | 0.936 | 0.962 | 0.0 | 0.0 |
| Household-index rationing | 0.982 | 0.907 | 129.9 | 31.5 |

These diagnostics highlight why production alone is insufficient: cheapest-only selection leaves many integrated firms with no sales while active sellers differ sharply between topologies. Price dispersion is mechanically zero in the fixed-price treatment. The index of active sellers is a firm fraction, not an estimate of competitive welfare.

## Validation and interpretation bounds

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` passed **56 tests** after implementation (includes six market-rule configurations, invalid input, replay and legacy dataset regression).
- Golden record: **288/288** master-seed period records for seeds 1–12 of the baseline integrated economy matched historical production, consumption, and employment data, with no changed legacy behavior in these indicators.
- Exact accounting: 19,008 engine period states had zero discrepancies in total money, natural resource, manufactured goods, productive capital, household flows and firm flows. These checks do not prove model realism or untested configurations correct.
- Different topologies are **not the same agents** with or without isolation: independent community substreams replace a monolithic integrated initialization. Paired-seed differences control master seed, not agent identity. Consequently topology gaps are descriptive.
- Approximate MC intervals are `mean +/- 1.96 * sample_sd / sqrt(12)`. With six exploratory arms, no multiplicity adjustment, 24-step horizon or external calibration, these numbers must not be read as precise general causal effects.

## Reproducibility and next falsification

Source scripts: `research/run_market_ablation.py`, `research/analyze_market_ablation.py`, `docs/v02_market_mechanisms.md`. Raw period CSVs and exact scenario JSONs are preserved for every arm in `research/v02_market_ablation_12/`. Run from repository root.

**Next:** test interactions (buyer choice × price adjustment × hiring expectation), isolate labor-matching pool changes from seller availability, then investigate explicit inventory cost accounting. Keep v0.2 on the feature branch until release quality gates pass.
