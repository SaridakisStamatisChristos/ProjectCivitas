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
    # Market-mechanism ablations; defaults preserve the historical algorithm.
    buyer_seller_rule: str = "mixed"  # mixed | cheapest | favorite
    hiring_expectation_rule: str = "adaptive"  # adaptive | stationary | blended
    rationing_order_rule: str = "random"  # random | household_id
    # Experimental access topology; false/false preserves fully open markets.
    # Regions are immutable labels derived from existing household/firm IDs.
    market_regions: int = 1
    restrict_household_sales: bool = False
    restrict_labor_hiring: bool = False
    # v0.2 experimental access-map and quote-information controls.
    # The defaults reproduce every historical scenario exactly.
    household_region_assignment: str = "modulo"  # modulo | balanced_shuffle
    region_assignment_seed: int = 0
    buyer_price_information: str = "full"  # full | two_quotes
    initial_resource: int = 500_000
    resource_capacity: int = 600_000
    regeneration_rate: float = 0.025
    output_inventory_buffer: float = 0.05
    price_adjustment: float = 0.02
    price_update_rule: str = "inventory"  # inventory | affordability_guard
    price_affordability_floor: float = 0.25  # minimum end-period affordable household share for a price increase
    price_floor_cents: int = 1
    transaction_trace: bool = False
    automation_base: float = 0.0
    automation_shock_step: int | None = None
    automation_shock_increase: float = 0.0
    # v0.2 development slice: physical capital is optional for v0.1 parity.
    capital_enabled: bool = False
    initial_capital_units_per_firm: int = 0
    capital_output_per_unit: int = 2
    capital_depreciation_rate: float = 0.04
    capital_investment_budget_share: float = 0.15
    capital_target_buffer: float = 0.10
    capital_input_sector: str = "goods"
    # Opt-in moving-average historical cost and firm book-equity accounting.
    cost_basis_accounting_enabled: bool = False
    # Optional fee transfers firms -> government for physical extraction.
    # Resource units stay in the separate physical conservation ledger.
    resource_extraction_fee_cents_per_unit: int = 0
    # No credit creation: loans transfer existing savings directly to firms.
    credit_enabled: bool = False
    credit_max_principal_per_firm_cents: int = 200_000
    credit_term_periods: int = 4
    credit_repayment_fraction: float = 0.25
    credit_firm_cash_reserve_cents: int = 100_000
    credit_lender_savings_share: float = 0.5
    # Household balances are separate, noninterest-bearing accounts. No credit.
    household_savings_rate: float = 0.0
    household_liquidity_floor_cents: int = 0
    savings_emergency_food_enabled: bool = True
    savings_essential_sector: str = "food"
    # None retains exact legacy initialization; populated by World Genesis only.
    world_genesis: dict[str, Any] | None = None
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
        data = asdict(self)
        # Exact legacy config digests/checkpoint JSON must stay unchanged for
        # every pre-Genesis scenario. Omit the optional field when disabled.
        if data["world_genesis"] is None:
            del data["world_genesis"]
        return {"schema_version": 1, **data}

    def validate(self) -> None:
        from civitas.world_genesis import validate_resolved
        validate_resolved(self.world_genesis, self)
        for name in ("population", "steps", "seed", "initial_household_cash_cents",
                     "initial_firm_cash_cents", "initial_resource", "resource_capacity",
                     "initial_capital_units_per_firm", "household_liquidity_floor_cents",
                     "region_assignment_seed", "resource_extraction_fee_cents_per_unit",
                     "credit_max_principal_per_firm_cents", "credit_firm_cash_reserve_cents"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        for name in ("household_size", "firms_per_sector", "price_floor_cents",
                     "capital_output_per_unit", "credit_term_periods"):
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
                     "automation_base", "automation_shock_increase",
                     "capital_depreciation_rate", "capital_investment_budget_share",
                     "capital_target_buffer", "price_affordability_floor", "household_savings_rate",
                     "credit_repayment_fraction", "credit_lender_savings_share"):
            value = getattr(self, name)
            if not isinstance(value, (float, int)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0,1]")
        if type(self.savings_emergency_food_enabled) is not bool:
            raise ValueError("savings_emergency_food_enabled must be boolean")
        if not isinstance(self.savings_essential_sector, str) or not self.savings_essential_sector:
            raise ValueError("savings_essential_sector must be nonempty string")
        if type(self.cost_basis_accounting_enabled) is not bool:
            raise ValueError("cost_basis_accounting_enabled must be boolean")
        if type(self.credit_enabled) is not bool:
            raise ValueError("credit_enabled must be boolean")
        if self.credit_enabled and not (self.cost_basis_accounting_enabled and self.capital_enabled):
            raise ValueError("credit requires both capital and historical-cost accounting")
        if self.credit_enabled and self.credit_max_principal_per_firm_cents <= 0:
            raise ValueError("credit requires a positive principal limit")
        if type(self.capital_enabled) is not bool:
            raise ValueError("capital_enabled must be boolean")
        if not self.capital_enabled and self.initial_capital_units_per_firm:
            raise ValueError("capital endowment requires capital_enabled")
        if type(self.capital_input_sector) is not str or not self.capital_input_sector:
            raise ValueError("capital_input_sector must be nonempty string")
        for field_name, choices in (("buyer_seller_rule", {"mixed", "cheapest", "favorite"}),
                                    ("hiring_expectation_rule", {"adaptive", "stationary", "blended"}),
                                    ("price_update_rule", {"inventory", "affordability_guard"}),
                                    ("rationing_order_rule", {"random", "household_id"})):
            if type(getattr(self, field_name)) is not str or getattr(self, field_name) not in choices:
                raise ValueError(f"{field_name} must be one of {sorted(choices)}")
        if type(self.market_regions) is not int or self.market_regions < 1:
            raise ValueError("market_regions must be a positive integer")
        if self.firms_per_sector % self.market_regions != 0:
            raise ValueError("market_regions must divide firms_per_sector exactly")
        if self.household_region_assignment not in {"modulo", "balanced_shuffle"} or type(self.household_region_assignment) is not str:
            raise ValueError("household_region_assignment must be modulo or balanced_shuffle")
        if self.buyer_price_information not in {"full", "two_quotes"} or type(self.buyer_price_information) is not str:
            raise ValueError("buyer_price_information must be full or two_quotes")
        for field_name in ("restrict_household_sales", "restrict_labor_hiring"):
            if type(getattr(self, field_name)) is not bool:
                raise ValueError(f"{field_name} must be boolean")
        if type(self.transaction_trace) is not bool:
            raise ValueError("transaction_trace must be boolean")
        if self.initial_resource > self.resource_capacity:
            raise ValueError("initial_resource cannot exceed resource_capacity")
        # NumPy arrays/checkpoints use signed int64; refuse initial states that
        # could wrap *before* the first accounting invariant is evaluated.
        i64max = (1 << 63) - 1
        n_households = (self.population + self.household_size - 1) // self.household_size
        n_firms = self.firms_per_sector * len(self.sectors)
        initial_money = (n_households * self.initial_household_cash_cents +
                         n_firms * self.initial_firm_cash_cents)
        initial_capital = n_firms * (self.initial_capital_units_per_firm if self.capital_enabled else 0)
        for label, value in (("initial_total_money", initial_money),
                             ("initial_capital_stock", initial_capital),
                             ("resource_capacity", self.resource_capacity),
                             ("initial_resource", self.initial_resource),
                             ("household_liquidity_floor_cents", self.household_liquidity_floor_cents),
                             ("population", self.population),
                             ("initial_household_cash_cents", self.initial_household_cash_cents),
                             ("initial_firm_cash_cents", self.initial_firm_cash_cents),
                             ("resource_extraction_fee_cents_per_unit", self.resource_extraction_fee_cents_per_unit),
                             ("credit_max_principal_per_firm_cents", self.credit_max_principal_per_firm_cents),
                             ("credit_firm_cash_reserve_cents", self.credit_firm_cash_reserve_cents)):
            if value > i64max:
                raise ValueError(f"{label} exceeds signed int64 storage")
        if self.cost_basis_accounting_enabled and self.capital_enabled:
            k = next((q for q in self.sectors if q.name == self.capital_input_sector), None)
            if k is not None and (k.price_cents * self.initial_capital_units_per_firm * n_firms > i64max):
                raise ValueError("initial historical capital cost basis exceeds signed int64")
        if self.automation_base + self.automation_shock_increase > 1:
            raise ValueError("automation adoption must remain in [0,1]")
        if self.automation_shock_step is not None and (type(self.automation_shock_step) is not int or self.automation_shock_step < 0):
            raise ValueError("automation_shock_step must be a nonnegative step index")
        if not self.sectors or len({s.name for s in self.sectors}) != len(self.sectors):
            raise ValueError("nonempty sectors with unique names required")
        if self.household_savings_rate and self.savings_emergency_food_enabled and self.savings_essential_sector not in {s.name for s in self.sectors}:
            raise ValueError("savings_essential_sector must identify a sector when savings enabled")
        if self.capital_enabled and self.capital_input_sector not in {s.name for s in self.sectors}:
            raise ValueError("capital_input_sector must identify an existing goods sector")
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
            if (sector.price_cents > i64max or sector.wage_cents > i64max or
                    sector.resource_per_unit > i64max):
                raise ValueError("sector numeric parameter exceeds signed int64")
