"""Level 1.1, Work Packages E/F: administrative capacity accumulation,
decay, and delegate discretion/appropriation."""

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


def _rule(rule_id=0, patch_id=0, members=(0, 1, 2), founder=0, fund=0.0):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    r = SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=founder, rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )
    r.fund = fund
    return r


def _delegate(agent_id=1, rule_id=0, tasks=("monitoring",), record_quality=0.2):
    return rd.Delegate(
        delegate_id=0, rule_id=rule_id, rule_lineage_id=rule_id, patch_id=0, agent_id=agent_id,
        tasks=tasks, appointment_method="lottery", start_step=0, record_quality=record_quality,
    )


class TestCapacityStartsAtZeroAndAccumulates:
    def test_capacity_is_zero_before_any_task_attempt(self):
        d = _delegate()
        assert d.capacity == 0.0

    def test_capacity_rises_with_successful_attempts(self):
        d = _delegate()
        d.task_attempts["monitoring"] = 10
        d.task_successes["monitoring"] = 10
        d.record_quality = 0.9
        assert d.capacity > 0.0

    def test_capacity_is_realized_performance_not_a_raw_trait(self):
        # Two delegates with identical agent traits but different
        # realized histories have different capacity -- capacity is a
        # function of task_attempts/task_successes/record_quality, never
        # a copy of any Agent field.
        d_good = _delegate()
        d_good.task_attempts["monitoring"] = 20
        d_good.task_successes["monitoring"] = 18
        d_bad = _delegate()
        d_bad.task_attempts["monitoring"] = 20
        d_bad.task_successes["monitoring"] = 2
        assert d_good.capacity > d_bad.capacity


class TestTaskPerformanceRound:
    def test_no_delegate_no_events(self):
        registry = {0: _rule()}
        agents = {i: _agent(i) for i in (0, 1, 2)}
        config = SimulationConfig.level11_delegation_only()
        rng = np.random.default_rng(0)
        log = EventLog()
        rd.task_performance_round(0, registry, {}, agents, config, rng, log)
        assert log.task_performances == []

    def test_task_attempt_recorded_and_costs_paid(self):
        rule = _rule()
        registry = {0: rule}
        d = _delegate()
        delegate_registry = {0: d}
        agents = {0: _agent(0, resources=5.0), 1: _agent(1, resources=5.0), 2: _agent(2, resources=5.0)}
        config = SimulationConfig.level11_delegation_only(delegation_task_cost=0.5)
        rng = np.random.default_rng(1)
        log = EventLog()
        rd.task_performance_round(0, registry, delegate_registry, agents, config, rng, log)
        assert len(log.task_performances) == 1
        assert log.task_performances[0].outcome in ("success", "failure")
        assert agents[1].resources == pytest.approx(4.5)  # delegate is agent 1; fund empty -> personal payment

    def test_task_cost_drawn_from_fund_when_available(self):
        rule = _rule(fund=10.0)
        registry = {0: rule}
        d = _delegate()
        delegate_registry = {0: d}
        agents = {0: _agent(0), 1: _agent(1, resources=5.0), 2: _agent(2)}
        config = SimulationConfig.level11_delegation_only(delegation_task_cost=0.5)
        rng = np.random.default_rng(1)
        log = EventLog()
        rd.task_performance_round(0, registry, delegate_registry, agents, config, rng, log)
        assert agents[1].resources == pytest.approx(5.0)  # untouched -- fund paid instead
        assert rule.fund == pytest.approx(9.5)

    def test_zero_members_causes_inactivity_decay_no_attempts(self):
        rule = _rule(members=())
        registry = {0: rule}
        d = _delegate(record_quality=0.5)
        delegate_registry = {0: d}
        agents = {1: _agent(1)}
        config = SimulationConfig.level11_delegation_only(delegation_inactivity_decay_rate=0.1)
        rng = np.random.default_rng(2)
        log = EventLog()
        rd.task_performance_round(0, registry, delegate_registry, agents, config, rng, log)
        assert log.task_performances == []
        assert d.record_quality == pytest.approx(0.45)
        assert d.task_attempts == {}

    def test_capacity_can_decay_from_repeated_failure(self):
        rule = _rule()
        registry = {0: rule}
        agent = _agent(1, administrative_reliability=0.02)
        d = _delegate(record_quality=0.5)
        delegate_registry = {0: d}
        agents = {0: _agent(0), 1: agent, 2: _agent(2)}
        config = SimulationConfig.level11_delegation_only(
            delegation_task_cost=0.0, delegation_capacity_learning_weight=0.0,
        )
        rng = np.random.default_rng(3)
        log = EventLog()
        start_quality = d.record_quality
        for step in range(60):
            rd.task_performance_round(step, registry, delegate_registry, agents, config, rng, log)
        assert d.record_quality < start_quality

    def test_workload_penalty_reduces_success_probability_with_more_tasks(self):
        agent = _agent(1, administrative_reliability=0.9)
        config = SimulationConfig.level11_delegation_only(delegation_workload_penalty_per_task=0.3)
        d1 = _delegate(tasks=("monitoring",))
        d2 = _delegate(tasks=("monitoring", "record_keeping", "communication"))
        rule = _rule()
        p1 = rd._success_probability(d1, agent, 1, rule, config)
        p2 = rd._success_probability(d2, agent, 3, rule, config)
        assert p2 < p1


