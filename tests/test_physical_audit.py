"""Adversarial replay and exact-accounting tests for physical stock/cost ledger."""
from dataclasses import replace
from copy import deepcopy
import json
import numpy as np
import pytest

from civitas.engine import Simulation
from civitas.model import Scenario, Sector
from civitas.physical_audit import (PhysicalAuditError, capture_physical_opening,
                                    audit_physical_period)
from civitas.persistence import checkpoint_save, checkpoint_load, save_run
from civitas.world_genesis import default_plan, resolve_plan


def scenario(**overrides):
    c = Scenario(name="physical-ledger", seed=41, population=80, firms_per_sector=2,
                 capital_enabled=True, initial_capital_units_per_firm=50,
                 capital_depreciation_rate=0.10, capital_investment_budget_share=0.25,
                 capital_output_per_unit=10, household_savings_rate=0.1,
                 credit_enabled=True, cost_basis_accounting_enabled=True,
                 resource_extraction_fee_cents_per_unit=3,
                 transaction_trace=True)
    return replace(c, **overrides)


def recorded(c=None):
    c = c or scenario()
    s = Simulation(c)
    opening = capture_physical_opening(s.state)
    p = s.step()
    return c, opening, s.state, p


def test_live_physical_replay_checks_firms_and_cost_bases():
    c, o, s, p = recorded()
    r = audit_physical_period(o, s, p, c)
    assert r.physical_event_count == len(p.physical_transactions) > 0
    assert r.production_units == p.metrics["production_units"]
    assert r.consumption_units == p.metrics["consumption_units"]
    assert r.resource_extracted_units == p.metrics["resource_extracted"]
    assert {x["kind"] for x in p.physical_transactions} >= {"manufacture", "depreciate", "consumer_sale"}


def test_resource_regeneration_after_first_period():
    c = scenario(resource_capacity=100000, initial_resource=50000, regeneration_rate=0.3)
    s = Simulation(c)
    for _ in range(4):
        opening = capture_physical_opening(s.state)
        p = s.step()
        r = audit_physical_period(opening, s.state, p, c)
        assert r.resource_regenerated_units == p.metrics["resource_regenerated"]
    assert sum(x["kind"] == "regenerate" for x in p.physical_transactions) == 1


def test_full_period_chain_with_and_without_history():
    for cost in (False, True):
        for credit in (False, True):
            c = scenario(cost_basis_accounting_enabled=cost, credit_enabled=(credit and cost))
            sim = Simulation(c)
            for _ in range(6):
                opening = capture_physical_opening(sim.state)
                p = sim.step()
                audit_physical_period(opening, sim.state, p, c)


def test_disable_tracing_requires_explicit_replay():
    c = scenario(transaction_trace=False)
    s = Simulation(c)
    opening = capture_physical_opening(s.state)
    p = s.step()
    assert p.physical_transactions == []
    with pytest.raises(PhysicalAuditError, match="trace"):
        audit_physical_period(opening, s.state, p, c)


@pytest.mark.parametrize("field, value", [("units", True), ("units", -1),
                                         ("units", 2**63), ("firm", 123456)])
def test_bad_event_quantity_or_firm_rejected(field, value):
    c, opening, state, p = recorded()
    changed = deepcopy(p)
    event = next(x for x in changed.physical_transactions if x["kind"] == "manufacture")
    event[field] = value
    with pytest.raises(PhysicalAuditError):
        audit_physical_period(opening, state, changed, c)


def test_duplicate_or_missing_event_rejected():
    c, opening, state, p = recorded()
    altered = deepcopy(p)
    altered.physical_transactions.append(deepcopy(altered.physical_transactions[0]))
    with pytest.raises(PhysicalAuditError):
        audit_physical_period(opening, state, altered, c)
    altered = deepcopy(p)
    altered.physical_transactions.pop()
    with pytest.raises(PhysicalAuditError):
        audit_physical_period(opening, state, altered, c)


