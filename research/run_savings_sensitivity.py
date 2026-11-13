"""Deterministic 2x3 savings/ownership factorial, summary and paired contrasts.

Run from project root:
  PYTHONPATH=src python research/run_savings_sensitivity.py --population 1000 --seeds 30

Intervals are normal-approximation Monte Carlo intervals over paired seeds,
not uncertainty bands for the economic model or real-world estimates.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import json
from pathlib import Path
import platform
import statistics
import time

import numpy as np
from civitas import __version__
from civitas.engine import Simulation
from civitas.model import Scenario
from civitas.persistence import config_digest

KEYS = ("employment_rate", "production_units", "consumption_units", "disposable_income_gini",
        "modeled_net_worth_gini", "household_monetary_assets_gini", "household_savings_stock_cents",
        "household_savings_deposited_cents", "household_savings_withdrawn_cents",
        "capital_stock_units", "firm_profit_proxy_cents", "resource_stock", "money_discrepancy_cents",
        "goods_discrepancy_units", "capital_discrepancy_units", "household_cashflow_discrepancy_cents",
        "firm_cashflow_discrepancy_cents")


def stats(vals):
    vals = [float(v) for v in vals if v is not None]
    if not vals:
        return {"n": 0, "mean": None, "sample_sd": None}
    return {"n": len(vals), "mean": statistics.mean(vals),
            "sample_sd": statistics.stdev(vals) if len(vals) > 1 else None}


def paired(a, b):
    diffs = [float(y) - float(x) for x, y in zip(a, b) if x is not None and y is not None]
    s = stats(diffs)
    if s["n"] > 1:
        margin = 1.96 * s["sample_sd"] / s["n"] ** 0.5
        s["approx_95pct_mc_interval"] = [s["mean"] - margin, s["mean"] + margin]
    else:
        s["approx_95pct_mc_interval"] = None
    return s


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--population", type=int, default=1000)
    p.add_argument("--only", help="run one named scenario and persist a resumable partial")
    p.add_argument("--finalize", action="store_true", help="aggregate six saved scenario partials")
    p.add_argument("--seeds", type=int, default=30, help="seeds 1..N")
    p.add_argument("--steps", type=int, default=24)
    p.add_argument("--output", type=Path, default=Path("results/savings_sensitivity"))
    a = p.parse_args(argv)
    if a.population < 0 or a.seeds < 2 or a.steps < 1:
        p.error("population >= 0, seeds >= 2 and steps >= 1 are required")
    configs = [Scenario.from_file(p) for p in sorted(Path("scenarios/savings_ownership").glob("*.json"))]
    assert len(configs) == 6, "expected exactly six factorial configurations"
    a.output.mkdir(parents=True, exist_ok=True)
    partial_dir = a.output / "partials"
    partial_dir.mkdir(exist_ok=True)
    observations = {}
    records = []
    t0 = time.perf_counter()
    if a.finalize:
        for c in configs:
            pfile = partial_dir / f"{c.name}.json"
            saved = json.loads(pfile.read_text(encoding="utf8"))
            if (saved["population"] != a.population or saved["steps"] != a.steps or
                    saved["seed_count"] != a.seeds or saved["scenario_digest"] != config_digest(c)):
                raise ValueError(f"partial metadata mismatch for {c.name}")
            observations[c.name] = {int(seed): m for seed, m in saved["by_seed"].items()}
        for name, obs in observations.items():
            for seed in range(1, a.seeds + 1):
                m = obs[seed]
                records.append({"scenario": name, "seed": seed, "population": a.population,
                                "steps": a.steps, **{key: m[key] for key in KEYS}})
        elapsed = sum(json.loads((partial_dir / f"{c.name}.json").read_text())["wall_seconds"]
                      for c in configs)
    else:
        selected = [c for c in configs if a.only is None or c.name == a.only]
        if not selected:
            raise ValueError("unrecognized --only scenario")
        for c0 in selected:
            name = c0.name
            observations[name] = {}
            t_scenario = time.perf_counter()
            for seed in range(1, a.seeds + 1):
                c = replace(c0, population=a.population, steps=a.steps, seed=seed)
                c.validate()
                sim = Simulation(c)
                periods = sim.run()
                metrics = periods[-1].metrics
                if any(metrics[k] != 0 for k in ("money_discrepancy_cents", "goods_discrepancy_units",
                                                       "capital_discrepancy_units", "firm_cashflow_discrepancy_cents",
                                                       "household_cashflow_discrepancy_cents")):
                    raise AssertionError(f"accounting failed for {name} seed {seed}")
                observations[name][seed] = metrics
                records.append({"scenario": name, "seed": seed, "population": a.population,
                                "steps": a.steps, **{key: metrics[key] for key in KEYS}})
            (partial_dir / f"{name}.json").write_text(json.dumps({
                "population": a.population, "steps": a.steps, "seed_count": a.seeds,
                "scenario_digest": config_digest(c0),
                "wall_seconds": time.perf_counter() - t_scenario,
                "by_seed": observations[name],
            }, allow_nan=False) + "\n", encoding="utf8")
            print(f"{name}: {len(observations[name])}/{a.seeds} completed", flush=True)
        if a.only:
            print(json.dumps({"partial_saved": str(partial_dir / (a.only + ".json")),
                              "runs": len(records)}))
            return
        elapsed = time.perf_counter() - t0
    with (a.output / "final_period.csv").open("w", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    summary = {name: {key: stats([o[key] for o in obs.values()]) for key in KEYS}
               for name, obs in observations.items()}
    contrasts = {}
    for own in (3, 8):
        base = f"savings_o{own:02d}_s00"
        for rate in (15, 30):
            treatment = f"savings_o{own:02d}_s{rate:02d}"
            contrasts[f"{treatment} minus {base}"] = {
                key: paired([observations[base][seed][key] for seed in range(1, a.seeds + 1)],
                            [observations[treatment][seed][key] for seed in range(1, a.seeds + 1)])
                for key in KEYS
            }
    for rate in (0, 15, 30):
        baseline = f"savings_o08_s{rate:02d}"
        treatment = f"savings_o03_s{rate:02d}"
        contrasts[f"{treatment} minus {baseline}"] = {
            key: paired([observations[baseline][seed][key] for seed in range(1, a.seeds + 1)],
                        [observations[treatment][seed][key] for seed in range(1, a.seeds + 1)])
            for key in KEYS
        }
    meta = {
        "purpose": "Exploratory savings/ownership factorial in CIVITAS, no real-world calibration",
        "model_version": __version__, "population": a.population, "steps": a.steps,
        "seeds": list(range(1, a.seeds + 1)), "replicates": a.seeds,
        "scenario_digests_at_original_population": {c.name: config_digest(c) for c in configs},
        "python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform(),
        "wall_seconds": elapsed, "total_runs": len(records),
        "uncertainty_note": "Paired normal approximation over seeds only; no model/parameter or external validity CI.",
    }
    for fname, value in (("summary.json", summary), ("paired_contrasts.json", contrasts),
                         ("metadata.json", meta)):
        (a.output / fname).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf8")
    print(json.dumps({"runs": len(records), "wall_seconds": elapsed, "output": str(a.output)}))

if __name__ == "__main__":
    main()
