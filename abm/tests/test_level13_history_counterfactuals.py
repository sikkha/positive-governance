"""Level 1.3, Work Package E (Section 10): history erasure and sequence
reversal counterfactuals (``core/historical_counterfactuals.py`` +
``Simulation``'s ``historical_pressure_series_override`` constructor
parameter).

See ``core/historical_counterfactuals.py``'s own module docstring for
the context-loss disclosure and the interpretive choices this work
package's tests are built on."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.core import historical_counterfactuals as hc
from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation


class TestErasePressureFrom:
    def test_erases_from_step_onward_to_floor(self):
        series = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        out = hc.erase_pressure_from(series, step=2)
        assert np.array_equal(out, [1.0, 2.0, 0.0, 0.0, 0.0])

    def test_leaves_prefix_untouched(self):
        series = np.array([1.0, 2.0, 3.0, 4.0])
        out = hc.erase_pressure_from(series, step=3)
        assert out[:3].tolist() == series[:3].tolist()

    def test_custom_floor_level(self):
        series = np.array([1.0, 2.0, 3.0])
        out = hc.erase_pressure_from(series, step=1, floor_level=0.25)
        assert np.array_equal(out, [1.0, 0.25, 0.25])

    def test_step_zero_erases_everything(self):
        series = np.array([1.0, 2.0, 3.0])
        out = hc.erase_pressure_from(series, step=0)
        assert np.array_equal(out, [0.0, 0.0, 0.0])

    def test_step_beyond_length_is_a_full_noop_copy(self):
        series = np.array([1.0, 2.0, 3.0])
        out = hc.erase_pressure_from(series, step=100)
        assert np.array_equal(out, series)
        assert out is not series

    def test_negative_step_raises(self):
        with pytest.raises(ValueError):
            hc.erase_pressure_from(np.array([1.0, 2.0]), step=-1)

    def test_does_not_mutate_input(self):
        series = np.array([1.0, 2.0, 3.0])
        original = series.copy()
        hc.erase_pressure_from(series, step=1)
        assert np.array_equal(series, original)

    def test_returns_float_array_even_for_int_input(self):
        series = np.array([1, 2, 3, 4])
        out = hc.erase_pressure_from(series, step=2)
        assert out.dtype == np.float64


class TestReversePressureOrder:
    def test_reverses_order(self):
        series = np.array([1.0, 2.0, 3.0, 4.0])
        out = hc.reverse_pressure_order(series)
        assert np.array_equal(out, [4.0, 3.0, 2.0, 1.0])

    def test_preserves_sum_and_multiset(self):
        series = np.array([1.0, 5.0, 2.0, 9.0, 0.5])
        out = hc.reverse_pressure_order(series)
        assert out.sum() == pytest.approx(series.sum())
        assert sorted(out.tolist()) == sorted(series.tolist())

    def test_does_not_mutate_input(self):
        series = np.array([1.0, 2.0, 3.0])
        original = series.copy()
        hc.reverse_pressure_order(series)
        assert np.array_equal(series, original)

    def test_double_reversal_is_identity(self):
        series = np.array([1.0, 7.0, 3.0, 2.0])
        out = hc.reverse_pressure_order(hc.reverse_pressure_order(series))
        assert np.array_equal(out, series)

    def test_single_element_series(self):
        series = np.array([5.0])
        out = hc.reverse_pressure_order(series)
        assert np.array_equal(out, [5.0])

    def test_empty_series(self):
        series = np.array([])
        out = hc.reverse_pressure_order(series)
        assert out.size == 0


def _single_channel_config(**overrides):
    kwargs = dict(
        population_size=20, n_steps=60, seed=17,
        historical_module_enabled=True, security_pressure_enabled=True,
        security_pressure_history_kind="early_pulse", security_pressure_low_level=0.1,
        security_pressure_high_level=0.8, security_pressure_onset_step=20,
        security_pressure_duration_steps=15, security_pressure_decay_rate=0.05,
        security_pressure_volatility_std=0.0, security_pressure_n_shocks=1,
        security_pressure_shock_width_steps=5, security_pressure_shock_interval_steps=10,
    )
    kwargs.update(overrides)
    return SimulationConfig.level1_rule_formation_default(**kwargs)


class TestSimulationOverrideMechanism:
    def test_backward_compatible_default_arg_produces_identical_run(self):
        # A config with no override supplied must behave exactly as
        # before this task's Simulation.__init__ signature change.
        config = _single_channel_config()
        r1 = Simulation(config).run()
        r2 = Simulation(config, historical_pressure_series_override=None).run()
        assert len(r1.metrics) == len(r2.metrics)
        for row1, row2 in zip(r1.metrics, r2.metrics):
            for key in row1:
                v1, v2 = row1[key], row2[key]
                if isinstance(v1, float) and np.isnan(v1):
                    assert np.isnan(v2)
                else:
                    assert v1 == v2

    def test_override_is_used_verbatim(self):
        config = _single_channel_config(n_steps=10)
        override_series = np.linspace(0.0, 1.0, 10)
        sim = Simulation(config, historical_pressure_series_override={"security_pressure_series": override_series})
        assert np.array_equal(sim.historical_state["security_pressure_series"], override_series)

    def test_override_bypasses_generation_for_that_channel_only(self):
        # With one channel enabled and overridden, the run must not
        # raise and must still populate historical_state normally.
        config = _single_channel_config(n_steps=10)
        override_series = np.zeros(10)
        sim = Simulation(config, historical_pressure_series_override={"security_pressure_series": override_series})
        sim.run()
        assert np.array_equal(sim.historical_state["security_pressure_series"], override_series)

    def test_other_rng_streams_are_unaffected_by_the_override(self):
        # Same seed, one channel enabled+overridden vs. generated: the
        # population/agent-level machinery (not the overridden pressure
        # channel itself) must draw identically, since it lives on
        # wholly separate named RNG streams.
        config = _single_channel_config(n_steps=40)
        base = Simulation(config)
        base.run()
        realized = base.historical_state["security_pressure_series"]

        erased = hc.erase_pressure_from(realized, step=20)
        cf = Simulation(config, historical_pressure_series_override={"security_pressure_series": erased})
        cf.run()

        assert len(base.agents) == len(cf.agents)
        for a1, a2 in zip(base.agents, cf.agents):
            assert a1.agent_id == a2.agent_id
            assert a1.patch_id == a2.patch_id


class TestMatchedPairCounterfactuals:
    def test_erasure_matched_pair_diverges_after_onset(self):
        config = _single_channel_config(n_steps=60)
        base = Simulation(config)
        base.run()
        realized = base.historical_state["security_pressure_series"]
        assert realized[30] != 0.0  # sanity: pressure is actually present mid-run

        erased = hc.erase_pressure_from(realized, step=20)
        cf = Simulation(config, historical_pressure_series_override={"security_pressure_series": erased})
        cf.run()

        assert np.array_equal(cf.historical_state["security_pressure_series"][:20], realized[:20])
        assert np.all(cf.historical_state["security_pressure_series"][20:] == 0.0)
        assert not np.array_equal(cf.historical_state["security_pressure_series"], realized)

    def test_reversal_matched_pair_preserves_total_pressure(self):
        config = _single_channel_config(n_steps=60)
        base = Simulation(config)
        base.run()
        realized = base.historical_state["security_pressure_series"]

        reversed_series = hc.reverse_pressure_order(realized)
        cf = Simulation(config, historical_pressure_series_override={"security_pressure_series": reversed_series})
        cf.run()

        assert cf.historical_state["security_pressure_series"].sum() == pytest.approx(realized.sum())
        assert not np.array_equal(cf.historical_state["security_pressure_series"], realized)

    def test_full_pipeline_runs_without_error_end_to_end(self):
        config = _single_channel_config(n_steps=80, population_size=30)
        base = Simulation(config)
        base.run()
        realized = base.historical_state["security_pressure_series"]
        for cf_series in (hc.erase_pressure_from(realized, step=40), hc.reverse_pressure_order(realized)):
            cf = Simulation(config, historical_pressure_series_override={"security_pressure_series": cf_series})
            result = cf.run()
            assert len(result.metrics) == config.n_steps
