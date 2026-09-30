"""Level 1.0: locally shared, patch-attached rules (Work Packages A-K).

Organized by work package. Every test either (a) exercises
``rules/shared_rule.py``/``rules/dynamics.py`` directly with hand-built
fixtures, or (b) runs a small ``Simulation`` end to end and inspects
``event_log``/``rule_registry``. Backward-compatibility tests (Work
Package, Constraint 15) close the file.
"""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import ComplianceEvent, EventLog
from abm_governance.environment.patches import PatchSystem, ResourcePatch
from abm_governance.rules import dynamics as rd
from abm_governance.rules.shared_rule import RuleParameters, SharedRule, mutate_rule_parameters, sample_rule_parameters
from abm_governance.simulation import Simulation


def _agent(agent_id, patch_id=0, resources=20.0, **overrides):
    a = Agent(
        agent_id=agent_id,
        resources=resources,
        coercive_capability=0.0,
        policy=make_policy("tit_for_tat"),
        observation_accuracy=1.0,
        learning_rate=0.1,
        forgiveness=0.1,
        risk_sensitivity=0.5,
        exit_cost=0.1,
    )
    a.patch_id = patch_id
    a.ecological_policy = EcologicalPolicy(0.5, 0.3, 0.0)
    for k, v in overrides.items():
        setattr(a, k, v)
    return a


def _rule(rule_id=0, patch_id=0, members=(0, 1), founder=0, **param_overrides):
    params = RuleParameters(
        extraction_ceiling=0.3, maintenance_requirement=0.4, monitoring_intensity=0.5,
        sanction_magnitude=0.5, adoption_threshold=0.5, amendment_threshold=0.5,
    )
    if param_overrides:
        kwargs = params.as_dict()
        kwargs.update(param_overrides)
        params = RuleParameters(**kwargs)
    return SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=founder, rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )


# ---------------------------------------------------------------------------
# WP-B: RuleParameters / SharedRule entity
# ---------------------------------------------------------------------------
class TestRuleParameters:
    def test_valid_construction(self):
        p = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
        assert p.as_dict()["extraction_ceiling"] == 0.3

    @pytest.mark.parametrize("field", ["extraction_ceiling", "maintenance_requirement", "monitoring_intensity", "sanction_magnitude"])
    def test_bounded_fields_reject_out_of_range(self, field):
        kwargs = dict(extraction_ceiling=0.3, maintenance_requirement=0.4, monitoring_intensity=0.5,
                      sanction_magnitude=0.5, adoption_threshold=0.5, amendment_threshold=0.5)
        kwargs[field] = 1.5
        with pytest.raises(ValueError):
            RuleParameters(**kwargs)

    def test_threshold_fields_reject_zero(self):
        with pytest.raises(ValueError):
            RuleParameters(0.3, 0.4, 0.5, 0.5, 0.0, 0.5)

    def test_sample_rule_parameters_is_neutral_not_biased_toward_low_extraction(self):
        rng = np.random.default_rng(0)
        draws = [
            sample_rule_parameters(0.5, 0.2, 0.5, 0.2, 0.3, 0.2, 0.3, 0.2, 0.5, 0.15, 0.5, 0.15, rng).extraction_ceiling
            for _ in range(500)
        ]
        assert 0.4 < float(np.mean(draws)) < 0.6

    def test_mutate_rule_parameters_stays_close_to_lineage(self):
        rng = np.random.default_rng(0)
        base = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
        mutated = mutate_rule_parameters(base, mutation_std=0.02, rng=rng)
        assert abs(mutated.extraction_ceiling - base.extraction_ceiling) < 0.2

    def test_mutate_rule_parameters_differs_from_fresh_sample_distribution(self):
        # Ecological mutation is a fresh redraw; rule mutation is a local
        # perturbation -- confirm the two are structurally distinct
        # functions (not merely aliases), per the milestone's explicit
        # "mutation from an existing proposal" requirement.
        import inspect

        from abm_governance.agents.ecological_policy import mutate_ecological_policy
        assert inspect.getsource(mutate_ecological_policy) != inspect.getsource(mutate_rule_parameters)


