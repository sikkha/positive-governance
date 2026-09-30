"""Level 0.3, Work Package E: observer-layer metrics for local patches and
the ecological-policy dimension -- hand-computed cases and degenerate
(zero-denominator / no-mechanism-active) behaviour."""

from __future__ import annotations

import math

import pytest

from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EcologicalActionEvent, EventLog, InteractionEvent
from abm_governance.environment.patches import PatchSystem, ResourcePatch
from abm_governance.interactions.game import COOPERATE, DEFECT
from abm_governance.observer.niche_metrics import (
    ecological_policy_diversity_bits,
    ecological_policy_snapshot,
    ecological_step_summary,
    joint_action_frequencies,
    patch_occupancy_summary,
)
from abm_governance.simulation import Simulation


# -- patch_occupancy_summary --------------------------------------------

def test_patch_occupancy_summary_all_nan_when_patch_system_is_none():
    row = patch_occupancy_summary(None)
    assert row["n_patches"] == 0
    for key in ("patch_occupancy_mean", "patch_occupancy_spatial_gini", "fraction_patches_depleted"):
        assert math.isnan(row[key])


def test_patch_occupancy_summary_hand_computed():
    p0 = ResourcePatch(patch_id=0, capacity=100.0, regen_rate=0.1, resources=90.0)  # occ=0.9 (abundant)
    p1 = ResourcePatch(patch_id=1, capacity=100.0, regen_rate=0.1, resources=2.0)  # occ=0.02 (depleted)
    p2 = ResourcePatch(patch_id=2, capacity=100.0, regen_rate=0.1, resources=50.0)  # occ=0.5 (neither)
    system = PatchSystem(patches={0: p0, 1: p1, 2: p2}, agent_patch={})
    row = patch_occupancy_summary(system)
    assert row["n_patches"] == 3
    assert row["patch_occupancy_mean"] == pytest.approx((0.9 + 0.02 + 0.5) / 3)
    assert row["patch_occupancy_min"] == pytest.approx(0.02)
    assert row["patch_occupancy_max"] == pytest.approx(0.9)
    assert row["n_patches_depleted"] == pytest.approx(1.0)
    assert row["n_patches_abundant"] == pytest.approx(1.0)
    assert row["fraction_patches_depleted"] == pytest.approx(1.0 / 3)
    assert row["fraction_patches_abundant"] == pytest.approx(1.0 / 3)
    assert row["aggregate_patch_resources"] == pytest.approx(142.0)
    assert row["aggregate_patch_capacity"] == pytest.approx(300.0)


def test_patch_occupancy_summary_spatial_gini_zero_when_all_patches_equal():
    patches = {i: ResourcePatch(patch_id=i, capacity=100.0, regen_rate=0.1, resources=40.0) for i in range(4)}
    row = patch_occupancy_summary(PatchSystem(patches=patches, agent_patch={}))
    assert row["patch_occupancy_spatial_gini"] == pytest.approx(0.0)


def test_patch_occupancy_summary_custom_thresholds():
    p0 = ResourcePatch(patch_id=0, capacity=100.0, regen_rate=0.1, resources=30.0)  # occ=0.3
    system = PatchSystem(patches={0: p0}, agent_patch={})
    row = patch_occupancy_summary(system, depleted_threshold=0.5, abundant_threshold=0.2)
    assert row["n_patches_depleted"] == pytest.approx(1.0)  # 0.3 <= 0.5
    assert row["n_patches_abundant"] == pytest.approx(1.0)  # 0.3 >= 0.2


# -- ecological_step_summary ---------------------------------------------

def test_ecological_step_summary_all_nan_when_no_events_this_step():
    row = ecological_step_summary(EventLog(), step=0)
    assert row["n_ecological_agents"] == 0
    assert math.isnan(row["ecological_requested_extraction_total"])
    assert math.isnan(row["restraint_frequency"])


