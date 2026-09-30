"""Level 1.3, Work Package B (Section 7): endogenous sequencing
measurement (``observer/sequencing_diagnostics.py``)."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import (
    AppealEvent,
    AuditEvent,
    ContributionEvent,
    CoordinationDissolutionEvent,
    CoordinationLinkEvent,
    CoordinationProposalEvent,
    DelegateAppointmentEvent,
    DelegateRemovalEvent,
    EventLog,
    MonitoringEvent,
    RecallEvent,
    RuleAdoptionEvent,
    RuleDissolutionEvent,
    RuleProposalEvent,
    SanctionEvent,
)
from abm_governance.core.historical_pressure import first_sustained_crossing
from abm_governance.observer import sequencing_diagnostics as sd
from abm_governance.simulation import Simulation


def _rule_adoption(step, rule_id, rule_lineage_id, patch_id=0, proposer=0):
    return RuleAdoptionEvent(
        step=step, patch_id=patch_id, rule_id=rule_id, rule_lineage_id=rule_lineage_id, proposer=proposer,
        n_eligible=3, n_supporters=3, support_fraction=1.0, adoption_threshold=0.5, adoption_process="voluntary",
    )


def _rule_dissolution(step, rule_id, rule_lineage_id, patch_id=0):
    return RuleDissolutionEvent(
        step=step, patch_id=patch_id, rule_id=rule_id, rule_lineage_id=rule_lineage_id,
        reason="support_below_floor", age_at_dissolution=step, founder_present_at_dissolution=True,
    )


def _rule_proposal(step, rule_lineage_id, patch_id=0, proposer=0, origin="proposal", parent_rule_lineage_id=None):
    return RuleProposalEvent(
        step=step, patch_id=patch_id, proposer=proposer, rule_lineage_id=rule_lineage_id,
        extraction_ceiling=0.5, maintenance_requirement=0.5, monitoring_intensity=0.5, sanction_magnitude=0.5,
        adoption_threshold=0.5, amendment_threshold=0.5, origin=origin, parent_rule_lineage_id=parent_rule_lineage_id,
    )


def _delegate_appoint(step, delegate_id, rule_id, patch_id=0, agent=1):
    return DelegateAppointmentEvent(
        step=step, patch_id=patch_id, rule_id=rule_id, rule_lineage_id=rule_id, delegate_id=delegate_id,
        agent=agent, tasks=("monitoring",), appointment_method="lottery", candidate_set=(agent,),
        selector_population=(0, 1, 2), support_fraction=1.0, predecessor_delegate_id=None,
        institutional_memory_inherited=0.0,
    )


def _delegate_remove(step, delegate_id, rule_id, patch_id=0, agent=1):
    return DelegateRemovalEvent(
        step=step, patch_id=patch_id, rule_id=rule_id, rule_lineage_id=rule_id, delegate_id=delegate_id,
        agent=agent, reason="recalled", tenure_steps=step, final_capacity=0.5, appropriated_total=0.0,
    )


class TestIntervalCounts:
    def test_single_open_interval_counts_from_start_to_end_of_run(self):
        out = sd._interval_counts([2], [None], n_steps=5)
        assert list(out) == [0.0, 0.0, 1.0, 1.0, 1.0]

    def test_closed_interval_includes_the_end_step(self):
        # Inclusive-end convention -- see _interval_counts's own
        # docstring for why (a same-step removal/dissolution/
        # dissolution-consequence event must still see its entity as
        # "active" for that step).
        out = sd._interval_counts([1], [3], n_steps=5)
        assert list(out) == [0.0, 1.0, 1.0, 1.0, 0.0]

    def test_overlapping_intervals_stack(self):
        out = sd._interval_counts([0, 1], [None, None], n_steps=3)
        assert list(out) == [1.0, 2.0, 2.0]

    def test_single_step_interval_counts_exactly_one_step(self):
        out = sd._interval_counts([2], [2], n_steps=5)
        assert list(out) == [0.0, 0.0, 1.0, 0.0, 0.0]

    def test_end_before_start_is_dropped(self):
        out = sd._interval_counts([3], [1], n_steps=5)
        assert list(out) == [0.0, 0.0, 0.0, 0.0, 0.0]


class TestSafeDivide:
    def test_divides_elementwise(self):
        out = sd._safe_divide(np.array([1.0, 2.0]), np.array([2.0, 4.0]))
        assert list(out) == pytest.approx([0.5, 0.5])

    def test_zero_denominator_yields_zero_not_nan(self):
        out = sd._safe_divide(np.array([1.0, 0.0]), np.array([0.0, 0.0]))
        assert list(out) == [0.0, 0.0]


class TestDelegationAndAdministrativeFunctionSeries:
    def test_delegation_series_reflects_active_delegate_fraction(self):
        log = EventLog()
        log.add(_rule_adoption(0, rule_id=0, rule_lineage_id=0))
        log.add(_delegate_appoint(2, delegate_id=0, rule_id=0))
        log.add(_delegate_remove(6, delegate_id=0, rule_id=0))
        series = sd.institutional_response_series(log, n_steps=10)
        d = series["delegation"]
        assert d[0] == 0.0  # no delegate yet
        assert d[3] == 1.0  # one rule, one delegate -> full coverage
        assert d[7] == 0.0  # delegate removed


class TestMonitoringSeries:
    def test_monitoring_series_is_fraction_of_active_rules_monitored_this_step(self):
        log = EventLog()
        log.add(_rule_adoption(0, rule_id=0, rule_lineage_id=0))
        log.add(_rule_adoption(0, rule_id=1, rule_lineage_id=1))
        log.add(MonitoringEvent(step=3, patch_id=0, rule_id=0, target=1, true_compliance=True, detected_violation=False, outcome="true_negative"))
        series = sd.institutional_response_series(log, n_steps=6)
        assert series["monitoring"][3] == pytest.approx(0.5)  # 1 of 2 active rules monitored
        assert series["monitoring"][4] == 0.0


class TestAccountabilitySeries:
    def test_accountability_series_counts_distinct_delegates_across_audit_recall_appeal(self):
        log = EventLog()
        log.add(_rule_adoption(0, rule_id=0, rule_lineage_id=0))
        log.add(_delegate_appoint(0, delegate_id=0, rule_id=0))
        log.add(AuditEvent(step=2, patch_id=0, rule_id=0, delegate_id=0, auditor=1, actual_misconduct_occurred=True, found_misconduct=True, outcome="true_positive", cost=0.1))
        log.add(AppealEvent(step=2, patch_id=0, rule_id=0, delegate_id=0, appellant=2, original_sanction_step=1, was_false_sanction=False, upheld=False, refund=0.0, cost=0.1))
        series = sd.institutional_response_series(log, n_steps=5)
        # both events target the SAME delegate at step 2 -- distinct count is 1, not 2.
        assert series["accountability"][2] == pytest.approx(1.0)


class TestBargainingParticipationSeries:
    def test_compliance_rate_computed_correctly(self):
        log = EventLog()
        log.add(ContributionEvent(step=1, patch_id=0, rule_id=0, agent=0, mode="voluntary", amount_asked=1.0, amount_paid=1.0, complied=True, fund_after=1.0))
        log.add(ContributionEvent(step=1, patch_id=0, rule_id=0, agent=1, mode="voluntary", amount_asked=1.0, amount_paid=0.0, complied=False, fund_after=1.0))
        series = sd.institutional_response_series(log, n_steps=3)
        assert series["bargaining_participation"][1] == pytest.approx(0.5)
        assert series["bargaining_participation"][0] == 0.0


class TestInterpatchCoordinationSeries:
    def test_link_presence_normalized_by_half_active_rule_count(self):
        log = EventLog()
        log.add(_rule_adoption(0, rule_id=0, rule_lineage_id=0, patch_id=0))
        log.add(_rule_adoption(0, rule_id=1, rule_lineage_id=1, patch_id=1))
        log.add(CoordinationLinkEvent(step=1, link_id=0, patch_id_a=0, patch_id_b=1, kind="information_exchange", accepted=True))
        series = sd.institutional_response_series(log, n_steps=4)
        # 1 active link, 2 active rules -> max possible links = 1 -> full coverage.
        assert series["interpatch_coordination"][2] == pytest.approx(1.0)

    def test_dissolution_ends_the_interval(self):
        log = EventLog()
        log.add(_rule_adoption(0, rule_id=0, rule_lineage_id=0, patch_id=0))
        log.add(_rule_adoption(0, rule_id=1, rule_lineage_id=1, patch_id=1))
        log.add(CoordinationLinkEvent(step=1, link_id=0, patch_id_a=0, patch_id_b=1, kind="information_exchange", accepted=True))
        log.add(CoordinationDissolutionEvent(step=3, link_id=0, patch_id_a=0, patch_id_b=1, duration_steps=2, reason="voluntary"))
        series = sd.institutional_response_series(log, n_steps=6)
        assert series["interpatch_coordination"][2] == pytest.approx(1.0)
        assert series["interpatch_coordination"][4] == 0.0


class TestGeneralizedRuleSeries:
    def test_generality_rises_as_function_families_are_exercised(self):
        log = EventLog()
        log.add(_rule_adoption(0, rule_id=0, rule_lineage_id=0))
        log.add(_delegate_appoint(1, delegate_id=0, rule_id=0))
        log.add(MonitoringEvent(step=2, patch_id=0, rule_id=0, target=1, true_compliance=True, detected_violation=False, outcome="true_negative"))
        series = sd.institutional_response_series(log, n_steps=5)
        g = series["generalized_rule"]
        assert g[0] == pytest.approx(0.0)   # only "founded" -- no family touched yet
        assert g[1] == pytest.approx(1 / 6)  # delegation touched
        assert g[2] == pytest.approx(2 / 6)  # + monitoring touched
        assert g[4] == pytest.approx(2 / 6)  # stays -- nothing new touched

    def test_no_active_rules_gives_zero_not_nan(self):
        log = EventLog()
        series = sd.institutional_response_series(log, n_steps=3)
        assert list(series["generalized_rule"]) == [0.0, 0.0, 0.0]


class TestCrossFounderReconstructionSeries:
    def test_same_founder_reconstruction_is_not_counted(self):
        log = EventLog()
        log.add(_rule_adoption(0, rule_id=0, rule_lineage_id=0, proposer=5))
        log.add(_rule_dissolution(10, rule_id=0, rule_lineage_id=0))
        log.add(_rule_proposal(11, rule_lineage_id=1, proposer=5, origin="mutation", parent_rule_lineage_id=0))
        log.add(_rule_adoption(12, rule_id=1, rule_lineage_id=1, proposer=5))
        series = sd.institutional_response_series(log, n_steps=20)
        assert np.all(series["cross_founder_reconstruction"] == 0.0)

    def test_different_founder_reconstruction_is_counted_and_ends_at_its_own_dissolution(self):
        log = EventLog()
        log.add(_rule_adoption(0, rule_id=0, rule_lineage_id=0, proposer=5))
        log.add(_rule_dissolution(10, rule_id=0, rule_lineage_id=0))
        log.add(_rule_proposal(11, rule_lineage_id=1, proposer=7, origin="mutation", parent_rule_lineage_id=0))
        log.add(_rule_adoption(12, rule_id=1, rule_lineage_id=1, proposer=7))
        log.add(_rule_dissolution(18, rule_id=1, rule_lineage_id=1))
        series = sd.institutional_response_series(log, n_steps=20)
        cf = series["cross_founder_reconstruction"]
        assert cf[11] == 0.0
        assert cf[13] == 1.0
        assert cf[19] == 0.0  # dissolved at 18

    def test_fresh_proposal_origin_is_never_counted(self):
        log = EventLog()
        log.add(_rule_proposal(0, rule_lineage_id=0, proposer=5, origin="proposal"))
        log.add(_rule_adoption(1, rule_id=0, rule_lineage_id=0, proposer=5))
        series = sd.institutional_response_series(log, n_steps=5)
        assert np.all(series["cross_founder_reconstruction"] == 0.0)


class TestSequencingVectorAndOrder:
    def test_vector_matches_first_sustained_crossing_directly(self):
        series = {"delegation": np.array([0.0, 1.0, 1.0, 1.0, 0.0])}
        vector = sd.sequencing_vector(series, min_duration_steps=3, thresholds={"delegation": 1.0})
        assert vector["delegation"] == first_sustained_crossing(series["delegation"], 1.0, 3)
        # every other dimension is absent from `series` -> None.
        for name in sd.INSTITUTIONAL_RESPONSE_DIMENSIONS:
            if name != "delegation":
                assert vector[name] is None

    def test_order_sorts_by_first_sustained_step_never_activated_last(self):
        vector = {
            "delegation": 5, "administrative_function": 2, "generalized_rule": None,
            "monitoring": 2, "accountability": None, "bargaining_participation": 10,
            "cross_founder_reconstruction": None, "interpatch_coordination": 5,
        }
        order = sd.sequencing_order(vector)
        # administrative_function and monitoring tie at 2 -> alphabetical.
        assert order[0] == "administrative_function"
        assert order[1] == "monitoring"
        # delegation and interpatch_coordination tie at 5 -> alphabetical.
        assert order.index("delegation") < order.index("interpatch_coordination")
        assert order[-1] in ("accountability", "cross_founder_reconstruction", "generalized_rule")
        never_activated = {"accountability", "cross_founder_reconstruction", "generalized_rule"}
        assert set(order[-3:]) == never_activated

    def test_order_is_a_permutation_of_all_dimension_names(self):
        vector = {name: None for name in sd.INSTITUTIONAL_RESPONSE_DIMENSIONS}
        order = sd.sequencing_order(vector)
        assert set(order) == set(sd.INSTITUTIONAL_RESPONSE_DIMENSIONS)
        assert len(order) == len(sd.INSTITUTIONAL_RESPONSE_DIMENSIONS)


class TestEndToEndOnARealRun:
    def test_runs_without_error_and_produces_well_formed_series(self):
        config = SimulationConfig.level11_complete(
            population_size=40, n_steps=150, n_patches=3, seed=17,
            monitoring_mode="voluntary", sanction_mode="voluntary",
            contribution_mode="voluntary", contribution_period_steps=5,
        )
        sim = Simulation(config)
        sim.run()
        series = sd.institutional_response_series(sim.event_log, config.n_steps)
        assert set(series.keys()) == set(sd.INSTITUTIONAL_RESPONSE_DIMENSIONS)
        for name, s in series.items():
            assert len(s) == config.n_steps
            assert np.all(np.isfinite(s))
            assert np.all(s >= 0.0)
            if name != "cross_founder_reconstruction":
                assert np.all(s <= 1.0 + 1e-9)
        vector = sd.sequencing_vector(series, min_duration_steps=config.activation_sustained_duration_steps)
        order = sd.sequencing_order(vector)
        assert set(order) == set(sd.INSTITUTIONAL_RESPONSE_DIMENSIONS)
        # A 150-step run with delegation+accountability+contributions active
        # should sustain-activate at least SOME dimensions.
        assert any(v is not None for v in vector.values())
