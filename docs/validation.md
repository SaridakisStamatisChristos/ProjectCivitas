# Verification and scientific validation

## Executable checks

Run `python -m pip install -e '.[test]' && pytest -q` from repo root. The tests cover deterministic fixed-seed replay; seed changes; monetary, stock and resource conservation; nonnegative cash and inventories; tax-and-transfer identity; absent agents and resources; a one-household zero-employment analytical toy; invalid scenario fields; invalid ledger transfers; 10000-agent smoke; automation shock timing; cross-scenario isolation; configuration hashes; Gini known values; and checkpoint/restoration. The CLI `run` and `resume` paths are tested with real artifacts.

`checkpoint.npz` uses a versioned, non-pickle NumPy format and includes all arrays and the NumPy bit generator state. Restoring under the same software/NumPy behavior must reproduce the remaining sequence *exactly*. The `metrics.csv` file is deliberately not included in a checkpoint; the resumed run writes its own continuation dataset and records the starting step.

## Limitations of verification

Passing conservation tests only establishes that this implementation follows these bookkeeping identities in tested conditions. It is not proof of correctness over arbitrary configurations and does not validate model realism. The reference implementation uses signed int64 arrays and has no general overflow proof at extreme values. One global resource, fixed households, limited sector count, simple price adjustments, and compressed wage models preclude precise macroeconomic inference. The difference between output and observed transactions is kept explicit.

## Model validation still open

No empirical calibration, real historical backtest, external replication, comprehensive sensitivity map, Bayesian uncertainty model, mechanism identification, or independent economist review is claimed. A restricted 2×3 savings/ownership factorial exists, but it does not establish model validity. Gini may be undefined in zero-income simulations and this is recorded as `null`. Random-event design and scheduling can change results: sensitivity to rule ordering is a future task. Runtime data are measurements from a particular execution environment, never guaranteed performance elsewhere.

## Evidence protocol

For every claim retain the exact scenario, `metadata.json`, `metrics.csv`, `journals.jsonl`, and checkpoint; record full command, environment, source revision, Python/NumPy versions, and tests. Data outputs and README claims must be updated only after execution. Use replicated experiments with multiple seeds for stochastic comparisons; descriptive mean/sample SD are **not** confidence bounds or causal estimates.

Per-transaction source/destination tracing is optional and test-covered. It is off by default; the grouped journal proves only categorized event totals, not per-account history. To retain granular audit logs, set `transaction_trace: true` in the scenario file.

## v0.2 development verification (provisional)

The original 15 tests continue passing. Additional tests independently check capital capacity, exact depreciation with flooring, goods-to-capital conversion, cash source/destination for interfirm purchases, internal conversion, accounting identities, seeded substreams, capital checkpoint replay, and v0.1 checkpoint migration. See `tests/test_capital.py`. No v0.2 full milestone or external scientific validation is claimed.

## Continued v0.2 development verification (savings and operating flows)

The extended suite checks deterministic v3 checkpoint replay, format-1/format-2 migrations, exact analytical savings deposit/withdrawal toy economies, reserve account zero-sum transfers, nonnegative balances, strict account-ID validation, owner-independent agent initial state, firm capital receipts and a profit proxy consistent with individual cash-flow identities. An actual previous-generation format-2 checkpoint was also successfully loaded and advanced, rather than relying only on fabricated historical data. Existing original v0.1 scenarios were compared directly with the original v0.2-capital source across 12 periods: every preexisting metric was identical for all four legacy scenarios.

The 2×3 factorial experiments executed 30 matched seeds at both 1,000 and 10,000 agents, all with zero money, goods, physical capital, firm flow and household flow discrepancies in the tested runs. The recorded CSV and paired normal-approximation seed intervals are research artifacts, **not proofs of any economic or political claim**. The initial 1,000-agent and 10,000-agent factorials are not normalized to equal per-capita firm money, firm count, capital or physical resource stocks. Exact commands and limitations are in `research/v02_savings_ownership_experiment.md`.

## v0.2 normalization / adversarial scale testing (13 November 2026)

`test_normalization.py` independently checks exactly scaled initial endowments using rational numbers, rejects infeasible integer ratios and verifies normalized deterministic replay with saved checkpoints. `test_randomized_invariants.py` checks 72 deterministic pseudorandom small scenarios involving zero population, taxation, investment, savings, shocks, resource exhaustion and checkpoint continuation. This is **bounded falsification**, not an exhaustive proof of numerical or economic correctness. The full test suite contains 45 passing cases in the recorded local run.

`research/v02_population_normalization_experiment.md` describes 360 normalized 24-period simulations plus a separate 600-run disjoint-market control. Both reject nonzero stock and cash-flow discrepancies on every period; all per-period CSV data and experiment metadata are preserved in `research/v02_population_normalized_*/` and `research/v02_market_partition_30/`. The normalization campaign found strong scale/market-topology sensitivity, so its measured savings effects are **not robust to market integration**. This falsifies broad interpretations of earlier uncalibrated model outputs. It does not establish a causal real-world effect of market size or market organization.

Initial signed-int64 state sums and transfer destination credits are now explicitly guarded. Large intermediate arithmetic in production and price metrics and extreme multistep regimes still lack a general overflow proof.

## Latest matched-access research gate

The matched-market runner uses a copy of the exact same initial full simulation state and RNG for four access rules for every seed. A SHA-256 attestation records initial state, owners and RNG. All four treatments must consume the same final random stream. Each period asserts six nonnegative-accounting/stock identities, and an atomic per-seed CSV shard is only accepted after completion. The aggregator rechecks per-shard sha256, exact scenario configuration digests, seed/arm/period coverage and duplicates. The committed aggregate period CSV is also checksummed and subject to verification. This is stronger **software-level paired counterfactual control**, not external scientific validation. The experiment remains sensitive to initial region assignment and global resource/hiring information spillovers. See `docs/v02_matched_market_access.md`.
