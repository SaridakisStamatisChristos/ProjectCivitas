"""Matched initial-state and RNG factorial: access, region allocation, price quotes.

Scientific scope: within-model experimental intervention. Not an empirical or
real-world prediction. Per-seed atomic CSV shards and SHA-256 verification.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import sys
import time

from civitas.engine import Simulation
from civitas.model import Scenario
from civitas.persistence import canonical_json, config_digest
from research.run_matched_market_access import digest_state

ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENTS = ("modulo", "balanced_shuffle")
INFORMATION = ("full", "two_quotes")
ACCESS = (False, True)
METRICS = ("production_per_person", "consumption_per_person", "employment_rate",
           "disposable_income_gini", "information_missed_per_person",
           "unmet_stock_per_person", "unmet_budget_per_person")
AUDIT = ("money_discrepancy_cents", "goods_discrepancy_units",
         "resource_discrepancy_units", "capital_discrepancy_units",
         "household_cashflow_discrepancy_cents", "firm_cashflow_discrepancy_cents")
HEADER = ["seed", "step", "assignment", "information", "sales_restricted", *METRICS]


def arm_names():
    return [(a, i, s) for a in ASSIGNMENTS for i in INFORMATION for s in ACCESS]


def baseline(seed: int, population: int, firms_per_sector: int, regions: int) -> Scenario:
    base = Scenario.from_file(ROOT / "scenarios/population_normalized/o08_s00_n10000.json")
    # Use the SAME initial per-household cash, per-firm cash, and capital setup
    # across all eight arms. Within-size pairing is exact, not cross-size.
    per_household_resource = 50
    return replace(base, name="region_information_factorial", seed=seed,
                   population=population, firms_per_sector=firms_per_sector,
                   market_regions=regions,
                   initial_resource=population * per_household_resource,
                   resource_capacity=population * per_household_resource * 6 // 5,
                   household_region_assignment="modulo", region_assignment_seed=37,
                   buyer_price_information="full",
                   restrict_household_sales=False, restrict_labor_hiring=False)


def scenario_digest(seed: int, population: int, firms_per_sector: int, regions: int) -> str:
    return config_digest(baseline(seed, population, firms_per_sector, regions))


def measured(metrics: dict, pop: int) -> dict:
    return dict(production_per_person=metrics["production_units"] / pop,
                consumption_per_person=metrics["consumption_units"] / pop,
                employment_rate=metrics["employment_rate"],
                disposable_income_gini=metrics["disposable_income_gini"],
                information_missed_per_person=metrics["information_missed_purchase_opportunities"] / pop,
                unmet_stock_per_person=metrics["unmet_stock_demand_units"] / pop,
                unmet_budget_per_person=metrics["unmet_budget_demand_units"] / pop)


def run_seed(output: Path, seed: int, steps: int, *, population: int = 10_000,
             firms_per_sector: int = 20, regions: int = 5):
    if type(seed) is not int or seed < 0 or steps < 1 or population < 1:
        raise ValueError("positive population/steps and nonnegative integer seed required")
    base = baseline(seed, population, firms_per_sector, regions)
    base.validate()
    output = Path(output)
    shard = output / "shards"
    shard.mkdir(parents=True, exist_ok=True)
    target = shard / f"seed_{seed:04d}.csv"
    sidecar = shard / f"seed_{seed:04d}.json"
    root = Simulation(base)
    root_rng = deepcopy(root.rng.bit_generator.state)
    initial_sha = digest_state(root)
    start = time.perf_counter()
    tmp = target.with_suffix(".csv.part")
    common_final_rng = None
    count = 0
    try:
        with tmp.open("w", newline="", encoding="utf8") as out:
            writer = csv.DictWriter(out, fieldnames=HEADER)
            writer.writeheader()
            for assignment, information, sales in arm_names():
                conf = replace(base, household_region_assignment=assignment,
                               buyer_price_information=information,
                               restrict_household_sales=sales)
                sim = Simulation(conf, state=deepcopy(root.state), rng_state=deepcopy(root_rng))
                if digest_state(sim) != initial_sha:
                    raise AssertionError("treatment has different initial economic state")
                for p in sim.run(steps):
                    if any(p.metrics[m] != 0 for m in AUDIT):
                        raise AssertionError(f"invariant failure: seed={seed}, arm={(assignment, information, sales)}")
                    writer.writerow(dict(seed=seed, step=p.metrics["step"],
                                         assignment=assignment, information=information,
                                         sales_restricted=int(sales),
                                         **measured(p.metrics, population)))
                    count += 1
                digest_rng = hashlib.sha256(canonical_json(sim.rng.bit_generator.state).encode()).hexdigest()
                if common_final_rng is None:
                    common_final_rng = digest_rng
                elif common_final_rng != digest_rng:
                    raise AssertionError("post-treatment RNG streams differ")
        tmp.replace(target)
        info = {"seed": seed, "steps": steps, "population": population,
                "firms_per_sector": firms_per_sector, "market_regions": regions,
                "scenario_sha256": scenario_digest(seed, population, firms_per_sector, regions),
                "initial_state_sha256": initial_sha,
                "final_rng_sha256": common_final_rng,
                "records": count, "csv_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "wall_seconds": time.perf_counter() - start}
        sidecar.write_text(json.dumps(info, indent=2) + "\n", encoding="utf8")
        return info
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def estimate(xs: list[float]) -> dict:
    if any(not math.isfinite(x) for x in xs):
        raise ValueError("nonfinite experimental values")
    mean = statistics.mean(xs)
    sd = statistics.stdev(xs) if len(xs) > 1 else None
    err = 1.96 * sd / math.sqrt(len(xs)) if sd is not None else None
    return {"mean": mean, "n": len(xs), "sample_sd": sd,
            "approximate_95pct_seed_interval": [mean-err, mean+err] if err is not None else None}


def finaleffects(data: dict, seeds: int, steps: int) -> dict:
    """Difference in potential outcomes per *identical initialization*, not a social-law estimate."""
    results = {"means": {}, "paired_effects": {}, "notes": [
        "Eight arms per seed share precisely matched agent, firm, equity, resource and RNG state.",
        "Assignment shuffling is balanced and uses a separate deterministic RNG substream.",
        "Price quote information (two sellers) is distinct from access eligibility (all or local firms).",
        "Seed intervals quantify Monte Carlo variability, not structural/model uncertainty.",
        "This is a synthetic simulation; no real-world policy implication is established."]}
    for a, i, s in arm_names():
        key=f"{a}|{i}|{'local' if s else 'open'}"
        results["means"][key]={m:estimate([data[(seed,steps,a,i,s)][m] for seed in range(1,seeds+1)])
                               for m in METRICS if all(data[(seed,steps,a,i,s)][m] is not None for seed in range(1,seeds+1))}
    for a in ASSIGNMENTS:
        for s in ACCESS:
            key=f"quotes_effect|{a}|{'local' if s else 'open'}"
            results["paired_effects"][key]={}
            for m in METRICS:
                diffs=[]
                for seed in range(1,seeds+1):
                    left=data[(seed,steps,a,"two_quotes",s)][m]
                    right=data[(seed,steps,a,"full",s)][m]
                    if left is None or right is None: diffs=[];break
                    diffs.append(left-right)
                if diffs:results["paired_effects"][key][m]=estimate(diffs)
        for i in INFORMATION:
            key=f"access_effect|{a}|{i}"
            results["paired_effects"][key]={}
            for m in METRICS:
                diffs=[]
                for seed in range(1,seeds+1):
                    l=data[(seed,steps,a,i,True)][m];r=data[(seed,steps,a,i,False)][m]
                    if l is None or r is None: diffs=[];break
                    diffs.append(l-r)
                if diffs:results["paired_effects"][key][m]=estimate(diffs)
        key=f"quote_access_interaction|{a}"
        results["paired_effects"][key]={}
        for m in METRICS:
            diffs=[]
            for seed in range(1,seeds+1):
                vals=[data[(seed,steps,a,i,s)][m] for i,s in
                      (("two_quotes",True),("full",True),("two_quotes",False),("full",False))]
                if any(v is None for v in vals): diffs=[];break
                diffs.append(vals[0]-vals[1]-vals[2]+vals[3])
            if diffs:results["paired_effects"][key][m]=estimate(diffs)
    return results


def finalize(output: Path, seeds: int, steps: int, *, population: int = 10_000,
             firms_per_sector: int = 20, regions: int = 5) -> dict:
    if not isinstance(seeds,int) or seeds < 2 or steps < 1:
        raise ValueError("at least two completed seeds and one time step required")
    output=Path(output)
    records={}
    metadata=[]
    all_rows=[]
    for seed in range(1,seeds+1):
        csvfile=output/"shards"/f"seed_{seed:04d}.csv"
        sidecar=output/"shards"/f"seed_{seed:04d}.json"
        info=json.loads(sidecar.read_text(encoding="utf8"))
        if (info["seed"]!=seed or info["steps"]!=steps or
            info["population"]!=population or info["firms_per_sector"]!=firms_per_sector or
            info["market_regions"]!=regions or
            info["scenario_sha256"]!=scenario_digest(seed,population,firms_per_sector,regions) or
            info["records"]!=len(arm_names())*steps or
            hashlib.sha256(csvfile.read_bytes()).hexdigest()!=info["csv_sha256"]):
            raise ValueError(f"seed {seed} definition or digest mismatch")
        metadata.append(info)
        with csvfile.open(newline="",encoding="utf8") as f:
            rows=list(csv.DictReader(f))
        if len(rows)!=len(arm_names())*steps:raise ValueError("incorrect period-row count")
        for row in rows:
            k=(int(row["seed"]),int(row["step"]),row["assignment"],row["information"],bool(int(row["sales_restricted"])))
            if k in records: raise ValueError("duplicate observation key")
            if k[0]!=seed or not (1<=k[1]<=steps) or k[2:] not in arm_names():
                raise ValueError("unknown/mismatched treatment key")
            measures={m:(float(row[m]) if row[m] else None) for m in METRICS}
            records[k]=measures
            all_rows.append(row)
        if len(records) != seed*steps*len(arm_names()):
            raise ValueError("missing treatment-period coverage")
    if len(records)!=seeds*steps*len(arm_names()):raise ValueError("incomplete factorial")
    summary=finaleffects(records,seeds,steps)
    summary["design"]={"seeds":seeds,"periods":steps,"population":population,
                       "firms_per_sector":firms_per_sector,"regions":regions,
                       "simulations":seeds*len(arm_names()),"observations":len(records),
                       "same_initial_state_for_all_treatments":True,
                       "global_hiring_and_interfirm_capital_markets":True}
    # Only emit atomic validated output after all sidecars and rows verified.
    output.mkdir(parents=True,exist_ok=True)
    tmp=output/"periods.csv.part"
    with tmp.open("w",newline="",encoding="utf8") as f:
        writer=csv.DictWriter(f,fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(all_rows)
    tmp.replace(output/"periods.csv")
    summary["periods_csv_sha256"]=hashlib.sha256((output/"periods.csv").read_bytes()).hexdigest()
    (output/"summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n",encoding="utf8")
    (output/"metadata.json").write_text(json.dumps({"python":sys.version,
        "platform":platform.platform(),"complete_shards":metadata},indent=2)+"\n",encoding="utf8")
    return {"observations":len(records), "experiments":seeds*len(arm_names()),
            "summary":summary}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seed",type=int)
    p.add_argument("--finalize",action="store_true")
    p.add_argument("--seeds",type=int,default=12)
    p.add_argument("--steps",type=int,default=24)
    p.add_argument("--population",type=int,default=10_000)
    p.add_argument("--firms-per-sector",type=int,default=20)
    p.add_argument("--regions",type=int,default=5)
    p.add_argument("--output",type=Path,default=ROOT/"research/v02_region_information_12")
    args=p.parse_args()
    if args.seed is not None:
        print(json.dumps(run_seed(args.output,args.seed,args.steps,population=args.population,
            firms_per_sector=args.firms_per_sector,regions=args.regions),indent=2))
    elif args.finalize:
        print(json.dumps(finalize(args.output,args.seeds,args.steps,population=args.population,
            firms_per_sector=args.firms_per_sector,regions=args.regions)["summary"]["design"],indent=2))
    else:
        p.error("use --seed N or --finalize")

if __name__=="__main__":
    main()
