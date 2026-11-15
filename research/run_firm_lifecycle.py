"""Matched-seed opt-in firm liquidation/re-entry campaign.

The deliberately insolvent opening firm is an *engineered initial stress case*,
not an endogenous bankrupt firm. This assesses numerical conservation and
mechanical intervention sensitivity, not real bankruptcy incidence.

Commands:
  PYTHONPATH=src:. python research/run_firm_lifecycle.py --seed 1
  PYTHONPATH=src:. python research/run_firm_lifecycle.py --finalize --seeds 12
  PYTHONPATH=src:. python research/run_firm_lifecycle.py --verify-only --seeds 12
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import statistics
import numpy as np
from civitas.engine import Simulation
from civitas.model import Scenario, Sector
from civitas.finance import CreditFlows, originate

OUTPUT = Path(__file__).resolve().parent / 'v02_firm_lifecycle_12seed'


def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False)


def scenario(seed: int) -> Scenario:
    return Scenario(name='v02-experimental-lifecycle-stress', seed=seed, steps=24,
        population=120, household_size=4, firms_per_sector=2,
        initial_household_cash_cents=3000, initial_firm_cash_cents=100,
        resource_capacity=10000, initial_resource=7000, regeneration_rate=0.02,
        capital_enabled=True, initial_capital_units_per_firm=2,
        cost_basis_accounting_enabled=True, capital_investment_budget_share=0.0,
        credit_enabled=True, credit_term_periods=4, credit_repayment_fraction=0,
        firm_lifecycle_enabled=True, firm_reentry_enabled=True,
        firm_reentry_contribution_cents=60, transaction_trace=True,
        sectors=(Sector('goods',0.35,100,50,1.0,1),))


def engineered_opening(sim: Simulation) -> None:
    s = sim.state
    # This synthetic opening balance sheet creates an insolvent firm, with the
    # money transferred into another firm's cash, not issued into existence.
    s.transfer('household', 0, 'savings', 0, 1200, 'savings_deposit')
    caps = np.zeros(len(s.household_savings), dtype=np.int64)
    caps[0] = 1200
    originate(s, 0, 1200, caps, CreditFlows.empty(s))
    s.transfer('firm', 0, 'firm', 1, 1300, 'capital_purchase')
    # Explicit inherited opening inventory endowment, recorded in production
    # opening totals. It is *not* claimed to have arisen through prior periods.
    s.inventory[0] = 3
    s.firm_inventory_basis_cents[0] = 70
    s.cumulative_output[0] += 3
    s.validate()


def seed_run(seed: int) -> dict:
    c=scenario(seed)
    anchor=Simulation(c)
    engineered_opening(anchor)
    base_state=deepcopy(anchor.state)
    rng_state=deepcopy(anchor.rng.bit_generator.state)
    arms=[]
    for active in (False, True):
        config=(c if active else replace(c, firm_lifecycle_enabled=False,
                                        firm_reentry_enabled=False,
                                        firm_reentry_contribution_cents=0))
        sim=Simulation(config,state=deepcopy(base_state),rng_state=deepcopy(rng_state))
        periods=sim.run(c.steps)
        for period in periods:
            m=period.metrics
            for key in ('money_discrepancy_cents','resource_discrepancy_units',
                        'goods_discrepancy_units','capital_discrepancy_units',
                        'firm_cashflow_discrepancy_cents','household_cashflow_discrepancy_cents',
                        'loan_discrepancy_cents','firm_book_equity_discrepancy_cents'):
                if m[key] != 0:
                    raise AssertionError(f'accounting discrepancy seed={seed}, {key}')
            if period.book_balance_report['book_equity_discrepancy_cents']:
                raise AssertionError('balance sheet failed independent replay')
        arms.append({'lifecycle_enabled': active,
                     'last_production_units': periods[-1].metrics['production_units'],
                     'last_active_firms': periods[-1].metrics['firm_active_count'],
                     'liquidations': sum(p.metrics['firm_liquidations'] for p in periods),
                     'reentries': sum(p.metrics['firm_reentries'] for p in periods),
                     'loan_defaults_cents': sum(p.metrics['loan_defaults_cents'] for p in periods),
                     'inventory_scrapped': sum(p.metrics['firm_liquidation_inventory_units'] for p in periods),
                     'capital_scrapped': sum(p.metrics['firm_liquidation_capital_units'] for p in periods),
                     'cash_events_replayed': sum(len(p.transactions) for p in periods),
                     'physical_events_replayed': sum(len(p.physical_transactions) for p in periods),
                     'lifecycle_events_replayed': sum(len(p.lifecycle_transactions) for p in periods),
                     'per_period': [{'period':p.metrics['step'],
                          'production_units':p.metrics['production_units'],
                          'consumption_units':p.metrics['consumption_units'],
                          'active_firms':p.metrics['firm_active_count'],
                          'liquidations':p.metrics['firm_liquidations'],
                          'reentries':p.metrics['firm_reentries'],
                          'loan_defaults_cents':p.metrics['loan_defaults_cents'],
                          'goods_discrepancy_units':p.metrics['goods_discrepancy_units'],
                          'money_discrepancy_cents':p.metrics['money_discrepancy_cents']}
                          for p in periods]})
    return {'seed':seed,'scenario':c.to_dict(),
            'opening_money_cents':base_state.initial_total_money,
            'opening_stock_shock':'engineered: 1200-cent loan + transfer to peer, 3 inherited finished goods',
            'arms':arms}


def save_seed(seed: int, folder: Path = OUTPUT) -> Path:
    folder.mkdir(parents=True,exist_ok=True)
    obj=seed_run(seed)
    raw=(canonical(obj)+'\n').encode()
    path=folder / f'seed_{seed:03d}.json'
    tmp=path.with_suffix('.tmp')
    tmp.write_bytes(raw)
    tmp.replace(path)
    path.with_suffix('.sha256').write_text(sha256(raw).hexdigest()+'\n')
    return path


def aggregate(folder: Path=OUTPUT,seeds: int=12) -> dict:
    rows=[]
    for seed in range(1,seeds+1):
        path=folder / f'seed_{seed:03d}.json'
        raw=path.read_bytes()
        if sha256(raw).hexdigest()!=path.with_suffix('.sha256').read_text().strip():
            raise ValueError(f'integrity failure for seed {seed}')
        obj=json.loads(raw)
        if obj['seed']!=seed or len(obj['arms'])!=2:
            raise ValueError('invalid or incomplete matched seed')
        if [a['lifecycle_enabled'] for a in obj['arms']] != [False,True]:
            raise ValueError('missing intervention arm')
        if any(len(a['per_period'])!=24 for a in obj['arms']):
            raise ValueError('incomplete per-period record')
        rows.append(obj)
    diffs=[r['arms'][1]['last_production_units']-r['arms'][0]['last_production_units'] for r in rows]
    out={'design':'synthetic matched-seed initial insolvency stress; not population bankruptcy incidence',
         'seeds':seeds,'simulations':2*seeds,'audited_periods':2*seeds*24,
         'cash_events_replayed':sum(a['cash_events_replayed'] for r in rows for a in r['arms']),
         'physical_events_replayed':sum(a['physical_events_replayed'] for r in rows for a in r['arms']),
         'lifecycle_events_replayed':sum(a['lifecycle_events_replayed'] for r in rows for a in r['arms']),
         'total_liquidations':sum(r['arms'][1]['liquidations'] for r in rows),
         'total_reentries':sum(r['arms'][1]['reentries'] for r in rows),
         'total_defaults_cents':sum(r['arms'][1]['loan_defaults_cents'] for r in rows),
         'mean_final_production_no_lifecycle':statistics.mean(r['arms'][0]['last_production_units'] for r in rows),
         'mean_final_production_with_lifecycle':statistics.mean(r['arms'][1]['last_production_units'] for r in rows),
         'paired_mean_final_output_difference':statistics.mean(diffs),
         'paired_approx_95pct_halfwidth':1.96*statistics.stdev(diffs)/(seeds**0.5) if seeds>1 else None,
         'caveat':'Only internal model consistency; no independent empirical calibration; small exploratory seed count'}
    return out


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int)
    parser.add_argument('--seeds',type=int,default=12)
    parser.add_argument('--finalize',action='store_true')
    parser.add_argument('--verify-only',action='store_true')
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args()
    if args.seed:
        if args.seed<=0:parser.error('seed must be >0')
        print(save_seed(args.seed,args.output))
    elif args.finalize or args.verify_only:
        summary=aggregate(args.output,args.seeds)
        if args.finalize:
            (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(json.dumps(summary,indent=2))
    else:parser.error('use --seed N, --finalize or --verify-only')

if __name__=='__main__':main()
