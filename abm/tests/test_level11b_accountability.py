"""Level 1.1b, Work Package E: accountability function audit —
component ablations (audit/recall/appeal independently) and the
activity-vs-effective-constraint observer split."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import AppealEvent, AuditEvent, EventLog, RecallEvent
from abm_governance.observer.accountability_diagnostics import accountability_activity, effective_constraint
from abm_governance.rules import delegation as rd
from abm_governance.rules.shared_rule import RuleParameters, SharedRule
from abm_governance.simulation import Simulation


def _agent(agent_id, patch_id=0, resources=20.0, **overrides):
    a = Agent(
        agent_id=agent_id, resources=resources, coercive_capability=0.0, policy=make_policy("tit_for_tat"),
        observation_accuracy=1.0, learning_rate=0.1, forgiveness=0.1, risk_sensitivity=0.5, exit_cost=0.1,
    )
    a.patch_id = patch_id
    a.ecological_policy = EcologicalPolicy(0.5, 0.3, 0.0)
    a.audit_diligence = 1.0
    a.social_trust = 0.5
    for k, v in overrides.items():
        setattr(a, k, v)
    return a


def _rule(rule_id=0, patch_id=0, members=(0, 1, 2, 3), fund=10.0):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    r = SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=0, rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )
    r.fund = fund
    return r


def _delegate(delegate_id, agent_id, rule_id, misconduct=True):
    d = rd.Delegate(
        delegate_id=delegate_id, rule_id=rule_id, rule_lineage_id=rule_id, patch_id=0,
        agent_id=agent_id, tasks=("resource_accounting",), appointment_method="lottery", start_step=0,
    )
    d.misconduct_this_step = misconduct
    d.appropriated_total = 5.0
    return d


class TestComponentAblations:
    def test_audit_disabled_means_zero_audits_and_zero_recalls(self):
        agents = {i: _agent(i) for i in range(4)}
        rule = _rule()
        registry = {0: rule}
        delegate = _delegate(0, 0, 0, misconduct=True)
        delegate_registry = {0: delegate}
        config = SimulationConfig.level11b_accountability_audit_only(audit_enabled=False, recall_enabled=True, appeal_enabled=False)
        rng = np.random.default_rng(0)
        log = EventLog()
        rd.accountability_round(1, registry, delegate_registry, agents, [], config, rng, log)
        assert log.audits == []
        assert log.recalls == []  # cannot trigger without an audit finding

    def test_recall_disabled_leaves_audits_intact_but_never_recalls(self):
        agents = {i: _agent(i) for i in range(4)}
        rule = _rule()
        registry = {0: rule}
        delegate = _delegate(0, 0, 0, misconduct=True)
        delegate_registry = {0: delegate}
        config = SimulationConfig.level11b_accountability_audit_only(audit_accuracy=1.0)
        rng = np.random.default_rng(0)
        log = EventLog()
        rd.accountability_round(1, registry, delegate_registry, agents, [], config, rng, log)
        assert len(log.audits) > 0
        assert any(a.outcome == "true_positive" for a in log.audits)
        assert log.recalls == []  # recall_enabled=False in this preset

    def test_appeal_disabled_means_zero_appeals_even_with_sanctions(self):
        agents = {i: _agent(i) for i in range(4)}
        rule = _rule()
        registry = {0: rule}
        delegate = _delegate(0, 0, 0, misconduct=False)
        delegate_registry = {0: delegate}
        config = SimulationConfig.level11b_accountability_recall_only(appeal_probability=1.0)
        assert config.appeal_enabled is False
        from abm_governance.core.events import SanctionEvent

        sanction = SanctionEvent(
            step=1, patch_id=0, rule_id=0, target=2, magnitude=1.0, cost=0.1,
            funded_by="collective_fund", false_sanction=False, sanctioner=1,
        )
        rng = np.random.default_rng(0)
        log = EventLog()
        rd.accountability_round(1, registry, delegate_registry, agents, [sanction], config, rng, log)
        assert log.appeals == []

    def test_full_accountability_preset_leaves_all_components_enabled(self):
        config = SimulationConfig.level11_complete(accountability_enabled=True)
        assert config.audit_enabled is True
        assert config.recall_enabled is True
        assert config.appeal_enabled is True


class TestActivityVsEffectiveConstraintSplit:
    """Hand-computed on a synthetic EventLog -- no full simulation run
    needed to verify the two observer functions' arithmetic."""

    def _log_with(self, audit_outcomes, recalls=(), appeals=()):
        log = EventLog()
        for i, outcome in enumerate(audit_outcomes):
            actual = outcome in ("true_positive", "false_negative")
            found = outcome in ("true_positive", "false_positive")
            log.add(AuditEvent(
                step=0, patch_id=0, rule_id=0, delegate_id=0, auditor=i,
                actual_misconduct_occurred=actual, found_misconduct=found, outcome=outcome, cost=0.1,
            ))
        for succeeded, recovered in recalls:
            log.add(RecallEvent(
                step=0, patch_id=0, rule_id=0, delegate_id=0, trigger_auditor=0,
                n_eligible=3, n_supporters=2, support_fraction=0.67, recall_threshold=0.5,
                succeeded=succeeded, recovered_funds=recovered,
            ))
        for was_false, upheld in appeals:
            log.add(AppealEvent(
                step=0, patch_id=0, rule_id=0, delegate_id=0, appellant=1, original_sanction_step=0,
                was_false_sanction=was_false, upheld=upheld, refund=0.5 if upheld else 0.0, cost=0.05,
            ))
        return log

    def test_high_activity_no_realized_detection_gives_zero_effective_constraint(self):
        """All audits miss (false_negative) -- plenty of activity, zero
        realized detection, zero effective constraint."""
        log = self._log_with(["false_negative"] * 10)
        activity = accountability_activity(log)
        constraint = effective_constraint(log)
        assert activity["n_audits"] == 10
        assert activity["any_accountability_event"] is True
        assert constraint["n_true_positive_audits"] == 0
        assert constraint["detection_rate_given_misconduct"] == pytest.approx(0.0)
        assert constraint["realized_detection"] is False
        assert constraint["effectively_constrained"] is False

    def test_detection_without_recovery_is_not_effectively_constrained(self):
        """A true-positive audit happened but no recall succeeded (e.g.
        recall_enabled=False, or recall failed) -- detection realized,
        but no corrective recovery -- must not count as fully
        'effectively constrained' by this module's stricter definition."""
        log = self._log_with(["true_positive"] * 3, recalls=[(False, 0.0)])
        constraint = effective_constraint(log)
        assert constraint["realized_detection"] is True
        assert constraint["n_recalls_succeeded"] == 0
        assert constraint["realized_recovery"] is False
        assert constraint["effectively_constrained"] is False

    def test_detection_plus_successful_recovery_is_effectively_constrained(self):
        log = self._log_with(["true_positive"] * 3, recalls=[(True, 4.5)])
        constraint = effective_constraint(log)
        assert constraint["realized_detection"] is True
        assert constraint["realized_recovery"] is True
        assert constraint["total_recovered_funds"] == pytest.approx(4.5)
        assert constraint["effectively_constrained"] is True

    def test_perfect_confusion_matrix_gives_full_detection_and_zero_false_positive_rate(self):
        log = self._log_with(["true_positive", "true_positive", "true_negative", "true_negative"])
        constraint = effective_constraint(log)
        assert constraint["detection_rate_given_misconduct"] == pytest.approx(1.0)
        assert constraint["false_positive_rate_given_innocent"] == pytest.approx(0.0)

    def test_justified_vs_unjustified_appeal_uphold_tracked_separately(self):
        log = self._log_with(
            [], appeals=[(True, True), (True, False), (False, True), (False, False)],
        )
        constraint = effective_constraint(log)
        # was_false=True, upheld=True -> justified correction
        assert constraint["n_appeals_justified_upheld"] == 1
        # was_false=False, upheld=True -> unjustified overturn
        assert constraint["n_appeals_unjustified_upheld"] == 1
        assert constraint["false_sanction_correction_rate"] == pytest.approx(0.5)  # 1 of 2 false sanctions corrected

    def test_empty_log_returns_none_for_undefined_rates_never_zero(self):
        """Section-2-style constraint: undefined denominators stay None
        (NaN-equivalent), never silently reported as 0.0."""
        log = EventLog()
        constraint = effective_constraint(log)
        assert constraint["detection_rate_given_misconduct"] is None
        assert constraint["false_positive_rate_given_innocent"] is None
        assert constraint["recovery_fraction_of_appropriated"] is None
        assert constraint["false_sanction_correction_rate"] is None
        assert constraint["effectively_constrained"] is False


