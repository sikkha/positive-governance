"""Level 1.2b, Work Package C (Section 7): tests for
``experiments/level12b_stage_c_feasibility_map.py``."""
from __future__ import annotations

import math

import pytest

from experiments.level12b_stage_c_feasibility_map import (
    N_PARAMETER_POINTS,
    N_STEPS,
    PARAMETER_SPACE,
    POPULATION_PATCH_COMBOS,
    SEEDS_PER_POINT,
    TOTAL_RUNS,
    _build_config,
    _build_perturbations,
    _classify_ecological_outcome,
    _predictive_correlation,
    build_design,
    design_hash,
)


class TestDesignArithmetic:
    def test_explicit_run_arithmetic_fields_meet_section_7_minimums(self):
        assert N_PARAMETER_POINTS >= 30
        assert SEEDS_PER_POINT >= 4
        assert N_STEPS >= 400
        assert TOTAL_RUNS == N_PARAMETER_POINTS * SEEDS_PER_POINT
        assert TOTAL_RUNS >= 120

    def test_design_saves_explicit_fields(self):
        design = build_design()
        assert design["n_parameter_points"] == N_PARAMETER_POINTS
        assert design["seeds_per_point"] == SEEDS_PER_POINT
        assert design["total_runs"] == TOTAL_RUNS
        assert design["n_steps"] == N_STEPS

    def test_design_has_at_least_two_population_patch_combos(self):
        design = build_design()
        combos_used = {(p["population_size"], p["n_patches"]) for p in design["points"]}
        assert len(combos_used) >= 2
        assert combos_used <= set(POPULATION_PATCH_COMBOS)

    def test_design_is_deterministic(self):
        d1 = build_design()
        d2 = build_design()
        assert d1 == d2
        assert design_hash(d1) == design_hash(d2)

    def test_every_point_has_seeds_per_point_seeds(self):
        design = build_design()
        for point in design["points"]:
            assert len(point["seeds"]) == SEEDS_PER_POINT
            assert len(set(point["seeds"])) == SEEDS_PER_POINT  # no duplicate seeds within a point

    def test_seeds_never_repeat_across_points(self):
        design = build_design()
        all_seeds = [s for p in design["points"] for s in p["seeds"]]
        assert len(all_seeds) == len(set(all_seeds))

    def test_nine_swept_dimensions_realize_section_7s_eight_named_dimensions(self):
        # Section 7 names 8 dimensions; "shock frequency" and "shock
        # magnitude" are two separate LHS columns here, both realizing
        # the one named "shock frequency/magnitude" dimension, plus the
        # population/patch-ratio selector -- 9 total swept quantities.
        assert len(PARAMETER_SPACE) == 9


class TestBroadButFixedInstitutionalDesign:
    def test_institutional_flags_identical_across_all_points(self):
        design = build_design()
        configs = [_build_config(p, p["seeds"][0]) for p in design["points"][:5]]
        institutional_fields = [
            "institutional_observation_enabled", "institutional_transmission_enabled",
            "migration_enabled", "membership_exit_enabled", "institutional_scaling_enabled",
            "monitoring_mode", "sanction_mode", "delegation_enabled", "rng_mode",
        ]
        for field in institutional_fields:
            values = {getattr(c, field) for c in configs}
            assert len(values) == 1, f"{field} varies across points -- institutional design must be fixed"

    def test_ecological_parameters_vary_across_points(self):
        design = build_design()
        configs = [_build_config(p, p["seeds"][0]) for p in design["points"][:5]]
        regen_rates = {c.patch_regen_rate for c in configs}
        assert len(regen_rates) > 1


class TestShockConstruction:
    def test_zero_magnitude_produces_no_perturbations(self):
        point = {"ecological_parameters": {"shock_interval_steps": 50.0, "shock_magnitude": 0.0}}
        assert _build_perturbations(point, 400) == ()

    def test_positive_magnitude_produces_recurring_shocks(self):
        point = {"ecological_parameters": {"shock_interval_steps": 100.0, "shock_magnitude": 0.3}}
        specs = _build_perturbations(point, 400)
        assert len(specs) == 3  # steps 100, 200, 300 (400 excluded, exclusive of n_steps)
        for spec in specs:
            assert spec["kind"] == "resource_depletion"
            assert spec["magnitude"] == pytest.approx(0.3)

    def test_interval_never_zero_or_negative(self):
        point = {"ecological_parameters": {"shock_interval_steps": 0.0, "shock_magnitude": 0.3}}
        specs = _build_perturbations(point, 10)
        assert all(s["start_step"] >= 1 for s in specs)


