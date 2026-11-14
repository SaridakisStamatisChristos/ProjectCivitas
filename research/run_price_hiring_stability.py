"""Matched-seed, long-horizon price × hiring mechanism experiment.

This executable study uses 2 price rules × 3 hiring rules; it is not a
calibration study. Seeds share initial state, ownership and an RNG stream.
Each complete treatment is saved atomically, source-bound and checksummed.

Examples:
 PYTHONPATH=src:. python research/run_price_hiring_stability.py --seed 1 --population 10000 --steps 72
 PYTHONPATH=src:. python research/run_price_hiring_stability.py --finalize --population 10000 --steps 72 --seeds 1,2,3,4,5,6,7,8
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
from research.run_credit_sensitivity import matched_state_hash
from research.run_demand_diagnostics import CHECKS, diag, scenarios

ROOT = Path(__file__).resolve().parents[1]
PRICE_RULES = ("inventory", "affordability_guard")
HIRING_RULES = ("adaptive", "blended", "stationary")
METRICS = ("production_units", "consumption_units", "employed", "resource_stock",
           "capital_stock_units", "total_inventory_units", "firm_cash_stock_cents",
           "household_spendable_cash_cents", "household_savings_stock_cents",
           "quoted_price_mean_cents", "budget_unmet_share_of_attempts",
           "household_nonessential_affordability", "firm_cash_share")
SOURCES = ("src/civitas/engine.py", "src/civitas/model.py", "src/civitas/state.py",
           "src/civitas/market_rules.py", "src/civitas/finance.py", "src/civitas/economy_costs.py",
           "research/run_demand_diagnostics.py", "research/run_credit_sensitivity.py",
           "research/run_price_hiring_stability.py")


def encoded(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, ensure_ascii=False).encode("utf8")


def digest(value) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def source_digest() -> str:
    h = hashlib.sha256()
    for f in SOURCES:
        h.update(f.encode() + b"\0" + (ROOT / f).read_bytes())
    return h.hexdigest()


def configs(population: int = 10_000, steps: int = 72) -> list:
    if type(population) is not int or population <= 0 or type(steps) is not int or steps < 48:
        raise ValueError("positive integer population and horizon >= 48 required")
    base = scenarios(population=population, steps=steps)[0]
    result = []
    for price in PRICE_RULES:
        for hiring in HIRING_RULES:
            result.append(replace(base, name=f"{price}__{hiring}", seed=0,
                                  price_update_rule=price,
                                  hiring_expectation_rule=hiring))
    return result


def atomic_json_gz(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".civitas-", delete=False) as stream:
        temp = stream.name
        try:
            with gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as zipped:
                zipped.write(encoded(record))
            stream.flush()
            os.fsync(stream.fileno())
        except Exception:
            os.unlink(temp)
            raise
    os.replace(temp, path)


def verify_cell(path: Path, cfg) -> dict:
    with gzip.open(path, "rb") as f:
        record = json.loads(f.read())
    sha = record.pop("sha256", None)
    if sha != digest(record):
        raise ValueError("experiment checksum mismatch")
    if record.get("schema") != 1 or record.get("source_sha256") != source_digest():
        raise ValueError("experiment source mismatch")
    if record.get("config_sha256") != digest(cfg.to_dict()):
        raise ValueError("experiment configuration mismatch")
    periods = record.get("periods")
    if not isinstance(periods, list) or len(periods) != cfg.steps:
        raise ValueError("missing periods")
    for idx, p in enumerate(periods, 1):
        if p.get("step") != idx:
            raise ValueError("period ordering mismatch")
        if any(p.get(k) != 0 for k in CHECKS):
            raise ValueError("accounting discrepancy in period")
        if (p["household_monetary_assets_cents"] !=
                p["household_spendable_cash_cents"] + p["household_savings_stock_cents"]):
            raise ValueError("household cash partition mismatch")
        if (p["household_monetary_assets_cents"] + p["firm_cash_stock_cents"] +
                p["government_cash_stock_cents"] != record["initial_total_money_cents"]):
            raise ValueError("monetary stock mismatch")
        if any(p[k] < 0 for k in ("resource_stock", "total_inventory_units", "production_units")):
            raise ValueError("negative physical stock")
    record["sha256"] = sha
    return record


def execute_cell(root: Path, cfg) -> dict:
    path = root / f"seed_{cfg.seed:04d}" / f"{cfg.name}.json.gz"
    if path.exists():
        return verify_cell(path, cfg)
    sim = Simulation(cfg)
    initial = matched_state_hash(sim)
    periods = []
    for _ in range(cfg.steps):
        m = sim.step().metrics
        if any(m.get(k) != 0 for k in CHECKS):
            raise AssertionError("simulation conservation failure")
        periods.append(diag(sim, m))
    row = {"schema": 1, "seed": cfg.seed, "arm": cfg.name,
           "config_sha256": digest(cfg.to_dict()), "source_sha256": source_digest(),
           "initial_state_sha256": initial,
           "end_rng_sha256": digest(sim.rng.bit_generator.state),
           "initial_total_money_cents": sim.state.initial_total_money,
           "periods": periods}
    atomic_json_gz(path, {**row, "sha256": digest(row)})
    return verify_cell(path, cfg)


def execute_seed(root: Path, seed: int, *, population: int = 10_000,
                 steps: int = 72) -> dict:
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be nonnegative integer")
    results = [execute_cell(root, replace(c, seed=seed)) for c in configs(population, steps)]
    if len({r["initial_state_sha256"] for r in results}) != 1:
        raise AssertionError("initial conditions differ among treatments")
    if len({r["end_rng_sha256"] for r in results}) != 1:
        raise AssertionError("random consumption diverged among treatments")
    return {"seed": seed, "runs": len(results), "periods": len(results) * steps}


def estimate(values: list[float]) -> dict:
    n = len(values)
    m = mean(values)
    sd = stdev(values) if n > 1 else None
    return {"mean": m, "sample_sd": sd, "n": n,
            "mc_95_lower": m - 1.96*sd/(n**0.5) if sd is not None else None,
            "mc_95_upper": m + 1.96*sd/(n**0.5) if sd is not None else None}


def finalize(root: Path, seeds: list[int], *, population: int = 10_000,
             steps: int = 72, write: bool = True) -> dict:
    if not seeds or len(set(seeds)) != len(seeds) or any(type(x) is not int or x < 0 for x in seeds):
        raise ValueError("need unique nonnegative seeds")
    arms = configs(population, steps)
    dataset = {}
    for seed in seeds:
        cells = {c.name: verify_cell(root/f"seed_{seed:04d}"/f"{c.name}.json.gz",
                                     replace(c, seed=seed)) for c in arms}
        if len({x["initial_state_sha256"] for x in cells.values()}) != 1:
            raise ValueError("unmatched seed initial states")
        if len({x["end_rng_sha256"] for x in cells.values()}) != 1:
            raise ValueError("random stream misalignment")
        dataset[seed] = cells
    horizons = sorted(set((24, 48, steps)))
    summary = {"schema": 1, "source_sha256": source_digest(),
               "design": {"population": population, "steps": steps, "seeds": sorted(seeds),
                          "arms": [c.name for c in arms], "runs": len(seeds)*len(arms),
                          "audited_periods": len(seeds)*len(arms)*steps,
                          "price_affordability_floor": arms[3].price_affordability_floor},
               "environment": {"python": sys.version.split()[0], "numpy": np.__version__,
                               "platform": platform.platform()},
               "means": {}, "paired": {}}
    def values(arm: str, t: int, metric: str) -> list[float]:
        return [dataset[seed][arm]["periods"][t-1][metric] for seed in seeds]
    for arm in [c.name for c in arms]:
        for t in horizons:
            summary["means"][f"{arm}_t{t}"] = {metric: estimate(values(arm, t, metric))
                                                for metric in METRICS}
        for t in horizons:
            if arm != "inventory__adaptive":
                vals = [a-b for a,b in zip(values(arm,t,"production_units"),
                                           values("inventory__adaptive",t,"production_units"))]
                summary["paired"][f"{arm}_vs_control_t{t}_production"] = estimate(vals)
    for hiring in HIRING_RULES:
        for t in horizons:
            a = values(f"affordability_guard__{hiring}", t, "production_units")
            b = values(f"inventory__{hiring}", t, "production_units")
            summary["paired"][f"guard_effect__{hiring}_t{t}"] = estimate([x-y for x,y in zip(a,b)])
    for hiring in ("blended", "stationary"):
        for t in horizons:
            a = [x-y for x,y in zip(values(f"affordability_guard__{hiring}",t,"production_units"),
                                     values(f"inventory__{hiring}",t,"production_units"))]
            b = [x-y for x,y in zip(values("affordability_guard__adaptive",t,"production_units"),
                                     values("inventory__adaptive",t,"production_units"))]
            summary["paired"][f"price_hiring_interaction__{hiring}_t{t}"] = estimate([x-y for x,y in zip(a,b)])
    if write:
        path = root/"summary.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, sort_keys=True, indent=2, allow_nan=False)+"\n", encoding="utf8")
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--seed", type=int)
    mode.add_argument("--finalize", action="store_true")
    mode.add_argument("--verify-only", action="store_true")
    p.add_argument("--seeds", default="1,2,3,4,5,6,7,8")
    p.add_argument("--population", type=int, default=10000)
    p.add_argument("--steps", type=int, default=72)
    p.add_argument("--output", type=Path, default=Path("results/price_hiring_stability"))
    a = p.parse_args()
    if a.seed is not None:
        print(json.dumps(execute_seed(a.output, a.seed, population=a.population, steps=a.steps)))
    else:
        seeds = [int(s) for s in a.seeds.split(",")]
        out = finalize(a.output, seeds, population=a.population, steps=a.steps, write=not a.verify_only)
        print(json.dumps({"design": out["design"], "paired": out["paired"]}, indent=2))


if __name__ == "__main__":
    main()
