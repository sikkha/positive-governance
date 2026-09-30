"""Level 0.3, Work Packages F/G/H/J: smoke tests for the four experiment
runner scripts, at minimal scale (these are integration tests of the
runners' plumbing -- manifests, failure reporting, output files -- not a
re-run of the full documented-scale experiments, which are executed
separately and their results discussed in the scientific note)."""

from __future__ import annotations

import json
import os

import pandas as pd
import pytest

from experiments import (
    niche_causal_interventions,
    niche_perturbation_recovery,
    niche_phase_search,
    niche_viability_threshold_sweep,
)


def test_niche_causal_interventions_smoke(tmp_path):
    summary = niche_causal_interventions.run(str(tmp_path), n_seeds=2, population_size=12, n_steps=24)
    assert summary["n_failures"] == 0
    assert os.path.exists(tmp_path / "niche_causal_trajectories.csv")
    assert os.path.exists(tmp_path / "niche_causal_paired_differences.csv")
    trajectories = pd.read_csv(tmp_path / "niche_causal_trajectories.csv")
    assert set(trajectories["condition"]) == set(niche_causal_interventions.CONDITIONS)
    assert set(summary["mean_by_condition"]) == set(niche_causal_interventions.CONDITIONS)


def test_niche_viability_threshold_sweep_smoke(tmp_path):
    summary = niche_viability_threshold_sweep.run(str(tmp_path), n_seeds=1, population_size=12, n_steps=24)
    assert summary["n_failures"] == 0
    points = pd.read_csv(tmp_path / "niche_viability_sweep_points.csv")
    assert set(points["mode"]) <= {"none", "dormancy_recovery", "removal_replacement"}
    assert (points["n_entered_distress"] >= 0).all()


def test_niche_phase_search_smoke(tmp_path):
    summary = niche_phase_search.run(str(tmp_path), n_points=3, seeds_per_point=1, n_steps=16)
    assert summary["n_failures"] == 0
    assert summary["n_runs"] == 3
    outcomes = pd.read_csv(tmp_path / "niche_phase_search_outcomes.csv")
    assert len(outcomes) == 3
    assert outcomes["region_label"].isin(
        {"depleted", "abundant", "interior-persistent", "oscillatory", "intermittent",
         "spatially-polarized", "recovering", "non-recovering", "unclassified"}
    ).all()


def test_niche_phase_search_design_is_reproducible():
    a = niche_phase_search.design_matrix(5, rng_seed=1)
    b = niche_phase_search.design_matrix(5, rng_seed=1)
    pd.testing.assert_frame_equal(a, b)
    c = niche_phase_search.design_matrix(5, rng_seed=2)
    assert not a.equals(c)


def test_niche_perturbation_recovery_smoke(tmp_path, monkeypatch):
    monkeypatch.setattr(niche_perturbation_recovery, "N_STEPS", 30)
    monkeypatch.setattr(niche_perturbation_recovery, "SHOCK_STEP", 15)
    monkeypatch.setattr(niche_perturbation_recovery, "PRE_SHOCK_WINDOW", 5)
    monkeypatch.setattr(niche_perturbation_recovery, "TEMPORARY_SHOCK_DURATION", 5)
    summary = niche_perturbation_recovery.run(str(tmp_path), n_seeds=1, population_size=14, n_steps=30)
    assert summary["n_failures"] == 0
    recovery = pd.read_csv(tmp_path / "niche_perturbation_recovery.csv")
    assert set(recovery["shock_type"]) == set(niche_perturbation_recovery.SHOCK_TYPES)
    # Every shock has a matched unperturbed control trajectory recorded.
    trajectories = pd.read_csv(tmp_path / "niche_perturbation_trajectories.csv")
    assert set(trajectories["arm"]) == {"control", "shocked"}


def test_niche_perturbation_removal_actually_isolates_agents():
    """The documented 'removal' semantics (alive=False + edges severed)
    must actually take effect -- not a silent no-op."""
    from abm_governance.core.config import SimulationConfig
    from abm_governance.simulation import Simulation

    config = SimulationConfig.level03_patches_default(seed=0, population_size=16, n_steps=1, mean_degree=4)
    sim = Simulation(config)
    target_id = sim.agents[0].agent_id
    n_edges_before = sim.graph.degree(target_id)
    assert n_edges_before > 0
    niche_perturbation_recovery._remove_agents(sim, [target_id])
    assert sim.agents_by_id[target_id].alive is False
    assert sim.graph.degree(target_id) == 0
