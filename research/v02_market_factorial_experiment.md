# CIVITAS v0.2 — Interaction study of market search, prices and hiring

**Status:** executed **synthetic computational experiment**, 2026-11-13, **not** an empirically calibrated socioeconomic claim. `0.2.0.dev0` development branch; stable v0.1 `main` is unchanged.

## Scientific question and preregistered mechanics

Earlier one-factor market ablations found a strong difference between integrated and partitioned markets. This experiment tests whether the effects of **seller ranking**, **price adaptation** and **hiring expectation** are additive, or whether factorial interactions are present. It does **not** test the earlier cheapest-first treatment; this design compares *historical mixed* search to *favorite-first* search only.

A complete 2×2×2 experiment uses three binary factors:

| Factor | 0, historical reference | 1, intervention |
|---|---|---|
| `b`: consumer search | `buyer_seller_rule=mixed` (75% cheapest preference) | `buyer_seller_rule=favorite` |
| `p`: posted price adjustment | `price_adjustment=0.02` | `price_adjustment=0` |
| `h`: firm hiring expectation | `hiring_expectation_rule=adaptive` | `hiring_expectation_rule=stationary` |

The other parameters are fixed to the normalized 8%-ownership, 0%-saving reference: 10,000 agents, 2,500 households, 60 firms, three sectors, capital and resource accounting, and the same baseline endowment structure. Per treatment and master seed, one integrated 10,000-agent economy is compared with ten isolated 1,000-agent economies, each with the same per-person initial aggregate endowments and firm density. Sector access differs across topologies by design.

**Execution:** eight factorial cells × eight master seeds × (one integrated economy plus ten isolated communities) × 24 abstract periods = **704 executable simulation instances**, **16,896 internally checked simulation periods**, and **3,072 complete topology-level period records**. All six money, physical resource, finished goods, productive capital, household flow and firm flow discrepancy checks returned zero in these executed periods. The runner raises an exception if a discrepancy is detected. No raw per-account transaction trace was enabled for this campaign.

The eight master seeds are `1..8`. Economic outcomes under different treatments are comparable within each topology under matched master seeds; the isolated communities use distinct community RNG substreams and are **not the same individuals** as the integrated population. Therefore the topology contrast is a *descriptive structural comparison*, not a person-level matched causal counterfactual.

## Final-period observations

Mean values across eight master seeds, measured in produced units **per person during the final period**, not cumulative outputs:

| Cell | Buyer | Price | Hiring | Integrated | Ten isolated average | Gap integrated − isolated |
|---|---|---|---|---:|---:|---:|
| b0p0h0 | Mixed | Adaptive | Adaptive | 0.25284 | 0.10795 | +0.14489 |
| b0p0h1 | Mixed | Adaptive | Stationary | 0.28897 | 0.25903 | +0.02995 |
| b0p1h0 | Mixed | Fixed | Adaptive | 0.18415 | 0.16080 | +0.02335 |
| b0p1h1 | Mixed | Fixed | Stationary | 0.19531 | 0.22575 | −0.03044 |
| b1p0h0 | Favorite | Adaptive | Adaptive | 0.11104 | 0.11657 | −0.00554 |
| b1p0h1 | Favorite | Adaptive | Stationary | 0.21848 | 0.21707 | +0.00140 |
| b1p1h0 | Favorite | Fixed | Adaptive | 0.13341 | 0.13550 | −0.00209 |
| b1p1h1 | Favorite | Fixed | Stationary | 0.16323 | 0.16364 | −0.00041 |

## Precisely defined factorial interactions

For an outcome `Y(b,p,h)`, with all omitted factors held at the historical (0) value, the seller×price interaction is `Y(1,1,0) − Y(1,0,0) − Y(0,1,0) + Y(0,0,0)`. Similarly, the seller×hiring and price×hiring interactions are second finite differences. The three-way interaction is

`Y111 − Y110 − Y101 − Y011 + Y100 + Y010 + Y001 − Y000`.

For the topology gap, `Y(b,p,h)` is itself **integrated output/person minus isolated output/person**. All estimates are applied to each master seed separately before averaging; approximate intervals are `mean ± 1.96 * sample_sd / sqrt(8)`.

| Contrast of topology gap | Mean units/person | Approximate 95% Monte Carlo interval |
|---|---:|---:|
| Seller × price | +0.12499 | [+0.11856, +0.13142] |
| Seller × hiring | +0.12188 | [+0.11780, +0.12595] |
| Price × hiring | +0.06115 | [+0.05574, +0.06656] |
| Seller × price × hiring | −0.06641 | [−0.07111, −0.06172] |

These are contrasts *under this factorial coding and reference baseline*; they are **not** universal effect sizes. The empirical pattern is nonadditive. In the historical mixed-search/adaptive-price setting, stationary hiring dramatically reduces the market-size advantage, but when favorite-first seller choice is also activated, the corresponding gap approaches zero. Fixed prices can eliminate or reverse the gap, depending on the other two factors.

A separate independent CSV recount (not using the experiment analyzer) verified all 3,072 row keys and reproduced the three-way mean `−0.0664125` exactly.

## Negative results, threats to inference and research priorities

- Eight master seeds are relatively few; narrow Monte Carlo intervals reflect only the particular stochastic generator under these *fixed* model assumptions, not behavioral or structural uncertainty. Many exploratory contrasts were inspected without multiplicity adjustment.
- The integrated topology gives consumers access to sixty firms, whereas each isolated community has access to six; procurement opportunity is **not independently fixed**. Topology is therefore entangled with seller access, not only number of agents.
- Hiring itself uses a sequential firm priority and global worker-pool ranking. This can create an allocation advantage when firms share a labor market, independent of consumer search. We have not separated firm access to employees from firm access to customers.
- Isolated communities are initialized using community-specific RNG substreams; the topology experiment does not preserve identical individual skills, cash and owner assignments across topologies. Initial aggregate per-person stocks match, not individual agent identities.
- Production and consumption are period flows; inventories can legitimately make consumption exceed same-period output. Neither flow is a welfare index.
- Firm profit remains an operating proxy; there is no inventory cost-of-goods-sold ledger, bank or loan model. No external macroeconomic or demographic calibration exists.

**Next most informative interventions:** explicitly bound consumer search to equal-sized seller pools within the integrated model, and separately bind labor recruitment to community pools, keeping individual agents and their initial conditions fixed. This allows seller-access effects to be distinguished from pooled-labor effects. Only then should we interpret large topology advantages. Full inventory cost basis and two-sided investment financing are separate v0.2 engineering gates.

## Reproduction

From repository root (Python 3.11+, NumPy):

```bash
PYTHONPATH=src:. python -m pytest -q
PYTHONPATH=src:. python research/run_market_factorial.py --seeds 8 --steps 24 --output results/market_factorial_8seed
# For parallel/restartable treatment execution, run each --only b0p0h0 ... b1p1h1
# then independently audit all eight complete CSVs and digests:
PYTHONPATH=src:. python research/run_market_factorial.py --finalize --seeds 8 --steps 24 --output results/market_factorial_8seed
```

The runner writes each cell's **all-period** CSV atomically, with scenario JSON, a seed-1 configuration digest, CSV SHA-256 and environment metadata. The finalizer validates all eight cells, exact row keys, seed counts, configuration hashes and file integrity before writing `factorial_analysis.json` with cell means, seed-level Monte Carlo intervals, and pairwise and three-way interactions. See `research/v02_market_factorial_8seed/` for archived results.
