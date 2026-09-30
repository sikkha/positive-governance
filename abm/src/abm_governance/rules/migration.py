"""Level 1.2, Work Package D: migration and membership selection.

**No encoded "people prefer democracy/strong states."** Every term in
the migration/exit utility comparison below is a neutral, already-
existing (or newly added, equally neutral) per-agent trait —
``violation_tolerance``, ``exit_cost``, ``social_trust``,
``risk_sensitivity``, ``contribution_willingness`` (reused from prior
levels, exactly the reuse discipline Work Package B/C already
established) plus one new trait, ``Agent.migration_propensity`` (a
baseline sensitivity scale, not a fixed "wants to move" flag — see that
field's own docstring). None of these traits, individually or combined,
encode a preference for any institutional *process* — an agent with
identical traits evaluates every candidate destination by the exact same
formula regardless of what that destination's institution's components
happen to be.

Two structurally distinct outcomes, per Work Package D's own
requirement:

- :func:`migration_round` — **physical relocation**
  (``PatchSystem.migrate``), which always also exits the agent from its
  origin rule's membership if it was a member (an agent cannot remain a
  voting/compliance member of a rule at a patch it no longer resides on
  in this codebase's existing invariant — every other rule-formation
  mechanism assumes rule membership is patch-local).
- :func:`membership_exit_round` — **membership exit only**: a resident
  agent leaves its own rule's membership without relocating (e.g. out of
  dissatisfaction), evaluated independently.

Both are gated by their own master flags
(``migration_enabled``/``membership_exit_enabled``, both default
``False``) and both preserve exact population accounting: no code path
here ever adds or removes an ``Agent`` object, or an entry from
``PatchSystem.agent_patch`` — only ``patch_id``/rule-membership
*assignment* changes.
"""

from __future__ import annotations

import numpy as np

from abm_governance.agents.adaptation import _stable_sigmoid
from abm_governance.agents.agent import Agent
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog, MembershipExitEvent, MigrationEvent
from abm_governance.environment.patches import PatchSystem
from abm_governance.rules.shared_rule import SharedRule


def _perceived_patch_signal(
    agent: Agent, patch_id: int, true_signal_history: dict[int, list[tuple[int, dict]]],
    config: SimulationConfig, rng: np.random.Generator,
) -> dict:
    """The same imperfect-perception discipline Work Package B/C use —
    an agent's own noisy read of the most recent true signal recorded
    for ``patch_id`` (Work Package B's history cache, reused here rather
    than duplicated). A patch this agent has no recorded history for
    (never reached by any observation) is perceived at a neutral prior
    (0.5 / 0.0 burden) — never a systematically pessimistic or
    optimistic default, which would itself be a hidden generative bias."""
    history = true_signal_history.get(patch_id, [])
    noise_scale = config.observation_noise_std * (1.0 - agent.observation_accuracy)
    if not history:
        return {"resource_level": 0.5, "fairness": 0.5, "burden": 0.0}
    _, true_signal = history[-1]

    def _perceive(key: str, default: float) -> float:
        v = true_signal.get(key, default)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            v = default
        return float(v + rng.normal(0.0, noise_scale))

    return {
        "resource_level": float(np.clip(_perceive("resource_level", 0.5), 0.0, 1.0)),
        "fairness": float(np.clip(_perceive("fairness", 0.5), 0.0, 1.0)),
        "burden": float(max(0.0, _perceive("burden", 0.0))),
    }


def _sanction_exposure(rule: SharedRule | None) -> float:
    if rule is None:
        return 0.0
    total = rule.compliance_count + rule.violation_count
    return (rule.sanction_count / total) if total > 0 else 0.0


def _utility(agent: Agent, rule: SharedRule | None, perceived: dict, is_member: bool) -> float:
    """Neutral utility of being at (and, if ``is_member``, a member of)
    one patch's institution — every weight below is either a fixed,
    symmetric constant (applied identically to origin and destination)
    or a heterogeneous per-agent trait; none is a governance-content
    term."""
    familiarity_bonus = 0.15 if is_member else 0.0
    exposure = _sanction_exposure(rule)
    return (
        perceived["resource_level"]
        + perceived["fairness"]
        - 0.1 * perceived["burden"]
        - exposure * (1.0 - agent.violation_tolerance)
        + familiarity_bonus
    )


