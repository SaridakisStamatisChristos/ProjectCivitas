"""Pure, inspectable alternatives for price and labor-demand feedback.

Designed for analytical toy cases, independent of the monetary ledger.
The historical default is mathematically unchanged. Prices are integer cents.
"""
from __future__ import annotations

import math


def expected_sales(*, rule: str, period: int, sector_household_demand: float,
                   firm_last_sales: int, sector_last_unmet_per_firm: float) -> float:
    """Units of demand anticipated by a firm before hiring.

    Stationary baseline B = households * demand_probability / firms_in_sector.
    Legacy adaptive A = max(B/4, prior sales + prior sector-unmet/firms).
    Blended is (B + A)/2, after period zero. No new RNG consumption.
    """
    if rule not in {"adaptive", "stationary", "blended"}:
        raise ValueError("invalid hiring expectation rule")
    if period == 0 or rule == "stationary":
        return sector_household_demand
    adaptive = max(sector_household_demand * 0.25,
                   firm_last_sales + sector_last_unmet_per_firm)
    if rule == "adaptive":
        return adaptive
    return (sector_household_demand + adaptive) / 2


def updated_price(*, current: int, stock: int, units_sold: int,
                  excess_threshold: int, adjustment: float, floor: int) -> int:
    """Unmodified historical price transition; affordability guard is applied by caller."""
    if stock == 0 and units_sold > 0:
        return max(floor, math.ceil(current * (1 + adjustment)))
    if stock > excess_threshold:
        return max(floor, math.floor(current * (1 - adjustment)))
    return current
