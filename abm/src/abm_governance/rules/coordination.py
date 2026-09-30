"""Level 1.1, Work Package I: minimal interpatch coordination.

A :class:`CoordinationLink` is the smallest defensible mechanism by which
two patches' own active rules can coordinate — not a state, constitution,
federation, merger, or national government (the milestone's own explicit
scope limit). Deliberately independent of ``rules/delegation.py`` (Work
Packages D-G): a rule can propose, accept, and operate a coordination
link with a neighboring rule with no delegate ever appointed at either
side — see ``core/config.py::SimulationConfig.level11_coordination_only``.

No explicit interpatch adjacency topology exists elsewhere in this
project (patches are assigned to agents via ``environment/patches.py``,
never to each other) — "neighboring patch" here means any other patch
that currently has an active rule, a documented scope simplification
(see ``docs/odd_level1.1.md``), not a claim that a richer interpatch
topology would be uninteresting.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from abm_governance.agents.agent import Agent
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import (
    CoordinationActivityEvent,
    CoordinationDissolutionEvent,
    CoordinationLinkEvent,
    CoordinationMaintenanceCostEvent,
    CoordinationProposalEvent,
    EventLog,
)
from abm_governance.core.historical_transmission import pressure_adjusted_probability, pressure_adjusted_scale
from abm_governance.rules.shared_rule import SharedRule

VALID_COORDINATION_KINDS = (
    "information_exchange", "ecological_restraint", "shared_monitoring",
    "mutual_assistance", "shared_records",
)


@dataclass
class CoordinationLink:
    link_id: int
    patch_id_a: int
    patch_id_b: int
    rule_id_a: int
    rule_id_b: int
    kind: str
    proposed_step: int
    accepted_step: int
    active: bool = True
    dissolved: bool = False
    dissolution_step: int | None = None
    dissolution_reason: str | None = None
    total_resource_transferred: float = 0.0
    total_cost: float = 0.0
    n_activity_steps: int = 0


@dataclass
class _PendingCoordinationProposal:
    patch_id_from: int
    patch_id_to: int
    rule_id_from: int
    rule_id_to: int
    kind: str
    proposer: int
    opened_step: int


def _dissolve_link(step: int, link: CoordinationLink, reason: str, event_log: EventLog) -> None:
    if not link.active:
        return
    link.active = False
    link.dissolved = True
    link.dissolution_step = step
    link.dissolution_reason = reason
    event_log.add(
        CoordinationDissolutionEvent(
            step=step, link_id=link.link_id, patch_id_a=link.patch_id_a, patch_id_b=link.patch_id_b,
            duration_steps=step - link.accepted_step, reason=reason,
        )
    )


def coordination_round(
    step: int,
    rule_registry: dict[int, SharedRule],
    agents_by_id: dict[int, Agent],
    patch_system,
    link_registry: dict[int, CoordinationLink],
    pending: dict[tuple[int, int], _PendingCoordinationProposal],
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
    id_state: dict,
    coordination_complexity_level: float = 0.0,
) -> None:
    """One step of proposal, bilateral acceptance, activity, and
    dissolution for interpatch coordination links (Work Package I). A
    strict no-op unless ``config.interpatch_coordination_enabled``.

    Level 1.3, Work Package A (Section 6): ``coordination_complexity_
    level`` (default ``0.0`` -- an exact no-op for every non-Level-1.3
    caller) feeds two independently-flagged channels below:
    "interoperable_demand" (proposal probability) and "cross_patch_
    transactions" (active-link transaction/activity probability)."""
    if not config.interpatch_coordination_enabled:
        return

    rule_by_patch = {r.patch_id: r for r in rule_registry.values() if r.active and r.members}
    linked_or_pending_patches: set[int] = set()
    for link in link_registry.values():
        if link.active:
            linked_or_pending_patches.add(link.patch_id_a)
            linked_or_pending_patches.add(link.patch_id_b)
    for key in pending:
        linked_or_pending_patches.update(key)

    # -- resolve pending proposals (bilateral: both patches' rules must
    # independently accept -- the proposing side is deemed to accept by
    # construction, so only the recipient's decision is drawn here). ----
    for key in list(pending.keys()):
        prop = pending[key]
        to_rule = rule_by_patch.get(prop.patch_id_to)
        from_rule = rule_by_patch.get(prop.patch_id_from)
        if to_rule is None or from_rule is None:
            del pending[key]
            event_log.add(
                CoordinationLinkEvent(
                    step=step, link_id=-1, patch_id_a=prop.patch_id_from, patch_id_b=prop.patch_id_to,
                    kind=prop.kind, accepted=False, reason="counterpart_rule_no_longer_active",
                )
            )
            continue
        window_expired = (step - prop.opened_step) >= (config.coordination_proposal_window_steps - 1)
        members = [agents_by_id[aid] for aid in to_rule.members if agents_by_id.get(aid) is not None and agents_by_id[aid].alive]
        accept_prob = float(np.mean([m.interpatch_acceptance_propensity for m in members])) if members else 0.0
        accepted = rng.random() < accept_prob
        if accepted:
            link_id = id_state["next_link_id"]
            id_state["next_link_id"] += 1
            link = CoordinationLink(
                link_id=link_id, patch_id_a=prop.patch_id_from, patch_id_b=prop.patch_id_to,
                rule_id_a=from_rule.rule_id, rule_id_b=to_rule.rule_id, kind=prop.kind,
                proposed_step=prop.opened_step, accepted_step=step,
            )
            link_registry[link_id] = link
            event_log.add(
                CoordinationLinkEvent(
                    step=step, link_id=link_id, patch_id_a=prop.patch_id_from, patch_id_b=prop.patch_id_to,
                    kind=prop.kind, accepted=True,
                )
            )
            del pending[key]
        elif window_expired:
            event_log.add(
                CoordinationLinkEvent(
                    step=step, link_id=-1, patch_id_a=prop.patch_id_from, patch_id_b=prop.patch_id_to,
                    kind=prop.kind, accepted=False, reason="window_expired",
                )
            )
            del pending[key]

    # -- new proposals -----------------------------------------------------
    if len(rule_by_patch) >= 2:
        for pid, rule in rule_by_patch.items():
            if pid in linked_or_pending_patches:
                continue
            members = [agents_by_id[aid] for aid in rule.members if agents_by_id.get(aid) is not None and agents_by_id[aid].alive]
            if not members:
                continue
            mean_propensity = float(np.mean([m.interpatch_proposal_probability for m in members]))
            # Level 1.2, Work Package A: ``coordination_link_policy`` override.
            coordination_bonus = (rule.institution_overrides or {}).get(
                "coordination_link_policy", config.coordination_proposal_probability
            )
            p_propose = float(np.clip(mean_propensity + coordination_bonus, 0.0, 1.0))
            if config.coordination_complexity_interoperable_demand_enabled:
                p_propose = pressure_adjusted_probability(
                    p_propose, coordination_complexity_level,
                    config.coordination_complexity_interoperable_demand_sensitivity,
                )
            if rng.random() >= p_propose:
                continue
            candidates = [other for other in rule_by_patch if other != pid and other not in linked_or_pending_patches]
            if not candidates:
                continue
            target_pid = int(rng.choice(candidates))
            kind = str(rng.choice(VALID_COORDINATION_KINDS))
            proposer = members[int(rng.integers(0, len(members)))]
            key = (pid, target_pid)
            pending[key] = _PendingCoordinationProposal(
                patch_id_from=pid, patch_id_to=target_pid, rule_id_from=rule.rule_id,
                rule_id_to=rule_by_patch[target_pid].rule_id, kind=kind, proposer=proposer.agent_id,
                opened_step=step,
            )
            event_log.add(
                CoordinationProposalEvent(
                    step=step, patch_id_from=pid, patch_id_to=target_pid, rule_id_from=rule.rule_id,
                    rule_id_to=rule_by_patch[target_pid].rule_id, kind=kind, proposer=proposer.agent_id,
                )
            )
            linked_or_pending_patches.add(pid)
            linked_or_pending_patches.add(target_pid)

    # -- active link operation ----------------------------------------------
    occupancy = {}
    if patch_system is not None:
        occupancy = {pid: patch.fraction_of_capacity for pid, patch in patch_system.patches.items()}
    for link in list(link_registry.values()):
        if not link.active:
            continue
        rule_a = rule_registry.get(link.rule_id_a)
        rule_b = rule_registry.get(link.rule_id_b)
        if rule_a is None or not rule_a.active:
            _dissolve_link(step, link, "rule_dissolved_a", event_log)
            continue
        if rule_b is None or not rule_b.active:
            _dissolve_link(step, link, "rule_dissolved_b", event_log)
            continue

        cost_each = config.coordination_cost_per_step
        paid_a = min(cost_each, rule_a.fund)
        rule_a.fund -= paid_a
        paid_b = min(cost_each, rule_b.fund)
        rule_b.fund -= paid_b
        link.total_cost += paid_a + paid_b
        # Level 1.2b, Work Package E fix: this fee is paid every step for
        # every active link, unconditionally -- log it unconditionally
        # too (see CoordinationMaintenanceCostEvent's docstring), rather
        # than relying on the activity-probability-gated
        # CoordinationActivityEvent below, which only sometimes fires.
        event_log.add(
            CoordinationMaintenanceCostEvent(step=step, link_id=link.link_id, cost=paid_a + paid_b)
        )

        activity_probability = config.coordination_activity_probability
        if config.coordination_complexity_cross_patch_transactions_enabled:
            activity_probability = pressure_adjusted_probability(
                activity_probability, coordination_complexity_level,
                config.coordination_complexity_cross_patch_transactions_sensitivity,
            )
        if rng.random() < activity_probability:
            info_accuracy = float(np.clip(1.0 - abs(rng.normal(0.0, config.coordination_info_error_std)), 0.0, 1.0))
            resource_transferred = 0.0
            if link.kind == "mutual_assistance":
                occ_a = occupancy.get(link.patch_id_a, 1.0)
                occ_b = occupancy.get(link.patch_id_b, 1.0)
                if occ_b < config.coordination_assistance_occupancy_threshold and rule_a.fund > 0.0:
                    resource_transferred = rule_a.fund * config.coordination_assistance_transfer_fraction
                    rule_a.fund -= resource_transferred
                    rule_b.fund += resource_transferred
                elif occ_a < config.coordination_assistance_occupancy_threshold and rule_b.fund > 0.0:
                    resource_transferred = rule_b.fund * config.coordination_assistance_transfer_fraction
                    rule_b.fund -= resource_transferred
                    rule_a.fund += resource_transferred
            link.n_activity_steps += 1
            link.total_resource_transferred += resource_transferred
            event_log.add(
                CoordinationActivityEvent(
                    step=step, link_id=link.link_id, patch_id_a=link.patch_id_a, patch_id_b=link.patch_id_b,
                    info_accuracy=info_accuracy, resource_transferred=resource_transferred, cost=paid_a + paid_b,
                )
            )

        if rng.random() < config.coordination_dissolution_probability:
            _dissolve_link(step, link, "voluntary", event_log)
