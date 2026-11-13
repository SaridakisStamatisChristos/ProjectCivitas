"""Resumable, per-seed investment-credit sensitivity experiment.

Matched within density and household savings propensity. No bank or new money.
Two densities are structurally different arrangements with equal total INITIAL
firm monetary/capital endowments; they are not identical populations of firms.
"""
from __future__ import annotations

import argparse
import dataclasses
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

ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    "money_discrepancy_cents", "resource_discrepancy_units", "goods_discrepancy_units",
    "capital_discrepancy_units", "household_cashflow_discrepancy_cents",
    "firm_cashflow_discrepancy_cents", "firm_book_equity_discrepancy_cents",
    "loan_discrepancy_cents",
)
MEASURES = (
    "production_units", "consumption_units", "employment_rate",
    "disposable_income_gini", "capital_stock_units", "firm_loan_liabilities_cents",
    "household_savings_stock_cents", "loan_origination_cents",
    "loan_repayment_cents", "loan_defaults_cents",
)
SOURCE_PATHS = (
    "src/civitas/engine.py", "src/civitas/model.py", "src/civitas/finance.py",
    "src/civitas/economy_costs.py", "src/civitas/state.py", "src/civitas/metrics.py",
    "src/civitas/persistence.py", "research/run_credit_sensitivity.py",
)


