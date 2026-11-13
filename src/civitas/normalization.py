"""Exact-ratio population scaling for controlled synthetic-economy experiments.

This only controls *initial* quantities; it does not assert scale invariance
of trajectories or normalize market frictions, random network effects, etc.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction

from civitas.model import Scenario


@dataclass(frozen=True)
class InitialEndowmentAudit:
    population: int
    firms: int
    households: int
    firms_per_person: Fraction
    household_money_per_person: Fraction
    firm_money_per_person: Fraction
    initial_resource_per_person: Fraction
    resource_capacity_per_person: Fraction
    initial_capital_per_person: Fraction
    # Per-firm distinct-owner count rounds to an integer; not an exact density constraint.
    realized_ownership_fraction_per_firm: Fraction


def audit_initial_endowments(scenario: Scenario) -> InitialEndowmentAudit:
    """Record exact starting-stock ratios (not trajectory outcome metrics)."""
    scenario.validate()
    if scenario.population == 0:
        raise ValueError("per-person audit is undefined for zero population")
    n = scenario.population
    h = (n + scenario.household_size - 1) // scenario.household_size
    nf = len(scenario.sectors) * scenario.firms_per_sector
    return InitialEndowmentAudit(
        population=n, firms=nf, households=h,
        firms_per_person=Fraction(nf, n),
        household_money_per_person=Fraction(h * scenario.initial_household_cash_cents, n),
        firm_money_per_person=Fraction(nf * scenario.initial_firm_cash_cents, n),
        initial_resource_per_person=Fraction(scenario.initial_resource, n),
        resource_capacity_per_person=Fraction(scenario.resource_capacity, n),
        initial_capital_per_person=Fraction(
            nf * (scenario.initial_capital_units_per_firm if scenario.capital_enabled else 0), n),
        realized_ownership_fraction_per_firm=Fraction(
            min(h, max(1, round(h * scenario.ownership_fraction))), h),
    )


def scale_population_exact(reference: Scenario, target_population: int,
                           *, name: str | None = None, seed: int | None = None) -> Scenario:
    """Change population while exactly preserving firm density and per-capita stocks.

    Firm count is integral per sector. Resource stocks and capacities are
    integral physical units. Inexact ratios are rejected rather than silently
    rounded. Household size must divide both populations for equal per-capita
    household cash. Per-firm cash and capital are held constant.
    """
    reference.validate()
    if type(target_population) is not int or target_population <= 0:
        raise ValueError("target_population must be a positive integer")
    if reference.population <= 0:
        raise ValueError("reference population must be positive")
    if (reference.population % reference.household_size or
            target_population % reference.household_size):
        raise ValueError("population must be a whole number of reference households")
    n0, n1 = reference.population, target_population

    def exact(value: int, label: str) -> int:
        numerator = value * n1
        result, remainder = divmod(numerator, n0)
        if remainder:
            raise ValueError(f"{label} cannot be exactly scaled as integer units")
        return result

    firms_per_sector = exact(reference.firms_per_sector, "firms_per_sector")
    if not firms_per_sector:
        raise ValueError("target would have zero firms per sector; increase target")
    scaled = replace(
        reference,
        name=name or f"{reference.name}_n{n1}",
        population=n1,
        seed=reference.seed if seed is None else seed,
        firms_per_sector=firms_per_sector,
        initial_resource=exact(reference.initial_resource, "initial_resource"),
        resource_capacity=exact(reference.resource_capacity, "resource_capacity"),
    )
    scaled.validate()
    a = audit_initial_endowments(reference)
    b = audit_initial_endowments(scaled)
    for field in ("firms_per_person", "household_money_per_person", "firm_money_per_person",
                  "initial_resource_per_person", "resource_capacity_per_person", "initial_capital_per_person"):
        if getattr(a, field) != getattr(b, field):
            raise AssertionError(f"failed initial normalization: {field}")
    return scaled
