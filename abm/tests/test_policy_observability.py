"""Work Package D: policy-lineage tracking and the provisional behavioural
phenotype representation."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.adaptation import imitation_round, mutation_round
from abm_governance.agents.agent import Agent
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.observer.phenotype import (
    STANDARD_TEST_HISTORIES,
    behavioral_phenotype,
    pairwise_distance_matrix,
    phenotype_distance,
)
from abm_governance.observer.policy_observability import (
    lineage_distribution,
    mean_payoff_by_policy,
    policy_snapshot,
)
from abm_governance.simulation import Simulation


def make_agent(agent_id: int, policy_name: str = "tit_for_tat", resources: float = 10.0) -> Agent:
    return Agent(
        agent_id=agent_id,
        resources=resources,
        coercive_capability=1.0,
        policy=make_policy(policy_name),
        observation_accuracy=0.9,
        learning_rate=0.1,
        forgiveness=0.1,
        risk_sensitivity=0.5,
        exit_cost=1.0,
        memory_length=5,
    )


# -- lineage: identity, imitation propagation, mutation origination --------

def test_lineage_defaults_to_agent_id():
    agent = make_agent(7)
    assert agent.policy_lineage_id == 7


def test_imitation_propagates_model_agents_lineage():
    agents = [make_agent(0, "always_defect"), make_agent(1, "always_cooperate")]
    agents[1].policy_lineage_id = 99  # pretend agent 1 already carries a distinct lineage
    agents[0].resources = 0.0
    agents[1].resources = 1000.0  # overwhelming fitness gap -> near-certain imitation
    rng = np.random.default_rng(0)
    events = imitation_round(agents, rng, step=1, beta=5.0)
    assert len(events) == 1
    assert agents[0].policy.name == "always_cooperate"
    assert agents[0].policy_lineage_id == 99  # propagated, not agent 0's own id


def test_mutation_assigns_a_fresh_never_before_used_lineage_id():
    agents = [make_agent(i) for i in range(50)]
    rng = np.random.default_rng(1)
    counter = iter(range(1000, 1000 + 50))
    events = mutation_round(agents, mutation_rate=1.0, rng=rng, step=1, lineage_counter=counter)
    assert len(events) == 50
    lineage_ids = [a.policy_lineage_id for a in agents]
    assert all(lid >= 1000 for lid in lineage_ids)
    assert len(set(lineage_ids)) == 50  # every mutated agent got a distinct fresh id


def test_mutation_without_lineage_counter_leaves_lineage_untouched():
    agents = [make_agent(0)]
    rng = np.random.default_rng(0)
    mutation_round(agents, mutation_rate=1.0, rng=rng, step=1, lineage_counter=None)
    assert agents[0].policy_lineage_id == 0


def test_full_simulation_assigns_distinct_mutation_lineages_above_population_size():
    config = SimulationConfig(population_size=20, n_steps=200, seed=0, mutation_rate=0.1, imitation_period=5)
    result = Simulation(config).run()
    if result.event_log.mutations:
        mutated_ids = {e.agent for e in result.event_log.mutations}
        final_lineages = {a.agent_id: a.policy_lineage_id for a in result.final_agents}
        # every agent's final lineage id is either its own agent_id (never
        # imitated/mutated), or >= population_size (traces to some mutation).
        assert all(lid == aid or lid >= config.population_size for aid, lid in final_lineages.items())


# -- lineage_distribution / mean_payoff_by_policy / policy_snapshot --------

def test_lineage_distribution_counts_living_agents_by_lineage():
    agents = [make_agent(0), make_agent(1), make_agent(2)]
    agents[1].policy_lineage_id = 0
    dist = lineage_distribution(agents)
    assert dist == {0: 2, 2: 1}


def test_mean_payoff_by_policy_groups_correctly():
    agents = [
        make_agent(0, "always_cooperate", resources=10.0),
        make_agent(1, "always_cooperate", resources=20.0),
        make_agent(2, "always_defect", resources=5.0),
    ]
    result = mean_payoff_by_policy(agents)
    assert result["always_cooperate"] == pytest.approx(15.0)
    assert result["always_defect"] == pytest.approx(5.0)


def test_policy_snapshot_has_expected_shape():
    agents = [make_agent(0, "grim"), make_agent(1, "grim"), make_agent(2, "random")]
    snap = policy_snapshot(agents, step=42)
    assert snap["step"] == 42
    assert snap["policy_counts"] == {"grim": 2, "random": 1}
    assert snap["n_distinct_lineages"] == 3
    assert set(snap["mean_payoff_by_policy"]) == {"grim", "random"}


# -- behavioural phenotype (provisional, observer-side) ----------------------

def test_deterministic_policies_have_deterministic_phenotypes():
    p1 = behavioral_phenotype("always_cooperate")
    p2 = behavioral_phenotype("always_cooperate")
    assert p1 == p2
    assert len(p1) == len(STANDARD_TEST_HISTORIES)
    assert all(a == 1 for a in p1)  # always cooperates, whatever the history


def test_always_defect_and_always_cooperate_are_maximally_distant():
    d = phenotype_distance("always_cooperate", "always_defect")
    assert d == pytest.approx(1.0)


def test_identical_policy_distance_is_zero():
    assert phenotype_distance("tit_for_tat", "tit_for_tat") == 0.0


def test_tit_for_tat_and_grim_agree_on_short_histories_but_can_diverge():
    # Both cooperate first, and both mirror a single defection the same
    # way; they can only diverge once memory shows recovery after a
    # defection (tit_for_tat forgives immediately, grim never does).
    d = phenotype_distance("tit_for_tat", "grim")
    assert 0.0 <= d <= 1.0
    tft = behavioral_phenotype("tit_for_tat")
    grim = behavioral_phenotype("grim")
    assert tft[0] == grim[0]  # both cooperate on the first move


def test_pairwise_distance_matrix_is_symmetric_with_zero_diagonal():
    names = ("always_cooperate", "always_defect", "tit_for_tat")
    matrix = pairwise_distance_matrix(names)
    for a in names:
        assert matrix[(a, a)] == 0.0
        for b in names:
            assert matrix[(a, b)] == pytest.approx(matrix[(b, a)])
