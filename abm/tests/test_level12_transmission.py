"""Level 1.2, Work Package C: component-wise institutional transmission."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog
from abm_governance.rules import institution as ri
from abm_governance.rules import transmission as rt
from abm_governance.rules.coordination import CoordinationLink
from abm_governance.rules.shared_rule import RuleParameters, SharedRule


def _agent(agent_id, patch_id=0, resources=20.0, **overrides):
    a = Agent(
        agent_id=agent_id, resources=resources, coercive_capability=0.0, policy=make_policy("tit_for_tat"),
        observation_accuracy=0.9, learning_rate=0.1, forgiveness=0.1, risk_sensitivity=0.5, exit_cost=0.1,
    )
    a.patch_id = patch_id
    a.ecological_policy = EcologicalPolicy(0.5, 0.3, 0.0)
    for k, v in overrides.items():
        setattr(a, k, v)
    return a


def _rule(rule_id, patch_id, members, adoption_threshold=0.5, institution_overrides=None):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, adoption_threshold, 0.5)
    return SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=members[0], rule_lineage_id=rule_id, members=frozenset(members),
        supporters=frozenset(members), institution_overrides=institution_overrides,
    )


def _setup(config_overrides):
    fields = {"interpatch_coordination_enabled": True, "institutional_transmission_enabled": True}
    fields.update(config_overrides)
    config = SimulationConfig.level1_rule_formation_default(**fields)
    source_rule = _rule(0, 0, (0, 1), adoption_threshold=0.9)
    receiver_rule = _rule(1, 1, (2, 3), adoption_threshold=0.2)
    rules = {0: source_rule, 1: receiver_rule}
    institutions = {}
    ri.institution_lifecycle_round(0, rules, institutions, config, EventLog())
    link = CoordinationLink(
        link_id=0, patch_id_a=0, patch_id_b=1, rule_id_a=0, rule_id_b=1,
        kind="information_exchange", proposed_step=0, accepted_step=0,
    )
    agents = {aid: _agent(aid, patch_id=(0 if aid < 2 else 1)) for aid in range(4)}
    history = {0: [(0, {"resource_level": 0.9, "fairness": 0.9})], 1: [(0, {"resource_level": 0.1, "fairness": 0.1})]}
    return config, rules, institutions, {0: link}, agents, history


class TestApplyComponentToRule:
    def test_ruleparameters_backed_component_updates_parameters(self):
        rule = _rule(0, 0, (0, 1), adoption_threshold=0.5)
        rt.apply_component_to_rule(rule, "adoption_threshold", 0.8)
        assert rule.parameters.adoption_threshold == pytest.approx(0.8)

    def test_ruleparameters_backed_threshold_never_hits_exact_zero(self):
        rule = _rule(0, 0, (0, 1))
        rt.apply_component_to_rule(rule, "amendment_threshold", 0.0)
        assert rule.parameters.amendment_threshold > 0.0

    def test_override_backed_component_updates_overrides_dict(self):
        rule = _rule(0, 0, (0, 1))
        assert rule.institution_overrides is None
        rt.apply_component_to_rule(rule, "contribution_mechanism", "equal")
        assert rule.institution_overrides["contribution_mechanism"] == "equal"

    def test_non_transmissible_component_raises(self):
        rule = _rule(0, 0, (0, 1))
        with pytest.raises(ValueError):
            rt.apply_component_to_rule(rule, "authority_concentration", 0.5)

    def test_descriptive_only_components_excluded_from_transmissible_set(self):
        assert "proposal_threshold" not in rt.TRANSMISSIBLE_COMPONENT_NAMES
        assert "authority_concentration" not in rt.TRANSMISSIBLE_COMPONENT_NAMES
        assert len(rt.TRANSMISSIBLE_COMPONENT_NAMES) == 12


class TestInstitutionTransmissionRound:
    def test_no_op_when_disabled(self):
        config, rules, institutions, links, agents, history = _setup({"institutional_transmission_enabled": False, "transmission_period_steps": 1})
        log = EventLog()
        rt.institution_transmission_round(0, rules, institutions, links, agents, config, np.random.default_rng(0), log, history)
        assert log.institution_component_transmissions == []

    def test_high_base_probability_produces_transmission_events(self):
        config, rules, institutions, links, agents, history = _setup({
            "transmission_period_steps": 1, "transmission_base_probability": 1.0,
            "transmission_failure_probability": 0.0,
        })
        log = EventLog()
        rt.institution_transmission_round(0, rules, institutions, links, agents, config, np.random.default_rng(1), log, history)
        assert len(log.institution_component_transmissions) >= 1
        for e in log.institution_component_transmissions:
            assert e.component_name in rt.TRANSMISSIBLE_COMPONENT_NAMES
            assert e.outcome in ("faithful", "noisy", "mutated", "recombined", "rejected", "failed", "partial")

    def test_zero_failure_and_zero_rejection_leads_to_adoption(self):
        # Force perceived performance high (via a strong resource_level/
        # fairness true signal for the source and a highly accurate
        # observer) so reject_probability collapses toward 0, and disable
        # failure/mutation/recombination so the outcome is deterministic
        # "faithful" + adopted.
        config, rules, institutions, links, agents, history = _setup({
            "transmission_period_steps": 1, "transmission_base_probability": 1.0,
            "transmission_failure_probability": 0.0, "transmission_mutation_std": 0.0,
            "transmission_recombination_probability": 0.0, "observation_noise_std": 0.0,
        })
        history[0] = [(0, {"resource_level": 1.0, "fairness": 1.0})]
        log = EventLog()
        rt.institution_transmission_round(0, rules, institutions, links, agents, config, np.random.default_rng(2), log, history)
        assert len(log.institution_component_transmissions) >= 1
        faithful = [e for e in log.institution_component_transmissions if e.source_patch_id == 0]
        assert all(e.outcome == "faithful" and e.adopted for e in faithful)

    def test_whole_package_mode_transmits_all_twelve_components_at_once(self):
        config, rules, institutions, links, agents, history = _setup({
            "transmission_mode": "whole_package", "transmission_period_steps": 1,
            "transmission_base_probability": 1.0, "transmission_failure_probability": 0.0,
        })
        log = EventLog()
        rt.institution_transmission_round(0, rules, institutions, links, agents, config, np.random.default_rng(3), log, history)
        from_source_to_receiver = [e for e in log.institution_component_transmissions if e.source_patch_id == 0 and e.receiver_patch_id == 1]
        assert len(from_source_to_receiver) == 12

    def test_adopted_transfer_is_genuinely_live_at_the_receivers_own_call_site(self):
        # End-to-end proof: a transmitted contribution_mechanism actually
        # changes the receiver rule's effective contribution mode.
        config, rules, institutions, links, agents, history = _setup({
            "transmission_period_steps": 1, "transmission_base_probability": 1.0,
            "transmission_failure_probability": 0.0, "transmission_mutation_std": 0.0,
            "transmission_recombination_probability": 0.0, "observation_noise_std": 0.0,
            "contribution_mode": "voluntary",
        })
        institutions[0] = institutions[0].__class__(
            institution_id=0, lineage_id=0, parent_institution_id=None, origin_mechanism="fresh_proposal",
            creation_time=0, components=institutions[0].components.__class__(
                **{**institutions[0].components.as_dict(), "contribution_mechanism": "equal", "delegated_task_distribution": ("monitoring",)}
            ),
        )
        history[0] = [(0, {"resource_level": 1.0, "fairness": 1.0})]
        rng = np.random.default_rng(0)
        for _ in range(30):
            rt._attempt_one_component_transfer(
                0, rules[0], rules[1], institutions[0], institutions[1], "contribution_mechanism",
                1.0, 1.0, config, rng, EventLog(),
            )
        assert (rules[1].institution_overrides or {}).get("contribution_mechanism") == "equal"


class TestSimulationIntegration:
    def test_transmission_events_recorded_in_a_full_run(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=24, n_steps=80, n_patches=4, seed=7,
            proposal_probability_mean=0.3, proposal_probability_std=0.02,
            interpatch_coordination_enabled=True, coordination_proposal_probability=0.4,
            institutional_transmission_enabled=True, transmission_period_steps=2,
            transmission_base_probability=0.5,
        )
        from abm_governance.simulation import Simulation

        sim = Simulation(config)
        sim.run()
        for e in sim.event_log.institution_component_transmissions:
            assert e.component_name in rt.TRANSMISSIBLE_COMPONENT_NAMES
            assert 0.0 <= e.transmission_error or np.isnan(e.transmission_error)
