"""Level 1.2, Work Package G: environmental heterogeneity — the one new
generative addition this work package needed (patch-quality spatial
correlation); every other named heterogeneity dimension (resource
regeneration, shock frequency/magnitude, information error, movement/
communication cost, population density) already had a pre-existing
config knob, listed in ``docs/odd_level1.2.md`` once written."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.environment.patches import build_patch_system
from abm_governance.rules import delegation as rd
from abm_governance.rules.shared_rule import RuleParameters, SharedRule
from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.events import EventLog
import networkx as nx


class TestPatchQualitySpatialCorrelation:
    def test_zero_correlation_is_a_strict_noop(self):
        graph = nx.cycle_graph(10)
        rng1 = np.random.default_rng(0)
        rng2 = np.random.default_rng(0)
        ps_a = build_patch_system(list(range(10)), graph, 5, 100.0, 0.5, 0.5, "random_assignment", 0.2, rng1, quality_spatial_correlation=0.0)
        ps_b = build_patch_system(list(range(10)), graph, 5, 100.0, 0.5, 0.5, "random_assignment", 0.2, rng2)
        for pid in ps_a.patches:
            assert ps_a.patches[pid].quality == pytest.approx(ps_b.patches[pid].quality)

    def test_perfect_correlation_makes_every_patch_identical_quality(self):
        graph = nx.cycle_graph(10)
        rng = np.random.default_rng(1)
        ps = build_patch_system(list(range(10)), graph, 6, 100.0, 0.5, 0.5, "random_assignment", 0.3, rng, quality_spatial_correlation=1.0)
        qualities = [p.quality for p in ps.patches.values()]
        assert all(q == pytest.approx(qualities[0]) for q in qualities)

    def test_out_of_range_correlation_rejected(self):
        graph = nx.cycle_graph(10)
        with pytest.raises(ValueError):
            build_patch_system(list(range(10)), graph, 3, 100.0, 0.5, 0.5, "random_assignment", 0.2, np.random.default_rng(0), quality_spatial_correlation=1.5)

    def test_config_default_reproduces_pre_level12_behavior(self):
        config = SimulationConfig.level03_patches_default(seed=4)
        assert config.patch_quality_spatial_correlation == 0.0


class TestScalingEconomiesOfScaleAllowed:
    def _agent(self, agent_id, resources=1000.0):
        a = Agent(
            agent_id=agent_id, resources=resources, coercive_capability=0.0, policy=make_policy("tit_for_tat"),
            observation_accuracy=0.9, learning_rate=0.1, forgiveness=0.1, risk_sensitivity=0.5, exit_cost=0.1,
        )
        a.ecological_policy = EcologicalPolicy(0.5, 0.3, 0.0)
        return a

    def test_negative_overhead_reduces_cost_but_never_below_floor(self):
        config = SimulationConfig.level1_rule_formation_default(
            delegation_enabled=True, interpatch_coordination_enabled=True,
            institutional_scaling_enabled=True, scaling_admin_overhead_per_patch=-0.5,
            delegation_task_cost=1.0, discretion_enabled=False,
        )
        params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
        rule = SharedRule(rule_id=0, patch_id=0, parameters=params, founding_step=0, founder_id=1, rule_lineage_id=0, members=frozenset({1, 2}))
        delegate = rd.Delegate(delegate_id=0, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=1, tasks=("monitoring",), appointment_method="voluntary_approval", start_step=0)
        agents = {1: self._agent(1), 2: self._agent(2)}
        log = EventLog()
        rd.task_performance_round(0, {0: rule}, {0: delegate}, agents, config, np.random.default_rng(0), log, jurisdiction_size_by_patch={0: 20})
        spent = sum(e.amount for e in log.administrative_spending)
        assert spent >= 0.1 * 1.0 - 1e-9
