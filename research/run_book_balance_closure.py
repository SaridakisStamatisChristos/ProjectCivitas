"""Reproducible synthetic balance-sheet closure campaign (no empirical calibration)."""
from __future__ import annotations

import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

from civitas.balance_sheet import capture_book_snapshot
from civitas.engine import Simulation
from civitas.model import Scenario, Sector
from civitas.persistence import canonical_json, config_digest


def configurations(seed: int, population: int = 128) -> list[Scenario]:
    base = Scenario(name="book-balance", seed=seed, population=population,
                    firms_per_sector=2, capital_enabled=True,
                    initial_capital_units_per_firm=40, capital_output_per_unit=3,
                    capital_depreciation_rate=0.05, capital_investment_budget_share=0.3,
                    household_savings_rate=0.5,
                    credit_term_periods=3, credit_firm_cash_reserve_cents=20000,
                    credit_max_principal_per_firm_cents=100000,
                    resource_extraction_fee_cents_per_unit=2,
                    transaction_trace=True)
    return [
        replace(base, name="cash-only", cost_basis_accounting_enabled=False,
                credit_enabled=False, resource_extraction_fee_cents_per_unit=0),
        replace(base, name="historical-cost", cost_basis_accounting_enabled=True,
                credit_enabled=False),
        replace(base, name="historical-cost-credit", cost_basis_accounting_enabled=True,
                credit_enabled=True),
    ]


def execute(seed: int, *, periods: int = 12, population: int = 128) -> list[dict]:
    if type(seed) is not int or seed < 0 or type(periods) is not int or periods < 1:
        raise ValueError("invalid seed or period count")
    if type(population) is not int or population < 1:
        raise ValueError("invalid population")
    rows = []
    for config in configurations(seed, population=population):
        sim = Simulation(config)
        initial_money = sim.state.total_money()
        for _ in range(periods):
            period = sim.step()
            report = period.book_balance_report
            if report is None:
                raise AssertionError("missing balance-sheet audit")
            book = capture_book_snapshot(sim.state, config)
            totals = book.totals()
            if (totals["total_money_cents"] != initial_money or
                    report["national_book_net_worth_cents"] != totals["national_book_net_worth_cents"] or
                    report["book_equity_discrepancy_cents"] != 0):
                raise AssertionError("book-balance closure discrepancy")
            rows.append({
                "seed": seed, "scenario": config.name,
                "scenario_sha256": config_digest(config),
                "step": period.metrics["step"],
                "production_units": period.metrics["production_units"],
                "consumption_units": period.metrics["consumption_units"],
                "loan_origination_cents": period.metrics["loan_origination_cents"],
                "loan_default_cents": period.metrics["loan_defaults_cents"],
                "monetary_transfers": len(period.transactions),
                "physical_events": len(period.physical_transactions),
                **report,
            })
    return rows


def execute_live_credit(seed: int) -> list[dict]:
    """Hand-built, explicitly seeded inventory/savings stock: loan then default."""
    c = Scenario(name="book-credit-origin/default", population=4, household_size=1,
                 seed=seed, firms_per_sector=2, initial_household_cash_cents=3000,
                 initial_firm_cash_cents=0, initial_resource=100, resource_capacity=100,
                 capital_enabled=True, initial_capital_units_per_firm=0,
                 capital_investment_budget_share=0.5, credit_enabled=True,
                 cost_basis_accounting_enabled=True, credit_lender_savings_share=1.0,
                 credit_firm_cash_reserve_cents=0, credit_repayment_fraction=0.,
                 credit_term_periods=1, dividend_share=0., tax_rate=0.,
                 household_savings_rate=0., transaction_trace=True,
                 sectors=(Sector("goods", 1., 100, 0, 1., 1),))
    sim = Simulation(c)
    sim.state.household_savings[0] += 2000
    sim.state.household_cash[0] -= 2000
    sim.state.inventory[1] = 10
    sim.state.cumulative_output[0] = 10  # disclose prefunded physical stock
    rows = []
    for _ in range(2):
        period = sim.step()
        rows.append({"seed": seed, "step": period.metrics["step"],
                     "loan_origination_cents": period.metrics["loan_origination_cents"],
                     "loan_defaults_cents": period.metrics["loan_defaults_cents"],
                     "ending_credit_cents": period.book_balance_report["credit_stock_cents"],
                     "equity_discrepancy_cents": period.book_balance_report["book_equity_discrepancy_cents"]})
    if ([row["loan_origination_cents"] for row in rows] != [200, 0] or
            [row["loan_defaults_cents"] for row in rows] != [0, 200] or
            [row["ending_credit_cents"] for row in rows] != [200, 0]):
        raise AssertionError("active-credit synthetic example did not exercise loan cycle")
    return rows


