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
