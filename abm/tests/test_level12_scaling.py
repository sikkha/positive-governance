"""Level 1.2, Work Package F: institutional scaling."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog
from abm_governance.rules import delegation as rd
from abm_governance.rules import scaling as rs
from abm_governance.rules.coordination import CoordinationLink
from abm_governance.rules.shared_rule import RuleParameters, SharedRule


def _link(link_id, a, b, active=True):
    return CoordinationLink(
        link_id=link_id, patch_id_a=a, patch_id_b=b, rule_id_a=a, rule_id_b=b,
        kind="information_exchange", proposed_step=0, accepted_step=0, active=active,
    )


class TestComputeCoordinationComponents:
    def test_no_links_yields_no_components(self):
        assert rs.compute_coordination_components({}) == {}

    def test_two_linked_patches_form_one_component(self):
        comps = rs.compute_coordination_components({0: _link(0, 0, 1)})
        assert comps == {0: frozenset({0, 1})}

    def test_chain_of_three_forms_one_component(self):
        comps = rs.compute_coordination_components({0: _link(0, 0, 1), 1: _link(1, 1, 2)})
        assert comps == {0: frozenset({0, 1, 2})}

    def test_inactive_link_excluded(self):
        comps = rs.compute_coordination_components({0: _link(0, 0, 1, active=False)})
        assert comps == {}

    def test_two_disjoint_pairs_form_two_components(self):
        comps = rs.compute_coordination_components({0: _link(0, 0, 1), 1: _link(1, 2, 3)})
        assert comps == {0: frozenset({0, 1}), 2: frozenset({2, 3})}


class TestJurisdictionSizeByPatch:
    def test_matches_component_size(self):
        comps = {0: frozenset({0, 1, 2})}
        sizes = rs.jurisdiction_size_by_patch(comps)
        assert sizes == {0: 3, 1: 3, 2: 3}

    def test_patch_outside_any_component_absent_defaults_to_one_via_get(self):
        sizes = rs.jurisdiction_size_by_patch({0: frozenset({0, 1})})
        assert sizes.get(5, 1) == 1


class TestInstitutionalScalingRound:
    def test_no_op_when_disabled(self):
        config = SimulationConfig.level1_rule_formation_default(institutional_scaling_enabled=False)
        log = EventLog()
        result = rs.institutional_scaling_round(0, {0: _link(0, 0, 1)}, config, log, {})
        assert log.coordination_scale_changes == []
        assert result == {}

    def test_new_jurisdiction_reports_grew(self):
        config = SimulationConfig.level1_rule_formation_default(interpatch_coordination_enabled=True, institutional_scaling_enabled=True)
        log = EventLog()
        result = rs.institutional_scaling_round(0, {0: _link(0, 0, 1)}, config, log, {})
        assert len(log.coordination_scale_changes) == 1
        assert log.coordination_scale_changes[0].change == "grew"
        assert log.coordination_scale_changes[0].jurisdiction_patch_count == 2
        assert result == {0: frozenset({0, 1})}

    def test_jurisdiction_growing_further_reports_grew_again(self):
        config = SimulationConfig.level1_rule_formation_default(interpatch_coordination_enabled=True, institutional_scaling_enabled=True)
        log = EventLog()
        prior = {0: frozenset({0, 1})}
        result = rs.institutional_scaling_round(1, {0: _link(0, 0, 1), 1: _link(1, 1, 2)}, config, log, prior)
        assert log.coordination_scale_changes[-1].change == "grew"
        assert log.coordination_scale_changes[-1].jurisdiction_patch_count == 3
        assert result == {0: frozenset({0, 1, 2})}

    def test_dissolution_reports_dissolved(self):
        config = SimulationConfig.level1_rule_formation_default(interpatch_coordination_enabled=True, institutional_scaling_enabled=True)
        log = EventLog()
        prior = {0: frozenset({0, 1})}
        result = rs.institutional_scaling_round(2, {}, config, log, prior)
        assert log.coordination_scale_changes[-1].change == "dissolved"
        assert result == {}

    def test_merge_of_two_jurisdictions_reports_merged(self):
        config = SimulationConfig.level1_rule_formation_default(interpatch_coordination_enabled=True, institutional_scaling_enabled=True)
        log = EventLog()
        prior = {0: frozenset({0, 1}), 2: frozenset({2, 3})}
        result = rs.institutional_scaling_round(3, {0: _link(0, 0, 1), 1: _link(1, 2, 3), 2: _link(2, 1, 2)}, config, log, prior)
        changes = {e.change for e in log.coordination_scale_changes}
        assert "merged" in changes
        assert len(result) == 1
        assert next(iter(result.values())) == frozenset({0, 1, 2, 3})

    def test_unchanged_jurisdiction_produces_no_event(self):
        config = SimulationConfig.level1_rule_formation_default(interpatch_coordination_enabled=True, institutional_scaling_enabled=True)
        log = EventLog()
        prior = {0: frozenset({0, 1})}
        rs.institutional_scaling_round(4, {0: _link(0, 0, 1)}, config, log, prior)
        assert log.coordination_scale_changes == []


class TestAdminOverheadLiveness:
    def _agent(self, agent_id, resources=50.0):
        a = Agent(
            agent_id=agent_id, resources=resources, coercive_capability=0.0, policy=make_policy("tit_for_tat"),
            observation_accuracy=0.9, learning_rate=0.1, forgiveness=0.1, risk_sensitivity=0.5, exit_cost=0.1,
        )
        a.ecological_policy = EcologicalPolicy(0.5, 0.3, 0.0)
        return a

    def test_larger_jurisdiction_spends_more_per_task_attempt(self):
        config = SimulationConfig.level1_rule_formation_default(
            delegation_enabled=True, interpatch_coordination_enabled=True,
            institutional_scaling_enabled=True, scaling_admin_overhead_per_patch=0.5,
            delegation_task_cost=1.0, discretion_enabled=False,
        )
        params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
        rule = SharedRule(rule_id=0, patch_id=0, parameters=params, founding_step=0, founder_id=1, rule_lineage_id=0, members=frozenset({1, 2}))
        delegate = rd.Delegate(delegate_id=0, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=1, tasks=("monitoring",), appointment_method="voluntary_approval", start_step=0)
        agents = {1: self._agent(1, resources=1000.0), 2: self._agent(2)}

        log_small = EventLog()
        rd.task_performance_round(0, {0: rule}, {0: delegate}, agents, config, np.random.default_rng(0), log_small, jurisdiction_size_by_patch={0: 1})
        spent_small = sum(e.amount for e in log_small.administrative_spending)

        log_large = EventLog()
        agents2 = {1: self._agent(1, resources=1000.0), 2: self._agent(2)}
        delegate2 = rd.Delegate(delegate_id=0, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=1, tasks=("monitoring",), appointment_method="voluntary_approval", start_step=0)
        rd.task_performance_round(0, {0: rule}, {0: delegate2}, agents2, config, np.random.default_rng(0), log_large, jurisdiction_size_by_patch={0: 5})
        spent_large = sum(e.amount for e in log_large.administrative_spending)

        assert spent_large > spent_small

    def test_none_jurisdiction_sizes_is_a_strict_noop(self):
        config = SimulationConfig.level1_rule_formation_default(delegation_enabled=True, delegation_task_cost=1.0, discretion_enabled=False)
        params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
        rule = SharedRule(rule_id=0, patch_id=0, parameters=params, founding_step=0, founder_id=1, rule_lineage_id=0, members=frozenset({1, 2}))
        delegate = rd.Delegate(delegate_id=0, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=1, tasks=("monitoring",), appointment_method="voluntary_approval", start_step=0)
        agents = {1: self._agent(1, resources=1000.0), 2: self._agent(2)}
        log = EventLog()
        rd.task_performance_round(0, {0: rule}, {0: delegate}, agents, config, np.random.default_rng(0), log)
        assert sum(e.amount for e in log.administrative_spending) == pytest.approx(1.0)


class TestSimulationIntegration:
    def test_scale_events_and_overhead_do_not_break_a_full_run(self):
        from abm_governance.simulation import Simulation

        config = SimulationConfig.level1_rule_formation_default(
            population_size=24, n_steps=80, n_patches=4, seed=17,
            proposal_probability_mean=0.3, proposal_probability_std=0.02,
            delegation_enabled=True, interpatch_coordination_enabled=True, coordination_proposal_probability=0.4,
            institutional_scaling_enabled=True, scaling_admin_overhead_per_patch=0.1,
        )
        sim = Simulation(config)
        sim.run()
        for e in sim.event_log.coordination_scale_changes:
            assert e.change in ("grew", "shrank", "merged", "fragmented", "dissolved")
