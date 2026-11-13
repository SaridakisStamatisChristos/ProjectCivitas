# CIVITAS v0.2 development: bilateral investment credit and resource-input fees

**Status:** Executable experimental mechanism; not calibrated banking or national accounts. Implemented as an **opt-in**, with v0.1/v0.2 historical scenarios unchanged when disabled. One time step remains an abstract economic period.

## State and timing

All monetary values are **integer cents**; physical stocks are integer units. In addition to household spendable cash `C_h` and reserved savings cash `B_h`, households now hold noncash face-value **loan receivables** `L_h`. Firms have cash `F_f`, inventory cost basis `I_f`, productive-capital cost basis `K_f`, and debt principal `D_f`.

A contract holds exactly `(household_id, firm_id, outstanding_principal, origination_step)`. A contract is a household asset and a firm liability; it is **not itself money**. No bank, interest, deposits, credit creation, collateral, guarantee, security market, or rolling maturity is modeled. Household participation in lending is an **imposed rule**, not a revealed preference or observed willingness to lend.

The period ordering relevant to the optional mechanisms is:

1. Capture opening household assets, loan receivables, firm cash, firm liabilities and firm book equity.
2. **Service existing loans** before wages; each firm has a fixed repayment budget: `floor(max(0, F_f - firm_cash_reserve) * repayment_fraction)`, applied in oldest-contract order. At `current_step - origination_step >= term`, any unpaid principal is written off at face value.
3. Depreciate capital, regenerate/extract resource stocks, hire/pay wages and produce. With `resource_extraction_fee_cents_per_unit = q`, a firm producing `x` goods, each using `r` resource units, pays government `q*r*x` cents, bounded by remaining firm cash after wages. The cash payment is an **inventory cost** when goods are produced, not a second physical resource consumption. Unproductive payroll is expensed.
4. Wage taxes and redistribution; household consumer purchases; **capital investment**.
5. If credit is enabled, a firm purchasing actual capital goods from a *different* firm may borrow up to the **precise cash shortfall** required by that purchase, subject to its aggregate outstanding-principal ceiling and lender savings budgets. No borrowing occurs for internal same-firm goods conversion or without available capital goods.
6. Compute earnings, pay dividends, allocate new voluntary-in-model savings out of disposable cash, check all stock/flow identities, reprice and increment time.

Each household's cumulative available lending *this period* is `floor(B_h * credit_lender_savings_share)` using an exact rational conversion of the configured decimal. Lender order rotates deterministically by `(firm_id + step)`; no random-number consumption is added. Before originating a loan, the whole multi-lender amount is preflighted against real savings balances, integer storage limits, and the firm's headroom; originations are then ordinary conserved `savings -> firm` money transfers. Capital purchases are the usual `firm -> supplier firm` transfers.

## Accounting identities

With monetary stock `M`, loan claims `A`, and firm debts `D`:

`M = sum(C_h + B_h) + sum(F_f) + government_cash = constant`.

`A = sum_h L_h = sum_f D_f = sum(active_contract_principal)`.

`D_end = D_open + principal_advanced - principal_repaid - principal_defaulted`.

`L_end = L_open + principal_advanced - principal_repaid - principal_defaulted`.

A household's **monetary** assets obey:

`Δ(C_h + B_h) = wages - wage_tax + transfers + dividends - consumer_spending - new_loans + principal_repayments`.

A firm's **cash** obeys:

`ΔF_f = consumer_sales + capital_goods_sales - wages - resource_fees - capital_goods_purchases - dividends + loans_received - principal_repaid`.

Government cash: `ΔG = wage_tax + resource_fees - transfers`.

For historical-cost accounting, firm book equity is `E_f = F_f + I_f + K_f - D_f`, and:

`ΔE_f = sales - consumer_COGS - capital_goods_COGS - uncapitalized_wages - book_depreciation - dividends + principal_defaulted`.

A default is **not** a transfer: the household's financial asset and firm's debt liability are written down together. The resulting lender loss and borrower debt-extinguishment gain are **not included in the operating earnings metric**, and the gain appears separately in book-equity reconciliation. This is an accounting convention, not a model of legal insolvency proceedings or taxed debt relief.

New metrics include originated, repaid, defaulted, and outstanding principal; household loan claims; government resource fees; firm resource-fee expense; and dual-side principal discrepancies. Book-equity, household cash flows, firm cash flows, money, finished goods, productive capital, and physical resources are independently audited. With no credit the new loan metrics remain zero and old scenario metrics retain their previous definitions.

## Checkpoints, constraints and limitations

Version-5 NPZ checkpoints serialize each contract and all household asset/firm liability arrays using pickle-free NumPy arrays; restored runs continue the same deterministic random stream. Versions 1–4 remain readable with zero added loan balances and contracts. A checkpoint claiming `credit_enabled=true` cannot load as a legacy format that lacks its history.

Credit requires `capital_enabled` **and** `cost_basis_accounting_enabled`; all three are opt-in. Default principal caps and parameters are scenario choices, **not optimized terms**. Direct lending competes with emergency liquid household reserves. Default erases credit claims but does not erase or issue currency. A loan might reduce production when its repayment/default or lender-liquidity consequences outweigh additional capital purchases. This is an expected possible result, not a code defect.

Known limitations: no interest, collateral, loan price discovery, risk selection, bargaining, loan resale, external-sector balance, insurance, insolvency law, debt tax accounting, monetary authority, resource opportunity cost beyond configured transfer fee, environmental feedback beyond physical regeneration, or empirical calibration. Firm earnings remain a simplified historical-cost model, not GAAP/IFRS financial statements. Multi-firm balance and integer-overflow stress at extreme scales are still open gates.

Run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q` and see `research/run_credit_experiment.py` for the controlled credit/resource-fee tests. **Do not merge to `main` or claim final v0.2 scientific validation based on these experiments.**
