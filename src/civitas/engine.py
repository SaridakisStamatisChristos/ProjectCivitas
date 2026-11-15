"""Discrete-time sequential economy; explicit order and conserved transactions.

Order each period: regenerate -> automation -> hire/pay wages -> produce ->
collect wage tax -> redistribute -> consume -> pay dividends -> reprice -> audit.
Markets are posted-price, budget constrained, with finite stock and rationing.
No issuance, mortality or reproduction. v0.2 adds optional physical capital, savings and bilateral credit.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Any
import numpy as np

from civitas.model import Scenario
from civitas.state import State
from civitas.economy_costs import allocated_basis, checked_add_i64
from civitas.finance import CreditFlows, service_loans, available_credit, originate
from civitas.market_rules import expected_sales, updated_price


@dataclass
class Period:
    metrics: dict[str, Any]
    journal: dict[str, dict[str, int]]
    transactions: list[dict]
    # Separate trace: financial claim extinguishment is NOT a money transfer.
    noncash_transactions: list[dict] = field(default_factory=list)
    physical_transactions: list[dict] = field(default_factory=list)
    book_balance_report: dict[str, int] | None = None


class Simulation:
    def __init__(self, scenario: Scenario, *, state: State | None = None,
                 rng_state: dict | None = None):
        scenario.validate()
        self.scenario = scenario
        self.rng = np.random.default_rng(scenario.seed)
        self.state = state if state is not None else self._initialize()
        if rng_state is not None:
            self.rng.bit_generator.state = rng_state
        # Access assignments are derived from immutable IDs, not fresh RNG draws.
        # All treatment arms therefore share identical agent/firm initial states,
        # RNG consumption and ownership draws when initialized from a snapshot.
        regions = scenario.market_regions
        self.household_regions = np.arange(len(self.state.household_cash), dtype=np.int64) % regions
        if scenario.household_region_assignment == "balanced_shuffle" and regions > 1:
            # A separate, explicitly seeded substream: never consume simulation RNG.
            # Shuffling labels retains precisely the same household count in each
            # region as the historical modulo assignment.
            allocation_rng = np.random.default_rng(
                np.random.SeedSequence([scenario.seed, scenario.region_assignment_seed, 20261113]))
            allocation_rng.shuffle(self.household_regions)
        self.agent_regions = self.household_regions[self.state.household_of_agent]
        self.firm_regions = np.tile(np.arange(scenario.firms_per_sector, dtype=np.int64) % regions,
                                    len(scenario.sectors))
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
        initial_capital_basis = 0
        if c.capital_enabled and c.cost_basis_accounting_enabled:
            initial_quote = next(sec.price_cents for sec in c.sectors if sec.name == c.capital_input_sector)
            initial_capital_basis = c.initial_capital_units_per_firm * initial_quote
        state = State(
            step=0,
            household_of_agent=np.arange(n, dtype=np.int64) // c.household_size,
            participation=self.rng.random(n) < c.labor_participation,
            skills=self.rng.uniform(0.75, 1.25, size=(n, ns)).astype(np.float64),
            household_cash=hh, household_savings=np.zeros(h, dtype=np.int64), firm_cash=ff, gov_cash=0,
            firm_capital=np.full(nf, c.initial_capital_units_per_firm if c.capital_enabled else 0, dtype=np.int64),
            initial_capital_total=nf * (c.initial_capital_units_per_firm if c.capital_enabled else 0),
            inventory=np.zeros(nf, dtype=np.int64),
            firm_inventory_basis_cents=np.zeros(nf, dtype=np.int64),
            firm_capital_basis_cents=np.full(nf, initial_capital_basis, dtype=np.int64),
            household_loan_assets_cents=np.zeros(h, dtype=np.int64),
            firm_loan_liabilities_cents=np.zeros(nf, dtype=np.int64), loans=[],
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
        if c.world_genesis is not None:
            # Independent substreams preserve legacy market RNG consumption.
            from civitas.world_genesis import apply_initialization
            apply_initialization(state, c)
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
        # Capture only in opt-in trace mode; no hot-path array copies otherwise.
        if s.trace_enabled:
            from civitas.ledger_audit import capture_opening
            opening_ledger = capture_opening(s)
            from civitas.physical_audit import capture_physical_opening
            opening_physical = capture_physical_opening(s)
            from civitas.balance_sheet import capture_book_snapshot
            opening_book = capture_book_snapshot(s, c)
        ns = len(c.sectors)
        nfirm_sector = c.firms_per_sector
        nf = ns * nfirm_sector
        H = len(s.household_cash)
        s.journal = {}
        s.transaction_events = []
        s.noncash_events = []
        s.physical_events = []
        wages = np.zeros(H, dtype=np.int64)
        household_income = np.zeros(H, dtype=np.int64)
        household_taxes = np.zeros(H, dtype=np.int64)
        household_transfers = np.zeros(H, dtype=np.int64)
        household_dividends = np.zeros(H, dtype=np.int64)
        household_purchase_spending = np.zeros(H, dtype=np.int64)
        household_opening_assets = s.household_cash.copy() + s.household_savings.copy()
        household_opening_claims = s.household_loan_assets_cents.copy()
        firm_opening_cash = s.firm_cash.copy()
        firm_opening_debt = s.firm_loan_liabilities_cents.copy()
        if c.cost_basis_accounting_enabled:
            firm_opening_book_equity = (s.firm_cash.astype(object) +
                                        s.firm_inventory_basis_cents.astype(object) +
                                        s.firm_capital_basis_cents.astype(object) -
                                        s.firm_loan_liabilities_cents.astype(object))
        credit_flows = CreditFlows.empty(s)
        if c.credit_enabled:
            service_loans(s, repayment_fraction=c.credit_repayment_fraction,
                          term=c.credit_term_periods,
                          reserve_cents=c.credit_firm_cash_reserve_cents,
                          flows=credit_flows)
        firm_consumption_cogs = np.zeros(nf, dtype=np.int64)
        firm_capital_goods_cogs = np.zeros(nf, dtype=np.int64)
        firm_uncapitalized_labor_cost = np.zeros(nf, dtype=np.int64)
        firm_book_depreciation_cost = np.zeros(nf, dtype=np.int64)
        government_opening_cash = s.gov_cash
        capital_sale_revenues = np.zeros(nf, dtype=np.int64)
        capital_purchase_spending = np.zeros(nf, dtype=np.int64)
        firm_dividend_payments = np.zeros(nf, dtype=np.int64)
        capital_depreciation_losses = np.zeros(nf, dtype=np.int64)
        sale_revenues = np.zeros(nf, dtype=np.int64)
        firm_wages = np.zeros(nf, dtype=np.int64)
        firm_resource_fees = np.zeros(nf, dtype=np.int64)
        production = np.zeros(nf, dtype=np.int64)
        sold = np.zeros(nf, dtype=np.int64)
        stock_unmet = np.zeros(ns, dtype=np.int64)
        budget_unmet = np.zeros(ns, dtype=np.int64)
        # Attempts that fail despite an accessible but unquoted stocked seller.
        # This is a synthetic information-friction diagnostic, not welfare loss.
        missed_quote_opportunities = np.zeros(ns, dtype=np.int64)
        automation = self.automation
        # Capital depreciates before production; fractional small-unit losses
        # round down independently each period (declared coarse model rule).
        capital_depreciated = 0
        if c.capital_enabled:
            losses = np.floor(s.firm_capital.astype(np.float64) * c.capital_depreciation_rate).astype(np.int64)
            if c.cost_basis_accounting_enabled:
                for f in range(nf):
                    loss = int(losses[f])
                    removed = allocated_basis(stock_units=int(s.firm_capital[f]),
                                              stock_cost_cents=int(s.firm_capital_basis_cents[f]),
                                              withdrawn_units=loss)
                    s.firm_capital_basis_cents[f] -= removed
                    firm_book_depreciation_cost[f] = removed
            if s.trace_enabled:
                for f, loss in enumerate(losses):
                    if loss:
                        s.physical_events.append({"kind": "depreciate", "firm": f, "units": int(loss),
                                                  "basis_cents": int(firm_book_depreciation_cost[f])})
            s.firm_capital -= losses
            capital_depreciation_losses = losses
            capital_depreciated = int(losses.sum())
            s.cumulative_capital_depreciated += capital_depreciated
        # Logistic restoration. Depleted stock of zero is an absorbing state.
        if c.resource_capacity:
            regenerated = min(c.resource_capacity - s.resource,
                              math.floor(c.regeneration_rate * s.resource * (1 - s.resource / c.resource_capacity)))
        else:
            regenerated = 0
        if s.trace_enabled and regenerated:
            s.physical_events.append({"kind": "regenerate", "units": int(regenerated)})
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
            expected = expected_sales(
                rule=c.hiring_expectation_rule, period=s.step,
                sector_household_demand=H * sector.demand_probability / nfirm_sector,
                firm_last_sales=int(s.last_sales[f]),
                sector_last_unmet_per_firm=int(s.last_unmet[sec]) / nfirm_sector,
            )
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
            if c.restrict_labor_hiring:
                available = available[self.agent_regions[available] == self.firm_regions[f]]
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
        if c.resource_extraction_fee_cents_per_unit:
            for f in range(nf):
                fee_per_good = (int(resource_cost[f]) *
                                c.resource_extraction_fee_cents_per_unit)
                labor_potential[f] = min(int(labor_potential[f]),
                                         int(s.firm_cash[f]) // fee_per_good)
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
        if c.resource_extraction_fee_cents_per_unit:
            for f in range(nf):
                amount = (int(production[f]) * int(resource_cost[f]) *
                          c.resource_extraction_fee_cents_per_unit)
                if amount:
                    s.transfer("firm", f, "government", 0, amount, "resource_fee")
                    firm_resource_fees[f] = amount
        if c.cost_basis_accounting_enabled:
            for f in range(nf):
                if production[f] > 0:
                    s.firm_inventory_basis_cents[f] = checked_add_i64(
                        int(s.firm_inventory_basis_cents[f]),
                        int(firm_wages[f]) + int(firm_resource_fees[f]))
                else:
                    firm_uncapitalized_labor_cost[f] = firm_wages[f]
        if s.trace_enabled:
            for f, count in enumerate(production):
                if count:
                    s.physical_events.append({"kind": "manufacture", "firm": f, "units": int(count),
                                               "resource_units": int(count) * int(resource_cost[f]),
                                               "basis_cents": (int(firm_wages[f]) + int(firm_resource_fees[f])
                                                               if c.cost_basis_accounting_enabled else 0)})
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
            # Draw permutation even for deterministic order: same RNG consumption
            # across treatment arms isolates order without shifting future draws.
            randomized_order = self.rng.permutation(H)
            order = randomized_order if c.rationing_order_rule == "random" else range(H)
            sector_ids = list(range(k * nfirm_sector, (k + 1) * nfirm_sector))
            # Price lists are local only when household-to-firm access is gated.
            # The unconstrained path is unchanged from previous releases.
            market_sellers = ({r: [f for f in sector_ids if self.firm_regions[f] == r]
                               for r in range(c.market_regions)}
                              if c.restrict_household_sales else None)
            global_by_price = sorted(sector_ids, key=lambda f: (int(s.prices[f]), (f + s.step) % nf))
            regional_by_price = ({r: sorted(firms, key=lambda f: (int(s.prices[f]), (f + s.step) % nf))
                                  for r, firms in market_sellers.items()}
                                 if market_sellers is not None else None)
            for h in order:
                if not would_buy[h]:
                    continue
                if market_sellers is None:
                    ids = sector_ids
                    by_price = global_by_price
                else:
                    region = int(self.household_regions[h])
                    ids = market_sellers[region]
                    by_price = regional_by_price[region]
                # Search information is distinct from legal access: in the
                # two-quote arm, households can trade with only two observed
                # sellers per sector/period. This quote set is deterministic,
                # computed from IDs/step, and consumes no shared RNG draws.
                eligible_ids = ids
                if c.buyer_price_information == "two_quotes" and len(ids) > 2:
                    first = (int(h) * 13007 + int(s.step) * 107 + k * 29) % len(ids)
                    ids = [ids[first], ids[(first + 1) % len(ids)]]
                    by_price = sorted(ids, key=lambda f: (int(s.prices[f]), (f + s.step) % nf))
                emergency_access = (c.household_savings_rate > 0 and
                                    c.savings_emergency_food_enabled and
                                    sector.name == c.savings_essential_sector)
                purchasing_power = (int(s.household_cash[h]) +
                                    (int(s.household_savings[h]) if emergency_access else 0))
                if all(int(s.prices[f]) > purchasing_power for f in ids):
                    budget_unmet[k] += 1
                    if len(eligible_ids) > len(ids) and any(
                        int(s.inventory[f]) > 0 and int(s.prices[f]) <= purchasing_power
                        for f in eligible_ids if f not in ids
                    ):
                        missed_quote_opportunities[k] += 1
                    continue
                favorite = ids[(int(h) + s.step) % len(ids)]
                if c.buyer_seller_rule == "cheapest":
                    candidates = by_price
                elif c.buyer_seller_rule == "favorite":
                    candidates = [favorite] + [f for f in by_price if f != favorite]
                else:
                    candidates = (by_price if prefers_cheapest[h] else
                                  [favorite] + [f for f in by_price if f != favorite])
                bought = False
                for f in candidates:
                    price = int(s.prices[f])
                    if s.inventory[f] and purchasing_power >= price:
                        shortfall = max(0, price - int(s.household_cash[h]))
                        if shortfall:
                            if not emergency_access:
                                raise AssertionError("inaccessible saving funded consumer purchase")
                            s.transfer("savings", int(h), "household", int(h), shortfall, "savings_withdrawal")
                            purchasing_power = int(s.household_cash[h])
                        s.transfer("household", int(h), "firm", f, price, "sale")
                        household_purchase_spending[h] += price
                        taken = 0
                        if c.cost_basis_accounting_enabled:
                            taken = allocated_basis(stock_units=int(s.inventory[f]),
                                                    stock_cost_cents=int(s.firm_inventory_basis_cents[f]),
                                                    withdrawn_units=1)
                            s.firm_inventory_basis_cents[f] -= taken
                            firm_consumption_cogs[f] += taken
                        if s.trace_enabled:
                            s.physical_events.append({"kind": "consumer_sale", "firm": f,
                                                      "household": int(h), "units": 1,
                                                      "basis_cents": int(taken), "price_cents": price})
                        s.inventory[f] -= 1
                        sold[f] += 1
                        sale_revenues[f] += price
                        bought = True
                        break
                if not bought:
                    if len(eligible_ids) > len(ids) and any(
                        int(s.inventory[f]) > 0 and int(s.prices[f]) <= purchasing_power
                        for f in eligible_ids if f not in ids
                    ):
                        missed_quote_opportunities[k] += 1
                    if any(int(s.inventory[f]) and int(s.prices[f]) <= int(s.household_cash[h]) for f in ids):
                        raise AssertionError("affordable inventory failed to clear")
                    if any(int(s.prices[f]) <= int(s.household_cash[h]) for f in ids):
                        stock_unmet[k] += 1
                    else:
                        budget_unmet[k] += 1
            s.cumulative_consumption[k] += int(sold[sector_ids].sum())
        # Investment is physical conversion of already-produced goods into capital.
        # Monetary purchases are firm-to-firm transfers; own-firm conversion
        # requires a goods stock but never fabricates a cash movement.
        capital_added = 0
        capital_purchases = 0
        investment_imputed_value = 0
        if c.credit_enabled:
            from fractions import Fraction
            limit = Fraction(str(c.credit_lender_savings_share))
            lending_caps = np.array(
                [(int(value) * limit.numerator) // limit.denominator
                 for value in s.household_savings], dtype=np.int64)
        else:
            lending_caps = np.zeros(H, dtype=np.int64)
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
                    if not need or (budget <= 0 and not c.credit_enabled):
                        break
                    price = int(s.prices[supplier])
                    if c.credit_enabled and supplier != f:
                        # Only originate debt if a stocked, external supplier has
                        # capital goods that baseline available cash cannot buy.
                        headroom = available_credit(s, f, lending_caps,
                                                    c.credit_max_principal_per_firm_cents)
                        desired_units = min(need, int(s.inventory[supplier]),
                                            (budget + headroom) // price)
                        shortfall = max(0, desired_units * price - budget)
                        if shortfall:
                            originate(s, f, shortfall, lending_caps, credit_flows)
                            budget += shortfall
                    units = min(need, int(s.inventory[supplier]), budget // price)
                    if units <= 0:
                        continue
                    value = units * price
                    if supplier != f:
                        s.transfer("firm", f, "firm", supplier, value, "capital_purchase")
                        capital_purchases += value
                        capital_purchase_spending[f] += value
                        capital_sale_revenues[supplier] += value
                    # When supplier == f, this is a documented internal inventory
                    # conversion; its valuation is imputed, not a transfer.
                    consumed_basis = acquisition_basis = 0
                    if c.cost_basis_accounting_enabled:
                        consumed_basis = allocated_basis(stock_units=int(s.inventory[supplier]),
                                                        stock_cost_cents=int(s.firm_inventory_basis_cents[supplier]),
                                                        withdrawn_units=int(units))
                        s.firm_inventory_basis_cents[supplier] -= consumed_basis
                        if supplier != f:
                            firm_capital_goods_cogs[supplier] += consumed_basis
                        acquisition_basis = value if supplier != f else consumed_basis
                        s.firm_capital_basis_cents[f] = checked_add_i64(
                            int(s.firm_capital_basis_cents[f]), int(acquisition_basis))
                    if s.trace_enabled:
                        s.physical_events.append({"kind": "convert_capital", "supplier": int(supplier),
                                                  "buyer": int(f), "units": int(units),
                                                  "basis_cents": int(consumed_basis),
                                                  "capital_cost_cents": int(acquisition_basis),
                                                  "price_cents": int(value)})
                    s.inventory[supplier] -= units
                    s.firm_capital[f] += units
                    s.cumulative_capital_goods_converted[capital_sec] += units
                    s.cumulative_capital_added += units
                    capital_added += units
                    investment_imputed_value += value
                    need -= units
                    budget -= value

        # Capital receipts are revenues for the supplier; purchases are assets
        # for the buyer, NOT current-period operating expenses. Depreciation is
        # valued at the current posted quote; this is an accrual PROFIT PROXY,
        # not a GAAP profit or an inventory cost-of-goods-sold calculation.
        capital_quote = 0
        if c.capital_enabled:
            capital_sec_idx = next(i for i, sec in enumerate(c.sectors)
                                   if sec.name == c.capital_input_sector)
            quotes = s.prices[capital_sec_idx * nfirm_sector:(capital_sec_idx + 1) * nfirm_sector]
            capital_quote = int(quotes.min())
        depreciation_expense_cents = capital_depreciation_losses * capital_quote
        firm_operating_surplus = (sale_revenues + capital_sale_revenues -
                                  firm_wages - firm_resource_fees)
        firm_profit_proxy = firm_operating_surplus - depreciation_expense_cents
        firm_cost_basis_earnings = (sale_revenues + capital_sale_revenues -
                                    firm_consumption_cogs - firm_capital_goods_cogs -
                                    firm_uncapitalized_labor_cost - firm_book_depreciation_cost)
        dividends = 0
        for f in range(nf):
            profit = int(firm_cost_basis_earnings[f] if c.cost_basis_accounting_enabled
                         else firm_profit_proxy[f])
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
                        firm_dividend_payments[f] += amount
                        dividends += amount

        # Savings are non-interest-bearing cash, not bank deposits.
        # When enabled, a prior savings balance can fund a documented
        # bilateral capital-goods loan. A household reserves a fraction of its
        # nonnegative disposable income, bounded by its spendable cash above
        # an explicit liquidity floor. Moves are internal balance transfers.
        savings_deposits = 0
        if c.household_savings_rate:
            net_income = wages - household_taxes + household_transfers + household_dividends
            for h in range(H):
                amount = min(math.floor(int(net_income[h]) * c.household_savings_rate),
                             max(0, int(s.household_cash[h]) - c.household_liquidity_floor_cents))
                if amount > 0:
                    s.transfer("household", h, "savings", h, amount, "savings_deposit")
                    savings_deposits += amount

        # Verify each household and each firm's period cash-flow identities,
        # not merely the aggregate stock of money.
        household_expected = (household_opening_assets + wages - household_taxes +
                              household_transfers + household_dividends - household_purchase_spending -
                              credit_flows.household_principal_advanced +
                              credit_flows.household_principal_repaid)
        household_actual = s.household_cash + s.household_savings
        household_flow_discrepancy = int(np.abs(household_actual - household_expected).sum())
        if household_flow_discrepancy:
            raise AssertionError("household cash-flow reconciliation violated")
        firm_expected = (firm_opening_cash + sale_revenues + capital_sale_revenues -
                         firm_wages - firm_resource_fees - capital_purchase_spending -
                         firm_dividend_payments + credit_flows.firm_principal_advanced -
                         credit_flows.firm_principal_repaid)
        firm_flow_discrepancy = int(np.abs(s.firm_cash - firm_expected).sum())
        if firm_flow_discrepancy:
            raise AssertionError("firm cash-flow reconciliation violated")
        if s.gov_cash != (government_opening_cash + tax_revenue +
                          int(firm_resource_fees.sum()) - transfer_spending):
            raise AssertionError("government cash-flow reconciliation violated")

        firm_book_equity_discrepancy = None
        if c.cost_basis_accounting_enabled:
            closing = (s.firm_cash.astype(object) + s.firm_inventory_basis_cents.astype(object) +
                       s.firm_capital_basis_cents.astype(object) -
                       s.firm_loan_liabilities_cents.astype(object))
            expected = (firm_opening_book_equity + firm_cost_basis_earnings.astype(object) -
                        firm_dividend_payments.astype(object) +
                        credit_flows.firm_principal_defaulted.astype(object))
            firm_book_equity_discrepancy = sum(abs(int(a-b)) for a,b in zip(closing,expected))
            if firm_book_equity_discrepancy:
                raise AssertionError("firm book-equity reconciliation violated")
        # Posted-price adjustment: shortage raises prices, excess stock lowers.
        old_prices = s.prices.copy()
        for f in range(nf):
            sector = c.sectors[f // nfirm_sector]
            prospect = updated_price(
                current=int(s.prices[f]), stock=int(s.inventory[f]),
                units_sold=int(sold[f]),
                excess_threshold=max(2, math.ceil(H * sector.demand_probability * 0.25 / nfirm_sector)),
                adjustment=c.price_adjustment, floor=c.price_floor_cents,
            )
            if (c.price_update_rule == "affordability_guard" and prospect > int(s.prices[f])
                    and c.price_affordability_floor > 0):
                # Descriptive affordability proxy at the *end* of the period.
                # End-period cash has already paid for observed purchases.
                # No direct transfers or production changes occur here.
                reserve_access = (sector.name == c.savings_essential_sector and
                                  c.savings_emergency_food_enabled and c.household_savings_rate > 0)
                affordable = s.household_cash >= prospect
                if reserve_access:
                    # Python-int addition prevents int64 wrap in the guard.
                    affordable = np.logical_or(
                        affordable,
                        (s.household_cash.astype(object) +
                         s.household_savings.astype(object)) >= prospect)
                min_affordable = math.ceil(H * c.price_affordability_floor)
                if int(np.count_nonzero(affordable)) < min_affordable:
                    prospect = int(s.prices[f])
            s.prices[f] = prospect
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
        modeled_net_worth = (s.household_cash + s.household_savings + equity +
                             s.household_loan_assets_cents)
        expected_claims = (household_opening_claims +
                           credit_flows.household_principal_advanced -
                           credit_flows.household_principal_repaid -
                           credit_flows.household_principal_defaulted)
        if not np.array_equal(expected_claims, s.household_loan_assets_cents):
            raise AssertionError("household loan-claim reconciliation violated")
        expected_debts = (firm_opening_debt + credit_flows.firm_principal_advanced -
                          credit_flows.firm_principal_repaid -
                          credit_flows.firm_principal_defaulted)
        if not np.array_equal(expected_debts, s.firm_loan_liabilities_cents):
            raise AssertionError("firm debt reconciliation violated")
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
            "household_savings_stock_cents": int(s.household_savings.sum()),
            "household_loan_assets_cents": int(s.household_loan_assets_cents.sum()),
            "firm_loan_liabilities_cents": int(s.firm_loan_liabilities_cents.sum()),
            "loan_origination_cents": int(credit_flows.firm_principal_advanced.sum()),
            "loan_repayment_cents": int(credit_flows.firm_principal_repaid.sum()),
            "loan_defaults_cents": int(credit_flows.firm_principal_defaulted.sum()),
            "loan_discrepancy_cents": (int(s.household_loan_assets_cents.sum()) -
                                       int(s.firm_loan_liabilities_cents.sum())),
            "household_savings_deposited_cents": savings_deposits,
            "household_savings_withdrawn_cents": s.journal.get("savings_withdrawal", {}).get("cents", 0),
            "household_monetary_assets_cents": int((s.household_cash + s.household_savings).sum()),
            "household_monetary_assets_gini": gini(s.household_cash + s.household_savings),
            "household_cashflow_discrepancy_cents": household_flow_discrepancy,
            "firm_cashflow_discrepancy_cents": firm_flow_discrepancy,
            "government_tax_revenue_cents": tax_revenue,
            "government_resource_fee_cents": int(firm_resource_fees.sum()),
            "government_transfer_cents": transfer_spending,
            "government_balance_cents": s.gov_cash,
            "wages_cents": int(firm_wages.sum()), "dividends_cents": dividends,
            "sales_cents": int(sale_revenues.sum()),
            "firm_capital_sales_revenue_cents": int(capital_sale_revenues.sum()),
            "firm_operating_cash_surplus_cents": int(firm_operating_surplus.sum()),
            "firm_capital_depreciation_expense_cents": int(depreciation_expense_cents.sum()),
            "firm_profit_proxy_cents": int(firm_profit_proxy.sum()),
            "firm_cost_basis_accounting_enabled": c.cost_basis_accounting_enabled,
            "firm_inventory_historical_cost_cents": int(s.firm_inventory_basis_cents.sum()),
            "firm_capital_historical_cost_cents": int(s.firm_capital_basis_cents.sum()),
            "firm_resource_input_fees_cents": int(firm_resource_fees.sum()),
            "firm_consumer_cogs_cents": int(firm_consumption_cogs.sum()),
            "firm_capital_goods_cogs_cents": int(firm_capital_goods_cogs.sum()),
            "firm_uncapitalized_labor_cost_cents": int(firm_uncapitalized_labor_cost.sum()),
            "firm_book_depreciation_cents": int(firm_book_depreciation_cost.sum()),
            "firm_cost_basis_earnings_cents": (int(firm_cost_basis_earnings.sum()) if c.cost_basis_accounting_enabled else None),
            "firm_book_equity_discrepancy_cents": firm_book_equity_discrepancy,
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
            # Mechanism diagnostics; not a welfare objective or real-world index.
            "quoted_price_spread_mean_cents": float(np.mean([
                int(s.prices[k*nfirm_sector:(k+1)*nfirm_sector].max()) -
                int(s.prices[k*nfirm_sector:(k+1)*nfirm_sector].min())
                for k in range(ns)])),
            "seller_sales_hhi_mean": float(np.mean([
                float(np.sum((sold[k*nfirm_sector:(k+1)*nfirm_sector] /
                              int(sold[k*nfirm_sector:(k+1)*nfirm_sector].sum())) ** 2))
                if int(sold[k*nfirm_sector:(k+1)*nfirm_sector].sum()) else None
                for k in range(ns)
                if int(sold[k*nfirm_sector:(k+1)*nfirm_sector].sum())])) if int(sold.sum()) else None,
            "active_sellers": int(np.count_nonzero(sold)),
            "unmet_stock_demand_units": int(stock_unmet.sum()),
            "unmet_budget_demand_units": int(budget_unmet.sum()),
            "information_missed_purchase_opportunities": int(missed_quote_opportunities.sum()),
            "total_money_cents": s.total_money(),
            "money_discrepancy_cents": s.total_money() - s.initial_total_money,
            "resource_discrepancy_units": s.initial_resource + s.cumulative_resource_regenerated - s.cumulative_resource_extracted - s.resource,
            "goods_discrepancy_units": int(np.abs(expected_stock - observed_stock).sum()),
        }
        period = Period(metrics, {key: dict(value) for key, value in s.journal.items()},
                        list(s.transaction_events), list(s.noncash_events), list(s.physical_events))
        if s.trace_enabled:
            from civitas.ledger_audit import audit_period
            audit_period(opening_ledger, s, period)
            from civitas.physical_audit import audit_physical_period
            audit_physical_period(opening_physical, s, period, c)
            from civitas.balance_sheet import audit_book_period
            period.book_balance_report = audit_book_period(opening_book, s, period, c)
        return period

    def run(self, steps: int | None = None) -> list[Period]:
        count = self.scenario.steps if steps is None else steps
        if type(count) is not int or count < 0:
            raise ValueError("steps must be nonnegative integer")
        return [self.step() for _ in range(count)]
