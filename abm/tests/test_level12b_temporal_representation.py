"""Level 1.2b, Work Package G (Section 12): tests for the temporal-
representation additions to ``observer/temporal_features.py`` (post_burn_in/
pre_shock windows, persistence/transition/shock-recovery features,
static-vs-dynamic grouping) and for
``experiments/level12b_stage_g_temporal_representation.py``'s burn-in-
sensitivity sweep and snapshot-driving pipeline."""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pytest

from abm_governance.observer import temporal_features as tf


def _snap(step, value):
    return {"step": step, "vector": {"C": {"numerator": value, "denominator": 1, "value": value}}}


class TestPostBurnInAndPreShockWindowBounds:
    def test_post_burn_in_spans_the_whole_post_burn_in_range(self):
        bounds = tf.compute_window_bounds(100, burn_in_fraction=0.2)
        assert bounds["post_burn_in"] == (20, 100)

    def test_post_burn_in_is_the_union_of_the_three_thirds(self):
        bounds = tf.compute_window_bounds(99, burn_in_fraction=0.2)
        assert bounds["post_burn_in"][0] == bounds["early_post_burn_in"][0]
        assert bounds["post_burn_in"][1] == bounds["late"][1]

    def test_pre_shock_only_present_with_shock_step(self):
        bounds = tf.compute_window_bounds(100, shock_step=None)
        assert "pre_shock" not in bounds
        bounds2 = tf.compute_window_bounds(100, shock_step=50, pre_shock_horizon=15)
        assert bounds2["pre_shock"] == (35, 50)

    def test_pre_shock_clamped_at_zero(self):
        bounds = tf.compute_window_bounds(100, shock_step=5, pre_shock_horizon=20)
        assert bounds["pre_shock"] == (0, 5)


class TestWindowPersistenceFeatures:
    def test_constant_series_fully_persistent_no_transitions(self):
        snapshots = [_snap(i, 5.0) for i in range(20)]
        feat = tf.window_persistence_features(snapshots, "C", (0, 20))
        assert feat["feature_kind"] == "dynamic"
        assert feat["fraction_in_band"] == pytest.approx(1.0)
        assert feat["longest_stable_episode_steps"] == 20
        assert feat["n_transitions"] == 0

    def test_step_change_detected_as_a_transition(self):
        snapshots = [_snap(i, 0.0) for i in range(10)] + [_snap(i, 100.0) for i in range(10, 20)]
        feat = tf.window_persistence_features(snapshots, "C", (0, 20))
        assert feat["n_transitions"] >= 1

    def test_oscillating_series_has_more_transitions_than_stable_one(self):
        rng = np.random.default_rng(0)
        stable = [_snap(i, float(5.0 + rng.normal(0.0, 0.01))) for i in range(40)]
        oscillating = [_snap(i, 5.0 + 10.0 * (i % 2)) for i in range(40)]
        f_stable = tf.window_persistence_features(stable, "C", (0, 40))
        f_oscillating = tf.window_persistence_features(oscillating, "C", (0, 40))
        assert f_oscillating["n_transitions"] > f_stable["n_transitions"]
        assert f_oscillating["longest_stable_episode_steps"] <= f_stable["longest_stable_episode_steps"]

    def test_degenerate_on_fewer_than_two_points(self):
        feat_empty = tf.window_persistence_features([], "C", (0, 10))
        assert np.isnan(feat_empty["fraction_in_band"])
        assert feat_empty["n_transitions"] == 0
        feat_one = tf.window_persistence_features([_snap(0, 1.0)], "C", (0, 10))
        assert np.isnan(feat_one["fraction_in_band"])

    def test_band_is_exported_alongside_the_features(self):
        snapshots = [_snap(i, float(i % 5)) for i in range(30)]
        feat = tf.window_persistence_features(snapshots, "C", (0, 30))
        assert feat["band_lower"] < feat["band_upper"]


