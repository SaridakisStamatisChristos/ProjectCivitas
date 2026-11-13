"""Independent arithmetic and data integrity checks for the factorial study."""
from __future__ import annotations
import csv
from dataclasses import replace
import json

import pytest
import numpy as np

from civitas.engine import Simulation
from civitas.model import Scenario
from civitas.persistence import checkpoint_save, checkpoint_load
from research.run_market_factorial import CELLS, analyze, contrast_weights, read_cells, run_cell, scenario_for


def test_factorial_has_all_unique_cells():
    assert len(CELLS) == 8
    assert len(set(CELLS.values())) == 8
    assert scenario_for("b0p0h0").buyer_seller_rule == "mixed"
    assert scenario_for("b1p0h0").buyer_seller_rule == "favorite"
    assert scenario_for("b0p1h0").price_adjustment == 0
    assert scenario_for("b0p0h1").hiring_expectation_rule == "stationary"


def test_difference_of_differences_and_three_way_formula():
    responses = {}
    for cell, (b, p, h) in CELLS.items():
        responses[cell] = 2 + b + 2*p + 3*h + 4*b*p + 5*b*h + 6*p*h + 7*b*p*h
    expected = {(0,):1, (1,):2, (2,):3,
                (0,1):4, (0,2):5, (1,2):6, (0,1,2):7}
    for f, correct in expected.items():
        weights = contrast_weights(f)
        assert sum(v*responses[cell] for cell,v in weights.items()) == correct


@pytest.mark.parametrize("f", [(), (0,0), (3,), (0,2,0)])
def test_invalid_factors(f):
    with pytest.raises(ValueError):
        contrast_weights(f)


def test_two_seeds_short_factorial_and_integrity(tmp_path, monkeypatch):
    monkeypatch.chdir(__import__("pathlib").Path(__file__).resolve().parents[1])
    for cell in CELLS:
        run_cell(tmp_path, cell, 2, 2)
    cells = read_cells(tmp_path, 2, 2)
    result = analyze(cells, 2, 2)
    assert len(result["cells"]) == 8
    assert result["factorial_interactions"]["seller_x_prices_x_hiring"]["production_per_person"]["gap"]["n"] == 2
    assert len(cells["b0p0h0"]) == 8
    target = tmp_path / "b0p0h0_periods.csv"
    target.write_bytes(target.read_bytes()+b"\n")
    with pytest.raises(ValueError, match="integrity"):
        read_cells(tmp_path, 2, 2)


def test_factorial_replay_under_joint_intervention(tmp_path, monkeypatch):
    monkeypatch.chdir(__import__("pathlib").Path(__file__).resolve().parents[1])
    conf = replace(scenario_for("b1p1h1"), population=100, firms_per_sector=2,
                   initial_resource=5000, resource_capacity=6000)
    one = Simulation(conf)
    one.run(3)
    saved = tmp_path / "checkpoint.npz"
    checkpoint_save(saved, conf, one.state, one.rng.bit_generator.state)
    cfg, state, rng = checkpoint_load(saved)
    two = Simulation(cfg, state=state, rng_state=rng)
    assert [p.metrics for p in one.run(4)] == [p.metrics for p in two.run(4)]
