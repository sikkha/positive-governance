"""Participation-opportunity accounting and the selective-participation
diagnostic (Level 0.2, Work Package A).

``observer/metrics.py`` already exports per-step opportunity/participation
counts and conditional probabilities (``opportunities_total``,
``p_cooperate_given_interaction``, ``p_cooperate_and_interaction_given_
opportunity``, etc.). This module answers the milestone's scientific
question 3 directly and explicitly, over an arbitrary step range (typically
a whole run, or its post-transient tail): **is Level-0.1's near-universal
measured cooperation caused by cooperative behaviour, or by distressed and
defecting agents progressively dropping out of the interacting
population?**

Everything here is a pure, read-only function of an
:class:`~abm_governance.core.events.EventLog` snapshot (plus, for the
category breakdowns that need it, the final agent list) — observer-layer
code, never called from generative decision logic, exactly like
``observer/enforcement.py`` and ``observer/metrics.py``.

Two breakdown dimensions (resource-status, degree) are read directly off
each :class:`~abm_governance.core.events.InteractionEvent`, stamped at the
moment the interaction happened (see ``simulation.py::_run_interactions``)
— exact, not reconstructed. Two more (policy-lineage/neighbourhood,
recent-payoff category) are *not* stamped per-event (that would double the
per-interaction event payload for two diagnostics the milestone brief
treats as secondary); instead they are computed by joining each
interaction's participant ids against the *final* agent state. This is a
documented approximation — an agent's lineage/recent-payoff bucket at
run-end may differ from its bucket at the time of a specific early-run
interaction, particularly for agents that later imitate a different
policy or whose payoff window has since moved on — and is called out
explicitly in ``docs/level0.2_scientific_note.md`` as a known limitation,
not silently treated as exact.
"""

from __future__ import annotations

import math
from collections import Counter

from abm_governance.agents.agent import Agent
from abm_governance.core.events import EventLog
from abm_governance.interactions.game import COOPERATE

#: Withhold-event reasons that represent a genuine non-participation
#: outcome for participation-bias purposes (i.e. "this agent-opportunity
#: did not become an interaction"), as opposed to bookkeeping detail about
#: *why*. See simulation.py::_run_interactions for where each reason is
#: produced.
_ALL_WITHHOLD_REASONS = (
    "distress",
    "partner_distress",
    "ineligible_dormant",
    "partner_ineligible_dormant",
)

#: Maps a withhold reason to the resource-status category it implies for
#: *that* agent-side (used only for the participant/nonparticipant
#: resource-status comparison below — the withhold event itself does not
#: carry a resource_status field, unlike InteractionEvent).
_REASON_TO_STATUS = {
    "distress": "distressed",
    "ineligible_dormant": "dormant",
    # A "partner_*" reason means *this* agent's own status was not the
    # blocking factor — it was willing/eligible but blocked by the other
    # side. Bucketed separately so it is never conflated with the agent's
    # own distress/dormancy.
    "partner_distress": "willing_but_partner_blocked",
    "partner_ineligible_dormant": "willing_but_partner_blocked",
}


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else math.nan


def _events_in_range(events: list, start_step: int | None, end_step: int | None) -> list:
    return [
        e
        for e in events
        if (start_step is None or e.step >= start_step) and (end_step is None or e.step < end_step)
    ]


