"""Independent analytical cases for moving-average inventory and firm books."""
from __future__ import annotations
from dataclasses import replace
import json
import numpy as np
import pytest

from civitas.economy_costs import allocated_basis, checked_add_i64
from civitas.engine import Simulation
from civitas.model import Scenario, Sector
from civitas.persistence import checkpoint_load, checkpoint_save, canonical_json


def toy(**kwargs):
    c=Scenario(name='cost-toy',population=1,household_size=1,seed=1,
               firms_per_sector=1,initial_household_cash_cents=500,
               initial_firm_cash_cents=1000,initial_resource=100,
               resource_capacity=100,regeneration_rate=0,dividend_share=0,
               capital_enabled=False,cost_basis_accounting_enabled=True,
               sectors=(Sector('food',1.0,100,50,2.0,1),))
    return replace(c,**kwargs)


def test_unit_basis_allocations_exact_no_rounding_loss():
    stock,cost=3,100
    costs=[]
    while stock:
        taken=allocated_basis(stock_units=stock,stock_cost_cents=cost,withdrawn_units=1)
        costs.append(taken);cost-=taken;stock-=1
    assert costs==[33,33,34]
    assert cost==0
    assert allocated_basis(stock_units=10,stock_cost_cents=101,withdrawn_units=4)==40
    with pytest.raises(ValueError):allocated_basis(stock_units=0,stock_cost_cents=3,withdrawn_units=0)
    with pytest.raises(ValueError):allocated_basis(stock_units=2,stock_cost_cents=3,withdrawn_units=3)
    with pytest.raises(OverflowError):checked_add_i64((1<<63)-1,1)


def test_toy_firm_book_profit_equals_change_in_assets_less_dividends():
    s=Simulation(toy())
    opening=int(s.state.firm_cash[0])+int(s.state.firm_inventory_basis_cents[0])
    p=s.step().metrics
    assert p['firm_consumer_cogs_cents']>=0
    assert p['firm_cost_basis_accounting_enabled'] is True
    assert p['firm_book_equity_discrepancy_cents']==0
    assert p['firm_cost_basis_earnings_cents']==(p['sales_cents']-p['firm_consumer_cogs_cents']
                                               -p['firm_uncapitalized_labor_cost_cents'])
    closing=int(s.state.firm_cash[0])+int(s.state.firm_inventory_basis_cents[0])
    assert closing-opening==p['firm_cost_basis_earnings_cents']
    assert p['money_discrepancy_cents']==p['goods_discrepancy_units']==0


def test_zero_production_labor_is_expensed_not_inventory():
    c=toy(sectors=(Sector('food',1.,100,50,0.01,1),))
    s=Simulation(c)
    p=s.step().metrics
    assert p['production_units']==0
    assert p['firm_inventory_historical_cost_cents']==0
    assert p['firm_uncapitalized_labor_cost_cents']==50
    assert p['firm_cost_basis_earnings_cents']==-50
    assert p['firm_book_equity_discrepancy_cents']==0


def test_capital_and_savings_24_steps_reconciles_books():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    c=Scenario.from_file(root/'scenarios/capital_reinvestment.json')
    c=replace(c,population=500,capital_depreciation_rate=.08,
              cost_basis_accounting_enabled=True,household_savings_rate=.1)
    for seed in (1,11,27):
        s=Simulation(replace(c,seed=seed))
        for p in s.run(24):
            m=p.metrics
            assert m['firm_book_equity_discrepancy_cents']==0
            assert m['firm_cashflow_discrepancy_cents']==0
            assert m['household_cashflow_discrepancy_cents']==0
            assert m['capital_discrepancy_units']==0
            assert m['goods_discrepancy_units']==0
            assert m['money_discrepancy_cents']==0
            assert (s.state.firm_inventory_basis_cents>=0).all()
            assert (s.state.firm_capital_basis_cents>=0).all()


def test_v4_checkpoint_exact_cost_basis_replay(tmp_path):
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    c=replace(Scenario.from_file(root/'scenarios/capital_reinvestment.json'),
              population=150,cost_basis_accounting_enabled=True,
              capital_depreciation_rate=.08)
    full=Simulation(c);all_metrics=[p.metrics for p in full.run(12)]
    partial=Simulation(c);prefix=[p.metrics for p in partial.run(5)]
    path=tmp_path/'new.npz'
    checkpoint_save(path,c,partial.state,partial.rng.bit_generator.state)
    with np.load(path,allow_pickle=False) as z:
        assert int(z['checkpoint_version'])==4
    cfg,state,rng=checkpoint_load(path)
    resumed=Simulation(cfg,state=state,rng_state=rng)
    suffix=[p.metrics for p in resumed.run(7)]
    assert prefix+suffix==all_metrics
    np.testing.assert_array_equal(resumed.state.firm_capital_basis_cents,full.state.firm_capital_basis_cents)
    np.testing.assert_array_equal(resumed.state.firm_inventory_basis_cents,full.state.firm_inventory_basis_cents)


def test_v3_cannot_invent_cost_history(tmp_path):
    c=toy()
    sim=Simulation(c)
    sim.step()
    source=tmp_path/'new.npz';legacy=tmp_path/'corrupt_v3.npz'
    checkpoint_save(source,c,sim.state,sim.rng.bit_generator.state)
    with np.load(source,allow_pickle=False) as z:
        fields={k:z[k].copy() for k in z.files if not k.endswith('_basis_cents')}
        fields['checkpoint_version']=np.array(3,dtype=np.int64)
    np.savez_compressed(legacy,**fields)
    with pytest.raises(ValueError,match='requires format 4'):
        checkpoint_load(legacy)


def test_cost_mode_boolean_and_empty_population():
    with pytest.raises(ValueError):toy(cost_basis_accounting_enabled=1).validate()
    s=Simulation(replace(toy(),population=0))
    assert s.step().metrics['firm_book_equity_discrepancy_cents']==0


def test_cost_comparison_reproducible_small_experiment(tmp_path):
    from research.run_cost_basis_comparison import run
    a=run(tmp_path/'a',seeds=2,steps=2,population=120)
    b=run(tmp_path/'b',seeds=2,steps=2,population=120)
    assert a['design']['executed_runs']==4
    assert a['design']['verified_periods']==8
    assert a['design']['record_sha256']==b['design']['record_sha256']
    assert a['paired_cost_basis_minus_legacy']==b['paired_cost_basis_minus_legacy']
