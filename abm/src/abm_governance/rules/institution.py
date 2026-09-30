"""Level 1.2, Work Package A: institutional component representation.

This module is deliberately separate from ``rules/shared_rule.py``.
``RuleParameters`` (Level 1.0) is the minimal, already-behaviorally-live
six-field content of one patch's active rule; :class:`InstitutionComponents`
here is Work Package A's broader fourteen-component *process* vocabulary
(proposal/adoption/contribution/monitoring/sanction/appeal/recall/
delegation/administration/authority/amendment/memory/succession/
coordination), used for transmission, lineage, and blind phenotype
discovery in Level 1.2 -- never for classifying an outcome into a
governance type (Section 3's structural terminology guard applies to
every docstring and identifier in this module).

**No component here is a governance-type name, and nothing in this
module computes, stores, or exposes a "preferred" or "target" component
configuration.** Values arrive from a proposer's own traits (mirroring
``rules/dynamics.py::propose_rule``) or from transmission (Work Package
C, ``rules/transmission.py``) -- never from an optimization toward any
observer-side vector.

Honest accounting of behavioral consequence (see ``docs/odd_level1.2.md``
for the full narrative) -- of the fourteen named Work Package A
components, this module's :class:`InstitutionComponents` stores all
fourteen, but they fall into three tiers:

- **Live via ``RuleParameters``** (four; already behaviorally
  consequential since Level 1.0/1.1, unchanged by Level 1.2):
  ``adoption_threshold``, ``amendment_threshold``, ``monitoring_allocation``
  (mirrors ``RuleParameters.monitoring_intensity``), ``sanction_procedure``
  (mirrors ``RuleParameters.sanction_magnitude``).
- **Live via ``SharedRule.institution_overrides``** (eight; newly wired
  this milestone -- each is a strict no-op unless an override is present,
  see the call sites listed in each field's docstring below):
  ``contribution_mechanism``, ``appeal_procedure``, ``recall_procedure``,
  ``delegated_task_distribution``, ``administrative_fund_rule``,
  ``memory_retention``, ``succession_procedure``, ``coordination_link_policy``.
- **Descriptive only** (two; recorded, transmitted, hashed, and used in
  distance metrics like every other component, but not read by any
  decision function in Level 1.2 -- a disclosed scope reduction, not an
  oversight): ``proposal_threshold`` (this codebase's actual proposal
  mechanism is a per-agent probabilistic draw, ``Agent.proposal_probability``,
  not a threshold gate; the component slot is retained for transmission/
  lineage bookkeeping and left available for a future milestone to wire
  behaviorally) and ``authority_concentration`` (Work Package F itself
  lists this as a "neutral, purely descriptive scale quantity" -- it is
  computed observer-side by ``observer/institutional_phenotype.py``, never
  supplied as a generative input).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

import numpy as np

from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog, InstitutionExtinctionEvent
from abm_governance.rules.shared_rule import SharedRule

#: The fourteen Work Package A component names, in the milestone's own
#: listed order. Every :class:`InstitutionComponents` field name below
#: matches one entry here exactly (module-level constant, not
#: recomputed, so any accidental field/name drift fails loudly in tests).
INSTITUTION_COMPONENT_NAMES: tuple[str, ...] = (
    "proposal_threshold",
    "adoption_threshold",
    "contribution_mechanism",
    "monitoring_allocation",
    "sanction_procedure",
    "appeal_procedure",
    "recall_procedure",
    "delegated_task_distribution",
    "administrative_fund_rule",
    "authority_concentration",
    "amendment_threshold",
    "memory_retention",
    "succession_procedure",
    "coordination_link_policy",
)

#: Component names whose value is numeric (float) -- used by the
#: structural distance metric to decide comparison rules; every name not
#: listed here is treated as categorical/tuple-valued.
_NUMERIC_COMPONENT_NAMES: frozenset[str] = frozenset(
    {
        "proposal_threshold",
        "adoption_threshold",
        "monitoring_allocation",
        "sanction_procedure",
        "appeal_procedure",
        "recall_procedure",
        "administrative_fund_rule",
        "authority_concentration",
        "amendment_threshold",
        "memory_retention",
        "coordination_link_policy",
    }
)
#: Categorical (string-valued) components.
_CATEGORICAL_COMPONENT_NAMES: frozenset[str] = frozenset({"contribution_mechanism", "succession_procedure"})
#: Tuple-of-string-valued components.
_SET_COMPONENT_NAMES: frozenset[str] = frozenset({"delegated_task_distribution"})

assert _NUMERIC_COMPONENT_NAMES | _CATEGORICAL_COMPONENT_NAMES | _SET_COMPONENT_NAMES == set(INSTITUTION_COMPONENT_NAMES)


@dataclass(frozen=True)
class InstitutionComponents:
    """The fourteen-slot Work Package A component bundle. Every numeric
    field is a fraction/propensity-scale value in ``[0, 1]`` (mirroring
    ``RuleParameters``'s own convention), independently separable and
    copyable (Work Package A requirement 2) -- nothing here couples one
    component's value to another's.
    """

    proposal_threshold: float
    adoption_threshold: float
    contribution_mechanism: str
    monitoring_allocation: float
    sanction_procedure: float
    appeal_procedure: float
    recall_procedure: float
    delegated_task_distribution: tuple[str, ...]
    administrative_fund_rule: float
    authority_concentration: float
    amendment_threshold: float
    memory_retention: float
    succession_procedure: str
    coordination_link_policy: float

    def __post_init__(self) -> None:
        for name in _NUMERIC_COMPONENT_NAMES:
            value = getattr(self, name)
            if not (0.0 <= float(value) <= 1.0):
                raise ValueError(f"InstitutionComponents.{name} must be in [0, 1], got {value}")
        if not self.delegated_task_distribution:
            raise ValueError("InstitutionComponents.delegated_task_distribution must be non-empty")

    def as_dict(self) -> dict:
        d = {name: getattr(self, name) for name in INSTITUTION_COMPONENT_NAMES}
        d["delegated_task_distribution"] = list(d["delegated_task_distribution"])
        return d

    def to_overrides(self) -> dict:
        """The subset of components that are actually read by
        ``SharedRule.institution_overrides`` call sites (the eight
        "live via override" components) plus the four already-live-via-
        ``RuleParameters`` names are intentionally EXCLUDED here --
        writing them into ``institution_overrides`` would be silently
        ignored (no call site reads them from there), which would be
        misleading. Callers that want the ``RuleParameters``-backed
        components applied must construct a ``RuleParameters`` from
        this bundle's ``adoption_threshold``/``amendment_threshold``/
        ``monitoring_allocation``/``sanction_procedure`` values directly
        (see ``rules/dynamics.py::propose_rule``)."""
        return {
            "contribution_mechanism": self.contribution_mechanism,
            "appeal_procedure": self.appeal_procedure,
            "recall_procedure": self.recall_procedure,
            "delegated_task_distribution": self.delegated_task_distribution,
            "administrative_fund_rule": self.administrative_fund_rule,
            "memory_retention": self.memory_retention,
            "succession_procedure": self.succession_procedure,
            "coordination_link_policy": self.coordination_link_policy,
        }

    def component_hash(self) -> str:
        """Deterministic (order-independent-by-construction, since
        ``json.dumps(..., sort_keys=True)`` is used) SHA-256 hash of this
        bundle's exact content -- Work Package A requirement 7."""
        payload = json.dumps(self.as_dict(), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sample_institution_components(
    proposer_traits: dict,
    rng: np.random.Generator,
    *,
    contribution_modes: tuple[str, ...],
    succession_procedures: tuple[str, ...],
    delegation_tasks: tuple[str, ...],
) -> InstitutionComponents:
    """Draw a fresh institution-component bundle from a proposer's own
    traits where available (mirrors ``rules/dynamics.py::propose_rule``'s
    own "draws from the proposer's own preferred_* traits" discipline --
    never an optimization toward any target), falling back to a neutral
    uniform/random-choice draw for any trait the proposer does not carry.
    ``proposer_traits`` is a plain dict (not an ``Agent``) so this
    function stays decoupled from the agent module; callers pass
    whatever subset of
    ``{"proposal_threshold", "adoption_threshold", "monitoring_allocation",
    "sanction_procedure", "appeal_procedure", "recall_procedure",
    "administrative_fund_rule", "amendment_threshold", "memory_retention",
    "coordination_link_policy"}`` the proposer's own trait vector has."""

    def _draw(name: str, default_mean: float = 0.5, std: float = 0.15) -> float:
        if name in proposer_traits:
            return float(np.clip(proposer_traits[name], 0.0, 1.0))
        return float(np.clip(rng.normal(default_mean, std), 0.0, 1.0))

    n_tasks = int(rng.integers(1, len(delegation_tasks) + 1))
    task_subset = tuple(sorted(rng.choice(list(delegation_tasks), size=n_tasks, replace=False).tolist()))

    return InstitutionComponents(
        proposal_threshold=_draw("proposal_threshold"),
        adoption_threshold=float(np.clip(_draw("adoption_threshold", 0.5, 0.15), 1e-3, 1.0)),
        contribution_mechanism=str(rng.choice(list(contribution_modes))),
        monitoring_allocation=_draw("monitoring_allocation"),
        sanction_procedure=_draw("sanction_procedure"),
        appeal_procedure=_draw("appeal_procedure"),
        recall_procedure=_draw("recall_procedure"),
        delegated_task_distribution=task_subset,
        administrative_fund_rule=_draw("administrative_fund_rule"),
        authority_concentration=0.0,  # descriptive only; filled in observer-side, never generatively.
        amendment_threshold=float(np.clip(_draw("amendment_threshold", 0.5, 0.15), 1e-3, 1.0)),
        memory_retention=_draw("memory_retention"),
        succession_procedure=str(rng.choice(list(succession_procedures))),
        coordination_link_policy=_draw("coordination_link_policy"),
    )


@dataclass
class InstitutionRecord:
    """One institution's full lineage/provenance record (Work Package A
    requirement 3). Distinct from a single :class:`~abm_governance.rules.
    shared_rule.SharedRule` -- an institution's *jurisdiction* may later
    span multiple patches (Work Package F, "institutional scaling"),
    while a ``SharedRule`` is always attached to exactly one patch;
    Level 1.2's initial wiring keeps a 1:1 correspondence between an
    ``InstitutionRecord`` and the ``SharedRule`` it was created alongside
    (``active_jurisdiction`` starts as ``{patch_id}``), and Work Package F
    is what may grow ``active_jurisdiction`` beyond one patch.
    """

    institution_id: int
    lineage_id: int
    parent_institution_id: int | None
    origin_mechanism: str  # e.g. "fresh_proposal", "component_transmission", "reconstruction", "recombination"
    creation_time: int
    components: InstitutionComponents
    active_jurisdiction: frozenset[int] = field(default_factory=frozenset)
    amendment_history: tuple[dict, ...] = field(default_factory=tuple)
    transmission_history: tuple[dict, ...] = field(default_factory=tuple)
    extinction_time: int | None = None
    extinction_reason: str | None = None

    @property
    def extinct(self) -> bool:
        return self.extinction_time is not None

    def with_amendment(self, step: int, new_components: InstitutionComponents, changed_fields: tuple[str, ...]) -> "InstitutionRecord":
        """Return a new record reflecting one amendment event (never
        mutates ``self`` in place -- callers hold the registry and decide
        whether to replace the entry, matching ``SharedRule``'s own
        pattern of dataclass replacement over the amendment lineage)."""
        entry = {"step": step, "changed_fields": list(changed_fields), "component_hash_before": self.components.component_hash(), "component_hash_after": new_components.component_hash()}
        return InstitutionRecord(
            institution_id=self.institution_id,
            lineage_id=self.lineage_id,
            parent_institution_id=self.parent_institution_id,
            origin_mechanism=self.origin_mechanism,
            creation_time=self.creation_time,
            components=new_components,
            active_jurisdiction=self.active_jurisdiction,
            amendment_history=self.amendment_history + (entry,),
            transmission_history=self.transmission_history,
        )

    def with_transmission_record(self, entry: dict) -> "InstitutionRecord":
        return InstitutionRecord(
            institution_id=self.institution_id,
            lineage_id=self.lineage_id,
            parent_institution_id=self.parent_institution_id,
            origin_mechanism=self.origin_mechanism,
            creation_time=self.creation_time,
            components=self.components,
            active_jurisdiction=self.active_jurisdiction,
            amendment_history=self.amendment_history,
            transmission_history=self.transmission_history + (entry,),
        )

    def with_extinction(self, step: int, reason: str) -> "InstitutionRecord":
        return InstitutionRecord(
            institution_id=self.institution_id,
            lineage_id=self.lineage_id,
            parent_institution_id=self.parent_institution_id,
            origin_mechanism=self.origin_mechanism,
            creation_time=self.creation_time,
            components=self.components,
            active_jurisdiction=self.active_jurisdiction,
            amendment_history=self.amendment_history,
            transmission_history=self.transmission_history,
            extinction_time=step,
            extinction_reason=reason,
        )

    def record_hash(self) -> str:
        """Deterministic hash of the full record (not just the current
        component bundle) -- includes lineage/history, so two
        institutions with identical current components but different
        provenance hash differently."""
        payload = {
            "institution_id": self.institution_id,
            "lineage_id": self.lineage_id,
            "parent_institution_id": self.parent_institution_id,
            "origin_mechanism": self.origin_mechanism,
            "creation_time": self.creation_time,
            "components": self.components.as_dict(),
            "active_jurisdiction": sorted(self.active_jurisdiction),
            "amendment_history": list(self.amendment_history),
            "transmission_history": list(self.transmission_history),
            "extinction_time": self.extinction_time,
            "extinction_reason": self.extinction_reason,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


# --- Component-distance metrics (Work Package A requirement 6) -------------
#
# Four DELIBERATELY SEPARATE notions of similarity -- never merged into
# one "closeness to a preferred governance type" score (Section 3's
# twelfth prohibited action). Each returns a value in [0, 1] where 0.0 is
# identical/shared and 1.0 is maximally different/unrelated, so all four
# are directly comparable in scale without implying they measure the
# same thing.


def structural_distance(a: InstitutionComponents, b: InstitutionComponents) -> float:
    """How different two component bundles' CONTENT is -- normalized
    mean absolute difference over numeric components plus a mismatch
    rate over categorical/tuple components. Says nothing about whether
    the two institutions share ancestry or produced similar outcomes."""
    numeric_terms = [abs(float(getattr(a, n)) - float(getattr(b, n))) for n in _NUMERIC_COMPONENT_NAMES]
    categorical_terms = [0.0 if getattr(a, n) == getattr(b, n) else 1.0 for n in _CATEGORICAL_COMPONENT_NAMES]
    set_terms = []
    for n in _SET_COMPONENT_NAMES:
        sa, sb = set(getattr(a, n)), set(getattr(b, n))
        union = sa | sb
        set_terms.append(0.0 if not union else 1.0 - len(sa & sb) / len(union))
    all_terms = numeric_terms + categorical_terms + set_terms
    return float(np.mean(all_terms)) if all_terms else 0.0


def lineage_distance(a: InstitutionRecord, b: InstitutionRecord) -> float:
    """Whether two institutions share ancestry -- 0.0 if they share a
    ``lineage_id``, else a graded value based on whether one is the
    other's recorded parent (0.25), or neither (1.0, "independently
    convergent" candidates -- see Section 11). Says nothing about
    current component content."""
    if a.lineage_id == b.lineage_id:
        return 0.0
    if a.parent_institution_id == b.institution_id or b.parent_institution_id == a.institution_id:
        return 0.25
    return 1.0


def behavioral_distance(a_event_rates: dict, b_event_rates: dict) -> float:
    """Distance between two institutions' REALIZED event-rate profiles
    (e.g. per-step compliance/violation/sanction/appropriation rates
    exported by the existing observer diagnostics) -- a purely
    observer-side, post-hoc quantity, never a generative input, and
    computed only from realized rates, never from component content.
    Keys present in only one profile are treated as a mismatch of
    magnitude equal to the present value (a graceful, undefined-rate-
    tolerant comparison, mirroring ``effective_constraint``'s "every
    undefined rate returns None, never 0.0" discipline -- ``None``
    entries on either side are skipped entirely rather than coerced)."""
    keys = set(a_event_rates) | set(b_event_rates)
    terms = []
    for k in keys:
        va, vb = a_event_rates.get(k), b_event_rates.get(k)
        if va is None or vb is None:
            continue
        terms.append(abs(float(va) - float(vb)))
    return float(np.mean(terms)) if terms else float("nan")


def functional_distance(a_outcomes: dict, b_outcomes: dict) -> float:
    """Distance between two institutions' realized FUNCTIONAL outcomes
    (e.g. ecological viability, population retention, shock-recovery
    time -- observer-side phenotype-vector-adjacent quantities, but this
    function itself never reads the phenotype vector; callers pass
    whichever outcome dict they have). Kept separate from
    ``behavioral_distance`` because two institutions can behave
    similarly (same event rates) yet produce different functional
    outcomes under different environments, or vice versa -- collapsing
    the two would hide exactly that distinction."""
    keys = set(a_outcomes) | set(b_outcomes)
    terms = []
    for k in keys:
        va, vb = a_outcomes.get(k), b_outcomes.get(k)
        if va is None or vb is None:
            continue
        terms.append(abs(float(va) - float(vb)))
    return float(np.mean(terms)) if terms else float("nan")


# --- Institution lifecycle tracking (derives InstitutionRecord bookkeeping
# from the pre-existing SharedRule lineage/dissolution fields each step,
# rather than requiring every rule-creation/amendment/dissolution call site
# across rules/dynamics.py to separately push updates -- a disclosed,
# functionally-equivalent simplification: SharedRule already carries every
# provenance field (rule_lineage_id, parent_rule_lineage_id, founding_step,
# dissolved, dissolution_step, dissolution_reason) this needs.) -------------


def components_from_rule(rule: SharedRule, config: SimulationConfig) -> InstitutionComponents:
    """Reconstruct this rule's current full 14-component bundle: the four
    ``RuleParameters``-backed components read directly off
    ``rule.parameters``, the eight override-backed components read via
    ``(rule.institution_overrides or {}).get(name, config.<default>)``
    (exactly the same fallback every live call site uses -- this function
    never diverges from what the rule actually does), and the two
    descriptive-only components at their fixed defaults."""
    overrides = rule.institution_overrides or {}
    return InstitutionComponents(
        proposal_threshold=rule.parameters.adoption_threshold,  # descriptive only; see module docstring.
        adoption_threshold=rule.parameters.adoption_threshold,
        contribution_mechanism=overrides.get("contribution_mechanism", config.contribution_mode),
        monitoring_allocation=rule.parameters.monitoring_intensity,
        sanction_procedure=rule.parameters.sanction_magnitude,
        appeal_procedure=float(np.clip(overrides.get("appeal_procedure", config.appeal_probability), 0.0, 1.0)),
        recall_procedure=float(np.clip(overrides.get("recall_procedure", config.recall_support_threshold), 0.0, 1.0)),
        delegated_task_distribution=tuple(overrides.get("delegated_task_distribution") or config.delegated_tasks),
        administrative_fund_rule=float(np.clip(overrides.get("administrative_fund_rule", config.delegation_task_cost), 0.0, 1.0)),
        authority_concentration=0.0,  # descriptive only; computed observer-side, never here.
        amendment_threshold=rule.parameters.amendment_threshold,
        memory_retention=float(np.clip(overrides.get("memory_retention", config.institutional_memory_retention), 0.0, 1.0)),
        succession_procedure=overrides.get("succession_procedure", config.delegate_selection_procedure),
        coordination_link_policy=float(np.clip(overrides.get("coordination_link_policy", config.coordination_proposal_probability), 0.0, 1.0)),
    )


#: Level 1.2, Work Package E requirement: differential persistence must
#: be reported by *neutral pressure*, never a global institutional
#: fitness function. This maps the raw, already-existing Level 1.0/1.1
#: dissolution reasons (``rules/dynamics.py::_dissolve``'s own
#: vocabulary, unchanged by Level 1.2) onto Work Package E's five neutral
#: channels. The raw reason itself is never discarded — it stays
#: available unchanged in ``InstitutionRecord.extinction_reason``; only
#: ``InstitutionExtinctionEvent.selection_channel`` is normalized.
_SELECTION_CHANNEL_MAP: dict[str, str] = {
    "membership_below_floor": "member_loss",
    "inactive_duration_exceeded": "member_loss",
    "fund_depleted": "administrative_overload",
    "support_below_floor": "voluntary_dissolution",
}


def selection_channel_for_reason(reason: str | None) -> str:
    return _SELECTION_CHANNEL_MAP.get(reason or "", "unspecified")


def institution_lifecycle_round(
    step: int,
    rule_registry: dict[int, SharedRule],
    institution_registry: dict[int, InstitutionRecord],
    config: SimulationConfig,
    event_log: EventLog,
) -> None:
    """Once per step: create an :class:`InstitutionRecord` for any newly
    active rule not yet tracked, record an amendment for any tracked
    institution whose current component bundle no longer matches its
    last-recorded one, and record an extinction for any tracked
    institution whose rule has since dissolved. Institution ids are the
    corresponding rule's own ``rule_id`` (a 1:1 correspondence in Level
    1.2's initial wiring -- Work Package F's scaling mechanism is what
    later lets one institution's ``active_jurisdiction`` span more than
    one patch; see ``InstitutionRecord``'s own docstring). A strict no-op
    when ``rule_registry`` is empty."""
    for rule_id, rule in rule_registry.items():
        current_components = components_from_rule(rule, config)
        existing = institution_registry.get(rule_id)
        if existing is None:
            parent_institution_id = None
            origin_mechanism = "fresh_proposal"
            if rule.parent_rule_lineage_id is not None:
                origin_mechanism = "reconstruction"
                for other in institution_registry.values():
                    if other.lineage_id == rule.parent_rule_lineage_id:
                        parent_institution_id = other.institution_id
                        break
            institution_registry[rule_id] = InstitutionRecord(
                institution_id=rule_id,
                lineage_id=rule.rule_lineage_id,
                parent_institution_id=parent_institution_id,
                origin_mechanism=origin_mechanism,
                creation_time=rule.founding_step,
                components=current_components,
                active_jurisdiction=frozenset({rule.patch_id}),
            )
            continue

        if existing.extinct:
            continue

        if rule.dissolved:
            institution_registry[rule_id] = existing.with_extinction(
                step, rule.dissolution_reason or "unspecified"
            )
            event_log.add(
                InstitutionExtinctionEvent(
                    step=step, institution_id=rule_id, lineage_id=existing.lineage_id,
                    patch_id=rule.patch_id, selection_channel=selection_channel_for_reason(rule.dissolution_reason),
                    final_member_count=rule.n_members,
                )
            )
            continue

        if current_components.component_hash() != existing.components.component_hash():
            changed = tuple(
                name for name in INSTITUTION_COMPONENT_NAMES
                if getattr(current_components, name) != getattr(existing.components, name)
            )
            institution_registry[rule_id] = existing.with_amendment(step, current_components, changed)