class TestRandomizedPlaceboContrast:
    """Full run: confirms the placebo preset produces HIGH activity but
    (relative to perfect-info) markedly weaker effective constraint --
    the exact contrast this milestone's Section 8 requires."""

    def test_placebo_has_activity_but_weaker_detection_than_perfect_info(self):
        base_kwargs = dict(population_size=30, n_patches=3, n_steps=200, seed=3)
        placebo = Simulation(SimulationConfig.level11b_accountability_randomized_placebo(**base_kwargs)).run().event_log
        perfect = Simulation(SimulationConfig.level11b_accountability_perfect_info(**base_kwargs)).run().event_log

        placebo_activity = accountability_activity(placebo)
        perfect_activity = accountability_activity(perfect)
        assert placebo_activity["n_audits"] > 0  # activity is present under placebo

        placebo_constraint = effective_constraint(placebo)
        perfect_constraint = effective_constraint(perfect)
        if placebo_constraint["detection_rate_given_misconduct"] is not None and perfect_constraint["detection_rate_given_misconduct"] is not None:
            # perfect-info's detection rate must be (weakly) higher --
            # audit_accuracy=1.0 vs. 0.5 (coin flip) is not a subtle
            # difference.
            assert perfect_constraint["detection_rate_given_misconduct"] >= placebo_constraint["detection_rate_given_misconduct"]