def _eco_event(step, agent, patch_id, req_h, act_h, req_m, m_eff, search_cost=0.0, occ=0.5):
    return EcologicalActionEvent(
        step=step, agent=agent, patch_id=patch_id, requested_extraction=req_h, actual_extraction=act_h,
        requested_maintenance=req_m, maintenance_effective=m_eff, ecological_search_cost=search_cost,
        local_occupancy_observed=occ,
    )


def test_ecological_step_summary_hand_computed():
    log = EventLog()
    log.add(_eco_event(0, 0, 0, req_h=10.0, act_h=5.0, req_m=0.0, m_eff=0.0, search_cost=1.0))  # extraction-active
    log.add(_eco_event(0, 1, 0, req_h=0.0, act_h=0.0, req_m=8.0, m_eff=4.0))  # restraint + maintenance-active
    log.add(_eco_event(0, 2, 0, req_h=0.0, act_h=0.0, req_m=0.0, m_eff=0.0))  # pure restraint
    row = ecological_step_summary(log, step=0)
    assert row["n_ecological_agents"] == 3
    assert row["ecological_requested_extraction_total"] == pytest.approx(10.0)
    assert row["ecological_actual_extraction_total"] == pytest.approx(5.0)
    assert row["ecological_extraction_shortfall_total"] == pytest.approx(5.0)
    assert row["ecological_requested_maintenance_total"] == pytest.approx(8.0)
    assert row["ecological_maintenance_effective_total"] == pytest.approx(4.0)
    assert row["ecological_search_cost_total"] == pytest.approx(1.0)
    assert row["restraint_count"] == pytest.approx(2.0)  # agents 1 and 2 requested zero extraction
    assert row["restraint_frequency"] == pytest.approx(2.0 / 3)
    assert row["extraction_active_count"] == pytest.approx(1.0)
    assert row["maintenance_active_count"] == pytest.approx(1.0)


def test_ecological_step_summary_only_uses_events_from_the_requested_step():
    log = EventLog()
    log.add(_eco_event(0, 0, 0, 5.0, 5.0, 0.0, 0.0))
    log.add(_eco_event(1, 0, 0, 7.0, 7.0, 0.0, 0.0))
    row = ecological_step_summary(log, step=1)
    assert row["ecological_requested_extraction_total"] == pytest.approx(7.0)


# -- joint_action_frequencies ---------------------------------------------

def _interaction(step, a, b, action_a, action_b):
    return InteractionEvent(
        step=step, agent_a=a, agent_b=b, action_a=action_a, action_b=action_b, payoff_a=0.0, payoff_b=0.0,
        observed_a_by_b=action_a, observed_b_by_a=action_b, punishment_available=False,
        resource_status_a="solvent", resource_status_b="solvent", degree_a=1, degree_b=1,
    )


def test_joint_action_frequencies_hand_computed():
    log = EventLog()
    # Agent 0: cooperates (majority), extraction-dominant.
    log.add(_interaction(0, 0, 9, COOPERATE, DEFECT))
    log.add(_eco_event(0, 0, 0, req_h=10.0, act_h=10.0, req_m=2.0, m_eff=1.0))
    # Agent 1: defects (majority), maintenance-dominant.
    log.add(_interaction(0, 1, 9, DEFECT, COOPERATE))
    log.add(_eco_event(0, 1, 0, req_h=2.0, act_h=2.0, req_m=10.0, m_eff=5.0))
    # Agent 2: has an ecological event but NO interaction this step ->
    # excluded from the joint tally entirely.
    log.add(_eco_event(0, 2, 0, req_h=5.0, act_h=5.0, req_m=0.0, m_eff=0.0))

    row = joint_action_frequencies(log, step=0)
    assert row["n_joint_eligible_agents"] == pytest.approx(2.0)
    assert row["cooperate_and_extraction_dominant_count"] == pytest.approx(1.0)
    assert row["defect_and_maintenance_dominant_count"] == pytest.approx(1.0)
    assert row["cooperate_and_maintenance_dominant_count"] == pytest.approx(0.0)
    assert row["defect_and_extraction_dominant_count"] == pytest.approx(0.0)
    assert row["cooperate_and_extraction_dominant_frequency"] == pytest.approx(0.5)


