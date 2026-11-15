"""Exact book-value balance sheets and transaction-derived equity roll-forwards.

These statements use *historical cost* when enabled, not market valuations.
Natural resources have physical quantities but no monetary carrying value.
Savings are segregated household cash (not bank deposits); bilateral principal
is simultaneously a household receivable and a firm payable. Equity is the
residual of firm book assets minus loans, attributed exactly to registered
owners, including signed deficits (not a legal owner-liability claim).
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from typing import TYPE_CHECKING

from civitas.ledger_audit import OpeningLedger, audit_period
from civitas.physical_audit import PhysicalOpening, audit_physical_period

if TYPE_CHECKING:
    from civitas.model import Scenario
    from civitas.state import State
    from civitas.engine import Period

I64_MAX = (1 << 63) - 1


class BalanceSheetError(AssertionError):
    """Book balance, residual equity, or equity flow fails independent audit."""


@dataclass(frozen=True)
class BookSnapshot:
    step: int
    household_cash: tuple[int, ...]
    household_savings: tuple[int, ...]
    household_loan_assets: tuple[int, ...]
    household_equity: tuple[int, ...]
    firm_cash: tuple[int, ...]
    firm_inventory_basis: tuple[int, ...]
    firm_capital_basis: tuple[int, ...]
    firm_debt: tuple[int, ...]
    firm_equity: tuple[int, ...]
    owners: tuple[tuple[int, ...], ...]
    government_cash: int
    unowned_equity: int
    prices: tuple[int, ...]
    resource: int
    inventory_units: tuple[int, ...]
    capital_units: tuple[int, ...]

    def totals(self) -> dict[str, int]:
        household_money = sum(self.household_cash) + sum(self.household_savings)
        claim = sum(self.household_loan_assets)
        firm_money = sum(self.firm_cash)
        debt = sum(self.firm_debt)
        inventory = sum(self.firm_inventory_basis)
        capital = sum(self.firm_capital_basis)
        equity = sum(self.firm_equity)
        attributed = sum(self.household_equity)
        national = household_money + firm_money + self.government_cash + inventory + capital
        return {
            "step": self.step,
            "household_cash_cents": sum(self.household_cash),
            "household_savings_cents": sum(self.household_savings),
            "household_loan_assets_cents": claim,
            "household_book_equity_cents": attributed,
            "household_book_net_worth_cents": household_money + claim + attributed,
            "firm_cash_cents": firm_money,
            "firm_inventory_basis_cents": inventory,
            "firm_capital_basis_cents": capital,
            "firm_loan_liabilities_cents": debt,
            "firm_total_book_equity_cents": equity,
            "government_cash_cents": self.government_cash,
            "unowned_firm_equity_cents": self.unowned_equity,
            "total_money_cents": household_money + firm_money + self.government_cash,
            "national_book_net_worth_cents": national,
            "natural_resource_units_unvalued": self.resource,
        }

    def as_dict(self, *, details: bool = False) -> dict:
        result: dict = {"method": "historical-cost book residual, not market value",
                        "totals": self.totals()}
        if details:
            result["households"] = [
                {"id": h, "cash_cents": cash, "savings_cents": savings,
                 "loan_claim_cents": claims, "attributed_equity_cents": equity,
                 "book_net_worth_cents": cash + savings + claims + equity}
                for h, (cash, savings, claims, equity) in enumerate(zip(
                    self.household_cash, self.household_savings,
                    self.household_loan_assets, self.household_equity, strict=True))]
            result["firms"] = [
                {"id": f, "cash_cents": cash, "inventory_basis_cents": inv,
                 "capital_basis_cents": cap, "loan_liability_cents": debt,
                 "book_equity_cents": equity}
                for f, (cash, inv, cap, debt, equity) in enumerate(zip(
                    self.firm_cash, self.firm_inventory_basis, self.firm_capital_basis,
                    self.firm_debt, self.firm_equity, strict=True))]
        return result


def _exact_ints(values) -> tuple[int, ...]:
    return tuple(int(x) for x in values)


def _owner_residual(firm_equity: tuple[int, ...], owners, household_count: int):
    attributed = [0] * household_count
    unowned = 0
    if len(firm_equity) != len(owners):
        raise BalanceSheetError("owner map does not match firm count")
    for f, ids in enumerate(owners):
        registered = [int(h) for h in ids]
        if len(registered) != len(set(registered)) or any(
            type(h) is not int or h < 0 or h >= household_count for h in registered
        ):
            raise BalanceSheetError("invalid firm owner IDs")
        if not registered:
            unowned += firm_equity[f]
            continue
        # A signed deficit is allocated as a *book residual* only. This does not
        # impose personal legal liability on shareholders.
        base, remainder = divmod(firm_equity[f], len(registered))
        for h in registered:
            attributed[h] += base
        for h in registered[:remainder]:
            attributed[h] += 1
    return tuple(attributed), unowned


def capture_book_snapshot(state: State, scenario: Scenario) -> BookSnapshot:
    """Capture a fully detached, integer-exact sector balance sheet."""
    cash, inventory, capital, debts = (_exact_ints(state.firm_cash),
                                      _exact_ints(state.firm_inventory_basis_cents),
                                      _exact_ints(state.firm_capital_basis_cents),
                                      _exact_ints(state.firm_loan_liabilities_cents))
    if not all(len(v) == len(cash) for v in (inventory, capital, debts)):
        raise BalanceSheetError("invalid firm balance-sheet dimensions")
    hc, hs, claims = (_exact_ints(state.household_cash),
                      _exact_ints(state.household_savings),
                      _exact_ints(state.household_loan_assets_cents))
    if len(hc) != len(hs) or len(hc) != len(claims):
        raise BalanceSheetError("invalid household balance-sheet dimensions")
    if not scenario.cost_basis_accounting_enabled and (any(inventory) or any(capital)):
        raise BalanceSheetError("non-cost-accounting mode cannot carry book asset basis")
    all_assets = hc + hs + claims + cash + inventory + capital + debts
    if any(x < 0 or x > I64_MAX for x in all_assets) or state.gov_cash < 0:
        raise BalanceSheetError("negative or overflowing balance-sheet stock")
    if sum(claims) != sum(debts):
        raise BalanceSheetError("bilateral loans do not balance")
    equity = tuple(cash[i] + inventory[i] + capital[i] - debts[i] for i in range(len(cash)))
    allocated, unowned = _owner_residual(equity, state.firm_owner_households, len(hc))
    snapshot = BookSnapshot(
        step=int(state.step), household_cash=hc, household_savings=hs,
        household_loan_assets=claims, household_equity=allocated,
        firm_cash=cash, firm_inventory_basis=inventory, firm_capital_basis=capital,
        firm_debt=debts, firm_equity=equity,
        owners=tuple(tuple(int(h) for h in owner) for owner in state.firm_owner_households),
        government_cash=int(state.gov_cash),
        unowned_equity=unowned, prices=_exact_ints(state.prices),
        resource=int(state.resource), inventory_units=_exact_ints(state.inventory),
        capital_units=_exact_ints(state.firm_capital))
    check_book_snapshot(snapshot)
    return snapshot


def check_book_snapshot(snapshot: BookSnapshot) -> None:
    """Independent whole-system balance-sheet identities, without NumPy overflow."""
    t = snapshot.totals()
    if t["household_loan_assets_cents"] != t["firm_loan_liabilities_cents"]:
        raise BalanceSheetError("aggregate financial principal differs")
    for cash, inv, cap, debt, equity in zip(snapshot.firm_cash,
             snapshot.firm_inventory_basis, snapshot.firm_capital_basis,
             snapshot.firm_debt, snapshot.firm_equity, strict=True):
        if cash + inv + cap != debt + equity:
            raise BalanceSheetError("firm assets != liabilities + book equity")
    owned, unowned = _owner_residual(snapshot.firm_equity, snapshot.owners,
                                    len(snapshot.household_cash))
    if owned != snapshot.household_equity or unowned != snapshot.unowned_equity:
        raise BalanceSheetError("household equity allocation differs from owner registry")
    if (t["household_book_equity_cents"] + snapshot.unowned_equity !=
            t["firm_total_book_equity_cents"]):
        raise BalanceSheetError("household claims do not sum to firm equity")
    if (t["household_book_net_worth_cents"] + snapshot.government_cash +
            snapshot.unowned_equity != t["national_book_net_worth_cents"]):
        raise BalanceSheetError("consolidated net worth double-counted assets or debts")
    if t["national_book_net_worth_cents"] != (t["total_money_cents"] +
            t["firm_inventory_basis_cents"] + t["firm_capital_basis_cents"]):
        raise BalanceSheetError("national assets do not reconcile")


def audit_book_period(opening: BookSnapshot, closing: State,
                      period: Period, scenario: Scenario) -> dict[str, int]:
    """Reconstruct financial and physical accounts, then verify equity change.

    Uses *only recorded transaction events* to compute historical-cost earnings;
    it does not read the engine's internal revenue, dividend, or COGS arrays.
    Supports legacy cash-only book values, but earnings roll-forward is only
    meaningful when the explicit historical-cost option is enabled.
    """
    if not closing.trace_enabled or closing.step != opening.step + 1:
        raise BalanceSheetError("requires consecutive fully traced periods")
    check_book_snapshot(opening)
    if opening.owners != tuple(tuple(int(h) for h in owners)
                              for owners in closing.firm_owner_households):
        raise BalanceSheetError("firm ownership changed without a title-transfer ledger")
    # Independently replay cash, loan principal, resource/finished-goods and
    # asset cost-basis movements before reading the closing balance sheet.
    audit_period(OpeningLedger(opening.household_cash, opening.household_savings,
                 opening.firm_cash, (opening.government_cash,),
                 opening.household_loan_assets, opening.firm_debt), closing, period)
    audit_physical_period(PhysicalOpening(opening.inventory_units,
                 opening.firm_inventory_basis, opening.capital_units,
                 opening.firm_capital_basis, opening.prices, opening.resource),
                 closing, period, scenario)
    end = capture_book_snapshot(closing, scenario)
    t = end.totals()
    if t["total_money_cents"] != opening.totals()["total_money_cents"]:
        raise BalanceSheetError("period created or destroyed money")
    # Test each firm's net-worth identity using actual traced economic events.
    earnings = [0] * len(opening.firm_cash)
    dividend = [0] * len(earnings)
    defaults = [0] * len(earnings)
    wages = [0] * len(earnings)
    manufacturing_firms = set()
    if scenario.cost_basis_accounting_enabled:
        for event in period.physical_transactions:
            kind = event["kind"]
            if kind == "manufacture":
                manufacturing_firms.add(event["firm"])
            elif kind == "depreciate":
                earnings[event["firm"]] -= event["basis_cents"]
            elif kind == "firm_liquidation":
                earnings[event["firm"]] -= (event["inventory_basis_cents"] +
                                               event["capital_basis_cents"])
            elif kind == "consumer_sale":
                earnings[event["firm"]] -= event["basis_cents"]
            elif kind == "convert_capital" and event["supplier"] != event["buyer"]:
                earnings[event["supplier"]] -= event["basis_cents"]
    for event in period.transactions:
        reason, cents = event["reason"], event["cents"]
        if reason == "wages":
            wages[event["source_id"]] += cents
        elif reason == "sale":
            earnings[event["destination_id"]] += cents
        elif reason == "capital_purchase":
            earnings[event["destination_id"]] += cents
        elif reason in ("dividend", "firm_liquidation_distribution",
                        "firm_liquidation_escheat"):
            dividend[event["source_id"]] += cents
        elif reason == "firm_capital_contribution":
            earnings[event["destination_id"]] += cents
    for event in period.noncash_transactions:
        defaults[event["borrower_firm"]] += event["cents"]
    if scenario.cost_basis_accounting_enabled:
        for f in range(len(earnings)):
            if f not in manufacturing_firms:
                earnings[f] -= wages[f]
            expected = opening.firm_equity[f] + earnings[f] - dividend[f] + defaults[f]
            if expected != end.firm_equity[f]:
                raise BalanceSheetError(f"firm {f}: transaction-derived earnings do not reconcile equity")
    # Independent household cash+claim+ownership roll-forward. End-of-period
    # sale expenses consume household cash; savings moves and principal lending
    # are internal reallocations of a household's financial assets.
    net_household_flows = [0] * len(opening.household_cash)
    for event in period.transactions:
        reason, value = event["reason"], event["cents"]
        if reason in ("wages", "transfer", "dividend",
                      "firm_liquidation_distribution"):
            net_household_flows[event["destination_id"]] += value
        elif reason in ("wage_tax", "sale", "firm_capital_contribution"):
            net_household_flows[event["source_id"]] -= value
    losses: Counter[int] = Counter()
    for event in period.noncash_transactions:
        losses[event["lender_household"]] += event["cents"]
    for h in range(len(opening.household_cash)):
        own_delta = end.household_equity[h] - opening.household_equity[h]
        expected = (opening.household_cash[h] + opening.household_savings[h] +
                    opening.household_loan_assets[h] + opening.household_equity[h] +
                    net_household_flows[h] + own_delta - losses[h])
        actual = (end.household_cash[h] + end.household_savings[h] +
                  end.household_loan_assets[h] + end.household_equity[h])
        if expected != actual:
            raise BalanceSheetError(f"household {h}: financial/owner net-worth roll-forward differs")
    before = opening.totals()
    report = {"step": end.step, "households": len(end.household_cash),
            "firms": len(end.firm_cash),
            "book_equity_discrepancy_cents": 0,
            "household_book_net_worth_cents": t["household_book_net_worth_cents"],
            "national_book_net_worth_cents": t["national_book_net_worth_cents"],
            "national_book_net_worth_change_cents": (t["national_book_net_worth_cents"] -
                                                      before["national_book_net_worth_cents"]),
            "unowned_equity_cents": t["unowned_firm_equity_cents"],
            "credit_stock_cents": t["firm_loan_liabilities_cents"],
            "asset_basis_total_cents": t["firm_inventory_basis_cents"] +
                                        t["firm_capital_basis_cents"]}
    if period.book_balance_report is not None and period.book_balance_report != report:
        raise BalanceSheetError("saved balance-sheet report disagrees with independent replay")
    return report
