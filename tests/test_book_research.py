from dataclasses import replace
import json
import pytest
from research.run_book_balance_closure import execute, execute_live_credit, write_campaign, verify_campaign


def test_small_campaign_executes_with_real_books():
    rows = execute(12, periods=2, population=24)
    assert len(rows) == 6
    assert all(row["book_equity_discrepancy_cents"] == 0 for row in rows)
    assert all(row["monetary_transfers"] >= 0 for row in rows)
    assert all(row["scenario_sha256"] for row in rows)


def test_campaign_replays_and_tamper_is_rejected(tmp_path):
    info = write_campaign(tmp_path, seeds=(1, 4), periods=3, population=24)
    assert info["runs"] == 6
    assert verify_campaign(tmp_path) == info
    path = tmp_path / "periods.jsonl"
    old = path.read_text()
    path.write_text(old.replace('"production_units":', '"production_units":999,' ,1))
    with pytest.raises(ValueError, match="SHA-256"):
        verify_campaign(tmp_path)
    path.write_text(old)
    summary_path = tmp_path / "summary.json"
    info["records_sha256"] = "0" * 64
    summary_path.write_text(json.dumps(info))
    with pytest.raises(ValueError, match="SHA-256"):
        verify_campaign(tmp_path)


def test_active_credit_replay_and_default():
    rows = execute_live_credit(7)
    assert [(r["loan_origination_cents"], r["loan_defaults_cents"],
             r["ending_credit_cents"]) for r in rows] == [(200, 0, 200), (0, 200, 0)]
