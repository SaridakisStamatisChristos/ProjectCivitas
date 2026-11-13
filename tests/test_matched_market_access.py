"""Exact-initial-state experiments: household purchase vs worker access partitions."""
from __future__ import annotations

from dataclasses import replace
import copy
from pathlib import Path

import numpy as np
import pytest

from civitas.engine import Simulation
from civitas.model import Scenario
from civitas.persistence import checkpoint_load, checkpoint_save


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Scenario.from_file(ROOT / 'scenarios/population_normalized/o08_s00_n10000.json')


def sample(**overrides):
    values = dict(name='matched_access_toy', population=200, seed=91,
                  firms_per_sector=10, market_regions=5, capital_enabled=False,
                  initial_resource=50000, resource_capacity=60000,
                  transaction_trace=True, initial_firm_cash_cents=200000)
    values.update(overrides)
    return Scenario(**values)


@pytest.mark.parametrize('kwargs', [
    {'market_regions': 0}, {'market_regions': -1},
    {'market_regions': 3}, {'market_regions': 11},
    {'market_regions': 1.0}, {'market_regions': True},
    {'restrict_household_sales': 1}, {'restrict_labor_hiring': 'yes'},
])
def test_invalid_access_specifications_rejected(kwargs):
    with pytest.raises(ValueError):
        sample(**kwargs).validate()


def test_market_region_count_without_restriction_is_behaviorally_inert():
    base = replace(REFERENCE, seed=4)
    open_model = Simulation(base)
    dormant_regions = Simulation(replace(base, market_regions=10))
    np.testing.assert_array_equal(open_model.state.skills, dormant_regions.state.skills)
    assert open_model.rng.bit_generator.state == dormant_regions.rng.bit_generator.state
    for a, b in zip(open_model.run(8), dormant_regions.run(8)):
        assert a.metrics == b.metrics
        assert a.journal == b.journal


def test_identical_initial_agents_firms_owners_resource_money_and_rng():
    config = sample(capital_enabled=True, initial_capital_units_per_firm=50)
    snapshot = Simulation(config)
    r0 = copy.deepcopy(snapshot.rng.bit_generator.state)
    for sales in (False, True):
        for hiring in (False, True):
            arm = Simulation(replace(config, restrict_household_sales=sales,
                                     restrict_labor_hiring=hiring),
                             state=copy.deepcopy(snapshot.state), rng_state=copy.deepcopy(r0))
            assert arm.rng.bit_generator.state == r0
            for attr in ('household_of_agent', 'skills', 'participation', 'household_cash',
                         'household_savings', 'firm_cash', 'firm_capital', 'inventory', 'prices'):
                np.testing.assert_array_equal(getattr(arm.state, attr), getattr(snapshot.state, attr))
            assert all(np.array_equal(a,b) for a,b in zip(arm.state.firm_owner_households,
                                                         snapshot.state.firm_owner_households))
            assert arm.state.resource == snapshot.state.resource
            assert arm.state.initial_total_money == snapshot.state.initial_total_money


def test_sales_access_boundary_is_respected_and_not_vacuous():
    c = sample(restrict_household_sales=True, market_regions=5)
    sim = Simulation(c)
    n_sales = 0
    for period in sim.run(4):
        for t in period.transactions:
            if t['reason'] != 'sale':
                continue
            n_sales += 1
            assert sim.household_regions[t['source_id']] == sim.firm_regions[t['destination_id']]
    assert n_sales > 10


def test_labor_access_boundary_and_payments_are_respected():
    c = sample(restrict_labor_hiring=True)
    sim = Simulation(c)
    hired_count = 0
    for p in sim.run(3):
        hired = np.flatnonzero(sim.state.last_employment >= 0)
        assert (sim.agent_regions[hired] == sim.firm_regions[sim.state.last_employment[hired]]).all()
        assert p.metrics['money_discrepancy_cents'] == 0
        hired_count += len(hired)
    assert hired_count > 10


