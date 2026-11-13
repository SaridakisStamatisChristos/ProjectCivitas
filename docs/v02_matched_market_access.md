# v0.2 experimental matched-market access (not a released model)

## Scientific question and intervention

Previous market-topology comparisons initialized a large economy and ten separate small economies using **different individual agents**. They therefore could not attribute differences solely to market access. This intervention holds the *complete initial artificial population and initial financial/physical stocks fixed*, then changes only eligibility for two classes of transactions: household purchases and individual labor hiring.

Let there be `R` hypothetical access regions, `H` households and `F` firms per sector. Both `R>=1` and `F mod R=0` are validated. For household `h` (0-indexed), firm `f` in sector `k`, and agent `a`:

- `r(h) = h mod R`;
- `r(f) = (f mod F) mod R` (firm IDs are grouped by sector);
- `r(a) = r(household_of_agent[a])`.

When `restrict_household_sales=true`, household `h` can buy from firm `f` in the requested sector **only if** `r(h)=r(f)`. Otherwise, all firms in that sector are eligible. When `restrict_labor_hiring=true`, firm `f` may hire agent `a` **only if** `r(a)=r(f)`; otherwise all as-yet-unemployed participating agents can apply. Each period's deterministic firm scheduling, worker skills and budget constraints still apply. Regional IDs are derived from existing IDs and require **no additional random-number draws**.

The 2x2 intervention uses four arms: `open`, `sales_only`, `labor_only`, `both`. It fixes `R=10`, `population=10000`, `F=20` (60 firms in three sectors), and all other scenario parameters, including 8% ownership and 0% household savings. Each region contains 250 households (1000 agents) and two firms per sector. The arms run 24 periods with 30 initial seeds. Each arm is initialized from a **deep copy of the same original `State` instance and the same PCG64 bit-generator state for that seed**. Initial-state hashes include the full owned/physical balance state, agent properties, household membership and RNG state; all arms must match. The RNG stream is checked again after all periods, because all sector-level demand and rationing draws are consumed independent of purchasing results.

The fundamental counterfactual is therefore within the **same artificial economy and same seed**. It is not a claim that perfectly identical real-world populations can be experimentally partitioned.

## Precisely what is *not* restricted

- Government taxes, transfers and its cash account remain common across regions.
- The single natural-resource pool and its regeneration/allocation remain common.
- Interfirm purchases of produced capital goods remain unrestricted across regions, including ownership links across regions.
- Firms continue to observe an economy-wide aggregated unmet-demand signal in adaptive hiring; the experiment does not isolate local information channels.
- Posted-price adjustment and rationing remain configured as in the original reference simulation; their indirect responses to changing transactions are expected, not separate exogenous changes.
- Regional labels are abstract access classes, not calibrated geography. No transportation, network learning, business entry, region-specific resources or trade cost model is implied.

This is an **access eligibility** experiment, not ten fully independent autarkic economies and not an identified real-world causal effect. The two access restrictions can interact through employment income, sale revenues, inventory and the common resource market.

## Accounting/causal constraints

- All money is integer cents, physical stocks integer units; original money, finished-goods, capital, resource and household/firm flow identities remain asserted each period.
- The `market_regions=1` default has unrestricted sales and hiring, preserving the prior baseline. Choosing more region labels without enabling either restriction is behaviorally inert.
- Only two new boolean intervention fields and a positive integer region count are added to the versioned scenario schema; existing scenario files remain readable with defaults.
- The nonpickle checkpoint format remains version 3 and already saves the complete scenario JSON. New region assignment arrays are derived at restore and do not require additional checkpoint arrays.
- Future experiments must test alternative region maps, ownership distributions, global versus local information, regional resource stocks, seller search rules and longer horizons. This one comparison is not validation of behavioral realism.

## Reproduction

```bash
python -m pip install -e '.[test]'
PYTHONPATH=src:. python -m pytest -q
# One resumable, atomic seed shard at a time (seeds 1–30):
PYTHONPATH=src:. python research/run_matched_market_access.py --seed 1 --steps 24 --output research/v02_matched_market_30
# Run each of seeds 2..30 analogously, then aggregate with digest and coverage checks:
PYTHONPATH=src:. python research/run_matched_market_access.py --finalize --seeds 30 --steps 24 --output research/v02_matched_market_30
PYTHONPATH=src:. python research/run_matched_market_access.py --verify-only --seeds 30 --steps 24 --output research/v02_matched_market_30
```

The complete aggregated `periods.csv`, `metadata.json`, `scenario_seed1.json`, and `summary.json` are preserved under `research/v02_matched_market_30/`. Separate `seed_shards/` are useful for restartability; their complete content also exists in the aggregated period data. All 2,880 period records are preserved (120 simulations × 24 periods). `metadata.json` includes scenario digests, SHA-256 of data, and initial/final RNG hashes for each seed. The paired Monte Carlo intervals quantify only variability across random seeds under a fixed configuration.
