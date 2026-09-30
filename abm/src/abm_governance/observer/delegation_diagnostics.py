"""Level 1.1, Work Packages J/K: observer-side delegation/capacity/
accountability/coordination metrics and the cautious mechanism-
validation classifier.

Same discipline as ``observer/institution_diagnostics.py`` (Level 1.0)
and ``dev_mem/project_vision.md`` §5: every function here is a pure,
read-only function of an already-collected snapshot (an ``EventLog``, a
list of ``Delegate``/``CoordinationLink`` instances); nothing here is
ever read by any decision function in ``simulation.py``/``agents/``/
``rules/``. Work Package J's nine dimensions are deliberately kept as
*separate* functions/dictionaries — never combined into one governance
score, and never used to assign one of the dissertation's three
governance trajectories (see the structural guard in
``tests/test_level11_structural_guard.py``).

Work Package K's :func:`classify_delegation` returns only labels from
:data:`VALID_LABELS` — a mechanism-validation vocabulary, not a
macro-phenotype vocabulary. Its purpose is to confirm the *mechanisms*
implemented here can both occur and fail to occur, never to claim a
recurrent institutional phenotype or reproduce the dissertation's SEM
typology (Section 6's own explicit instruction, restated in
``docs/level1.1_scientific_note.md``).
"""

from __future__ import annotations

import numpy as np

from abm_governance.core.events import EventLog
from abm_governance.rules.coordination import CoordinationLink
from abm_governance.rules.delegation import Delegate
from abm_governance.rules.shared_rule import SharedRule

DEFAULT_MIN_DELEGATION_DURATION_STEPS = 30
DEFAULT_PERSISTENT_DELEGATION_DURATION_STEPS = 100
DEFAULT_MIN_COORDINATION_DURATION_STEPS = 20

#: Work Package K's fixed, cautious label vocabulary — every entry names
#: a mechanism-validation state, never a governance type.
VALID_LABELS = (
    "no_delegation",
    "attempted_delegation",
    "delegate_selected",
    "unstable_delegation",
    "persistent_delegation",
    "accountable_delegation",
    "weakly_constrained_delegation",
    "administratively_inactive",
    "administratively_functional",
    "fragmented_coordination",
    "interpatch_coordination",
    "unclassified",
)


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else float("nan")


# ---------------------------------------------------------------------------
# Work Package J: nine separate observer dimensions, one function each.
# ---------------------------------------------------------------------------
def administrative_capacity_metrics(delegates: list[Delegate], event_log: EventLog) -> dict:
    perf = event_log.task_performances
    n_success = sum(1 for e in perf if e.outcome == "success")
    n_failure = sum(1 for e in perf if e.outcome == "failure")
    n_withheld = sum(1 for e in perf if e.outcome == "withheld")
    n_total = len(perf)
    capacities = [d.capacity for d in delegates if d.task_attempts]
    return {
        "n_task_attempts": n_total,
        "n_task_successes": n_success,
        "n_task_failures": n_failure,
        "n_task_withheld": n_withheld,
        "task_completion_reliability": _safe_ratio(n_success, n_total),
        "mean_realized_capacity": float(np.mean(capacities)) if capacities else float("nan"),
        "mean_record_quality": float(np.mean([d.record_quality for d in delegates])) if delegates else float("nan"),
    }


def delegation_concentration_metrics(delegates: list[Delegate]) -> dict:
    if not delegates:
        return {
            "n_delegates_ever": 0, "mean_n_tasks_per_delegate": float("nan"),
            "mean_tenure_steps": float("nan"), "concentration_index": float("nan"),
        }
    n_tasks = [len(d.tasks) for d in delegates]
    tenures = [((d.removal_step if d.removal_step is not None else d.start_step) - d.start_step) for d in delegates]
    # A simple concentration index: fraction of all task-slots held by
    # the single most task-heavy delegate (Herfindahl-style, bounded
    # [1/n, 1]) -- never combined with any other dimension here.
    total_task_slots = sum(n_tasks)
    concentration = (max(n_tasks) / total_task_slots) if total_task_slots else float("nan")
    return {
        "n_delegates_ever": len(delegates),
        "mean_n_tasks_per_delegate": float(np.mean(n_tasks)),
        "mean_tenure_steps": float(np.mean(tenures)),
        "concentration_index": concentration,
    }


