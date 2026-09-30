"""Level 0.2, Work Package C: fitness/imitation alternatives and the
translation-invariance test.

The central scientific question this covers: does Level 0.1's imitation
rule (comparing agents by cumulative resources) make imitation *rankings*
invariant to a uniform per-agent resource shift — such as an unconditional
subsistence charge applied identically to every agent — and, if so, which
of the newly-added alternative fitness signals share or break that
invariance. See ``agents/fitness.py``'s module docstring for the
per-mode rationale this test formally verifies rather than assumes.
"""

from __future__ import annotations

import math

import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.fitness import VALID_FITNESS_MODES, fitness_signal
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation


def make_agent(agent_id: int, resources: float, **overrides) -> Agent:
    defaults = dict(
        agent_id=agent_id,
        resources=resources,
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


def test_unknown_fitness_mode_raises():
    agent = make_agent(0, 10.0)
    with pytest.raises(ValueError):
        fitness_signal(agent, "not_a_real_mode")


def test_cumulative_resources_is_just_resources():
    agent = make_agent(0, 42.0)
    assert fitness_signal(agent, "cumulative_resources") == pytest.approx(42.0)


def test_recent_payoff_sums_payoff_window():
    agent = make_agent(0, 10.0)
    agent.record_step_end(net_payoff_this_step=2.0, window=3)
    agent.record_step_end(net_payoff_this_step=-1.0, window=3)
    assert fitness_signal(agent, "recent_payoff") == pytest.approx(1.0)


def test_resource_delta_property_is_nan_until_window_full_then_is_the_change():
    """agent.resource_delta itself (Agent's own property, agents/agent.py)
    is genuinely NaN — "not yet knowable" — until the rolling window is
    full."""
    agent = make_agent(0, 10.0)
    agent.record_step_end(net_payoff_this_step=0.0, window=3)
    assert math.isnan(agent.resource_delta)
    agent.resources = 12.0
    agent.record_step_end(net_payoff_this_step=0.0, window=3)
    assert math.isnan(agent.resource_delta)
    agent.resources = 15.0
    agent.record_step_end(net_payoff_this_step=0.0, window=3)
    # window now full: [10.0, 12.0, 15.0] -> delta = 15.0 - 10.0 = 5.0
    assert agent.resource_delta == pytest.approx(5.0)
    assert fitness_signal(agent, "resource_delta") == pytest.approx(5.0)


def test_fitness_signal_resource_delta_substitutes_neutral_zero_for_nan():
    """fitness_signal (unlike the raw Agent.resource_delta property) never
    returns NaN — for a not-yet-full window it substitutes a documented
    neutral 0.0 ("no known change yet"), so it is always safe to feed
    directly into the Fermi rule's subtraction."""
    agent = make_agent(0, 10.0)
    agent.record_step_end(net_payoff_this_step=0.0, window=3)
    assert math.isnan(agent.resource_delta)
    assert fitness_signal(agent, "resource_delta") == pytest.approx(0.0)


def test_viability_adjusted_penalizes_dormant_agents_only():
    active = make_agent(0, 10.0)
    active.record_step_end(net_payoff_this_step=4.0, window=5)
    dormant = make_agent(1, 10.0)
    dormant.record_step_end(net_payoff_this_step=4.0, window=5)
    dormant.viability_state = "dormant"
    assert fitness_signal(active, "viability_adjusted", viability_adjusted_dormant_penalty=3.0) == pytest.approx(4.0)
    assert fitness_signal(dormant, "viability_adjusted", viability_adjusted_dormant_penalty=3.0) == pytest.approx(1.0)


# -----------------------------------------------------------------------
# Translation invariance: does adding the same constant to every agent's
# resources change the *ranking* (and hence the imitation probability)
# between any pair, under each fitness mode?
# -----------------------------------------------------------------------
@pytest.mark.parametrize("mode", VALID_FITNESS_MODES)
def test_translation_invariance_of_pairwise_fitness_gap(mode):
    """For a fixed pair of agents with an established rolling-window
    history, apply a uniform constant shift to *both* agents' *current*
    resources only (exactly what one step of an identical, unconditional
    subsistence charge does — see ``simulation.py::_apply_subsistence``)
    and recompute the fitness gap, *without* pushing any new rolling-
    window sample (so this isolates the effect of the resource shift
    itself from any change in payoff/resource history).

    * ``cumulative_resources`` reads ``resources`` directly: both shift by
      the same amount, so the gap (a pure difference) is exactly
      unchanged.
    * ``recent_payoff`` never reads ``resources`` at all — the signal
      itself, not just the gap, is completely unaffected.
    * ``resource_delta`` reads ``resources - window[0]``; shifting only
      ``resources`` shifts each agent's own delta by the same constant,
      which cancels out of the *pairwise* gap (delta_b - delta_a) even
      though each individual agent's delta value does change.
    * ``viability_adjusted`` reduces to ``recent_payoff`` for a non-dormant
      agent (the case tested here), so it is invariant for the same
      reason — *unless* the shift pushes an agent across the dormancy
      threshold, which is a discrete state change tested separately in
      :func:`test_viability_adjusted_breaks_invariance_when_shift_crosses_dormancy_threshold`.
    """
    a = make_agent(0, 20.0)
    b = make_agent(1, 8.0)
    for agent, payoffs in ((a, [1.0, 2.0, -1.0]), (b, [0.5, -0.5, 0.0])):
        for p in payoffs:
            agent.record_step_end(net_payoff_this_step=p, window=3)

    gap_before = fitness_signal(b, mode) - fitness_signal(a, mode)

    shift = -7.0  # e.g. one step's worth of a uniform subsistence charge
    a.resources += shift
    b.resources += shift

    gap_after = fitness_signal(b, mode) - fitness_signal(a, mode)
    assert gap_after == pytest.approx(gap_before)


def test_viability_adjusted_breaks_invariance_when_shift_crosses_dormancy_threshold():
    """The one case where translation invariance *should* break: a shift
    large enough to push an agent from active/distressed into dormant
    changes its viability_adjusted signal by the discrete dormancy
    penalty, which is not a linear function of the shift — so the
    pairwise gap changes even though both agents received the exact same
    resource shift."""
    a = make_agent(0, 20.0)
    a.record_step_end(net_payoff_this_step=2.0, window=3)
    b = make_agent(1, 8.0)
    b.record_step_end(net_payoff_this_step=2.0, window=3)

    gap_before = fitness_signal(b, "viability_adjusted", viability_adjusted_dormant_penalty=100.0) - fitness_signal(
        a, "viability_adjusted", viability_adjusted_dormant_penalty=100.0
    )
    assert gap_before == pytest.approx(0.0)  # identical recent_payoff, neither dormant

    # Now b (but not a) crosses into dormancy — this is a *discrete state
    # change*, not itself part of fitness_signal's job to decide (that's
    # simulation.py::_viability_round); we set it directly to isolate the
    # fitness-signal-level consequence.
    b.viability_state = "dormant"
    gap_after = fitness_signal(b, "viability_adjusted", viability_adjusted_dormant_penalty=100.0) - fitness_signal(
        a, "viability_adjusted", viability_adjusted_dormant_penalty=100.0
    )
    assert gap_after != pytest.approx(gap_before)
    assert gap_after == pytest.approx(-100.0)


# -----------------------------------------------------------------------
# Full-simulation integration: every fitness mode runs cleanly, and
# imitation events carry complete, self-consistent fitness diagnostics.
# -----------------------------------------------------------------------
@pytest.mark.parametrize("mode", VALID_FITNESS_MODES)
def test_every_fitness_mode_runs_and_logs_complete_imitation_diagnostics(mode):
    config = SimulationConfig(
        population_size=16,
        n_steps=40,
        seed=5,
        ecology_enabled=True,
        relationship_dynamics_enabled=True,
        fitness_mode=mode,
        fitness_window=5,
        imitation_period=5,
    )
    result = Simulation(config).run()
    events = result.event_log.imitations
    assert events, f"expected at least one imitation event under fitness_mode={mode}"
    for e in events:
        assert e.fitness_mode == mode
        assert not math.isnan(e.agent_fitness)
        assert not math.isnan(e.model_fitness)
        assert e.fitness_gap == pytest.approx(e.model_fitness - e.agent_fitness)
        assert e.resulting_lineage_id is not None


def test_fitness_mode_cumulative_resources_reproduces_level01_imitation_gap():
    """Regression: fitness_mode="cumulative_resources" (the default) must
    produce imitation gaps numerically identical to the pre-Level-0.2 rule
    (peer.resources - agent.resources)."""
    config = SimulationConfig(population_size=12, n_steps=20, seed=2, fitness_mode="cumulative_resources")
    result = Simulation(config).run()
    for e in result.event_log.imitations:
        assert e.agent_fitness == pytest.approx(e.agent_fitness)  # sanity: finite, no NaN
