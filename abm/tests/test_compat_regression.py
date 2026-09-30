"""Compatibility-mode regression test: a Level-0.1 run in
``SimulationConfig.level0_compat()`` mode must reproduce the pre-Level-0.1
saved baseline (``outputs/level0_default/metrics.csv``, generated and
committed before any Level 0.1 code existed) exactly, on every column that
still exists. New Level 0.1 columns are expected to be present in addition
— only the original columns are required to match.

This is the concrete, automated form of the milestone's "reproduce the
existing 500-step seed-0 run before changing the model" and
"compatibility-mode regression" requirements.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.core.export import export_results
from abm_governance.simulation import Simulation

_BASELINE_CSV = os.path.join(os.path.dirname(__file__), "..", "outputs", "level0_default", "metrics.csv")

_ORIGINAL_COLUMNS = [
    "step",
    "population_size",
    "cooperation_rate",
    "defection_rate",
    "punishment_frequency",
    "erroneous_punishment_rate",
    "mean_resources",
    "resource_gini",
    "network_density",
    "network_clustering",
    "mean_degree",
    "relationship_count",
    "mean_relationship_age",
    "policy_diversity_bits",
    "exit_count",
    "rewire_count",
    "imitation_count",
    "mutation_count",
]


@pytest.mark.skipif(not os.path.exists(_BASELINE_CSV), reason="baseline snapshot not present in this checkout")
def test_compat_mode_reproduces_saved_level0_baseline_exactly(tmp_path):
    baseline = pd.read_csv(_BASELINE_CSV)

    config = SimulationConfig.level0_compat(seed=0, n_steps=500)
    result = Simulation(config).run()
    export_results(result, str(tmp_path))
    reproduced = pd.read_csv(tmp_path / "metrics.csv")

    assert list(reproduced["step"]) == list(baseline["step"])
    for col in _ORIGINAL_COLUMNS:
        assert col in reproduced.columns, f"compat-mode output lost original column {col!r}"
        assert np.allclose(
            baseline[col].to_numpy(dtype=float), reproduced[col].to_numpy(dtype=float), equal_nan=True
        ), f"column {col!r} diverged from the saved Level-0 baseline under compat mode"


@pytest.mark.skipif(not os.path.exists(_BASELINE_CSV), reason="baseline snapshot not present in this checkout")
def test_compat_mode_adds_new_columns_without_removing_old_ones():
    baseline = pd.read_csv(_BASELINE_CSV)
    config = SimulationConfig.level0_compat(seed=0, n_steps=20)
    result = Simulation(config).run()
    reproduced = pd.DataFrame(result.metrics)
    assert set(_ORIGINAL_COLUMNS).issubset(set(reproduced.columns))
    assert set(reproduced.columns) - set(baseline.columns), "expected Level 0.1 to add new columns"


def test_default_config_is_no_longer_compat_mode():
    """Sanity check that the default config actually exercises Level 0.1
    (this test would be vacuous if someone accidentally reverted the
    defaults back to compat mode)."""
    config = SimulationConfig()
    assert config.ecology_enabled is True
    assert config.relationship_dynamics_enabled is True
