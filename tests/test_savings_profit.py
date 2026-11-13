"""v0.2 next-slice verification: savings, flow identities, migration and replay."""
from dataclasses import replace
import json

import numpy as np
import pytest

from civitas.engine import Simulation
from civitas.model import Scenario, Sector
from civitas.persistence import canonical_json, checkpoint_load, checkpoint_save


def toy(**values):
    c = Scenario(
        name="savings_toy", seed=17, population=4, household_size=4,
        firms_per_sector=1, sectors=(Sector("food", 1.0, 20, 100, 1.0, 1),),
        initial_household_cash_cents=0, initial_firm_cash_cents=1000,
        initial_resource=100, resource_capacity=100, regeneration_rate=0,
        dividend_share=0, output_inventory_buffer=0, household_savings_rate=.5,
        household_liquidity_floor_cents=25, capital_enabled=False,
    )
    return replace(c, **values)


def test_analytical_one_household_saving_and_flow():
    sim = Simulation(toy())
    sim.state.participation[:] = True
    sim.state.skills[:] = 1.0
    m = sim.step().metrics
    assert m["household_gross_wages_cents"] == 100
    assert m["sales_cents"] == 20
    assert m["household_savings_deposited_cents"] == 50
    assert int(sim.state.household_cash[0]) == 30
    assert int(sim.state.household_savings[0]) == 50
    assert sim.state.total_money() == 1000
    assert m["household_cashflow_discrepancy_cents"] == 0
    assert m["firm_cashflow_discrepancy_cents"] == 0
    assert m["household_monetary_assets_cents"] == 80


def test_emergency_essential_withdrawal_and_no_money_creation():
    sim = Simulation(toy(transaction_trace=True))
    sim.state.participation[:] = True
    sim.state.skills[:] = 1.0
    sim.step()
    assert int(sim.state.household_savings[0]) == 50
    # A higher second-period price makes liquid wages insufficient but total
    # household money sufficient; the difference must be explicitly released.
    sim.state.prices[0] = 150
    period = sim.step()
    assert period.metrics["sales_cents"] == 150
    assert period.metrics["household_savings_withdrawn_cents"] == 20
    withdrawals = [tx for tx in period.transactions if tx["reason"] == "savings_withdrawal"]
    assert withdrawals == [{"source": "savings", "source_id": 0, "destination": "household",
                            "destination_id": 0, "cents": 20, "reason": "savings_withdrawal"}]
    assert period.metrics["money_discrepancy_cents"] == 0
    assert period.metrics["household_cashflow_discrepancy_cents"] == 0


def test_savings_disabled_cannot_finance_consumption():
    c = toy(savings_emergency_food_enabled=False)
    sim = Simulation(c)
    sim.state.participation[:] = True
    sim.state.skills[:] = 1
    sim.step()
    sim.state.prices[0] = 150
    period = sim.step()
    assert period.metrics["household_savings_withdrawn_cents"] == 0
    assert period.metrics["sales_cents"] == 0
    assert period.metrics["unmet_budget_demand_units"] >= 1


def test_savings_accounts_are_transfers_not_money_issuance():
    sim = Simulation(toy(household_savings_rate=0))
    s = sim.state
    s.transfer("firm", 0, "household", 0, 100, "wage_example")
    s.transfer("household", 0, "savings", 0, 65, "savings_deposit")
    assert s.total_money() == s.initial_total_money
    assert int(s.household_cash[0]) == 35
    assert int(s.household_savings[0]) == 65
    with pytest.raises(ValueError):
        s.transfer("savings", 0, "firm", 0, 66, "invalid_overdraft")
    assert s.total_money() == s.initial_total_money
    s.validate()


