# CIVITAS v0.2 — Physical flow and historical-cost replay

**Status:** Experimental auditing infrastructure (`0.2.0.dev0`). No empirical validation or financial-reporting compliance is claimed. This extends, and does not replace, the independently replayed cash/principal journal.

## Motivation

Aggregate conservation can detect that goods were duplicated, but not that ten units were booked against the wrong firm when total units remain unchanged. Likewise, a firm can misallocate a historical-cost cent to the wrong seller while total book value still appears correct. This opt-in physical journal captures the actual operations for every firm, and an independent reducer reconstructs each account from an opening snapshot.

## Independent opening balances

`capture_physical_opening(state)` copies every firm's goods inventory, inventory carrying value in cents, productive capital units, capital carrying value in cents, period-opening posted prices, and the natural resource stock. The snapshot is separate from the mutable simulation state. A simulated period records `Period.physical_transactions`, and `audit_physical_period(opening, closing, period, scenario)` independently replays the event list.

## Exact event schema

| Event | Required data | Physical effects |
|---|---|---|
| `depreciate` | firm, units, basis_cents | Decrease firm's capital units and allocated carrying value |
| `regenerate` | units | Increase common renewable resources |
| `manufacture` | firm, units, resource_units, basis_cents | Consume resources and add finished inventory plus manufacturing cost basis |
| `consumer_sale` | firm, household, units=1, basis_cents, price_cents | Remove one unit and its cost basis; cross-check matching household-to-firm cash payment |
| `convert_capital` | supplier, buyer, units, basis_cents, capital_cost_cents, price_cents | Remove supplier's finished capital goods, add buyer's physical capital, and allocate both asset bases |

Production's physical resource intensity must match that sector's configured units of resource per good. Resource fees must match firm-to-government financial transfers. Manufacturing cost basis must equal wages paid plus extraction fees for firms producing positive units. Nonproducing firms' wage expense remains uncapitalized. Material conversions are exact; goods cannot be silently created by capex. External capital purchases must match a firm-to-firm financial transfer; own-firm conversions have **no fictitious cash payment**. Weighted-average cost basis allocation is checked in independent integer arithmetic, and recorded prices must match period-opening quoted prices.

Event order is monotone through **depreciation → regeneration → manufacture → consumer sale → capital conversion**, consistent with current economic operation ordering (loans are a separate financial trace). Signed-int64 quantities, unknown fields, invalid entities, duplicate production events, cash mismatches, negative stocks and non-causal operations fail closed.

## Reconciliation and tests

The independent reducer checks every firm, not only sector or aggregate totals: ending inventory and inventory basis, capital units and capital basis, and the common resource stock. It also cross-checks per-sector production and consumption and selected exact integer period metrics (including COGS, capex valuation and capital depreciation). The separate monetary auditor replays cash balances and bilateral loan principal; both execute automatically when scenario `transaction_trace=True` or CLI `--audit-ledger` is used.

Tracing is **off by default** to preserve previous scenario behavior and runtime cost. Trace records are written as `physical_transactions.jsonl` alongside `transactions.jsonl` and `noncash_transactions.jsonl`. Ordinary simulation trajectories and checkpoints retain their existing format and random-number stream. A checkpoint is a snapshot of the live world, not a permanent record of past events; the standalone JSONL evidence must be archived for historical forensic inspection.

```bash
PYTHONPATH=src:. python -m pytest -q
PYTHONPATH=src:. python research/run_physical_closure.py --output research/v02_physical_ledger_20
PYTHONPATH=src:. python research/run_physical_closure.py --output research/v02_physical_ledger_20 --verify-only
PYTHONPATH=src:. python research/run_physical_closure.py --output research/v02_physical_ledger_20 --verify-replay
```

## Limitations and next accounting gate

Physical audit does **not** yet constitute a full standards-compliant balance sheet. It lacks detailed household durable goods, intermediate-input networks, finished-goods transfer/title accounts, tax basis adjustments, comprehensive firm cash-flow statements, interest receivables and public-sector asset statements. No accounting event journal can independently prove a production process is economically realistic merely because the simulator and event trace agree. The correct next gate is an independently testable **opening + transactions = closing** multi-party consolidated balance sheet with business closure, intra-sector procurement and firm insolvency, plus adversarial randomized fault injection.
