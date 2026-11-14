# World Genesis v1 — configurable and stochastic CIVITAS initial conditions

**Status:** Experimental subsystem of `0.2.0.dev0`; historical scenarios unchanged. Not a calibrated population generator.

## Principle

A civilization begins from an explicit initial state, not a hardcoded economic outcome. World Genesis separates **sampling initial conditions** from **economic transition laws**. The latter remain transparent, deterministic given the recorded random stream and configurable simulation rules. Higher production is not assumed to be better by definition.

`civitas genesis` writes four linked artifacts: `plan.json` (sampling specification), `scenario.json` (one resolved, fully portable scenario), `initial_checkpoint.npz` (exact starting arrays and simulation RNG), and `manifest.json` (plan/config/initial-state/RNG hashes and conserved starting stocks). Replay requires no external APIs. `civitas verify-world` validates all four and regenerates the starting state. The hashes detect accidental tampering, not an adversary who rewrites and rehashes every artifact.

## Three modes

- **Configured**: fixed scenario parameters and optional fixed per-household/per-firm starting values. The pre-existing engine's seeded skill/participation/ownership draws remain in force unless explicitly overridden. No stochastic configuration draws permitted.
- **Hybrid (recommended/default for *new* worlds)**: the user fixes aggregate population, firms, institutions and initial total endowments; individual cash endowments can be drawn from lognormal weights, with **exact integer-cent total conservation**. Per-firm initial posted prices and skills can also differ. Optional starting savings are moved out of cash, not created.
- **Randomized**: in addition to the microstate rules, a named seeded generator samples *scenario-level* population, firm density, labor participation, ownership, tax and saving rates from declared ranges or finite choices, **once per world**. Those draws are frozen in `scenario.json`. Population/rule sampling is deliberately not empirically calibrated. Randomized population with fixed resource/capital quantities changes per-capita endowments unless the user normalizes them explicitly.

None of these modes dynamically randomizes economic laws mid-simulation. Existing stochastic market, hiring and consumption behavior continues to follow the already documented engine rules and seed.

## CLI quickstart

```bash
# Uses Hybrid for *new* worlds; historical scenario.json paths are unaffected.
PYTHONPATH=src python -m civitas genesis --mode hybrid --name experiment_1 --seed 42 --population 10000 --output results/world_1
PYTHONPATH=src python -m civitas verify-world --world results/world_1
PYTHONPATH=src python -m civitas run --scenario results/world_1/scenario.json --steps 24 --output results/run_1
PYTHONPATH=src python -m civitas resume --checkpoint results/world_1/initial_checkpoint.npz --steps 24 --output results/run_1_exact

# Fixed conditions from a user-edited plan; three sample plans provided.
PYTHONPATH=src python -m civitas genesis --plan scenarios/world_genesis/configured.json --output results/configured_world
PYTHONPATH=src python -m civitas genesis --plan scenarios/world_genesis/randomized.json --output results/randomized_world
```

Genesis refuses to overwrite an existing world unless `--force` is explicitly supplied. The CLI `run` and `resume` commands remain unchanged.

## Supported plan structure

```json
{
  "schema_version": 1,
  "mode": "hybrid",
  "seed": 42,
  "base_scenario": {"name": "my_world", "population": 1200, "firms_per_sector": 3},
  "scenario_draws": {},
  "initialization": {
    "household_cash_cents": {"distribution": "lognormal", "sigma": 0.7, "preserve_total": true},
    "firm_cash_cents": {"distribution": "lognormal", "sigma": 0.5, "preserve_total": true},
    "household_savings_fraction": {"distribution": "uniform", "low": 0.05, "high": 0.3},
    "price_multiplier": {"distribution": "uniform", "low": 0.95, "high": 1.05}
  }
}
```

The `base_scenario` uses the ordinary validated CIVITAS scenario schema, not a separate engine. `scenario_draws` supports whitelisted scalar fields with `fixed`, `uniform_int`, `uniform` or `choice` distributions. `initialization` supports `household_cash_cents`, `firm_cash_cents`, `firm_capital_units` (only when capital enabled), `household_savings_fraction`, `price_multiplier`, `skills`, and `participation_probability`. Each attribute uses a stable **independent named seed substream**; drawing one attribute cannot perturb another or consume the economic engine's future random stream.

Cash and capital distributions use `fixed`, `uniform_int`, or `lognormal`. For lognormal and uniform-integer endowments, `preserve_total: true` (default) redistributes the baseline total using deterministic largest-remainder integer allocation. This preserves starting **aggregate** household or firm cash exactly, including each cent; it does not preserve individual holdings. For `fixed`, `preserve_total` defaults **false**, allowing a precise user-set amount per account. If `preserve_total: false` with lognormal, the scenario per-account endowment is the approximate mean; sampled totals must still fit int64. The starting savings fraction transfers existing household cash into savings; it issues no currency. Prices and skills use fixed or bounded uniform distributions. Participation probabilities are sampled using an independent substream.

The initial ownership generator is unchanged: ownership concentration depends on the resolved `ownership_fraction` and seed, and is not yet an arbitrary ownership graph. There is no initial debt distribution or arbitrary initial inventory injection in v1, because those require separate balanced, auditable asset/liability and production histories. Existing simulations and old checkpoint formats remain supported.

## Accounting and scientific limits

- Integer-cent cash conservation: `initial_total_money = sum(household_cash) + sum(household_savings) + sum(firm_cash) + government_cash`.
- Initial physical capital equals the exact generated sum across firms; historical cost basis (when enabled) is reconciled using the configured input sector's initial reference unit price.
- Generated starting resource stock and monetary endowments are recorded; finite limits and normal scenario validation apply.
- `state_fingerprint` hashes the initial arrays and firm owners; the manifest separately hashes the scenario and RNG state. The checkpoint, not a mutable global seed, is the authoritative state snapshot.
- Distribution choices, random seeds and global economic assumptions remain experiment design choices. This is **not** evidence that simulated wealth, behaviors, policies, crises or inequalities are realistic.
- Python/NumPy versions should be recorded with research runs for scientific re-execution; sampling streams are deterministic in the verified environment, but bit-for-bit cross-version stability is not a general guarantee.
- Initial validation is not a comprehensive proof that all future extreme-value trajectories avoid integer overflow.

## Verification

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q
PYTHONPATH=src python -m civitas verify-world --world results/world_1
```

Tests cover legacy parity, determinism, independent substreams, exact total endowments, custom fixed endowments, starting savings, capital basis, zero population, checkpoint replay, malformed plans, forbidden sampling, and corrupted archive fingerprints.