def test_profit_proxy_and_firm_cashflow_reconcile_with_cross_firm_capex():
    c = Scenario(name="capital_saving", population=400, seed=29,
                 capital_enabled=True, initial_capital_units_per_firm=35,
                 capital_depreciation_rate=.10, capital_investment_budget_share=.75,
                 household_savings_rate=.12, household_liquidity_floor_cents=3000)
    sim = Simulation(c)
    results = sim.run(8)
    assert any(p.metrics["capital_interfirm_purchases_cents"] > 0 for p in results)
    for p in results:
        m = p.metrics
        assert m["firm_profit_proxy_cents"] == (
            m["sales_cents"] + m["firm_capital_sales_revenue_cents"] - m["wages_cents"]
            - m["firm_capital_depreciation_expense_cents"])
        assert m["firm_capital_sales_revenue_cents"] == m["capital_interfirm_purchases_cents"]
        assert m["firm_cashflow_discrepancy_cents"] == 0
        assert m["household_cashflow_discrepancy_cents"] == 0
        assert m["money_discrepancy_cents"] == 0
        assert m["capital_discrepancy_units"] == 0
        assert m["goods_discrepancy_units"] == 0


def test_savings_checkpoint_v3_exact_replay(tmp_path):
    c = toy(initial_household_cash_cents=400, capital_enabled=False)
    whole = Simulation(c)
    uninterrupted = [p.metrics for p in whole.run(5)]
    partial = Simulation(c)
    start = [p.metrics for p in partial.run(2)]
    p = tmp_path / "v3.npz"
    checkpoint_save(p, c, partial.state, partial.rng.bit_generator.state)
    with np.load(p, allow_pickle=False) as z:
        assert int(z["checkpoint_version"]) == 3
    config, state, rng = checkpoint_load(p)
    resumed = Simulation(config, state=state, rng_state=rng)
    suffix = [p.metrics for p in resumed.run(3)]
    assert start + suffix == uninterrupted
    np.testing.assert_array_equal(whole.state.household_savings, resumed.state.household_savings)


def test_v2_checkpoint_migration_to_zero_savings(tmp_path):
    # A real v0.2 checkpoint has no savings array or related config fields.
    c = toy(household_savings_rate=0, initial_household_cash_cents=200)
    sim = Simulation(c)
    sim.run(2)
    p3 = tmp_path / "new.npz"
    p2 = tmp_path / "old.npz"
    checkpoint_save(p3, c, sim.state, sim.rng.bit_generator.state)
    missing_fields = {"household_savings_rate", "household_liquidity_floor_cents",
                      "savings_emergency_food_enabled", "savings_essential_sector"}
    with np.load(p3, allow_pickle=False) as z:
        archive = {k: z[k].copy() for k in z.files if k != "household_savings"}
        archive["checkpoint_version"] = np.array(2, dtype=np.int64)
        old_config = json.loads(str(z["config_json"]))
        archive["config_json"] = np.array(canonical_json({k:v for k,v in old_config.items()
                                                           if k not in missing_fields}))
    np.savez_compressed(p2, **archive)
    recovered, state, rng = checkpoint_load(p2)
    assert not np.any(state.household_savings)
    original_next = Simulation(c, state=sim.state, rng_state=sim.rng.bit_generator.state).step().metrics
    migrated_next = Simulation(recovered, state=state, rng_state=rng).step().metrics
    assert migrated_next == original_next


def test_parameter_validation_and_small_population():
    for values in (dict(household_savings_rate=-.01),
                   dict(household_savings_rate=1.01),
                   dict(household_liquidity_floor_cents=-1),
                   dict(savings_emergency_food_enabled=1),
                   dict(savings_essential_sector="unknown")):
        with pytest.raises(ValueError):
            toy(**values).validate()
    sim = Simulation(Scenario(name="empty", population=0, household_savings_rate=.3))
    assert sim.step().metrics["household_savings_stock_cents"] == 0
    assert sim.step().metrics["household_cashflow_discrepancy_cents"] == 0


def test_transfer_rejects_negative_and_out_of_range_account_ids_atomically():
    s = Simulation(toy()).state
    before = s.total_money()
    for src, idx, dest, dest_idx in (
        ("household", -1, "firm", 0),
        ("firm", 0, "savings", -1),
        ("savings", 1, "firm", 0),
        ("firm", 0, "household", 99),
        ("firm", 0, "government", 1),
    ):
        with pytest.raises(IndexError):
            s.transfer(src, idx, dest, dest_idx, 1, "invalid")
        assert s.total_money() == before
        assert not s.journal