def accountability_intensity_metrics(event_log: EventLog) -> dict:
    n_audits = len(event_log.audits)
    n_recalls = len(event_log.recalls)
    n_recalls_succeeded = sum(1 for e in event_log.recalls if e.succeeded)
    n_appeals = len(event_log.appeals)
    n_appeals_upheld = sum(1 for e in event_log.appeals if e.upheld)
    total_cost = sum(e.cost for e in event_log.audits) + sum(e.cost for e in event_log.appeals)
    return {
        "n_audits": n_audits,
        "n_recall_attempts": n_recalls,
        "n_recalls_succeeded": n_recalls_succeeded,
        "n_appeals": n_appeals,
        "n_appeals_upheld": n_appeals_upheld,
        "total_accountability_cost": total_cost,
    }


def effective_constraint_metrics(delegates: list[Delegate], event_log: EventLog) -> dict:
    audits = event_log.audits
    n_tp = sum(1 for e in audits if e.outcome == "true_positive")
    n_fn = sum(1 for e in audits if e.outcome == "false_negative")
    n_fp = sum(1 for e in audits if e.outcome == "false_positive")
    n_tn = sum(1 for e in audits if e.outcome == "true_negative")
    appeals_true_positive = [e for e in event_log.appeals if e.was_false_sanction]
    appeals_false_positive = [e for e in event_log.appeals if not e.was_false_sanction]
    n_appeals_true_upheld = sum(1 for e in appeals_true_positive if e.upheld)
    n_appeals_false_rejected = sum(1 for e in appeals_false_positive if not e.upheld)
    total_appropriated = sum(d.appropriated_total for d in delegates)
    total_recovered = sum(e.recovered_funds for e in event_log.recalls)
    return {
        "p_misconduct_detected": _safe_ratio(n_tp, n_tp + n_fn),
        "p_justified_challenge_succeeds": _safe_ratio(n_appeals_true_upheld, len(appeals_true_positive)),
        "p_unjustified_challenge_fails": _safe_ratio(n_appeals_false_rejected, len(appeals_false_positive)),
        "audit_false_positive_rate": _safe_ratio(n_fp, n_fp + n_tn),
        "total_appropriated_resources": total_appropriated,
        "total_appropriated_resources_recovered": total_recovered,
        "appropriation_recovery_rate": _safe_ratio(total_recovered, total_appropriated),
    }


def legitimacy_support_metrics(delegates: list[Delegate], rules: list[SharedRule], event_log: EventLog) -> dict:
    n_contribution_asks = sum(1 for e in event_log.contributions if e.amount_asked > 0)
    n_contribution_complied = sum(1 for e in event_log.contributions if e.complied)
    n_exits = sum(1 for e in event_log.memberships if e.kind == "exit")
    n_joins = sum(1 for e in event_log.memberships if e.kind == "join")
    n_recall_attempts = len(event_log.recalls)
    n_recall_failed = sum(1 for e in event_log.recalls if not e.succeeded)
    return {
        "contribution_compliance_rate": _safe_ratio(n_contribution_complied, n_contribution_asks),
        "n_voluntary_exits": n_exits,
        "n_joins": n_joins,
        "delegate_survival_rate_under_challenge": _safe_ratio(n_recall_failed, n_recall_attempts),
    }


def administrative_extraction_metrics(delegates: list[Delegate], event_log: EventLog) -> dict:
    admin_cost = sum(e.amount for e in event_log.administrative_spending)
    appropriated = sum(d.appropriated_total for d in delegates)
    false_sanction_harm = sum(
        e.magnitude for e in event_log.sanctions if e.false_sanction
    )
    contribution_burden = sum(e.amount_paid for e in event_log.contributions)
    return {
        "total_administrative_cost": admin_cost,
        "total_appropriated_resources": appropriated,
        "total_false_sanction_harm": false_sanction_harm,
        "total_contribution_burden": contribution_burden,
    }


