"""Level 1.0, Work Packages J/K: observer-side institutional metrics and
the conservative proto-institution diagnostic.

Same discipline as every other observer module (``dev_mem/project_vision.
md`` §5): every function here is a pure function of a read-only snapshot
(an ``EventLog``, a list of ``SharedRule`` instances, a list of agents);
nothing here is ever read by any decision function in ``simulation.py``/
``agents/``/``rules/``. "Proto-institution" and every label below are
observer-side vocabulary only — the generative layer never sees or acts on
them (see ``rules/__init__.py``'s docstring, ``agents/agent.py::
FORBIDDEN_ATTRIBUTE_SUBSTRINGS``).

Work Package J deliberately keeps its categories (formation, persistence,
membership, compliance/enforcement, ecological effects, welfare/
distribution, social effects) as *separate* dictionaries rather than one
combined score — the milestone's explicit "do not combine into one score."

Work Package K's :func:`classify_rule` applies the milestone's own
conservative criteria (Constraint/Work-Package K: collective recognition,
behavioral relevance, minimum-duration persistence, founder independence,
recorded social reproduction, recorded lineage, violation possibility, and
nontrivial cost) and only ever returns the milestone's own cautious label
vocabulary -- never a "mature governance" term. Classification here scopes
to a single :class:`~abm_governance.rules.shared_rule.SharedRule` *instance*
(one proposal-to-dissolution episode); a lineage that survives across a
dissolution/reconstruction pair is two instances sharing a
``rule_lineage_id``/``parent_rule_lineage_id`` chain -- see
:func:`lineage_chain` for stitching instances of the same lineage together
before asking whether a *lineage* (not merely one instance) persisted.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from abm_governance.core.events import EventLog
from abm_governance.rules.shared_rule import SharedRule

#: Work Package K default thresholds (documented, overridable — same
#: convention as every other observer-layer threshold in this project,
#: e.g. ``observer/niche_metrics.py``'s occupancy region thresholds).
DEFAULT_MIN_DURATION_STEPS = 30
DEFAULT_PERSISTENT_DURATION_STEPS = 100

VALID_LABELS = (
    "no_proposal",
    "proposal_rejected",
    "short_lived_convention",
    "founder_dependent_arrangement",
    "proto_institution",
    "persistent_proto_institution",
    "dissolved",
    "reconstructed",
    "unclassified",
)


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else float("nan")


# ---------------------------------------------------------------------------
# Work Package J: observer metrics, one category per function.
# ---------------------------------------------------------------------------
def formation_metrics(event_log: EventLog) -> dict:
    n_proposals = len(event_log.rule_proposals)
    n_adoptions = len(event_log.rule_adoptions)
    n_rejections = len(event_log.rule_rejections)
    n_reconstructions = sum(1 for e in event_log.rule_proposals if e.origin == "mutation")
    return {
        "n_proposals": n_proposals,
        "n_adoptions": n_adoptions,
        "n_rejections": n_rejections,
        "n_reconstruction_attempts": n_reconstructions,
        "adoption_rate": _safe_ratio(n_adoptions, n_proposals),
    }


def persistence_metrics(rules: list[SharedRule], final_step: int) -> dict:
    if not rules:
        return {
            "n_rule_instances": 0, "mean_lifetime_steps": float("nan"),
            "median_lifetime_steps": float("nan"), "n_founder_independent": 0,
            "founder_independence_rate": float("nan"), "n_still_active_at_run_end": 0,
        }
    lifetimes = []
    founder_independent = 0
    still_active = 0
    for r in rules:
        end = r.dissolution_step if r.dissolved else final_step
        lifetimes.append(max(0, end - r.founding_step))
        if not r.active:
            still_active += 0
        else:
            still_active += 1
        if r.dissolved and not r.dissolution_reason == "membership_below_floor":
            pass
        if r.dissolved:
            # founder-independent lifetime: did the rule survive at all
            # past a step where the founder was no longer a member?
            founder_independent += 0 if r.founder_id in r.members else 1
        elif r.founder_id not in r.members:
            founder_independent += 1
    return {
        "n_rule_instances": len(rules),
        "mean_lifetime_steps": float(np.mean(lifetimes)),
        "median_lifetime_steps": float(np.median(lifetimes)),
        "n_founder_independent": founder_independent,
        "founder_independence_rate": _safe_ratio(founder_independent, len(rules)),
        "n_still_active_at_run_end": still_active,
    }


def membership_metrics(rules: list[SharedRule], event_log: EventLog) -> dict:
    if not rules:
        return {"mean_peak_members": float("nan"), "n_joins": 0, "n_exits": 0, "n_exclusions": 0}
    joins = sum(1 for e in event_log.memberships if e.kind == "join")
    exits = sum(1 for e in event_log.memberships if e.kind == "exit")
    exclusions = sum(1 for e in event_log.memberships if e.kind == "exclusion")
    peak_by_rule: dict[int, int] = {}
    for e in event_log.memberships:
        peak_by_rule[e.rule_id] = max(peak_by_rule.get(e.rule_id, 0), 1)
    for r in rules:
        peak_by_rule[r.rule_id] = max(peak_by_rule.get(r.rule_id, 0), r.n_members)
    return {
        "mean_peak_members": float(np.mean(list(peak_by_rule.values()))) if peak_by_rule else float("nan"),
        "n_joins": joins,
        "n_exits": exits,
        "n_exclusions": exclusions,
    }


def compliance_enforcement_metrics(event_log: EventLog) -> dict:
    n_compliant = sum(1 for e in event_log.compliances if e.complied)
    n_violated = sum(1 for e in event_log.compliances if e.violated)
    n_total = n_compliant + n_violated
    n_altered = sum(1 for e in event_log.compliances if e.enforcement_altered_action)

    outcomes = [e.outcome for e in event_log.monitorings]
    n_tp = outcomes.count("true_positive")
    n_fp = outcomes.count("false_positive")
    n_tn = outcomes.count("true_negative")
    n_fn = outcomes.count("false_negative")

    n_sanctions = len(event_log.sanctions)
    n_false_sanctions = sum(1 for e in event_log.sanctions if e.false_sanction)
    total_sanction_cost = sum(e.cost for e in event_log.sanctions)
    total_monitoring_cost = sum(e.cost_to_monitor for e in event_log.monitorings)

    return {
        "compliance_rate": _safe_ratio(n_compliant, n_total),
        "violation_rate": _safe_ratio(n_violated, n_total),
        "enforcement_altered_action_rate": _safe_ratio(n_altered, n_total),
        "monitoring_true_positive_rate": _safe_ratio(n_tp, n_tp + n_fn),
        "monitoring_false_positive_rate_observed": _safe_ratio(n_fp, n_fp + n_tn),
        "n_sanctions": n_sanctions,
        "false_sanction_rate": _safe_ratio(n_false_sanctions, n_sanctions),
        "total_sanction_cost": total_sanction_cost,
        "total_monitoring_cost": total_monitoring_cost,
    }


def welfare_metrics(agents: list, rules: list[SharedRule]) -> dict:
    from abm_governance.observer.metrics import gini

    member_ids = {aid for r in rules for aid in r.members}
    member_resources = [a.resources for a in agents if a.agent_id in member_ids and a.alive]
    nonmember_resources = [a.resources for a in agents if a.agent_id not in member_ids and a.alive]
    return {
        "mean_member_resources": float(np.mean(member_resources)) if member_resources else float("nan"),
        "mean_nonmember_resources": float(np.mean(nonmember_resources)) if nonmember_resources else float("nan"),
        "member_gini": gini(member_resources) if member_resources else float("nan"),
        "nonmember_gini": gini(nonmember_resources) if nonmember_resources else float("nan"),
        "overall_gini": gini([a.resources for a in agents if a.alive]),
    }


def social_effects_metrics(agents: list, event_log: EventLog, rules: list[SharedRule]) -> dict:
    """Cooperation among members vs. nonmembers -- reported completely
    separately from institutional compliance (Constraint 13: "social
    cooperation must remain independent from institutional compliance" —
    this function never mixes the two ledgers, it only reports both,
    side by side, from the pre-existing, unmodified ``InteractionEvent``
    log)."""
    from abm_governance.interactions.game import COOPERATE

    member_ids = {aid for r in rules for aid in r.members}
    member_coop = member_total = nonmember_coop = nonmember_total = 0
    for e in event_log.interactions:
        for aid, action in ((e.agent_a, e.action_a), (e.agent_b, e.action_b)):
            if aid in member_ids:
                member_total += 1
                member_coop += action == COOPERATE
            else:
                nonmember_total += 1
                nonmember_coop += action == COOPERATE
    return {
        "member_cooperation_rate": _safe_ratio(member_coop, member_total),
        "nonmember_cooperation_rate": _safe_ratio(nonmember_coop, nonmember_total),
    }


def summarize_institutional_metrics(agents: list, event_log: EventLog, rules: list[SharedRule], final_step: int) -> dict:
    """One dict of dicts, one key per Work Package J category — never
    merged into a single score."""
    return {
        "formation": formation_metrics(event_log),
        "persistence": persistence_metrics(rules, final_step),
        "membership": membership_metrics(rules, event_log),
        "compliance_enforcement": compliance_enforcement_metrics(event_log),
        "welfare": welfare_metrics(agents, rules),
        "social_effects": social_effects_metrics(agents, event_log, rules),
    }


# ---------------------------------------------------------------------------
# Work Package K: proto-institution criteria + cautious classification.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ProtoInstitutionCriteria:
    collective_recognition: bool
    behavioral_relevance: bool
    minimum_duration: bool
    founder_independence: bool
    social_reproduction_recorded: bool
    lineage_recorded: bool
    violation_possibility_remains: bool
    nontrivial_cost: bool

    @property
    def all_met(self) -> bool:
        return all(
            (
                self.collective_recognition, self.behavioral_relevance, self.minimum_duration,
                self.founder_independence, self.social_reproduction_recorded, self.lineage_recorded,
                self.violation_possibility_remains, self.nontrivial_cost,
            )
        )


def evaluate_proto_institution_criteria(
    rule: SharedRule,
    event_log: EventLog,
    final_step: int,
    min_duration_steps: int = DEFAULT_MIN_DURATION_STEPS,
) -> ProtoInstitutionCriteria:
    end = rule.dissolution_step if rule.dissolved else final_step
    duration = max(0, end - rule.founding_step)

    own_compliance = [e for e in event_log.compliances if e.rule_id == rule.rule_id]
    own_memberships = [e for e in event_log.memberships if e.rule_id == rule.rule_id]
    own_proposal = next((e for e in event_log.rule_proposals if e.rule_lineage_id == rule.rule_lineage_id), None)
    own_monitorings = [e for e in event_log.monitorings if e.rule_id == rule.rule_id]
    own_sanctions = [e for e in event_log.sanctions if e.rule_id == rule.rule_id]

    peak_members = max([rule.n_members] + [1 for _ in own_memberships if _.kind == "join"] + [0])
    collective_recognition = peak_members > 1 or len(rule.members) > 1

    behavioral_relevance = any(e.enforcement_altered_action for e in own_compliance)

    founder_independence = (rule.founder_id not in rule.members) and (
        rule.dissolved and not rule.dissolution_reason == "membership_below_floor" and duration > 0
        or not rule.dissolved
    ) and any(e.kind == "join" for e in own_memberships)

    social_reproduction_recorded = any(e.kind == "join" for e in own_memberships) or (
        own_proposal is not None and own_proposal.origin in ("mutation", "imitation")
    )

    lineage_recorded = own_proposal is not None and (
        own_proposal.origin == "proposal" or own_proposal.parent_rule_lineage_id is not None
    )

    violation_possibility_remains = any(e.violated for e in own_compliance) or rule.violation_count > 0

    nontrivial_cost = (
        any(e.cost_to_monitor > 0 for e in own_monitorings)
        or any(e.cost > 0 for e in own_sanctions)
        or any(e.kind == "exit" and e.reason == "voluntary" for e in own_memberships)
    )

    return ProtoInstitutionCriteria(
        collective_recognition=collective_recognition,
        behavioral_relevance=behavioral_relevance,
        minimum_duration=duration >= min_duration_steps,
        founder_independence=founder_independence,
        social_reproduction_recorded=social_reproduction_recorded,
        lineage_recorded=lineage_recorded,
        violation_possibility_remains=violation_possibility_remains,
        nontrivial_cost=nontrivial_cost,
    )


def classify_rule(
    rule: SharedRule | None,
    event_log: EventLog,
    patch_id: int,
    final_step: int,
    min_duration_steps: int = DEFAULT_MIN_DURATION_STEPS,
    persistent_duration_steps: int = DEFAULT_PERSISTENT_DURATION_STEPS,
) -> dict:
    """Cautious, observer-side classification of one rule instance (or,
    if ``rule`` is ``None``, of a patch that never produced an adopted
    rule at all). Returns ``{"label": ..., "criteria": ProtoInstitutionCriteria | None, "duration_steps": int | None}``
    -- never a "mature governance" label (see ``VALID_LABELS``)."""
    proposals_here = [e for e in event_log.rule_proposals if e.patch_id == patch_id]
    adoptions_here = [e for e in event_log.rule_adoptions if e.patch_id == patch_id]

    if rule is None:
        if not proposals_here:
            return {"label": "no_proposal", "criteria": None, "duration_steps": None}
        return {"label": "proposal_rejected", "criteria": None, "duration_steps": None}

    end = rule.dissolution_step if rule.dissolved else final_step
    duration = max(0, end - rule.founding_step)
    criteria = evaluate_proto_institution_criteria(rule, event_log, final_step, min_duration_steps)

    is_reconstruction = any(
        e.rule_lineage_id == rule.rule_lineage_id and e.origin == "mutation" and e.parent_rule_lineage_id is not None
        for e in event_log.rule_proposals
    )

    if not criteria.minimum_duration:
        label = "short_lived_convention"
    elif not criteria.founder_independence:
        label = "founder_dependent_arrangement"
    elif criteria.all_met and duration >= persistent_duration_steps:
        label = "persistent_proto_institution"
    elif criteria.all_met:
        label = "proto_institution"
    else:
        label = "unclassified"

    if is_reconstruction:
        label = "reconstructed"
    elif rule.dissolved and label not in ("short_lived_convention", "founder_dependent_arrangement"):
        label = "dissolved"

    assert label in VALID_LABELS
    return {"label": label, "criteria": criteria, "duration_steps": duration}


# ---------------------------------------------------------------------------
# Level 1.1, Work Package B: welfare accounting repair.
#
# ``welfare_metrics`` above already returns NaN (not 0.0) for an empty
# group -- verified directly by
# tests/test_level11_welfare_accounting.py::test_atomic_baseline_reports_nan_not_zero_member_mean,
# so requirement 1 was already met by the Level 1.0 implementation (see
# docs/level1.0_audit_supplement.md). What was missing is the full
# denominator/numerator export, the population-weighted overall mean, and
# an explicit within-patch member/nonmember contrast that never claims to
# be a causal effect (requirements 3-5) -- ``welfare_accounting`` below is
# additive, not a replacement for ``welfare_metrics`` (existing callers/
# tests are unaffected).
# ---------------------------------------------------------------------------
def welfare_accounting(agents: list, rules: list[SharedRule], patch_system=None) -> dict:
    """Full welfare-accounting export (Work Package B requirement 3).
    Member/nonmember status is determined the same way as
    ``welfare_metrics`` (any rule's current membership); an
    ``atomic_baseline`` run (``rules=[]``) reports ``member_count=0`` and
    every member-side numerator/mean as NaN, never a misleading 0.0.

    This function is strictly *descriptive*: it never claims that a raw
    member/nonmember difference is a causal effect of membership
    (selection into membership is not accounted for here — Work Package
    B requirements 4-5). Callers wanting a causal estimate must use a
    matched-seed counterfactual design (see
    ``experiments/level11_stage5_causal_decomposition.py``), never this
    function's own contrast alone."""
    member_ids = {aid for r in rules for aid in r.members}
    living = [a for a in agents if a.alive]
    member_agents = [a for a in living if a.agent_id in member_ids]
    nonmember_agents = [a for a in living if a.agent_id not in member_ids]

    member_count = len(member_agents)
    nonmember_count = len(nonmember_agents)
    member_numerator = float(sum(a.resources for a in member_agents))
    nonmember_numerator = float(sum(a.resources for a in nonmember_agents))
    overall_numerator = float(sum(a.resources for a in living))
    overall_count = len(living)

    member_mean = (member_numerator / member_count) if member_count else float("nan")
    nonmember_mean = (nonmember_numerator / nonmember_count) if nonmember_count else float("nan")
    overall_mean = (overall_numerator / overall_count) if overall_count else float("nan")

    within_patch_contrasts = []
    if patch_system is not None:
        for pid, patch in patch_system.patches.items():
            patch_members = [a for a in member_agents if a.patch_id == pid]
            patch_nonmembers = [a for a in nonmember_agents if a.patch_id == pid]
            if patch_members and patch_nonmembers:
                m_mean = sum(a.resources for a in patch_members) / len(patch_members)
                nm_mean = sum(a.resources for a in patch_nonmembers) / len(patch_nonmembers)
                within_patch_contrasts.append(m_mean - nm_mean)

    return {
        "member_count": member_count,
        "nonmember_count": nonmember_count,
        "member_resource_numerator": member_numerator,
        "nonmember_resource_numerator": nonmember_numerator,
        "member_denominator_valid": member_count > 0,
        "nonmember_denominator_valid": nonmember_count > 0,
        "mean_member_resources": member_mean,
        "mean_nonmember_resources": nonmember_mean,
        "population_weighted_overall_mean": overall_mean,
        "descriptive_member_minus_nonmember_diff": (
            (member_mean - nonmember_mean) if (member_count and nonmember_count) else float("nan")
        ),
        "within_patch_contrast_mean": (
            float(np.mean(within_patch_contrasts)) if within_patch_contrasts else float("nan")
        ),
        "within_patch_contrast_n_patches": len(within_patch_contrasts),
        "is_causal_estimate": False,
        "note": (
            "descriptive_member_minus_nonmember_diff and within_patch_contrast_mean are "
            "selection-confounded descriptive contrasts, not causal effects of membership -- "
            "see docs/level1.1_scientific_note.md for the descriptive-vs-causal distinction."
        ),
    }


def seed_level_welfare_contrast(per_seed_diffs: list[float]) -> dict:
    """Aggregate a list of already-computed
    ``descriptive_member_minus_nonmember_diff`` values, one per seed, into
    a seed-level summary (Work Package B requirement 3's "seed-level
    aggregate contrast") — the seed, not the patch-run, is the unit
    averaged over here; use
    ``observer/replication_units.py::seed_clustered_bootstrap_ci`` for an
    uncertainty interval around this same quantity."""
    valid = [d for d in per_seed_diffs if d is not None and not (isinstance(d, float) and np.isnan(d))]
    return {
        "n_seeds": len(per_seed_diffs),
        "n_seeds_valid": len(valid),
        "mean_seed_level_contrast": float(np.mean(valid)) if valid else float("nan"),
    }


# ---------------------------------------------------------------------------
# Level 1.1, Work Package C: persistence and reconstruction eligibility.
# ---------------------------------------------------------------------------
def eligible_active_rules(
    rules: list[SharedRule],
    event_step: int,
    min_duration_steps: int = DEFAULT_MIN_DURATION_STEPS,
) -> list[SharedRule]:
    """An eligible pre-event rule (Work Package C requirement 1): active
    at ``event_step``, has existed for at least ``min_duration_steps`` as
    of that step, has a valid ``rule_lineage_id``, and is not already
    marked dissolved as of that step."""
    eligible = []
    for r in rules:
        if r.founding_step > event_step:
            continue
        if r.dissolved and r.dissolution_step is not None and r.dissolution_step <= event_step:
            continue
        if r.rule_lineage_id is None:
            continue
        if (event_step - r.founding_step) < min_duration_steps:
            continue
        eligible.append(r)
    return eligible


def survival_after_event(eligible_rules: list[SharedRule], active_rule_ids_after: set) -> dict:
    """Work Package C requirement 2: ``P(active after event | eligible
    active rule before event)`` — never divides by an unfiltered rule
    count."""
    n_eligible = len(eligible_rules)
    n_surviving = sum(1 for r in eligible_rules if r.rule_id in active_rule_ids_after)
    return {
        "n_eligible_active_rules": n_eligible,
        "n_surviving_rules": n_surviving,
        "survival_rate": _safe_ratio(n_surviving, n_eligible),
    }


def eligible_dissolutions(
    rules: list[SharedRule],
    window_start: int,
    window_end: int,
    min_duration_steps: int = DEFAULT_MIN_DURATION_STEPS,
) -> list[SharedRule]:
    """Dissolutions eligible for a reconstruction-eligibility analysis
    (Work Package C requirement 3's denominator): dissolved within
    ``(window_start, window_end]``, met the minimum duration at
    dissolution, and carries a valid lineage id."""
    out = []
    for r in rules:
        if not r.dissolved or r.dissolution_step is None:
            continue
        if not (window_start < r.dissolution_step <= window_end):
            continue
        if r.rule_lineage_id is None:
            continue
        if (r.dissolution_step - r.founding_step) < min_duration_steps:
            continue
        out.append(r)
    return out


def _rule_content_distance(a, b) -> float:
    """Euclidean distance between two ``RuleParameters`` over their six
    fields — Work Package C's "rule-content distance" export."""
    fields_a = a.as_dict()
    fields_b = b.as_dict()
    return float(np.sqrt(sum((fields_a[k] - fields_b[k]) ** 2 for k in fields_a)))


def reconstruction_metrics(
    eligible_dissolved: list[SharedRule],
    all_rules: list[SharedRule],
    event_log: EventLog,
    persistent_duration_steps: int = DEFAULT_PERSISTENT_DURATION_STEPS,
) -> dict:
    """Work Package C requirements 2-5: distinguishes reconstruction
    *proposal* (a mutation-origin ``RuleProposalEvent`` naming this
    lineage as parent), *adoption* (an actual ``SharedRule`` instance
    whose ``parent_rule_lineage_id`` matches), and *persistence* (that
    child rule itself lasting >= ``persistent_duration_steps`` or still
    active). Every counted instance carries a real
    ``parent_rule_lineage_id`` — never inferred from parameter similarity
    alone (the same discipline as Level 1.0's own Work Package K
    ``lineage_recorded`` criterion)."""
    n_eligible = len(eligible_dissolved)
    n_attempts = 0
    n_adopted = 0
    n_persistent = 0
    times_to_reconstruction = []
    content_distances = []
    lineage_hop_distances = []
    for r in eligible_dissolved:
        proposals = [
            e for e in event_log.rule_proposals
            if e.parent_rule_lineage_id == r.rule_lineage_id and e.patch_id == r.patch_id and e.step > r.dissolution_step
        ]
        if proposals:
            n_attempts += 1
            times_to_reconstruction.append(proposals[0].step - r.dissolution_step)
        children = [cr for cr in all_rules if cr.parent_rule_lineage_id == r.rule_lineage_id]
        if children:
            n_adopted += 1
            for child in children:
                content_distances.append(_rule_content_distance(r.parameters, child.parameters))
                lineage_hop_distances.append(1)  # direct mutation: one lineage hop by construction
                child_duration = (child.dissolution_step if child.dissolved else None)
                if not child.dissolved:
                    n_persistent += 1  # still active counts as persistent-so-far
                elif child_duration is not None and (child_duration - child.founding_step) >= persistent_duration_steps:
                    n_persistent += 1
    return {
        "n_eligible_dissolutions": n_eligible,
        "n_reconstruction_attempts": n_attempts,
        "n_reconstruction_adoptions": n_adopted,
        "n_persistent_reconstructions": n_persistent,
        "reconstruction_attempt_rate": _safe_ratio(n_attempts, n_eligible),
        "reconstruction_adoption_rate": _safe_ratio(n_adopted, n_eligible),
        "persistent_reconstruction_rate": _safe_ratio(n_persistent, n_eligible),
        "mean_time_to_reconstruction_steps": (
            float(np.mean(times_to_reconstruction)) if times_to_reconstruction else float("nan")
        ),
        "mean_lineage_distance_hops": (
            float(np.mean(lineage_hop_distances)) if lineage_hop_distances else float("nan")
        ),
        "mean_rule_content_distance": float(np.mean(content_distances)) if content_distances else float("nan"),
    }


def lineage_chain(lineage_id: int, all_rules: list[SharedRule]) -> list[SharedRule]:
    """Every rule instance sharing this lineage id directly, plus every
    instance whose ``parent_rule_lineage_id`` chains back to it —
    ordered by ``founding_step``. Used to ask "did this *lineage*
    persist across a dissolution/reconstruction pair" as distinct from
    "did this *instance* persist" (Work Package G)."""
    by_lineage = {r.rule_lineage_id: r for r in all_rules}
    members = [r for r in all_rules if r.rule_lineage_id == lineage_id]
    frontier = list(members)
    seen = {lineage_id}
    while frontier:
        current = frontier.pop()
        for r in all_rules:
            if r.parent_rule_lineage_id == current.rule_lineage_id and r.rule_lineage_id not in seen:
                seen.add(r.rule_lineage_id)
                members.append(r)
                frontier.append(r)
    return sorted(members, key=lambda r: r.founding_step)
