"""Adversarial cash-creditor protection and backwards compatibility tests."""
from dataclasses import replace

import pytest

from civitas.dividend_policy import creditor_protected_dividend as cap
from civitas.engine import Simulation
from civitas.model import Scenario, Sector
from civitas.state import LoanContract


def test_proposed_payout_is_limited_by_equity_and_cash_reserved_for_principal():
    assert cap(proposed_cents=90,cash_cents=100,inventory_basis_cents=1_000,
               capital_basis_cents=500,loan_principal_cents=80)==20
    assert cap(proposed_cents=90,cash_cents=1_000,inventory_basis_cents=0,
               capital_basis_cents=0,loan_principal_cents=980)==20
    assert cap(proposed_cents=90,cash_cents=150,inventory_basis_cents=0,
               capital_basis_cents=0,loan_principal_cents=200)==0
    assert cap(proposed_cents=90,cash_cents=100,inventory_basis_cents=0,
               capital_basis_cents=0,loan_principal_cents=0)==90
    assert cap(proposed_cents=0,cash_cents=100,inventory_basis_cents=0,
               capital_basis_cents=0,loan_principal_cents=80)==0


@pytest.mark.parametrize('bad', [-1,1.2,True,None,'22'])
def test_proposed_rejects_noninteger_or_negative(bad):
    with pytest.raises(ValueError):
        cap(proposed_cents=bad,cash_cents=100,inventory_basis_cents=0,
            capital_basis_cents=0,loan_principal_cents=0)


def test_no_lifecycle_legacy_trajectory_identical_to_historical_default():
    conf=Scenario(name='legacy dividend check', seed=107, population=40,
                  initial_firm_cash_cents=100_000,
                  cost_basis_accounting_enabled=True)
    a=Simulation(conf)
    b=Simulation(replace(conf, transaction_trace=True))
    for _ in range(8):
        assert a.step().metrics==b.step().metrics
    assert a.rng.bit_generator.state==b.rng.bit_generator.state


def test_lifecycle_guard_is_operative_even_with_positive_current_earnings():
    # Synthetic claims are matched to liabilities. This exercises the dividend
    # decision under stress without prescribing an interest-rate model.
    conf=Scenario(name='guarded', seed=3, population=40, firms_per_sector=1,
                  initial_firm_cash_cents=25_000, initial_household_cash_cents=100_000,
                  cost_basis_accounting_enabled=True, capital_enabled=False,
                  dividend_share=1.0, tax_rate=0,
                  sectors=(Sector('food',1.0,1000,100,2.0,1),))
    baseline=Simulation(replace(conf, name="baseline"))
    guarded=Simulation(replace(conf, name="guarded"))
    object.__setattr__(guarded.scenario,'firm_lifecycle_enabled',True)
    for sim in (baseline,guarded):
        s=sim.state
        cash=int(s.firm_cash[0]); debt=cash+50_000
        s.firm_loan_liabilities_cents[0]=debt
        s.household_loan_assets_cents[0]=debt
        s.loans=[LoanContract(0,0,debt,0)]
    a=baseline.step();b=guarded.step()
    assert a.metrics['dividends_cents'] > 0
    assert b.metrics['dividends_cents'] == 0
    assert b.metrics['money_discrepancy_cents']==0
