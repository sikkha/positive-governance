"""Work Package A: environment resource pool, extraction, regeneration,
carrying-capacity boundary, subsistence, and the distress/withhold survival
consequence."""

from __future__ import annotations

import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.environment.resource_pool import EnvironmentResourcePool
from abm_governance.simulation import Simulation


# -- EnvironmentResourcePool unit behaviour --------------------------------

def test_pool_rejects_invalid_construction():
    with pytest.raises(ValueError):
        EnvironmentResourcePool(capacity=0.0, regen_rate=0.5, resources=0.0)
    with pytest.raises(ValueError):
        EnvironmentResourcePool(capacity=100.0, regen_rate=-0.1, resources=0.0)
    with pytest.raises(ValueError):
        EnvironmentResourcePool(capacity=100.0, regen_rate=0.5, resources=150.0)  # exceeds capacity


def test_extraction_is_capped_by_available_resources():
    pool = EnvironmentResourcePool(capacity=100.0, regen_rate=0.0, resources=10.0)
    got = pool.extract(50.0)
    assert got == pytest.approx(10.0)
    assert pool.resources == pytest.approx(0.0)
    assert pool.total_extracted == pytest.approx(10.0)

    got_more = pool.extract(5.0)
    assert got_more == 0.0  # pool is empty
    assert pool.resources == 0.0


def test_extraction_of_nonpositive_amount_is_a_no_op():
    pool = EnvironmentResourcePool(capacity=100.0, regen_rate=0.0, resources=50.0)
    assert pool.extract(0.0) == 0.0
    assert pool.extract(-5.0) == 0.0
    assert pool.resources == 50.0


def test_regeneration_matches_hand_computed_logistic_step():
    # g(R, K) = r * R * (1 - R/K); R=50, K=200, r=0.5 -> g = 0.5*50*(1-0.25) = 18.75
    pool = EnvironmentResourcePool(capacity=200.0, regen_rate=0.5, resources=50.0)
    added = pool.regenerate()
    assert added == pytest.approx(18.75)
    assert pool.resources == pytest.approx(68.75)
    assert pool.total_regenerated == pytest.approx(18.75)


def test_regeneration_is_clipped_at_carrying_capacity():
    # Near K, growth would overshoot without clipping: R=190, K=200, r=2.0
    # -> g = 2.0*190*(1-0.95) = 19.0, unclamped R' = 209 > K
    pool = EnvironmentResourcePool(capacity=200.0, regen_rate=2.0, resources=190.0)
    pool.regenerate()
    assert pool.resources <= 200.0
    assert pool.resources == pytest.approx(200.0)


def test_regeneration_never_pushes_resources_below_zero():
    pool = EnvironmentResourcePool(capacity=200.0, regen_rate=0.0, resources=0.0)
    added = pool.regenerate()
    assert added == 0.0
    assert pool.resources == 0.0


def test_fraction_of_capacity_property():
    pool = EnvironmentResourcePool(capacity=200.0, regen_rate=0.1, resources=50.0)
    assert pool.fraction_of_capacity == pytest.approx(0.25)


# -- carrying-capacity boundary under a full simulation --------------------

def test_environment_resources_stay_within_bounds_across_a_run():
    config = SimulationConfig(population_size=30, n_steps=150, seed=3, ecology_enabled=True)
    result = Simulation(config).run()
    resources = [row["environment_resources"] for row in result.metrics]
    assert all(0.0 <= r <= config.environment_capacity for r in resources)
    assert result.final_environment_pool is not None
    assert 0.0 <= result.final_environment_pool.resources <= config.environment_capacity


def test_ecology_disabled_reports_nan_environment_columns():
    config = SimulationConfig.level0_compat(population_size=20, n_steps=10, seed=0)
    result = Simulation(config).run()
    assert result.final_environment_pool is None
    for row in result.metrics:
        assert row["environment_resources"] != row["environment_resources"]  # NaN != NaN


# -- subsistence -------------------------------------------------------------

def test_subsistence_charges_every_agent_uniformly_every_step():
    config = SimulationConfig(population_size=10, n_steps=5, seed=0, ecology_enabled=True, subsistence_cost=0.7)
    result = Simulation(config).run()
    for event in result.event_log.subsistence:
        assert event.per_agent_cost == pytest.approx(0.7)
        assert event.n_agents_charged == 10
        assert event.total_cost == pytest.approx(7.0)
    assert len(result.event_log.subsistence) == 5  # one per step


def test_zero_subsistence_cost_emits_no_events():
    config = SimulationConfig(population_size=10, n_steps=5, seed=0, ecology_enabled=True, subsistence_cost=0.0)
    result = Simulation(config).run()
    assert result.event_log.subsistence == []


def test_subsistence_not_charged_when_ecology_disabled():
    config = SimulationConfig.level0_compat(population_size=10, n_steps=5, seed=0)
    result = Simulation(config).run()
    assert result.event_log.subsistence == []


# -- distress / withhold survival consequence -------------------------------

def test_distressed_agents_can_withhold_from_interactions():
    # Force distress: threshold above any plausible starting resources.
    config = SimulationConfig(
        population_size=20,
        n_steps=10,
        seed=0,
        ecology_enabled=True,
        distress_threshold=1e9,
        distress_engagement_prob=0.0,  # never engage while distressed
        subsistence_cost=0.0,
    )
    result = Simulation(config).run()
    assert len(result.event_log.withholds) > 0
    # With distress_engagement_prob=0.0 and everyone always distressed, no
    # interaction should have been able to occur at all.
    assert len(result.event_log.interactions) == 0


def test_non_distressed_agents_never_withhold():
    config = SimulationConfig(
        population_size=20,
        n_steps=10,
        seed=0,
        ecology_enabled=True,
        distress_threshold=-1e9,  # nobody is ever distressed
    )
    result = Simulation(config).run()
    assert result.event_log.withholds == []


def test_withholding_disabled_when_ecology_disabled_even_with_low_resources():
    # In compat mode, distress logic must never engage — no extra RNG
    # draws, no withhold events — regardless of resource levels.
    config = SimulationConfig.level0_compat(population_size=20, n_steps=10, seed=0)
    result = Simulation(config).run()
    assert result.event_log.withholds == []
