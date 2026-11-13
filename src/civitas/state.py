"""Contiguous agent data, mutable economic state and exact ledger transfers."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np


@dataclass
class LoanContract:
    lender_household: int
    borrower_firm: int
    outstanding_cents: int
    opened_step: int


@dataclass
class State:
    step: int
    household_of_agent: np.ndarray
    participation: np.ndarray
    skills: np.ndarray
    household_cash: np.ndarray
    household_savings: np.ndarray
    firm_cash: np.ndarray
    firm_capital: np.ndarray
    firm_inventory_basis_cents: np.ndarray
    firm_capital_basis_cents: np.ndarray
    household_loan_assets_cents: np.ndarray
    firm_loan_liabilities_cents: np.ndarray
    loans: list[LoanContract]
    gov_cash: int
    inventory: np.ndarray
    prices: np.ndarray
    resource: int
    initial_total_money: int
    initial_resource: int
    firm_owner_households: tuple[np.ndarray, ...]
    last_sales: np.ndarray
    last_unmet: np.ndarray
    last_employment: np.ndarray
    cumulative_output: np.ndarray
    cumulative_consumption: np.ndarray
    cumulative_capital_goods_converted: np.ndarray
    initial_capital_total: int = 0
    cumulative_capital_added: int = 0
    cumulative_capital_depreciated: int = 0
    cumulative_resource_extracted: int = 0
    cumulative_resource_regenerated: int = 0
    # Journals store summarized transaction categories, not personal trajectories.
    journal: dict[str, dict[str, int]] = field(default_factory=dict)
    trace_enabled: bool = False
    transaction_events: list[dict] = field(default_factory=list)

    def total_money(self) -> int:
        return (int(self.household_cash.sum()) + int(self.household_savings.sum()) +
                int(self.firm_cash.sum()) + int(self.gov_cash))

    def transfer(self, source: str, source_id: int, dest: str, dest_id: int,
                 amount: int, reason: str) -> None:
        """Atomic conserved transfer. Mutates nothing on invalid transaction."""
        if not isinstance(amount, (int, np.integer)) or amount < 0:
            raise ValueError("transfer amount must be nonnegative integer cents")
        amount = int(amount)
        if amount == 0:
            return
        def balance(kind: str, idx: int) -> int:
            if type(idx) not in (int, np.int32, np.int64) or idx < 0:
                raise IndexError("account id must be a nonnegative integer")
            if kind == "government":
                if idx != 0:
                    raise IndexError("government account id must be 0")
                return int(self.gov_cash)
            accounts = {"household": self.household_cash,
                        "savings": self.household_savings,
                        "firm": self.firm_cash}
            if kind not in accounts:
                raise ValueError(f"unknown account kind {kind}")
            if idx >= len(accounts[kind]):
                raise IndexError(f"account {kind}:{idx} out of range")
            return int(accounts[kind][idx])
        available = balance(source, source_id)
        balance(dest, dest_id)  # validate destination before any mutation
        if available < amount:
            raise ValueError(f"insufficient funds: {source}:{source_id}, {reason}")
        if source == dest and source_id == dest_id:
            return
        # All stored account balances are serialised as signed int64. Even if
        # the source can pay, crediting an almost-full destination must fail
        # atomically instead of wrapping around in NumPy arithmetic.
        i64max = (1 << 63) - 1
        if amount > i64max or balance(dest, dest_id) > i64max - amount:
            raise OverflowError("transfer destination exceeds signed int64")
        if source == "household":
            self.household_cash[source_id] -= amount
        elif source == "savings":
            self.household_savings[source_id] -= amount
        elif source == "firm":
            self.firm_cash[source_id] -= amount
        else:
            self.gov_cash -= amount
        if dest == "household":
            self.household_cash[dest_id] += amount
        elif dest == "savings":
            self.household_savings[dest_id] += amount
        elif dest == "firm":
            self.firm_cash[dest_id] += amount
        else:
            self.gov_cash += amount
        v = self.journal.setdefault(reason, {"cents": 0, "count": 0})
        v["cents"] += amount
        v["count"] += 1
        if self.trace_enabled:
            self.transaction_events.append({"source": source, "source_id": source_id,
                                            "destination": dest, "destination_id": dest_id,
                                            "cents": amount, "reason": reason})

    def validate(self, expected_resources: int | None = None) -> None:
        if (self.household_cash < 0).any() or (self.household_savings < 0).any() or (self.firm_cash < 0).any() or self.gov_cash < 0:
            raise AssertionError("negative monetary account")
        if ((self.firm_inventory_basis_cents < 0).any() or (self.firm_capital_basis_cents < 0).any()):
            raise AssertionError("negative historical cost basis")
        if (self.inventory == 0).any() and np.any(self.firm_inventory_basis_cents[self.inventory == 0] != 0):
            raise AssertionError("zero inventory cannot carry historical cost")
        if (self.firm_capital == 0).any() and np.any(self.firm_capital_basis_cents[self.firm_capital == 0] != 0):
            raise AssertionError("zero physical capital cannot carry historical cost")
        if ((self.household_loan_assets_cents < 0).any() or
                (self.firm_loan_liabilities_cents < 0).any()):
            raise AssertionError("negative loan claim or liability")
        claims = [0] * len(self.household_loan_assets_cents)
        debts = [0] * len(self.firm_loan_liabilities_cents)
        for contract in self.loans:
            if not (0 <= contract.lender_household < len(claims) and
                    0 <= contract.borrower_firm < len(debts) and
                    type(contract.outstanding_cents) is int and contract.outstanding_cents > 0 and
                    type(contract.opened_step) is int and 0 <= contract.opened_step <= self.step):
                raise AssertionError("invalid outstanding loan contract")
            claims[contract.lender_household] += contract.outstanding_cents
            debts[contract.borrower_firm] += contract.outstanding_cents
        if (claims != [int(x) for x in self.household_loan_assets_cents] or
                debts != [int(x) for x in self.firm_loan_liabilities_cents]):
            raise AssertionError("bilateral credit asset/liability imbalance")
        if (self.firm_capital < 0).any():
            raise AssertionError("negative firm physical capital")
        if (int(self.firm_capital.sum()) != self.initial_capital_total +
                self.cumulative_capital_added - self.cumulative_capital_depreciated):
            raise AssertionError("physical capital stock identity violated")
        if (self.cumulative_capital_goods_converted < 0).any():
            raise AssertionError("negative converted goods total")
        if int(self.cumulative_capital_goods_converted.sum()) != self.cumulative_capital_added:
            raise AssertionError("capital goods conversion identity violated")
        if (self.inventory < 0).any() or self.resource < 0:
            raise AssertionError("negative physical stock")
        if self.total_money() != self.initial_total_money:
            raise AssertionError("unexplained monetary balance change")
        if expected_resources is not None and self.resource != expected_resources:
            raise AssertionError("unexplained resource stock change")
        if (self.prices < 1).any():
            raise AssertionError("invalid price")
