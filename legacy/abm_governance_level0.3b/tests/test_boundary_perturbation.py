"""Level 0.2, Work Package J: the boundary-perturbation experiment
runner (experiments/boundary_perturbation.py)."""

from __future__ import annotations

import importlib.util
import os
import sys

import pytest

_PATH = os.path.join(os.path.dirname(__file__), "..", "experiments", "boundary_perturbation.py")
_spec = importlib.util.spec_from_file_location("boundary_perturbation", _PATH)
bp = importlib.util.module_from_spec(_spec)
sys.modules["boundary_perturbation"] = bp
_spec.loader.exec_module(bp)


def _boundary_params():
    return {
        "environment_regen_rate": 0.7, "environment_capacity": 800.0, "subsistence_cost": 0.5,
        "payoff_temptation": 4.0, "payoff_reward": 2.5, "distress_threshold": -2.0,
    }


def test_shock_kinds_are_all_valid_perturbation_kinds():
    from abm_governance.core.config import VALID_PERTURBATION_KINDS

    for kind in bp.SHOCK_KINDS:
        assert kind in VALID_PERTURBATION_KINDS


def test_build_config_applies_perturbation_only_for_non_none_shock(monkeypatch):
    monkeypatch.setattr(bp, "N_STEPS", 20)
    monkeypatch.setattr(bp, "PRE_SHOCK_STEPS", 5)
    monkeypatch.setattr(bp, "SHOCK_DURATION", 3)
    monkeypatch.setattr(bp, "POPULATION_SIZE", 8)

    control_spec = bp.RunSpec(boundary_point_id="x", shock_kind="none", seed=0, params=_boundary_params())
    control_config = bp._build_config(control_spec)
    assert control_config.perturbations == ()

    shock_spec = bp.RunSpec(boundary_point_id="x", shock_kind="resource_depletion", seed=0, params=_boundary_params())
    shock_config = bp._build_config(shock_spec)
    assert len(shock_config.perturbations) == 1
    assert shock_config.perturbations[0]["kind"] == "resource_depletion"
    assert shock_config.perturbations[0]["start_step"] == 5


def test_run_one_end_to_end_tiny(monkeypatch):
    monkeypatch.setattr(bp, "N_STEPS", 30)
    monkeypatch.setattr(bp, "PRE_SHOCK_STEPS", 10)
    monkeypatch.setattr(bp, "SHOCK_DURATION", 5)
    monkeypatch.setattr(bp, "POPULATION_SIZE", 10)

    spec = bp.RunSpec(boundary_point_id="x", shock_kind="resource_depletion", seed=0, params=_boundary_params())
    record = bp._run_one(spec)
    assert record["status"] == "ok", record.get("error")
    assert "pre_mean_occupancy" in record
    assert "recovered_after_shock" in record


def test_run_one_never_raises_on_bad_params():
    bad_spec = bp.RunSpec(
        boundary_point_id="x", shock_kind="none", seed=0,
        params={**_boundary_params(), "environment_capacity": -5.0},  # invalid: triggers ValueError
    )
    record = bp._run_one(bad_spec)
    assert record["status"] == "failed"
    assert record["error"] is not None


def test_aggregate_produces_one_row_per_point_and_shock():
    records = [
        {
            "boundary_point_id": "p1", "shock_kind": "none", "seed": s, "status": "ok",
            "pre_mean_occupancy": 0.5, "during_mean_occupancy": 0.5, "post_mean_occupancy": 0.5,
            "pre_unmet_demand": 0.0, "during_unmet_demand": 0.0, "post_unmet_demand": 0.0,
            "pre_participation_rate": 0.9, "during_participation_rate": 0.9, "post_participation_rate": 0.9,
            "pre_policy_diversity_bits": 1.0, "during_policy_diversity_bits": 1.0, "post_policy_diversity_bits": 1.0,
            "pre_cooperation_rate": 0.6, "during_cooperation_rate": 0.6, "post_cooperation_rate": 0.6,
            "pre_turnover": 0.1, "post_turnover": 0.1,
            "post_shock_conditional_cooperation_rate": 0.6, "post_shock_unconditional_cooperation_rate": 0.55,
            "recovered_after_shock": s % 2 == 0,
        }
        for s in range(4)
    ]
    df = bp.aggregate(records)
    assert len(df) == 1
    assert df.iloc[0]["n_seeds"] == 4
    assert df.iloc[0]["fraction_recovered"] == pytest.approx(0.5)
