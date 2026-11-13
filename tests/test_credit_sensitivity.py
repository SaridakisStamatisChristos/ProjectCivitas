"""Adversarial checks of the resumable sensitivity-study evidence pipeline."""
from __future__ import annotations
import copy
import json
from pathlib import Path

import pytest

from research.run_credit_sensitivity import (
    CHECKS, digest, finalize, make_configs, run_seed, source_digest, verify_seed,
)


@pytest.fixture(scope="module")
def populated(tmp_path_factory):
    output = tmp_path_factory.mktemp("credit_shards")
    run_seed(output, 5, population=100, steps=3)
    return output


def test_density_switch_preserves_aggregate_initial_firm_cash_and_capital():
    cfgs=make_configs(10_000, 24)
    assert len(cfgs)==12
    assert len({c.name for c in cfgs})==12
    for c in cfgs:
        assert c.firms_per_sector*3*c.initial_firm_cash_cents==3*20*20_000
        assert c.firms_per_sector*3*c.initial_capital_units_per_firm==3*20*20
        assert c.initial_resource==5_000_000
        assert c.resource_capacity==6_000_000
    assert {c.credit_term_periods for c in cfgs if c.credit_enabled}=={2,6}
    assert {c.household_savings_rate for c in cfgs}=={0.25,0.75}


def test_full_seed_audits_12_cells_and_matched_initials(populated):
    cfg={c.name:c for c in make_configs(100,3)}
    record=verify_seed(populated/"seed_0005.json",cfg,5,source_digest())
    assert len(record["cells"])==12
    assert all(len(c["periods"])==3 for c in record["cells"])
    assert all(all(m[k]==0 for k in CHECKS) for c in record["cells"] for m in c["periods"])
    assert all(c["total_originations_cents"]==0 for c in record["cells"] if c["name"].endswith("control"))
    for density in (10,20):
        for savings in (25,75):
            matched=[c["initial_state_sha256"] for c in record["cells"]
                     if c["name"].startswith(f"density{density}_savings{savings}_")]
            assert len(set(matched))==1


def test_rerunning_seed_is_idempotent(populated):
    path=populated/"seed_0005.json"
    before=path.read_bytes()
    run_seed(populated,5,population=100,steps=3)
    assert path.read_bytes()==before


def test_finalization_rejects_missing_seeds(populated):
    with pytest.raises(FileNotFoundError):
        finalize(populated,[5,6],population=100,steps=3)
    with pytest.raises(ValueError):
        finalize(populated,[5,5],population=100,steps=3)


def test_finalization_reports_all_periods_and_credit_contrasts(populated):
    stats=finalize(populated,[5],population=100,steps=3)
    assert stats["design"]["audited_periods"]==36
    assert stats["design"]["runs"]==12
    assert len(stats["paired_credit_effects"])==8
    assert stats["paired_credit_effects"]["density10_savings25_term2_minus_control"]["production_units"]["n"]==1


def test_tampered_shard_rejected_even_if_checksum_recomputed(populated,tmp_path):
    source=json.loads((populated/"seed_0005.json").read_text())
    # A new self-consistent checksum cannot conceal an invalid accounting row.
    source["cells"][0]["periods"][0]["money_discrepancy_cents"]=1
    payload={k:v for k,v in source.items() if k!="data_sha256"}
    source["data_sha256"]=digest(payload)
    p=tmp_path/"seed_0005.json"
    p.write_text(json.dumps(source))
    cfg={c.name:c for c in make_configs(100,3)}
    with pytest.raises(ValueError,match="accounting invariant"):
        verify_seed(p,cfg,5,source_digest())


def test_corrupt_config_digest_rejected_even_if_checksum_recomputed(populated,tmp_path):
    source=json.loads((populated/"seed_0005.json").read_text())
    source["cells"][0]["config_sha256"]="f"*64
    payload={k:v for k,v in source.items() if k!="data_sha256"}
    source["data_sha256"]=digest(payload)
    p=tmp_path/"seed_0005.json"
    p.write_text(json.dumps(source))
    cfg={c.name:c for c in make_configs(100,3)}
    with pytest.raises(ValueError,match="configuration digest"):
        verify_seed(p,cfg,5,source_digest())
