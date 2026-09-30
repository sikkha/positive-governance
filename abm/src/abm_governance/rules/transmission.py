"""Level 1.2, Work Package C: component-wise institutional transmission.

Reuses the same active-coordination-link topology Work Package B's
observation reuses (a disclosed simplification, not a claim the two must
always coincide) as the "interpatch_communication" transmission route.
Component-wise by default (``config.transmission_mode ==
"component_wise"``, one randomly selected component per attempt);
whole-package copy is the one explicit, separately-configured, rare
route (``config.transmission_mode == "whole_package"``) Work Package C
requires.

**No distance-to-preferred-macro-type calculation anywhere in this
module.** Copy probability depends only on the receiver's own noisy
*perceived* performance of the source (never the true value, never any
observer-side phenotype vector) — Section 3's prohibited action 11 ("no
rewarding agents for approaching any observer-side macro-vector") is
structurally impossible here since this module never imports the
observer-side phenotype module at all.

**Disclosed reduction**: the two descriptive-only Work Package A
components (``proposal_threshold``, ``authority_concentration``) are
excluded from the transmissible set — ``rules/institution.py::
components_from_rule`` derives both as fixed functions of other fields
rather than storing them independently, so there is no persistent slot
for a transmitted value to land in. See
``rules/institution.py``'s own module docstring for the full "live via
RuleParameters / live via override / descriptive only" accounting."""

from __future__ import annotations

import numpy as np

from abm_governance.core.config import (
    VALID_CONTRIBUTION_MODES,
    VALID_DELEGATE_SELECTION_PROCEDURES,
    SimulationConfig,
)
from abm_governance.core.events import EventLog, InstitutionComponentTransmissionEvent
from abm_governance.rules.coordination import CoordinationLink
from abm_governance.rules.institution import (
    _CATEGORICAL_COMPONENT_NAMES,
    _NUMERIC_COMPONENT_NAMES,
    _SET_COMPONENT_NAMES,
    InstitutionRecord,
)
from abm_governance.rules.shared_rule import RuleParameters, SharedRule

#: The twelve components this milestone's transmission wiring actually
#: moves -- see the module docstring for why the other two are excluded.
#:
#: **Cross-process reproducibility fix (Level 1.3b, Stage 0, task
#: #115).** Previously built as ``tuple(n for n in (A | B | C) if ...)``
#: -- iterating directly over a frozenset UNION of string component
#: names. Set/frozenset iteration order for ``str`` elements depends on
#: Python's per-process hash randomization (``PYTHONHASHSEED``), so this
#: constant's element ORDER (fixed once per process at import time, but
#: different across separate process launches) silently varied across
#: runs. ``rules/transmission.py::institution_transmission_round`` calls
#: ``rng.choice(TRANSMISSIBLE_COMPONENT_NAMES)`` to pick which component
#: transmits -- the RNG-drawn INDEX is fully deterministic given the
#: seed, but which component NAME sat at that index silently differed
#: by process, cascading into a different (though still internally
#: consistent) simulation trajectory. Confirmed via 15 separate process
#: launches of the same seeded config: contribution-event counts ranged
#: over {412..425} with the bug present, and were exactly 420 in all 15
#: launches once this was fixed to a stable, sorted order (see
#: ``docs/level1.3b_bargaining_activation_audit.md``'s sibling finding
#: in `docs/level1.3b_inference_audit.md` and this milestone's own
#: Stage 0 report, ``outputs/level13b_stage0_frozen_compatibility/``).
#: This bug predates Level 1.3b entirely (introduced at Level 1.2, Work
#: Package C) -- it was never caught before because every prior
#: "matched-seed"/"exact compatibility" check in this codebase ran both
#: compared configs within a SINGLE process invocation (sharing one
#: hash seed by construction), so it was structurally invisible until
#: Level 1.3b's Stage 0 compared a fresh run against an archive from a
#: DIFFERENT, earlier process for the first time.
TRANSMISSIBLE_COMPONENT_NAMES: tuple[str, ...] = tuple(
    sorted(
        n for n in (_NUMERIC_COMPONENT_NAMES | _CATEGORICAL_COMPONENT_NAMES | _SET_COMPONENT_NAMES)
        if n not in ("proposal_threshold", "authority_concentration")
    )
)

