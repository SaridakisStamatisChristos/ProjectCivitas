"""Seeded independent cash + physical stock replay over heterogeneous synthetic worlds.

Execute:
  PYTHONPATH=src:. python research/run_physical_closure.py --output research/v02_physical_ledger_20
Recheck saved digest:
  PYTHONPATH=src:. python research/run_physical_closure.py --output research/v02_physical_ledger_20 --verify-only
Regenerate the entire experiment and compare:
  PYTHONPATH=src:. python research/run_physical_closure.py --output research/v02_physical_ledger_20 --verify-replay
"""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import argparse
import hashlib
import json
import tempfile
from civitas.engine import Simulation
from civitas.ledger_audit import capture_opening, audit_period
from civitas.physical_audit import capture_physical_opening, audit_physical_period
from civitas.model import Scenario
from civitas.world_genesis import default_plan, resolve_plan

MODES = ("legacy", "capital_cost", "savings_credit", "hybrid_world")
CHECKS = ("money_discrepancy_cents", "resource_discrepancy_units",
          "goods_discrepancy_units", "capital_discrepancy_units",
          "household_cashflow_discrepancy_cents", "firm_cashflow_discrepancy_cents",
          "loan_discrepancy_cents")


def config(mode: str, seed: int, population: int) -> Scenario:
    if mode == "hybrid_world":
        return replace(resolve_plan(default_plan(mode="hybrid", seed=seed,
                                                name=f"physical_{mode}_{seed}",
                                                population=population)), transaction_trace=True)
    common = dict(name=f"physical_{mode}_{seed}", population=population,
                  seed=seed, firms_per_sector=3, transaction_trace=True)
    if mode == "legacy":
        return Scenario(**common)
    common.update(capital_enabled=True, cost_basis_accounting_enabled=True,
                  initial_capital_units_per_firm=30, capital_depreciation_rate=0.08,
                  capital_output_per_unit=10, capital_investment_budget_share=0.2,
                  resource_extraction_fee_cents_per_unit=3)
    if mode == "capital_cost":
        return Scenario(**common)
    if mode == "savings_credit":
        return Scenario(**common, credit_enabled=True, household_savings_rate=0.25)
    raise ValueError("unknown world mode")


def _digest(data: object) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode("ascii")).hexdigest()


