"""Compare one integrated large market with ten noninteracting small markets.

Both configurations have exactly matched *total* starting endowments and
firm density. This probes market-structure sensitivity, not causal realism.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
import platform
import statistics
import time
import numpy as np
from civitas import __version__
from civitas.engine import Simulation
from civitas.normalization import audit_initial_endowments
from run_population_normalized import make_scenario, summarize, paired_contrast

METRICS=("production_per_person","consumption_per_person","employment_rate")

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--seeds",type=int,default=30)
    p.add_argument("--steps",type=int,default=24)
    p.add_argument("--integrated-root",type=Path,default=Path("results/normalized_10000_30"))
    p.add_argument("--output",type=Path,default=Path("results/market_partition_control"))
    args=p.parse_args(argv)
    if args.seeds<2 or args.steps<1:
        p.error("require seeds>=2 and steps>=1")
    args.output.mkdir(parents=True,exist_ok=True)
    report={}
    all_records=[]
    t0=time.perf_counter()
    for saving in (0,30):
        key=f"o08_s{saving:02d}"
        integrated={}
        with (args.integrated_root/f"{key}_periods.csv").open(newline="") as f:
            for row in csv.DictReader(f):
                if int(row["period"])==args.steps and int(row["seed"])<=args.seeds:
                    integrated[int(row["seed"])]= {k:float(row[k]) for k in METRICS}
        if sorted(integrated)!=list(range(1,args.seeds+1)):
            raise ValueError("incomplete integrated dataset or step mismatch")
        partitioned={}
        for seed in range(1,args.seeds+1):
            # Explicit distinct independent substreams, not overlapping draws.
            per_period=[{"production":0,"consumption":0,"employed":0,"labor_force":0}
                        for _ in range(args.steps)]
            for community in range(10):
                internal_seed=int(np.random.SeedSequence([seed,community,38491]).generate_state(1)[0])
                scenario=make_scenario(8,saving,1000,internal_seed)
                for step,period in enumerate(Simulation(scenario).run(args.steps)):
                    m=period.metrics
                    per_period[step]["production"]+=m["production_units"]
                    per_period[step]["consumption"]+=m["consumption_units"]
                    per_period[step]["employed"]+=m["employed"]
                    per_period[step]["labor_force"]+=m["labor_force"]
                    for k in ("money_discrepancy_cents","goods_discrepancy_units","capital_discrepancy_units", "resource_discrepancy_units", "household_cashflow_discrepancy_cents", "firm_cashflow_discrepancy_cents"):
                        if m[k]!=0: raise AssertionError((seed,community,step,k))
            for step,period in enumerate(per_period,1):
                all_records.append({"saving_rate":saving,"seed":seed,"period":step,
                                    "production_per_person":period["production"]/10000,
                                    "consumption_per_person":period["consumption"]/10000,
                                    "employment_rate":period["employed"]/period["labor_force"] if period["labor_force"] else None})
            partitioned[seed]={k:all_records[-1][k] for k in METRICS}
        report[key]={"integrated":{k:summarize([integrated[i][k] for i in range(1,args.seeds+1)]) for k in METRICS},
                     "ten_disconnected_markets":{k:summarize([partitioned[i][k] for i in range(1,args.seeds+1)]) for k in METRICS},
                     "partition_minus_integrated":{k:paired_contrast([integrated[i][k] for i in range(1,args.seeds+1)],[partitioned[i][k] for i in range(1,args.seeds+1)]) for k in METRICS}}
        print(f"{key}: completed {args.seeds} integrated + {args.seeds}×10 isolated, elapsed={time.perf_counter()-t0:.1f}s",flush=True)
    with (args.output/"periods.csv").open("w",newline="",encoding="utf8") as f:
        writer=csv.DictWriter(f,fieldnames=list(all_records[0]))
        writer.writeheader();writer.writerows(all_records)
    meta={"software_version":__version__,"python":platform.python_version(),"numpy":np.__version__,
          "platform":platform.platform(),"seeds":args.seeds,"steps":args.steps,
          "integrated_population":10000,"partition_count":10,"partition_population":1000,
          "independent_replicas":10*args.seeds*2,
          "source_integrated_directory":str(args.integrated_root),
          "exact_stock_normalization_verified": True,
          "remark":"Ownership share 8% matches at both scales; model not externally calibrated", 
          "elapsed_seconds":time.perf_counter()-t0}
    (args.output/"summary.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf8")
    (args.output/"metadata.json").write_text(json.dumps(meta,indent=2,allow_nan=False)+"\n",encoding="utf8")

if __name__=="__main__": main()
