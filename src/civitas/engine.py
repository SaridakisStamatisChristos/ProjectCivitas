"""Discrete-time sequential economy; explicit order and conserved transactions.

Order each period: regenerate -> automation -> hire/pay wages -> produce ->
collect wage tax -> redistribute -> consume -> pay dividends -> reprice -> audit.
Markets are posted-price, budget constrained, with finite stock and rationing.
No borrowing, issuance, credit, mortality, reproduction or depreciation in v0.1.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Any
import numpy as np

from civitas.model import Scenario
from civitas.state import State


@dataclass
class Period:
    metrics: dict[str, Any]
    journal: dict[str, dict[str, int]]
    transactions: list[dict]


class Simulation:
    def __init__(self, scenario: Scenario, *, state: State | None = None,
                 rng_state: dict | None = None):
        scenario.validate()
        self.scenario = scenario
        self.rng = np.random.default_rng(scenario.seed)
        self.state = state if state is not None else self._initialize()
        if rng_state is not None:
            self.rng.bit_generator.state = rng_state
        self.state.trace_enabled = scenario.transaction_trace
        self.state.validate()

    def _initialize(self) -> State:
        c = self.scenario
        n = c.population
        h = (n + c.household_size - 1) // c.household_size
        ns = len(c.sectors)
        nf = ns * c.firms_per_sector
        owners: list[np.ndarray] = []
        # In capital-mode experiments, ownership sampling has its own RNG
        # substream. Changing ownership concentration then does NOT silently
        # change agent skills, participation or subsequent market random draws.
        # Capital-disabled v0.1 retains its original RNG consumption order.
        owner_rng = (np.random.default_rng(np.random.SeedSequence([c.seed, 918273]))
                     if c.capital_enabled else self.rng)
        for _ in range(nf):
            k = min(h, max(1, round(h * c.ownership_fraction))) if h else 0
            owners.append(np.sort(owner_rng.choice(h, k, replace=False)).astype(np.int64))
        hh = np.full(h, c.initial_household_cash_cents, dtype=np.int64)
        ff = np.full(nf, c.initial_firm_cash_cents, dtype=np.int64)
        state = State(
            step=0,
            household_of_agent=np.arange(n, dtype=np.int64) // c.household_size,
            participation=self.rng.random(n) < c.labor_participation,
            skills=self.rng.uniform(0.75, 1.25, size=(n, ns)).astype(np.float64),
            household_cash=hh, firm_cash=ff, gov_cash=0,
            firm_capital=np.full(nf, c.initial_capital_units_per_firm if c.capital_enabled else 0, dtype=np.int64),
            initial_capital_total=nf * (c.initial_capital_units_per_firm if c.capital_enabled else 0),
            inventory=np.zeros(nf, dtype=np.int64),
            prices=np.array([sector.price_cents for sector in c.sectors for _ in range(c.firms_per_sector)], dtype=np.int64),
            resource=c.initial_resource,
            initial_total_money=int(hh.sum()) + int(ff.sum()),
            initial_resource=c.initial_resource,
            firm_owner_households=tuple(owners),
            last_sales=np.zeros(nf, dtype=np.int64),
            last_unmet=np.zeros(ns, dtype=np.int64),
            last_employment=np.full(n, -1, dtype=np.int32),
            cumulative_output=np.zeros(ns, dtype=np.int64),
            cumulative_consumption=np.zeros(ns, dtype=np.int64),
            cumulative_capital_goods_converted=np.zeros(ns, dtype=np.int64),
        )
        return state

    @property
    def automation(self) -> float:
        c = self.scenario
        extra = (c.automation_shock_increase if c.automation_shock_step is not None
                 and self.state.step >= c.automation_shock_step else 0.0)
        return c.automation_base + extra

    def step(self) -> Period:
        s = self.state
        c = self.scenario
        ns = len(c.sectors)
        nfirm_sector = c.firms_per_sector
        nf = ns * nfirm_sector
        H = len(s.household_cash)
        s.journal = {}
        s.transaction_events = []
        wages = np.zeros(H, dtype=np.int64)
        household_income = np.zeros(H, dtype=np.int64)
        household_taxes = np.zeros(H, dtype=np.int64)
        household_transfers = np.zeros(H, dtype=np.int64)
        household_dividends = np.zeros(H, dtype=np.int64)
        sale_revenues = np.zeros(nf, dtype=np.int64)
        firm_wages = np.zeros(nf, dtype=np.int64)
        production = np.zeros(nf, dtype=np.int64)
        sold = np.zeros(nf, dtype=np.int64)
        stock_unmet = np.zeros(ns, dtype=np.int64)
        budget_unmet = np.zeros(ns, dtype=np.int64)
        automation = self.automation
        # Capital depreciates before production; fractional small-unit losses
        # round down independently each period (declared coarse model rule).
        capital_depreciated = 0
        if c.capital_enabled:
            losses = np.floor(s.firm_capital.astype(np.float64) * c.capital_depreciation_rate).astype(np.int64)
            s.firm_capital -= losses
            capital_depreciated = int(losses.sum())
            s.cumulative_capital_depreciated += capital_depreciated
        # Logistic restoration. Depleted stock of zero is an absorbing state.
        if c.resource_capacity:
            regenerated = min(c.resource_capacity - s.resource,
                              math.floor(c.regeneration_rate * s.resource * (1 - s.resource / c.resource_capacity)))
        else:
            regenerated = 0
        s.resource += regenerated
        s.cumulative_resource_regenerated += regenerated

        # Hiring is explicitly sequential, rotating the firm priority each step.
        # No agent can be hired twice.  Firm cash limits wage offers.
        s.last_employment.fill(-1)
        candidate = s.participation.copy()
        desired_output = np.zeros(nf, dtype=np.int64)
        labor_potential = np.zeros(nf, dtype=np.int64)
        for offset in range(nf):
            f = (s.step + offset) % nf
            sec = f // nfirm_sector
            sector = c.sectors[sec]
            expected = (H * sector.demand_probability / nfirm_sector if s.step == 0 else
                        max(H * sector.demand_probability * 0.25 / nfirm_sector,
                            int(s.last_sales[f]) + int(s.last_unmet[sec]) / nfirm_sector))
            target = math.ceil(expected * (1 + c.output_inventory_buffer))
            need = max(0, target - int(s.inventory[f]))
            desired_output[f] = need
            if c.capital_enabled:
                need = min(need, int(s.firm_capital[f]) * c.capital_output_per_unit)
            if not need:
                continue
            expected_units_per_worker = sector.productivity * (1 + automation)
            worker_count = min(int(candidate.sum()),
                               math.ceil(need / expected_units_per_worker),
                               int(s.firm_cash[f]) // sector.wage_cents if sector.wage_cents else int(candidate.sum()))
            if worker_count <= 0:
                continue
            available = np.flatnonzero(candidate)
            ranked = available[np.argsort(-s.skills[available, sec], kind="stable")]
            selected = ranked[:worker_count]
            candidate[selected] = False
            s.last_employment[selected] = f
            if sector.wage_cents:
                indices, counts = np.unique(s.household_of_agent[selected], return_counts=True)
                for hh, count in zip(indices, counts):
                    amount = int(count) * sector.wage_cents
                    s.transfer("firm", f, "household", int(hh), amount, "wages")
                    wages[hh] += amount
                    household_income[hh] += amount
                    firm_wages[f] += amount
            # Productivity depends on actual hired workers' heterogeneous skills.
            labor_potential[f] = min(need, math.floor(float(s.skills[selected, sec].sum()) * expected_units_per_worker))

        # Resource scarcity: proportional preliminary shares, followed by stable
        # rotating residual allocation. No firm can extract more than exists.
        resource_cost = np.array([q.resource_per_unit for q in c.sectors for _ in range(nfirm_sector)], dtype=np.int64)
        requested = int(np.dot(labor_potential, resource_cost))
        if requested <= s.resource:
            production[:] = labor_potential
        elif requested > 0:
            ratio = s.resource / requested
            production[:] = np.floor(labor_potential * ratio).astype(np.int64)
            remaining = s.resource - int(np.dot(production, resource_cost))
            while remaining > 0:
                changed = False
                for j in range(nf):
                    f = (s.step + j) % nf
                    if production[f] < labor_potential[f] and remaining >= resource_cost[f]:
                        production[f] += 1
                        remaining -= int(resource_cost[f])
                        changed = True
                if not changed:
                    break
        used_resource = int(np.dot(production, resource_cost))
        s.resource -= used_resource
        s.cumulative_resource_extracted += used_resource
        s.inventory += production
        for k in range(ns):
            s.cumulative_output[k] += int(production[k * nfirm_sector:(k + 1) * nfirm_sector].sum())

        # Labor-income taxes follow payroll. Government starts with zero money.
        tax_revenue = 0
        for h in np.flatnonzero(wages):
            tax = math.floor(int(wages[h]) * c.tax_rate)
            if tax:
                s.transfer("household", int(h), "government", 0, tax, "wage_tax")
                tax_revenue += tax
                household_taxes[h] += tax
        transfer_spending = 0
        if H and tax_revenue:
            budget = math.floor(tax_revenue * c.redistribution_share)
            eligible = max(1, math.ceil(H * c.transfer_recipient_fraction))
            # Bottom ranked households by gross wage, stable household-ID tie-break.
            recipients = np.argsort(wages, kind="stable")[:eligible]
            base, remainder = divmod(budget, eligible)
            for j, h in enumerate(recipients):
                amount = base + (1 if j < remainder else 0)
                if amount:
                    s.transfer("government", 0, "household", int(h), amount, "transfer")
                    transfer_spending += amount
                    household_income[h] += amount
                    household_transfers[h] += amount

        # Period draws are fixed-shape for every sector, independent of stock.
        # Unaffordable attempted demands are NOT counted as stock shortages.
        for k, sector in enumerate(c.sectors):
            would_buy = self.rng.random(H) < sector.demand_probability
            prefers_cheapest = self.rng.random(H) < c.buyer_cheapest_probability
            order = self.rng.permutation(H)
            ids = list(range(k * nfirm_sector, (k + 1) * nfirm_sector))
            by_price = sorted(ids, key=lambda f: (int(s.prices[f]), (f + s.step) % nf))
            for h in order:
                if not would_buy[h]:
                    continue
                if all(int(s.prices[f]) > int(s.household_cash[h]) for f in ids):
                    budget_unmet[k] += 1
                    continue
                favorite = ids[(int(h) + s.step) % nfirm_sector]
                candidates = by_price if prefers_cheapest[h] else [favorite] + [f for f in by_price if f != favorite]
                bought = False
                for f in candidates:
                    price = int(s.prices[f])
                    if s.inventory[f] and s.household_cash[h] >= price:
                        s.transfer("household", int(h), "firm", f, price, "sale")
                        s.inventory[f] -= 1
                        sold[f] += 1
                        sale_revenues[f] += price
                        bought = True
                        break
                if not bought:
                    if any(int(s.inventory[f]) and int(s.prices[f]) <= int(s.household_cash[h]) for f in ids):
                        raise AssertionError("affordable inventory failed to clear")
                    if any(int(s.prices[f]) <= int(s.household_cash[h]) for f in ids):
                        stock_unmet[k] += 1
                    else:
                        budget_unmet[k] += 1
            s.cumulative_consumption[k] += int(sold[ids].sum())
        # Investment is physical conversion of already-produced goods into capital.
        # Monetary purchases are firm-to-firm transfers; own-firm conversion
        # requires a goods stock but never fabricates a cash movement.
        capital_added = 0
        capital_purchases = 0
        investment_imputed_value = 0
        if c.capital_enabled and c.capital_investment_budget_share > 0:
            capital_sec = next(i for i, sector in enumerate(c.sectors)
                               if sector.name == c.capital_input_sector)
            suppliers = list(range(capital_sec * nfirm_sector, (capital_sec + 1) * nfirm_sector))
            suppliers.sort(key=lambda f: (int(s.prices[f]), f))
            for offset in range(nf):
                f = (s.step + offset) % nf
                target = math.ceil(int(desired_output[f]) * (1 + c.capital_target_buffer)
                                   / c.capital_output_per_unit)
                need = max(0, target - int(s.firm_capital[f]))
                budget = math.floor(int(s.firm_cash[f]) * c.capital_investment_budget_share)
                for supplier in suppliers:
                    if not need or budget <= 0:
                        break
                    price = int(s.prices[supplier])
                    units = min(need, int(s.inventory[supplier]), budget // price)
                    if units <= 0:
                        continue
                    value = units * price
                    if supplier != f:
                        s.transfer("firm", f, "firm", supplier, value, "capital_purchase")
                        capital_purchases += value
                    # When supplier == f, this is a documented internal inventory
                    # conversion; its valuation is imputed, not a transfer.
                    s.inventory[supplier] -= units
                    s.firm_capital[f] += units
                    s.cumulative_capital_goods_converted[capital_sec] += units
                    s.cumulative_capital_added += units
                    capital_added += units
                    investment_imputed_value += value
                    need -= units
                    budget -= value

        # Fraction of current positive operating surplus paid to assigned owners.
        dividends = 0
        for f in range(nf):
            profit = int(sale_revenues[f] - firm_wages[f])
            distributed = min(int(s.firm_cash[f]), math.floor(max(0, profit) * c.dividend_share))
            owners = s.firm_owner_households[f]
            if distributed and len(owners):
                base, remainder = divmod(distributed, len(owners))
                for j, h in enumerate(owners):
                    amount = base + (1 if j < remainder else 0)
                    if amount:
                        s.transfer("firm", f, "household", int(h), amount, "dividend")
                        household_income[h] += amount
                        household_dividends[h] += amount
                        dividends += amount

        # Posted-price adjustment: shortage raises prices, excess stock lowers.
        old_prices = s.prices.copy()
        for f in range(nf):
            sector = c.sectors[f // nfirm_sector]
            if s.inventory[f] == 0 and sold[f] > 0:
                s.prices[f] = max(c.price_floor_cents, math.ceil(s.prices[f] * (1 + c.price_adjustment)))
            elif s.inventory[f] > max(2, math.ceil(H * sector.demand_probability * 0.25 / nfirm_sector)):
                s.prices[f] = max(c.price_floor_cents, math.floor(s.prices[f] * (1 - c.price_adjustment)))
        s.last_sales[:] = sold
        s.last_unmet[:] = stock_unmet
        s.step += 1
        s.validate(expected_resources=(s.initial_resource + s.cumulative_resource_regenerated - s.cumulative_resource_extracted))
        expected_stock = (s.cumulative_output - s.cumulative_consumption -
                          s.cumulative_capital_goods_converted)
        observed_stock = np.array([int(s.inventory[k * nfirm_sector:(k+1)*nfirm_sector].sum()) for k in range(ns)])
        if not np.array_equal(expected_stock, observed_stock):
            raise AssertionError("physical product identity violated")

        from civitas.metrics import gini, household_equity_values
        disposable_income = wages - household_taxes + household_transfers + household_dividends
        if np.any(disposable_income < 0):
            raise AssertionError("negative household disposable income")
        if int(disposable_income.sum()) != (int(wages.sum()) - tax_revenue +
                                            transfer_spending + dividends):
            raise AssertionError("household income flow identity violated")
        equity = household_equity_values(s, c)
        modeled_net_worth = s.household_cash + equity
        employee_count = int((s.last_employment >= 0).sum())
        workforce_count = int(s.participation.sum())
        total_sales = int(sold.sum())
        transaction_price = (float(np.dot(sold, old_prices)) / total_sales if total_sales else None)
        metrics = {
            "step": s.step, "population": c.population, "households": H,
            "labor_force": workforce_count, "labor_participation_rate": (workforce_count / c.population if c.population else None),
            "employed": employee_count, "employment_rate": (employee_count / workforce_count if workforce_count else None),
            "production_units": int(production.sum()), "consumption_units": total_sales,
            "production_by_sector": {q.name: int(production[i*nfirm_sector:(i+1)*nfirm_sector].sum()) for i,q in enumerate(c.sectors)},
            "consumption_by_sector": {q.name: int(sold[i*nfirm_sector:(i+1)*nfirm_sector].sum()) for i,q in enumerate(c.sectors)},
            "quoted_price_mean_cents": (float(np.mean(s.prices)) if nf else None),
            "transaction_weighted_price_cents": transaction_price,
            "mean_household_income_cents": (float(household_income.mean()) if H else None),
            "income_gini": gini(household_income),
            "mean_household_disposable_income_cents": (float(disposable_income.mean()) if H else None),
            "disposable_income_gini": gini(disposable_income),
            "disposable_income_total_cents": int(disposable_income.sum()),
            "household_gross_wages_cents": int(wages.sum()),
            "household_income_tax_cents": int(household_taxes.sum()),
            "household_transfer_income_cents": int(household_transfers.sum()),
            "household_dividend_income_cents": int(household_dividends.sum()),
            "mean_household_modeled_net_worth_cents": (float(modeled_net_worth.mean()) if H else None),
            "modeled_net_worth_gini": gini(modeled_net_worth),
            "equity_asset_value_cents": int(equity.sum()),
            "mean_household_liquid_wealth_cents": (float(s.household_cash.mean()) if H else None),
            "liquid_wealth_gini": gini(s.household_cash),
            "government_tax_revenue_cents": tax_revenue,
            "government_transfer_cents": transfer_spending,
            "government_balance_cents": s.gov_cash,
            "wages_cents": int(firm_wages.sum()), "dividends_cents": dividends,
            "sales_cents": int(sale_revenues.sum()),
            "resource_stock": s.resource, "resource_extracted": used_resource,
            "resource_regenerated": regenerated,
            "automation_adoption": automation,
            "capital_stock_units": int(s.firm_capital.sum()),
            "capital_added_units": capital_added,
            "capital_depreciated_units": capital_depreciated,
            "capital_investment_goods_value_cents": investment_imputed_value,
            "capital_interfirm_purchases_cents": capital_purchases,
            "capital_discrepancy_units": (s.initial_capital_total + s.cumulative_capital_added -
                                          s.cumulative_capital_depreciated - int(s.firm_capital.sum())),
            "unmet_stock_demand_units": int(stock_unmet.sum()),
            "unmet_budget_demand_units": int(budget_unmet.sum()),
            "total_money_cents": s.total_money(),
            "money_discrepancy_cents": s.total_money() - s.initial_total_money,
            "resource_discrepancy_units": s.initial_resource + s.cumulative_resource_regenerated - s.cumulative_resource_extracted - s.resource,
            "goods_discrepancy_units": int(np.abs(expected_stock - observed_stock).sum()),
        }
        return Period(metrics, {key: dict(value) for key, value in s.journal.items()},
                      list(s.transaction_events))

    def run(self, steps: int | None = None) -> list[Period]:
        count = self.scenario.steps if steps is None else steps
        if type(count) is not int or count < 0:
            raise ValueError("steps must be nonnegative integer")
        return [self.step() for _ in range(count)]
