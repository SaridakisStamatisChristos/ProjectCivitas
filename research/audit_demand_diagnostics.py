"""Independent standard-library auditor for v0.2 demand-contraction experiments.

Checks period completeness and monetary stock identities, identical initialization,
RNG alignment, checksum integrity and independently recomputes every saved mean
and paired contrast. This does not independently prove the engine's equations.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, stdev

ARMS = ("control", "no_saving", "full_dividends", "fixed_prices",
        "stationary_hiring", "no_depreciation")
CHECKS = (
    "money_discrepancy_cents", "resource_discrepancy_units", "goods_discrepancy_units",
    "capital_discrepancy_units", "household_cashflow_discrepancy_cents",
    "firm_cashflow_discrepancy_cents", "firm_book_equity_discrepancy_cents",
    "loan_discrepancy_cents",
)


def digest(record: object) -> str:
    return hashlib.sha256(json.dumps(record,sort_keys=True,separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf8")).hexdigest()


def numerical_check(record: dict, values: list[float]) -> None:
    n=len(values)
    avg=mean(values)
    sd=stdev(values) if n > 1 else None
    half=1.96*sd/math.sqrt(n) if sd is not None else None
    for key,expected in (("n",n),("mean",avg),("sample_sd",sd),
                         ("mc95_low",avg-half if half is not None else None),
                         ("mc95_high",avg+half if half is not None else None)):
        actual=record[key]
        if (expected is None and actual is not None or
            expected is not None and (actual is None or not math.isclose(
                float(actual),float(expected),rel_tol=1e-10,abs_tol=1e-10))):
            raise ValueError(f"incorrect saved statistical {key}: {actual} vs {expected}")


def audit(output: Path) -> dict:
    summary=json.loads((output/"summary.json").read_text(encoding="utf8"))
    design=summary["design"]
    seeds=design["seeds"]
    horizon=design["steps"]
    if (not seeds or len(set(seeds))!=len(seeds) or horizon<48 or design["arms"]!=list(ARMS) or
        design["runs"]!=len(seeds)*len(ARMS) or
        design["audited_periods"]!=len(seeds)*len(ARMS)*horizon):
        raise ValueError("invalid or incomplete research design")
    by_seed={}
    for seed in seeds:
        by_arm={}
        for arm in ARMS:
            path=output/f"seed_{seed:04d}"/f"{arm}.json.gz"
            with gzip.open(path,"rb") as stream:
                record=json.loads(stream.read().decode("utf8"))
            saved=record.pop("sha256",None)
            if saved!=digest(record):
                raise ValueError("corrupt cell hash")
            if (record["schema"]!=1 or record["seed"]!=seed or record["name"]!=arm or
                    record["source_sha256"]!=summary["source_sha256"]):
                raise ValueError("invalid cell metadata/source version")
            periods=record["periods"]
            if len(periods)!=horizon or [p["step"] for p in periods]!=list(range(1,horizon+1)):
                raise ValueError("missing, repeated or misordered periods")
            money=record["initial_total_money_cents"]
            for p in periods:
                if any(p.get(key)!=0 for key in CHECKS):
                    raise ValueError("period accounting identity violation")
                if (p["household_spendable_cash_cents"]+p["household_savings_stock_cents"]+
                    p["firm_cash_stock_cents"]+p["government_cash_stock_cents"]!=money):
                    raise ValueError("period monetary distribution mismatch")
                if p["household_monetary_assets_cents"]!=(p["household_spendable_cash_cents"]+
                                                         p["household_savings_stock_cents"]):
                    raise ValueError("double-counted household monetary assets")
                if any(p[x]<0 for x in ("resource_stock","production_units", "consumption_units",
                                        "total_inventory_units","capital_stock_units")):
                    raise ValueError("negative physical state")
            by_arm[arm]=record
        if (len({c["initial_state_sha256"] for c in by_arm.values()})!=1 or
                len({c["end_rng_state_sha256"] for c in by_arm.values()})!=1):
            raise ValueError("treatment arms not matched")
        by_seed[seed]=by_arm
    for label,aggregates in summary["means"].items():
        arm,period=label.rsplit("_t",1)
        if arm not in ARMS or int(period) not in (24,horizon):
            raise ValueError("unrecognized aggregate")
        for metric,record in aggregates.items():
            values=[by_seed[s][arm]["periods"][int(period)-1][metric] for s in seeds]
            numerical_check(record,values)
    for label,record in summary["paired_effects"].items():
        try:
            arm,suffix=label.split("_vs_control_")
        except ValueError:
            raise ValueError("unrecognized contrast") from None
        if arm not in ARMS or arm=="control":
            raise ValueError("unrecognized treatment")
        if suffix.startswith("t") and suffix.endswith("_production"):
            period=int(suffix[1:-len("_production")])
            values=[(by_seed[s][arm]["periods"][period-1]["production_units"]-
                     by_seed[s]["control"]["periods"][period-1]["production_units"])
                    for s in seeds]
        elif suffix.startswith("change_t24_t"):
            period=int(suffix[len("change_t24_t"):])
            values=[((by_seed[s][arm]["periods"][period-1]["production_units"]-
                      by_seed[s][arm]["periods"][23]["production_units"]) -
                     (by_seed[s]["control"]["periods"][period-1]["production_units"]-
                      by_seed[s]["control"]["periods"][23]["production_units"]))
                    for s in seeds]
        else:
            raise ValueError("unrecognized paired contrast")
        if period not in (24,horizon):
            raise ValueError("unexpected analysis horizon")
        numerical_check(record,values)
    expected_mean_keys={f"{arm}_t{step}" for arm in ARMS for step in (24,horizon)}
    expected_pair_keys=({f"{arm}_vs_control_t{step}_production"
                         for arm in ARMS if arm!="control" for step in (24,horizon)} |
                        {f"{arm}_vs_control_change_t24_t{horizon}"
                         for arm in ARMS if arm!="control"})
    if set(summary["means"])!=expected_mean_keys or set(summary["paired_effects"])!=expected_pair_keys:
        raise ValueError("missing/extra statistic in saved summary")
    return {"audited_runs":len(seeds)*len(ARMS),
            "audited_periods":len(seeds)*len(ARMS)*horizon,
            "seeds":seeds,"sha256_source":summary["source_sha256"],
            "status":"verified computational invariants and summary arithmetic"}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    print(json.dumps(audit(parser.parse_args().output),indent=2))
