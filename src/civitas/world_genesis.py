"""Reproducible World Genesis: explicit endowments, sampled worlds and provenance.

World *parameters* are sampled once when a plan is resolved. Per-household
and per-firm attributes are sampled using independent seeded substreams when
an initial State is created. Saved Scenario JSON is self-contained; checkpoints
capture the actual realized State. No external APIs or implicit randomness.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from civitas.model import Scenario
    from civitas.state import State

I64MAX = (1 << 63) - 1
MODES = frozenset({"configured", "randomized", "hybrid"})
# Only scalar, persistent simulation parameters may be drawn. Rule implementation
# cannot be changed by a generator; policy *selection* is explicit and auditable.
SCENARIO_DRAW_FIELDS = frozenset({
    "population", "household_size", "firms_per_sector", "initial_household_cash_cents",
    "initial_firm_cash_cents", "initial_resource", "resource_capacity",
    "labor_participation", "tax_rate", "redistribution_share", "transfer_recipient_fraction",
    "dividend_share", "ownership_fraction", "buyer_cheapest_probability",
    "household_savings_rate", "initial_capital_units_per_firm", "capital_depreciation_rate",
    "capital_investment_budget_share", "regeneration_rate", "price_adjustment",
    "credit_lender_savings_share", "credit_repayment_fraction", "credit_term_periods",
    "buyer_seller_rule", "hiring_expectation_rule", "price_update_rule",
})
INITIAL_FIELDS = frozenset({
    "household_cash_cents", "firm_cash_cents", "firm_capital_units",
    "price_multiplier", "skills", "participation_probability", "household_savings_fraction",
})
MONEY_FIELDS = {"household_cash_cents", "firm_cash_cents", "firm_capital_units"}
STREAM_TAGS = {
    "household_cash_cents": 101, "firm_cash_cents": 102,
    "firm_capital_units": 103, "price_multiplier": 104,
    "skills": 105, "participation_probability": 106,
    "household_savings_fraction": 107,
}


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(obj: Any) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def _obj(raw: Any, context: str, keys: set[str]) -> dict:
    if type(raw) is not dict:
        raise ValueError(f"{context} must be a JSON object")
    extra = set(raw) - keys
    if extra:
        raise ValueError(f"unknown {context} fields: {sorted(extra)}")
    return raw


def _number(value: Any, context: str, *, minimum: float = 0.0, maximum: float = float('inf')) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{context} must be finite and in [{minimum}, {maximum}]")
    return float(value)


def _nonnegative_int(value: Any, context: str, maximum: int = I64MAX) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f"{context} must be integer in [0,{maximum}]")
    return value


def validate_spec(spec: Any, *, field: str, scenario_field: bool = False) -> None:
    """Reject malformed specs *before* sampling; whitelist distributions."""
    d = _obj(spec, field, {"distribution", "value", "low", "high", "sigma", "preserve_total", "values"})
    distribution = d.get("distribution")
    if distribution not in ("fixed", "uniform_int", "uniform", "lognormal", "choice"):
        raise ValueError(f"{field}: unknown distribution")
    expected = {"fixed": {"distribution", "value"},
                "uniform_int": {"distribution", "low", "high"},
                "uniform": {"distribution", "low", "high"},
                "lognormal": {"distribution", "sigma"},
                "choice": {"distribution", "values"}}[distribution]
    if field in MONEY_FIELDS and distribution in {"uniform_int", "lognormal", "fixed"}:
        expected = expected | {"preserve_total"}
    if set(d) - expected or not (expected - {"preserve_total"}) <= set(d):
        raise ValueError(f"{field}: invalid or missing fields for {distribution}")
    if "preserve_total" in d and type(d["preserve_total"]) is not bool:
        raise ValueError(f"{field}: preserve_total must be boolean")
    if distribution == "fixed":
        if type(d["value"]) not in (str, int, float, bool) or (isinstance(d["value"], float) and not math.isfinite(d["value"])):
            raise ValueError(f"{field}: invalid fixed value")
    if distribution in {"uniform", "uniform_int"}:
        if distribution == "uniform_int":
            _nonnegative_int(d["low"], f"{field}.low", I64MAX-1)
            _nonnegative_int(d["high"], f"{field}.high", I64MAX-1)
        else:
            _number(d["low"], f"{field}.low", minimum=0 if field != "skills" else 0.01, maximum=100)
            _number(d["high"], f"{field}.high", minimum=0 if field != "skills" else 0.01, maximum=100)
        if d["low"] > d["high"]:
            raise ValueError(f"{field}: low cannot exceed high")
    if distribution == "lognormal":
        _number(d["sigma"], f"{field}.sigma", minimum=0, maximum=3)
    if distribution == "choice":
        if not isinstance(d["values"], list) or not 1 <= len(d["values"]) <= 100:
            raise ValueError(f"{field}: choice values must be a nonempty short list")
        if any(type(v) not in (str, int, float, bool) or (type(v) is float and not math.isfinite(v)) for v in d["values"]):
            raise ValueError(f"{field}: choice values must be finite scalar literals")
    if not scenario_field:
        if field in MONEY_FIELDS and distribution not in {"fixed", "uniform_int", "lognormal"}:
            raise ValueError(f"{field}: require nonnegative integer or lognormal distribution")
        if field in {"price_multiplier", "skills", "participation_probability", "household_savings_fraction"} and distribution not in {"fixed", "uniform"}:
            raise ValueError(f"{field}: require fixed or uniform distribution")
        limits = {"price_multiplier": (0.01, 10.0), "skills": (0.01, 100.0),
                  "participation_probability": (0.0, 1.0), "household_savings_fraction": (0.0, 1.0)}
        if field in limits:
            candidates = [d["value"]] if distribution == "fixed" else [d["low"], d["high"]]
            for val in candidates:
                _number(val, field, minimum=limits[field][0], maximum=limits[field][1])
        if field in MONEY_FIELDS and distribution == "fixed":
            _nonnegative_int(d["value"], f"{field}.value")


def validate_resolved(genesis: Any, scenario: Scenario) -> None:
    if genesis is None:
        return
    d = _obj(genesis, "world_genesis", {"schema_version", "mode", "seed", "initialization", "plan_sha256"})
    if d.get("schema_version") != 1 or d.get("mode") not in MODES:
        raise ValueError("unsupported World Genesis version or mode")
    _nonnegative_int(d.get("seed"), "world_genesis.seed")
    digest = d.get("plan_sha256")
    if type(digest) is not str or len(digest) != 64 or any(x not in "0123456789abcdef" for x in digest):
        raise ValueError("invalid plan_sha256")
    config = _obj(d.get("initialization"), "world_genesis.initialization", set(INITIAL_FIELDS))
    if d["mode"] == "configured" and any(x.get("distribution") not in ("fixed",) for x in config.values() if type(x) is dict):
        raise ValueError("configured worlds cannot use stochastic initial distributions")
    for field, spec in config.items():
        validate_spec(spec, field=field)
    if "firm_capital_units" in config and not scenario.capital_enabled:
        raise ValueError("firm capital distributions require capital_enabled")


def _scenario_spec(field: str, spec: dict) -> None:
    validate_spec(spec, field=field, scenario_field=True)
    if spec["distribution"] == "lognormal":
        raise ValueError("lognormal not supported for scalar scenario parameters")


def _sample_scenario(spec: dict, rng: np.random.Generator) -> Any:
    dist = spec["distribution"]
    if dist == "fixed":
        return spec["value"]
    if dist == "choice":
        return spec["values"][int(rng.integers(0, len(spec["values"])))]
    if dist == "uniform_int":
        return int(rng.integers(spec["low"], spec["high"] + 1))
    if dist == "uniform":
        return float(rng.uniform(spec["low"], spec["high"]))
    raise AssertionError(dist)


def resolve_plan(plan: dict[str, Any]) -> Scenario:
    """Sample high-level world parameters exactly once; return portable scenario."""
    from civitas.model import Scenario
    d = _obj(plan, "genesis plan", {"schema_version", "mode", "seed", "base_scenario", "scenario_draws", "initialization"})
    if d.get("schema_version") != 1 or d.get("mode") not in MODES:
        raise ValueError("unsupported genesis plan version or mode")
    seed = _nonnegative_int(d.get("seed"), "plan.seed")
    base = _obj(d.get("base_scenario"), "base_scenario", set(Scenario.__dataclass_fields__) | {"schema_version"})
    if "world_genesis" in base:
        raise ValueError("base_scenario cannot contain another world_genesis")
    draws = _obj(d.get("scenario_draws", {}), "scenario_draws", set(SCENARIO_DRAW_FIELDS))
    initialization = _obj(d.get("initialization", {}), "initialization", set(INITIAL_FIELDS))
    if d["mode"] == "configured" and any(x.get("distribution") != "fixed" for x in draws.values() if type(x) is dict):
        raise ValueError("configured world forbids stochastic scalar draws")
    for field, spec in draws.items():
        _scenario_spec(field, spec)
    if d["mode"] == "randomized" and not any(
        item.get("distribution") != "fixed" for item in list(draws.values()) + list(initialization.values())
        if type(item) is dict
    ):
        raise ValueError("randomized mode requires at least one stochastic parameter")
    raw = dict(base)
    raw.setdefault("name", f"civitas_{d['mode']}_{seed}")
    raw.setdefault("seed", seed)
    rng = np.random.default_rng(np.random.SeedSequence([seed, 710001]))
    for field in sorted(draws):
        raw[field] = _sample_scenario(draws[field], rng)
    raw["world_genesis"] = {"schema_version": 1, "mode": d["mode"],
                            "seed": seed, "initialization": json.loads(canonical(initialization)),
                            "plan_sha256": _digest(plan)}
    return Scenario.from_dict(raw)


def default_plan(*, mode: str = "hybrid", seed: int = 42,
                 name: str = "genesis_world", population: int = 10000) -> dict:
    """Useful ready-to-run defaults; overrides can be provided by plan JSON."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {sorted(MODES)}")
    _nonnegative_int(seed, "seed")
    _nonnegative_int(population, "population")
    base = {"name": name, "population": population, "seed": seed}
    initialization: dict[str, dict] = {}
    draws: dict[str, dict] = {}
    if mode in {"hybrid", "randomized"}:
        initialization = {
            "household_cash_cents": {"distribution": "lognormal", "sigma": 0.7, "preserve_total": True},
            "firm_cash_cents": {"distribution": "lognormal", "sigma": 0.5, "preserve_total": True},
            "price_multiplier": {"distribution": "uniform", "low": 0.95, "high": 1.05},
            "skills": {"distribution": "uniform", "low": 0.75, "high": 1.25},
        }
    if mode == "randomized":
        draws = {
            "population": {"distribution": "uniform_int", "low": max(1, population * 3 // 4),
                           "high": max(1, population * 5 // 4)},
            "firms_per_sector": {"distribution": "choice", "values": [2, 3, 4, 6]},
            "labor_participation": {"distribution": "uniform", "low": 0.65, "high": 0.85},
            "ownership_fraction": {"distribution": "uniform", "low": 0.03, "high": 0.15},
            "tax_rate": {"distribution": "uniform", "low": 0, "high": 0.25},
            "household_savings_rate": {"distribution": "uniform", "low": 0, "high": 0.30},
        }
    return {"schema_version": 1, "mode": mode, "seed": seed,
            "base_scenario": base, "scenario_draws": draws,
            "initialization": initialization}


def _substream(seed: int, label: str) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence([seed, 710002, STREAM_TAGS[label]]))


def _spread_exact(total: int, weights: np.ndarray) -> np.ndarray:
    """Hamilton largest-remainder allocation with *integer* arithmetic."""
    if len(weights) == 0:
        if total:
            raise ValueError("cannot distribute a nonzero endowment among zero accounts")
        return np.zeros(0, dtype=np.int64)
    if total < 0 or total > I64MAX:
        raise ValueError("total endowment out of signed-int64 range")
    quantized = [max(1, int(float(w) * 1_000_000)) for w in weights]
    denominator = sum(quantized)
    q, r = zip(*(divmod(total * w, denominator) for w in quantized))
    allocated = list(q)
    missing = total - sum(allocated)
    # Tie-breaking by account ID makes allocation fully deterministic.
    for ix in sorted(range(len(weights)), key=lambda i: (-r[i], i))[:missing]:
        allocated[ix] += 1
    return np.asarray(allocated, dtype=np.int64)


def _sample_accounts(field: str, spec: dict, base: np.ndarray, seed: int) -> np.ndarray:
    n = len(base)
    if n == 0:
        return base.copy()
    rng = _substream(seed, field)
    distribution = spec["distribution"]
    if distribution == "fixed":
        samples = np.full(n, spec["value"], dtype=np.int64)
    elif distribution == "uniform_int":
        samples = rng.integers(spec["low"], spec["high"] + 1, size=n, dtype=np.int64)
    else:
        samples = rng.lognormal(mean=-0.5 * float(spec["sigma"]) ** 2,
                                sigma=float(spec["sigma"]), size=n)
    if spec.get("preserve_total", distribution != "fixed"):
        return _spread_exact(sum(map(int, base)), samples)
    if distribution == "lognormal":
        # Nonpreserving draws use the *baseline per-account* endowment as mean.
        # This does not alter a historical scenario's cash unless explicitly chosen.
        if not np.all(base == base[0]):
            raise ValueError("lognormal unpreserved requires equal baseline units")
        samples = np.rint(samples * int(base[0]))
        if not np.all(np.isfinite(samples)) or np.any(samples > I64MAX):
            raise ValueError("sampled monetary values overflow signed int64")
        samples = np.asarray(samples, dtype=np.int64)
    if sum(map(int, samples)) > I64MAX:
        raise ValueError("sampled total exceeds signed int64")
    return samples


def apply_initialization(state: State, scenario: Scenario) -> None:
    """Replace selected initial attributes, without consuming engine RNG draws."""
    genesis = scenario.world_genesis
    if genesis is None:
        return
    config = genesis["initialization"]
    seed = genesis["seed"]
    for label, attr in (("household_cash_cents", "household_cash"),
                        ("firm_cash_cents", "firm_cash"),
                        ("firm_capital_units", "firm_capital")):
        if label in config:
            setattr(state, attr, _sample_accounts(label, config[label], getattr(state, attr), seed))
    if "household_savings_fraction" in config:
        d = config["household_savings_fraction"]
        rng = _substream(seed, "household_savings_fraction")
        fractions = (np.full(len(state.household_cash), float(d["value"]))
                     if d["distribution"] == "fixed" else
                     rng.uniform(d["low"], d["high"], size=len(state.household_cash)))
        deposits = np.floor(state.household_cash.astype(np.float64) * fractions)
        if np.any(~np.isfinite(deposits)) or np.any(deposits < 0):
            raise ValueError("invalid generated initial savings")
        # Float multiplication can round one cent above integer cash near i64max;
        # guard using exact Python integer min at the account boundary.
        transfer = np.asarray([min(int(cash), int(amount))
                               for cash, amount in zip(state.household_cash, deposits, strict=True)],
                              dtype=np.int64)
        state.household_cash -= transfer
        state.household_savings += transfer
    if "price_multiplier" in config:
        d = config["price_multiplier"]
        rng = _substream(seed, "price_multiplier")
        multipliers = (np.full(len(state.prices), float(d["value"]))
                       if d["distribution"] == "fixed" else rng.uniform(d["low"], d["high"], size=len(state.prices)))
        values = np.rint(state.prices.astype(np.float64) * multipliers)
        if not np.all(np.isfinite(values)) or np.any(values > I64MAX):
            raise ValueError("generated price overflow")
        state.prices = np.maximum(scenario.price_floor_cents, values.astype(np.int64))
    if "skills" in config:
        d = config["skills"]
        rng = _substream(seed, "skills")
        state.skills = (np.full_like(state.skills, float(d["value"]))
                        if d["distribution"] == "fixed" else rng.uniform(d["low"], d["high"], size=state.skills.shape))
    if "participation_probability" in config:
        d = config["participation_probability"]
        rng = _substream(seed, "participation_probability")
        probabilities = (float(d["value"]) if d["distribution"] == "fixed"
                         else rng.uniform(d["low"], d["high"], size=len(state.participation)))
        state.participation = rng.random(len(state.participation)) < probabilities
    # Book basis depends on realized physical capital. The initial acquisition
    # convention is the sector's reference posted price, not future sale prices.
    state.initial_capital_total = sum(map(int, state.firm_capital))
    if scenario.capital_enabled and scenario.cost_basis_accounting_enabled:
        quote = next(sec.price_cents for sec in scenario.sectors if sec.name == scenario.capital_input_sector)
        basis = [int(v) * quote for v in state.firm_capital]
        if sum(basis) > I64MAX:
            raise ValueError("generated capital historical-cost basis overflow")
        state.firm_capital_basis_cents = np.asarray(basis, dtype=np.int64)
    state.initial_total_money = (sum(map(int, state.household_cash)) +
                                 sum(map(int, state.household_savings)) +
                                 sum(map(int, state.firm_cash)))
    if state.initial_total_money > I64MAX:
        raise ValueError("generated total money exceeds signed int64")
    state.validate()


def state_fingerprint(state: State) -> str:
    """Stable SHA-256 of economically relevant initial state (no private names)."""
    sha = hashlib.sha256(b"CIVITAS-GENESIS-STATE-v1\0")
    fields = ("household_of_agent", "participation", "skills", "household_cash",
              "household_savings", "firm_cash", "firm_capital", "firm_inventory_basis_cents",
              "firm_capital_basis_cents", "inventory", "prices", "last_sales", "last_unmet",
              "last_employment", "household_loan_assets_cents", "firm_loan_liabilities_cents")
    for name in fields:
        a = np.asarray(getattr(state, name))
        if a.dtype.kind == "f":
            a = a.astype("<f8", copy=False)
        elif a.dtype.kind == "b":
            a = a.astype("u1", copy=False)
        else:
            a = a.astype("<i8", copy=False)
        sha.update(name.encode() + b"\0" + canonical(a.shape).encode() + b"\0" + a.tobytes())
    for owners in state.firm_owner_households:
        a = np.asarray(owners, dtype="<i8")
        sha.update(len(a).to_bytes(8, "little") + a.tobytes())
    sha.update(canonical({"resource": state.resource, "gov_cash": state.gov_cash,
                          "initial_total_money": state.initial_total_money,
                          "initial_capital_total": state.initial_capital_total}).encode())
    return sha.hexdigest()


def world_manifest(scenario: Scenario, state: State, rng_state: dict) -> dict:
    from civitas.persistence import config_digest
    return {"world_genesis_schema_version": 1, "mode": scenario.world_genesis["mode"],
            "seed": scenario.world_genesis["seed"],
            "plan_sha256": scenario.world_genesis["plan_sha256"],
            "scenario_sha256": config_digest(scenario),
            "initial_state_sha256": state_fingerprint(state),
            "engine_rng_state_sha256": _digest(rng_state),
            "population": scenario.population, "households": len(state.household_cash),
            "firms": len(state.firm_cash),
            "total_initial_money_cents": state.initial_total_money,
            "household_initial_money_cents": sum(map(int, state.household_cash)),
            "household_initial_savings_cents": sum(map(int, state.household_savings)),
            "firm_initial_money_cents": sum(map(int, state.firm_cash)),
            "total_initial_capital_units": state.initial_capital_total,
            "resource_initial_units": state.resource,
            "caveat": "Synthetic initial conditions; not calibrated demographic or financial data."}


def write_world(output: str | Path, plan: dict[str, Any], *, force: bool = False) -> dict:
    from civitas.engine import Simulation
    from civitas.persistence import checkpoint_save
    scenario = resolve_plan(plan)
    sim = Simulation(scenario)
    path = Path(output)
    target_names = ("plan.json", "scenario.json", "manifest.json", "initial_checkpoint.npz")
    if any((path / name).exists() for name in target_names) and not force:
        raise FileExistsError("world already exists; use --force for an intentional replacement")
    manifest = world_manifest(scenario, sim.state, sim.rng.bit_generator.state)
    path.mkdir(parents=True, exist_ok=True)
    (path / "plan.json").write_text(json.dumps(plan, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (path / "scenario.json").write_text(json.dumps(scenario.to_dict(), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    checkpoint_save(path / "initial_checkpoint.npz", scenario, sim.state, sim.rng.bit_generator.state)
    (path / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return manifest


def verify_world(path: str | Path) -> dict:
    """Verify saved genesis provenance against both stored and regenerated states."""
    from civitas.engine import Simulation
    from civitas.model import Scenario
    from civitas.persistence import checkpoint_load
    path = Path(path)
    plan = json.loads((path / "plan.json").read_text(encoding="utf-8"))
    scenario = Scenario.from_file(path / "scenario.json")
    expected = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    if scenario.to_dict() != resolve_plan(plan).to_dict():
        raise ValueError("saved scenario does not match resolved plan")
    saved_scenario, stored_state, stored_rng = checkpoint_load(path / "initial_checkpoint.npz")
    if saved_scenario.to_dict() != scenario.to_dict() or stored_state.step != 0:
        raise ValueError("initial checkpoint scenario or step mismatch")
    saved = world_manifest(scenario, stored_state, stored_rng)
    if saved != expected:
        raise ValueError("initial checkpoint or genesis manifest mismatch")
    replay = Simulation(scenario)
    realized = world_manifest(scenario, replay.state, replay.rng.bit_generator.state)
    if realized != expected:
        raise ValueError("generated world is not reproducible from saved scenario")
    return {"verified": True, **realized}
