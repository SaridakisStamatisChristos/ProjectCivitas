"""Analytical, compatibility, and adversarial tests for price/hiring alternatives."""
from dataclasses import replace
import math

import numpy as np
import pytest

from civitas.engine import Simulation
from civitas.market_rules import expected_sales, updated_price
from civitas.model import Scenario, Sector
from civitas.persistence import checkpoint_save, checkpoint_load
from research.run_demand_diagnostics import scenarios


def test_expected_sales_independent_analytical_cases():
    args = dict(period=2, sector_household_demand=20.0,
                firm_last_sales=2, sector_last_unmet_per_firm=1.0)
    assert expected_sales(rule="adaptive", **args) == 5
    assert expected_sales(rule="stationary", **args) == 20
    assert expected_sales(rule="blended", **args) == 12.5
    for rule in ("adaptive", "stationary", "blended"):
        assert expected_sales(rule=rule, **(args | {"period": 0})) == 20
    with pytest.raises(ValueError):
        expected_sales(rule="not_a_rule", **args)


def test_legacy_price_equation_exact_integer_rounding():
    assert updated_price(current=101, stock=0, units_sold=1, excess_threshold=2,
                         adjustment=0.02, floor=1) == math.ceil(101 * 1.02)
    assert updated_price(current=101, stock=8, units_sold=0, excess_threshold=2,
                         adjustment=0.02, floor=100) == 100
    assert updated_price(current=101, stock=2, units_sold=1, excess_threshold=2,
                         adjustment=0.02, floor=1) == 101
    assert updated_price(current=1, stock=0, units_sold=1, excess_threshold=2,
                         adjustment=0, floor=1) == 1


def test_scenario_rejects_invalid_market_parameters():
    base = scenarios(population=80, steps=48)[0]
    for bad in ("bad", "", [], None):
        with pytest.raises(ValueError):
            replace(base, price_update_rule=bad).validate()
    for bad in (-0.01, 1.01, float("nan"), "25%"):
        with pytest.raises(ValueError):
            replace(base, price_affordability_floor=bad).validate()
    with pytest.raises(ValueError):
        replace(base, hiring_expectation_rule="unbounded").validate()


def test_zero_firms_stock_and_zero_population_edge_cases():
    a = replace(Scenario(name="empty"), population=0, firms_per_sector=2,
                price_update_rule="affordability_guard", hiring_expectation_rule="blended")
    s = Simulation(a)
    for p in s.run(3):
        assert p.metrics["money_discrepancy_cents"] == 0
        assert p.metrics["goods_discrepancy_units"] == 0


def test_full_long_run_invariants_and_replay(tmp_path):
    base = scenarios(population=96, steps=48)[0]
    cfg = replace(base, seed=29, price_update_rule="affordability_guard",
                  price_affordability_floor=0.4, hiring_expectation_rule="blended")
    sim = Simulation(cfg)
    for _ in range(12):
        m = sim.step().metrics
        for k in ("money_discrepancy_cents", "resource_discrepancy_units",
                  "goods_discrepancy_units", "capital_discrepancy_units",
                  "household_cashflow_discrepancy_cents", "firm_cashflow_discrepancy_cents",
                  "loan_discrepancy_cents"):
            assert m[k] == 0
    f = tmp_path / "state.npz"
    checkpoint_save(f, cfg, sim.state, sim.rng.bit_generator.state)
    c2, st2, rng2 = checkpoint_load(f)
    resumed = Simulation(c2, state=st2, rng_state=rng2)
    for _ in range(20):
        assert sim.step().metrics == resumed.step().metrics
    assert sim.rng.bit_generator.state == resumed.rng.bit_generator.state


def test_new_rules_share_initial_population_and_random_stream():
    base = scenarios(population=112, steps=48)[0]
    sims = [Simulation(replace(base, seed=11, price_update_rule=rule,
                               hiring_expectation_rule=hiring))
            for rule in ("inventory", "affordability_guard")
            for hiring in ("adaptive", "blended", "stationary")]
    for s in sims[1:]:
        np.testing.assert_array_equal(s.state.household_cash, sims[0].state.household_cash)
        np.testing.assert_array_equal(s.state.skills, sims[0].state.skills)
        np.testing.assert_array_equal(s.state.firm_cash, sims[0].state.firm_cash)
    for _ in range(7):
        for sim in sims:
            sim.step()
        assert all(sim.rng.bit_generator.state == sims[0].rng.bit_generator.state for sim in sims)


def test_default_trajectory_matches_explicit_historical_settings():
    c = replace(scenarios(population=150, steps=48)[0], seed=37)
    a = Simulation(c)
    b = Simulation(replace(c, price_update_rule="inventory",
                           price_affordability_floor=0.25,
                           hiring_expectation_rule="adaptive"))
    assert [p.metrics for p in a.run(16)] == [p.metrics for p in b.run(16)]


