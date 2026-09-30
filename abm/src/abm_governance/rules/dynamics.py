"""Round functions implementing Work Packages C-H (proposal, adoption,
membership, compliance, monitoring, collective sanctioning, lineage,
amendment, dissolution) on top of the entities defined in
``rules/shared_rule.py``.

Step ordering (see ``simulation.py::Simulation._ecological_round`` and
``Simulation._rule_formation_round``):

1. Inside ``_ecological_round``, *before* each patch's extraction/
   maintenance requests are submitted: every member of an active rule has
   its compliance decided (:func:`decide_rule_compliance`, using only
   this agent's own traits, its own ecological policy's *intended*
   request, and this rule's own parameters — never a global quantity),
   and the request actually submitted is adjusted accordingly
   (:func:`apply_rule_compliance`). This keeps the intended-vs-actual
   distinction (Work Package I) anchored to the same request pipeline
   every other agent uses, rather than a parallel mechanism.
2. After ``_ecological_round`` has produced this step's realized
   extraction/maintenance and logged one :class:`~abm_governance.core.
   events.ComplianceEvent` per rule member (ground truth for step 3),
   ``Simulation._rule_formation_round`` runs, in order:
   monitoring -> sanctioning -> proposal/adoption -> membership ->
   amendment -> dissolution. Monitoring/sanctioning consume this step's
   *already-realized* compliance ground truth (never influence it
   retroactively); proposal/adoption/membership/amendment/dissolution
   only ever change what is active *next* step.

Every function below takes only local, already-in-scope arguments (a
single agent, a single rule, a single patch's eligible-member list, this
step's config/rng) — nothing here reads or writes any global/population-
wide/cross-patch quantity, per the milestone's Constraint 3.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from abm_governance.agents.adaptation import _stable_sigmoid
from abm_governance.agents.agent import Agent
from abm_governance.core.config import SimulationConfig
from abm_governance.core.entrenchment import (
    entrenchment_adjusted_threshold,
    entrenchment_level,
    entrenchment_survival_probability,
)
from abm_governance.core.events import (
    ComplianceEvent,
    EventLog,
    LegitimacyEvent,
    MembershipEvent,
    MonitoringEvent,
    RuleAdoptionEvent,
    RuleAmendmentEvent,
    RuleDissolutionEvent,
    RuleProposalEvent,
    RuleRejectionEvent,
    SanctionEvent,
)
from abm_governance.core.legitimacy import (
    legitimacy_step,
    performance_legitimacy_target,
    procedural_legitimacy_target,
)
from abm_governance.rules.shared_rule import RuleParameters, SharedRule, mutate_rule_parameters


# ---------------------------------------------------------------------------
# Work Package D: per-member compliance decision (called from inside
# Simulation._ecological_round, once per member of an active rule, before
# that member's request is submitted to its patch).
# ---------------------------------------------------------------------------
def decide_rule_compliance(
    agent: Agent,
    rule: SharedRule,
    intended_extraction_propensity: float,
    intended_maintenance_propensity: float,
    config: SimulationConfig,
    rng: np.random.Generator,
) -> bool:
    """Return ``True`` (complies) or ``False`` (violates) for one member
    this step.

    Not a solved expected-utility optimum (the milestone explicitly
    permits "bounded, noisy decision rules" — Work Package D). The
    heuristic used: a member feels *temptation* to violate only to the
    extent its own (unconstrained) ecological policy would already have
    exceeded the rule's extraction ceiling or fallen short of its
    maintenance requirement, on the same propensity scale
    ``RuleParameters`` is expressed in::

        temptation = max(0, intended_extraction_propensity - ceiling)
                   + max(0, requirement - intended_maintenance_propensity)

    If ``temptation <= 0`` the agent already satisfies the rule with no
    constraint (deterministically compliant — enforcement did not need to
    "alter" anything; see :func:`apply_rule_compliance`). Otherwise a
    logistic draw compares that temptation against the agent's own
    ``violation_tolerance`` trait and a *perceived deterrence* term
    (``rule.parameters.monitoring_intensity * rule.parameters.
    sanction_magnitude`` — the rule's own stated monitoring/sanction
    strength, a purely local quantity every member of the rule can be
    assumed aware of, not this step's *realized* enforcement, which the
    member cannot yet know when deciding)."""
    if config.randomized_pseudo_institution_mode:
        # Stage-4 condition 8 ("randomized pseudo-institution"): the
        # compliance decision deliberately ignores the rule's actual
        # content and this agent's own traits entirely -- an
        # unconditional coin flip -- so that institutional *activity and
        # cost* (monitoring/sanctioning still run normally on top of
        # whatever this returns) is matched to a real rule while the
        # rule-content-to-behavior linkage is deliberately severed (see
        # core/config.py's docstring for this field).
        return bool(rng.random() < config.randomized_pseudo_institution_compliance_probability)

    ceiling = rule.parameters.extraction_ceiling
    requirement = rule.parameters.maintenance_requirement
    temptation = max(0.0, intended_extraction_propensity - ceiling) + max(
        0.0, requirement - intended_maintenance_propensity
    )
    if temptation <= 0.0:
        return True
    deterrence = rule.parameters.monitoring_intensity * rule.parameters.sanction_magnitude
    noise = max(config.institutional_decision_noise_std, 1e-6)
    p_violate = _stable_sigmoid((temptation - agent.violation_tolerance - deterrence) / noise)
    return not (rng.random() < p_violate)


def apply_rule_compliance(
    intended_h: float,
    intended_m: float,
    rule: SharedRule,
    complied: bool,
    harvest_unit: float,
    maintenance_unit: float,
) -> tuple[float, float, bool]:
    """Return ``(actual_h, actual_m, enforcement_altered_action)``.

    A violator's request is untouched (``intended_h, intended_m,
    False``) — violation is a real possibility, never mechanically
    disallowed (Constraint 9). A complier's request is capped at the
    rule's extraction ceiling and floored at its maintenance requirement,
    both converted from the ``[0, 1]`` propensity scale to this patch's
    resource-unit scale by the same ``harvest_unit``/``maintenance_unit``
    constants :func:`~abm_governance.agents.ecological_policy.
    decide_ecological_action` uses, so a rule's content is comparable
    across patches with different unit scales. ``enforcement_altered_
    action`` is ``True`` only when the cap/floor actually bound — a
    complier whose own policy already satisfied the rule sees no change,
    which is exactly the "the agent happened to already comply" case the
    milestone's Work Package I distinguishes from "the rule changed
    behavior"."""
    if not complied:
        return intended_h, intended_m, False
    ceiling_units = rule.parameters.extraction_ceiling * harvest_unit
    floor_units = rule.parameters.maintenance_requirement * maintenance_unit
    actual_h = min(intended_h, ceiling_units)
    actual_m = max(intended_m, floor_units)
    altered = (actual_h != intended_h) or (actual_m != intended_m)
    return actual_h, actual_m, altered


