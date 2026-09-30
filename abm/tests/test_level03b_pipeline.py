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
    niche_phase_search,
)
from experiments.level03b_common import CONDITION_OVERRIDES, build_candidate_config

# ---------------------------------------------------------------------
# Level 1.1b, Work Package B: artifact-independent testing.
#
# The four tests below this comment (the historical-corpus-dependent
# variants) require ``outputs/niche_phase_search/`` (Level 0.3's original
# 16-point x 3-seed phase-search corpus) to already be committed in this
# checkout -- it is the ground truth a "reproduces committed outcomes
# bit-for-bit" check is checking *against*, so there is no way to
# meaningfully run that specific check without it (regenerating it here
# would just compare a freshly-generated file to itself, which tests
# nothing). Per the Level 1.1b brief: this is treated as an
# artifact-availability condition, not a source-code failure, and is
# *skipped* (never silently passed, never xfailed unconditionally) with a
# precise reason naming the exact missing path -- while the pipeline
# LOGIC itself (bit-for-bit reproduction, point-level aggregation, the
# denominator-is-points-not-runs distinction, the n=3 unanimity
# requirement) is additionally covered, unconditionally, by
# ``TestPhaseSearchReanalysisWithSyntheticFixture`` below using a tiny
# (2 points x 2 seeds x 20 steps) in-test-generated fixture produced by
# ``niche_phase_search.run()`` itself -- deterministic, self-contained,
# and independent of what historical artifacts happen to be present in
# any given checkout.
_NICHE_PHASE_SEARCH_DESIGN = "outputs/niche_phase_search/niche_phase_search_design.csv"
_NICHE_PHASE_SEARCH_OUTCOMES = "outputs/niche_phase_search/niche_phase_search_outcomes.csv"
_requires_niche_phase_search_corpus = pytest.mark.skipif(
    not (os.path.exists(_NICHE_PHASE_SEARCH_DESIGN) and os.path.exists(_NICHE_PHASE_SEARCH_OUTCOMES)),
    reason=(
        f"Level 0.3's historical phase-search corpus is not committed in this checkout "
        f"(missing {_NICHE_PHASE_SEARCH_DESIGN} and/or {_NICHE_PHASE_SEARCH_OUTCOMES}); "
        f"see TestPhaseSearchReanalysisWithSyntheticFixture for the artifact-independent "
        f"coverage of this same pipeline logic."
    ),
)
_REANALYSIS_POINT_LEVEL_CSV = "outputs/level03b_phase_search_reanalysis/point_level_reanalysis.csv"
_requires_committed_reanalysis_output = pytest.mark.skipif(
    not os.path.exists(_REANALYSIS_POINT_LEVEL_CSV),
    reason=(
        f"{_REANALYSIS_POINT_LEVEL_CSV} does not exist in this checkout (it is produced by "
        f"a real run of level03b_phase_search_reanalysis.run() against the historical Level "
        f"0.3 corpus, which is itself not committed here -- see "
        f"TestPhaseSearchReanalysisWithSyntheticFixture for artifact-independent coverage)."
    ),
)


# ---------------------------------------------------------------------
# Work Package B: reanalysis smoke test + parameter-point aggregation.
# ---------------------------------------------------------------------
@_requires_niche_phase_search_corpus
def test_phase_search_reanalysis_reproduces_committed_outcomes_bit_for_bit():
    summary = level03b_phase_search_reanalysis.run(out_root="/tmp/test_l03b_reanalysis_smoke")
    assert summary["n_mismatches_vs_committed_level03_outcomes"] == 0
    assert summary["n_runs_reanalyzed"] == 48
    assert summary["n_points"] == 16


@_requires_committed_reanalysis_output
def test_reanalysis_point_level_aggregation_denominator_is_points_not_runs():
    point_level = pd.read_csv("outputs/level03b_phase_search_reanalysis/point_level_reanalysis.csv")
    assert len(point_level) == 16
    assert (point_level["n_seeds"] == 3).all()
    assert set(point_level.columns) >= {"agreement_fraction", "is_robustly_classified", "plurality_new_label"}


@_requires_committed_reanalysis_output
def test_robust_label_agreement_requires_unanimity_at_n_equals_3():
    point_level = pd.read_csv("outputs/level03b_phase_search_reanalysis/point_level_reanalysis.csv")
    for _, row in point_level.iterrows():
        if row["is_robustly_classified"]:
            assert row["agreement_fraction"] == pytest.approx(1.0)


