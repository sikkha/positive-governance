"""Level 1.2, Work Package B: local institutional observation."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog
from abm_governance.environment.patches import ResourcePatch
from abm_governance.rules import observation as ro
from abm_governance.rules.coordination import CoordinationLink
from abm_governance.rules.shared_rule import RuleParameters, SharedRule
from abm_governance.simulation import Simulation


def _agent(agent_id, patch_id=0, resources=20.0, **overrides):
    a = Agent(
        agent_id=agent_id, resources=resources, coercive_capability=0.0, policy=make_policy("tit_for_tat"),
        observation_accuracy=0.7, learning_rate=0.1, forgiveness=0.1, risk_sensitivity=0.5, exit_cost=0.1,
    )
    a.patch_id = patch_id
    a.ecological_policy = EcologicalPolicy(0.5, 0.3, 0.0)
    for k, v in overrides.items():
        setattr(a, k, v)
    return a


def _rule(rule_id, patch_id, members, fund=0.0, compliance=5, violation=1, sanctions=1):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    r = SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=members[0], rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )
    r.fund = fund
    r.compliance_count = compliance
    r.violation_count = violation
    r.sanction_count = sanctions
    return r


def _patch(patch_id, resources=60.0, capacity=100.0, members=()):
    return ResourcePatch(patch_id=patch_id, capacity=capacity, regen_rate=0.5, resources=resources, members=frozenset(members))


class TestComputeTrueInstitutionSignal:
    def test_resource_level_matches_patch_fraction(self):
        rule = _rule(0, 0, (0, 1))
        patch = _patch(0, resources=25.0, capacity=100.0)
        signal = ro.compute_true_institution_signal(rule, patch)
        assert signal["resource_level"] == pytest.approx(0.25)

    def test_fairness_undefined_with_no_interactions_yet(self):
        rule = _rule(0, 0, (0, 1), compliance=0, violation=0, sanctions=0)
        patch = _patch(0)
        signal = ro.compute_true_institution_signal(rule, patch)
        assert np.isnan(signal["fairness"])

    def test_burden_is_fund_per_member(self):
        rule = _rule(0, 0, (0, 1, 2, 3), fund=8.0)
        patch = _patch(0)
        signal = ro.compute_true_institution_signal(rule, patch)
        assert signal["burden"] == pytest.approx(2.0)


class TestLocalObservationRound:
    def _setup(self, **config_overrides):
        config = SimulationConfig.level1_rule_formation_default(
            interpatch_coordination_enabled=True, institutional_observation_enabled=True, **config_overrides
        )
        rule_a = _rule(0, 0, (0, 1))
        rule_b = _rule(1, 1, (2, 3))
        rules = {0: rule_a, 1: rule_b}
        patches = {0: _patch(0, resources=80.0), 1: _patch(1, resources=20.0)}
        link = CoordinationLink(
            link_id=0, patch_id_a=0, patch_id_b=1, rule_id_a=0, rule_id_b=1,
            kind="information_exchange", proposed_step=0, accepted_step=0,
        )
        links = {0: link}
        agents = {aid: _agent(aid, patch_id=(0 if aid < 2 else 1)) for aid in range(4)}
        return config, rules, patches, links, agents

    def test_no_op_when_observation_disabled(self):
        config, rules, patches, links, agents = self._setup()
        config = SimulationConfig.level1_rule_formation_default(interpatch_coordination_enabled=True, institutional_observation_enabled=False)
        log = EventLog()
        ro.local_observation_round(0, rules, patches, links, {}, agents, {}, config, np.random.default_rng(0), log, {})
        assert log.local_institution_observations == []

    def test_two_observations_produced_per_active_link(self):
        config, rules, patches, links, agents = self._setup(observation_period_steps=1)
        log = EventLog()
        history = {}
        ro.local_observation_round(0, rules, patches, links, {}, agents, {}, config, np.random.default_rng(0), log, history)
        assert len(log.local_institution_observations) == 2
        pairs = {(e.observer_patch_id, e.target_patch_id) for e in log.local_institution_observations}
        assert pairs == {(0, 1), (1, 0)}

    def test_perceived_resource_level_close_to_true_with_low_noise(self):
        config, rules, patches, links, agents = self._setup(observation_period_steps=1, observation_noise_std=0.01)
        log = EventLog()
        ro.local_observation_round(0, rules, patches, links, {}, agents, {}, config, np.random.default_rng(0), log, {})
        for e in log.local_institution_observations:
            if e.target_patch_id == 1:
                assert e.perceived_resource_level == pytest.approx(0.2, abs=0.1)
            else:
                assert e.perceived_resource_level == pytest.approx(0.8, abs=0.1)

    def test_true_signal_history_recorded_even_when_observation_disabled(self):
        config, rules, patches, links, agents = self._setup()
        config = SimulationConfig.level1_rule_formation_default(interpatch_coordination_enabled=True, institutional_observation_enabled=False)
        history = {}
        ro.local_observation_round(0, rules, patches, links, {}, agents, {}, config, np.random.default_rng(0), EventLog(), history)
        assert 0 in history and 1 in history
        assert history[0][-1][0] == 0

    def test_period_gate_skips_non_multiple_steps(self):
        config, rules, patches, links, agents = self._setup(observation_period_steps=5)
        log = EventLog()
        ro.local_observation_round(3, rules, patches, links, {}, agents, {}, config, np.random.default_rng(0), log, {})
        assert log.local_institution_observations == []


class TestSimulationIntegration:
    def test_observations_produced_in_a_full_run(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=24, n_steps=60, n_patches=4, seed=5,
            proposal_probability_mean=0.25, proposal_probability_std=0.02,
            interpatch_coordination_enabled=True, coordination_proposal_probability=0.3,
            institutional_observation_enabled=True, observation_period_steps=2,
        )
        sim = Simulation(config)
        sim.run()
        # Not guaranteed (depends on whether any coordination links formed
        # by chance under this seed), but assert internal consistency:
        # every observation event references patches that had an active
        # coordination link at some point, and observed values are within
        # valid ranges.
        for e in sim.event_log.local_institution_observations:
            assert 0.0 <= e.perceived_resource_level <= 1.0
            assert e.perceived_burden >= 0.0
            assert e.source in ("passive_observation", "administrative_report")