def test_joint_action_frequencies_zero_denominator_is_nan_not_zero():
    row = joint_action_frequencies(EventLog(), step=0)
    assert row["n_joint_eligible_agents"] == pytest.approx(0.0)
    for label in (
        "cooperate_and_extraction_dominant",
        "cooperate_and_maintenance_dominant",
        "defect_and_extraction_dominant",
        "defect_and_maintenance_dominant",
    ):
        assert math.isnan(row[f"{label}_frequency"])
        assert row[f"{label}_count"] == pytest.approx(0.0)


def test_joint_action_frequencies_tie_broken_toward_defect():
    log = EventLog()
    log.add(_interaction(0, 0, 9, COOPERATE, DEFECT))
    log.add(_interaction(0, 0, 8, DEFECT, DEFECT))  # agent 0: 1 cooperate, 1 defect -> tie -> "defect"
    log.add(_eco_event(0, 0, 0, req_h=10.0, act_h=10.0, req_m=0.0, m_eff=0.0))
    row = joint_action_frequencies(log, step=0)
    assert row["defect_and_extraction_dominant_count"] == pytest.approx(1.0)
    assert row["cooperate_and_extraction_dominant_count"] == pytest.approx(0.0)


# -- ecological-policy diversity / snapshot --------------------------------

def make_agent(agent_id, ext, maint, scar):
    from abm_governance.agents.agent import Agent
    from abm_governance.agents.policy import make_policy

    return Agent(
        agent_id=agent_id, resources=10.0, coercive_capability=1.0, policy=make_policy("tit_for_tat"),
        observation_accuracy=0.9, learning_rate=0.1, forgiveness=0.1, risk_sensitivity=0.5,
        exit_cost=1.0, memory_length=5, ecological_policy=EcologicalPolicy(ext, maint, scar),
    )


def test_ecological_policy_diversity_zero_when_all_agents_identical():
    agents = [make_agent(i, 0.5, 0.5, 0.5) for i in range(10)]
    assert ecological_policy_diversity_bits(agents) == pytest.approx(0.0)


def test_ecological_policy_diversity_positive_when_agents_differ():
    agents = [make_agent(i, 0.1, 0.1, 0.1) for i in range(5)] + [make_agent(i + 5, 0.9, 0.9, 0.9) for i in range(5)]
    assert ecological_policy_diversity_bits(agents) > 0.0


def test_ecological_policy_snapshot_structure():
    agents = [make_agent(i, 0.2 * i, 0.1 * i, 0.05 * i) for i in range(5)]
    row = ecological_policy_snapshot(agents, step=3)
    assert row["step"] == 3
    assert row["n_distinct_ecological_lineages"] == 5  # default lineage_id == agent_id, all distinct
    assert "extraction_propensity_mean" in row


# -- full-simulation integration: metrics row always carries the new
# columns, NaN under global_pool topology, real values under patches.
# ---------------------------------------------------------------------

def test_full_run_metrics_rows_always_carry_niche_columns():
    config = SimulationConfig(population_size=10, n_steps=5, seed=0)  # global_pool
    result = Simulation(config).run()
    for row in result.metrics:
        assert "patch_occupancy_mean" in row
        assert math.isnan(row["patch_occupancy_mean"])
        assert row["n_ecological_agents"] == 0


def test_full_run_metrics_rows_carry_real_niche_values_under_patches():
    config = SimulationConfig.level03_patches_default(population_size=12, n_steps=5, seed=0)
    result = Simulation(config).run()
    for row in result.metrics:
        assert not math.isnan(row["patch_occupancy_mean"])
        assert row["n_ecological_agents"] == 12