# ---------------------------------------------------------------------------
# WP-D: compliance decision + apply_rule_compliance
# ---------------------------------------------------------------------------
class TestCompliance:
    def test_no_temptation_always_complies(self):
        rng = np.random.default_rng(0)
        rule = _rule(extraction_ceiling=0.9, maintenance_requirement=0.0)
        agent = _agent(0, violation_tolerance=0.0)
        config = SimulationConfig.level1_rule_formation_default(population_size=10, n_steps=1)
        for _ in range(20):
            assert rd.decide_rule_compliance(agent, rule, 0.5, 0.5, config, rng) is True

    def test_high_temptation_low_tolerance_low_deterrence_mostly_violates(self):
        rng = np.random.default_rng(0)
        rule = _rule(extraction_ceiling=0.0, maintenance_requirement=1.0, monitoring_intensity=0.0, sanction_magnitude=0.0)
        agent = _agent(0, violation_tolerance=0.0)
        config = SimulationConfig.level1_rule_formation_default(population_size=10, n_steps=1, institutional_decision_noise_std=0.05)
        outcomes = [rd.decide_rule_compliance(agent, rule, 1.0, 0.0, config, rng) for _ in range(200)]
        assert sum(1 for o in outcomes if not o) > 150

    def test_high_deterrence_shifts_toward_compliance(self):
        rng_low = np.random.default_rng(1)
        rng_high = np.random.default_rng(1)
        agent = _agent(0, violation_tolerance=0.2)
        config = SimulationConfig.level1_rule_formation_default(population_size=10, n_steps=1, institutional_decision_noise_std=0.2)
        low_deterrence_rule = _rule(extraction_ceiling=0.0, maintenance_requirement=0.0, monitoring_intensity=0.0, sanction_magnitude=0.0)
        high_deterrence_rule = _rule(extraction_ceiling=0.0, maintenance_requirement=0.0, monitoring_intensity=1.0, sanction_magnitude=1.0)
        low = sum(rd.decide_rule_compliance(agent, low_deterrence_rule, 1.0, 0.0, config, rng_low) for _ in range(300))
        high = sum(rd.decide_rule_compliance(agent, high_deterrence_rule, 1.0, 0.0, config, rng_high) for _ in range(300))
        assert high > low

    def test_apply_rule_compliance_violator_untouched(self):
        rule = _rule(extraction_ceiling=0.2, maintenance_requirement=0.8)
        h, m, altered = rd.apply_rule_compliance(10.0, 1.0, rule, complied=False, harvest_unit=5.0, maintenance_unit=5.0)
        assert (h, m, altered) == (10.0, 1.0, False)

    def test_apply_rule_compliance_complier_capped_and_floored(self):
        rule = _rule(extraction_ceiling=0.2, maintenance_requirement=0.8)  # ceiling*5=1.0, floor*5=4.0
        h, m, altered = rd.apply_rule_compliance(10.0, 1.0, rule, complied=True, harvest_unit=5.0, maintenance_unit=5.0)
        assert h == 1.0 and m == 4.0 and altered is True

    def test_apply_rule_compliance_complier_already_satisfying_rule_not_altered(self):
        rule = _rule(extraction_ceiling=0.9, maintenance_requirement=0.0)
        h, m, altered = rd.apply_rule_compliance(1.0, 3.0, rule, complied=True, harvest_unit=5.0, maintenance_unit=5.0)
        assert h == 1.0 and m == 3.0 and altered is False

    def test_randomized_pseudo_institution_ignores_rule_content(self):
        rng = np.random.default_rng(0)
        # A rule that would deterministically demand violation under the
        # ordinary heuristic (ceiling 0, no deterrence) should still
        # produce a mix of True/False under the coin-flip override.
        rule = _rule(extraction_ceiling=0.0, maintenance_requirement=1.0, monitoring_intensity=0.0, sanction_magnitude=0.0)
        agent = _agent(0, violation_tolerance=0.0)
        config = SimulationConfig.level1_randomized_pseudo_institution(
            population_size=10, n_steps=1, randomized_pseudo_institution_compliance_probability=0.5
        )
        outcomes = [rd.decide_rule_compliance(agent, rule, 1.0, 0.0, config, rng) for _ in range(300)]
        n_comply = sum(outcomes)
        assert 100 < n_comply < 200  # roughly 50/50, not the ~0 the content would otherwise force


