"""Level 1.2b, Work Package A: ecological accounting ledger audit.

Observer-only (read-only diagnostics) — never imported by ``rules/`` or
``simulation.py``, checked by the same generative/observer AST
import-direction guard every prior level's observer module is checked by.
This module computes no governance label, phenotype, or SEM-related
quantity; it exists solely to verify that every resource unit in the
model is accounted for, per Section 5's SUPPLY / DEMAND / STOCK-CHANGE
discipline.

**Scope, stated plainly:** this module audits ``ecology_topology=
"patches"`` runs only, matching Level 1.2's own exclusive scope (Level
1.2b never runs ``"global_pool"``). It further assumes
``config.ecological_actions_affect_patch=True`` (the default, and what
every Level 1.2/1.2b main run uses) — under the
``ecological_actions_affect_patch=False`` "no environmental effect"
counterfactual, agents are still credited ``actual_extraction`` while the
*patch* is deliberately left untouched (Work Package F's own documented
design, `environment/patches.py`'s module docstring), so the system-level
identity this module checks does NOT close under that counterfactual by
construction — a known, disclosed exception, not a defect in either the
counterfactual or this audit.

## The complete category inventory (Section 5)

**SUPPLY (exogenous to the closed patch/agent/fund system — genuinely
created, not transferred from elsewhere):**

- ``regeneration`` — ``ResourcePatch.regenerate()``'s logistic growth.
  The only *intended* exogenous inflow in the model.
- ``appeal_refund`` (``AppealEvent.refund``) — credited to an appellant's
  resources with no corresponding debit anywhere in the model (not drawn
  from ``rule.fund``, not equal to the original sanction's
  ``penalty_applied``). **A genuine finding of this audit**: appeal
  refunds are an unacknowledged exogenous resource injection, not a
  reversal of the original sanction. Reported here, not corrected —
  correcting the mechanism would be a generative-layer redesign outside
  Work Package A's audit-only scope.
- ``replacement_injection`` (``ReplacementEvent.initial_resources``) —
  under ``viability_mode="removal_replacement"`` only, a freshly-drawn
  starting endowment for the new occupant, unrelated in magnitude to the
  ``resources_at_removal`` amount it replaces (see
  ``demand_replacement_loss`` below — these are two independent
  quantities, never netted against each other by the generative code).

**DEMAND (leaves the closed system entirely — no receiver anywhere):**

- ``subsistence`` (``SubsistenceEvent.total_cost``).
- ``search_cost`` (``EcologicalActionEvent.ecological_search_cost``,
  summed).
- ``maintenance_inefficiency_loss`` — the gap between what agents pay
  into maintenance (``cumulative_maintenance_invested``) and what
  actually reaches the patch (``cumulative_maintenance_effective``):
  ``maintenance_efficiency < 1.0`` and/or a near-capacity patch ceiling
  both contribute; the difference is genuinely wasted, not stored or
  transferred anywhere.
- ``monitoring_cost`` (``MonitoringEvent.cost_deducted``, summed — NOT
  ``cost_to_monitor``, which is stamped on every event of a monitoring
  round even though the underlying deduction happens once per round;
  ``cost_deducted`` attributes it to exactly one event per round).
- ``sanction_cost`` (bystander-funded: ``SanctionEvent.
  sanctioner_cost_deducted``, the actual — possibly resource-capped —
  amount; collective-fund-funded: ``SanctionEvent.cost``, exact and
  uncapped since it is guarded upstream by ``rule.fund < cost``; zero
  under ``"mechanical"``).
- ``sanction_penalty`` (``SanctionEvent.penalty_applied``, summed — see
  the Work-Package-A note in ``core/events.py`` documenting why this
  field was added this milestone: it did not exist before this audit).
- ``administrative_spending`` (``AdministrativeSpendingEvent.amount``,
  summed — funded from ``rule.fund`` or the delegate's own resources,
  either way a sink from the closed system).
- ``migration_cost`` (``MigrationEvent.movement_cost`` where
  ``outcome == "succeeded"`` only — refused/failed attempts pay nothing).
- ``coordination_cost`` (``CoordinationMaintenanceCostEvent.cost``,
  summed — the per-step, per-active-link maintenance fee paid by both
  member rules' funds. Level 1.2b, Work Package E fix: this fee is
  charged EVERY step for EVERY active link, unconditionally, but was
  previously only captured via ``CoordinationActivityEvent.cost``, which
  is gated behind a separate ``coordination_activity_probability`` roll
  and so under-recorded the fee on any step that roll did not fire — the
  dominant source of a newly-discovered ledger residual that only became
  visible at Work Package E's production scale (hundreds of steps,
  multiple concurrent links). See ``CoordinationMaintenanceCostEvent``'s
  own docstring in ``core/events.py``.).
- ``appeal_cost`` (``AppealEvent.cost_deducted``, summed — the actual,
  possibly resource-capped deduction; Level 1.2b, Work Package E fix,
  see ``AppealEvent.cost_deducted``'s own docstring).
- ``fund_dissolution_lost`` (``FundDissolutionEvent.amount`` where
  ``disposition == "lost"``, OR ``disposition == "distributed_to_members"``
  with ``n_recipients == 0`` — Level 1.2b, Work Package E fix: the latter
  is a "no living recipients" edge case that
  ``rules/contributions.py::resolve_dissolution_fund`` itself documents
  as "falls through to lost in effect", but whose event keeps the
  configured-intent ``disposition`` label rather than being rewritten —
  see this function's own inline comment for the full explanation).
- ``fund_dissolution_retained_off_registry`` (``FundDissolutionEvent.
  amount`` where ``disposition == "retained_for_reconstruction"``) — a
  **measurement-convention note, not a resource loss**: the amount is
  genuinely retained (documented in ``rules/contributions.py``'s own
  dissolution-disposition docstring), but the ``SharedRule`` object
  carrying it is removed from ``rule_registry`` at dissolution, so
  ``system_total_resources()`` (which only sums registry-live objects)
  cannot see it going forward. Tracked as its own labeled category
  rather than folded into ``fund_dissolution_lost``, so a reader can
  distinguish "genuinely gone" from "gone from this diagnostic's own
  summable state, but not from the model's intent."
- ``replacement_loss`` (``ReplacementEvent.resources_at_removal``, summed
  — under ``removal_replacement`` mode only).
- ``punishment_cost``/``punishment_penalty`` (``PunishmentEvent.
  cost_to_punisher``/``penalty_to_target``, summed) — **an addition
  beyond Section 5's own illustrative category list, found necessary by
  this audit**: bilateral costly punishment (Level 0.1, always available
  whenever ``punishment_enabled``, on by default from
  ``level11_complete`` onward) is a real, substantial resource sink —
  neither the punisher's cost nor the target's penalty is credited
  anywhere (``interactions/game.py::apply_punishment``) — and without
  tracking it, a whole-run system-total reconciliation cannot close.
  Confirmed by this module's own integration tests: omitting this
  category left a residual of several hundred to over a thousand units
  on a 40-step, 16-agent run, while every hand-computed synthetic-event
  test (which never included punishment) reconciled to exact zero
  without it. The social game's own payoff-matrix exchanges
  (``InteractionEvent``) are, by contrast, correctly NOT a separate
  category here: under ``ecology_topology="patches"``, every positive
  game payoff is extracted from the acting agent's own patch
  (``simulation.py``'s interaction round, ``category="game"``) and
  credited to the agent in the same operation, so it is already a
  same-step patch→agent transfer fully reflected in
  ``system_total_resources()``'s own patch/agent snapshots, needing no
  additional bookkeeping (verified directly: the two
  ``TestFullSimulationResidualIsZero`` runs reconcile to zero once
  punishment is added, with no game-payoff category needed at all).

**NET-ZERO INTERNAL TRANSFERS (redistribution within the closed system;
tracked for transparency per Section 5 requirement 3, never counted as
creation or destruction):** extraction (patch → agent), contributions
(agent → fund), appropriation (fund → agent), ``mutual_assistance``
interfund transfers (fund → fund), fund dissolution under
``"distributed_to_members"`` (fund → agents).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def system_total_resources(patch_system: Any, agents: list, rule_registry: dict) -> float:
    """Sum of every registry-live resource holding: all patches' current
    stock, all agents' current resources (living or dormant — a
    dormant/removed agent's resources remain part of the system total
    exactly like any other agent's, per Section 5.6's required "dormant
    and removed agents" test case; only permanently-departed agents via
    ``removal_replacement`` have their pre-replacement balance leave the
    system, tracked separately as ``replacement_loss``), and every
    currently-registered rule's collective fund. Never reads agent
    ``alive``/``viability_state`` — those are behavioral/eligibility
    flags, orthogonal to whether the agent's resource balance is still
    part of the closed system (it always is, until replacement)."""
    total = 0.0
    if patch_system is not None:
        total += sum(p.resources for p in patch_system.patches.values())
    total += sum(a.resources for a in agents)
    total += sum(r.fund for r in rule_registry.values())
    return total


@dataclass
class LedgerReconciliation:
    """One reconciled SUPPLY/DEMAND/STOCK-CHANGE identity over a step
    window (or a whole run). ``residual`` is
    ``closing_stock - opening_stock - total_supply + total_demand``;
    Section 5 requirement 7 is that this is exactly zero within
    documented floating-point tolerance (``LEDGER_RESIDUAL_TOLERANCE``)
    before any feasibility mapping is attempted."""

    opening_stock: float
    closing_stock: float

    supply_regeneration: float
    supply_appeal_refund: float
    supply_replacement_injection: float
    supply_recall_fund_recovery: float

    demand_subsistence: float
    demand_search_cost: float
    demand_maintenance_inefficiency_loss: float
    demand_monitoring_cost: float
    demand_sanction_cost: float
    demand_sanction_penalty: float
    demand_administrative_spending: float
    demand_migration_cost: float
    demand_coordination_cost: float
    demand_appeal_cost: float
    demand_fund_dissolution_lost: float
    demand_fund_dissolution_retained_off_registry: float
    demand_replacement_loss: float
    demand_punishment_cost: float
    demand_punishment_penalty: float
    demand_exit_cost: float
    demand_connection_search_cost: float
    demand_audit_cost: float
    demand_membership_exit_cost: float
    #: Level 1.2b, Work Package C: resource_depletion shocks applied to
    #: patches (see the note at this field's computation site above).
    #: Always ``0.0`` for any run with no active ``resource_depletion``
    #: perturbation.
    demand_shock_loss: float

    #: Requested vs. fulfilled extraction demand, exported separately
    #: per Section 5 requirement 1.
    total_requested_extraction: float
    total_fulfilled_extraction: float
    total_unmet_extraction_demand: float

    #: Net-zero internal transfers, reported for transparency (Section 5
    #: requirement 2/3) — never included in the supply/demand totals.
    transfer_extraction_patch_to_agent: float
    transfer_contributions_agent_to_fund: float
    transfer_appropriation_fund_to_agent: float
    transfer_mutual_assistance_fund_to_fund: float
    transfer_fund_dissolution_distributed: float

    residual: float = field(init=False)

    @property
    def total_supply(self) -> float:
        return (
            self.supply_regeneration
            + self.supply_appeal_refund
            + self.supply_replacement_injection
            + self.supply_recall_fund_recovery
        )

    @property
    def total_demand(self) -> float:
        return (
            self.demand_subsistence
            + self.demand_search_cost
            + self.demand_maintenance_inefficiency_loss
            + self.demand_monitoring_cost
            + self.demand_sanction_cost
            + self.demand_sanction_penalty
            + self.demand_administrative_spending
            + self.demand_migration_cost
            + self.demand_coordination_cost
            + self.demand_appeal_cost
            + self.demand_fund_dissolution_lost
            + self.demand_fund_dissolution_retained_off_registry
            + self.demand_replacement_loss
            + self.demand_punishment_cost
            + self.demand_punishment_penalty
            + self.demand_exit_cost
            + self.demand_connection_search_cost
            + self.demand_audit_cost
            + self.demand_membership_exit_cost
            + self.demand_shock_loss
        )

    def __post_init__(self) -> None:
        self.residual = self.closing_stock - self.opening_stock - self.total_supply + self.total_demand


#: Section 5 requirement 7's "documented floating-point tolerance."
LEDGER_RESIDUAL_TOLERANCE = 1e-6


def _events_in_window(events: list, step_min: int | None, step_max: int | None) -> list:
    if step_min is None and step_max is None:
        return list(events)
    lo = step_min if step_min is not None else float("-inf")
    hi = step_max if step_max is not None else float("inf")
    return [e for e in events if lo <= e.step <= hi]


def compute_ledger_reconciliation(
    *,
    opening_stock: float,
    closing_stock: float,
    patch_system: Any,
    event_log: Any,
    step_min: int | None = None,
    step_max: int | None = None,
    search_cost: float = 0.0,
    membership_exit_cost: float = 0.0,
) -> LedgerReconciliation:
    """Reconcile the SUPPLY/DEMAND identity over ``[step_min, step_max]``
    (inclusive; ``None`` on either bound means unbounded in that
    direction). ``opening_stock``/``closing_stock`` must be
    ``system_total_resources()`` snapshots taken immediately before the
    first step and immediately after the last step of the window being
    audited — this function does not take those snapshots itself, so it
    can be used identically for a single patch-step, a multi-step
    system window, or a whole seed-run.

    Regeneration and maintenance-invested/effective are read from each
    patch's own cumulative counters as a WHOLE-RUN total (Work Package A
    requirement: ``ResourcePatch`` does not track a per-step regeneration
    event, only a running cumulative sum) — so this function is only
    exact for a window starting at step 0. A window audit starting later
    than step 0 must instead take before/after cumulative-counter
    snapshots itself and pass their *deltas* via
    ``regeneration_override``/``maintenance_invested_override``/
    ``maintenance_effective_override`` (see
    ``tests/test_level12b_ecological_ledger.py`` for the pattern)."""
    subsistence = sum(e.total_cost for e in _events_in_window(event_log.subsistence, step_min, step_max))
    eco_actions = _events_in_window(event_log.ecological_actions, step_min, step_max)
    # NOTE: intentionally NOT named ``search_cost`` -- that name is the
    # function parameter carrying ``config.search_cost`` (the *relationship*-
    # formation search cost per attempt, used below for
    # ``connection_search_cost_total``), a completely different quantity
    # from this ecological-harvest search cost. A prior version of this
    # function shadowed the parameter with this sum, which silently zeroed
    # out ``connection_search_cost_total`` whenever ecological search cost
    # summed to zero -- caught by the Level 1.2b full-simulation residual
    # tests (``TestFullSimulationResidualIsZero``), not by any synthetic
    # unit test, since every synthetic test exercises only one category at
    # a time.
    ecological_search_cost_total = sum(e.ecological_search_cost for e in eco_actions)
    requested_extraction = sum(e.requested_extraction for e in eco_actions)
    fulfilled_extraction = sum(e.actual_extraction for e in eco_actions)

    # ``MonitoringEvent.cost_to_monitor`` (kept for backward compatibility)
    # is stamped onto *every* MonitoringEvent produced in a single
    # (step, patch, rule) monitoring round even though the underlying
    # deduction from the monitor's resources happens only once per round
    # -- summing it would multiply-count. ``cost_deducted`` instead
    # attributes the one real, possibly-capped deduction to exactly one
    # event per round (see rules/dynamics.py::monitoring_round), so
    # summing it is exact.
    monitoring_cost = sum(e.cost_deducted for e in _events_in_window(event_log.monitorings, step_min, step_max))
    sanctions = _events_in_window(event_log.sanctions, step_min, step_max)
    # ``SanctionEvent.cost`` records the *intended* cost regardless of who
    # pays it. For ``funded_by == "bystander"`` the actual deduction from
    # the sanctioner's own resources is capped at their available
    # resources (``sanctioner_cost_deducted``, possibly less than
    # ``cost``); for ``funded_by == "collective_fund"`` the deduction is
    # from ``rule.fund`` and is never capped (guarded upstream by
    # ``rule.fund < cost``), so ``cost`` itself is exact there; for
    # ``funded_by == "mechanical"`` both are zero.
    sanction_cost = sum(
        e.sanctioner_cost_deducted if e.funded_by == "bystander" else e.cost for e in sanctions
    )
    sanction_penalty = sum(e.penalty_applied for e in sanctions)
    admin_spending = sum(e.amount for e in _events_in_window(event_log.administrative_spending, step_min, step_max))
    migration_cost = sum(
        e.movement_cost for e in _events_in_window(event_log.migrations, step_min, step_max) if e.outcome == "succeeded"
    )
    # Level 1.2b, Work Package E fix: sum the unconditional per-step,
    # per-active-link maintenance fee (CoordinationMaintenanceCostEvent),
    # not CoordinationActivityEvent.cost -- the latter is gated behind
    # coordination_activity_probability and under-records the fee (see
    # this module's own docstring and CoordinationMaintenanceCostEvent's
    # docstring in core/events.py for the full explanation).
    coordination_cost = sum(
        e.cost for e in _events_in_window(event_log.coordination_maintenance_costs, step_min, step_max)
    )
    mutual_assistance_transfer = sum(
        e.resource_transferred for e in _events_in_window(event_log.coordination_activity, step_min, step_max)
    )
    appeals = _events_in_window(event_log.appeals, step_min, step_max)
    # Level 1.2b, Work Package E fix: sum the actual (possibly resource-
    # capped) ``cost_deducted``, not the uncapped intended ``cost`` --
    # see ``AppealEvent.cost_deducted``'s own docstring in core/events.py.
    appeal_cost = sum(e.cost_deducted for e in appeals)
    appeal_refund = sum(e.refund for e in appeals)

    dissolutions = _events_in_window(event_log.fund_dissolutions, step_min, step_max)
    # Level 1.2b, Work Package E production-scale ledger-residual fix:
    # ``rules/contributions.py::resolve_dissolution_fund``'s own
    # docstring/comment discloses that a ``"distributed_to_members"``
    # disposition with NO living recipients (``n_recipients == 0``)
    # "falls through to lost in effect" -- the amount is never actually
    # added to any agent's resources, even though the event's own
    # ``disposition`` field still reads ``"distributed_to_members"`` (the
    # CONFIGURED intent, preserved for audit purposes rather than
    # silently rewritten). Treating every ``"distributed_to_members"``
    # event as a net-zero TRANSFER (the pre-existing behavior) was
    # therefore wrong for this ``n_recipients == 0`` edge case -- a real
    # sink invisible until a dissolution with zero living members
    # actually occurred (too rare at Work Package A's own short-run
    # validation scale to surface). Only genuine transfers (>=1 living
    # recipient) are counted as ``transfer_fund_dissolution_distributed``
    # below; the zero-recipient amount is folded into
    # ``demand_fund_dissolution_lost`` instead, matching what actually
    # happened to the resources.
    fund_lost = sum(
        e.amount for e in dissolutions
        if e.disposition == "lost" or (e.disposition == "distributed_to_members" and e.n_recipients == 0)
    )
    fund_retained_off_registry = sum(e.amount for e in dissolutions if e.disposition == "retained_for_reconstruction")
    fund_distributed = sum(
        e.amount for e in dissolutions if e.disposition == "distributed_to_members" and e.n_recipients > 0
    )

    contributions = _events_in_window(event_log.contributions, step_min, step_max)
    contribution_transfer = sum(e.amount_paid for e in contributions)

    appropriations = _events_in_window(event_log.appropriations, step_min, step_max)
    appropriation_transfer = sum(e.amount for e in appropriations)

    replacements = _events_in_window(event_log.replacements, step_min, step_max)
    replacement_loss = sum(e.resources_at_removal for e in replacements)
    replacement_injection = sum(e.initial_resources for e in replacements)

    punishments = _events_in_window(event_log.punishments, step_min, step_max)
    punishment_cost = sum(e.cost_to_punisher for e in punishments)
    punishment_penalty = sum(e.penalty_to_target for e in punishments)

    # Relationship-exit cost (Level 0.1's endogenous exit, plus Level 0's
    # own "compatibility-mode" ExitEvent -- disclosed alongside
    # punishment above as a second necessary-but-not-in-Section-5's-
    # illustrative-list sink: exiting a relationship is affordability-
    # gated (network/dynamics.py::exit_relationship) and the cost is
    # never credited anywhere).
    exit_cost_total = sum(e.exit_cost for e in _events_in_window(event_log.exits, step_min, step_max))
    exit_cost_total += sum(e.exit_cost for e in _events_in_window(event_log.edges_removed, step_min, step_max))

    # Relationship-*search* cost (distinct from ecological search cost --
    # see the docstring above): a fixed per-attempt constant not logged
    # on ConnectionProposalEvent itself, so derived as count * cost,
    # mirroring simulation.py's own gating condition exactly.
    n_search_attempts = sum(
        1 for e in _events_in_window(event_log.connection_proposals, step_min, step_max) if e.reason != "no_candidate"
    )
    connection_search_cost_total = search_cost * n_search_attempts

    # ``AuditEvent.cost`` records the intended cost; the actual deduction
    # from ``auditor.resources`` is capped at their available resources
    # (``cost_deducted``, possibly less than ``cost``) -- same capped-
    # deduction pattern as monitoring/sanction/membership-exit above.
    audit_cost_total = sum(e.cost_deducted for e in _events_in_window(event_log.audits, step_min, step_max))

    # A second genuine exogenous injection alongside appeal_refund
    # (found by this audit): a successful recall credits rule.fund with
    # a fraction of the removed delegate's *own* appropriated_total --
    # the delegate keeps what it appropriated; this is not drawn back
    # from the delegate's resources, so it is pure supply, not a
    # reversal of the earlier (already-untracked, since appropriation
    # is a fund->agent transfer, not a sink) appropriation.
    recall_fund_recovery = sum(e.recovered_funds for e in _events_in_window(event_log.recalls, step_min, step_max))

    # Level 1.0's own voluntary-membership-exit cost (MembershipEvent
    # kind="exit" -- distinct from Level 1.2's MembershipExitEvent,
    # which has its own reasons "migration"/"dissatisfaction" and no
    # cost of its own). The deduction is capped at the exiting agent's
    # available resources (rules/dynamics.py::membership_round), so the
    # actual amount removed is not always exactly ``config.membership_exit_cost``;
    # ``exit_cost_deducted`` records the real, possibly-capped amount per
    # event, so summing it (rather than ``membership_exit_cost * count``)
    # is exact. The ``membership_exit_cost`` parameter is kept for
    # backward compatibility but is no longer used to derive this total.
    membership_exit_cost_total = sum(
        e.exit_cost_deducted for e in _events_in_window(event_log.memberships, step_min, step_max) if e.kind == "exit"
    )

    regeneration = 0.0
    maintenance_invested = 0.0
    maintenance_effective = 0.0
    shock_loss = 0.0
    if patch_system is not None and step_min is None:
        regeneration = sum(p.cumulative_regeneration for p in patch_system.patches.values())
        maintenance_invested = sum(p.cumulative_maintenance_invested for p in patch_system.patches.values())
        maintenance_effective = sum(p.cumulative_maintenance_effective for p in patch_system.patches.values())
        # Level 1.2b, Work Package C: resource_depletion perturbations
        # applied to patches (core/perturbation.py, ResourcePatch.
        # apply_shock_loss) -- a genuine sink, no receiver, same category
        # as Section 5's originally-illustrative "shock losses" demand
        # entry, only now implemented (Work Package A's own audit
        # predates patches-topology shock support and so could not yet
        # exercise this category -- it always summed to 0.0 for every
        # Work Package A test run).
        shock_loss = sum(p.cumulative_shock_loss for p in patch_system.patches.values())
    maintenance_inefficiency_loss = max(0.0, maintenance_invested - maintenance_effective)

    return LedgerReconciliation(
        opening_stock=opening_stock,
        closing_stock=closing_stock,
        supply_regeneration=regeneration,
        supply_appeal_refund=appeal_refund,
        supply_replacement_injection=replacement_injection,
        supply_recall_fund_recovery=recall_fund_recovery,
        demand_subsistence=subsistence,
        demand_search_cost=ecological_search_cost_total,
        demand_maintenance_inefficiency_loss=maintenance_inefficiency_loss,
        demand_monitoring_cost=monitoring_cost,
        demand_sanction_cost=sanction_cost,
        demand_sanction_penalty=sanction_penalty,
        demand_administrative_spending=admin_spending,
        demand_migration_cost=migration_cost,
        demand_coordination_cost=coordination_cost,
        demand_appeal_cost=appeal_cost,
        demand_fund_dissolution_lost=fund_lost,
        demand_fund_dissolution_retained_off_registry=fund_retained_off_registry,
        demand_replacement_loss=replacement_loss,
        demand_punishment_cost=punishment_cost,
        demand_punishment_penalty=punishment_penalty,
        demand_exit_cost=exit_cost_total,
        demand_connection_search_cost=connection_search_cost_total,
        demand_audit_cost=audit_cost_total,
        demand_membership_exit_cost=membership_exit_cost_total,
        demand_shock_loss=shock_loss,
        total_requested_extraction=requested_extraction,
        total_fulfilled_extraction=fulfilled_extraction,
        total_unmet_extraction_demand=max(0.0, requested_extraction - fulfilled_extraction),
        transfer_extraction_patch_to_agent=fulfilled_extraction,
        transfer_contributions_agent_to_fund=contribution_transfer,
        transfer_appropriation_fund_to_agent=appropriation_transfer,
        transfer_mutual_assistance_fund_to_fund=mutual_assistance_transfer,
        transfer_fund_dissolution_distributed=fund_distributed,
    )


def realized_balance_ratio(supply: float, requested_demand: float) -> float | None:
    """Section 6.3: ``realized supply / realized requested demand`` for
    one step or window. Returns ``None`` (never ``0.0``/``inf``-as-a-
    sentinel) when ``requested_demand`` is exactly ``0.0`` — an
    undefined ratio, not a "perfectly fed" ratio of zero pressure over
    zero demand. This is a diagnostic OUTCOME, never a design variable —
    callers must never feed this into any ex ante feasibility ratio
    (Section 6.1/6.2), only report it after the fact."""
    if requested_demand <= 0.0:
        return None
    return supply / requested_demand
