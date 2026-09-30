"""Level 1.3b, Work Package F / Stage 5 (task #118): regression tests
for ``observer/historical_persistence.py`` and the new
``equalize_pressure_series`` counterfactual transform."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.core.historical_counterfactuals import (
    equalize_pressure_series,
    erase_pressure_from,
    reverse_pressure_order,
)
from abm_governance.observer.historical_persistence import (
    CLASSIFICATION_CATEGORIES,
    WINDOW_FRACTIONS,
    classify_persistence,
    condition_rank_stability,
    convergence_divergence_slope,
    early_to_middle_displacement,
    late_window_variance,
    middle_to_late_displacement,
    trajectory_distance,
    window_bounds,
    windowed_mean,
)


class TestEqualizePressureSeries:
    def test_replaces_every_entry_with_the_mean(self):
        series = np.array([0.1, 0.1, 0.9, 0.9, 0.1])
        out = equalize_pressure_series(series)
        assert np.allclose(out, series.mean())

    def test_preserves_sum_exactly_up_to_floating_point(self):
        series = np.array([0.2, 0.4, 0.6, 0.1, 0.9, 0.3])
        out = equalize_pressure_series(series)
        assert np.isclose(out.sum(), series.sum())

    def test_does_not_mutate_input(self):
        series = np.array([0.1, 0.5, 0.9])
        original = series.copy()
        equalize_pressure_series(series)
        assert np.array_equal(series, original)

    def test_empty_series_returns_empty(self):
        out = equalize_pressure_series(np.array([]))
        assert out.size == 0

    def test_distinct_from_erase_and_reverse(self):
        series = np.array([0.1, 0.1, 0.9, 0.9])
        eq = equalize_pressure_series(series)
        er = erase_pressure_from(series, step=2)
        rv = reverse_pressure_order(series)
        assert not np.array_equal(eq, er)
        assert not np.array_equal(eq, rv)


class TestWindowBounds:
    def test_early_window_starts_at_zero(self):
        lo, hi = window_bounds(500, "early")
        assert lo == 0
        assert hi == 100  # 0.2 * 500

    def test_final_sustained_ends_at_n_steps(self):
        lo, hi = window_bounds(500, "final_sustained")
        assert hi == 500
        assert lo == 450  # 0.9 * 500

    def test_bounds_never_exceed_n_steps(self):
        for name in WINDOW_FRACTIONS:
            lo, hi = window_bounds(10, name)
            assert 0 <= lo < hi <= 10

    def test_rejects_zero_steps(self):
        with pytest.raises(ValueError):
            window_bounds(0, "early")


class TestWindowedDiagnostics:
    def test_windowed_mean_hand_computed(self):
        series = np.zeros(10)
        series[8:] = 1.0  # steps 8,9 -> "late" window's tail region
        n_steps = 10
        # late window is [0.8*10, 1.0*10) = [8, 10)
        assert windowed_mean(series, n_steps, "late") == pytest.approx(1.0)
        assert windowed_mean(series, n_steps, "early") == pytest.approx(0.0)

    def test_displacement_zero_for_constant_series(self):
        series = np.full(500, 0.42)
        assert early_to_middle_displacement(series, 500) == pytest.approx(0.0)
        assert middle_to_late_displacement(series, 500) == pytest.approx(0.0)

    def test_displacement_detects_a_step_change(self):
        series = np.zeros(500)
        series[250:] = 1.0  # step change right at the middle/late boundary region
        e2m = early_to_middle_displacement(series, 500)
        m2l = middle_to_late_displacement(series, 500)
        assert e2m == pytest.approx(0.5)  # early(mean 0) -> middle(half 0, half 1) is a half-window jump
        assert m2l == pytest.approx(0.5)  # middle(mean 0.5) -> late(fully 1.0) is another half-window jump

    def test_late_window_variance_zero_for_flat_tail(self):
        series = np.zeros(500)
        series[400:] = 1.0
        assert late_window_variance(series, 500) == pytest.approx(0.0)

    def test_late_window_variance_positive_for_noisy_tail(self):
        rng = np.random.default_rng(0)
        series = np.zeros(500)
        series[450:] = rng.normal(0.5, 0.2, size=50)
        assert late_window_variance(series, 500) > 0.0

    def test_convergence_divergence_slope_zero_for_constant(self):
        series = np.full(300, 0.5)
        assert convergence_divergence_slope(series, 300) == pytest.approx(0.0, abs=1e-9)

    def test_convergence_divergence_slope_positive_for_rising_trend(self):
        series = np.linspace(0.0, 1.0, 300)
        assert convergence_divergence_slope(series, 300) > 0.0


class TestTrajectoryDistance:
    def test_zero_for_identical_series(self):
        series = np.linspace(0.0, 1.0, 500)
        result = trajectory_distance(series, series, 500)
        assert result["summary_euclidean_distance"] == pytest.approx(0.0, abs=1e-9)
        for w in ("early", "middle", "late", "final_sustained"):
            assert result[f"gap_at_{w}"] == pytest.approx(0.0, abs=1e-9)

    def test_positive_for_a_shifted_series(self):
        series_a = np.full(500, 0.2)
        series_b = np.full(500, 0.8)
        result = trajectory_distance(series_a, series_b, 500)
        assert result["summary_euclidean_distance"] > 0.0
        assert result["gap_at_early"] == pytest.approx(0.6)


class TestConditionRankStability:
    def test_perfect_stability_when_order_never_changes(self):
        means = {
            "a": {"early": 0.1, "middle": 0.2, "late": 0.3},
            "b": {"early": 0.5, "middle": 0.6, "late": 0.7},
            "c": {"early": 0.9, "middle": 0.95, "late": 0.99},
        }
        result = condition_rank_stability(means)
        assert result["early_to_middle"] == pytest.approx(1.0)
        assert result["middle_to_late"] == pytest.approx(1.0)

    def test_full_reversal_gives_negative_correlation(self):
        means = {
            "a": {"early": 0.1, "middle": 0.9, "late": 0.9},
            "b": {"early": 0.5, "middle": 0.5000001, "late": 0.5},
            "c": {"early": 0.9, "middle": 0.1, "late": 0.1},
        }
        result = condition_rank_stability(means)
        assert result["early_to_middle"] < 0.0

    def test_nan_for_a_single_condition(self):
        result = condition_rank_stability({"a": {"early": 0.1, "middle": 0.2}})
        assert np.isnan(result["early_to_middle"])


class TestClassifyPersistence:
    def test_no_detectable_differentiation(self):
        label = classify_persistence(early_to_middle=0.001, middle_to_late=0.001, late_variance=0.0001, slope=0.0001)
        assert label == "no_detectable_differentiation"

    def test_entrenched_path_dependence(self):
        label = classify_persistence(early_to_middle=0.3, middle_to_late=0.001, late_variance=0.0001, slope=0.0001)
        assert label == "entrenched_path_dependence"

    def test_transient_differentiation_when_reconverging(self):
        label = classify_persistence(early_to_middle=0.3, middle_to_late=-0.3, late_variance=0.02, slope=0.05)
        assert label == "transient_differentiation"

    def test_every_returned_label_is_a_known_category(self):
        rng = np.random.default_rng(1)
        for _ in range(50):
            label = classify_persistence(
                early_to_middle=float(rng.uniform(-0.5, 0.5)),
                middle_to_late=float(rng.uniform(-0.5, 0.5)),
                late_variance=float(rng.uniform(0.0, 0.05)),
                slope=float(rng.uniform(-0.01, 0.01)),
            )
            assert label in CLASSIFICATION_CATEGORIES