# ---------------------------------------------------------------------------
# Pending-proposal bookkeeping (Work Package C). Kept as a small local
# dataclass rather than a SharedRule, since a pending proposal is not yet
# a rule (it has no members, no fund, no lineage-active status) — this
# mirrors the milestone's own "individual action -> repeated convention ->
# shared rule -> proto-institution" progression by keeping "proposed but
# not yet adopted" structurally distinct from "active."
# ---------------------------------------------------------------------------
@dataclass
class _PendingProposal:
    proposer: int
    parameters: RuleParameters
    rule_lineage_id: int
    opened_step: int
    origin: str
    parent_rule_lineage_id: int | None
    supporters: set = field(default_factory=set)


def _eligible_agents(patch_id: int, agents_by_id: dict[int, Agent], patch_system) -> list[Agent]:
    return [agents_by_id[aid] for aid in patch_system.patches[patch_id].members if agents_by_id[aid].alive]


def _support_fraction(supporters: set, eligible: list[Agent], config: SimulationConfig) -> float:
    if not eligible:
        return 0.0
    if config.adoption_process == "resource_weighted_voting":
        total_w = sum(max(a.resources, 0.0) for a in eligible)
        support_w = sum(max(a.resources, 0.0) for a in eligible if a.agent_id in supporters)
        return support_w / total_w if total_w > 0 else 0.0
    return len(supporters) / len(eligible)


def propose_rule(
    agent: Agent,
    patch_id: int,
    occupancy: float,
    config: SimulationConfig,
    rng: np.random.Generator,
    next_lineage_id: int,
    parent_rule: SharedRule | None,
) -> tuple[RuleParameters, str, int | None]:
    """Draw one proposal's content (Work Package B/C).

    Ordinarily a fresh draw from the proposer's own ``preferred_*``
    traits (``origin="proposal"``, no parent lineage — an independent
    proposal, never optimized for future patch survival). When
    ``parent_rule`` is given (this patch's most recently dissolved rule,
    passed by the caller only when the proposer happens to draw a
    reconstruction attempt — see ``Simulation._rule_formation_round``'s
    ``reconstruction_probability`` gate) the proposal is instead a
    bounded mutation of that dissolved rule's final parameters
    (``origin="mutation"``, ``parent_rule_lineage_id`` set) — true
    lineage transmission, distinguishable downstream from an
    independently-drawn proposal that merely happens to look similar."""
    if parent_rule is not None:
        params = mutate_rule_parameters(parent_rule.parameters, config.rule_mutation_std, rng)
        return params, "mutation", parent_rule.rule_lineage_id
    params = RuleParameters(
        extraction_ceiling=float(np.clip(agent.preferred_extraction_ceiling, 0.0, 1.0)),
        maintenance_requirement=float(np.clip(agent.preferred_maintenance_requirement, 0.0, 1.0)),
        monitoring_intensity=float(np.clip(agent.preferred_monitoring_intensity, 0.0, 1.0)),
        sanction_magnitude=float(np.clip(agent.preferred_sanction_magnitude, 0.0, 1.0)),
        adoption_threshold=float(np.clip(agent.preferred_adoption_threshold, 1e-3, 1.0)),
        amendment_threshold=float(np.clip(agent.preferred_amendment_threshold, 1e-3, 1.0)),
    )
    return params, "proposal", None


