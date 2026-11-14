"""Safely restore an archived CIVITAS price/hiring factorial dataset.

The solid-compressed .tar.xz contains plain JSON records (not the original
per-shard gzip bytes). Restoration regenerates .json.gz and independently
checks every checksum, accounting identity and published summary.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
from pathlib import Path, PurePosixPath
import tarfile
import tempfile

from research.audit_price_hiring_stability import audit

MAX_MEMBER = 2 * 1024 * 1024


def restore(archive: Path, target: Path) -> dict:
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True, exist_ok=False)
    restored = 0
    try:
        with tarfile.open(archive, mode="r:xz") as t:
            for member in t:
                member_path = PurePosixPath(member.name)
                if (not member.isfile() or member.size > MAX_MEMBER or member.size < 0 or
                    member_path.is_absolute() or ".." in member_path.parts):
                    raise ValueError("unsafe archive entry")
                parts = member_path.parts
                expected = (len(parts) == 1 and parts[0] == "summary.json") or (
                    len(parts) == 2 and parts[0].startswith("seed_") and
                    len(parts[0]) == 9 and parts[0][5:].isdigit() and
                    parts[1].endswith(".json") and not parts[1].startswith("."))
                if not expected:
                    raise ValueError("unexpected archive path")
                dest = target.joinpath(*parts)
                if len(parts) == 2:
                    dest = dest.with_suffix(".json.gz")
                if dest.exists():
                    raise ValueError("duplicate archive entry")
                source = t.extractfile(member)
                if source is None:
                    raise ValueError("unreadable archive entry")
                raw = source.read(MAX_MEMBER + 1)
                if len(raw) != member.size:
                    raise ValueError("archive size mismatch")
                json.loads(raw)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if len(parts) == 1:
                    dest.write_bytes(raw)
                else:
                    with dest.open("wb") as f:
                        with gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as g:
                            g.write(raw)
                restored += 1
        result = audit(target)
        result["restored_files"] = restored
        return result
    except Exception:
        # Never leave behind an apparently complete but unverified dataset.
        import shutil
        shutil.rmtree(target)
        raise


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("archive", type=Path)
    cli.add_argument("output", type=Path)
    options = cli.parse_args()
    print(json.dumps(restore(options.archive, options.output), indent=2))
