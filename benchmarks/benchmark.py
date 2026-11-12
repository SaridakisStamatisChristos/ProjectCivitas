"""Measured CPU reference times: each workload is separate and deterministic."""
from __future__ import annotations
import argparse
from dataclasses import replace
import json
import os
import platform
import sys
from time import perf_counter
from pathlib import Path
import numpy as np
from civitas.model import Scenario
from civitas.engine import Simulation


def run(n: int, periods: int) -> dict:
    c = replace(Scenario(name="cpu_reference"), population=n, steps=periods, seed=7)
    sim = Simulation(c)
    state = sim.state
    arrays = [state.household_of_agent, state.participation, state.skills,
              state.household_cash, state.firm_cash, state.inventory,
              state.prices, state.last_sales, state.last_unmet,
              state.last_employment, state.cumulative_output,
              state.cumulative_consumption, *state.firm_owner_households]
    state_bytes = sum(a.nbytes for a in arrays)
    start = perf_counter()
    records = sim.run(periods)
    elapsed = perf_counter() - start
    return {"agents":n,"periods":periods,"seed":7,"wall_seconds":elapsed,
            "state_array_bytes":state_bytes,
            "final_accounting_discrepancies":{
                k:records[-1].metrics[k] if records else None
                for k in ("money_discrepancy_cents", "resource_discrepancy_units", "goods_discrepancy_units")}}


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument('--agents',default='1000,10000,100000')
    p.add_argument('--steps',type=int,default=3)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    d={"python":platform.python_version(),"numpy":np.__version__,"platform":platform.platform(),
       "benchmark_note":"wall-time observations in this invocation, not hardware-independent predictions",
       "runs":[run(int(x),a.steps) for x in a.agents.split(',')]}
    result=json.dumps(d,indent=2)+'\n'
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(result,encoding='utf-8')
    print(result)

if __name__ == '__main__':main()
