"""Observer-layer metric correctness, including a regression test for a
falsy-zero bug in relationship-age computation (step 0 is a valid start
step but is falsy in Python)."""

from __future__ import annotations

import networkx as nx
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.policy import make_policy
from abm_governance.core.events import EventLog
from abm_governance.observer.metrics import compute_step_metrics, gini, shannon_entropy


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
        exit_cost=1.0,
        memory_length=5,
    )


def test_gini_perfect_equality_is_zero():
    assert gini([5.0, 5.0, 5.0, 5.0]) == pytest.approx(0.0)


def test_gini_empty_or_all_zero_is_zero():
    assert gini([]) == 0.0
    assert gini([0.0, 0.0, 0.0]) == 0.0


def test_gini_known_case():
    # Hand-verified: one agent has everything, rest have nothing.
    values = [0.0, 0.0, 0.0, 10.0]
    g = gini(values)
    assert g == pytest.approx(0.75, abs=1e-6)


def test_shannon_entropy_single_category_is_zero():
    assert shannon_entropy(["a", "a", "a"]) == 0.0


def test_shannon_entropy_two_equal_categories_is_one_bit():
    assert shannon_entropy(["a", "b", "a", "b"]) == pytest.approx(1.0)


def test_relationship_age_counts_edges_started_at_step_zero():
    """Regression test: relationship_started_at == 0 must not be treated as
    'unknown' just because 0 is falsy."""
    graph = nx.Graph()
    graph.add_nodes_from([0, 1])
    graph.add_edge(0, 1)
    a0, a1 = make_agent(0), make_agent(1)
    a0.ensure_partner(1, step=0)
    a1.ensure_partner(0, step=0)

    metrics = compute_step_metrics([a0, a1], graph, EventLog(), step=5)
    assert metrics["mean_relationship_age"] == pytest.approx(5.0)
