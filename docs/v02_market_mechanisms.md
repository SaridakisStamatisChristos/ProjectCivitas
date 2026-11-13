# CIVITAS v0.2 — Controlled market-mechanism ablations

**Status:** executable research extension on `feature/v0.2-capital-accounting`.
Not an empirical prediction, an institutional evaluation, or a completed v0.2 release.

## Core question

Why does a unified market of 10,000 agents produce a different per-person outcome
than ten separate markets of 1,000 agents, despite exactly normalized initial
firm density, cash, natural resources and productive capital?

The initial experiment showed a pronounced difference. This extension **does not
assume** that it can be explained by one cause. It permits one-factor interventions
on buyer search, firm hiring expectations, and allocation order. Existing
`price_adjustment=0` is the fixed-price control.

## Intervention definitions and time semantics

All variants retain the historical time-step order: physical depreciation,
resource regeneration, sequential employment and payroll, constrained production,
taxation and redistribution, consumption, capital acquisition, dividends,
household reserve deposits, account reconciliation, posted-price updates and
metrics. Every sale and movement remains a real journaled transaction.

* `buyer_seller_rule="mixed"` (historical default): for each sector a household
  attempts the cheapest available seller with probability
  `buyer_cheapest_probability` (historically 0.75), and otherwise attempts a
  deterministic household-specific preferred seller first. Failed first choices
  fall back to the other sellers sorted by price. The stochastic cheapest-choice
  vector is always sampled whether the intervention uses it or not, preserving
  the number of market RNG draws across treatments.
* `buyer_seller_rule="cheapest"`: all households use lowest-quoted-price-first
  ranking, with inventory-aware fallbacks. This does **not** model unlimited
  information or real search costs.
* `buyer_seller_rule="favorite"`: all households use their deterministic
  favorite first and price-sorted fallbacks thereafter. This is not the same
  as forcing purchases from one seller when that seller has no stock.
* `hiring_expectation_rule="adaptive"` (historical default): a firm's desired
  production at t=0 follows mean sector demand per firm; subsequently it is
  `max(0.25 * initial_mean, last_sales_f + last_unmet_sector / firms_per_sector)`.
  A configurable inventory buffer and current inventory determine required
  output, bounded by available workers, firm cash, capital and resources.
* `hiring_expectation_rule="stationary"`: desired production in **every**
  period starts from mean sector demand per firm rather than prior sales and
  shortages. It remains constrained by inventory and productive inputs. This
  deliberately disables one feedback mechanism, not a proposed superior
  real-world hiring policy.
* `rationing_order_rule="random"` (historical default): each sector's potential
  buyers are sampled in a seeded random order for inventory allocation.
* `rationing_order_rule="household_id"`: lower household indices buy first;
  the unused seeded permutation is still sampled to preserve the RNG stream.
  This is a mechanism probe, **not** a normative fairness recommendation.
* `price_adjustment=0` holds posted prices constant in the documented test
  configurations, whose opening prices exceed the price floor. Other cases with
  a higher configured floor require explicit checking before calling them fixed.

These controls do not alter the original default equations. They are versioned
scenario fields in `src/civitas/model.py`, handled in `engine.py`.

## Measurements

At each period, report production, consumption and employment; unsatisfied
stock/budget demand; the fraction of firms with positive sales, mean intra-sector
quoted-price spread, and mean sector sales Herfindahl index (only for sectors
with nonzero transactions). These are diagnostics, not welfare indicators.
Mean raw HHI changes mechanically with firm count; it is **not** suitable for
direct comparison across markets with two versus twenty firms per sector.

The existing nonnegative stocks and exact cash-flow identities remain mandatory.
The experiment checks six zero-discrepancy conditions each simulated period:
money, natural resource, finished goods, physical capital, household cash flows,
and firm cash flows.

## Experimental design

Starting from the 1,000-agent capital-and-saving scenario at 8% household
ownership and 0% savings propensity, use exact scaling to obtain 10,000 agents:
60 firms (20 in each of three sectors), 2,500 households, identical **per-person**
opening cash, stock, resource capacity and physical capital. Compare with ten
independent 1,000-agent communities, each containing six firms. All have the
same total starting endowments when aggregated.

For each of six rules, 12 master seeds and 24 abstract periods are executed in
both topologies, yielding 72 integrated runs and 720 independent-community runs.
The 720 community runs are aggregated by master seed to 72 equivalent
10,000-agent observations, then compared on a per-person basis. This campaign
contains **792 executed engine instances / 19,008 internally checked periods**;
its CSV files have 3,456 topology-level period records (one integrated and one
aggregated-isolated record per master seed and period).

The ten communities use independent substreams derived from the master seed and
community index. This **does not** mean integrated and isolated simulations
contain identical agents. In contrast, the within-topology ablation arms with
the same seed and population begin from exactly the same attributes and
ownership mapping. Treatment state trajectories then diverge by design.

For any measure y, define the descriptive topology gap under rule r:

```
G_r(s) = y_integrated(r,s) - y_isolated_aggregate(r,s)
Delta_r(s) = G_r(s) - G_reference(s)
```

The code reports mean `Delta_r`, sample standard deviation, and an exploratory
normal-approximate 95% Monte Carlo interval over 12 seed blocks. These intervals
only describe uncertainty due to sampled RNG streams within this precise
artificial model. They are **not** calibrated effect confidence intervals;
multiple testing and structural assumption uncertainty are not covered.

## Reproduction

```bash
python -m pip install -e '.[test]'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
PYTHONPATH=src python research/run_market_ablation.py --seeds 12 --steps 24 \
  --output results/market_ablation_12
PYTHONPATH=src python research/analyze_market_ablation.py \
  --input results/market_ablation_12 --seeds 12 --steps 24
```

The committed evidence uses six independently restartable runs:

```bash
for name in reference cheapest_only favorite_first stationary_hiring fixed_prices household_id_ration; do
  PYTHONPATH=src python research/run_market_ablation.py --only "$name" --seeds 12 --steps 24 \
    --output "research/v02_market_ablation_12/$name"
done
PYTHONPATH=src python research/analyze_market_ablation.py \
  --input research/v02_market_ablation_12 --seeds 12 --steps 24
```

A separate golden-record audit compared the original 10,000-agent normalized
market outputs with the new reference treatment for **288 seed-period records**
and found exact production, consumption and employment agreement within CSV
floating serialization tolerance. See `golden_reference_audit.json`.

## Scientific limitations and falsification priorities

1. Buyer preference is stylized. Stationary hiring might alter an endogenous
   supply-demand feedback loop without representing reasonable business forecasts.
2. Endogenous price spreads, sales and investment are simultaneously evolving;
   a one-factor ablation identifies **sensitivity**, not a unique causal pathway.
3. The market topology differs in the number of firms accessible to each
   household and the set of workers accessible to each firm; further controls
   must restrict these separately.
4. Twelve seeds and 24 abstract periods are insufficient to characterize
   robust asymptotics or long-horizon distributions.
5. Seller HHI, stockouts and income inequality are neither welfare measures
   nor empirically calibrated socioeconomic indicators.
6. Full inventory cost-of-goods sold, complete firm balance sheets and formal
   int64-overflow proof remain open release gates.

**Next test:** factorial interactions between buyer choice, adaptive prices and
hiring expectations; independently hold worker matching pools fixed while
varying seller access. Do not attribute all differences to any one mechanism.
