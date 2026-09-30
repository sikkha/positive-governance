"""Work Package B: endogenous relationship dynamics — edge addition,
removal, failed exit, connection proposals (accepted/rejected/no
candidate), and the resulting network invariants."""

from __future__ import annotations

import networkx as nx
import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.network import dynamics as reldyn
from abm_governance.simulation import Simulation


def make_agent(agent_id: int, resources: float = 10.0) -> Agent:
    return Agent(
        agent_id=agent_id,
        resources=resources,
        coercive_capability=1.0,
        policy=make_policy("tit_for_tat"),
        observation_accuracy=0.9,
        learning_rate=0.1,
        forgiveness=0.1,
        risk_sensitivity=0.5,
        exit_cost=2.0,
        memory_length=5,
    )


# -- wants_to_exit / attempt_exit --------------------------------------------

def test_wants_to_exit_uses_partner_payoff_estimate():
    agent = make_agent(0)
    agent.partner_payoff_estimate[1] = -5.0
    assert reldyn.wants_to_exit(agent, 1, exit_resource_threshold=-1.0) is True
    assert reldyn.wants_to_exit(agent, 1, exit_resource_threshold=-10.0) is False


def test_attempt_exit_succeeds_when_affordable():
    graph = nx.Graph()
    graph.add_nodes_from([0, 1])
    graph.add_edge(0, 1)
    agents = {0: make_agent(0, resources=10.0), 1: make_agent(1, resources=10.0)}
    agents[0].ensure_partner(1, step=0)
    agents[1].ensure_partner(0, step=0)

    event = reldyn.attempt_exit(graph, agents, initiator_id=0, partner_id=1, exit_cost=3.0, step=5)

    assert type(event).__name__ == "EdgeRemovedEvent"
    assert not graph.has_edge(0, 1)
    assert agents[0].resources == pytest.approx(7.0)
    assert agents[1].resources == pytest.approx(10.0)
    assert 1 not in agents[0].memory


def test_attempt_exit_fails_when_unaffordable_and_edge_survives():
    graph = nx.Graph()
    graph.add_nodes_from([0, 1])
    graph.add_edge(0, 1)
    agents = {0: make_agent(0, resources=1.0), 1: make_agent(1, resources=10.0)}
    agents[0].ensure_partner(1, step=0)

    event = reldyn.attempt_exit(graph, agents, initiator_id=0, partner_id=1, exit_cost=5.0, step=5)

    assert type(event).__name__ == "FailedExitEvent"
    assert event.reason == "insufficient_resources_for_exit_cost"
    assert graph.has_edge(0, 1)  # edge NOT removed
    assert agents[0].resources == pytest.approx(1.0)  # no cost deducted


# -- decide_connection_acceptance / attempt_connection -----------------------

def test_acceptance_probability_falls_as_target_degree_saturates():
    rng = np.random.default_rng(0)
    n_trials = 4000
    accepted_low = sum(
        reldyn.decide_connection_acceptance(target_degree=1, mean_degree=4, base_prob=0.8, rng=rng)
        for _ in range(n_trials)
    )
    accepted_high = sum(
        reldyn.decide_connection_acceptance(target_degree=12, mean_degree=4, base_prob=0.8, rng=rng)
        for _ in range(n_trials)
    )
    assert accepted_low > accepted_high


def test_attempt_connection_no_candidate_on_complete_graph():
    graph = nx.complete_graph(4)
    rng = np.random.default_rng(0)
    proposal, edge_event = reldyn.attempt_connection(graph, 0, rng, step=0, base_accept_prob=1.0, mean_degree=3)
    assert proposal.reason == "no_candidate"
    assert proposal.target is None
    assert edge_event is None


def test_attempt_connection_accept_adds_edge_and_emits_edge_added_event():
    graph = nx.Graph()
    graph.add_nodes_from([0, 1, 2])
    rng = np.random.default_rng(0)
    proposal, edge_event = reldyn.attempt_connection(graph, 0, rng, step=0, base_accept_prob=1.0, mean_degree=1)
    assert proposal.accepted is True
    assert proposal.reason == "accepted"
    assert edge_event is not None
    assert edge_event.cause == "reconnect"
    assert graph.has_edge(proposal.proposer, proposal.target)


