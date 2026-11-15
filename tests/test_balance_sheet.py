"""End-to-end and adversarial balance-sheet tests, with exact integer accounting."""
from copy import deepcopy
from dataclasses import replace
import json

import numpy as np
import pytest

from civitas.balance_sheet import (BalanceSheetError, capture_book_snapshot,
                                   check_book_snapshot, audit_book_period)
from civitas.cli import main
from civitas.engine import Simulation
from civitas.model import Scenario
from civitas.persistence import checkpoint_load, checkpoint_save
from civitas.world_genesis import default_plan, resolve_plan


def scenario(**changes):
    base = Scenario(name="balance-sheet", seed=17, population=64,
                    firms_per_sector=2, capital_enabled=True,
                    initial_capital_units_per_firm=50, capital_output_per_unit=3,
                    capital_depreciation_rate=0.10,
                    capital_investment_budget_share=0.45,
                    household_savings_rate=0.40,
                    credit_enabled=True, credit_term_periods=2,
                    credit_firm_cash_reserve_cents=0,
                    cost_basis_accounting_enabled=True,
                    resource_extraction_fee_cents_per_unit=2,
                    transaction_trace=True)
    return replace(base, **changes)


def test_detached_initial_statements_and_consolidation():
    sim = Simulation(scenario())
    snap = capture_book_snapshot(sim.state, sim.scenario)
    sums = snap.totals()
    assert sums["national_book_net_worth_cents"] == (
        sums["total_money_cents"] + sums["firm_inventory_basis_cents"] +
        sums["firm_capital_basis_cents"])
    assert sums["household_loan_assets_cents"] == sums["firm_loan_liabilities_cents"] == 0
    assert sum(snap.household_equity) + snap.unowned_equity == sum(snap.firm_equity)
    sim.state.firm_cash[0] += 4
    assert snap.firm_cash[0] + 4 == int(sim.state.firm_cash[0])
    check_book_snapshot(snap)


def test_carrying_value_and_owner_shares_are_integer_exact():
    sim = Simulation(scenario())
    s = sim.state
    s.firm_cash[0] = 1
    s.firm_capital_basis_cents[0] = 0
    s.firm_capital[0] = 0
    s.firm_loan_liabilities_cents[0] = 0
    s.firm_owner_households = (np.array([0, 1, 2], dtype=np.int64),) + s.firm_owner_households[1:]
    snap = capture_book_snapshot(s, sim.scenario)
    # The one-cent residual goes to the first registered owner, exactly.
    s.firm_owner_households = (np.array([], dtype=np.int64),) + s.firm_owner_households[1:]
    without = capture_book_snapshot(s, sim.scenario)
    for h, delta in enumerate((1, 0, 0)):
        assert snap.household_equity[h] - without.household_equity[h] == delta
    check_book_snapshot(snap)


def test_trace_replays_periods_and_reconciles_earnings():
    sim = Simulation(scenario())
    for _ in range(6):
        opening = capture_book_snapshot(sim.state, sim.scenario)
        period = sim.step()
        report = audit_book_period(opening, sim.state, period, sim.scenario)
        assert report == period.book_balance_report
        assert report["book_equity_discrepancy_cents"] == 0
        assert report["national_book_net_worth_cents"] == capture_book_snapshot(sim.state, sim.scenario).totals()["national_book_net_worth_cents"]


def test_trace_and_untraced_metrics_and_random_streams_unchanged():
    traced = Simulation(scenario())
    plain = Simulation(scenario(transaction_trace=False))
    for _ in range(5):
        a, b = traced.step(), plain.step()
        assert a.metrics == b.metrics
        assert a.journal == b.journal
        assert a.book_balance_report is not None
        assert b.book_balance_report is None
    assert traced.rng.bit_generator.state == plain.rng.bit_generator.state


def test_no_cost_basis_mode_reports_only_recorded_cash_values():
    s = Simulation(scenario(cost_basis_accounting_enabled=False,
                            credit_enabled=False, resource_extraction_fee_cents_per_unit=0))
    for _ in range(4):
        p = s.step()
        totals = capture_book_snapshot(s.state, s.scenario).totals()
        assert totals["firm_inventory_basis_cents"] == 0
        assert totals["firm_capital_basis_cents"] == 0
        assert totals["national_book_net_worth_cents"] == totals["total_money_cents"]
        assert p.book_balance_report["book_equity_discrepancy_cents"] == 0


