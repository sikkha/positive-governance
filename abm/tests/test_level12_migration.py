"""Level 1.2, Work Package D: migration and membership selection."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog
from abm_governance.environment.patches import PatchSystem, ResourcePatch
from abm_governance.rules import migration as rm
from abm_governance.rules.shared_rule import RuleParameters, SharedRule
from abm_governance.simulation import Simulation


def _agent(agent_id, patch_id=0, resources=20.0, migration_propensity=0.9, **overrides):
    a = Agent(
        agent_id=agent_id, resources=resources, coercive_capability=0.0, policy=make_policy("tit_for_tat"),
        observation_accuracy=0.9, learning_rate=0.1, forgiveness=0.1, risk_sensitivity=0.5, exit_cost=0.1,
    )
    a.patch_id = patch_id
    a.ecological_policy = EcologicalPolicy(0.5, 0.3, 0.0)
    a.migration_propensity = migration_propensity
    for k, v in overrides.items():
        setattr(a, k, v)
    return a


def _rule(rule_id, patch_id, members):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    return SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=members[0], rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )


def _patch_system(n_patches=2, resources_per_patch=None, members_per_patch=None):
    patches = {}
    agent_patch = {}
    for pid in range(n_patches):
        res = (resources_per_patch or {}).get(pid, 50.0)
        members = (members_per_patch or {}).get(pid, ())
        patches[pid] = ResourcePatch(patch_id=pid, capacity=100.0, regen_rate=0.5, resources=res, members=frozenset(members))
        for aid in members:
            agent_patch[aid] = pid
    return PatchSystem(patches=patches, agent_patch=agent_patch)


class TestMigrationRoundPopulationAccounting:
    def test_no_op_when_disabled(self):
        config = SimulationConfig.level1_rule_formation_default(migration_enabled=False)
        ps = _patch_system(members_per_patch={0: (0, 1), 1: ()})
        agents = {0: _agent(0), 1: _agent(1)}
        log = EventLog()
        rm.migration_round(0, {}, ps, agents, config, np.random.default_rng(0), log, {})
        assert log.migrations == []
        assert ps.agent_patch == {0: 0, 1: 0}

    def test_population_conserved_across_many_migration_steps(self):
        config = SimulationConfig.level1_rule_formation_default(
            migration_enabled=True, migration_evaluation_period_steps=1, migration_cost=0.0,
        )
        n_agents = 10
        ps = _patch_system(n_patches=3, members_per_patch={0: tuple(range(n_agents))})
        agents = {aid: _agent(aid, resources=100.0) for aid in range(n_agents)}
        log = EventLog()
        rng = np.random.default_rng(1)
        history = {0: [(0, {"resource_level": 0.9, "fairness": 0.9, "burden": 0.0})]}
        for step in range(20):
            rm.migration_round(step, {}, ps, agents, config, rng, log, history)
        # Every original agent id is still present exactly once.
        assert set(ps.agent_patch.keys()) == set(range(n_agents))
        # Every patch's members frozenset matches agent_patch exactly.
        for pid, patch in ps.patches.items():
            expected = {aid for aid, p in ps.agent_patch.items() if p == pid}
            assert patch.members == frozenset(expected)

    def test_successful_migration_exits_origin_membership(self):
        config = SimulationConfig.level1_rule_formation_default(
            migration_enabled=True, migration_evaluation_period_steps=1, migration_cost=0.0,
        )
        ps = _patch_system(n_patches=2, members_per_patch={0: (0,)})
        rule0 = _rule(0, 0, (0,))
        agents = {0: _agent(0, resources=100.0, migration_propensity=1.0)}
        agents[0].rule_member_of = 0
        log = EventLog()
        history = {1: [(0, {"resource_level": 1.0, "fairness": 1.0, "burden": 0.0})], 0: [(0, {"resource_level": 0.0, "fairness": 0.0, "burden": 1.0})]}
        rng = np.random.default_rng(2)
        for step in range(10):
            rm.migration_round(step, {0: rule0}, ps, agents, config, rng, log, history)
            if agents[0].agent_id not in rule0.members and ps.agent_patch[0] == 1:
                break
        succeeded = [e for e in log.migrations if e.outcome == "succeeded"]
        assert succeeded, "expected at least one successful migration under a strongly favorable utility gap"
        assert 0 not in rule0.members
        assert agents[0].rule_member_of is None

    def test_refused_no_capacity_leaves_agent_in_place(self):
        config = SimulationConfig.level1_rule_formation_default(
            migration_enabled=True, migration_evaluation_period_steps=1, migration_cost=0.0,
            migration_capacity_per_patch=1,
        )
        ps = _patch_system(n_patches=2, members_per_patch={0: (0,), 1: (1,)})
        agents = {0: _agent(0, resources=100.0, migration_propensity=1.0), 1: _agent(1, resources=100.0)}
        log = EventLog()
        history = {1: [(0, {"resource_level": 1.0, "fairness": 1.0, "burden": 0.0})], 0: [(0, {"resource_level": 0.0, "fairness": 0.0, "burden": 1.0})]}
        rng = np.random.default_rng(3)
        for step in range(10):
            rm.migration_round(step, {}, ps, agents, config, rng, log, history)
        refused = [e for e in log.migrations if e.outcome == "refused_no_capacity"]
        assert refused
        assert ps.agent_patch[0] == 0

    def test_refused_cost_when_agent_cannot_afford_migration(self):
        config = SimulationConfig.level1_rule_formation_default(
            migration_enabled=True, migration_evaluation_period_steps=1, migration_cost=1000.0,
        )
        ps = _patch_system(n_patches=2, members_per_patch={0: (0,)})
        agents = {0: _agent(0, resources=1.0, migration_propensity=1.0)}
        log = EventLog()
        history = {1: [(0, {"resource_level": 1.0, "fairness": 1.0, "burden": 0.0})], 0: [(0, {"resource_level": 0.0, "fairness": 0.0, "burden": 1.0})]}
        rng = np.random.default_rng(4)
        for step in range(10):
            rm.migration_round(step, {}, ps, agents, config, rng, log, history)
        outcomes = {e.outcome for e in log.migrations}
        assert "refused_cost" in outcomes or "succeeded" not in outcomes
        assert ps.agent_patch[0] == 0

    def test_zero_migration_propensity_agent_never_moves(self):
        config = SimulationConfig.level1_rule_formation_default(
            migration_enabled=True, migration_evaluation_period_steps=1, migration_cost=0.0,
        )
        ps = _patch_system(n_patches=2, members_per_patch={0: (0,)})
        agents = {0: _agent(0, resources=100.0, migration_propensity=0.0)}
        log = EventLog()
        history = {1: [(0, {"resource_level": 1.0, "fairness": 1.0, "burden": 0.0})]}
        rng = np.random.default_rng(5)
        for step in range(20):
            rm.migration_round(step, {}, ps, agents, config, rng, log, history)
        assert log.migrations == []
        assert ps.agent_patch[0] == 0


class TestMembershipExitRound:
    def test_no_op_when_disabled(self):
        config = SimulationConfig.level1_rule_formation_default(membership_exit_enabled=False)
        rule = _rule(0, 0, (0, 1))
        agents = {0: _agent(0), 1: _agent(1)}
        log = EventLog()
        rm.membership_exit_round(0, {0: rule}, agents, config, np.random.default_rng(0), log)
        assert log.membership_exits == []
        assert rule.members == frozenset({0, 1})

    def test_high_dissatisfaction_produces_exits_without_relocation(self):
        config = SimulationConfig.level1_rule_formation_default(
            membership_exit_enabled=True, migration_evaluation_period_steps=1,
        )
        rule = _rule(0, 0, tuple(range(20)))
        rule.compliance_count = 2
        rule.violation_count = 8
        rule.sanction_count = 8
        rule.fund = 100.0
        agents = {aid: _agent(aid, violation_tolerance=0.0, contribution_willingness=0.0) for aid in range(20)}
        log = EventLog()
        rng = np.random.default_rng(6)
        for step in range(30):
            rm.membership_exit_round(step, {0: rule}, agents, config, rng, log)
        assert len(log.membership_exits) >= 1
        for e in log.membership_exits:
            assert e.reason == "dissatisfaction"
            assert agents[e.agent_id].patch_id == 0  # never relocated


class TestSimulationIntegration:
    def test_migration_preserves_exact_population_in_a_full_run(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=24, n_steps=60, n_patches=4, seed=9,
            migration_enabled=True, migration_evaluation_period_steps=3, migration_cost=0.2,
            migration_propensity_mean=0.3, migration_propensity_std=0.1,
        )
        sim = Simulation(config)
        sim.run()
        assert set(sim.patch_system.agent_patch.keys()) == {a.agent_id for a in sim.agents}
        for pid, patch in sim.patch_system.patches.items():
            expected = {aid for aid, p in sim.patch_system.agent_patch.items() if p == pid}
            assert patch.members == frozenset(expected)
