"""Paired opt-in credit × resource-fee experiment, entirely locally executable.

Each 2×2 treatment retains the same seeded synthetic initial economy. Outputs
are observations from this specified model, not policy evidence about reality.
"""
from __future__ import annotations
import argparse
from dataclasses import replace
import csv
import hashlib
import json
from pathlib import Path
from statistics import mean, stdev
import time

from civitas.engine import Simulation
from civitas.model import Scenario
from civitas.persistence import canonical_json

OBSERVE = (
    "step", "population", "production_units", "consumption_units", "employed",
    "employment_rate", "disposable_income_gini", "modeled_net_worth_gini",
    "capital_stock_units", "capital_added_units", "resource_extracted",
    "resource_stock", "government_resource_fee_cents",
    "firm_resource_input_fees_cents", "firm_book_equity_discrepancy_cents",
    "loan_origination_cents", "loan_repayment_cents", "loan_defaults_cents",
    "household_savings_stock_cents", "household_loan_assets_cents",
    "firm_loan_liabilities_cents", "loan_discrepancy_cents",
    "money_discrepancy_cents", "resource_discrepancy_units",
    "goods_discrepancy_units", "capital_discrepancy_units",
    "household_cashflow_discrepancy_cents", "firm_cashflow_discrepancy_cents",
)
CHECKS = (
    "money_discrepancy_cents", "resource_discrepancy_units",
    "goods_discrepancy_units", "capital_discrepancy_units",
    "household_cashflow_discrepancy_cents", "firm_cashflow_discrepancy_cents",
    "firm_book_equity_discrepancy_cents", "loan_discrepancy_cents",
)
COMPARE = ("production_units", "consumption_units", "employment_rate",
           "disposable_income_gini", "capital_stock_units", "loan_defaults_cents")


def variants(base: Scenario) -> list[Scenario]:
    return [replace(base, name=f"credit_{int(lending)}_resourcefee_{fee}",
                    credit_enabled=lending, resource_extraction_fee_cents_per_unit=fee)
            for fee in (0, 20) for lending in (False, True)]


def analyze(rows: list[dict], seeds: list[int], config: list[Scenario]) -> dict:
    last = {(r["scenario"], r["seed"]):r for r in rows if r["step"] == config[0].steps}
    summary = {}
    for scenario in config:
        name = scenario.name
        samples = [last[(name, seed)] for seed in seeds]
        summary[name] = {
            k: {"mean": mean(v), "sample_sd": stdev(v) if len(v)>1 else None,
                "n":len(v)} if v else {"mean":None,"sample_sd":None,"n":0}
            for k in COMPARE
            for v in [[float(r[k]) for r in samples if r[k] is not None]]
        }
        summary[name]["total_originations_cents"] = sum(r["loan_origination_cents"] for r in rows if r["scenario"]==name)
        summary[name]["total_repayments_cents"] = sum(r["loan_repayment_cents"] for r in rows if r["scenario"]==name)
        summary[name]["total_defaults_cents"] = sum(r["loan_defaults_cents"] for r in rows if r["scenario"]==name)
    contrasts = {}
    for fee in (0,20):
        treated = f"credit_1_resourcefee_{fee}"
        control = f"credit_0_resourcefee_{fee}"
        contrasts[str(fee)] = {}
        for metric in COMPARE:
            d = [last[(treated,seed)][metric] - last[(control,seed)][metric]
                 for seed in seeds if last[(treated,seed)][metric] is not None
                 and last[(control,seed)][metric] is not None]
            avg = mean(d) if d else None
            sd = stdev(d) if len(d)>1 else None
            margin = 1.96 * sd / len(d)**.5 if sd is not None else None
            contrasts[str(fee)][metric] = {"paired_mean":avg,
                                            "sample_sd":sd,
                                            "mc_95_interval":([avg-margin,avg+margin]
                                                              if margin is not None else None),
                                            "n":len(d)}
    return {"scenario_summary":summary, "paired_credit_minus_no_credit":contrasts}


def run(output: Path, *, population: int=1000, seeds: int=12, steps: int=24,
        normalized_firm_density: bool=False) -> dict:
    if population < 0 or seeds < 1 or steps < 1:
        raise ValueError("population must be nonnegative; seeds and steps positive")
    base = Scenario.from_file(Path(__file__).resolve().parents[1]/"scenarios/credit_research_base.json")
    base = replace(base,population=population,steps=steps)
    if normalized_firm_density:
        if population < 1000 or population % 1000:
            raise ValueError("normalized study requires population in multiples of 1000")
        factor = population // 1000
        base = replace(base, firms_per_sector=2*factor,
                       initial_resource=base.initial_resource*factor,
                       resource_capacity=base.resource_capacity*factor)
    configs = variants(base)
    for cfg in configs:cfg.validate()
    output.mkdir(parents=True,exist_ok=True)
    rows = []
    seed_ids = list(range(1,seeds+1))
    t0 = time.perf_counter()
    for seed in seed_ids:
        for scenario in configs:
            cfg=replace(scenario,seed=seed)
            sim=Simulation(cfg)
            for period in sim.run(steps):
                metric=period.metrics
                if any(metric[k]!=0 for k in CHECKS):
                    raise AssertionError("economy conservation or account flow failed")
                rows.append({"scenario":cfg.name,"seed":seed,
                             **{k:metric[k] for k in OBSERVE}})
            sim.state.validate()
    duration=time.perf_counter()-t0
    with (output/"periods.csv").open("w",encoding="utf8",newline="") as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    digest=hashlib.sha256((output/"periods.csv").read_bytes()).hexdigest()
    stats=analyze(rows,seed_ids,configs)
    result = {
        "design":{"population":population,"seeds":seeds,"steps":steps,
                  "firm_density_normalized": normalized_firm_density,
                  "firms_per_sector": base.firms_per_sector,
                  "runs":seeds*len(configs),"audited_periods":len(rows),
                  "periods_sha256":digest,"elapsed_wall_seconds":duration,
                  "model_status":"uncalibrated, exploratory synthetic economy"},
        "configurations": {x.name:x.to_dict() for x in configs},
        **stats,
    }
    (output/"summary.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--population",type=int,default=1000)
    p.add_argument("--seeds",type=int,default=12)
    p.add_argument("--steps",type=int,default=24)
    p.add_argument("--output",type=Path,default=Path("results/credit_factorial"))
    p.add_argument("--normalized-firm-density", action="store_true")
    a=p.parse_args()
    result=run(a.output,population=a.population,seeds=a.seeds,steps=a.steps,
               normalized_firm_density=a.normalized_firm_density)
    print(json.dumps(result["design"],indent=2))

if __name__ == "__main__":main()
