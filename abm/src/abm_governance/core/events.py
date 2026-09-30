"""Structured event log — the sole channel the observer layer reads from.

The generative layer appends immutable event records here as the simulation
proceeds. Nothing downstream (observer, viz, cli) ever mutates simulation
state directly; it only reads from an :class:`EventLog` snapshot or the
final agent/network state. This keeps the generative/observer boundary a
hard, testable seam rather than a convention people can accidentally
violate.

Level 0.1 note on event families: the original Level-0 exit/rewiring events
(:class:`ExitEvent`, :class:`RewireEvent`) are kept unmodified and are only
ever produced by the *compatibility-mode* code path
(``network/graph.py``, used when ``relationship_dynamics_enabled=False``).
The new Work-Package-B relationship dynamics
(``network/dynamics.py``, used when ``relationship_dynamics_enabled=True``)
produce a distinct family of event types (:class:`EdgeAddedEvent`,
:class:`EdgeRemovedEvent`, :class:`FailedExitEvent`,
:class:`ConnectionProposalEvent`) precisely because the milestone brief
found the old "rewire" semantics ambiguous (it only ever adds edges) and
asked for edge addition, removal, replacement, and failed/rejected
proposals to be separately typed and separately counted. Never conflate
the two families when interpreting an event log — check
``config.relationship_dynamics_enabled`` to know which one a given run
used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InteractionEvent:
    step: int
    agent_a: int
    agent_b: int
    action_a: int  # 1 = cooperate, 0 = defect (ground truth)
    action_b: int
    payoff_a: float  # amount actually credited to a (may be extraction-capped; see environment/resource_pool.py)
    payoff_b: float
    #: What b perceived a's action to be (post observation-noise), and vice
    #: versa. Needed, together with PunishmentEvent, to build the
    #: enforcement confusion matrix in observer/metrics.py.
    observed_a_by_b: int
    observed_b_by_a: int
    #: Whether punishment was structurally possible this interaction
    #: (config.punishment_enabled) — distinguishes "no eligible punishment
    #: mechanism" from "punishment was possible but did not occur" in the
    #: confusion matrix's denominators.
    punishment_available: bool
    #: Level 0.2, Work Package A: each side's resource-status category
    #: ("solvent" | "distressed" | "dormant") and network degree, stamped
    #: at the moment this interaction happened (not reconstructed later
    #: from final state) so participation/cooperation can be broken down
    #: by point-in-time resource status exactly, not approximately. Always
    #: "solvent" and the true degree when ecology/viability tracking is
    #: off (Level-0/Level-0.1-compatible default), which costs nothing —
    #: these are plain attribute reads, no extra RNG, no extra event.
    resource_status_a: str = "solvent"
    resource_status_b: str = "solvent"
    degree_a: int = 0
    degree_b: int = 0


@dataclass(frozen=True)
class PunishmentEvent:
    step: int
    punisher: int
    target: int
    cost_to_punisher: float
    penalty_to_target: float
    erroneous: bool  # True if the punished agent actually cooperated (observation error)
    #: Always True at Level 0.1: punishment here is always the wronged
    #: party's immediate sanction against the same partner within the same
    #: encounter, never a delayed or third-party act. Kept as an explicit
    #: field (rather than omitted) so a future third-party/group
    #: enforcement mechanism (Level 2+) can set it False without changing
    #: this event's shape.
    retaliatory: bool = True


@dataclass(frozen=True)
class ExitEvent:
    """Level-0 compatibility-mode exit (unconditional; no failed-exit
    concept). Produced only by ``network/graph.py::exit_relationship``."""

    step: int
    agent: int
    former_partner: int
    exit_cost: float


@dataclass(frozen=True)
class RewireEvent:
    """Level-0 compatibility-mode "rewiring" — in the original
    implementation this only ever *adds* an edge (see the milestone
    diagnostic in dev_mem/status_update.md); it never replaces one.
    Produced only by ``network/graph.py::rewire``."""

    step: int
    agent: int
    new_partner: int | None  # None if no eligible partner was found


@dataclass(frozen=True)
class ImitationEvent:
    step: int
    agent: int  # the imitator (the milestone brief's "target agent" — the one whose policy changes)
    old_policy: str
    new_policy: str
    model_agent: int  # the peer copied from (the milestone brief's "source agent" — origin of the copied policy)
    #: Level 0.2, Work Package C: the fitness signal (under whichever
    #: config.fitness_mode was active) for ``agent`` and ``model_agent`` at
    #: decision time, their difference (``model_fitness - agent_fitness``,
    #: the Fermi-rule input), each side's viability state, and which
    #: fitness mode produced these values. Defaulted (not required) so
    #: existing call sites/tests that don't care about fitness diagnostics
    #: keep working unchanged.
    agent_fitness: float = 0.0
    model_fitness: float = 0.0
    fitness_gap: float = 0.0
    fitness_mode: str = "cumulative_resources"
    agent_viability_state: str = "active"
    model_viability_state: str = "active"
    #: agent.policy_lineage_id immediately after this event (== model
    #: agent's lineage id, since imitation propagates it) — recorded
    #: explicitly so lineage descent is readable straight from the event
    #: log without cross-referencing final agent state.
    resulting_lineage_id: int = 0


@dataclass(frozen=True)
class MutationEvent:
    step: int
    agent: int
    old_policy: str
    new_policy: str


@dataclass(frozen=True)
class EdgeAddedEvent:
    """Work-Package-B relationship dynamics: a new edge came into being."""

    step: int
    agent_a: int
    agent_b: int
    cause: str  # "initial" | "reconnect"


@dataclass(frozen=True)
class EdgeRemovedEvent:
    """Work-Package-B relationship dynamics: a voluntary, affordable exit."""

    step: int
    initiator: int
    partner: int
    exit_cost: float
    cause: str = "voluntary_exit"


@dataclass(frozen=True)
class FailedExitEvent:
    """The agent wanted to exit a relationship but could not afford
    ``exit_cost`` — the edge is *not* removed."""

    step: int
    agent: int
    partner: int
    reason: str = "insufficient_resources_for_exit_cost"


@dataclass(frozen=True)
class ConnectionProposalEvent:
    """A connection attempt and its outcome. ``accepted=True`` is always
    paired with an :class:`EdgeAddedEvent` at the same step for the same
    pair. ``reason='no_candidate'`` means no eligible target existed at
    all (the proposer is connected to everyone else already)."""

    step: int
    proposer: int
    target: int | None
    accepted: bool
    reason: str  # "accepted" | "rejected" | "no_candidate"


@dataclass(frozen=True)
class SubsistenceEvent:
    """One aggregate record per step of the uniform per-agent upkeep
    charge (see core/config.py::subsistence_cost). Aggregated rather than
    per-agent because the charge is uniform and unconditional — the
    per-agent total is exactly ``per_agent_cost * n_agents_charged``."""

    step: int
    per_agent_cost: float
    n_agents_charged: int
    total_cost: float


@dataclass(frozen=True)
class WithholdEvent:
    """A distressed agent did not engage in an otherwise-scheduled
    interaction this step (Work Package A survival consequence: reduced
    interaction capacity, not death — see agents/agent.py)."""

    step: int
    agent: int
    partner: int
    reason: str = "distress"


@dataclass(frozen=True)
class PerturbationEvent:
    """Start/end marker for a scheduled perturbation (Work Package G)."""

    step: int
    kind: str
    magnitude: float
    phase: str  # "start" | "end"


@dataclass(frozen=True)
class ViabilityTransitionEvent:
    """A single agent's viability-state transition (Level 0.2, Work
    Package B). ``from_state``/``to_state`` are each one of
    ``{"active","distressed","dormant","nonviable"}``. Recorded for every
    transition, in both ``dormancy_recovery`` and ``removal_replacement``
    modes (and never at all in ``viability_mode="none"``)."""

    step: int
    agent: int
    from_state: str
    to_state: str
    resources_at_transition: float
    cause: str  # e.g. "deficit_streak_exceeded", "resources_recovered", "dormancy_exceeded"


@dataclass(frozen=True)
class ReplacementEvent:
    """An agent was removed for persistent nonviability and a replacement
    now occupies the same population slot (``removal_replacement`` mode
    only). ``agent_id`` is unchanged (same network node); ``old_
    demographic_id``/``new_demographic_id`` distinguish the two distinct
    individuals; ``inheritance`` records which
    ``viability_replacement_policy`` rule produced the replacement's
    starting policy."""

    step: int
    agent_id: int
    old_demographic_id: int
    new_demographic_id: int
    old_policy: str
    new_policy: str
    inheritance: str  # one of VALID_REPLACEMENT_POLICIES (core/config.py)
    resources_at_removal: float
    initial_resources: float


@dataclass(frozen=True)
class EcologicalActionEvent:
    """One agent's ecological decision and its actual outcome, one step
    (Level 0.3, Work Packages B/C). ``requested_extraction``/
    ``requested_maintenance`` are what ``agents/ecological_policy.py::
    decide_ecological_action`` returned; ``actual_extraction`` is what the
    patch's allocation rule actually granted (see
    ``environment/patches.py::allocate_extraction`` — may be less than
    requested under scarcity); ``maintenance_effective`` is
    ``maintenance_efficiency * requested_maintenance``, capped by however
    much headroom the patch had left (see
    ``ResourcePatch.apply_maintenance``); ``requested_maintenance`` is
    paid by the agent in full regardless of effectiveness (maintenance
    cost is an immediate, unconditional individual cost — see the
    milestone's non-negotiable constraint 4). Only ever produced when
    ``config.ecology_topology == "patches"``."""

    step: int
    agent: int
    patch_id: int
    requested_extraction: float
    actual_extraction: float
    requested_maintenance: float
    maintenance_effective: float
    ecological_search_cost: float
    local_occupancy_observed: float  # the patch occupancy this decision was based on (start-of-decision snapshot)


@dataclass(frozen=True)
class EcologicalImitationEvent:
    """Ecological-policy analog of :class:`ImitationEvent` (Level 0.3,
    Work Package D). Independent of, and may occur on a different step's
    peer draw than, any :class:`ImitationEvent` for the same agent — see
    ``config.ecological_inheritance_mode``."""

    step: int
    agent: int
    model_agent: int
    old_extraction_propensity: float
    new_extraction_propensity: float
    old_maintenance_propensity: float
    new_maintenance_propensity: float
    old_scarcity_sensitivity: float
    new_scarcity_sensitivity: float
    agent_fitness: float
    model_fitness: float
    fitness_gap: float
    fitness_mode: str
    resulting_ecological_lineage_id: int
    inheritance_mode: str = "independent"  # "independent" | "coupled_same_model"


@dataclass(frozen=True)
class EcologicalMutationEvent:
    """Ecological-policy analog of :class:`MutationEvent` (Level 0.3,
    Work Package D)."""

    step: int
    agent: int
    old_extraction_propensity: float
    new_extraction_propensity: float
    old_maintenance_propensity: float
    new_maintenance_propensity: float
    old_scarcity_sensitivity: float
    new_scarcity_sensitivity: float
    resulting_ecological_lineage_id: int


@dataclass(frozen=True)
class RuleProposalEvent:
    """A rule proposal, whether or not it is later adopted (Level 1.0,
    Work Package B/C). ``origin`` distinguishes a fresh proposal from an
    existing member's traits from a mutated variant of an existing
    lineage (Work Package G) or a proposal copied from an observed
    neighboring patch's rule (imitation) -- ``parent_rule_lineage_id`` is
    set only for the latter two, never for a fresh proposal, which is
    what makes lineage vs. mere numerical similarity distinguishable
    downstream (see observer/institution_diagnostics.py)."""

    step: int
    patch_id: int
    proposer: int
    rule_lineage_id: int
    extraction_ceiling: float
    maintenance_requirement: float
    monitoring_intensity: float
    sanction_magnitude: float
    adoption_threshold: float
    amendment_threshold: float
    origin: str = "proposal"  # "proposal" | "mutation" | "imitation"
    parent_rule_lineage_id: int | None = None


@dataclass(frozen=True)
class RuleAdoptionEvent:
    """A proposal cleared its adoption threshold and became an active
    rule (Work Package C)."""

    step: int
    patch_id: int
    rule_id: int
    rule_lineage_id: int
    proposer: int
    n_eligible: int
    n_supporters: int
    support_fraction: float
    adoption_threshold: float
    adoption_process: str
    founding_members: tuple = ()


@dataclass(frozen=True)
class RuleRejectionEvent:
    """A proposal failed to clear its adoption threshold, or its proposal
    window expired, or it was superseded by another proposal at the same
    patch the same step (Work Package C — "reasons for rejection where
    calculable")."""

    step: int
    patch_id: int
    proposer: int
    rule_lineage_id: int
    n_eligible: int
    n_supporters: int
    support_fraction: float
    adoption_threshold: float
    reason: str = "insufficient_support"


@dataclass(frozen=True)
class MembershipEvent:
    """A join, voluntary exit, or exclusion event for an already-active
    rule (Work Package D)."""

    step: int
    patch_id: int
    rule_id: int
    agent: int
    kind: str  # "join" | "exit" | "exclusion"
    reason: str = ""
    #: Level 1.2b, Work Package A: for ``kind == "exit"`` only, the amount
    #: actually deducted from ``agent.resources`` (``config.membership_exit_cost``
    #: capped at ``max(0.0, agent.resources - config.membership_exit_cost)``'s
    #: implied floor, i.e. never more than the agent's resources at the
    #: instant of exit) — not always exactly ``config.membership_exit_cost``
    #: when the agent's resources are low. An additional record, not an
    #: additional decision (same precedent as ``SanctionEvent.penalty_applied``):
    #: this field did not exist before, but the value it records was already
    #: being computed and applied; no exit behavior changes. Defaults to
    #: ``0.0`` so every pre-existing ``MembershipEvent(...)`` construction
    #: (including ``kind == "join"``/``"exclusion"``, where it is meaningless
    #: and left at its default) remains valid unchanged. Surfaced by the
    #: Level 1.2b ecological-ledger audit: the pre-existing behavior already
    #: capped this deduction at the agent's available resources, but nothing
    #: recorded when that cap actually bound, so a ledger built from
    #: ``config.membership_exit_cost`` alone silently overcounts demand for
    #: any agent that exits while low on resources.
    exit_cost_deducted: float = 0.0


@dataclass(frozen=True)
class ComplianceEvent:
    """One member's per-step intended-vs-actual ecological action under
    an active rule (Level 1.0, Work Package D/I — the "intended what
    ecological_policy would have requested" vs. "what the institution
    required" vs. "what the agent actually did" distinction). Produced
    only for agents who are members of an active rule this step;
    non-members' ecological actions are recorded only by the ordinary
    ``EcologicalActionEvent``, unchanged."""

    step: int
    patch_id: int
    rule_id: int
    agent: int
    intended_extraction: float
    intended_maintenance: float
    actual_extraction: float
    actual_maintenance: float
    complied: bool
    violated: bool
    #: True iff the compliance decision itself changed the action taken
    #: this step (i.e. ``complied`` and the rule's ceiling/requirement
    #: actually bound); False means either the agent violated, or it
    #: complied but its own ecological policy already satisfied the rule
    #: without needing to be constrained — distinguishing "the rule
    #: changed behavior" from "the agent happened to already comply."
    enforcement_altered_action: bool = False


@dataclass(frozen=True)
class MonitoringEvent:
    """One monitoring observation and its confusion-matrix outcome
    (Level 1.0, Work Package E — reusing the Level 0.1 confusion-matrix
    discipline). ``monitor`` is ``None`` only under
    ``monitoring_mode="perfect"`` (a diagnostic control with no specific
    observing agent)."""

    step: int
    patch_id: int
    rule_id: int
    target: int
    true_compliance: bool
    detected_violation: bool
    outcome: str  # "true_positive" | "false_positive" | "true_negative" | "false_negative"
    monitor: int | None = None
    cost_to_monitor: float = 0.0
    #: Level 1.2b, Work Package A: the amount actually deducted from
    #: ``monitor_agent.resources`` (``cost_to_monitor`` capped at
    #: ``max(0.0, monitor_agent.resources - cost_to_monitor)``'s implied
    #: floor) — not always exactly ``cost_to_monitor`` when the monitor's
    #: resources are low at the instant of monitoring. An additional
    #: record, not an additional decision (same precedent as
    #: ``SanctionEvent.penalty_applied``): this field did not exist
    #: before, but the value it records was already being computed and
    #: applied; no monitoring behavior changes. Defaults to ``0.0`` so
    #: every pre-existing ``MonitoringEvent(...)`` construction (including
    #: ``monitor is None`` under ``monitoring_mode="perfect"``, where it
    #: is meaningless and left at its default) remains valid unchanged.
    cost_deducted: float = 0.0


@dataclass(frozen=True)
class SanctionEvent:
    """One sanction event, distinct from Level 0 bilateral
    :class:`PunishmentEvent` because it (a) responds to violation of a
    shared rule, not a partner's defection in a single interaction, (b)
    is attached to a specific rule/rule-lineage, and (c) its cost may be
    distributed/funded rather than always borne by the wronged party
    (Level 1.0, Work Package F)."""

    step: int
    patch_id: int
    rule_id: int
    target: int
    magnitude: float
    cost: float
    funded_by: str  # "bystander" | "collective_fund" | "mechanical"
    false_sanction: bool  # the target was actually compliant (a detected false positive got sanctioned)
    sanctioner: int | None = None
    #: Level 1.2b, Work Package A: the amount actually deducted from
    #: ``target.resources`` (``min(magnitude * sanction_penalty_unit,
    #: target.resources)`` at the instant of sanctioning — capped, so not
    #: always exactly ``magnitude * sanction_penalty_unit``). An
    #: additional record, not an additional decision (same precedent as
    #: Level 1.1b's ``AppropriationOpportunityEvent``): this field did not
    #: exist before, but the value it records was already being computed
    #: and applied; no sanction behavior changes. Defaults to ``0.0`` so
    #: every pre-existing positional/keyword ``SanctionEvent(...)``
    #: construction (including in tests) remains valid unchanged. A
    #: real, previously-unrecorded ecological sink: this resource loss
    #: had no corresponding logged field anywhere prior to this addition,
    #: which the Level 1.2b ecological-ledger audit surfaced.
    penalty_applied: float = 0.0
    #: Level 1.2b, Work Package A: for ``funded_by == "bystander"`` only,
    #: the amount actually deducted from ``sanctioner.resources`` (``cost``
    #: capped at ``max(0.0, sanctioner.resources - cost)``'s implied
    #: floor) — not always exactly ``cost`` when the bystander's resources
    #: are low at the instant of sanctioning. Meaningless (left at its
    #: default) for ``funded_by in ("collective_fund", "mechanical")``,
    #: where the cost is either drawn from ``rule.fund`` with no cap
    #: (guarded upstream by ``rule.fund < cost``) or zero. An additional
    #: record, not an additional decision (same precedent as this event's
    #: own ``penalty_applied``): this field did not exist before, but the
    #: value it records was already being computed and applied; no
    #: sanction behavior changes. Defaults to ``0.0`` so every
    #: pre-existing ``SanctionEvent(...)`` construction remains valid
    #: unchanged.
    sanctioner_cost_deducted: float = 0.0


@dataclass(frozen=True)
class RuleAmendmentEvent:
    """A proposed change to one active rule's parameters and whether it
    was adopted through the same local support process used for adoption
    (Level 1.0, Work Package H)."""

    step: int
    patch_id: int
    rule_id: int
    rule_lineage_id: int
    proposer: int
    field_changed: str
    old_value: float
    new_value: float
    n_eligible: int
    n_supporters: int
    support_fraction: float
    adopted: bool
    #: Level 1.3, Work Package C: the actual threshold ``support_fraction``
    #: was compared against to decide ``adopted`` -- equal to
    #: ``rule.parameters.amendment_threshold`` unless entrenchment raised
    #: it this step (see ``core/entrenchment.py``), in which case this is
    #: the RAISED value. An additional record, not an additional decision
    #: (same precedent as ``AuditEvent.cost_deducted`` and siblings):
    #: without this field, a downstream analysis reading this event and
    #: comparing ``support_fraction`` against ``rule.parameters.
    #: amendment_threshold`` alone would silently see the WRONG threshold
    #: whenever entrenchment was active. Defaults to ``0.0`` for backward
    #: compatibility with any pre-existing direct construction (including
    #: this project's own tests).
    effective_amendment_threshold: float = 0.0


@dataclass(frozen=True)
class RuleDissolutionEvent:
    """An active rule dissolved (Level 1.0, Work Package H). ``reason``
    is one of ``"membership_below_floor"``, ``"support_below_floor"``,
    ``"inactive_duration_exceeded"``, or ``"fund_depleted"``.
    ``founder_present_at_dissolution`` distinguishes a rule that outlived
    its founder from one that dissolved with its founder still a
    member/present in the population."""

    step: int
    patch_id: int
    rule_id: int
    rule_lineage_id: int
    reason: str
    age_at_dissolution: int
    founder_present_at_dissolution: bool


@dataclass(frozen=True)
class DelegateNominationEvent:
    """One nomination toward a rule's (currently vacant) delegate slot
    (Level 1.1, Work Package D). Multiple nominations may occur the same
    step before selection resolves; every one is recorded, not only the
    eventual winner."""

    step: int
    patch_id: int
    rule_id: int
    rule_lineage_id: int
    nominator: int
    candidate: int
    self_nomination: bool


@dataclass(frozen=True)
class DelegateAppointmentEvent:
    """A candidate cleared the configured selection procedure and became
    this rule's active delegate (Work Package D). ``candidate_set`` and
    ``selector_population`` are recorded so appointment breadth is
    auditable after the fact (Work Package D requirement 7)."""

    step: int
    patch_id: int
    rule_id: int
    rule_lineage_id: int
    delegate_id: int
    agent: int
    tasks: tuple[str, ...]
    appointment_method: str  # "voluntary_approval" | "plurality_support" | "threshold_acceptance" | "lottery"
    candidate_set: tuple[int, ...]
    selector_population: tuple[int, ...]
    support_fraction: float
    predecessor_delegate_id: int | None = None
    institutional_memory_inherited: float = 0.0


@dataclass(frozen=True)
class DelegateRemovalEvent:
    """A delegate's tenure ended (Work Package D/G) — resignation,
    replacement, dormancy, recall, or the rule itself dissolving.
    ``reason`` is one of ``"resignation"``, ``"recalled"``,
    ``"dormant"``, ``"rule_dissolved"``, ``"member_exit"``."""

    step: int
    patch_id: int
    rule_id: int
    rule_lineage_id: int
    delegate_id: int
    agent: int
    reason: str
    tenure_steps: int
    final_capacity: float
    appropriated_total: float


@dataclass(frozen=True)
class TaskPerformanceEvent:
    """One delegate task-performance realization this step (Work Package
    E/F) — the generative-layer record every capacity/discretion
    computation is built from. ``outcome`` is ``"success"``,
    ``"failure"``, or ``"withheld"`` (effort deliberately reduced —
    Work Package F "effort reduction")."""

    step: int
    patch_id: int
    rule_id: int
    delegate_id: int
    agent: int
    task: str
    outcome: str
    capacity_before: float
    cost: float


@dataclass(frozen=True)
class AppropriationEvent:
    """A delegate diverted resources from the rule's collective fund for
    private benefit (Work Package F) — always fully resource-accounted:
    the amount removed from ``rule.fund`` equals the amount credited to
    the delegate's own ``resources`` (see ``tests`` ledger checks)."""

    step: int
    patch_id: int
    rule_id: int
    delegate_id: int
    agent: int
    amount: float
    fund_before: float
    fund_after: float


@dataclass(frozen=True)
class AppropriationOpportunityEvent:
    """Level 1.1b, Work Package D: logged every time an appropriation
    *opportunity* exists (``config.discretion_enabled and rule.fund >
    0.0``) — regardless of whether the delegate actually attempted
    anything. This is the record Level 1.1 never produced: ``
    AppropriationEvent`` only fires on an actual appropriation, so there
    was no way to tell "opportunity was rare" apart from "opportunity was
    common but conduct declined it" — a silent non-event, the same
    methodological gap Level 1.1's accountability/coordination results
    had. Distinguishes opportunity (an event exists at all -- ``O_t``),
    propensity (a fixed per-agent trait, read off unchanged), attempt
    propensity (``attempted`` — the realized Bernoulli draw at this
    opportunity), and conditional intensity (``fraction_of_opportunity``
    given ``attempted``). ``attempted_amount`` and ``realized_amount``
    are always equal in the current implementation (appropriation has no
    partial-failure mode — see ``rules/delegation.py::
    task_performance_round``); kept as two separate fields so a future
    partial-failure mechanism would not require an event-schema change."""

    step: int
    patch_id: int
    rule_id: int
    delegate_id: int
    agent: int
    fund_before: float
    appropriation_propensity: float
    p_appropriate: float
    attempted: bool
    attempted_amount: float
    realized_amount: float
    fraction_of_opportunity: float


@dataclass(frozen=True)
class AuditEvent:
    """A member's audit attempt against the current delegate (Work
    Package G) — imperfect: ``found_misconduct`` need not equal
    ``actual_misconduct_occurred`` (a confusion-matrix outcome, the same
    discipline as Level 1.0's ``MonitoringEvent``)."""

    step: int
    patch_id: int
    rule_id: int
    delegate_id: int
    auditor: int
    actual_misconduct_occurred: bool
    found_misconduct: bool
    outcome: str  # "true_positive" | "false_positive" | "true_negative" | "false_negative"
    cost: float
    #: Level 1.2b, Work Package A: the amount actually deducted from
    #: ``auditor.resources`` (``cost`` capped at ``max(0.0,
    #: auditor.resources - cost)``'s implied floor) — not always exactly
    #: ``cost`` when the auditor's resources are low at the instant of
    #: auditing. An additional record, not an additional decision (same
    #: precedent as ``SanctionEvent.penalty_applied``): this field did not
    #: exist before, but the value it records was already being computed
    #: and applied; no audit behavior changes. Defaults to ``0.0`` so
    #: every pre-existing ``AuditEvent(...)`` construction remains valid
    #: unchanged.
    cost_deducted: float = 0.0


@dataclass(frozen=True)
class RecallEvent:
    """A recall vote against the current delegate, triggered by an audit
    that found (correctly or falsely) misconduct (Work Package G).
    ``succeeded=False`` records "delegates can sometimes survive
    unsuccessful challenges" (Work Package G requirement 5)."""

    step: int
    patch_id: int
    rule_id: int
    delegate_id: int
    trigger_auditor: int
    n_eligible: int
    n_supporters: int
    support_fraction: float
    recall_threshold: float
    succeeded: bool
    recovered_funds: float = 0.0


@dataclass(frozen=True)
class AppealEvent:
    """An appeal against one of this rule's own sanction events (Work
    Package G) — distinct from ``RecallEvent`` (an appeal challenges one
    sanction; a recall challenges the delegate's continued tenure).
    ``upheld`` need not track ``was_false_sanction`` (imperfect
    information — appeal review is itself an error-prone local
    process)."""

    step: int
    patch_id: int
    rule_id: int
    delegate_id: int | None
    appellant: int
    original_sanction_step: int
    was_false_sanction: bool
    upheld: bool
    refund: float
    cost: float
    #: Level 1.2b, Work Package E production-scale ledger-residual fix
    #: (same "additional record, not additional decision" precedent as
    #: ``MonitoringEvent.cost_deducted``/``SanctionEvent.
    #: sanctioner_cost_deducted``/``MembershipEvent.exit_cost_deducted``/
    #: ``AuditEvent.cost_deducted``): ``cost`` above is the *intended*
    #: ``config.appeal_cost``, uncapped; ``cost_deducted`` is the actual
    #: (possibly resource-capped) amount deducted from the appellant's
    #: own resources, which can be less than ``cost`` — or, before this
    #: fix, spuriously negative if the appellant's resources were already
    #: negative (see ``rules/delegation.py``'s appeal-cost deduction site
    #: for the full explanation). Defaults to 0.0 for backward
    #: compatibility with any synthetic event predating this field.
    cost_deducted: float = 0.0


@dataclass(frozen=True)
class ContributionEvent:
    """One member's per-period collective-contribution decision (Work
    Package H) — deliberately independent of that member's ecological-
    rule compliance (a separate ledger, Work Package H requirement 2)."""

    step: int
    patch_id: int
    rule_id: int
    agent: int
    mode: str  # "equal" | "voluntary" | "proportional" | "negotiated"
    amount_asked: float
    amount_paid: float
    complied: bool
    fund_after: float


@dataclass(frozen=True)
class AdministrativeSpendingEvent:
    """One expenditure from a rule's collective fund (or, when the fund
    cannot cover it, from the delegate's own resources) on an
    administrative category (Work Package H requirement 4)."""

    step: int
    patch_id: int
    rule_id: int
    delegate_id: int | None
    category: str  # "monitoring" | "maintenance_coordination" | "record_keeping" | "communication" | "sanction" | "overhead"
    amount: float
    funded_by: str  # "collective_fund" | "delegate_personal"


@dataclass(frozen=True)
class FundDissolutionEvent:
    """What happened to a rule's remaining collective-fund balance at
    dissolution (Work Package H requirement 6) — resource-accounted:
    ``amount`` is fully disposed of via exactly one ``disposition``."""

    step: int
    patch_id: int
    rule_id: int
    rule_lineage_id: int
    amount: float
    disposition: str  # "distributed_to_members" | "lost" | "retained_for_reconstruction"
    n_recipients: int = 0


@dataclass(frozen=True)
class CoordinationProposalEvent:
    """A patch's active rule proposed an interpatch coordination link
    (Work Package I) — the second patch must independently accept (see
    ``CoordinationLinkEvent``); this event alone never creates a link."""

    step: int
    patch_id_from: int
    patch_id_to: int
    rule_id_from: int
    rule_id_to: int
    kind: str  # "information_exchange" | "ecological_restraint" | "shared_monitoring" | "mutual_assistance" | "shared_records"
    proposer: int


@dataclass(frozen=True)
class CoordinationLinkEvent:
    """Resolution of a pending interpatch coordination proposal —
    ``accepted=False`` records a rejection or an expired proposal window
    (Work Package I requirement: "rejections" must be exportable, not
    only acceptances)."""

    step: int
    link_id: int
    patch_id_a: int
    patch_id_b: int
    kind: str
    accepted: bool
    reason: str = ""


@dataclass(frozen=True)
class CoordinationActivityEvent:
    """One step of an already-active coordination link's operation
    (Work Package I) — information transmission is imperfect
    (``info_error``) and costly (``cost``); ``resource_transferred`` is
    0.0 except for ``kind="mutual_assistance"`` links that actually move
    resources this step."""

    step: int
    link_id: int
    patch_id_a: int
    patch_id_b: int
    info_accuracy: float
    resource_transferred: float
    cost: float


@dataclass(frozen=True)
class CoordinationDissolutionEvent:
    """An active interpatch coordination link ended (Work Package I)."""

    step: int
    link_id: int
    patch_id_a: int
    patch_id_b: int
    duration_steps: int
    reason: str  # "voluntary" | "rule_dissolved_a" | "rule_dissolved_b" | "sustained_inactivity"


@dataclass(frozen=True)
class CoordinationMaintenanceCostEvent:
    """Level 1.2b, Work Package E production-scale ledger-residual fix:
    ``rules/coordination.py``'s per-active-link maintenance fee
    (``config.coordination_cost_per_step``, deducted from each side's
    ``rule.fund``) is charged EVERY step for EVERY active link,
    unconditionally — independent of whether that same step's
    ``coordination_activity_probability`` roll fires and produces a
    ``CoordinationActivityEvent``. Before this event existed, the ledger
    only summed ``CoordinationActivityEvent.cost`` for
    ``demand_coordination_cost``, so on any step where the activity roll
    did not fire the fee was silently paid but never recorded — this was
    the dominant source of Level 1.2b's newly-discovered ledger residual
    at Work Package E's production scale (small at short scale, where
    few steps/links exist to hide it; large at hundreds of steps and
    multiple concurrent links). Logged once per active link per step,
    additively — ``CoordinationActivityEvent.cost`` is left unchanged for
    backward compatibility, but ``ecological_ledger.py`` now sums THIS
    event's ``cost`` instead of ``CoordinationActivityEvent.cost`` (never
    both, to avoid double-counting the same fee)."""

    step: int
    link_id: int
    cost: float


@dataclass(frozen=True)
class LocalInstitutionObservationEvent:
    """Level 1.2, Work Package B: one agent's imperfect, possibly
    delayed, possibly distorted perception of another patch's currently
    active institution. ``true_signal_hash`` links back to the ground-
    truth summary this perception was derived from, for observer-side
    audit only — no decision function ever reads a true signal directly,
    only ``perceived_*`` fields (Work Package B's "agents cannot see the
    observer-side phenotype vector or true global performance"
    requirement). ``source`` distinguishes passive cross-patch
    observation from an administrative report that could be selectively
    disclosed or distorted when discretion mechanisms support it."""

    step: int
    observer_patch_id: int
    target_patch_id: int
    observer_agent: int
    source: str  # "passive_observation" | "administrative_report" | "delegate_contact"
    signal_step: int  # step the underlying true state was drawn from (<= step; step - signal_step is the delay)
    perceived_resource_level: float
    perceived_fairness: float
    perceived_stability: float
    perceived_burden: float
    distorted: bool
    true_signal_hash: str


@dataclass(frozen=True)
class InstitutionComponentTransmissionEvent:
    """Level 1.2, Work Package C: one component-wise (or, rarely, whole-
    package) institutional transmission attempt. Distinguished from
    individual *policy* imitation (``ImitationEvent``/
    ``EcologicalImitationEvent``) — this event is about institutional
    *process* components copying between institutions, not an agent
    copying a peer's own strategy. ``outcome`` covers the full range
    Work Package C requires: faithful transfer, noisy transfer, mutation,
    recombination, rejection, and failure — never guaranteed success."""

    step: int
    source_institution_id: int
    receiver_institution_id: int
    source_patch_id: int
    receiver_patch_id: int
    route: str  # "migration" | "interpatch_communication" | "delegate_contact" | "observation" | "post_shock_learning" | "reconstruction" | "imitation_by_dissatisfied_member"
    component_name: str  # one of institution.INSTITUTION_COMPONENT_NAMES, or "__whole_package__"
    perceived_source_performance: float
    true_source_performance: float
    transmission_error: float  # magnitude of noise/mutation applied, 0.0 for a faithful copy
    outcome: str  # "faithful" | "noisy" | "mutated" | "recombined" | "rejected" | "failed" | "partial"
    adopted: bool


@dataclass(frozen=True)
class MigrationEvent:
    """Level 1.2, Work Package D: one agent's realized cross-patch
    migration (physical relocation, ``PatchSystem.agent_patch``
    reassignment) — distinguished from ``MembershipExitEvent`` (leaving a
    rule's membership while remaining resident on the same patch).
    ``outcome`` allows "attempted, refused/failed" as well as success."""

    step: int
    agent_id: int
    origin_patch_id: int
    destination_patch_id: int
    expected_resource_gain: float
    perceived_fairness_origin: float
    perceived_fairness_destination: float
    movement_cost: float
    outcome: str  # "succeeded" | "refused_cost" | "refused_no_capacity" | "failed"
    carried_institutional_knowledge: bool


@dataclass(frozen=True)
class MembershipExitEvent:
    """An agent left a rule's membership without physically migrating —
    kept distinct from ``MembershipEvent`` (Level 1.0's join/reason
    record) and from ``MigrationEvent`` (Work Package D requirement:
    "membership exit vs. physical migration" must be distinguishable)."""

    step: int
    agent_id: int
    rule_id: int
    patch_id: int
    reason: str


@dataclass(frozen=True)
class InstitutionExtinctionEvent:
    """Level 1.2, Work Package E: an institution's lineage ended —
    distinguished from a bare ``RuleDissolutionEvent`` (Level 1.1's own
    rule-level record, which this event does not replace) by carrying
    the *institution*-level bookkeeping (``InstitutionRecord``
    extinction) and an explicit ``selection_channel`` naming which
    neutral pressure realized the extinction (never a global fitness
    function — Work Package E requirement: "no global institutional
    fitness function")."""

    step: int
    institution_id: int
    lineage_id: int
    patch_id: int
    selection_channel: str  # "member_loss" | "ecological_collapse" | "administrative_overload" | "shock" | "fragmentation" | "voluntary_dissolution"
    final_member_count: int


@dataclass(frozen=True)
class CoordinationScaleChangeEvent:
    """Level 1.2, Work Package F: a coordination-network connected
    component gained or lost a patch, tracked via neutral quantities only
    (patch count, network size) — never named a state/federation/empire/
    any governance-type term."""

    step: int
    component_root_patch_id: int  # the lowest patch_id in the connected component, used as a stable identifier across steps
    jurisdiction_patch_count: int
    change: str  # "grew" | "shrank" | "fragmented" | "merged" | "dissolved"


@dataclass(frozen=True)
class LegitimacyEvent:
    """Level 1.3, Work Package D (Section 9): one step's updated dual
    legitimacy ledger values for one active rule — logged once per
    active rule per step whenever AT LEAST ONE of
    ``config.performance_legitimacy_enabled``/``config.procedural_
    legitimacy_enabled`` is on (the disabled channel's value stays at
    its ``SharedRule`` default, ``0.0``, and is still recorded here so a
    downstream reader never has to special-case which channel was on).
    "legitimacy" is permitted here per project_vision.md §5's Level 1.3
    amendment — the Agent-level ban is untouched."""

    step: int
    patch_id: int
    rule_id: int
    performance_legitimacy: float
    procedural_legitimacy: float
    performance_legitimacy_target: float
    procedural_legitimacy_target: float


#: event-class -> (EventLog attribute name). Declared once, next to the
#: event types themselves, so adding a new event type is a two-line change
#: (the dataclass above + one entry here) rather than an if/elif chain.
_EVENT_LOG_ATTR: dict[type, str] = {
    InteractionEvent: "interactions",
    PunishmentEvent: "punishments",
    ExitEvent: "exits",
    RewireEvent: "rewires",
    ImitationEvent: "imitations",
    MutationEvent: "mutations",
    EdgeAddedEvent: "edges_added",
    EdgeRemovedEvent: "edges_removed",
    FailedExitEvent: "failed_exits",
    ConnectionProposalEvent: "connection_proposals",
    SubsistenceEvent: "subsistence",
    WithholdEvent: "withholds",
    PerturbationEvent: "perturbations",
    ViabilityTransitionEvent: "viability_transitions",
    ReplacementEvent: "replacements",
    EcologicalActionEvent: "ecological_actions",
    EcologicalImitationEvent: "ecological_imitations",
    EcologicalMutationEvent: "ecological_mutations",
    RuleProposalEvent: "rule_proposals",
    RuleAdoptionEvent: "rule_adoptions",
    RuleRejectionEvent: "rule_rejections",
    MembershipEvent: "memberships",
    ComplianceEvent: "compliances",
    MonitoringEvent: "monitorings",
    SanctionEvent: "sanctions",
    RuleAmendmentEvent: "rule_amendments",
    RuleDissolutionEvent: "rule_dissolutions",
    DelegateNominationEvent: "delegate_nominations",
    DelegateAppointmentEvent: "delegate_appointments",
    DelegateRemovalEvent: "delegate_removals",
    TaskPerformanceEvent: "task_performances",
    AppropriationEvent: "appropriations",
    AppropriationOpportunityEvent: "appropriation_opportunities",
    AuditEvent: "audits",
    RecallEvent: "recalls",
    AppealEvent: "appeals",
    ContributionEvent: "contributions",
    AdministrativeSpendingEvent: "administrative_spending",
    FundDissolutionEvent: "fund_dissolutions",
    CoordinationProposalEvent: "coordination_proposals",
    CoordinationLinkEvent: "coordination_links",
    CoordinationActivityEvent: "coordination_activity",
    CoordinationDissolutionEvent: "coordination_dissolutions",
    CoordinationMaintenanceCostEvent: "coordination_maintenance_costs",
    # --- Level 1.2 -----------------------------------------------------
    LocalInstitutionObservationEvent: "local_institution_observations",
    InstitutionComponentTransmissionEvent: "institution_component_transmissions",
    MigrationEvent: "migrations",
    MembershipExitEvent: "membership_exits",
    InstitutionExtinctionEvent: "institution_extinctions",
    CoordinationScaleChangeEvent: "coordination_scale_changes",
    LegitimacyEvent: "legitimacy_events",
}


@dataclass
class EventLog:
    """Append-only container for all event types in a run."""

    interactions: list[InteractionEvent] = field(default_factory=list)
    punishments: list[PunishmentEvent] = field(default_factory=list)
    exits: list[ExitEvent] = field(default_factory=list)
    rewires: list[RewireEvent] = field(default_factory=list)
    imitations: list[ImitationEvent] = field(default_factory=list)
    mutations: list[MutationEvent] = field(default_factory=list)
    edges_added: list[EdgeAddedEvent] = field(default_factory=list)
    edges_removed: list[EdgeRemovedEvent] = field(default_factory=list)
    failed_exits: list[FailedExitEvent] = field(default_factory=list)
    connection_proposals: list[ConnectionProposalEvent] = field(default_factory=list)
    subsistence: list[SubsistenceEvent] = field(default_factory=list)
    withholds: list[WithholdEvent] = field(default_factory=list)
    perturbations: list[PerturbationEvent] = field(default_factory=list)
    viability_transitions: list[ViabilityTransitionEvent] = field(default_factory=list)
    replacements: list[ReplacementEvent] = field(default_factory=list)
    ecological_actions: list[EcologicalActionEvent] = field(default_factory=list)
    ecological_imitations: list[EcologicalImitationEvent] = field(default_factory=list)
    ecological_mutations: list[EcologicalMutationEvent] = field(default_factory=list)
    rule_proposals: list[RuleProposalEvent] = field(default_factory=list)
    rule_adoptions: list[RuleAdoptionEvent] = field(default_factory=list)
    rule_rejections: list[RuleRejectionEvent] = field(default_factory=list)
    memberships: list[MembershipEvent] = field(default_factory=list)
    compliances: list[ComplianceEvent] = field(default_factory=list)
    monitorings: list[MonitoringEvent] = field(default_factory=list)
    sanctions: list[SanctionEvent] = field(default_factory=list)
    rule_amendments: list[RuleAmendmentEvent] = field(default_factory=list)
    rule_dissolutions: list[RuleDissolutionEvent] = field(default_factory=list)
    # --- Level 1.1: delegation, capacity, discretion, accountability -------
    delegate_nominations: list[DelegateNominationEvent] = field(default_factory=list)
    delegate_appointments: list[DelegateAppointmentEvent] = field(default_factory=list)
    delegate_removals: list[DelegateRemovalEvent] = field(default_factory=list)
    task_performances: list[TaskPerformanceEvent] = field(default_factory=list)
    appropriations: list[AppropriationEvent] = field(default_factory=list)
    #: Level 1.1b, Work Package D — every appropriation *opportunity*
    #: (fund > 0 while discretion is enabled), whether or not attempted;
    #: superset of ``appropriations`` (every AppropriationEvent has a
    #: matching AppropriationOpportunityEvent with attempted=True, but
    #: not vice versa).
    appropriation_opportunities: list[AppropriationOpportunityEvent] = field(default_factory=list)
    audits: list[AuditEvent] = field(default_factory=list)
    recalls: list[RecallEvent] = field(default_factory=list)
    appeals: list[AppealEvent] = field(default_factory=list)
    contributions: list[ContributionEvent] = field(default_factory=list)
    administrative_spending: list[AdministrativeSpendingEvent] = field(default_factory=list)
    fund_dissolutions: list[FundDissolutionEvent] = field(default_factory=list)
    coordination_proposals: list[CoordinationProposalEvent] = field(default_factory=list)
    coordination_links: list[CoordinationLinkEvent] = field(default_factory=list)
    coordination_activity: list[CoordinationActivityEvent] = field(default_factory=list)
    coordination_dissolutions: list[CoordinationDissolutionEvent] = field(default_factory=list)
    #: Level 1.2b, Work Package E fix — see ``CoordinationMaintenanceCostEvent``'s
    #: own docstring: the unconditional per-step, per-active-link fee, a
    #: superset in coverage of ``coordination_activity`` (fires every step
    #: an active link exists, not only on the activity-probability roll).
    coordination_maintenance_costs: list[CoordinationMaintenanceCostEvent] = field(default_factory=list)
    # --- Level 1.2: open institutional evolution and blind phenotype discovery
    local_institution_observations: list[LocalInstitutionObservationEvent] = field(default_factory=list)
    institution_component_transmissions: list[InstitutionComponentTransmissionEvent] = field(default_factory=list)
    migrations: list[MigrationEvent] = field(default_factory=list)
    membership_exits: list[MembershipExitEvent] = field(default_factory=list)
    institution_extinctions: list[InstitutionExtinctionEvent] = field(default_factory=list)
    coordination_scale_changes: list[CoordinationScaleChangeEvent] = field(default_factory=list)
    legitimacy_events: list[LegitimacyEvent] = field(default_factory=list)

    def add(self, event: Any) -> None:
        attr = _EVENT_LOG_ATTR.get(type(event))
        if attr is None:
            raise TypeError(f"Unknown event type: {type(event)!r}")
        getattr(self, attr).append(event)

    def events_at_step(self, step: int) -> dict[str, list]:
        return {attr: [e for e in getattr(self, attr) if e.step == step] for attr in _EVENT_LOG_ATTR.values()}
