"""Independent per-firm physical stock and historical-cost event replay.

Only trace-enabled periods are eligible for audit. Production, consumption,
capital conversion, and resource regeneration are tracked as distinct physical
flows. This module does not call engine production or cost-allocation helpers.
Prices/cash are cross-checked against the independent monetary transfer trace.
It is not a full standards-compliant balance sheet or a goods-title ledger.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from civitas.engine import Period
    from civitas.model import Scenario
    from civitas.state import State

MAX_I64 = 2**63 - 1


class PhysicalAuditError(AssertionError):
    """A recorded physical event or associated asset movement is inconsistent."""


@dataclass(frozen=True)
class PhysicalOpening:
    inventory: tuple[int, ...]
    inventory_basis: tuple[int, ...]
    capital: tuple[int, ...]
    capital_basis: tuple[int, ...]
    prices: tuple[int, ...]
    resource: int


@dataclass(frozen=True)
class PhysicalReport:
    physical_event_count: int
    production_units: int
    consumption_units: int
    resource_extracted_units: int
    resource_regenerated_units: int
    capital_added_units: int
    capital_depreciated_units: int
    inventory_basis_cents: int
    capital_basis_cents: int


def capture_physical_opening(state: State) -> PhysicalOpening:
    return PhysicalOpening(
        inventory=tuple(map(int, state.inventory)),
        inventory_basis=tuple(map(int, state.firm_inventory_basis_cents)),
        capital=tuple(map(int, state.firm_capital)),
        capital_basis=tuple(map(int, state.firm_capital_basis_cents)),
        prices=tuple(map(int, state.prices)),
        resource=int(state.resource),
    )


def _integer(event: dict, key: str, *, positive: bool = False) -> int:
    value = event[key]
    if type(value) is not int or value < (1 if positive else 0) or value > MAX_I64:
        raise PhysicalAuditError(f"invalid physical {key}")
    return value


def audit_physical_period(opening: PhysicalOpening, closing: State, period: Period,
                          scenario: Scenario) -> PhysicalReport:
    if not closing.trace_enabled:
        raise PhysicalAuditError("physical audit requires transaction trace")
    events = period.physical_transactions
    if type(events) is not list:
        raise PhysicalAuditError("missing physical event stream")
    nf = len(opening.inventory)
    if not all(len(x) == nf for x in (opening.inventory_basis, opening.capital,
                                     opening.capital_basis, closing.inventory,
                                     closing.firm_inventory_basis_cents,
                                     closing.firm_capital, closing.firm_capital_basis_cents)):
        raise PhysicalAuditError("firm dimensions disagree")
    if nf != len(scenario.sectors) * scenario.firms_per_sector:
        raise PhysicalAuditError("scenario firm count differs")
    inventory, inv_basis = list(opening.inventory), list(opening.inventory_basis)
    capital, cap_basis = list(opening.capital), list(opening.capital_basis)
    resource = opening.resource
    if len(opening.prices) != nf:
        raise PhysicalAuditError("opening price list differs from firm count")
    produced = consumed = extracted = regenerated = added = depreciated = 0
    prod_sectors = [0] * len(scenario.sectors)
    consumption_sectors = [0] * len(scenario.sectors)
    sales = Counter()
    purchases = Counter()
    expenses = Counter()
    production_basis_by_firm = Counter()
    consumer_cogs = capital_cogs = depreciation_cogs = 0
    produced_firms = set()
    last_stage = -1
    stage = {"depreciate": 0, "regenerate": 1, "manufacture": 2,
             "consumer_sale": 3, "convert_capital": 4}
    for i, event in enumerate(events):
        if type(event) is not dict or type(event.get("kind")) is not str:
            raise PhysicalAuditError(f"physical event {i}: invalid schema")
        kind = event["kind"]
        fields = {
            "regenerate": {"kind", "units"},
            "depreciate": {"kind", "firm", "units", "basis_cents"},
            "manufacture": {"kind", "firm", "units", "resource_units", "basis_cents"},
            "consumer_sale": {"kind", "firm", "household", "units", "basis_cents", "price_cents"},
            "convert_capital": {"kind", "supplier", "buyer", "units", "basis_cents", "capital_cost_cents", "price_cents"},
        }
        if kind not in fields or set(event) != fields[kind]:
            raise PhysicalAuditError(f"physical event {i}: unknown kind or unexpected fields")
        if stage[kind] < last_stage:
            raise PhysicalAuditError("physical event sequence violates period stage order")
        last_stage = stage[kind]
        def firm(key: str) -> int:
            v = _integer(event, key)
            if v >= nf:
                raise PhysicalAuditError(f"physical event {i}: firm out of bounds")
            return v
        units = _integer(event, "units", positive=True)
        if kind == "regenerate":
            if resource > MAX_I64 - units:
                raise PhysicalAuditError("resource regeneration overflows signed-int64")
            resource += units
            regenerated += units
            continue
        if kind == "depreciate":
            f = firm("firm")
            basis = _integer(event, "basis_cents")
            if units > capital[f] or basis > cap_basis[f]:
                raise PhysicalAuditError("depreciation exceeds owned stock")
            if basis != cap_basis[f] * units // capital[f]:
                raise PhysicalAuditError("depreciation historical-cost allocation incorrect")
            capital[f] -= units
            cap_basis[f] -= basis
            depreciated += units
            depreciation_cogs += basis
        elif kind == "manufacture":
            f = firm("firm")
            sec = f // scenario.firms_per_sector
            resource_units = _integer(event, "resource_units")
            basis = _integer(event, "basis_cents")
            if resource_units != units * scenario.sectors[sec].resource_per_unit:
                raise PhysicalAuditError("manufacturing resource intensity differs from scenario")
            if resource_units > resource:
                raise PhysicalAuditError("manufacture consumes nonexistent resource")
            if f in produced_firms:
                raise PhysicalAuditError("duplicate production event for firm")
            produced_firms.add(f)
            inventory[f] += units
            inv_basis[f] += basis
            resource -= resource_units
            extracted += resource_units
            produced += units
            prod_sectors[sec] += units
            production_basis_by_firm[f] += basis
            if scenario.resource_extraction_fee_cents_per_unit and resource_units:
                expenses[f] += resource_units * scenario.resource_extraction_fee_cents_per_unit
        elif kind == "consumer_sale":
            f = firm("firm")
            h = _integer(event, "household")
            basis = _integer(event, "basis_cents")
            cents = _integer(event, "price_cents", positive=True)
            if units != 1 or h >= len(closing.household_cash):
                raise PhysicalAuditError("consumer sale requires one unit and valid household")
            if inventory[f] < units or inv_basis[f] < basis:
                raise PhysicalAuditError("consumer sale exceeds firm stock/cost")
            if basis != inv_basis[f] * units // inventory[f]:
                raise PhysicalAuditError("sale historical-cost allocation incorrect")
            if cents != opening.prices[f]:
                raise PhysicalAuditError("sale price differs from period opening quote")
            inventory[f] -= units
            inv_basis[f] -= basis
            consumed += units
            consumption_sectors[f // scenario.firms_per_sector] += units
            consumer_cogs += basis
            sales[(h, f, cents)] += 1
        elif kind == "convert_capital":
            supplier, buyer = firm("supplier"), firm("buyer")
            cost = _integer(event, "basis_cents")
            acquisition = _integer(event, "capital_cost_cents")
            price = _integer(event, "price_cents", positive=True)
            if supplier // scenario.firms_per_sector != next(
                    (j for j,s in enumerate(scenario.sectors) if s.name == scenario.capital_input_sector), -1):
                raise PhysicalAuditError("capital conversion requires capital-input supplier")
            if inventory[supplier] < units or inv_basis[supplier] < cost:
                raise PhysicalAuditError("conversion exceeds seller inventory/cost")
            if cost != inv_basis[supplier] * units // inventory[supplier]:
                raise PhysicalAuditError("capital-goods historical-cost allocation incorrect")
            if price != units * opening.prices[supplier]:
                raise PhysicalAuditError("capital-goods price differs from period opening quote")
            if not scenario.capital_enabled:
                raise PhysicalAuditError("capital conversion requires enabled capital")
            if scenario.cost_basis_accounting_enabled:
                if acquisition != (price if supplier != buyer else cost):
                    raise PhysicalAuditError("capital asset basis contradicts acquisition")
            elif cost or acquisition:
                raise PhysicalAuditError("disabled cost accounting cannot invent asset basis")
            inventory[supplier] -= units
            inv_basis[supplier] -= cost
            capital[buyer] += units
            cap_basis[buyer] += acquisition
            added += units
            if buyer != supplier:
                purchases[(buyer, supplier, price)] += 1
                capital_cogs += cost
        else:
            raise PhysicalAuditError(f"unexpected physical event {i}")
        if any(v < 0 or v > MAX_I64 for v in (resource, inventory[f], inv_basis[f], capital[f], cap_basis[f])):
            raise PhysicalAuditError("replayed stocks overflow or become negative")

    actual = (tuple(map(int, closing.inventory)), tuple(map(int, closing.firm_inventory_basis_cents)),
              tuple(map(int, closing.firm_capital)), tuple(map(int, closing.firm_capital_basis_cents)),
              int(closing.resource))
    reconstructed = (tuple(inventory), tuple(inv_basis), tuple(capital), tuple(cap_basis), resource)
    if actual != reconstructed:
        labels = ("finished-goods inventory", "inventory cost basis", "productive capital",
                  "capital cost basis", "natural resources")
        for label, observed, expected in zip(labels, actual, reconstructed):
            if observed != expected:
                raise PhysicalAuditError(f"{label}: physical event replay disagrees with closing state")

    monetary_sales = Counter((tx["source_id"], tx["destination_id"], tx["cents"])
                             for tx in period.transactions if tx.get("reason") == "sale")
    monetary_capital = Counter((tx["source_id"], tx["destination_id"], tx["cents"])
                               for tx in period.transactions if tx.get("reason") == "capital_purchase")
    monetary_fees = Counter((tx["source_id"], tx["cents"])
                            for tx in period.transactions if tx.get("reason") == "resource_fee")
    if sales != monetary_sales or purchases != monetary_capital:
        raise PhysicalAuditError("physical sales/capital conversions disagree with cash settlement")
    # One extraction fee per producing firm, rather than per individual item.
    fees = {f: cents for f, cents in expenses.items() if cents > 0}
    if Counter({(f, cents): 1 for f, cents in fees.items()}) != monetary_fees:
        raise PhysicalAuditError("resource extraction charges differ from monetary ledger")
    wages = Counter()
    for tx in period.transactions:
        if tx.get("reason") == "wages":
            wages[tx["source_id"]] += tx["cents"]
    if scenario.cost_basis_accounting_enabled:
        for f in range(nf):
            if production_basis_by_firm[f] != (wages[f] + expenses[f] if f in produced_firms else 0):
                raise PhysicalAuditError("manufacturing cost basis disagrees with wage and resource expense")
    else:
        if any(x["basis_cents"] for x in events if "basis_cents" in x) or any(
                x["capital_cost_cents"] for x in events if "capital_cost_cents" in x):
            raise PhysicalAuditError("disabled cost basis recorded nonzero book value")
    expected_metrics = {
        "production_units": produced, "consumption_units": consumed,
        "resource_extracted": extracted, "resource_regenerated": regenerated,
        "resource_stock": resource, "capital_added_units": added,
        "capital_depreciated_units": depreciated,
        "capital_stock_units": sum(capital),
        "firm_inventory_historical_cost_cents": sum(inv_basis),
        "firm_capital_historical_cost_cents": sum(cap_basis),
        "firm_consumer_cogs_cents": consumer_cogs,
        "firm_capital_goods_cogs_cents": capital_cogs,
        "firm_book_depreciation_cents": depreciation_cogs,
        "firm_resource_input_fees_cents": sum(expenses.values()),
        "firm_uncapitalized_labor_cost_cents": (
            sum(wages[f] for f in range(nf) if f not in produced_firms)
            if scenario.cost_basis_accounting_enabled else 0),
        "capital_investment_goods_value_cents": sum(
            event["price_cents"] for event in events if event["kind"] == "convert_capital"),
    }
    for key, value in expected_metrics.items():
        if type(period.metrics.get(key)) is not int or period.metrics[key] != value:
            raise PhysicalAuditError(f"physical metric {key} differs from replay")
    for j, sec in enumerate(scenario.sectors):
        if (period.metrics["production_by_sector"].get(sec.name) != prod_sectors[j] or
                period.metrics["consumption_by_sector"].get(sec.name) != consumption_sectors[j]):
            raise PhysicalAuditError("sector production/consumption differs from replay")
    return PhysicalReport(len(events), produced, consumed, extracted, regenerated, added,
                          depreciated, sum(inv_basis), sum(cap_basis))
