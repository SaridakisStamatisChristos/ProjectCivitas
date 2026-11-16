"""Conservative dividend solvency gate for lifecycle-enabled firms.

The current liquidator scraps all noncash assets at zero salvage. Therefore,
allowing distributions against noncash asset book value could divert scarce
liquid cash from contractual principal creditors. This policy reserves all
outstanding loan principal in cash, *as well as* enforcing positive book equity.
It is deliberately stronger than a conventional corporate dividend test and
must be revisited when real collateral recovery/asset sales are implemented.
"""
from __future__ import annotations


def creditor_protected_dividend(
    *, proposed_cents: int, cash_cents: int, inventory_basis_cents: int,
    capital_basis_cents: int, loan_principal_cents: int,
) -> int:
    """Return largest safe dividend in integer cents, without state mutation.

    D <= max(0, equity), D <= max(0, cash - loan principal),
    where equity = cash + historical-cost tangible assets - principal.
    A zero-salvage liquidator motivates full principal cash reservation.
    """
    values = (proposed_cents, cash_cents, inventory_basis_cents,
              capital_basis_cents, loan_principal_cents)
    if any(type(value) is not int or value < 0 for value in values):
        raise ValueError("dividend policy requires nonnegative integer-cent inputs")
    equity = cash_cents + inventory_basis_cents + capital_basis_cents - loan_principal_cents
    return min(proposed_cents, max(0, equity), max(0, cash_cents - loan_principal_cents))
