# CIVITAS v0.2: candidate price and hiring rules

**Status:** implemented, software-tested experimental alternatives. The default rules remain unchanged; no candidate is declared a scientific or policy winner.

All simulations advance in abstract discrete periods. All posted prices and cash accounts are integer cents; resource, finished goods and capital units are integers. A step's hiring decisions precede production, consumer purchases, and end-of-step repricing. The new rules introduce no random draws, financial transfers, or physical production outside those already present in the engine.

## Hiring targets

For sector `k`, firm `f` in that sector, let `H` denote household count, `d_k` the probability that one household requests its sector good, and `N_k` the number of firms in sector `k`. At the beginning of period `t`, define:

- `B = H*d_k/N_k` (stationary expected per-firm household demand).
- `A(t) = max(0.25*B, sales_f(t−1) + unmet_stock_k(t−1)/N_k)` for `t > 0` (historical adaptive estimate). The `unmet_stock` signal is sector-wide, not firm-specific.
- At `t = 0`, all three choices use `B`.

The new **blended** estimate is `(B + A(t))/2`; existing choices are **adaptive** `A(t)` and **stationary** `B`. All three then pass through *the existing* inventory buffer, productive capital constraint, labor productivity, worker availability, hiring ordering, and firm wage-budget checks. Wages themselves do not adjust; this is not a wage-bargaining model.

## Price transition

Let `p_f(t)` be the quoted price *before* end-of-period repricing, `q_f` unsold finished stock, `z_f` goods sold, `α` `price_adjustment`, and `p_min` the minimum price. The historical `inventory` rule proposes:

- If `q_f=0` and `z_f>0`: `p_proposed = max(p_min, ceil(p_f*(1+α)))`.
- Otherwise if `q_f > max(2, ceil(H*d_k*0.25/N_k))`: `p_proposed = max(p_min, floor(p_f*(1−α)))`.
- Otherwise `p_proposed = p_f`.

The new **affordability_guard** rule applies the *same* proposed price decreases and unchanged prices. For proposed **increases only**, it checks whether at least `ceil(τ*H)` households have end-of-period purchasing power `>= p_proposed` (`τ = price_affordability_floor`, default `0.25`). If the test fails, the price remains at the old `p_f`. Food-sector households may include savings balances where the configured essential-good emergency withdrawal rule applies; otherwise only spendable household cash counts. The rule is observational at repricing time and consumes no RNG.

Important interpretative limits: purchasing power is measured **after** current purchases and dividends, not the purchasing power at the time of sale. It considers all households, not only customers who sought this specific good, and is not restricted to a firm's geographic market. It is an intentionally coarse *global affordability signal*. It can freeze price increases even if actual buyers are willing to pay more. `τ=0` makes the guard inert. It does not create a price equilibrium and it does not assert price controls are desirable in real economies.

## Configuration

```json
{
  "price_update_rule": "affordability_guard",
  "price_affordability_floor": 0.25,
  "hiring_expectation_rule": "blended"
}
```

`price_update_rule` accepts `inventory` (default) or `affordability_guard`; `hiring_expectation_rule` accepts `adaptive` (default), `blended`, or `stationary`. `price_affordability_floor` is a finite numeric value in `[0,1]`. Invalid strings and out-of-range parameters are rejected. All new fields persist through scenario JSON and exact scenario-replay NPZ checkpoints. The `market_rules.py` module contains the pure historical price formula and all three hiring equations, permitting independent analytical tests.

## Verification versus scientific validation

Software verification checks deterministic seeds, zero-population behavior, exact historical-default regression, finite nonnegative stock/monetary identities, replay from checkpoint, the zero-guard-inert case (testable), intact RNG streams, and independently audited experimental records. These checks do not validate consumer behavior, rational expectations, employment institutions, equilibrium properties, or real-world predictions.
