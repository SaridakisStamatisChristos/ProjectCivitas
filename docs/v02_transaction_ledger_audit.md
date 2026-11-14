# CIVITAS v0.2 — Independent transaction-level cash and credit audit

**Status:** experimental verification feature, not a complete financial accounting system.

## Why this exists

Before this extension, CIVITAS checked conservation of total money, goods, resources, capital, per-firm cash and per-household combined cash/savings, and several cost-basis and loan-principal identities. Those checks can miss *misallocated* transfers: a payment to the wrong household can preserve total money and even some economic summary statistics. A separate replay of every traced transaction provides a more stringent control.

## Scope

`civitas.ledger_audit` captures the opening household cash, savings, firm cash, government cash, household loan assets and firm loan liabilities. For each positive, signed-64-bit transfer in `Period.transactions`, an independent reducer validates account types and IDs, reason-to-account direction, spending capacity, receiving capacity, and the exact transferred amount. It replays each payment in order.

The model's financial events use explicit account pairings, including `wages`, `wage_tax`, `transfer`, `sale`, `capital_purchase`, `resource_fee`, `dividend`, `savings_deposit`, `savings_withdrawal`, `loan_origination`, and `loan_repayment`. Household savings transfer IDs must identify the same household; lending must move existing savings into firm cash and create a matched, noncash creditor asset/debtor liability. Repayment cancels principal on both sides.

A **loan default is not a cash transfer**. The trace now stores its creditor, debtor and extinguished principal in `Period.noncash_transactions`; this is written to a separate `noncash_transactions.jsonl` file. The auditor deducts the writeoff symmetrically from both financial positions and verifies the `loan_default_noncash` summary journal. It does not misrepresent writeoffs as newly issued or destroyed currency.

The replay must agree exactly with **every** closing account and claim, not only aggregate totals. The independent journal totals (counts and cents per reason), selected published integer metrics and recorded total money are also verified. Unexpected or malformed transaction fields, unknown payment classifications, negative intermediates, overflow and mismatched evidence fail the audit.

The simulation performs this audit **automatically after each step** when `transaction_trace=True`; it does not silently pass if tracing is disabled. Tracing is off by default, retaining existing economic rules and benchmark performance. In Python, `capture_opening(sim.state)` and `audit_period(opening, sim.state, result)` permit explicit repeated verification outside the engine. `Period.noncash_transactions` has an empty-list default for compatibility.

## Usage

```bash
PYTHONPATH=src:. python -m civitas run \
  --scenario scenarios/market.json \
  --steps 12 --audit-ledger --output results/audited_baseline

PYTHONPATH=src:. python research/run_ledger_closure.py \
  --seeds 1,2,3,5,8 --steps 12 --population 400 \
  --output results/ledger_closure

PYTHONPATH=src:. python research/run_ledger_closure.py \
  --verify-only --output results/ledger_closure

PYTHONPATH=src:. python -m pytest -q
```

When using `--audit-ledger`, the resolved scenario sets `transaction_trace=True`, intentionally changing the configuration hash, but not the random decisions or underlying economic behavior. Existing `resume` commands honor the `transaction_trace` property saved in the checkpoint.

## Validation and limitations

The independent replay is robust against participant mispostings even when they cancel in the grand totals. Adversarial tests alter IDs, transfer amounts/reasons, journal counts, metrics and loan writeoff events. Additional tests cover the exact persisted JSONL trace, deterministic checkpoint continuation, World Genesis and actual in-engine capital-purchase lending/default.

**Not included in this ledger:** physical inventory movement, resource extraction, initial or manufactured inventory cost-basis, household equity-valuations and accrual income recognition. The engine's physical and firm-book-equity checks still operate separately. A future unified multi-asset transaction engine with independently reconstructed physical balances, costs and full beginning/ending financial statements is required before calling the entire CIVITAS economy accounting-complete. Trace data can be very large for 10,000+ agents; keep it opt-in.

The audit validates what the simulated event stream represents, not whether the underlying economic institutions or behavioral assumptions match empirical economies.