def write_campaign(destination: str | Path, *, seeds: tuple[int, ...] = (2, 3, 5, 7, 11, 13),
                   periods: int = 12, population: int = 128) -> dict:
    target = Path(destination)
    target.mkdir(parents=True, exist_ok=True)
    observed = []
    for seed in seeds:
        observed.extend(execute(seed, periods=periods, population=population))
    text = "".join(canonical_json(row) + "\n" for row in observed)
    (target / "periods.jsonl").write_text(text, encoding="utf-8")
    credit_rows = [record for seed in seeds for record in execute_live_credit(seed)]
    credit_text = "".join(canonical_json(row) + "\n" for row in credit_rows)
    (target / "active_credit.jsonl").write_text(credit_text, encoding="utf-8")
    summary = {
        "design": "3 accounting mechanisms × 6 seeds × 12 periods, synthetic uncalibrated",
        "population": population, "seeds": list(seeds), "periods_per_run": periods,
        "runs": 3 * len(seeds), "audited_periods": len(observed),
        "cash_transfers": sum(row["monetary_transfers"] for row in observed),
        "physical_events": sum(row["physical_events"] for row in observed),
        "loan_originations_cents": sum(row["loan_origination_cents"] for row in observed),
        "loan_defaults_cents": sum(row["loan_default_cents"] for row in observed),
        "max_book_equity_discrepancy_cents": max(row["book_equity_discrepancy_cents"] for row in observed),
        "active_credit_runs": len(seeds), "active_credit_periods": len(credit_rows),
        "active_credit_originated_cents": sum(row["loan_origination_cents"] for row in credit_rows),
        "active_credit_defaulted_cents": sum(row["loan_defaults_cents"] for row in credit_rows),
        "active_credit_sha256": sha256(credit_text.encode("utf-8")).hexdigest(),
        "records_sha256": sha256(text.encode("utf-8")).hexdigest(),
    }
    (target / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def verify_campaign(directory: str | Path, *, rerun: bool = True) -> dict:
    target = Path(directory)
    s = json.loads((target / "summary.json").read_text(encoding="utf-8"))
    text = (target / "periods.jsonl").read_text(encoding="utf-8")
    if sha256(text.encode("utf-8")).hexdigest() != s["records_sha256"]:
        raise ValueError("dataset SHA-256 mismatch")
    rows = [json.loads(line) for line in text.splitlines()]
    if len(rows) != s["audited_periods"] or len(rows) != s["runs"] * s["periods_per_run"]:
        raise ValueError("dataset record count mismatch")
    credit_text = (target / "active_credit.jsonl").read_text(encoding="utf-8")
    if sha256(credit_text.encode("utf-8")).hexdigest() != s["active_credit_sha256"]:
        raise ValueError("active-credit SHA-256 mismatch")
    credit_rows = [json.loads(line) for line in credit_text.splitlines()]
    if len(credit_rows) != s["active_credit_periods"] or len(credit_rows) != 2 * len(s["seeds"]):
        raise ValueError("active-credit record count mismatch")
    if rerun:
        expected_credit = [row for seed in s["seeds"] for row in execute_live_credit(seed)]
        if credit_rows != expected_credit:
            raise ValueError("active-credit dataset disagrees with replay")
        expected = []
        for seed in s["seeds"]:
            expected.extend(execute(seed, periods=s["periods_per_run"],
                                    population=s["population"]))
        if rows != expected:
            raise ValueError("dataset differs from independently repeated simulation")
    return s


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(verify_campaign(args.output) if args.verify else
                     write_campaign(args.output), indent=2))


if __name__ == "__main__":
    main()
