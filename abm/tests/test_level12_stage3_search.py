"""Level 1.2, Stage 3: main open evolutionary search -- parameter-draw sanity tests."""

from __future__ import annotations

import importlib
import inspect

from experiments import level12_stage3_search as stage3
from tests.test_level12_structural_guards import FORBIDDEN_LEVEL12_TERMS, _strip_docstrings_and_comments


class TestBuildParameterDraws:
    def test_deterministic_given_fixed_seed(self):
        a = stage3.build_parameter_draws()
        b = stage3.build_parameter_draws()
        assert a == b

    def test_returns_exactly_n_parameter_draws(self):
        draws = stage3.build_parameter_draws()
        assert len(draws) == stage3.N_PARAMETER_DRAWS

    def test_every_draw_within_its_own_declared_bounds(self):
        draws = stage3.build_parameter_draws()
        for draw in draws:
            for name, lo, hi in stage3.PARAMETER_SPACE:
                assert lo <= draw[name] <= hi, f"{name}={draw[name]} outside [{lo}, {hi}]"

    def test_every_declared_parameter_present_in_every_draw(self):
        draws = stage3.build_parameter_draws()
        expected_names = {name for name, _, _ in stage3.PARAMETER_SPACE}
        for draw in draws:
            assert set(draw.keys()) == expected_names

    def test_draws_are_not_all_identical_space_filling(self):
        draws = stage3.build_parameter_draws()
        # a genuine Latin Hypercube sample should not collapse every draw
        # to the same point -- a basic sanity check the sampler is doing
        # something, not a claim about coverage quality.
        migration_costs = {round(d["migration_cost"], 6) for d in draws}
        assert len(migration_costs) == len(draws)


class TestBuildConfig:
    def test_config_carries_rng_mode_mechanism_substreams(self):
        draws = stage3.build_parameter_draws()
        config = stage3._build_config(draws[0], draw_id=0, seed_idx=0)
        assert config.rng_mode == "mechanism_substreams"

    def test_config_seeds_never_collide_across_draws_or_seed_indices(self):
        seeds = set()
        for draw_id in range(3):
            for seed_idx in range(stage3.N_SEEDS_PER_DRAW):
                config = stage3._build_config({name: lo for name, lo, _ in stage3.PARAMETER_SPACE}, draw_id, seed_idx)
                assert config.seed not in seeds
                seeds.add(config.seed)

    def test_all_five_level12_mechanism_flags_enabled(self):
        draws = stage3.build_parameter_draws()
        config = stage3._build_config(draws[0], draw_id=0, seed_idx=0)
        assert config.institutional_observation_enabled is True
        assert config.institutional_transmission_enabled is True
        assert config.migration_enabled is True
        assert config.membership_exit_enabled is True
        assert config.institutional_scaling_enabled is True


class TestForbiddenTerminologyGuardExtendsToStage3Script:
    def test_stage3_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level12_stage3_search")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL12_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
