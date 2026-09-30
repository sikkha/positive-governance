"""Manually-derived EWMA checks for memory, reputation, and payoff estimate
updates, plus forgiveness decay and bounded memory length."""

from __future__ import annotations

import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.policy import make_policy


def make_agent(**overrides) -> Agent:
    defaults = dict(
        agent_id=0,
        resources=10.0,
        coercive_capability=1.0,
        policy=make_policy("tit_for_tat"),
        observation_accuracy=0.9,
        learning_rate=0.5,
        forgiveness=0.2,
        risk_sensitivity=0.5,
        exit_cost=1.0,
        memory_length=3,
    )
    defaults.update(overrides)
    return Agent(**defaults)


def test_reputation_ewma_matches_hand_calculation():
    agent = make_agent(learning_rate=0.5)
    # prior is 0.5 (neutral) on first contact
    agent.record_observation(partner_id=1, observed_action=1, payoff=2.0, step=0)
    assert agent.reputation_estimates[1] == pytest.approx(0.75)
    agent.record_observation(partner_id=1, observed_action=1, payoff=3.0, step=1)
    assert agent.reputation_estimates[1] == pytest.approx(0.875)
    agent.record_observation(partner_id=1, observed_action=0, payoff=-1.0, step=2)
    assert agent.reputation_estimates[1] == pytest.approx(0.4375)


def test_payoff_estimate_ewma_matches_hand_calculation():
    agent = make_agent(learning_rate=0.5)
    agent.record_observation(partner_id=1, observed_action=1, payoff=2.0, step=0)
    assert agent.partner_payoff_estimate[1] == pytest.approx(1.0)
    agent.record_observation(partner_id=1, observed_action=1, payoff=3.0, step=1)
    assert agent.partner_payoff_estimate[1] == pytest.approx(2.0)
    agent.record_observation(partner_id=1, observed_action=0, payoff=-1.0, step=2)
    assert agent.partner_payoff_estimate[1] == pytest.approx(0.5)


def test_forgiveness_decay_matches_hand_calculation():
    agent = make_agent(learning_rate=0.5, forgiveness=0.2)
    agent.record_observation(partner_id=1, observed_action=0, payoff=0.0, step=0)
    agent.record_observation(partner_id=1, observed_action=0, payoff=0.0, step=1)
    # reputation after two defections observed: 0.5 -> 0.25 -> 0.125
    assert agent.reputation_estimates[1] == pytest.approx(0.125)
    agent.decay_reputations()
    # (1 - 0.2) * 0.125 + 0.2 * 0.5 = 0.1 + 0.1 = 0.2
    assert agent.reputation_estimates[1] == pytest.approx(0.2)


def test_memory_is_bounded_by_memory_length():
    agent = make_agent(memory_length=3)
    for action in (1, 1, 0, 1):  # 4 observations into a maxlen=3 deque
        agent.record_observation(partner_id=1, observed_action=action, payoff=0.0, step=0)
    assert agent.partner_history(1) == [1, 0, 1]


def test_forget_partner_clears_all_partner_state():
    agent = make_agent()
    agent.record_observation(partner_id=1, observed_action=1, payoff=1.0, step=0)
    assert 1 in agent.memory
    agent.forget_partner(1)
    assert 1 not in agent.memory
    assert 1 not in agent.reputation_estimates
    assert 1 not in agent.partner_payoff_estimate
    assert 1 not in agent.relationship_started_at


def test_relationship_started_at_records_first_contact_step():
    agent = make_agent()
    agent.ensure_partner(partner_id=2, step=7)
    assert agent.relationship_started_at[2] == 7
    # a later ensure_partner call for the same partner does not overwrite it
    agent.ensure_partner(partner_id=2, step=99)
    assert agent.relationship_started_at[2] == 7


def test_forbidden_attribute_name_guard():
    from abm_governance.agents.agent import FORBIDDEN_ATTRIBUTE_SUBSTRINGS

    assert "state_capacity" in FORBIDDEN_ATTRIBUTE_SUBSTRINGS
    assert "legitimacy" in FORBIDDEN_ATTRIBUTE_SUBSTRINGS
