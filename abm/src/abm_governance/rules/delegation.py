"""Level 1.1, Work Packages D-G: endogenous delegation, administrative
capacity, discretion/appropriation, and accountability/constraint,
layered on top of an already-active :class:`~abm_governance.rules.
shared_rule.SharedRule`.

Deliberately not named after any governance concept — a :class:`Delegate`
is a bare "one member holds limited, task-specific authority over this
rule for now" record, exactly analogous to how ``SharedRule`` itself is
not a "Government"/"Court" object (see ``dev_mem/project_vision.md`` §5,
§9, ``rules/__init__.py``'s naming-rationale docstring). Every criterion
that later *labels* an arrangement (e.g. "persistent_delegation") lives
only in ``observer/delegation_diagnostics.py`` — nothing here reads or
writes an observer-side label.

Step ordering (see ``simulation.py::Simulation._delegation_round``, which
runs immediately after ``_rule_formation_round``):

1. :func:`accountability_round` (Work Package G) — audits, appeals, and
   recalls act on *last* step's already-realized delegate behavior,
   mirroring Level 1.0's "monitoring/sanctioning consume this step's
   already-realized ground truth, never influence it retroactively"
   discipline. A recall here can remove the delegate before step 2 runs.
2. :func:`nomination_and_selection_round` (Work Package D) — only when a
   rule currently has no active delegate; produces a fresh appointment
   this step if a candidate clears the configured selection procedure.
3. :func:`task_performance_round` (Work Packages E/F) — the current
   (possibly freshly appointed) delegate performs its assigned tasks
   this step, accumulating realized capacity and, when
   ``discretion_enabled``, potentially exercising discretion
   (effort reduction, appropriation).

Every function below takes only local, already-in-scope arguments (a
single rule, its own delegate, its own members, this step's config/rng)
— nothing here reads or writes any global/population-wide/cross-patch
quantity, per the milestone's Constraint 6 (agent decisions may use only
locally available information).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from abm_governance.agents.adaptation import _stable_sigmoid
from abm_governance.agents.agent import Agent
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import (
    AppealEvent,
    AppropriationEvent,
    AppropriationOpportunityEvent,
    AuditEvent,
    DelegateAppointmentEvent,
    DelegateNominationEvent,
    DelegateRemovalEvent,
    EventLog,
    RecallEvent,
    TaskPerformanceEvent,
)
from abm_governance.core.historical_transmission import pressure_adjusted_probability, pressure_adjusted_scale
from abm_governance.rules.contributions import TASK_TO_SPENDING_CATEGORY, pay_administrative_cost
from abm_governance.rules.shared_rule import SharedRule


@dataclass
class Delegate:
    """One rule's currently-active (or removed, kept for tenure/lineage
    bookkeeping by the caller) delegate. Mirrors ``SharedRule``'s own
    "lightweight running totals here, full per-event record in the
    EventLog" discipline."""

    delegate_id: int
    rule_id: int
    rule_lineage_id: int
    patch_id: int
    agent_id: int
    tasks: tuple[str, ...]
    appointment_method: str
    start_step: int
    candidate_set: tuple[int, ...] = ()
    selector_population: tuple[int, ...] = ()
    support_fraction: float = 0.0
    predecessor_delegate_id: int | None = None
    active: bool = True
    removal_step: int | None = None
    removal_reason: str | None = None

    # -- Work Package E: capacity, realized from performance only ----------
    #: task -> cumulative attempts / successes. A fresh delegate always
    #: starts at 0 attempts for *itself* — institutional_memory (on the
    #: rule, not here) is the only channel through which a predecessor's
    #: experience can influence this delegate's starting record_quality.
    task_attempts: dict[str, int] = field(default_factory=dict)
    task_successes: dict[str, int] = field(default_factory=dict)
    #: Realized record-keeping quality in [0, 1] — rises on success,
    #: decays on failure or inactivity; this, not a raw trait, is what
    #: observer/delegation_diagnostics.py reads as "capacity."
    record_quality: float = 0.2

    # -- Work Package F: discretion / appropriation -------------------------
    appropriated_total: float = 0.0
    misconduct_count: int = 0
    effort_withheld_count: int = 0

    # -- Work Package G: accountability --------------------------------------
    audits_survived: int = 0
    audits_failed: int = 0
    appeals_upheld_against: int = 0
    appeals_rejected_against: int = 0
    #: Whether *this* step's task_performance_round already recorded at
    #: least one misconduct event, consumed (and reset) by the next
    #: step's accountability_round — "actual_misconduct_occurred" ground
    #: truth for the audit confusion matrix.
    misconduct_this_step: bool = False

    @property
    def capacity(self) -> float:
        """Observer- and mechanism-facing realized-capacity index in
        [0, 1] — a function of actual completion rate and accumulated
        record quality, never a raw assigned trait (Work Package E
        requirement 8)."""
        attempted = sum(self.task_attempts.values())
        if attempted == 0:
            return 0.0
        completion_rate = sum(self.task_successes.values()) / attempted
        experience_term = min(1.0, attempted / 50.0)
        return float(np.clip(0.5 * completion_rate + 0.3 * self.record_quality + 0.2 * experience_term, 0.0, 1.0))

    @property
    def tenure_steps_as_of(self) -> int:
        return -1  # computed by the caller (needs current step); placeholder never read directly