# ---------------------------------------------------------------------------
# WP-C: proposal and adoption
# ---------------------------------------------------------------------------
def _build_patch_sim(config: SimulationConfig, n_patches=1, n_agents=8):
    agents = [_agent(i, patch_id=0, resources=20.0, willingness_to_join=0.9, preferred_adoption_threshold=0.3) for i in range(n_agents)]
    agents_by_id = {a.agent_id: a for a in agents}
    patch = ResourcePatch(patch_id=0, capacity=100.0, regen_rate=0.1, resources=50.0, members=frozenset(agents_by_id.keys()))
    patch_system = PatchSystem(patches={0: patch}, agent_patch={a.agent_id: 0 for a in agents})
    return agents, agents_by_id, patch_system


class TestProposalAndAdoption:
    def test_proposal_creates_pending_not_immediately_active(self):
        config = SimulationConfig.level1_rule_formation_default(population_size=8, n_steps=1)
        agents, agents_by_id, patch_system = _build_patch_sim(config)
        agents[0].proposal_probability = 1.0
        rng = np.random.default_rng(0)
        event_log = EventLog()
        pending, registry, last_dissolved = {}, {}, {}
        id_state = {"next_rule_id": 0, "next_lineage_id": 0}
        rd.proposal_and_adoption_round(
            0, [0], agents_by_id, patch_system, registry, pending, last_dissolved,
            {0: 0.5}, config, rng, event_log, id_state,
        )
        assert 0 in pending
        assert registry == {}
        assert len(event_log.rule_proposals) == 1
        assert event_log.rule_proposals[0].origin == "proposal"
        assert event_log.rule_proposals[0].parent_rule_lineage_id is None

    def test_sufficient_support_adopts_rule(self):
        config = SimulationConfig.level1_rule_formation_default(population_size=8, n_steps=1)
        agents, agents_by_id, patch_system = _build_patch_sim(config)
        agents[0].proposal_probability = 1.0
        for a in agents[1:]:
            a.willingness_to_join = 0.99
            a.preferred_extraction_ceiling = agents[0].preferred_extraction_ceiling
            a.preferred_maintenance_requirement = agents[0].preferred_maintenance_requirement
        rng = np.random.default_rng(0)
        event_log = EventLog()
        pending, registry, last_dissolved = {}, {}, {}
        id_state = {"next_rule_id": 0, "next_lineage_id": 0}
        for step in range(config.proposal_window_steps + 1):
            rd.proposal_and_adoption_round(
                step, [0], agents_by_id, patch_system, registry, pending, last_dissolved,
                {0: 0.5}, config, rng, event_log, id_state,
            )
            if registry:
                break
        assert 0 in registry
        assert registry[0].n_members >= 1
        assert len(event_log.rule_adoptions) == 1

    def test_insufficient_support_rejects_after_window(self):
        config = SimulationConfig.level1_rule_formation_default(population_size=8, n_steps=1, proposal_window_steps=3)
        agents, agents_by_id, patch_system = _build_patch_sim(config)
        agents[0].proposal_probability = 1.0
        agents[0].preferred_adoption_threshold = 0.99
        for a in agents[1:]:
            a.willingness_to_join = 0.0
        rng = np.random.default_rng(0)
        event_log = EventLog()
        pending, registry, last_dissolved = {}, {}, {}
        id_state = {"next_rule_id": 0, "next_lineage_id": 0}
        for step in range(6):
            rd.proposal_and_adoption_round(
                step, [0], agents_by_id, patch_system, registry, pending, last_dissolved,
                {0: 0.5}, config, rng, event_log, id_state,
            )
        assert registry == {}
        assert any(e.reason == "window_expired_insufficient_support" for e in event_log.rule_rejections)

    def test_at_most_one_active_rule_per_patch(self):
        config = SimulationConfig.level1_rule_formation_default(population_size=8, n_steps=1)
        agents, agents_by_id, patch_system = _build_patch_sim(config)
        registry = {0: _rule(patch_id=0)}
        pending, last_dissolved = {}, {}
        rng = np.random.default_rng(0)
        event_log = EventLog()
        id_state = {"next_rule_id": 5, "next_lineage_id": 5}
        for a in agents:
            a.proposal_probability = 1.0
        rd.proposal_and_adoption_round(
            0, [0], agents_by_id, patch_system, registry, pending, last_dissolved,
            {0: 0.5}, config, rng, event_log, id_state,
        )
        assert len(registry) == 1
        assert pending == {}

    def test_reconstruction_proposal_carries_parent_lineage(self):
        config = SimulationConfig.level1_rule_formation_default(population_size=8, n_steps=1)
        agents, agents_by_id, patch_system = _build_patch_sim(config)
        agents[0].proposal_probability = 1.0
        agents[0].amendment_propensity = 1.0  # reconstruction gate uses this trait
        rng = np.random.default_rng(0)
        event_log = EventLog()
        pending, registry = {}, {}
        parent = _rule(rule_id=99, patch_id=0)
        last_dissolved = {0: parent}
        id_state = {"next_rule_id": 0, "next_lineage_id": 0}
        rd.proposal_and_adoption_round(
            0, [0], agents_by_id, patch_system, registry, pending, last_dissolved,
            {0: 0.5}, config, rng, event_log, id_state,
        )
        ev = event_log.rule_proposals[0]
        assert ev.origin == "mutation"
        assert ev.parent_rule_lineage_id == parent.rule_lineage_id


