"""Independent stored-data recount for the 2×3 price/hiring experiment.

Does not call the experiment runner's verification, aggregation, or estimator
functions. Recomputes all saved summaries from the checked, immutable records.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics

from research.run_price_hiring_stability import configs, METRICS, PRICE_RULES, HIRING_RULES, SOURCES

ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    "money_discrepancy_cents", "resource_discrepancy_units", "goods_discrepancy_units",
    "capital_discrepancy_units", "household_cashflow_discrepancy_cents",
    "firm_cashflow_discrepancy_cents", "firm_book_equity_discrepancy_cents",
    "loan_discrepancy_cents",
)


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, ensure_ascii=False).encode("utf8")


def audit(folder: Path) -> dict:
    summary = json.loads((folder / "summary.json").read_text(encoding="utf8"))
    design = summary["design"]
    population, steps, seeds = design["population"], design["steps"], design["seeds"]
    arms = configs(population, steps)
    names = [c.name for c in arms]
    if names != design["arms"] or len(seeds) != len(set(seeds)):
        raise ValueError("experiment design mismatch")
    if design["runs"] != len(seeds)*len(names) or design["audited_periods"] != len(seeds)*len(names)*steps:
        raise ValueError("inconsistent experiment record counts")
    source = hashlib.sha256()
    for filename in SOURCES:
        source.update(filename.encode()+b"\0"+(ROOT/filename).read_bytes())
    if summary["source_sha256"] != source.hexdigest():
        raise ValueError("summary source mismatch")
    trajectories = {}
    for seed in seeds:
        init_hashes, rng_hashes = set(), set()
        for cfg in arms:
            path = folder/f"seed_{seed:04d}"/f"{cfg.name}.json.gz"
            with gzip.open(path,"rb") as f:
                record = json.loads(f.read())
            expected_digest = record.pop("sha256", None)
            if expected_digest != hashlib.sha256(canonical(record)).hexdigest():
                raise ValueError("raw shard checksum mismatch")
            if record["config_sha256"] != hashlib.sha256(canonical(
                {**cfg.to_dict(),"seed":seed})).hexdigest():
                raise ValueError("scenario mismatch")
            if record["source_sha256"] != source.hexdigest():
                raise ValueError("shard source mismatch")
            init_hashes.add(record["initial_state_sha256"])
            rng_hashes.add(record["end_rng_sha256"])
            rows = record["periods"]
            if len(rows) != steps or [x["step"] for x in rows] != list(range(1,steps+1)):
                raise ValueError("missing or duplicated period")
            for row in rows:
                if any(row.get(key) != 0 for key in CHECKS):
                    raise ValueError("accounting identity mismatch")
                if (row["household_monetary_assets_cents"]+row["firm_cash_stock_cents"]+
                        row["government_cash_stock_cents"] != record["initial_total_money_cents"]):
                    raise ValueError("monetary partition mismatch")
            trajectories[(seed,cfg.name)] = rows
        if len(init_hashes) != 1 or len(rng_hashes) != 1:
            raise ValueError("unmatched initial state or RNG")

    def vals(arm,t,metric):
        return [trajectories[(seed,arm)][t-1][metric] for seed in seeds]

    def check(value, values):
        n=len(values)
        avg=statistics.mean(values)
        sd=statistics.stdev(values) if n>1 else None
        expected={"mean":avg,"sample_sd":sd,"n":n,
                  "mc_95_lower":avg-1.96*sd/math.sqrt(n) if sd is not None else None,
                  "mc_95_upper":avg+1.96*sd/math.sqrt(n) if sd is not None else None}
        if value.keys() != expected.keys():
            raise ValueError("statistical columns mismatch")
        for key,a in expected.items():
            b=value[key]
            if a is None:
                if b is not None:raise ValueError("saved statistical mean mismatch")
            elif not isinstance(b,(int,float)) or not math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-11):
                raise ValueError("saved statistical mean mismatch")

    horizon = sorted(set((24,48,steps)))
    expected_means=set()
    expected_paired=set()
    for arm in names:
        for t in horizon:
            key=f"{arm}_t{t}";expected_means.add(key)
            for metric in METRICS:
                check(summary["means"][key][metric], vals(arm,t,metric))
            if arm != "inventory__adaptive":
                key=f"{arm}_vs_control_t{t}_production";expected_paired.add(key)
                check(summary["paired"][key], [x-y for x,y in zip(
                    vals(arm,t,"production_units"),vals("inventory__adaptive",t,"production_units"))])
    for hiring in HIRING_RULES:
        for t in horizon:
            key=f"guard_effect__{hiring}_t{t}";expected_paired.add(key)
            check(summary["paired"][key], [x-y for x,y in zip(
                vals(f"affordability_guard__{hiring}",t,"production_units"),
                vals(f"inventory__{hiring}",t,"production_units"))])
    for hiring in ("blended","stationary"):
        for t in horizon:
            key=f"price_hiring_interaction__{hiring}_t{t}";expected_paired.add(key)
            check(summary["paired"][key],[
                (trajectories[(seed,f"affordability_guard__{hiring}")][t-1]["production_units"]-
                 trajectories[(seed,f"inventory__{hiring}")][t-1]["production_units"])-
                (trajectories[(seed,"affordability_guard__adaptive")][t-1]["production_units"]-
                 trajectories[(seed,"inventory__adaptive")][t-1]["production_units"])
                for seed in seeds])
    if set(summary["means"])!=expected_means or set(summary["paired"])!=expected_paired:
        raise ValueError("missing or unexpected summary keys")
    return {"status":"verified", "runs":len(trajectories),
            "audited_periods":len(trajectories)*steps,
            "checked_means":len(expected_means)*len(METRICS),
            "checked_paired_estimates":len(expected_paired),
            "source_sha256":source.hexdigest()}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder",type=Path)
    print(json.dumps(audit(p.parse_args().folder),indent=2))
