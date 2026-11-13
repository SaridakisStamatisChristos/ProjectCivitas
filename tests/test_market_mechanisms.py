"""Market intervention validation, exact accounting, and replay."""
from dataclasses import replace
import numpy as np
import pytest
from civitas.engine import Simulation
from civitas.model import Scenario
from civitas.persistence import checkpoint_save, checkpoint_load


def baseline(**changes):
    base = Scenario(name="market_ablation_fixture", population=400, firms_per_sector=2, initial_resource=22000,
                    resource_capacity=30000, capital_enabled=True,
                    initial_capital_units_per_firm=140,
                    capital_depreciation_rate=.05, capital_investment_budget_share=.4,
                    household_savings_rate=.2, ownership_fraction=.08, seed=19)
    return replace(base, **changes)


def audit(m):
    for key in ("money_discrepancy_cents", "goods_discrepancy_units", "resource_discrepancy_units",
                "capital_discrepancy_units", "firm_cashflow_discrepancy_cents",
                "household_cashflow_discrepancy_cents"):
        assert m[key] == 0
    assert m["active_sellers"] >= 0
    assert m["quoted_price_spread_mean_cents"] >= 0
    assert m["seller_sales_hhi_mean"] is None or 0 < m["seller_sales_hhi_mean"] <= 1


@pytest.mark.parametrize("field,options", [
    ("buyer_seller_rule", ("mixed", "cheapest", "favorite")),
    ("hiring_expectation_rule", ("adaptive", "stationary")),
    ("rationing_order_rule", ("random", "household_id")),
])
def test_ablation_repeatability_and_invariants(field, options):
    for value in options:
        scenario = baseline(**{field: value})
        one, two = Simulation(scenario), Simulation(scenario)
        for _ in range(4):
            a, b = one.step().metrics, two.step().metrics
            assert a == b
            audit(a)


@pytest.mark.parametrize("field", ["buyer_seller_rule", "hiring_expectation_rule", "rationing_order_rule"])
def test_rule_validation(field):
    for value in ("unknown", "", [], None):
        with pytest.raises(ValueError, match=field):
            baseline(**{field: value}).validate()


def test_original_default_matches_explicit_rules():
    a = Simulation(baseline())
    b = Simulation(baseline(buyer_seller_rule="mixed",
                            hiring_expectation_rule="adaptive", rationing_order_rule="random"))
    assert [p.metrics for p in a.run(7)] == [p.metrics for p in b.run(7)]


def test_no_price_adjustment_is_fixed():
    sim = Simulation(baseline(price_adjustment=0))
    old = sim.state.prices.copy()
    sim.run(9)
    np.testing.assert_array_equal(sim.state.prices, old)


def test_checkpoint_ablation_compatibility(tmp_path):
    scenario = baseline(buyer_seller_rule="cheapest", hiring_expectation_rule="stationary",
                        rationing_order_rule="household_id", price_adjustment=0)
    sim = Simulation(scenario)
    sim.run(3)
    f = tmp_path / "market.npz"
    checkpoint_save(f, scenario, sim.state, sim.rng.bit_generator.state)
    loaded_scenario, loaded_state, loaded_rng = checkpoint_load(f)
    assert loaded_scenario == scenario
    resumed = Simulation(loaded_scenario, state=loaded_state, rng_state=loaded_rng)
    for _ in range(4):
        assert sim.step().metrics == resumed.step().metrics


def test_treatments_preserve_identical_initial_agents():
    a = Simulation(baseline(buyer_seller_rule="cheapest"))
    b = Simulation(baseline(buyer_seller_rule="favorite"))
    np.testing.assert_array_equal(a.state.skills, b.state.skills)
    np.testing.assert_array_equal(a.state.participation, b.state.participation)
    np.testing.assert_array_equal(a.state.household_cash, b.state.household_cash)


def test_historical_normalized_production_consumption_employment_parity():
    """Golden-record regression independent of newly implemented rule defaults."""
    import csv
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    c = Scenario.from_file(root / "scenarios/population_normalized/o08_s00_n10000.json")
    path = root / "research/v02_population_normalized_10000/o08_s00_periods.csv"
    with path.open(newline="", encoding="utf8") as f:
        rows = [r for r in csv.DictReader(f) if int(r["seed"]) == 1]
    assert len(rows) == 24
    sim = Simulation(replace(c, seed=1))
    for actual, old in zip(sim.run(24), rows):
        m = actual.metrics
        assert m["step"] == int(old["period"])
        assert m["production_units"] == int(old["production_units"])
        assert m["consumption_units"] == int(old["consumption_units"])
        assert m["employment_rate"] == pytest.approx(float(old["employment_rate"]), abs=1e-15)
