# CIVITAS v0.2 — Exact population normalization and market-partition falsification campaign

**Execution date:** 2026-11-13. **Status:** synthetic agent-based-model experiment, executed and checked, **not** empirical economic evidence. Software version: 0.2.0.dev0. Host: Linux x86_64, Python 3.13.5, NumPy 2.3.5. Code and reproducibility protocol: `src/civitas/normalization.py`, `research/run_population_normalized.py`, `research/run_market_partition_control.py`, and `docs/v02_population_normalization.md`.

## Research question and hypotheses

The prior savings/ownership study compared N=1,000 with N=10,000 while holding six firms and initial resource/capital/cash endowments fixed. These differences made the populations economically incomparable. **H1:** matching firm density and all initial stock ratios per person may reduce differences across population sizes. **H2:** the number of firms interacting inside the same market (market connectivity/topology) may still generate different outcomes even with matched starting ratios.

## Design and initial controls

The new reference design starts with 1,000 agents, 250 households, six firms, 50,000 resource units, 60,000 resource capacity, 2,700 physical capital units, 12 million cents of initial firm cash and 3.75 million cents household cash. For 10,000 agents all economy-wide initial quantities (including firm count) multiply by ten; per-firm and per-household endowments remain unchanged. Normalization is **exact integer arithmetic**, and invalid scale ratios are rejected. See protocol for all six invariant ratios.

Six scenarios = ownership share 3% versus 8%, crossed with saving rate 0%, 15%, 30%; all other configured parameters match within population. **30 seeds** per cell, **24 abstract periods**, at 1,000 and 10,000 agents = **360 runs and 8,640 period records**. Every period checks zero discrepancies in money, resource, finished goods, productive capital, per-household and per-firm cash-flows. All 8,640 passed these specified invariants. The complete per-period CSV records, scenario configurations, summaries and initial ratios are in the data archive.

**Ownership discretization caveat:** nominal 3% maps to 8 of 250 households (3.2%) in the smaller model and 75 of 2,500 (3%) in the larger model; the 8% settings have exact 20/250 and 200/2500 counts. Other unnormalized model mechanisms include finite competition sets and integer rounding in resource regeneration and pricing.

## Results — final period only, 30-seed means

| Agents | Nominal ownership share | Saving propensity | Production / person | Consumption / person | Employment rate | Disposable-income Gini |
|---:|---:|---:|---:|---:|---:|---:|
| 1,000 | 3% | 0% | 0.10893 | 0.10517 | 11.41% | 0.7290 |
| 1,000 | 3% | 15% | 0.11170 | 0.10430 | 11.70% | 0.7214 |
| 1,000 | 3% | 30% | 0.10897 | 0.10553 | 11.38% | 0.7221 |
| 1,000 | 8% | 0% | 0.11387 | 0.10837 | 11.94% | 0.7071 |
| 1,000 | 8% | 15% | 0.11827 | 0.11183 | 12.36% | 0.6902 |
| 1,000 | 8% | 30% | 0.11580 | 0.11063 | 12.09% | 0.6838 |
| 10,000 | 3% | 0% | 0.24172 | 0.24325 | 25.01% | 0.4617 |
| 10,000 | 3% | 15% | 0.21273 | 0.21426 | 22.01% | 0.4876 |
| 10,000 | 3% | 30% | 0.18100 | 0.18446 | 18.71% | 0.5233 |
| 10,000 | 8% | 0% | 0.25125 | 0.25205 | 25.98% | 0.4147 |
| 10,000 | 8% | 15% | 0.21405 | 0.21546 | 22.14% | 0.4440 |
| 10,000 | 8% | 30% | 0.18644 | 0.18763 | 19.27% | 0.4718 |

Savings effect: treatment 30% minus 0% saving within the same population and ownership setting (same seed indices):

| Agents | Ownership | Production/person difference [approx. 95% MC interval] | Disposable-income Gini difference |
|---:|---:|---:|---:|
| 1,000 | 3% | +0.00003 [-0.00605, +0.00612] | -0.0069 |
| 1,000 | 8% | +0.00193 [-0.00256, +0.00642] | -0.0233 |
| 10,000 | 3% | -0.06072 [-0.06305, -0.05839] | +0.0616 |
| 10,000 | 8% | -0.06481 [-0.06696, -0.06266] | +0.0571 |

