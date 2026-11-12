# CIVITAS v0.1 mathematical specification

## Units and state

Time `t = 0,1,...` is an abstract economic period. There are `N` agents, `H = ceil(N/h)` households, `K` sectors, and `F = K × f` firms. Households and firms are distinct monetary accounts. State includes household cash `C_h(t) ∈ Z_+` cents, firm cash `B_f(t) ∈ Z_+`, government cash `G(t) ∈ Z_+`, firm inventory `I_f(t) ∈ Z_+` bundles, resource stock `R(t) ∈ Z_+` extraction units, posted price `p_f(t) ∈ Z_+`, agent sector skill `s_{ik} ∈ [0.75,1.25]`, and fixed participation `l_i ∈ {0,1}`. Initial draw uses independent seeded pseudo-random numbers and a fixed population/household assignment; it does **not** reproduce a demographic dataset.

## Resource regeneration

For capacity `K_R`, resource rate `r`, beginning-of-period regeneration is

`ΔR_t = min(K_R - R_t, floor(r R_t (1 - R_t/K_R)))`, if `K_R>0`, else `0`.

The available physical stock becomes `R'_t = R_t + ΔR_t`. At `R_t=0`, the regeneration term is zero: resource extinction is permanent in v0.1. This is a design choice, not a general ecological law.

## Employment and production

Firm `f` has sector `k(f)`, base labor efficiency `a_k > 0`, wage `w_k` cents per worker, and resource input `q_k >=1` units per produced bundle. Automation rate `α_t = α_0 + 1[t >= t_shock] Δα` is bounded in `[0,1]`.

Firm desired output is the positive difference between an expected household-demand-plus-buffer target and existing inventory. Expected demand initially equals `H × sector demand probability / firms-in-sector` and subsequently depends on past firm sales plus a share of unmet stock demand (with a baseline floor). Hiring is sequential and ordered by a rotating firm index; in each firm, candidates are ranked by sector skill. Hiring is subject to available participants and the firm's cash budget. Each hired worker is paid the fixed sector wage immediately.

For hired agent set `L_f(t)`, physical potential output is

`P*_f = min(desired_f, floor(a_k × (1+α_t) × sum_{i∈L_f} s_{ik}))`.

The economy has one resource pool. If `sum_f q_k P*_f <= R'_t`, output `P_f = P*_f`. Otherwise first allocate `floor(P*_f × R'_t / sum_j q_j P*_j)` units, then add feasible whole production units in rotating firm order until no eligible feasible request remains. Therefore `0 <= P_f <= P*_f` and `sum_f q_k P_f <= R'_t`. Set `R_{t+1} = R'_t - sum_f q_k P_f` and inventory += output.

## Transactions, redistribution and money

Every payment invokes `transfer(source,destination,a)` where `a` is an integer number of cents and source has at least `a`. Firm-to-household wage payments obey `w_k` per employee. Households pay government `floor(τ × wage_income_h)` in tax (`0 <= τ <=1`). Government spends `floor(ρ × total_period_tax)` (`0<=ρ<=1`) equally among a fraction `γ` of households with the lowest gross wage income; unavoidable integer remainders go to lower stable household IDs. With zero households or zero collections, no transfers occur. Cash conservation is exact:

`M(t) = sum_h C_h(t) + sum_f B_f(t) + G(t) = M(0)`.

No monetary creation, credit, taxation of dividends, public borrowing, or spending beyond collected taxes occurs. Governments only allocate collected tax proceeds, retaining the unspent remainder.

## Consumption and pricing

Each household independently considers at most one bundle of each sector per period. Demand is a Bernoulli draw with probability `d_k`. The consumer first uses current cash affordability, then evaluates firms by probabilistic preference for the lowest posted price or a rotating habitual provider; stocked affordable firms receive a transfer and lose one inventory unit. If no purchase is feasible, either stock shortage or affordability failure is recorded, not double counted. Fulfilled purchases reduce inventory, increase firm cash, and are counted as consumption.

For each firm, positive operating surplus is `π_f^+ = max(0, sales_f - wages_f)` where sales and wages refer to the same current period. Fraction `δ` (rounded down) is distributed as equal whole-cent dividends to the seeded registered owner households; any remainder goes to lower owner IDs. This is a **surplus-distribution rule**, not an accounting model of full corporate profit.

At end of period, stock-out after positive sales changes price to `ceil(p_f (1+η))`. Excess inventory over a declared threshold changes it to `max(price_floor, floor(p_f(1-η)))`. Otherwise quote remains constant. Transactions use prices from **before** this reprice step. The v0.1 model has no clearing-price solver.

## Invariants and observables

Resource balance: `initial_resource + cumulative_regeneration - cumulative_extraction - current_stock = 0`.

Finished-goods balance in sector `k`: `cumulative_production_k - cumulative_sales_k - current_inventory_k = 0`.

Money discrepancy: `current_money - initial_money = 0`.

Employment rate is `currently_hired_agents / initial_participants`, undefined for no participants. Household income is period wages + transfers + dividends, before a tax deduction to avoid changing the definition mid-run. A distinct net disposable income is **not** yet reported. Household *liquid wealth* is household cash. The unweighted household Gini is `G = 2 Σ_i i x_(i)/(n Σ x) - (n+1)/n` for sorted nonnegative amounts, undefined at zero total or zero households. The transaction-weighted price is `Σ_f units_sold_f × prior_price_f / Σ_f units_sold_f`, undefined if there are no transactions. These metrics are artificial measurements, not normative welfare scores.

## Stochastic control and conflict resolution

A seed initializes a NumPy PCG64 generator. Agent skills, participation and firm owners are drawn once. For each sector and period, demand Bernoulli draws, preferred-seller draws and a randomized household purchasing order are generated in fixed sizes. Firm priority rotates deterministically by period index; worker selection uses stable sorting with agent-ID ties; scarce resource residuals use the same rotating priority. Under an identical engine, config, runtime-compatible NumPy version and serialized RNG state, replay is exact. Matching seeds across scenarios helps initialize shared populations but does not guarantee perfectly coupled stochastic decisions once their paths diverge.
