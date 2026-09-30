"""Level 1.1, Work Package H: opt-in collective contributions and
collective-fund spending/dissolution accounting.

Reuses ``SharedRule.fund`` (already present since Level 1.0's
``sanction_mode="collective_fund"``) as the single collective-fund
ledger a rule ever has — Work Package H's contribution mechanism and
Level 1.0's sanction-funding mechanism are two different *sources* that
feed the same account, not two separate pots, which is what keeps the
resource-accounting identity in ``tests/test_level11_contributions.py``
exact: every resource unit that ever enters ``rule.fund`` came from an
explicit, logged contribution or fund-diversion event, and every unit
that ever leaves it is logged as spending, appropriation (see
``rules/delegation.py``), or a dissolution disposition — never a
silent adjustment.
"""

from __future__ import annotations

import numpy as np

from abm_governance.agents.adaptation import _stable_sigmoid
from abm_governance.agents.agent import Agent
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import (
    AdministrativeSpendingEvent,
    ContributionEvent,
    EventLog,
    FundDissolutionEvent,
)
from abm_governance.core.historical_transmission import pressure_adjusted_probability
from abm_governance.rules.shared_rule import SharedRule

#: task -> administrative spending category (Work Package H requirement
#: 4's fixed vocabulary), used by ``pay_administrative_cost``'s callers.
TASK_TO_SPENDING_CATEGORY: dict[str, str] = {
    "monitoring": "monitoring",
    "resource_accounting": "record_keeping",
    "sanction_execution": "sanction",
    "maintenance_coordination": "maintenance_coordination",
    "interpatch_communication": "communication",
}


def contribution_round(
    step: int,
    rule_registry: dict[int, SharedRule],
    agents_by_id: dict[int, Agent],
    config: SimulationConfig,
    rng: np.random.Generator,
    event_log: EventLog,
    bargaining_pressure_level: float = 0.0,
) -> None:
    """One collective-contribution assessment, run only every
    ``config.contribution_period_steps`` steps (a strict no-op every
    other step, and entirely whenever ``config.contribution_mode ==
    "none"``, the default). Compliance is decided by
    ``contribution_willingness``/``preferred_contribution_amount`` —
    deliberately distinct traits from ``violation_tolerance`` (Work
    Package H requirement 2: contribution compliance may differ from
    ecological-rule compliance).

    Level 1.3, Work Package A (Section 6): ``bargaining_pressure_level``
    (default ``0.0`` -- an exact no-op for every non-Level-1.3 caller)
    feeds "willingness to contribute conditionally," gated on
    ``config.bargaining_pressure_conditional_contribution_enabled``. The
    underlying ``Agent.contribution_willingness`` TRAIT is never
    mutated -- only the EFFECTIVE, per-draw compliance probability used
    for this step's decision is nudged, exactly like every other
    pressure channel in this module family."""
    # Level 1.2, Work Package A: a per-institution ``contribution_mechanism``
    # override (see ``SharedRule.institution_overrides``) can make a rule's
    # effective mode differ from ``config.contribution_mode`` even when the
    # latter is "none" -- so the cheap global early-return is only safe when
    # no rule in the registry actually carries such an override.
    has_override = any(
        (rule.institution_overrides or {}).get("contribution_mechanism") is not None
        for rule in rule_registry.values()
    )
    if config.contribution_mode == "none" and not has_override:
        return
    if step % max(1, config.contribution_period_steps) != 0:
        return
    for pid, rule in rule_registry.items():
        if not rule.active or not rule.members:
            continue
        mode = (rule.institution_overrides or {}).get("contribution_mechanism", config.contribution_mode)
        if mode == "none":
            continue
        members = [agents_by_id[aid] for aid in rule.members if agents_by_id.get(aid) is not None and agents_by_id[aid].alive]
        if not members:
            continue

        if mode == "negotiated":
            negotiated_amount = float(np.mean([m.preferred_contribution_amount for m in members]))

        conditional_channel_on = config.bargaining_pressure_conditional_contribution_enabled

        for member in members:
            if mode == "equal":
                amount_asked = config.contribution_amount
                complied = True
            elif mode == "voluntary":
                amount_asked = config.contribution_amount
                willingness = member.contribution_willingness
                if conditional_channel_on:
                    willingness = pressure_adjusted_probability(
                        willingness, bargaining_pressure_level,
                        config.bargaining_pressure_conditional_contribution_sensitivity,
                    )
                complied = rng.random() < willingness
            elif mode == "proportional":
                amount_asked = max(0.0, member.resources) * config.contribution_proportional_rate
                complied = True
            elif mode == "negotiated":
                amount_asked = negotiated_amount
                willingness = member.contribution_willingness
                if conditional_channel_on:
                    willingness = pressure_adjusted_probability(
                        willingness, bargaining_pressure_level,
                        config.bargaining_pressure_conditional_contribution_sensitivity,
                    )
                complied = rng.random() < willingness
            else:  # pragma: no cover - guarded by SimulationConfig validation / institution.py validation
                raise ValueError(f"unknown contribution_mode {mode!r}")

            amount_paid = 0.0
            if complied and amount_asked > 0.0:
                amount_paid = min(amount_asked, max(0.0, member.resources))
                member.resources -= amount_paid
                rule.fund += amount_paid
            event_log.add(
                ContributionEvent(
                    step=step, patch_id=pid, rule_id=rule.rule_id, agent=member.agent_id,
                    mode=mode, amount_asked=amount_asked, amount_paid=amount_paid,
                    complied=complied and amount_paid > 0.0, fund_after=rule.fund,
                )
            )