def proposal_and_adoption_round(
    step: int,
    patch_ids: list[int],
    agents_by_id: dict[int, Agent],
    patch_system,
    rule_registry: dict[int, SharedRule],
    pending: dict[int, _PendingProposal],
    last_dissolved_by_patch: dict[int, SharedRule],
    occupancy_snapshot: dict[int, float],
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
    id_state: dict,
) -> None:
    """Work Package C: one step of proposal opening, support
    accumulation, and adopt/reject resolution. ``id_state`` holds mutable
    ``{"next_rule_id": int, "next_lineage_id": int}`` counters (kept
    outside this module so ``Simulation`` owns their persistence across
    steps, exactly like its existing ``agent_id``/edge counters)."""
    for pid in patch_ids:
        eligible = _eligible_agents(pid, agents_by_id, patch_system)
        if not eligible:
            continue

        if pid in rule_registry and rule_registry[pid].active:
            continue  # Constraint: at most one active rule per patch.

        if pid in pending:
            proposal = pending[pid]
            proposer_agent = agents_by_id.get(proposal.proposer)
            # Support accumulation: every eligible non-proposer agent not
            # yet recorded as a supporter gets one more chance to support
            # this step (a monotonically growing set — this is "support
            # accumulation," not a single up-or-down vote).
            for member in eligible:
                if member.agent_id == proposal.proposer or member.agent_id in proposal.supporters:
                    continue
                closeness = 1.0 - min(
                    1.0,
                    abs(member.preferred_extraction_ceiling - proposal.parameters.extraction_ceiling)
                    + abs(member.preferred_maintenance_requirement - proposal.parameters.maintenance_requirement),
                )
                noise = max(config.institutional_decision_noise_std, 1e-6)
                p_support = _stable_sigmoid((member.willingness_to_join + closeness - 1.0) / noise)
                if rng.random() < p_support:
                    proposal.supporters.add(member.agent_id)

            support_frac = _support_fraction(proposal.supporters, eligible, config)
            window_expired = (step - proposal.opened_step) >= (config.proposal_window_steps - 1)
            if support_frac >= proposal.parameters.adoption_threshold:
                rule_id = id_state["next_rule_id"]
                id_state["next_rule_id"] += 1
                founding_members = frozenset(proposal.supporters | {proposal.proposer})
                new_rule = SharedRule(
                    rule_id=rule_id,
                    patch_id=pid,
                    parameters=proposal.parameters,
                    founding_step=step,
                    founder_id=proposal.proposer,
                    rule_lineage_id=proposal.rule_lineage_id,
                    members=founding_members,
                    supporters=frozenset(proposal.supporters),
                    parent_rule_lineage_id=proposal.parent_rule_lineage_id,
                )
                rule_registry[pid] = new_rule
                for aid in founding_members:
                    agents_by_id[aid].rule_member_of = rule_id
                event_log.add(
                    RuleAdoptionEvent(
                        step=step,
                        patch_id=pid,
                        rule_id=rule_id,
                        rule_lineage_id=proposal.rule_lineage_id,
                        proposer=proposal.proposer,
                        n_eligible=len(eligible),
                        n_supporters=len(proposal.supporters),
                        support_fraction=support_frac,
                        adoption_threshold=proposal.parameters.adoption_threshold,
                        adoption_process=config.adoption_process,
                        founding_members=tuple(sorted(founding_members)),
                    )
                )
                del pending[pid]
            elif window_expired:
                event_log.add(
                    RuleRejectionEvent(
                        step=step,
                        patch_id=pid,
                        proposer=proposal.proposer,
                        rule_lineage_id=proposal.rule_lineage_id,
                        n_eligible=len(eligible),
                        n_supporters=len(proposal.supporters),
                        support_fraction=support_frac,
                        adoption_threshold=proposal.parameters.adoption_threshold,
                        reason="window_expired_insufficient_support",
                    )
                )
                del pending[pid]
            continue

        # No active rule, no pending proposal: eligible agents may open one.
        occ = occupancy_snapshot.get(pid, 1.0)
        scarcity_scale = 1.0 + config.proposal_probability_scarcity_sensitivity * (1.0 - occ)
        proposers = []
        for member in eligible:
            p_propose = float(np.clip(member.proposal_probability * scarcity_scale, 0.0, 1.0))
            if rng.random() < p_propose:
                proposers.append(member)
        if not proposers:
            continue
        proposer = proposers[0]
        for other in proposers[1:]:
            event_log.add(
                RuleRejectionEvent(
                    step=step,
                    patch_id=pid,
                    proposer=other.agent_id,
                    rule_lineage_id=-1,
                    n_eligible=len(eligible),
                    n_supporters=0,
                    support_fraction=0.0,
                    adoption_threshold=other.preferred_adoption_threshold,
                    reason="superseded_same_step",
                )
            )

        parent_rule = last_dissolved_by_patch.get(pid)
        attempt_reconstruction = (
            parent_rule is not None and rng.random() < proposer.amendment_propensity
        )
        params, origin, parent_lineage = propose_rule(
            proposer, pid, occ, config, rng,
            id_state["next_lineage_id"], parent_rule if attempt_reconstruction else None,
        )
        if parent_lineage is None:
            lineage_id = id_state["next_lineage_id"]
            id_state["next_lineage_id"] += 1
        else:
            lineage_id = id_state["next_lineage_id"]
            id_state["next_lineage_id"] += 1
        event_log.add(
            RuleProposalEvent(
                step=step,
                patch_id=pid,
                proposer=proposer.agent_id,
                rule_lineage_id=lineage_id,
                extraction_ceiling=params.extraction_ceiling,
                maintenance_requirement=params.maintenance_requirement,
                monitoring_intensity=params.monitoring_intensity,
                sanction_magnitude=params.sanction_magnitude,
                adoption_threshold=params.adoption_threshold,
                amendment_threshold=params.amendment_threshold,
                origin=origin,
                parent_rule_lineage_id=parent_lineage,
            )
        )
        pending[pid] = _PendingProposal(
            proposer=proposer.agent_id,
            parameters=params,
            rule_lineage_id=lineage_id,
            opened_step=step,
            origin=origin,
            parent_rule_lineage_id=parent_lineage,
        )


