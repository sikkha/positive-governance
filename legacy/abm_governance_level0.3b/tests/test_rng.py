"""Seed reproducibility: same seed -> identical run; different seed -> divergent run."""

from __future__ import annotations

from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation


def _run(seed: int, steps: int = 40, population: int = 24) -> list[dict]:
    config = SimulationConfig(population_size=population, n_steps=steps, seed=seed)
    return Simulation(config).run().metrics


def test_same_seed_is_bit_for_bit_identical():
    metrics_a = _run(seed=7)
    metrics_b = _run(seed=7)
    assert metrics_a == metrics_b


def test_same_seed_identical_across_multiple_repeats():
    reference = _run(seed=3)
    for _ in range(3):
        assert _run(seed=3) == reference


def test_different_seeds_diverge():
    metrics_a = _run(seed=1)
    metrics_b = _run(seed=2)
    assert metrics_a != metrics_b
    # cooperation_rate trajectories should differ at least somewhere
    coop_a = [m["cooperation_rate"] for m in metrics_a]
    coop_b = [m["cooperation_rate"] for m in metrics_b]
    assert coop_a != coop_b


def test_rng_seed_validation():
    from abm_governance.core.rng import make_rng
    import pytest

    with pytest.raises(ValueError):
        make_rng(-1)
