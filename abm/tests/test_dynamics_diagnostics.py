"""Work Package F: reusable dynamical diagnostics, checked against small
hand-computable series. None of these functions classify a trajectory —
see observer/dynamics.py's module docstring for the (unimplemented,
documentation-only) operational criteria."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.observer.dynamics import (
    autocorrelation,
    change_point_candidates,
    detrended_autocorrelation,
    endpoint_dispersion,
    periodogram,
    regime_time_fraction,
    rolling_mean,
    rolling_variance,
    stationarity_heuristic,
)


def test_rolling_mean_matches_hand_computation():
    series = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    out = rolling_mean(series, window=2)
    # window=2: [1], [1,2], [2,3], [3,4], [4,5] -> means
    assert out == pytest.approx([1.0, 1.5, 2.5, 3.5, 4.5])


def test_rolling_variance_matches_hand_computation():
    series = np.array([1.0, 1.0, 1.0, 5.0])
    out = rolling_variance(series, window=2)
    # [1] var=0, [1,1] var=0, [1,1] var=0, [1,5] var = ((1-3)^2+(5-3)^2)/2 = 4
    assert out == pytest.approx([0.0, 0.0, 0.0, 4.0])


def test_rolling_functions_reject_bad_window():
    with pytest.raises(ValueError):
        rolling_mean(np.array([1.0, 2.0]), window=0)
    with pytest.raises(ValueError):
        rolling_variance(np.array([1.0, 2.0]), window=-1)


def test_autocorrelation_of_constant_series_is_nan():
    series = np.array([5.0] * 10)
    acf = autocorrelation(series, max_lag=3)
    assert np.all(np.isnan(acf))


def test_autocorrelation_lag_zero_is_one():
    series = np.array([1.0, 3.0, 2.0, 5.0, 4.0, 6.0])
    acf = autocorrelation(series, max_lag=2)
    assert acf[0] == pytest.approx(1.0)


def test_autocorrelation_alternating_series_hand_computed():
    # series = [1, -1, 1, -1, 1, -1], mean 0, so centered == series.
    # This uses the standard "biased" ACF estimator (normalizes every lag
    # by the FULL series' variance, not the shorter overlapping window's),
    # so finite-sample values are not exactly +-1 even for a perfectly
    # alternating series — hand-computed below.
    # var = sum(x_i^2) = 6.
    # lag=1: sum(x[:5]*x[1:]) = (1*-1)+(-1*1)+(1*-1)+(-1*1)+(1*-1) = -5 -> -5/6
    # lag=2: sum(x[:4]*x[2:]) = (1*1)+(-1*-1)+(1*1)+(-1*-1) = 4 -> 4/6
    series = np.array([1.0, -1.0, 1.0, -1.0, 1.0, -1.0])
    acf = autocorrelation(series, max_lag=2)
    assert acf[0] == pytest.approx(1.0)
    assert acf[1] == pytest.approx(-5 / 6)
    assert acf[2] == pytest.approx(4 / 6)


def test_detrended_autocorrelation_removes_pure_linear_trend():
    # A pure linear trend, once first-differenced, becomes a constant
    # series -> its autocorrelation is NaN (no residual fluctuation left).
    series = np.arange(20.0)
    acf = detrended_autocorrelation(series, max_lag=3)
    assert np.all(np.isnan(acf))


def test_periodogram_detects_a_pure_sine_frequency():
    n = 200
    freq = 0.1  # cycles per sample
    t = np.arange(n)
    series = np.sin(2 * np.pi * freq * t)
    freqs, power = periodogram(series)
    peak_freq = freqs[np.argmax(power)]
    assert peak_freq == pytest.approx(freq, abs=0.01)


def test_periodogram_on_short_series_is_empty():
    freqs, power = periodogram(np.array([1.0]))
    assert len(freqs) == 0
    assert len(power) == 0


def test_stationarity_heuristic_flags_a_clear_level_shift():
    # Nonzero mean on the "stable" series avoids a division-by-near-zero
    # blowup in the coefficient-of-variation (a known CV pitfall, not a
    # bug: CV is only a meaningful stability indicator when the series
    # doesn't hover near zero).
    stable = np.random.default_rng(0).normal(50.0, 0.5, size=100)
    shifting = np.concatenate([np.zeros(20), np.ones(20) * 10, np.ones(20) * 100])
    stable_result = stationarity_heuristic(stable, n_windows=5)
    shifting_result = stationarity_heuristic(shifting, n_windows=3)
    assert stable_result["chunk_mean_cv"] < shifting_result["chunk_mean_cv"]


def test_stationarity_heuristic_short_series_returns_nan():
    result = stationarity_heuristic(np.array([1.0, 2.0]), n_windows=5)
    assert result["chunk_mean_cv"] != result["chunk_mean_cv"]  # NaN


def test_change_point_candidates_detects_an_obvious_step():
    series = np.concatenate([np.zeros(30), np.ones(30) * 100])
    candidates = change_point_candidates(series, window=5, z_threshold=2.0)
    assert len(candidates) > 0
    # The detected candidate(s) should be near the true jump at index 30.
    assert any(25 <= c <= 35 for c in candidates)


def test_change_point_candidates_empty_for_flat_series():
    series = np.ones(40) * 5.0
    assert change_point_candidates(series, window=5, z_threshold=2.0) == []


def test_regime_time_fraction_sums_to_one():
    series = np.random.default_rng(0).uniform(0, 1, size=200)
    result = regime_time_fraction(series, n_bins=4)
    assert sum(result["fractions"]) == pytest.approx(1.0)
    assert len(result["fractions"]) == 4


def test_regime_time_fraction_constant_series_is_single_bin():
    result = regime_time_fraction(np.ones(10) * 3.0, n_bins=5)
    assert result["fractions"] == [1.0]


def test_endpoint_dispersion_hand_computed():
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    result = endpoint_dispersion(values)
    assert result["n"] == 5
    assert result["mean"] == pytest.approx(3.0)
    assert result["min"] == 1.0
    assert result["max"] == 5.0
    assert result["iqr"] == pytest.approx(2.0)  # 75th pct=4, 25th pct=2


def test_endpoint_dispersion_ignores_nan_values():
    values = np.array([1.0, np.nan, 3.0])
    result = endpoint_dispersion(values)
    assert result["n"] == 2
    assert result["mean"] == pytest.approx(2.0)


def test_endpoint_dispersion_empty_input():
    result = endpoint_dispersion(np.array([]))
    assert result["n"] == 0
    assert result["mean"] != result["mean"]  # NaN
