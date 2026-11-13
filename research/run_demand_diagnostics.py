"""Matched long-horizon demand contraction diagnostics for CIVITAS v0.2.

Scientific purpose: falsify competing within-model explanations of production
contraction. Rules tested are interventions on the simulator, NOT policy forecasts.
Every complete (seed, treatment) is checksummed and safely resumable.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
from statistics import mean, stdev
import sys
import tempfile

import numpy as np

from civitas.engine import Simulation
from civitas.model import Scenario
from research.run_credit_pathways import configs as prior_configs
from research.run_credit_sensitivity import matched_state_hash

ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    "money_discrepancy_cents", "resource_discrepancy_units", "goods_discrepancy_units",
    "capital_discrepancy_units", "household_cashflow_discrepancy_cents",
    "firm_cashflow_discrepancy_cents", "firm_book_equity_discrepancy_cents",
    "loan_discrepancy_cents",
)
OUTCOMES = ("production_units", "consumption_units", "employed", "resource_stock",
            "capital_stock_units", "unmet_budget_demand_units", "unmet_stock_demand_units",
            "quoted_price_mean_cents", "household_spendable_cash_cents",
            "household_savings_stock_cents", "firm_cash_stock_cents",
            "total_inventory_units", "budget_unmet_share_of_attempts",
            "household_nonessential_affordability", "household_food_affordability",
            "household_monetary_assets_cents", "firm_cash_share", "household_cash_share")
ARMS = ("control", "no_saving", "full_dividends", "fixed_prices",
        "stationary_hiring", "no_depreciation")
SOURCE_PATHS = (
    "src/civitas/model.py", "src/civitas/state.py", "src/civitas/engine.py",
    "src/civitas/metrics.py", "src/civitas/finance.py", "src/civitas/economy_costs.py",
    "research/run_credit_pathways.py", "research/run_credit_sensitivity.py",
    "research/run_demand_diagnostics.py",
)


def encode(data: object) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, ensure_ascii=False).encode("utf8")


def sha(data: object) -> str:
    return hashlib.sha256(encode(data)).hexdigest()


def source_sha() -> str:
    hasher = hashlib.sha256()
    for path in SOURCE_PATHS:
        hasher.update(path.encode() + b"\0")
        hasher.update((ROOT / path).read_bytes())
    return hasher.hexdigest()


def scenarios(population: int = 10_000, steps: int = 48) -> list[Scenario]:
    if type(population) is not int or population <= 0 or type(steps) is not int or steps < 48:
        raise ValueError("positive population and >= 48 steps required")
    base = replace(prior_configs(population, steps)[0], name="control", seed=0)
    arms = (
        base,
        replace(base, name="no_saving", household_savings_rate=0.0),
        replace(base, name="full_dividends", dividend_share=1.0),
        replace(base, name="fixed_prices", price_adjustment=0.0),
        replace(base, name="stationary_hiring", hiring_expectation_rule="stationary"),
        replace(base, name="no_depreciation", capital_depreciation_rate=0.0),
    )
    assert tuple(c.name for c in arms) == ARMS
    for c in arms:
        c.validate()
    return list(arms)


def diag(sim: Simulation, metrics: dict) -> dict:
    """Post-step state: observables only, never mutates state or consumes RNG."""
    s, c = sim.state, sim.scenario
    household_cash = int(s.household_cash.sum())
    savings = int(s.household_savings.sum())
    firm_cash = int(s.firm_cash.sum())
    gov = int(s.gov_cash)
    if household_cash + savings + firm_cash + gov != s.initial_total_money:
        raise AssertionError("diagnostic monetary partition mismatch")
    h = len(s.household_cash)
    nf = c.firms_per_sector
    minimum = [int(s.prices[k * nf:(k + 1) * nf].min()) for k in range(len(c.sectors))]
    is_food = [q.name == c.savings_essential_sector and c.savings_emergency_food_enabled
               for q in c.sectors]
    affordable = []
    for k, floor in enumerate(minimum):
        buying_power = (s.household_cash + s.household_savings
                        if is_food[k] and c.household_savings_rate > 0 else s.household_cash)
        affordable.append(int(np.count_nonzero(buying_power >= floor)))
    food_indices = [k for k, q in enumerate(c.sectors) if q.name == "food"]
    nonfood_indices = [k for k in range(len(c.sectors)) if k not in food_indices]
    total_money = s.initial_total_money
    attempts = int(metrics["consumption_units"] + metrics["unmet_stock_demand_units"] +
                   metrics["unmet_budget_demand_units"])
    return {
        "step": metrics["step"],
        **{key: metrics[key] for key in CHECKS},
        "production_units": metrics["production_units"],
        "consumption_units": metrics["consumption_units"],
        "employed": metrics["employed"],
        "resource_stock": metrics["resource_stock"],
        "capital_stock_units": metrics["capital_stock_units"],
        "unmet_budget_demand_units": metrics["unmet_budget_demand_units"],
        "unmet_stock_demand_units": metrics["unmet_stock_demand_units"],
        "quoted_price_mean_cents": metrics["quoted_price_mean_cents"],
        "household_spendable_cash_cents": household_cash,
        "household_savings_stock_cents": savings,
        "household_monetary_assets_cents": household_cash + savings,
        "firm_cash_stock_cents": firm_cash,
        "government_cash_stock_cents": gov,
        "total_inventory_units": int(s.inventory.sum()),
        "budget_unmet_share_of_attempts": (metrics["unmet_budget_demand_units"] / attempts if attempts else None),
        "household_nonessential_affordability": (sum(affordable[k] for k in nonfood_indices) /
                                                     (h * len(nonfood_indices))
                                                     if h and nonfood_indices else None),
        "household_food_affordability": (sum(affordable[k] for k in food_indices) /
                                         (h * len(food_indices)) if h and food_indices else None),
        "firm_cash_share": firm_cash / total_money if total_money else None,
        "household_cash_share": household_cash / total_money if total_money else None,
        "wages_cents": metrics["wages_cents"],
        "dividends_cents": metrics["dividends_cents"],
        "sales_cents": metrics["sales_cents"],
        "capital_added_units": metrics["capital_added_units"],
        "capital_depreciated_units": metrics["capital_depreciated_units"],
    }


def atomic_write(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = encode(record)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".civitas-", suffix=".tmp",
                                     delete=False) as stream:
        temp = stream.name
        with gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as zipped:
            zipped.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def verify_cell(path: Path, config: Scenario) -> dict:
    with gzip.open(path, "rb") as stream:
        record = json.loads(stream.read())
    value = record.pop("sha256", None)
    if value != sha(record):
        raise ValueError("experiment shard checksum mismatch")
    if record.get("schema") != 1 or record.get("source_sha256") != source_sha():
        raise ValueError("experiment shard source mismatch")
    if record.get("config_sha256") != sha(config.to_dict()):
        raise ValueError("experiment shard configuration mismatch")
    periods = record.get("periods", [])
    if len(periods) != config.steps or [p.get("step") for p in periods] != list(range(1, config.steps+1)):
        raise ValueError("missing or repeated experiment periods")
    for p in periods:
        if any(p.get(k) != 0 for k in CHECKS):
            raise ValueError("experiment accounting mismatch")
        if p["household_monetary_assets_cents"] != (p["household_spendable_cash_cents"] +
                                                    p["household_savings_stock_cents"]):
            raise ValueError("household stock accounting mismatch")
        if (p["household_monetary_assets_cents"] + p["firm_cash_stock_cents"] +
                p["government_cash_stock_cents"] != record["initial_total_money_cents"]):
            raise ValueError("monetary partition mismatch")
        if any(p[k] < 0 for k in ("production_units", "resource_stock", "total_inventory_units")):
            raise ValueError("negative stock")
    record["sha256"] = value
    return record


def execute_cell(output: Path, scenario: Scenario) -> dict:
    path = output / f"seed_{scenario.seed:04d}" / f"{scenario.name}.json.gz"
    if path.exists():
        return verify_cell(path, scenario)
    sim = Simulation(scenario)
    init = matched_state_hash(sim)
    observations = []
    for _ in range(scenario.steps):
        m = sim.step().metrics
        if any(m[k] != 0 for k in CHECKS):
            raise AssertionError("engine invariant failure")
        observations.append(diag(sim, m))
    record = {"schema": 1, "seed": scenario.seed, "name": scenario.name,
              "config_sha256": sha(scenario.to_dict()), "source_sha256": source_sha(),
              "initial_state_sha256": init,
              "initial_total_money_cents": sim.state.initial_total_money,
              "end_rng_state_sha256": sha(sim.rng.bit_generator.state),
              "periods": observations}
    atomic_write(path, {**record, "sha256": sha(record)})
    return verify_cell(path, scenario)


def execute_seed(output: Path, seed: int, *, population: int = 10000,
                 steps: int = 48) -> dict:
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be nonnegative int")
    cells = [execute_cell(output, replace(c, seed=seed)) for c in scenarios(population, steps)]
    if len({cell["initial_state_sha256"] for cell in cells}) != 1:
        raise AssertionError("treatment initial state mismatch")
    if len({cell["end_rng_state_sha256"] for cell in cells}) != 1:
        raise AssertionError("treatment RNG drift")
    return {"seed": seed, "cells": len(cells), "periods": len(cells)*steps}


def _interval(values: list[float]) -> dict:
    n = len(values)
    avg = mean(values)
    sd = stdev(values) if n > 1 else None
    half = 1.96 * sd / (n**0.5) if sd is not None else None
    return {"n": n, "mean": avg, "sample_sd": sd,
            "mc95_low": avg-half if half is not None else None,
            "mc95_high": avg+half if half is not None else None}


def finalize(output: Path, seeds: list[int], *, population: int = 10000,
             steps: int = 48, write: bool = True) -> dict:
    if not seeds or len(set(seeds)) != len(seeds) or any(type(s) is not int or s < 0 for s in seeds):
        raise ValueError("seeds must be nonempty unique nonnegative integers")
    configs = scenarios(population, steps)
    dataset = {}
    for seed in seeds:
        cells = [verify_cell(output/f"seed_{seed:04d}"/f"{c.name}.json.gz",
                             replace(c, seed=seed)) for c in configs]
        if len({c["initial_state_sha256"] for c in cells}) != 1:
            raise ValueError("unmatched initial states")
        if len({c["end_rng_state_sha256"] for c in cells}) != 1:
            raise ValueError("RNG alignment mismatch")
        dataset[seed] = {c["name"]: c for c in cells}
    result = {
        "schema": 1, "source_sha256": source_sha(),
        "design": {"population": population, "steps": steps, "seeds": sorted(seeds),
                   "arms": list(ARMS), "runs": len(seeds)*len(ARMS),
                   "audited_periods": len(seeds)*len(ARMS)*steps},
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__,
                        "platform": platform.platform()},
        "means": {}, "paired_effects": {},
    }
    indicators = ("production_units", "consumption_units", "employed",
                  "unmet_budget_demand_units", "resource_stock", "capital_stock_units",
                  "total_inventory_units", "firm_cash_stock_cents", "household_spendable_cash_cents",
                  "household_savings_stock_cents", "quoted_price_mean_cents",
                  "budget_unmet_share_of_attempts", "household_nonessential_affordability",
                  "firm_cash_share")
    for arm in ARMS:
        for period in (24, steps):
            key=f"{arm}_t{period}"
            result["means"][key] = {indicator: _interval([
                dataset[seed][arm]["periods"][period-1][indicator] for seed in seeds
            ]) for indicator in indicators}
        if arm != "control":
            for period in (24, steps):
                diffs=[dataset[seed][arm]["periods"][period-1]["production_units"] -
                       dataset[seed]["control"]["periods"][period-1]["production_units"]
                       for seed in seeds]
                result["paired_effects"][f"{arm}_vs_control_t{period}_production"] = _interval(diffs)
            changes=[(dataset[seed][arm]["periods"][steps-1]["production_units"]-
                      dataset[seed][arm]["periods"][23]["production_units"]) -
                     (dataset[seed]["control"]["periods"][steps-1]["production_units"]-
                      dataset[seed]["control"]["periods"][23]["production_units"])
                     for seed in seeds]
            result["paired_effects"][f"{arm}_vs_control_change_t24_t{steps}"]=_interval(changes)
    if write:
        path=output/"summary.json"
        content=json.dumps(result, sort_keys=True, indent=2, allow_nan=False)+"\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf8", dir=path.parent,
                                         prefix=".civitas-", delete=False) as tmp:
            tmp.write(content)
            tmp.flush(); os.fsync(tmp.fileno()); temp=tmp.name
        os.replace(temp,path)
    return result


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--seed", type=int)
    mode.add_argument("--finalize", action="store_true")
    mode.add_argument("--verify-only", action="store_true")
    p.add_argument("--population", type=int, default=10000)
    p.add_argument("--steps", type=int, default=48)
    p.add_argument("--seeds", default="1,2,3,4,5,6,7,8")
    p.add_argument("--output", type=Path, default=Path("results/demand_diagnostics"))
    args=p.parse_args()
    if args.seed is not None:
        print(json.dumps(execute_seed(args.output,args.seed,population=args.population,
                                      steps=args.steps),indent=2))
    else:
        seeds=[int(x) for x in args.seeds.split(",")]
        result=finalize(args.output,seeds,population=args.population,steps=args.steps,
                        write=not args.verify_only)
        print(json.dumps({"design":result["design"],"paired_effects":result["paired_effects"]},indent=2))

if __name__=="__main__":
    main()
