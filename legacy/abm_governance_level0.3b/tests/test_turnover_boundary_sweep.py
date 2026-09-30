"""Level 0.2, Work Package G: the boundary-region relationship-turnover
sweep runner (experiments/turnover_boundary_sweep.py)."""

from __future__ import annotations

import importlib.util
import os
import sys

import pytest

_PATH = os.path.join(os.path.dirname(__file__), "..", "experiments", "turnover_boundary_sweep.py")
_spec = importlib.util.spec_from_file_location("turnover_boundary_sweep", _PATH)
tbs = importlib.util.module_from_spec(_spec)
sys.modules["turnover_boundary_sweep"] = tbs
_spec.loader.exec_module(tbs)


def _boundary_params():
    return {
        "environment_regen_rate": 0.7, "environment_capacity": 800.0, "subsistence_cost": 0.5,
        "payoff_temptation": 4.0, "payoff_reward": 2.5, "distress_threshold": -2.0,
    }


def test_axis_sweeps_do_not_tune_toward_maximal_turnover():
    """Sanity check on the milestone's explicit instruction not to tune
    turnover to maximize movement: every axis includes at least one value
    that is *not* the most turnover-permissive extreme (i.e. this isn't a
    one-directional sweep toward "more turnover")."""
    assert len(tbs.AXIS_SWEEPS["exit_cost"]) >= 3
    assert min(tbs.AXIS_SWEEPS["exit_cost"]) < max(tbs.AXIS_SWEEPS["exit_cost"])
    assert set(tbs.AXIS_SWEEPS["relationship_exit_enabled"]) == {True, False}


def test_build_config_overrides_exactly_one_axis(monkeypatch):
    monkeypatch.setattr(tbs, "N_STEPS", 15)
    monkeypatch.setattr(tbs, "POPULATION_SIZE", 8)
    spec = tbs.RunSpec(boundary_point_id="x", axis="exit_cost", value=2.5, seed=0, params=_boundary_params())
    config = tbs._build_config(spec)
    assert config.exit_cost == pytest.approx(2.5)
    assert config.environment_capacity == pytest.approx(800.0)


def test_run_one_end_to_end_tiny(monkeypatch):
    monkeypatch.setattr(tbs, "N_STEPS", 20)
    monkeypatch.setattr(tbs, "POPULATION_SIZE", 10)
    spec = tbs.RunSpec(boundary_point_id="x", axis="mean_degree", value=3, seed=0, params=_boundary_params())
    record = tbs._run_one(spec)
    assert record["status"] == "ok", record.get("error")
    assert "relationship_turnover_rate" in record


def test_run_one_never_raises_on_bad_params():
    bad_spec = tbs.RunSpec(
        boundary_point_id="x", axis="exit_cost", value=1.0, seed=0,
        params={**_boundary_params(), "environment_capacity": -1.0},
    )
    record = tbs._run_one(bad_spec)
    assert record["status"] == "failed"
    assert record["error"] is not None


def test_aggregate_groups_by_point_axis_and_value():
    records = [
        {
            "boundary_point_id": "p1", "axis": "exit_cost", "value": v, "seed": s, "status": "ok",
            "relationship_turnover_rate": 0.1, "mean_relationship_age_final": 5.0,
            "component_count_final": 1, "largest_component_share_final": 1.0,
            "isolated_agent_count_final": 0, "policy_assortativity_final": 0.2,
            "edges_added_total": 10, "edges_removed_total": 8, "proposal_accepted_total": 12,
            "age_cooperation_correlation": 0.3, "final_cooperation_rate": 0.7, "final_mean_occupancy": 0.5,
        }
        for v in (0.2, 1.0)
        for s in range(3)
    ]
    df = tbs.aggregate(records)
    assert len(df) == 2
    assert set(df["value"]) == {0.2, 1.0}
    assert (df["n_seeds"] == 3).all()
