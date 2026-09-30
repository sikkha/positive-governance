"""The rule entity and its minimal parameter representation (Level 1.0,
Work Packages A/B).

A :class:`SharedRule` is attached to exactly one patch (Work Package A:
"The institution is attached to a local ecological patch, not globally
applied to all agents"). At most one rule is active per patch in Level
1.0 (the milestone's own permitted simplification); competing proposals
that lose the same-step tie-break, or that fail adoption, are still fully
observable via ``core/events.py::RuleProposalEvent``/``RuleRejectionEvent``
even though they never become active.

``RuleParameters`` (Work Package B) is the minimal, independently-mutable
representation the milestone specifies::

    I_j = (h_max, m_min, q_monitor, s, theta_adopt, theta_amend)

Nothing in this module reads or writes any agent's ``ecological_policy``
directly, any agent's *social* ``policy``, or any global/population-wide
quantity — every function here takes only the values it needs as
arguments (Work Package I: institutions must not silently overwrite the
ecological genotype; see ``rules/dynamics.py::apply_rule_compliance``
for where a rule's parameters are actually allowed to influence a
member's *actual* action, and note that it never touches the member's
stored ``ecological_policy``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

_PARAM_NAMES = (
    "extraction_ceiling",
    "maintenance_requirement",
    "monitoring_intensity",
    "sanction_magnitude",
    "adoption_threshold",
    "amendment_threshold",
)


@dataclass(frozen=True)
class RuleParameters:
    """I_j = (h_max, m_min, q_monitor, s, theta_adopt, theta_amend).

    ``extraction_ceiling``/``maintenance_requirement`` are propensity-
    scale values in ``[0, 1]`` (interpreted exactly like
    ``EcologicalPolicy.extraction_propensity``/``maintenance_propensity``
    — a ceiling/floor on the *propensity*, not the raw harvest-unit
    quantity, so a rule's content is comparable across patches with
    different ``ecological_harvest_unit`` scales). ``monitoring_intensity``
    and ``sanction_magnitude`` are the proposer's *preferred* monitoring/
    sanction strength (used as this rule's own record of what it asked
    for; the simulation's actual monitoring/sanctioning behavior is also
    governed by ``config.monitoring_mode``/``config.sanction_mode``, which
    this rule's own field does not override — see the module docstring of
    ``rules/dynamics.py``). ``adoption_threshold``/``amendment_threshold``
    are fractions in ``(0, 1]``.

    Low extraction and high maintenance are *not* assumed superior here —
    nothing in this dataclass or its construction favors any particular
    value; see ``propose_rule``/``mutate_rule_parameters`` in
    ``rules/dynamics.py`` for where actual values come from (a proposer's
    own traits, or a bounded perturbation of an existing lineage — never
    an optimization toward ecological outcome).
    """

    extraction_ceiling: float
    maintenance_requirement: float
    monitoring_intensity: float
    sanction_magnitude: float
    adoption_threshold: float
    amendment_threshold: float

    def __post_init__(self) -> None:
        for name in ("extraction_ceiling", "maintenance_requirement", "monitoring_intensity", "sanction_magnitude"):
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"RuleParameters.{name} must be in [0, 1], got {value}")
        for name in ("adoption_threshold", "amendment_threshold"):
            value = getattr(self, name)
            if not (0.0 < value <= 1.0):
                raise ValueError(f"RuleParameters.{name} must be in (0, 1], got {value}")

    def as_dict(self) -> dict:
        return {name: getattr(self, name) for name in _PARAM_NAMES}


@dataclass
class SharedRule:
    """One patch's currently-active (or dissolved, kept for lineage
    bookkeeping) locally shared rule.

    History (compliance/violation/observation/sanction/amendment counts)
    is kept here only as lightweight running totals, mirroring
    ``environment/patches.py::ResourcePatch``'s cumulative-ledger
    discipline — the full per-event record lives in the
    :class:`~abm_governance.core.events.EventLog`, not duplicated here.
    """

    rule_id: int
    patch_id: int
    parameters: RuleParameters
    founding_step: int
    founder_id: int
    rule_lineage_id: int
    active: bool = True
    members: frozenset = field(default_factory=frozenset)
    #: Agents who supported this rule's most recent adoption or amendment
    #: vote (distinct from ``members`` — a supporter may abstain from
    #: membership, though in this minimal implementation adoption support
    #: and founding membership coincide; kept as a separate field so a
    #: later amendment vote's supporter set does not silently overwrite
    #: who is actually a member).
    supporters: frozenset = field(default_factory=frozenset)
    #: Agents currently recognized as monitors of this rule
    #: (``config.monitoring_mode in {"designated"}`` only; empty under
    #: "none"/"voluntary"/"perfect", which have no persistent monitor
    #: identity).
    monitors: frozenset = field(default_factory=frozenset)
    #: Accumulated institutional fund (``config.sanction_mode ==
    #: "collective_fund"`` only; always 0.0 otherwise).
    fund: float = 0.0
    #: Cumulative counters (Work Package A "compliance/violation/
    #: observation/sanction/amendment history" — running totals; the full
    #: per-event record is in the EventLog).
    compliance_count: int = 0
    violation_count: int = 0
    observation_count: int = 0
    sanction_count: int = 0
    amendment_count: int = 0
    #: Consecutive steps this rule has had zero members (dissolution
    #: trigger bookkeeping).
    consecutive_empty_steps: int = 0
    #: Consecutive steps this rule's fund has been exactly 0.0 while a
    #: violation was detected (collective_fund dissolution trigger
    #: bookkeeping).
    consecutive_fund_depleted_steps: int = 0
    dissolved: bool = False
    dissolution_step: int | None = None
    dissolution_reason: str | None = None
    #: Which rule lineage this rule's own lineage descended from, if any
    #: (Work Package G "reconstruction" — a new rule at the same patch,
    #: proposed with parameters copied/mutated from the dissolved
    #: predecessor's lineage, rather than an independently-drawn fresh
    #: proposal).
    parent_rule_lineage_id: int | None = None

    # --- Level 1.1: institutional memory (Work Package E) -------------------
    #: A rule-level (not delegate-level) retained-knowledge scalar in
    #: ``[0, 1]`` — distinct from any individual delegate's own
    #: ``Delegate.record_quality``/task-performance history, which resets
    #: with that individual. On delegate replacement, a configurable
    #: fraction of the outgoing delegate's realized record quality is
    #: absorbed here (``config.institutional_memory_retention``) and a
    #: fraction of *this* value is, in turn, granted to the incoming
    #: delegate as a starting-quality bonus (see
    #: ``rules/delegation.py::_replace_delegate``) — "some knowledge may
    #: survive delegate replacement; some may be lost" (Work Package E
    #: requirement 7). Always ``0.0`` (a strict no-op) unless
    #: ``config.delegation_enabled`` is ``True``; reset to ``0.0`` on this
    #: rule's own dissolution (memory is tied to the rule's own
    #: continuity, not the population at large).
    institutional_memory: float = 0.0

    # --- Level 1.2: institution-component overrides (Work Package A) -------
    #: A strict no-op-by-default (``None``) per-institution override map,
    #: keyed by a subset of the Work Package A component names (see
    #: ``rules/institution.py::INSTITUTION_COMPONENT_NAMES``). Every call
    #: site that reads one of these components reads
    #: ``(rule.institution_overrides or {}).get(<name>, config.<default_field>)``
    #: — with no override present (``None``, or a dict missing that key),
    #: behavior is byte-for-byte identical to reading the global config
    #: field directly, exactly as every prior level's own config flags do.
    #: This keeps institution-component transmission (Work Package C)
    #: genuinely behaviorally consequential at its specific call site
    #: without requiring every component to migrate into
    #: :class:`RuleParameters` or a population-wide trait. See
    #: ``docs/odd_level1.2.md`` for the full per-component "live via
    #: RuleParameters / live via override / descriptive only" accounting.
    institution_overrides: dict | None = None

    # --- Level 1.3, Work Package D (Section 9): dual legitimacy ledgers ----
    #: Performance legitimacy (L_P) in [0, 1] — tracks toward this rule's
    #: own cumulative compliance rate (see ``core/legitimacy.py``).
    #: Always ``0.0`` (a strict no-op, never updated) unless
    #: ``config.performance_legitimacy_enabled``. "legitimacy" is
    #: permitted on ``SharedRule`` specifically per project_vision.md
    #: §5's Level 1.3 amendment — the Agent-level ban is untouched.
    performance_legitimacy: float = 0.0
    #: Procedural/reciprocal legitimacy (L_R) in [0, 1] — tracks toward
    #: the inverse of this rule's own cumulative sanction intensity (see
    #: ``core/legitimacy.py``). Always ``0.0`` unless
    #: ``config.procedural_legitimacy_enabled``.
    procedural_legitimacy: float = 0.0

    @property
    def n_members(self) -> int:
        return len(self.members)

    @property
    def age(self) -> int:
        return -1  # computed by the caller (needs current step); placeholder never read directly


def sample_rule_parameters(
    extraction_ceiling_mean: float, extraction_ceiling_std: float,
    maintenance_requirement_mean: float, maintenance_requirement_std: float,
    monitoring_intensity_mean: float, monitoring_intensity_std: float,
    sanction_magnitude_mean: float, sanction_magnitude_std: float,
    adoption_threshold_mean: float, adoption_threshold_std: float,
    amendment_threshold_mean: float, amendment_threshold_std: float,
    rng: np.random.Generator,
) -> RuleParameters:
    """Draw a fresh, neutral-initialization rule proposal — used only
    when a proposer's own preference traits are unavailable (this
    project's normal path draws a proposal directly from the proposer's
    own ``preferred_*`` agent traits instead; see
    ``rules/dynamics.py::propose_rule``). Kept for the milestone's
    explicit "or a neutral initialization distribution for proposal
    traits" allowance and for constructing the initial population's
    ``preferred_*`` traits themselves."""
    def _clip01(x):
        return float(np.clip(x, 0.0, 1.0))

    def _clip_open(x):
        return float(np.clip(x, 1e-3, 1.0))

    return RuleParameters(
        extraction_ceiling=_clip01(rng.normal(extraction_ceiling_mean, extraction_ceiling_std)),
        maintenance_requirement=_clip01(rng.normal(maintenance_requirement_mean, maintenance_requirement_std)),
        monitoring_intensity=_clip01(rng.normal(monitoring_intensity_mean, monitoring_intensity_std)),
        sanction_magnitude=_clip01(rng.normal(sanction_magnitude_mean, sanction_magnitude_std)),
        adoption_threshold=_clip_open(rng.normal(adoption_threshold_mean, adoption_threshold_std)),
        amendment_threshold=_clip_open(rng.normal(amendment_threshold_mean, amendment_threshold_std)),
    )


def mutate_rule_parameters(parameters: RuleParameters, mutation_std: float, rng: np.random.Generator) -> RuleParameters:
    """A bounded Gaussian perturbation of an *existing* rule's
    parameters — deliberately distinct from ecological-policy mutation's
    fresh redraw (see ``agents/ecological_policy.py::
    mutate_ecological_policy``'s docstring for why that one is a fresh
    draw): the milestone specifically asks for "mutation from an existing
    proposal," i.e. local variation around a lineage, not an independent
    re-roll that would sever the lineage's own identity. Each of the six
    parameters is perturbed independently and re-clipped to its valid
    range."""
    def _clip01(x):
        return float(np.clip(x, 0.0, 1.0))

    def _clip_open(x):
        return float(np.clip(x, 1e-3, 1.0))

    return RuleParameters(
        extraction_ceiling=_clip01(parameters.extraction_ceiling + rng.normal(0.0, mutation_std)),
        maintenance_requirement=_clip01(parameters.maintenance_requirement + rng.normal(0.0, mutation_std)),
        monitoring_intensity=_clip01(parameters.monitoring_intensity + rng.normal(0.0, mutation_std)),
        sanction_magnitude=_clip01(parameters.sanction_magnitude + rng.normal(0.0, mutation_std)),
        adoption_threshold=_clip_open(parameters.adoption_threshold + rng.normal(0.0, mutation_std)),
        amendment_threshold=_clip_open(parameters.amendment_threshold + rng.normal(0.0, mutation_std)),
    )