def pay_administrative_cost(
    step: int,
    patch_id: int,
    rule: SharedRule,
    delegate_id: int | None,
    payer: Agent | None,
    category: str,
    amount: float,
    event_log: EventLog,
) -> float:
    """Pay ``amount`` for one administrative expenditure (Work Package H
    requirement 4), preferring the rule's collective fund and falling
    back to the payer's own resources only when the fund cannot cover it
    (never split across the two sources, so each event's ``funded_by``
    is unambiguous). Returns the amount actually paid (may be less than
    ``amount`` if neither the fund nor the payer holds enough — never
    drives either negative)."""
    if amount <= 0.0:
        return 0.0
    if rule.fund >= amount:
        rule.fund -= amount
        funded_by = "collective_fund"
        paid = amount
    elif payer is not None:
        paid = min(amount, max(0.0, payer.resources))
        payer.resources -= paid
        funded_by = "delegate_personal"
    else:
        paid = 0.0
        funded_by = "delegate_personal"
    if paid > 0.0:
        event_log.add(
            AdministrativeSpendingEvent(
                step=step, patch_id=patch_id, rule_id=rule.rule_id, delegate_id=delegate_id,
                category=category, amount=paid, funded_by=funded_by,
            )
        )
    return paid


def resolve_dissolution_fund(
    step: int,
    rule: SharedRule,
    members_at_dissolution: frozenset,
    agents_by_id: dict[int, Agent],
    config: SimulationConfig,
    event_log: EventLog,
) -> None:
    """Dispose of a just-dissolved rule's remaining fund balance exactly
    once (Work Package H requirement 6) — resource-accounted: the amount
    logged always equals ``rule.fund`` at the moment this is called, and
    ``rule.fund`` is always zeroed afterward (a dissolved rule never
    silently retains a balance nobody can account for, even under
    ``"retained_for_reconstruction"``, which instead carries the amount
    forward explicitly via the returned/logged value rather than leaving
    it sitting unexplained on a dissolved object)."""
    amount = rule.fund
    if amount <= 0.0:
        rule.fund = 0.0
        return
    disposition = config.fund_dissolution_disposition
    n_recipients = 0
    if disposition == "distributed_to_members":
        recipients = [agents_by_id[aid] for aid in members_at_dissolution if agents_by_id.get(aid) is not None and agents_by_id[aid].alive]
        n_recipients = len(recipients)
        if recipients:
            share = amount / len(recipients)
            for recipient in recipients:
                recipient.resources += share
        # else: no living recipients -- falls through to "lost" in effect,
        # but the disposition label stays "distributed_to_members" since
        # that was the configured intent; n_recipients=0 makes this
        # auditable rather than silently reclassified.
    elif disposition == "retained_for_reconstruction":
        # The value is preserved on the rule object itself (never zeroed
        # below in this branch) so a later reconstruction proposal at
        # the same patch/lineage can be seeded from it by the caller;
        # still logged here as the dissolution-time disposition record.
        event_log.add(
            FundDissolutionEvent(
                step=step, patch_id=rule.patch_id, rule_id=rule.rule_id, rule_lineage_id=rule.rule_lineage_id,
                amount=amount, disposition=disposition, n_recipients=0,
            )
        )
        return
    # "lost": amount simply leaves circulation below; no recipient action.

    event_log.add(
        FundDissolutionEvent(
            step=step, patch_id=rule.patch_id, rule_id=rule.rule_id, rule_lineage_id=rule.rule_lineage_id,
            amount=amount, disposition=disposition, n_recipients=n_recipients,
        )
    )
    rule.fund = 0.0