class TestWindowShockRecoveryFeatures:
    def test_reuses_regulation_diagnostics_perturbation_recovery_fields(self):
        pre = [_snap(i, 1.0) for i in range(20)]
        dip = [_snap(20, -5.0)]
        post = [_snap(i, 1.0) for i in range(21, 40)]
        snapshots = pre + dip + post
        feat = tf.window_shock_recovery_features(snapshots, "C", shock_step=20, pre_shock_horizon=20, post_shock_horizon=19)
        for key in ("recovered", "recovery_time_steps", "immediate_shock_magnitude", "time_to_minimum", "overshoot", "pre_shock_min", "pre_shock_max"):
            assert key in feat
        assert feat["feature_kind"] == "dynamic"
        assert feat["shock_step"] == 20

    def test_gradual_recovery_is_detected(self):
        # a slightly noisy pre-shock baseline (band_width > 0 -- a
        # perfectly flat baseline is perturbation_recovery's own
        # documented degenerate case, recovered=False regardless of
        # post-shock values, since "recovery" would be a vacuous
        # exact-equality test)
        pre_values = [9.9, 10.0, 10.1, 9.95, 10.05] * 4
        pre = [_snap(i, v) for i, v in enumerate(pre_values)]
        # dips hard then climbs back toward the pre-shock band
        post_values = [0.0, 1.0, 3.0, 5.0, 7.0, 9.0, 9.5, 10.0, 10.0, 10.0]
        post = [_snap(21 + i, v) for i, v in enumerate(post_values)]
        snapshots = pre + [_snap(20, 0.0)] + post
        feat = tf.window_shock_recovery_features(snapshots, "C", shock_step=20, pre_shock_horizon=20, post_shock_horizon=10)
        assert feat["recovered"] is True
        assert feat["recovery_time_steps"] >= 0

    def test_no_data_degenerate(self):
        feat = tf.window_shock_recovery_features([], "C", shock_step=20)
        assert feat["recovered"] is False
        assert math.isnan(feat["recovery_time_steps"])


class TestExtractAllTemporalFeaturesIncludesPersistenceAndShockRecovery:
    def test_every_window_carries_a_persistence_subkey(self):
        snapshots = [_snap(i, float(i % 7)) for i in range(100)]
        bundle = tf.extract_all_temporal_features(snapshots, "C", 100, burn_in_fraction=0.2)
        for name in ("post_burn_in", "early_post_burn_in", "middle", "late", "terminal"):
            assert "persistence" in bundle[name]
            assert bundle[name]["persistence"]["feature_kind"] == "dynamic"

    def test_shock_recovery_key_present_only_when_shock_step_given(self):
        snapshots = [_snap(i, float(i % 7)) for i in range(100)]
        bundle_no_shock = tf.extract_all_temporal_features(snapshots, "C", 100, burn_in_fraction=0.2)
        assert "shock_recovery" not in bundle_no_shock
        bundle_shock = tf.extract_all_temporal_features(snapshots, "C", 100, burn_in_fraction=0.2, shock_step=50)
        assert "shock_recovery" in bundle_shock
        assert bundle_shock["shock_recovery"]["shock_step"] == 50


class TestGroupFeaturesByKind:
    def test_single_dimension_bundle_separated_correctly(self):
        snapshots = [_snap(i, float(i % 5)) for i in range(100)]
        bundle = tf.extract_all_temporal_features(snapshots, "C", 100, burn_in_fraction=0.2)
        grouped = tf.group_features_by_kind(bundle)
        assert set(grouped.keys()) == {"static", "dynamic"}
        for window_name in ("post_burn_in", "early_post_burn_in", "middle", "late", "terminal"):
            assert window_name in grouped["static"]
            assert grouped["static"][window_name]["feature_kind"] == "static"
            assert window_name in grouped["dynamic"]
            assert "dynamic" in grouped["dynamic"][window_name]
            assert "persistence" in grouped["dynamic"][window_name]
        assert "nonstationarity" in grouped["dynamic"]
        assert "nonstationarity" not in grouped["static"]

    def test_no_dynamic_field_leaks_into_static_side(self):
        snapshots = [_snap(i, float(i % 5)) for i in range(100)]
        bundle = tf.extract_all_temporal_features(snapshots, "C", 100, burn_in_fraction=0.2, shock_step=50)
        grouped = tf.group_features_by_kind(bundle)
        for window_entry in grouped["static"].values():
            assert window_entry["feature_kind"] == "static"
        assert "shock_recovery" in grouped["dynamic"]
        assert "shock_recovery" not in grouped["static"]

    def test_multi_dimension_bundle_also_separated(self):
        snapshots_c = [_snap(i, float(i % 5)) for i in range(60)]

        def snap_e(step, value):
            return {"step": step, "vector": {"E": {"numerator": value, "denominator": 1, "value": value}}}

        snapshots_e = [snap_e(i, float(i % 3)) for i in range(60)]
        bundle_c = tf.extract_all_temporal_features(snapshots_c, "C", 60, burn_in_fraction=0.2)
        bundle_e = tf.extract_all_temporal_features(snapshots_e, "E", 60, burn_in_fraction=0.2)
        multi_bundle = {"C": bundle_c, "E": bundle_e}
        grouped = tf.group_features_by_kind(multi_bundle)
        assert set(grouped["static"].keys()) == {"C", "E"}
        assert set(grouped["dynamic"].keys()) == {"C", "E"}
        assert "post_burn_in" in grouped["static"]["C"]
        assert "post_burn_in" in grouped["dynamic"]["E"]

    def test_joint_view_is_simply_the_undivided_bundle(self):
        """Section 12: static and dynamic must be analyzable 'separately
        AND jointly'. The joint view is just the original bundle,
        unflattened -- grouping never discards or duplicates a field
        relative to the input bundle's own window-level keys."""
        snapshots = [_snap(i, float(i % 5)) for i in range(60)]
        bundle = tf.extract_all_temporal_features(snapshots, "C", 60, burn_in_fraction=0.2)
        grouped = tf.group_features_by_kind(bundle)
        for window_name in ("post_burn_in", "early_post_burn_in", "middle", "late", "terminal"):
            assert grouped["static"][window_name] == bundle[window_name]["static"]
            assert grouped["dynamic"][window_name]["dynamic"] == bundle[window_name]["dynamic"]
            assert grouped["dynamic"][window_name]["persistence"] == bundle[window_name]["persistence"]


