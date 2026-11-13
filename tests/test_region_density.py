"""Independent design, reproducibility and tamper checks for density experiment."""
from __future__ import annotations
import csv
import json
from pathlib import Path
from dataclasses import replace

import pytest

from civitas.engine import Simulation
from research.run_region_density import build_scenario, run_shard, finalize


def test_equal_initial_total_firm_cash_capital_and_resources():
    a=build_scenario(17, 10); b=build_scenario(17, 20)
    assert a.initial_firm_cash_cents * a.firms_per_sector == b.initial_firm_cash_cents * b.firms_per_sector
    assert a.initial_capital_units_per_firm * a.firms_per_sector == b.initial_capital_units_per_firm * b.firms_per_sector
    assert a.initial_resource == b.initial_resource
    assert a.resource_capacity == b.resource_capacity
    assert a.population == b.population
    assert a.initial_household_cash_cents == b.initial_household_cash_cents


def test_reject_unsupported_design():
    for firms, population in [(5,10000),(10,1000),(11,10000)]:
        with pytest.raises(ValueError):build_scenario(1,firms,population)


def test_seed_shards_are_deterministic(tmp_path):
    out=tmp_path/'one'; out2=tmp_path/'two'
    first=run_shard(out, seed=1,firms=10,steps=2)
    second=run_shard(out2,seed=1,firms=10,steps=2)
    assert first['csv_sha256']==second['csv_sha256']
    assert first['initial_state_sha256']==second['initial_state_sha256']
    assert first['final_rng_sha256']==second['final_rng_sha256']
    assert first['rows']==8


def test_complete_factorial_and_tamper_detection(tmp_path):
    for seed in (1,2):
        for firms in (10,20):run_shard(tmp_path,seed=seed,firms=firms,steps=1)
    report=finalize(tmp_path,seeds=2,steps=1)
    assert report['design']['independent_simulations']==16
    assert report['design']['verified_period_records']==16
    path=tmp_path/'shards'/'f10_s001.csv'
    path.write_text(path.read_text()+'# modification\n')
    with pytest.raises(ValueError,match='tampered'):
        finalize(tmp_path,seeds=2,steps=1)
