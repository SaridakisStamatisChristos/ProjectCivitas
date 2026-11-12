# Verification and scientific validation

## Executable checks

Run `python -m pip install -e '.[test]' && pytest -q` from repo root. The tests cover deterministic fixed-seed replay; seed changes; monetary, stock and resource conservation; nonnegative cash and inventories; tax-and-transfer identity; absent agents and resources; a one-household zero-employment analytical toy; invalid scenario fields; invalid ledger transfers; 10000-agent smoke; automation shock timing; cross-scenario isolation; configuration hashes; Gini known values; and checkpoint/restoration. The CLI `run` and `resume` paths are tested with real artifacts.

`checkpoint.npz` uses a versioned, non-pickle NumPy format and includes all arrays and the NumPy bit generator state. Restoring under the same software/NumPy behavior must reproduce the remaining sequence *exactly*. The `metrics.csv` file is deliberately not included in a checkpoint; the resumed run writes its own continuation dataset and records the starting step.

## Limitations of verification

Passing conservation tests only establishes that this implementation follows these bookkeeping identities in tested conditions. It is not proof of correctness over arbitrary configurations and does not validate model realism. The reference implementation uses signed int64 arrays and has no general overflow proof at extreme values. One global resource, fixed households, limited sector count, simple price adjustments, and compressed wage models preclude precise macroeconomic inference. The difference between output and observed transactions is kept explicit.

## Model validation still open

No empirical calibration, real historical backtest, external replication, sensitivity map, Bayesian uncertainty model, mechanism identification, or independent economist review is claimed. Gini may be undefined in zero-income simulations and this is recorded as `null`. Random-event design and scheduling can change results: sensitivity to rule ordering is a future task. Runtime data are measurements from a particular execution environment, never guaranteed performance elsewhere.

## Evidence protocol

For every claim retain the exact scenario, `metadata.json`, `metrics.csv`, `journals.jsonl`, and checkpoint; record full command, environment, source revision, Python/NumPy versions, and tests. Data outputs and README claims must be updated only after execution. Use replicated experiments with multiple seeds for stochastic comparisons; descriptive mean/sample SD are **not** confidence bounds or causal estimates.

Per-transaction source/destination tracing is optional and test-covered. It is off by default; the grouped journal proves only categorized event totals, not per-account history. To retain granular audit logs, set `transaction_trace: true` in the scenario file.

## v0.2 development verification (provisional)

The original 15 tests continue passing. Additional tests independently check capital capacity, exact depreciation with flooring, goods-to-capital conversion, cash source/destination for interfirm purchases, internal conversion, accounting identities, seeded substreams, capital checkpoint replay, and v0.1 checkpoint migration. See `tests/test_capital.py`. No v0.2 full milestone or external scientific validation is claimed.