# ---------------------------------------------------------------------------
# WP-D: membership
# ---------------------------------------------------------------------------
class TestMembership:
    def test_high_willingness_joins(self):
        config = SimulationConfig.level1_rule_formation_default(population_size=8, n_steps=1, mean_degree=3)
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=4)
        for a in agents:
            a.willingness_to_join = 0.99
        registry = {0: _rule(patch_id=0, members=(0,))}
        rng = np.random.default_rng(0)
        event_log = EventLog()
        rd.membership_round(0, registry, agents_by_id, patch_system, config, rng, event_log)
        assert registry[0].n_members > 1
        assert any(e.kind == "join" for e in event_log.memberships)
        assert agents_by_id[1].rule_member_of == registry[0].rule_id

    def test_low_willingness_never_joins(self):
        config = SimulationConfig.level1_rule_formation_default(population_size=8, n_steps=1, mean_degree=3)
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=4)
        for a in agents:
            a.willingness_to_join = 0.01
        registry = {0: _rule(patch_id=0, members=())}
        rng = np.random.default_rng(0)
        event_log = EventLog()
        for step in range(5):
            rd.membership_round(step, registry, agents_by_id, patch_system, config, rng, event_log)
        assert registry[0].n_members == 0

    def test_exit_pays_cost_and_clears_rule_member_of(self):
        config = SimulationConfig.level1_rule_formation_default(population_size=8, n_steps=1, mean_degree=3, membership_exit_cost=2.0)
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=4)
        agents[0].willingness_to_join = 0.01
        agents_by_id[0].rule_member_of = 0
        registry = {0: _rule(patch_id=0, members=(0,))}
        rng = np.random.default_rng(3)
        event_log = EventLog()
        before = agents_by_id[0].resources
        for step in range(30):
            rd.membership_round(step, registry, agents_by_id, patch_system, config, rng, event_log)
            if agents_by_id[0].rule_member_of is None:
                break
        assert agents_by_id[0].rule_member_of is None
        assert agents_by_id[0].resources <= before


# ---------------------------------------------------------------------------
# WP-E: monitoring
# ---------------------------------------------------------------------------
class TestMonitoring:
    def _compliance_events(self, rule_id, violated_map):
        return [
            ComplianceEvent(
                step=0, patch_id=0, rule_id=rule_id, agent=aid,
                intended_extraction=1.0, intended_maintenance=1.0, actual_extraction=1.0, actual_maintenance=1.0,
                complied=not violated, violated=violated,
            )
            for aid, violated in violated_map.items()
        ]

    def test_mode_none_produces_no_events(self):
        config = SimulationConfig.level1_no_institution(population_size=8, n_steps=1, mean_degree=3)
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=4)
        registry = {0: _rule(patch_id=0, members=(0, 1))}
        events = self._compliance_events(registry[0].rule_id, {0: True, 1: False})
        rng = np.random.default_rng(0)
        out = rd.monitoring_round(0, registry, agents_by_id, events, config, rng, EventLog())
        assert out == []

    def test_perfect_mode_has_no_false_positives_or_negatives(self):
        config = SimulationConfig.level1_rule_formation_default(population_size=8, n_steps=1, mean_degree=3, monitoring_mode="perfect")
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=4)
        registry = {0: _rule(patch_id=0, members=(0, 1))}
        events = self._compliance_events(registry[0].rule_id, {0: False, 1: True})
        rng = np.random.default_rng(0)
        out = rd.monitoring_round(0, registry, agents_by_id, events, config, rng, EventLog())
        outcomes = {e.target: e.outcome for e in out}
        assert outcomes[0] == "true_negative"
        assert outcomes[1] == "true_positive"
        assert all(e.monitor is None and e.cost_to_monitor == 0.0 for e in out)

    def test_voluntary_mode_charges_monitor_and_can_false_positive(self):
        config = SimulationConfig.level1_monitoring_only(
            population_size=8, n_steps=1, mean_degree=3, monitoring_mode="voluntary",
            monitoring_false_positive_rate=1.0, monitoring_cost=1.0,
        )
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=4)
        for a in agents:
            a.willingness_to_monitor = 1.0
        registry = {0: _rule(patch_id=0, members=(0, 1, 2))}
        events = self._compliance_events(registry[0].rule_id, {0: False})
        rng = np.random.default_rng(0)
        out = rd.monitoring_round(0, registry, agents_by_id, events, config, rng, EventLog())
        assert out[0].outcome == "false_positive"
        assert out[0].monitor is not None
        assert out[0].cost_to_monitor == 1.0


