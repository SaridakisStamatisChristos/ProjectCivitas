"""Reproducible, explicitly normalized 2x3 ownership/savings experiment.

The run stores *all periods* per seed, unlike earlier final-period-only
campaigns. Initial per-capita stocks and firm density are audited exactly.
The output describes the model, not external populations.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import replace, asdict
from fractions import Fraction
import hashlib
import json
import platform
from pathlib import Path
import statistics
import time

import numpy as np

from civitas import __version__
from civitas.engine import Simulation
from civitas.model import Scenario
from civitas.normalization import audit_initial_endowments, scale_population_exact
from civitas.persistence import canonical_json, config_digest

FIELDS = ("employment_rate", "production_units", "consumption_units", "disposable_income_gini",
          "modeled_net_worth_gini", "resource_stock", "capital_stock_units",
          "household_savings_stock_cents", "money_discrepancy_cents", "goods_discrepancy_units",
          "capital_discrepancy_units", "resource_discrepancy_units",
          "household_cashflow_discrepancy_cents", "firm_cashflow_discrepancy_cents")
CHECKS = tuple(k for k in FIELDS if k.endswith("discrepancy_cents") or k.endswith("discrepancy_units"))


def make_scenario(ownership: int, savings: int, population: int, seed: int) -> Scenario:
    base = Scenario.from_file(f"scenarios/savings_ownership/savings_o{ownership:02d}_s{savings:02d}.json")
    ref = replace(base, population=1000, firms_per_sector=2,
                  initial_resource=50000, resource_capacity=60000)
    return scale_population_exact(ref, population,
                                  name=f"normalized_o{ownership:02d}_s{savings:02d}_n{population}",
                                  seed=seed)


def summarize(values: list[float | None]) -> dict:
    valid = [float(x) for x in values if x is not None]
    return {"n": len(valid), "mean": statistics.mean(valid) if valid else None,
            "sd": statistics.stdev(valid) if len(valid) > 1 else None}


def paired_contrast(a: list[float | None], b: list[float | None]) -> dict:
    if len(a) != len(b):
        raise ValueError("seeds do not match")
    diffs = [float(y) - float(x) for x, y in zip(a, b) if x is not None and y is not None]
    s = summarize(diffs)
    delta = 1.96 * s["sd"] / (len(diffs) ** .5) if len(diffs) > 1 else None
    return {**s, "approx_95pct_mc_interval": [s["mean"] - delta, s["mean"] + delta]
            if delta is not None else None}


def fractions_to_strings(obj):
    return {k: str(v) if isinstance(v, Fraction) else v for k, v in asdict(obj).items()}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--population", type=int, choices=[1000, 10000], required=True)
    parser.add_argument("--seeds", type=int, default=30)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--only", choices=[f"o{o:02d}_s{s:02d}" for o in (3, 8) for s in (0, 15, 30)])
    args = parser.parse_args(argv)
    if args.seeds < 2 or args.steps < 1:
        parser.error("seeds >= 2 and steps >= 1 required")
    root = args.output or Path(f"results/normalized_{args.population}_seeds{args.seeds}")
    root.mkdir(parents=True, exist_ok=True)
    audits, summaries, obs, contrasts = {}, {}, {}, {}
    total_rows = 0
    total_runs = 0
    begin = time.perf_counter()
    choices = [(o, s) for o in (3, 8) for s in (0, 15, 30)]
    if args.only:
        choices = [(o, s) for o, s in choices if args.only == f"o{o:02d}_s{s:02d}"]
    for ownership, savings in choices:
        label = f"o{ownership:02d}_s{savings:02d}"
        ref = make_scenario(ownership, savings, 1000, 1)
        config = make_scenario(ownership, savings, args.population, 1)
        initial = audit_initial_endowments(config)
        audits[label] = {"reference": fractions_to_strings(audit_initial_endowments(ref)),
                         "target": fractions_to_strings(initial),
                         "config_sha256_seed_1": config_digest(config)}
        (root / f"{label}_config.json").write_text(json.dumps(config.to_dict(), indent=2) + "\n")
        by_seed = {}
        path = root / f"{label}_periods.csv"
        keys = ("seed", "period", "population", "firms", "production_per_person", "consumption_per_person", *FIELDS)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for seed in range(1, args.seeds + 1):
                c = replace(config, seed=seed)
                simulation = Simulation(c)
                last = None
                for period in simulation.run(args.steps):
                    m = period.metrics
                    if any(m[k] != 0 for k in CHECKS):
                        raise AssertionError(f"accounting discrepancy: {label} seed={seed} step={m['step']}")
                    writer.writerow({"seed":seed, "period":m["step"], "population":c.population,
                                     "firms":len(simulation.state.firm_cash),
                                     "production_per_person":m["production_units"]/c.population,
                                     "consumption_per_person":m["consumption_units"]/c.population,
                                     **{k:m[k] for k in FIELDS}})
                    last = m
                    total_rows += 1
                assert last is not None
                by_seed[seed] = {**{k:last[k] for k in FIELDS},
                                 "production_per_person": last["production_units"] / c.population,
                                 "consumption_per_person": last["consumption_units"] / c.population}
                total_runs += 1
        obs[label] = by_seed
        summaries[label] = {k:summarize([rec[k] for rec in by_seed.values()])
                            for k in (*FIELDS,"production_per_person","consumption_per_person")}
        print(f"n={args.population} {label} runs={len(by_seed)} elapsed={time.perf_counter()-begin:.1f}s", flush=True)
    if len(choices) == 6:
        for ownership in (3,8):
            b = obs[f"o{ownership:02d}_s00"]
            for saving in (15,30):
                t = obs[f"o{ownership:02d}_s{saving:02d}"]
                contrasts[f"o{ownership:02d}_s{saving:02d}_vs_s00"] = {
                    k:paired_contrast([b[i][k] for i in range(1,args.seeds+1)],
                                      [t[i][k] for i in range(1,args.seeds+1)])
                    for k in ("production_per_person", "consumption_per_person", "disposable_income_gini")}
    seconds = time.perf_counter() - begin
    metadata = {"model_version":__version__, "python":platform.python_version(), "numpy":np.__version__,
                "platform":platform.platform(), "population":args.population,"seeds":args.seeds,
                "periods":args.steps,"total_runs":total_runs,"total_period_records":total_rows,
                "wall_seconds":seconds,"initialization_method":"exact integer-ratio normalization",
                "limitation":"Uncalibrated synthetic rules; Monte Carlo intervals only; not scale-invariance evidence"}
    for filename, obj in (("initial_audit.json",audits), ("summary.json",summaries),
                          ("paired_contrasts.json",contrasts),("metadata.json",metadata)):
        (root/filename).write_text(json.dumps(obj, indent=2, allow_nan=False)+"\n",encoding="utf8")
    print(json.dumps({"output":str(root),"runs":total_runs,"rows":total_rows,"wall_seconds":round(seconds,2)}),flush=True)


if __name__ == "__main__":
    main()
