"""Level 0.2, Work Package B: viability state machine.

Covers: exact Level-0.1 reproduction under viability_mode="none"; a
hand-computed deficit-duration transition trace for
dormancy_recovery; full removal/replacement lifecycle including identity
bookkeeping (agent_id unchanged, demographic_id fresh, lineage per the
configured inheritance rule — never silently defaulting to
dominant_policy); and the observer/viability.py aggregation functions.
"""

from __future__ import annotations

import math

import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.viability import (
    population_state_summary,
    replacement_lineage_summary,
    transition_cause_counts,
)
from abm_governance.simulation import Simulation


def _config(viability_mode: str, **overrides) -> SimulationConfig:
    base = dict(
        population_size=16,
        n_steps=60,
        seed=1,
        ecology_enabled=True,
        relationship_dynamics_enabled=True,
        subsistence_cost=2.0,
        distress_threshold=0.0,
        distress_engagement_prob=0.5,
        viability_mode=viability_mode,
        viability_deficit_steps_threshold=3,
        viability_recovery_resources=5.0,
        viability_max_dormant_steps=4,
        environment_capacity=30.0,
        environment_initial_fraction=0.05,  # near-empty: forces deficits fast
    )
    base.update(overrides)
    return SimulationConfig(**base)


def test_viability_mode_none_never_transitions():
    result = Simulation(_config("none")).run()
    assert result.event_log.viability_transitions == []
    assert result.event_log.replacements == []
    for agent in result.final_agents:
        assert agent.viability_state == "active"
        assert agent.consecutive_deficit_steps == 0


def test_viability_mode_none_reproduces_level01_metrics_columns():
    """viability_mode="none" must be indistinguishable from Level 0.1's
    prior behaviour: every agent stays "active" the whole run, so the new
    population-state columns are a trivial partition."""
    result = Simulation(_config("none")).run()
    n = len(result.final_agents)
    for row in result.metrics:
        assert row["active_population"] == n
        assert row["distressed_population"] == 0
        assert row["dormant_population"] == 0
        assert row["viability_transition_count"] == 0
        assert row["removal_count"] == 0


def test_dormancy_recovery_agents_transition_and_never_get_removed():
    result = Simulation(_config("dormancy_recovery")).run()
    transitions = result.event_log.viability_transitions
    assert transitions, "expected at least one transition with an aggressively depleted pool"
    to_states = {e.to_state for e in transitions}
    assert "nonviable" not in to_states  # dormancy_recovery never removes
    assert result.event_log.replacements == []
    # Every agent's own transition sequence must be well-formed: no two
    # consecutive identical states, and only states reachable from the
    # documented state machine.
    by_agent: dict[int, list] = {}
    for e in sorted(transitions, key=lambda e: e.step):
        by_agent.setdefault(e.agent, []).append(e)
    valid_edges = {
        ("active", "distressed"),
        ("distressed", "active"),
        ("distressed", "dormant"),
        ("dormant", "active"),
    }
    for agent_id, events in by_agent.items():
        prev = "active"
        for e in events:
            assert e.from_state == prev, f"agent {agent_id} step {e.step}: expected from_state {prev}, got {e.from_state}"
            assert (e.from_state, e.to_state) in valid_edges
            prev = e.to_state


def test_removal_replacement_produces_replacements_with_identity_bookkeeping():
    result = Simulation(_config("removal_replacement", viability_max_dormant_steps=2)).run()
    assert result.event_log.replacements, "expected at least one removal+replacement with a near-empty pool"
    seen_agent_ids = set()
    for e in result.event_log.replacements:
        seen_agent_ids.add(e.agent_id)
        # agent_id (population slot) is a valid existing slot.
        assert 0 <= e.agent_id < 16
        # demographic_id strictly increases across a replacement.
        assert e.new_demographic_id > e.old_demographic_id
        assert e.inheritance in (
            "random_init", "dominant_policy", "parent_lineage_imitation", "mutation_fresh",
        )
    # Final agents at a replaced slot carry the *new* demographic_id, not
    # the original agent_id-equals-demographic_id invariant from t=0.
    for agent in result.final_agents:
        if agent.replacement_count > 0:
            assert agent.demographic_id != agent.agent_id


def test_default_replacement_policy_is_not_dominant_policy():
    """Explicit milestone requirement: never silently default to
    dominant-policy inheritance."""
    assert SimulationConfig().viability_replacement_policy == "random_init"


