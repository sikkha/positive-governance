"""Level 1.2, Work Package E: differential persistence reporting
(observer-side only — no new generative mechanism)."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import (
    AuditEvent,
    EventLog,
    FundDissolutionEvent,
    MembershipExitEvent,
    MigrationEvent,
)
from abm_governance.observer.differential_persistence import (
    demographic_selection_summary,
    differential_persistence_report,
    ecological_selection_summary,
    institutional_selection_summary,
    organizational_selection_summary,
)
from abm_governance.rules.institution import InstitutionComponents, InstitutionRecord, selection_channel_for_reason
from abm_governance.simulation import Simulation


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


class TestSelectionChannelMapping:
    def test_known_reasons_map_to_neutral_channels(self):
        assert selection_channel_for_reason("membership_below_floor") == "member_loss"
        assert selection_channel_for_reason("fund_depleted") == "administrative_overload"
        assert selection_channel_for_reason("support_below_floor") == "voluntary_dissolution"

    def test_unknown_reason_maps_to_unspecified(self):
        assert selection_channel_for_reason("something_new") == "unspecified"
        assert selection_channel_for_reason(None) == "unspecified"


class TestDemographicSelectionSummary:
    def test_tallies_migration_outcomes_and_exit_reasons(self):
        log = EventLog()
        log.add(MigrationEvent(step=0, agent_id=0, origin_patch_id=0, destination_patch_id=1, expected_resource_gain=0.1, perceived_fairness_origin=0.5, perceived_fairness_destination=0.6, movement_cost=1.0, outcome="succeeded", carried_institutional_knowledge=True))
        log.add(MigrationEvent(step=1, agent_id=1, origin_patch_id=0, destination_patch_id=1, expected_resource_gain=0.1, perceived_fairness_origin=0.5, perceived_fairness_destination=0.6, movement_cost=1.0, outcome="refused_cost", carried_institutional_knowledge=False))
        log.add(MembershipExitEvent(step=2, agent_id=2, rule_id=0, patch_id=0, reason="dissatisfaction"))
        summary = demographic_selection_summary(log)
        assert summary["migration_outcomes"] == {"succeeded": 1, "refused_cost": 1}
        assert summary["n_migrations_succeeded"] == 1
        assert summary["n_membership_exits"] == 1


class TestInstitutionalSelectionSummary:
    def test_splits_by_neutral_channel_and_reports_durations(self):
        registry = {
            0: InstitutionRecord(institution_id=0, lineage_id=0, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components(), extinction_time=10, extinction_reason="membership_below_floor"),
            1: InstitutionRecord(institution_id=1, lineage_id=1, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components(), extinction_time=20, extinction_reason="fund_depleted"),
            2: InstitutionRecord(institution_id=2, lineage_id=2, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components()),  # still surviving
        }
        summary = institutional_selection_summary(registry)
        assert summary["n_extinct"] == 2
        assert summary["n_surviving"] == 1
        assert summary["by_channel"]["member_loss"]["count"] == 1
        assert summary["by_channel"]["member_loss"]["mean_duration"] == pytest.approx(10)
        assert summary["by_channel"]["administrative_overload"]["count"] == 1


class TestOrganizationalSelectionSummary:
    def test_separates_extinct_from_surviving_institutions(self):
        registry = {
            0: InstitutionRecord(institution_id=0, lineage_id=0, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components(), extinction_time=5, extinction_reason="fund_depleted"),
            1: InstitutionRecord(institution_id=1, lineage_id=1, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components()),
        }
        log = EventLog()
        log.add(FundDissolutionEvent(step=5, patch_id=0, rule_id=0, rule_lineage_id=0, amount=0.0, disposition="distributed_to_members"))
        log.add(AuditEvent(step=1, patch_id=0, rule_id=0, delegate_id=0, auditor=1, actual_misconduct_occurred=True, found_misconduct=True, outcome="true_positive", cost=0.1))
        log.add(AuditEvent(step=1, patch_id=1, rule_id=1, delegate_id=1, auditor=2, actual_misconduct_occurred=False, found_misconduct=False, outcome="true_negative", cost=0.1))
        summary = organizational_selection_summary(log, registry)
        assert summary["fund_dissolutions_among_extinct"] == 1
        assert summary["fund_dissolutions_among_surviving"] == 0
        assert summary["realized_misconduct_rate_among_extinct"] == pytest.approx(1.0)
        assert summary["realized_misconduct_rate_among_surviving"] == pytest.approx(0.0)


class TestDifferentialPersistenceReport:
    def test_returns_all_four_channels_separately(self):
        report = differential_persistence_report(EventLog(), {})
        assert set(report.keys()) == {"demographic", "institutional", "ecological", "organizational"}

    def test_never_merges_channels_into_one_score(self):
        report = differential_persistence_report(EventLog(), {})
        for value in report.values():
            assert isinstance(value, dict)
        # No single "score"/"fitness" key anywhere in the report.
        flat_keys = set()
        for v in report.values():
            flat_keys |= set(v.keys())
        assert not any("fitness" in k or k == "score" for k in flat_keys)


class TestSimulationIntegration:
    def test_report_runs_cleanly_after_a_full_simulation(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=20, n_steps=60, n_patches=3, seed=13,
            proposal_probability_mean=0.3, proposal_probability_std=0.02,
            migration_enabled=True, migration_evaluation_period_steps=4,
            membership_exit_enabled=True,
        )
        sim = Simulation(config)
        sim.run()
        report = differential_persistence_report(sim.event_log, sim.institution_registry, sim.patch_system)
        assert set(report.keys()) == {"demographic", "institutional", "ecological", "organizational"}
        assert report["institutional"]["n_extinct"] + report["institutional"]["n_surviving"] == len(sim.institution_registry)
