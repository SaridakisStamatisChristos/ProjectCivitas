"""Adversarial validation for long-horizon mechanism diagnostics."""
from dataclasses import replace
import gzip
import json

import pytest

from civitas.engine import Simulation
from research.run_demand_diagnostics import (
    ARMS, CHECKS, diag, encode, execute_cell, execute_seed, finalize,
    scenarios, sha, verify_cell,
)


def test_matched_design_and_interventions():
    configs = scenarios(80, 48)
    assert tuple(x.name for x in configs) == ARMS
    assert not configs[0].credit_enabled
    assert configs[1].household_savings_rate == 0
    assert configs[2].dividend_share == 1
    assert configs[3].price_adjustment == 0
    assert configs[4].hiring_expectation_rule == "stationary"
    assert configs[5].capital_depreciation_rate == 0
    for cfg in configs:
        Simulation(cfg).state.validate()


def test_poststep_observer_does_not_mutate_or_consume_rng():
    sim = Simulation(replace(scenarios(96,48)[0],seed=7))
    m = sim.step().metrics
    rng = sim.rng.bit_generator.state
    before = (sim.state.total_money(),sim.state.resource,sim.state.inventory.copy())
    a = diag(sim,m)
    b = diag(sim,m)
    assert a == b and a["step"] == 1
    assert all(a[k] == 0 for k in CHECKS)
    assert sim.rng.bit_generator.state == rng
    assert sim.state.total_money() == before[0]
    assert sim.state.resource == before[1]
    assert (sim.state.inventory == before[2]).all()


def test_replay_resume_and_paired_means(tmp_path):
    assert execute_seed(tmp_path,5,population=90,steps=48)["cells"] == 6
    assert execute_seed(tmp_path,5,population=90,steps=48)["periods"] == 288
    result=finalize(tmp_path,[5],population=90,steps=48)
    assert result["design"]["audited_periods"] == 288
    assert result["means"]["control_t48"]["production_units"]["n"] == 1
    assert result["paired_effects"]["fixed_prices_vs_control_change_t24_t48"]["n"] == 1
    assert finalize(tmp_path,[5],population=90,steps=48,write=False) == result


def test_missing_and_checksum_tamper_rejected(tmp_path):
    cfg=replace(scenarios(80,48)[0],seed=3)
    with pytest.raises(FileNotFoundError):
        finalize(tmp_path,[3],population=80,steps=48)
    execute_cell(tmp_path,cfg)
    path=tmp_path/'seed_0003'/'control.json.gz'
    with gzip.open(path,'rb') as stream:
        raw=json.loads(stream.read())
    raw['periods'][0]['money_discrepancy_cents']=5
    with gzip.open(path,'wb') as stream:stream.write(encode(raw))
    with pytest.raises(ValueError,match='checksum'):
        verify_cell(path,cfg)
    raw.pop('sha256');raw['sha256']=sha(raw)
    with gzip.open(path,'wb') as stream:stream.write(encode(raw))
    with pytest.raises(ValueError,match='accounting mismatch'):
        verify_cell(path,cfg)


def test_wrong_parameters_rejected(tmp_path):
    with pytest.raises(ValueError):scenarios(population=0,steps=48)
    with pytest.raises(ValueError):scenarios(population=100,steps=24)
    with pytest.raises(ValueError):execute_seed(tmp_path,-1,population=100)
    with pytest.raises(ValueError):finalize(tmp_path,[1,1])
    cfg=replace(scenarios(80,48)[0],seed=1)
    execute_cell(tmp_path,cfg)
    with pytest.raises(ValueError,match='configuration'):
        verify_cell(tmp_path/'seed_0001'/'control.json.gz',replace(cfg,dividend_share=0.1))


def test_monetary_partition_and_affordability_edge_cases():
    c=replace(scenarios(40,48)[0],seed=4)
    sim=Simulation(c)
    metrics=sim.step().metrics
    d=diag(sim,metrics)
    assert d['household_monetary_assets_cents'] + d['firm_cash_stock_cents'] + d['government_cash_stock_cents'] == sim.state.initial_total_money
    assert 0 <= d['firm_cash_share'] <= 1
    assert 0 <= d['household_nonessential_affordability'] <= 1
    assert 0 <= d['household_food_affordability'] <= 1


def test_independent_auditor_and_tampered_summary(tmp_path):
    from research.audit_demand_diagnostics import audit
    execute_seed(tmp_path,6,population=90,steps=48)
    finalize(tmp_path,[6],population=90,steps=48)
    assert audit(tmp_path)["audited_periods"] == 288
    report=tmp_path/'summary.json'
    data=json.loads(report.read_text())
    data['paired_effects']['fixed_prices_vs_control_t48_production']['mean']+=1
    report.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='saved statistical mean'):
        audit(tmp_path)


def test_archival_restoration_audits_content_and_prevents_overwrite(tmp_path):
    import zipfile
    from research.restore_demand_diagnostics import restore
    root=tmp_path/'raw'
    execute_seed(root,2,population=40,steps=48)
    finalize(root,[2],population=40,steps=48)
    archive=tmp_path/'evidence.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for path in root.rglob('*'):
            if path.is_file():z.write(path,path.relative_to(root).as_posix())
    assert restore(archive,tmp_path/'restored')['audited_runs'] == 6
    with pytest.raises(FileExistsError):restore(archive,tmp_path/'restored')
    with zipfile.ZipFile(tmp_path/'danger.zip','w') as z:
        z.writestr('../escape.json','bad')
    with pytest.raises(ValueError):restore(tmp_path/'danger.zip',tmp_path/'target')
