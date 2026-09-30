"""Level 1.1, Work Package I: minimal interpatch coordination
(proposal, bilateral acceptance, activity, dissolution)."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog
from abm_governance.rules import coordination as rc
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


def _rule(rule_id, patch_id, members=(0, 1, 2), founder=None, fund=0.0):
    if founder is None:
        founder = members[0]
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    r = SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=founder, rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )
    r.fund = fund
    return r


def _two_patch_setup(**agent_overrides):
    """rule 0 at patch 0 (members 0,1), rule 1 at patch 1 (members 2,3)."""
    agents = {
        0: _agent(0, patch_id=0, **agent_overrides), 1: _agent(1, patch_id=0, **agent_overrides),
        2: _agent(2, patch_id=1, **agent_overrides), 3: _agent(3, patch_id=1, **agent_overrides),
    }
    registry = {0: _rule(0, patch_id=0, members=(0, 1)), 1: _rule(1, patch_id=1, members=(2, 3))}
    return agents, registry


class TestDisabledIsNoOp:
    def test_coordination_round_is_a_strict_noop_when_disabled(self):
        agents, registry = _two_patch_setup(interpatch_proposal_probability=1.0, interpatch_acceptance_propensity=1.0)
        link_registry: dict = {}
        pending: dict = {}
        config = SimulationConfig.level11_coordination_only(interpatch_coordination_enabled=False)
        rng = np.random.default_rng(0)
        log = EventLog()
        id_state = {"next_link_id": 0}
        rc.coordination_round(0, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert link_registry == {}
        assert pending == {}
        assert log.coordination_proposals == []


class TestProposalAndAcceptance:
    def test_certain_proposal_and_acceptance_creates_a_link(self):
        agents, registry = _two_patch_setup(interpatch_proposal_probability=1.0, interpatch_acceptance_propensity=1.0)
        link_registry: dict = {}
        pending: dict = {}
        config = SimulationConfig.level11_coordination_only(coordination_proposal_probability=1.0)
        rng = np.random.default_rng(1)
        log = EventLog()
        id_state = {"next_link_id": 0}
        # step 0: proposal created (nobody linked/pending yet)
        rc.coordination_round(0, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert len(log.coordination_proposals) == 1
        assert len(pending) == 1
        # step 1: pending proposal resolved -- acceptance propensity 1.0 => accepted
        rc.coordination_round(1, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert len(link_registry) == 1
        link = next(iter(link_registry.values()))
        assert link.active is True
        assert {link.patch_id_a, link.patch_id_b} == {0, 1}
        assert len(log.coordination_links) == 1
        assert log.coordination_links[0].accepted is True
        assert pending == {}

    def test_zero_acceptance_propensity_never_forms_a_link_after_window_expires(self):
        agents, registry = _two_patch_setup(interpatch_proposal_probability=1.0, interpatch_acceptance_propensity=0.0)
        link_registry: dict = {}
        pending: dict = {}
        config = SimulationConfig.level11_coordination_only(
            coordination_proposal_probability=1.0, coordination_proposal_window_steps=3,
        )
        rng = np.random.default_rng(2)
        log = EventLog()
        id_state = {"next_link_id": 0}
        for step in range(6):
            rc.coordination_round(step, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert link_registry == {}
        rejected = [e for e in log.coordination_links if e.accepted is False]
        assert rejected, "expected an explicit rejection event once the proposal window expired"
        assert rejected[0].reason == "window_expired"

    def test_no_proposal_with_a_single_active_rule(self):
        agents = {0: _agent(0, patch_id=0, interpatch_proposal_probability=1.0)}
        registry = {0: _rule(0, patch_id=0, members=(0,))}
        link_registry: dict = {}
        pending: dict = {}
        config = SimulationConfig.level11_coordination_only(coordination_proposal_probability=1.0)
        rng = np.random.default_rng(3)
        log = EventLog()
        id_state = {"next_link_id": 0}
        rc.coordination_round(0, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert log.coordination_proposals == []
        assert pending == {}

    def test_a_patch_already_linked_does_not_propose_again(self):
        agents, registry = _two_patch_setup(interpatch_proposal_probability=1.0, interpatch_acceptance_propensity=1.0)
        registry[2] = _rule(2, patch_id=2, members=(4,))
        agents[4] = _agent(4, patch_id=2, interpatch_proposal_probability=1.0, interpatch_acceptance_propensity=1.0)
        existing_link = rc.CoordinationLink(
            link_id=0, patch_id_a=0, patch_id_b=1, rule_id_a=0, rule_id_b=1, kind="information_exchange",
            proposed_step=0, accepted_step=0,
        )
        link_registry = {0: existing_link}
        pending: dict = {}
        config = SimulationConfig.level11_coordination_only(coordination_proposal_probability=1.0)
        rng = np.random.default_rng(4)
        log = EventLog()
        id_state = {"next_link_id": 1}
        rc.coordination_round(1, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        # patches 0 and 1 are already linked; only patch 2 is free, and it
        # has no eligible partner (0 and 1 are excluded) -- no new proposal.
        assert log.coordination_proposals == []


class TestActiveLinkOperation:
    def test_cost_is_deducted_from_both_funds_each_active_step(self):
        agents, registry = _two_patch_setup()
        registry[0].fund = 10.0
        registry[1].fund = 10.0
        link = rc.CoordinationLink(
            link_id=0, patch_id_a=0, patch_id_b=1, rule_id_a=0, rule_id_b=1, kind="information_exchange",
            proposed_step=0, accepted_step=0,
        )
        link_registry = {0: link}
        pending: dict = {}
        config = SimulationConfig.level11_coordination_only(
            coordination_cost_per_step=1.0, coordination_activity_probability=0.0,
            coordination_dissolution_probability=0.0, coordination_proposal_probability=0.0,
        )
        rng = np.random.default_rng(5)
        log = EventLog()
        id_state = {"next_link_id": 1}
        rc.coordination_round(1, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert registry[0].fund == pytest.approx(9.0)
        assert registry[1].fund == pytest.approx(9.0)
        assert link.total_cost == pytest.approx(2.0)

    def test_cost_never_drives_a_fund_negative(self):
        agents, registry = _two_patch_setup()
        registry[0].fund = 0.3
        registry[1].fund = 0.0
        link = rc.CoordinationLink(
            link_id=0, patch_id_a=0, patch_id_b=1, rule_id_a=0, rule_id_b=1, kind="information_exchange",
            proposed_step=0, accepted_step=0,
        )
        link_registry = {0: link}
        pending: dict = {}
        config = SimulationConfig.level11_coordination_only(
            coordination_cost_per_step=1.0, coordination_activity_probability=0.0,
            coordination_dissolution_probability=0.0, coordination_proposal_probability=0.0,
        )
        rng = np.random.default_rng(6)
        log = EventLog()
        id_state = {"next_link_id": 1}
        rc.coordination_round(1, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert registry[0].fund == pytest.approx(0.0)
        assert registry[1].fund == pytest.approx(0.0)

    def test_mutual_assistance_transfers_from_the_less_occupied_to_the_more_occupied(self):
        class _FakePatch:
            def __init__(self, fraction):
                self.fraction_of_capacity = fraction

        class _FakePatchSystem:
            def __init__(self, patches):
                self.patches = patches

        agents, registry = _two_patch_setup()
        registry[0].fund = 100.0
        registry[1].fund = 0.0
        link = rc.CoordinationLink(
            link_id=0, patch_id_a=0, patch_id_b=1, rule_id_a=0, rule_id_b=1, kind="mutual_assistance",
            proposed_step=0, accepted_step=0,
        )
        link_registry = {0: link}
        pending: dict = {}
        # patch 1 is nearly empty (low occupancy) -> patch 0's fund (which
        # is not the needy one) assists it, per the module's own rule:
        # transfer flows toward whichever side is *below* the threshold.
        patch_system = _FakePatchSystem({0: _FakePatch(1.0), 1: _FakePatch(0.0)})
        config = SimulationConfig.level11_coordination_only(
            coordination_cost_per_step=0.0, coordination_activity_probability=1.0,
            coordination_dissolution_probability=0.0, coordination_proposal_probability=0.0,
            coordination_assistance_occupancy_threshold=0.2, coordination_assistance_transfer_fraction=0.25,
        )
        rng = np.random.default_rng(7)
        log = EventLog()
        id_state = {"next_link_id": 1}
        rc.coordination_round(1, registry, agents, patch_system, link_registry, pending, config, rng, log, id_state)
        assert registry[1].fund == pytest.approx(25.0)
        assert registry[0].fund == pytest.approx(75.0)
        assert link.total_resource_transferred == pytest.approx(25.0)
        assert len(log.coordination_activity) == 1
        assert log.coordination_activity[0].resource_transferred == pytest.approx(25.0)

    def test_link_dissolves_when_either_rule_is_no_longer_active(self):
        agents, registry = _two_patch_setup()
        registry[1].active = False
        link = rc.CoordinationLink(
            link_id=0, patch_id_a=0, patch_id_b=1, rule_id_a=0, rule_id_b=1, kind="information_exchange",
            proposed_step=0, accepted_step=0,
        )
        link_registry = {0: link}
        pending: dict = {}
        config = SimulationConfig.level11_coordination_only(coordination_proposal_probability=0.0)
        rng = np.random.default_rng(8)
        log = EventLog()
        id_state = {"next_link_id": 1}
        rc.coordination_round(5, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert link.active is False
        assert link.dissolved is True
        assert link.dissolution_reason == "rule_dissolved_b"
        assert len(log.coordination_dissolutions) == 1
        assert log.coordination_dissolutions[0].duration_steps == 5

    def test_certain_dissolution_probability_ends_an_active_link(self):
        agents, registry = _two_patch_setup()
        link = rc.CoordinationLink(
            link_id=0, patch_id_a=0, patch_id_b=1, rule_id_a=0, rule_id_b=1, kind="information_exchange",
            proposed_step=0, accepted_step=0,
        )
        link_registry = {0: link}
        pending: dict = {}
        config = SimulationConfig.level11_coordination_only(
            coordination_dissolution_probability=1.0, coordination_activity_probability=0.0,
            coordination_proposal_probability=0.0,
        )
        rng = np.random.default_rng(9)
        log = EventLog()
        id_state = {"next_link_id": 1}
        rc.coordination_round(1, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert link.active is False
        assert link.dissolution_reason == "voluntary"


class TestEndToEndActivation:
    def test_coordination_mechanism_fires_in_a_full_run(self):
        config = SimulationConfig.level11_coordination_only(population_size=60, n_steps=300, n_patches=4, seed=9)
        sim = Simulation(config)
        sim.run()
        assert len(sim.event_log.coordination_proposals) > 0
        assert sim.coordination_link_registry or len(sim.event_log.coordination_links) > 0

    def test_no_interpatch_coordination_preset_never_produces_activity(self):
        config = SimulationConfig.level11_no_interpatch_coordination(population_size=40, n_steps=150, n_patches=3, seed=10)
        assert config.interpatch_coordination_enabled is False
        sim = Simulation(config)
        sim.run()
        assert sim.event_log.coordination_proposals == []
        assert sim.event_log.coordination_links == []
        assert sim.coordination_link_registry == {}

    def test_delegation_is_independent_of_coordination(self):
        # level11_coordination_only has delegation_enabled=False: no
        # delegate is ever appointed even though coordination is fully
        # active, demonstrating Work Package I's independence from D-G.
        config = SimulationConfig.level11_coordination_only(population_size=50, n_steps=250, n_patches=3, seed=11)
        assert config.delegation_enabled is False
        sim = Simulation(config)
        sim.run()
        assert sim.event_log.delegate_appointments == []
        assert sim.delegate_registry == {}
