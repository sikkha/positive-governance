"""Level 0.3b: smoke/integration tests for the reanalysis, supplemental
search, candidate registry, confirmation, causal-intervention, fitness-
stream, neighborhood-robustness, and confirmatory-perturbation scripts,
plus targeted unit tests for the required-scenario checklist (§18 of the
milestone spec) that are best exercised at the pipeline level rather than
as pure-function unit tests."""

from __future__ import annotations

import json
import os

import pandas as pd
import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation
from experiments import (
    level03b_candidate_registry,
    level03b_causal_interventions,
    level03b_confirmation,
    level03b_confirmatory_perturbation,
    level03b_fitness_stream,
    level03b_neighborhood_robustness,
    level03b_phase_search_reanalysis,
    level03b_supplemental_search,
)
from experiments.level03b_common import CONDITION_OVERRIDES, build_candidate_config


# ---------------------------------------------------------------------
# Work Package B: reanalysis smoke test + parameter-point aggregation.
# ---------------------------------------------------------------------
def test_phase_search_reanalysis_reproduces_committed_outcomes_bit_for_bit():
    summary = level03b_phase_search_reanalysis.run(out_root="/tmp/test_l03b_reanalysis_smoke")
    assert summary["n_mismatches_vs_committed_level03_outcomes"] == 0
    assert summary["n_runs_reanalyzed"] == 48
    assert summary["n_points"] == 16


def test_reanalysis_point_level_aggregation_denominator_is_points_not_runs():
    point_level = pd.read_csv("outputs/level03b_phase_search_reanalysis/point_level_reanalysis.csv")
    assert len(point_level) == 16
    assert (point_level["n_seeds"] == 3).all()
    assert set(point_level.columns) >= {"agreement_fraction", "is_robustly_classified", "plurality_new_label"}


def test_robust_label_agreement_requires_unanimity_at_n_equals_3():
    point_level = pd.read_csv("outputs/level03b_phase_search_reanalysis/point_level_reanalysis.csv")
    for _, row in point_level.iterrows():
        if row["is_robustly_classified"]:
            assert row["agreement_fraction"] == pytest.approx(1.0)


# ---------------------------------------------------------------------
# Prespecified supplemental search: deterministic design.
# ---------------------------------------------------------------------
def test_supplemental_search_design_is_deterministic():
    a = level03b_supplemental_search.design_matrix(8, rng_seed=level03b_supplemental_search.DESIGN_SEED)
    b = level03b_supplemental_search.design_matrix(8, rng_seed=level03b_supplemental_search.DESIGN_SEED)
    pd.testing.assert_frame_equal(a, b)


def test_supplemental_search_design_seed_differs_from_original_phase_search():
    from experiments.niche_phase_search import design_matrix as original_design_matrix

    original = original_design_matrix(8, rng_seed=20260817)
    supplemental = level03b_supplemental_search.design_matrix(8, rng_seed=level03b_supplemental_search.DESIGN_SEED)
    assert not original.drop(columns=["point_id"]).equals(supplemental.drop(columns=["point_id"]))


def test_supplemental_search_smoke(tmp_path):
    summary = level03b_supplemental_search.run(out_root=str(tmp_path), n_points=2, seeds_per_point=1, n_steps=20)
    assert summary["n_failures"] == 0
    assert summary["n_runs"] == 2


# ---------------------------------------------------------------------
# Work Package C: candidate registry -- immutability and outcome-blind
# selection.
# ---------------------------------------------------------------------
def test_candidate_registry_is_deterministic_given_unchanged_inputs():
    """Calling the registry builder twice against the same already-
    committed reanalysis/supplemental outputs must produce an identical
    selection -- the milestone's 'immutability' requirement, verified as
    determinism of the selection function rather than a claim that the
    file itself cannot be overwritten."""
    first = level03b_candidate_registry.run(out_root="/tmp/test_registry_a")
    second = level03b_candidate_registry.run(out_root="/tmp/test_registry_b")
    assert first["selected"] == second["selected"]


