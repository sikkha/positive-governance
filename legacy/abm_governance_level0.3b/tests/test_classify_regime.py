"""Level 0.3b, Work Package A4: hand-constructed validation tests for the
audited, burn-in-aware regime classifier
(``observer/regulation_diagnostics.py::classify_regime`` and its
supporting diagnostics). The original Level 0.3 classifier
(``nonstationary_classification``) is covered separately, unchanged, in
``tests/test_regulation_diagnostics.py``."""

from __future__ import annotations

import math

import numpy as np
import pytest

from abm_governance.observer.regulation_diagnostics import (
    CLASSIFIER_VERSION,
    autocorrelation,
    band_transitions,
    classify_regime,
    detect_peaks_and_troughs,
    dominant_spectral_power_ratio,
    linear_trend,
    peak_to_trough_amplitude,
    rolling_variance,
)

RNG = np.random.default_rng(20260817)


# ---------------------------------------------------------------------
# Supporting diagnostics -- hand-computed / structurally checked.
# ---------------------------------------------------------------------
def test_linear_trend_hand_computed():
    # y = 2x + 1 exactly -> slope 2.0, R^2 == 1.0
    y = 2.0 * np.arange(10) + 1.0
    result = linear_trend(y)
    assert result["slope"] == pytest.approx(2.0)
    assert result["r_squared"] == pytest.approx(1.0)


def test_linear_trend_degenerate_cases():
    assert math.isnan(linear_trend([])["slope"])
    one_point = linear_trend([5.0])
    assert one_point["slope"] == 0.0
    assert math.isnan(one_point["r_squared"])
    constant = linear_trend(np.full(50, 3.0))
    assert constant["slope"] == pytest.approx(0.0, abs=1e-9)
    assert math.isnan(constant["r_squared"])


def test_rolling_variance_hand_computed():
    series = [0.0, 0.0, 2.0, 2.0, 0.0, 0.0]
    variances = rolling_variance(series, window=2)
    # windows: [0,0]->0, [0,2]->1, [2,2]->0, [2,0]->1, [0,0]->0
    assert list(variances) == pytest.approx([0.0, 1.0, 0.0, 1.0, 0.0])


def test_rolling_variance_degenerate_short_series():
    assert len(rolling_variance([1.0, 2.0], window=5)) == 0
    assert len(rolling_variance([1.0, 2.0], window=0)) == 0


def test_detect_peaks_and_troughs_hand_computed():
    series = [0.0, 1.0, 0.0, -1.0, 0.0, 1.0, 0.0]
    result = detect_peaks_and_troughs(series, prominence=0.5)
    assert list(result["peak_indices"]) == [1, 5]
    assert list(result["trough_indices"]) == [3]


def test_peak_to_trough_amplitude_hand_computed():
    series = [0.0, 1.0, 0.0, 1.0, 0.0]
    result = peak_to_trough_amplitude(series, prominence=0.5)
    assert result["n_extrema"] == 3  # peak, trough, peak
    assert result["median_amplitude"] == pytest.approx(1.0)


def test_peak_to_trough_amplitude_no_extrema_is_zero_not_nan():
    result = peak_to_trough_amplitude(np.full(20, 0.5))
    assert result["n_extrema"] == 0
    assert result["median_amplitude"] == 0.0


def test_autocorrelation_perfect_period_2():
    # Alternating +1/-1: strongly negative at lag 1 (each step flips
    # sign), strongly positive at lag 2 (period matches exactly). The
    # normalization here divides by n (not n-lag), so edge effects keep
    # the magnitude just under 1.0 rather than exactly at it.
    series = np.tile([1.0, -1.0], 20)
    ac = autocorrelation(series, max_lag=4)
    assert ac[0] < -0.9
    assert ac[1] > 0.9


def test_autocorrelation_constant_series_is_zero_not_spurious():
    """A mathematically constant series has floating-point variance on the
    order of 1e-33, not exactly 0.0 -- naively dividing by it produces
    spurious near-1.0 "autocorrelation." Regression test for that bug,
    found while constructing this test suite."""
    series = np.full(200, 0.01)
    ac = autocorrelation(series, max_lag=50)
    assert np.allclose(ac, 0.0)


