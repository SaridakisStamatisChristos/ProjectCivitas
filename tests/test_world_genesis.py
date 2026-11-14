"""World Genesis: invariants, backward compatibility, tampering and replay."""
from __future__ import annotations
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from civitas.cli import main
from civitas.engine import Simulation
from civitas.model import Scenario, Sector
from civitas.persistence import checkpoint_load, checkpoint_save
from civitas.world_genesis import (default_plan, resolve_plan, state_fingerprint,
                                   verify_world, write_world)


def plan(mode="hybrid", seed=11, population=120):
    return default_plan(mode=mode, seed=seed, population=population, name="genesis_test")


def test_legacy_state_and_trajectory_equal_configured_mode():
    old = Scenario(name="genesis_test", population=120, seed=11)
    assert "world_genesis" not in old.to_dict()
    generated = resolve_plan(plan("configured"))
    a = Simulation(old)
    b = Simulation(generated)
    assert state_fingerprint(a.state) == state_fingerprint(b.state)
    assert a.rng.bit_generator.state == b.rng.bit_generator.state
    assert [x.metrics for x in a.run(5)] == [x.metrics for x in b.run(5)]


def test_hybrid_replay_independent_of_call_order():
    c = resolve_plan(plan("hybrid"))
    a, b = Simulation(c), Simulation(c)
    assert state_fingerprint(a.state) == state_fingerprint(b.state)
    assert a.rng.bit_generator.state == b.rng.bit_generator.state
    assert [x.metrics for x in a.run(6)] == [x.metrics for x in b.run(6)]


def test_hybrid_cash_and_firm_cash_preserve_exact_totals_and_inequality():
    c = resolve_plan(plan(population=160))
    s = Simulation(c).state
    assert int(s.household_cash.sum()) == 40 * c.initial_household_cash_cents
    assert int(s.firm_cash.sum()) == len(s.firm_cash) * c.initial_firm_cash_cents
    assert len(set(s.household_cash.tolist())) > 2
    assert len(set(s.firm_cash.tolist())) > 2
    assert s.total_money() == s.initial_total_money
    s.validate()


def test_randomized_scalar_draws_are_saved_and_reproducible():
    p = plan("randomized")
    a, b = resolve_plan(p), resolve_plan(p)
    assert a.to_dict() == b.to_dict()
    assert 90 <= a.population <= 150
    assert a.firms_per_sector in {2, 3, 4, 6}
    assert 0 <= a.tax_rate <= 0.25
    assert a != resolve_plan(plan("randomized", seed=12))


def test_per_field_rng_isolation():
    p1 = plan()
    p2 = plan()
    p2["initialization"].pop("skills")
    a, b = Simulation(resolve_plan(p1)), Simulation(resolve_plan(p2))
    assert np.array_equal(a.state.household_cash, b.state.household_cash)
    assert np.array_equal(a.state.firm_cash, b.state.firm_cash)
    assert np.array_equal(a.state.prices, b.state.prices)
    assert a.rng.bit_generator.state == b.rng.bit_generator.state


def test_fixed_initial_balances_override_in_configured_mode():
    p = plan("configured")
    p["initialization"] = {"household_cash_cents": {"distribution": "fixed", "value": 1234},
                           "firm_cash_cents": {"distribution": "fixed", "value": 5678}}
    sim = Simulation(resolve_plan(p))
    assert np.all(sim.state.household_cash == 1234)
    assert np.all(sim.state.firm_cash == 5678)
    assert sim.state.initial_total_money == len(sim.state.household_cash) * 1234 + len(sim.state.firm_cash) * 5678


def test_fixed_preserving_funds_is_explicit():
    p = plan("configured")
    p["initialization"] = {"household_cash_cents": {"distribution": "fixed", "value": 999,
                                                      "preserve_total": True}}
    sim = Simulation(resolve_plan(p))
    assert np.all(sim.state.household_cash == sim.scenario.initial_household_cash_cents)


def test_constant_skill_and_participation_probability():
    p = plan("configured")
    p["initialization"] = {"skills": {"distribution": "fixed", "value": 1.1},
                           "participation_probability": {"distribution": "fixed", "value": 0.0},
                           "price_multiplier": {"distribution": "fixed", "value": 1.1}}
    sim = Simulation(resolve_plan(p))
    assert np.all(sim.state.skills == 1.1)
    assert not np.any(sim.state.participation)
    assert np.all(sim.state.prices > 0)


def test_capital_heterogeneity_reconciles_cost_basis():
    p = plan()
    p["base_scenario"].update({"capital_enabled": True, "cost_basis_accounting_enabled": True,
                               "initial_capital_units_per_firm": 11})
    p["initialization"]["firm_capital_units"] = {"distribution": "uniform_int", "low": 1, "high": 20,
                                                     "preserve_total": True}
    c = resolve_plan(p)
    s = Simulation(c).state
    assert s.initial_capital_total == len(s.firm_capital) * 11
    assert np.all(s.firm_capital_basis_cents == s.firm_capital * next(q.price_cents for q in c.sectors if q.name == c.capital_input_sector))
    assert len(set(s.firm_capital.tolist())) > 1
    s.validate()