#: component name -> RuleParameters field name, for the four components
#: already behaviorally live via RuleParameters (see
#: ``rules/institution.py``'s module docstring).
_RULEPARAMETERS_BACKED: dict[str, str] = {
    "adoption_threshold": "adoption_threshold",
    "amendment_threshold": "amendment_threshold",
    "monitoring_allocation": "monitoring_intensity",
    "sanction_procedure": "sanction_magnitude",
}
#: The eight components backed by ``SharedRule.institution_overrides``.
_OVERRIDE_BACKED: frozenset[str] = frozenset(
    {
        "contribution_mechanism", "appeal_procedure", "recall_procedure",
        "delegated_task_distribution", "administrative_fund_rule",
        "memory_retention", "succession_procedure", "coordination_link_policy",
    }
)
#: RuleParameters fields that must stay strictly in (0, 1] (never exactly
#: 0), per ``RuleParameters.__post_init__``.
_OPEN_INTERVAL_FIELDS: frozenset[str] = frozenset({"adoption_threshold", "amendment_threshold"})


def apply_component_to_rule(rule: SharedRule, component_name: str, value) -> None:
    """Actually write a (possibly transformed) transmitted component
    value into the receiving rule -- the step that makes transmission
    genuinely behaviorally consequential, not merely recorded. Mutates
    ``rule.parameters`` (a fresh ``RuleParameters`` instance -- it is
    frozen) or ``rule.institution_overrides`` in place, depending on
    which tier ``component_name`` belongs to."""
    if component_name in _RULEPARAMETERS_BACKED:
        field_name = _RULEPARAMETERS_BACKED[component_name]
        current = rule.parameters.as_dict()
        v = float(value)
        if field_name in _OPEN_INTERVAL_FIELDS:
            v = float(np.clip(v, 1e-3, 1.0))
        else:
            v = float(np.clip(v, 0.0, 1.0))
        current[field_name] = v
        rule.parameters = RuleParameters(**current)
    elif component_name in _OVERRIDE_BACKED:
        overrides = dict(rule.institution_overrides or {})
        overrides[component_name] = value
        rule.institution_overrides = overrides
    else:
        raise ValueError(f"component {component_name!r} is not transmissible in Level 1.2's initial wiring")


def _performance_scalar(true_signal: dict) -> float:
    """A single scalar summary of a true institution signal, used only
    to derive a perceived-performance draw for transmission's own copy-
    probability adjustment -- never itself passed to any decision
    function; only the receiver's own *noisy* perception of it is."""
    terms = [v for v in (true_signal.get("resource_level"), true_signal.get("fairness")) if v is not None and not np.isnan(v)]
    return float(np.mean(terms)) if terms else float("nan")


def _attempt_one_component_transfer(
    step: int,
    source_rule: SharedRule,
    receiver_rule: SharedRule,
    source_inst: InstitutionRecord,
    receiver_inst: InstitutionRecord,
    component_name: str,
    perceived_source_performance: float,
    true_source_performance: float,
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
) -> None:
    if rng.random() < config.transmission_failure_probability:
        event_log.add(
            InstitutionComponentTransmissionEvent(
                step=step, source_institution_id=source_inst.institution_id, receiver_institution_id=receiver_inst.institution_id,
                source_patch_id=source_rule.patch_id, receiver_patch_id=receiver_rule.patch_id, route="interpatch_communication",
                component_name=component_name, perceived_source_performance=perceived_source_performance,
                true_source_performance=true_source_performance, transmission_error=0.0, outcome="failed", adopted=False,
            )
        )
        return

    source_value = getattr(source_inst.components, component_name)
    receiver_value = getattr(receiver_inst.components, component_name)
    transmission_error = 0.0
    outcome = "faithful"
    new_value = source_value

    if component_name in _NUMERIC_COMPONENT_NAMES:
        if config.transmission_recombination_probability > 0.0 and rng.random() < config.transmission_recombination_probability:
            weight = float(rng.uniform(0.3, 0.7))
            new_value = float(np.clip(weight * float(source_value) + (1.0 - weight) * float(receiver_value), 0.0, 1.0))
            outcome = "recombined"
            transmission_error = abs(new_value - float(source_value))
        elif config.transmission_mutation_std > 0.0:
            noise = float(rng.normal(0.0, config.transmission_mutation_std))
            new_value = float(np.clip(float(source_value) + noise, 0.0, 1.0))
            transmission_error = abs(noise)
            outcome = "noisy" if transmission_error < config.transmission_mutation_std * 1.5 else "mutated"
    elif component_name in _CATEGORICAL_COMPONENT_NAMES:
        mutate_prob = float(np.clip(config.transmission_mutation_std, 0.0, 1.0))
        if rng.random() < mutate_prob:
            choices = VALID_CONTRIBUTION_MODES if component_name == "contribution_mechanism" else VALID_DELEGATE_SELECTION_PROCEDURES
            candidate = str(rng.choice(list(choices)))
            if candidate != source_value:
                new_value = candidate
                outcome = "mutated"
                transmission_error = 1.0
    elif component_name in _SET_COMPONENT_NAMES:
        if config.transmission_mutation_std > 0.0 and rng.random() < config.transmission_mutation_std:
            n = len(source_value)
            subset_size = max(1, int(rng.integers(1, n + 1)))
            if subset_size < n:
                new_value = tuple(sorted(rng.choice(list(source_value), size=subset_size, replace=False).tolist()))
                outcome = "partial"
                transmission_error = 1.0 - (subset_size / n)

    # Rejection: a receiver may decline an inbound transfer outright
    # (switching cost / distrust proxy, Work Package C's own "rejected"
    # outcome) -- more likely when perceived source performance is low,
    # never zero (Work Package C: "must not guarantee survival" applies
    # symmetrically to acceptance).
    reject_probability = float(np.clip(0.3 * (1.0 - perceived_source_performance), 0.0, 1.0))
    adopted = rng.random() >= reject_probability
    if not adopted:
        outcome = "rejected"
    else:
        apply_component_to_rule(receiver_rule, component_name, new_value)

    event_log.add(
        InstitutionComponentTransmissionEvent(
            step=step, source_institution_id=source_inst.institution_id, receiver_institution_id=receiver_inst.institution_id,
            source_patch_id=source_rule.patch_id, receiver_patch_id=receiver_rule.patch_id, route="interpatch_communication",
            component_name=component_name, perceived_source_performance=perceived_source_performance,
            true_source_performance=true_source_performance, transmission_error=transmission_error,
            outcome=outcome, adopted=adopted,
        )
    )


