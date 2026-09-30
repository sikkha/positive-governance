"""Population and resource-accounting invariants that must hold for any run,
regardless of parameters — the kind of check that catches a silent
resource-leak or double-count bug that per-function unit tests would miss."""

from __future__ import annotations

import pytest

from abm_governance.agents.agent import FORBIDDEN_ATTRIBUTE_SUBSTRINGS, Agent
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation


def _run(seed: int, punishment_enabled: bool, n_steps: int = 60) -> Simulation:
    """Level-0 compatibility-mode run. As of Level 0.1, ``SimulationConfig()``
    defaults to ecology + relationship-dynamics enabled, which changes the
    resource ledger identity (see
    ``test_ecological_resource_accounting_identity_holds_exactly`` below).
    This helper explicitly requests the compatibility mode so the original
    Level-0 ledger identity below continues to mean what it says."""
    config = SimulationConfig.level0_compat(
        population_size=30,
        n_steps=n_steps,
        seed=seed,
        punishment_enabled=punishment_enabled,
        imitation_period=7,
        rewiring_period=4,
        exit_resource_threshold=-0.5,  # aggressive, to exercise exit/rewiring paths
    )
    return Simulation(config)


def _run_level01(seed: int, punishment_enabled: bool, n_steps: int = 60) -> Simulation:
    """Level-0.1 run with ecology and relationship dynamics both active —
    the new default configuration."""
    config = SimulationConfig(
        population_size=30,
        n_steps=n_steps,
        seed=seed,
        punishment_enabled=punishment_enabled,
        imitation_period=7,
        rewiring_period=4,
        exit_resource_threshold=-0.5,
        ecology_enabled=True,
        relationship_dynamics_enabled=True,
    )
    return Simulation(config)


@pytest.mark.parametrize("seed", [0, 1, 2])
@pytest.mark.parametrize("punishment_enabled", [True, False])
def test_population_size_is_constant_across_the_run(seed, punishment_enabled):
    sim = _run(seed, punishment_enabled)
    result = sim.run()
    assert len(result.final_agents) == sim.config.population_size
    assert all(a.alive for a in result.final_agents)  # Level 0 has no death


@pytest.mark.parametrize("seed", [0, 1, 2])
@pytest.mark.parametrize("punishment_enabled", [True, False])
def test_resource_accounting_identity_holds_exactly(seed, punishment_enabled):
    """final_total = initial_total + sum(interaction payoffs)
                                    - sum(punishment costs + penalties)
                                    - sum(exit costs)
    This must hold to floating-point tolerance for every run: it is the
    ledger identity that guarantees no resources are silently created or
    destroyed outside of the accounted mechanisms.
    """
    sim = _run(seed, punishment_enabled)
    result = sim.run()

    payoff_total = sum(e.payoff_a + e.payoff_b for e in result.event_log.interactions)
    punishment_total = sum(
        e.cost_to_punisher + e.penalty_to_target for e in result.event_log.punishments
    )
    exit_total = sum(e.exit_cost for e in result.event_log.exits)

    expected_final = result.initial_total_resources + payoff_total - punishment_total - exit_total
    actual_final = sum(a.resources for a in result.final_agents)

    assert actual_final == pytest.approx(expected_final, rel=1e-9, abs=1e-6)

    if not punishment_enabled:
        assert len(result.event_log.punishments) == 0


@pytest.mark.parametrize("seed", [0, 1, 2])
@pytest.mark.parametrize("punishment_enabled", [True, False])
def test_ecological_resource_accounting_identity_holds_exactly(seed, punishment_enabled):
    """Level 0.1 ledger identity, extending the Level-0 one above with the
    new named sinks: subsistence and (Work-Package-B) search cost, plus
    the Work-Package-B edge-removal family of exit costs. Interaction
    payoffs in the event log are already extraction-capped by the
    environment pool (see environment/resource_pool.py), so no separate
    "extraction" term is needed here — the pool's own internal ledger is
    checked independently in test_environment.py.
    """
    sim = _run_level01(seed, punishment_enabled)
    result = sim.run()

    payoff_total = sum(e.payoff_a + e.payoff_b for e in result.event_log.interactions)
    punishment_total = sum(e.cost_to_punisher + e.penalty_to_target for e in result.event_log.punishments)
    exit_total = sum(e.exit_cost for e in result.event_log.exits)  # legacy family: empty in this mode
    exit_total += sum(e.exit_cost for e in result.event_log.edges_removed)
    subsistence_total = sum(e.total_cost for e in result.event_log.subsistence)
    search_total = sum(
        1 for e in result.event_log.connection_proposals if e.reason != "no_candidate"
    ) * sim.config.search_cost

    expected_final = (
        result.initial_total_resources
        + payoff_total
        - punishment_total
        - exit_total
        - subsistence_total
        - search_total
    )
    actual_final = sum(a.resources for a in result.final_agents)

    assert actual_final == pytest.approx(expected_final, rel=1e-9, abs=1e-6)
    assert len(result.event_log.exits) == 0  # legacy family must be silent in this mode
    assert len(result.event_log.rewires) == 0


def test_no_agent_ever_holds_a_forbidden_attribute_name():
    """Structural guard against reintroducing governance-normative concepts
    into the generative layer (dev_mem/project_vision.md, section 5)."""
    agent = Agent(
        agent_id=0,
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
    for name in vars(agent):
        lowered = name.lower()
        assert not any(bad in lowered for bad in FORBIDDEN_ATTRIBUTE_SUBSTRINGS), name


def test_agent_construction_rejects_forbidden_attribute_injection():
    import dataclasses

    from abm_governance.agents import agent as agent_module

    # Simulate what would happen if a future edit added a forbidden field,
    # by monkeypatching a subclass with one, and confirming construction
    # is refused rather than silently allowed.
    @dataclasses.dataclass
    class _BadAgent(agent_module.Agent):
        legitimacy_score: float = 0.0

    with pytest.raises(ValueError):
        _BadAgent(
            agent_id=0,
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


@pytest.mark.parametrize("seed", [0, 1])
def test_all_metrics_rows_reference_consistent_population_size(seed):
    sim = _run(seed, punishment_enabled=True, n_steps=20)
    result = sim.run()
    sizes = {row["population_size"] for row in result.metrics}
    assert sizes == {sim.config.population_size}
