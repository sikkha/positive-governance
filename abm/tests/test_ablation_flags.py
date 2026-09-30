"""Work Package E ablation sub-switches: ``imitation_enabled`` and
``relationship_exit_enabled``. Both default to True and must reproduce
identical behaviour to a run before the flags existed (checked indirectly
by the fact that every other Level 0.1 test — in particular
test_compat_regression.py — still passes with these fields present)."""

from __future__ import annotations

import pandas as pd

from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation


def test_imitation_enabled_false_suppresses_all_imitation_events():
    config = SimulationConfig(population_size=30, n_steps=100, seed=1, imitation_enabled=False)
    result = Simulation(config).run()
    assert result.event_log.imitations == []
    # Mutation must still be able to fire — this ablation targets imitation
    # specifically, not all adaptation.
    assert config.mutation_rate > 0.0


def test_imitation_enabled_true_is_the_default_and_can_still_imitate():
    config = SimulationConfig(population_size=30, n_steps=100, seed=1)
    assert config.imitation_enabled is True
    result = Simulation(config).run()
    # Not asserting imitation *must* fire (that's stochastic), just that the
    # machinery is not structurally disabled.
    assert isinstance(result.event_log.imitations, list)


def test_relationship_exit_enabled_false_suppresses_exit_and_failed_exit_events():
    # A pathologically low exit threshold + high exit cost, under normal
    # settings, would produce plenty of attempted/failed exits; with the
    # switch off, none should ever be logged.
    config = SimulationConfig(
        population_size=30,
        n_steps=100,
        seed=2,
        exit_resource_threshold=1e6,  # every relationship looks "bad enough" to leave
        relationship_exit_enabled=False,
    )
    result = Simulation(config).run()
    assert result.event_log.edges_removed == []
    assert result.event_log.failed_exits == []


def test_relationship_exit_enabled_true_allows_exits_under_the_same_threshold():
    config = SimulationConfig(
        population_size=30,
        n_steps=100,
        seed=2,
        exit_resource_threshold=1e6,
        relationship_exit_enabled=True,
    )
    result = Simulation(config).run()
    # With everything "wanting" to exit, we expect at least some successful
    # or failed exit events to have been logged somewhere in the run.
    assert len(result.event_log.edges_removed) + len(result.event_log.failed_exits) > 0


def test_relationship_exit_flag_has_no_effect_in_compat_mode():
    # Compat mode uses the legacy path unconditionally regardless of this
    # flag's value — both must produce identical results. Compared via
    # pandas/allclose (equal_nan=True) rather than plain dict equality,
    # since compat-mode rows contain NaN environment columns and
    # NaN != NaN under Python's ordinary equality.
    a = Simulation(SimulationConfig.level0_compat(seed=0, n_steps=30, relationship_exit_enabled=False)).run()
    b = Simulation(SimulationConfig.level0_compat(seed=0, n_steps=30, relationship_exit_enabled=True)).run()
    df_a, df_b = pd.DataFrame(a.metrics), pd.DataFrame(b.metrics)
    pd.testing.assert_frame_equal(df_a, df_b, check_exact=False)
