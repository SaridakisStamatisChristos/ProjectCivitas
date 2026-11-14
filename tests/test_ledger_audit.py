"""Independent journal replay, including adverse and noncash credit paths."""
from __future__ import annotations
from dataclasses import replace
from copy import deepcopy
import json
import numpy as np
import pytest

from civitas.engine import Simulation
from civitas.finance import CreditFlows, originate
from civitas.ledger_audit import LedgerAuditError, audit_period, capture_opening
from civitas.model import Scenario, Sector
from civitas.persistence import checkpoint_load, checkpoint_save, save_run
from civitas.world_genesis import default_plan, resolve_plan


def traced(**kwargs):
    return replace(Scenario(name="ledger-example", population=80, firms_per_sector=2,
                            seed=5, transaction_trace=True, tax_rate=0.3,
                            household_savings_rate=0.1, savings_emergency_food_enabled=True,
                            resource_extraction_fee_cents_per_unit=4), **kwargs)


def one_period():
    s = Simulation(traced())
    opening = capture_opening(s.state)
    p = s.step()
    return opening, s.state, p


def test_reconstructs_all_cash_accounts_and_journal_without_engine_helpers():
    opening, closing, period = one_period()
    report = audit_period(opening, closing, period)
    assert report.transfer_count == len(period.transactions) > 0
    assert report.transfer_cents == sum(x["cents"] for x in period.transactions)
    assert report.noncash_writeoff_count == 0
    assert report.money_stock_cents == closing.initial_total_money
    assert {x["reason"] for x in period.transactions} >= {"wages", "wage_tax", "sale", "resource_fee"}


def test_replay_catches_account_level_misposting_even_when_total_money_balances():
    opening, closing, p = one_period()
    # A duplicated transfer moves money between two recorded participants,
    # keeping global money stock constant but breaking participant balances.
    falsified = deepcopy(p)
    falsified.transactions.append(deepcopy(falsified.transactions[0]))
    with pytest.raises(LedgerAuditError):
        audit_period(opening, closing, falsified)


def test_replay_catches_closing_state_balanced_but_assigned_to_wrong_household():
    opening, closing, p = one_period()
    tampered = deepcopy(closing)
    tampered.household_cash[0] += 1
    tampered.household_cash[1] -= 1
    with pytest.raises(LedgerAuditError, match="household"):
        audit_period(opening, tampered, p)


@pytest.mark.parametrize("mutate", [
    lambda p: p.transactions[0].__setitem__("reason", "sale"),
    lambda p: p.transactions[0].__setitem__("cents", True),
    lambda p: p.transactions[0].__setitem__("source_id", -1),
    lambda p: p.transactions[0].__setitem__("destination_id", 2**53),
    lambda p: p.transactions[0].__setitem__("cents", 2**63),
    lambda p: p.journal["wages"].__setitem__("count", 7_777),
    lambda p: p.journal["wages"].__setitem__("count", True),
    lambda p: p.metrics.__setitem__("sales_cents", -22),
])
def test_adversarial_transaction_journal_and_metric_mutations(mutate):
    opening, closing, p = one_period()
    altered = deepcopy(p)
    mutate(altered)
    with pytest.raises(LedgerAuditError):
        audit_period(opening, closing, altered)


def test_no_trace_never_passes_as_a_complete_audit():
    sim = Simulation(replace(traced(), transaction_trace=False))
    before = capture_opening(sim.state)
    p = sim.step()
    with pytest.raises(LedgerAuditError, match="transaction tracing"):
        audit_period(before, sim.state, p)


def test_credit_claims_defaults_and_monetary_transfers_reconcile(tmp_path):
    c = traced(
        population=4, household_size=1, firms_per_sector=1, tax_rate=0.0,
        savings_emergency_food_enabled=False, household_savings_rate=0.0,
        capital_enabled=True, initial_capital_units_per_firm=10,
        capital_investment_budget_share=0.0,
        cost_basis_accounting_enabled=True, credit_enabled=True,
        credit_repayment_fraction=0.0, credit_term_periods=1,
        credit_firm_cash_reserve_cents=0,
        sectors=(Sector("goods", 0.1, 100, 50, 2.0, 2),),
    )
    sim = Simulation(c)
    state = sim.state
    state.household_savings[0] += 1000
    state.household_cash[0] -= 1000
    flows = CreditFlows.empty(state)
    state.trace_enabled = True
    assert originate(state, 0, 500, state.household_savings.copy(), flows) == 500
    state.validate()
    opening1 = capture_opening(state)
    first = sim.step()
    assert audit_period(opening1, state, first).outstanding_claims_cents == 500
    opening2 = capture_opening(state)
    second = sim.step()
    result = audit_period(opening2, state, second)
    assert result.noncash_writeoff_count == 1
    assert result.noncash_writeoff_cents == 500
    assert result.outstanding_claims_cents == 0
    assert second.journal["loan_default_noncash"]["cents"] == 500
    assert not any(tx["reason"] == "loan_default_noncash" for tx in second.transactions)
    save_run(tmp_path, c, [first, second], seed=c.seed, elapsed_seconds=0)
    written = (tmp_path / "noncash_transactions.jsonl").read_text().splitlines()
    assert len(written) == 1
    assert json.loads(written[0])["cents"] == 500
    corrupt = deepcopy(second)
    corrupt.noncash_transactions[0]["borrower_firm"] = 400
    with pytest.raises(LedgerAuditError, match="creditor/debtor"):
        audit_period(opening2, state, corrupt)
    corrupt = deepcopy(second)
    corrupt.noncash_transactions.append(deepcopy(corrupt.noncash_transactions[0]))
    with pytest.raises(LedgerAuditError):
        audit_period(opening2, state, corrupt)


