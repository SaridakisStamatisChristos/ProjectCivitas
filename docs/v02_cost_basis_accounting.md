# CIVITAS v0.2 experimental historical-cost inventory and capital books

**Status:** implemented and tested as **opt-in** model (`cost_basis_accounting_enabled: true`) on the development branch. It is a simplified **historical-cost ledger**, **not** GAAP/IFRS accounting or externally calibrated economics. The stable scenarios default to `false` and preserve their v0.1/v0.2-legacy simulation decisions and cash flows exactly.

## 1. Basis model

For each firm `f` store (i) physical finished goods `I_f` and their integer-cent carrying basis `V_f`, (ii) physical productive capital `K_f` and its integer-cent carrying basis `B_f`, and (iii) cash `C_f`. These are three distinct stocks. No financing liabilities, bank deposits, interest, revaluation, sale of equity, or tax on profits are represented.

New inventory and capital basis arrays reside in `State`. A firm's initial physical capital is assigned an **imputed acquisition basis** equal to initial capital units multiplied by the initial posted price of the selected capital-input sector. That is an explicit initialization assumption, not evidence of actual historical expenditure. Initial finished-goods inventory and its basis are both zero.

## 2. Integer arithmetic and unit-cost withdrawal

When a firm owns `Q>0` units with historical cost `V` cents and withdraws `q` units (`0 ≤ q ≤ Q`), the removed basis is

`cost(Q,V,q) = V` if `q = Q`, otherwise `floor(V × q / Q)`.

For `Q = q = V = 0`, this is zero. Invalid withdrawals or nonzero cost on zero inventory raise an exception. This **pooled moving-average accounting rule** assigns all residual rounding cents when the last unit leaves. The same function governs goods COGS, goods converted into capital, and depreciation by physical capital units. Computations use Python integer intermediates; cost-basis assignments reject signed-int64 overflow.

Wages are paid at hiring. When finished goods are produced in the period, **all associated direct labor costs** are capitalized into inventory basis. If a firm pays wages but produces zero units, those wages are immediately charged as a period expense (no fictitious inventory asset). No other inputs are capitalized: extracted natural resources have no separate historical purchase cost in the current model. This is an important limitation.

## 3. Consumer sales, investment, depreciation

- On a household purchase, the seller receives the actual posted-price cash and removes **one unit** of inventory and its integer historical cost. Price less removed carrying cost contributes to realized gross earnings.
- On a cross-firm capital-goods transaction, the supplier receives the actual price in cash, derecognizes inventory and its basis, and recognizes that inventory cost in COGS. The buyer pays cash, removes no own inventory, receives productive physical capital and capitalizes **purchase price** as its acquisition basis.
- When a firm uses its own goods as capital, inventory and its historic basis move to capital without an artificial cash transaction, profit or loss.
- At the beginning of each period, the model's physical depreciation rule removes capital units. Their proportional carrying cost is charged as a **noncash book depreciation expense**.

The old posted-price depreciation estimate and cash-surplus profit proxy remain observable for comparison but are not used as the dividend basis when historical-cost accounting is enabled.

## 4. Firm balance-sheet identity

For each firm and each period, define model book equity

`E_f = C_f + V_f + B_f`.

With current household-sale revenue `R_f`, other-firm capital-goods-sale revenue `G_f`, consumer sales COGS `U_f`, sold capital-goods inventory COGS `X_f`, paid wages that produced zero output `W0_f`, physical depreciation cost `D_f`, and cash dividends `Div_f`, the **defined** synthetic earnings are

`Π_f = R_f + G_f - U_f - X_f - W0_f - D_f`.

The model asserts for **every firm**:

`E_f(t+1) - E_f(t) = Π_f - Div_f`.

Investment purchases are asset swaps, not costs deducted twice from earnings. Direct wages capitalized to unsold finished goods stay in inventory basis until sold/converted. Cash is transferred exclusively through the existing account ledger; neither a manufacturing basis entry nor depreciation creates or destroys money. When enabled, dividends are a bounded fraction of **positive historical-cost earnings**, limited by available firm cash. This is a behavioral/policy change relative to the legacy proxy, not a neutral accounting presentation change.

**Scope limitations:** no cost for natural-resource extraction, no capital maintenance purchased outside the capital-goods sector, no financing liabilities or household ownership trading, no actual share prices, no taxes on business earnings, no overhead or R&D, no losses carried forward, no distinction between FIFO and multiple product batches, no full national accounts. For that reason, these are *cost-basis earnings* and *book-equity proxy*, not comprehensive audited corporate profits or full balance sheets.

## 5. Persistence and backward compatibility

New cost-enabled runs use nonpickle **checkpoint format 4**. They persist the two historical cost arrays; the loader verifies stock and basis consistency before resuming. When cost accounting is **disabled**, the historical format-3 checkpoint remains the default and old formats 1, 2 and 3 are supported. Loading a format-3 checkpoint that claims cost accounting is enabled is **rejected**, because the missing cost history cannot be reconstructed safely. No retroactive cost values are fabricated. Random-number sequences are unchanged by cost-bookkeeping operations.

## 6. Reproduction

```bash
python -m pip install -e '.[test]'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
civitas run --scenario scenarios/cost_basis_reinvestment.json --seed 7 --steps 24 --output results/cost_basis_7
PYTHONPATH=src:. python research/run_cost_basis_comparison.py --population 10000 --seeds 8 --steps 24 --output results/cost_basis_comparison
```

Numerical experiment evidence and caveats are in `research/v02_cost_basis_experiment.md`. No empirical social-scientific validation is claimed.