# ---------------------------------------------------------------------------
# Work Package D: nomination and selection.
# ---------------------------------------------------------------------------
def _candidate_evaluation_score(
    candidate: Agent,
    n_eligible: int,
    max_resources: float,
    prior_capacity: float,
    config: SimulationConfig,
) -> float:
    """One evaluator-independent component of a candidate's support
    score, combining observed reliability (this candidate's own prior
    delegate track record — a neutral 0.5 prior if it has never held the
    role), perceived competence, social trust, relative resource
    position, and an administrative-cost-aversion penalty scaling with
    jurisdiction size — an explicit, inspectable heuristic (Work Package
    D's own "documented heuristic" register, not a solved optimum)."""
    reliability = prior_capacity if prior_capacity > 0.0 else 0.5
    resource_position = (candidate.resources / max_resources) if max_resources > 0 else 0.5
    cost_aversion_penalty = min(1.0, n_eligible / 20.0)
    score = (
        config.delegate_evaluation_reliability_weight * reliability
        + config.delegate_evaluation_competence_weight * candidate.perceived_competence
        + config.delegate_evaluation_trust_weight * candidate.social_trust
        + config.delegate_evaluation_resource_weight * resource_position
        - config.delegate_evaluation_cost_aversion_weight * cost_aversion_penalty
    )
    return score