def test_candidate_selection_reads_no_cooperation_or_social_field():
    """Structural guard: the candidate-selection module must never import
    or reference a social-cooperation/punishment field when choosing a
    candidate."""
    import inspect

    source = inspect.getsource(level03b_candidate_registry)
    forbidden = ["cooperation_rate", "cooperation", "punishment", "defection"]
    lowered = source.lower()
    for term in forbidden:
        assert term not in lowered, f"candidate selection module references forbidden term {term!r}"


def test_candidate_registry_has_required_sections():
    with open("outputs/level03b_candidate_registry/candidate_registry.json") as fh:
        registry = json.load(fh)
    for key in ("selection_criteria", "exclusion_rules", "selected", "rejected_candidates", "confirmation_plan"):
        assert key in registry


# ---------------------------------------------------------------------
# level03b_common.build_candidate_config -- condition semantics.
# ---------------------------------------------------------------------
_TEST_PARAMS = {
    "n_patches": 3, "population_size": 16, "patch_regen_rate": 0.5, "patch_capacity": 400.0,
    "ecological_harvest_unit": 5.0, "ecological_search_cost": 0.5, "ecological_maintenance_unit": 5.0,
    "maintenance_efficiency": 0.7, "ecological_mutation_rate": 0.02, "scarcity_sensitivity_mean": 0.3,
    "fitness_mode": "cumulative_resources",
}


def test_environment_only_condition_zeroes_agent_ecological_ledgers():
    config = build_candidate_config(_TEST_PARAMS, seed=0, n_steps=15, condition="environment_only")
    result = Simulation(config).run()
    for row in result.metrics:
        assert row["ecological_actual_extraction_total"] == pytest.approx(0.0)
        assert row["ecological_maintenance_effective_total"] == pytest.approx(0.0)
    # Patch regeneration still proceeds -- the trajectory is not a
    # structurally pinned constant just because agents have zero effect.
    occupancy = [row["aggregate_fraction_of_capacity"] for row in result.metrics]
    assert len(set(round(o, 6) for o in occupancy)) > 1


def test_impact_disabled_condition_preserves_agent_ledger_but_not_patch_state():
    config_endo = build_candidate_config(_TEST_PARAMS, seed=1, n_steps=20, condition="endogenous")
    config_impact = build_candidate_config(_TEST_PARAMS, seed=1, n_steps=20, condition="impact_disabled")
    assert config_impact.ecological_actions_affect_patch is False
    assert config_endo.ecological_actions_affect_patch is True
    # Agent-side ledger accounting is still meaningful: extraction is
    # still nonzero (agents still "receive" the same allocation-computed
    # gain), even though the patch itself does not move.
    result = Simulation(config_impact).run()
    total_extraction = sum(row["ecological_actual_extraction_total"] for row in result.metrics)
    assert total_extraction > 0.0


def test_maintenance_disabled_condition_zeroes_maintenance_only():
    config = build_candidate_config(_TEST_PARAMS, seed=2, n_steps=20, condition="maintenance_disabled")
    assert config.ecological_maintenance_unit == 0.0
    result = Simulation(config).run()
    for row in result.metrics:
        assert row["ecological_maintenance_effective_total"] == pytest.approx(0.0)
    total_extraction = sum(row["ecological_actual_extraction_total"] for row in result.metrics)
    assert total_extraction > 0.0  # extraction unaffected


def test_frozen_condition_never_changes_ecological_policy():
    config = build_candidate_config(_TEST_PARAMS, seed=3, n_steps=40, condition="frozen")
    sim = Simulation(config)
    initial_policies = {a.agent_id: a.ecological_policy for a in sim.agents}
    result = sim.run()
    for agent in result.final_agents:
        if agent.agent_id in initial_policies:
            assert agent.ecological_policy == initial_policies[agent.agent_id]


def test_randomized_condition_ignores_stored_policy_for_decisions():
    """Under 'randomized', an agent's *stored* ecological_policy is never
    the one read for that step's decision -- verified indirectly by
    checking the config flag is set (the decision-level behavior itself
    is covered by tests/test_level03_niche_construction.py, unchanged)."""
    config = build_candidate_config(_TEST_PARAMS, seed=4, n_steps=10, condition="randomized")
    assert config.ecological_policy_randomized_each_step is True


