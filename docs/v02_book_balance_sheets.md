# CIVITAS v0.2 — Audited book-value balance sheets

**Status:** experimental `0.2.0.dev0`. This document describes an internally reconciled synthetic accounting convention, **not GAAP/IFRS compliance, a market valuation, or a calibrated economic model**.

## Scope and equations

The simulator records four financially relevant sectors: households, firms, government and an explicit *unowned firm-equity residual* for zero-household/ownerless worlds. All values below are integer cents; physical quantities remain in separate integer-unit records.

For firm \(f\):

\[
A_f = C_f + I_f + K_f, \qquad L_f = D_f, \qquad E_f=A_f-L_f.
\]

- \(C_f\): liquid firm cash.
- \(I_f\): finished-goods inventory **historical carrying cost**, if the cost-basis model is enabled; otherwise zero book value.
- \(K_f\): productive-capital historical basis, if enabled; otherwise zero book value.
- \(D_f\): bilateral principal owed to households.
- \(E_f\): signed residual equity. **Negative residual equity is not an enforceable household payment obligation**.

Each registered firm owner receives an exact integer allocation of that signed book residual: equal quotient and a stable owner-ID-order residual. Without owners, the entire residual is recorded in `unowned_firm_equity_cents` rather than disappearing. The owner attribution is a bookkeeping convention, not a stock exchange price or a shareholder liability rule.

For household \(h\):

\[
NW_h = C_h + S_h + R_h + \sum_f E_{hf}.
\]

Here \(S_h\) is **cash already set aside** in a separate savings account; it is **not** a claim on a banking intermediary. \(R_h\) is bilateral outstanding loan principal against firms. No interest accrues. The government holds its liquid tax/fee surplus \(G\), with no government debt or public capital valuation yet.

CIVITAS checks:

\[
\begin{aligned}
\sum_h R_h &= \sum_f D_f,\\
\sum_h \sum_f E_{hf} + E_{unowned} &= \sum_f E_f,\\
\sum_h NW_h + G + E_{unowned} &= M + \sum_f(I_f+K_f),\\
M &= \sum_h(C_h+S_h)+\sum_f C_f+G.
\end{aligned}
\]

The firm cash and inventory/capital claims are counted **once** in the consolidated total. Natural-resource stock and goods consumed by households are **not monetarily valued**. The national book-net-worth total is therefore **not national wealth or GDP**.

## Period flow audit

For fully trace-enabled periods, the new `audit_book_period` delegates monetary principal and physical-cost event replay to the separate independent auditors; then independently recomputes firm book-equity roll-forward from *recorded transactions only*:

\[
E_f^{t+1} = E_f^t + \text{consumer sales} + \text{external capital-good sales}
 -\text{consumer COGS} -\text{external capital-good COGS}
 -\text{uncapitalized wages} -\text{book depreciation}
 -\text{dividends} +\text{principal defaults}.
\]

This earnings identity is enforced **only when historical-cost accounting is enabled**. For legacy scenarios without recorded inventory/capital cost basis, a formal operating-income roll-forward would be misleading; the stock-level, household, monetary and physical identities still apply.

Every household's beginning cash+savings+loan receivable+attributed firm equity is checked against end-of-period balance plus traced receipts/purchases/taxes, owner equity movement and explicit lender default losses. The government's cash is reconciled by the cash transfer auditor.

The owner registry is immutable in the current engine. An unexplained ownership change is a hard failure; a future equity-title transaction must be explicitly journaled before firm entry/exit or share transfers are enabled.

## User workflow

```bash
PYTHONPATH=src:. python -m pytest -q
PYTHONPATH=src:. python -m civitas run --scenario scenarios/capital_reinvestment.json --steps 12 --audit-ledger --output results/audited
PYTHONPATH=src:. python -m civitas balance-sheet --checkpoint results/audited/checkpoint.npz --output results/audited/book_snapshot.json --details
PYTHONPATH=src:. python -m research.run_book_balance_closure --output research/v02_book_balance_6seed --verify
```

A traced run emits `book_balance_reports.jsonl` in addition to monetary/physical events. The checkpoint command can produce a compact summary (default) or per-firm/per-household accounts with `--details`; no earlier checkpoint format changes or new scenario configuration fields are needed. The previous `household_equity_values` market-quote heuristic remains untouched for historical metrics and is **not** the new historical-cost book value.

## Known limitations and remaining gates

- Monetary book values are **historical cost**, not replacement/market value, and opening capital basis uses a stipulated quote. With cost accounting disabled, real inventory/capital are still present but carry zero book value.
- No household consumption assets, bank deposits, interest revenue, public debt, public infrastructure balance, accrued payables or capital revaluation. No claim of IFRS/GAAP accounting.
- A firm's negative equity is a **diagnostic**: no creditor recovery priority, court bankruptcy, resolution or limited-liability law has been implemented.
- Ownership shares are deterministic book attributions, not independently negotiable assets. Transfers of equity title, firm creation and dissolution remain unimplemented.
- Book calculations use unbounded Python integers for auditing, while existing NumPy intermediate computations in the simulation still require further overflow hardening.
- Both auditor and engine process the **same synthetic event traces**. Exact internal reconciliation does not validate the realism or truth of those events.

Next: explicit firm lifecycle and insolvency liquidation rules, stronger intermediate integer safety, complete cross-sector cost accounting, and externally benchmarked long-horizon behavior.