def nomination_and_selection_round(
    step: int,
    rule_registry: dict[int, SharedRule],
    agents_by_id: dict[int, Agent],
    patch_system,
    delegate_registry: dict[int, Delegate],
    pending_nominations: dict[int, dict],
    prior_capacity_by_agent: dict[int, float],
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
    id_state: dict,
    delegate_history: list[Delegate] | None = None,
) -> None:
    """One step of nomination accumulation and, once the window expires
    or the whole eligible population has had a chance to nominate,
    selection resolution (Work Package D). ``pending_nominations`` holds
    ``rule_id -> {"opened_step": int, "candidates": dict[int, set[int]]}``
    (candidate -> set of nominators), owned by the caller across steps
    exactly like Level 1.0's ``_pending_rule_proposals``.
    ``prior_capacity_by_agent`` is a read-only snapshot (agent_id -> most
    recently realized capacity as a delegate, 0.0 if never delegated) the
    caller maintains from delegate-removal events, used only as an
    "observed reliability" input — never written here."""
    noise = max(config.institutional_decision_noise_std, 1e-6)
    for pid, rule in rule_registry.items():
        if not rule.active or not rule.members:
            continue
        existing = delegate_registry.get(rule.rule_id)
        if existing is not None and existing.active:
            continue  # at most one active delegate per rule (documented simplification).

        eligible = [agents_by_id[aid] for aid in rule.members if agents_by_id.get(aid) is not None and agents_by_id[aid].alive]
        if not eligible:
            continue

        state = pending_nominations.setdefault(rule.rule_id, {"opened_step": step, "candidates": {}})
        candidates: dict[int, set[int]] = state["candidates"]
        for nominator in eligible:
            if rng.random() >= nominator.nomination_probability:
                continue
            # Self-nomination or nominating a random fellow member
            # (deterministic tie-break via rng.random(), not agent order).
            self_nom = rng.random() < 0.5
            candidate_id = nominator.agent_id if self_nom else int(rng.choice(list(rule.members)))
            candidates.setdefault(candidate_id, set()).add(nominator.agent_id)
            event_log.add(
                DelegateNominationEvent(
                    step=step, patch_id=pid, rule_id=rule.rule_id, rule_lineage_id=rule.rule_lineage_id,
                    nominator=nominator.agent_id, candidate=candidate_id, self_nomination=self_nom,
                )
            )

        window_expired = (step - state["opened_step"]) >= (config.delegate_nomination_window_steps - 1)
        if not candidates or not window_expired:
            continue

        # Evaluation: every eligible member scores every candidate this
        # step (a fresh, independent draw each resolution — not carried
        # over from earlier nomination-window steps, keeping this
        # analogous to Level 1.0's adoption-threshold check happening
        # once, at resolution).
        max_resources = max((a.resources for a in eligible), default=0.0)
        candidate_support: dict[int, float] = {}
        for cand_id in candidates:
            prior_capacity = prior_capacity_by_agent.get(cand_id, 0.0)
            supporters = 0
            for evaluator in eligible:
                if evaluator.agent_id == cand_id:
                    continue
                score = _candidate_evaluation_score(agents_by_id[cand_id], len(eligible), max_resources, prior_capacity, config)
                p_support = _stable_sigmoid(score / noise)
                if rng.random() < p_support:
                    supporters += 1
            candidate_support[cand_id] = supporters / max(1, len(eligible) - 1)

        # Level 1.2, Work Package A: ``succession_procedure`` override.
        procedure = (rule.institution_overrides or {}).get("succession_procedure", config.delegate_selection_procedure)
        selected_id = None
        if procedure == "lottery":
            selected_id = int(rng.choice(list(candidates.keys())))
            support = candidate_support[selected_id]
        elif procedure == "plurality_support":
            selected_id = max(candidate_support, key=candidate_support.get)
            support = candidate_support[selected_id]
            if support <= 0.0:
                selected_id = None
        else:  # voluntary_approval / threshold_acceptance
            eligible_candidates = {
                cid: s for cid, s in candidate_support.items() if s >= config.delegate_selection_support_threshold
            }
            if eligible_candidates:
                selected_id = max(eligible_candidates, key=eligible_candidates.get)
                support = eligible_candidates[selected_id]

        if selected_id is not None:
            delegate_id = id_state["next_delegate_id"]
            id_state["next_delegate_id"] += 1
            if existing is not None:
                # Work Package E requirement 7: a configurable fraction of
                # the just-departed delegate's own realized record quality
                # is absorbed into this rule's institutional_memory here,
                # at the moment of replacement -- rule.institutional_memory
                # is never written anywhere else, so a rule with no prior
                # delegate (existing is None) correctly stays at its 0.0
                # default (nothing to remember yet). Overwrites rather than
                # accumulates across multiple past delegates: memory
                # reflects the most recently departed office-holder's own
                # quality, not an ever-thickening blend that would make
                # "how much does the current successor actually inherit"
                # unauditable.
                # Level 1.2, Work Package A: ``memory_retention`` override.
                retention = (rule.institution_overrides or {}).get(
                    "memory_retention", config.institutional_memory_retention
                )
                rule.institutional_memory = float(np.clip(
                    existing.record_quality * retention, 0.0, 1.0,
                ))
            memory_bonus = rule.institutional_memory * config.institutional_memory_transfer_to_new_delegate
            # Level 1.2, Work Package A: ``delegated_task_distribution`` override.
            tasks_override = (rule.institution_overrides or {}).get("delegated_task_distribution")
            new_delegate = Delegate(
                delegate_id=delegate_id,
                rule_id=rule.rule_id,
                rule_lineage_id=rule.rule_lineage_id,
                patch_id=pid,
                agent_id=selected_id,
                tasks=tuple(tasks_override) if tasks_override else tuple(config.delegated_tasks),
                appointment_method=procedure,
                start_step=step,
                candidate_set=tuple(sorted(candidates.keys())),
                selector_population=tuple(sorted(a.agent_id for a in eligible)),
                support_fraction=float(support),
                predecessor_delegate_id=existing.delegate_id if existing is not None else None,
                record_quality=float(np.clip(memory_bonus, 0.0, 1.0)),
            )
            if existing is not None and delegate_history is not None:
                # The outgoing delegate (already inactive by construction
                # -- see the loop's own "at most one active delegate"
                # continue-guard above) would otherwise be lost the
                # instant the registry slot is overwritten; preserve its
                # full realized-performance/appropriation/accountability
                # record for observer-side history (Work Package D
                # requirement: every delegation event's outcomes must be
                # recorded, not merely the currently-active delegate's).
                delegate_history.append(existing)
            delegate_registry[rule.rule_id] = new_delegate
            event_log.add(
                DelegateAppointmentEvent(
                    step=step, patch_id=pid, rule_id=rule.rule_id, rule_lineage_id=rule.rule_lineage_id,
                    delegate_id=delegate_id, agent=selected_id, tasks=new_delegate.tasks,
                    appointment_method=procedure, candidate_set=new_delegate.candidate_set,
                    selector_population=new_delegate.selector_population, support_fraction=float(support),
                    predecessor_delegate_id=new_delegate.predecessor_delegate_id,
                    institutional_memory_inherited=new_delegate.record_quality,
                )
            )
        del pending_nominations[rule.rule_id]


