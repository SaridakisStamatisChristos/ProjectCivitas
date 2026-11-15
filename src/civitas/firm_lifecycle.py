"""Opt-in firm-slot exit and owner-funded re-entry; no money creation.

This is a deliberately bounded first implementation of a firm lifecycle: firm
identity, sector and owners are fixed; a closed slot may be recapitalized by its
existing owners. There is no secondary market or new legal-entity ID yet.

An insolvent firm is liquidated with zero salvage value for unsold goods and
productive capital. Loan creditors receive available cash in contract order;
remaining principal is symmetrically written off. Physical disposal is traced.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from civitas.state import State
from civitas.finance import CreditFlows


@dataclass
class LifecycleFlows:
    firm_contributions: np.ndarray
    household_contributions: np.ndarray
    firm_distributions: np.ndarray
    household_distributions: np.ndarray
    firm_asset_writeoffs: np.ndarray
    liquidations: int = 0
    entries: int = 0
    inventory_scrapped: int = 0
    capital_scrapped: int = 0

    @classmethod
    def empty(cls, state: State) -> 'LifecycleFlows':
        nf, h = len(state.firm_cash), len(state.household_cash)
        return cls(np.zeros(nf, dtype=np.int64), np.zeros(h, dtype=np.int64),
                   np.zeros(nf, dtype=np.int64), np.zeros(h, dtype=np.int64),
                   np.zeros(nf, dtype=np.int64))


def reenter(state: State, *, contribution_cents: int, flows: LifecycleFlows) -> None:
    """Recapitalize vacant slots only with owners' spendable cash.

    Deterministic, equal-sized owner contributions. Insufficient funds skip the
    slot; no partial entry and no RNG draw occurs.
    """
    if contribution_cents <= 0:
        return
    for f, active in enumerate(state.firm_active):
        if active:
            continue
        owners = state.firm_owner_households[f]
        if not len(owners):
            continue
        base, rest = divmod(contribution_cents, len(owners))
        contributions = [(int(h), base + int(i < rest)) for i, h in enumerate(owners)]
        if any(int(state.household_cash[h]) < amount for h, amount in contributions):
            continue
        if int(state.firm_cash[f]) != 0 or int(state.inventory[f]) or int(state.firm_capital[f]) or int(state.firm_loan_liabilities_cents[f]):
            raise AssertionError('closed slot must have zero cash, assets and liabilities')
        for h, amount in contributions:
            if amount:
                state.transfer('household', h, 'firm', f, amount, 'firm_capital_contribution')
                flows.household_contributions[h] += amount
                flows.firm_contributions[f] += amount
        state.firm_active[f] = True
        if state.trace_enabled:
            state.lifecycle_events.append({'kind': 'firm_reentry', 'firm': int(f),
                                           'contribution_cents': int(flows.firm_contributions[f])})
        flows.entries += 1


def liquidate(state: State, firm: int, *, credit: CreditFlows,
              flows: LifecycleFlows, cost_basis_enabled: bool,
              firms_per_sector: int) -> None:
    """Terminate one active firm, tracing loan settlement and tangible losses."""
    if not state.firm_active[firm]:
        raise ValueError('cannot liquidate an already inactive firm')
    remaining = []
    for contract in state.loans:
        if contract.borrower_firm != firm:
            remaining.append(contract)
            continue
        h, debt = contract.lender_household, contract.outstanding_cents
        payment = min(int(state.firm_cash[firm]), debt)
        if payment:
            state.transfer('firm', firm, 'savings', h, payment, 'loan_repayment')
            state.firm_loan_liabilities_cents[firm] -= payment
            state.household_loan_assets_cents[h] -= payment
            credit.firm_principal_repaid[firm] += payment
            credit.household_principal_repaid[h] += payment
            debt -= payment
        if debt:
            state.firm_loan_liabilities_cents[firm] -= debt
            state.household_loan_assets_cents[h] -= debt
            credit.firm_principal_defaulted[firm] += debt
            credit.household_principal_defaulted[h] += debt
            journal = state.journal.setdefault('loan_default_noncash', {'cents': 0, 'count': 0})
            journal['cents'] += debt
            journal['count'] += 1
            if state.trace_enabled:
                state.noncash_events.append({'reason': 'loan_default_noncash',
                                             'lender_household': h,
                                             'borrower_firm': int(firm), 'cents': debt})
    state.loans = remaining
    inv, cap = int(state.inventory[firm]), int(state.firm_capital[firm])
    inv_basis, cap_basis = (int(state.firm_inventory_basis_cents[firm]),
                            int(state.firm_capital_basis_cents[firm]))
    if (inv or cap) and state.trace_enabled:
        state.physical_events.append({
            'kind': 'firm_liquidation', 'firm': int(firm),
            'inventory_units': inv, 'capital_units': cap,
            'inventory_basis_cents': inv_basis, 'capital_basis_cents': cap_basis,
        })
    state.inventory[firm] = 0
    state.firm_capital[firm] = 0
    state.firm_inventory_basis_cents[firm] = 0
    state.firm_capital_basis_cents[firm] = 0
    state.cumulative_inventory_liquidated[firm // firms_per_sector] += inv
    state.cumulative_capital_liquidated += cap
    flows.firm_asset_writeoffs[firm] = inv_basis + cap_basis
    flows.inventory_scrapped += inv
    flows.capital_scrapped += cap
    # After repaying creditors, return only existing cash to registered owners.
    residue = int(state.firm_cash[firm])
    if residue:
        owners = state.firm_owner_households[firm]
        if len(owners):
            base, remainder_cents = divmod(residue, len(owners))
            for i, owner in enumerate(owners):
                paid = base + int(i < remainder_cents)
                if paid:
                    state.transfer('firm', firm, 'household', int(owner), paid,
                                   'firm_liquidation_distribution')
                    flows.firm_distributions[firm] += paid
                    flows.household_distributions[int(owner)] += paid
        else:
            state.transfer('firm', firm, 'government', 0, residue,
                           'firm_liquidation_escheat')
            flows.firm_distributions[firm] += residue
    state.firm_active[firm] = False
    if state.trace_enabled:
        state.lifecycle_events.append({'kind': 'firm_liquidation', 'firm': int(firm),
                                       'inventory_units': inv, 'capital_units': cap,
                                       'asset_writeoff_cents': inv_basis + cap_basis})
    state.last_sales[firm] = 0
    flows.liquidations += 1


def close_insolvent(state: State, *, credit: CreditFlows,
                    flows: LifecycleFlows, cost_basis_enabled: bool,
                    firms_per_sector: int) -> None:
    """Close negative-book-equity or completely exhausted active firm slots."""
    for firm, active in enumerate(state.firm_active):
        if not active:
            continue
        equity = (int(state.firm_cash[firm]) +
                  (int(state.firm_inventory_basis_cents[firm]) +
                   int(state.firm_capital_basis_cents[firm]) if cost_basis_enabled else 0) -
                  int(state.firm_loan_liabilities_cents[firm]))
        exhausted = (int(state.firm_cash[firm]) == 0 and
                     int(state.inventory[firm]) == 0 and
                     int(state.firm_capital[firm]) == 0)
        if equity < 0 or exhausted:
            liquidate(state, firm, credit=credit, flows=flows,
                      cost_basis_enabled=cost_basis_enabled,
                      firms_per_sector=firms_per_sector)
