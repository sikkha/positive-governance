"""Level 1.2, Section 7: temporal phenotype representation."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.observer import temporal_features as tf
from abm_governance.rules.institution import InstitutionComponents, InstitutionRecord


def _components(**overrides):
    base = dict(
        proposal_threshold=0.3, adoption_threshold=0.5, contribution_mechanism="voluntary",
        monitoring_allocation=0.4, sanction_procedure=0.4, appeal_procedure=0.2, recall_procedure=0.5,
        delegated_task_distribution=("monitoring",), administrative_fund_rule=0.1, authority_concentration=0.0,
        amendment_threshold=0.5, memory_retention=0.5, succession_procedure="voluntary_approval",
        coordination_link_policy=0.02,
    )
    base.update(overrides)
    return InstitutionComponents(**base)


def _snapshot(step, value):
    return {"step": step, "vector": {"C": {"numerator": value, "denominator": 1, "value": value}}}


class TestComputeWindowBounds:
    def test_windows_partition_post_burn_in_range(self):
        bounds = tf.compute_window_bounds(100, burn_in_fraction=0.2)
        assert bounds["early_post_burn_in"][0] == 20
        assert bounds["late"][1] == 100
        assert bounds["early_post_burn_in"][1] <= bounds["middle"][0] + 1

    def test_terminal_window_is_the_final_fraction(self):
        bounds = tf.compute_window_bounds(100, burn_in_fraction=0.2, terminal_fraction=0.1)
        assert bounds["terminal"] == (90, 100)

    def test_shock_windows_only_present_when_shock_step_given(self):
        bounds = tf.compute_window_bounds(100, shock_step=None)
        assert "shock" not in bounds
        bounds2 = tf.compute_window_bounds(100, shock_step=50, post_shock_horizon=10)
        assert bounds2["shock"] == (50, 51)
        assert bounds2["post_shock"] == (51, 61)

    def test_zero_steps_degenerate_but_no_crash(self):
        bounds = tf.compute_window_bounds(0)
        assert bounds["early_post_burn_in"] == (0, 0)


class TestWindowStaticFeatures:
    def test_mean_and_variance_computed_correctly(self):
        snapshots = [_snapshot(i, float(i)) for i in range(10)]
        feat = tf.window_static_features(snapshots, "C", (0, 10))
        assert feat["feature_kind"] == "static"
        assert feat["mean"] == pytest.approx(4.5)
        assert feat["n_observations"] == 10
        assert feat["missingness_fraction"] == pytest.approx(0.0)

    def test_empty_window_yields_nan(self):
        feat = tf.window_static_features([_snapshot(0, 1.0)], "C", (5, 10))
        assert np.isnan(feat["mean"])
        assert np.isnan(feat["missingness_fraction"])

    def test_nan_values_counted_as_missing(self):
        snapshots = [_snapshot(0, 1.0), _snapshot(1, float("nan")), _snapshot(2, 3.0)]
        feat = tf.window_static_features(snapshots, "C", (0, 3))
        assert feat["n_observations"] == 3
        assert feat["n_defined"] == 2
        assert feat["missingness_fraction"] == pytest.approx(1 / 3)


class TestWindowDynamicFeatures:
    def test_trend_detects_positive_slope(self):
        snapshots = [_snapshot(i, float(i)) for i in range(10)]
        feat = tf.window_dynamic_features(snapshots, "C", (0, 10))
        assert feat["feature_kind"] == "dynamic"
        assert feat["trend_slope"] > 0

    def test_constant_series_has_zero_slope(self):
        snapshots = [_snapshot(i, 5.0) for i in range(10)]
        feat = tf.window_dynamic_features(snapshots, "C", (0, 10))
        assert feat["trend_slope"] == pytest.approx(0.0)


class TestLineageTurnover:
    def _rec(self, iid, lineage, creation, extinction=None):
        return InstitutionRecord(institution_id=iid, lineage_id=lineage, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=creation, components=_components(), extinction_time=extinction, extinction_reason="x" if extinction is not None else None)

    def test_no_turnover_when_all_lineages_predate_window(self):
        registry = {0: self._rec(0, 0, creation=0)}
        result = tf.lineage_turnover(registry, (10, 20))
        assert result["n_new_lineages"] == 0
        assert result["turnover_ratio"] == pytest.approx(0.0)

    def test_new_lineage_created_within_window_counted(self):
        registry = {0: self._rec(0, 0, creation=0), 1: self._rec(1, 1, creation=15)}
        result = tf.lineage_turnover(registry, (10, 20))
        assert result["n_new_lineages"] == 1
        assert result["turnover_ratio"] == pytest.approx(1.0)

    def test_nan_turnover_when_nothing_present_at_start(self):
        registry = {0: self._rec(0, 0, creation=15)}
        result = tf.lineage_turnover(registry, (10, 20))
        assert np.isnan(result["turnover_ratio"])


class TestExtinctionReconstructionCounts:
    def test_counts_within_window_only(self):
        registry = {
            0: InstitutionRecord(institution_id=0, lineage_id=0, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components(), extinction_time=15, extinction_reason="x"),
            1: InstitutionRecord(institution_id=1, lineage_id=1, parent_institution_id=0, origin_mechanism="reconstruction", creation_time=16, components=_components()),
            2: InstitutionRecord(institution_id=2, lineage_id=2, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components(), extinction_time=50, extinction_reason="x"),
        }
        result = tf.extinction_reconstruction_counts(registry, (10, 20))
        assert result["n_extinctions"] == 1
        assert result["n_reconstructions"] == 1


class TestDetectNonstationarity:
    def test_flags_a_clear_regime_shift(self):
        snapshots = [_snapshot(i, 0.0) for i in range(50)] + [_snapshot(i, 100.0) for i in range(50, 100)]
        result = tf.detect_nonstationarity(snapshots, "C", 100, burn_in_fraction=0.0)
        assert result["nonstationary"] is True or result["nonstationary"] == True  # noqa: E712

    def test_stationary_series_not_flagged(self):
        rng = np.random.default_rng(0)
        snapshots = [_snapshot(i, float(rng.normal(0.0, 0.01))) for i in range(100)]
        result = tf.detect_nonstationarity(snapshots, "C", 100, burn_in_fraction=0.0)
        assert result["nonstationary"] is False or result["nonstationary"] == False  # noqa: E712


class TestExtractAllTemporalFeatures:
    def test_bundles_static_and_dynamic_per_window(self):
        snapshots = [_snapshot(i, float(i % 5)) for i in range(100)]
        result = tf.extract_all_temporal_features(snapshots, "C", 100, burn_in_fraction=0.2)
        for name in ("early_post_burn_in", "middle", "late", "terminal"):
            assert name in result
            assert "static" in result[name] and "dynamic" in result[name]
        assert "nonstationarity" in result
