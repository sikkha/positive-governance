"""Level 1.2, Work Package B: local institutional observation.

Agents never see the observer-side phenotype vector (``observer/
institutional_phenotype.py``, Section 6) or any true global-performance
quantity. What an agent *can* act on is a noisy, possibly delayed,
possibly distorted **local perception** of another institution's
condition — this module produces that perception, and only that
perception, as a :class:`~abm_governance.core.events.
LocalInstitutionObservationEvent`. The **true** underlying values
(:func:`compute_true_institution_signal`) are computed and logged
alongside every perception purely for observer-side audit (linked by
``true_signal_hash``) — no decision function anywhere in this codebase
reads a true signal directly; every downstream generative use (Work
Package C's transmission, Work Package D's migration) reads only
``perceived_*`` fields.

**Locally-constrained**: observation is not global. It travels only over
the same active interpatch coordination links Work Package I (Level 1.1)
already tracks — a patch with no coordination link to any other patch
observes nothing about any other patch this milestone. This is a
disclosed reuse of an existing topology, not a claim that coordination
and observation must always coincide in a later milestone."""

from __future__ import annotations

import numpy as np

from abm_governance.agents.agent import Agent
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog, LocalInstitutionObservationEvent
from abm_governance.environment.patches import ResourcePatch
from abm_governance.rules.coordination import CoordinationLink
from abm_governance.rules.institution import InstitutionRecord
from abm_governance.rules.shared_rule import SharedRule


def compute_true_institution_signal(rule: SharedRule, patch: ResourcePatch) -> dict:
    """Pure, read-only ground-truth summary of one patch's currently
    active institution — a generative-layer quantity available for
    propagation (unlike the observer package's own diagnostics, this is
    computed inline during a run, not post-hoc), but never itself passed
    to any decision function. Four dimensions, deliberately simple and
    directly computable from already-tracked ``SharedRule``/
    ``ResourcePatch`` fields (never imported from ``observer/``, which
    would violate the generative/observer one-directional dependency):

    - ``resource_level``: the target patch's own fraction of capacity.
    - ``fairness``: ``1 - sanctions / (compliances + violations)`` — a
      cheap realized-sanction-rate proxy, deliberately distinct from
      (and simpler than) ``observer/accountability_diagnostics.py``'s
      own ``effective_constraint()``, which this module must not import.
    - ``stability``: ``1.0`` while the rule is active and undissolved,
      ``0.0`` once dissolved (this function is only ever called on an
      active rule, so it always returns ``1.0`` in practice — kept as an
      explicit field for future extension, e.g. age-normalized
      stability).
    - ``burden``: this step's realized fund spend per member (0 if no
      spend recorded, i.e. ``rule.fund`` itself is not a burden measure
      -- consumption is).
    """
    resource_level = patch.fraction_of_capacity
    total_interactions = rule.compliance_count + rule.violation_count
    fairness = 1.0 - (rule.sanction_count / total_interactions) if total_interactions > 0 else float("nan")
    stability = 0.0 if rule.dissolved else 1.0
    burden = (rule.fund / rule.n_members) if rule.n_members > 0 else 0.0
    return {
        "resource_level": float(np.clip(resource_level, 0.0, 1.0)),
        "fairness": fairness,
        "stability": stability,
        "burden": float(burden),
    }