class TestEcologicalOutcomeClassification:
    def test_collapse(self):
        assert _classify_ecological_outcome(mean_ratio_post_burn_in=0.02, fraction_below_one=1.0) == "collapse"

    def test_saturation(self):
        assert _classify_ecological_outcome(mean_ratio_post_burn_in=5.0, fraction_below_one=0.0) == "saturation"

    def test_other_moderate_pressure(self):
        assert _classify_ecological_outcome(mean_ratio_post_burn_in=1.2, fraction_below_one=0.3) == "other"

    def test_nan_never_coerced_to_a_label(self):
        assert _classify_ecological_outcome(mean_ratio_post_burn_in=math.nan, fraction_below_one=0.5) == "other"
        assert _classify_ecological_outcome(mean_ratio_post_burn_in=0.5, fraction_below_one=math.nan) == "other"

    def test_low_ratio_but_not_persistent_deficit_is_not_collapse(self):
        # low mean ratio alone, without a high fraction-below-one, must
        # not be labeled collapse -- both conditions are required.
        assert _classify_ecological_outcome(mean_ratio_post_burn_in=0.05, fraction_below_one=0.2) == "other"


class TestPredictiveCorrelation:
    def test_hand_computed_perfect_positive_correlation(self):
        records = [
            {"structural_ratio": float(i), "expected_ratio": float(i), "realized_mean_ratio_post_burn_in": float(i)}
            for i in range(1, 6)
        ]
        result = _predictive_correlation(records)
        assert result["structural_ratio_vs_realized_mean"] == pytest.approx(1.0)
        assert result["expected_ratio_vs_realized_mean"] == pytest.approx(1.0)
        assert result["n_pairs_structural"] == 5

    def test_none_when_fewer_than_three_finite_pairs(self):
        records = [
            {"structural_ratio": 1.0, "expected_ratio": 1.0, "realized_mean_ratio_post_burn_in": 1.0},
            {"structural_ratio": 2.0, "expected_ratio": 2.0, "realized_mean_ratio_post_burn_in": 2.0},
        ]
        result = _predictive_correlation(records)
        assert result["structural_ratio_vs_realized_mean"] is None

    def test_nonfinite_pairs_excluded_not_coerced(self):
        records = [
            {"structural_ratio": 1.0, "expected_ratio": 1.0, "realized_mean_ratio_post_burn_in": 1.0},
            {"structural_ratio": 2.0, "expected_ratio": 2.0, "realized_mean_ratio_post_burn_in": 2.0},
            {"structural_ratio": math.nan, "expected_ratio": 3.0, "realized_mean_ratio_post_burn_in": 3.0},
            {"structural_ratio": 4.0, "expected_ratio": 4.0, "realized_mean_ratio_post_burn_in": 4.0},
        ]
        result = _predictive_correlation(records)
        assert result["n_pairs_structural"] == 3
        assert result["n_pairs_expected"] == 4


class TestActualExperimentOutputIfPresent:
    """If Work Package C's own run has already been executed (its output
    files exist on disk from this session's own experiment run), verify
    the saved results meet Section 7's completion requirements. Skipped
    entirely if the experiment has not been run in this environment."""

    def test_results_meet_section_7_requirements(self):
        import json
        import os

        out_dir = "outputs/level12b_stage_c_feasibility_map"
        if not os.path.exists(f"{out_dir}/results.json"):
            pytest.skip("Work Package C experiment output not present in this environment")
        with open(f"{out_dir}/results.json") as f:
            report = json.load(f)
        assert report["n_runs_completed"] == TOTAL_RUNS
        assert report["n_runs_failed"] == 0
        # Section 7: "if every point collapses/saturates, stop and report
        # envelope failure" -- must not have triggered for a genuinely
        # informative design.
        assert report["envelope_failure"] is False
        assert set(report["outcome_counts"].keys()) - {"collapse", "saturation", "other"} == set()
