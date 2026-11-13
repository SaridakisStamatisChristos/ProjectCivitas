"""Independent, stdlib-only audit of CIVITAS v0.2 credit pathway records.

Unlike run_credit_pathways.py, this file imports no simulation code. It
recomputes stored SHA-256 digests, conservation, loan stock-flow, matched-state
and negative-control identities, then independently checks reported means.

Usage: python research/audit_credit_pathways.py research/v02_credit_pathways_10000
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean

CHECKS = (
    "money_discrepancy_cents", "resource_discrepancy_units", "goods_discrepancy_units",
    "capital_discrepancy_units", "household_cashflow_discrepancy_cents",
    "firm_cashflow_discrepancy_cents", "firm_book_equity_discrepancy_cents",
    "loan_discrepancy_cents",
)


def canonical(x: object) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, ensure_ascii=False).encode("utf-8")


def sha256(x: object) -> str:
    return hashlib.sha256(canonical(x)).hexdigest()


def audit(folder: Path) -> dict:
    summary = json.loads((folder / "summary.json").read_text())
    design = summary["design"]
    seeds = design["seeds"]
    steps = design["steps"]
    if len(seeds) != len(set(seeds)) or not seeds:
        raise ValueError("invalid or duplicated seed ID")
    total = 0
    for seed in seeds:
        path = folder / f"seed_{seed:04d}.json"
        record = json.loads(path.read_text())
        saved = record.pop("data_sha256")
        if saved != sha256(record) or saved != summary["shard_sha256"][str(seed)]:
            raise ValueError(f"SHA-256 mismatch for seed {seed}")
        if record["seed"] != seed or record["steps"] != steps or record["source_sha256"] != design["source_sha256"]:
            raise ValueError("seed or model source mismatch")
        cells = record["cells"]
        if len(cells) != design["scenarios"] or len({c["name"] for c in cells}) != len(cells):
            raise ValueError("duplicate/missing treatment")
        if len({c["initial_state_sha256"] for c in cells}) != 1:
            raise ValueError("unmatched initial state")
        indexed = {c["name"]:c for c in cells}
        for pct in (25, 75):
            if indexed[f"s{pct}_control"]["periods"] != indexed[f"s{pct}_sham"]["periods"]:
                raise ValueError("no-lending sham differs from no-credit control")
        for cell in cells:
            rows=cell["periods"]
            if len(rows) != steps or [r["step"] for r in rows] != list(range(1, steps+1)):
                raise ValueError("incomplete trajectory")
            debt=0
            for row in rows:
                if any(row[k] != 0 for k in CHECKS):
                    raise ValueError("nonzero conservation discrepancy")
                debt += row["loan_origination_cents"] - row["loan_repayment_cents"] - row["loan_defaults_cents"]
                if debt != row["firm_loan_liabilities_cents"] or debt < 0:
                    raise ValueError("unbalanced credit principal")
                total += 1
    if total != design["audited_periods"]:
        raise ValueError("audited-period count mismatch")
    # A second independent pass checks the reported mean at BOTH horizons.
    for name, results in summary["final_period_means"].items():
        for horizon in (24, steps):
            observations=[]
            for seed in seeds:
                record=json.loads((folder / f"seed_{seed:04d}.json").read_text())
                cell=next(x for x in record["cells"] if x["name"] == name)
                observations.append(float(cell["periods"][horizon-1]["production_units"]))
            if abs(mean(observations) - results[str(horizon)]["production_units"]["mean"]) > 1e-9:
                raise ValueError("production summary does not match raw period observations")
    return {"seeds": len(seeds), "simulations": len(seeds)*design["scenarios"],
            "audited_periods": total, "all_shards_verified": True,
            "matched_initial_states": True, "no_funding_sham_identical": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.folder), indent=2))


if __name__ == "__main__":
    main()