# ---------------------------------------------------------------------------
# Work Package D: membership (join / leave) for already-active rules.
# ---------------------------------------------------------------------------
def membership_round(
    step: int,
    rule_registry: dict[int, SharedRule],
    agents_by_id: dict[int, Agent],
    patch_system,
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
) -> None:
    noise = max(config.institutional_decision_noise_std, 1e-6)
    for pid, rule in list(rule_registry.items()):
        if not rule.active:
            continue
        eligible = _eligible_agents(pid, agents_by_id, patch_system)
        members = set(rule.members)
        for agent in eligible:
            if agent.agent_id in members:
                continue
            p_join = _stable_sigmoid((agent.willingness_to_join - 0.5) / noise)
            if rng.random() < p_join:
                members.add(agent.agent_id)
                agent.rule_member_of = rule.rule_id
                event_log.add(
                    MembershipEvent(step=step, patch_id=pid, rule_id=rule.rule_id, agent=agent.agent_id, kind="join")
                )
        for aid in list(members):
            agent = agents_by_id.get(aid)
            if agent is None or not agent.alive:
                members.discard(aid)
                continue
            p_leave = _stable_sigmoid((0.5 - agent.willingness_to_join) / noise) * 0.2
            if rng.random() < p_leave:
                members.discard(aid)
                agent.rule_member_of = None
                resources_before_exit = agent.resources
                # Level 1.2b, Work Package E fix -- see the monitoring-
                # cost deduction site below for the full explanation.
                exit_cost_deducted = max(0.0, min(config.membership_exit_cost, resources_before_exit))
                agent.resources = resources_before_exit - exit_cost_deducted
                event_log.add(
                    MembershipEvent(
                        step=step, patch_id=pid, rule_id=rule.rule_id, agent=aid, kind="exit", reason="voluntary",
                        exit_cost_deducted=exit_cost_deducted,
                    )
                )
        rule.members = frozenset(members)


