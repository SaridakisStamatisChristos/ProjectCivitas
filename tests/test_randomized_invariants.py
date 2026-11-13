"""Deterministic bounded random stress checks; not economic model validation."""
from dataclasses import replace

import numpy as np

from civitas.engine import Simulation
from civitas.model import Scenario
from civitas.persistence import checkpoint_load, checkpoint_save


IDENTITIES = (
    "money_discrepancy_cents", "goods_discrepancy_units", "capital_discrepancy_units",
    "resource_discrepancy_units", "household_cashflow_discrepancy_cents",
    "firm_cashflow_discrepancy_cents",
)


def test_bounded_randomized_cases_keep_conservation_and_resume(tmp_path):
    rng = np.random.default_rng(932874)
    for iteration in range(72):
        n = int(rng.choice([0, 1, 2, 4, 11, 32, 150, 400]))
        cap = bool(rng.integers(0, 2))
        resource_capacity = int(rng.integers(0, 15000))
        scenario = Scenario(
            name=f"stress_{iteration}", population=n, seed=int(rng.integers(0, 200000)),
            household_size=int(rng.integers(1, 6)), firms_per_sector=int(rng.integers(1, 4)),
            initial_household_cash_cents=int(rng.integers(0, 20000)),
            initial_firm_cash_cents=int(rng.integers(0, 100000)),
            initial_resource=int(rng.integers(0, resource_capacity+1)),
            resource_capacity=resource_capacity,
            regeneration_rate=float(rng.choice([0.0,.02,.2,1.0])),
            labor_participation=float(rng.random()),
            tax_rate=float(rng.random()),
            redistribution_share=float(rng.random()),
            dividend_share=float(rng.random()),
            ownership_fraction=float(rng.choice([0.0,.01,.5,1.0])),
            capital_enabled=cap,
            initial_capital_units_per_firm=int(rng.integers(0, 500)) if cap else 0,
            capital_depreciation_rate=float(rng.choice([0.0,.01,.1,1.0])),
            capital_investment_budget_share=float(rng.random()),
            household_savings_rate=float(rng.random()),
            automation_base=float(rng.random()),
        )
        scenario.validate()
        whole = Simulation(scenario)
        first = [p.metrics for p in whole.run(3)]
        for record in first:
            for invariant in IDENTITIES:
                assert record[invariant] == 0, (iteration, invariant, record)
        checkpoint = tmp_path / f"fuzz_{iteration}.npz"
        checkpoint_save(checkpoint, scenario, whole.state, whole.rng.bit_generator.state)
        original_tail = [p.metrics for p in whole.run(3)]
        restored_scenario, restored_state, restored_rng = checkpoint_load(checkpoint)
        resumed = Simulation(restored_scenario, state=restored_state, rng_state=restored_rng)
        replay_tail = [p.metrics for p in resumed.run(3)]
        assert original_tail == replay_tail
        for record in replay_tail:
            for invariant in IDENTITIES:
                assert record[invariant] == 0, (iteration, invariant, record)
