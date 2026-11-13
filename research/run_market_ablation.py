"""Mechanism-by-mechanism falsification of integrated-vs-partitioned markets.

Independent isolated community draws are *not* paired at agent level with a
single integrated simulation; comparisons across topology are descriptive.
Within a given topology, seeds and unchanged initial populations are paired.
"""
from __future__ import annotations
import argparse
import csv
from dataclasses import replace
import json
import platform
import statistics
import sys
import time
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_population_normalized import make_scenario, summarize, paired_contrast
from civitas import __version__
from civitas.engine import Simulation
from civitas.normalization import audit_initial_endowments
from civitas.persistence import config_digest

RULES = {
    "reference": {},
    "cheapest_only": {"buyer_seller_rule": "cheapest"},
    "favorite_first": {"buyer_seller_rule": "favorite"},
    "stationary_hiring": {"hiring_expectation_rule": "stationary"},
    "fixed_prices": {"price_adjustment": 0},
    "household_id_ration": {"rationing_order_rule": "household_id"},
}
IDENTITIES = ("money_discrepancy_cents", "goods_discrepancy_units",
              "resource_discrepancy_units", "capital_discrepancy_units",
              "household_cashflow_discrepancy_cents", "firm_cashflow_discrepancy_cents")
METRICS = ("production_per_person", "consumption_per_person", "employment_rate",
           "active_seller_fraction", "quoted_price_spread_mean_cents",
           "unmet_stock_per_person", "unmet_budget_per_person")


def measure(m: dict, population: int, firms: int) -> dict:
    return {
        "production_per_person": m["production_units"] / population,
        "consumption_per_person": m["consumption_units"] / population,
        "employment_rate": m["employed"] / m["labor_force"] if m["labor_force"] else None,
        "active_seller_fraction": m["active_sellers"] / firms,
        "quoted_price_spread_mean_cents": m["quoted_price_spread_mean_cents"],
        "unmet_stock_per_person": m["unmet_stock_demand_units"] / population,
        "unmet_budget_per_person": m["unmet_budget_demand_units"] / population,
    }


def verify(m):
    for key in IDENTITIES:
        if m[key] != 0:
            raise AssertionError(f"{key}={m[key]} at step {m['step']}")


def run_integrated(config, steps):
    sim = Simulation(config)
    result = []
    firms = len(sim.state.firm_cash)
    for p in sim.run(steps):
        m = p.metrics
        verify(m)
        result.append(measure(m, config.population, firms))
    return result


def run_partitioned(config, master_seed, steps):
    # Same initial per-person stocks and firm density as integrated economy.
    sums = [{"production_per_person": 0., "consumption_per_person": 0.,
             "employment_rate": 0., "active_seller_fraction": 0.,
             "quoted_price_spread_mean_cents": 0., "unmet_stock_per_person": 0.,
             "unmet_budget_per_person": 0.} for _ in range(steps)]
    employment_num = [0] * steps
    employment_den = [0] * steps
    for community in range(10):
        inner_seed = int(np.random.SeedSequence([master_seed, community, 38491]).generate_state(1)[0])
        local = replace(config, population=1000, firms_per_sector=2,
                        initial_resource=config.initial_resource//10,
                        resource_capacity=config.resource_capacity//10,
                        seed=inner_seed)
        # Explicitly preserve the original reference's firm endowment per firm.
        for step, m in enumerate(Simulation(local).run(steps)):
            r = measure(m.metrics, 1000, len(local.sectors)*local.firms_per_sector)
            for key in METRICS:
                if key != "employment_rate":
                    sums[step][key] += r[key] / 10
            employment_num[step] += m.metrics["employed"]
            employment_den[step] += m.metrics["labor_force"]
            verify(m.metrics)
    for step, item in enumerate(sums):
        item["employment_rate"] = (employment_num[step]/employment_den[step]
                                   if employment_den[step] else None)
    return sums


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=12)
    p.add_argument("--steps", type=int, default=24)
    p.add_argument("--output", type=Path, default=Path("results/market_ablation"))
    p.add_argument("--only", choices=RULES.keys())
    a = p.parse_args()
    if a.seeds < 2 or a.steps < 1:
        p.error("seeds >=2 and steps>=1 required")
    a.output.mkdir(parents=True, exist_ok=True)
    report = {}
    start = time.perf_counter()
    first_config = make_scenario(8, 0, 10000, 1)
    initial_audit = audit_initial_endowments(first_config)
    total_internal_runs = 0
    all_rows = 0
    for label, treatment in RULES.items():
        if a.only and a.only != label:
            continue
        integ, isolated = {}, {}
        c = replace(first_config, name=f"market_ablation_{label}", **treatment)
        (a.output / f"{label}_scenario.json").write_text(
            json.dumps(c.to_dict(), indent=2) + "\n", encoding="utf8")
        dest = a.output / f"{label}_periods.csv"
        fields = ["seed", "period", "topology", *METRICS]
        with dest.open("w", newline="", encoding="utf8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for seed in range(1, a.seeds + 1):
                ci = replace(c, seed=seed)
                large = run_integrated(ci, a.steps)
                parts = run_partitioned(ci, seed, a.steps)
                for topology, periods in (("integrated", large), ("ten_isolated", parts)):
                    for period, metrics in enumerate(periods, 1):
                        writer.writerow({"seed": seed, "period": period,
                                         "topology": topology, **metrics})
                        all_rows += 1
                integ[seed], isolated[seed] = large[-1], parts[-1]
                total_internal_runs += 11
        report[label] = {
            "config_sha256_seed_1": config_digest(c),
            "integrated": {k: summarize([integ[i][k] for i in range(1, a.seeds+1)]) for k in METRICS},
            "isolated": {k: summarize([isolated[i][k] for i in range(1, a.seeds+1)]) for k in METRICS},
            "isolated_minus_integrated": {
                k: paired_contrast([integ[i][k] for i in range(1, a.seeds+1)],
                                   [isolated[i][k] for i in range(1, a.seeds+1)]) for k in METRICS},
        }
        print(f"{label}: {a.seeds} integrated + {a.seeds*10} isolated communities; elapsed {time.perf_counter()-start:.1f}s", flush=True)
    meta = {
        "model_version": __version__, "python": platform.python_version(),
        "numpy": np.__version__, "platform": platform.platform(),
        "seeds_per_treatment": a.seeds, "periods": a.steps,
        "internal_simulations": total_internal_runs, "period_rows": all_rows,
        "initial_firms": len(first_config.sectors)*first_config.firms_per_sector,
        "initial_money_per_person": str(initial_audit.household_money_per_person + initial_audit.firm_money_per_person),
        "resource_stock_per_person": str(initial_audit.initial_resource_per_person),
        "capital_per_person": str(initial_audit.initial_capital_per_person),
        "total_wall_seconds": time.perf_counter()-start,
        "caveat": "Uncalibrated model; isolated communities use independent substreams. Seed-level topology contrasts are NOT agent-level matched counterfactuals. Single-factor ablations preserve initial agent state only within the integrated comparison.",
    }
    (a.output / "summary.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    (a.output / "metadata.json").write_text(json.dumps(meta, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"completed": list(report), "internal_runs": total_internal_runs,
                      "period_rows": all_rows, "seconds": round(time.perf_counter()-start,2)}), flush=True)

if __name__ == "__main__":
    main()
