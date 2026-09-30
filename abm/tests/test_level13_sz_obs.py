"""Level 1.3, Work Package G (Section 12): observer-side S_obs/Z_obs
measurement layer (``observer/sz_obs.py``).

See that module's own docstring for the context-loss disclosure and the
composite-membership rationale this work package's tests are built
on."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import (
    AuditEvent,
    DelegateAppointmentEvent,
    EventLog,
    LegitimacyEvent,
    MonitoringEvent,
    RuleAdoptionEvent,
)
from abm_governance.observer import sz_obs
from abm_governance.simulation import Simulation


def _rule_adoption(step, rule_id, patch_id=0, proposer=0):
    return RuleAdoptionEvent(
        step=step, patch_id=patch_id, rule_id=rule_id, rule_lineage_id=rule_id, proposer=proposer,
        n_eligible=3, n_supporters=3, support_fraction=1.0, adoption_threshold=0.5, adoption_process="voluntary",
    )


def _delegate_appoint(step, rule_id, patch_id=0, delegate_id=1, agent=1):
    return DelegateAppointmentEvent(
        step=step, patch_id=patch_id, rule_id=rule_id, rule_lineage_id=rule_id, delegate_id=delegate_id,
        agent=agent, tasks=("monitoring",), appointment_method="lottery", candidate_set=(agent,),
        selector_population=(0, 1, 2), support_fraction=1.0, predecessor_delegate_id=None,
        institutional_memory_inherited=0.0,
    )


def _monitoring(step, rule_id, patch_id=0, target=2):
    return MonitoringEvent(
        step=step, patch_id=patch_id, rule_id=rule_id, target=target,
        true_compliance=True, detected_violation=False, outcome="true_negative", monitor=1,
    )


def _audit(step, rule_id, patch_id=0, delegate_id=1, auditor=2):
    return AuditEvent(
        step=step, patch_id=patch_id, rule_id=rule_id, delegate_id=delegate_id, auditor=auditor,
        actual_misconduct_occurred=False, found_misconduct=False, outcome="true_negative", cost=0.1,
    )


def _legitimacy(step, rule_id, patch_id=0, performance=0.5, procedural=0.5):
    return LegitimacyEvent(
        step=step, patch_id=patch_id, rule_id=rule_id,
        performance_legitimacy=performance, procedural_legitimacy=procedural,
        performance_legitimacy_target=performance, procedural_legitimacy_target=procedural,
    )


def _log_with(events_by_field: dict) -> EventLog:
    log = EventLog()
    for field, events in events_by_field.items():
        getattr(log, field).extend(events)
    return log


class TestPerformanceLegitimacySeries:
    def test_all_zero_with_no_events(self):
        log = EventLog()
        out = sz_obs.performance_legitimacy_series(log, n_steps=10)
        assert np.all(out == 0.0)

    def test_single_rule_reproduces_its_own_value(self):
        log = _log_with({"legitimacy_events": [_legitimacy(3, rule_id=1, performance=0.8)]})
        out = sz_obs.performance_legitimacy_series(log, n_steps=10)
        assert out[3] == pytest.approx(0.8)
        assert out[0] == 0.0

    def test_averages_across_rules_at_the_same_step(self):
        log = _log_with({"legitimacy_events": [
            _legitimacy(2, rule_id=1, performance=1.0), _legitimacy(2, rule_id=2, performance=0.0),
        ]})
        out = sz_obs.performance_legitimacy_series(log, n_steps=5)
        assert out[2] == pytest.approx(0.5)

    def test_patch_scoping(self):
        log = _log_with({"legitimacy_events": [
            _legitimacy(1, rule_id=1, patch_id=0, performance=1.0), _legitimacy(1, rule_id=2, patch_id=1, performance=0.0),
        ]})
        out = sz_obs.performance_legitimacy_series(log, n_steps=5, patch_ids=frozenset({0}))
        assert out[1] == pytest.approx(1.0)


class TestProceduralLegitimacySeries:
    def test_independent_of_performance_channel(self):
        log = _log_with({"legitimacy_events": [_legitimacy(4, rule_id=1, performance=0.9, procedural=0.1)]})
        perf = sz_obs.performance_legitimacy_series(log, n_steps=10)
        proc = sz_obs.procedural_legitimacy_series(log, n_steps=10)
        assert perf[4] == pytest.approx(0.9)
        assert proc[4] == pytest.approx(0.1)


class TestSObsSeries:
    def test_zero_with_no_events_at_all(self):
        log = EventLog()
        out = sz_obs.s_obs_series(log, n_steps=10)
        assert np.all(out == 0.0)

    def test_rises_with_delegation_and_monitoring_activity(self):
        log = _log_with({
            "rule_adoptions": [_rule_adoption(0, rule_id=1)],
            "delegate_appointments": [_delegate_appoint(0, rule_id=1)],
            "monitorings": [_monitoring(t, rule_id=1) for t in range(10)],
        })
        out = sz_obs.s_obs_series(log, n_steps=10)
        assert out[5] > 0.0

    def test_bounded_in_unit_interval(self):
        log = _log_with({
            "rule_adoptions": [_rule_adoption(0, rule_id=1)],
            "delegate_appointments": [_delegate_appoint(0, rule_id=1)],
            "monitorings": [_monitoring(t, rule_id=1) for t in range(20)],
            "legitimacy_events": [_legitimacy(t, rule_id=1, performance=1.0) for t in range(20)],
        })
        out = sz_obs.s_obs_series(log, n_steps=20)
        assert np.all(out >= 0.0)
        assert np.all(out <= 1.0)

    def test_includes_performance_legitimacy_component(self):
        # With every Work Package B response dimension at zero (no
        # events for them) but full performance legitimacy every step,
        # S_obs must be exactly 1/5 (one nonzero component of five).
        log = _log_with({"legitimacy_events": [_legitimacy(t, rule_id=1, performance=1.0) for t in range(5)]})
        out = sz_obs.s_obs_series(log, n_steps=5)
        assert out[2] == pytest.approx(0.2)


class TestZObsSeries:
    def test_zero_with_no_events_at_all(self):
        log = EventLog()
        out = sz_obs.z_obs_series(log, n_steps=10)
        assert np.all(out == 0.0)

    def test_includes_procedural_legitimacy_component(self):
        # accountability and bargaining_participation both zero (no
        # events); procedural legitimacy full every step -> exactly 1/3.
        log = _log_with({"legitimacy_events": [_legitimacy(t, rule_id=1, procedural=1.0) for t in range(5)]})
        out = sz_obs.z_obs_series(log, n_steps=5)
        assert out[2] == pytest.approx(1.0 / 3.0)

    def test_rises_with_accountability_activity(self):
        log = _log_with({
            "rule_adoptions": [_rule_adoption(0, rule_id=1)],
            "delegate_appointments": [_delegate_appoint(0, rule_id=1)],
            "audits": [_audit(t, rule_id=1) for t in range(10)],
        })
        out = sz_obs.z_obs_series(log, n_steps=10)
        assert out[5] > 0.0

    def test_bounded_in_unit_interval(self):
        log = _log_with({
            "rule_adoptions": [_rule_adoption(0, rule_id=1)],
            "delegate_appointments": [_delegate_appoint(0, rule_id=1)],
            "audits": [_audit(t, rule_id=1) for t in range(20)],
            "legitimacy_events": [_legitimacy(t, rule_id=1, procedural=1.0) for t in range(20)],
        })
        out = sz_obs.z_obs_series(log, n_steps=20)
        assert np.all(out >= 0.0)
        assert np.all(out <= 1.0)


class TestSObsZObsSeriesWrapper:
    def test_matches_individual_calls(self):
        log = _log_with({"legitimacy_events": [_legitimacy(1, rule_id=1, performance=0.6, procedural=0.4)]})
        s1, z1 = sz_obs.s_obs_z_obs_series(log, n_steps=5)
        s2 = sz_obs.s_obs_series(log, n_steps=5)
        z2 = sz_obs.z_obs_series(log, n_steps=5)
        assert np.array_equal(s1, s2)
        assert np.array_equal(z1, z2)


class TestSObsZObsSummary:
    def test_returns_expected_keys(self):
        log = EventLog()
        out = sz_obs.s_obs_z_obs_summary(log, n_steps=10)
        assert set(out.keys()) == {"S_obs", "Z_obs"}

    def test_full_run_mean_by_default(self):
        log = _log_with({"legitimacy_events": [_legitimacy(t, rule_id=1, performance=1.0) for t in range(10)]})
        out = sz_obs.s_obs_z_obs_summary(log, n_steps=10)
        assert out["S_obs"] == pytest.approx(0.2)  # 1/5 every step -> mean 0.2

    def test_windowed_mean_restricts_to_trailing_steps(self):
        events = [_legitimacy(t, rule_id=1, performance=(1.0 if t >= 8 else 0.0)) for t in range(10)]
        log = _log_with({"legitimacy_events": events})
        full = sz_obs.s_obs_z_obs_summary(log, n_steps=10)
        windowed = sz_obs.s_obs_z_obs_summary(log, n_steps=10, window_steps=2)
        assert windowed["S_obs"] > full["S_obs"]
        assert windowed["S_obs"] == pytest.approx(0.2)  # both of the last 2 steps at 1.0 performance -> 1/5 mean


class TestEndToEndOnARealRun:
    def test_runs_without_error_and_produces_bounded_series(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=40, n_steps=150, n_patches=3, seed=13,
            monitoring_mode="voluntary", sanction_mode="voluntary",
        )
        sim = Simulation(config)
        sim.run()
        s_series, z_series = sz_obs.s_obs_z_obs_series(sim.event_log, config.n_steps)
        assert len(s_series) == config.n_steps
        assert len(z_series) == config.n_steps
        assert np.all(s_series >= 0.0) and np.all(s_series <= 1.0)
        assert np.all(z_series >= 0.0) and np.all(z_series <= 1.0)
        summary = sz_obs.s_obs_z_obs_summary(sim.event_log, config.n_steps)
        assert 0.0 <= summary["S_obs"] <= 1.0
        assert 0.0 <= summary["Z_obs"] <= 1.0

    def test_runs_with_legitimacy_channels_enabled(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=30, n_steps=120, n_patches=2, seed=21,
            monitoring_mode="voluntary", sanction_mode="voluntary",
            performance_legitimacy_enabled=True, procedural_legitimacy_enabled=True,
        )
        sim = Simulation(config)
        sim.run()
        s_series, z_series = sz_obs.s_obs_z_obs_series(sim.event_log, config.n_steps)
        assert np.all(s_series >= 0.0) and np.all(s_series <= 1.0)
        assert np.all(z_series >= 0.0) and np.all(z_series <= 1.0)

    def test_no_config_flag_required_module_is_pure_observation(self):
        # A frozen-reference run has no Level 1.3-specific mechanism
        # active, but Work Package B's response dimensions this module
        # reuses are built from ordinary Level 1.0/1.1/1.2 event types
        # (delegation, monitoring, accountability, ...) which DO occur
        # here -- this test's point is only that the call succeeds
        # without reading any config flag, not that the series are zero.
        # The two legitimacy components specifically ARE guaranteed
        # zero, since LegitimacyEvent is a Level 1.3 Work Package D
        # event type that cannot be logged on a frozen-reference run.
        config = SimulationConfig.level12b_frozen_reference(population_size=20, n_steps=60, seed=5)
        sim = Simulation(config)
        sim.run()
        assert sim.event_log.legitimacy_events == []
        s_series, z_series = sz_obs.s_obs_z_obs_series(sim.event_log, config.n_steps)  # must not raise
        assert np.all(sz_obs.performance_legitimacy_series(sim.event_log, config.n_steps) == 0.0)
        assert np.all(sz_obs.procedural_legitimacy_series(sim.event_log, config.n_steps) == 0.0)
        assert np.all(s_series >= 0.0) and np.all(s_series <= 1.0)
        assert np.all(z_series >= 0.0) and np.all(z_series <= 1.0)
