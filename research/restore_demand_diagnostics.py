"""Restore and validate the archived v0.2 demand-diagnostics raw observations.

No network, API or nonstandard library required. Restricts paths to exact expected
seed shards and summary, rejects dangerous zip members, then audits all restored
records and statistics independently. Does not overwrite pre-existing output.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import zipfile
from research.audit_demand_diagnostics import ARMS, audit


def restore(archive: Path, destination: Path) -> dict:
    if not archive.is_file():
        raise FileNotFoundError(archive)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError("refusing to overwrite nonempty target directory")
    with zipfile.ZipFile(archive, "r") as source:
        names=source.namelist()
        if len(names)!=len(set(names)) or "summary.json" not in names:
            raise ValueError("invalid archive entries or missing summary")
        summary=json.loads(source.read("summary.json"))
        seeds=summary["design"]["seeds"]
        expected={"summary.json"} | {f"seed_{seed:04d}/{arm}.json.gz"
                                      for seed in seeds for arm in ARMS}
        if set(names)!=expected:
            raise ValueError("missing or unexpected archive entry")
        if any(not re.fullmatch(r"seed_\d{4}/[a-z_]+\.json\.gz|summary\.json",x)
               for x in names):
            raise ValueError("invalid archive path")
        # Decompress in memory with bounded member size before writing; reject
        # malformed zip contents and use no general-purpose extractall().
        payload={}
        for info in source.infolist():
            if info.file_size > 5_000_000:
                raise ValueError("oversized archive member")
            payload[info.filename]=source.read(info.filename)
    destination.mkdir(parents=True, exist_ok=True)
    for name,content in payload.items():
        path=destination/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(content)
    return audit(destination)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    print(json.dumps(restore(args.archive,args.output),indent=2))
