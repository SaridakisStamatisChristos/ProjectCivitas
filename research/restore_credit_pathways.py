"""Restore archived gzip seed data, verifying exact canonical SHA-256 checksums.

Example:
 python research/restore_credit_pathways.py research/v02_credit_pathways_10000 results/restored_credit_pathways
 PYTHONPATH=src:. python research/run_credit_pathways.py --finalize --seeds 1,2,3,4,5,6 --population 10000 --steps 48 --output results/restored_credit_pathways
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def restore(archive_dir: Path, output: Path) -> dict:
    summary = json.loads((archive_dir / "summary.json").read_text())
    expected = summary["shard_sha256"]
    output.mkdir(parents=True, exist_ok=True)
    for seed, digest in expected.items():
        gz = archive_dir / f"seed_{int(seed):04d}.json.gz"
        raw = gzip.decompress(gz.read_bytes())
        obj = json.loads(raw)
        actual = obj.pop("data_sha256", None)
        canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                               allow_nan=False, ensure_ascii=False).encode("utf-8")
        if actual != digest or hashlib.sha256(canonical).hexdigest() != digest:
            raise ValueError(f"archive data SHA-256 mismatch for seed {seed}")
        dest = output / f"seed_{int(seed):04d}.json"
        if dest.exists() and dest.read_bytes() != raw:
            raise FileExistsError(f"refusing to replace an existing different shard: {dest}")
        dest.write_bytes(raw)
    summary_path = output / "summary.json"
    if summary_path.exists() and summary_path.read_bytes() != (archive_dir / "summary.json").read_bytes():
        raise FileExistsError("refusing to overwrite a different summary")
    summary_path.write_bytes((archive_dir / "summary.json").read_bytes())
    return {"restored": len(expected), "output": str(output)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive_directory", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    print(json.dumps(restore(a.archive_directory, a.output), indent=2))


if __name__ == "__main__":
    main()
