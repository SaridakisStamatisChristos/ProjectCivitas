# Scientific assumptions, provenance and interpretation

**Status:** CIVITAS v0.1 is a synthetic research instrument, not a calibrated model of any actual country.

- **Discrete-time agent interaction:** methodological inspiration from agent-based computational economics, Sugarscape and complex adaptive systems. Specific equations here are CIVITAS simplifications, not direct reproductions of those models.
- **Labor allocation:** fixed skills, one job/period, sequential matching, fixed posted wages and firm cash limits. Original v0.1 design; no labor bargaining, worker welfare, educational dynamics, gender/age demographics, or equilibrium guarantee.
- **Household formation:** deterministic groups of up to four agents; shared cash accounts. Original simplification. Household consumption is one abstract bundle per sector, independent of household size; v0.1 does **not** model individual nutrition.
- **Markets:** posted prices, finite inventories, randomized purchase sequence and budget limits. Common agent-based modeling simplification, not Walrasian equilibrium or a verified representation of commercial markets.
- **Production:** labor skill × sector productivity × automation factor; integer floor and resource input. Original simplified production function; capital constraints beyond wage liquidity are absent.
- **Resource regeneration:** logistic rule is a standard systems-dynamics functional form; parameter magnitudes are hypothetical. Resource extinction at zero is an implication of this rule, not ecological validation.
- **Tax and redistribution:** fiscal flows have exact ledger transfers, with one proportional wage tax and transfers to lowest gross wage households. These are configurable normative institutional rules, not political labels.
- **Ownership and dividends:** each firm has a random subset of household owners and distributes a fixed fraction of positive current operating surplus; firm value and ownership wealth are not modeled.
- **Automation:** higher output per unit of labor is an imposed parametric shock. It does not represent the complete economics or engineering of AI adoption; access to additional production depends on markets, incomes, resource constraints and ownership rules.
- **Inequality:** Gini over household period gross receipts and over cash balances, respectively. Liquid wealth omits corporate equity, housing, public assets, debts and price adjustments. Neither Gini is a complete measure of societal prosperity or fairness.

## Pre-registered illustrative questions for baseline experiments

1. With everything else equal, does higher wage taxation plus redistributive transfers mechanically reduce the Gini of measured *gross receipts*? Note that transfers are included in receipts; taxes are not deducted from the reported income measure. Effects may include endogenous spending and employment shifts.
2. Does an automation efficiency shock alter labor utilization and the share of income paid as dividends, holding input resource availability constant?
3. Does a lower initial resource stock with lower regeneration rate reduce sustained physical output versus an otherwise identical market configuration?

All three hypotheses are **within-model**, not empirical social predictions. The scenarios contain large confounding in B and C if comparing after their dynamic trajectories diverge. Paired seeds provide partial control, not identical realized histories. Future sensitivity sweeps must vary production, demand, preferences, ownership concentration, tax schedules, and resource rules. External calibration requires independent observations and explicit model validation targets.
