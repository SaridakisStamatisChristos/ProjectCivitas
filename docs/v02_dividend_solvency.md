# CIVITAS v0.2 — Solvency-aware dividends

**Status:** Experimental, lifecycle-enabled firm policy. Not a real-world legal-solvency rule, GAAP/IFRS implementation, or evidence of economic welfare.

## Problem

Before this change, CIVITAS calculated a firm's dividend as the smaller of available cash and its nonnegative current-period profit times the configured payout share. For a firm with large outstanding principal, the calculation could transfer cash to owners immediately before the `firm_lifecycle_enabled` path liquidated the firm and defaulted its creditors.

This is inconsistent with the current lifecycle's stated **zero-salvage assumption**: goods and capital are scrapped rather than sold for creditor recovery.

## Implemented rule

For **lifecycle-enabled** firms, with all monetary quantities in integer cents:

- `C`: cash after operations and existing loan servicing, immediately before the payout.
- `I`: inventory carrying value at historical cost.
- `K`: productive-capital carrying value at historical cost.
- `P`: remaining outstanding loan principal.
- `D_legacy`: dividend proposed by the old profit-share rule.

Define book equity `E = C + I + K − P`. The actual payout is

```text
D = min(D_legacy, max(0, E), max(0, C − P))
```

This enforces two independent ceilings:

1. **Book-equity floor**: an owner distribution cannot make positive equity negative.
2. **Zero-salvage creditor reserve**: all currently outstanding principal stays protected by liquid cash before a dividend. This avoids relying on inventory or capital that liquidation would immediately scrap.

For example, a firm with cash 100, inventory carrying value 1,000 and loan principal 80 may distribute at most **20**, regardless of higher reported earnings. An insolvent firm with cash 150 and principal 200 distributes **zero**.

The policy is implemented as a deterministic, side-effect-free integer function (`src/civitas/dividend_policy.py`), called immediately before the existing owner transfer loop. It consumes no random numbers and writes no new asset or account type.

## Compatibility and limitations

- **Default/legacy scenarios:** unchanged, because `firm_lifecycle_enabled` defaults to false. Their historical scenario hashes, metric schema, and payout formula are retained.
- **Lifecycle-enabled scenarios:** guard always applies; no separate toggles or hidden automatic selection.
- **Positive but illiquid firms:** may distribute nothing, even if they have positive book equity. This is intentional under current zero salvage, but could be too conservative under real collateral or sale markets.
- **Principal, not interest:** the present credit contracts model zero-interest principal only. Creditor hierarchy, wages owed, tax arrears, legal priorities, escrow, and asset market liquidity are not represented.
- **Time horizon:** all outstanding principal is reserved, regardless of maturity. The rule is an experimental safety invariant, not an optimized dividend policy.
- **Book values:** asset values are historical cost and cannot be interpreted as liquidation recovery values.

## Verification evidence and boundaries

The source patch was executed against the previous reproducible pre-lifecycle source archive with **255 passing tests** (the archive's 247 pre-lifecycle regressions plus 8 new tests). The integration stress test creates corresponding lender claims and borrower principal liabilities, then verifies positive earnings are not paid to owners under insufficient creditor coverage. Other tests cover exact caps, zero/negative equity, type failures, replay alignment, and legacy-mode parity.

The newer GitHub lifecycle checkpoint already reports 260 tests from its own prior verification, but that prior count is not proof that the **combined** branch with this patch has run all tests. A full combined-tree regression is a remaining verification gate if CI or a current checkout is available.

The change adds no empirical calibration and makes no claim that suppressing dividends improves production or welfare.

## Follow-up

Before relaxing this conservative reserve, implement bilateral physical title transfers for real liquidation salvage sales, explicit creditor priority, and independently audited cash recovery. Only then test alternative payouts under matched seeds over multiple horizons; do not choose a rule based solely on higher production.
