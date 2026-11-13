"""Matched counterfactual loan-funding experiment (v0.2 developmental science).

Independent factors: household savings propensity, lendable share, loan term.
Includes a 'sham credit' control that has credit enabled but ZERO funding.
One household/firm economy, identical initial state within every seed; neither
fresh money creation nor an interest-bearing bank is represented.

Usage (from project root):
  PYTHONPATH=src:. python research/run_credit_pathways.py --seed 1 --population 10000 --steps 48 --output results/credit_pathways
  PYTHONPATH=src:. python research/run_credit_pathways.py --finalize --seeds 1,2,3,4,5,6,7,8 --population 10000 --steps 48 --output results/credit_pathways
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import platform
from statistics import mean, stdev
import sys
import tempfile

import numpy as np

from civitas.engine import Simulation
from civitas.model import Scenario
from research.run_credit_sensitivity import matched_state_hash

ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    "money_discrepancy_cents", "resource_discrepancy_units", "goods_discrepancy_units",
    "capital_discrepancy_units", "household_cashflow_discrepancy_cents",
    "firm_cashflow_discrepancy_cents", "firm_book_equity_discrepancy_cents",
    "loan_discrepancy_cents",
)
OUTCOMES = (
    "production_units", "consumption_units", "employment_rate", "disposable_income_gini",
    "capital_stock_units", "firm_loan_liabilities_cents", "household_savings_stock_cents",
    "loan_origination_cents", "loan_repayment_cents", "loan_defaults_cents",
)
FUNDING = ("limited", "broad")
TERMS = (2, 6)
SAVINGS = (25, 75)
SOURCE_PATHS = (
    "src/civitas/engine.py", "src/civitas/model.py", "src/civitas/state.py",
    "src/civitas/finance.py", "src/civitas/economy_costs.py",
    "src/civitas/metrics.py", "research/run_credit_sensitivity.py",
    "research/run_credit_pathways.py",
)


def canonical(x: object) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, ensure_ascii=False).encode("utf-8")


def digest(x: object) -> str:
    return hashlib.sha256(canonical(x)).hexdigest()


def source_digest() -> str:
    h = hashlib.sha256()
    for rel in SOURCE_PATHS:
        h.update(rel.encode() + b"\0")
        h.update((ROOT / rel).read_bytes())
    return h.hexdigest()


def configs(population: int, steps: int) -> list[Scenario]:
    if type(population) is not int or population <= 0 or type(steps) is not int or steps < 24:
        raise ValueError("population must be positive and horizon must be >=24")
    base = Scenario.from_file(ROOT / "scenarios/credit_research_base.json")
    base = replace(base, population=population, steps=steps,
                   firms_per_sector=10, initial_resource=5_000_000,
                   resource_capacity=6_000_000, initial_firm_cash_cents=40_000,
                   initial_capital_units_per_firm=40)
    cells: list[Scenario] = []
    for rate in SAVINGS:
        group = replace(base, household_savings_rate=rate / 100)
        cells.append(replace(group, name=f"s{rate}_control", credit_enabled=False))
        cells.append(replace(group, name=f"s{rate}_sham", credit_enabled=True,
                             credit_lender_savings_share=0.0))
        for fund, share in (("limited", 0.15), ("broad", 0.75)):
            for term in TERMS:
                cells.append(replace(group, name=f"s{rate}_{fund}_term{term}",
                                     credit_enabled=True, credit_lender_savings_share=share,
                                     credit_term_periods=term))
    for cfg in cells:
        cfg.validate()
    return cells


def _write_atomic(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".civitas-",
                                     suffix=".tmp", mode="w", delete=False,
                                     encoding="utf-8") as stream:
        filename = stream.name
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(filename, path)


def observe(config: Scenario) -> tuple[dict, str, dict]:
    sim = Simulation(config)
    init_hash = matched_state_hash(sim)
    periods = []
    outstanding = 0
    for result in sim.run(config.steps):
        m = result.metrics
        for invariant in CHECKS:
            if m[invariant] != 0:
                raise AssertionError(f"{config.name}: period {m['step']}: {invariant}={m[invariant]}")
        # Stronger than an aggregate balance check: principal changes reconcile
        # with every recorded origination, repayment and writeoff in each period.
        predicted = (outstanding + m["loan_origination_cents"]
                     - m["loan_repayment_cents"] - m["loan_defaults_cents"])
        if predicted != m["firm_loan_liabilities_cents"] or predicted < 0:
            raise AssertionError(f"loan roll-forward mismatch in {config.name}")
        outstanding = predicted
        periods.append({key: m[key] for key in ("step", *CHECKS, *OUTCOMES)})
    sim.state.validate()
    return ({"name": config.name, "config_sha256": digest(config.to_dict()),
             "initial_state_sha256": init_hash, "periods": periods},
            init_hash, sim.rng.bit_generator.state)


def run_cell(output: Path, seed: int, config: Scenario) -> dict:
    """Persist and verify one scenario atomically; safe to resume interrupted seeds."""
    path = output / f"seed_{seed:04d}" / f"{config.name}.json"
    cfg = replace(config, seed=seed)
    if path.exists():
        return verify_cell(path, cfg, source_digest())
    cell, _, _ = observe(cfg)
    payload = {"schema": 1, "seed": seed, "source_sha256": source_digest(),
               "cell": cell}
    _write_atomic(path, {**payload, "data_sha256": digest(payload)})
    return verify_cell(path, cfg, source_digest())


def verify_cell(path: Path, config: Scenario, source: str) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    checksum = record.pop("data_sha256", None)
    if checksum != digest(record):
        raise ValueError(f"invalid individual cell checksum: {path}")
    if (record.get("schema") != 1 or record.get("source_sha256") != source or
            record.get("seed") != config.seed or
            record["cell"]["name"] != config.name or
            record["cell"]["config_sha256"] != digest(config.to_dict())):
        raise ValueError(f"individual cell configuration changed: {path}")
    periods = record["cell"]["periods"]
    if len(periods) != config.steps or [p["step"] for p in periods] != list(range(1, config.steps+1)):
        raise ValueError("incomplete individual cell periods")
    outstanding = 0
    for p in periods:
        if any(p[k] != 0 for k in CHECKS):
            raise ValueError("individual cell conservation failure")
        outstanding += p["loan_origination_cents"] - p["loan_repayment_cents"] - p["loan_defaults_cents"]
        if outstanding != p["firm_loan_liabilities_cents"] or outstanding < 0:
            raise ValueError("individual cell principal mismatch")
    record["data_sha256"] = checksum
    return record


def execute_seed(output: Path, seed: int, *, population: int = 10_000,
                 steps: int = 48) -> dict:
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be nonnegative integer")
    expected = configs(population, steps)
    path = output / f"seed_{seed:04d}.json"
    if path.exists():
        return verify_seed(path, seed, expected, source_digest())
    cells = [run_cell(output, seed, cfg)["cell"] for cfg in expected]
    initial_hashes = [c["initial_state_sha256"] for c in cells]
    if len(set(initial_hashes)) != 1:
        raise AssertionError("treatments do not share identical initial state and RNG")
    # Controls: reserving zero savings for lending must not change outcomes,
    # including the random stream. Compare complete period-level records.
    by_name = {c["name"]: c for c in cells}
    for s in SAVINGS:
        if by_name[f"s{s}_control"]["periods"] != by_name[f"s{s}_sham"]["periods"]:
            raise AssertionError("zero-lending sham changed the economic trajectory")
    payload = {"schema": 1, "seed": seed, "population": population, "steps": steps,
               "source_sha256": source_digest(), "cells": cells}
    record = {**payload, "data_sha256": digest(payload)}
    _write_atomic(path, record)
    return verify_seed(path, seed, expected, source_digest())


def verify_seed(path: Path, seed: int, expected: list[Scenario], source: str) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    checksum = record.pop("data_sha256", None)
    if checksum != digest(record):
        raise ValueError(f"invalid shard checksum: {path}")
    if (record.get("schema") != 1 or record.get("seed") != seed or
            record.get("population") != expected[0].population or
            record.get("steps") != expected[0].steps or
            record.get("source_sha256") != source):
        raise ValueError("seed, source, horizon, or population changed")
    actual = record.get("cells", [])
    if len(actual) != len(expected) or {c["name"] for c in actual} != {c.name for c in expected}:
        raise ValueError("missing or repeated treatment")
    for c in actual:
        cfg = next(e for e in expected if e.name == c["name"])
        if c["config_sha256"] != digest(replace(cfg, seed=seed).to_dict()):
            raise ValueError("configuration mismatch")
        periods = c["periods"]
        if len(periods) != cfg.steps or [p["step"] for p in periods] != list(range(1, cfg.steps+1)):
            raise ValueError("incomplete period series")
        outstanding = 0
        for p in periods:
            if any(p[k] != 0 for k in CHECKS):
                raise ValueError("accounting discrepancy in saved record")
            outstanding += p["loan_origination_cents"]-p["loan_repayment_cents"]-p["loan_defaults_cents"]
            if outstanding != p["firm_loan_liabilities_cents"] or outstanding < 0:
                raise ValueError("broken outstanding principal identity")
    if len({c["initial_state_sha256"] for c in actual}) != 1:
        raise ValueError("initial states differ")
    by = {c["name"]: c for c in actual}
    for s in SAVINGS:
        if by[f"s{s}_control"]["periods"] != by[f"s{s}_sham"]["periods"]:
            raise ValueError("sham trajectory differs")
    record["data_sha256"] = checksum
    return record


def _summary(x: list[float]) -> dict:
    return {"mean": mean(x), "sample_sd": stdev(x) if len(x) > 1 else None,
            "n": len(x)}


def _contrast(x: list[float]) -> dict:
    s = _summary(x)
    sd = s["sample_sd"]
    mu = s["mean"]
    s["approx_mc_95_interval"] = ([mu - 1.96 * sd / math.sqrt(len(x)),
                                   mu + 1.96 * sd / math.sqrt(len(x))]
                                  if sd is not None else None)
    return s


def finalize(output: Path, seeds: list[int], *, population: int = 10_000,
             steps: int = 48) -> dict:
    if not seeds or len(set(seeds)) != len(seeds) or any(type(s) is not int or s < 0 for s in seeds):
        raise ValueError("seeds must be unique nonnegative integer IDs")
    expected = configs(population, steps)
    hashes = source_digest()
    data = [verify_seed(output / f"seed_{seed:04d}.json", seed, expected, hashes)
            for seed in seeds]
    cells = {cfg.name: [] for cfg in expected}
    for row in data:
        for cell in row["cells"]:
            cells[cell["name"]].append(cell)
    horizons = sorted({24, steps})
    means = {}
    paired = {}
    for name, rows in cells.items():
        means[name] = {}
        for t in horizons:
            last = [c["periods"][t-1] for c in rows]
            means[name][str(t)] = {
                k: _summary([float(p[k]) for p in last if p[k] is not None])
                for k in ("production_units", "consumption_units", "employment_rate",
                          "disposable_income_gini", "capital_stock_units",
                          "firm_loan_liabilities_cents")
            }
        means[name]["flows"] = {
            k: sum(sum(int(p[k]) for p in c["periods"]) for c in rows)
            for k in ("loan_origination_cents", "loan_repayment_cents", "loan_defaults_cents")}
    for s in SAVINGS:
        for t in horizons:
            base = [r["periods"][t-1] for r in cells[f"s{s}_control"]]
            for fund in FUNDING:
                for term in TERMS:
                    name = f"s{s}_{fund}_term{term}"
                    treated = [r["periods"][t-1] for r in cells[name]]
                    label = f"s{s}_{fund}_term{term}_minus_control_t{t}"
                    paired[label] = {}
                    for metric in ("production_units", "consumption_units", "employment_rate",
                                   "disposable_income_gini"):
                        delta = [float(a[metric]) - float(b[metric]) for a,b in zip(treated,base)
                                 if a[metric] is not None and b[metric] is not None]
                        paired[label][metric] = _contrast(delta) if delta else None
            # The interaction estimates whether higher household saving changes
            # credit treatment effect (not saving rate's direct effect).
    for fund in FUNDING:
        for term in TERMS:
            for t in horizons:
                c25 = cells["s25_control"]
                c75 = cells["s75_control"]
                t25 = cells[f"s25_{fund}_term{term}"]
                t75 = cells[f"s75_{fund}_term{term}"]
                diff = [((t75[i]["periods"][t-1]["production_units"] - c75[i]["periods"][t-1]["production_units"])
                         - (t25[i]["periods"][t-1]["production_units"] - c25[i]["periods"][t-1]["production_units"]))
                        for i in range(len(seeds))]
                paired[f"savings_credit_interaction_{fund}_term{term}_t{t}"] = {"production_units": _contrast(diff)}
    result = {
        "design": {"population": population, "steps": steps, "seeds": seeds,
                   "runs": len(seeds)*len(expected), "audited_periods": len(seeds)*len(expected)*steps,
                   "scenarios": len(expected), "source_sha256": hashes,
                   "environment": {"python": sys.version.split()[0], "numpy": np.__version__,
                                   "platform": platform.platform()},
                   "limits": "Same stochastic initial state; 0% fund sham; fixed synthetic rules, zero interest, no calibration; intervals are seed MC only."},
        "final_period_means": means, "paired_effects": paired,
        "shard_sha256": {str(row["seed"]): row["data_sha256"] for row in data},
    }
    _write_atomic(output / "summary.json", result)
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument("--seed", type=int)
    action.add_argument("--finalize", action="store_true")
    p.add_argument("--cell", default=None, help="with --seed: run/verify ONE treatment shard only")
    p.add_argument("--population", type=int, default=10_000)
    p.add_argument("--steps", type=int, default=48)
    p.add_argument("--seeds", default="1,2,3,4,5,6,7,8")
    p.add_argument("--output", type=Path, default=Path("results/credit_pathways"))
    a = p.parse_args()
    if a.finalize:
        result = finalize(a.output, [int(x) for x in a.seeds.split(",")],
                          population=a.population, steps=a.steps)
        print(json.dumps(result["design"], indent=2))
    elif a.cell is not None:
        cfg = next((x for x in configs(a.population, a.steps) if x.name == a.cell), None)
        if cfg is None:
            p.error(f"unknown cell {a.cell}")
        record = run_cell(a.output, a.seed, cfg)
        print(json.dumps({"seed": a.seed, "cell": a.cell,
                          "data_sha256": record["data_sha256"]}, indent=2))
    else:
        record = execute_seed(a.output, a.seed, population=a.population, steps=a.steps)
        print(json.dumps({"seed": record["seed"], "cells": len(record["cells"]),
                          "data_sha256": record["data_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