def test_closing_inventory_reallocated_keeps_global_sum_but_replay_fails():
    c, opening, state, p = recorded()
    altered = deepcopy(state)
    assert len(altered.inventory) >= 2 and int(altered.inventory[1]) > 0
    altered.inventory[0] += 1
    altered.inventory[1] -= 1
    assert altered.inventory.sum() == state.inventory.sum()
    with pytest.raises(PhysicalAuditError, match="inventory"):
        audit_physical_period(opening, altered, p, c)


def test_cash_sales_and_physical_sales_must_match():
    c, opening, state, p = recorded()
    altered = deepcopy(p)
    event = next(x for x in altered.physical_transactions if x["kind"] == "consumer_sale")
    event["price_cents"] += 1
    with pytest.raises(PhysicalAuditError, match="opening quote"):
        audit_physical_period(opening, state, altered, c)


def test_resource_intensity_and_basis_falsification_detected():
    c, opening, state, p = recorded()
    altered = deepcopy(p)
    event = next(x for x in altered.physical_transactions if x["kind"] == "manufacture")
    event["resource_units"] += 1
    with pytest.raises(PhysicalAuditError, match="intensity"):
        audit_physical_period(opening, state, altered, c)
    altered = deepcopy(p)
    event = next(x for x in altered.physical_transactions if x["kind"] == "manufacture")
    event["basis_cents"] += 1
    with pytest.raises(PhysicalAuditError):
        audit_physical_period(opening, state, altered, c)


def test_balance_metrics_falsification_detected():
    c, opening, state, p = recorded()
    for key in ("resource_extracted", "production_units", "firm_inventory_historical_cost_cents"):
        altered = deepcopy(p)
        altered.metrics[key] += 1
        with pytest.raises(PhysicalAuditError, match="metric"):
            audit_physical_period(opening, state, altered, c)


def test_capital_conversion_and_payment_match():
    c = scenario(population=20, firms_per_sector=1, initial_capital_units_per_firm=1,
                 capital_output_per_unit=1, capital_depreciation_rate=0,
                 capital_target_buffer=1.0, initial_firm_cash_cents=50000,
                 capital_investment_budget_share=0.5)
    sim = Simulation(c)
    # Carry a real inventory into the period without falsely treating the
    # product as newly created. Its cumulative stock identity is updated too.
    supplier = next(i for i,s in enumerate(c.sectors) if s.name == c.capital_input_sector)
    sim.state.inventory[supplier] += 10
    sim.state.cumulative_output[supplier] += 10
    before = capture_physical_opening(sim.state)
    p = sim.step()
    conversion = [x for x in p.physical_transactions if x["kind"] == "convert_capital"]
    assert conversion, "the fixture must exercise physical capital conversion"
    assert any(x["buyer"] != x["supplier"] for x in conversion)
    audit_physical_period(before, sim.state, p, c)
    changed = deepcopy(p)
    x = next(x for x in changed.physical_transactions if x["kind"] == "convert_capital")
    x["buyer"] = 100000
    with pytest.raises(PhysicalAuditError):
        audit_physical_period(before, sim.state, changed, c)


def test_checkpoint_replay_and_legacy_trace_invariance(tmp_path):
    c = scenario(population=40)
    traced = Simulation(c)
    normal = Simulation(replace(c, transaction_trace=False))
    for _ in range(3):
        a = traced.step()
        b = normal.step()
        assert a.metrics == b.metrics
        assert a.journal == b.journal
    assert traced.rng.bit_generator.state == normal.rng.bit_generator.state
    archive = tmp_path / "physical.npz"
    checkpoint_save(archive, c, traced.state, traced.rng.bit_generator.state)
    rc, state, rng = checkpoint_load(archive)
    restarted = Simulation(rc, state=state, rng_state=rng)
    before = capture_physical_opening(restarted.state)
    p = restarted.step()
    assert audit_physical_period(before, restarted.state, p, rc).physical_event_count > 0
    assert p.metrics == traced.step().metrics