def institutional_scale_metrics(rules: list[SharedRule], delegates: list[Delegate], links: list[CoordinationLink]) -> dict:
    active_rules = [r for r in rules if r.active]
    return {
        "n_active_rules": len(active_rules),
        "mean_membership_size": float(np.mean([r.n_members for r in active_rules])) if active_rules else float("nan"),
        "n_jurisdictional_patches": len({r.patch_id for r in active_rules}),
        "n_active_coordination_links": sum(1 for link in links if link.active),
        "n_coordination_links_ever": len(links),
        "mean_delegate_task_scope": float(np.mean([len(d.tasks) for d in delegates])) if delegates else float("nan"),
    }


def institutional_flexibility_metrics(rules: list[SharedRule], event_log: EventLog) -> dict:
    n_amendments = len(event_log.rule_amendments)
    n_adopted_amendments = sum(1 for e in event_log.rule_amendments if e.adopted)
    magnitudes = [abs(e.new_value - e.old_value) for e in event_log.rule_amendments if e.adopted]
    return {
        "n_amendment_attempts": n_amendments,
        "n_amendments_adopted": n_adopted_amendments,
        "amendment_frequency": _safe_ratio(n_adopted_amendments, len(rules)) if rules else float("nan"),
        "mean_amendment_magnitude": float(np.mean(magnitudes)) if magnitudes else float("nan"),
    }


def founder_independence_metrics(rules: list[SharedRule], delegates: list[Delegate]) -> dict:
    """Reuses ``institution_diagnostics.persistence_metrics``'s own
    founder-independence definition for rules; adds the delegate-level
    analog (a delegate lineage — successive delegates at the same rule,
    chained via ``predecessor_delegate_id`` — outliving its first
    holder)."""
    n_delegate_successions = sum(1 for d in delegates if d.predecessor_delegate_id is not None)
    return {
        "n_delegate_successions": n_delegate_successions,
        "delegate_succession_rate": _safe_ratio(n_delegate_successions, len(delegates)) if delegates else float("nan"),
    }


def functional_effect(condition_values: list[float], baseline_values: list[float]) -> dict:
    """A generic paired-or-unpaired difference-with-uncertainty helper
    (Work Package J "functional effect": extraction/maintenance/
    occupancy/welfare change attributable to the institution, after
    accounting for institutional cost). Deliberately generic — the
    caller supplies whatever already-computed per-seed values it wants
    compared (e.g. final occupancy under a delegation condition vs. a
    matched no-delegation baseline); this function does not know or care
    what quantity it is. Uses
    ``observer/replication_units.py::seed_clustered_bootstrap_ci``-style
    resampling directly (kept self-contained rather than importing, so
    this module has no dependency on the specific seed-keying scheme a
    caller uses)."""
    cond = np.asarray([v for v in condition_values if v is not None and not (isinstance(v, float) and np.isnan(v))], dtype=float)
    base = np.asarray([v for v in baseline_values if v is not None and not (isinstance(v, float) and np.isnan(v))], dtype=float)
    if cond.size == 0 or base.size == 0:
        return {"mean_effect": float("nan"), "n_condition": int(cond.size), "n_baseline": int(base.size)}
    return {
        "mean_effect": float(np.mean(cond) - np.mean(base)),
        "n_condition": int(cond.size),
        "n_baseline": int(base.size),
    }


def summarize_delegation_metrics(
    delegates: list[Delegate],
    rules: list[SharedRule],
    links: list[CoordinationLink],
    event_log: EventLog,
) -> dict:
    """One dict of dicts, one key per Work Package J category — never
    merged into a single score (mirrors
    ``institution_diagnostics.summarize_institutional_metrics``)."""
    return {
        "administrative_capacity": administrative_capacity_metrics(delegates, event_log),
        "delegation_concentration": delegation_concentration_metrics(delegates),
        "accountability_intensity": accountability_intensity_metrics(event_log),
        "effective_constraint": effective_constraint_metrics(delegates, event_log),
        "legitimacy_support": legitimacy_support_metrics(delegates, rules, event_log),
        "administrative_extraction": administrative_extraction_metrics(delegates, event_log),
        "institutional_scale": institutional_scale_metrics(rules, delegates, links),
        "institutional_flexibility": institutional_flexibility_metrics(rules, event_log),
        "founder_independence": founder_independence_metrics(rules, delegates),
    }


