"""Strategy adaptation: imitation and low-rate mutation/experimentation.

These run on their own timescale (see ``core/scheduler.py``), decoupled
from the per-tick action loop. Fitness is never a governance-level score;
as of Level 0.2 (Work Package C) it is one of several configurable,
equally-unprivileged signals derived purely from an agent's own economic
history — see ``agents/fitness.py``.
"""

from __future__ import annotations

from typing import Iterator, Sequence

import numpy as np

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy, mutate_ecological_policy
from abm_governance.agents.fitness import fitness_signal
from abm_governance.agents.policy import VALID_POLICY_NAMES, make_policy
from abm_governance.core.events import (
    EcologicalImitationEvent,
    EcologicalMutationEvent,
    ImitationEvent,
    MutationEvent,
)


def _stable_sigmoid(x: float) -> float:
    """Numerically stable logistic sigmoid (avoids overflow warnings from
    ``exp`` for large |x|; mathematically identical to 1 / (1 + exp(-x))."""
    if x >= 0:
        z = np.exp(-x)
        return 1.0 / (1.0 + z)
    z = np.exp(x)
    return z / (1.0 + z)


def imitation_round(
    agents: Sequence[Agent],
    rng: np.random.Generator,
    step: int,
    beta: float = 0.5,
    fitness_mode: str = "cumulative_resources",
    viability_adjusted_dormant_penalty: float = 0.0,
) -> list[ImitationEvent]:
    """One synchronous imitation round.

    Each living agent samples one other living agent uniformly at random
    and adopts that peer's policy with the Fermi-rule probability::

        p = 1 / (1 + exp(-beta * (peer_fitness - own_fitness)))

    so imitation is more likely (but never certain, and never impossible)
    the larger the fitness gap. ``fitness_mode`` selects which signal
    ``peer_fitness``/``own_fitness`` are (see ``agents/fitness.py`` —
    ``"cumulative_resources"`` reproduces the exact Level-0.1 rule).
    """
    events: list[ImitationEvent] = []
    living = [a for a in agents if a.alive]
    if len(living) < 2:
        return events

    ids = np.array([a.agent_id for a in living])
    for agent in living:
        candidates = ids[ids != agent.agent_id]
        if len(candidates) == 0:
            continue
        peer_id = int(rng.choice(candidates))
        peer = next(a for a in living if a.agent_id == peer_id)
        if peer.policy.name == agent.policy.name:
            continue
        own_fitness = fitness_signal(agent, fitness_mode, viability_adjusted_dormant_penalty)
        peer_fitness = fitness_signal(peer, fitness_mode, viability_adjusted_dormant_penalty)
        gap = peer_fitness - own_fitness
        p_imitate = _stable_sigmoid(beta * gap)
        if rng.random() < p_imitate:
            old_name = agent.policy.name
            agent.policy = make_policy(peer.policy.name)
            # Cultural-lineage propagation (Level 0.1, Work Package D): the
            # imitator's strategy now traces back to the model agent's
            # lineage. This is bookkeeping only — it never affects
            # resources, actions, or any RNG draw.
            agent.policy_lineage_id = peer.policy_lineage_id
            events.append(
                ImitationEvent(
                    step=step,
                    agent=agent.agent_id,
                    old_policy=old_name,
                    new_policy=agent.policy.name,
                    model_agent=peer.agent_id,
                    agent_fitness=own_fitness,
                    model_fitness=peer_fitness,
                    fitness_gap=gap,
                    fitness_mode=fitness_mode,
                    agent_viability_state=agent.viability_state,
                    model_viability_state=peer.viability_state,
                    resulting_lineage_id=agent.policy_lineage_id,
                )
            )
    return events


def mutation_round(
    agents: Sequence[Agent],
    mutation_rate: float,
    rng: np.random.Generator,
    step: int,
    lineage_counter: Iterator[int] | None = None,
) -> list[MutationEvent]:
    """Each living agent independently mutates to a uniformly random policy
    (possibly its own current one, by chance) with probability
    ``mutation_rate``. This is the sole source of behavioural
    experimentation/novelty in Level 0.

    ``lineage_counter`` (Level 0.1, Work Package D) yields fresh,
    never-before-used lineage ids for mutated agents — a mutation is
    treated as originating a *new* strategy variant, distinct from
    imitation's propagation of an existing lineage. If ``None``, lineage
    ids are left untouched (used by call sites that don't care about
    lineage bookkeeping, e.g. isolated unit tests).
    """
    events: list[MutationEvent] = []
    for agent in agents:
        if not agent.alive:
            continue
        if rng.random() < mutation_rate:
            old_name = agent.policy.name
            new_name = VALID_POLICY_NAMES[int(rng.integers(0, len(VALID_POLICY_NAMES)))]
            agent.policy = make_policy(new_name)
            if lineage_counter is not None:
                agent.policy_lineage_id = next(lineage_counter)
            events.append(
                MutationEvent(step=step, agent=agent.agent_id, old_policy=old_name, new_policy=new_name)
            )
    return events


