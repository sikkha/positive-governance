"""Level 1.1b, Work Package G: functional shock recovery.

Level 1.1 reported a 10/10 reappointment rate after recall and called
this "recovery." This module tests
`experiments/level11b_functional_shock_recovery.py`'s pure
`_analyze_shocks(event_log)` function directly on small synthetic
`EventLog`s, verifying reappointment and functional-recovery are
computed as genuinely distinct quantities that can diverge, plus a
small-scale full-simulation smoke test."""

from __future__ import annotations

import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import (
    DelegateAppointmentEvent,
    DelegateRemovalEvent,
    EventLog,
    TaskPerformanceEvent,
)
from experiments.level11b_functional_shock_recovery import (
    RECOVERY_WINDOW_STEPS,
    _analyze_shocks,
    _summarize_run,
)


def _removal(delegate_id, rule_id, step, final_capacity, reason="recalled"):
    return DelegateRemovalEvent(
        step=step, patch_id=0, rule_id=rule_id, rule_lineage_id=rule_id, delegate_id=delegate_id,
        agent=delegate_id, reason=reason, tenure_steps=step, final_capacity=final_capacity,
        appropriated_total=0.0,
    )


def _appointment(delegate_id, rule_id, step, predecessor_delegate_id=None):
    return DelegateAppointmentEvent(
        step=step, patch_id=0, rule_id=rule_id, rule_lineage_id=rule_id, delegate_id=delegate_id,
        agent=delegate_id, tasks=("resource_accounting",), appointment_method="lottery",
        candidate_set=(delegate_id,), selector_population=(delegate_id,), support_fraction=1.0,
        predecessor_delegate_id=predecessor_delegate_id,
    )


def _task_event(delegate_id, rule_id, step, capacity_before, outcome="success"):
    return TaskPerformanceEvent(
        step=step, patch_id=0, rule_id=rule_id, delegate_id=delegate_id, agent=delegate_id,
        task="resource_accounting", outcome=outcome, capacity_before=capacity_before, cost=0.0,
    )


