"""Level 1.1b, Work Package E: two deliberately separate observer
concepts for accountability, read-only from an :class:`EventLog`
snapshot — never fed back into any generative-layer decision.

``accountability_activity`` is purely descriptive: how much accountability
*machinery ran* — audit/recall/appeal attempts and their raw counts,
regardless of whether anything they did was correct or corrective. A run
with ``accountability_enabled=True`` and a high audit rate but terrible
``audit_accuracy`` (a "randomized placebo" condition — audits fire
constantly but carry no information) would score HIGH on activity.

``effective_constraint`` requires REALIZED outcomes: true-positive
detections, successful recalls that actually recovered funds, appeals
that actually corrected a false sanction. It is computed **only** from
event-level ground truth already present in the log
(``AuditEvent.outcome``, ``RecallEvent.succeeded``/``recovered_funds``,
``AppealEvent.was_false_sanction``/``upheld``) — never from
``config.accountability_enabled`` or any other config flag directly. A
"randomized placebo" condition (audits happen constantly but
``audit_accuracy`` carries no real signal) would score LOW on effective
constraint even while scoring HIGH on activity — this is the entire
point of keeping the two concepts separate: Level 1.1's classifier used
config-flag presence as a stand-in for "accountable," which conflated
the two.
"""

from __future__ import annotations

from abm_governance.core.events import EventLog


def accountability_activity(event_log: EventLog, step_range: tuple[int, int] | None = None) -> dict:
    """Purely descriptive machinery-ran counts — never conditioned on
    whether an audit/recall/appeal was correct. ``step_range`` (start,
    end) restricts to ``start <= step < end`` when given; ``None`` uses
    the whole log."""

    def _in_range(step: int) -> bool:
        if step_range is None:
            return True
        start, end = step_range
        return start <= step < end

    audits = [e for e in event_log.audits if _in_range(e.step)]
    recalls = [e for e in event_log.recalls if _in_range(e.step)]
    appeals = [e for e in event_log.appeals if _in_range(e.step)]
    return {
        "n_audits": len(audits),
        "n_recall_votes": len(recalls),
        "n_appeals": len(appeals),
        "total_audit_cost": sum(a.cost for a in audits),
        "total_appeal_cost": sum(a.cost for a in appeals),
        "any_accountability_event": bool(audits or recalls or appeals),
    }


def effective_constraint(event_log: EventLog, step_range: tuple[int, int] | None = None) -> dict:
    """Realized-outcome-only accountability effectiveness. Every field
    here is computed from event ground truth, not config flags: a run
    where ``accountability_enabled=True`` but ``audit_accuracy=0.5``
    (coin-flip detection) will show near-zero ``detection_rate_given_
    misconduct`` and near-zero ``recovery_fraction_of_appropriated`` even
    though :func:`accountability_activity` reports plenty of activity."""

    def _in_range(step: int) -> bool:
        if step_range is None:
            return True
        start, end = step_range
        return start <= step < end

    audits = [e for e in event_log.audits if _in_range(e.step)]
    recalls = [e for e in event_log.recalls if _in_range(e.step)]
    appeals = [e for e in event_log.appeals if _in_range(e.step)]
    appropriations = [e for e in event_log.appropriations if _in_range(e.step)]

    n_true_positive = sum(1 for a in audits if a.outcome == "true_positive")
    n_false_negative = sum(1 for a in audits if a.outcome == "false_negative")
    n_false_positive = sum(1 for a in audits if a.outcome == "false_positive")
    n_true_negative = sum(1 for a in audits if a.outcome == "true_negative")
    n_actual_misconduct_audited = n_true_positive + n_false_negative
    n_actual_innocent_audited = n_false_positive + n_true_negative

    detection_rate_given_misconduct = (
        n_true_positive / n_actual_misconduct_audited if n_actual_misconduct_audited > 0 else None
    )
    false_positive_rate_given_innocent = (
        n_false_positive / n_actual_innocent_audited if n_actual_innocent_audited > 0 else None
    )

    n_recalls_succeeded = sum(1 for r in recalls if r.succeeded)
    total_recovered = sum(r.recovered_funds for r in recalls if r.succeeded)
    total_appropriated = sum(a.amount for a in appropriations)
    recovery_fraction_of_appropriated = (
        total_recovered / total_appropriated if total_appropriated > 0 else None
    )

    # An appeal is a CORRECTIVE outcome (effective constraint on the
    # accountability apparatus itself, not on the delegate) only when it
    # upholds a genuinely false sanction -- an appeal that overturns a
    # justified sanction is the opposite of effective constraint (a
    # false-positive-in-review), tracked separately.
    n_appeals_justified_upheld = sum(1 for a in appeals if a.was_false_sanction and a.upheld)
    n_appeals_unjustified_upheld = sum(1 for a in appeals if not a.was_false_sanction and a.upheld)
    n_false_sanctions_appealed = sum(1 for a in appeals if a.was_false_sanction)
    false_sanction_correction_rate = (
        n_appeals_justified_upheld / n_false_sanctions_appealed if n_false_sanctions_appealed > 0 else None
    )

    realized_detection = n_true_positive > 0
    realized_recovery = n_recalls_succeeded > 0 and total_recovered > 0.0
    realized_false_sanction_correction = n_appeals_justified_upheld > 0
    # "Effectively constrained" requires at least one REALIZED corrective
    # outcome grounded in a true detection or a genuine appeal
    # correction -- never merely that accountability_enabled=True or
    # that audits/recalls/appeals were attempted.
    effectively_constrained = realized_detection and (realized_recovery or n_recalls_succeeded > 0)

    return {
        "n_true_positive_audits": n_true_positive,
        "n_false_negative_audits": n_false_negative,
        "n_false_positive_audits": n_false_positive,
        "n_true_negative_audits": n_true_negative,
        "detection_rate_given_misconduct": detection_rate_given_misconduct,
        "false_positive_rate_given_innocent": false_positive_rate_given_innocent,
        "n_recalls_succeeded": n_recalls_succeeded,
        "total_recovered_funds": total_recovered,
        "total_appropriated": total_appropriated,
        "recovery_fraction_of_appropriated": recovery_fraction_of_appropriated,
        "n_appeals_justified_upheld": n_appeals_justified_upheld,
        "n_appeals_unjustified_upheld": n_appeals_unjustified_upheld,
        "false_sanction_correction_rate": false_sanction_correction_rate,
        "realized_detection": realized_detection,
        "realized_recovery": realized_recovery,
        "realized_false_sanction_correction": realized_false_sanction_correction,
        "effectively_constrained": effectively_constrained,
    }