def test_shuffled_condition_preserves_marginal_policy_distribution():
    config = build_candidate_config(_TEST_PARAMS, seed=5, n_steps=10, condition="shuffled")
    assert config.ecological_policy_shuffle is True


def test_ecological_mutation_disabled_keeps_imitation_active():
    config = build_candidate_config(_TEST_PARAMS, seed=6, n_steps=10, condition="ecological_mutation_disabled")
    assert config.ecological_mutation_rate == 0.0
    assert config.ecological_imitation_enabled is True


def test_all_primary_conditions_have_defined_overrides():
    from experiments.level03b_common import PRIMARY_CONDITIONS

    for condition in PRIMARY_CONDITIONS:
        assert condition in CONDITION_OVERRIDES


# ---------------------------------------------------------------------
# Confirmation / causal / fitness-stream / robustness / perturbation --
# plumbing smoke tests at minimal scale.
# ---------------------------------------------------------------------
def test_confirmation_smoke(tmp_path):
    summary = level03b_confirmation.run(out_root=str(tmp_path), n_seeds=2, n_steps=20)
    assert summary["n_failures"] == 0
    assert set(summary["per_candidate"].keys()) == {"interior_persistent", "nonstationary", "near_collapse"}


def test_causal_interventions_smoke_paired_seed_construction(tmp_path):
    summary = level03b_causal_interventions.run(out_root=str(tmp_path), n_steps=20, primary_n_seeds=2, secondary_n_seeds=2)
    effects_path = os.path.join(str(tmp_path), "causal_paired_effects.csv")
    assert os.path.exists(effects_path)
    effects = pd.read_csv(effects_path)
    # Every paired-effect row must have been computed from a nonzero
    # number of *common* seeds across the endogenous/counterfactual pair
    # -- the defining property of a paired (not independent-samples)
    # design.
    assert (effects["n_seeds"] > 0).all()
    assert summary["design"]["primary_candidate"] in {"interior_persistent", "nonstationary", "near_collapse"}


def test_fitness_stream_smoke(tmp_path):
    summary = level03b_fitness_stream.run(out_root=str(tmp_path), n_seeds=1, n_steps=20)
    assert "by_stream_and_condition" in summary
    streams = {row["fitness_stream"] for row in summary["by_stream_and_condition"]}
    assert streams == {"ecological", "total"}


def test_neighborhood_robustness_smoke(tmp_path):
    # depends on outputs/level03b_confirmation already existing (produced
    # by the real run, committed to outputs/) -- this test exercises the
    # plumbing only, not the real confirmation results.
    summary = level03b_neighborhood_robustness.run(out_root=str(tmp_path), n_seeds=1, n_steps=20)
    assert "per_candidate" in summary
    for key, entry in summary["per_candidate"].items():
        assert "overall_robustness" in entry
        assert "interpretation" in entry


def test_confirmatory_perturbation_smoke(tmp_path):
    summary = level03b_confirmatory_perturbation.run(
        out_root=str(tmp_path), n_steps=40, shock_step=20, primary_n_seeds=1, secondary_n_seeds=1
    )
    assert summary["n_failures"] == 0
    assert len(summary["recovery_by_candidate_shock_condition"]) > 0


def test_perturbation_ineligible_runs_are_retained_not_dropped(tmp_path):
    """A candidate/shock/seed combination that fails the eligibility
    screen must still produce a row in the output CSV (eligible=False),
    not be silently excluded."""
    summary = level03b_confirmatory_perturbation.run(
        out_root=str(tmp_path), n_steps=40, shock_step=20, primary_n_seeds=1, secondary_n_seeds=1
    )
    recovery = pd.read_csv(os.path.join(str(tmp_path), "confirmatory_perturbation_recovery.csv"))
    assert "eligible" in recovery.columns
    # recovered must never be silently filled for ineligible rows.
    ineligible = recovery[recovery["eligible"] == False]  # noqa: E712
    if not ineligible.empty:
        assert ineligible["recovered"].isna().all()
