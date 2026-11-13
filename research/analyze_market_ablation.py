"""Re-analyze committed per-period market-ablation CSV records.

Uses matched *master seed IDs* for comparisons. Isolated markets contain
independent agent streams; intervals are Monte Carlo sampling estimates only.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import math
import statistics

RULES = ["reference", "cheapest_only", "favorite_first", "stationary_hiring",
         "fixed_prices", "household_id_ration"]
MEASURES = ["production_per_person", "consumption_per_person", "employment_rate",
            "active_seller_fraction", "quoted_price_spread_mean_cents",
            "unmet_stock_per_person", "unmet_budget_per_person"]


def estimate(values):
    n=len(values)
    mean=statistics.mean(values)
    sd=statistics.stdev(values) if n>1 else None
    width=1.96*sd/math.sqrt(n) if sd is not None else None
    return {"n":n,"mean":mean,"sample_sd":sd,
            "approx_95pct_mc_interval":[mean-width,mean+width] if width is not None else None}


def read_results(directory, seeds, steps):
    records={}
    for rule in RULES:
        path=directory/rule/f"{rule}_periods.csv"
        cases={}
        with path.open(newline="", encoding="utf8") as f:
            rows=list(csv.DictReader(f))
        if len(rows)!=seeds*steps*2:
            raise ValueError(f"{path}: expected {seeds*steps*2} rows, found {len(rows)}")
        for row in rows:
            key=(int(row["seed"]), int(row["period"]),row["topology"])
            if key in cases: raise ValueError(f"duplicate row {key}")
            cases[key]={k:(float(row[k]) if row[k] else None) for k in MEASURES}
        expected={(seed,step,top) for seed in range(1,seeds+1)
                  for step in range(1,steps+1)
                  for top in ("integrated","ten_isolated")}
        if set(cases)!=expected:raise ValueError(f"incomplete cells in {path}")
        records[rule]=cases
    return records


def analyze(directory, seeds, steps):
    rows=read_results(directory,seeds,steps)
    results={}
    baseline=rows["reference"]
    for rule,values in rows.items():
        item={}
        for metric in MEASURES:
            integrated=[values[(s,steps,"integrated")][metric] for s in range(1,seeds+1)]
            partition=[values[(s,steps,"ten_isolated")][metric] for s in range(1,seeds+1)]
            if any(v is None for v in integrated+partition):
                item[metric]=None
                continue
            gap=[x-y for x,y in zip(integrated, partition)]
            base_int=[baseline[(s,steps,"integrated")][metric] for s in range(1,seeds+1)]
            base_isolated=[baseline[(s,steps,"ten_isolated")][metric] for s in range(1,seeds+1)]
            base_gap=[x-y for x,y in zip(base_int,base_isolated)]
            item[metric]={"integrated": estimate(integrated),
                          "isolated":estimate(partition),
                          "integrated_minus_isolated":estimate(gap),
                          "change_in_integrated_vs_reference": estimate([a-b for a,b in zip(integrated,base_int)]),
                          "change_in_isolated_vs_reference":estimate([a-b for a,b in zip(partition,base_isolated)]),
                          "change_in_market_gap_vs_reference":estimate([a-b for a,b in zip(gap,base_gap)])}
        results[rule]=item
    return results


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path("research/v02_market_ablation_12"))
    p.add_argument("--seeds",type=int,default=12)
    p.add_argument("--steps",type=int,default=24)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    result=analyze(a.input,a.seeds,a.steps)
    destination=a.output or (a.input/"combined_analysis.json")
    destination.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("Measured market-size production gaps, difference from baseline, MC intervals:")
    for name in RULES:
        prod=result[name]["production_per_person"]
        delta=prod["change_in_market_gap_vs_reference"]
        print(f"{name:<22} gap {prod['integrated_minus_isolated']['mean']:+.5f}  delta {delta['mean']:+.5f}  CI {delta['approx_95pct_mc_interval']}")

if __name__=="__main__":main()