# ---------------------------------------------------------------------------
# Work Package E: monitoring.
# ---------------------------------------------------------------------------
def monitoring_round(
    step: int,
    rule_registry: dict[int, SharedRule],
    agents_by_id: dict[int, Agent],
    compliance_events: list[ComplianceEvent],
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
) -> list[MonitoringEvent]:
    """Reuses Level 0.1's confusion-matrix discipline: each monitored
    member's *actual* compliance this step (from ``compliance_events``,
    already realized by ``_ecological_round``) is observed with error —
    ``detected_violation`` need not equal ``true_compliance``'s
    negation."""
    produced: list[MonitoringEvent] = []
    if config.monitoring_mode == "none":
        return produced

    by_rule: dict[int, list[ComplianceEvent]] = {}
    for ev in compliance_events:
        by_rule.setdefault(ev.rule_id, []).append(ev)

    for pid, rule in rule_registry.items():
        if not rule.active:
            continue
        targets = by_rule.get(rule.rule_id, [])
        if not targets:
            continue
        monitor_id = None
        if config.monitoring_mode == "voluntary":
            members = list(rule.members)
            volunteers = [aid for aid in members if rng.random() < agents_by_id[aid].willingness_to_monitor]
            if not volunteers:
                continue
            monitor_id = int(rng.choice(volunteers))
        elif config.monitoring_mode == "designated":
            monitors = list(rule.monitors) or list(rule.members)
            if not monitors:
                continue
            monitor_id = int(rng.choice(monitors))
        # "perfect": monitor stays None.

        cost = 0.0
        cost_deducted_once = 0.0
        if config.monitoring_mode in ("voluntary", "designated") and monitor_id is not None:
            monitor_agent = agents_by_id[monitor_id]
            cost = config.monitoring_cost
            resources_before_monitor = monitor_agent.resources
            # Level 1.2b, Work Package A: the deduction below happens
            # exactly once per (step, patch, rule) monitoring round, no
            # matter how many ``targets`` (violations observed) follow --
            # but the pre-existing ``cost_to_monitor`` field is
            # (unchanged, for backward compatibility) stamped onto every
            # MonitoringEvent produced this round. ``cost_deducted`` below
            # instead attributes the one real deduction to only the first
            # event of the round, so summing it never overcounts.
            #
            # Level 1.2b, Work Package E production-scale fix: compute
            # the actual deduction as ``max(0.0, min(cost,
            # resources_before))`` rather than deducting via
            # ``max(0.0, resources_before - cost)`` and diffing after the
            # fact -- the latter silently resets an already-negative
            # ``resources_before`` (a legitimate distress/deficit state
            # elsewhere in this model) back to exactly 0.0, producing a
            # spurious NEGATIVE ``cost_deducted`` (a phantom resource
            # gain from nowhere) instead of correctly charging nothing
            # further. See ``rules/delegation.py``'s audit-cost site for
            # the identical fix and full explanation.
            cost_deducted_once = max(0.0, min(cost, resources_before_monitor))
            monitor_agent.resources = resources_before_monitor - cost_deducted_once

        accuracy = 1.0 if config.monitoring_mode == "perfect" else config.monitoring_detection_accuracy
        fp_rate = 0.0 if config.monitoring_mode == "perfect" else config.monitoring_false_positive_rate

        cost_attributed = False
        for ev in targets:
            true_compliance = not ev.violated
            if true_compliance:
                detected = rng.random() < fp_rate
                outcome = "false_positive" if detected else "true_negative"
            else:
                detected = rng.random() < accuracy
                outcome = "true_positive" if detected else "false_negative"
            rule.observation_count += 1
            this_event_cost_deducted = 0.0
            if not cost_attributed:
                this_event_cost_deducted = cost_deducted_once
                cost_attributed = True
            m_event = MonitoringEvent(
                step=step,
                patch_id=pid,
                rule_id=rule.rule_id,
                target=ev.agent,
                true_compliance=true_compliance,
                detected_violation=detected,
                outcome=outcome,
                monitor=monitor_id,
                cost_to_monitor=cost if monitor_id is not None else 0.0,
                cost_deducted=this_event_cost_deducted,
            )
            event_log.add(m_event)
            produced.append(m_event)
    return produced


# ---------------------------------------------------------------------------
# Work Package F: collective sanctioning.
# ---------------------------------------------------------------------------
def sanction_round(
    step: int,
    rule_registry: dict[int, SharedRule],
    agents_by_id: dict[int, Agent],
    monitoring_events: list[MonitoringEvent],
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
) -> None:
    if config.sanction_mode == "none":
        return
    detected = [ev for ev in monitoring_events if ev.detected_violation]
    for ev in detected:
        rule = rule_registry.get(ev.patch_id)
        if rule is None or not rule.active or rule.rule_id != ev.rule_id:
            continue
        magnitude = rule.parameters.sanction_magnitude
        target = agents_by_id.get(ev.target)
        if target is None:
            continue
        false_sanction = ev.true_compliance

        sanctioner_cost_deducted = 0.0
        if config.sanction_mode == "voluntary":
            candidates = [aid for aid in rule.members if aid != ev.target]
            bystanders = [aid for aid in candidates if rng.random() < agents_by_id[aid].sanction_preference]
            if not bystanders:
                continue
            sanctioner_id = int(rng.choice(bystanders))
            cost = config.sanction_cost_per_unit * magnitude
            resources_before_sanction = agents_by_id[sanctioner_id].resources
            # Level 1.2b, Work Package E fix -- see the monitoring-cost
            # deduction site above for the full explanation.
            sanctioner_cost_deducted = max(0.0, min(cost, resources_before_sanction))
            agents_by_id[sanctioner_id].resources = resources_before_sanction - sanctioner_cost_deducted
            funded_by = "bystander"
        elif config.sanction_mode == "collective_fund":
            cost = config.sanction_cost_per_unit * magnitude
            if rule.fund < cost:
                continue  # insufficient institutional resources: no sanction this event
            rule.fund -= cost
            sanctioner_id = None
            funded_by = "collective_fund"
        elif config.sanction_mode == "imposed_perfect":
            sanctioner_id = None
            cost = 0.0
            funded_by = "mechanical"
        else:
            continue

        # Level 1.2b, Work Package E production-scale ledger-residual fix:
        # this must clamp against ``max(0.0, target.resources)``, not
        # ``target.resources`` directly. If ``target.resources`` is
        # already negative (e.g. from an earlier sanction this same
        # step, or any other deduction this milestone deliberately
        # leaves uncapped), the un-clamped ``min(positive, negative)``
        # evaluates to that negative resources value, making ``penalty``
        # ITSELF negative -- so ``target.resources -= penalty`` then
        # *restores* the target back toward zero (a phantom resource
        # gain from nowhere) instead of taking a penalty, and every
        # ``SanctionEvent.penalty_applied`` this produces is a negative
        # number silently corrupting ``demand_sanction_penalty``. Every
        # other capped-deduction site in this codebase already floors at
        # zero before taking the ``min`` (see
        # ``environment/patches.py``/``resource_pool.py``/
        # ``rules/contributions.py``); this was the one exception, and
        # the dominant source of a ledger residual invisible at Level
        # 1.2b Work Package A's own short-run validation scale (too few
        # steps for any agent's resources to actually go negative) but
        # large at Work Package E's production scale (hundreds of steps,
        # much more opportunity for sustained distress).
        penalty = min(magnitude * config.sanction_penalty_unit, max(0.0, target.resources))
        target.resources -= penalty
        rule.sanction_count += 1
        event_log.add(
            SanctionEvent(
                step=step,
                patch_id=ev.patch_id,
                rule_id=rule.rule_id,
                target=ev.target,
                magnitude=magnitude,
                cost=cost,
                funded_by=funded_by,
                false_sanction=false_sanction,
                sanctioner=sanctioner_id,
                penalty_applied=penalty,
                sanctioner_cost_deducted=sanctioner_cost_deducted,
            )
        )


