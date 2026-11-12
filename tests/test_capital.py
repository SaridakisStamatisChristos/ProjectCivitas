"""v0.2 development-gate tests: integer flows, physical capital and reproducibility."""
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest

from civitas.engine import Simulation
from civitas.metrics import household_equity_values
from civitas.model import Scenario, Sector
from civitas.persistence import checkpoint_load, checkpoint_save


def scenario(**changes):
    base = Scenario(name="capital_toy", population=80, household_size=4, seed=11,
                    capital_enabled=True, initial_capital_units_per_firm=12,
                    capital_output_per_unit=1, capital_depreciation_rate=0.0,
                    capital_investment_budget_share=0.8, capital_target_buffer=0.4,
                    firms_per_sector=1, sectors=(
                        Sector("food", 1.0, 150, 75, 1.0, 2),
                        Sector("goods", 0.8, 200, 100, 1.0, 3)),
                    initial_resource=10000, resource_capacity=10000,
                    regeneration_rate=0.0, initial_household_cash_cents=0,
                    initial_firm_cash_cents=100000, dividend_share=0.0)
    return replace(base, **changes)


def test_capital_unit_capacity_is_binding():
    c = scenario(initial_capital_units_per_firm=1,
                 capital_investment_budget_share=0)
    sim = Simulation(c)
    p = sim.step().metrics
    assert p["production_units"] <= len(sim.state.firm_capital)
    assert p["capital_stock_units"] == 2
    assert p["capital_discrepancy_units"] == 0


def test_zero_capital_means_zero_production():
    c = scenario(initial_capital_units_per_firm=0)
    p = Simulation(c).step().metrics
    assert p["production_units"] == 0
    assert p["capital_added_units"] == 0


def test_depreciation_exact_nonnegative():
    c = scenario(capital_depreciation_rate=0.25, capital_investment_budget_share=0)
    sim = Simulation(c)
    first = sim.step().metrics
    assert first["capital_depreciated_units"] == 6   # 12 * .25 * two firms
    assert first["capital_stock_units"] == 18
    second = sim.step().metrics
    assert second["capital_depreciated_units"] == 4  # floor(9*.25) * 2
    assert second["capital_stock_units"] == 14
    assert second["capital_discrepancy_units"] == 0


def test_capital_converts_real_goods_and_preserves_physical_balance():
    sim = Simulation(scenario())
    original_total = sim.state.total_money()
    results = sim.run(6)
    assert any(p.metrics["capital_added_units"] > 0 for p in results)
    for p in results:
        m = p.metrics
        assert m["money_discrepancy_cents"] == 0
        assert m["capital_discrepancy_units"] == 0
        assert m["goods_discrepancy_units"] == 0
        assert m["resource_discrepancy_units"] == 0
    assert sim.state.total_money() == original_total
    assert sum(sim.state.cumulative_capital_goods_converted) == sim.state.cumulative_capital_added
    assert (sim.state.firm_capital >= 0).all()


def test_cross_firm_capital_purchases_have_source_destination():
    c = scenario(transaction_trace=True)
    sim = Simulation(c)
    # The food firm needs capital; the goods firm already has ample capital.
    sim.state.firm_capital[:] = [1, 200]
    sim.state.initial_capital_total = 201
    result = sim.step()
    cross = [tx for tx in result.transactions if tx["reason"] == "capital_purchase"]
    assert len(cross) > 0
    assert all(tx["source"] == "firm" and tx["destination"] == "firm" for tx in cross)
    assert all(tx["source_id"] != tx["destination_id"] for tx in cross)
    assert sum(tx["cents"] for tx in cross) == result.metrics["capital_interfirm_purchases_cents"]
    assert result.metrics["goods_discrepancy_units"] == 0
    assert result.metrics["capital_discrepancy_units"] == 0


def test_own_goods_conversion_requires_inventory_but_no_money_transfer():
    c = scenario(transaction_trace=True, capital_investment_budget_share=1.0)
    sim = Simulation(c)
    sim.state.firm_capital[:] = [100, 1]
    sim.state.initial_capital_total = 101
    p = sim.step()
    assert p.metrics["capital_added_units"] >= 1
    assert p.metrics["capital_investment_goods_value_cents"] > 0
    assert p.metrics["capital_interfirm_purchases_cents"] == 0
    assert all(tx["reason"] != "capital_purchase" for tx in p.transactions)


def test_household_disposable_income_identity_and_tax():
    c = scenario(tax_rate=0.4, redistribution_share=0.6, dividend_share=0.4,
                 initial_household_cash_cents=4000)
    for p in Simulation(c).run(3):
        m = p.metrics
        assert m["disposable_income_total_cents"] == (
            m["household_gross_wages_cents"] - m["government_tax_revenue_cents"]
            + m["government_transfer_cents"] + m["dividends_cents"])
        assert 0 <= m["disposable_income_gini"] <= 1


