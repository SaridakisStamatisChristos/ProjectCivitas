"""Contiguous agent data, mutable economic state and exact ledger transfers."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np


@dataclass
class State:
    step: int
    household_of_agent: np.ndarray
    participation: np.ndarray
    skills: np.ndarray
    household_cash: np.ndarray
    firm_cash: np.ndarray
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
    cumulative_resource_extracted: int = 0
    cumulative_resource_regenerated: int = 0
    # Journals store summarized transaction categories, not personal trajectories.
    journal: dict[str, dict[str, int]] = field(default_factory=dict)

    def total_money(self) -> int:
        return int(self.household_cash.sum()) + int(self.firm_cash.sum()) + int(self.gov_cash)

    def transfer(self, source: str, source_id: int, dest: str, dest_id: int,
                 amount: int, reason: str) -> None:
        """Atomic conserved transfer. Mutates nothing on invalid transaction."""
        if not isinstance(amount, (int, np.integer)) or amount < 0:
            raise ValueError("transfer amount must be nonnegative integer cents")
        amount = int(amount)
        if amount == 0:
            return
        def balance(kind: str, idx: int) -> int:
            if kind == "household":
                return int(self.household_cash[idx])
            if kind == "firm":
                return int(self.firm_cash[idx])
            if kind == "government":
                if idx != 0:
                    raise IndexError("government account id must be 0")
                return int(self.gov_cash)
            raise ValueError(f"unknown account kind {kind}")
        available = balance(source, source_id)
        balance(dest, dest_id)  # validate destination before any mutation
        if available < amount:
            raise ValueError(f"insufficient funds: {source}:{source_id}, {reason}")
        if source == dest and source_id == dest_id:
            return
        if source == "household":
            self.household_cash[source_id] -= amount
        elif source == "firm":
            self.firm_cash[source_id] -= amount
        else:
            self.gov_cash -= amount
        if dest == "household":
            self.household_cash[dest_id] += amount
        elif dest == "firm":
            self.firm_cash[dest_id] += amount
        else:
            self.gov_cash += amount
        v = self.journal.setdefault(reason, {"cents": 0, "count": 0})
        v["cents"] += amount
        v["count"] += 1

    def validate(self, expected_resources: int | None = None) -> None:
        if (self.household_cash < 0).any() or (self.firm_cash < 0).any() or self.gov_cash < 0:
            raise AssertionError("negative monetary account")
        if (self.inventory < 0).any() or self.resource < 0:
            raise AssertionError("negative physical stock")
        if self.total_money() != self.initial_total_money:
            raise AssertionError("unexplained monetary balance change")
        if expected_resources is not None and self.resource != expected_resources:
            raise AssertionError("unexplained resource stock change")
        if (self.prices < 1).any():
            raise AssertionError("invalid price")