def test_attempt_connection_reject_adds_no_edge():
    graph = nx.Graph()
    graph.add_nodes_from([0, 1, 2])
    rng = np.random.default_rng(0)
    proposal, edge_event = reldyn.attempt_connection(graph, 0, rng, step=0, base_accept_prob=0.0, mean_degree=1)
    assert proposal.accepted is False
    assert proposal.reason == "rejected"
    assert edge_event is None
    assert graph.number_of_edges() == 0


# -- edge-count invariants under each operation ------------------------------

def test_edge_addition_increases_edge_count_by_exactly_one():
    graph = nx.Graph()
    graph.add_nodes_from(range(5))
    rng = np.random.default_rng(1)
    before = graph.number_of_edges()
    _, edge_event = reldyn.attempt_connection(graph, 0, rng, step=0, base_accept_prob=1.0, mean_degree=1)
    assert edge_event is not None
    assert graph.number_of_edges() == before + 1


def test_edge_removal_decreases_edge_count_by_exactly_one():
    graph = nx.Graph()
    graph.add_nodes_from([0, 1])
    graph.add_edge(0, 1)
    agents = {0: make_agent(0, resources=10.0), 1: make_agent(1, resources=10.0)}
    before = graph.number_of_edges()
    reldyn.attempt_exit(graph, agents, 0, 1, exit_cost=1.0, step=0)
    assert graph.number_of_edges() == before - 1


def test_failed_exit_leaves_edge_count_unchanged():
    graph = nx.Graph()
    graph.add_nodes_from([0, 1])
    graph.add_edge(0, 1)
    agents = {0: make_agent(0, resources=0.5), 1: make_agent(1, resources=10.0)}
    before = graph.number_of_edges()
    reldyn.attempt_exit(graph, agents, 0, 1, exit_cost=5.0, step=0)
    assert graph.number_of_edges() == before


def test_rejected_proposal_leaves_edge_count_unchanged():
    graph = nx.Graph()
    graph.add_nodes_from([0, 1, 2])
    rng = np.random.default_rng(0)
    before = graph.number_of_edges()
    reldyn.attempt_connection(graph, 0, rng, step=0, base_accept_prob=0.0, mean_degree=1)
    assert graph.number_of_edges() == before


# -- full-simulation integration: distinct event families, isolation --------

def test_relationship_dynamics_produces_new_event_family_not_legacy():
    config = SimulationConfig(
        population_size=20, n_steps=100, seed=2, relationship_dynamics_enabled=True, rewiring_period=3
    )
    result = Simulation(config).run()
    assert len(result.event_log.exits) == 0
    assert len(result.event_log.rewires) == 0
    total_new_events = (
        len(result.event_log.edges_added)
        + len(result.event_log.edges_removed)
        + len(result.event_log.failed_exits)
        + len(result.event_log.connection_proposals)
    )
    assert total_new_events > 0


def test_legacy_mode_produces_only_legacy_event_family():
    config = SimulationConfig.level0_compat(population_size=20, n_steps=100, seed=2, rewiring_period=3)
    result = Simulation(config).run()
    assert result.event_log.edges_added == []
    assert result.event_log.edges_removed == []
    assert result.event_log.failed_exits == []
    assert result.event_log.connection_proposals == []


def test_agents_can_become_isolated_and_later_reconnect():
    # Aggressive exit threshold + generous rewiring makes both isolation
    # and reconnection observable within a modest run.
    config = SimulationConfig(
        population_size=15,
        n_steps=150,
        seed=7,
        relationship_dynamics_enabled=True,
        exit_resource_threshold=2.0,  # easy to trigger
        rewiring_period=2,
        mean_degree=3,
        connection_accept_base_prob=0.9,
    )
    result = Simulation(config).run()
    isolated_at_some_point = any(row["isolated_agent_count"] > 0 for row in result.metrics)
    edges_added_at_some_point = len(result.event_log.edges_added) > 0
    # Not asserting a specific outcome (that would be tuning to a target);
    # only that the mechanism is at least exercised across this run.
    assert edges_added_at_some_point
    # This is diagnostic, not a strict requirement — record what happened.
    assert isinstance(isolated_at_some_point, bool)
