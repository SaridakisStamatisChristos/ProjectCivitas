"""Conserved bilateral household-to-firm investment finance (no money issuance).

All contracts are zero-interest, principal-only, integer cents. Households lend
from their existing savings accounts; claims are separate noncash financial
assets. Repayment returns existing firm cash to lenders' savings; at maturity,
any remaining principal is written off symmetrically, without a cash transfer.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
import numpy as np

from civitas.state import LoanContract, State
from civitas.economy_costs import checked_add_i64


@dataclass
class CreditFlows:
    firm_principal_advanced: np.ndarray
    firm_principal_repaid: np.ndarray
    firm_principal_defaulted: np.ndarray
    household_principal_advanced: np.ndarray
    household_principal_repaid: np.ndarray
    household_principal_defaulted: np.ndarray

    @classmethod
    def empty(cls, state: State) -> CreditFlows:
        return cls(*(np.zeros(n, dtype=np.int64) for n in (
            len(state.firm_cash), len(state.firm_cash), len(state.firm_cash),
            len(state.household_cash), len(state.household_cash), len(state.household_cash))))


def service_loans(state: State, *, repayment_fraction: float, term: int,
                  reserve_cents: int, flows: CreditFlows) -> None:
    """Repay from current firm cash above reserve, then write off matured debt.

    Operates at beginning of a period, prior to labor expenditures. A contract
    is mature once step-opened_step >= term, with no grace period. Default is
    a balance-sheet loss to lender and a debt-extinguishment gain to borrower.
    """
    rate = Fraction(str(repayment_fraction))
    budgets = [(max(0, int(x) - reserve_cents) * rate.numerator) // rate.denominator
               for x in state.firm_cash]
    active: list[LoanContract] = []
    for loan in state.loans:
        f, h = loan.borrower_firm, loan.lender_household
        paid = min(loan.outstanding_cents, budgets[f])
        if paid:
            state.transfer("firm", f, "savings", h, paid, "loan_repayment")
            loan.outstanding_cents -= paid
            state.firm_loan_liabilities_cents[f] -= paid
            state.household_loan_assets_cents[h] -= paid
            flows.firm_principal_repaid[f] += paid
            flows.household_principal_repaid[h] += paid
            budgets[f] -= paid
        if loan.outstanding_cents and state.step - loan.opened_step >= term:
            amount = loan.outstanding_cents
            state.household_loan_assets_cents[h] -= amount
            state.firm_loan_liabilities_cents[f] -= amount
            flows.firm_principal_defaulted[f] += amount
            flows.household_principal_defaulted[h] += amount
            # Explicit noncash journal; never misreport as a monetary transfer.
            item = state.journal.setdefault("loan_default_noncash", {"cents": 0, "count": 0})
            item["cents"] += amount
            item["count"] += 1
        elif loan.outstanding_cents:
            active.append(loan)
    state.loans = active


def available_credit(state: State, firm: int, caps: np.ndarray,
                     max_outstanding_cents: int) -> int:
    headroom = max(0, max_outstanding_cents - int(state.firm_loan_liabilities_cents[firm]))
    return min(headroom, sum(int(x) for x in caps))


def originate(state: State, firm: int, cents: int, caps: np.ndarray,
              flows: CreditFlows) -> int:
    """Fund an exact capital-goods cash shortfall, or fail before any transfer.

    caps is a per-lender, per-period budget initialized by the caller. The
    transfer uses real savings; contracts + bilateral totals are recorded.
    """
    if type(cents) is not int or cents < 0 or len(caps) != len(state.household_savings):
        raise ValueError("invalid requested principal or savings funding budget")
    remaining = cents
    if not remaining:
        return 0
    # Plan and validate the whole loan before modifying any account. Direct
    # callers cannot create partial sets of loans with impossible funding.
    plan: list[tuple[int, int]] = []
    for i in range(len(caps)):
        h = (firm + state.step + i) % len(caps)
        amount = min(remaining, int(caps[h]), int(state.household_savings[h]))
        if amount > 0:
            plan.append((h, amount))
            remaining -= amount
        if remaining == 0:
            break
    if remaining:
        raise ValueError("loan amount exceeds genuinely available savings")
    checked_add_i64(int(state.firm_cash[firm]), cents)
    checked_add_i64(int(state.firm_loan_liabilities_cents[firm]), cents)
    for h, amount in plan:
        checked_add_i64(int(state.household_loan_assets_cents[h]), amount)
    for h, amount in plan:
        state.transfer("savings", h, "firm", firm, amount, "loan_origination")
        state.household_loan_assets_cents[h] += amount
        state.firm_loan_liabilities_cents[firm] += amount
        caps[h] -= amount
        flows.household_principal_advanced[h] += amount
        flows.firm_principal_advanced[firm] += amount
        state.loans.append(LoanContract(h, firm, amount, state.step))
    return cents
