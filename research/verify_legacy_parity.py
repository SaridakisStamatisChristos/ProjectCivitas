"""Compare all original metric keys against a preserved previous checkout.

Example: python research/verify_legacy_parity.py --reference ../CIVITAS-v02-old \
             --candidate . --output results/credit_legacy_parity.json
This launches each installation with its own Python path, avoiding cross-import.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

CASES = ("market","mixed_redistributive","automation_shock",
         "resource_scarcity","capital_reinvestment","capital_depreciation_only")
SEEDS = (7,11,13)
SCRIPT = '''from dataclasses import replace
import json,sys
from pathlib import Path
from civitas.engine import Simulation
from civitas.model import Scenario
p=Path(sys.argv[1])
result={}
for name in sys.argv[2].split(','):
  cfg=Scenario.from_file(p/'scenarios'/f'{name}.json')
  for seed in (7,11,13):
    q=replace(cfg,population=200,seed=seed)
    result[f'{name}_{seed}']=[x.metrics for x in Simulation(q).run(12)]
print(json.dumps(result,sort_keys=True,allow_nan=False))'''


def read(checkout: Path) -> tuple[dict, str]:
    env=dict(os.environ,PYTHONPATH=str(checkout/'src'))
    raw=subprocess.check_output([sys.executable,"-c",SCRIPT,str(checkout),",".join(CASES)],env=env)
    return json.loads(raw),hashlib.sha256(raw).hexdigest()


def verify(reference: Path,candidate: Path) -> dict:
    old,old_hash=read(reference)
    new,new_hash=read(candidate)
    if old.keys()!=new.keys():
        raise AssertionError('scenario/seed set differs')
    total=0
    for key,periods in old.items():
        if len(periods)!=len(new[key]):raise AssertionError('period count differs')
        for i,metrics in enumerate(periods):
            for field,value in metrics.items():
                if field not in new[key][i] or new[key][i][field]!=value:
                    raise AssertionError(f'legacy metric drift: {key} period {i}, field {field}')
                total+=1
    return {"scenarios":len(CASES),"seeds":list(SEEDS),"steps":12,
            "period_states":sum(map(len,old.values())),
            "historical_metric_cells_exact":total,"result":"PASS",
            "reference_sha256":old_hash,"candidate_sha256":new_hash}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--reference',required=True,type=Path)
    p.add_argument('--candidate',required=True,type=Path)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    result=verify(a.reference.resolve(),a.candidate.resolve())
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