# ---------------------------------------------------------------------
# Level 0.3, Work Package D: ecological-policy imitation/mutation.
# ---------------------------------------------------------------------

def ecological_imitation_round(
    agents: Sequence[Agent],
    rng: np.random.Generator,
    step: int,
    beta: float = 0.5,
    fitness_mode: str = "cumulative_resources",
    viability_adjusted_dormant_penalty: float = 0.0,
) -> list[EcologicalImitationEvent]:
    """Ecological-policy analog of :func:`imitation_round`: each living
    agent independently samples one peer *for this dimension* (its own
    draw, potentially different from whatever peer a concurrent
    :func:`imitation_round` call sampled for the social dimension — this
    is what makes ``config.ecological_inheritance_mode="independent"``
    satisfy the milestone's "both copied independently from potentially
    different model agents" requirement) and adopts that peer's
    *ecological* policy (all three traits at once, as a single copied
    vector — traits are not imitated individually) with the same
    Fermi-rule probability, computed from ``stream="ecological"``
    fitness."""
    events: list[EcologicalImitationEvent] = []
    living = [a for a in agents if a.alive]
    if len(living) < 2:
        return events

    ids = np.array([a.agent_id for a in living])
    for agent in living:
        candidates = ids[ids != agent.agent_id]
        if len(candidates) == 0:
            continue
        peer_id = int(rng.choice(candidates))
        peer = next(a for a in living if a.agent_id == peer_id)
        if peer.ecological_policy == agent.ecological_policy:
            continue
        own_fitness = fitness_signal(agent, fitness_mode, viability_adjusted_dormant_penalty, stream="ecological")
        peer_fitness = fitness_signal(peer, fitness_mode, viability_adjusted_dormant_penalty, stream="ecological")
        gap = peer_fitness - own_fitness
        p_imitate = _stable_sigmoid(beta * gap)
        if rng.random() < p_imitate:
            old = agent.ecological_policy
            agent.ecological_policy = peer.ecological_policy
            agent.ecological_policy_lineage_id = peer.ecological_policy_lineage_id
            events.append(
                EcologicalImitationEvent(
                    step=step,
                    agent=agent.agent_id,
                    model_agent=peer.agent_id,
                    old_extraction_propensity=old.extraction_propensity,
                    new_extraction_propensity=agent.ecological_policy.extraction_propensity,
                    old_maintenance_propensity=old.maintenance_propensity,
                    new_maintenance_propensity=agent.ecological_policy.maintenance_propensity,
                    old_scarcity_sensitivity=old.scarcity_sensitivity,
                    new_scarcity_sensitivity=agent.ecological_policy.scarcity_sensitivity,
                    agent_fitness=own_fitness,
                    model_fitness=peer_fitness,
                    fitness_gap=gap,
                    fitness_mode=fitness_mode,
                    resulting_ecological_lineage_id=agent.ecological_policy_lineage_id,
                    inheritance_mode="independent",
                )
            )
    return events


