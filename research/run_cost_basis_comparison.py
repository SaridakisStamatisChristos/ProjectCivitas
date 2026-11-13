"""Opt-in historical-cost accounting comparison; synthetic methods audit.

Compare legacy profit-proxy dividends to cost-basis earnings dividends with
same initial economic state and random streams, recording all period results.
This changes the dividend rule, so contrasts are rule sensitivity, not the
pure effect of a reporting method.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
import csv
import hashlib
import json
from pathlib import Path
import platform
import statistics
import math
import time

from civitas.engine import Simulation
from civitas.model import Scenario
from civitas.persistence import config_digest, canonical_json

ROOT=Path(__file__).resolve().parents[1]
AUDITS=("money_discrepancy_cents","resource_discrepancy_units",
        "goods_discrepancy_units","capital_discrepancy_units",
        "household_cashflow_discrepancy_cents","firm_cashflow_discrepancy_cents")
METRICS=("production_units","consumption_units","employment_rate",
         "disposable_income_gini","firm_profit_proxy_cents",
         "firm_cost_basis_earnings_cents","firm_book_equity_discrepancy_cents",
         "firm_consumer_cogs_cents","firm_capital_goods_cogs_cents",
         "firm_capital_historical_cost_cents","firm_inventory_historical_cost_cents",
         "dividends_cents","capital_stock_units","firm_cashflow_discrepancy_cents")
FIELDS=["seed","arm","step",*METRICS]


def config(seed:int,population:int):
    if type(seed) is not int or seed<0 or type(population) is not int or population<1:
        raise ValueError("seed nonnegative and population positive integer required")
    c=Scenario.from_file(ROOT/'scenarios/capital_reinvestment.json')
    return replace(c,name="cost_basis_matched_comparison",seed=seed,
                   population=population,cost_basis_accounting_enabled=False)


def estimate(vals:list[float]):
    mean=statistics.mean(vals)
    sd=statistics.stdev(vals) if len(vals)>1 else None
    half=1.96*sd/math.sqrt(len(vals)) if sd is not None else None
    return {"mean":mean,"sample_sd":sd,"n":len(vals),
            "approximate_95pct_seed_interval":[mean-half,mean+half] if half is not None else None}


def run(output:Path, seeds:int=8,steps:int=24,population:int=10_000):
    if type(seeds) is not int or seeds<2 or type(steps) is not int or steps<1:
        raise ValueError("need at least two seeds and a positive number of periods")
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    records=[]; metadata=[];final={};start=time.perf_counter()
    for seed in range(1,seeds+1):
        base=config(seed,population)
        initial=Simulation(base)
        common_rng=deepcopy(initial.rng.bit_generator.state)
        last_rng=None
        for mode in (False,True):
            arm="cost_basis" if mode else "legacy_proxy"
            conf=replace(base,cost_basis_accounting_enabled=mode)
            sim=Simulation(conf)
            # Deep-copy a common economic state; cost basis bookkeeping is
            # the sole initial-state difference (already zero inventory).
            if not mode:
                default_initial_cash=sim.state.firm_cash.copy()
                default_owner=sim.state.firm_owner_households
                initial_capital=sim.state.firm_capital.copy()
            else:
                assert (default_initial_cash==sim.state.firm_cash).all()
                assert (initial_capital==sim.state.firm_capital).all()
                assert all((a==b).all() for a,b in zip(default_owner,sim.state.firm_owner_households))
            assert sim.rng.bit_generator.state == common_rng
            for period in sim.run(steps):
                m=period.metrics
                if any(m[key] !=0 for key in AUDITS):
                    raise AssertionError("model physical or money accounting failure")
                if mode and m["firm_book_equity_discrepancy_cents"]!=0:
                    raise AssertionError("cost-basis equity reconciliation failure")
                record={"seed":seed,"arm":arm,"step":m["step"]}
                for key in METRICS:record[key]=m[key]
                records.append(record)
                if m["step"]==steps:final[(seed,arm)]=m
            rng_digest=hashlib.sha256(canonical_json(sim.rng.bit_generator.state).encode()).hexdigest()
            if last_rng is not None and last_rng!=rng_digest:
                raise AssertionError("accounting arm changed RNG stream")
            last_rng=rng_digest
        metadata.append({"seed":seed,"common_rng_sha256":last_rng,
                         "config_digest_legacy":config_digest(base),
                         "notes":"Identical initial agents/firms/cash/capital; only cost-basis ledger initialized using posted price."})
    path=output/'periods.csv'
    with path.open("w",newline="",encoding="utf8") as fp:
        wr=csv.DictWriter(fp,fieldnames=FIELDS);wr.writeheader();wr.writerows(records)
    compare={"design":{"population":population,"seeds":seeds,"periods":steps,
                       "executed_runs":2*seeds,"verified_periods":len(records),
                       "python":platform.python_version(),"platform":platform.platform(),
                       "elapsed_seconds":time.perf_counter()-start,
                       "record_sha256":hashlib.sha256(path.read_bytes()).hexdigest()},
             "final_means":{},"paired_cost_basis_minus_legacy":{},"metadata":metadata,
             "limitations":["Cost-basis mode changes the dividend base as well as financial reporting, hence paired differences are conditional model responses.",
                            "Inventory manufacturing costs include paid direct labor only; no material/energy cost allocation, overhead, financing, taxes or IFRS/GAAP assertion.",
                            "Initial capital book value uses an explicitly imputed input-sector price, not historical purchase evidence.",
                            "Seed intervals measure Monte Carlo variability, not model uncertainty or real-world policy effects."]}
    for arm in ('legacy_proxy','cost_basis'):
        compare['final_means'][arm]={key:estimate([float(final[(seed,arm)][key]) for seed in range(1,seeds+1)])
                                     for key in ('production_units','consumption_units','dividends_cents','capital_stock_units','firm_profit_proxy_cents')}
    for key in ('production_units','consumption_units','dividends_cents','capital_stock_units'):
        diffs=[float(final[(seed,'cost_basis')][key])-float(final[(seed,'legacy_proxy')][key]) for seed in range(1,seeds+1)]
        compare['paired_cost_basis_minus_legacy'][key]=estimate(diffs)
    (output/'summary.json').write_text(json.dumps(compare,indent=2,allow_nan=False)+'\n')
    return compare


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',default='results/cost_basis_compare')
    p.add_argument('--seeds',type=int,default=8)
    p.add_argument('--steps',type=int,default=24)
    p.add_argument('--population',type=int,default=10_000)
    args=p.parse_args()
    x=run(Path(args.output),seeds=args.seeds,steps=args.steps,population=args.population)
    print(json.dumps(x['design'],indent=2))

if __name__=='__main__':main()