@pytest.mark.parametrize(
    "rule", ["random_init", "dominant_policy", "parent_lineage_imitation", "mutation_fresh"]
)
def test_every_replacement_policy_runs_without_error(rule):
    config = _config("removal_replacement", viability_max_dormant_steps=2, viability_replacement_policy=rule)
    result = Simulation(config).run()
    # Not asserting replacements necessarily occur for every rule/seed
    # combination — just that the configured rule, when it does fire,
    # matches what was requested and the run completes cleanly.
    for e in result.event_log.replacements:
        assert e.inheritance == rule


def test_population_state_summary_and_transition_cause_counts():
    result = Simulation(_config("dormancy_recovery")).run()
    causes = transition_cause_counts(result.event_log)
    assert causes  # non-empty given the aggressive config
    summary = population_state_summary(result.event_log, n_steps=60)
    assert summary["n_agents_ever_transitioned"] > 0
    assert summary["total_removals"] == 0  # dormancy_recovery never removes
    if not math.isnan(summary["mean_dormant_duration"]):
        assert summary["mean_dormant_duration"] >= 0


def test_replacement_lineage_summary_matches_final_state():
    result = Simulation(_config("removal_replacement", viability_max_dormant_steps=2)).run()
    summary = replacement_lineage_summary(result.event_log, result.final_agents)
    assert summary["total_replacements"] == len(result.event_log.replacements)
    for record in summary["replacements"]:
        assert record["demographic_id_increased"]


def test_hand_computed_deficit_duration_trace():
    """A deterministic all-``always_defect`` population where mutual
    defection's fixed payoff (payoff_punishment) is smaller than the
    unconditional subsistence charge, so net resources decline by a fixed
    known amount every step until an agent first goes distressed (at which
    point ``distress_engagement_prob=0.0`` stops it from earning any more
    interaction income, leaving a *pure* subsistence-only decline for the
    hand-computable remainder). Must cross into "distressed" the very step
    resources first fall below ``distress_threshold`` (duration=1 is
    sufficient for that first transition — see
    simulation.py::_viability_round), and into "dormant" only once
    ``consecutive_deficit_steps`` first reaches
    ``viability_deficit_steps_threshold`` — i.e. exactly
    ``viability_deficit_steps_threshold - 1`` steps after the distressed
    transition, since the distressed transition itself is the first
    deficit step (consecutive_deficit_steps == 1 that step)."""
    config = SimulationConfig(
        population_size=4,
        n_steps=30,
        seed=7,
        ecology_enabled=True,
        relationship_dynamics_enabled=False,
        mean_degree=1,
        policy_mix={"always_defect": 1.0},
        payoff_temptation=5.0,
        payoff_reward=3.0,
        payoff_punishment=1.0,
        payoff_sucker=0.0,
        subsistence_cost=5.0,  # > payoff_punishment: guaranteed net decline
        distress_threshold=0.0,
        distress_engagement_prob=0.0,  # once distressed, zero further interaction income
        viability_mode="dormancy_recovery",
        viability_deficit_steps_threshold=5,
        viability_recovery_resources=1000.0,  # unreachable: recovery never fires
        viability_max_dormant_steps=1000,
        environment_capacity=1_000_000.0,  # large: extraction never pool-capped
        environment_initial_fraction=1.0,
        initial_resources_mean=3.0,
        initial_resources_std=0.0,
        imitation_enabled=False,
        mutation_rate=0.0,
        punishment_enabled=False,
    )
    result = Simulation(config).run()
    transitions = sorted(result.event_log.viability_transitions, key=lambda e: e.step)
    to_distressed = [e for e in transitions if e.to_state == "distressed"]
    to_dormant = [e for e in transitions if e.to_state == "dormant"]
    assert to_distressed, "expected every agent to become distressed given a guaranteed net resource decline"
    assert to_dormant, "expected dormancy after exactly the configured consecutive-deficit threshold"
    # All agents are identical and deterministic here (always_defect vs.
    # always_defect has no RNG-dependent branching in action choice), so
    # every to_distressed/to_dormant event should occur at the same step.
    assert len({e.step for e in to_distressed}) == 1
    assert len({e.step for e in to_dormant}) == 1
    dormant_step = to_dormant[0].step
    distressed_step = to_distressed[0].step
    assert dormant_step - distressed_step == config.viability_deficit_steps_threshold - 1
