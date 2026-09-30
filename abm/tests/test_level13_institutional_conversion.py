"""Level 1.3, Work Package F (Section 11): institutional conversion
detection (``observer/institutional_conversion.py``).

See that module's own docstring for the context-loss disclosure and the
interpretive choice ("conversion" = persistent form, shifted dominant
function) this work package's tests are built on."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import (
    AuditEvent,
    ContributionEvent,
    DelegateAppointmentEvent,
    EventLog,
    MonitoringEvent,
    RuleAdoptionEvent,
    RuleDissolutionEvent,
    SanctionEvent,
)
from abm_governance.observer import institutional_conversion as ic
from abm_governance.simulation import Simulation


def _rule_adoption(step, rule_id, rule_lineage_id=None, patch_id=0, proposer=0):
    return RuleAdoptionEvent(
        step=step, patch_id=patch_id, rule_id=rule_id, rule_lineage_id=rule_lineage_id or rule_id, proposer=proposer,
        n_eligible=3, n_supporters=3, support_fraction=1.0, adoption_threshold=0.5, adoption_process="voluntary",
    )


def _rule_dissolution(step, rule_id, rule_lineage_id=None, patch_id=0):
    return RuleDissolutionEvent(
        step=step, patch_id=patch_id, rule_id=rule_id, rule_lineage_id=rule_lineage_id or rule_id,
        reason="support_below_floor", age_at_dissolution=step, founder_present_at_dissolution=True,
    )


def _delegate_appoint(step, rule_id, patch_id=0, delegate_id=1, agent=1):
    return DelegateAppointmentEvent(
        step=step, patch_id=patch_id, rule_id=rule_id, rule_lineage_id=rule_id, delegate_id=delegate_id,
        agent=agent, tasks=("monitoring",), appointment_method="lottery", candidate_set=(agent,),
        selector_population=(0, 1, 2), support_fraction=1.0, predecessor_delegate_id=None,
        institutional_memory_inherited=0.0,
    )


def _contribution(step, rule_id, patch_id=0, agent=0):
    return ContributionEvent(
        step=step, patch_id=patch_id, rule_id=rule_id, agent=agent, mode="voluntary",
        amount_asked=1.0, amount_paid=1.0, complied=True, fund_after=1.0,
    )


def _sanction(step, rule_id, patch_id=0, target=2):
    return SanctionEvent(
        step=step, patch_id=patch_id, rule_id=rule_id, target=target, magnitude=0.5, cost=0.1,
        funded_by="bystander", false_sanction=False, sanctioner=1,
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


def _log_with(events_by_field: dict) -> EventLog:
    log = EventLog()
    for field, events in events_by_field.items():
        getattr(log, field).extend(events)
    return log


class TestIntervalCounts:
    def test_single_open_interval(self):
        out = ic._interval_counts([2], [None], n_steps=5)
        assert list(out) == [0.0, 0.0, 1.0, 1.0, 1.0]

    def test_closed_interval_inclusive_end(self):
        out = ic._interval_counts([1], [3], n_steps=5)
        assert list(out) == [0.0, 1.0, 1.0, 1.0, 0.0]


class TestSafeDivide:
    def test_zero_denominator_is_zero_not_nan(self):
        out = ic._safe_divide(np.array([1.0, 0.0]), np.array([0.0, 0.0]))
        assert list(out) == [0.0, 0.0]

    def test_normal_division(self):
        out = ic._safe_divide(np.array([1.0, 3.0]), np.array([2.0, 6.0]))
        assert list(out) == [0.5, 0.5]


class TestRuleLifetimes:
    def test_open_and_closed_lifetimes(self):
        log = _log_with({
            "rule_adoptions": [_rule_adoption(0, rule_id=10), _rule_adoption(5, rule_id=20)],
            "rule_dissolutions": [_rule_dissolution(15, rule_id=20)],
        })
        lifetimes = ic._rule_lifetimes(log, None)
        assert lifetimes[10] == [0, 0, None]
        assert lifetimes[20] == [5, 0, 15]

    def test_patch_scoping(self):
        log = _log_with({"rule_adoptions": [_rule_adoption(0, rule_id=10, patch_id=0), _rule_adoption(0, rule_id=11, patch_id=1)]})
        lifetimes = ic._rule_lifetimes(log, frozenset({0}))
        assert 10 in lifetimes
        assert 11 not in lifetimes


class TestDominantFamilySeries:
    def test_none_below_min_activity(self):
        touches = [(0, "monitoring"), (1, "monitoring")]
        series = ic._dominant_family_series(touches, lo=0, hi=5, window_steps=10, min_window_activity=3)
        assert series == [None, None, None, None, None]

    def test_becomes_dominant_once_activity_threshold_met(self):
        touches = [(0, "monitoring"), (1, "monitoring"), (2, "monitoring")]
        series = ic._dominant_family_series(touches, lo=0, hi=3, window_steps=10, min_window_activity=3)
        assert series == [None, None, "monitoring"]

    def test_window_slides_and_drops_old_touches(self):
        # 3 "monitoring" touches early, then 3 "contribution" touches
        # once the window has fully slid past the monitoring ones.
        touches = [(0, "monitoring"), (1, "monitoring"), (2, "monitoring"),
                   (10, "contribution"), (11, "contribution"), (12, "contribution")]
        series = ic._dominant_family_series(touches, lo=0, hi=13, window_steps=3, min_window_activity=3)
        assert series[2] == "monitoring"
        assert series[5] is None  # window has slid off the monitoring cluster, nothing new yet
        assert series[12] == "contribution"


class TestDetectConversions:
    def test_no_conversion_when_function_never_shifts(self):
        log = _log_with({
            "rule_adoptions": [_rule_adoption(0, rule_id=1)],
            "monitorings": [_monitoring(t, rule_id=1) for t in range(0, 100, 2)],
        })
        records = ic.detect_conversions(log, n_steps=100, window_steps=20, min_window_activity=2, min_persistence_steps=10)
        assert records == []

    def test_conversion_detected_after_sustained_shift(self):
        # Founding function: monitoring, steps 0-29. Then a sustained
        # shift to contribution from step 40 onward -- long enough
        # (60 steps) to clear a 20-step persistence requirement well
        # inside the window.
        events = [_monitoring(t, rule_id=1) for t in range(0, 30, 2)]
        events += [_contribution(t, rule_id=1) for t in range(40, 100, 2)]
        log = _log_with({"rule_adoptions": [_rule_adoption(0, rule_id=1)], "monitorings": events[:15], "contributions": events[15:]})
        records = ic.detect_conversions(log, n_steps=100, window_steps=20, min_window_activity=2, min_persistence_steps=10)
        assert len(records) == 1
        rec = records[0]
        assert rec.rule_id == 1
        assert rec.founding_family == "monitoring"
        assert rec.converted_family == "contribution"
        assert rec.adopt_step == 0

    def test_never_reaching_founding_activity_yields_no_record(self):
        log = _log_with({
            "rule_adoptions": [_rule_adoption(0, rule_id=1)],
            "monitorings": [_monitoring(5, rule_id=1)],  # single touch, never crosses min_window_activity
        })
        records = ic.detect_conversions(log, n_steps=50, window_steps=20, min_window_activity=3, min_persistence_steps=5)
        assert records == []

    def test_dissolved_rule_cannot_convert_after_dissolution(self):
        # Monitoring dominant until dissolution at step 30; any activity
        # logged after that (should not happen in a real run, but the
        # function must still respect the lifetime window) is outside
        # scope because hi is capped at dissolve_step + 1.
        events_before = [_monitoring(t, rule_id=1) for t in range(0, 30, 2)]
        log = _log_with({
            "rule_adoptions": [_rule_adoption(0, rule_id=1)],
            "rule_dissolutions": [_rule_dissolution(30, rule_id=1)],
            "monitorings": events_before,
        })
        records = ic.detect_conversions(log, n_steps=50, window_steps=20, min_window_activity=2, min_persistence_steps=5)
        assert records == []

    def test_at_most_one_conversion_per_rule(self):
        # monitoring -> contribution -> back to monitoring: only the
        # FIRST sustained shift is recorded.
        events = [_monitoring(t, rule_id=1) for t in range(0, 20, 2)]
        events += [_contribution(t, rule_id=1) for t in range(30, 60, 2)]
        events += [_monitoring(t, rule_id=1) for t in range(70, 100, 2)]
        log = _log_with({
            "rule_adoptions": [_rule_adoption(0, rule_id=1)],
            "monitorings": [e for e in events if e.rule_id == 1][:10] + [e for e in events if e.rule_id == 1][20:],
            "contributions": [e for e in events if e.rule_id == 1][10:20],
        })
        records = ic.detect_conversions(log, n_steps=100, window_steps=20, min_window_activity=2, min_persistence_steps=10)
        assert len(records) == 1
        assert records[0].converted_family == "contribution"

    def test_multiple_rules_sorted_by_detected_step(self):
        rule_a_events = [_monitoring(t, rule_id=1) for t in range(0, 20, 2)] + [_contribution(t, rule_id=1) for t in range(60, 100, 2)]
        rule_b_events = [_sanction(t, rule_id=2) for t in range(0, 20, 2)] + [_audit(t, rule_id=2) for t in range(30, 100, 2)]
        log = _log_with({
            "rule_adoptions": [_rule_adoption(0, rule_id=1), _rule_adoption(0, rule_id=2)],
            "monitorings": [e for e in rule_a_events if isinstance(e, MonitoringEvent)],
            "contributions": [e for e in rule_a_events if isinstance(e, ContributionEvent)],
            "sanctions": [e for e in rule_b_events if isinstance(e, SanctionEvent)],
            "audits": [e for e in rule_b_events if isinstance(e, AuditEvent)],
        })
        records = ic.detect_conversions(log, n_steps=100, window_steps=20, min_window_activity=2, min_persistence_steps=10)
        assert [r.rule_id for r in records] == [2, 1]  # rule 2 converts earlier (step 30 vs 60)


class TestConversionIncidenceSeries:
    def test_zero_when_no_conversions(self):
        log = _log_with({
            "rule_adoptions": [_rule_adoption(0, rule_id=1)],
            "monitorings": [_monitoring(t, rule_id=1) for t in range(0, 50, 2)],
        })
        series = ic.conversion_incidence_series(log, n_steps=50, window_steps=20, min_window_activity=2, min_persistence_steps=10)
        assert np.all(series == 0.0)

    def test_rises_to_full_incidence_after_conversion(self):
        events = [_monitoring(t, rule_id=1) for t in range(0, 20, 2)]
        events += [_contribution(t, rule_id=1) for t in range(40, 100, 2)]
        log = _log_with({
            "rule_adoptions": [_rule_adoption(0, rule_id=1)],
            "monitorings": [e for e in events if isinstance(e, MonitoringEvent)],
            "contributions": [e for e in events if isinstance(e, ContributionEvent)],
        })
        series = ic.conversion_incidence_series(log, n_steps=100, window_steps=20, min_window_activity=2, min_persistence_steps=10)
        assert series[10] == 0.0  # before conversion, the one active rule is unconverted.
        assert series[99] == 1.0  # after conversion, the one active rule counts as converted.

    def test_returns_fraction_bounded_in_unit_interval(self):
        log = _log_with({
            "rule_adoptions": [_rule_adoption(0, rule_id=1), _rule_adoption(0, rule_id=2)],
            "monitorings": [_monitoring(t, rule_id=1) for t in range(0, 50, 2)],
            "sanctions": [_sanction(t, rule_id=2) for t in range(0, 50, 2)],
        })
        series = ic.conversion_incidence_series(log, n_steps=50)
        assert np.all(series >= 0.0)
        assert np.all(series <= 1.0)


class TestEndToEndOnARealRun:
    def test_runs_without_error_and_produces_bounded_series(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=40, n_steps=200, n_patches=3, seed=7,
            monitoring_mode="voluntary", sanction_mode="voluntary",
        )
        sim = Simulation(config)
        sim.run()
        records = ic.detect_conversions(sim.event_log, config.n_steps)
        for rec in records:
            assert 0 <= rec.detected_step < config.n_steps
            assert rec.founding_family in ic.FUNCTION_FAMILIES
            assert rec.converted_family in ic.FUNCTION_FAMILIES
            assert rec.founding_family != rec.converted_family
        series = ic.conversion_incidence_series(sim.event_log, config.n_steps)
        assert len(series) == config.n_steps
        assert np.all(series >= 0.0)
        assert np.all(series <= 1.0)

    def test_no_config_flag_required_module_is_pure_observation(self):
        # Section 11's own footprint claim: this module reads no config
        # flag at all -- it is applicable to ANY completed run's event
        # log, disabled or not, gated or not.
        config = SimulationConfig.level12b_frozen_reference(population_size=20, n_steps=60, seed=3)
        sim = Simulation(config)
        sim.run()
        records = ic.detect_conversions(sim.event_log, config.n_steps)  # must not raise
        assert isinstance(records, list)
