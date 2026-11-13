"""Exact integer-cent carrying-cost allocation for synthetic inventories.

This reference cost model uses one pooled, moving-average cost basis per firm.
For a withdrawal of `units` physical goods, cents are allocated in integer
proportion, with the full residual assigned when the final unit is removed.
There is no floating arithmetic, market revaluation or invisible cash flow.
"""
from __future__ import annotations

I64_MAX = (1 << 63) - 1


def allocated_basis(*, stock_units: int, stock_cost_cents: int, withdrawn_units: int) -> int:
    """Return consumed historical cost, without mutating caller's inventory."""
    for name, value in (("stock_units", stock_units),
                        ("stock_cost_cents", stock_cost_cents),
                        ("withdrawn_units", withdrawn_units)):
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a nonnegative integer")
    if withdrawn_units > stock_units:
        raise ValueError("cannot remove more units than held")
    if stock_units == 0:
        if stock_cost_cents != 0:
            raise ValueError("zero physical stock cannot carry nonzero cost basis")
        return 0
    if withdrawn_units == stock_units:
        return stock_cost_cents
    return stock_cost_cents * withdrawn_units // stock_units


def checked_add_i64(old: int, added: int) -> int:
    """Reject overflow before writing back to a NumPy int64 account."""
    if old < 0 or added < 0 or old + added > I64_MAX:
        raise OverflowError("historical cost basis cannot fit signed int64")
    return old + added
