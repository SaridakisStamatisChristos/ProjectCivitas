"""Within-agent-state, within-RNG 2x2 sales/labor access experiment.

No policy can alter initial agents, household cash, firm capital, resources,
ownership, or random draws: each treatment starts from one deep-copied state
per seed and its copied PCG64 bit-generator state. Only labor and consumer
seller eligibility change. The fiscal system, natural-resource pool and
interfirm investment are deliberately COMMON across regions (not autarkies).
"""
from __future__ import annotations

import argparse
import csv
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import math
import platform
from pathlib import Path
import statistics
import time

import numpy as np
from civitas import __version__
from civitas.engine import Simulation
from civitas.model import Scenario
from civitas.persistence import canonical_json, config_digest

BASE = Path(__file__).resolve().parents[1]
ORIGINAL_CHECKPOINT = '96703d9dfa39e5e753ae7a710bb398876496ec78'
ACCESS = {"open": (False, False), "sales_only": (True, False),
          "labor_only": (False, True), "both": (True, True)}
METRICS = ("production_per_person", "consumption_per_person", "employment_rate",
           "disposable_income_gini", "active_seller_fraction", "resource_per_person",
           "unmet_stock_per_person", "unmet_budget_per_person")
AUDIT = ("money_discrepancy_cents", "goods_discrepancy_units",
         "resource_discrepancy_units", "capital_discrepancy_units",
         "household_cashflow_discrepancy_cents", "firm_cashflow_discrepancy_cents")


def scenario(seed: int) -> Scenario:
    c = Scenario.from_file(BASE / 'scenarios/population_normalized/o08_s00_n10000.json')
    return replace(c, name='matched_market_access', seed=seed, market_regions=10)


