"""Seeded, independently replayed evidence for CIVITAS cash/loan journal closure.

Run from the repository root:
  PYTHONPATH=src:. python research/run_ledger_closure.py --output results/ledger_closure

Checks each participant's monetary balances and bilateral loan claims, all
period journal totals, six physical/cash conservation diagnostics, and
checkpoint replay. Results reflect a synthetic model; no empirical claim.
"""
from __future__ import annotations
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from civitas.engine import Simulation
from civitas.ledger_audit import capture_opening, audit_period
from civitas.world_genesis import default_plan, resolve_plan
from civitas.persistence import checkpoint_save, checkpoint_load

CHECKS = (
    "money_discrepancy_cents", "resource_discrepancy_units",
    "goods_discrepancy_units", "capital_discrepancy_units",
    "household_cashflow_discrepancy_cents", "firm_cashflow_discrepancy_cents",
    "loan_discrepancy_cents",
)
MODES = ("configured", "hybrid", "randomized")


def execute(*, seeds: tuple[int, ...] = (1, 2, 3, 5, 8), steps: int = 12,
            population: int = 400, output: Path) -> dict:
    if (not seeds or any(type(seed) is not int or seed < 0 for seed in seeds) or
            type(steps) is not int or steps <= 0 or
            type(population) is not int or population < 0):
        raise ValueError("positive horizon, nonnegative population, nonnegative seeds required")
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for mode in MODES:
        for seed in seeds:
            plan = default_plan(mode=mode, seed=seed,
                                name=f"ledger_{mode}_{seed}", population=population)
            c = replace(resolve_plan(plan), steps=steps, transaction_trace=True)
            sim = Simulation(c)
            money_stock = sim.state.total_money()
            count, cash_volume, writeoffs, credit_volume = 0, 0, 0, 0
            for _ in range(steps):
                opening = capture_opening(sim.state)
                period = sim.step()  # includes the independent auditor itself
                verdict = audit_period(opening, sim.state, period)  # external explicit check
                for check in CHECKS:
                    value = period.metrics[check]
                    if value != 0:
                        raise AssertionError(f"{mode} seed={seed} {check}={value}")
                if c.cost_basis_accounting_enabled and period.metrics["firm_book_equity_discrepancy_cents"]:
                    raise AssertionError("nonzero book-equity discrepancy")
                if verdict.money_stock_cents != money_stock:
                    raise AssertionError("cash stock changed")
                count += verdict.transfer_count
                cash_volume += verdict.transfer_cents
                writeoffs += verdict.noncash_writeoff_cents
                credit_volume += period.metrics["loan_origination_cents"]
            # Independently validate restoring the live checkpoint and auditing
            # another period. The working state does not include previous trace.
            path = output / f".tmp_{mode}_{seed}.npz"
            checkpoint_save(path, c, sim.state, sim.rng.bit_generator.state)
            rc, state, rng = checkpoint_load(path)
            path.unlink()
            restored = Simulation(rc, state=state, rng_state=rng)
            if restored.state.step != steps:
                raise AssertionError("checkpoint step changed")
            initial = capture_opening(restored.state)
            next_period = restored.step()
            audit_period(initial, restored.state, next_period)
            if next_period.metrics != sim.step().metrics:
                raise AssertionError("checkpoint restart changed trajectory")
            rows.append({
                "mode": mode, "seed": seed, "population": c.population,
                "steps": steps, "cash_stock_cents": money_stock,
                "transfer_count": count, "transfer_cents": cash_volume,
                "loan_origination_cents": credit_volume,
                "noncash_writeoff_cents": writeoffs,
                "checkpoint_replay": "exact", "identity_failures": 0,
            })
    result = {
        "schema": 1, "kind": "synthetic_ledger_closure",
        "scope": "cash transfers, savings accounts, principal loans, noncash loan defaults; not full GAAP/IFRS",
        "seeds": list(seeds), "requested_population": population,
        "modes": list(MODES), "horizon": steps,
        "runs": len(rows), "audited_periods": len(rows) * steps,
        "transfer_count": sum(r["transfer_count"] for r in rows),
        "transfer_cents": sum(r["transfer_cents"] for r in rows),
        "identity_failures": 0, "rows": rows,
    }
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True).encode("utf-8")
    result["payload_sha256"] = hashlib.sha256(canonical).hexdigest()
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def verify_summary(path: Path) -> dict:
    """Recount a saved experimental result and reject missing/modified rows.

    This verifies the report's integrity and accounting declarations; the
    original execution (or independent rerun) verifies the actual engine.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if type(payload) is not dict or type(payload.get("payload_sha256")) is not str:
        raise ValueError("invalid ledger experiment summary")
    digest = payload.pop("payload_sha256")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("ledger experiment evidence hash mismatch")
    rows = payload.get("rows")
    if (type(rows) is not list or type(payload.get("audited_periods")) is not int or
            payload.get("runs") != len(rows) or
            payload["audited_periods"] != sum(row["steps"] for row in rows) or
            payload.get("transfer_count") != sum(row["transfer_count"] for row in rows) or
            payload.get("transfer_cents") != sum(row["transfer_cents"] for row in rows) or
            payload.get("identity_failures") != 0 or
            any(row.get("identity_failures") != 0 or row.get("checkpoint_replay") != "exact"
                for row in rows)):
        raise ValueError("ledger experiment summary rows are inconsistent")
    payload["payload_sha256"] = digest
    return payload


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", default="1,2,3,5,8")
    p.add_argument("--steps", type=int, default=12)
    p.add_argument("--population", type=int, default=400)
    p.add_argument("--output", type=Path, default=Path("results/ledger_closure"))
    p.add_argument("--verify-only", action="store_true", help="verify a saved summary digest and row totals")
    args = p.parse_args()
    result = (verify_summary(args.output / "summary.json") if args.verify_only else
              execute(seeds=tuple(int(v) for v in args.seeds.split(",")), steps=args.steps,
                      population=args.population, output=args.output))
    print(json.dumps({key: result[key] for key in
                      ("runs", "audited_periods", "transfer_count", "transfer_cents", "identity_failures", "payload_sha256")}, indent=2))


if __name__ == "__main__":
    main()
