"""Opt-in firm exit/entry conservation, replay, and adversarial audit tests."""
from __future__ import annotations
from dataclasses import replace
from copy import deepcopy
import numpy as np
import pytest

from civitas.model import Scenario, Sector
from civitas.engine import Simulation
from civitas.finance import CreditFlows, originate
from civitas.firm_lifecycle import LifecycleFlows, liquidate
from civitas.firm_lifecycle_audit import audit_firm_lifecycle, FirmLifecycleAuditError
from civitas.persistence import checkpoint_save, checkpoint_load, config_digest
from civitas.physical_audit import capture_physical_opening, audit_physical_period, PhysicalAuditError
from civitas.ledger_audit import capture_opening, audit_period, LedgerAuditError
from civitas.balance_sheet import capture_book_snapshot, audit_book_period, BalanceSheetError


def scenario(**overrides):
    values = dict(name='firm-lifecycle-analytical', population=12, household_size=1,
                  firms_per_sector=2, capital_enabled=True,
                  cost_basis_accounting_enabled=True, credit_enabled=True,
                  credit_term_periods=4, credit_repayment_fraction=0.0,
                  firm_lifecycle_enabled=True, firm_reentry_enabled=True,
                  firm_reentry_contribution_cents=60,
                  initial_capital_units_per_firm=2,
                  capital_investment_budget_share=0.0,
                  initial_firm_cash_cents=100,
                  initial_household_cash_cents=3000,
                  household_savings_rate=0.0, transaction_trace=True,
                  sectors=(Sector('goods',0.0,100,50,1.0,1),))
    values.update(overrides)
    return Scenario(**values)


def bankrupt(sim: Simulation, principal: int = 1200, inventory: int = 3):
    """Create a balanced opening insolvent firm; cash leaves, debt remains.

    The synthetic initial market setup is an explicitly controlled stress
    scenario, not an endogenous loan-investment transaction history.
    """
    state = sim.state
    state.transfer('household',0,'savings',0,principal,'savings_deposit')
    originate(state,0,principal,np.full(len(state.household_cash),principal,dtype=np.int64),
              CreditFlows.empty(state))
    state.transfer('firm',0,'firm',1,principal + 100,'capital_purchase')
    if inventory:
        state.inventory[0] = inventory
        state.firm_inventory_basis_cents[0] = 70
        state.cumulative_output[0] += inventory
    state.validate()
    return state


def test_bilateral_default_liquidates_assets_and_replays():
    sim = Simulation(scenario())
    state = bankrupt(sim)
    before = state.total_money()
    p = sim.step()
    assert p.metrics['firm_liquidations'] == 1
    assert p.metrics['loan_defaults_cents'] == 1200
    assert p.metrics['firm_liquidation_inventory_units'] == 3
    assert p.metrics['firm_liquidation_capital_units'] == 2
    assert p.metrics['firm_liquidation_basis_cents'] == 270
    assert p.metrics['capital_discrepancy_units'] == 0
    assert p.metrics['goods_discrepancy_units'] == 0
    assert p.metrics['firm_book_equity_discrepancy_cents'] == 0
    assert state.total_money() == before
    assert state.firm_active.tolist() == [False, True]
    assert state.firm_loan_liabilities_cents[0] == 0
    assert state.household_loan_assets_cents.sum() == 0
    assert any(t['kind'] == 'firm_liquidation' for t in p.physical_transactions)
    assert len(p.lifecycle_transactions) == 1


def test_funded_reentry_exact_replay_from_format6(tmp_path):
    sim = Simulation(scenario())
    bankrupt(sim)
    first = sim.step()
    path=tmp_path/'firm_lifecycle.npz'
    checkpoint_save(path,sim.scenario,sim.state,sim.rng.bit_generator.state)
    with np.load(path,allow_pickle=False) as z:
        assert int(z['checkpoint_version']) == 6
    cfg,saved,rng=checkpoint_load(path)
    assert saved.firm_active.tolist() == [False,True]
    restart=Simulation(cfg,state=saved,rng_state=rng)
    p=sim.step()
    q=restart.step()
    assert p.metrics == q.metrics
    assert p.transactions == q.transactions
    assert p.lifecycle_transactions == q.lifecycle_transactions
    assert p.book_balance_report == q.book_balance_report
    assert p.metrics['firm_reentries'] == 1
    assert p.metrics['firm_reentry_contributions_cents'] == 60
    assert p.metrics['firm_active_count'] == 2
    assert any(x['reason']=='firm_capital_contribution' for x in p.transactions)


def test_unfunded_firm_remains_inactive_without_issuing_money():
    sc=scenario(firm_reentry_contribution_cents=100_000)
    sim=Simulation(sc)
    bankrupt(sim)
    sim.step()
    p=sim.step()
    assert p.metrics['firm_reentries']==0
    assert not sim.state.firm_active[0]
    assert p.metrics['firm_reentry_contributions_cents']==0
    assert p.metrics['money_discrepancy_cents']==0


def test_closed_firm_ignored_by_consumer_and_labor():
    sc=scenario(firm_reentry_enabled=False,household_savings_rate=0.0,
                sectors=(Sector('goods',1.0,100,10,1.0,1),))
    sim=Simulation(sc)
    bankrupt(sim)
    sim.step()
    p=sim.step()
    assert p.metrics['firm_reentries']==0
    assert not sim.state.firm_active[0]
    assert all(x['destination_id']!=0 for x in p.transactions if x['reason']=='sale')
    assert all(x['source_id']!=0 for x in p.transactions if x['reason']=='wages')


