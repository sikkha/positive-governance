"""Level 1.3, task #105 (test requirements sweep): cross-stage
``rng_mode="mechanism_substreams"`` compliance.

Directly motivated by task #109's own bug: Stage 0/1/3/4/5's first
drafts all silently left at least one config construction path at
``SimulationConfig``'s own class default (``legacy_single_stream``),
violating the frozen preregistration manifest's own ``RNG_COMMITMENTS``
("mandatory for every Stage 0-9 run; legacy_single_stream is never
used this milestone"). Every stage was fixed and re-verified at the
time (see ``dev_mem/status_update.md``'s task #109 entry), but nothing
previously stood as a standing REGRESSION guard against the same class
of omission creeping back in on a future edit. This file is that
guard: one test per stage script that actually constructs a
``SimulationConfig``, asserting ``rng_mode == "mechanism_substreams"``
on the config it actually builds (not merely a source-text check),
wherever the stage's own API exposes a config-building function to call
directly."""

from __future__ import annotations

from experiments import (
    level13_common,
    level13_stage1_activation as stage1,
    level13_stage3_sequencing_entrenchment_factorial as stage3,
    level13_stage4_open_pressure_history_search as stage4,
    level13_stage5_causal_counterfactuals as stage5,
    level13_stage9_scale_and_shock_robustness as stage9,
)
from abm_governance.core.config import SimulationConfig


class TestStage0RngModeCompliance:
    """Stage 0's own config construction is inlined per-comparison
    inside ``run_stage0`` rather than factored into a standalone
    helper (unlike every other stage) -- a source-text presence check
    is this stage's own honest substitute for a live-config check."""

    def test_mechanism_substreams_literal_present_in_source(self):
        import inspect

        from experiments import level13_stage0_exact_compatibility as stage0
        source = inspect.getsource(stage0)
        assert 'rng_mode="mechanism_substreams"' in source


class TestStage1RngModeCompliance:
    def test_base_dict_sets_mechanism_substreams(self):
        assert stage1._BASE["rng_mode"] == "mechanism_substreams"

    def test_constructed_config_actually_has_it(self):
        config = SimulationConfig.level1_rule_formation_default(
            seed=1, **stage1._BASE, **stage1.CONDITIONS["level13_baseline"],
        )
        assert config.rng_mode == "mechanism_substreams"


class TestStage2RngModeCompliance:
    """Stage 2's own throwaway configs are built via
    ``level12b_frozen_reference()`` (never overridden), which sets
    ``mechanism_substreams`` internally -- inherited compliance, not an
    explicit override, but still worth a direct check since this is
    exactly the kind of implicit assumption task #109's own bug showed
    can silently stop holding after a refactor."""

    def test_ecological_design_configs_are_compliant(self):
        design = level13_common.build_ecological_feasibility_design(n_points=2, seed=1, n_steps=10)
        assert design["n_points"] == 2  # smoke: the call itself must not raise.
        cfg = SimulationConfig.level12b_frozen_reference(population_size=8, n_patches=2, n_steps=5, seed=1)
        assert cfg.rng_mode == "mechanism_substreams"


class TestStage3RngModeCompliance:
    def test_build_config_sets_mechanism_substreams(self):
        order_name = next(iter(stage3.ORDERINGS))
        config = stage3._build_config(order_name, entrenchment_enabled=False, seed=1)
        assert config.rng_mode == "mechanism_substreams"


class TestStage4RngModeCompliance:
    def test_build_config_sets_mechanism_substreams(self):
        draws = stage4.lhs_draws(n=1, seed=1)
        config = stage4._build_config(draws[0], seed=1)
        assert config.rng_mode == "mechanism_substreams"


class TestStage5RngModeCompliance:
    def test_base_config_sets_mechanism_substreams(self):
        config = stage5._base_config(1)
        assert config.rng_mode == "mechanism_substreams"


class TestStage7RngModeCompliance:
    """Stage 7 constructs no config of its own -- it calls Stage 4's
    own ``_build_config``/``_run_one`` verbatim (see its module
    docstring), so ``TestStage4RngModeCompliance`` above already
    covers it; documented here rather than silently uncovered."""


class TestStage9RngModeCompliance:
    def test_build_config_sets_mechanism_substreams(self):
        config = stage9._build_config(40, 3, seed=1)
        assert config.rng_mode == "mechanism_substreams"
