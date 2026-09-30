"""Enforcement diagnostics: the punishment confusion matrix (Level 0.1,
Work Package C).

The Level-0 ``erroneous_punishment_rate`` metric was scientifically
interesting but under-decomposed: its denominator ("punishments issued
this step") can be small or zero, and it conflates observation error with
punishment-policy behaviour. This module builds an explicit confusion
matrix — true/false positive/negative punishment — plus perception-error
rates, each with an explicit, documented denominator. Any conditional
probability with zero eligible observations is reported as ``NaN``
(``math.nan``), never silently as 0.0.

All functions here are pure, read-only functions of an
:class:`~abm_governance.core.events.EventLog` snapshot — observer-layer
code, never called from generative decision logic.

Definitions (per *directed* observation — i.e. one agent observing one
partner in one interaction; every interaction yields two of these):

* **True positive**: the partner actually defected, and the observer
  punished them.
* **False positive**: the partner actually cooperated, and the observer
  punished them anyway (necessarily driven by observation error, since
  punishment is only ever triggered by a *perceived* defection at Level
  0.1 — see ``simulation.py::_maybe_punish``).
* **True negative**: the partner actually cooperated, and the observer did
  not punish them.
* **False negative**: the partner actually defected, and the observer did
  not punish them (either because they didn't perceive the defection, or
  because they perceived it but the stochastic punishment draw declined).

An observation only enters the confusion matrix if punishment was
*available* that interaction (``config.punishment_enabled``); this
distinguishes "no eligible enforcement mechanism" from "enforcement was
possible but did not occur."
"""

from __future__ import annotations

import math
from typing import Iterator

from abm_governance.core.events import EventLog
from abm_governance.interactions.game import COOPERATE, DEFECT


def _directed_observations(
    event_log: EventLog, start_step: int | None, end_step: int | None
) -> Iterator[tuple[int, int, int, int, int, bool]]:
    """Yield one tuple per directed observation:
    ``(step, observer, partner, true_action_of_partner,
    perceived_action_of_partner, punishment_available)``.
    Every :class:`InteractionEvent` yields exactly two of these (a's view
    of b, and b's view of a)."""
    for e in event_log.interactions:
        if start_step is not None and e.step < start_step:
            continue
        if end_step is not None and e.step >= end_step:
            continue
        yield (e.step, e.agent_b, e.agent_a, e.action_a, e.observed_a_by_b, e.punishment_available)
        yield (e.step, e.agent_a, e.agent_b, e.action_b, e.observed_b_by_a, e.punishment_available)


def confusion_counts(
    event_log: EventLog, start_step: int | None = None, end_step: int | None = None
) -> dict:
    """Raw, always-well-defined integer counts over the given step range
    (``end_step`` exclusive, matching Python slice semantics; ``None``
    means unbounded on that side). Feed these into
    :func:`confusion_matrix_rates` for the conditional probabilities."""
    punished_pairs = set()
    for p in event_log.punishments:
        if start_step is not None and p.step < start_step:
            continue
        if end_step is not None and p.step >= end_step:
            continue
        punished_pairs.add((p.step, p.punisher, p.target))

    tp = fp = tn = fn = 0
    n_actual_cooperate = n_actual_defect = 0
    n_perceived_defect_given_coop = 0
    n_perceived_coop_given_defect = 0
    n_perceived_defect_eligible = 0
    n_punished_given_perceived_defect = 0
    n_eligible = 0

    for step, observer, partner, true_action, perceived, available in _directed_observations(
        event_log, start_step, end_step
    ):
        if true_action == COOPERATE:
            n_actual_cooperate += 1
            if perceived == DEFECT:
                n_perceived_defect_given_coop += 1
        elif true_action == DEFECT:
            n_actual_defect += 1
            if perceived == COOPERATE:
                n_perceived_coop_given_defect += 1

        if not available:
            continue
        n_eligible += 1
        punished = (step, observer, partner) in punished_pairs

        if perceived == DEFECT:
            n_perceived_defect_eligible += 1
            if punished:
                n_punished_given_perceived_defect += 1

        if true_action == DEFECT and punished:
            tp += 1
        elif true_action == COOPERATE and punished:
            fp += 1
        elif true_action == COOPERATE and not punished:
            tn += 1
        elif true_action == DEFECT and not punished:
            fn += 1

    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "n_eligible": n_eligible,
        "n_actual_cooperate": n_actual_cooperate,
        "n_actual_defect": n_actual_defect,
        "n_perceived_defect_given_coop": n_perceived_defect_given_coop,
        "n_perceived_coop_given_defect": n_perceived_coop_given_defect,
        "n_perceived_defect_eligible": n_perceived_defect_eligible,
        "n_punished_given_perceived_defect": n_punished_given_perceived_defect,
    }


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else math.nan


def confusion_matrix_rates(counts: dict) -> dict:
    """The five conditional probabilities the milestone brief asks for,
    computed from :func:`confusion_counts`' output. Every denominator is
    explicit in the source below; any that is zero yields ``math.nan``,
    never a silently-substituted 0.0."""
    return {
        "tp": counts["tp"],
        "fp": counts["fp"],
        "tn": counts["tn"],
        "fn": counts["fn"],
        "n_eligible": counts["n_eligible"],
        # P(punishment | actual defection) = tp / (tp + fn)
        "p_punishment_given_actual_defection": _safe_ratio(counts["tp"], counts["tp"] + counts["fn"]),
        # P(punishment | actual cooperation) = fp / (fp + tn)
        "p_punishment_given_actual_cooperation": _safe_ratio(counts["fp"], counts["fp"] + counts["tn"]),
        # P(perceived defection | actual cooperation)
        "p_perceived_defection_given_actual_cooperation": _safe_ratio(
            counts["n_perceived_defect_given_coop"], counts["n_actual_cooperate"]
        ),
        # P(perceived cooperation | actual defection)
        "p_perceived_cooperation_given_actual_defection": _safe_ratio(
            counts["n_perceived_coop_given_defect"], counts["n_actual_defect"]
        ),
        # P(punishment | perceived defection) — should track
        # config.punishment_probability closely in expectation, since
        # punishment is only ever attempted following a perceived
        # defection (see simulation.py::_maybe_punish).
        "p_punishment_given_perceived_defection": _safe_ratio(
            counts["n_punished_given_perceived_defect"], counts["n_perceived_defect_eligible"]
        ),
        # Precision/recall framing, provided for convenience alongside the
        # conditional probabilities above (recall == p_punishment_given_actual_defection).
        "punishment_precision": _safe_ratio(counts["tp"], counts["tp"] + counts["fp"]),
        "punishment_recall": _safe_ratio(counts["tp"], counts["tp"] + counts["fn"]),
    }


def confusion_matrix_summary(
    event_log: EventLog, start_step: int | None = None, end_step: int | None = None
) -> dict:
    """Convenience wrapper: counts + rates in one call."""
    counts = confusion_counts(event_log, start_step, end_step)
    return confusion_matrix_rates(counts)