**Outcome:** equal per-capita starting endowments and equal firm density did **not** remove the scale-dependent saving effect. In the 1,000-agent model, production differences under higher saving are small and not clearly distinguished from zero by these intervals. In the integrated 10,000-agent model, they are substantially negative. Therefore the earlier suggestion that savings propensity alone determines a particular directional production effect **fails this robustness test**. We retain the result as a counterexample to unwarranted model generalization.

## Market structure control: one integrated market versus ten isolated local markets

Using nominal **8% household ownership** (exact at both scales) and saving rates 0%/30%, we compared the existing integrated 10,000-agent run for each seed with an aggregate of **ten noninteracting 1,000-agent economies**. Each independent community has 2 firms per sector and its own RNG stream. Across all ten, total population, resources, firm count, initial cash and capital exactly match the integrated 10,000-agent initial quantities. The only design change is whether firms and households are confined to ten separate market pools or participate in one integrated sector-wide market. We ran 30 distinct master seeds per treatment, **600 additional isolated 1,000-person simulations**, 14,400 internally verified periods. The integrated 10,000-agent records were reused from the previous 360-run experiment, not computed twice.

| Saving rate | Integrated production/person | Isolated production/person | Integrated consumption/person | Isolated consumption/person |
|---:|---:|---:|---:|---:|
| 0% | 0.25125 | 0.11077 | 0.25205 | 0.10647 |
| 30% | 0.18644 | 0.11698 | 0.18763 | 0.11183 |

At 0% saving, the estimated isolated-minus-integrated production/person difference was **-0.14047** [approx. MC interval -0.14307, -0.13788]. At 30% saving the corresponding difference was **-0.06946** [approx. MC interval -0.07144, -0.06748].

**Interpretation:** A large portion of the cross-scale output difference is associated with the **market-interaction boundary and firm-competition set**, not unmatched initial quantities. This does **not** isolate which particular internal operation (seller choice, repricing, hiring priority, inventory allocation, or stochastic draws) causes the difference. A mechanism-level ablation test is still necessary. The two groups are synthetic independent draws, not identical real households under a randomized policy intervention.

## Scientific limitations and quality gates

- Experimental time is abstract; the 24th period is not an economy-wide equilibrium or calibrated year.
- The reported MC intervals use 30 seed-level differences and normal approximation; they exclude model specification, parameter, external empirical and multiple-comparison uncertainty. Substream coupling across populations is not exact agent matching.
- Production and consumption can differ in one period because existing inventory changes; resource, finished goods and capital conservation are checked.
- Apparent strong price-competition effects may be artifacts of the current simplistic consumer-choice and price-adjustment algorithms. They should be isolated with controlled ablations before adding further institutional modules.
- All 360 main factorial runs passed the six listed conservation identities; the 600 separate-community simulations also passed them. This is software verification under tested conditions, not an economic theory proof.
- The engine does not yet have full inventory cost-of-goods sold, explicit borrowing/liabilities, national accounts, calibrated behaviors, or a general signed-int64 arithmetic proof.

## Reproduction

```bash
python -m pip install -e '.[test]'
pytest -q
PYTHONPATH=src python research/run_population_normalized.py --population 1000 --seeds 30 --steps 24 --output results/normalized_1000_30
PYTHONPATH=src python research/run_population_normalized.py --population 10000 --seeds 30 --steps 24 --output results/normalized_10000_30
PYTHONPATH=src python research/run_market_partition_control.py --seeds 30 --steps 24 --integrated-root results/normalized_10000_30 --output results/market_partition_30
```

Recorded local simulation execution times: 12.41s (1,000-agent factorial), 274.11s (10,000-agent factorial), 44.96s (10×1,000 local-market control), separate from testing and file handling. They are not throughput guarantees.

**Next falsification objective:** instrument firm-level seller choice, price dispersion, supply/demand and rationing under 2 versus 20 firms/sector and construct a fixed-market-size replication baseline. Investigate alternate pricing/matching mechanisms. Continue economic-accounting improvements independently, keeping all scenarios explicitly versioned.
