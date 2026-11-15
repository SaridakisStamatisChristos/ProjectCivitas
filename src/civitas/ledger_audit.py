"""Independent, transaction-by-transaction monetary and credit ledger auditor.

This module intentionally does not call State.transfer, the engine's journal
accounting helpers, or its financial reconciliation equations. The opening
snapshot, immutable event evidence, final state, and period aggregates must
agree *per participant*, not only in their grand totals.

Scope: cash/savings/treasury transfers, bilateral principal and noncash loan
writeoffs. Physical stock and historical-cost valuations remain independently
validated by the simulation engine and are not claimed to be part of this
monetary journal. Do not confuse this with a general-purpose double-entry
financial accounting standard.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from civitas.state import State
    from civitas.engine import Period

I64_MAX = 2**63 - 1

# Reason -> (source-account kind, destination-account kind). Explicit rules
# prevent a mislabeled payment from passing an aggregate reconciliation.
TRANSFER_RULES = {
    "wages": ("firm", "household"),
    "wage_tax": ("household", "government"),
    "transfer": ("government", "household"),
    "sale": ("household", "firm"),
    "capital_purchase": ("firm", "firm"),
    "resource_fee": ("firm", "government"),
    "dividend": ("firm", "household"),
    "savings_deposit": ("household", "savings"),
    "savings_withdrawal": ("savings", "household"),
    "loan_origination": ("savings", "firm"),
    "loan_repayment": ("firm", "savings"),
    "firm_capital_contribution": ("household", "firm"),
    "firm_liquidation_distribution": ("firm", "household"),
    "firm_liquidation_escheat": ("firm", "government"),
}
NONCASH_WRITE_OFF = "loan_default_noncash"

# Only exact, integer metrics with an established one-to-one journal mapping.
REASON_METRICS = {
    "wages": "household_gross_wages_cents",
    "wage_tax": "government_tax_revenue_cents",
    "transfer": "government_transfer_cents",
    "sale": "sales_cents",
    "capital_purchase": "capital_interfirm_purchases_cents",
    "resource_fee": "government_resource_fee_cents",
    "dividend": "dividends_cents",
    "savings_deposit": "household_savings_deposited_cents",
    "savings_withdrawal": "household_savings_withdrawn_cents",
    "loan_origination": "loan_origination_cents",
    "loan_repayment": "loan_repayment_cents",
    "firm_capital_contribution": "firm_reentry_contributions_cents",
    "firm_liquidation_distribution": "firm_liquidation_distributions_cents",
    "firm_liquidation_escheat": "firm_liquidation_escheat_cents",
    NONCASH_WRITE_OFF: "loan_defaults_cents",
}


class LedgerAuditError(AssertionError):
    """A monetary transfer, credit claim or journal fails independent replay."""


@dataclass(frozen=True)
class OpeningLedger:
    household: tuple[int, ...]
    savings: tuple[int, ...]
    firm: tuple[int, ...]
    government: tuple[int, ...]
    household_claims: tuple[int, ...]
    firm_debts: tuple[int, ...]


@dataclass(frozen=True)
class LedgerAuditReport:
    transfer_count: int
    transfer_cents: int
    noncash_writeoff_count: int
    noncash_writeoff_cents: int
    outstanding_claims_cents: int
    money_stock_cents: int


def capture_opening(state: State) -> OpeningLedger:
    """Make a disjoint initial snapshot; the engine may mutate State in place."""
    return OpeningLedger(
        household=tuple(int(v) for v in state.household_cash),
        savings=tuple(int(v) for v in state.household_savings),
        firm=tuple(int(v) for v in state.firm_cash),
        government=(int(state.gov_cash),),
        household_claims=tuple(int(v) for v in state.household_loan_assets_cents),
        firm_debts=tuple(int(v) for v in state.firm_loan_liabilities_cents),
    )


def _checked_amount(value: object) -> int:
    if type(value) is not int or not 0 < value <= I64_MAX:
        raise LedgerAuditError("ledger amount must be a positive signed-int64 integer")
    return value


def audit_period(opening: OpeningLedger, closing: State, period: Period) -> LedgerAuditReport:
    """Replay all traced transfers, then reconcile journal, credit and metrics.

    Requires a *complete* trace for the period. An absent trace is not a
    successful audit, even if no money moved: callers must explicitly enable
    tracing, and must provide matching journal totals for any events.
    """
    if not closing.trace_enabled:
        raise LedgerAuditError("transaction tracing must be enabled for independent audit")
    accounts = {
        "household": list(opening.household),
        "savings": list(opening.savings),
        "firm": list(opening.firm),
        "government": list(opening.government),
    }
    claims = list(opening.household_claims)
    debts = list(opening.firm_debts)
    if len(claims) != len(accounts["household"]) or len(debts) != len(accounts["firm"]):
        raise LedgerAuditError("opening credit dimensions differ from cash account dimensions")
    transfer_totals: Counter[str] = Counter()
    transfer_counts: Counter[str] = Counter()
    total_cents = 0
    for number, tx in enumerate(period.transactions):
        if type(tx) is not dict or set(tx) != {
            "source", "source_id", "destination", "destination_id", "cents", "reason"
        }:
            raise LedgerAuditError(f"transaction {number}: unexpected schema")
        reason = tx["reason"]
        rule = TRANSFER_RULES.get(reason)
        if rule is None or (tx["source"], tx["destination"]) != rule:
            raise LedgerAuditError(f"transaction {number}: incorrect payment classification")
        src, dst = rule
        sid, did = tx["source_id"], tx["destination_id"]
        if (type(sid) is not int or type(did) is not int or
                not 0 <= sid < len(accounts[src]) or not 0 <= did < len(accounts[dst])):
            raise LedgerAuditError(f"transaction {number}: account ID out of bounds")
        if src == dst and sid == did:
            raise LedgerAuditError(f"transaction {number}: no-op transfer must not be recorded")
        if reason in ("savings_deposit", "savings_withdrawal") and sid != did:
            raise LedgerAuditError(f"transaction {number}: savings moved to a different household")
        cents = _checked_amount(tx["cents"])
        if accounts[src][sid] < cents:
            raise LedgerAuditError(f"transaction {number}: source cannot fund transfer")
        if accounts[dst][did] > I64_MAX - cents:
            raise LedgerAuditError(f"transaction {number}: recipient would overflow")
        accounts[src][sid] -= cents
        accounts[dst][did] += cents
        if reason == "loan_origination":
            if claims[sid] > I64_MAX - cents or debts[did] > I64_MAX - cents:
                raise LedgerAuditError("credit principal would exceed signed-int64 storage")
            claims[sid] += cents
            debts[did] += cents
        elif reason == "loan_repayment":
            if claims[did] < cents or debts[sid] < cents:
                raise LedgerAuditError("principal repayment exceeds outstanding claims")
            claims[did] -= cents
            debts[sid] -= cents
        transfer_totals[reason] += cents
        transfer_counts[reason] += 1
        total_cents += cents

    noncash = period.noncash_transactions
    if not isinstance(noncash, list):
        raise LedgerAuditError("noncash transaction evidence must be a list")
    noncash_total = 0
    for number, event in enumerate(noncash):
        if (type(event) is not dict or set(event) != {
            "reason", "lender_household", "borrower_firm", "cents"
        } or event["reason"] != NONCASH_WRITE_OFF):
            raise LedgerAuditError(f"noncash event {number}: unexpected schema or reason")
        h, f = event["lender_household"], event["borrower_firm"]
        if (type(h) is not int or type(f) is not int or
                not 0 <= h < len(claims) or not 0 <= f < len(debts)):
            raise LedgerAuditError(f"noncash event {number}: creditor/debtor out of bounds")
        cents = _checked_amount(event["cents"])
        claims[h] -= cents
        debts[f] -= cents
        noncash_total += cents
    if any(x < 0 or x > I64_MAX for x in claims + debts):
        raise LedgerAuditError("negative or overflowing credit principal during replay")

    # Strongest check: one integer equality for *every* monetary account and
    # *every* lender claim / borrower debt; aggregate totals are not enough.
    expected = {
        **accounts,
        "household_claims": claims,
        "firm_debts": debts,
    }
    actual = {
        "household": [int(x) for x in closing.household_cash],
        "savings": [int(x) for x in closing.household_savings],
        "firm": [int(x) for x in closing.firm_cash],
        "government": [int(closing.gov_cash)],
        "household_claims": [int(x) for x in closing.household_loan_assets_cents],
        "firm_debts": [int(x) for x in closing.firm_loan_liabilities_cents],
    }
    for kind, calculated in expected.items():
        if calculated != actual[kind]:
            raise LedgerAuditError(f"{kind}: replay disagrees with closing state")

    if type(period.journal) is not dict:
        raise LedgerAuditError("journal must be a mapping")
    reconstructed = {reason: {"cents": transfer_totals[reason], "count": transfer_counts[reason]}
                     for reason in transfer_totals}
    if noncash:
        reconstructed[NONCASH_WRITE_OFF] = {"cents": noncash_total, "count": len(noncash)}
    for reason, item in period.journal.items():
        if (reason not in REASON_METRICS or type(item) is not dict or
                set(item) != {"cents", "count"} or
                type(item["cents"]) is not int or type(item["count"]) is not int or
                item["cents"] < 0 or item["count"] < 0):
            raise LedgerAuditError("journal contains an unrecognized or malformed entry")
    if reconstructed != period.journal:
        raise LedgerAuditError("journal count/reason/amount differs from underlying events")

    for reason, field in REASON_METRICS.items():
        measured = noncash_total if reason == NONCASH_WRITE_OFF else transfer_totals[reason]
        if (field not in period.metrics and measured == 0 and
                reason.startswith('firm_')):
            continue
        if type(period.metrics.get(field)) is not int or period.metrics[field] != measured:
            raise LedgerAuditError(f"metric {field} differs from underlying transactions")
    total_money = sum(sum(values) for values in accounts.values())
    if period.metrics.get("total_money_cents") != total_money:
        raise LedgerAuditError("reported monetary stock differs from replay")
    if period.metrics.get("household_loan_assets_cents") != sum(claims):
        raise LedgerAuditError("reported household loan claims differ from replay")
    if period.metrics.get("firm_loan_liabilities_cents") != sum(debts):
        raise LedgerAuditError("reported firm loan liabilities differ from replay")
    if sum(claims) != sum(debts):
        raise LedgerAuditError("lender assets and borrower debts differ")
    return LedgerAuditReport(
        transfer_count=len(period.transactions), transfer_cents=total_cents,
        noncash_writeoff_count=len(noncash), noncash_writeoff_cents=noncash_total,
        outstanding_claims_cents=sum(claims), money_stock_cents=total_money,
    )