# ---------------------------------------------------------------------------
# Work Packages E/F: task performance, capacity accumulation, discretion.
# ---------------------------------------------------------------------------
def _success_probability(
    delegate: Delegate, agent: Agent, n_tasks_this_step: int, rule: SharedRule, config: SimulationConfig,
    security_pressure_level: float = 0.0,
) -> float:
    """Level 1.3, Work Package A (Section 6): two of security
    pressure's registered microscopic channels live here, and only
    here -- ``security_pressure_level`` defaults to ``0.0`` (an exact
    no-op for every non-Level-1.3 caller, including every existing
    Level 1.1/1.1b/1.2/1.2b test that calls this function directly).

    "returns_to_delegation": under sustained security pressure, a
    delegate's realized administrative reliability is worth more (an
    elevated ``base``) -- delegation becomes a more valuable channel
    for coordinated response, exactly as the theoretical translation's
    point A describes.

    "admin_capacity_demand": pressure also raises how much accumulated
    capacity itself matters to task success (a scaled ``capacity_bonus``
    weight) -- demand for administrative capacity rising under pressure,
    not merely reliability.

    Both are additive/multiplicative NUDGES to an already-existing,
    already-tested formula (core/historical_transmission.py's own
    ``pressure_adjusted_probability``/``pressure_adjusted_scale``) --
    neither introduces a new success pathway or bypasses the existing
    capacity/workload/scale terms below."""
    base = agent.administrative_reliability
    if config.security_pressure_returns_to_delegation_enabled:
        base = pressure_adjusted_probability(
            base, security_pressure_level, config.security_pressure_returns_to_delegation_sensitivity,
        )
    capacity_weight = config.delegation_capacity_learning_weight
    if config.security_pressure_admin_capacity_demand_enabled:
        capacity_weight = pressure_adjusted_scale(
            capacity_weight, security_pressure_level, config.security_pressure_admin_capacity_demand_sensitivity,
        )
    capacity_bonus = capacity_weight * delegate.capacity
    workload_penalty = config.delegation_workload_penalty_per_task * max(0, n_tasks_this_step - 1)
    scale_term = config.delegation_scale_coefficient * (rule.n_members / 10.0)
    return float(np.clip(base + capacity_bonus - workload_penalty - scale_term, 0.02, 0.98))