def test_unowned_and_signed_negative_firm_equity_are_not_hidden():
    sim = Simulation(scenario())
    s = sim.state
    # A unilateral synthetic debt is invalid against the loan ledger, so test
    # a signed residual directly on an otherwise valid immutable snapshot.
    snap = capture_book_snapshot(s, sim.scenario)
    altered = replace(snap, firm_equity=(snap.firm_equity[0] - 1,) + snap.firm_equity[1:])
    with pytest.raises(BalanceSheetError, match="firm assets"):
        check_book_snapshot(altered)
    # Empty-owner stress: the residual is explicit, never lost in consolidation.
    s.firm_owner_households = (np.array([], dtype=np.int64),) + s.firm_owner_households[1:]
    with_unowned = capture_book_snapshot(s, sim.scenario)
    assert with_unowned.unowned_equity == with_unowned.firm_equity[0]
    check_book_snapshot(with_unowned)


def test_negative_firm_equity_can_be_attributed_without_inventing_a_loan():
    # Build a structurally consistent synthetic contract with firm debt > assets.
    from civitas.state import LoanContract
    sim = Simulation(scenario())
    s = sim.state
    s.firm_cash[0] = 0
    s.firm_capital[0] = 0
    s.firm_capital_basis_cents[0] = 0
    s.firm_loan_liabilities_cents[0] = 3
    s.household_loan_assets_cents[0] = 3
    s.loans = [LoanContract(0, 0, 3, 0)]
    snap = capture_book_snapshot(s, sim.scenario)
    assert snap.firm_equity[0] == -3
    assert sum(snap.household_equity) + snap.unowned_equity == sum(snap.firm_equity)
    check_book_snapshot(snap)


def test_tamper_with_cash_or_cost_basis_or_equity_is_detected():
    sim = Simulation(scenario())
    opening = capture_book_snapshot(sim.state, sim.scenario)
    period = sim.step()
    altered = deepcopy(sim.state)
    altered.firm_cash[0] += 5
    altered.firm_cash[1] -= 5
    with pytest.raises(AssertionError):
        audit_book_period(opening, altered, period, sim.scenario)
    altered = deepcopy(sim.state)
    altered.firm_inventory_basis_cents[0] += 1
    with pytest.raises(AssertionError):
        audit_book_period(opening, altered, period, sim.scenario)
    changed_period = deepcopy(period)
    tx = next(x for x in changed_period.transactions if x["reason"] == "sale")
    tx["cents"] += 1
    with pytest.raises(AssertionError):
        audit_book_period(opening, sim.state, changed_period, sim.scenario)


def test_wrong_ownership_allocation_or_debt_fails():
    s = Simulation(scenario())
    snap = capture_book_snapshot(s.state, s.scenario)
    if len(snap.household_equity) >= 2:
        altered = replace(snap, household_equity=(snap.household_equity[0] + 1,
                          snap.household_equity[1] - 1) + snap.household_equity[2:])
        # Sum is unchanged, but an owner-level mismatch must still fail.
        assert altered.totals() == snap.totals()
        with pytest.raises(BalanceSheetError, match="owner registry"):
            check_book_snapshot(altered)
    s.state.firm_loan_liabilities_cents[0] += 1
    with pytest.raises(BalanceSheetError, match="bilateral"):
        capture_book_snapshot(s.state, s.scenario)


def test_full_checkpoint_restart_and_cli_json(tmp_path):
    sim = Simulation(scenario())
    sim.run(3)
    path = tmp_path / "checkpoint.npz"
    checkpoint_save(path, sim.scenario, sim.state, sim.rng.bit_generator.state)
    output = tmp_path / "books.json"
    assert main(["balance-sheet", "--checkpoint", str(path), "--output", str(output), "--details"]) == 0
    doc = json.loads(output.read_text())
    assert len(doc["firms"]) == len(sim.state.firm_cash)
    assert len(doc["households"]) == len(sim.state.household_cash)
    assert doc["totals"] == capture_book_snapshot(sim.state, sim.scenario).totals()
    cfg, state, rng = checkpoint_load(path)
    restored = Simulation(cfg, state=state, rng_state=rng)
    first = restored.step()
    other = sim.step()
    assert first.metrics == other.metrics
    assert first.book_balance_report == other.book_balance_report


