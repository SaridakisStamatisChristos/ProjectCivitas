"""Repeat the matched-buyer quote/access experiment at standard 10,000-agent scale.

Two seller densities (10, 20 firms per sector) are designed with the same
*aggregate* initial firm cash, physical capital, population and natural stock.
This is not a perfect firm-density causal experiment: matching and ownership
assignment change when the number of firms changes. Each within-density arm
starts from exactly identical state and RNG; the between-density comparison
is explicitly descriptive.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
import csv
import hashlib
import json
from pathlib import Path
import statistics
import math
import sys
import time

from civitas.engine import Simulation
from civitas.persistence import canonical_json, config_digest
from research.run_matched_market_access import digest_state
from research.run_region_information import baseline, measured, AUDIT, METRICS

DENSITIES = (10, 20)
ARMS = ((False, "full"), (False, "two_quotes"),
        (True, "full"), (True, "two_quotes"))
HEADER = ["seed", "step", "firms_per_sector", "sales_restricted", "information", *METRICS]


def build_scenario(seed: int, firms: int, population: int = 10_000):
    if firms not in DENSITIES or population != 10_000:
        raise ValueError("research design supports 10 or 20 firms per sector and 10,000 agents")
    # Total firm cash and initial capital stock conserved across densities.
    root = baseline(seed, population, firms, 5)
    config = replace(root, name=f"market_density_{firms}",
                     initial_firm_cash_cents=2_000_000 * 20 // firms,
                     initial_capital_units_per_firm=450 * 20 // firms,
                     restrict_labor_hiring=False,
                     household_region_assignment="balanced_shuffle",
                     region_assignment_seed=37)
    config.validate()
    return config


def run_shard(output: Path, *, seed: int, firms: int, steps: int = 24):
    if type(seed) is not int or seed < 1 or type(steps) is not int or steps < 1:
        raise ValueError("seed and steps must be positive integers")
    config = build_scenario(seed, firms)
    base = Simulation(config)
    state_sha = digest_state(base)
    starting_rng = deepcopy(base.rng.bit_generator.state)
    folder = Path(output) / "shards"
    folder.mkdir(parents=True, exist_ok=True)
    csv_path = folder / f"f{firms}_s{seed:03d}.csv"
    meta_path = folder / f"f{firms}_s{seed:03d}.json"
    temp = csv_path.with_suffix(".csv.part")
    final_rng = None
    started = time.perf_counter()
    try:
        with temp.open("w", newline="", encoding="utf8") as fp:
            wr = csv.DictWriter(fp, fieldnames=HEADER)
            wr.writeheader()
            for restricted, info in ARMS:
                arm = replace(config, restrict_household_sales=restricted,
                              buyer_price_information=info)
                sim = Simulation(arm, state=deepcopy(base.state), rng_state=deepcopy(starting_rng))
                if digest_state(sim) != state_sha:
                    raise AssertionError("treatment initial states differ")
                for period in sim.run(steps):
                    if any(period.metrics[field] != 0 for field in AUDIT):
                        raise AssertionError("accounting failure")
                    wr.writerow({"seed": seed, "step": period.metrics["step"],
                                 "firms_per_sector": firms, "sales_restricted": int(restricted),
                                 "information": info, **measured(period.metrics, config.population)})
                rng_hash = hashlib.sha256(canonical_json(sim.rng.bit_generator.state).encode()).hexdigest()
                if final_rng is not None and rng_hash != final_rng:
                    raise AssertionError("treatment altered random-number consumption")
                final_rng = rng_hash
        temp.replace(csv_path)
        metadata = {"seed": seed, "firms_per_sector": firms, "steps": steps,
                    "population": config.population, "initial_state_sha256": state_sha,
                    "scenario_sha256": config_digest(config), "final_rng_sha256": final_rng,
                    "rows": len(ARMS) * steps,
                    "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
                    "elapsed_wall_seconds": time.perf_counter() - started}
        meta_path.write_text(json.dumps(metadata, indent=2) + "\n")
        return metadata
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def _estimate(vals):
    vals = list(vals)
    if not vals or not all(math.isfinite(v) for v in vals):
        raise ValueError("valid observations required")
    mu = statistics.mean(vals)
    sd = statistics.stdev(vals) if len(vals) > 1 else None
    err = 1.96 * sd / math.sqrt(len(vals)) if sd is not None else None
    return {"mean": mu, "sd": sd, "n": len(vals),
            "approximate_95pct_seed_interval": [mu-err, mu+err] if err is not None else None}


def finalize(output: Path, *, seeds: int, steps: int = 24):
    if seeds < 2 or steps < 1:
        raise ValueError("at least 2 seeds and 1 period required")
    output = Path(output)
    final = {}
    total_rows = 0
    for firms in DENSITIES:
        for seed in range(1, seeds+1):
            stem = output / "shards" / f"f{firms}_s{seed:03d}"
            csv_path, sidecar = stem.with_suffix(".csv"), stem.with_suffix(".json")
            m = json.loads(sidecar.read_text())
            if (m["seed"] != seed or m["firms_per_sector"] != firms or m["steps"] != steps
                    or m["rows"] != steps * len(ARMS)
                    or m["scenario_sha256"] != config_digest(build_scenario(seed, firms))
                    or m["csv_sha256"] != hashlib.sha256(csv_path.read_bytes()).hexdigest()):
                raise ValueError(f"tampered or incompatible seed shard {stem}")
            with csv_path.open(newline="", encoding="utf8") as fp:
                rows = list(csv.DictReader(fp))
            if len(rows) != m["rows"]:
                raise ValueError(f"incomplete shard {stem}")
            expected = {(int(s), info, step) for s, info in ARMS for step in range(1, steps+1)}
            observed = {(int(row["sales_restricted"]), row["information"], int(row["step"])) for row in rows}
            if observed != expected or len(rows) != len(expected):
                raise ValueError(f"missing or duplicate treatment row {stem}")
            for row in rows:
                if int(row["seed"]) != seed or int(row["firms_per_sector"]) != firms:
                    raise ValueError("mismatched row metadata")
                key = (firms, seed, int(row["sales_restricted"]), row["information"])
                if int(row["step"]) == steps:
                    final[key] = {metric: float(row[metric]) if row[metric] else None for metric in METRICS}
            total_rows += len(rows)
    summary = {"design": {"population": 10_000, "steps": steps, "seeds": seeds,
                          "firms_per_sector": list(DENSITIES), "market_regions": 5,
                          "independent_simulations": seeds*len(DENSITIES)*len(ARMS),
                          "verified_period_records": total_rows,
                          "notes": ["Within-density matched state and RNG; between densities same total money and capital but different firm structures.",
                                    "Intervals measure seed variability only, not model or parameter uncertainty.",
                                    "This is a synthetic experiment, not evidence about real societies."]},
               "means": {}, "paired_effects": {}}
    for firms in DENSITIES:
        for restricted, info in ARMS:
            k = f"{firms}|{'local' if restricted else 'open'}|{info}"
            summary["means"][k] = {metric: _estimate(final[(firms, seed, int(restricted), info)][metric]
                                                        for seed in range(1,seeds+1))
                                    for metric in METRICS
                                    if all(final[(firms,seed,int(restricted),info)][metric] is not None
                                           for seed in range(1,seeds+1))}
        for restricted in (False, True):
            label = f"{firms}|quotes_effect|{'local' if restricted else 'open'}"
            summary["paired_effects"][label] = {
                "production_per_person": _estimate(
                    final[(firms,seed,int(restricted),"two_quotes")]["production_per_person"] -
                    final[(firms,seed,int(restricted),"full")]["production_per_person"]
                    for seed in range(1,seeds+1))}
        summary["paired_effects"][f"{firms}|quote_access_interaction"] = {
            "production_per_person": _estimate(
                final[(firms,seed,1,"two_quotes")]["production_per_person"]-
                final[(firms,seed,1,"full")]["production_per_person"]-
                final[(firms,seed,0,"two_quotes")]["production_per_person"]+
                final[(firms,seed,0,"full")]["production_per_person"]
                for seed in range(1,seeds+1))}
    output.mkdir(parents=True, exist_ok=True)
    (output/"summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    return summary


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output",default="results/region_density_10000")
    ap.add_argument("--seed",type=int)
    ap.add_argument("--firms",type=int,choices=DENSITIES)
    ap.add_argument("--seeds",type=int,default=8)
    ap.add_argument("--steps",type=int,default=24)
    ap.add_argument("--finalize",action="store_true")
    a=ap.parse_args()
    if a.finalize:
        if a.seed is not None or a.firms is not None: ap.error("finalize does not accept seed or firms")
        print(json.dumps(finalize(Path(a.output),seeds=a.seeds,steps=a.steps)["design"],indent=2))
    elif a.seed is not None and a.firms is not None:
        print(json.dumps(run_shard(Path(a.output),seed=a.seed,firms=a.firms,steps=a.steps), indent=2))
    else: ap.error("specify both --seed and --firms, or --finalize")

if __name__=="__main__":main()
