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

    def add(self, event: Any) -> None:
        attr = _EVENT_LOG_ATTR.get(type(event))
        if attr is None:
            raise TypeError(f"Unknown event type: {type(event)!r}")
        getattr(self, attr).append(event)

    def events_at_step(self, step: int) -> dict[str, list]:
        return {attr: [e for e in getattr(self, attr) if e.step == step] for attr in _EVENT_LOG_ATTR.values()}