# ---------------------------------------------------------------------------
# Work Package K: cautious, duration-gated, post-hoc classifier.
# ---------------------------------------------------------------------------
def classify_delegation(
    rule: SharedRule | None,
    delegates_at_rule: list[Delegate],
    links_at_rule: list[CoordinationLink],
    event_log: EventLog,
    final_step: int,
    min_duration_steps: int = DEFAULT_MIN_DELEGATION_DURATION_STEPS,
    persistent_duration_steps: int = DEFAULT_PERSISTENT_DELEGATION_DURATION_STEPS,
) -> dict:
    """Classify one rule's delegation history into exactly one label
    from :data:`VALID_LABELS` (Work Package K) — duration-gated,
    burn-in-aware (a delegate that has not yet held office for
    ``min_duration_steps`` is never called "persistent"), and auditable
    (the returned dict carries every count the label was derived from).
    Coordination labels ("fragmented_coordination",
    "interpatch_coordination") are only reachable when this rule has no
    delegation history at all but does have coordination links — mirrors
    Work Package I's deliberate independence from D-G. Never forces a
    label: "unclassified" is a legitimate, expected outcome (Constraint
    8/9)."""
    if rule is None or not delegates_at_rule:
        if links_at_rule:
            durations = [
                ((link.dissolution_step if link.dissolved else final_step) - link.accepted_step)
                for link in links_at_rule
            ]
            if any(d >= DEFAULT_MIN_COORDINATION_DURATION_STEPS for d in durations):
                return {"label": "interpatch_coordination", "n_delegates": 0, "n_links": len(links_at_rule)}
            return {"label": "fragmented_coordination", "n_delegates": 0, "n_links": len(links_at_rule)}
        if any(e.candidate for e in event_log.delegate_nominations if rule is not None and e.rule_id == rule.rule_id):
            return {"label": "attempted_delegation", "n_delegates": 0, "n_links": 0}
        return {"label": "no_delegation", "n_delegates": 0, "n_links": 0}

    tenures = []
    for d in delegates_at_rule:
        end = d.removal_step if d.removal_step is not None else final_step
        tenures.append(max(0, end - d.start_step))
    max_tenure = max(tenures) if tenures else 0
    n_delegates = len(delegates_at_rule)

    total_attempts = sum(sum(d.task_attempts.values()) for d in delegates_at_rule)
    total_successes = sum(sum(d.task_successes.values()) for d in delegates_at_rule)
    completion_rate = _safe_ratio(total_successes, total_attempts)

    n_audits = sum(
        1 for e in event_log.audits if any(e.delegate_id == d.delegate_id for d in delegates_at_rule)
    )
    n_recalls_succeeded = sum(
        1 for e in event_log.recalls if e.succeeded and any(e.delegate_id == d.delegate_id for d in delegates_at_rule)
    )
    n_appeals_upheld = sum(
        1 for e in event_log.appeals
        if e.upheld and e.delegate_id is not None and any(e.delegate_id == d.delegate_id for d in delegates_at_rule)
    )
    any_misconduct = any(d.appropriated_total > 0 or d.effort_withheld_count > 0 for d in delegates_at_rule)

    if max_tenure < min_duration_steps:
        label = "delegate_selected"
    elif n_delegates >= 2 and all(t < min_duration_steps for t in tenures[:-1]):
        # Multiple delegates, and every predecessor's tenure was itself
        # short -- turnover without any one holder settling in.
        label = "unstable_delegation"
    elif total_attempts == 0:
        label = "administratively_inactive"
    elif not (completion_rate == completion_rate):  # NaN guard, unreachable given total_attempts>0 above
        label = "unclassified"
    elif any_misconduct and (n_recalls_succeeded > 0 or n_appeals_upheld > 0):
        label = "accountable_delegation"
    elif any_misconduct and n_audits > 0 and n_recalls_succeeded == 0 and n_appeals_upheld == 0:
        label = "weakly_constrained_delegation"
    elif max_tenure >= persistent_duration_steps and completion_rate >= 0.3:
        label = "persistent_delegation"
    elif completion_rate < 0.15:
        label = "administratively_inactive"
    elif completion_rate >= 0.5:
        label = "administratively_functional"
    else:
        label = "unclassified"

    assert label in VALID_LABELS
    return {
        "label": label,
        "n_delegates": n_delegates,
        "max_tenure_steps": max_tenure,
        "task_completion_rate": completion_rate,
        "n_audits": n_audits,
        "n_recalls_succeeded": n_recalls_succeeded,
        "n_appeals_upheld": n_appeals_upheld,
        "any_misconduct": any_misconduct,
    }