def participation_bias_summary(
    event_log: EventLog, start_step: int | None = None, end_step: int | None = None
) -> dict:
    """The core Work-Package-A diagnostic, aggregated over
    ``[start_step, end_step)`` (``None``/``None`` = the whole run).

    Reports, side by side, four *different* things that "cooperation rate"
    can mean, so that a run where they diverge sharply is immediately
    legible as selective-participation bias rather than genuine behavioural
    cooperation:

    * ``conditional_cooperation_rate`` — P(C | interaction). The Level-0.1
      legacy metric: cooperation among agent-sides that actually
      interacted. This is what can approach 1.0 even while most of the
      population is not participating.
    * ``unconditional_cooperation_rate`` — P(C ∩ interaction | opportunity).
      Realized cooperation as a fraction of *every* agent-opportunity that
      existed this range, whether or not it resulted in an interaction.
      This is the one that falls well below the conditional rate exactly
      when selective participation (not universal cooperative behaviour)
      is inflating the conditional rate.
    * ``participation_rate`` — P(interaction | opportunity). How much of
      the theoretically-possible interaction volume was actually realized.
    * ``withdrawal_rate`` — 1 - participation_rate, decomposed by cause
      (distress vs. dormancy vs. partner-blocked).

    All ratios use ``_safe_ratio`` (NaN, with the underlying counts always
    reported alongside, for a zero denominator).
    """
    interactions = _events_in_range(event_log.interactions, start_step, end_step)
    withholds = _events_in_range(event_log.withholds, start_step, end_step)

    n_actions = 2 * len(interactions)
    n_cooperate = sum((e.action_a == COOPERATE) + (e.action_b == COOPERATE) for e in interactions)
    withhold_reason_counts = Counter(e.reason for e in withholds)
    n_withhold = len(withholds)

    opportunities_total = n_actions + n_withhold

    return {
        "start_step": start_step,
        "end_step": end_step,
        "opportunities_total": opportunities_total,
        "completed_agent_opportunities": n_actions,
        "completed_interactions": len(interactions),
        "cooperate_count": n_cooperate,
        "defect_count": n_actions - n_cooperate,
        "withhold_total": n_withhold,
        "withhold_by_reason": dict(withhold_reason_counts),
        # -- the four headline rates --------------------------------------
        "conditional_cooperation_rate": _safe_ratio(n_cooperate, n_actions),
        "unconditional_cooperation_rate": _safe_ratio(n_cooperate, opportunities_total),
        "participation_rate": _safe_ratio(n_actions, opportunities_total),
        "withdrawal_rate": _safe_ratio(n_withhold, opportunities_total),
        "distress_withdrawal_rate": _safe_ratio(
            sum(withhold_reason_counts.get(r, 0) for r in ("distress", "partner_distress")), opportunities_total
        ),
        "dormancy_withdrawal_rate": _safe_ratio(
            sum(withhold_reason_counts.get(r, 0) for r in ("ineligible_dormant", "partner_ineligible_dormant")),
            opportunities_total,
        ),
        # -- the bias diagnostic itself -------------------------------------
        # A large positive gap (conditional >> unconditional) is the
        # selective-participation signature the milestone's scientific
        # question 3 asks about: cooperation looks universal only among
        # the shrinking subset of agents still interacting.
        "conditional_minus_unconditional_gap": (
            _safe_ratio(n_cooperate, n_actions) - _safe_ratio(n_cooperate, opportunities_total)
            if n_actions and opportunities_total
            else math.nan
        ),
    }


def cooperation_by_resource_status(
    event_log: EventLog, start_step: int | None = None, end_step: int | None = None
) -> dict:
    """Conditional cooperation rate broken down by each interacting side's
    point-in-time resource status ("solvent"/"distressed"/"dormant" —
    "dormant" only appears here in ``dormancy_recovery`` mode, since
    ``removal_replacement`` and the hard eligibility gate mean a dormant
    agent's opportunities are withheld, not completed; see
    simulation.py::_run_interactions). Also reports, for comparison, how
    many agent-opportunities were *withheld* while in each implied status
    — this is the "resource distribution of participants vs.
    nonparticipants" comparison the milestone brief asks for."""
    interactions = _events_in_range(event_log.interactions, start_step, end_step)
    withholds = _events_in_range(event_log.withholds, start_step, end_step)

    coop_counts: Counter = Counter()
    action_counts: Counter = Counter()
    for e in interactions:
        coop_counts[e.resource_status_a] += 1 if e.action_a == COOPERATE else 0
        action_counts[e.resource_status_a] += 1
        coop_counts[e.resource_status_b] += 1 if e.action_b == COOPERATE else 0
        action_counts[e.resource_status_b] += 1

    nonparticipant_counts: Counter = Counter()
    for e in withholds:
        status = _REASON_TO_STATUS.get(e.reason, "unknown")
        nonparticipant_counts[status] += 1

    categories = sorted(set(action_counts) | set(nonparticipant_counts))
    return {
        cat: {
            "participant_agent_opportunities": action_counts.get(cat, 0),
            "participant_cooperate_count": coop_counts.get(cat, 0),
            "cooperation_rate": _safe_ratio(coop_counts.get(cat, 0), action_counts.get(cat, 0)),
            "nonparticipant_agent_opportunities": nonparticipant_counts.get(cat, 0),
        }
        for cat in categories
    }


def _degree_category(degree: int, bins: tuple[tuple[int, int, str], ...]) -> str:
    for lo, hi, label in bins:
        if lo <= degree <= hi:
            return label
    return "other"  # pragma: no cover - defensive, unreachable given an open-ended final bin


#: Default degree-category bins (inclusive on both ends; last bin is
#: effectively open-ended via a large upper bound). Documented, not a
#: magic number buried in the function body — mirrors the milestone
#: brief's "avoid magic numbers" requirement for classification thresholds.
DEFAULT_DEGREE_BINS: tuple[tuple[int, int, str], ...] = (
    (0, 0, "isolated"),
    (1, 2, "low_degree"),
    (3, 5, "mid_degree"),
    (6, 10_000, "high_degree"),
)


