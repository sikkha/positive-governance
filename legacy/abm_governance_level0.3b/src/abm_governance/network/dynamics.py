"""Active, endogenous relationship dynamics (Level 0.1, Work Package B).

Distinct from ``network/graph.py``, which is kept unmodified as the
Level-0 *compatibility-mode* implementation (used when
``relationship_dynamics_enabled=False``). The milestone brief found the
original ``rewire()`` operation's semantics ambiguous — it only ever adds
an edge, never removes or replaces one — so this module defines a
separate, explicitly-typed family of operations: voluntary exit (with an
explicit failed-exit case for an agent that cannot afford ``exit_cost``),
and connection *proposals* that a target can accept or reject, rather than
a proposer unilaterally wiring itself to a random stranger.

No global optimization is used anywhere in this module. Every decision
(exit, accept/reject) is a function of information locally available to
one agent: its own resources, its own EWMA estimate of a specific
partner's payoff, or (for the target of a proposal) its own current
degree. Nothing here inspects population-wide state to decide what would
be "best" for the system.
"""

from __future__ import annotations

import numpy as np

from abm_governance.agents.agent import Agent
from abm_governance.core.events import (
    ConnectionProposalEvent,
    EdgeAddedEvent,
    EdgeRemovedEvent,
    FailedExitEvent,
)


def wants_to_exit(agent: Agent, partner_id: int, exit_resource_threshold: float) -> bool:
    """An agent wants to end a relationship when its own EWMA estimate of
    the payoff it gets from that specific partner (a blend of remembered
    treatment and expected future payoff — see agents/agent.py) has fallen
    below ``exit_resource_threshold``. This is the same criterion the
    Level-0 compatibility mode uses; Level 0.1 adds the affordability
    check below rather than changing the *decision* to exit."""
    return agent.partner_payoff_estimate.get(partner_id, 0.0) < exit_resource_threshold


def attempt_exit(
    graph,
    agents_by_id: dict[int, Agent],
    initiator_id: int,
    partner_id: int,
    exit_cost: float,
    step: int,
):
    """Try to end the relationship between ``initiator_id`` and
    ``partner_id``. Returns an :class:`EdgeRemovedEvent` on success or a
    :class:`FailedExitEvent` if the initiator cannot afford ``exit_cost``
    (the edge is left intact in that case — this is the "resource
    condition" gate on exit the milestone brief asked for)."""
    agent = agents_by_id[initiator_id]
    if agent.resources < exit_cost:
        return FailedExitEvent(step=step, agent=initiator_id, partner=partner_id)

    graph.remove_edge(initiator_id, partner_id)
    agent.resources -= exit_cost
    agent.forget_partner(partner_id)
    agents_by_id[partner_id].forget_partner(initiator_id)
    return EdgeRemovedEvent(step=step, initiator=initiator_id, partner=partner_id, exit_cost=exit_cost)


def decide_connection_acceptance(
    target_degree: int,
    mean_degree: int,
    base_prob: float,
    rng: np.random.Generator,
) -> bool:
    """A target accepts a connection proposal with probability
    ``base_prob``, discounted as its own current degree already exceeds
    ``mean_degree`` (a saturating, purely local heuristic — an
    already well-connected agent is less inclined to add yet another
    relationship). Never inspects the proposer's identity or any
    population-wide quantity."""
    if mean_degree <= 0:
        saturation = 0.0
    else:
        saturation = max(0.0, (target_degree / mean_degree) - 1.0)
    adjusted_prob = min(1.0, max(0.0, base_prob / (1.0 + saturation)))
    return bool(rng.random() < adjusted_prob)


def attempt_connection(
    graph,
    proposer_id: int,
    rng: np.random.Generator,
    step: int,
    base_accept_prob: float,
    mean_degree: int,
):
    """One connection-seeking attempt by ``proposer_id``: pick a
    uniformly-random non-neighbour as a candidate target, and have the
    target accept or reject per :func:`decide_connection_acceptance`.

    Returns ``(ConnectionProposalEvent, EdgeAddedEvent | None)``; the
    second element is non-``None`` exactly when the proposal was
    accepted. ``reason='no_candidate'`` (target is ``None``) means the
    proposer has no eligible non-neighbour at all — it is already
    connected to everyone else in the population.
    """
    n = graph.number_of_nodes()
    candidates = [x for x in range(n) if x != proposer_id and not graph.has_edge(proposer_id, x)]
    if not candidates:
        return ConnectionProposalEvent(step=step, proposer=proposer_id, target=None, accepted=False, reason="no_candidate"), None

    target_id = int(candidates[int(rng.integers(0, len(candidates)))])
    target_degree = graph.degree(target_id)
    accepted = decide_connection_acceptance(target_degree, mean_degree, base_accept_prob, rng)

    if accepted:
        graph.add_edge(proposer_id, target_id)
        proposal = ConnectionProposalEvent(step=step, proposer=proposer_id, target=target_id, accepted=True, reason="accepted")
        edge_event = EdgeAddedEvent(step=step, agent_a=proposer_id, agent_b=target_id, cause="reconnect")
        return proposal, edge_event

    proposal = ConnectionProposalEvent(step=step, proposer=proposer_id, target=target_id, accepted=False, reason="rejected")
    return proposal, None
