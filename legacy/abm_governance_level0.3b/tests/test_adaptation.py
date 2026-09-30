"""Imitation/mutation timescale and rate checks."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.adaptation import imitation_round, mutation_round
from abm_governance.agents.agent import Agent
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.scheduler import Scheduler
from abm_governance.simulation import Simulation


def make_population(n: int, policy_name: str = "always_cooperate") -> list[Agent]:
    return [
        Agent(
            agent_id=i,
            resources=10.0,
            coercive_capability=1.0,
            policy=make_policy(policy_name),
            observation_accuracy=0.9,
            learning_rate=0.1,
            forgiveness=0.1,
            risk_sensitivity=0.5,
            exit_cost=1.0,
            memory_length=5,
        )
        for i in range(n)
    ]


# -- Scheduler periodicity -------------------------------------------------

def test_scheduler_fires_on_exact_multiples_only():
    scheduler = Scheduler(imitation_period=10, rewiring_period=5)
    imitate_steps = [s for s in range(41) if scheduler.should_imitate(s)]
    rewire_steps = [s for s in range(41) if scheduler.should_rewire(s)]
    assert imitate_steps == [10, 20, 30, 40]
    assert rewire_steps == [5, 10, 15, 20, 25, 30, 35, 40]


def test_scheduler_never_fires_on_step_zero():
    scheduler = Scheduler(imitation_period=1, rewiring_period=1)
    assert scheduler.should_imitate(0) is False
    assert scheduler.should_rewire(0) is False


def test_scheduler_rejects_nonpositive_periods():
    with pytest.raises(ValueError):
        Scheduler(imitation_period=0, rewiring_period=5)
    with pytest.raises(ValueError):
        Scheduler(imitation_period=5, rewiring_period=-1)


# -- imitation ---------------------------------------------------------------

def test_imitation_prefers_higher_fitness_peer():
    # A rich always_defect population next to one poor always_cooperate
    # agent: with a strong beta, the poor agent should almost always
    # imitate a richer peer.
    agents = make_population(10, policy_name="always_defect")
    for a in agents:
        a.resources = 100.0
    agents[0].resources = 1.0
    agents[0].policy = make_policy("always_cooperate")

    rng = np.random.default_rng(0)
    adoption_count = 0
    trials = 200
    for _ in range(trials):
        agents[0].policy = make_policy("always_cooperate")
        imitation_round(agents, rng, step=1, beta=5.0)
        if agents[0].policy.name == "always_defect":
            adoption_count += 1
    assert adoption_count / trials > 0.9


def test_imitation_no_effect_with_single_agent():
    agents = make_population(1)
    rng = np.random.default_rng(0)
    events = imitation_round(agents, rng, step=1)
    assert events == []


# -- mutation ------------------------------------------------------------

def test_mutation_rate_matches_configured_probability_statistically():
    n_agents = 5000
    agents = make_population(n_agents, policy_name="always_cooperate")
    rng = np.random.default_rng(123)
    rate = 0.05
    events = mutation_round(agents, mutation_rate=rate, rng=rng, step=1)
    observed_rate = len(events) / n_agents
    # binomial std error ~ sqrt(p(1-p)/n) ~ 0.003 here; allow generous margin
    assert observed_rate == pytest.approx(rate, abs=0.01)


def test_mutation_rate_zero_never_mutates():
    agents = make_population(200)
    rng = np.random.default_rng(0)
    events = mutation_round(agents, mutation_rate=0.0, rng=rng, step=1)
    assert events == []


# -- end-to-end: events only occur on the scheduled steps --------------------

def test_full_simulation_only_logs_adaptation_events_on_scheduled_steps():
    config = SimulationConfig(
        population_size=20,
        n_steps=41,
        imitation_period=10,
        rewiring_period=5,
        mutation_rate=0.2,
        seed=1,
    )
    result = Simulation(config).run()
    imitation_steps = {e.step for e in result.event_log.imitations}
    mutation_steps = {e.step for e in result.event_log.mutations}
    rewire_steps = {e.step for e in result.event_log.rewires}
    exit_steps = {e.step for e in result.event_log.exits}

    assert imitation_steps <= {10, 20, 30, 40}
    assert mutation_steps <= {10, 20, 30, 40}
    assert rewire_steps <= {5, 10, 15, 20, 25, 30, 35, 40}
    assert exit_steps <= {5, 10, 15, 20, 25, 30, 35, 40}
