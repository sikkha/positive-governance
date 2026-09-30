"""Network construction, exit, and rewiring correctness."""

from __future__ import annotations

import networkx as nx
import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.policy import make_policy
from abm_governance.network.graph import build_network, exit_relationship, rewire


def make_agent(agent_id: int) -> Agent:
    return Agent(
        agent_id=agent_id,
        resources=10.0,
        coercive_capability=1.0,
        policy=make_policy("tit_for_tat"),
        observation_accuracy=0.9,
        learning_rate=0.1,
        forgiveness=0.1,
        risk_sensitivity=0.5,
        exit_cost=2.0,
        memory_length=5,
    )


@pytest.mark.parametrize("topology", ["erdos_renyi", "watts_strogatz", "regular"])
def test_build_network_no_self_loops_or_duplicate_edges(topology):
    rng = np.random.default_rng(0)
    graph = build_network(30, topology, mean_degree=4, rewiring_prob=0.2, rng=rng)
    assert graph.number_of_nodes() == 30
    assert nx.number_of_selfloops(graph) == 0
    # networkx.Graph structurally forbids duplicate (parallel) edges;
    # this assertion documents that invariant explicitly for this codebase.
    assert not graph.is_multigraph()


def test_build_network_is_deterministic_given_seed():
    rng_a = np.random.default_rng(5)
    rng_b = np.random.default_rng(5)
    graph_a = build_network(20, "watts_strogatz", mean_degree=4, rewiring_prob=0.3, rng=rng_a)
    graph_b = build_network(20, "watts_strogatz", mean_degree=4, rewiring_prob=0.3, rng=rng_b)
    assert set(graph_a.edges()) == set(graph_b.edges())


def test_build_network_rejects_unknown_topology():
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        build_network(10, "made_up", mean_degree=2, rewiring_prob=0.1, rng=rng)


def test_exit_removes_edge_and_deducts_exact_cost():
    graph = nx.Graph()
    graph.add_nodes_from([0, 1])
    graph.add_edge(0, 1)
    agents = {0: make_agent(0), 1: make_agent(1)}
    agents[0].ensure_partner(1, step=0)
    agents[1].ensure_partner(0, step=0)

    initial_resources = agents[0].resources
    event = exit_relationship(graph, agents, initiator_id=0, partner_id=1, exit_cost=3.0, step=5)

    assert not graph.has_edge(0, 1)
    assert agents[0].resources == pytest.approx(initial_resources - 3.0)
    assert agents[1].resources == pytest.approx(10.0)  # partner pays nothing
    assert event.exit_cost == 3.0
    assert event.agent == 0
    assert event.former_partner == 1
    assert 1 not in agents[0].memory
    assert 0 not in agents[1].memory


def test_exit_raises_if_no_edge_exists():
    graph = nx.Graph()
    graph.add_nodes_from([0, 1])
    agents = {0: make_agent(0), 1: make_agent(1)}
    with pytest.raises(ValueError):
        exit_relationship(graph, agents, initiator_id=0, partner_id=1, exit_cost=1.0, step=0)


def test_rewire_restores_degree_when_partner_available():
    graph = nx.Graph()
    graph.add_nodes_from(range(4))
    graph.add_edge(0, 1)  # agent 0 has degree 1; agents 2, 3 are eligible new partners
    rng = np.random.default_rng(0)
    event = rewire(graph, agent_id=0, rng=rng, step=0)
    assert event.new_partner in (2, 3)
    assert graph.has_edge(0, event.new_partner)
    assert graph.degree(0) == 2


def test_rewire_returns_none_when_fully_connected():
    graph = nx.complete_graph(4)
    rng = np.random.default_rng(0)
    event = rewire(graph, agent_id=0, rng=rng, step=0)
    assert event.new_partner is None
    assert graph.degree(0) == 3  # unchanged


def test_rewire_never_creates_self_loop_or_duplicate_edge():
    rng = np.random.default_rng(1)
    graph = build_network(10, "erdos_renyi", mean_degree=3, rewiring_prob=0.1, rng=rng)
    for _ in range(50):
        for node in list(graph.nodes()):
            rewire(graph, agent_id=node, rng=rng, step=0)
    assert nx.number_of_selfloops(graph) == 0
