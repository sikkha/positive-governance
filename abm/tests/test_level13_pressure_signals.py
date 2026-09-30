"""Level 1.3, Section 5: core historical variables -- pressure-history
generation, cumulative-exposure/rescale utilities, the generic
first-sustained-crossing primitive, and Simulation wiring."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.core.historical_pressure import (
    PressureHistorySpec,
    VALID_PRESSURE_HISTORY_KINDS,
    cumulative_exposure,
    first_sustained_crossing,
    generate_pressure_series,
    rescale_to_target_exposure,
)
from abm_governance.simulation import Simulation


class TestConstantKinds:
    def test_constant_low_is_flat_at_low_level(self):
        series = generate_pressure_series(PressureHistorySpec(kind="constant_low", low_level=0.2), n_steps=50)
        assert np.all(series == 0.2)
        assert len(series) == 50

    def test_constant_high_is_flat_at_high_level(self):
        series = generate_pressure_series(PressureHistorySpec(kind="constant_high", high_level=0.8), n_steps=50)
        assert np.all(series == 0.8)


class TestPulseKinds:
    def test_early_pulse_window_matches_spec(self):
        spec = PressureHistorySpec(kind="early_pulse", low_level=0.1, high_level=0.9, onset_step=5, duration_steps=10)
        series = generate_pressure_series(spec, n_steps=60)
        assert np.all(series[:5] == 0.1)
        assert np.all(series[5:15] == 0.9)
        assert np.all(series[15:] == 0.1)  # decay_rate=0 -> immediate drop

    def test_late_pulse_positions_window_late(self):
        spec = PressureHistorySpec(kind="late_pulse", low_level=0.1, high_level=0.9, onset_step=40, duration_steps=10)
        series = generate_pressure_series(spec, n_steps=60)
        assert np.all(series[:40] == 0.1)
        assert np.all(series[40:50] == 0.9)
        assert np.all(series[50:] == 0.1)

    def test_decay_rate_produces_gradual_fade_never_below_low(self):
        spec = PressureHistorySpec(
            kind="early_pulse", low_level=0.1, high_level=0.9, onset_step=0, duration_steps=5, decay_rate=0.3,
        )
        series = generate_pressure_series(spec, n_steps=40)
        post_window = series[5:]
        assert np.all(post_window >= 0.1 - 1e-12)
        assert np.all(np.diff(post_window) <= 1e-12)  # monotonically non-increasing
        assert post_window[-1] == pytest.approx(0.1, abs=1e-3)


class TestRampKinds:
    def test_gradual_rise_endpoints(self):
        spec = PressureHistorySpec(kind="gradual_rise", low_level=0.0, high_level=1.0, onset_step=0, duration_steps=20)
        series = generate_pressure_series(spec, n_steps=20)
        assert series[0] == pytest.approx(0.0)
        assert series[-1] == pytest.approx(1.0)
        assert np.all(np.diff(series) >= -1e-12)

    def test_gradual_decline_endpoints(self):
        spec = PressureHistorySpec(kind="gradual_decline", low_level=0.0, high_level=1.0, onset_step=0, duration_steps=20)
        series = generate_pressure_series(spec, n_steps=20)
        assert series[0] == pytest.approx(1.0)
        assert series[-1] == pytest.approx(0.0)
        assert np.all(np.diff(series) <= 1e-12)


class TestRepeatedShocks:
    def test_shock_count_and_spacing(self):
        spec = PressureHistorySpec(
            kind="repeated_shocks", low_level=0.0, high_level=1.0,
            onset_step=0, n_shocks=3, shock_width_steps=2, shock_interval_steps=10,
        )
        series = generate_pressure_series(spec, n_steps=40)
        # Shock windows: [0,2), [10,12), [20,22)
        assert np.all(series[0:2] == 1.0)
        assert np.all(series[2:10] == 0.0)
        assert np.all(series[10:12] == 1.0)
        assert np.all(series[20:22] == 1.0)
        assert np.sum(series == 1.0) == 6

    def test_zero_shocks_is_flat_low(self):
        spec = PressureHistorySpec(kind="repeated_shocks", low_level=0.3, n_shocks=0)
        series = generate_pressure_series(spec, n_steps=20)
        assert np.all(series == 0.3)


class TestStochasticReproducible:
    def test_requires_rng(self):
        spec = PressureHistorySpec(kind="stochastic_reproducible")
        with pytest.raises(ValueError):
            generate_pressure_series(spec, n_steps=10, rng=None)

    def test_same_seed_same_series(self):
        spec = PressureHistorySpec(kind="stochastic_reproducible", low_level=0.5, volatility_std=0.1)
        s1 = generate_pressure_series(spec, n_steps=30, rng=np.random.default_rng(7))
        s2 = generate_pressure_series(spec, n_steps=30, rng=np.random.default_rng(7))
        assert np.array_equal(s1, s2)

    def test_different_seed_diverges(self):
        spec = PressureHistorySpec(kind="stochastic_reproducible", low_level=0.5, volatility_std=0.1)
        s1 = generate_pressure_series(spec, n_steps=30, rng=np.random.default_rng(7))
        s2 = generate_pressure_series(spec, n_steps=30, rng=np.random.default_rng(8))
        assert not np.array_equal(s1, s2)

    def test_never_negative(self):
        spec = PressureHistorySpec(kind="stochastic_reproducible", low_level=0.01, volatility_std=5.0)
        series = generate_pressure_series(spec, n_steps=200, rng=np.random.default_rng(1))
        assert np.all(series >= 0.0)


class TestValidation:
    def test_unknown_kind_rejected(self):
        with pytest.raises(ValueError):
            generate_pressure_series(PressureHistorySpec(kind="not_a_real_kind"), n_steps=10)

    def test_high_below_low_rejected(self):
        with pytest.raises(ValueError):
            generate_pressure_series(PressureHistorySpec(low_level=0.9, high_level=0.1), n_steps=10)

    def test_negative_n_steps_rejected(self):
        with pytest.raises(ValueError):
            generate_pressure_series(PressureHistorySpec(), n_steps=0)

    def test_bad_decay_rate_rejected(self):
        with pytest.raises(ValueError):
            generate_pressure_series(PressureHistorySpec(decay_rate=1.5), n_steps=10)

    def test_all_valid_kinds_are_generatable(self):
        for kind in VALID_PRESSURE_HISTORY_KINDS:
            spec = PressureHistorySpec(kind=kind, volatility_std=0.1)
            rng = np.random.default_rng(0) if kind == "stochastic_reproducible" else None
            series = generate_pressure_series(spec, n_steps=25, rng=rng)
            assert len(series) == 25
            assert np.all(np.isfinite(series))


class TestCumulativeExposureAndRescale:
    def test_cumulative_exposure_is_the_sum(self):
        series = np.array([1.0, 2.0, 3.0])
        assert cumulative_exposure(series) == 6.0

    def test_rescale_matches_target_and_preserves_shape(self):
        series = generate_pressure_series(
            PressureHistorySpec(kind="early_pulse", low_level=0.0, high_level=1.0, onset_step=0, duration_steps=5),
            n_steps=20,
        )
        rescaled = rescale_to_target_exposure(series, target_exposure=50.0)
        assert cumulative_exposure(rescaled) == pytest.approx(50.0)
        # shape preserved: the ratio between any two nonzero entries is unchanged
        nz = series > 0
        assert np.allclose(rescaled[nz] / series[nz], rescaled[nz][0] / series[nz][0])

    def test_all_zero_series_returned_unchanged(self):
        series = np.zeros(10)
        rescaled = rescale_to_target_exposure(series, target_exposure=5.0)
        assert np.array_equal(rescaled, series)

    def test_negative_target_rejected(self):
        with pytest.raises(ValueError):
            rescale_to_target_exposure(np.ones(5), target_exposure=-1.0)

    def test_matched_pair_can_hold_exposure_equal_across_reversed_order(self):
        """Section 5's own "paired sequence-reversal / matched cumulative
        exposure" requirement, exercised directly: build W-first and
        B-first histories with identical total exposure."""
        w_first = generate_pressure_series(
            PressureHistorySpec(kind="early_pulse", low_level=0.0, high_level=1.0, onset_step=0, duration_steps=10),
            n_steps=60,
        )
        b_first_as_w = generate_pressure_series(
            PressureHistorySpec(kind="late_pulse", low_level=0.0, high_level=1.0, onset_step=50, duration_steps=10),
            n_steps=60,
        )
        assert cumulative_exposure(w_first) == pytest.approx(cumulative_exposure(b_first_as_w))
        assert not np.array_equal(w_first, b_first_as_w)  # genuinely different temporal order


class TestFirstSustainedCrossing:
    def test_finds_first_run_meeting_duration(self):
        series = np.array([0, 0, 1, 1, 0, 1, 1, 1, 1, 0])
        # threshold 1, min_duration 3 -> first run of len>=3 starts at index 5
        assert first_sustained_crossing(series, threshold=1, min_duration_steps=3) == 5

    def test_single_spike_does_not_count(self):
        series = np.array([0, 1, 0, 0, 0])
        assert first_sustained_crossing(series, threshold=1, min_duration_steps=2) is None

    def test_returns_none_when_never_sustained(self):
        series = np.zeros(20)
        assert first_sustained_crossing(series, threshold=1.0, min_duration_steps=5) is None

    def test_exact_length_run_counts(self):
        series = np.array([1, 1, 1])
        assert first_sustained_crossing(series, threshold=1, min_duration_steps=3) == 0

    def test_invalid_min_duration_rejected(self):
        with pytest.raises(ValueError):
            first_sustained_crossing(np.ones(5), threshold=1.0, min_duration_steps=0)


class TestSimulationWiring:
    def test_disabled_channel_has_no_series_even_when_module_enabled(self):
        config = SimulationConfig.level12b_frozen_reference(
            population_size=20, n_steps=30, seed=1, historical_module_enabled=True, security_pressure_enabled=False,
        )
        sim = Simulation(config)
        assert sim.historical_state == {}

    def test_enabled_channel_produces_correct_length_series(self):
        config = SimulationConfig.level12b_frozen_reference(
            population_size=20, n_steps=30, seed=1, historical_module_enabled=True, security_pressure_enabled=True,
            security_pressure_history_kind="constant_high", security_pressure_high_level=0.7,
        )
        sim = Simulation(config)
        series = sim.historical_state["security_pressure_series"]
        assert len(series) == 30
        assert np.all(series == 0.7)
        assert "bargaining_pressure_series" not in sim.historical_state
        assert "coordination_complexity_series" not in sim.historical_state

    def test_all_three_channels_can_be_enabled_simultaneously(self):
        config = SimulationConfig.level12b_frozen_reference(
            population_size=20, n_steps=30, seed=1, historical_module_enabled=True,
            security_pressure_enabled=True, bargaining_pressure_enabled=True, coordination_complexity_enabled=True,
        )
        sim = Simulation(config)
        assert set(sim.historical_state.keys()) == {
            "security_pressure_series", "bargaining_pressure_series", "coordination_complexity_series",
        }

    def test_stochastic_channel_reproducible_across_identical_seeds(self):
        kwargs = dict(
            population_size=20, n_steps=30, seed=5, historical_module_enabled=True, security_pressure_enabled=True,
            security_pressure_history_kind="stochastic_reproducible", security_pressure_volatility_std=0.05,
        )
        s1 = Simulation(SimulationConfig.level12b_frozen_reference(**kwargs)).historical_state["security_pressure_series"]
        s2 = Simulation(SimulationConfig.level12b_frozen_reference(**kwargs)).historical_state["security_pressure_series"]
        assert np.array_equal(s1, s2)

    def test_bad_pressure_field_raises_at_config_construction(self):
        with pytest.raises(ValueError):
            SimulationConfig.level12b_frozen_reference(security_pressure_history_kind="not_a_kind")
