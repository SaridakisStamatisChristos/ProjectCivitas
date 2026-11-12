"""Portable checkpoints, recorded metrics, and SQLite experiment metadata."""
from __future__ import annotations
import csv
import hashlib
import json
import platform
from pathlib import Path
import sqlite3
from typing import Any
import numpy as np
from civitas import __version__
from civitas.model import Scenario
from civitas.state import State


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def config_digest(c: Scenario) -> str:
    return hashlib.sha256(canonical_json(c.to_dict()).encode()).hexdigest()


def checkpoint_save(path: str | Path, scenario: Scenario, state: State, rng_state: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    owners = state.firm_owner_households
    owner_sizes = np.array([len(o) for o in owners], dtype=np.int64)
    owner_offsets = np.r_[0, np.cumsum(owner_sizes)]
    owner_ids = np.concatenate(owners) if len(owners) else np.array([], dtype=np.int64)
    np.savez_compressed(
        target, checkpoint_version=np.array(1, dtype=np.int64),
        software_version=np.array(__version__),
        config_json=np.array(canonical_json(scenario.to_dict())),
        rng_json=np.array(canonical_json(rng_state)),
        step=np.array(state.step, dtype=np.int64),
        gov_cash=np.array(state.gov_cash, dtype=np.int64),
        resource=np.array(state.resource, dtype=np.int64),
        initial_total_money=np.array(state.initial_total_money, dtype=np.int64),
        initial_resource=np.array(state.initial_resource, dtype=np.int64),
        cumulative_resource_extracted=np.array(state.cumulative_resource_extracted, dtype=np.int64),
        cumulative_resource_regenerated=np.array(state.cumulative_resource_regenerated, dtype=np.int64),
        household_of_agent=state.household_of_agent, participation=state.participation,
        skills=state.skills, household_cash=state.household_cash,
        firm_cash=state.firm_cash, inventory=state.inventory,
        prices=state.prices, last_sales=state.last_sales,
        last_unmet=state.last_unmet, last_employment=state.last_employment,
        cumulative_output=state.cumulative_output,
        cumulative_consumption=state.cumulative_consumption,
        owner_offsets=owner_offsets, owner_ids=owner_ids,
    )


def checkpoint_load(path: str | Path) -> tuple[Scenario, State, dict]:
    with np.load(Path(path), allow_pickle=False) as z:
        if int(z["checkpoint_version"]) != 1:
            raise ValueError("unsupported checkpoint format")
        if str(z["software_version"]) != __version__:
            raise ValueError("checkpoint software version differs; migration required")
        scenario = Scenario.from_dict(json.loads(str(z["config_json"])))
        offsets = z["owner_offsets"]
        ids = z["owner_ids"]
        owners = tuple(ids[int(offsets[i]):int(offsets[i+1])].copy() for i in range(len(offsets) - 1))
        fields = ("household_of_agent", "participation", "skills", "household_cash", "firm_cash",
                  "inventory", "prices", "last_sales", "last_unmet", "last_employment",
                  "cumulative_output", "cumulative_consumption")
        arrays = {f: z[f].copy() for f in fields}
        state = State(
            step=int(z["step"]), gov_cash=int(z["gov_cash"]), resource=int(z["resource"]),
            initial_total_money=int(z["initial_total_money"]),
            initial_resource=int(z["initial_resource"]),
            cumulative_resource_extracted=int(z["cumulative_resource_extracted"]),
            cumulative_resource_regenerated=int(z["cumulative_resource_regenerated"]),
            firm_owner_households=owners, **arrays,
        )
        rng = json.loads(str(z["rng_json"]))
    # Validate checkpoint shapes as well as invariants before resuming.
    h = (scenario.population + scenario.household_size - 1) // scenario.household_size
    nf = len(scenario.sectors) * scenario.firms_per_sector
    if (len(state.household_cash) != h or len(state.participation) != scenario.population
            or state.skills.shape != (scenario.population, len(scenario.sectors))
            or len(state.firm_cash) != nf or len(owners) != nf):
        raise ValueError("checkpoint dimensions do not match scenario")
    state.validate(expected_resources=state.initial_resource + state.cumulative_resource_regenerated - state.cumulative_resource_extracted)
    return scenario, state, rng


def save_run(directory: str | Path, scenario: Scenario, periods: list,
             *, seed: int, elapsed_seconds: float, initial_step: int = 0) -> dict:
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    rows = [p.metrics for p in periods]
    (target / "config.json").write_text(json.dumps(scenario.to_dict(), indent=2) + "\n", encoding="utf-8")
    with (target / "metrics.csv").open("w", newline="", encoding="utf-8") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            for record in rows:
                writer.writerow({k: canonical_json(v) if isinstance(v, dict) else v for k, v in record.items()})
        else:
            f.write("step\n")
    with (target / "journals.jsonl").open("w", encoding="utf-8") as f:
        for p in periods:
            f.write(canonical_json({"step": p.metrics["step"], "entries": p.journal}) + "\n")
    meta = {
        "model_version": __version__, "config_sha256": config_digest(scenario),
        "scenario": scenario.name, "seed": seed, "initial_step": initial_step,
        "completed_steps": len(rows), "elapsed_wall_seconds": elapsed_seconds,
        "python": platform.python_version(), "numpy": np.__version__,
        "platform": platform.platform(), "last_metrics": rows[-1] if rows else None,
        "caveat": "Artificial model outcomes, not real-world predictions. Wall time is nondeterministic.",
    }
    (target / "metadata.json").write_text(json.dumps(meta, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with sqlite3.connect(target / "experiments.sqlite3") as db:
        db.execute("CREATE TABLE IF NOT EXISTS runs (run_id INTEGER PRIMARY KEY, scenario TEXT NOT NULL, seed INTEGER NOT NULL, config_sha256 TEXT NOT NULL, model_version TEXT NOT NULL, steps INTEGER NOT NULL, elapsed_seconds REAL NOT NULL, metadata_json TEXT NOT NULL)")
        db.execute("INSERT INTO runs (scenario,seed,config_sha256,model_version,steps,elapsed_seconds,metadata_json) VALUES (?,?,?,?,?,?,?)",
                   (scenario.name, seed, config_digest(scenario), __version__, len(rows), elapsed_seconds, canonical_json(meta)))
    return meta
