# CIVITAS v0.2 development — bounded firm insolvency and re-entry

**Status:** Experimental opt-in mechanism, not a stable economic model, legal insolvency implementation, GAAP/IFRS balance sheet, or validated corporate-demography forecast.

## Scope and configuration

```json
{
  "firm_lifecycle_enabled": true,
  "firm_reentry_enabled": true,
  "firm_reentry_contribution_cents": 60,
  "cost_basis_accounting_enabled": true,
  "transaction_trace": true
}
```

Defaults are `false`, `false`, and `0`; old scenarios omit these fields in canonical serialization. Lifecycle requires historical-cost accounting; re-entry requires lifecycle. The current simulator retains **a fixed number of firm slots** (sector and firm ID do not change). An inactive slot has zero cash, inventory, capital, and debt. A re-entering firm uses the **same** registered owners; this is a restart/recapitalization, not the entry of a legally new firm with a new ownership registry.

### End-of-period liquidation

An active firm is selected for liquidation if either:

1. Its book equity is negative: `cash + inventory historical cost + capital historical cost − outstanding principal < 0`;
2. It is completely exhausted: cash, physical finished-goods inventory and productive capital are all zero.

Liquidation occurs **after** ordinary sales, dividends, savings allocations and capital purchases for the period. A firm's previously paid wages and current-period employment are not undone. This is a deliberately simple one-period insolvency rule, with no court procedures, temporary administration or rehabilitation. An insolvent firm may still have paid dividends earlier in the period; an equity-based pre-dividend gate is future work.

The firm repays outstanding contracts **in stored origination order**, using only existing cash. Principal still unpaid is written off on *both* lender assets and borrower liabilities. A default transfers no money. Any remaining inventory and capital are physically scrapped and their cost basis expensed; **zero salvage proceeds** are assumed. Any residual money is distributed to registered owners, with integer-cent remainders allocated by owner ID order; truly unowned residual money is transferred to government. Its active flag becomes false, and all remaining assets and debts must be zero.

A new period can recapitalize a closed slot if all registered owners can pay their equal share of the configured contribution from spendable household cash. Contributions are exact household-to-firm transfers; insufficient joint funding leaves the slot inactive. The firm starts with **cash only**, not magically granted capital or goods. Random-number generation is unaffected by lifecycle selection.

## Independent stock-flow identities

- Total money: `household cash + household savings + firm cash + government cash = initial money`.
- Debt: total loan claims = total firm loan liabilities; contractual origination, repayment and default must reconcile per household and per firm.
- Capital: `ending capital = initial capital + cumulative purchases/conversions − cumulative depreciation − cumulative liquidation scrapping`.
- Sector inventory: `ending stock = cumulative output − cumulative consumer purchases − cumulative capital conversion − cumulative inventory scrapping`.
- Firm book equity: `E = cash + inventory cost basis + productive-capital cost basis − loan liabilities`. During one period, `ΔE = transaction-derived earnings − dividends + owner contributions − liquidation cash distributions + principal defaults − disposal basis losses`.
- Household attributed equity remains based on the immutable owner registry; matching paid-in capital lowers household cash while increasing its attributed ownership residual.

Transaction traces contain `firm_capital_contribution`, `firm_liquidation_distribution`, `firm_liquidation_escheat`, ordinary loan repayments and noncash loan defaults. Physical traces contain a distinct `firm_liquidation` inventory/capital disposal event. A third `firm_lifecycle_transactions.jsonl` stream records entry and exit transitions. The independent lifecycle auditor must reconcile the activity flags and each transition with the cash and physical traces; the book and physical auditors independently replay their corresponding balances.

Checkpoint **format 6** is used only for lifecycle-enabled scenarios. It stores the active-firm mask and cumulative scrapping counters. Versions 1–5 remain loadable by their existing readers/compatibility rules; non-lifecycle checkpoint output retains its original format. The previous model's metric keys and scenario digest are unchanged with the option disabled.

## Known restrictions and next gates

- Fixed firm count and inherited ownership: no genuine incorporation, ownership market, sector switches or competitive entry.
- Zero salvage for tangible assets; no transfer of liquidation inventory or capital to purchasing firms.
- Loan-principal claim priority follows stored order, not contractually negotiated collateral or legal seniority.
- No bankruptcy filing, taxes on liquidation, labor severance or payroll arrears; employment is period-based.
- No modeled share-transfer ledger, equity issuance to new owners, retained earnings restrictions, asset auctions, interest accrual or institutional bankruptcy regime.
- Cents and units use signed-int64 storage; full overflow proof under arbitrary multi-period extremes remains open.
- Generated prices/production are stylized and not empirically calibrated.

**Next development:** enforce solvency-aware dividend limits; add assets sales to other firms with counterpart physical title events; model genuinely new entrants without changing historical ID mappings; then stress-test long-horizon sector turnover and credit cascades.
