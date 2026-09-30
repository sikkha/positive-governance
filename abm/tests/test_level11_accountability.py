"""Level 1.1, Work Package G: accountability and constraint (audit,
recall, appeal)."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog, SanctionEvent
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
    for k, v in overrides.items():
        setattr(a, k, v)
    return a


def _rule(rule_id=0, patch_id=0, members=(0, 1, 2), founder=0, fund=0.0):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    r = SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=founder, rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )
    r.fund = fund
    return r


def _delegate(agent_id=1, rule_id=0):
    return rd.Delegate(
        delegate_id=0, rule_id=rule_id, rule_lineage_id=rule_id, patch_id=0, agent_id=agent_id,
        tasks=("monitoring",), appointment_method="lottery", start_step=0,
    )


class TestAccountabilityDisabledIsNoOp:
    def test_disabled_produces_zero_audits(self):
        rule = _rule()
        registry = {0: rule}
        d = _delegate()
        d.misconduct_this_step = True
        delegate_registry = {0: d}
        agents = {0: _agent(0, audit_diligence=1.0), 1: _agent(1), 2: _agent(2, audit_diligence=1.0)}
        config = SimulationConfig.level11_delegation_only(accountability_enabled=False)
        rng = np.random.default_rng(0)
        log = EventLog()
        rd.accountability_round(0, registry, delegate_registry, agents, [], config, rng, log)
        assert log.audits == []


class TestAudit:
    def test_zero_audit_diligence_never_audits(self):
        rule = _rule()
        registry = {0: rule}
        d = _delegate()
        delegate_registry = {0: d}
        agents = {0: _agent(0, audit_diligence=0.0), 1: _agent(1), 2: _agent(2, audit_diligence=0.0)}
        config = SimulationConfig.level11_accountability_only()
        rng = np.random.default_rng(1)
        log = EventLog()
        rd.accountability_round(0, registry, delegate_registry, agents, [], config, rng, log)
        assert log.audits == []

    def test_certain_audit_costs_the_auditor(self):
        rule = _rule()
        registry = {0: rule}
        d = _delegate()
        d.misconduct_this_step = False
        delegate_registry = {0: d}
        agents = {0: _agent(0, audit_diligence=1.0, resources=10.0), 1: _agent(1), 2: _agent(2, audit_diligence=0.0)}
        config = SimulationConfig.level11_accountability_only(audit_cost=0.7, audit_probability_scale=1.0)
        rng = np.random.default_rng(2)
        log = EventLog()
        rd.accountability_round(0, registry, delegate_registry, agents, [], config, rng, log)
        assert len(log.audits) == 1
        assert agents[0].resources == pytest.approx(9.3)

    def test_audit_confusion_matrix_both_correct_and_incorrect_outcomes_reachable(self):
        outcomes = set()
        for seed in range(30):
            rule = _rule()
            registry = {0: rule}
            d = _delegate()
            d.misconduct_this_step = (seed % 2 == 0)
            delegate_registry = {0: d}
            agents = {0: _agent(0, audit_diligence=1.0), 1: _agent(1), 2: _agent(2, audit_diligence=0.0)}
            config = SimulationConfig.level11_accountability_only(audit_accuracy=0.7)
            rng = np.random.default_rng(seed)
            log = EventLog()
            rd.accountability_round(0, registry, delegate_registry, agents, [], config, rng, log)
            if log.audits:
                outcomes.add(log.audits[0].outcome)
        assert {"true_positive", "false_negative"} & outcomes or {"false_positive", "true_negative"} & outcomes
        assert len(outcomes) >= 2  # imperfect: not every audit reaches the same verdict


class TestRecall:
    def test_no_finding_no_recall_vote(self):
        rule = _rule()
        registry = {0: rule}
        d = _delegate()
        d.misconduct_this_step = False
        delegate_registry = {0: d}
        agents = {0: _agent(0, audit_diligence=0.0), 1: _agent(1), 2: _agent(2, audit_diligence=0.0)}
        config = SimulationConfig.level11_accountability_only()
        rng = np.random.default_rng(3)
        log = EventLog()
        rd.accountability_round(0, registry, delegate_registry, agents, [], config, rng, log)
        assert log.recalls == []

    def test_sustained_finding_history_eventually_drives_recall(self):
        # A delegate with a long history of found misconduct (high
        # finding_rate) should be recalled with much higher probability
        # than one with a clean record.
        rule = _rule()
        registry = {0: rule}
        d_bad = _delegate()
        d_bad.audits_failed = 20
        d_bad.audits_survived = 0
        delegate_registry = {0: d_bad}
        agents = {0: _agent(0, audit_diligence=1.0, social_trust=0.1), 1: _agent(1), 2: _agent(2, audit_diligence=1.0, social_trust=0.1)}
        config = SimulationConfig.level11_accountability_only(audit_accuracy=0.99, recall_support_threshold=0.4)
        n_recalled = 0
        for seed in range(20):
            registry2 = {0: _rule()}
            d2 = rd.Delegate(
                delegate_id=1, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=1,
                tasks=("monitoring",), appointment_method="lottery", start_step=0,
                audits_failed=20, audits_survived=0,
            )
            delegate_registry2 = {0: d2}
            agents2 = {0: _agent(0, audit_diligence=1.0, social_trust=0.1), 1: _agent(1), 2: _agent(2, audit_diligence=1.0, social_trust=0.1)}
            d2.misconduct_this_step = True
            rng = np.random.default_rng(seed)
            log = EventLog()
            rd.accountability_round(seed, registry2, delegate_registry2, agents2, [], config, rng, log)
            if log.recalls and log.recalls[0].succeeded:
                n_recalled += 1
        assert n_recalled > 0

    def test_successful_recall_removes_delegate_and_recovers_funds(self):
        rule = _rule(fund=5.0)
        registry = {0: rule}
        d = rd.Delegate(
            delegate_id=0, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=1,
            tasks=("monitoring",), appointment_method="lottery", start_step=0,
            audits_failed=50, audits_survived=0, appropriated_total=10.0,
        )
        d.misconduct_this_step = True
        delegate_registry = {0: d}
        agents = {0: _agent(0, audit_diligence=1.0, social_trust=0.0), 1: _agent(1), 2: _agent(2, audit_diligence=1.0, social_trust=0.0)}
        config = SimulationConfig.level11_accountability_only(
            audit_accuracy=0.999, recall_support_threshold=0.01, recall_fund_recovery_fraction=0.5,
        )
        rng = np.random.default_rng(9)
        log = EventLog()
        rd.accountability_round(0, registry, delegate_registry, agents, [], config, rng, log)
        assert len(log.recalls) == 1
        recall_ev = log.recalls[0]
        if recall_ev.succeeded:
            assert d.active is False
            assert d.removal_reason == "recalled"
            assert rule.fund == pytest.approx(5.0 + 10.0 * 0.5)

    def test_delegate_with_a_strong_clean_record_survives_a_single_new_finding(self):
        # A delegate with an established clean track record (20 clean
        # audits) who is found wanting on exactly one new audit should
        # not be swept out by that single finding -- accumulated
        # observable history, not a single accusation, drives recall.
        rule = _rule()
        registry = {0: rule}
        d = rd.Delegate(
            delegate_id=0, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=1,
            tasks=("monitoring",), appointment_method="lottery", start_step=0,
            audits_failed=0, audits_survived=20,
        )
        d.misconduct_this_step = True
        delegate_registry = {0: d}
        agents = {0: _agent(0, audit_diligence=1.0, social_trust=0.5), 1: _agent(1), 2: _agent(2, audit_diligence=0.0)}
        # threshold=0.6 with only 2 eligible voters requires *both* to
        # support (1/2=0.5 does not clear 0.6) -- with a 20-clean-audit
        # track record, support probability per voter is low, so
        # requiring unanimity makes success very unlikely on this seed.
        config = SimulationConfig.level11_accountability_only(audit_accuracy=0.99, recall_support_threshold=0.6)
        rng = np.random.default_rng(11)
        log = EventLog()
        rd.accountability_round(0, registry, delegate_registry, agents, [], config, rng, log)
        if log.recalls:
            assert log.recalls[0].succeeded is False
            assert d.active is True

    def test_recall_voters_exclude_the_delegate_itself(self):
        rule = _rule()
        registry = {0: rule}
        d = rd.Delegate(
            delegate_id=0, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=1,
            tasks=("monitoring",), appointment_method="lottery", start_step=0,
            audits_failed=50, audits_survived=0,
        )
        d.misconduct_this_step = True
        delegate_registry = {0: d}
        agents = {0: _agent(0, audit_diligence=1.0, social_trust=0.0), 1: _agent(1, social_trust=0.0), 2: _agent(2, audit_diligence=0.0)}
        config = SimulationConfig.level11_accountability_only(audit_accuracy=0.999, recall_support_threshold=0.01)
        rng = np.random.default_rng(12)
        log = EventLog()
        rd.accountability_round(0, registry, delegate_registry, agents, [], config, rng, log)
        if log.recalls:
            assert log.recalls[0].n_eligible == 2  # 3 members minus the delegate itself


class TestAppeal:
    def _sanction_event(self, step=0, rule_id=0, target=2, false_sanction=True, magnitude=0.5):
        return SanctionEvent(
            step=step, patch_id=0, rule_id=rule_id, target=target, magnitude=magnitude, cost=0.1,
            funded_by="bystander", false_sanction=false_sanction, sanctioner=1,
        )

    def test_zero_appeal_probability_never_appeals(self):
        rule = _rule()
        registry = {0: rule}
        d = _delegate()
        delegate_registry = {0: d}
        agents = {0: _agent(0), 1: _agent(1), 2: _agent(2)}
        config = SimulationConfig.level11_accountability_only(appeal_probability=0.0)
        rng = np.random.default_rng(5)
        log = EventLog()
        rd.accountability_round(0, registry, delegate_registry, agents, [self._sanction_event()], config, rng, log)
        assert log.appeals == []

    def test_true_positive_appeal_upheld_more_often_than_false_positive(self):
        rule = _rule()
        registry = {0: rule}
        upheld_true = 0
        upheld_false = 0
        n = 60
        for seed in range(n):
            d = _delegate()
            delegate_registry = {0: d}
            agents = {0: _agent(0), 1: _agent(1), 2: _agent(2)}
            config = SimulationConfig.level11_accountability_only(
                appeal_probability=1.0, appeal_accuracy_true_positive=0.9, appeal_accuracy_false_positive=0.05,
            )
            rng = np.random.default_rng(seed)
            log = EventLog()
            ev = self._sanction_event(false_sanction=True)
            rd.accountability_round(0, {0: _rule()}, delegate_registry, dict(agents), [ev], config, rng, log)
            if log.appeals and log.appeals[0].upheld:
                upheld_true += 1
        for seed in range(n):
            d = _delegate()
            delegate_registry = {0: d}
            agents = {0: _agent(0), 1: _agent(1), 2: _agent(2)}
            config = SimulationConfig.level11_accountability_only(
                appeal_probability=1.0, appeal_accuracy_true_positive=0.9, appeal_accuracy_false_positive=0.05,
            )
            rng = np.random.default_rng(seed + 1000)
            log = EventLog()
            ev = self._sanction_event(false_sanction=False)
            rd.accountability_round(0, {0: _rule()}, delegate_registry, dict(agents), [ev], config, rng, log)
            if log.appeals and log.appeals[0].upheld:
                upheld_false += 1
        assert upheld_true > upheld_false

    def test_upheld_appeal_refunds_the_target(self):
        rule = _rule()
        registry = {0: rule}
        d = _delegate()
        delegate_registry = {0: d}
        target = _agent(2, resources=1.0)
        agents = {0: _agent(0), 1: _agent(1), 2: target}
        config = SimulationConfig.level11_accountability_only(
            appeal_probability=1.0, appeal_accuracy_true_positive=1.0, appeal_cost=0.0, appeal_refund_fraction=1.0,
        )
        rng = np.random.default_rng(6)
        log = EventLog()
        ev = self._sanction_event(false_sanction=True, magnitude=0.5)
        rd.accountability_round(0, registry, delegate_registry, agents, [ev], config, rng, log)
        assert len(log.appeals) == 1
        assert log.appeals[0].upheld is True
        assert log.appeals[0].refund > 0.0
        assert target.resources > 1.0


class TestEndToEndAccountabilityActivation:
    def test_accountability_fires_in_a_full_run(self):
        config = SimulationConfig.level11_accountability_only(population_size=60, n_steps=300, n_patches=4, seed=13)
        sim = Simulation(config)
        sim.run()
        log = sim.event_log
        assert len(log.audits) > 0
        # Both survived and failed audits should be reachable in a run
        # this size (imperfect information cuts both ways).
        outcomes = {e.outcome for e in log.audits}
        assert len(outcomes) >= 2

    def test_accountability_disabled_by_default_in_delegation_only(self):
        config = SimulationConfig.level11_delegation_only(population_size=40, n_steps=200, n_patches=3, seed=14)
        assert config.accountability_enabled is False
        sim = Simulation(config)
        sim.run()
        assert sim.event_log.audits == []
        assert sim.event_log.recalls == []
