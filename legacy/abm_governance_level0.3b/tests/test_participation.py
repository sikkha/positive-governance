"""Level 0.2, Work Package A: participation-opportunity accounting.

Covers the core opportunities_total identity (a hand-computed
micro-scenario plus a full-simulation invariant check across every mode
combination that touches the interaction-eligibility branches), the
NaN-safe conditional-probability columns in ``observer/metrics.py``, and
the ``observer/participation.py`` diagnostics.
"""

from __future__ import annotations

import math

import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog, InteractionEvent, WithholdEvent
from abm_governance.interactions.game import COOPERATE, DEFECT
from abm_governance.observer.metrics import compute_step_metrics
from abm_governance.observer.participation import (
    cooperation_by_degree,
    cooperation_by_policy_lineage,
    cooperation_by_recent_payoff,
    cooperation_by_resource_status,
    participation_bias_summary,
)
from abm_governance.simulation import Simulation


def make_agent(agent_id: int, **overrides) -> Agent:
    defaults = dict(
        agent_id=agent_id,
        resources=10.0,
        coercive_capability=1.0,
        policy=make_policy("tit_for_tat"),
        observation_accuracy=0.9,
        learning_rate=0.1,
        forgiveness=0.1,
        risk_sensitivity=0.5,
        exit_cost=1.0,
        memory_length=5,
    )
    defaults.update(overrides)
    return Agent(**defaults)


# ---------------------------------------------------------------------
# Hand-computed micro-scenario: 2 completed interactions (4 agent-sides),
# 3 withhold events (3 agent-sides) => opportunities_total = 7.
# ---------------------------------------------------------------------
def _hand_built_event_log() -> EventLog:
    log = EventLog()
    log.add(
        InteractionEvent(
            step=0, agent_a=0, agent_b=1, action_a=COOPERATE, action_b=COOPERATE,
            payoff_a=3.0, payoff_b=3.0, observed_a_by_b=COOPERATE, observed_b_by_a=COOPERATE,
            punishment_available=False, resource_status_a="solvent", resource_status_b="solvent",
            degree_a=2, degree_b=2,
        )
    )
    log.add(
        InteractionEvent(
            step=0, agent_a=2, agent_b=3, action_a=DEFECT, action_b=COOPERATE,
            payoff_a=5.0, payoff_b=0.0, observed_a_by_b=DEFECT, observed_b_by_a=COOPERATE,
            punishment_available=False, resource_status_a="distressed", resource_status_b="solvent",
            degree_a=1, degree_b=3,
        )
    )
    log.add(WithholdEvent(step=0, agent=4, partner=5, reason="distress"))
    log.add(WithholdEvent(step=0, agent=5, partner=4, reason="partner_distress"))
    log.add(WithholdEvent(step=0, agent=6, partner=7, reason="ineligible_dormant"))
    return log


def test_hand_computed_opportunities_total_identity():
    log = _hand_built_event_log()
    summary = participation_bias_summary(log)
    # 2 interactions * 2 sides = 4 completed agent-opportunities; 3 withholds.
    assert summary["completed_agent_opportunities"] == 4
    assert summary["withhold_total"] == 3
    assert summary["opportunities_total"] == 7


def test_hand_computed_cooperation_rates():
    log = _hand_built_event_log()
    summary = participation_bias_summary(log)
    # cooperate_count: interaction 1 both cooperate (2), interaction 2 one
    # cooperates (1) => 3 of 4 completed agent-opportunities cooperated.
    assert summary["cooperate_count"] == 3
    assert summary["conditional_cooperation_rate"] == pytest.approx(3 / 4)
    assert summary["unconditional_cooperation_rate"] == pytest.approx(3 / 7)
    assert summary["participation_rate"] == pytest.approx(4 / 7)
    # The bias diagnostic: conditional rate is strictly higher than
    # unconditional whenever any opportunities were withheld.
    assert summary["conditional_minus_unconditional_gap"] > 0


def test_zero_denominator_yields_nan_not_zero():
    empty = EventLog()
    summary = participation_bias_summary(empty)
    assert math.isnan(summary["conditional_cooperation_rate"])
    assert math.isnan(summary["unconditional_cooperation_rate"])
    assert math.isnan(summary["participation_rate"])
    assert summary["opportunities_total"] == 0


def test_cooperation_by_resource_status_breakdown():
    log = _hand_built_event_log()
    by_status = cooperation_by_resource_status(log)
    assert by_status["solvent"]["participant_agent_opportunities"] == 3  # a0,b1,b3
    assert by_status["distressed"]["participant_agent_opportunities"] == 1  # a2
    assert by_status["distressed"]["cooperation_rate"] == pytest.approx(0.0)  # a2 defected
    # Nonparticipant side: agent 4/5 withheld under distress-family
    # reasons, agent 6 under a dormancy reason.
    assert by_status["distressed"]["nonparticipant_agent_opportunities"] == 1
    assert by_status["dormant"]["nonparticipant_agent_opportunities"] == 1
    assert by_status["willing_but_partner_blocked"]["nonparticipant_agent_opportunities"] == 1


def test_cooperation_by_degree_breakdown():
    log = _hand_built_event_log()
    by_degree = cooperation_by_degree(log)
    assert by_degree["low_degree"]["agent_opportunities"] == 3  # degree 1 and 2, 2
    assert by_degree["mid_degree"]["agent_opportunities"] == 1  # degree 3


def test_cooperation_by_policy_lineage_and_recent_payoff_are_join_based():
    log = _hand_built_event_log()
    agents = [make_agent(i, resources=float(i)) for i in range(4)]
    agents[0].policy_lineage_id = 100
    agents[1].policy_lineage_id = 100
    agents[2].policy_lineage_id = 200
    agents[3].policy_lineage_id = 200
    by_lineage = cooperation_by_policy_lineage(log, agents)
    assert by_lineage[100]["agent_opportunities"] == 2
    assert by_lineage[200]["agent_opportunities"] == 2

    # recent_payoff defaults to 0.0 (empty window) => "near_zero" bucket.
    by_payoff = cooperation_by_recent_payoff(log, agents)
    assert sum(v["agent_opportunities"] for v in by_payoff.values()) == 4


# ---------------------------------------------------------------------
# Full-simulation invariant: opportunities_total == completed_agent_
# opportunities + withhold_total, every single step, regardless of mode.
# ---------------------------------------------------------------------
@pytest.mark.parametrize("viability_mode", ["none", "dormancy_recovery", "removal_replacement"])
def test_opportunities_identity_holds_every_step(viability_mode):
    config = SimulationConfig(
        population_size=20,
        n_steps=40,
        seed=3,
        ecology_enabled=True,
        relationship_dynamics_enabled=True,
        subsistence_cost=1.5,  # aggressive, to actually drive distress/dormancy
        distress_threshold=0.0,
        distress_engagement_prob=0.3,
        viability_mode=viability_mode,
        viability_deficit_steps_threshold=3,
        viability_max_dormant_steps=5,
        environment_capacity=50.0,
        environment_initial_fraction=0.1,
    )
    result = Simulation(config).run()
    for row in result.metrics:
        expected_total = row["completed_agent_opportunities"] + row["withhold_total_this_step"]
        assert row["opportunities_total"] == pytest.approx(expected_total), row["step"]


def test_p_columns_are_nan_without_config():
    agents = [make_agent(0), make_agent(1)]
    log = EventLog()
    row = compute_step_metrics(agents, __import__("networkx").Graph(), log, step=0)
    assert math.isnan(row["opportunities_total"])
    assert math.isnan(row["p_interaction_given_opportunity"])
