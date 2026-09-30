"""Level 0.2, Work Package D: ecological balance indicator and region
labels, plus an integration check that a full simulation run's metrics
series feeds cleanly into ``run_balance_summary``."""

from __future__ import annotations

import math

import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.ecological_balance import (
    ecological_region_label,
    run_balance_summary,
    step_balance_indicators,
)
from abm_governance.simulation import Simulation


def test_step_balance_indicators_hand_computed():
    row = {
        "realized_regeneration": 10.0,
        "max_sustainable_regeneration": 25.0,
        "potential_extraction_demand": 20.0,
    }
    b = step_balance_indicators(row)
    assert b["b_t_realized"] == pytest.approx(0.5)
    assert b["b_t_structural"] == pytest.approx(1.25)


def test_step_balance_indicators_nan_for_zero_demand():
    row = {"realized_regeneration": 5.0, "max_sustainable_regeneration": 5.0, "potential_extraction_demand": 0.0}
    b = step_balance_indicators(row)
    assert math.isnan(b["b_t_realized"])
    assert math.isnan(b["b_t_structural"])


@pytest.mark.parametrize(
    "occupancy,b_t,expected",
    [
        (0.01, 5.0, "depleted"),  # occupancy takes precedence even with high B_t
        (0.5, 2.0, "supply_dominant"),
        (0.5, 0.1, "demand_dominant"),
        (0.5, 1.0, "boundary"),
        (float("nan"), 1.0, "unknown"),
    ],
)
def test_ecological_region_label_cases(occupancy, b_t, expected):
    assert ecological_region_label(occupancy, b_t) == expected


def test_run_balance_summary_on_synthetic_series():
    rows = [
        {
            "step": i,
            "environment_fraction_of_capacity": 0.0 if i < 5 else 0.8,
            "realized_regeneration": 0.0 if i < 5 else 4.0,
            "max_sustainable_regeneration": 10.0,
            "potential_extraction_demand": 5.0,
        }
        for i in range(10)
    ]
    summary = run_balance_summary(rows)
    assert summary["n_steps"] == 10
    assert summary["fraction_time_depleted"] == pytest.approx(0.5)
    assert summary["pool_persistence"] == pytest.approx(0.5)
    assert len(summary["region_labels"]) == 10
    assert summary["region_labels"][0] == "depleted"
    assert summary["region_labels"][-1] in ("supply_dominant", "boundary", "demand_dominant")


def test_run_balance_summary_integrates_with_real_simulation_output():
    config = SimulationConfig(population_size=12, n_steps=25, seed=1, ecology_enabled=True)
    result = Simulation(config).run()
    summary = run_balance_summary(result.metrics)
    assert summary["n_steps"] == 25
    assert 0.0 <= summary["pool_persistence"] <= 1.0 or math.isnan(summary["pool_persistence"])


def test_ecology_disabled_yields_unknown_labels_and_nan_summary():
    config = SimulationConfig.level0_compat(population_size=10, n_steps=10, seed=1)
    result = Simulation(config).run()
    summary = run_balance_summary(result.metrics)
    assert all(lbl == "unknown" for lbl in summary["region_labels"])
    assert math.isnan(summary["mean_occupancy"])