def test_access_only_experiment_rnd_stream_matched_and_checkpoint_resume(tmp_path):
    c = sample(restrict_household_sales=True, restrict_labor_hiring=True,
               capital_enabled=True, initial_capital_units_per_firm=50)
    full = Simulation(c)
    truth = [p.metrics for p in full.run(6)]
    partial = Simulation(c)
    first = [p.metrics for p in partial.run(3)]
    checkpoint = tmp_path / 'access.npz'
    checkpoint_save(checkpoint, c, partial.state, partial.rng.bit_generator.state)
    restored_c, restored_state, restored_rng = checkpoint_load(checkpoint)
    assert restored_c == c
    resumed = Simulation(restored_c, state=restored_state, rng_state=restored_rng)
    assert first + [p.metrics for p in resumed.run(3)] == truth


def test_no_population_edges_with_access_restrictions():
    sim = Simulation(sample(population=0, restrict_household_sales=True,
                            restrict_labor_hiring=True))
    for period in sim.run(2):
        assert period.metrics['production_units'] == 0
        assert period.metrics['consumption_units'] == 0
        assert period.metrics['money_discrepancy_cents'] == 0


def test_independent_sales_and_labor_factorial_runs():
    base = sample(seed=29)
    root = Simulation(base)
    initial_rng = copy.deepcopy(root.rng.bit_generator.state)
    actual = {}
    for sales in (False, True):
        for labor in (False, True):
            sim = Simulation(replace(base, restrict_household_sales=sales,
                                     restrict_labor_hiring=labor),
                             state=copy.deepcopy(root.state), rng_state=copy.deepcopy(initial_rng))
            for record in sim.run(3):
                assert all(record.metrics[k] == 0 for k in ('money_discrepancy_cents',
                    'goods_discrepancy_units', 'resource_discrepancy_units', 'capital_discrepancy_units',
                    'household_cashflow_discrepancy_cents', 'firm_cashflow_discrepancy_cents'))
            actual[(sales,labor)] = sim.rng.bit_generator.state
    assert all(val == next(iter(actual.values())) for val in actual.values())


def test_runner_small_replay_and_file_integrity(tmp_path):
    from research.run_matched_market_access import execute, read_verified, contrasts
    md,summary=execute(tmp_path, seeds=2, steps=3)
    assert md['simulations']==8 and md['audited_periods']==24
    rows,_=read_verified(tmp_path,2,3)
    assert len(rows)==24
    assert summary == contrasts(rows,2,3)
    path=tmp_path/'periods.csv'
    path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='sha256'):
        read_verified(tmp_path,2,3)


def test_factorial_interaction_formula_independent_toy_values():
    from research.run_matched_market_access import contrasts, METRICS
    fake={}
    for seed in (1,2):
        for arm,value in {'open':10.0,'sales_only':8.0,'labor_only':5.0,'both':4.0}.items():
            fake[(seed,1,arm)]={m:value for m in METRICS}
    output=contrasts(fake,2,1)
    assert output['paired_effects']['sales_labor_interaction']['production_per_person']['mean'] == 1.0
    assert output['paired_effects']['sales_given_open']['production_per_person']['mean']==-2.0
    assert output['paired_effects']['labor_given_open']['production_per_person']['mean']==-5.0


def test_seed_shards_validate_completeness(tmp_path):
    from research.run_matched_market_access import run_single_seed, finalize_shards, read_verified
    run_single_seed(tmp_path, 1, 2)
    with pytest.raises(FileNotFoundError):
        finalize_shards(tmp_path, 2, 2)
    run_single_seed(tmp_path, 2, 2)
    info, summary=finalize_shards(tmp_path,2,2)
    assert info['simulations']==8 and info['audited_periods']==16
    assert len(read_verified(tmp_path,2,2)[0])==16
    path=tmp_path/'seed_shards'/'seed_0002.csv'
    path.write_bytes(path.read_bytes()+b'X')
    with pytest.raises(ValueError,match='digest'):
        finalize_shards(tmp_path,2,2)