class TestPhaseSearchReanalysisWithSyntheticFixture:
    """Artifact-independent coverage of the same reanalysis-pipeline
    logic the three skip-guarded tests above exercise against the real
    historical corpus, using a tiny, fully self-contained, deterministic
    fixture instead: ``niche_phase_search.run()`` itself (the exact same
    code Level 0.3 used to produce the historical corpus in the first
    place) generates a 2-point x 2-seed x 20-step design/outcomes pair,
    which is then fed straight into
    ``level03b_phase_search_reanalysis.run()`` via its existing
    ``design_path``/``old_outcomes_path``/``n_steps`` parameters. Runs
    unconditionally, in every checkout, regardless of what historical
    artifacts happen to be present."""

    @classmethod
    @pytest.fixture(scope="class")
    def synthetic_reanalysis(cls, tmp_path_factory):
        corpus_root = str(tmp_path_factory.mktemp("synthetic_phase_search_corpus"))
        niche_phase_search.run(out_root=corpus_root, n_points=2, seeds_per_point=2, n_steps=20)
        out_root = str(tmp_path_factory.mktemp("synthetic_phase_search_reanalysis"))
        summary = level03b_phase_search_reanalysis.run(
            out_root=out_root,
            design_path=os.path.join(corpus_root, "niche_phase_search_design.csv"),
            old_outcomes_path=os.path.join(corpus_root, "niche_phase_search_outcomes.csv"),
            n_steps=20,
        )
        return out_root, summary

    def test_reproduces_its_own_freshly_generated_outcomes_bit_for_bit(self, synthetic_reanalysis):
        _, summary = synthetic_reanalysis
        # niche_phase_search.run() and level03b_phase_search_reanalysis.run()
        # both call the identical deterministic (SimulationConfig, seed) ->
        # Simulation path (core/rng.py) -- re-running the same (point,
        # seed) pairs must reproduce the freshly-generated "old" outcomes
        # exactly, which is the entire scientific claim under test here.
        assert summary["n_mismatches_vs_committed_level03_outcomes"] == 0
        assert summary["n_runs_reanalyzed"] == 4  # 2 points x 2 seeds
        assert summary["n_points"] == 2

    def test_point_level_aggregation_denominator_is_points_not_runs(self, synthetic_reanalysis):
        out_root, _ = synthetic_reanalysis
        point_level = pd.read_csv(os.path.join(out_root, "point_level_reanalysis.csv"))
        assert len(point_level) == 2  # points, not the 4 underlying (point, seed) runs
        assert (point_level["n_seeds"] == 2).all()
        assert set(point_level.columns) >= {"agreement_fraction", "is_robustly_classified", "plurality_new_label"}

    def test_robust_label_agreement_requires_unanimity(self, synthetic_reanalysis):
        out_root, _ = synthetic_reanalysis
        point_level = pd.read_csv(os.path.join(out_root, "point_level_reanalysis.csv"))
        for _, row in point_level.iterrows():
            if row["is_robustly_classified"]:
                assert row["agreement_fraction"] == pytest.approx(1.0)
            else:
                # at n=2 seeds/point, "not robust" must mean the two seeds
                # actually disagreed (agreement_fraction == 0.5) -- never a
                # silently-passed default.
                assert row["agreement_fraction"] == pytest.approx(0.5)


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
_CANDIDATE_REGISTRY_INPUT_PATHS = (
    level03b_candidate_registry.REANALYSIS_POINT_LEVEL,
    level03b_candidate_registry.SUPPLEMENTAL_POINT_LEVEL,
    level03b_candidate_registry.DESIGN_ORIGINAL,
    level03b_candidate_registry.DESIGN_SUPPLEMENTAL,
)


@pytest.mark.skipif(
    not all(os.path.exists(p) for p in _CANDIDATE_REGISTRY_INPUT_PATHS),
    reason=(
        "level03b_candidate_registry.run() reads four hardcoded historical-artifact paths "
        f"({', '.join(_CANDIDATE_REGISTRY_INPUT_PATHS)}); not all are committed in this "
        "checkout -- see test_select_candidates_is_deterministic_given_unchanged_inputs "
        "for artifact-independent coverage of the same determinism property, exercised "
        "directly against the pure select_candidates() function."
    ),
)
def test_candidate_registry_is_deterministic_given_unchanged_inputs():
    """Calling the registry builder twice against the same already-
    committed reanalysis/supplemental outputs must produce an identical
    selection -- the milestone's 'immutability' requirement, verified as
    determinism of the selection function rather than a claim that the
    file itself cannot be overwritten."""
    first = level03b_candidate_registry.run(out_root="/tmp/test_registry_a")
    second = level03b_candidate_registry.run(out_root="/tmp/test_registry_b")
    assert first["selected"] == second["selected"]