def migration_round(
    step: int,
    rule_by_patch: dict[int, SharedRule],
    patch_system: PatchSystem,
    agents_by_id: dict[int, Agent],
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
    true_signal_history: dict[int, list[tuple[int, dict]]],
) -> None:
    """Once per step (only every
    ``config.migration_evaluation_period_steps`` steps): every living
    agent evaluates exactly one uniformly-random candidate destination
    patch against its current one. A strict no-op when
    ``config.migration_enabled`` is False."""
    if not config.migration_enabled:
        return
    if step % max(1, config.migration_evaluation_period_steps) != 0:
        return
    patch_ids = list(patch_system.patches.keys())
    if len(patch_ids) < 2:
        return
    noise = max(config.migration_decision_noise_std, 1e-6)

    for agent_id in list(patch_system.agent_patch.keys()):
        agent = agents_by_id.get(agent_id)
        if agent is None or not agent.alive or agent.migration_propensity <= 0.0:
            continue
        origin_pid = patch_system.agent_patch[agent_id]
        candidates = [pid for pid in patch_ids if pid != origin_pid]
        destination_pid = int(rng.choice(candidates))

        origin_rule = rule_by_patch.get(origin_pid)
        dest_rule = rule_by_patch.get(destination_pid)
        is_member_origin = origin_rule is not None and origin_rule.active and agent_id in origin_rule.members

        perceived_origin = _perceived_patch_signal(agent, origin_pid, true_signal_history, config, rng)
        perceived_dest = _perceived_patch_signal(agent, destination_pid, true_signal_history, config, rng)

        utility_stay = _utility(agent, origin_rule, perceived_origin, is_member_origin)
        utility_move = (
            _utility(agent, dest_rule, perceived_dest, False)
            - config.migration_cost * 0.05 * agent.exit_cost
            - 0.1 * agent.social_trust
        )

        p_move = _stable_sigmoid((utility_move - utility_stay) / noise) * agent.migration_propensity
        if rng.random() >= p_move:
            continue

        capacity_ok = True
        if config.migration_capacity_per_patch is not None:
            capacity_ok = len(patch_system.patches[destination_pid].members) < config.migration_capacity_per_patch

        expected_gain = perceived_dest["resource_level"] - perceived_origin["resource_level"]
        if not capacity_ok:
            outcome = "refused_no_capacity"
        elif config.migration_cost > agent.resources:
            outcome = "refused_cost"
        else:
            outcome = "succeeded"

        carried_knowledge = False
        if outcome == "succeeded":
            agent.resources -= config.migration_cost
            if is_member_origin:
                origin_rule.members = origin_rule.members - {agent_id}
                agent.rule_member_of = None
                event_log.add(
                    MembershipExitEvent(step=step, agent_id=agent_id, rule_id=origin_rule.rule_id, patch_id=origin_pid, reason="migration")
                )
                # The agent's own experience of the origin institution
                # travels with it (Work Package C's "migration" route is
                # realized here, not as a separate transmission-round
                # call -- the knowledge only *could* later inform an
                # imitation-by-dissatisfied-member event at the
                # destination; it grants no automatic membership there,
                # per Work Package D's own "no accidental institutional
                # imposition via migration" implicit requirement).
                carried_knowledge = True
            patch_system.migrate(agent_id, destination_pid)
            agent.patch_id = destination_pid

        event_log.add(
            MigrationEvent(
                step=step, agent_id=agent_id, origin_patch_id=origin_pid, destination_patch_id=destination_pid,
                expected_resource_gain=expected_gain, perceived_fairness_origin=perceived_origin["fairness"],
                perceived_fairness_destination=perceived_dest["fairness"], movement_cost=config.migration_cost,
                outcome=outcome, carried_institutional_knowledge=carried_knowledge,
            )
        )


def membership_exit_round(
    step: int,
    rule_by_patch: dict[int, SharedRule],
    agents_by_id: dict[int, Agent],
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
) -> None:
    """Once per step (only every
    ``config.migration_evaluation_period_steps`` steps): every member of
    every active rule evaluates whether to leave membership without
    relocating. A strict no-op when ``config.membership_exit_enabled``
    is False."""
    if not config.membership_exit_enabled:
        return
    if step % max(1, config.migration_evaluation_period_steps) != 0:
        return
    noise = max(config.migration_decision_noise_std, 1e-6)
    for pid, rule in rule_by_patch.items():
        if not rule.active or not rule.members:
            continue
        exposure = _sanction_exposure(rule)
        burden = (rule.fund / rule.n_members) if rule.n_members > 0 else 0.0
        for agent_id in list(rule.members):
            agent = agents_by_id.get(agent_id)
            if agent is None or not agent.alive:
                continue
            dissatisfaction = (
                exposure * (1.0 - agent.violation_tolerance)
                + 0.1 * burden * (1.0 - agent.contribution_willingness)
            )
            p_exit = _stable_sigmoid((dissatisfaction - 0.3) / noise) * 0.2
            if rng.random() < p_exit:
                rule.members = rule.members - {agent_id}
                agent.rule_member_of = None
                event_log.add(
                    MembershipExitEvent(step=step, agent_id=agent_id, rule_id=rule.rule_id, patch_id=pid, reason="dissatisfaction")
                )