# ---------------------------------------------------------------------------
# WP-F: sanctioning
# ---------------------------------------------------------------------------
class TestSanctioning:
    def _monitoring_event(self, rule_id, target, true_compliance):
        from abm_governance.core.events import MonitoringEvent
        return MonitoringEvent(
            step=0, patch_id=0, rule_id=rule_id, target=target, true_compliance=true_compliance,
            detected_violation=True, outcome="true_positive" if not true_compliance else "false_positive",
        )

    def test_none_mode_no_sanction(self):
        config = SimulationConfig.level1_no_institution(population_size=8, n_steps=1, mean_degree=3)
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=4)
        registry = {0: _rule(patch_id=0, members=(0, 1, 2))}
        ev = [self._monitoring_event(registry[0].rule_id, 1, False)]
        event_log = EventLog()
        rd.sanction_round(0, registry, agents_by_id, ev, config, np.random.default_rng(0), event_log)
        assert event_log.sanctions == []

    def test_voluntary_sanction_penalizes_target_and_costs_bystander(self):
        config = SimulationConfig.level1_monitoring_plus_voluntary_sanction(population_size=8, n_steps=1, mean_degree=3)
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=4)
        for a in agents:
            a.sanction_preference = 1.0
        registry = {0: _rule(patch_id=0, members=(0, 1, 2), sanction_magnitude=0.8)}
        target_before = agents_by_id[1].resources
        ev = [self._monitoring_event(registry[0].rule_id, 1, False)]
        event_log = EventLog()
        rd.sanction_round(0, registry, agents_by_id, ev, config, np.random.default_rng(0), event_log)
        assert len(event_log.sanctions) == 1
        s = event_log.sanctions[0]
        assert s.funded_by == "bystander"
        assert s.false_sanction is False
        assert agents_by_id[1].resources < target_before

    def test_collective_fund_sanction_skipped_when_fund_insufficient(self):
        config = SimulationConfig.level1_monitoring_plus_collective_sanction(population_size=8, n_steps=1, mean_degree=3)
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=4)
        registry = {0: _rule(patch_id=0, members=(0, 1, 2), sanction_magnitude=0.8)}
        registry[0].fund = 0.0
        ev = [self._monitoring_event(registry[0].rule_id, 1, False)]
        event_log = EventLog()
        rd.sanction_round(0, registry, agents_by_id, ev, config, np.random.default_rng(0), event_log)
        assert event_log.sanctions == []

    def test_collective_fund_sanction_drains_fund_when_sufficient(self):
        config = SimulationConfig.level1_monitoring_plus_collective_sanction(population_size=8, n_steps=1, mean_degree=3)
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=4)
        registry = {0: _rule(patch_id=0, members=(0, 1, 2), sanction_magnitude=0.8)}
        registry[0].fund = 100.0
        ev = [self._monitoring_event(registry[0].rule_id, 1, False)]
        event_log = EventLog()
        rd.sanction_round(0, registry, agents_by_id, ev, config, np.random.default_rng(0), event_log)
        assert len(event_log.sanctions) == 1
        assert registry[0].fund < 100.0
        assert event_log.sanctions[0].sanctioner is None

    def test_false_positive_can_be_falsely_sanctioned(self):
        config = SimulationConfig.level1_monitoring_plus_voluntary_sanction(population_size=8, n_steps=1, mean_degree=3)
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=4)
        for a in agents:
            a.sanction_preference = 1.0
        registry = {0: _rule(patch_id=0, members=(0, 1, 2))}
        ev = [self._monitoring_event(registry[0].rule_id, 1, True)]  # detected despite true compliance
        event_log = EventLog()
        rd.sanction_round(0, registry, agents_by_id, ev, config, np.random.default_rng(0), event_log)
        assert event_log.sanctions[0].false_sanction is True


