# CIVITAS v0.2 — Transaction-level accounting closure experiment

**Execution date:** 2026-11-14. **Model status:** `0.2.0.dev0`, experimental. This is a numerical/software audit of a synthetic agent-based economy, not an empirical economic-validation study.

## Objective and method

Test whether an independent, strictly typed transaction-level ledger can reconstruct every participant's opening-to-closing cash holdings (household spendable cash, household savings, firm cash and government cash) and the lender and borrower positions of bilateral investment-credit contracts. Replay actual ordered transfers using a separate implementation (`src/civitas/ledger_audit.py`), cross-check the journal count and cents for each reason, selected reported metrics, and closing balances. For defaults, audit explicit creditor/debtor events instead of inventing a monetary transfer.

A separate adversarial suite deliberately corrupts transfer IDs, reasons, amounts, journal counts and loan writeoffs. The engine runs the audit automatically only with `transaction_trace=True`, retaining unchanged legacy outputs and RNG consumption when tracing is off.

## Completed sample

Three World Genesis modes — configured, Hybrid, randomized — each tested with independently seeded instances `1,2,3,5,8`. Each of **15 runs** executed **12 periods**, for **180 fully audited engine periods**. Population requests were 400 agents per seed; randomized mode may draw a different population within its declared plan bounds. All full runs additionally performed an exact checkpoint-restore comparison for the following period.

| Quantity | Verified value |
|---|---:|
| Complete world runs | 15 |
| Audited periods | 180 |
| Individual cash transfers replayed | 69,425 |
| Sum of transaction amounts (gross throughput, cents) | 123,516,369 |
| Monetary/physical/loan identity failures | 0 |
| Exact checkpoint next-step replay failures | 0 |
| Full automated regression tests after implementation | 206 passed |

**Scope qualification:** The 123,516,369-cent total is *gross transferred value*, including multiple movements of the same money; it is not newly created money, GDP, value added, or welfare. The default 15-world campaign does not exercise lending because its resolved genesis plans do not enable the credit mechanism. Real credit origination and maturity default are covered separately by a deterministic capital-investment analytical test (`test_live_engine_credit_origination_then_noncash_default`) where a firm borrows 200 cents and later extinguishes a 200-cent claim without a cash writeoff transfer.

## Reproduction

```bash
PYTHONPATH=src:. python -m pytest -q
PYTHONPATH=src:. python research/run_ledger_closure.py \
  --seeds 1,2,3,5,8 --steps 12 --population 400 \
  --output results/ledger_closure
PYTHONPATH=src:. python research/run_ledger_closure.py \
  --verify-only --output results/ledger_closure
```

The serialized experiment metadata is preserved as `research/v02_transaction_ledger_15/summary.json`; the runner produces a SHA-256 of the canonical summary (without its own hash) and rejects altered metadata during `--verify-only`. Restoring the original computation requires the same source code, dependency/environment assumptions and seeds. This summary does **not** replace full per-transfer audit logs; those are written only when the CLI option `--audit-ledger` is enabled and retained in the destination run folder.

## Limitations and next steps

This milestone does not reconstruct the physical inventory ledger, per-unit input cost basis, accrued household/firm income, bankruptcy recovery or a complete financial statement system. Physical stock accounting, COGS and firm book equity are still independently enforced by their existing engine-level identities, not by a new multi-asset event store. The transaction-level feature is an opt-in verification layer that deliberately increases memory and log volume; benchmark/runtime overhead has not been established across all scales. The original price/hiring dynamics and long-horizon contraction remain under research, and all behavior must remain attributed to its synthetic assumptions.

**Next engineering gate:** unify nonmonetary goods and capital movements into typed events, independently reconstruct firm inventory and historical-cost balances, and add complete beginning/flow/ending balance sheets before implementing firm entry, bankruptcy and supply-chain links.