def task_performance_round(
    step: int,
    rule_registry: dict[int, SharedRule],
    delegate_registry: dict[int, Delegate],
    agents_by_id: dict[int, Agent],
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
    discretion_rng: np.random.Generator | None = None,
    jurisdiction_size_by_patch: dict[int, int] | None = None,
    security_pressure_level: float = 0.0,
) -> None:
    """Once per step, for every rule with an active delegate: the
    delegate attempts each of its assigned tasks (Work Package E), each
    subject to capacity-driven success/failure, resource cost, and —
    when ``config.discretion_enabled`` — a chance of deliberate effort
    reduction or fund appropriation (Work Package F). Capacity
    (:attr:`Delegate.capacity`) is a pure read of accumulated
    ``task_attempts``/``task_successes``/``record_quality`` — nothing
    here lets the delegate or any agent directly set/maximize it, only
    perform tasks whose *realized outcome* updates it (Work Package E
    requirement "must not directly maximize observer-side C_t").

    Level 1.1b, Work Package A: ``rng`` drives only the ordinary
    success/failure draw (administrative task performance); the
    effort-withholding and fund-appropriation draws — the two
    *discretionary* decisions — are drawn from ``discretion_rng`` when
    given, so a causal experiment can ablate discretion without
    perturbing the task-success stream at all. ``discretion_rng``
    defaults to ``rng`` when omitted (e.g. legacy single-stream mode,
    where both parameters are the same object anyway, so this is a
    genuine no-op, not merely a compatible default)."""
    if discretion_rng is None:
        discretion_rng = rng
    for pid, rule in rule_registry.items():
        if not rule.active:
            continue
        delegate = delegate_registry.get(rule.rule_id)
        if delegate is None or not delegate.active:
            continue
        agent = agents_by_id.get(delegate.agent_id)
        if agent is None or not agent.alive:
            continue

        delegate.misconduct_this_step = False
        n_tasks = len(delegate.tasks)
        if rule.n_members == 0:
            # Nothing to administer this step: inactivity decay only
            # (Work Package E requirement 2), no attempts recorded.
            delegate.record_quality = float(np.clip(delegate.record_quality * (1.0 - config.delegation_inactivity_decay_rate), 0.0, 1.0))
            continue

        capacity_before = delegate.capacity
        any_task_ran = False
        for task in delegate.tasks:
            # Work Package F: effort reduction — a deliberate choice to
            # withhold effort this task this step, made *before* the
            # ordinary success/failure draw (an agent can only reduce
            # effort it would otherwise have spent).
            withheld = False
            if config.discretion_enabled:
                p_withhold = float(
                    np.clip(agent.effort_reduction_propensity * config.effort_reduction_opportunity_scale, 0.0, 1.0)
                )
                withheld = discretion_rng.random() < p_withhold

            # Level 1.2, Work Package A: ``administrative_fund_rule`` override.
            cost = (rule.institution_overrides or {}).get("administrative_fund_rule", config.delegation_task_cost)
            # Level 1.2, Work Package F: "admin workload increases with
            # scale" -- a strict no-op (multiplier stays 1.0) unless the
            # caller supplies a jurisdiction size for this rule's patch
            # (only ever non-None when config.institutional_scaling_enabled
            # is True; see Simulation._institutional_scaling_round).
            if jurisdiction_size_by_patch is not None:
                jurisdiction_size = jurisdiction_size_by_patch.get(pid, 1)
                multiplier = 1.0 + config.scaling_admin_overhead_per_patch * max(0, jurisdiction_size - 1)
                cost = cost * max(0.1, multiplier)
            if withheld:
                delegate.effort_withheld_count += 1
                delegate.misconduct_this_step = True
                # Withholding effort saves the agent its ordinary cost
                # but still counts as an attempt with a near-floor
                # success draw (never mechanically guaranteed to fail —
                # "misconduct must be possible but not inevitable" cuts
                # both ways: withheld effort can still get lucky).
                p_success = 0.05
                cost = 0.0
            else:
                p_success = _success_probability(delegate, agent, n_tasks, rule, config, security_pressure_level)
                category = TASK_TO_SPENDING_CATEGORY.get(task, "overhead")
                pay_administrative_cost(step, pid, rule, delegate.delegate_id, agent, category, cost, event_log)

            success = rng.random() < p_success
            delegate.task_attempts[task] = delegate.task_attempts.get(task, 0) + 1
            if success:
                delegate.task_successes[task] = delegate.task_successes.get(task, 0) + 1
                delegate.record_quality = float(np.clip(delegate.record_quality + 0.01, 0.0, 1.0))
            else:
                delegate.record_quality = float(np.clip(delegate.record_quality - 0.005, 0.0, 1.0))
            any_task_ran = True
            event_log.add(
                TaskPerformanceEvent(
                    step=step, patch_id=pid, rule_id=rule.rule_id, delegate_id=delegate.delegate_id,
                    agent=agent.agent_id, task=task,
                    outcome="withheld" if withheld else ("success" if success else "failure"),
                    capacity_before=capacity_before, cost=cost,
                )
            )

        if not any_task_ran:
            delegate.record_quality = float(np.clip(delegate.record_quality * (1.0 - config.delegation_inactivity_decay_rate), 0.0, 1.0))

        # Work Package F: fund appropriation — a separate discretionary
        # decision from effort reduction, gated on the fund actually
        # holding something to appropriate (Work Package F requirement
        # "appropriation must be fully resource-accounted": the amount
        # removed from the fund always equals the amount credited to the
        # delegate).
        if config.discretion_enabled and rule.fund > 0.0:
            # Level 1.1b, Work Package D: an AppropriationOpportunityEvent
            # is logged for EVERY opportunity, whether or not attempted --
            # the record Level 1.1 never produced (AppropriationEvent
            # alone cannot distinguish "opportunity was rare" from
            # "opportunity was common but conduct declined it").
            fund_before = rule.fund
            p_appropriate = float(np.clip(agent.appropriation_propensity * config.appropriation_opportunity_scale, 0.0, 1.0))
            attempted = discretion_rng.random() < p_appropriate
            attempted_amount = 0.0
            realized_amount = 0.0
            if attempted:
                attempted_amount = min(rule.fund, rule.fund * config.appropriation_fraction_of_fund)
                realized_amount = attempted_amount  # no partial-failure mode exists yet
                rule.fund -= realized_amount
                agent.resources += realized_amount
                delegate.appropriated_total += realized_amount
                delegate.misconduct_count += 1
                delegate.misconduct_this_step = True
                event_log.add(
                    AppropriationEvent(
                        step=step, patch_id=pid, rule_id=rule.rule_id, delegate_id=delegate.delegate_id,
                        agent=agent.agent_id, amount=realized_amount, fund_before=fund_before, fund_after=rule.fund,
                    )
                )
            event_log.add(
                AppropriationOpportunityEvent(
                    step=step, patch_id=pid, rule_id=rule.rule_id, delegate_id=delegate.delegate_id,
                    agent=agent.agent_id, fund_before=fund_before,
                    appropriation_propensity=agent.appropriation_propensity, p_appropriate=p_appropriate,
                    attempted=attempted, attempted_amount=attempted_amount, realized_amount=realized_amount,
                    fraction_of_opportunity=(realized_amount / fund_before) if fund_before > 0.0 else 0.0,
                )
            )