class TestStageGExperimentModule:
    def test_four_burn_in_definitions_preregistered(self):
        from experiments.level12b_stage_g_temporal_representation import BURN_IN_SENSITIVITY_DEFINITIONS

        assert set(BURN_IN_SENSITIVITY_DEFINITIONS.keys()) == {"primary", "shorter", "longer", "terminal_only"}
        assert BURN_IN_SENSITIVITY_DEFINITIONS["primary"]["burn_in_fraction"] == 0.2
        assert BURN_IN_SENSITIVITY_DEFINITIONS["terminal_only"]["windows_included"] == ("terminal",)

    def test_definitions_hash_deterministic(self):
        from experiments.level12b_stage_g_temporal_representation import definitions_hash

        assert definitions_hash() == definitions_hash()

    def test_filter_bundle_to_windows_keeps_diagnostics_always(self):
        from experiments.level12b_stage_g_temporal_representation import _filter_bundle_to_windows

        snapshots = [_snap(i, float(i % 5)) for i in range(60)]
        bundle = tf.extract_all_temporal_features(snapshots, "C", 60, burn_in_fraction=0.2, shock_step=30)
        filtered = _filter_bundle_to_windows(bundle, ("terminal",))
        assert set(filtered.keys()) == {"terminal", "nonstationarity", "shock_recovery"}

    def test_filter_bundle_none_keeps_everything(self):
        from experiments.level12b_stage_g_temporal_representation import _filter_bundle_to_windows

        snapshots = [_snap(i, float(i % 5)) for i in range(60)]
        bundle = tf.extract_all_temporal_features(snapshots, "C", 60, burn_in_fraction=0.2)
        assert _filter_bundle_to_windows(bundle, None) == bundle

    def test_all_ten_dimensions_covered(self):
        from experiments.level12b_stage_g_temporal_representation import PHENOTYPE_DIMENSIONS

        assert set(PHENOTYPE_DIMENSIONS) == set("CELDMRSFVH")


class TestActualExperimentOutputIfPresent:
    """Skipped entirely if the validation run has not been executed in
    this environment."""

    def test_results_meet_section_12_structural_requirements(self):
        out_dir = "outputs/level12b_stage_g_temporal_representation"
        if not os.path.exists(f"{out_dir}/results.json"):
            pytest.skip("Work Package G experiment output not present in this environment")
        with open(f"{out_dir}/results.json") as f:
            report = json.load(f)
        assert report["n_records"] == len(report["records"])
        assert report["n_records"] > 0
        for rec in report["records"]:
            assert set(rec["dimension_features"].keys()) == set("CELDMRSFVH")
            for dim, per_def in rec["dimension_features"].items():
                assert set(per_def.keys()) == {"primary", "shorter", "longer", "terminal_only"}
                for def_name, views in per_def.items():
                    assert set(views.keys()) == {"joint", "grouped"}
                    assert "lineage_turnover" in views["joint"]
                    assert "extinction_reconstruction" in views["joint"]
                    if def_name == "terminal_only":
                        assert "terminal" in views["joint"]
                        assert "post_burn_in" not in views["joint"]
