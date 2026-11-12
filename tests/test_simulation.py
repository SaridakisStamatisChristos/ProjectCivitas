from dataclasses import replace
import json
from pathlib import Path
import numpy as np
import pytest
from civitas.engine import Simulation
from civitas.metrics import gini
from civitas.model import Scenario, Sector
from civitas.persistence import checkpoint_save, checkpoint_load, config_digest
from civitas.cli import main


def config(**kwargs):
    return replace(Scenario(name="test", population=120, steps=5, seed=29), **kwargs)


def test_determinism_and_seed_sensitivity():
    c = config()
    a = [p.metrics for p in Simulation(c).run()]
    b = [p.metrics for p in Simulation(c).run()]
    d = [p.metrics for p in Simulation(replace(c, seed=30)).run()]
    assert a == b
    assert a != d


def test_money_goods_and_resource_conserved():
    for c in (config(), config(tax_rate=0.35), config(initial_resource=0),
              config(automation_shock_step=1, automation_shock_increase=0.6)):
        sim = Simulation(c)
        for period in sim.run(8):
            m = period.metrics
            assert m["money_discrepancy_cents"] == 0
            assert m["goods_discrepancy_units"] == 0
            assert m["resource_discrepancy_units"] == 0
            assert (sim.state.inventory >= 0).all()
            assert (sim.state.household_cash >= 0).all()
            assert (sim.state.firm_cash >= 0).all()
            assert sim.state.resource >= 0


def test_tax_and_transfers_balanced():
    c = config(tax_rate=0.40, redistribution_share=1.0)
    periods = Simulation(c).run(3)
    for p in periods:
        m = p.metrics
        assert m["government_transfer_cents"] == m["government_tax_revenue_cents"]
        assert m["government_balance_cents"] == 0
        assert p.journal.get("wage_tax", {}).get("cents", 0) == m["government_tax_revenue_cents"]
        assert p.journal.get("transfer", {}).get("cents", 0) == m["government_transfer_cents"]


def test_zero_population_and_no_resources():
    sim = Simulation(config(population=0, initial_resource=0))
    periods = sim.run(3)
    assert all(p.metrics["production_units"] == 0 for p in periods)
    assert all(p.metrics["income_gini"] is None for p in periods)
    assert periods[-1].metrics["employment_rate"] is None
    assert sim.state.total_money() == sim.state.initial_total_money


def test_single_household_financial_constraints():
    sim = Simulation(config(population=1, household_size=1, initial_household_cash_cents=0,
                            initial_firm_cash_cents=0))
    result = sim.step().metrics
    assert result["production_units"] == 0
    assert result["consumption_units"] == 0
    assert result["total_money_cents"] == 0


def test_checkpoint_replay(tmp_path):
    c = config(population=110, automation_shock_step=4, automation_shock_increase=0.5)
    full = Simulation(c)
    full_periods = [p.metrics for p in full.run(9)]
    split = Simulation(c)
    first = [p.metrics for p in split.run(3)]
    p = tmp_path / "state.npz"
    checkpoint_save(p, c, split.state, split.rng.bit_generator.state)
    recovered_c, state, rng = checkpoint_load(p)
    later = Simulation(recovered_c, state=state, rng_state=rng)
    rest = [p.metrics for p in later.run(6)]
    assert full_periods == first + rest
    assert np.array_equal(full.state.household_cash, later.state.household_cash)
    assert np.array_equal(full.state.firm_cash, later.state.firm_cash)
    assert full.state.resource == later.state.resource


def test_config_rejects_incorrect_inputs():
    with pytest.raises(ValueError):
        Scenario.from_dict({"schema_version": 2})
    with pytest.raises(ValueError):
        Scenario.from_dict({"ghost_parameter": 1})
    for change in ({"tax_rate": -0.1}, {"automation_base": 1.1},
                   {"population": -10}, {"household_size": 0},
                   {"initial_resource": 2, "resource_capacity": 1},
                   {"automation_shock_step": -1}):
        with pytest.raises(ValueError):
            replace(config(), **change).validate()


def test_ledger_rejects_invalid_transfer_without_mutation():
    sim = Simulation(config())
    before = sim.state.total_money()
    with pytest.raises(ValueError):
        sim.state.transfer("household", 0, "firm", 0, 10**12, "invalid")
    with pytest.raises(ValueError):
        sim.state.transfer("household", 0, "firm", 0, -1, "invalid")
    assert sim.state.total_money() == before


def test_exact_toy_case_no_participants_no_money_creation():
    single = Sector("food", 1.0, 100, 50, 1.0, 1)
    c = config(population=2, household_size=2, firms_per_sector=1,
               sectors=(single,), labor_participation=0.0,
               initial_household_cash_cents=100, initial_firm_cash_cents=100,
               initial_resource=5, resource_capacity=5, regeneration_rate=0.0)
    sim = Simulation(c)
    p = sim.step()
    assert p.metrics["production_units"] == 0
    assert p.metrics["consumption_units"] == 0
    assert p.metrics["unmet_stock_demand_units"] == 1
    assert sim.state.resource == 5
    assert sim.state.total_money() == 200


def test_gini_cases():
    assert gini(np.array([10, 10])) == pytest.approx(0)
    assert gini(np.array([0, 10])) == pytest.approx(.5)
    assert gini(np.array([])) is None
    assert gini(np.array([0, 0])) is None


def test_automation_boundary_and_activation():
    c = config(automation_shock_step=2, automation_shock_increase=1)
    sim = Simulation(c)
    assert sim.automation == 0
    assert sim.step().metrics["automation_adoption"] == 0
    assert sim.step().metrics["automation_adoption"] == 0
    assert sim.step().metrics["automation_adoption"] == 1


def test_scenario_isolation_and_versioned_hash():
    a = config()
    b = replace(a, tax_rate=0.2)
    assert config_digest(a) != config_digest(b)
    run_a = [p.metrics for p in Simulation(a).run(3)]
    Simulation(b).run(3)
    assert [p.metrics for p in Simulation(a).run(3)] == run_a


def test_cli_run_and_resume(tmp_path):
    p = tmp_path / "scenario.json"
    p.write_text(json.dumps(config().to_dict()))
    first = tmp_path / "first"
    second = tmp_path / "second"
    assert main(["run", "--scenario", str(p), "--steps", "2", "--output", str(first)]) == 0
    assert (first / "metrics.csv").exists()
    assert (first / "experiments.sqlite3").exists()
    assert main(["resume", "--checkpoint", str(first / "checkpoint.npz"),
                 "--steps", "2", "--output", str(second)]) == 0
    assert (second / "checkpoint.npz").exists()


def test_finite_prices_and_large_population_smoke():
    sim = Simulation(config(population=10000))
    r = sim.step().metrics
    assert r["population"] == 10000
    assert r["money_discrepancy_cents"] == 0
    assert (sim.state.prices > 0).all()
