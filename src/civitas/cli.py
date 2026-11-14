"""CLI for simulation execution, checkpoints, and replicated scenario experiments."""
from __future__ import annotations
import argparse
from dataclasses import replace
import json
from pathlib import Path
import statistics
import time
from civitas.engine import Simulation
from civitas.model import Scenario
from civitas.persistence import checkpoint_load, checkpoint_save, save_run


def _run(sim: Simulation, steps: int, output: Path) -> dict:
    start_step = sim.state.step
    t0 = time.perf_counter()
    periods = sim.run(steps)
    elapsed = time.perf_counter() - t0
    meta = save_run(output, sim.scenario, periods, seed=sim.scenario.seed,
                    elapsed_seconds=elapsed, initial_step=start_step)
    checkpoint_save(output / "checkpoint.npz", sim.scenario, sim.state, sim.rng.bit_generator.state)
    return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="civitas", description="Local-first artificial civilization laboratory")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="execute one scenario")
    run.add_argument("--scenario", required=True, type=Path)
    run.add_argument("--steps", type=int)
    run.add_argument("--seed", type=int)
    run.add_argument("--output", type=Path, default=Path("results/run"))
    resume = sub.add_parser("resume", help="continue an exact saved simulation state")
    resume.add_argument("--checkpoint", required=True, type=Path)
    resume.add_argument("--steps", type=int, required=True)
    resume.add_argument("--output", type=Path, default=Path("results/resumed"))
    suite = sub.add_parser("suite", help="replicated runs across scenario files")
    suite.add_argument("--scenarios", nargs="+", required=True, type=Path)
    suite.add_argument("--seeds", default="7,11,13")
    suite.add_argument("--steps", type=int)
    suite.add_argument("--output", type=Path, default=Path("results/suite"))
    genesis = sub.add_parser("genesis", help="generate a reproducible initial world")
    genesis.add_argument("--plan", type=Path, help="optional JSON plan with parameter distributions")
    genesis.add_argument("--mode", choices=("configured", "randomized", "hybrid"), default="hybrid")
    genesis.add_argument("--seed", type=int, default=42)
    genesis.add_argument("--name", default="genesis_world")
    genesis.add_argument("--population", type=int, default=10000)
    genesis.add_argument("--output", required=True, type=Path)
    genesis.add_argument("--force", action="store_true", help="replace an existing generated world")
    verify = sub.add_parser("verify-world", help="verify genesis plan, scenario, checkpoint and hashes")
    verify.add_argument("--world", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command == "verify-world":
        from civitas.world_genesis import verify_world
        print(json.dumps(verify_world(args.world), indent=2))
    elif args.command == "genesis":
        from civitas.world_genesis import default_plan, write_world
        plan = (json.loads(args.plan.read_text(encoding="utf-8")) if args.plan is not None else
                default_plan(mode=args.mode, seed=args.seed, name=args.name, population=args.population))
        print(json.dumps(write_world(args.output, plan, force=args.force), indent=2))
    elif args.command == "run":
        c = Scenario.from_file(args.scenario)
        c = replace(c, **({"seed": args.seed} if args.seed is not None else {}))
        c.validate()
        result = _run(Simulation(c), c.steps if args.steps is None else args.steps, args.output)
        print(json.dumps(result, indent=2))
    elif args.command == "resume":
        c, state, rng = checkpoint_load(args.checkpoint)
        result = _run(Simulation(c, state=state, rng_state=rng), args.steps, args.output)
        print(json.dumps(result, indent=2))
    else:
        seeds = [int(s) for s in args.seeds.split(",")]
        if not seeds or any(seed < 0 for seed in seeds):
            parser.error("seeds must be nonnegative integers")
        args.output.mkdir(parents=True, exist_ok=True)
        grouped: dict[str, list[dict]] = {}
        for p in args.scenarios:
            scenario = Scenario.from_file(p)
            for seed in seeds:
                c = replace(scenario, seed=seed)
                c.validate()
                run_meta = _run(Simulation(c), c.steps if args.steps is None else args.steps,
                                args.output / c.name / f"seed_{seed}")
                if run_meta["last_metrics"] is not None:
                    grouped.setdefault(c.name, []).append(run_meta["last_metrics"])
        summary = {}
        for name, observations in grouped.items():
            summary[name] = {"replications": len(observations)}
            for metric in ("employment_rate", "consumption_units", "production_units",
                           "income_gini", "disposable_income_gini",
                           "modeled_net_worth_gini", "liquid_wealth_gini", "resource_stock",
                           "capital_stock_units", "capital_added_units",
                           "capital_depreciated_units", "capital_interfirm_purchases_cents",
                           "disposable_income_total_cents",
                           "household_savings_stock_cents", "household_savings_deposited_cents",
                           "household_savings_withdrawn_cents", "household_monetary_assets_gini",
                           "firm_profit_proxy_cents", "firm_capital_depreciation_expense_cents",
                           "firm_cashflow_discrepancy_cents", "household_cashflow_discrepancy_cents",
                           "money_discrepancy_cents",
                           "goods_discrepancy_units", "capital_discrepancy_units"):
                vals = [r[metric] for r in observations if r[metric] is not None]
                summary[name][metric] = {
                    "mean": statistics.mean(vals) if vals else None,
                    "sample_sd": statistics.stdev(vals) if len(vals) > 1 else None,
                    "n": len(vals),
                }
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
