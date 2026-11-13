"""End-to-end adversarial checks for credit pathway counterfactual research."""
from __future__ import annotations

from dataclasses import replace
import json

import pytest

from civitas.engine import Simulation
from research.run_credit_pathways import (
    CHECKS, canonical, configs, digest, execute_seed, finalize,
    source_digest, verify_seed,
)


def test_factorial_spec_and_zero_lend_sham() -> None:
    cells = configs(120, 24)
    assert len(cells) == 12
    assert len({c.name for c in cells}) == 12
    for s in (25, 75):
        control = next(c for c in cells if c.name == f"s{s}_control")
        sham = next(c for c in cells if c.name == f"s{s}_sham")
        assert not control.credit_enabled and sham.credit_enabled
        assert sham.credit_lender_savings_share == 0
        a, b = Simulation(replace(control, seed=9)), Simulation(replace(sham, seed=9))
        for x, y in zip(a.run(24), b.run(24)):
            assert x.metrics == y.metrics
        assert a.rng.bit_generator.state == b.rng.bit_generator.state


def test_seed_replay_source_and_accounting(tmp_path) -> None:
    record = execute_seed(tmp_path, 4, population=96, steps=24)
    assert record == execute_seed(tmp_path, 4, population=96, steps=24)
    assert len(record["cells"]) == 12
    assert len({c["initial_state_sha256"] for c in record["cells"]}) == 1
    for c in record["cells"]:
        assert all(p[k] == 0 for p in c["periods"] for k in CHECKS)
    outcome = finalize(tmp_path, [4], population=96, steps=24)
    assert outcome["design"]["runs"] == 12
    assert outcome["design"]["audited_periods"] == 288
    assert "savings_credit_interaction_broad_term6_t24" in outcome["paired_effects"]
    assert outcome["final_period_means"]["s25_control"]["24"]["production_units"]["n"] == 1


def test_report_rejects_missing_and_corrupted_shards(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        finalize(tmp_path, [1], population=90, steps=24)
    record = execute_seed(tmp_path, 1, population=90, steps=24)
    path = tmp_path / "seed_0001.json"
    original = json.loads(path.read_text())
    original["cells"][0]["periods"][0]["money_discrepancy_cents"] = 9
    path.write_text(json.dumps(original))
    with pytest.raises(ValueError, match="checksum"):
        verify_seed(path, 1, configs(90, 24), source_digest())
    # A malicious edit may recompute the checksum but cannot bypass invariants.
    original.pop("data_sha256")
    original["data_sha256"] = digest(original)
    path.write_text(json.dumps(original))
    with pytest.raises(ValueError, match="accounting discrepancy"):
        finalize(tmp_path, [1], population=90, steps=24)
    assert record["seed"] == 1


def test_report_rejects_principal_rollforward_forgery(tmp_path) -> None:
    execute_seed(tmp_path, 2, population=120, steps=24)
    path = tmp_path / "seed_0002.json"
    record = json.loads(path.read_text())
    cell = next(c for c in record["cells"] if c["name"] == "s25_sham")
    cell["periods"][0]["loan_origination_cents"] += 1
    record.pop("data_sha256")
    record["data_sha256"] = digest(record)
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="outstanding principal identity"):
        finalize(tmp_path, [2], population=120, steps=24)


def test_invalid_population_and_horizon_and_seed(tmp_path) -> None:
    for population, horizon in ((0, 24), (100, 23), (-1, 30)):
        with pytest.raises(ValueError):
            configs(population, horizon)
    with pytest.raises(ValueError):
        execute_seed(tmp_path, -1, population=100, steps=24)
    with pytest.raises(ValueError):
        finalize(tmp_path, [1, 1], population=100, steps=24)
    with pytest.raises(ValueError):
        finalize(tmp_path, [], population=100, steps=24)


def test_interrupted_seed_resume_and_cell_tamper(tmp_path) -> None:
    from research.run_credit_pathways import run_cell, verify_cell
    cfg = next(c for c in configs(72, 24) if c.name == "s25_control")
    first = run_cell(tmp_path, 8, cfg)
    assert first == run_cell(tmp_path, 8, cfg)
    # Complete the other 11 treatments without overwriting the first shard.
    executed = execute_seed(tmp_path, 8, population=72, steps=24)
    assert executed["cells"][0] == first["cell"]
    shard = tmp_path / "seed_0008" / "s25_control.json"
    manipulated = json.loads(shard.read_text())
    manipulated["cell"]["periods"].pop()
    manipulated.pop("data_sha256")
    manipulated["data_sha256"] = digest(manipulated)
    shard.write_text(json.dumps(manipulated))
    with pytest.raises(ValueError, match="incomplete individual cell"):
        verify_cell(shard, replace(cfg, seed=8), source_digest())


def test_independent_auditor_detects_tampered_mean(tmp_path) -> None:
    from research.audit_credit_pathways import audit
    for seed in (1, 2):
        execute_seed(tmp_path, seed, population=64, steps=24)
    finalize(tmp_path, [1, 2], population=64, steps=24)
    clean = audit(tmp_path)
    assert clean["simulations"] == 24 and clean["audited_periods"] == 576
    summary = json.loads((tmp_path / "summary.json").read_text())
    summary["final_period_means"]["s25_control"]["24"]["production_units"]["mean"] += 1
    (tmp_path / "summary.json").write_text(json.dumps(summary))
    with pytest.raises(ValueError, match="production summary"):
        audit(tmp_path)


def test_gzip_evidence_restore_with_integrity(tmp_path) -> None:
    import gzip
    from pathlib import Path
    from research.restore_credit_pathways import restore
    samples = tmp_path / "original"
    for seed in (1, 2):
        execute_seed(samples, seed, population=80, steps=24)
    finalize(samples, [1, 2], population=80, steps=24)
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "summary.json").write_bytes((samples / "summary.json").read_bytes())
    for seed in (1, 2):
        source = samples / f"seed_{seed:04d}.json"
        (archive / f"seed_{seed:04d}.json.gz").write_bytes(gzip.compress(source.read_bytes(), mtime=0))
    restored = tmp_path / "restored"
    assert restore(archive, restored)["restored"] == 2
    assert (restored / "seed_0002.json").read_bytes() == (samples / "seed_0002.json").read_bytes()
    assert restore(archive, restored)["restored"] == 2
    (archive / "seed_0002.json.gz").write_bytes(gzip.compress(b'{"bad":true}',mtime=0))
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        restore(archive, tmp_path / "reject")
