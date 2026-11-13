# CIVITAS v0.2 experimental savings and firm-flow extension

Status: **implemented and software-tested on development branch**, not externally calibrated. One period is an abstract unit. Money is integer cents; physical quantities are integer units. This specification is independent of any political conclusion.

## New state and scenario controls

Each household `h` has a spendable cash account `C_h` and a separate noninterest-bearing reserve `B_h` (`household_savings`). This reserve is modeled as hoarded currency, **not a bank deposit**: no bank, lending, investment intermediary, money multiplier, account insurance or reserve interest is implied. Household monetary assets are `C_h+B_h`; these must **not** be added to the aggregate money supply twice.

Scenario fields with default values (off for legacy runs):

- `household_savings_rate=0`: proportion of nonnegative current disposable income targeted for saving; range [0,1].
- `household_liquidity_floor_cents=0`: household spendable-cash minimum respected by deposits.
- `savings_emergency_food_enabled=true`: allow reserve withdrawals **only for a requested good** in the named essential sector.
- `savings_essential_sector="food"`: sector designation used by the preceding rule; must exist when enabled with a positive savings rate.

Existing capital and ownership controls are unchanged. The legacy v0.1 four scenarios retain default zero savings and remain compatible.

## Timing, decision functions and accounting

For each period the existing order is: depreciation; renewable stock regeneration; labor matching and wage transfers; constrained goods production; wage taxes and transfers; cash-budgeted consumer purchases with conditional savings release for the essential sector; real-goods investment; cash-profit-proxy dividends; household saving deposits; exact per-account-flow reconciliation; repricing; invariant checks and metrics.

For a buyer of an essential good at posted price `p`, the agent may use the reserve if `C_h < p <= C_h+B_h` and stock exists. The engine transfers exactly `p-C_h` from the household's reserve to its spendable cash; only then does it execute the normal household-to-firm purchase. Nonessential demand is financed from `C_h` alone. Requested saving occurs **after** expenditure and dividends:

```
D_h = wages_h - wage_tax_h + transfers_h + dividends_h
saving_deposit_h = min(floor(max(0,D_h) * savings_rate),
                       max(0, C_h_after_purchases - liquidity_floor))
B_h_after = B_h_before + saving_deposit_h - savings_withdrawal_h
```

Deposits and withdrawals are explicit conserved source-to-destination ledger movements. No household or firm may create money by moving funds into a reserve. This is a stylized liquidity-buffer rule, **not a behavioral estimate**.

For a firm `f`, define receipts from household purchases `R_f`, revenue from selling produced capital-input goods to *other firms* `I_f`, current wages paid `W_f`, and cash paid for capital goods to other firms `X_f`. Own-firm physical conversion is a nonmonetary inventory-to-capital conversion. Let `δK_f` be physically depreciated capital units during the period, and `p^K_t` the **lowest posted price of the capital-input sector before repricing**. Then:

```
operating_cash_surplus_proxy_f = R_f + I_f - W_f
noncash_depreciation_proxy_f = δK_f * p^K_t
profit_proxy_f = operating_cash_surplus_proxy_f - noncash_depreciation_proxy_f
dividends_f = min(current_cash_f, floor(max(0, profit_proxy_f) * dividend_share))
Δfirm_cash_f = R_f + I_f - W_f - X_f - dividends_f
Δ(C_h + B_h) = wages_h - tax_h + transfers_h + dividends_h - purchases_h
Δgovernment_cash = tax_receipts - transfers
```

Capital purchases **are not charged as an operating expense**; they exchange cash for productive assets (or convert own inventory). Every cross-firm purchase is recognized as a receipt by its source supplier; this fixes the earlier omission of such receipts from the supplier's profit measure. Depreciation is noncash. These are modeling approximations, **not fully accrual-compliant profits**: there is no unit-cost inventory accounting, cost of goods sold, impairment, liabilities, interest, external dividends on undistributed reserves, or full balance sheet. The numerator of `profit_proxy` should not be interpreted as audited net earnings.

Every period asserts all account-level cash-flow identities, as well as existing money, capital, natural-resource and finished-goods identities. Negative or out-of-range account IDs are rejected. The new metrics explicitly report savings balance, deposited and withdrawn values, total household monetary assets, equity-valued modeled net worth, capital-goods sales revenue, depreciation expense, and reconciliation discrepancies.

## Persistence and compatibility

New checkpoints use `checkpoint_version=3` and serialize `household_savings`. Versions 1 (`0.1.0`) and 2 (`0.2.0.dev0`) are read by migration, adding zero reserve balances, without changing historic capital or RNG state. New v3 checkpoints must match the current software version. A real previous-release v2 checkpoint (`capital_reinvestment`, seed 7, 24 periods) was extracted from the earlier experiment archive and resumed under the new engine, with zero listed accounting discrepancies. The test suite also constructs versioned migration examples and verifies exact RNG continuation. The old accounting/production rules are behaviorally equivalent for legacy scenarios because all newly introduced mechanisms are disabled by default.

## Known limitations / validation priorities

- Savings are inactive monetary reserves; **they do not finance investment**. A future v0.2 stage should add explicit lending, equity issuance, or government allocation only if the corresponding liabilities and flows are represented on both sides.
- No economy-wide price index, national-accounting double-entry capital valuation, bank, or complete corporate income statement is implied.
- Population changes do not automatically scale the fixed number of firms, initial firm cash/capital, and total resources; population-size experiments differ in structural per-capita endowments.
- Signed int64 overflow at extreme configurations remains an open engineering gate. Model trajectories are not externally calibrated.
- The final-period experimental confidence intervals are Monte Carlo approximations over random seeds under **fixed assumptions** only; model and parameter uncertainty are much larger and unmeasured.