def cooperation_by_degree(
    event_log: EventLog,
    start_step: int | None = None,
    end_step: int | None = None,
    bins: tuple[tuple[int, int, str], ...] = DEFAULT_DEGREE_BINS,
) -> dict:
    """Conditional cooperation rate broken down by each interacting side's
    point-in-time network degree category. Isolated agents (degree 0)
    structurally cannot appear here (they have no edges to interact
    over) — this function reports interacting-side degree only; use
    ``observer/network_diagnostics.py::isolated_agent_count`` for the
    isolation half of the "prevented by isolation" category."""
    interactions = _events_in_range(event_log.interactions, start_step, end_step)
    coop_counts: Counter = Counter()
    action_counts: Counter = Counter()
    for e in interactions:
        cat_a = _degree_category(e.degree_a, bins)
        cat_b = _degree_category(e.degree_b, bins)
        coop_counts[cat_a] += 1 if e.action_a == COOPERATE else 0
        action_counts[cat_a] += 1
        coop_counts[cat_b] += 1 if e.action_b == COOPERATE else 0
        action_counts[cat_b] += 1
    return {
        cat: {
            "agent_opportunities": action_counts[cat],
            "cooperate_count": coop_counts[cat],
            "cooperation_rate": _safe_ratio(coop_counts[cat], action_counts[cat]),
        }
        for cat in action_counts
    }


def cooperation_by_policy_lineage(
    event_log: EventLog,
    final_agents: list[Agent],
    start_step: int | None = None,
    end_step: int | None = None,
) -> dict:
    """Conditional cooperation rate broken down by each interacting side's
    *final-state* ``policy_lineage_id``. Approximate (see module
    docstring): joins each interaction's participant id against final
    agent state rather than the lineage id that agent actually held at
    interaction time, so this systematically attributes early-run
    interactions to whatever lineage the agent ended the run on. Reported
    anyway because the milestone brief asks for it, with this limitation
    documented rather than hidden."""
    lineage_by_id = {a.agent_id: a.policy_lineage_id for a in final_agents}
    interactions = _events_in_range(event_log.interactions, start_step, end_step)
    coop_counts: Counter = Counter()
    action_counts: Counter = Counter()
    for e in interactions:
        lin_a = lineage_by_id.get(e.agent_a, "unknown")
        lin_b = lineage_by_id.get(e.agent_b, "unknown")
        coop_counts[lin_a] += 1 if e.action_a == COOPERATE else 0
        action_counts[lin_a] += 1
        coop_counts[lin_b] += 1 if e.action_b == COOPERATE else 0
        action_counts[lin_b] += 1
    return {
        lin: {
            "agent_opportunities": action_counts[lin],
            "cooperate_count": coop_counts[lin],
            "cooperation_rate": _safe_ratio(coop_counts[lin], action_counts[lin]),
        }
        for lin in action_counts
    }


#: Default recent-payoff category bins, expressed as (lo, hi, label) over
#: the agent's final ``recent_payoff`` value. Unlike the degree bins,
#: there is no natural fixed scale for payoff (it depends on the payoff
#: matrix and fitness_window), so callers running an unusual payoff-matrix
#: configuration should pass their own bins rather than rely on this
#: default going unchecked.
DEFAULT_RECENT_PAYOFF_BINS: tuple[tuple[float, float, str], ...] = (
    (float("-inf"), -0.01, "negative"),
    (-0.01, 0.01, "near_zero"),
    (0.01, float("inf"), "positive"),
)


def cooperation_by_recent_payoff(
    event_log: EventLog,
    final_agents: list[Agent],
    start_step: int | None = None,
    end_step: int | None = None,
    bins: tuple[tuple[float, float, str], ...] = DEFAULT_RECENT_PAYOFF_BINS,
) -> dict:
    """Conditional cooperation rate broken down by each interacting side's
    *final-state* ``recent_payoff`` category. Approximate for the same
    reason, and in the same direction, as
    :func:`cooperation_by_policy_lineage` — see module docstring."""

    def _bucket(value: float) -> str:
        for lo, hi, label in bins:
            if lo <= value < hi:
                return label
        return bins[-1][2]

    payoff_by_id = {a.agent_id: a.recent_payoff for a in final_agents}
    interactions = _events_in_range(event_log.interactions, start_step, end_step)
    coop_counts: Counter = Counter()
    action_counts: Counter = Counter()
    for e in interactions:
        cat_a = _bucket(payoff_by_id.get(e.agent_a, 0.0))
        cat_b = _bucket(payoff_by_id.get(e.agent_b, 0.0))
        coop_counts[cat_a] += 1 if e.action_a == COOPERATE else 0
        action_counts[cat_a] += 1
        coop_counts[cat_b] += 1 if e.action_b == COOPERATE else 0
        action_counts[cat_b] += 1
    return {
        cat: {
            "agent_opportunities": action_counts[cat],
            "cooperate_count": coop_counts[cat],
            "cooperation_rate": _safe_ratio(coop_counts[cat], action_counts[cat]),
        }
        for cat in action_counts
    }