def institution_transmission_round(
    step: int,
    rule_by_patch: dict[int, SharedRule],
    institution_registry: dict[int, InstitutionRecord],
    link_registry: dict[int, CoordinationLink],
    agents_by_id: dict[int, object],
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
    true_signal_history: dict[int, list[tuple[int, dict]]],
) -> None:
    """Once per step (only every ``config.transmission_period_steps``
    steps): every active coordination link is evaluated in both
    directions as a potential "interpatch_communication" transmission
    opportunity. A strict no-op when
    ``config.institutional_transmission_enabled`` is False."""
    if not config.institutional_transmission_enabled:
        return
    if step % max(1, config.transmission_period_steps) != 0:
        return

    for link in link_registry.values():
        if not link.active:
            continue
        for source_pid, receiver_pid in ((link.patch_id_a, link.patch_id_b), (link.patch_id_b, link.patch_id_a)):
            source_rule = rule_by_patch.get(source_pid)
            receiver_rule = rule_by_patch.get(receiver_pid)
            if source_rule is None or receiver_rule is None or not source_rule.active or not receiver_rule.active:
                continue
            source_inst = institution_registry.get(source_rule.rule_id)
            receiver_inst = institution_registry.get(receiver_rule.rule_id)
            if source_inst is None or receiver_inst is None:
                continue

            receiver_members = [
                agents_by_id[aid] for aid in receiver_rule.members
                if agents_by_id.get(aid) is not None and agents_by_id[aid].alive
            ]
            if not receiver_members:
                continue
            receiving_agent = receiver_members[int(rng.integers(0, len(receiver_members)))]

            history = true_signal_history.get(source_pid, [])
            true_signal = history[-1][1] if history else {"resource_level": float("nan"), "fairness": float("nan")}
            true_perf = _performance_scalar(true_signal)
            noise_scale = config.observation_noise_std * (1.0 - receiving_agent.observation_accuracy)
            perceived_perf = (
                float(np.clip(true_perf + rng.normal(0.0, noise_scale), 0.0, 1.0)) if not np.isnan(true_perf) else 0.5
            )

            p_attempt = float(np.clip(config.transmission_base_probability + (perceived_perf - 0.5) * 0.3, 0.0, 1.0))
            if rng.random() >= p_attempt:
                continue

            if config.transmission_mode == "whole_package":
                component_names = list(TRANSMISSIBLE_COMPONENT_NAMES)
            else:
                component_names = [str(rng.choice(TRANSMISSIBLE_COMPONENT_NAMES))]

            for component_name in component_names:
                _attempt_one_component_transfer(
                    step, source_rule, receiver_rule, source_inst, receiver_inst, component_name,
                    perceived_perf, true_perf, config, rng, event_log,
                )
