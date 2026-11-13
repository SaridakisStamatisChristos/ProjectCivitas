"""Reproducible factorial market interaction study (2^3 cells, two topologies).

Contrasts are differences of effects *inside the simulator*. Independent
community initializations are not the same agents as the integrated market;
topology effects are descriptive, not person-level causal estimates.

Run --only CELL on independent workers, then --finalize. The fully validated
aggregator never reports missing or partial cell data as completed research.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import hashlib
import json
import math
import platform
from pathlib import Path
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_market_ablation import METRICS, run_integrated, run_partitioned
from run_population_normalized import make_scenario
from civitas import __version__
from civitas.persistence import config_digest

FACTORS = ("seller", "prices", "hiring")
TOPOLOGIES = ("integrated", "ten_isolated")
CELLS = {f"b{b}p{p}h{h}": (b, p, h)
         for b in (0, 1) for p in (0, 1) for h in (0, 1)}
METADATA_NAME = "settings.json"


def scenario_for(cell: str, seed: int = 1):
    b, p, h = CELLS[cell]
    base = make_scenario(8, 0, 10000, seed)
    return replace(base, name=f"factorial_{cell}",
                   buyer_seller_rule="favorite" if b else "mixed",
                   price_adjustment=0.0 if p else base.price_adjustment,
                   hiring_expectation_rule="stationary" if h else "adaptive")


def data_file(root: Path, cell: str) -> Path:
    return root / f"{cell}_periods.csv"


def settings(seeds: int, steps: int) -> dict:
    return {"schema_version": 1, "software_version": __version__,
            "python": platform.python_version(), "numpy": np.__version__,
            "seeds": seeds, "periods": steps, "cells": CELLS,
            "population_integrated": 10000,
            "isolated_communities": 10, "population_per_community": 1000,
            "hypothesis": "Do seller-search, posted-price adaptation and hiring feedback interact in the topology production gap?",
            "baseline_commit": "5561d0f0716220dfe0948e2d041f00f50e96ce94"}


def run_cell(root: Path, cell: str, seeds: int, steps: int):
    root.mkdir(parents=True, exist_ok=True)
    reference = scenario_for(cell)
    target = data_file(root, cell)
    # Stage a complete file and atomic rename; interrupted runs remain invisible
    # to the finalizer. A unique worker per cell is required.
    temp = target.with_suffix(".csv.part")
    start = time.perf_counter()
    with temp.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["seed", "period", "topology", *METRICS])
        writer.writeheader()
        for seed in range(1, seeds + 1):
            conf = replace(reference, seed=seed)
            for topology, periods in (("integrated", run_integrated(conf, steps)),
                                      ("ten_isolated", run_partitioned(conf, seed, steps))):
                for period_number, metrics in enumerate(periods, 1):
                    writer.writerow({"seed": seed, "period": period_number,
                                     "topology": topology, **metrics})
    temp.replace(target)
    info = {"cell": cell, "factor_settings": dict(zip(FACTORS, CELLS[cell])),
            "seeds": seeds, "steps": steps,
            "scenario_sha256_seed1": config_digest(reference),
            "data_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "internal_simulations": 11 * seeds, "audited_periods": 11 * seeds * steps,
            "topology_period_rows": 2 * seeds * steps,
            "wall_seconds": time.perf_counter() - start,
            **settings(seeds, steps)}
    (root / f"{cell}_metadata.json").write_text(json.dumps(info, indent=2) + "\n")
    (root / f"{cell}_scenario.json").write_text(json.dumps(reference.to_dict(), indent=2) + "\n")
    return info


def read_cells(root: Path, seeds: int, steps: int) -> dict:
    expected = {(s, t, topology) for s in range(1, seeds + 1)
                for t in range(1, steps + 1) for topology in TOPOLOGIES}
    result = {}
    for cell in CELLS:
        filename = data_file(root, cell)
        mdfile = root / f"{cell}_metadata.json"
        md = json.loads(mdfile.read_text())
        if md["seeds"] != seeds or md["steps"] != steps or md["cell"] != cell:
            raise ValueError(f"experiment definition mismatch: {cell}")
        if md["scenario_sha256_seed1"] != config_digest(scenario_for(cell)):
            raise ValueError(f"configuration mismatch: {cell}")
        if hashlib.sha256(filename.read_bytes()).hexdigest() != md["data_sha256"]:
            raise ValueError(f"data integrity failure: {cell}")
        records = {}
        with filename.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = (int(row["seed"]), int(row["period"]), row["topology"])
                if key in records:
                    raise ValueError(f"duplicate row: {cell} {key}")
                records[key] = {name: (float(row[name]) if row[name] else None) for name in METRICS}
        if set(records) != expected:
            raise ValueError(f"incomplete or unexpected records: {cell}")
        result[cell] = records
    return result


def contrast_weights(factors: tuple[int, ...]) -> dict[str, int]:
    """Finite difference of a binary factorial response at all-other-factors zero.

    Example (seller,prices): y110-y100-y010+y000, evaluated at h=0.
    """
    if not factors or len(set(factors)) != len(factors) or any(i not in (0, 1, 2) for i in factors):
        raise ValueError("one to three distinct factor indices required")
    weights = {}
    for bits in range(1 << len(factors)):
        v = [0, 0, 0]
        for j, k in enumerate(factors):
            v[k] = (bits >> j) & 1
        weights["b{}p{}h{}".format(*v)] = (-1) ** (len(factors) - sum(v))
    return weights


def estimate(values: list[float]):
    if not values:
        raise ValueError("empty observations")
    mean = statistics.mean(values)
    sd = statistics.stdev(values) if len(values) > 1 else None
    margin = 1.96 * sd / math.sqrt(len(values)) if sd is not None else None
    return {"n": len(values), "mean": mean, "sample_sd": sd,
            "approx_95pct_mc_interval": [mean-margin, mean+margin] if margin is not None else None}


def analyze(records: dict, seeds: int, steps: int):
    summary = {"cells": {}, "factorial_interactions": {},
               "notes": ["Monte Carlo intervals quantify seed variation only; no external validity.",
                         "Topology seeds do not imply identical individual agents across topologies.",
                         "Factor contrasts are finite differences at other factors set to historical defaults.",
                         "Multiple exploratory contrasts are not multiplicity corrected."]}
    for metric in METRICS:
        for cell in CELLS:
            summary["cells"].setdefault(cell, {})[metric] = {}
            for topology in TOPOLOGIES:
                values = [records[cell][(seed, steps, topology)][metric] for seed in range(1, seeds+1)]
                summary["cells"][cell][metric][topology] = estimate(values) if all(v is not None for v in values) else None
            pairs = [(records[cell][(seed, steps, "integrated")][metric],
                      records[cell][(seed, steps, "ten_isolated")][metric])
                     for seed in range(1, seeds+1)]
            summary["cells"][cell][metric]["gap"] = (estimate([x-y for x, y in pairs])
                                                           if all(x is not None and y is not None for x,y in pairs)
                                                           else None)
        for factors in ((0,), (1,), (2,), (0,1), (0,2), (1,2), (0,1,2)):
            label = "_x_".join(FACTORS[k] for k in factors)
            weights = contrast_weights(factors)
            summary["factorial_interactions"].setdefault(label, {})[metric] = {}
            for topology in (*TOPOLOGIES, "gap"):
                values = []
                for seed in range(1, seeds + 1):
                    y = {cell: records[cell][(seed, steps, "integrated")][metric] -
                         records[cell][(seed, steps, "ten_isolated")][metric]
                         if topology == "gap" and records[cell][(seed, steps, "integrated")][metric] is not None
                         and records[cell][(seed, steps, "ten_isolated")][metric] is not None
                         else records[cell][(seed, steps, topology)][metric] if topology != "gap" else None
                         for cell in weights}
                    if all(v is not None for v in y.values()):
                        values.append(sum(weights[cell] * y[cell] for cell in weights))
                summary["factorial_interactions"][label][metric][topology] = estimate(values) if values else None
    return summary


def finalize(root: Path, seeds: int, steps: int):
    records = read_cells(root, seeds, steps)
    result = analyze(records, seeds, steps)
    result["metadata"] = {**settings(seeds, steps), "internal_simulations": 8*seeds*11,
                          "audited_periods": 8*seeds*11*steps,
                          "topology_period_rows": 8*seeds*2*steps,
                          "cell_digests": {cell: hashlib.sha256(data_file(root, cell).read_bytes()).hexdigest()
                                           for cell in CELLS}}
    (root / "factorial_analysis.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    for cell in CELLS:
        p = result["cells"][cell]["production_per_person"]
        print(f"{cell} integrated={p['integrated']['mean']:.5f} isolated={p['ten_isolated']['mean']:.5f} gap={p['gap']['mean']:+.5f}")
    for name in ("seller_x_prices", "seller_x_hiring", "prices_x_hiring", "seller_x_prices_x_hiring"):
        v = result["factorial_interactions"][name]["production_per_person"]["gap"]
        print(f"{name}: gap contrast {v['mean']:+.6f}, 95% MC {v['approx_95pct_mc_interval']}")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--output", type=Path, default=Path("results/market_factorial"))
    parser.add_argument("--only", choices=CELLS)
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args(argv)
    if args.seeds < 2 or args.steps < 1:
        parser.error("seeds >= 2 and steps >= 1 required")
    args.output.mkdir(parents=True, exist_ok=True)
    if args.finalize:
        if args.only:
            parser.error("--finalize cannot be combined with --only")
        finalize(args.output, args.seeds, args.steps)
    else:
        for cell in ([args.only] if args.only else CELLS):
            result = run_cell(args.output, cell, args.seeds, args.steps)
            print(f"{cell}: {result['internal_simulations']} runs, {result['audited_periods']} audited periods, "
                  f"{result['wall_seconds']:.2f}s", flush=True)
        if not args.only:
            finalize(args.output, args.seeds, args.steps)


if __name__ == "__main__":
    main()