# ---------------------------------------------------------------------------
# Level 1.1b, Work Package H: audited classifier vs. historical classifier.
# ---------------------------------------------------------------------------
def classify_delegation_audited(
    rule: SharedRule | None,
    delegates_at_rule: list[Delegate],
    links_at_rule: list[CoordinationLink],
    event_log: EventLog,
    final_step: int,
    min_duration_steps: int = DEFAULT_MIN_DELEGATION_DURATION_STEPS,
    persistent_duration_steps: int = DEFAULT_PERSISTENT_DELEGATION_DURATION_STEPS,
) -> dict:
    """Same label vocabulary, same duration-gating, same
    no-delegation/coordination/tenure/completion-rate branches as
    :func:`classify_delegation` (the "historical" classifier this
    milestone found conflated accountability *activity* with
    accountability *effective constraint* — Work Package E) —
    deliberately NOT a rewrite, a byte-for-byte structural copy with
    exactly two ground-truth corrections applied to the accountability-
    dependent branches:

    1. ``classify_delegation`` counts ANY audit as evidence toward
       "weakly_constrained_delegation" and ANY vote-succeeded recall
       (``RecallEvent.succeeded``, regardless of whether the recall
       actually clawed back any funds) toward "accountable_delegation".
       This audited version additionally requires a REALIZED true-
       positive detection (``AuditEvent.outcome == "true_positive"``)
       before a recall/appeal outcome can count toward
       "accountable_delegation" at all — mirrors
       ``observer/accountability_diagnostics.effective_constraint``'s
       own realized-detection requirement (Work Package E).
    2. ``classify_delegation``'s ``n_appeals_upheld`` counts EVERY
       upheld appeal, including one that wrongly overturned a
       genuinely justified sanction (``was_false_sanction=False``,
       ``upheld=True`` — an "unjustified overturn" in
       ``accountability_diagnostics``'s own vocabulary) as evidence of
       "accountable_delegation". That is backwards: an unjustified
       overturn is a failure of the appeals process, not a success of
       it. This audited version only counts an upheld appeal toward
       "accountable_delegation" when ``was_false_sanction=True`` (a
       genuinely corrective outcome).

    Neither correction changes ``VALID_LABELS`` or any non-
    accountability branch (duration-gating, coordination, tenure,
    completion-rate thresholds are untouched) — this function exists
    to answer exactly one question: does correcting the accountability
    ground-truth requirement change which rules get called
    "accountable_delegation," and by how much? (See
    ``experiments/level11b_audited_classifier_comparison.py``.)"""
    if rule is None or not delegates_at_rule:
        # Identical to classify_delegation -- no accountability logic
        # is reachable in the no-delegation/coordination branch.
        if links_at_rule:
            durations = [
                ((link.dissolution_step if link.dissolved else final_step) - link.accepted_step)
                for link in links_at_rule
            ]
            if any(d >= DEFAULT_MIN_COORDINATION_DURATION_STEPS for d in durations):
                return {"label": "interpatch_coordination", "n_delegates": 0, "n_links": len(links_at_rule)}
            return {"label": "fragmented_coordination", "n_delegates": 0, "n_links": len(links_at_rule)}
        if any(e.candidate for e in event_log.delegate_nominations if rule is not None and e.rule_id == rule.rule_id):
            return {"label": "attempted_delegation", "n_delegates": 0, "n_links": 0}
        return {"label": "no_delegation", "n_delegates": 0, "n_links": 0}

    tenures = []
    for d in delegates_at_rule:
        end = d.removal_step if d.removal_step is not None else final_step
        tenures.append(max(0, end - d.start_step))
    max_tenure = max(tenures) if tenures else 0
    n_delegates = len(delegates_at_rule)

    total_attempts = sum(sum(d.task_attempts.values()) for d in delegates_at_rule)
    total_successes = sum(sum(d.task_successes.values()) for d in delegates_at_rule)
    completion_rate = _safe_ratio(total_successes, total_attempts)

    n_audits = sum(
        1 for e in event_log.audits if any(e.delegate_id == d.delegate_id for d in delegates_at_rule)
    )
    # -- Correction 1: realized detection, not mere audit occurrence. --
    n_true_positive_audits = sum(
        1 for e in event_log.audits
        if e.outcome == "true_positive" and any(e.delegate_id == d.delegate_id for d in delegates_at_rule)
    )
    n_recalls_succeeded = sum(
        1 for e in event_log.recalls if e.succeeded and any(e.delegate_id == d.delegate_id for d in delegates_at_rule)
    )
    n_recalls_succeeded_with_realized_recovery = sum(
        1 for e in event_log.recalls
        if e.succeeded and e.recovered_funds > 0.0 and any(e.delegate_id == d.delegate_id for d in delegates_at_rule)
    )
    # -- Correction 2: only a genuinely corrective (was_false_sanction)
    # upheld appeal counts -- an unjustified overturn never does. --
    n_appeals_upheld = sum(
        1 for e in event_log.appeals
        if e.upheld and e.delegate_id is not None and any(e.delegate_id == d.delegate_id for d in delegates_at_rule)
    )
    n_appeals_justified_upheld = sum(
        1 for e in event_log.appeals
        if e.upheld and e.was_false_sanction and e.delegate_id is not None
        and any(e.delegate_id == d.delegate_id for d in delegates_at_rule)
    )
    any_misconduct = any(d.appropriated_total > 0 or d.effort_withheld_count > 0 for d in delegates_at_rule)

    realized_accountability = (
        n_true_positive_audits > 0
        and (n_recalls_succeeded_with_realized_recovery > 0 or n_appeals_justified_upheld > 0)
    )

    if max_tenure < min_duration_steps:
        label = "delegate_selected"
    elif n_delegates >= 2 and all(t < min_duration_steps for t in tenures[:-1]):
        label = "unstable_delegation"
    elif total_attempts == 0:
        label = "administratively_inactive"
    elif not (completion_rate == completion_rate):  # NaN guard, unreachable given total_attempts>0 above
        label = "unclassified"
    elif any_misconduct and realized_accountability:
        label = "accountable_delegation"
    elif any_misconduct and n_audits > 0 and not realized_accountability:
        label = "weakly_constrained_delegation"
    elif max_tenure >= persistent_duration_steps and completion_rate >= 0.3:
        label = "persistent_delegation"
    elif completion_rate < 0.15:
        label = "administratively_inactive"
    elif completion_rate >= 0.5:
        label = "administratively_functional"
    else:
        label = "unclassified"

    assert label in VALID_LABELS
    return {
        "label": label,
        "n_delegates": n_delegates,
        "max_tenure_steps": max_tenure,
        "task_completion_rate": completion_rate,
        "n_audits": n_audits,
        "n_true_positive_audits": n_true_positive_audits,
        "n_recalls_succeeded": n_recalls_succeeded,
        "n_recalls_succeeded_with_realized_recovery": n_recalls_succeeded_with_realized_recovery,
        "n_appeals_upheld": n_appeals_upheld,
        "n_appeals_justified_upheld": n_appeals_justified_upheld,
        "any_misconduct": any_misconduct,
        "realized_accountability": realized_accountability,
    }