def execute(*, seeds: tuple[int, ...] = (1, 2, 3, 5, 8),
            steps: int = 12, population: int = 120, output: Path) -> dict:
    if (not seeds or len(set(seeds)) != len(seeds) or
            any(type(seed) is not int or seed < 0 for seed in seeds) or
            type(steps) is not int or steps < 1 or
            type(population) is not int or population < 0):
        raise ValueError("nonnegative unique seeds, nonnegative population and positive steps required")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for mode in MODES:
        for seed in seeds:
            scenario = config(mode, seed, population)
            simulation = Simulation(scenario)
            evidence = []
            for _ in range(steps):
                money_open = capture_opening(simulation.state)
                physical_open = capture_physical_opening(simulation.state)
                period = simulation.step()
                cash = audit_period(money_open, simulation.state, period)
                physical = audit_physical_period(physical_open, simulation.state, period, scenario)
                if any(period.metrics[key] != 0 for key in CHECKS):
                    raise AssertionError("a stock-flow identity failed")
                if (period.metrics["firm_book_equity_discrepancy_cents"] not in (0, None)):
                    raise AssertionError("a book-equity reconciliation failed")
                evidence.append({
                    "step": period.metrics["step"],
                    "transfers": cash.transfer_count,
                    "noncash_writeoffs": cash.noncash_writeoff_count,
                    "physical_events": physical.physical_event_count,
                    "units_produced": physical.production_units,
                    "units_consumed": physical.consumption_units,
                    "resource_extracted": physical.resource_extracted_units,
                    "capital_added": physical.capital_added_units,
                    "capital_depreciated": physical.capital_depreciated_units,
                    "cash_volume_cents": cash.transfer_cents,
                    "event_sha256": _digest({"cash": period.transactions,
                                             "noncash": period.noncash_transactions,
                                             "physical": period.physical_transactions}),
                })
            rows.append({"mode": mode, "seed": seed, "population": scenario.population,
                         "periods": steps, "physical_events": sum(x["physical_events"] for x in evidence),
                         "cash_transfers": sum(x["transfers"] for x in evidence),
                         "production_units": sum(x["units_produced"] for x in evidence),
                         "consumption_units": sum(x["units_consumed"] for x in evidence),
                         "cash_volume_cents": sum(x["cash_volume_cents"] for x in evidence),
                         "steps": evidence})
    summary = {"schema": 1, "kind": "synthetic_physical_and_cash_ledger_closure",
               "seeds": list(seeds), "horizon": steps, "requested_population": population,
               "modes": list(MODES), "runs": len(rows), "audited_periods": len(rows) * steps,
               "physical_events": sum(r["physical_events"] for r in rows),
               "cash_transfers": sum(r["cash_transfers"] for r in rows),
               "production_units": sum(r["production_units"] for r in rows),
               "consumption_units": sum(r["consumption_units"] for r in rows),
               "identity_failures": 0, "rows": rows,
               "scope": "event-level physical quantities, integer historical costs, and cash settlement; synthetic economics only"}
    summary["payload_sha256"] = _digest(summary)
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def verify_summary(path: Path) -> dict:
    result = json.loads(Path(path).read_text(encoding="utf-8"))
    given = result.pop("payload_sha256", None)
    if type(given) is not str or given != _digest(result):
        raise ValueError("physical experiment hash mismatch")
    rows = result["rows"]
    if (result.get("runs") != len(rows) or
            result.get("audited_periods") != sum(row["periods"] for row in rows) or
            result.get("physical_events") != sum(row["physical_events"] for row in rows) or
            result.get("cash_transfers") != sum(row["cash_transfers"] for row in rows) or
            result.get("production_units") != sum(row["production_units"] for row in rows) or
            result.get("consumption_units") != sum(row["consumption_units"] for row in rows) or
            result.get("identity_failures") != 0 or
            any(len(row["steps"]) != row["periods"] or
                row["physical_events"] != sum(x["physical_events"] for x in row["steps"]) or
                row["cash_transfers"] != sum(x["transfers"] for x in row["steps"]) or
                row["production_units"] != sum(x["units_produced"] for x in row["steps"]) or
                row["consumption_units"] != sum(x["units_consumed"] for x in row["steps"])
                for row in rows)):
        raise ValueError("physical experiment totals disagree with saved period observations")
    result["payload_sha256"] = given
    return result


def verify_replay(path: Path) -> dict:
    saved = verify_summary(path)
    with tempfile.TemporaryDirectory() as temp:
        again = execute(seeds=tuple(saved["seeds"]), population=saved["requested_population"],
                        steps=saved["horizon"], output=Path(temp))
    if saved != again:
        raise ValueError("physical experiment deterministic replay differs")
    return saved


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seeds", default="1,2,3,5,8")
    p.add_argument("--steps", type=int, default=12)
    p.add_argument("--population", type=int, default=120)
    p.add_argument("--output", type=Path, default=Path("research/v02_physical_ledger_20"))
    p.add_argument("--verify-only", action="store_true")
    p.add_argument("--verify-replay", action="store_true")
    args = p.parse_args()
    if args.verify_replay:
        result = verify_replay(args.output / "summary.json")
    elif args.verify_only:
        result = verify_summary(args.output / "summary.json")
    else:
        result = execute(seeds=tuple(int(s) for s in args.seeds.split(",")),
                         steps=args.steps, population=args.population, output=args.output)
    print(json.dumps({k: result[k] for k in
                      ("runs", "audited_periods", "physical_events", "cash_transfers",
                       "identity_failures", "payload_sha256")}, indent=2))

if __name__ == "__main__":
    main()