def test_random_hybrid_genesis_world_supports_physical_replay():
    for seed in (3, 5, 11):
        c = resolve_plan(default_plan(mode="hybrid", seed=seed, name="physical-genesis", population=80))
        c = replace(c, transaction_trace=True)
        sim = Simulation(c)
        for _ in range(3):
            before = capture_physical_opening(sim.state)
            p = sim.step()
            assert audit_physical_period(before, sim.state, p, c).production_units == p.metrics["production_units"]


def test_physical_trace_is_exported_with_step_and_replay(tmp_path):
    c = scenario()
    sim = Simulation(c)
    before = capture_physical_opening(sim.state)
    p = sim.step()
    audit_physical_period(before, sim.state, p, c)
    save_run(tmp_path, c, [p], seed=c.seed, elapsed_seconds=0)
    export = tmp_path / "physical_transactions.jsonl"
    assert export.is_file()
    data = [json.loads(line) for line in export.read_text().splitlines()]
    assert len(data) == len(p.physical_transactions)
    assert all(x["step"] == p.metrics["step"] for x in data)


def test_research_campaign_recounts_and_exactly_replays(tmp_path):
    from research.run_physical_closure import execute, verify_summary, verify_replay
    output = tmp_path / "campaign"
    result = execute(seeds=(1, 2), steps=3, population=48, output=output)
    assert result["runs"] == 8
    assert result["audited_periods"] == 24
    assert result["physical_events"] > 0
    assert result["cash_transfers"] > 0
    assert verify_summary(output / "summary.json") == result
    assert verify_replay(output / "summary.json") == result


def test_research_campaign_rejects_missing_or_altered_result(tmp_path):
    from research.run_physical_closure import execute, verify_summary
    path = tmp_path / "trial"
    execute(seeds=(1,), steps=1, population=32, output=path)
    document = path / "summary.json"
    altered = json.loads(document.read_text())
    altered["rows"][0]["physical_events"] += 1
    document.write_text(json.dumps(altered))
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_summary(document)
    document.unlink()
    with pytest.raises(FileNotFoundError):
        verify_summary(document)


def test_research_campaign_refuses_duplicate_or_invalid_seeds(tmp_path):
    from research.run_physical_closure import execute
    for params in ({"seeds": (1, 1)}, {"seeds": ()}, {"seeds": (-1,)},
                   {"steps": 0}, {"population": -1}):
        with pytest.raises(ValueError):
            execute(output=tmp_path, **params)


def test_invalid_capital_conversion_cost_fails_audit():
    c = scenario(population=20, firms_per_sector=1, initial_capital_units_per_firm=1,
                 capital_output_per_unit=1, capital_depreciation_rate=0,
                 capital_target_buffer=1.0, initial_firm_cash_cents=50000,
                 capital_investment_budget_share=0.5)
    s = Simulation(c)
    idx = next(i for i, sec in enumerate(c.sectors) if sec.name == c.capital_input_sector)
    s.state.inventory[idx] += 12
    s.state.cumulative_output[idx] += 12
    opening = capture_physical_opening(s.state)
    p = s.step()
    cap = next(x for x in p.physical_transactions if x["kind"] == "convert_capital")
    assert cap["capital_cost_cents"] > 0
    tampered = deepcopy(p)
    event = next(x for x in tampered.physical_transactions if x["kind"] == "convert_capital")
    event["capital_cost_cents"] += 1
    with pytest.raises(PhysicalAuditError, match="asset basis"):
        audit_physical_period(opening, s.state, tampered, c)


def test_physical_events_out_of_stage_order_are_rejected():
    c, opening, state, p = recorded()
    tampered = deepcopy(p)
    events = tampered.physical_transactions
    sale = next(i for i,x in enumerate(events) if x["kind"] == "consumer_sale")
    manufacturing = next(i for i,x in enumerate(events) if x["kind"] == "manufacture")
    events[sale], events[manufacturing] = events[manufacturing], events[sale]
    with pytest.raises(PhysicalAuditError):
        audit_physical_period(opening, state, tampered, c)