def test_guard_protects_hikes_not_inventory_based_price_decreases():
    # First make sure a conventional stockout produces a price increase.
    sector = Sector("food", 1.0, 100, 0, 1.0, 1)
    cfg = Scenario(name="one_good", population=4, household_size=4,
                   firms_per_sector=1, initial_household_cash_cents=100,
                   initial_firm_cash_cents=100, initial_resource=100,
                   resource_capacity=100, regeneration_rate=0,
                   price_adjustment=0.5, output_inventory_buffer=0,
                   labor_participation=1.0, sectors=(sector,),
                   household_savings_rate=0)
    old = Simulation(cfg)
    old.step()
    assert old.state.prices[0] == 150
    guarded = Simulation(replace(cfg, price_update_rule="affordability_guard",
                                 price_affordability_floor=1.0))
    guarded.step()
    assert guarded.state.prices[0] == 100
    assert old.state.inventory[0] == guarded.state.inventory[0]
    assert old.state.total_money() == guarded.state.total_money()


def test_resumable_factorial_and_tamper_rejection(tmp_path):
    import gzip
    import json
    from research.run_price_hiring_stability import (
        configs, execute_seed, finalize, verify_cell, digest, encoded,
    )
    assert len(configs(population=80, steps=48)) == 6
    assert execute_seed(tmp_path, 7, population=80, steps=48)["periods"] == 288
    assert execute_seed(tmp_path, 7, population=80, steps=48)["runs"] == 6
    report = finalize(tmp_path, [7], population=80, steps=48)
    assert report["design"]["audited_periods"] == 288
    assert report["paired"]["price_hiring_interaction__blended_t48"]["n"] == 1
    c = replace(configs(population=80, steps=48)[0], seed=7)
    path = tmp_path / "seed_0007" / f"{c.name}.json.gz"
    with gzip.open(path, "rb") as f:
        record = json.loads(f.read())
    record["periods"][0]["money_discrepancy_cents"] = 5
    with gzip.open(path, "wb") as f:
        f.write(encoded(record))
    with pytest.raises(ValueError, match="checksum"):
        verify_cell(path, c)
    record.pop("sha256", None)
    record["sha256"] = digest(record)
    with gzip.open(path, "wb") as f:
        f.write(encoded(record))
    with pytest.raises(ValueError, match="accounting discrepancy"):
        verify_cell(path, c)


def test_incomplete_factorial_rejected(tmp_path):
    from research.run_price_hiring_stability import configs, execute_cell, finalize
    cfg = replace(configs(80, 48)[0], seed=1)
    execute_cell(tmp_path, cfg)
    with pytest.raises(FileNotFoundError):
        finalize(tmp_path, [1], population=80, steps=48)
    with pytest.raises(ValueError):
        finalize(tmp_path, [1,1], population=80, steps=48)


def test_independent_auditor_detects_tampered_summary(tmp_path):
    import json
    from research.run_price_hiring_stability import execute_seed, finalize
    from research.audit_price_hiring_stability import audit
    execute_seed(tmp_path, 3, population=84, steps=48)
    finalize(tmp_path, [3], population=84, steps=48)
    assert audit(tmp_path)["audited_periods"] == 288
    file=tmp_path/"summary.json"
    record=json.loads(file.read_text())
    record["means"]["inventory__adaptive_t48"]["production_units"]["mean"]+=1
    file.write_text(json.dumps(record))
    with pytest.raises(ValueError,match="saved statistical mean"):
        audit(tmp_path)


def test_safe_archive_restore_and_audit(tmp_path):
    import io
    import json
    import gzip
    import tarfile
    from research.run_price_hiring_stability import execute_seed, finalize
    from research.restore_price_hiring_stability import restore

    source = tmp_path / "source"
    execute_seed(source, 7, population=80, steps=48)
    finalize(source, [7], population=80, steps=48)
    archive = tmp_path / "valid.tar.xz"
    with tarfile.open(archive, "w:xz") as t:
        for path in source.rglob("*"):
            if not path.is_file():
                continue
            data = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
            name = path.relative_to(source).as_posix()
            if name.endswith(".json.gz"):
                name = name[:-3]
            tarinfo = tarfile.TarInfo(name)
            tarinfo.size = len(data)
            t.addfile(tarinfo, io.BytesIO(data))
    assert restore(archive, tmp_path/"restored")["audited_periods"] == 288
    with pytest.raises(FileExistsError):
        restore(archive, tmp_path/"restored")
    invalid = tmp_path/"invalid.tar.xz"
    with tarfile.open(invalid, "w:xz") as t:
        payload = b"{}"
        info = tarfile.TarInfo("../overwrite.json")
        info.size = len(payload)
        t.addfile(info, io.BytesIO(payload))
    with pytest.raises(ValueError, match="unsafe archive"):
        restore(invalid, tmp_path/"not_restored")
    assert not (tmp_path/"not_restored").exists()


def test_zero_affordability_threshold_is_exact_historical_path():
    # Guard at τ=0 must never veto a proposed price increase.
    baseline = replace(scenarios(240, 48)[0], seed=23)
    original = Simulation(baseline)
    zero_guard = Simulation(replace(baseline, price_update_rule="affordability_guard",
                                    price_affordability_floor=0))
    assert [step.metrics for step in original.run(48)] == [step.metrics for step in zero_guard.run(48)]