def test_autocorrelation_degenerate_short_series():
    assert len(autocorrelation([1.0, 2.0], max_lag=5)) == 0


def test_dominant_spectral_power_ratio_hand_computed():
    n = 100
    t = np.arange(n)
    pure_sine = np.sin(2 * np.pi * t / 10.0)
    result = dominant_spectral_power_ratio(pure_sine)
    # A single clean sinusoid should concentrate nearly all power in one bin.
    assert result["power_ratio"] > 0.9
    assert result["dominant_period_steps"] == pytest.approx(10.0, abs=1.0)


def test_dominant_spectral_power_ratio_degenerate_constant():
    result = dominant_spectral_power_ratio(np.full(50, 0.3))
    assert math.isnan(result["power_ratio"])


def test_band_transitions_hand_computed():
    series = [0.0, 0.0, 0.5, 0.5, 0.5, 0.9, 0.9]
    result = band_transitions(series, lower_bound=0.1, upper_bound=0.8, min_dwell_steps=1)
    assert result["n_transitions"] == 2
    assert result["segments"] == [("depleted", 2), ("interior", 3), ("abundant", 2)]


def test_band_transitions_collapses_short_dwells():
    # A single-step excursion into "abundant" should be swallowed into its
    # neighboring "interior" segment, not counted as two real transitions.
    series = [0.5] * 5 + [0.9] + [0.5] * 5
    result = band_transitions(series, lower_bound=0.1, upper_bound=0.8, min_dwell_steps=3)
    assert result["n_transitions"] == 0
    assert len(result["segments"]) == 1


def test_band_transitions_empty_series():
    result = band_transitions([], lower_bound=0.1, upper_bound=0.8)
    assert result == {"n_transitions": 0, "segments": []}


# ---------------------------------------------------------------------
# classify_regime -- the required Work Package A4 validation scenarios.
# ---------------------------------------------------------------------
def test_classifier_version_is_exported_and_stable_string():
    assert isinstance(CLASSIFIER_VERSION, str) and CLASSIFIER_VERSION


def test_burn_in_excludes_an_initialization_transient():
    """A wild spike confined entirely to the first 20% of the series must
    not affect the label or any post-burn-in statistic."""
    n = 200
    transient = np.full(40, 0.99)
    stable = 0.5 + RNG.normal(0, 0.01, n - 40)
    series = np.concatenate([transient, stable])
    result = classify_regime(series, burn_in_fraction=0.2)
    assert result["burn_in_steps"] == 40
    assert result["analyzed_window"] == [40, 200]
    assert result["label"] == "interior-persistent"
    # The excluded transient's extreme value must not leak into the
    # reported mean/terminal occupancy.
    assert result["mean_occupancy"] < 0.6


def test_explicit_burn_in_steps_overrides_fraction():
    series = np.concatenate([np.full(10, 0.99), np.full(90, 0.5)])
    result = classify_regime(series, burn_in_fraction=0.5, burn_in_steps=10)
    assert result["burn_in_steps"] == 10
    assert result["n_steps_analyzed"] == 90


def test_constant_depleted_trajectory():
    result = classify_regime(np.full(200, 0.01))
    assert result["label"] == "depleted"
    assert result["depleted_criteria_met"] is True


def test_constant_abundant_trajectory():
    result = classify_regime(np.full(200, 0.95))
    assert result["label"] == "abundant"
    assert result["abundant_criteria_met"] is True


def test_stable_interior_trajectory():
    series = 0.5 + RNG.normal(0, 0.01, 200)
    result = classify_regime(series)
    assert result["label"] == "interior-persistent"


def test_monotonic_decline_is_never_classified_as_oscillation():
    series = np.linspace(0.9, 0.0, 200)
    result = classify_regime(series)
    assert result["label"] != "oscillatory"
    assert result["strong_trend"] is True
    assert result["has_multi_cycle_oscillation_signature"] is False