def digest_state(sim: Simulation) -> str:
    s = sim.state
    h = hashlib.sha256()
    for key in ('household_of_agent','participation','skills','household_cash',
                'household_savings','firm_cash','firm_capital','inventory',
                'prices','last_sales','last_unmet','last_employment',
                'cumulative_output','cumulative_consumption','cumulative_capital_goods_converted'):
        a = np.ascontiguousarray(getattr(s, key))
        h.update(key.encode()); h.update(a.dtype.str.encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
    for owner in s.firm_owner_households:
        h.update(len(owner).to_bytes(8, 'little')); h.update(np.ascontiguousarray(owner).tobytes())
    for field in ('step','gov_cash','resource','initial_total_money','initial_resource',
                  'initial_capital_total','cumulative_capital_added','cumulative_capital_depreciated',
                  'cumulative_resource_extracted','cumulative_resource_regenerated'):
        h.update(f'{field}={getattr(s, field)};'.encode())
    h.update(canonical_json(sim.rng.bit_generator.state).encode())
    return h.hexdigest()


def measure(metrics: dict, population: int, n_firms: int) -> dict:
    return {
        'production_per_person': metrics['production_units']/population,
        'consumption_per_person': metrics['consumption_units']/population,
        'employment_rate': metrics['employment_rate'],
        'disposable_income_gini': metrics['disposable_income_gini'],
        'active_seller_fraction': metrics['active_sellers']/n_firms,
        'resource_per_person': metrics['resource_stock']/population,
        'unmet_stock_per_person': metrics['unmet_stock_demand_units']/population,
        'unmet_budget_per_person': metrics['unmet_budget_demand_units']/population,
    }


def verify(period):
    for name in AUDIT:
        if period.metrics[name] != 0:
            raise AssertionError(f'accounting identity {name}: {period.metrics[name]} step {period.metrics["step"]}')


def estimate(values):
    if not values or any(x is None or not math.isfinite(x) for x in values):
        return None
    mean = statistics.mean(values)
    sd = statistics.stdev(values) if len(values) >= 2 else None
    err = (1.96*sd/math.sqrt(len(values))) if sd is not None else None
    return {'n':len(values),'mean':mean,'sample_sd':sd,
            'approx_95pct_monte_carlo_interval':[mean-err,mean+err] if err is not None else None}


def contrasts(seed_records, seeds: int, steps: int) -> dict:
    result = {'final_period':{},'paired_effects':{},'notes':[
        'Four arms use exactly the same initial agents/firms/ownership/RNG for each seed.',
        'Household-purchase eligibility and worker-to-firm hiring eligibility are the only direct interventions.',
        'Common government, resource pool, global hiring information and interfirm capital trades persist.',
        'Confidence intervals only quantify seed-related Monte Carlo error, not model or parameter uncertainty.',
        'Effects are conditional on this synthetic model; not empirical policy estimates.']}
    for arm in ACCESS:
        result['final_period'][arm] = {m:estimate([seed_records[(i,steps,arm)][m] for i in range(1,seeds+1)])
                                         for m in METRICS}
    formulas = {'sales_given_open': {'sales_only':1,'open':-1},
                'labor_given_open':{'labor_only':1,'open':-1},
                'both_vs_open':{'both':1,'open':-1},
                'sales_labor_interaction':{'both':1,'sales_only':-1,'labor_only':-1,'open':1}}
    for name,weights in formulas.items():
        result['paired_effects'][name] = {}
        for m in METRICS:
            sample=[]
            for i in range(1,seeds+1):
                y=[(seed_records[(i,steps,arm)][m],w) for arm,w in weights.items()]
                if any(v is None for v,w in y):
                    sample=[]; break
                sample.append(sum(v*w for v,w in y))
            result['paired_effects'][name][m]=estimate(sample)
    return result


def read_verified(output: Path, seeds: int, steps: int):
    md=json.loads((output/'metadata.json').read_text())
    path=output/'periods.csv'
    if md['seeds'] != seeds or md['steps'] != steps or md['arms'] != ACCESS:
        # JSON list conversion makes tuples into arrays.
        if (md['seeds'],md['steps']) != (seeds,steps) or md['arms'] != {k:list(v) for k,v in ACCESS.items()}:
            raise ValueError('metadata configuration mismatch')
    if hashlib.sha256(path.read_bytes()).hexdigest() != md['data_sha256']:
        raise ValueError('period data sha256 mismatch')
    expected={(seed,step,arm) for seed in range(1,seeds+1)
              for step in range(1,steps+1) for arm in ACCESS}
    rows={}
    with path.open(newline='',encoding='utf8') as stream:
        for raw in csv.DictReader(stream):
            key=(int(raw['seed']),int(raw['step']),raw['arm'])
            if key in rows: raise ValueError(f'duplicate record {key}')
            rows[key]={m:(float(raw[m]) if raw[m] else None) for m in METRICS}
    if set(rows) != expected:
        raise ValueError(f'incomplete or unexpected period records ({len(rows)} vs {len(expected)})')
    if len(md['initial_hashes']) != seeds or len(md['final_rng_hashes']) != seeds:
        raise ValueError('missing initial/RNG attestation')
    return rows,md


def execute(output: Path, seeds: int=30, steps: int=24):
    if seeds < 2 or steps < 1:
        raise ValueError('seeds>=2, steps>=1 required')
    output.mkdir(parents=True,exist_ok=True)
    path=output/'periods.csv'
    tmp=output/'periods.csv.part'
    initial_hashes={}
    final_rng_hashes={}
    t0=time.perf_counter()
    n_periods=0
    with tmp.open('w',newline='',encoding='utf8') as stream:
        writer=csv.DictWriter(stream,fieldnames=['seed','step','arm',*METRICS])
        writer.writeheader()
        for seed in range(1,seeds+1):
            c=scenario(seed)
            initial=Simulation(c)
            start_state=deepcopy(initial.state)
            rng_state=deepcopy(initial.rng.bit_generator.state)
            root_hash=digest_state(initial)
            initial_hashes[str(seed)]=root_hash
            end_rng={}
            for arm,(sales,labor) in ACCESS.items():
                treatment=replace(c,restrict_household_sales=sales,restrict_labor_hiring=labor)
                sim=Simulation(treatment,state=deepcopy(start_state),rng_state=deepcopy(rng_state))
                if digest_state(sim) != root_hash:
                    raise AssertionError(f'initial-state mismatch: {seed} {arm}')
                nf=len(sim.state.firm_cash)
                for period in sim.run(steps):
                    verify(period)
                    writer.writerow({'seed':seed,'step':period.metrics['step'],'arm':arm,
                                     **measure(period.metrics,c.population,nf)})
                    n_periods += 1
                end_rng[arm]=hashlib.sha256(canonical_json(sim.rng.bit_generator.state).encode()).hexdigest()
            if len(set(end_rng.values())) != 1:
                raise AssertionError(f'random stream divergence across treatments: {seed}')
            final_rng_hashes[str(seed)]=next(iter(end_rng.values()))
    tmp.replace(path)
    md={'schema_version':1,'model_version':__version__,
        'baseline_commit':ORIGINAL_CHECKPOINT,
        'scenario_digest_seed1':config_digest(scenario(1)),
        'seeds':seeds,'steps':steps,'arms':{k:list(v) for k,v in ACCESS.items()},
        'population':scenario(1).population,'firm_count':scenario(1).firms_per_sector*len(scenario(1).sectors),
        'regions':scenario(1).market_regions,
        'initial_hashes':initial_hashes,'final_rng_hashes':final_rng_hashes,
        'simulations':seeds*len(ACCESS),'audited_periods':n_periods,
        'data_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'python':platform.python_version(),'numpy':np.__version__,
        'platform':platform.platform(),'wall_seconds':time.perf_counter()-t0,
        'disclosure':'Only households’ consumer seller pools and individual labor access are restricted; capital procurement, fiscal transfers, resource allocation, and global unmet-demand hiring information remain shared. No empirical calibration.'}
    (output/'metadata.json').write_text(json.dumps(md,indent=2,allow_nan=False)+'\n')
    rows,_=read_verified(output,seeds,steps)
    summary=contrasts(rows,seeds,steps)
    (output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    (output/'scenario_seed1.json').write_text(json.dumps(scenario(1).to_dict(),indent=2)+'\n')
    return md,summary



def run_single_seed(output: Path, seed: int, steps: int):
    """Atomic independently reproducible shard, no partial seed counted."""
    if seed < 1 or steps < 1:
        raise ValueError('seed and steps must be positive')
    target_dir = output / 'seed_shards'
    target_dir.mkdir(parents=True,exist_ok=True)
    filename = target_dir / f'seed_{seed:04d}.csv'
    sidecar = target_dir / f'seed_{seed:04d}.json'
    temp = filename.with_suffix('.csv.part')
    base = Simulation(scenario(seed))
    rng0 = deepcopy(base.rng.bit_generator.state)
    state0 = deepcopy(base.state)
    digest0 = digest_state(base)
    final_rngs = []
    count = 0
    t0 = time.perf_counter()
    with temp.open('w',newline='',encoding='utf8') as stream:
        writer = csv.DictWriter(stream,fieldnames=['seed','step','arm',*METRICS])
        writer.writeheader()
        for name,(sales,labor) in ACCESS.items():
            cfg=replace(scenario(seed), restrict_household_sales=sales,
                        restrict_labor_hiring=labor)
            sim=Simulation(cfg,state=deepcopy(state0),rng_state=deepcopy(rng0))
            assert digest_state(sim) == digest0
            for period in sim.run(steps):
                verify(period)
                writer.writerow({'seed':seed,'step':period.metrics['step'],'arm':name,
                                 **measure(period.metrics,cfg.population,len(sim.state.firm_cash))})
                count += 1
            final_rngs.append(hashlib.sha256(canonical_json(sim.rng.bit_generator.state).encode()).hexdigest())
    if len(set(final_rngs)) != 1:
        temp.unlink(missing_ok=True)
        raise AssertionError(f'RNG streams diverged for seed {seed}')
    temp.replace(filename)
    md={'seed':seed,'steps':steps,'num_records':count,'initial_sha256':digest0,
        'final_rng_sha256':final_rngs[0],
        'config_sha256':config_digest(scenario(seed)),
        'data_sha256':hashlib.sha256(filename.read_bytes()).hexdigest(),
        'runtime_seconds':time.perf_counter()-t0}
    sidecar.write_text(json.dumps(md,indent=2)+'\n',encoding='utf8')
    return md


def finalize_shards(output: Path,seeds: int,steps: int):
    """Reject missing, tampered, duplicated, or definition-mismatched seed shards."""
    if seeds<2 or steps<1: raise ValueError('invalid experiment size')
    output.mkdir(parents=True,exist_ok=True)
    shards=output/'seed_shards'
    tmp=output/'periods.csv.part'
    ini_hashes={}
    rng_hashes={}
    with tmp.open('w',newline='',encoding='utf8') as stream:
        writer=csv.DictWriter(stream,fieldnames=['seed','step','arm',*METRICS])
        writer.writeheader()
        for seed in range(1,seeds+1):
            csvfile=shards/f'seed_{seed:04d}.csv'
            sidecar=shards/f'seed_{seed:04d}.json'
            md=json.loads(sidecar.read_text())
            if (md['seed']!=seed or md['steps']!=steps or
                    md['config_sha256']!=config_digest(scenario(seed)) or
                    md['num_records'] != len(ACCESS)*steps or
                    hashlib.sha256(csvfile.read_bytes()).hexdigest()!=md['data_sha256']):
                raise ValueError(f'shard definition or digest mismatch: {seed}')
            rows={}
            with csvfile.open(newline='',encoding='utf8') as f:
                for row in csv.DictReader(f):
                    key=(int(row['seed']),int(row['step']),row['arm'])
                    if key in rows: raise ValueError(f'duplicate row in seed {seed}: {key}')
                    rows[key]=row
            expected={(seed,period,arm) for period in range(1,steps+1) for arm in ACCESS}
            if set(rows)!=expected:
                raise ValueError(f'invalid shard coverage: {seed}')
            for period in range(1,steps+1):
                for arm in ACCESS:
                    writer.writerow(rows[(seed,period,arm)])
            ini_hashes[str(seed)] = md['initial_sha256']
            rng_hashes[str(seed)] = md['final_rng_sha256']
    tmp.replace(output/'periods.csv')
    file=output/'periods.csv'
    md={'schema_version':1,'model_version':__version__,
        'baseline_commit':ORIGINAL_CHECKPOINT,
        'scenario_digest_seed1':config_digest(scenario(1)),
        'seeds':seeds,'steps':steps,'arms':{k:list(v) for k,v in ACCESS.items()},
        'population':scenario(1).population,
        'firm_count':scenario(1).firms_per_sector*len(scenario(1).sectors),
        'regions':scenario(1).market_regions,
        'initial_hashes':ini_hashes,'final_rng_hashes':rng_hashes,
        'simulations':seeds*len(ACCESS),'audited_periods':seeds*len(ACCESS)*steps,
        'data_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
        'python':platform.python_version(),'numpy':np.__version__,
        'platform':platform.platform(),'record_origin':'independently verified atomic per-seed shards',
        'disclosure':'Same agents/firms/assets and PCG64 state within each seed. Only household sales and labor access are gated; government, natural resource, demand signals and capital procurement remain global.'}
    (output/'metadata.json').write_text(json.dumps(md,indent=2,allow_nan=False)+'\n')
    rows,_=read_verified(output,seeds,steps)
    report=contrasts(rows,seeds,steps)
    (output/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    (output/'scenario_seed1.json').write_text(json.dumps(scenario(1).to_dict(),indent=2)+'\n')
    return md,report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--seeds',type=int,default=30)
    ap.add_argument('--steps',type=int,default=24)
    ap.add_argument('--output',type=Path,default=BASE/'research/v02_matched_market_30')
    ap.add_argument('--verify-only',action='store_true')
    ap.add_argument('--seed',type=int,help='run just this atomic seed shard')
    ap.add_argument('--finalize',action='store_true',help='aggregate and verify complete seed shards')
    a=ap.parse_args()
    if a.seed is not None:
        print(json.dumps(run_single_seed(a.output,a.seed,a.steps),indent=2))
        return
    if a.finalize:
        md,summary=finalize_shards(a.output,a.seeds,a.steps)
    elif a.verify_only:
        rows,md=read_verified(a.output,a.seeds,a.steps)
        summary=contrasts(rows,a.seeds,a.steps)
    else:
        md,summary=execute(a.output,a.seeds,a.steps)
    print(json.dumps({'verified':True,'simulations':md['simulations'],
                      'audited_periods':md['audited_periods'],
                      'production_means':{k:round(summary['final_period'][k]['production_per_person']['mean'],6)
                                          for k in ACCESS},
                      'interaction':summary['paired_effects']['sales_labor_interaction']['production_per_person']},
                     indent=2))


if __name__=='__main__':
    main()
