"""Regression, causal isolation, quote observation and deterministic replay checks."""
from dataclasses import replace
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from civitas.engine import Simulation
from civitas.model import Scenario
from civitas.persistence import checkpoint_save, checkpoint_load

ROOT = Path(__file__).resolve().parents[1]
BASE = Scenario.from_file(ROOT / 'scenarios/population_normalized/o08_s00_n10000.json')


def toy(**opts):
    values = dict(name='region_info_toy', population=120, household_size=4,
                  firms_per_sector=8, market_regions=4, seed=13,
                  initial_resource=50_000, resource_capacity=60_000,
                  initial_firm_cash_cents=200_000, transaction_trace=True)
    values.update(opts)
    return Scenario(**values)


@pytest.mark.parametrize('bad', [
    {'household_region_assignment': 'random'},
    {'household_region_assignment': None},
    {'buyer_price_information': 'everyone'},
    {'buyer_price_information': 1},
    {'region_assignment_seed': -1},
    {'region_assignment_seed': 0.7},
    {'region_assignment_seed': True},
])
def test_invalid_region_and_information_params(bad):
    with pytest.raises(ValueError):
        toy(**bad).validate()


def test_balanced_shuffle_preserves_region_counts_rng_state_and_initial_accounts():
    base = toy(population=200, firms_per_sector=10, market_regions=5)
    a = Simulation(base)
    b = Simulation(replace(base, household_region_assignment='balanced_shuffle',
                           region_assignment_seed=29))
    np.testing.assert_array_equal(np.bincount(a.household_regions),
                                  np.bincount(b.household_regions))
    assert not np.array_equal(a.household_regions, b.household_regions)
    for key in ('household_cash', 'household_savings', 'firm_cash',
                'firm_capital', 'skills', 'participation'):
        np.testing.assert_array_equal(getattr(a.state, key), getattr(b.state, key))
    assert a.rng.bit_generator.state == b.rng.bit_generator.state
    assert np.array_equal(b.household_regions,
                          Simulation(replace(base, household_region_assignment='balanced_shuffle',
                                             region_assignment_seed=29)).household_regions)
    assert not np.array_equal(b.household_regions,
                              Simulation(replace(base, household_region_assignment='balanced_shuffle',
                                                 region_assignment_seed=30)).household_regions)


def test_assignment_inert_when_sales_and_labor_unrestricted():
    base = replace(BASE, seed=6, market_regions=5)
    a = Simulation(base)
    b = Simulation(replace(base, household_region_assignment='balanced_shuffle',
                           region_assignment_seed=101))
    for x,y in zip(a.run(6),b.run(6)):
        assert x.metrics == y.metrics
        assert x.journal == y.journal


def test_full_quotes_historical_behavior_and_no_diagnostics():
    base = toy()
    a = Simulation(base)
    b = Simulation(replace(base, buyer_price_information='full'))
    for x,y in zip(a.run(5),b.run(5)):
        assert x.metrics == y.metrics
        assert x.metrics['information_missed_purchase_opportunities'] == 0


@pytest.mark.parametrize('sales', [False,True])
def test_two_quotes_limit_which_firms_could_sell(sales):
    c = toy(buyer_price_information='two_quotes', restrict_household_sales=sales)
    sim = Simulation(c)
    sold = 0
    for step in range(4):
        period = sim.step()
        for tx in period.transactions:
            if tx['reason'] != 'sale':
                continue
            h = tx['source_id']; f = tx['destination_id']
            sector = f//c.firms_per_sector
            lo = sector*c.firms_per_sector
            if sales:
                options = [i for i in range(lo,lo+c.firms_per_sector)
                           if sim.firm_regions[i] == sim.household_regions[h]]
            else:
                options = list(range(lo,lo+c.firms_per_sector))
            if len(options)>2:
                first = (h*13007 + step*107 + sector*29)%len(options)
                options = [options[first],options[(first+1)%len(options)]]
            assert f in options
            sold+=1
        assert all(period.metrics[k]==0 for k in ('money_discrepancy_cents',
            'resource_discrepancy_units', 'goods_discrepancy_units',
            'capital_discrepancy_units', 'household_cashflow_discrepancy_cents',
            'firm_cashflow_discrepancy_cents'))
    assert sold > 5


def test_two_quotes_can_fail_with_unseen_available_inventory():
    # Construct a consistent stock fixture: an available good exists at a firm
    # that this household cannot observe. No production or wage process runs.
    from civitas.model import Sector
    c=toy(population=1, household_size=1, market_regions=1,
          sectors=(Sector('food',1.0,100,0,1.0,1),),
          firms_per_sector=4, labor_participation=0.0,
          buyer_price_information='two_quotes',
          initial_household_cash_cents=1000,
          initial_resource=0, resource_capacity=0)
    sim=Simulation(c)
    visible={0,1}  # h=0, step=0, k=0
    assert all(f not in visible for f in (2,3))
    sim.state.inventory[2]=1
    sim.state.cumulative_output[0]=1
    result=sim.step()
    assert result.metrics['consumption_units']==0
    assert result.metrics['information_missed_purchase_opportunities']==1
    assert result.metrics['goods_discrepancy_units']==0
    full=replace(c,buyer_price_information='full')
    full_sim=Simulation(full)
    full_sim.state.inventory[2]=1
    full_sim.state.cumulative_output[0]=1
    assert full_sim.step().metrics['consumption_units']==1


def test_seed_paired_rng_state_and_checkpoint_roundtrip(tmp_path):
    base=toy(population=200, firms_per_sector=10, market_regions=5,
             capital_enabled=True, initial_capital_units_per_firm=50)
    root=Simulation(base)
    init_rng=deepcopy(root.rng.bit_generator.state)
    end_rngs=[]
    for assignment in ('modulo','balanced_shuffle'):
        for info in ('full','two_quotes'):
            for sales in (False,True):
                c=replace(base,household_region_assignment=assignment,
                          buyer_price_information=info,restrict_household_sales=sales)
                sim=Simulation(c,state=deepcopy(root.state),rng_state=deepcopy(init_rng))
                first=[p.metrics for p in sim.run(2)]
                fn=tmp_path/f'{assignment}-{info}-{sales}.npz'
                checkpoint_save(fn,c,sim.state,sim.rng.bit_generator.state)
                rc,rs,rr=checkpoint_load(fn)
                resumed=Simulation(rc,state=rs,rng_state=rr)
                second=[p.metrics for p in resumed.run(2)]
                direct=Simulation(c,state=deepcopy(root.state),rng_state=deepcopy(init_rng))
                assert first+second==[p.metrics for p in direct.run(4)]
                end_rngs.append(direct.rng.bit_generator.state)
    assert all(x==end_rngs[0] for x in end_rngs)


def test_small_factorial_integrity_and_tampering(tmp_path):
    from research.run_region_information import run_seed, finalize
    run_seed(tmp_path,1,3,population=200,firms_per_sector=10,regions=5)
    run_seed(tmp_path,2,3,population=200,firms_per_sector=10,regions=5)
    report=finalize(tmp_path,2,3,population=200,firms_per_sector=10,regions=5)
    assert report['observations']==48
    assert report['experiments']==16
    f=tmp_path/'shards'/'seed_0002.csv'
    f.write_bytes(f.read_bytes()+b'X')
    with pytest.raises(ValueError,match='digest'):
        finalize(tmp_path,2,3,population=200,firms_per_sector=10,regions=5)