def coupled_dual_imitation_round(
    agents: Sequence[Agent],
    rng: np.random.Generator,
    step: int,
    beta: float = 0.5,
    fitness_mode: str = "cumulative_resources",
    viability_adjusted_dormant_penalty: float = 0.0,
) -> tuple[list[ImitationEvent], list[EcologicalImitationEvent]]:
    """``config.ecological_inheritance_mode="coupled_same_model"``: each
    living agent draws exactly **one** peer (shared between both
    dimensions — this is what makes the two dimensions come from "the
    same model agent," the milestone's third inheritance mode) and makes
    **one** Fermi decision, using the *social* (``stream="total"``)
    fitness signal as the designated comparison signal. On acceptance,
    both the social policy and the ecological policy are copied from
    that same peer — regardless of whether either was already identical
    (unlike the independent-mode functions, which skip a no-op copy;
    coupling both dimensions to one accept/reject decision means a
    same-valued dimension is still "copied," just invisibly)."""
    imitation_events: list[ImitationEvent] = []
    ecological_events: list[EcologicalImitationEvent] = []
    living = [a for a in agents if a.alive]
    if len(living) < 2:
        return imitation_events, ecological_events

    ids = np.array([a.agent_id for a in living])
    for agent in living:
        candidates = ids[ids != agent.agent_id]
        if len(candidates) == 0:
            continue
        peer_id = int(rng.choice(candidates))
        peer = next(a for a in living if a.agent_id == peer_id)

        own_fitness = fitness_signal(agent, fitness_mode, viability_adjusted_dormant_penalty, stream="total")
        peer_fitness = fitness_signal(peer, fitness_mode, viability_adjusted_dormant_penalty, stream="total")
        gap = peer_fitness - own_fitness
        p_imitate = _stable_sigmoid(beta * gap)
        if rng.random() >= p_imitate:
            continue

        old_social_name = agent.policy.name
        agent.policy = make_policy(peer.policy.name)
        agent.policy_lineage_id = peer.policy_lineage_id
        imitation_events.append(
            ImitationEvent(
                step=step,
                agent=agent.agent_id,
                old_policy=old_social_name,
                new_policy=agent.policy.name,
                model_agent=peer.agent_id,
                agent_fitness=own_fitness,
                model_fitness=peer_fitness,
                fitness_gap=gap,
                fitness_mode=fitness_mode,
                agent_viability_state=agent.viability_state,
                model_viability_state=peer.viability_state,
                resulting_lineage_id=agent.policy_lineage_id,
            )
        )

        old_eco = agent.ecological_policy
        agent.ecological_policy = peer.ecological_policy
        agent.ecological_policy_lineage_id = peer.ecological_policy_lineage_id
        ecological_events.append(
            EcologicalImitationEvent(
                step=step,
                agent=agent.agent_id,
                model_agent=peer.agent_id,
                old_extraction_propensity=old_eco.extraction_propensity,
                new_extraction_propensity=agent.ecological_policy.extraction_propensity,
                old_maintenance_propensity=old_eco.maintenance_propensity,
                new_maintenance_propensity=agent.ecological_policy.maintenance_propensity,
                old_scarcity_sensitivity=old_eco.scarcity_sensitivity,
                new_scarcity_sensitivity=agent.ecological_policy.scarcity_sensitivity,
                agent_fitness=own_fitness,
                model_fitness=peer_fitness,
                fitness_gap=gap,
                fitness_mode=fitness_mode,
                resulting_ecological_lineage_id=agent.ecological_policy_lineage_id,
                inheritance_mode="coupled_same_model",
            )
        )
    return imitation_events, ecological_events


def ecological_mutation_round(
    agents: Sequence[Agent],
    mutation_rate: float,
    rng: np.random.Generator,
    step: int,
    extraction_mean: float,
    extraction_std: float,
    maintenance_mean: float,
    maintenance_std: float,
    scarcity_mean: float,
    scarcity_std: float,
    lineage_counter,
) -> list[EcologicalMutationEvent]:
    """Ecological-policy analog of :func:`mutation_round`: each living
    agent independently mutates (a fresh redraw from the configured
    distribution — see ``agents/ecological_policy.py::
    mutate_ecological_policy``) with probability ``mutation_rate``,
    receiving a fresh ecological lineage id."""
    events: list[EcologicalMutationEvent] = []
    for agent in agents:
        if not agent.alive:
            continue
        if rng.random() < mutation_rate:
            old = agent.ecological_policy
            new_policy: EcologicalPolicy = mutate_ecological_policy(
                extraction_mean, extraction_std, maintenance_mean, maintenance_std, scarcity_mean, scarcity_std, rng
            )
            agent.ecological_policy = new_policy
            agent.ecological_policy_lineage_id = next(lineage_counter)
            events.append(
                EcologicalMutationEvent(
                    step=step,
                    agent=agent.agent_id,
                    old_extraction_propensity=old.extraction_propensity,
                    new_extraction_propensity=new_policy.extraction_propensity,
                    old_maintenance_propensity=old.maintenance_propensity,
                    new_maintenance_propensity=new_policy.maintenance_propensity,
                    old_scarcity_sensitivity=old.scarcity_sensitivity,
                    new_scarcity_sensitivity=new_policy.scarcity_sensitivity,
                    resulting_ecological_lineage_id=agent.ecological_policy_lineage_id,
                )
            )
    return events