def test_select_candidates_is_deterministic_given_unchanged_inputs():
    """Artifact-independent coverage of the same determinism property as
    the skip-guarded test above, exercised directly against
    ``select_candidates()`` -- a pure function of its input DataFrame,
    with no file I/O at all -- using a small synthetic ``combined`` table
    built in-test rather than the real (possibly-absent) historical
    reanalysis/supplemental outputs. Runs unconditionally."""
    combined = pd.DataFrame(
        [
            {
                "point_id": 0, "source": "original_16pt_reanalysis", "n_seeds": 3,
                "plurality_new_label": "interior-persistent", "agreement_fraction": 1.0,
                "n_interior_persistent_seeds": 3, "n_oscillatory_seeds": 0, "n_intermittent_seeds": 0,
                "mean_mean_occupancy": 0.55, "mean_terminal_occupancy": 0.55,
            },
            {
                "point_id": 1, "source": "original_16pt_reanalysis", "n_seeds": 3,
                "plurality_new_label": "oscillatory", "agreement_fraction": 0.667,
                "n_interior_persistent_seeds": 0, "n_oscillatory_seeds": 2, "n_intermittent_seeds": 0,
                "mean_mean_occupancy": 0.30, "mean_terminal_occupancy": 0.30,
            },
            {
                "point_id": 2, "source": "supplemental_32pt_search", "n_seeds": 3,
                "plurality_new_label": "depleted", "agreement_fraction": 1.0,
                "n_interior_persistent_seeds": 0, "n_oscillatory_seeds": 0, "n_intermittent_seeds": 0,
                "mean_mean_occupancy": 0.06, "mean_terminal_occupancy": 0.05,
            },
            {
                "point_id": 3, "source": "supplemental_32pt_search", "n_seeds": 3,
                "plurality_new_label": "interior-persistent", "agreement_fraction": 1.0,
                "n_interior_persistent_seeds": 2, "n_oscillatory_seeds": 0, "n_intermittent_seeds": 0,
                "mean_mean_occupancy": 0.60, "mean_terminal_occupancy": 0.60,
            },
        ]
    )
    first = level03b_candidate_registry.select_candidates(combined.copy())
    second = level03b_candidate_registry.select_candidates(combined.copy())
    assert first["selected"] == second["selected"]
    assert first["rejected"] == second["rejected"]
    # Also exercise the actual selection logic, not just its determinism:
    # point 0 has strictly more passing seeds (3) than point 3 (2) for
    # interior-persistent, so it must win the tie-break.
    assert first["selected"]["interior_persistent"]["point_id"] == 0
    assert first["selected"]["nonstationary"]["point_id"] == 1
    assert first["selected"]["nonstationary"]["type"] == "oscillatory"


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
    # Level 1.1b, Work Package B: level03b_neighborhood_robustness.run()
    # needs both a candidate registry (outputs/level03b_candidate_
    # registry/candidate_registry.json -- committed in this checkout, so
    # used directly at its default path) and a confirmation summary
    # (outputs/level03b_confirmation/level03b_confirmation_summary.json
    # -- NOT committed in this checkout). Rather than depending on the
    # missing historical confirmation output, generate a small,
    # self-contained one in-test via level03b_confirmation.run() itself
    # (the exact same code that would have produced the historical one)
    # and pass its path explicitly -- this test exercises the plumbing
    # only, not real confirmation results, in either case.
    confirmation_summary = level03b_confirmation.run(out_root=str(tmp_path / "confirmation"), n_seeds=1, n_steps=20)
    assert confirmation_summary["n_failures"] == 0
    confirmation_summary_path = os.path.join(str(tmp_path / "confirmation"), "level03b_confirmation_summary.json")
    assert os.path.exists(confirmation_summary_path)

    summary = level03b_neighborhood_robustness.run(
        out_root=str(tmp_path / "robustness"), confirmation_summary_path=confirmation_summary_path,
        n_seeds=1, n_steps=20,
    )
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