# ---------------------------------------------------------------------------
# Work Package H: amendment and dissolution.
# ---------------------------------------------------------------------------
_AMENDABLE_FIELDS = (
    "extraction_ceiling", "maintenance_requirement", "monitoring_intensity", "sanction_magnitude",
)


def amendment_round(
    step: int,
    rule_registry: dict[int, SharedRule],
    agents_by_id: dict[int, Agent],
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
    last_dissolved_by_patch: dict[int, SharedRule] | None = None,
    entrenchment_rng: np.random.Generator | None = None,
) -> None:
    """Level 1.3, Work Package C (Section 8): ``entrenchment_rng``
    (defaults to ``rng`` when omitted, exactly ``task_performance_
    round``'s own ``discretion_rng`` precedent) drives only the
    dissolution-SURVIVAL draw below, gated on
    ``config.entrenchment_enabled`` -- a strict no-op, including zero
    extra draws from either stream, when disabled."""
    if entrenchment_rng is None:
        entrenchment_rng = rng
    noise = max(config.institutional_decision_noise_std, 1e-6)
    # ``list(...)`` (not a bare ``.items()`` view) -- this loop can
    # dissolve-and-remove a rule from ``rule_registry`` mid-iteration
    # (see the "support_below_floor" branch below), exactly like
    # ``dissolution_round``'s own loop already does for the same reason.
    for pid, rule in list(rule_registry.items()):
        if not rule.active or not rule.members:
            continue
        proposer_id = None
        for aid in rule.members:
            agent = agents_by_id.get(aid)
            if agent is not None and rng.random() < agent.amendment_propensity:
                proposer_id = aid
                break
        if proposer_id is None:
            continue
        field_name = _AMENDABLE_FIELDS[int(rng.integers(0, len(_AMENDABLE_FIELDS)))]
        old_value = getattr(rule.parameters, field_name)
        proposed = mutate_rule_parameters(rule.parameters, config.rule_mutation_std, rng)
        new_value = getattr(proposed, field_name)
        kwargs = rule.parameters.as_dict()
        kwargs[field_name] = new_value
        proposed_params = RuleParameters(**kwargs)

        supporters = {
            aid for aid in rule.members
            if rng.random() < _stable_sigmoid((agents_by_id[aid].willingness_to_join - 0.5) / noise)
        }
        members_list = [agents_by_id[aid] for aid in rule.members if aid in agents_by_id]
        support_frac = _support_fraction(supporters, members_list, config)
        age = step - rule.founding_step
        entrenchment = entrenchment_level(age, config.entrenchment_maturation_steps) if config.entrenchment_enabled else 0.0
        effective_amendment_threshold = rule.parameters.amendment_threshold
        if config.entrenchment_enabled:
            # Work Package C: a more-entrenched institution is harder to
            # successfully amend -- status-quo bias rising with age.
            effective_amendment_threshold = entrenchment_adjusted_threshold(
                effective_amendment_threshold, entrenchment, config.entrenchment_amendment_threshold_sensitivity,
            )
        adopted = support_frac >= effective_amendment_threshold
        if adopted:
            rule.parameters = proposed_params
            rule.amendment_count += 1
        event_log.add(
            RuleAmendmentEvent(
                step=step,
                patch_id=pid,
                rule_id=rule.rule_id,
                rule_lineage_id=rule.rule_lineage_id,
                proposer=proposer_id,
                field_changed=field_name,
                old_value=old_value,
                new_value=new_value if adopted else old_value,
                n_eligible=len(members_list),
                n_supporters=len(supporters),
                support_fraction=support_frac,
                adopted=adopted,
                effective_amendment_threshold=effective_amendment_threshold,
            )
        )
        if not adopted:
            # a rejected amendment attempt still counts toward the
            # support-floor dissolution trigger (Work Package H).
            rule.consecutive_fund_depleted_steps = rule.consecutive_fund_depleted_steps
            if support_frac < config.rule_dissolution_support_floor and _attempt_dissolve(
                step, rule, agents_by_id, "support_below_floor", event_log, config, entrenchment, entrenchment_rng,
            ):
                # Level 1.2b, Work Package E production-scale ledger-
                # residual fix: every OTHER dissolution path
                # (``dissolution_round``) removes the just-dissolved rule
                # from ``rule_registry`` in the same call that deactivates
                # it -- this "support_below_floor" path (an amendment
                # rejected badly enough to also fail the support floor)
                # previously left the now-inactive, dissolved rule
                # sitting in the registry indefinitely. Since
                # ``system_total_resources()`` sums every registry-live
                # rule's ``fund`` regardless of ``.active``, a stale
                # entry with a nonzero fund silently kept counting toward
                # the closed system's total; if a later
                # ``proposal_and_adoption_round`` call then formed a NEW
                # rule at the same patch, ``rule_registry[pid] = new_rule``
                # would overwrite (and permanently drop) that stale
                # entry's fund with no disposal event at all -- an
                # untracked sink, invisible at Work Package A's own
                # short-run validation scale (too few amendment-triggered
                # dissolutions to matter) but a real contributor to the
                # ledger residual newly discovered at Work Package E's
                # production scale. ``Simulation._rule_formation_round``
                # snapshots ``rule_registry``'s patch-id keys BEFORE this
                # round runs and diffs them AFTER ``dissolution_round``
                # runs, so removing the entry here is enough for that
                # existing before/after machinery (delegate cleanup +
                # ``resolve_dissolution_fund``) to pick this dissolution
                # up exactly like any other -- which in turn requires
                # ``last_dissolved_by_patch`` (the same dict
                # ``dissolution_round`` writes to) to be updated HERE
                # too, since ``Simulation._rule_formation_round`` looks
                # up the dissolved rule object via that dict, keyed by
                # patch id, to find its ``.dissolution_step``/fund.
                # Without this, the fund/delegate cleanup below would
                # silently never fire for this dissolution path (a
                # distinct bug from the missing ``del`` above -- fixed
                # together since both stem from this path never having
                # matched ``dissolution_round``'s own full cleanup).
                if pid in rule_registry:
                    if last_dissolved_by_patch is not None:
                        last_dissolved_by_patch[pid] = rule
                    del rule_registry[pid]