def test_equity_claims_sum_to_marked_firm_assets():
    c = scenario()
    sim = Simulation(c)
    equity = household_equity_values(sim.state, c)
    k = next(i for i, sec in enumerate(c.sectors) if sec.name == c.capital_input_sector)
    price = int(sim.state.prices[k])
    actual = sum(int(sim.state.firm_cash[f]) + int(sim.state.inventory[f]) * int(sim.state.prices[f])
                 + int(sim.state.firm_capital[f]) * price for f in range(len(sim.state.firm_cash)))
    assert int(equity.sum()) == actual
    assert (equity >= 0).all()


def test_checkpoint_replay_with_capital(tmp_path):
    c = scenario(capital_depreciation_rate=0.1, dividend_share=0.4)
    whole = Simulation(c)
    obs = [p.metrics for p in whole.run(10)]
    half = Simulation(c)
    first = [p.metrics for p in half.run(4)]
    path = tmp_path / 'c2.npz'
    checkpoint_save(path, c, half.state, half.rng.bit_generator.state)
    with np.load(path, allow_pickle=False) as z:
        assert int(z["checkpoint_version"]) == 2
    loaded_c, state, rng = checkpoint_load(path)
    continued = Simulation(loaded_c, state=state, rng_state=rng)
    remaining = [p.metrics for p in continued.run(6)]
    assert first + remaining == obs
    assert np.array_equal(whole.state.firm_capital, continued.state.firm_capital)
    assert np.array_equal(whole.state.household_cash, continued.state.household_cash)


def test_old_checkpoint_migration(tmp_path):
    # Synthesize an actual version-1 serialization using the documented v0.1
    # NPZ field layout (the project's original smoke output is not committed).
    from civitas.persistence import canonical_json
    import json
    c = Scenario(name="legacy", population=32, seed=5)
    sim = Simulation(c)
    sim.run(2)
    new_path = tmp_path / "new.npz"
    old_path = tmp_path / "legacy.npz"
    checkpoint_save(new_path, c, sim.state, sim.rng.bit_generator.state)
    excluded_fields = {"firm_capital", "cumulative_capital_goods_converted",
                       "initial_capital_total", "cumulative_capital_added",
                       "cumulative_capital_depreciated"}
    new_scenario_fields = {"capital_enabled", "initial_capital_units_per_firm",
                           "capital_output_per_unit", "capital_depreciation_rate",
                           "capital_investment_budget_share", "capital_target_buffer",
                           "capital_input_sector"}
    with np.load(new_path, allow_pickle=False) as z:
        archive = {key: z[key].copy() for key in z.files if key not in excluded_fields}
        archive["checkpoint_version"] = np.array(1, dtype=np.int64)
        archive["software_version"] = np.array("0.1.0")
        old_config = json.loads(str(z["config_json"]))
        archive["config_json"] = np.array(canonical_json({k: v for k, v in old_config.items()
                                                            if k not in new_scenario_fields}))
    np.savez_compressed(old_path, **archive)
    recovered, state, rng = checkpoint_load(old_path)
    assert not recovered.capital_enabled
    assert (state.firm_capital == 0).all()
    assert Simulation(recovered, state=state, rng_state=rng).step().metrics['capital_discrepancy_units'] == 0


def test_ownership_treatment_shares_non_owner_initial_conditions():
    a = Simulation(scenario(ownership_fraction=0.03))
    b = Simulation(scenario(ownership_fraction=0.3))
    assert np.array_equal(a.state.skills, b.state.skills)
    assert np.array_equal(a.state.participation, b.state.participation)
    assert a.rng.bit_generator.state == b.rng.bit_generator.state
    assert sum(map(len, a.state.firm_owner_households)) != sum(map(len, b.state.firm_owner_households))


def test_config_validation_capital_boundaries():
    for changes in ({'capital_investment_budget_share': -0.01},
                    {'capital_depreciation_rate': 1.01},
                    {'initial_capital_units_per_firm': -1},
                    {'capital_output_per_unit': 0},
                    {'capital_input_sector': 'nonexistent'}):
        with pytest.raises(ValueError):
            scenario(**changes).validate()
    with pytest.raises(ValueError):
        replace(scenario(), capital_enabled=False).validate()


def test_v01_legacy_scenario_remains_behaviorally_equivalent():
    c = Scenario(name='market', population=280, seed=7)
    s = Simulation(c)
    observed = s.run(5)
    assert all(p.metrics['capital_stock_units'] == 0 for p in observed)
    assert all(p.metrics['capital_added_units'] == 0 for p in observed)
    assert all(p.metrics['capital_discrepancy_units'] == 0 for p in observed)
    assert all(p.metrics['disposable_income_gini'] == p.metrics['income_gini'] for p in observed)