def test_false_or_tampered_lifecycle_transition_rejected():
    sim=Simulation(scenario())
    bankrupt(sim)
    opening = tuple(bool(x) for x in sim.state.firm_active)
    p=sim.step()
    altered=deepcopy(p)
    altered.lifecycle_transactions[0]['asset_writeoff_cents'] += 1
    with pytest.raises(FirmLifecycleAuditError):
        audit_firm_lifecycle(opening, sim.state, altered)
    altered=deepcopy(p)
    altered.lifecycle_transactions.clear()
    with pytest.raises(FirmLifecycleAuditError):
        audit_firm_lifecycle(opening, sim.state, altered)


def test_asset_scrap_tamper_rejected_by_physical_replayer():
    sim=Simulation(scenario())
    bankrupt(sim)
    opening=capture_physical_opening(sim.state)
    p=sim.step()
    corrupted=deepcopy(p)
    for event in corrupted.physical_transactions:
        if event['kind']=='firm_liquidation':
            event['inventory_units'] += 1
            break
    with pytest.raises(PhysicalAuditError):
        audit_physical_period(opening,sim.state,corrupted,sim.scenario)


def test_cash_transfer_and_writeoff_tamper_rejected():
    sim=Simulation(scenario())
    bankrupt(sim)
    opening=capture_opening(sim.state)
    p=sim.step()
    corrupted=deepcopy(p)
    corrupted.noncash_transactions[0]['cents'] -= 1
    with pytest.raises(LedgerAuditError):
        audit_period(opening,sim.state,corrupted)


def test_reporting_tamper_rejected_by_book_audit():
    sim=Simulation(scenario())
    bankrupt(sim)
    opening=capture_book_snapshot(sim.state,sim.scenario)
    p=sim.step()
    corrupted=deepcopy(p)
    corrupted.book_balance_report['national_book_net_worth_cents'] += 2
    with pytest.raises(BalanceSheetError):
        audit_book_period(opening,sim.state,corrupted,sim.scenario)


def test_lifecycle_requires_cost_basis_and_valid_flags():
    with pytest.raises(ValueError):
        scenario(cost_basis_accounting_enabled=False).validate()
    with pytest.raises(ValueError):
        scenario(firm_lifecycle_enabled=False,firm_reentry_enabled=True).validate()
    with pytest.raises(ValueError):
        scenario(firm_lifecycle_enabled=1).validate()
    with pytest.raises(ValueError):
        scenario(firm_reentry_contribution_cents=-1).validate()


def test_legacy_scenario_digest_unchanged():
    from civitas.model import Scenario
    raw=Scenario(name='legacy').to_dict()
    assert 'firm_lifecycle_enabled' not in raw
    assert 'firm_reentry_enabled' not in raw
    assert 'firm_reentry_contribution_cents' not in raw


def test_adversarial_corrupt_inactive_firm_rejected():
    sim=Simulation(scenario())
    bankrupt(sim)
    sim.step()
    sim.state.firm_cash[0]=1
    with pytest.raises(AssertionError,match='inactive firm'):
        sim.state.validate()


def test_liquidation_satisfies_earliest_creditor_first_without_minting():
    sim=Simulation(scenario())
    s=sim.state
    for h in (0,1):
        s.transfer('household',h,'savings',h,100,'savings_deposit')
        caps=np.zeros(len(s.household_cash),dtype=np.int64)
        caps[h]=100
        originate(s,0,100,caps,CreditFlows.empty(s))
    # Preserve 50 cents for creditors; transfer 250 to a live company.
    s.transfer('firm',0,'firm',1,250,'capital_purchase')
    before=s.total_money()
    cf=CreditFlows.empty(s)
    lf=LifecycleFlows.empty(s)
    liquidate(s,0,credit=cf,flows=lf,cost_basis_enabled=True,firms_per_sector=2)
    assert cf.firm_principal_repaid[0]==50
    assert cf.firm_principal_defaulted[0]==150
    assert s.household_loan_assets_cents[0]==0
    assert int(s.household_savings[0])==50
    assert s.household_loan_assets_cents[1]==0
    assert s.firm_loan_liabilities_cents[0]==0
    assert s.total_money()==before
    s.validate()


def test_enter_then_exit_same_period_has_complete_transition_trace():
    sc=scenario(credit_enabled=False, capital_enabled=False, initial_capital_units_per_firm=0,
                initial_resource=0,resource_capacity=0,
                firm_reentry_contribution_cents=60,
                sectors=(Sector('goods',1.0,100,60,1.0,1),))
    sim=Simulation(sc)
    s=sim.state
    owner=int(s.firm_owner_households[0][0])
    s.transfer('firm',0,'household',owner,100,'dividend')
    s.firm_active[0]=False
    s.validate()
    p=sim.step()
    assert [x['kind'] for x in p.lifecycle_transactions if x['firm']==0] == [
        'firm_reentry', 'firm_liquidation']
    assert p.metrics['firm_reentries']==1
    assert p.metrics['firm_liquidations'] >= 1
    assert not s.firm_active[0]
    assert p.metrics['money_discrepancy_cents']==0
    assert p.metrics['firm_book_equity_discrepancy_cents']==0