class TestDiscretionAndAppropriation:
    def test_discretion_disabled_never_appropriates(self):
        rule = _rule(fund=100.0)
        registry = {0: rule}
        agent = _agent(1, appropriation_propensity=1.0)  # would always try if enabled
        d = _delegate()
        delegate_registry = {0: d}
        agents = {0: _agent(0), 1: agent, 2: _agent(2)}
        config = SimulationConfig.level11_delegation_only(discretion_enabled=False, delegation_task_cost=0.0)
        rng = np.random.default_rng(4)
        log = EventLog()
        for step in range(20):
            rd.task_performance_round(step, registry, delegate_registry, agents, config, rng, log)
        assert log.appropriations == []
        assert d.appropriated_total == 0.0
        assert rule.fund == pytest.approx(100.0)  # untouched: no task cost, no appropriation

    def test_zero_appropriation_propensity_never_appropriates_even_when_enabled(self):
        rule = _rule(fund=100.0)
        registry = {0: rule}
        agent = _agent(1, appropriation_propensity=0.0)
        d = _delegate()
        delegate_registry = {0: d}
        agents = {0: _agent(0), 1: agent, 2: _agent(2)}
        config = SimulationConfig.level11_delegation_only(discretion_enabled=True)
        rng = np.random.default_rng(5)
        log = EventLog()
        for step in range(20):
            rd.task_performance_round(step, registry, delegate_registry, agents, config, rng, log)
        assert log.appropriations == []

    def test_certain_appropriation_is_fully_resource_accounted(self):
        rule = _rule(fund=100.0)
        registry = {0: rule}
        agent = _agent(1, appropriation_propensity=1.0, resources=0.0)
        d = _delegate()
        delegate_registry = {0: d}
        agents = {0: _agent(0), 1: agent, 2: _agent(2)}
        config = SimulationConfig.level11_delegation_only(
            discretion_enabled=True, appropriation_opportunity_scale=1.0, appropriation_fraction_of_fund=0.3,
            delegation_task_cost=0.0,
        )
        rng = np.random.default_rng(6)
        log = EventLog()
        rd.task_performance_round(0, registry, delegate_registry, agents, config, rng, log)
        assert len(log.appropriations) == 1
        ev = log.appropriations[0]
        assert ev.fund_before == pytest.approx(100.0)
        assert ev.fund_after == pytest.approx(70.0)
        assert ev.amount == pytest.approx(30.0)
        assert rule.fund == pytest.approx(70.0)
        assert agent.resources == pytest.approx(30.0)
        assert d.appropriated_total == pytest.approx(30.0)
        # ledger identity: amount removed from fund == amount credited to delegate
        assert ev.fund_before - ev.fund_after == pytest.approx(agent.resources)

    def test_appropriation_impossible_with_empty_fund(self):
        rule = _rule(fund=0.0)
        registry = {0: rule}
        agent = _agent(1, appropriation_propensity=1.0)
        d = _delegate()
        delegate_registry = {0: d}
        agents = {0: _agent(0), 1: agent, 2: _agent(2)}
        config = SimulationConfig.level11_delegation_only(discretion_enabled=True)
        rng = np.random.default_rng(7)
        log = EventLog()
        rd.task_performance_round(0, registry, delegate_registry, agents, config, rng, log)
        assert log.appropriations == []

    def test_certain_effort_reduction_is_recorded_as_withheld(self):
        rule = _rule()
        registry = {0: rule}
        agent = _agent(1, effort_reduction_propensity=1.0)
        d = _delegate()
        delegate_registry = {0: d}
        agents = {0: _agent(0), 1: agent, 2: _agent(2)}
        config = SimulationConfig.level11_delegation_only(discretion_enabled=True, effort_reduction_opportunity_scale=1.0)
        rng = np.random.default_rng(8)
        log = EventLog()
        rd.task_performance_round(0, registry, delegate_registry, agents, config, rng, log)
        assert log.task_performances[0].outcome == "withheld"
        assert d.effort_withheld_count == 1
        assert d.misconduct_this_step is True

    def test_misconduct_is_possible_but_not_inevitable(self):
        # With a moderate appropriation_propensity, both misconduct and
        # no-misconduct outcomes are reachable across seeds -- misconduct
        # must be possible but never mechanically certain.
        outcomes = set()
        for seed in range(10):
            rule = _rule(fund=50.0)
            registry = {0: rule}
            agent = _agent(1, appropriation_propensity=0.5)
            d = _delegate()
            delegate_registry = {0: d}
            agents = {0: _agent(0), 1: agent, 2: _agent(2)}
            config = SimulationConfig.level11_delegation_only(discretion_enabled=True)
            rng = np.random.default_rng(seed)
            log = EventLog()
            rd.task_performance_round(0, registry, delegate_registry, agents, config, rng, log)
            outcomes.add(len(log.appropriations) > 0)
        assert outcomes == {True, False}


class TestEndToEndCapacityActivation:
    def test_capacity_accumulates_and_can_decay_in_a_full_run(self):
        config = SimulationConfig.level11_capacity_only(population_size=50, n_steps=300, n_patches=3, seed=3)
        sim = Simulation(config)
        sim.run()
        all_delegates = list(sim.delegate_registry.values()) + sim.delegate_history
        with_attempts = [d for d in all_delegates if sum(d.task_attempts.values()) > 0]
        assert with_attempts, "expected at least one delegate to have attempted a task"
        assert any(d.capacity > 0.0 for d in with_attempts)

    def test_discretion_off_by_default_in_delegation_only_preset(self):
        config = SimulationConfig.level11_delegation_only(population_size=40, n_steps=200, n_patches=3, seed=4)
        assert config.discretion_enabled is False
        sim = Simulation(config)
        sim.run()
        assert sim.event_log.appropriations == []