def _dissolve(step: int, rule: SharedRule, agents_by_id: dict[int, Agent], reason: str, event_log: EventLog) -> None:
    if not rule.active:
        return
    founder = agents_by_id.get(rule.founder_id)
    founder_present = founder is not None and founder.alive
    for aid in list(rule.members):
        agent = agents_by_id.get(aid)
        if agent is not None and agent.rule_member_of == rule.rule_id:
            agent.rule_member_of = None
    rule.active = False
    rule.dissolved = True
    rule.dissolution_step = step
    rule.dissolution_reason = reason
    rule.members = frozenset()
    event_log.add(
        RuleDissolutionEvent(
            step=step,
            patch_id=rule.patch_id,
            rule_id=rule.rule_id,
            rule_lineage_id=rule.rule_lineage_id,
            reason=reason,
            age_at_dissolution=step - rule.founding_step,
            founder_present_at_dissolution=founder_present,
        )
    )


def _attempt_dissolve(
    step: int,
    rule: SharedRule,
    agents_by_id: dict[int, Agent],
    reason: str,
    event_log: EventLog,
    config: SimulationConfig,
    entrenchment: float,
    entrenchment_rng: np.random.Generator,
) -> bool:
    """Level 1.3, Work Package C: the shared "did this dissolution
    trigger actually dissolve the rule" gate used by every dissolution
    site in this module. When ``config.entrenchment_enabled``, a rule
    that breaches a trigger draws a chance to SURVIVE it anyway, scaled
    by its own ``entrenchment`` (caller-computed once per rule per
    round, not recomputed here). Returns ``True`` iff the rule was
    actually dissolved — a strict no-op (always ``True``, zero extra
    draws) when disabled, exactly Level 1.2b behavior."""
    if config.entrenchment_enabled:
        survive_p = entrenchment_survival_probability(entrenchment, config.entrenchment_dissolution_survival_sensitivity)
        if survive_p > 0.0 and entrenchment_rng.random() < survive_p:
            return False
    _dissolve(step, rule, agents_by_id, reason, event_log)
    return True


