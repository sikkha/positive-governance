"""Level 1.1, Work Package D: endogenous delegation (nomination,
candidate evaluation, selection, removal/replacement)."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog
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


def _rule(rule_id=0, patch_id=0, members=(0, 1, 2), founder=0):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    return SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=founder, rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )


class TestNominationAndSelection:
    def test_zero_nomination_probability_produces_no_nominations(self):
        agents = {i: _agent(i, nomination_probability=0.0) for i in range(3)}
        rule = _rule()
        registry = {0: rule}
        delegate_registry: dict = {}
        pending: dict = {}
        prior_capacity: dict = {}
        config = SimulationConfig.level11_delegation_only()
        rng = np.random.default_rng(0)
        log = EventLog()
        id_state = {"next_delegate_id": 0}
        for step in range(config.delegate_nomination_window_steps + 1):
            rd.nomination_and_selection_round(
                step, registry, agents, None, delegate_registry, pending, prior_capacity, config, rng, log, id_state,
            )
        assert log.delegate_nominations == []
        assert delegate_registry == {}

    def test_certain_nomination_and_lottery_selection_always_appoints(self):
        agents = {i: _agent(i, nomination_probability=1.0) for i in range(4)}
        rule = _rule(members=(0, 1, 2, 3))
        registry = {0: rule}
        delegate_registry: dict = {}
        pending: dict = {}
        prior_capacity: dict = {}
        config = SimulationConfig.level11_delegation_only(delegate_selection_procedure="lottery")
        rng = np.random.default_rng(1)
        log = EventLog()
        id_state = {"next_delegate_id": 0}
        for step in range(config.delegate_nomination_window_steps + 1):
            rd.nomination_and_selection_round(
                step, registry, agents, None, delegate_registry, pending, prior_capacity, config, rng, log, id_state,
            )
        assert 0 in delegate_registry
        assert delegate_registry[0].agent_id in {0, 1, 2, 3}
        assert len(log.delegate_appointments) == 1
        assert log.delegate_appointments[0].appointment_method == "lottery"

    def test_threshold_acceptance_appoints_nobody_when_support_never_clears_the_bar(self):
        # All evaluation weight placed on the (always non-positive)
        # cost-aversion term and support required at unanimity (1.0) --
        # deterministically demonstrates "threshold_acceptance appoints
        # no one below threshold" without depending on a delicate
        # multi-term score calibration.
        agents = {i: _agent(i, nomination_probability=1.0) for i in range(4)}
        rule = _rule(members=(0, 1, 2, 3))
        registry = {0: rule}
        delegate_registry: dict = {}
        pending: dict = {}
        config = SimulationConfig.level11_delegation_only(
            delegate_selection_procedure="threshold_acceptance", delegate_selection_support_threshold=1.0,
            delegate_evaluation_reliability_weight=0.0, delegate_evaluation_competence_weight=0.0,
            delegate_evaluation_trust_weight=0.0, delegate_evaluation_resource_weight=0.0,
            delegate_evaluation_cost_aversion_weight=1.0, institutional_decision_noise_std=0.05,
        )
        rng = np.random.default_rng(2)
        log = EventLog()
        id_state = {"next_delegate_id": 0}
        for step in range(config.delegate_nomination_window_steps + 1):
            rd.nomination_and_selection_round(
                step, registry, agents, None, delegate_registry, pending, {}, config, rng, log, id_state,
            )
        assert delegate_registry == {}
        assert len(log.delegate_nominations) > 0  # nominations still happened; only selection failed

    def test_candidate_evaluation_score_rewards_higher_traits(self):
        weak = _agent(1, perceived_competence=0.05, social_trust=0.05, resources=1.0)
        strong = _agent(2, perceived_competence=0.95, social_trust=0.95, resources=1.0)
        config = SimulationConfig.level11_delegation_only()
        weak_score = rd._candidate_evaluation_score(weak, n_eligible=4, max_resources=1.0, prior_capacity=0.0, config=config)
        strong_score = rd._candidate_evaluation_score(strong, n_eligible=4, max_resources=1.0, prior_capacity=0.0, config=config)
        assert strong_score > weak_score

    def test_candidate_evaluation_score_uses_prior_delegate_capacity_as_reliability(self):
        candidate = _agent(1)
        config = SimulationConfig.level11_delegation_only()
        low_prior = rd._candidate_evaluation_score(candidate, n_eligible=4, max_resources=20.0, prior_capacity=0.01, config=config)
        high_prior = rd._candidate_evaluation_score(candidate, n_eligible=4, max_resources=20.0, prior_capacity=0.99, config=config)
        assert high_prior > low_prior

    def test_only_one_active_delegate_per_rule_at_a_time(self):
        agents = {i: _agent(i, nomination_probability=1.0) for i in range(4)}
        rule = _rule(members=(0, 1, 2, 3))
        registry = {0: rule}
        existing = rd.Delegate(
            delegate_id=99, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=1,
            tasks=("monitoring",), appointment_method="lottery", start_step=0, active=True,
        )
        delegate_registry = {0: existing}
        pending: dict = {}
        config = SimulationConfig.level11_delegation_only()
        rng = np.random.default_rng(3)
        log = EventLog()
        id_state = {"next_delegate_id": 0}
        rd.nomination_and_selection_round(0, registry, agents, None, delegate_registry, pending, {}, config, rng, log, id_state)
        assert delegate_registry[0] is existing
        assert log.delegate_nominations == []

    def test_replacement_appends_predecessor_to_history_and_carries_memory(self):
        agents = {i: _agent(i, nomination_probability=1.0) for i in range(4)}
        rule = _rule(members=(0, 1, 2, 3))
        registry = {0: rule}
        predecessor = rd.Delegate(
            delegate_id=5, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=1,
            tasks=("monitoring",), appointment_method="lottery", start_step=0, active=False, removal_step=10,
            record_quality=0.5,
        )
        delegate_registry = {0: predecessor}
        pending: dict = {}
        config = SimulationConfig.level11_delegation_only(
            delegate_selection_procedure="lottery", institutional_memory_transfer_to_new_delegate=0.4,
            institutional_memory_retention=0.6,
        )
        rng = np.random.default_rng(4)
        log = EventLog()
        id_state = {"next_delegate_id": 6}
        history: list = []
        for step in range(config.delegate_nomination_window_steps + 1):
            rd.nomination_and_selection_round(
                step, registry, agents, None, delegate_registry, pending, {}, config, rng, log, id_state, history,
            )
        assert history == [predecessor]
        new_delegate = delegate_registry[0]
        assert new_delegate.delegate_id != predecessor.delegate_id
        assert new_delegate.predecessor_delegate_id == predecessor.delegate_id
        # institutional_memory is absorbed from the *predecessor's own*
        # realized record_quality (0.5) scaled by institutional_memory_
        # retention (0.6) at the moment of replacement, then a fraction of
        # that (institutional_memory_transfer_to_new_delegate=0.4) is
        # granted to the successor as a starting-quality bonus.
        assert rule.institutional_memory == pytest.approx(0.5 * 0.6)
        assert new_delegate.record_quality == pytest.approx(0.5 * 0.6 * 0.4)

    def test_institutional_memory_stays_zero_for_a_rules_first_ever_delegate(self):
        agents = {i: _agent(i, nomination_probability=1.0) for i in range(4)}
        rule = _rule(members=(0, 1, 2, 3))
        registry = {0: rule}
        delegate_registry: dict = {}
        pending: dict = {}
        config = SimulationConfig.level11_delegation_only(delegate_selection_procedure="lottery")
        rng = np.random.default_rng(5)
        log = EventLog()
        id_state = {"next_delegate_id": 0}
        for step in range(config.delegate_nomination_window_steps + 1):
            rd.nomination_and_selection_round(
                step, registry, agents, None, delegate_registry, pending, {}, config, rng, log, id_state,
            )
        assert rule.institutional_memory == pytest.approx(0.0)
        # memory_bonus = 0.0 * transfer_fraction = 0.0 -- the first-ever
        # delegate at a rule starts with zero record_quality, not the
        # Delegate dataclass's own out-of-context default (0.2), since
        # the constructor always passes the (here zero) memory bonus
        # explicitly.
        assert delegate_registry[0].record_quality == pytest.approx(0.0)


class TestDelegateRemoval:
    def test_remove_delegate_is_idempotent_and_logs_once(self):
        agent = _agent(0)
        delegate = rd.Delegate(
            delegate_id=0, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=0,
            tasks=("monitoring",), appointment_method="lottery", start_step=0,
        )
        log = EventLog()
        rd._remove_delegate(10, delegate, {0: agent}, "resignation", log)
        rd._remove_delegate(11, delegate, {0: agent}, "resignation", log)
        assert len(log.delegate_removals) == 1
        assert delegate.active is False
        assert delegate.removal_step == 10

    def test_rule_dissolution_removes_its_delegate(self):
        delegate = rd.Delegate(
            delegate_id=0, rule_id=7, rule_lineage_id=7, patch_id=0, agent_id=0,
            tasks=("monitoring",), appointment_method="lottery", start_step=0,
        )
        registry = {7: delegate}
        log = EventLog()
        rd.handle_rule_dissolution_removals(20, {7}, registry, {}, {0: _agent(0)}, log)
        assert delegate.active is False
        assert delegate.removal_reason == "rule_dissolved"
        assert len(log.delegate_removals) == 1


class TestEndToEndActivation:
    def test_delegation_mechanism_fires_in_a_short_run(self):
        config = SimulationConfig.level11_delegation_only(
            population_size=50, n_steps=250, n_patches=3, seed=5,
        )
        sim = Simulation(config)
        sim.run()
        assert len(sim.event_log.delegate_nominations) > 0
        assert len(sim.event_log.delegate_appointments) > 0
        assert len(sim.event_log.task_performances) > 0

    def test_zero_nomination_probability_population_never_appoints(self):
        config = SimulationConfig.level11_delegation_only(population_size=30, n_steps=150, n_patches=2, seed=6)
        sim = Simulation(config)
        for agent in sim.agents:
            agent.nomination_probability = 0.0
        sim.run()
        assert sim.event_log.delegate_appointments == []
        assert sim.delegate_registry == {}

    def test_delegate_appointment_records_full_export_fields(self):
        config = SimulationConfig.level11_delegation_only(population_size=50, n_steps=250, n_patches=3, seed=8)
        sim = Simulation(config)
        sim.run()
        assert sim.event_log.delegate_appointments, "expected at least one appointment in this seeded run"
        ev = sim.event_log.delegate_appointments[0]
        assert ev.patch_id is not None
        assert ev.rule_lineage_id is not None
        assert ev.tasks
        assert ev.candidate_set
        assert ev.selector_population
        assert 0.0 <= ev.support_fraction <= 1.0
        assert ev.appointment_method in (
            "voluntary_approval", "plurality_support", "threshold_acceptance", "lottery",
        )