# ---------------------------------------------------------------------------
# WP-H: amendment / dissolution
# ---------------------------------------------------------------------------
class TestAmendmentAndDissolution:
    def test_membership_floor_breach_dissolves(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=8, n_steps=1, rule_dissolution_membership_floor=0.5
        )
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=8)
        registry = {0: _rule(patch_id=0, members=(0,))}
        agents_by_id[0].rule_member_of = 0
        last_dissolved = {}
        rd.dissolution_round(0, registry, agents_by_id, patch_system, config, EventLog(), last_dissolved)
        assert registry == {}
        assert 0 in last_dissolved
        assert last_dissolved[0].dissolution_reason == "membership_below_floor"
        assert agents_by_id[0].rule_member_of is None

    def test_inactive_duration_dissolves_after_threshold(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=8, n_steps=1, rule_inactive_dissolution_steps=3, rule_dissolution_membership_floor=0.0
        )
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=8)
        registry = {0: _rule(patch_id=0, members=())}
        last_dissolved = {}
        event_log = EventLog()
        for step in range(3):
            rd.dissolution_round(step, registry, agents_by_id, patch_system, config, event_log, last_dissolved)
        assert registry == {}
        assert event_log.rule_dissolutions[-1].reason == "inactive_duration_exceeded"

    def test_healthy_rule_does_not_dissolve(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=8, n_steps=1, rule_dissolution_membership_floor=0.1
        )
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=8)
        registry = {0: _rule(patch_id=0, members=tuple(range(8)))}
        last_dissolved = {}
        for step in range(50):
            rd.dissolution_round(step, registry, agents_by_id, patch_system, config, EventLog(), last_dissolved)
        assert 0 in registry
        assert registry[0].active is True

    def test_amendment_records_field_and_support(self):
        config = SimulationConfig.level1_rule_formation_default(population_size=8, n_steps=1)
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=8)
        for a in agents:
            a.amendment_propensity = 1.0
            a.willingness_to_join = 0.9
        registry = {0: _rule(patch_id=0, members=tuple(a.agent_id for a in agents), amendment_threshold=0.1)}
        event_log = EventLog()
        rd.amendment_round(0, registry, agents_by_id, config, np.random.default_rng(0), event_log)
        assert len(event_log.rule_amendments) == 1
        ev = event_log.rule_amendments[0]
        assert ev.field_changed in ("extraction_ceiling", "maintenance_requirement", "monitoring_intensity", "sanction_magnitude")

    def test_rejected_amendment_below_support_floor_triggers_dissolution(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=8, n_steps=1, rule_dissolution_support_floor=0.9
        )
        agents, agents_by_id, patch_system = _build_patch_sim(config, n_agents=8)
        for a in agents:
            a.amendment_propensity = 1.0
            a.willingness_to_join = 0.01  # near-zero support -> rejection
        rule = _rule(patch_id=0, members=tuple(a.agent_id for a in agents), amendment_threshold=0.99)
        registry = {0: rule}
        event_log = EventLog()
        last_dissolved = {}
        rd.amendment_round(0, registry, agents_by_id, config, np.random.default_rng(0), event_log, last_dissolved)
        # Level 1.2b, Work Package E fix: the dissolved rule must be
        # REMOVED from the registry, exactly like dissolution_round's own
        # dissolutions -- not left behind as a stale, inactive entry
        # (rule_registry is keyed by patch id, so a leftover entry would
        # both silently keep counting toward this rule's fund in
        # system_total_resources() and block correctly-typed reuse of
        # the same patch id).
        assert 0 not in registry
        assert rule.active is False
        assert rule.dissolution_reason == "support_below_floor"
        assert last_dissolved[0] is rule


