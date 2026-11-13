# CIVITAS v0.2 — Historical-cost accounting intervention

**Executed:** 2026-11-13. **Environment:** Python 3.13.5 / NumPy 2.3.5, Linux x86_64. **Design:** 10,000 agents, 24 periods, seeds 1–8, paired legacy profit proxy versus opt-in historical-cost dividend base. **16 simulations and 384 audited periods.** Full period-level records and deterministic runner are preserved in `research/v02_cost_basis_10000_8/` and `research/run_cost_basis_comparison.py`.

At each seed, the same agent skills, employment participation, owners, firm cash, initial physical capital, household money, and common initial RNG state were used in both arms. The historical-cost arm additionally initializes a zero finished-goods book basis and an imputed initial physical-capital basis at the declared input-sector posted price. The cost-tracking and book-equity accounting are deterministic and do not consume random draws.

## Final-period sample means

| Observable | Legacy proxy dividends | Historical-cost earnings dividends |
|---|---:|---:|
| Production units | 1,950.50 | 1,926.13 |
| Consumption units | 1,838.38 | 1,836.13 |
| Dividends paid, cents | 1,191,204.63 | 1,154,068.25 |
| Physical capital stock, units | 1,563.00 | 1,585.50 |
| Legacy profit proxy, cents | 1,617,071.75 | 1,610,538.75 |

The cost-basis arm produced 24.38 fewer final-period units on average. The divergence is **not an accounting-neutral effect**: the two modes deliberately use *different rules for deciding dividends* (old surplus proxy versus cost-basis earnings). Changes in household purchasing power feed back into production and capital investment. We must not interpret this contrast as evidence that an accounting practice is economically better or worse.

Across all cost-enabled periods the model verified each firm's defined identity `Δ(cash + inventory_basis + capital_basis) = historical_cost_earnings − dividends`; all checked monetary, physical resource, finished-goods, capital, household cash-flow, and firm cash-flow discrepancies were zero. Earlier 96 reference period records in the **disabled** cost mode matched the saved baseline byte-for-byte, demonstrating behavioral compatibility in that tested control.

## Boundaries and incomplete work

- Historical inventory costs include paid manufacturing labor only. There is no explicit priced raw-material purchase, general overhead, debt, interest, income taxes on firms, verified capital acquisition cost before the synthetic initial conditions, or comprehensive general ledger.
- Pooled moving-average integer costing is a **declared modeling choice**, not a universal valuation rule.
- Household-owned firm equity remains separately marked using a posted-price model; do not confuse this value with firm historical-cost book equity.
- Initial v3 checkpoints containing historical-cost-less inventories are not silently upgraded into accounting-enabled v4 histories.
- An attempted 30-seed combined run was interrupted by the execution limit **before producing a completed dataset**. Only the verified eight-seed experiment is included here. The missing 22 seeds are not claimed as executed.
- No real-world economic calibration, independent replication, or long-run convergence conclusion.

## Reproduction

```bash
PYTHONPATH=src:. python research/run_cost_basis_comparison.py --population 10000 --seeds 8 --steps 24 --output results/cost_basis_10000
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -q
```