def test_initial_checkpoint_and_full_replay(tmp_path):
    c = resolve_plan(plan())
    full = Simulation(c)
    expected = [x.metrics for x in full.run(6)]
    split = Simulation(c)
    first = [x.metrics for x in split.run(2)]
    path = tmp_path / "state.npz"
    checkpoint_save(path, c, split.state, split.rng.bit_generator.state)
    recovered, state, rng = checkpoint_load(path)
    rest = [x.metrics for x in Simulation(recovered, state=state, rng_state=rng).run(4)]
    assert expected == first + rest


def test_generate_and_verify_roundtrip_and_tamper(tmp_path):
    target = tmp_path / "world"
    write_world(target, plan())
    assert verify_world(target)["verified"] is True
    with pytest.raises(FileExistsError):
        write_world(target, plan())
    manifest = json.loads((target / "manifest.json").read_text())
    manifest["total_initial_money_cents"] += 1
    (target / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="mismatch"):
        verify_world(target)
    write_world(target, plan(), force=True)
    assert verify_world(target)["verified"]


def test_cli_genesis_verify_run_and_resume(tmp_path):
    target=tmp_path / "world"
    assert main(["genesis", "--mode", "hybrid", "--seed", "17", "--population", "80", "--output", str(target)]) == 0
    assert main(["verify-world", "--world", str(target)]) == 0
    assert main(["run", "--scenario", str(target / "scenario.json"), "--steps", "2",
                 "--output", str(tmp_path / "run")]) == 0
    assert main(["resume", "--checkpoint", str(target / "initial_checkpoint.npz"),
                 "--steps", "2", "--output", str(tmp_path / "resume")]) == 0


@pytest.mark.parametrize("change", [
    lambda p: p.update({"unexpected": 1}),
    lambda p: p.update({"mode": "magical"}),
    lambda p: p.update({"seed": -1}),
    lambda p: p.update({"initialization": {"unknown": {"distribution": "fixed", "value": 3}}}),
    lambda p: p.update({"initialization": {"household_cash_cents": {"distribution": "eval", "value": "1"}}}),
    lambda p: p.update({"initialization": {"household_cash_cents": {"distribution": "uniform_int", "low": 2, "high": 1}}}),
    lambda p: p.update({"initialization": {"skills": {"distribution": "uniform", "low": -1, "high": 2}}}),
    lambda p: p.update({"initialization": {"price_multiplier": {"distribution": "fixed", "value": float("nan")}}}),
    lambda p: p.update({"scenario_draws": {"seed": {"distribution": "fixed", "value": 1}}}),
    lambda p: p.update({"base_scenario": {"population": -1}}),
])
def test_reject_invalid_plans(change):
    p = plan()
    change(p)
    with pytest.raises((ValueError, TypeError)):
        resolve_plan(p)


def test_configured_forbids_stochastic_draw():
    p = plan("configured")
    p["scenario_draws"] = {"population": {"distribution": "uniform_int", "low": 10, "high": 100}}
    with pytest.raises(ValueError):
        resolve_plan(p)


def test_scenario_rejects_invalid_embedded_world_definition():
    c=resolve_plan(plan())
    for change in (dict(c.world_genesis, seed=-1), dict(c.world_genesis, initialization={"unknown": {"distribution": "fixed", "value": 2}})):
        with pytest.raises(ValueError):
            replace(c, world_genesis=change).validate()


def test_preservation_under_zero_agents():
    p=plan(population=0)
    c=resolve_plan(p)
    s=Simulation(c).state
    assert s.total_money()==s.initial_total_money
    assert len(s.household_cash)==0
    assert s.validate() is None


def test_initial_savings_split_conserves_wealth_and_finances_from_real_stock():
    p=plan("configured", population=80)
    p["initialization"] = {"household_savings_fraction": {"distribution": "fixed", "value": 0.4}}
    c=resolve_plan(p)
    s=Simulation(c).state
    assert sum(map(int, s.household_savings)) == len(s.household_savings) * 6000
    assert sum(map(int, s.household_cash)) == len(s.household_cash) * 9000
    assert s.total_money() == s.initial_total_money
    s.validate()


def test_savings_fraction_rng_independent_of_cash_draw():
    p1=plan()
    p2=plan()
    p2["initialization"]["household_savings_fraction"] = {"distribution":"uniform", "low": 0.1, "high":0.7}
    a,b=Simulation(resolve_plan(p1)),Simulation(resolve_plan(p2))
    assert np.array_equal(a.state.firm_cash,b.state.firm_cash)
    assert np.array_equal(a.state.prices,b.state.prices)
    assert np.array_equal(a.state.household_cash, b.state.household_cash+b.state.household_savings)
    assert a.state.initial_total_money==b.state.initial_total_money


def test_randomized_requires_randomness():
    p=plan("randomized")
    p["initialization"] = {}
    p["scenario_draws"] = {"population": {"distribution":"fixed", "value":120}}
    with pytest.raises(ValueError):
        resolve_plan(p)
