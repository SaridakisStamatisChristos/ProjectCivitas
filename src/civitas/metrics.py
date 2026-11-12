"""Transparent distribution statistics: unweighted household Gini."""
from __future__ import annotations
import numpy as np


def gini(values: np.ndarray) -> float | None:
    """Gini of nonnegative monetary income/wealth; zero total -> undefined."""
    x = np.sort(np.asarray(values, dtype=np.float64))
    n = len(x)
    if n == 0 or float(x.sum()) <= 0:
        return None
    if (x < 0).any():
        raise ValueError("Gini requires nonnegative measurements")
    return float((2.0 * np.dot(np.arange(1, n + 1), x) / (n * x.sum())) - (n + 1) / n)


def household_equity_values(state, scenario) -> np.ndarray:
    """Allocate model-marked firm equity equally among registered owners.

    No liabilities, stock exchange or market-cap valuation exists. Firm assets
    are cash, merchandise quoted at own posted price, and capital at the
    lowest current posted quote in the capital input sector. Firm capitalization
    is a modeling convention, not conserved financial wealth.
    """
    wealth = np.zeros(len(state.household_cash), dtype=np.int64)
    if not wealth.size:
        return wealth
    capital_price = 0
    if scenario.capital_enabled:
        k = next(i for i, sec in enumerate(scenario.sectors)
                 if sec.name == scenario.capital_input_sector)
        lo = k * scenario.firms_per_sector
        capital_price = int(state.prices[lo:lo + scenario.firms_per_sector].min())
    for f, owners in enumerate(state.firm_owner_households):
        if not len(owners):
            continue
        value = (int(state.firm_cash[f]) + int(state.inventory[f]) * int(state.prices[f])
                 + int(state.firm_capital[f]) * capital_price)
        base, remainder = divmod(value, len(owners))
        wealth[owners] += base
        if remainder:
            wealth[owners[:remainder]] += 1
    return wealth
