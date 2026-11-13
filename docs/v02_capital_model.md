# CIVITAS v0.2 development slice: capital, investment, and household accounts

**Status:** implemented experimental extension on `feature/v0.2-capital-accounting`. NOT a completed v0.2 release, empirical model calibration, or theorem of economic behavior.

## Motivation and model classification

- **Baseline source:** v0.1 is an explicitly stylized agent-based production-and-consumption simulation.
- **New simplifying assumptions:** one produced bundle from the designated `capital_input_sector` is convertible into one unit of productive capital; noncapital firms and capital-producing firms both use the same service-capacity rule. The model has no bank, machinery supplier balance sheet, credit, or irreversibility adjustment cost beyond inventory consumption.
- **New CIVITAS design:** fixed firm-capital capacity, end-of-step investment, integer physical capital conservation, explicit firm-to-firm cash transfers, household model-marked equity and net disposable receipts.
- **Unverified hypotheses:** productive reinvestment may buffer a depreciation shock; ownership concentration may affect aggregate demand via household purchasing power. Tests must falsify those predictions under varied assumptions.

## State, units, and budgets

For each firm `f`, physical capital stock `K_f(t)` is an integer number of capital units. At initialization the designer may endow `K_f(0)=K_init`. These are **exogenous initial assets** and are not newly produced in the simulated economy. Monetary accounts and resource inventories remain separate.

At the beginning of period `t`, capital depreciates:

`D_f(t)=floor(delta * K_f(t))`, `K'_f=K_f-D_f`.

Fractional depreciation is rounded down at each firm each period, creating a known small-stock threshold effect. This is not a continuous-time depreciation solution. Capital does not consume additional resource per period, other than its input resource during the production of the capital goods.

The firm seeks output `Q*_f(t)` through its existing v0.1 demand expectation. Its **operational target** (and hence hired workers) is capped by `b * K'_f`, where `b=capital_output_per_unit` is a fixed maximum produced goods per unit of capital per period. Actual production is still constrained by skills, labor, finance and the global resource.

At the end of consumption but before dividends, each firm calculates:

`K_target = ceil(Q*_f(t) * (1+beta)/b)` and `investment_need=max(0,K_target-K'_f)`.

The firm may authorize expenditure of at most `floor(mu * firm_cash_f)` cents on physical capital input. It visits sellers in the `capital_input_sector` in ascending posted-price order, and each investment purchase is capped by supplier remaining physical inventory, current budget and desired units. A purchase of `q` goods at unit price `p` gives:

- supplier `inventory -= q`;
- buyer `firm_capital += q`;
- firm-to-firm transfer of `q*p` cents if buyer and supplier are different firms.

If buying its own production, no *external* monetary transfer occurs. The inventory still disappears and productive capital appears. The imputed value is included in `capital_investment_goods_value_cents`, but **not** in `capital_interfirm_purchases_cents` or ledger transfers.

**Transition order:** resource regeneration → scheduled automation → capital depreciation → hiring/payroll → physical output → wage taxation → transfers → household purchases → investment conversion → dividends (bounded by remaining liquid firm cash) → repricing → invariant audit.

In the *initial* capital-only slice, the simple profit proxy for dividends was `max(0, sales-current_wages)`; it excluded depreciation and capital-cost accounting. Investments are asset conversions, not expensed into that proxy. Thus this is *not* GAAP/IFRS profit or a complete corporate sector balance sheet.

## Accounting identities

1. Monetary conservation: `M(t) = households cash + firms cash + government cash = M(0)`.
2. Physical resource: `R(0) + cumulative_regeneration - cumulative_extraction = R(t)`.
3. Finished goods, per sector: `cumulative_output - household_consumption - goods_converted_into_capital = current_firm_inventory`.
4. Capital stock: `sum_f K_f(t) = sum_f K_f(0) + cumulative_capital_conversions - cumulative_depreciation`.
5. Household net current-period cash receipts: `Y_h^net = wages_h - wage_tax_h + transfers_h + dividends_h`. Sales spending is **not** a subtraction from disposable income: it changes household cash, which is reported as liquid wealth.

All cash and physical goods quantities are integer. The engine checks these identities at every period. No monetary supply is created by capex; suppliers receive buyers' funds. Nonnegative cash and inventories are required.

## Equity and household net worth (modeled, not market-observed)

For each firm, a simple non-traded asset proxy is

`E_f = firm_cash_f + inventory_f * current_firm_price_f + capital_f * cheapest_current_capital_goods_price`.

Each firm's owner set splits the integer-cent value equally; deterministic whole-cent remainders go to lowest stored owner IDs. Household `modeled_net_worth = household_cash + sum_f allocated_E_f`.

This **does not measure actual share prices, realizable asset values, comprehensive household net worth, debt-adjusted equity, or external wealth**. Firms have no debt in this release. A price quotation changing can re-mark modeled wealth without money creation. The share-count and ownership-control mechanics remain simplified.

The legacy `income_gini` remains gross wages plus transfers and dividends to avoid silently changing v0.1 metric semantics. New `disposable_income_gini` deducts wage taxes. Ginis are unweighted across households; zero total income means undefined.

## Scenarios and identification

- `capital_depreciation_only.json`: capital enabled, depreciates, investment budget share zero.
- `capital_reinvestment.json`: same initial state, positive capital investment budget share.
- `capital_concentrated_ownership.json`: same capital investment budget but ownership concentration changes.

For capital-enabled runs, ownership draw uses a dedicated seeded NumPy RNG substream, isolated from agent skill, labor participation and market draws. Thus paired seeds preserve non-owner initial conditions across ownership treatments. Original capital-disabled v0.1 RNG order remains unchanged.

This is a **policy-comparison inside this particular computer model**, not identified causal effects in real societies. Within-simulation effects are sensitive to agent rules, fixed prices, no debt, initial cash endowment, single renewable resource, one capital-goods conversion ratio, and modeled ownership valuation.

## Compatibility and limitations

The capital feature is off for the original scenarios. A new `checkpoint_version=2` stores capital arrays and cumulative conversions. The loader also migrates v0.1 format-1 checkpoints produced by software `0.1.0`, adding zero capital arrays and preserving original pseudorandom state. New development checkpoints must match `0.2.0.dev0` exactly. NumPy bit-generator behavior and NumPy versions affect exact replay portability.

No capital repair industry, entry/exit, real loans, unemployment insurance, exogenous investment liquidity, endogenous wages, intertemporal household optimization, net financial asset issuance, or distribution of capital ownership rights is implemented. Extreme configurations can still exceed int64 safe ranges; arbitrary-scale integer validity has not been proven.

## Superseding v0.2 savings/flow refinement

This document records the original capital-only behavior. The later development slice changes the dividend base to recognize external capital-goods supplier revenues and subtract noncash posted-price depreciation expense; the resulting value remains a **proxy** without unit-cost inventory valuation. The latest written definition, complete reconciliation equations, and format-3 checkpoints are specified in [v02_savings_profit.md](v02_savings_profit.md).