# ---------------------------------------------------------------------------
# Work Package G: accountability and constraint.
# ---------------------------------------------------------------------------
def accountability_round(
    step: int,
    rule_registry: dict[int, SharedRule],
    delegate_registry: dict[int, Delegate],
    agents_by_id: dict[int, Agent],
    sanction_events_this_step: list,
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
    bargaining_pressure_level: float = 0.0,
) -> None:
    """One step of member audits (against *last* step's already-realized
    delegate behavior, recorded on :attr:`Delegate.misconduct_this_step`
    by :func:`task_performance_round`), possible recall, and appeals
    against this step's freshly produced ``SanctionEvent``s (Level 1.0
    mechanism, reused here rather than duplicated — see ``rules/
    dynamics.py::sanction_round``). A strict no-op unless
    ``config.accountability_enabled``.

    Level 1.3, Work Package A (Section 6): ``bargaining_pressure_level``
    (default ``0.0`` -- an exact no-op for every non-Level-1.3 caller)
    feeds the "appeal_recall" channel below, gated on its own
    ``config.bargaining_pressure_appeal_recall_enabled`` flag."""
    if not config.accountability_enabled:
        return
    for pid, rule in rule_registry.items():
        if not rule.active:
            continue
        delegate = delegate_registry.get(rule.rule_id)
        if delegate is None or not delegate.active:
            continue
        members = [agents_by_id[aid] for aid in rule.members if agents_by_id.get(aid) is not None and agents_by_id[aid].alive]
        # Level 1.1b, Work Package E: audit_enabled=False is a strict
        # no-op for this rule's audits this step (auditors=[], zero extra
        # draws, zero AuditEvents) -- exactly like every other master/
        # component flag in this codebase.
        auditors = [
            m for m in members
            if m.agent_id != delegate.agent_id
            and rng.random() < float(np.clip(m.audit_diligence * config.audit_probability_scale, 0.0, 1.0))
        ] if config.audit_enabled else []
        actual_misconduct = delegate.misconduct_this_step
        recall_triggered_by: int | None = None
        for auditor in auditors:
            resources_before_audit = auditor.resources
            # Level 1.2b, Work Package E production-scale ledger-residual
            # fix: ``max(0.0, resources_before - cost)`` alone is only a
            # correct "capped deduction" when ``resources_before >= 0``.
            # This model's viability system (Level 0.2) deliberately lets
            # agent resources go negative elsewhere (subsistence/
            # ecological deficits are the intended "distress" mechanic),
            # so an already-negative ``resources_before`` here previously
            # made the deduction formula silently RESET the auditor back
            # to exactly 0.0 -- a phantom resource gain from nowhere --
            # and the resulting ``audit_cost_deducted = before - after``
            # came out NEGATIVE, corrupting ``demand_audit_cost``. Every
            # site sharing this ``max(0.0, resources - cost)`` pattern
            # had the same latent bug (see ``dynamics.py``'s monitoring/
            # sanction/membership-exit sites and this file's own appeal
            # site); computing the actual deduction FIRST, floored at
            # both ends, fixes all of them identically and is a no-op
            # whenever ``resources_before`` was already non-negative.
            audit_cost_deducted = max(0.0, min(config.audit_cost, resources_before_audit))
            auditor.resources = resources_before_audit - audit_cost_deducted
            correct_draw = rng.random() < config.audit_accuracy
            found = correct_draw if actual_misconduct else (not correct_draw)
            if actual_misconduct:
                outcome = "true_positive" if found else "false_negative"
            else:
                outcome = "false_positive" if found else "true_negative"
            event_log.add(
                AuditEvent(
                    step=step, patch_id=pid, rule_id=rule.rule_id, delegate_id=delegate.delegate_id,
                    auditor=auditor.agent_id, actual_misconduct_occurred=actual_misconduct,
                    found_misconduct=found, outcome=outcome, cost=config.audit_cost,
                    cost_deducted=audit_cost_deducted,
                )
            )
            if found:
                delegate.audits_failed += 1
                if recall_triggered_by is None:
                    recall_triggered_by = auditor.agent_id
            else:
                delegate.audits_survived += 1

        recall_voters = [m for m in members if m.agent_id != delegate.agent_id]
        if config.recall_enabled and recall_triggered_by is not None and recall_voters:
            noise = max(config.institutional_decision_noise_std, 1e-6)
            # Recall support is driven only by locally observable
            # information -- this delegate's own accumulated audit
            # track record (a Laplace-smoothed fraction of past audits
            # that found misconduct, so a single early finding does not
            # by itself manufacture near-certain support -- "delegates
            # can sometimes survive unsuccessful challenges" must hold
            # even right after a first accusation) plus each member's
            # individual distrust trait -- never the hidden ground-truth
            # ``actual_misconduct`` flag itself (a member cannot see
            # that; it only sees audit verdicts, exactly like Level
            # 1.0's monitoring/sanction decisions use only locally
            # available information). The delegate itself never votes on
            # its own recall.
            total_audits_of_delegate = delegate.audits_failed + delegate.audits_survived
            prior_strength = 3.0
            finding_rate = (delegate.audits_failed + prior_strength * 0.5) / (total_audits_of_delegate + prior_strength)
            supporters = {
                m.agent_id for m in recall_voters
                if rng.random() < _stable_sigmoid((finding_rate - 0.5 + (1.0 - m.social_trust) * 0.3) / noise)
            }
            support_fraction = len(supporters) / len(recall_voters)
            # Level 1.2, Work Package A: ``recall_procedure`` override.
            recall_threshold = (rule.institution_overrides or {}).get(
                "recall_procedure", config.recall_support_threshold
            )
            if config.bargaining_pressure_appeal_recall_enabled:
                # Section 6 "appeal AND recall propensity": bargaining
                # pressure lowers the support bar needed for a
                # successful recall (a nudge to the threshold itself,
                # never to support_fraction, which stays a pure read of
                # auditor votes) -- floored well above 0 so recall never
                # becomes mechanically automatic.
                recall_threshold = max(
                    0.05,
                    recall_threshold - config.bargaining_pressure_appeal_recall_sensitivity * bargaining_pressure_level,
                )
            succeeded = support_fraction >= recall_threshold
            recovered = 0.0
            if succeeded:
                recovered = delegate.appropriated_total * config.recall_fund_recovery_fraction
                rule.fund += recovered
                _remove_delegate(step, delegate, agents_by_id, "recalled", event_log)
            event_log.add(
                RecallEvent(
                    step=step, patch_id=pid, rule_id=rule.rule_id, delegate_id=delegate.delegate_id,
                    trigger_auditor=recall_triggered_by, n_eligible=len(recall_voters), n_supporters=len(supporters),
                    support_fraction=support_fraction, recall_threshold=recall_threshold,
                    succeeded=succeeded, recovered_funds=recovered,
                )
            )

        if not config.appeal_enabled:
            continue
        # Level 1.2, Work Package A: ``appeal_procedure`` override (the
        # appeal *probability* only -- accuracy stays global, a disclosed
        # scope reduction; see docs/odd_level1.2.md).
        appeal_probability = (rule.institution_overrides or {}).get("appeal_procedure", config.appeal_probability)
        if config.bargaining_pressure_appeal_recall_enabled:
            # Section 6: "appeal and recall propensity" rises with
            # bargaining pressure -- a nudge to the same probability the
            # per-institution override above already may have adjusted,
            # never a bypass of it.
            appeal_probability = pressure_adjusted_probability(
                appeal_probability, bargaining_pressure_level, config.bargaining_pressure_appeal_recall_sensitivity,
            )
        for sanction_ev in sanction_events_this_step:
            if sanction_ev.rule_id != rule.rule_id:
                continue
            target = agents_by_id.get(sanction_ev.target)
            if target is None or not target.alive:
                continue
            if rng.random() >= appeal_probability:
                continue
            accuracy = config.appeal_accuracy_true_positive if sanction_ev.false_sanction else config.appeal_accuracy_false_positive
            upheld = rng.random() < accuracy
            refund = 0.0
            resources_before_appeal = target.resources
            # Level 1.2b, Work Package E fix -- see AuditEvent's sibling
            # deduction site above for the full explanation of why this
            # must clamp against ``max(0.0, resources_before)`` rather
            # than deducting via ``max(0.0, resources_before - cost)``
            # directly. Also newly disclosed as its own tracked field
            # (``AppealEvent.cost_deducted``): the ledger previously used
            # ``AppealEvent.cost`` (the uncapped intended
            # ``config.appeal_cost`` constant) for every appeal
            # regardless of whether the deduction was actually capped --
            # the same "capped deduction vs. logged intent" mismatch
            # already fixed this milestone for monitoring/sanction/
            # membership-exit/audit costs, missed here until this scale
            # of run surfaced it.
            appeal_cost_deducted = max(0.0, min(config.appeal_cost, resources_before_appeal))
            target.resources = resources_before_appeal - appeal_cost_deducted
            if upheld:
                refund = min(sanction_ev.magnitude * 3.0, sanction_ev.magnitude * 3.0) * config.appeal_refund_fraction
                target.resources += refund
                delegate.appeals_upheld_against += 1
            else:
                delegate.appeals_rejected_against += 1
            event_log.add(
                AppealEvent(
                    step=step, patch_id=pid, rule_id=rule.rule_id,
                    delegate_id=delegate.delegate_id if delegate.active else None,
                    appellant=target.agent_id, original_sanction_step=sanction_ev.step,
                    was_false_sanction=sanction_ev.false_sanction, upheld=upheld, refund=refund,
                    cost=config.appeal_cost, cost_deducted=appeal_cost_deducted,
                )
            )


