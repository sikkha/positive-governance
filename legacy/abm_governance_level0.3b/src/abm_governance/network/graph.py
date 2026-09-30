"""Dynamic interaction network.

Builds the initial relationship graph and implements costly exit and
rewiring. All randomness here is drawn from the single injected RNG — this
module never calls NetworkX's own random generators (which would seed
independently of the simulation's RNG stream and silently break
reproducibility).
"""

from __future__ import annotations

import networkx as nx
import numpy as np

from abm_governance.agents.agent import Agent
from abm_governance.core.events import ExitEvent, RewireEvent


def build_network(
    n_agents: int,
    topology: str,
    mean_degree: int,
    rewiring_prob: float,
    rng: np.random.Generator,
) -> nx.Graph:
    """Construct the initial relationship graph.

    ``topology`` is one of ``"erdos_renyi"``, ``"watts_strogatz"``,
    ``"regular"``. Degree is only approximately ``mean_degree`` for
    ``erdos_renyi`` (it is a target expectation, not a guarantee).
    """
    graph = nx.Graph()
    graph.add_nodes_from(range(n_agents))

    if topology == "erdos_renyi":
        p = min(1.0, mean_degree / max(1, n_agents - 1))
        for i in range(n_agents):
            for j in range(i + 1, n_agents):
                if rng.random() < p:
                    graph.add_edge(i, j)
        return graph

    k = mean_degree - (mean_degree % 2)  # force even, classic ring-lattice requirement
    k = max(2, k)
    for i in range(n_agents):
        for offset in range(1, k // 2 + 1):
            graph.add_edge(i, (i + offset) % n_agents)

    if topology == "regular":
        return graph

    if topology == "watts_strogatz":
        for i in range(n_agents):
            for offset in range(1, k // 2 + 1):
                neighbor = (i + offset) % n_agents
                if not graph.has_edge(i, neighbor):
                    continue  # already rewired away earlier in the loop
                if rng.random() < rewiring_prob:
                    non_neighbors = [
                        x for x in range(n_agents) if x != i and not graph.has_edge(i, x)
                    ]
                    if not non_neighbors:
                        continue
                    new_neighbor = int(non_neighbors[int(rng.integers(0, len(non_neighbors)))])
                    graph.remove_edge(i, neighbor)
                    graph.add_edge(i, new_neighbor)
        return graph

    raise ValueError(f"Unknown topology {topology!r}")


def exit_relationship(
    graph: nx.Graph,
    agents_by_id: dict[int, Agent],
    initiator_id: int,
    partner_id: int,
    exit_cost: float,
    step: int,
) -> ExitEvent:
    """The initiator unilaterally exits the relationship with ``partner_id``,
    paying ``exit_cost`` out of their own resources. Both sides forget their
    direct memory of one another (Level 0 has no persistent reputation
    beyond an active relationship; that arrives at Level 1)."""
    if not graph.has_edge(initiator_id, partner_id):
        raise ValueError(f"No edge between {initiator_id} and {partner_id} to exit")
    graph.remove_edge(initiator_id, partner_id)
    agents_by_id[initiator_id].resources -= exit_cost
    agents_by_id[initiator_id].forget_partner(partner_id)
    agents_by_id[partner_id].forget_partner(initiator_id)
    return ExitEvent(step=step, agent=initiator_id, former_partner=partner_id, exit_cost=exit_cost)


def rewire(
    graph: nx.Graph,
    agent_id: int,
    rng: np.random.Generator,
    step: int,
) -> RewireEvent:
    """Attempt to form one new relationship for ``agent_id`` with a
    uniformly-random non-neighbour. Returns a :class:`RewireEvent` with
    ``new_partner=None`` if no eligible candidate exists (e.g. the agent is
    already connected to everyone else)."""
    n = graph.number_of_nodes()
    candidates = [
        x for x in range(n) if x != agent_id and not graph.has_edge(agent_id, x)
    ]
    if not candidates:
        return RewireEvent(step=step, agent=agent_id, new_partner=None)
    new_partner = int(candidates[int(rng.integers(0, len(candidates)))])
    graph.add_edge(agent_id, new_partner)
    return RewireEvent(step=step, agent=agent_id, new_partner=new_partner)