def test_damped_oscillation_is_not_classified_as_sustained_oscillation():
    n = 200
    t = np.arange(n)
    series = 0.5 + 0.3 * np.exp(-t / 40.0) * np.sin(2 * np.pi * t / 20.0)
    result = classify_regime(series)
    assert result["label"] != "oscillatory"
    assert result["has_multi_cycle_oscillation_signature"] is False


def test_sustained_multi_cycle_oscillation_is_classified_oscillatory():
    n = 200
    t = np.arange(n)
    series = 0.5 + 0.3 * np.sin(2 * np.pi * t / 25.0) + RNG.normal(0, 0.005, n)
    result = classify_regime(series)
    assert result["label"] == "oscillatory"
    assert result["has_multi_cycle_oscillation_signature"] is True
    assert result["n_completed_cycles"] >= 3


def test_small_amplitude_noise_is_not_classified_as_oscillation():
    series = 0.5 + RNG.normal(0, 0.01, 200)
    result = classify_regime(series)
    assert result["label"] != "oscillatory"


def test_intermittent_band_switching():
    segments = [
        ("depleted", 0.02, 15),
        ("interior", 0.5, 22),
        ("depleted", 0.02, 9),
        ("interior", 0.55, 30),
        ("depleted", 0.03, 12),
        ("interior", 0.45, 40),
        ("depleted", 0.02, 20),
        ("interior", 0.5, 52),
    ]
    series = []
    for _, val, dur in segments:
        series.extend(list(val + RNG.normal(0, 0.01, dur)))
    result = classify_regime(np.array(series))
    assert result["label"] == "intermittent"
    assert result["n_band_transitions"] > 1
    assert result["oscillatory_criteria_met"] is False


def test_one_time_structural_break_is_not_forced_into_a_named_regime():
    series = np.concatenate([np.full(100, 0.9), np.full(100, 0.02)])
    result = classify_regime(series)
    # A single abrupt regime shift satisfies none of the strict, duration/
    # fraction-gated criteria for any named label -- it must not be forced.
    assert result["label"] == "unclassified"


def test_initialization_overshoot_then_stability_settles_interior():
    n = 200
    overshoot = np.concatenate([np.full(40, 0.99), 0.5 + RNG.normal(0, 0.01, n - 40)])
    result = classify_regime(overshoot, burn_in_fraction=0.2)
    assert result["label"] == "interior-persistent"


def test_near_threshold_behavior_does_not_crash_and_is_not_forced():
    series = 0.05 + RNG.normal(0, 0.02, 200)
    result = classify_regime(series)
    assert result["label"] in {
        "depleted",
        "interior-persistent",
        "oscillatory",
        "intermittent",
        "unclassified",
    }


def test_short_series_is_unclassified_not_crashing():
    result = classify_regime([0.5, 0.5, 0.5])
    assert result["label"] == "unclassified"
    assert result["n_steps_analyzed"] == 2  # burn-in (round(0.2*3)=1) excludes one step


def test_missing_data_empty_series_is_unclassified():
    result = classify_regime([])
    assert result["label"] == "unclassified"
    assert result["n_steps_analyzed"] == 0
    assert math.isnan(result["mean_occupancy"])


def test_degenerate_constant_series_single_step():
    result = classify_regime([0.5])
    assert result["label"] == "unclassified"


def test_never_uses_the_word_for_a_proven_stable_fixed_point():
    """Structural guard extending the Level 0.3 discipline over the new
    Work Package A module section: the same forbidden dynamical-systems
    term must not appear anywhere in this file's own source, nor leak
    into any label this classifier can emit."""
    import inspect

    from abm_governance.observer import regulation_diagnostics

    source = inspect.getsource(regulation_diagnostics)
    assert "attractor" not in source.lower()

    allowed_labels = {
        "depleted",
        "abundant",
        "interior-persistent",
        "oscillatory",
        "intermittent",
        "unclassified",
    }
    for _ in range(30):
        random_series = RNG.normal(0.5, 0.3, RNG.integers(0, 300))
        result = classify_regime(np.clip(random_series, 0.0, 1.0))
        assert result["label"] in allowed_labels
