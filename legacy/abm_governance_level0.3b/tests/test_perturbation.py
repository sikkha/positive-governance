"""Work Package G: the generic perturbation interface — scheduling,
instantaneous vs. continuous effects, and boundary events."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import PerturbationEvent
from abm_governance.core.perturbation import (
    PerturbationSpec,
    apply_instantaneous_effects,
    boundary_events,
    effective_observation_accuracy,
    effective_regen_rate,
    effective_subsistence_cost,
    specs_from_config,
)
from abm_governance.environment.resource_pool import EnvironmentResourcePool
from abm_governance.simulation import Simulation


def test_perturbation_spec_is_active_only_within_window():
    spec = PerturbationSpec(start_step=10, duration=5, kind="observation_noise_increase", magnitude=0.2)
    assert spec.end_step == 15
    assert not spec.is_active(9)
    assert spec.is_active(10)
    assert spec.is_active(14)
    assert not spec.is_active(15)


def test_specs_from_config_round_trips_dicts():
    perturbations = ({"start_step": 5, "duration": 3, "kind": "resource_depletion", "magnitude": 0.5},)
    specs = specs_from_config(perturbations)
    assert len(specs) == 1
    assert specs[0].start_step == 5
    assert specs[0].kind == "resource_depletion"


def test_resource_depletion_removes_exact_fraction_once():
    pool = EnvironmentResourcePool(capacity=1000.0, regen_rate=0.0, resources=400.0)
    spec = PerturbationSpec(start_step=3, duration=2, kind="resource_depletion", magnitude=0.25)
    rng = np.random.default_rng(0)

    apply_instantaneous_effects(spec, step=2, pool=pool, rng=rng)  # before window: no effect
    assert pool.resources == pytest.approx(400.0)

    apply_instantaneous_effects(spec, step=3, pool=pool, rng=rng)  # exactly at start_step
    assert pool.resources == pytest.approx(300.0)  # removed 25% of 400

    apply_instantaneous_effects(spec, step=4, pool=pool, rng=rng)  # later steps: no further effect
    assert pool.resources == pytest.approx(300.0)


def test_observation_noise_increase_has_no_instantaneous_pool_effect():
    pool = EnvironmentResourcePool(capacity=1000.0, regen_rate=0.0, resources=400.0)
    spec = PerturbationSpec(start_step=0, duration=5, kind="observation_noise_increase", magnitude=0.3)
    rng = np.random.default_rng(0)
    apply_instantaneous_effects(spec, step=0, pool=pool, rng=rng)
    assert pool.resources == pytest.approx(400.0)  # unaffected


def test_effective_observation_accuracy_reduced_while_active_and_floored_at_zero():
    spec = PerturbationSpec(start_step=0, duration=5, kind="observation_noise_increase", magnitude=0.3)
    assert effective_observation_accuracy(0.9, [spec]) == pytest.approx(0.6)
    assert effective_observation_accuracy(0.9, []) == pytest.approx(0.9)
    big_spec = PerturbationSpec(start_step=0, duration=5, kind="observation_noise_increase", magnitude=1.0)
    assert effective_observation_accuracy(0.2, [big_spec]) == pytest.approx(0.0)  # floored, not negative


def test_boundary_events_start_and_end_markers():
    specs = [PerturbationSpec(start_step=5, duration=3, kind="resource_depletion", magnitude=0.5)]
    start_events = boundary_events(specs, step=5, n_steps=100)
    assert len(start_events) == 1
    assert start_events[0].phase == "start"

    mid_events = boundary_events(specs, step=6, n_steps=100)
    assert mid_events == []

    end_events = boundary_events(specs, step=8, n_steps=100)  # end_step = 5+3 = 8
    assert len(end_events) == 1
    assert end_events[0].phase == "end"

    # end marker suppressed if it would fall outside the run
    late_events = boundary_events(specs, step=8, n_steps=8)
    assert late_events == []


def test_config_validates_perturbation_specs():
    with pytest.raises(ValueError):
        SimulationConfig(perturbations=({"start_step": -1, "duration": 1, "kind": "resource_depletion", "magnitude": 0.5},))
    with pytest.raises(ValueError):
        SimulationConfig(perturbations=({"start_step": 0, "duration": 0, "kind": "resource_depletion", "magnitude": 0.5},))
    with pytest.raises(ValueError):
        SimulationConfig(perturbations=({"start_step": 0, "duration": 1, "kind": "not_a_real_kind", "magnitude": 0.5},))
    with pytest.raises(ValueError):
        SimulationConfig(perturbations=({"start_step": 0, "duration": 1, "kind": "resource_depletion", "magnitude": 1.5},))
    with pytest.raises(ValueError):
        SimulationConfig(perturbations=({"start_step": 0, "duration": 1},))  # missing keys


def test_no_perturbations_by_default():
    config = SimulationConfig()
    assert config.perturbations == ()


# -- full-simulation scheduling ------------------------------------------

def test_perturbation_scheduling_in_a_full_run():
    config = SimulationConfig(
        population_size=20,
        n_steps=40,
        seed=0,
        ecology_enabled=True,
        perturbations=({"start_step": 10, "duration": 5, "kind": "resource_depletion", "magnitude": 0.5},),
    )
    result = Simulation(config).run()
    starts = [e for e in result.event_log.perturbations if e.phase == "start"]
    ends = [e for e in result.event_log.perturbations if e.phase == "end"]
    assert len(starts) == 1 and starts[0].step == 10
    assert len(ends) == 1 and ends[0].step == 15

    pool_before = result.metrics[9]["environment_resources"]
    pool_after = result.metrics[10]["environment_resources"]
    # The depletion should show up as a sharp drop between step 9 and 10
    # (allowing for the same step's ordinary extraction/regen too).
    assert pool_after < pool_before


def test_unperturbed_run_emits_no_perturbation_events():
    config = SimulationConfig(population_size=15, n_steps=20, seed=0)
    result = Simulation(config).run()
    assert result.event_log.perturbations == []


def test_perturbation_does_not_change_rng_draws_when_absent_vs_empty_tuple():
    # Belt-and-braces regression: explicitly empty perturbations tuple must
    # behave identically to the default.
    a = Simulation(SimulationConfig(population_size=15, n_steps=20, seed=0, perturbations=())).run()
    b = Simulation(SimulationConfig(population_size=15, n_steps=20, seed=0)).run()
    assert a.metrics == b.metrics


# -- Level 0.2, Work Package J: new shock kinds ---------------------------

def test_effective_subsistence_cost_scales_up_only_while_active():
    spec = PerturbationSpec(start_step=5, duration=3, kind="subsistence_increase", magnitude=0.5)
    assert effective_subsistence_cost(2.0, [spec]) == pytest.approx(3.0)  # +50%
    assert effective_subsistence_cost(2.0, []) == pytest.approx(2.0)


def test_effective_regen_rate_scales_down_and_floors_at_zero():
    spec = PerturbationSpec(start_step=5, duration=3, kind="regeneration_reduction", magnitude=0.8)
    assert effective_regen_rate(0.5, [spec]) == pytest.approx(0.1)  # 20% of base
    oversized = PerturbationSpec(start_step=5, duration=3, kind="regeneration_reduction", magnitude=1.5)
    assert effective_regen_rate(0.5, [oversized]) == pytest.approx(0.0)  # floored, never negative
    assert effective_regen_rate(0.5, []) == pytest.approx(0.5)


def test_subsistence_increase_perturbation_in_a_full_run_raises_charged_cost():
    config = SimulationConfig(
        population_size=20,
        n_steps=20,
        seed=0,
        ecology_enabled=True,
        subsistence_cost=1.0,
        perturbations=({"start_step": 5, "duration": 3, "kind": "subsistence_increase", "magnitude": 1.0},),
    )
    result = Simulation(config).run()
    subsistence_by_step = {e.step: e.per_agent_cost for e in result.event_log.subsistence}
    assert subsistence_by_step[4] == pytest.approx(1.0)
    assert subsistence_by_step[5] == pytest.approx(2.0)  # +100% while active
    assert subsistence_by_step[7] == pytest.approx(2.0)  # still within [5, 8)
    assert subsistence_by_step[8] == pytest.approx(1.0)  # back to baseline


def test_regeneration_reduction_perturbation_leaves_pool_regen_rate_unchanged_after():
    config = SimulationConfig(
        population_size=20,
        n_steps=20,
        seed=0,
        ecology_enabled=True,
        environment_regen_rate=0.5,
        perturbations=({"start_step": 5, "duration": 3, "kind": "regeneration_reduction", "magnitude": 0.9},),
    )
    sim = Simulation(config)
    sim.run()
    # The temporary per-call mutation must be restored, not left dangling.
    assert sim.pool.regen_rate == pytest.approx(0.5)