def test_hybrid_world_book_replay():
    c = resolve_plan(default_plan(mode="hybrid", seed=21, name="book-genesis", population=96))
    c = replace(c, transaction_trace=True)
    sim = Simulation(c)
    for _ in range(3):
        p = sim.step()
        assert p.book_balance_report["book_equity_discrepancy_cents"] == 0


def test_period_report_saved_separately(tmp_path):
    from civitas.persistence import save_run
    sim = Simulation(scenario())
    periods = sim.run(3)
    save_run(tmp_path, sim.scenario, periods, seed=sim.scenario.seed,
             elapsed_seconds=0, initial_step=0)
    rows = [json.loads(line) for line in (tmp_path / "book_balance_reports.jsonl").read_text().splitlines()]
    assert rows == [x.book_balance_report for x in periods]
    assert rows[-1]["step"] == 3


def test_audit_rejects_missing_trace():
    sim = Simulation(scenario(transaction_trace=False))
    opening = capture_book_snapshot(sim.state, sim.scenario)
    p = sim.step()
    with pytest.raises(BalanceSheetError, match="traced"):
        audit_book_period(opening, sim.state, p, sim.scenario)


def test_live_origination_repayment_and_default_book_replay():
    from civitas.model import Sector
    c = Scenario(name="book-live-credit", population=4, household_size=1,
                 seed=42, firms_per_sector=2, initial_household_cash_cents=3000,
                 initial_firm_cash_cents=0, initial_resource=100,
                 resource_capacity=100, capital_enabled=True,
                 initial_capital_units_per_firm=0,
                 capital_investment_budget_share=0.5,
                 credit_enabled=True, cost_basis_accounting_enabled=True,
                 credit_lender_savings_share=1.0,
                 credit_firm_cash_reserve_cents=0,
                 credit_repayment_fraction=0., credit_term_periods=1,
                 dividend_share=0., tax_rate=0., household_savings_rate=0.,
                 transaction_trace=True,
                 sectors=(Sector("goods", 1.0, 100, 0, 1.0, 1),))
    sim = Simulation(c)
    state = sim.state
    state.household_savings[0] = 2000
    state.household_cash[0] -= 2000
    state.inventory[1] = 10
    state.cumulative_output[0] = 10
    opening = capture_book_snapshot(state, c)
    first = sim.step()
    assert first.metrics["loan_origination_cents"] == 200
    assert audit_book_period(opening, state, first, c)["credit_stock_cents"] == 200
    next_opening = capture_book_snapshot(state, c)
    second = sim.step()
    assert second.metrics["loan_defaults_cents"] == 200
    assert audit_book_period(next_opening, state, second, c)["credit_stock_cents"] == 0


def test_owner_registry_mutation_without_transaction_rejected():
    sim = Simulation(scenario())
    opening = capture_book_snapshot(sim.state, sim.scenario)
    period = sim.step()
    altered = deepcopy(sim.state)
    ids = tuple(np.array(o, copy=True) for o in altered.firm_owner_households)
    ids = (np.array([0, 2], dtype=np.int64),) + ids[1:]
    altered.firm_owner_households = ids
    with pytest.raises(BalanceSheetError, match="ownership changed"):
        audit_book_period(opening, altered, period, sim.scenario)


def test_tampered_period_balance_report_is_detected():
    sim = Simulation(scenario())
    opening = capture_book_snapshot(sim.state, sim.scenario)
    period = sim.step()
    forged = deepcopy(period)
    forged.book_balance_report["national_book_net_worth_cents"] += 1
    with pytest.raises(BalanceSheetError, match="saved balance-sheet report"):
        audit_book_period(opening, sim.state, forged, sim.scenario)
