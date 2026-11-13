# CIVITAS v0.2 bilateral credit × resource cost — executed report

**Research classification:** Within-model simulation intervention, 13 November 2026. Not empirical validation or financial advice. Synthetic agents and coarse firms; 24 abstract periods per run. Random seeds start from the same environment for all four treatment arms within a population/density.

## Method

Four configurations cross `credit_enabled` off/on with `resource_extraction_fee_cents_per_unit` 0/20. Firms are given limited initial cash (20,000 cents) and productive capital (20 units/firm), savings propensity 0.75, investment-budget share 0.05, 4-period zero-interest loan maturity, 10% repayment budget over a 10,000-cent reserve, and a maximum 500,000-cent principal per borrower. Loan funding comes **only** from existing household savings, not new bank deposits.

- Small population: 1,000 agents, six firms, 12 seeds, 48 complete runs, 1,152 audited periods; 3.58 seconds measured engine time.
- Standard population: 10,000 agents, **still only six firms**, eight seeds, 32 complete runs, 768 audited periods; 18.04 seconds measured engine time. **These populations do not have matched per-capita productive endowments.**
- The extra proposed 10,000-agent/60-firm normalized four-seed campaign **exceeded the execution limit**, generated no complete result dataset, and is **excluded**. A distinct two-seed smoke on that higher-density setting showed positive loan originations, but cannot establish outcome effects.
- All recorded rows were tested for zero money, physical-resource, goods, capital, household cash-flow, firm cash-flow, book-equity and bilateral loan discrepancies. Checks passed for these completed runs.

## Results (final-period means)

| Population | No credit / fee 0 | Credit / fee 0 | No credit / fee 20 | Credit / fee 20 |
|---|---:|---:|---:|---:|
| 1,000 — production units | 137.25 | 129.67 | 8.83 | 8.83 |
| 10,000 — production units | 240.00 | 240.00 | 80.00 | 80.00 |

At 1,000 agents with no resource fee, enabling lending changed final-period production by **-7.58 units**, paired seed approximate 95% Monte Carlo interval **[-13.43, -1.74]**. The new-credit runs originated **2,373,796 cents**, repaid **1,755,560**, and explicitly defaulted **618,236** over 12 seeds and 24 periods.

With fee=20 cents per resource unit, this low-cash setting largely suppresses activity and recorded no lending. At 10,000 agents, six firms and very limited firm endowment produced no loan originations in the completed configurations; credit on/off made no measurable difference in this limited 24-period sample. **Neither observation establishes that lending is generically damaging or neutral.** The model's firm and resource scale, seller inventories, cash endowments, investment targets, lender availability, and loan rules are dominant constraints.

## Accounting and causal interpretation

Every cent of loan principal is an actual `savings -> firm` transfer, and every repayment is `firm -> savings`. Defaults reduce matched lender claims and borrower liabilities by equal amounts without currency movement. Fee payments are ordinary `firm -> government` transfers; physical extraction remains separately conserved. A test of saved checkpoint format 5 traversed live originations, repayments and defaults and reproduced the exact continuation.

The intervals shown quantify seed-to-seed Monte Carlo uncertainty under these precise assumptions only. Their short horizons and small samples **do not** quantify parameter uncertainty, scientific model validity, real economic behavior, or long-term welfare. This campaign establishes executable mechanisms and accounting, **not** a robust lending policy ranking.

## Reproduce

```bash
python -m pip install -e '.[test]'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
PYTHONPATH=src:. python research/run_credit_experiment.py --population 1000 --seeds 12 --steps 24 --output results/credit1000
PYTHONPATH=src:. python research/run_credit_experiment.py --population 10000 --seeds 8 --steps 24 --output results/credit10000
```

Preserved research artifacts: `research/v02_credit_experiment_1000/` and `research/v02_credit_experiment_10000/` contain **every observed period**, exact scenario configurations, seed-based paired contrasts and SHA-256 digests. `research/v02_credit_legacy_parity.json` independently records comparison against the preceding GitHub development source: **15,768 existing metric values matched exactly** across 216 historical periods with new features disabled.

**Next scientific objective:** complete a properly scaled, computationally bounded firm-density study and longer horizons; model alternative loan risk/maturity/default assumptions; independently inspect inventory-cost and input-price mechanisms. No v0.2 release or main merge is justified yet.
