"""Independently recompute CIVITAS v0.2 within-model paired seed effects.

Requires only Python stdlib; normal-approximate 95% Monte Carlo intervals
quantify run-to-run seed uncertainty, NOT real-world predictive intervals.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean, stdev, NormalDist

SCENARIOS = (
    'capital_depreciation_only',
    'capital_reinvestment',
    'capital_concentrated_ownership',
)
METRICS = (
    'employment_rate', 'production_units', 'consumption_units',
    'disposable_income_gini', 'modeled_net_worth_gini',
    'capital_stock_units', 'capital_added_units',
)


def analyze(root: Path) -> dict:
    records: dict[str, dict[int, dict]] = {}
    for scenario in SCENARIOS:
        records[scenario] = {}
        for directory in sorted((root / scenario).glob('seed_*')):
            seed = int(directory.name.split('_')[-1])
            with (directory / 'metrics.csv').open(newline='', encoding='utf-8') as fd:
                rows = list(csv.DictReader(fd))
            if not rows:
                raise ValueError(f'empty run {directory}')
            for period in rows:
                for invariant in ('money_discrepancy_cents', 'resource_discrepancy_units',
                                  'goods_discrepancy_units', 'capital_discrepancy_units'):
                    if int(period[invariant]) != 0:
                        raise AssertionError(f'{directory} period {period["step"]}: {invariant}')
                if int(period['capital_stock_units']) < 0:
                    raise AssertionError('negative capital')
            if len(rows) != 24:
                raise ValueError(f'{directory} has {len(rows)} periods, expected 24')
            records[scenario][seed] = rows[-1]
    seeds = sorted(set.intersection(*(set(v) for v in records.values())))
    if not seeds or any(set(v) != set(seeds) for v in records.values()):
        raise ValueError('scenario seed sets differ: cannot perform paired comparisons')

    def val(scenario: str, seed: int, key: str) -> float:
        item = records[scenario][seed][key]
        if item in ('', 'None'):
            raise ValueError(f'undefined {key} for {scenario} seed {seed}')
        return float(item)

    tcrit = NormalDist().inv_cdf(.975)
    comparisons = {}
    for label, a, b in (
        ('reinvestment_minus_no_investment', 'capital_reinvestment', 'capital_depreciation_only'),
        ('concentration_minus_reinvestment', 'capital_concentrated_ownership', 'capital_reinvestment'),
    ):
        comparisons[label] = {}
        for key in METRICS:
            diffs = [val(a, seed, key) - val(b, seed, key) for seed in seeds]
            center = mean(diffs)
            sd = stdev(diffs) if len(diffs) > 1 else None
            halfwidth = tcrit * sd / math.sqrt(len(diffs)) if sd is not None else None
            comparisons[label][key] = {
                'mean_paired_difference': center,
                'sample_sd_of_differences': sd,
                'normal_approx_95pct_mc_interval': ([center - halfwidth, center + halfwidth]
                                                     if halfwidth is not None else None),
                'n_pairs': len(diffs),
            }
    return {
        'model_version': '0.2.0.dev0',
        'periods_per_run': 24,
        'population_per_run': 10000,
        'paired_seeds': seeds,
        'period_records_audited': sum(len(v) for v in records.values()) * 24,
        'accounting_discrepancies_found': 0,
        'confidence_interval_type': '95% normal approximation across paired stochastic model seeds',
        'confidence_interval_caveat': 'This is Monte Carlo variability for the specified artificial model only; not empirical or structural uncertainty.',
        'comparisons': comparisons,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('suite_directory', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = analyze(args.suite_directory)
    output = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding='utf-8')
    else:
        print(output)


if __name__ == '__main__':
    main()
