"""Independent exact-ratio stock validation and engine integration."""
from dataclasses import replace
from fractions import Fraction

import pytest

from civitas.engine import Simulation
from civitas.model import Scenario
from civitas.normalization import audit_initial_endowments, scale_population_exact
from civitas.persistence import checkpoint_load, checkpoint_save


def reference():
    return Scenario(name="normalized_ref", population=1000, household_size=4,
                    firms_per_sector=2, initial_resource=50000, resource_capacity=60000,
                    capital_enabled=True, initial_capital_units_per_firm=450,
                    capital_depreciation_rate=.05, capital_investment_budget_share=.4,
                    household_savings_rate=.15)


def test_per_capita_exact_accounting_and_density():
    c = reference()
    scaled = scale_population_exact(c, 10000, seed=111)
    assert scaled.population == 10000
    assert scaled.firms_per_sector == 20
    assert scaled.initial_resource == 500000
    assert scaled.resource_capacity == 600000
    a, b = audit_initial_endowments(c), audit_initial_endowments(scaled)
    for field in ("firms_per_person", "household_money_per_person", "firm_money_per_person",
                  "initial_resource_per_person", "resource_capacity_per_person", "initial_capital_per_person"):
        assert getattr(a, field) == getattr(b, field)
    assert b.firms_per_person == Fraction(6, 1000)
    assert b.firm_money_per_person == Fraction(12000, 1)
    assert b.household_money_per_person == Fraction(3750, 1)
    assert b.initial_capital_per_person == Fraction(27, 10)


def test_scaler_rejects_fractional_counts_and_partial_households():
    c = reference()
    for target in (-1, 0, 999, 1012, 1001, True):
        with pytest.raises(ValueError):
            scale_population_exact(c, target)
    with pytest.raises(ValueError):
        scale_population_exact(replace(c, population=0), 1000)
    with pytest.raises(ValueError):
        audit_initial_endowments(replace(c, population=0))


def test_normalized_simulation_conservation_and_determinism():
    for n in (1000, 10000):
        c = scale_population_exact(reference(), n, seed=4)
        a, b = Simulation(c), Simulation(c)
        for _ in range(3):
            m1, m2 = a.step().metrics, b.step().metrics
            assert m1 == m2
            for key in ("money_discrepancy_cents", "goods_discrepancy_units",
                        "capital_discrepancy_units", "resource_discrepancy_units",
                        "firm_cashflow_discrepancy_cents", "household_cashflow_discrepancy_cents"):
                assert m1[key] == 0


def test_normalization_checkpoint_roundtrip(tmp_path):
    c = scale_population_exact(reference(), 1000, seed=9)
    sim = Simulation(c)
    sim.run(3)
    path = tmp_path / "normalized.npz"
    checkpoint_save(path, c, sim.state, sim.rng.bit_generator.state)
    c2, state, rng = checkpoint_load(path)
    assert c2 == c
    assert Simulation(c, state=state, rng_state=rng).step().metrics == sim.step().metrics


def test_actual_owner_fraction_rounding_is_visible():
    a = audit_initial_endowments(replace(reference(), ownership_fraction=.03))
    b = audit_initial_endowments(scale_population_exact(replace(reference(), ownership_fraction=.03), 10000))
    assert a.realized_ownership_fraction_per_firm == Fraction(8, 250)
    assert b.realized_ownership_fraction_per_firm == Fraction(75, 2500)


def test_preflight_rejects_oversized_initial_money_and_stocks():
    with pytest.raises(ValueError, match="initial_total_money"):
        replace(reference(), initial_firm_cash_cents=2**62).validate()
    with pytest.raises(ValueError, match="initial_capital_stock"):
        replace(reference(), initial_capital_units_per_firm=2**62).validate()
    with pytest.raises(ValueError, match="signed int64"):
        replace(reference(), resource_capacity=2**63).validate()


def test_credit_overflow_rejected_before_debit():
    sim = Simulation(reference())
    s = sim.state
    s.household_cash[0] = (2**63 - 1) - 2
    s.firm_cash[0] = 1000
    before = (int(s.household_cash[0]), int(s.firm_cash[0]))
    with pytest.raises(OverflowError):
        s.transfer("firm", 0, "household", 0, 10, "would_overflow")
    assert before == (int(s.household_cash[0]), int(s.firm_cash[0]))
    assert not s.journal