def dissolution_round(
    step: int,
    rule_registry: dict[int, SharedRule],
    agents_by_id: dict[int, Agent],
    patch_system,
    config: SimulationConfig,
    event_log: EventLog,
    last_dissolved_by_patch: dict[int, SharedRule],
    entrenchment_rng: np.random.Generator | None = None,
) -> None:
    """Level 1.3, Work Package C: ``entrenchment_rng`` drives only the
    dissolution-survival draw in :func:`_attempt_dissolve`, gated on
    ``config.entrenchment_enabled``. Required (raises ``ValueError``,
    not a silent fallback) when entrenchment is enabled and omitted —
    unlike ``amendment_round``'s ``rng``-based default, this function
    has no other pre-existing random stream of its own to safely reuse
    (Level 1.2b's ``dissolution_round`` drew no randomness at all)."""
    if config.entrenchment_enabled and entrenchment_rng is None:
        raise ValueError("entrenchment_rng is required when config.entrenchment_enabled is True")
    for pid, rule in list(rule_registry.items()):
        if not rule.active:
            continue
        eligible = _eligible_agents(pid, agents_by_id, patch_system)
        membership_floor_breach = (
            len(eligible) > 0 and rule.n_members / len(eligible) < config.rule_dissolution_membership_floor
        )
        if rule.n_members == 0:
            rule.consecutive_empty_steps += 1
        else:
            rule.consecutive_empty_steps = 0
        inactive_breach = rule.consecutive_empty_steps >= config.rule_inactive_dissolution_steps

        fund_breach = False
        if config.sanction_mode == "collective_fund" and config.rule_fund_depletion_dissolution_steps > 0:
            if rule.fund <= 0.0 and rule.violation_count > 0:
                rule.consecutive_fund_depleted_steps += 1
            else:
                rule.consecutive_fund_depleted_steps = 0
            fund_breach = rule.consecutive_fund_depleted_steps >= config.rule_fund_depletion_dissolution_steps

        if membership_floor_breach or inactive_breach or fund_breach:
            entrenchment = (
                entrenchment_level(step - rule.founding_step, config.entrenchment_maturation_steps)
                if config.entrenchment_enabled else 0.0
            )
            reason = (
                "membership_below_floor" if membership_floor_breach
                else "inactive_duration_exceeded" if inactive_breach
                else "fund_depleted"
            )
            _attempt_dissolve(step, rule, agents_by_id, reason, event_log, config, entrenchment, entrenchment_rng)

        if rule.dissolved and pid in rule_registry:
            last_dissolved_by_patch[pid] = rule
            del rule_registry[pid]


# ---------------------------------------------------------------------------
# Level 1.3, Work Package D (Section 9): dual legitimacy channels.
# ---------------------------------------------------------------------------
def legitimacy_round(
    step: int,
    rule_registry: dict[int, SharedRule],
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
) -> None:
    """One step of dual legitimacy ledger updates for every active rule
    — a strict no-op (zero draws, zero events, ``rule.performance_
    legitimacy``/``rule.procedural_legitimacy`` left at their defaults)
    unless AT LEAST ONE of ``config.performance_legitimacy_enabled``/
    ``config.procedural_legitimacy_enabled`` is set. See
    ``core/legitimacy.py``'s own module docstring for the full disclosed
    target-signal rationale and the two channels' independence from
    each other and from delegation."""
    if not (config.performance_legitimacy_enabled or config.procedural_legitimacy_enabled):
        return
    for pid, rule in rule_registry.items():
        if not rule.active:
            continue
        p_target = performance_legitimacy_target(rule.compliance_count, rule.violation_count)
        r_target = procedural_legitimacy_target(rule.compliance_count, rule.violation_count, rule.sanction_count)
        if config.performance_legitimacy_enabled:
            rule.performance_legitimacy = legitimacy_step(
                rule.performance_legitimacy, p_target,
                config.performance_legitimacy_learning_rate, config.performance_legitimacy_fallibility_std, rng,
            )
        if config.procedural_legitimacy_enabled:
            rule.procedural_legitimacy = legitimacy_step(
                rule.procedural_legitimacy, r_target,
                config.procedural_legitimacy_learning_rate, config.procedural_legitimacy_fallibility_std, rng,
            )
        event_log.add(
            LegitimacyEvent(
                step=step, patch_id=pid, rule_id=rule.rule_id,
                performance_legitimacy=rule.performance_legitimacy,
                procedural_legitimacy=rule.procedural_legitimacy,
                performance_legitimacy_target=p_target,
                procedural_legitimacy_target=r_target,
            )
        )
