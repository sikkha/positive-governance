"""Level 1.2, Stages 6-7: scaling robustness + perturbation/transition -- structural tests."""

from __future__ import annotations

import importlib
import inspect

import pytest

from experiments import level12_stage6_scaling_robustness as stage6
from experiments import level12_stage7_perturbation as stage7
from tests.test_level12_structural_guards import FORBIDDEN_LEVEL12_TERMS, _strip_docstrings_and_comments


class TestStage6ConfigBuilder:
    def test_seeds_never_collide_across_conditions(self):
        seeds = set()
        for condition_id in range(4):
            for seed_idx in range(stage6.N_SEEDS_PER_CONDITION):
                config = stage6._build_config(40, 3, seed_idx, condition_id)
                assert config.seed not in seeds
                seeds.add(config.seed)

    def test_config_carries_requested_population_and_patches(self):
        config = stage6._build_config(80, 6, 0, 0)
        assert config.population_size == 80
        assert config.n_patches == 6

    def test_all_five_mechanism_flags_enabled(self):
        config = stage6._build_config(40, 3, 0, 0)
        assert config.institutional_observation_enabled is True
        assert config.institutional_transmission_enabled is True
        assert config.migration_enabled is True
        assert config.membership_exit_enabled is True
        assert config.institutional_scaling_enabled is True


class TestStage7ConfigBuilder:
    def test_shocked_config_carries_one_perturbation_spec(self):
        config = stage7._build_config("observation_noise_increase", 0, 0, with_shock=True)
        assert len(config.perturbations) == 1
        assert config.perturbations[0]["kind"] == "observation_noise_increase"

    def test_unshocked_config_carries_no_perturbations(self):
        config = stage7._build_config("observation_noise_increase", 0, 0, with_shock=False)
        assert config.perturbations == ()

    def test_shocked_and_unshocked_share_the_same_seed(self):
        # Isolating the shock's own effect requires holding the seed
        # fixed between the shocked/unshocked pair -- only
        # ``with_shock`` may differ.
        shocked = stage7._build_config("subsistence_increase", 1, 0, with_shock=True)
        unshocked = stage7._build_config("subsistence_increase", 1, 0, with_shock=False)
        assert shocked.seed == unshocked.seed

    def test_both_perturbation_types_are_not_pool_gated_no_ops(self):
        # Documented, load-bearing assumption of this stage: resource_
        # depletion/regeneration_reduction are pool-only no-ops under
        # ecology_topology="patches" (always true for Level 1.2), so
        # this stage must use the other two kinds specifically.
        assert set(stage7.PERTURBATION_TYPES) == {"observation_noise_increase", "subsistence_increase"}
        assert "resource_depletion" not in stage7.PERTURBATION_TYPES
        assert "regeneration_reduction" not in stage7.PERTURBATION_TYPES


@pytest.mark.parametrize("module_name", ["experiments.level12_stage6_scaling_robustness", "experiments.level12_stage7_perturbation"])
class TestForbiddenTerminologyGuardExtendsToStage6And7Scripts:
    def test_module_free_of_forbidden_terms(self, module_name):
        module = importlib.import_module(module_name)
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL12_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
