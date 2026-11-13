"""Exact analytical tests for real-savings-funded, principal-only bilateral credit."""
from dataclasses import replace
import numpy as np
import pytest

from civitas.engine import Simulation
from civitas.finance import CreditFlows, originate, service_loans
from civitas.model import Scenario, Sector
from civitas.persistence import checkpoint_load, checkpoint_save


def small_credit(**kwargs):
    base = Scenario(
        name="credit-toy", population=4, household_size=1, seed=11,
        firms_per_sector=1, initial_household_cash_cents=10_000,
        initial_firm_cash_cents=20_000, initial_resource=1000,
        resource_capacity=1000, regeneration_rate=0.0,
        tax_rate=0.0, dividend_share=0.0,
        capital_enabled=True, initial_capital_units_per_firm=20,
        cost_basis_accounting_enabled=True, credit_enabled=True,
        capital_investment_budget_share=0.2,
        household_savings_rate=0.4, savings_emergency_food_enabled=False,
        credit_repayment_fraction=0.5,
        credit_firm_cash_reserve_cents=0,
        credit_term_periods=3, credit_lender_savings_share=1.0,
        sectors=(Sector("goods", 1.0, 100, 50, 2.0, 2),),
    )
    return replace(base, **kwargs)


def test_credit_requires_explicit_physical_and_historical_books():
    for changes in (
        dict(credit_enabled=True,capital_enabled=False),
        dict(credit_enabled=True,cost_basis_accounting_enabled=False),
        dict(credit_enabled=1),
        dict(credit_term_periods=0),
        dict(credit_max_principal_per_firm_cents=-1),
        dict(credit_repayment_fraction=1.01),
        dict(credit_lender_savings_share=-.01),
        dict(resource_extraction_fee_cents_per_unit=-1),
    ):
        with pytest.raises(ValueError):
            replace(small_credit(), **changes).validate()


def test_exact_loan_originations_and_cross_account_money_conservation():
    sim = Simulation(small_credit())
    state = sim.state
    state.household_savings[:] = [250, 400, 50, 0]
    state.household_cash[:] -= state.household_savings
    initial_cash = state.total_money()
    flow = CreditFlows.empty(state)
    caps = state.household_savings.copy()
    assert originate(state, firm=0, cents=600, caps=caps, flows=flow) == 600
    assert state.total_money() == initial_cash
    assert sum(x.outstanding_cents for x in state.loans) == 600
    assert state.firm_loan_liabilities_cents.tolist() == [600]
    assert state.household_loan_assets_cents.tolist() == [250, 350, 0, 0]
    assert state.household_savings.tolist() == [0, 50, 50, 0]
    assert flow.firm_principal_advanced.tolist() == [600]
    assert sum(flow.household_principal_advanced) == 600
    state.validate()
    with pytest.raises(ValueError):
        originate(state, 0, 1000, caps, flow)
    assert state.total_money() == initial_cash


def test_repayment_and_maturity_default_are_symmetric_and_noncash():
    sim = Simulation(small_credit(credit_repayment_fraction=.0, credit_term_periods=2))
    s = sim.state
    s.household_savings[0] = 1000
    s.household_cash[0] -= 1000
    flow = CreditFlows.empty(s)
    originate(s,0,1000,s.household_savings.copy(),flow)
    opening_money=s.total_money()
    s.step=1
    repay=CreditFlows.empty(s)
    service_loans(s,repayment_fraction=.25,term=2,reserve_cents=19000,flows=repay)
    assert repay.firm_principal_repaid.sum()==500
    assert repay.firm_principal_defaulted.sum()==0
    assert int(s.firm_loan_liabilities_cents[0])==500
    assert s.total_money()==opening_money
    s.step=2
    expired=CreditFlows.empty(s)
    service_loans(s,repayment_fraction=0.,term=2,reserve_cents=0,flows=expired)
    assert int(expired.firm_principal_defaulted.sum())==500
    assert int(expired.household_principal_defaulted.sum())==500
    assert s.household_loan_assets_cents.sum()==0
    assert s.firm_loan_liabilities_cents.sum()==0
    assert s.total_money()==opening_money
    assert s.journal['loan_default_noncash']['cents']==500
    s.validate()


def test_corrupt_credit_liability_or_contract_is_detected():
    sim=Simulation(small_credit())
    sim.state.household_loan_assets_cents[0]=1
    with pytest.raises(AssertionError,match='bilateral'):
        sim.state.validate()


def test_resource_use_fee_transfers_exact_cash_and_capitalizes_cost():
    c = small_credit(credit_enabled=False,resource_extraction_fee_cents_per_unit=3,
                     population=1,labor_participation=1.0, dividend_share=0.0,
                     capital_investment_budget_share=0.0)
    s = Simulation(c)
    s.state.skills[:] = 1.0
    metrics = s.step().metrics
    assert metrics['resource_extracted'] == 2 * metrics['production_units']
    assert metrics['government_resource_fee_cents'] == 3 * metrics['resource_extracted']
    assert metrics['firm_resource_input_fees_cents'] == metrics['government_resource_fee_cents']
    assert metrics['firm_book_equity_discrepancy_cents']==0
    assert metrics['money_discrepancy_cents']==0
    assert metrics['resource_discrepancy_units']==0
    assert metrics['loan_origination_cents']==0