def _hash_true_signal(true_signal: dict) -> str:
    import hashlib
    import json

    return hashlib.sha256(json.dumps(true_signal, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def form_local_observation(
    step: int,
    observer_patch_id: int,
    target_patch_id: int,
    observer_agent: Agent,
    true_signal: dict,
    config: SimulationConfig,
    rng: np.random.Generator,
    *,
    source: str,
    signal_step: int,
    distortion_scale: float = 0.0,
) -> LocalInstitutionObservationEvent:
    """One agent's noisy/delayed/possibly-distorted perception of one
    target patch's true institution signal. ``distortion_scale`` (only
    ever nonzero when ``source == "administrative_report"`` and
    ``config.discretion_enabled``) shifts every perceived value toward a
    fixed, arbitrary-but-deterministic bias direction (never toward a
    "more favorable to the reporting delegate" direction specifically —
    Work Package B requires reports to be *possibly* mistaken/distorted,
    not systematically self-serving, which would be a hidden generative
    assumption this milestone's outcome-blindness rule forbids)."""
    noise_scale = config.observation_noise_std * (1.0 - observer_agent.observation_accuracy)

    def _perceive(true_value: float) -> float:
        if np.isnan(true_value):
            return float("nan")
        noisy = true_value + rng.normal(0.0, noise_scale)
        if distortion_scale > 0.0:
            # A fixed, deterministic-direction bias (away from the
            # neutral midpoint 0.5) scaled by distortion_scale -- not
            # correlated with whether it favors any particular agent.
            bias_direction = 1.0 if true_value >= 0.5 else -1.0
            noisy += bias_direction * distortion_scale * 0.2
        return float(np.clip(noisy, 0.0, 1.0))

    distorted = distortion_scale > 0.0
    return LocalInstitutionObservationEvent(
        step=step,
        observer_patch_id=observer_patch_id,
        target_patch_id=target_patch_id,
        observer_agent=observer_agent.agent_id,
        source=source,
        signal_step=signal_step,
        perceived_resource_level=_perceive(true_signal["resource_level"]),
        perceived_fairness=_perceive(true_signal["fairness"]),
        perceived_stability=_perceive(true_signal["stability"]),
        perceived_burden=float(np.clip(true_signal["burden"] + rng.normal(0.0, noise_scale), 0.0, None)),
        distorted=distorted,
        true_signal_hash=_hash_true_signal(true_signal),
    )


def local_observation_round(
    step: int,
    rule_by_patch: dict[int, SharedRule],
    patches: dict[int, ResourcePatch],
    link_registry: dict[int, CoordinationLink],
    institution_registry: dict[int, InstitutionRecord],
    agents_by_id: dict[int, "Agent"],
    delegate_registry: dict,
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
    true_signal_history: dict[int, list[tuple[int, dict]]],
) -> None:
    """Once per step (only every ``config.observation_period_steps``
    steps): every active coordination link produces exactly two
    observations (each direction), plus true-signal history bookkeeping
    for every currently active rule (kept regardless of whether it is
    observed this step, so a later delayed observation elsewhere can
    still find it). A strict no-op when
    ``config.institutional_observation_enabled`` is False."""
    # True-signal history bookkeeping happens every step this function is
    # called (not gated by the period), so delay lookups stay accurate
    # regardless of how often observations themselves are formed.
    max_history = max(1, config.observation_delay_max_steps + 1)
    for pid, rule in rule_by_patch.items():
        if not rule.active:
            continue
        true_signal = compute_true_institution_signal(rule, patches[pid])
        history = true_signal_history.setdefault(pid, [])
        history.append((step, true_signal))
        if len(history) > max_history:
            del history[: len(history) - max_history]

    if not config.institutional_observation_enabled:
        return
    if step % max(1, config.observation_period_steps) != 0:
        return

    for link in link_registry.values():
        if not link.active:
            continue
        for observer_pid, target_pid in ((link.patch_id_a, link.patch_id_b), (link.patch_id_b, link.patch_id_a)):
            target_rule = rule_by_patch.get(target_pid)
            if target_rule is None or not target_rule.active:
                continue
            observer_rule = rule_by_patch.get(observer_pid)
            if observer_rule is None or not observer_rule.members:
                continue
            observer_members = [
                agents_by_id[aid] for aid in observer_rule.members
                if agents_by_id.get(aid) is not None and agents_by_id[aid].alive
            ]
            if not observer_members:
                continue
            observer_agent = observer_members[int(rng.integers(0, len(observer_members)))]

            delay = int(rng.integers(0, config.observation_delay_max_steps + 1)) if config.observation_delay_max_steps > 0 else 0
            history = true_signal_history.get(target_pid, [])
            signal_step, true_signal = history[-1] if history else (step, compute_true_institution_signal(target_rule, patches[target_pid]))
            if delay > 0 and history:
                target_signal_step = step - delay
                best = min(history, key=lambda entry: abs(entry[0] - target_signal_step))
                signal_step, true_signal = best

            target_delegate = delegate_registry.get(target_rule.rule_id)
            use_admin_report = (
                config.discretion_enabled
                and target_delegate is not None
                and target_delegate.active
            )
            source = "administrative_report" if use_admin_report else "passive_observation"
            distortion_scale = 0.0
            if use_admin_report and config.administrative_report_distortion_scale > 0.0:
                reporting_agent = agents_by_id.get(target_delegate.agent_id)
                if reporting_agent is not None:
                    distortion_scale = float(
                        reporting_agent.effort_reduction_propensity * config.administrative_report_distortion_scale
                    )

            event = form_local_observation(
                step, observer_pid, target_pid, observer_agent, true_signal, config, rng,
                source=source, signal_step=signal_step, distortion_scale=distortion_scale,
            )
            event_log.add(event)
