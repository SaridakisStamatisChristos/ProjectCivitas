"""Versioned scenario definitions and strict validation.

All monetary quantities use integer cents; physical quantities use integer units.
A model time step is one abstract production-and-consumption period, not a
calibrated calendar month.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Sector:
    name: str
    demand_probability: float
    price_cents: int
    wage_cents: int
    productivity: float
    resource_per_unit: int

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> Sector:
        return Sector(**raw)


@dataclass(frozen=True)
class Scenario:
    name: str
    population: int = 10000
    household_size: int = 4
    steps: int = 24
    seed: int = 42
    firms_per_sector: int = 2
    initial_household_cash_cents: int = 15000
    initial_firm_cash_cents: int = 2_000_000
    labor_participation: float = 0.78
    tax_rate: float = 0.0
    redistribution_share: float = 0.90
    transfer_recipient_fraction: float = 0.30
    dividend_share: float = 0.65
    ownership_fraction: float = 0.08
    buyer_cheapest_probability: float = 0.75
    initial_resource: int = 500_000
    resource_capacity: int = 600_000
    regeneration_rate: float = 0.025
    output_inventory_buffer: float = 0.05
    price_adjustment: float = 0.02
    price_floor_cents: int = 1
    automation_base: float = 0.0
    automation_shock_step: int | None = None
    automation_shock_increase: float = 0.0
    sectors: tuple[Sector, ...] = field(default_factory=lambda: (
        Sector("food", 1.0, 1500, 1400, 1.25, 2),
        Sector("goods", 0.55, 2500, 2300, 1.25, 3),
        Sector("services", 0.30, 4000, 3800, 1.25, 1),
    ))

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Scenario:
        allowed = set(cls.__dataclass_fields__)
        extra = set(raw) - allowed - {"schema_version"}
        if extra:
            raise ValueError(f"unknown scenario fields: {sorted(extra)}")
        if raw.get("schema_version", 1) != 1:
            raise ValueError("unsupported scenario schema_version")
        values = {k: v for k, v in raw.items() if k != "schema_version"}
        if "sectors" in values:
            values["sectors"] = tuple(Sector.from_dict(s) for s in values["sectors"])
        obj = cls(**values)
        obj.validate()
        return obj

    @classmethod
    def from_file(cls, path: str | Path) -> Scenario:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, **asdict(self)}

    def validate(self) -> None:
        for name in ("population", "steps", "seed", "initial_household_cash_cents",
                     "initial_firm_cash_cents", "initial_resource", "resource_capacity"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        for name in ("household_size", "firms_per_sector", "price_floor_cents"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("labor_participation", "tax_rate", "redistribution_share",
                     "transfer_recipient_fraction", "dividend_share", "ownership_fraction",
                     "buyer_cheapest_probability"):
            value = getattr(self, name)
            if not isinstance(value, (float, int)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0,1]")
        for name in ("regeneration_rate", "output_inventory_buffer", "price_adjustment",
                     "automation_base", "automation_shock_increase"):
            value = getattr(self, name)
            if not isinstance(value, (float, int)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0,1]")
        if self.initial_resource > self.resource_capacity:
            raise ValueError("initial_resource cannot exceed resource_capacity")
        if self.automation_base + self.automation_shock_increase > 1:
            raise ValueError("automation adoption must remain in [0,1]")
        if self.automation_shock_step is not None and (type(self.automation_shock_step) is not int or self.automation_shock_step < 0):
            raise ValueError("automation_shock_step must be a nonnegative step index")
        if not self.sectors or len({s.name for s in self.sectors}) != len(self.sectors):
            raise ValueError("nonempty sectors with unique names required")
        for sector in self.sectors:
            if not sector.name or not 0 <= sector.demand_probability <= 1:
                raise ValueError("invalid sector name/probability")
            if type(sector.price_cents) is not int or sector.price_cents < 1:
                raise ValueError("sector price_cents must be a positive integer")
            if type(sector.wage_cents) is not int or sector.wage_cents < 0:
                raise ValueError("sector wage_cents must be nonnegative")
            if not 0 < sector.productivity <= 100 or not isinstance(sector.productivity, (int, float)):
                raise ValueError("sector productivity must be in (0,100]")
            if type(sector.resource_per_unit) is not int or sector.resource_per_unit < 1:
                raise ValueError("sector resource_per_unit must be a positive integer")
