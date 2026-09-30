"""Work Package B: network-structure diagnostics (isolation, components,
degree/age distributions, turnover rate, assortativity)."""

from __future__ import annotations

import math

import networkx as nx
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.policy import make_policy
from abm_governance.core.events import EdgeAddedEvent, EdgeRemovedEvent, EventLog, ExitEvent, RewireEvent
from abm_governance.observer.network_diagnostics import (
    component_stats,
    degree_distribution_summary,
    isolated_agent_count,
    policy_assortativity,
    relationship_age_distribution,
    relationship_turnover_rate,
)


def make_agent(agent_id: int, policy_name: str = "tit_for_tat") -> Agent:
    return Agent(
        agent_id=agent_id,
        resources=10.0,
        coercive_capability=1.0,
        policy=make_policy(policy_name),
        observation_accuracy=0.9,
        learning_rate=0.1,
        forgiveness=0.1,
        risk_sensitivity=0.5,
        exit_cost=1.0,
        memory_length=5,
    )


def test_isolated_agent_count():
    graph = nx.Graph()
    graph.add_nodes_from(range(5))
    graph.add_edge(0, 1)
    assert isolated_agent_count(graph) == 3  # 2, 3, 4 isolated


def test_component_stats_single_component():
    graph = nx.path_graph(5)
    stats = component_stats(graph)
    assert stats["component_count"] == 1
    assert stats["largest_component_share"] == pytest.approx(1.0)


def test_component_stats_fragmented():
    graph = nx.Graph()
    graph.add_nodes_from(range(6))
    graph.add_edge(0, 1)
    graph.add_edge(2, 3)
    # 4, 5 isolated -> components: {0,1}, {2,3}, {4}, {5} = 4 components, largest size 2/6
    stats = component_stats(graph)
    assert stats["component_count"] == 4
    assert stats["largest_component_share"] == pytest.approx(2 / 6)


def test_degree_distribution_summary_hand_computed():
    graph = nx.Graph()
    graph.add_nodes_from(range(4))
    graph.add_edge(0, 1)
    graph.add_edge(0, 2)
    graph.add_edge(0, 3)
    # degrees: 0->3, 1->1, 2->1, 3->1
    stats = degree_distribution_summary(graph)
    assert stats["degree_mean"] == pytest.approx(1.5)
    assert stats["degree_min"] == 1
    assert stats["degree_max"] == 3


def test_degree_distribution_summary_empty_graph():
    graph = nx.Graph()
    stats = degree_distribution_summary(graph)
    assert stats["degree_mean"] == 0.0


def test_relationship_age_distribution_uses_earliest_known_start():
    graph = nx.Graph()
    graph.add_nodes_from([0, 1])
    graph.add_edge(0, 1)
    a0, a1 = make_agent(0), make_agent(1)
    a0.ensure_partner(1, step=2)
    a1.ensure_partner(0, step=2)
    stats = relationship_age_distribution({0: a0, 1: a1}, graph, step=10)
    assert stats["age_mean"] == pytest.approx(8.0)


def test_relationship_turnover_rate_counts_both_event_families():
    log = EventLog()
    log.add(EdgeAddedEvent(step=1, agent_a=0, agent_b=1, cause="reconnect"))
    log.add(EdgeRemovedEvent(step=2, initiator=2, partner=3, exit_cost=1.0))
    log.add(RewireEvent(step=3, agent=4, new_partner=5))
    log.add(RewireEvent(step=3, agent=6, new_partner=None))  # failed: must not count
    log.add(ExitEvent(step=4, agent=7, former_partner=8, exit_cost=1.0))

    rate = relationship_turnover_rate(log, start_step=0, end_step=5)
    # additions: 1 (EdgeAdded) + 1 (successful Rewire) = 2
    # removals: 1 (EdgeRemoved) + 1 (Exit) = 2
    # total 4 events over 5 steps
    assert rate == pytest.approx(4 / 5)


def test_relationship_turnover_rate_zero_when_no_events():
    log = EventLog()
    assert relationship_turnover_rate(log, start_step=0, end_step=10) == 0.0


def test_policy_assortativity_nan_for_sparse_or_uniform_graphs():
    graph = nx.Graph()
    graph.add_nodes_from([0, 1])
    graph.add_edge(0, 1)
    agents = [make_agent(0, "tit_for_tat"), make_agent(1, "tit_for_tat")]
    # only one edge -> undefined per this module's convention
    assert math.isnan(policy_assortativity(graph, agents))

    # uniform policy across many edges -> also undefined (no variance)
    graph2 = nx.path_graph(5)
    agents2 = [make_agent(i, "tit_for_tat") for i in range(5)]
    assert math.isnan(policy_assortativity(graph2, agents2))


def test_policy_assortativity_perfectly_assortative_graph():
    # Two disjoint-by-policy triangles connected by nothing: within-group
    # edges only -> perfect assortativity by policy (+1.0).
    graph = nx.Graph()
    graph.add_edges_from([(0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5)])
    agents = [make_agent(i, "always_cooperate") for i in (0, 1, 2)] + [
        make_agent(i, "always_defect") for i in (3, 4, 5)
    ]
    value = policy_assortativity(graph, agents)
    assert value == pytest.approx(1.0, abs=1e-6)
