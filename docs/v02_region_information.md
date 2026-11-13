# CIVITAS v0.2: regional allocation and bounded price information

**Classification:** experimental simulation rules, no empirical calibration; model version remains `0.2.0.dev0`.

## Research problem

The previous exact-matched 30-seed access experiment assigned households to regions using `household_id mod R`. This was deterministic but could correlate household IDs with queue position and ownership indexing. The consumer market also assumed full knowledge of every eligible seller's posted quote. We add two *independent, optional* interventions, preserving historical defaults:

1. `household_region_assignment = "modulo" | "balanced_shuffle"`. For `balanced_shuffle`, take the vector of labels `r_h = h mod R` and shuffle **labels only**, using a separate PCG64 generator seeded by `SeedSequence([scenario.seed, region_assignment_seed, 20261113])`. Household counts by region are preserved exactly. Agent region equals its household region. Firm regions remain `firm_id_within_sector mod R`. The original simulation RNG and complete agent/asset state remain unchanged.
2. `buyer_price_information = "full" | "two_quotes"`. In `full`, buyers can rank all their legally accessible sellers, as before. In `two_quotes`, if more than two firms are eligible in the requested sector, the buyer sees **two sequential seller IDs in the eligible ID list** starting at `(household_id * 13007 + step * 107 + sector_id * 29) mod eligible_firm_count` and wrapping once. The choice is deterministic and does not consume simulation random draws. The unquoted firms are not considered in this purchase attempt, even when they have an affordable product in stock.

`restrict_household_sales` still determines seller *eligibility* (all sector firms vs same-region firms). Price information determines which members of that eligible set the buyer **observes**; quote observations are not geographic travel or an information network. The existing `buyer_seller_rule` determines how the **observed** sellers are ranked.

## Timing, information and conservation

Each household faces a single purchase attempt for each sector, as before. The observed subset is constructed after legal seller eligibility is established, before affordability and ranking. If no observed seller is affordable, the attempted purchase is recorded under `unmet_budget_demand_units`; if observed options are affordable but out of stock, unmet stock demand is recorded. A new diagnostic, `information_missed_purchase_opportunities`, counts unsuccessful purchase attempts for which **an eligible, unobserved firm actually held affordable stock at that moment**. This diagnostic is not a welfare or consumer surplus metric and is not additive to the purchase shortfall. There is no exogenous price information cost and no behavioral learning.

All transfers, physical products, capital stocks and resource accounting remain unchanged. The new assignment random generator is separate from the main PCG64 generator, so arms that differ only by assignment, quote information or sales restrictions still consume the same shared RNG draws. Checkpoints already encode all scenario parameters and RNG state; region labels are rederived on restoration without a schema change.

## Experimental factorial (2 × 2 × 2)

Three factors are varied: assignment (`modulo`, `balanced_shuffle`), quote information (`full`, `two_quotes`) and seller access (`open`, `local`). Worker hiring, natural resources, government finance and capital procurement remain global. The **same initial population, household cash, firms, firm owners, capital and RNG state** are cloned into all eight arms within each seed. The scenario uses five abstract regions and twenty firms per sector: each local region contains four eligible suppliers per sector, making the two-quote information constraint nontrivial even under local sales access.

Let `Y(a,i,s;z)` be the final-period outcome in assignment condition `a`, information condition `i` and access condition `s`, with seed `z`. The paired quote effect for fixed assignment and access is

`Q(a,s) = mean_z[Y(a,two_quotes,s;z) - Y(a,full,s;z)]`.

The quote/access interaction for assignment `a` is

`I(a) = mean_z[(Y(a,two_quotes,local;z) - Y(a,full,local;z)) - (Y(a,two_quotes,open;z) - Y(a,full,open;z))]`.

These are Monte Carlo means conditional on a fixed synthetic model, not estimates of real-world intervention effects. Approximate 95% seed intervals use `mean ± 1.96 * sample_sd / sqrt(n)` and exclude structural, calibration and mechanism uncertainty. Final-period effects do **not** characterize long-run equilibrium.

## Reproduction

From the project root, with Python 3.11+ and NumPy installed:

```bash
python -m pip install -e '.[test]'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
for seed in $(seq 1 30); do
  PYTHONPATH=src:. python research/run_region_information.py --seed "$seed" --population 1000 --firms-per-sector 20 --regions 5 --steps 24 --output research/v02_region_information_1000
done
PYTHONPATH=src:. python research/run_region_information.py --finalize --seeds 30 --population 1000 --firms-per-sector 20 --regions 5 --steps 24 --output research/v02_region_information_1000
```

Each seed emits an atomic, SHA-256-checked CSV shard and a metadata sidecar containing initial-state and final RNG hashes. Finalization rejects missing, altered or non-complete data and writes per-period data, Monte Carlo summaries and environment metadata. The production-scale campaign should be repeated at 10,000 agents; population-specific parameter scaling is **not** established by one smaller population experiment.

## Known limitations

- The shuffled region rule is a balanced permutation, **not** random geography, migration or social community membership.
- `two_quotes` means observing exactly two adjacent sellers in an ID list, not a calibrated search cost or a realistic purchasing algorithm.
- Same-region sales still share economy-wide worker markets, government, resource supply, price feedback and interfirm capital procurement; no claim of separate autarkies.
- Firms do not observe local unmet demand separately, and the main production scheduler still uses aggregate sector information.
- Inventory costs, full business net-profit accounting and savings financing of capital remain open v0.2 release gates.
