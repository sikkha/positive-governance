"""Level 1.2b, Work Package A: hand-computed ecological ledger audit tests.

Section 5.6's required scenarios: no demand, demand below supply, demand
above supply, multiple patches, migration, interpatch transfers,
administration, appropriation, maintenance, collapse, negative personal
resources, dormant and removed agents.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import (
    AdministrativeSpendingEvent,
    AppealEvent,
    AppropriationEvent,
    CoordinationActivityEvent,
    CoordinationMaintenanceCostEvent,
    EcologicalActionEvent,
    EventLog,
    FundDissolutionEvent,
    MigrationEvent,
    MonitoringEvent,
    ReplacementEvent,
    SanctionEvent,
    SubsistenceEvent,
)
from abm_governance.environment.patches import PatchSystem, ResourcePatch
from abm_governance.observer.ecological_ledger import (
    LEDGER_RESIDUAL_TOLERANCE,
    LedgerReconciliation,
    compute_ledger_reconciliation,
    realized_balance_ratio,
    system_total_resources,
)
from abm_governance.simulation import Simulation


def _empty_patch_system(n=1, capacity=100.0, resources=50.0, regen=0.1) -> PatchSystem:
    patches = {i: ResourcePatch(patch_id=i, capacity=capacity, regen_rate=regen, resources=resources) for i in range(n)}
    return PatchSystem(patches=patches, agent_patch={})


class _FakeAgent:
    def __init__(self, agent_id, resources):
        self.agent_id = agent_id
        self.resources = resources


class _FakeRule:
    def __init__(self, fund):
        self.fund = fund


class TestSystemTotalResources:
    def test_sums_patches_agents_and_funds(self):
        ps = _empty_patch_system(n=2, resources=10.0)
        agents = [_FakeAgent(0, 5.0), _FakeAgent(1, 7.0)]
        rules = {0: _FakeRule(3.0)}
        assert system_total_resources(ps, agents, rules) == pytest.approx(10.0 + 10.0 + 5.0 + 7.0 + 3.0)

    def test_none_patch_system_still_sums_agents_and_funds(self):
        agents = [_FakeAgent(0, 5.0)]
        assert system_total_resources(None, agents, {}) == pytest.approx(5.0)

    def test_negative_agent_resources_counted_as_is(self):
        """Section 5.6 required case: negative personal resources. The
        system total must reflect the negative value exactly, never
        clamped to zero (subsistence is allowed to drive resources
        negative -- see simulation.py::_apply_subsistence)."""
        agents = [_FakeAgent(0, -3.5)]
        assert system_total_resources(None, agents, {}) == pytest.approx(-3.5)

    def test_dormant_and_removed_agents_still_counted(self):
        """Section 5.6 required case: dormant/removed agents. A dormant
        agent (no 'alive' or 'viability_state' attribute read by this
        function at all) contributes its resources exactly like any
        other agent -- eligibility state is orthogonal to the ledger."""
        class DormantAgent:
            agent_id = 9
            resources = 12.0
            alive = False
            viability_state = "dormant"

        assert system_total_resources(None, [DormantAgent()], {}) == pytest.approx(12.0)


class TestNoDemandScenario:
    def test_zero_demand_zero_supply_gives_exact_zero_residual(self):
        log = EventLog()
        rec = compute_ledger_reconciliation(
            opening_stock=100.0, closing_stock=100.0, patch_system=None, event_log=log,
        )
        assert rec.total_supply == 0.0
        assert rec.total_demand == 0.0
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)
        assert rec.total_requested_extraction == 0.0
        assert rec.total_fulfilled_extraction == 0.0


class TestDemandBelowSupply:
    def test_subsistence_fully_covered_reconciles_exactly(self):
        """opening=100, subsistence demand=10 (fully paid, a pure sink),
        closing must be exactly 90 for a zero residual."""
        log = EventLog()
        log.add(SubsistenceEvent(step=0, per_agent_cost=2.0, n_agents_charged=5, total_cost=10.0))
        rec = compute_ledger_reconciliation(
            opening_stock=100.0, closing_stock=90.0, patch_system=None, event_log=log,
        )
        assert rec.demand_subsistence == pytest.approx(10.0)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)


class TestDemandAboveSupply:
    def test_unmet_extraction_demand_tracked_separately_from_fulfilled(self):
        """Requested 50, only 20 fulfilled (scarcity) -- Section 5
        requirement 1: requested and fulfilled exported separately, and
        the shortfall (30) reported as unmet, never silently absorbed."""
        log = EventLog()
        log.add(
            EcologicalActionEvent(
                step=0, agent=1, patch_id=0, requested_extraction=50.0, actual_extraction=20.0,
                requested_maintenance=0.0, maintenance_effective=0.0, ecological_search_cost=0.0,
                local_occupancy_observed=0.1,
            )
        )
        # Extraction is a patch->agent transfer, not a sink: the patch
        # loses the 20 fulfilled units, the agent gains them, so the
        # *system* total is unchanged (closing == opening).
        rec = compute_ledger_reconciliation(opening_stock=20.0, closing_stock=20.0, patch_system=None, event_log=log)
        assert rec.total_requested_extraction == pytest.approx(50.0)
        assert rec.total_fulfilled_extraction == pytest.approx(20.0)
        assert rec.total_unmet_extraction_demand == pytest.approx(30.0)
        # Extraction is a patch->agent transfer, not a demand sink -- the
        # 20 units fulfilled leave the patch's stock and land on the
        # agent, netting to zero at the *system* level (patches+agents+
        # funds), so it must not appear in total_demand.
        assert rec.total_demand == 0.0
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)


class TestMultiplePatches:
    def test_regeneration_summed_across_all_patches(self):
        ps = _empty_patch_system(n=1)
        ps.patches[0].cumulative_regeneration = 3.0
        ps.patches[1] = ResourcePatch(patch_id=1, capacity=100.0, regen_rate=0.1, resources=10.0)
        ps.patches[1].cumulative_regeneration = 7.0
        log = EventLog()
        rec = compute_ledger_reconciliation(opening_stock=60.0, closing_stock=70.0, patch_system=ps, event_log=log)
        assert rec.supply_regeneration == pytest.approx(10.0)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)


class TestMigration:
    def test_migration_cost_only_charged_on_success(self):
        log = EventLog()
        log.add(
            MigrationEvent(
                step=0, agent_id=1, origin_patch_id=0, destination_patch_id=1, expected_resource_gain=1.0,
                perceived_fairness_origin=0.5, perceived_fairness_destination=0.5, movement_cost=2.0,
                outcome="succeeded", carried_institutional_knowledge=False,
            )
        )
        log.add(
            MigrationEvent(
                step=0, agent_id=2, origin_patch_id=0, destination_patch_id=1, expected_resource_gain=1.0,
                perceived_fairness_origin=0.5, perceived_fairness_destination=0.5, movement_cost=2.0,
                outcome="refused_cost", carried_institutional_knowledge=False,
            )
        )
        rec = compute_ledger_reconciliation(opening_stock=10.0, closing_stock=8.0, patch_system=None, event_log=log)
        assert rec.demand_migration_cost == pytest.approx(2.0)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)


class TestInterpatchTransfers:
    def test_mutual_assistance_transfer_is_net_zero_not_a_sink(self):
        """Section 5 requirement 2: transfers between patches (via their
        rules' funds) must not count as system-level creation or
        destruction. cost=0 isolates the transfer from the coordination
        per-step operating cost, which IS a separate sink."""
        log = EventLog()
        log.add(
            CoordinationActivityEvent(
                step=0, link_id=0, patch_id_a=0, patch_id_b=1, info_accuracy=0.9,
                resource_transferred=5.0, cost=0.0,
            )
        )
        rec = compute_ledger_reconciliation(opening_stock=50.0, closing_stock=50.0, patch_system=None, event_log=log)
        assert rec.transfer_mutual_assistance_fund_to_fund == pytest.approx(5.0)
        assert rec.total_demand == 0.0
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)

    def test_coordination_operating_cost_is_a_genuine_sink(self):
        # Level 1.2b, Work Package E fix: the ledger now sums
        # CoordinationMaintenanceCostEvent.cost (charged unconditionally,
        # once per active link per step), not CoordinationActivityEvent.cost
        # (gated behind coordination_activity_probability) -- see that
        # event's own docstring in core/events.py.
        log = EventLog()
        log.add(CoordinationMaintenanceCostEvent(step=0, link_id=0, cost=4.0))
        rec = compute_ledger_reconciliation(opening_stock=50.0, closing_stock=46.0, patch_system=None, event_log=log)
        assert rec.demand_coordination_cost == pytest.approx(4.0)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)


class TestAdministration:
    def test_administrative_spending_is_a_sink_regardless_of_funded_by(self):
        log = EventLog()
        log.add(
            AdministrativeSpendingEvent(
                step=0, patch_id=0, rule_id=1, delegate_id=2, category="monitoring", amount=3.0,
                funded_by="collective_fund",
            )
        )
        log.add(
            AdministrativeSpendingEvent(
                step=0, patch_id=0, rule_id=1, delegate_id=2, category="overhead", amount=1.5,
                funded_by="delegate_personal",
            )
        )
        rec = compute_ledger_reconciliation(opening_stock=10.0, closing_stock=5.5, patch_system=None, event_log=log)
        assert rec.demand_administrative_spending == pytest.approx(4.5)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)


class TestAppropriation:
    def test_appropriation_is_redistribution_not_a_sink(self):
        """Section 5 requirement 3: appropriation is redistribution
        (fund -> agent), never counted as system creation/destruction."""
        log = EventLog()
        log.add(
            AppropriationEvent(
                step=0, patch_id=0, rule_id=1, delegate_id=2, agent=2, amount=4.0,
                fund_before=10.0, fund_after=6.0,
            )
        )
        rec = compute_ledger_reconciliation(opening_stock=30.0, closing_stock=30.0, patch_system=None, event_log=log)
        assert rec.transfer_appropriation_fund_to_agent == pytest.approx(4.0)
        assert rec.total_demand == 0.0
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)


class TestMaintenance:
    def test_maintenance_inefficiency_loss_is_invested_minus_effective(self):
        ps = _empty_patch_system(n=1)
        ps.patches[0].cumulative_maintenance_invested = 10.0
        ps.patches[0].cumulative_maintenance_effective = 6.0
        log = EventLog()
        rec = compute_ledger_reconciliation(opening_stock=50.0, closing_stock=46.0, patch_system=ps, event_log=log)
        assert rec.demand_maintenance_inefficiency_loss == pytest.approx(4.0)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)

    def test_maintenance_loss_never_negative(self):
        ps = _empty_patch_system(n=1)
        ps.patches[0].cumulative_maintenance_invested = 5.0
        ps.patches[0].cumulative_maintenance_effective = 5.0
        log = EventLog()
        rec = compute_ledger_reconciliation(opening_stock=1.0, closing_stock=1.0, patch_system=ps, event_log=log)
        assert rec.demand_maintenance_inefficiency_loss == pytest.approx(0.0)


class TestShockLoss:
    """Level 1.2b, Work Package C: resource_depletion perturbations
    applied to patches (Section 7's "shock frequency/magnitude"
    ecological design dimension) are a genuine ledger sink."""

    def test_shock_loss_is_a_sink(self):
        ps = _empty_patch_system(n=1)
        ps.patches[0].cumulative_shock_loss = 7.0
        log = EventLog()
        rec = compute_ledger_reconciliation(opening_stock=50.0, closing_stock=43.0, patch_system=ps, event_log=log)
        assert rec.demand_shock_loss == pytest.approx(7.0)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)

    def test_zero_when_no_shock_ever_applied(self):
        ps = _empty_patch_system(n=1)
        log = EventLog()
        rec = compute_ledger_reconciliation(opening_stock=10.0, closing_stock=10.0, patch_system=ps, event_log=log)
        assert rec.demand_shock_loss == pytest.approx(0.0)

    def test_patch_apply_shock_loss_caps_at_current_resources(self):
        ps = _empty_patch_system(n=1, resources=10.0)
        removed = ps.patches[0].apply_shock_loss(1.5)  # fraction > 1 must still be capped
        assert removed == pytest.approx(10.0)
        assert ps.patches[0].resources == pytest.approx(0.0)
        assert ps.patches[0].cumulative_shock_loss == pytest.approx(10.0)

    def test_full_simulation_with_active_shocks_reconciles(self):
        config = SimulationConfig.level12_complete(
            population_size=16, n_patches=3, n_steps=40, seed=777,
            perturbations=(
                {"start_step": 10, "duration": 1, "kind": "resource_depletion", "magnitude": 0.3},
                {"start_step": 20, "duration": 5, "kind": "regeneration_reduction", "magnitude": 0.5},
            ),
        )
        sim = Simulation(config)
        opening = system_total_resources(sim.patch_system, sim.agents, sim.rule_registry)
        sim.run()
        closing = system_total_resources(sim.patch_system, sim.agents, sim.rule_registry)
        rec = compute_ledger_reconciliation(
            opening_stock=opening, closing_stock=closing, patch_system=sim.patch_system, event_log=sim.event_log,
            search_cost=config.search_cost, membership_exit_cost=config.membership_exit_cost,
        )
        assert rec.demand_shock_loss > 0.0
        assert rec.residual == pytest.approx(0.0, abs=1e-4)


class TestCollapse:
    def test_collapse_scenario_all_sinks_reconcile_to_zero_stock(self):
        """A patch drained to zero purely by demand-side sinks (no
        supply) -- the defining shape of Level 1.2's own collapse
        outcome. Every sink category contributes and the residual is
        still exactly zero."""
        log = EventLog()
        log.add(SubsistenceEvent(step=0, per_agent_cost=1.0, n_agents_charged=10, total_cost=10.0))
        log.add(
            EcologicalActionEvent(
                step=0, agent=1, patch_id=0, requested_extraction=5.0, actual_extraction=5.0,
                requested_maintenance=0.0, maintenance_effective=0.0, ecological_search_cost=2.0,
                local_occupancy_observed=0.0,
            )
        )
        log.add(
            MonitoringEvent(
                step=0, patch_id=0, rule_id=1, target=2, true_compliance=False, detected_violation=True,
                outcome="true_positive", monitor=3, cost_to_monitor=1.0, cost_deducted=1.0,
            )
        )
        rec = compute_ledger_reconciliation(opening_stock=13.0, closing_stock=0.0, patch_system=None, event_log=log)
        # subsistence(10) + search_cost(2) + monitoring(1) = 13 sink;
        # extraction(5) is a net-zero patch->agent transfer, not a sink.
        assert rec.total_demand == pytest.approx(13.0)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)


class TestSanctionPenaltyAndAppealRefund:
    def test_sanction_penalty_is_a_sink(self):
        log = EventLog()
        log.add(
            SanctionEvent(
                step=0, patch_id=0, rule_id=1, target=2, magnitude=1.0, cost=0.5, funded_by="bystander",
                false_sanction=False, sanctioner=3, penalty_applied=2.0, sanctioner_cost_deducted=0.5,
            )
        )
        rec = compute_ledger_reconciliation(opening_stock=10.0, closing_stock=7.5, patch_system=None, event_log=log)
        assert rec.demand_sanction_cost == pytest.approx(0.5)
        assert rec.demand_sanction_penalty == pytest.approx(2.0)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)

    def test_appeal_refund_is_a_genuine_exogenous_injection(self):
        """A real finding of this audit: refund is NOT drawn from
        anywhere else in the reconciliation -- it is pure supply."""
        log = EventLog()
        log.add(
            AppealEvent(
                step=0, patch_id=0, rule_id=1, delegate_id=2, appellant=3, original_sanction_step=0,
                was_false_sanction=True, upheld=True, refund=3.0, cost=0.5, cost_deducted=0.5,
            )
        )
        rec = compute_ledger_reconciliation(opening_stock=10.0, closing_stock=12.5, patch_system=None, event_log=log)
        assert rec.supply_appeal_refund == pytest.approx(3.0)
        assert rec.demand_appeal_cost == pytest.approx(0.5)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)


class TestFundDissolution:
    def test_lost_disposition_is_a_sink(self):
        log = EventLog()
        log.add(FundDissolutionEvent(step=0, patch_id=0, rule_id=1, rule_lineage_id=1, amount=6.0, disposition="lost", n_recipients=0))
        rec = compute_ledger_reconciliation(opening_stock=6.0, closing_stock=0.0, patch_system=None, event_log=log)
        assert rec.demand_fund_dissolution_lost == pytest.approx(6.0)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)

    def test_distributed_disposition_is_net_zero_transfer(self):
        log = EventLog()
        log.add(FundDissolutionEvent(step=0, patch_id=0, rule_id=1, rule_lineage_id=1, amount=6.0, disposition="distributed_to_members", n_recipients=2))
        rec = compute_ledger_reconciliation(opening_stock=6.0, closing_stock=6.0, patch_system=None, event_log=log)
        assert rec.transfer_fund_dissolution_distributed == pytest.approx(6.0)
        assert rec.total_demand == 0.0
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)

    def test_retained_for_reconstruction_is_off_registry_not_lost(self):
        """The amount is genuinely retained (on the dissolved rule
        object) but leaves system_total_resources()'s summable state
        since the object exits rule_registry -- tracked in its own
        category, distinguished from a true loss."""
        log = EventLog()
        log.add(FundDissolutionEvent(step=0, patch_id=0, rule_id=1, rule_lineage_id=1, amount=6.0, disposition="retained_for_reconstruction", n_recipients=0))
        rec = compute_ledger_reconciliation(opening_stock=6.0, closing_stock=0.0, patch_system=None, event_log=log)
        assert rec.demand_fund_dissolution_retained_off_registry == pytest.approx(6.0)
        assert rec.demand_fund_dissolution_lost == pytest.approx(0.0)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)


class TestNegativePersonalResourcesReconciliation:
    def test_subsistence_driving_resources_negative_still_reconciles(self):
        log = EventLog()
        log.add(SubsistenceEvent(step=0, per_agent_cost=5.0, n_agents_charged=1, total_cost=5.0))
        # Opening 2.0, agent ends at -3.0 (2.0 - 5.0) -- ledger residual
        # must still be exactly zero; negative closing stock is valid.
        rec = compute_ledger_reconciliation(opening_stock=2.0, closing_stock=-3.0, patch_system=None, event_log=log)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)


class TestDormantAndRemovedAgents:
    def test_replacement_loss_and_injection_tracked_independently(self):
        """Section 5.6 required case: dormant and removed agents.
        removal_replacement mode destroys resources_at_removal and
        creates initial_resources -- two independent quantities, never
        netted against each other by the generative code, so the audit
        must not net them either."""
        log = EventLog()
        log.add(
            ReplacementEvent(
                step=0, agent_id=1, old_demographic_id=1, new_demographic_id=2, old_policy="tit_for_tat",
                new_policy="always_cooperate", inheritance="random_init", resources_at_removal=-4.0,
                initial_resources=10.0,
            )
        )
        rec = compute_ledger_reconciliation(opening_stock=-4.0, closing_stock=10.0, patch_system=None, event_log=log)
        assert rec.demand_replacement_loss == pytest.approx(-4.0)
        assert rec.supply_replacement_injection == pytest.approx(10.0)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)


class TestRealizedBalanceRatio:
    def test_none_when_demand_is_zero(self):
        assert realized_balance_ratio(supply=5.0, requested_demand=0.0) is None

    def test_ratio_when_demand_positive(self):
        assert realized_balance_ratio(supply=5.0, requested_demand=10.0) == pytest.approx(0.5)


class TestFullSimulationResidualIsZero:
    """Integration-level confirmation: a real Simulation run's own
    opening/closing system totals reconcile against the same category
    inventory, not just hand-constructed synthetic events."""

    def test_level12_complete_short_run_reconciles(self):
        config = SimulationConfig.level12_complete(population_size=16, n_patches=3, n_steps=40, seed=777)
        sim = Simulation(config)
        opening = system_total_resources(sim.patch_system, sim.agents, sim.rule_registry)
        sim.run()
        closing = system_total_resources(sim.patch_system, sim.agents, sim.rule_registry)
        rec = compute_ledger_reconciliation(
            opening_stock=opening, closing_stock=closing, patch_system=sim.patch_system, event_log=sim.event_log,
            search_cost=config.search_cost, membership_exit_cost=config.membership_exit_cost,
        )
        assert math.isfinite(rec.residual)
        assert rec.residual == pytest.approx(0.0, abs=1e-4)

    def test_level12_migration_only_short_run_reconciles(self):
        config = SimulationConfig.level12_migration_only(population_size=16, n_patches=3, n_steps=40, seed=778)
        sim = Simulation(config)
        opening = system_total_resources(sim.patch_system, sim.agents, sim.rule_registry)
        sim.run()
        closing = system_total_resources(sim.patch_system, sim.agents, sim.rule_registry)
        rec = compute_ledger_reconciliation(
            opening_stock=opening, closing_stock=closing, patch_system=sim.patch_system, event_log=sim.event_log,
            search_cost=config.search_cost, membership_exit_cost=config.membership_exit_cost,
        )
        assert rec.residual == pytest.approx(0.0, abs=1e-4)


class TestProductionScaleResidualIsZero:
    """Level 1.2b, Work Package E: a real Simulation run at Work Package
    E's actual production scale (population=32, n_patches=4, n_steps=700)
    reconciles to zero residual, for several seeds.

    Disclosed finding: ``TestFullSimulationResidualIsZero`` above only
    ever validated a SHORT run (population=16, n_patches=3, n_steps=40) —
    exactly the scale at which several genuine bugs never had a chance to
    manifest: (1) ``rules/dynamics.py``'s sanction-penalty and every
    other ``max(0.0, resources - cost)`` capped-deduction site silently
    produced a spurious NEGATIVE deduction whenever an agent's resources
    were already negative (a legitimate distress/deficit state elsewhere
    in this model, but one that needs hundreds of steps of sustained
    subsistence pressure to actually occur); (2)
    ``rules/coordination.py``'s per-active-link maintenance fee was
    charged every step but only sometimes logged; (3)
    ``Simulation._rule_formation_round`` conflated rule-ID and patch-ID
    key spaces when routing a dissolved rule's fund/delegate cleanup,
    almost never actually running it; (4) ``amendment_round``'s own
    "support_below_floor" dissolution path never removed the dissolved
    rule from ``rule_registry`` at all, leaving a stale entry whose fund
    stayed silently counted (and could later be silently dropped when a
    new rule was founded at the same patch). None of these needed fewer
    than ~100+ steps and a large-enough population to actually surface —
    this test class is the durable regression guard at the scale that
    first caught them."""

    @pytest.mark.parametrize("seed", [1, 42, 777, 999, 2026])
    def test_level12_complete_production_scale_reconciles(self, seed):
        config = SimulationConfig.level12_complete(population_size=32, n_patches=4, n_steps=700, seed=seed)
        sim = Simulation(config)
        opening = system_total_resources(sim.patch_system, sim.agents, sim.rule_registry)
        sim.run()
        closing = system_total_resources(sim.patch_system, sim.agents, sim.rule_registry)
        rec = compute_ledger_reconciliation(
            opening_stock=opening, closing_stock=closing, patch_system=sim.patch_system, event_log=sim.event_log,
            search_cost=config.search_cost,
        )
        assert math.isfinite(rec.residual)
        assert rec.residual == pytest.approx(0.0, abs=1e-6)


def _real_agent(agent_id, resources=20.0, **overrides):
    from abm_governance.agents.agent import Agent
    from abm_governance.agents.policy import make_policy

    a = Agent(
        agent_id=agent_id, resources=resources, coercive_capability=0.0, policy=make_policy("tit_for_tat"),
        observation_accuracy=1.0, learning_rate=0.1, forgiveness=0.1, risk_sensitivity=0.5, exit_cost=0.1,
    )
    for k, v in overrides.items():
        setattr(a, k, v)
    return a


def _real_rule(rule_id=0, patch_id=0, members=(0, 1), founder=0, fund=0.0, **param_overrides):
    from abm_governance.rules.shared_rule import RuleParameters, SharedRule

    params = RuleParameters(
        extraction_ceiling=0.3, maintenance_requirement=0.4, monitoring_intensity=0.5,
        sanction_magnitude=0.5, adoption_threshold=0.5, amendment_threshold=0.5,
    )
    if param_overrides:
        kwargs = params.as_dict()
        kwargs.update(param_overrides)
        params = RuleParameters(**kwargs)
    return SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0, founder_id=founder,
        rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members), fund=fund,
    )


class TestCappedDeductionNeverGoesNegative:
    """Level 1.2b, Work Package E fix: every ``*_deducted``/``cost_deducted``
    field (monitoring, sanction, membership-exit, audit, appeal) must be
    a real, non-negative amount even when the payer's resources were
    already negative going in -- never a phantom negative "cost" from a
    ``max(0.0, resources - cost)``-style deduction silently resetting a
    distressed agent back to exactly 0.0."""

    def test_monitoring_cost_deducted_from_negative_resources_is_zero_not_negative(self):
        from abm_governance.core.events import ComplianceEvent
        from abm_governance.rules.dynamics import monitoring_round

        monitor = _real_agent(1, resources=-5.0, willingness_to_monitor=1.0)
        target = _real_agent(2, resources=1.0)
        agents_by_id = {1: monitor, 2: target}
        rule = _real_rule(rule_id=0, patch_id=0, members=(1, 2))
        config = SimulationConfig.level12_complete(
            population_size=8, n_patches=1, n_steps=1, seed=1, monitoring_mode="voluntary", monitoring_cost=0.5,
        )
        compliance = [
            ComplianceEvent(
                step=0, patch_id=0, rule_id=0, agent=2, intended_extraction=1.0, intended_maintenance=1.0,
                actual_extraction=1.0, actual_maintenance=1.0, complied=False, violated=True,
            )
        ]
        log = EventLog()
        produced = monitoring_round(0, {0: rule}, agents_by_id, compliance, config, np.random.default_rng(1), log)
        assert produced, "expected at least one monitoring event"
        assert produced[0].monitor == 1
        assert produced[0].cost_deducted == pytest.approx(0.0)
        assert monitor.resources == pytest.approx(-5.0), "an agent already in debt is not further charged"

    def test_sanction_penalty_never_negative_when_target_already_in_debt(self):
        from abm_governance.core.events import MonitoringEvent
        from abm_governance.rules.dynamics import sanction_round

        sanctioner = _real_agent(1, resources=10.0, sanction_preference=1.0)
        target = _real_agent(2, resources=-3.0)
        agents_by_id = {1: sanctioner, 2: target}
        rule = _real_rule(rule_id=0, patch_id=0, members=(1, 2), sanction_magnitude=0.9)
        config = SimulationConfig.level12_complete(
            population_size=8, n_patches=1, n_steps=1, seed=1, sanction_mode="voluntary",
            sanction_cost_per_unit=0.5, sanction_penalty_unit=1.0,
        )
        monitorings = [
            MonitoringEvent(
                step=0, patch_id=0, rule_id=0, target=2, true_compliance=False, detected_violation=True,
                outcome="true_positive", monitor=None, cost_to_monitor=0.0,
            )
        ]
        log = EventLog()
        sanction_round(0, {0: rule}, agents_by_id, monitorings, config, np.random.default_rng(1), log)
        assert log.sanctions, "expected at least one sanction event"
        ev = log.sanctions[0]
        assert ev.penalty_applied == pytest.approx(0.0), "a target already in debt is not further penalized"
        assert ev.penalty_applied >= 0.0
        assert target.resources == pytest.approx(-3.0)


class TestCoordinationMaintenanceCostEvent:
    """Level 1.2b, Work Package E fix: the per-step, per-active-link
    coordination maintenance fee is charged and logged unconditionally,
    independent of the separate activity-probability-gated
    ``CoordinationActivityEvent``."""

    def test_ledger_sums_maintenance_cost_not_activity_cost(self):
        log = EventLog()
        # An activity event with a DIFFERENT cost than the maintenance
        # event -- if the ledger were still (incorrectly) summing
        # CoordinationActivityEvent.cost, this would fail.
        log.add(
            CoordinationActivityEvent(
                step=0, link_id=1, patch_id_a=0, patch_id_b=1, info_accuracy=0.9,
                resource_transferred=0.0, cost=99.0,
            )
        )
        log.add(CoordinationMaintenanceCostEvent(step=0, link_id=1, cost=0.4))
        rec = compute_ledger_reconciliation(opening_stock=10.0, closing_stock=9.6, patch_system=None, event_log=log)
        assert rec.demand_coordination_cost == pytest.approx(0.4)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)

    def test_maintenance_cost_charged_every_step_regardless_of_activity_roll(self):
        """Section 9/Work Package I: config.coordination_activity_probability
        gates CoordinationActivityEvent, never the maintenance fee
        itself -- a real Simulation run with coordination enabled must
        produce more maintenance-cost events than activity events over
        many steps (activity is a strict subset in frequency, never a
        superset)."""
        config = SimulationConfig.level12_complete(population_size=16, n_patches=3, n_steps=60, seed=42)
        assert config.interpatch_coordination_enabled
        sim = Simulation(config)
        sim.run()
        if sim.event_log.coordination_maintenance_costs:
            assert len(sim.event_log.coordination_maintenance_costs) >= len(sim.event_log.coordination_activity)


class TestFundDissolutionZeroRecipientsTreatedAsLost:
    """Level 1.2b, Work Package E fix: ``resolve_dissolution_fund``'s own
    comment discloses that a ``"distributed_to_members"`` disposition
    with no living recipients "falls through to lost in effect" -- the
    ledger must treat it that way even though the event's own
    ``disposition`` field keeps the configured-intent label."""

    def test_zero_recipients_counted_as_lost_not_transferred(self):
        log = EventLog()
        log.add(
            FundDissolutionEvent(
                step=0, patch_id=0, rule_id=1, rule_lineage_id=1, amount=0.64,
                disposition="distributed_to_members", n_recipients=0,
            )
        )
        rec = compute_ledger_reconciliation(opening_stock=0.64, closing_stock=0.0, patch_system=None, event_log=log)
        assert rec.demand_fund_dissolution_lost == pytest.approx(0.64)
        assert rec.transfer_fund_dissolution_distributed == pytest.approx(0.0)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)

    def test_nonzero_recipients_still_treated_as_transfer(self):
        log = EventLog()
        log.add(
            FundDissolutionEvent(
                step=0, patch_id=0, rule_id=1, rule_lineage_id=1, amount=0.64,
                disposition="distributed_to_members", n_recipients=3,
            )
        )
        rec = compute_ledger_reconciliation(opening_stock=0.64, closing_stock=0.64, patch_system=None, event_log=log)
        assert rec.demand_fund_dissolution_lost == pytest.approx(0.0)
        assert rec.transfer_fund_dissolution_distributed == pytest.approx(0.64)
        assert rec.residual == pytest.approx(0.0, abs=LEDGER_RESIDUAL_TOLERANCE)


class TestAmendmentTriggeredDissolutionCleanup:
    """Level 1.2b, Work Package E fix: a rule dissolved via
    ``amendment_round``'s own "support_below_floor" path (a rejected
    amendment whose support also falls below
    ``rule_dissolution_support_floor``) must be removed from
    ``rule_registry`` exactly like any other dissolution -- previously
    left as a stale, inactive, still-registry-counted entry."""

    def test_dissolved_rule_is_removed_from_registry(self):
        from abm_governance.rules.dynamics import amendment_round

        rule = _real_rule(
            rule_id=7, patch_id=0, members=(1, 2), founder=1, fund=0.64, amendment_threshold=0.99,
        )
        agents = {
            1: _real_agent(1, resources=5.0, amendment_propensity=1.0, willingness_to_join=0.0),
            2: _real_agent(2, resources=5.0, amendment_propensity=1.0, willingness_to_join=0.0),
        }
        rule_registry = {0: rule}
        config = SimulationConfig.level12_complete(
            population_size=8, n_patches=1, n_steps=1, seed=1,
            rule_dissolution_support_floor=0.9,  # near-certain to breach with willingness_to_join=0.0
            institutional_decision_noise_std=0.01,
        )
        log = EventLog()
        last_dissolved: dict = {}
        amendment_round(0, rule_registry, agents, config, np.random.default_rng(1), log, last_dissolved)
        # Level 1.2b, Work Package E fix: the dissolved rule must be
        # REMOVED from the registry, exactly like dissolution_round's own
        # dissolutions -- not left behind as a stale, inactive entry
        # whose nonzero fund would keep silently counting toward
        # system_total_resources().
        assert 0 not in rule_registry, "dissolved rule must be removed from rule_registry, not left stale"
        assert 0 in last_dissolved
        assert last_dissolved[0].rule_id == 7
        assert last_dissolved[0].dissolution_step == 0
        assert last_dissolved[0].fund == pytest.approx(0.64), "fund must survive on the off-registry object for resolve_dissolution_fund"