class TestReappointmentVsFunctionalRecoveryAreDistinctQuantities:
    def test_reappointed_but_not_recovered_is_the_central_case_this_work_package_exists_to_catch(self):
        """The synthetic case Level 1.1's "10/10 reappointment = recovery"
        framing would have missed: a successor IS appointed promptly, but
        its own realized capacity never gets close to the departed
        delegate's -- reappointment_rate=1.0, full_recovery_rate=0.0."""
        log = EventLog()
        log.add(_removal(delegate_id=0, rule_id=0, step=10, final_capacity=0.8))
        log.add(_appointment(delegate_id=1, rule_id=0, step=12, predecessor_delegate_id=0))
        log.add(_task_event(delegate_id=1, rule_id=0, step=15, capacity_before=0.1))
        log.add(_task_event(delegate_id=1, rule_id=0, step=20, capacity_before=0.15))

        result = _analyze_shocks(log)
        assert result["n_shocks"] == 1
        assert result["reappointment_rate"] == pytest.approx(1.0)
        # last capacity_before within window is 0.15; pre-shock was 0.8.
        assert result["mean_recovery_gap"] == pytest.approx(0.15 - 0.8)
        assert result["full_recovery_rate_among_reappointed_with_defined_gap"] == pytest.approx(0.0)
        assert result["within_tolerance_recovery_rate_among_reappointed_with_defined_gap"] == pytest.approx(0.0)

    def test_reappointed_and_fully_recovered_scores_positively_on_both(self):
        log = EventLog()
        log.add(_removal(delegate_id=0, rule_id=0, step=10, final_capacity=0.3))
        log.add(_appointment(delegate_id=1, rule_id=0, step=12, predecessor_delegate_id=0))
        log.add(_task_event(delegate_id=1, rule_id=0, step=40, capacity_before=0.5))

        result = _analyze_shocks(log)
        assert result["mean_recovery_gap"] == pytest.approx(0.5 - 0.3)
        assert result["full_recovery_rate_among_reappointed_with_defined_gap"] == pytest.approx(1.0)
        assert result["within_tolerance_recovery_rate_among_reappointed_with_defined_gap"] == pytest.approx(1.0)

    def test_never_reappointed_within_window_scores_zero_reappointment_and_no_recovery_data(self):
        log = EventLog()
        log.add(_removal(delegate_id=0, rule_id=0, step=10, final_capacity=0.5))
        # Appointment happens, but far outside the reappointment window.
        log.add(_appointment(delegate_id=1, rule_id=0, step=10 + RECOVERY_WINDOW_STEPS + 100, predecessor_delegate_id=0))

        result = _analyze_shocks(log)
        assert result["n_shocks"] == 1
        assert result["n_reappointed"] == 0
        assert result["reappointment_rate"] == pytest.approx(0.0)
        # No reappointment -> no recovery_gap datapoint at all (never
        # coerced to a False/0.0 "not recovered" verdict for a shock
        # that was never even reappointed).
        assert result["n_recovery_gap_defined"] == 0
        assert result["mean_recovery_gap"] is None
        assert result["full_recovery_rate_among_reappointed_with_defined_gap"] is None

    def test_reappointed_but_successor_never_performs_a_task_leaves_gap_undefined_not_zero(self):
        log = EventLog()
        log.add(_removal(delegate_id=0, rule_id=0, step=10, final_capacity=0.5))
        log.add(_appointment(delegate_id=1, rule_id=0, step=12, predecessor_delegate_id=0))
        # No TaskPerformanceEvent ever recorded for delegate_id=1.

        result = _analyze_shocks(log)
        assert result["n_reappointed"] == 1
        assert result["n_gap_undefined_among_reappointed"] == 1
        assert result["n_recovery_gap_defined"] == 0
        assert result["mean_recovery_gap"] is None

    def test_no_shocks_at_all_returns_none_for_every_rate_never_zero(self):
        log = EventLog()
        result = _analyze_shocks(log)
        assert result["n_shocks"] == 0
        assert result["reappointment_rate"] is None
        assert result["mean_recovery_gap"] is None
        assert result["mean_pre_shock_completion_rate"] is None

    def test_non_recall_removal_reasons_are_excluded_from_shock_analysis(self):
        """Only recall-triggered removals are 'shocks' for this work
        package -- a routine rule dissolution is a different event
        entirely and must not be miscounted as an accountability
        shock."""
        log = EventLog()
        log.add(_removal(delegate_id=0, rule_id=0, step=10, final_capacity=0.5, reason="rule_dissolved"))
        log.add(_appointment(delegate_id=1, rule_id=0, step=12, predecessor_delegate_id=0))
        log.add(_task_event(delegate_id=1, rule_id=0, step=15, capacity_before=0.5))

        result = _analyze_shocks(log)
        assert result["n_shocks"] == 0

    def test_completion_rate_dimension_computed_independently_of_capacity_gap(self):
        """Regression guard for the mechanistic finding this work
        package's confirmatory sweep surfaced: completion rate can
        recover fully while capacity's recovery_gap stays negative,
        because capacity's experience_term resets to 0 for every new
        delegate regardless of predecessor quality -- the two
        dimensions must be tracked as genuinely separate numbers, not
        collapsed into one "recovered" bit."""
        log = EventLog()
        log.add(_removal(delegate_id=0, rule_id=0, step=10, final_capacity=0.9))
        log.add(_task_event(delegate_id=0, rule_id=0, step=5, capacity_before=0.85, outcome="success"))
        log.add(_task_event(delegate_id=0, rule_id=0, step=8, capacity_before=0.9, outcome="success"))
        log.add(_appointment(delegate_id=1, rule_id=0, step=12, predecessor_delegate_id=0))
        log.add(_task_event(delegate_id=1, rule_id=0, step=15, capacity_before=0.05, outcome="success"))
        log.add(_task_event(delegate_id=1, rule_id=0, step=20, capacity_before=0.08, outcome="success"))

        result = _analyze_shocks(log)
        assert result["mean_pre_shock_completion_rate"] == pytest.approx(1.0)
        assert result["mean_post_shock_completion_rate"] == pytest.approx(1.0)
        assert result["mean_recovery_gap"] < -0.5  # capacity did NOT recover despite perfect completion


class TestSweepScriptSmoke:
    def test_summarize_run_returns_well_formed_dict_at_small_scale(self):
        cfg = SimulationConfig.level11b_substreams(population_size=20, n_patches=2, n_steps=150, seed=0)
        result = _summarize_run(cfg)
        assert set(result.keys()) >= {
            "n_shocks", "n_reappointed", "reappointment_rate", "mean_recovery_gap",
            "full_recovery_rate_among_reappointed_with_defined_gap",
        }
        if result["reappointment_rate"] is not None:
            assert 0.0 <= result["reappointment_rate"] <= 1.0