def test_trace_preserves_default_model_trajectory():
    a = Simulation(traced(transaction_trace=False))
    b = Simulation(traced(transaction_trace=True))
    for _ in range(5):
        ap, bp = a.step(), b.step()
        assert ap.metrics == bp.metrics
        assert ap.journal == bp.journal
    assert a.rng.bit_generator.state == b.rng.bit_generator.state


def test_checkpoint_continuation_ledger_audit_still_functions(tmp_path):
    c = traced(population=30)
    sim = Simulation(c)
    sim.run(2)
    p = tmp_path / "checkpoint.npz"
    checkpoint_save(p, c, sim.state, sim.rng.bit_generator.state)
    rc, state, rng = checkpoint_load(p)
    restart = Simulation(rc, state=state, rng_state=rng)
    opening = capture_opening(restart.state)
    result = restart.step()
    assert audit_period(opening, restart.state, result).money_stock_cents == state.initial_total_money


def test_random_world_replay_and_ledger_audit():
    plan = default_plan(mode="hybrid", seed=123, name="ledger-world", population=80)
    c = resolve_plan(plan)
    c = replace(c, transaction_trace=True)
    s = Simulation(c)
    for _ in range(3):
        start = capture_opening(s.state)
        period = s.step()
        assert audit_period(start, s.state, period).money_stock_cents == s.state.initial_total_money


def test_empty_zero_cash_world_replays_with_no_transactions():
    sim = Simulation(traced(population=0, initial_resource=0, capital_enabled=False,
                            initial_firm_cash_cents=0, household_savings_rate=0.0))
    opening = capture_opening(sim.state)
    period = sim.step()
    report = audit_period(opening, sim.state, period)
    assert report.transfer_count == 0
    assert report.money_stock_cents == 0


def test_live_engine_credit_origination_then_noncash_default():
    # Supplier goods are existing inventory: seed their cumulative production
    # so the physical identity is also checked, not bypassed in this test.
    c = Scenario(
        name="audit-live-credit", population=4, household_size=1, seed=42,
        firms_per_sector=2, initial_household_cash_cents=3000,
        initial_firm_cash_cents=0, initial_resource=100, resource_capacity=100,
        capital_enabled=True, initial_capital_units_per_firm=0,
        capital_investment_budget_share=0.5,
        credit_enabled=True, cost_basis_accounting_enabled=True,
        credit_lender_savings_share=1.0, credit_firm_cash_reserve_cents=0,
        credit_repayment_fraction=0., credit_term_periods=1,
        dividend_share=0., tax_rate=0., household_savings_rate=0.,
        transaction_trace=True, sectors=(Sector("goods", 1.0, 100, 0, 1.0, 1),),
    )
    sim = Simulation(c)
    state = sim.state
    state.household_savings[0] = 2000
    state.household_cash[0] -= 2000
    state.inventory[1] = 10
    state.cumulative_output[0] = 10
    initial = capture_opening(state)
    first = sim.step()
    assert first.metrics["loan_origination_cents"] == 200
    assert audit_period(initial, state, first).outstanding_claims_cents == 200
    later = capture_opening(state)
    second = sim.step()
    assert second.metrics["loan_defaults_cents"] == 200
    assert audit_period(later, state, second).noncash_writeoff_cents == 200
    assert state.total_money() == state.initial_total_money


def test_run_cli_audit_flag_writes_both_trace_streams(tmp_path):
    from civitas.cli import main
    from civitas.persistence import checkpoint_load
    path = tmp_path / "example.json"
    path.write_text(json.dumps(traced(population=20, transaction_trace=False).to_dict()))
    output = tmp_path / "result"
    assert main(["run", "--scenario", str(path), "--steps", "2",
                 "--audit-ledger", "--output", str(output)]) == 0
    assert (output / "transactions.jsonl").is_file()
    assert (output / "noncash_transactions.jsonl").is_file()
    assert (output / "transactions.jsonl").read_text().strip()
    scenario, state, _ = checkpoint_load(output / "checkpoint.npz")
    assert scenario.transaction_trace
    assert state.step == 2


def test_experiment_summary_recounts_and_detects_tampering(tmp_path):
    from research.run_ledger_closure import execute, verify_summary
    from pathlib import Path
    output = tmp_path / "a"
    result = execute(seeds=(1, 2), steps=2, population=40, output=output)
    assert result["runs"] == 6
    assert result["audited_periods"] == 12
    assert result["transfer_count"] > 0
    assert verify_summary(output / "summary.json") == result
    # Replay is deterministic across output directories, even for randomized worlds.
    other = execute(seeds=(1, 2), steps=2, population=40, output=tmp_path / "b")
    assert other == result
    damaged = json.loads((output / "summary.json").read_text())
    damaged["rows"][0]["transfer_cents"] += 1
    (output / "summary.json").write_text(json.dumps(damaged))
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_summary(output / "summary.json")


def test_experiment_runner_rejects_invalid_parameters(tmp_path):
    from research.run_ledger_closure import execute
    for kwargs in ({"seeds": (-1,)}, {"seeds": ()}, {"steps": 0}, {"population": -1}):
        with pytest.raises(ValueError):
            execute(output=tmp_path, **kwargs)
