# CIVITAS v0.2: exact population-normalization protocol

**Status:** locally executable engineering mechanism, not an invariance theorem or an empirically validated model. The previous 1,000- versus 10,000-agent savings comparison did *not* hold firm density or aggregate cash/resources/capital per person constant.

## Reference design and exact integer normalization

For a reference scenario with population `N₀`, household size `h`, sectors `J`, `f₀` firms per sector, cash per household `c`, cash per firm `b`, physical capital per firm `k`, renewable resource stock `R₀` and capacity `K₀`, a target population `N` uses:

- `H(N) = N/h` households (requires both populations divisible by `h`);
- `f(N) = f₀ × N/N₀` firms per sector (integer only);
- `R(N) = R₀ × N/N₀` renewable stock (integer only);
- `K(N) = K₀ × N/N₀` renewable capacity (integer only);
- per-household and per-firm starting cash and per-firm physical capital stay constant.

All these requirements are exact rational arithmetic, **not** rounded floating-point comparisons. An impossible target is rejected. The reference scenario used for this campaign has `N₀=1,000`, `h=4`, `J=3`, `f₀=2`, `c=15,000` cents, `b=2,000,000` cents, `k=450` physical-capital units, `R₀=50,000` and `K₀=60,000`. The target at 10,000 agents has 20 firms/sector, 60 firms total, 2,500 households, `R=500,000`, and `K=600,000`.

The resulting *initial* invariants per person are:

| Variable | Both populations |
|---|---:|
| Firms per person | 0.006 |
| Household starting cash per person | 3,750 cents |
| Firm starting cash per person | 12,000 cents |
| Total starting cash per person | 15,750 cents |
| Resource stock per person | 50 units |
| Renewable capacity per person | 60 units |
| Firm physical capital per person | 2.7 units |

`scale_population_exact()` in `src/civitas/normalization.py` enforces these six invariants and produces a record through `audit_initial_endowments()`. The 12 explicit scenario files in `scenarios/population_normalized/` make the design inspectable without executing configuration-generation code.

## What this does *not* normalize

The number of households participating in ownership is chosen by rounding `H × ownership_fraction` to a whole number (minimum one). At 3% nominal ownership, 250 households yield 8 owner-households per firm (**3.2% actual**), whereas 2,500 households yield 75 (**3% actual**). This difference is explicitly reported in `InitialEndowmentAudit.realized_ownership_fraction_per_firm`; **do not** claim the 3% population comparison is perfectly matched in ownership density.

Logistic resource regeneration is floored to an integer at each step, so per-capita regeneration is not mathematically identical at different sizes. Firm competition, finite sample variation, firm-level transactions, hiring order, minimum thresholds, random numbers, integer wages, rationing order, posted-price adjustment and capital-good availability are not scale-invariant. The purpose of this campaign is to test sensitivity, *not* to assume the normalization makes the full equations scale-independent.

Initial seeded agent attributes are freshly generated at each population size; a seed of 7 does **not** represent a one-to-one pairing of all inhabitants in a 1,000- and a 10,000-person world. Paired-seed confidence intervals measure Monte Carlo variation under this implementation and no other uncertainty.

## Reproducibility

```bash
python -m pip install -e '.[test]'
pytest -q
PYTHONPATH=src python research/run_population_normalized.py --population 1000 --seeds 30 --steps 24
PYTHONPATH=src python research/run_population_normalized.py --population 10000 --seeds 30 --steps 24
```

The runner validates six within-run conservation/flow identities on **every period**, retains all period rows, scenario JSON, exact initial-endowment audits, 30 seed-level final-period summary statistics and within-population paired-seed comparisons. `research/v02_population_normalization_experiment.md` records execution evidence and limitations.

## Signed int64 boundaries

The scenario validator now rejects initial money, physical capital and resource stocks that exceed signed 64-bit integer storage. The atomic account transfer rejects a credit that would overflow its destination **before** debiting the source. These guards cover *initial conditions and individual transfer destinations*, not all possible large-number arithmetic in 24-period production, revenue and stock aggregation. An exhaustive signed-int64 overflow proof remains an explicit v0.2 release gate.