def canonical(item: object) -> bytes:
    return json.dumps(item, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(item: object) -> str:
    return hashlib.sha256(canonical(item)).hexdigest()


def source_digest() -> str:
    d = hashlib.sha256()
    for rel in SOURCE_PATHS:
        d.update(rel.encode("utf-8") + b"\0")
        d.update((ROOT / rel).read_bytes())
    return d.hexdigest()


def matched_state_hash(sim: Simulation) -> str:
    """Include arrays, scalar state, ownership and RNG, without serializing runs."""
    d = hashlib.sha256()
    for field in dataclasses.fields(sim.state):
        val = getattr(sim.state, field.name)
        d.update(field.name.encode() + b"\0")
        if isinstance(val, np.ndarray):
            d.update(str(val.dtype).encode() + b";")
            d.update(str(val.shape).encode() + b";")
            d.update(val.tobytes())
        elif isinstance(val, tuple):
            d.update(canonical([x.tolist() if isinstance(x, np.ndarray) else x for x in val]))
        else:
            d.update(canonical(val))
    d.update(canonical(sim.rng.bit_generator.state))
    return d.hexdigest()


def make_configs(population: int, steps: int) -> list[Scenario]:
    if population <= 0 or steps <= 0:
        raise ValueError("population and steps must be positive")
    base = Scenario.from_file(ROOT / "scenarios/credit_research_base.json")
    # 10,000-agent research uses 5m/6m resource endowment; this is fixed
    # BETWEEN firm densities rather than multiplied by the firm count.
    base = replace(base, population=population, steps=steps,
                   initial_resource=5_000_000, resource_capacity=6_000_000)
    cells: list[Scenario] = []
    for density in (10, 20):
        for savings_percent in (25, 75):
            for label, lending, term in (("control", False, 4),
                                         ("term2", True, 2),
                                         ("term6", True, 6)):
                # Total firms (3*density), initial CASH, and physical CAPITAL
                # are fixed across densities (20*20,000 and 20*20 per sector).
                cfg = replace(
                    base,
                    name=f"density{density}_savings{savings_percent}_{label}",
                    firms_per_sector=density,
                    initial_firm_cash_cents=20_000 * 20 // density,
                    initial_capital_units_per_firm=20 * 20 // density,
                    household_savings_rate=savings_percent / 100,
                    credit_enabled=lending,
                    credit_term_periods=term,
                    resource_extraction_fee_cents_per_unit=0,
                )
                cfg.validate()
                cells.append(cfg)
    return cells


def _atomic_json(path: Path, record: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n"
    # Write to the SAME filesystem and atomically rename after full fsync.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=".seed-", suffix=".tmp", delete=False) as tmp:
        tempname = tmp.name
        tmp.write(payload)
        tmp.flush()
        os.fsync(tmp.fileno())
    os.replace(tempname, path)


def run_seed(output: Path, seed: int, *, population: int=10_000,
             steps: int=24) -> dict:
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    configs = make_configs(population, steps)
    source = source_digest()
    expected_cells = {cfg.name: cfg for cfg in configs}
    path = output / f"seed_{seed:04d}.json"
    if path.exists():
        return verify_seed(path, expected_cells, seed, source)
    rows=[]
    fingerprints={}
    for config in configs:
        sim = Simulation(replace(config,seed=seed))
        fingerprint = matched_state_hash(sim)
        fingerprints[config.name] = fingerprint
        observations=[]
        for period in sim.run(steps):
            m=period.metrics
            if any(m[check] != 0 for check in CHECKS):
                raise AssertionError(f"accounting discrepancy {config.name}, step {m['step']}")
            observations.append({k:m[k] for k in ("step", *CHECKS, *MEASURES)})
        sim.state.validate()
        rows.append({
            "name":config.name,
            "config_sha256":digest(replace(config,seed=seed).to_dict()),
            "initial_state_sha256":fingerprint,
            "periods":observations,
            "total_originations_cents":sum(m["loan_origination_cents"] for m in observations),
            "total_repayments_cents":sum(m["loan_repayment_cents"] for m in observations),
            "total_defaults_cents":sum(m["loan_defaults_cents"] for m in observations),
        })
    for density in (10,20):
        for savings_percent in (25,75):
            group={name:hash for name,hash in fingerprints.items()
                   if name.startswith(f"density{density}_savings{savings_percent}_")}
            if len(set(group.values()))!=1 or len(group)!=3:
                raise AssertionError(f"initial-state mismatch among credit treatments: {group}")
    payload={"schema_version":1,"seed":seed,"population":population,
             "steps":steps,"source_sha256":source,"cells":rows}
    record={**payload,"data_sha256":digest(payload)}
    _atomic_json(path,record)
    return verify_seed(path,expected_cells,seed,source)


def verify_seed(path: Path, configs: dict[str, Scenario], seed: int,
                expected_source: str) -> dict:
    record=json.loads(path.read_text(encoding="utf-8"))
    checksum=record.pop("data_sha256",None)
    if checksum != digest(record):
        raise ValueError(f"tampered or corrupt seed shard: {path}")
    if (record.get("schema_version") != 1 or record.get("seed") != seed or
            record.get("source_sha256") != expected_source or
            record.get("population") != next(iter(configs.values())).population or
            record.get("steps") != next(iter(configs.values())).steps or
            len(record.get("cells",[])) != len(configs)):
        raise ValueError("inconsistent experiment configuration or source digest")
    seen=set()
    for cell in record["cells"]:
        name=cell["name"]
        if name not in configs or name in seen:
            raise ValueError("unexpected or duplicate experiment cell")
        seen.add(name)
        expected=digest(replace(configs[name],seed=seed).to_dict())
        if cell.get("config_sha256")!=expected:
            raise ValueError("scenario configuration digest mismatch")
        periods=cell.get("periods",[])
        if (len(periods)!=configs[name].steps or
                [m.get("step") for m in periods]!=list(range(1,len(periods)+1))):
            raise ValueError("missing, duplicated or misordered observation periods")
        if any(m.get(k) != 0 for m in periods for k in CHECKS):
            raise ValueError("accounting invariant violated in saved shard")
        if any(sum(p[metric] for p in periods)!=cell[f"total_{label}_cents"]
               for metric,label in (("loan_origination_cents","originations"),
                                    ("loan_repayment_cents","repayments"),
                                    ("loan_defaults_cents","defaults"))):
            raise ValueError("loan movement totals do not reconcile")
    for density in (10,20):
        for saving in (25,75):
            matches=[c["initial_state_sha256"] for c in record["cells"]
                     if c["name"].startswith(f"density{density}_savings{saving}_")]
            if len(matches)!=3 or len(set(matches))!=1:
                raise ValueError("initial state no longer matched")
    record["data_sha256"]=checksum
    return record


def _summarize(values: list[float]) -> dict:
    return {"mean":mean(values) if values else None,
            "sample_sd":stdev(values) if len(values)>1 else None,"n":len(values)}


def finalize(output: Path, seeds: list[int], *, population:int=10_000,
             steps:int=24) -> dict:
    if not seeds or len(seeds)!=len(set(seeds)) or any(s<0 for s in seeds):
        raise ValueError("seeds must be unique nonnegative integers")
    configs={cfg.name:cfg for cfg in make_configs(population,steps)}
    source=source_digest()
    records=[]
    for seed in seeds:
        path=output / f"seed_{seed:04d}.json"
        if not path.exists():
            raise FileNotFoundError(f"missing completed seed shard: {path}")
        records.append(verify_seed(path,configs,seed,source))
    cells={name:[] for name in configs}
    for record in records:
        for cell in record["cells"]:
            cells[cell["name"]].append(cell)
    groups={}
    contrasts={}
    for name,observations in cells.items():
        groups[name]={
            "final_period":{k:_summarize([float(c["periods"][-1][k]) for c in observations
                                             if c["periods"][-1][k] is not None])
                            for k in ("production_units","employment_rate",
                                      "disposable_income_gini","capital_stock_units")},
            "total_originations_cents":sum(c["total_originations_cents"] for c in observations),
            "total_repayments_cents":sum(c["total_repayments_cents"] for c in observations),
            "total_defaults_cents":sum(c["total_defaults_cents"] for c in observations),
        }
    for density in (10,20):
        for savings in (25,75):
            base=f"density{density}_savings{savings}_"
            control=cells[base+"control"]
            for maturity in (2,6):
                treated=cells[base+f"term{maturity}"]
                effects={}
                for metric in ("production_units","employment_rate","disposable_income_gini"):
                    d=[t["periods"][-1][metric]-c["periods"][-1][metric]
                       for t,c in zip(treated,control)
                       if t["periods"][-1][metric] is not None and c["periods"][-1][metric] is not None]
                    stats=_summarize(d)
                    sd=stats["sample_sd"]
                    x=stats["mean"]
                    stats["approx_mc_95_interval"]=(
                        [x-1.96*sd/math.sqrt(len(d)),x+1.96*sd/math.sqrt(len(d))]
                        if sd is not None else None)
                    effects[metric]=stats
                contrasts[base+f"term{maturity}_minus_control"]=effects
    result={"design":{"seeds":seeds,"population":population,"steps":steps,
                      "runs":len(seeds)*len(configs),"audited_periods":len(seeds)*len(configs)*steps,
                      "source_sha256":source,"scenario_count":len(configs),
                      "initial_total_firm_cash_cents":3*20*20_000,
                      "initial_total_capital_units":3*20*20,
                      "environment":{"python":sys.version.split()[0],
                                     "numpy":np.__version__,"platform":platform.platform()},
                      "limitations":"Within-model matched random seeds; firm counts, ownership and market structure differ across densities."},
            "scenario_summary":groups,"paired_credit_effects":contrasts,
            "seed_sha256":{str(r["seed"]):r["data_sha256"] for r in records}}
    _atomic_json(output/"summary.json",result)
    return result


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    g=parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--seed",type=int,help="execute or verify one complete matched seed")
    g.add_argument("--finalize",action="store_true",help="verify complete shards and aggregate")
    parser.add_argument("--population",type=int,default=10_000)
    parser.add_argument("--steps",type=int,default=24)
    parser.add_argument("--seeds",default="1,2,3,4,5,6,7,8",help="comma-separated expected seed IDs for finalize")
    parser.add_argument("--output",type=Path,default=Path("results/credit_sensitivity"))
    args=parser.parse_args()
    if args.finalize:
        expected=[int(x) for x in args.seeds.split(",")]
        result=finalize(args.output,expected,population=args.population,steps=args.steps)
        print(json.dumps(result["design"],indent=2))
    else:
        record=run_seed(args.output,args.seed,population=args.population,steps=args.steps)
        print(json.dumps({"seed":record["seed"],"cells":len(record["cells"]),
                          "digest":record["data_sha256"]},indent=2))


if __name__=="__main__":
    main()
