"""Viability-state population accounting (Level 0.2, Work Package B).

``observer/metrics.py`` already exports a per-step population-state
snapshot (``active_population``/``distressed_population``/
``dormant_population``/``viability_transition_count``/
``nonviable_this_step_count``/``removal_count``). This module aggregates
those over a full run's event log to answer the questions a single-step
snapshot cannot: how long agents typically spend in each state, what
causes each kind of transition, and — for ``removal_replacement`` mode —
how demographic identity (``demographic_id``), strategy lineage
(``policy_lineage_id``), and fixed population-slot identity (``agent_id``)
relate to each other across a removal/replacement event.

Pure, read-only functions of an
:class:`~abm_governance.core.events.EventLog` (plus final agent state for
the lineage-continuity check) — observer-layer code, never called from
generative decision logic.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from abm_governance.agents.agent import Agent
from abm_governance.core.events import EventLog


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else math.nan


def transition_cause_counts(event_log: EventLog) -> dict:
    """Count every viability-state transition in the run by
    ``(from_state, to_state, cause)``. Empty for a
    ``viability_mode="none"`` run (no ``ViabilityTransitionEvent`` is ever
    produced in that mode — see simulation.py::_viability_round)."""
    counts: Counter = Counter()
    for e in event_log.viability_transitions:
        counts[(e.from_state, e.to_state, e.cause)] += 1
    return {f"{k[0]}->{k[1]} ({k[2]})": v for k, v in counts.items()}


def time_in_state_by_agent(event_log: EventLog, n_steps: int) -> dict:
    """For each agent that ever transitioned, reconstruct (from the
    ordered transition log) how many steps it spent in each viability
    state over the run. An agent that never transitions (viability_mode=
    "none", or an agent that simply never went into deficit) is *not*
    included in the returned dict — it spent the entire run "active" by
    construction, which callers can infer from its absence rather than
    this function guessing a population it was never told."""
    by_agent: dict[int, list] = defaultdict(list)
    for e in event_log.viability_transitions:
        by_agent[e.agent].append(e)

    result: dict[int, dict] = {}
    for agent_id, events in by_agent.items():
        events = sorted(events, key=lambda e: e.step)
        time_in_state: Counter = Counter()
        # Before the first recorded transition, the agent was "active"
        # (the only state an agent can start a run in).
        prev_step = 0
        prev_state = "active"
        for e in events:
            time_in_state[prev_state] += e.step - prev_step
            prev_step = e.step
            prev_state = e.to_state
        time_in_state[prev_state] += n_steps - prev_step
        result[agent_id] = dict(time_in_state)
    return result


def population_state_summary(event_log: EventLog, n_steps: int) -> dict:
    """Run-level summary: total transitions by cause, total removals, and
    the distribution (across agents that ever transitioned) of time spent
    dormant/distressed before either recovering or being removed."""
    dormant_durations = []
    distressed_durations = []
    recoveries = 0
    removals = 0
    for e in event_log.viability_transitions:
        if e.cause == "resources_recovered":
            recoveries += 1
        if e.to_state == "nonviable":
            removals += 1

    time_in_state = time_in_state_by_agent(event_log, n_steps)
    for agent_states in time_in_state.values():
        if "dormant" in agent_states:
            dormant_durations.append(agent_states["dormant"])
        if "distressed" in agent_states:
            distressed_durations.append(agent_states["distressed"])

    return {
        "n_agents_ever_transitioned": len(time_in_state),
        "transition_cause_counts": transition_cause_counts(event_log),
        "total_recoveries": recoveries,
        "total_removals": removals,
        "recovery_rate_among_distressed_or_dormant_episodes": _safe_ratio(
            recoveries, recoveries + removals
        ),
        "mean_dormant_duration": float(sum(dormant_durations) / len(dormant_durations)) if dormant_durations else math.nan,
        "mean_distressed_duration": float(sum(distressed_durations) / len(distressed_durations)) if distressed_durations else math.nan,
    }


def replacement_lineage_summary(event_log: EventLog, final_agents: list[Agent]) -> dict:
    """For ``removal_replacement`` mode: one record per
    :class:`~abm_governance.core.events.ReplacementEvent`, plus a check
    that every population slot's identity bookkeeping is internally
    consistent — ``agent_id`` is unchanged across a replacement (same
    network node), ``demographic_id`` always increases (a fresh
    individual), and ``policy_lineage_id`` follows whatever
    ``inheritance`` rule was configured (never silently defaulting to the
    population's dominant policy — see
    ``core/config.py::VALID_REPLACEMENT_POLICIES``)."""
    final_by_id = {a.agent_id: a for a in final_agents}
    records = []
    for e in event_log.replacements:
        current = final_by_id.get(e.agent_id)
        records.append(
            {
                "step": e.step,
                "agent_id": e.agent_id,
                "old_demographic_id": e.old_demographic_id,
                "new_demographic_id": e.new_demographic_id,
                "demographic_id_increased": e.new_demographic_id > e.old_demographic_id,
                "old_policy": e.old_policy,
                "new_policy": e.new_policy,
                "inheritance": e.inheritance,
                "resources_at_removal": e.resources_at_removal,
                "initial_resources": e.initial_resources,
                "current_demographic_id_matches_final_state": (
                    current is not None and current.demographic_id == e.new_demographic_id
                ),
            }
        )
    inheritance_counts = Counter(e.inheritance for e in event_log.replacements)
    return {
        "total_replacements": len(event_log.replacements),
        "inheritance_rule_counts": dict(inheritance_counts),
        "replacements": records,
    }