def test_resource_fee_can_prevent_production_when_firms_cannot_pay():
    c = small_credit(population=1, labor_participation=1.0,
                     credit_enabled=False, initial_firm_cash_cents=50,
                     resource_extraction_fee_cents_per_unit=10000,
                     capital_investment_budget_share=0.0)
    s = Simulation(c)
    m = s.step().metrics
    assert m['production_units']==0
    assert m['government_resource_fee_cents']==0
    assert m['firm_book_equity_discrepancy_cents']==0


def test_credit_checkpoint_v5_exact_replay_with_real_loans(tmp_path):
    from pathlib import Path
    source=Scenario.from_file(Path(__file__).resolve().parents[1]/'scenarios/capital_reinvestment.json')
    cfg=replace(source,population=1000,initial_capital_units_per_firm=20,
                initial_firm_cash_cents=20000,capital_investment_budget_share=.05,
                cost_basis_accounting_enabled=True,credit_enabled=True,
                household_savings_rate=.75,credit_firm_cash_reserve_cents=10000,
                credit_repayment_fraction=.10,
                credit_max_principal_per_firm_cents=500000)
    full=Simulation(cfg)
    all_metrics=[p.metrics for p in full.run(18)]
    assert sum(m['loan_origination_cents'] for m in all_metrics)>0
    assert sum(m['loan_repayment_cents'] for m in all_metrics)>0
    assert sum(m['loan_defaults_cents'] for m in all_metrics)>0
    partial=Simulation(cfg)
    prefix=[p.metrics for p in partial.run(12)]
    checkpoint=tmp_path/'credit.npz'
    checkpoint_save(checkpoint,cfg,partial.state,partial.rng.bit_generator.state)
    with np.load(checkpoint,allow_pickle=False) as z:
        assert int(z['checkpoint_version'])==5
        assert len(z['loan_lender_ids'])>0
    decoded,state,rng=checkpoint_load(checkpoint)
    restored=Simulation(decoded,state=state,rng_state=rng)
    assert prefix + [p.metrics for p in restored.run(6)] == all_metrics
    assert restored.state.total_money()==full.state.total_money()
    np.testing.assert_array_equal(restored.state.household_loan_assets_cents,
                                  full.state.household_loan_assets_cents)
    np.testing.assert_array_equal(restored.state.firm_loan_liabilities_cents,
                                  full.state.firm_loan_liabilities_cents)


def test_legacy_configurations_do_not_create_credit_or_resource_fees():
    c=Scenario(name='legacy-test', population=50)
    s=Simulation(c)
    for p in s.run(3):
        m=p.metrics
        assert m['loan_origination_cents']==0
        assert m['loan_defaults_cents']==0
        assert m['firm_loan_liabilities_cents']==0
        assert m['government_resource_fee_cents']==0
        assert m['money_discrepancy_cents']==0


def test_credit_funding_preflights_entire_multi_lender_batch():
    s=Simulation(small_credit()).state
    s.household_savings[:]=[10,10,0,0]
    s.household_cash[:]-=s.household_savings
    before=(s.total_money(),s.firm_cash.copy(),s.household_savings.copy())
    flows=CreditFlows.empty(s)
    caps=np.array([100,100,0,0],dtype=np.int64)  # invalid optimistic caller budget
    with pytest.raises(ValueError,match='genuinely available'):
        originate(s,0,50,caps,flows)
    assert s.total_money()==before[0]
    np.testing.assert_array_equal(s.firm_cash,before[1])
    np.testing.assert_array_equal(s.household_savings,before[2])
    assert not s.loans
    assert s.firm_loan_liabilities_cents.sum()==0


def test_experiment_runner_reproduces_seed_matched_accounting(tmp_path):
    from research.run_credit_experiment import run
    a=run(tmp_path/'one',population=1000,seeds=2,steps=3)
    b=run(tmp_path/'two',population=1000,seeds=2,steps=3)
    assert a['design']['runs']==8
    assert a['design']['audited_periods']==24
    assert a['design']['periods_sha256']==b['design']['periods_sha256']
    assert a['scenario_summary']==b['scenario_summary']
    assert a['paired_credit_minus_no_credit']==b['paired_credit_minus_no_credit']
    with pytest.raises(ValueError, match='multiples of 1000'):
        run(tmp_path/'bad',population=1200,seeds=1,steps=2,normalized_firm_density=True)


def test_credit_requires_v5_checkpoint_not_fabricated_accounts(tmp_path):
    cfg=small_credit()
    sim=Simulation(cfg)
    path=tmp_path/'source.npz'
    checkpoint_save(path,cfg,sim.state,sim.rng.bit_generator.state)
    with np.load(path,allow_pickle=False) as z:
        fields={k:z[k].copy() for k in z.files if not k.startswith('loan_')
                and k not in ('household_loan_assets_cents','firm_loan_liabilities_cents')}
    fields['checkpoint_version']=np.array(4,dtype=np.int64)
    bad=tmp_path/'bad.npz'
    np.savez_compressed(bad,**fields)
    with pytest.raises(ValueError,match='requires format 5'):
        checkpoint_load(bad)