def _remove_delegate(step: int, delegate: Delegate, agents_by_id: dict[int, Agent], reason: str, event_log: EventLog) -> None:
    if not delegate.active:
        return
    delegate.active = False
    delegate.removal_step = step
    delegate.removal_reason = reason
    event_log.add(
        DelegateRemovalEvent(
            step=step, patch_id=delegate.patch_id, rule_id=delegate.rule_id, rule_lineage_id=delegate.rule_lineage_id,
            delegate_id=delegate.delegate_id, agent=delegate.agent_id, reason=reason,
            tenure_steps=step - delegate.start_step, final_capacity=delegate.capacity,
            appropriated_total=delegate.appropriated_total,
        )
    )


def handle_rule_dissolution_removals(
    step: int,
    dissolved_rule_ids: set[int],
    delegate_registry: dict[int, Delegate],
    rule_registry_snapshot: dict[int, SharedRule],
    agents_by_id: dict[int, Agent],
    event_log: EventLog,
) -> None:
    """Any active delegate whose rule dissolved this step is removed
    with ``reason="rule_dissolved"`` (Work Package D requirement:
    delegates may "become dormant" — a dissolved rule leaves its
    delegate with nothing to administer)."""
    for delegate in delegate_registry.values():
        if delegate.active and delegate.rule_id in dissolved_rule_ids:
            _remove_delegate(step, delegate, agents_by_id, "rule_dissolved", event_log)
