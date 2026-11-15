# CIVITAS book-value balance-sheet verification campaign

**Version:** `0.2.0.dev0` (experimental). **Calibration:** none. All results describe software/model consistency only.

The main campaign executes 6 independent seeds (2,3,5,7,11,13), each under three accounting settings (cash-only, historical cost, and historical cost with enabled bilateral credit), across 12 periods with 128 agents. Inputs are given in `research/run_book_balance_closure.py`.

**Verified:** 18 simulations and **216 complete period audits**, including **26,311 monetary transfers and 11,858 physical events**; no book-equity or monetary conservation discrepancies. The credit-enabled standard settings originated no loans, so they do **not** provide observed evidence of credit flows. This negative result is preserved, not concealed.

To verify nonzero credit flows, a separate, hand-constructed four-person synthetic model (six seeds; exactly two periods per seed) begins with one prefunded seller goods stock and a household's 2,000 cents deliberately transferred from spendable cash into savings. Each scenario genuinely originates 200 cents of principal and subsequently defaults the same amount. Thus **6 additional simulations / 12 period audits**, **1,200 cents originated**, **1,200 cents defaulted**, final loan stock zero, and zero equity discrepancies. This is a software boundary-case fixture, **not a representative economic experiment**.

Data:
- `research/v02_book_balance_6seed/periods.jsonl`: complete per-period accounting reports (not complete individual transaction traces).
- `research/v02_book_balance_6seed/active_credit.jsonl`: the six explicit loan/default two-period observations.
- `research/v02_book_balance_6seed/summary.json`: design, exact counts, SHA-256 digests.
- `research/run_book_balance_closure.py --verify`: hashes the records, reruns the full campaign from seeds and configs, and matches every saved record, rejecting tampering.

The executable unit and adversarial tests also cover per-owner residual rounding, signed negative equity, ownerless firms, misattributed household equity, a changed ownership registry, incorrect transfers, inventory-cost errors, exact checkpoint resumption, trace-on/off metric equivalence and CLI JSON export. These checks are internal verification, **not** external scientific validation.
