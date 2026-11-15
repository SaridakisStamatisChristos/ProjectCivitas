"""Independent firm-activity replay cross-checked to financial and physical events."""
from __future__ import annotations
from collections import Counter
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from civitas.engine import Period
    from civitas.state import State

class FirmLifecycleAuditError(AssertionError):
    """A firm transition or settlement disagrees with the transaction trace."""


def audit_firm_lifecycle(opening_active: tuple[bool, ...], closing: State,
                         period: Period) -> dict[str, int]:
    if not closing.trace_enabled or len(opening_active) != len(closing.firm_active):
        raise FirmLifecycleAuditError('firm lifecycle audit requires compatible full trace')
    active = list(opening_active)
    events = period.lifecycle_transactions
    if type(events) is not list:
        raise FirmLifecycleAuditError('missing lifecycle event stream')
    entries = exits = 0
    contribution_by_firm = Counter()
    inventory = capital = asset_basis = 0
    for tx in period.transactions:
        if tx['reason'] == 'firm_capital_contribution':
            contribution_by_firm[tx['destination_id']] += tx['cents']
    event_contributions = Counter()
    exit_firms = set()
    seen_entry = set()
    seen_exit = set()
    exiting = False
    for event in events:
        if type(event) is not dict or type(event.get('firm')) is not int:
            raise FirmLifecycleAuditError('invalid firm lifecycle event')
        f = event['firm']
        if not 0 <= f < len(active):
            raise FirmLifecycleAuditError('unknown firm transition')
        kind = event.get('kind')
        if kind == 'firm_reentry':
            if (exiting or set(event) != {'kind','firm','contribution_cents'} or
                    active[f] or f in seen_entry or f in seen_exit or
                    type(event['contribution_cents']) is not int or
                    event['contribution_cents'] <= 0):
                raise FirmLifecycleAuditError('invalid or unfunded firm reentry')
            seen_entry.add(f)
            event_contributions[f] += event['contribution_cents']
            active[f] = True
            entries += 1
        elif kind == 'firm_liquidation':
            exiting = True
            if (set(event) != {'kind','firm','inventory_units','capital_units','asset_writeoff_cents'} or
                    not active[f] or f in seen_exit or any(type(event[k]) is not int or event[k] < 0 for k in
                        ('inventory_units','capital_units','asset_writeoff_cents'))):
                raise FirmLifecycleAuditError('invalid firm liquidation')
            seen_exit.add(f)
            inventory += event['inventory_units']
            capital += event['capital_units']
            asset_basis += event['asset_writeoff_cents']
            exit_firms.add(f)
            active[f] = False
            exits += 1
        else:
            raise FirmLifecycleAuditError('unexpected firm lifecycle event')
    if active != [bool(v) for v in closing.firm_active]:
        raise FirmLifecycleAuditError('activity flags differ from recorded transitions')
    if contribution_by_firm != event_contributions:
        raise FirmLifecycleAuditError('capital contributions differ from firm entry events')
    scrapped = Counter()
    for event in period.physical_transactions:
        if event.get('kind') == 'firm_liquidation':
            f = event['firm']
            if f not in exit_firms:
                raise FirmLifecycleAuditError('unregistered firm disposed of physical assets')
            scrapped[f] = (event['inventory_units'], event['capital_units'],
                          event['inventory_basis_cents'] + event['capital_basis_cents'])
    for event in events:
        if event['kind'] == 'firm_liquidation':
            actual = (event['inventory_units'], event['capital_units'], event['asset_writeoff_cents'])
            if actual != scrapped.get(event['firm'], (0, 0, 0)):
                raise FirmLifecycleAuditError('firm disposal differs from physical trace')
    for f in exit_firms:
        if any(int(array[f]) != 0 for array in (closing.firm_cash, closing.inventory,
                   closing.firm_inventory_basis_cents, closing.firm_capital,
                   closing.firm_capital_basis_cents, closing.firm_loan_liabilities_cents)):
            raise FirmLifecycleAuditError('liquidated firm retains a nonzero asset or liability')
    expected = {'firm_active_count': sum(active), 'firm_reentries': entries,
                'firm_liquidations': exits,
                'firm_reentry_contributions_cents': sum(event_contributions.values()),
                'firm_liquidation_inventory_units': inventory,
                'firm_liquidation_capital_units': capital,
                'firm_liquidation_basis_cents': asset_basis}
    for key, amount in expected.items():
        if (key not in period.metrics and not events and
                all(opening_active) and all(active)):
            continue
        if type(period.metrics.get(key)) is not int or period.metrics[key] != amount:
            raise FirmLifecycleAuditError(f'metric {key} differs from lifecycle trace')
    return expected