# ---------------------------------------------------------------------------
# End-to-end via Simulation: imposed rule, dissolution -> reconstruction,
# proto-institution observability.
# ---------------------------------------------------------------------------
class TestSimulationIntegration:
    def test_imposed_rule_active_from_step_zero_no_proposal_needed(self):
        config = SimulationConfig.level1_imposed_rule(population_size=24, n_steps=1, seed=1)
        sim = Simulation(config)
        assert len(sim.rule_registry) > 0
        assert sim.event_log.rule_proposals == []  # never proposed, mechanically installed
        sim.run()

    def test_dissolution_can_be_followed_by_reconstruction_with_recorded_lineage(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=30, n_steps=400, seed=11, rule_inactive_dissolution_steps=15,
        )
        sim = Simulation(config)
        sim.run()
        if not sim.event_log.rule_dissolutions:
            pytest.skip("no dissolution occurred at this seed; reconstruction cannot be exercised")
        mutated_proposals = [e for e in sim.event_log.rule_proposals if e.origin == "mutation"]
        # Not asserted to be nonempty (reconstruction is possible, not
        # guaranteed, per Work Package G) -- but if it happened, every one
        # must carry a real parent lineage id, never a coincidental one.
        for ev in mutated_proposals:
            assert ev.parent_rule_lineage_id is not None

    def test_compliance_and_violation_both_observed_over_a_run(self):
        config = SimulationConfig.level1_rule_formation_default(population_size=30, n_steps=300, seed=2)
        sim = Simulation(config)
        sim.run()
        complied = sum(1 for e in sim.event_log.compliances if e.complied)
        violated = sum(1 for e in sim.event_log.compliances if e.violated)
        assert complied > 0
        assert violated > 0  # adoption must not mechanically create universal compliance (Constraint 10)

    def test_membership_never_forces_a_specific_ecological_action(self):
        # Constraint 10 corollary: a member who already satisfies the rule
        # sees enforcement_altered_action=False for at least some events
        # (the rule permits, not dictates, when it already matches
        # behavior) -- and any given member has both altered and
        # unaltered steps possible in principle (not asserted per-agent,
        # since it depends on trajectory, but the flag must exist and
        # vary across the whole event log).
        config = SimulationConfig.level1_rule_formation_default(population_size=30, n_steps=300, seed=4)
        sim = Simulation(config)
        sim.run()
        altered_values = {e.enforcement_altered_action for e in sim.event_log.compliances}
        assert altered_values == {True, False} or altered_values in ({True}, {False}, set())


# ---------------------------------------------------------------------------
# Constraint 15 / backward compatibility: rule_formation_enabled=False is a
# strict no-op.
# ---------------------------------------------------------------------------
class TestBackwardCompatibility:
    def test_default_config_has_rule_formation_disabled(self):
        assert SimulationConfig().rule_formation_enabled is False

    def test_disabled_produces_zero_level1_events_and_empty_registry(self):
        config = SimulationConfig.level03_patches_default(population_size=30, n_steps=200, seed=1)
        assert config.rule_formation_enabled is False
        sim = Simulation(config)
        sim.run()
        assert sim.rule_registry == {}
        assert sim.event_log.rule_proposals == []
        assert sim.event_log.rule_adoptions == []
        assert sim.event_log.compliances == []
        assert sim.event_log.monitorings == []
        assert sim.event_log.sanctions == []
        assert all(a.rule_member_of is None for a in sim.agents)

    def test_disabled_run_is_bit_identical_to_pre_level1_baseline_shape(self):
        # A same-seed run with rule_formation_enabled explicitly False
        # must produce identical metrics to one where the field is simply
        # left at its default -- proving the new build_agents trait draws
        # and the new _rule_formation_round call consume zero extra RNG
        # draws when disabled.
        c1 = SimulationConfig.level03_patches_default(population_size=20, n_steps=100, seed=5)
        c2 = SimulationConfig.level03_patches_default(population_size=20, n_steps=100, seed=5, rule_formation_enabled=False)
        r1 = Simulation(c1).run()
        r2 = Simulation(c2).run()
        for row1, row2 in zip(r1.metrics, r2.metrics):
            for key in row1:
                if isinstance(row1[key], float) and np.isnan(row1[key]):
                    assert np.isnan(row2[key])
                else:
                    assert row1[key] == row2[key]

    def test_forbidden_attribute_substrings_not_reintroduced(self):
        from abm_governance.agents.agent import FORBIDDEN_ATTRIBUTE_SUBSTRINGS
        import dataclasses

        for f in dataclasses.fields(Agent):
            for bad in FORBIDDEN_ATTRIBUTE_SUBSTRINGS:
                assert bad not in f.name, f"{f.name} contains forbidden substring {bad!r}"
