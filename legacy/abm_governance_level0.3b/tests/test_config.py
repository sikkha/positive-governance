"""Configuration validation: bad configs must fail loudly, never silently clamp."""

from __future__ import annotations

import dataclasses

import pytest

from abm_governance.core.config import SimulationConfig


def test_default_config_is_valid():
    config = SimulationConfig()
    assert config.population_size > 0


@pytest.mark.parametrize(
    "field_name,bad_value",
    [
        ("population_size", 1),
        ("population_size", 0),
        ("n_steps", 0),
        ("observation_accuracy_mean", 1.5),
        ("observation_accuracy_mean", -0.1),
        ("mutation_rate", -0.01),
        ("mutation_rate", 1.5),
        ("punishment_cost", -1.0),
        ("exit_cost", -1.0),
        ("imitation_period", 0),
        ("rewiring_period", 0),
        ("seed", -1),
        ("topology", "made_up_topology"),
        ("memory_length", 0),
        ("initial_resources_mean", 0.0),
        ("initial_resources_mean", -5.0),
        ("initial_coercive_capability_mean", -1.0),
        ("interactions_per_step", 0),
        ("environment_capacity", 0.0),
        ("environment_capacity", -10.0),
        ("environment_regen_rate", -0.1),
        ("environment_regen_rate", 2.5),
        ("environment_initial_fraction", -0.1),
        ("environment_initial_fraction", 1.5),
        ("subsistence_cost", -0.5),
        ("distress_engagement_prob", -0.1),
        ("distress_engagement_prob", 1.1),
        ("search_cost", -0.5),
        ("connection_accept_base_prob", -0.1),
        ("connection_accept_base_prob", 1.1),
    ],
)
def test_invalid_scalar_field_raises(field_name, bad_value):
    with pytest.raises(ValueError):
        dataclasses.replace(SimulationConfig(), **{field_name: bad_value})


def test_mean_degree_must_be_less_than_population():
    with pytest.raises(ValueError):
        SimulationConfig(population_size=5, mean_degree=10)


def test_policy_mix_must_sum_to_one():
    with pytest.raises(ValueError):
        SimulationConfig(policy_mix={"always_cooperate": 0.5, "always_defect": 0.6})


def test_policy_mix_rejects_unknown_policy():
    with pytest.raises(ValueError):
        SimulationConfig(policy_mix={"machiavellian": 1.0})


def test_policy_mix_rejects_negative_fraction():
    with pytest.raises(ValueError):
        SimulationConfig(policy_mix={"always_cooperate": -0.2, "always_defect": 1.2})


def test_perturbation_spec_must_be_a_mapping():
    with pytest.raises(ValueError):
        SimulationConfig(perturbations=(("not", "a", "mapping"),))


def test_level0_compat_preset_is_valid_and_disables_new_mechanisms():
    config = SimulationConfig.level0_compat()
    assert config.ecology_enabled is False
    assert config.relationship_dynamics_enabled is False
    assert config.perturbations == ()


def test_level0_compat_accepts_overrides():
    config = SimulationConfig.level0_compat(seed=42, n_steps=10)
    assert config.seed == 42
    assert config.n_steps == 10
    assert config.ecology_enabled is False


def test_payoff_ordering_enforced():
    with pytest.raises(ValueError):
        SimulationConfig(payoff_temptation=1.0, payoff_reward=5.0, payoff_punishment=1.0, payoff_sucker=0.0)


def test_yaml_roundtrip(tmp_path):
    config = SimulationConfig(population_size=10, seed=5)
    path = tmp_path / "config.yaml"
    config.to_yaml(str(path))
    loaded = SimulationConfig.from_yaml(str(path))
    assert loaded == config


# -----------------------------------------------------------------------
# Level 0.3 field validation (Work Packages A/B/C/D).
# -----------------------------------------------------------------------
@pytest.mark.parametrize(
    "field_name,bad_value",
    [
        ("ecology_topology", "not_a_topology"),
        ("n_patches", 0),
        ("patch_capacity", 0.0),
        ("patch_capacity", -5.0),
        ("patch_regen_rate", -0.1),
        ("patch_regen_rate", 2.5),
        ("patch_initial_fraction", -0.1),
        ("patch_initial_fraction", 1.5),
        ("patch_quality_std", -0.1),
        ("patch_assignment_mode", "not_a_mode"),
        ("extraction_propensity_std", -0.1),
        ("maintenance_propensity_std", -0.1),
        ("scarcity_sensitivity_std", -0.1),
        ("ecological_harvest_unit", -1.0),
        ("ecological_maintenance_unit", -1.0),
        ("ecological_search_cost", -0.1),
        ("extraction_propensity_mean", -0.1),
        ("extraction_propensity_mean", 1.5),
        ("maintenance_propensity_mean", -0.1),
        ("maintenance_propensity_mean", 1.5),
        ("scarcity_sensitivity_mean", -0.1),
        ("scarcity_sensitivity_mean", 1.5),
        ("maintenance_efficiency", -0.1),
        ("maintenance_efficiency", 1.5),
        ("ecological_allocation_rule", "not_a_rule"),
        ("ecological_mutation_rate", -0.1),
        ("ecological_mutation_rate", 1.5),
        ("fitness_mode_ecological", "not_a_mode"),
        ("ecological_inheritance_mode", "not_a_mode"),
    ],
)
def test_invalid_level03_scalar_field_raises(field_name, bad_value):
    with pytest.raises(ValueError):
        dataclasses.replace(SimulationConfig(), **{field_name: bad_value})


def test_level03_patches_default_preset_is_valid_and_activates_patches():
    config = SimulationConfig.level03_patches_default()
    assert config.ecology_topology == "patches"
    assert config.n_patches >= 1


def test_level03_patches_default_preset_accepts_overrides():
    config = SimulationConfig.level03_patches_default(seed=9, n_patches=8)
    assert config.seed == 9
    assert config.n_patches == 8
    assert config.ecology_topology == "patches"


def test_level02_compat_preset_is_valid_and_uses_global_pool_topology():
    config = SimulationConfig.level02_compat()
    assert config.ecology_topology == "global_pool"
    assert config.ecology_enabled is True


def test_level0_compat_preset_also_pins_global_pool_topology():
    config = SimulationConfig.level0_compat()
    assert config.ecology_topology == "global_pool"


# -- Level 0.3, Work Package F/G/H/J named presets -----------------------

def test_level03_no_environmental_effect_preset():
    config = SimulationConfig.level03_no_environmental_effect()
    assert config.ecology_topology == "patches"
    assert config.ecological_actions_affect_patch is False


def test_level03_frozen_ecological_policy_preset():
    config = SimulationConfig.level03_frozen_ecological_policy()
    assert config.ecological_imitation_enabled is False
    assert config.ecological_mutation_rate == 0.0


def test_level03_randomized_ecological_policy_preset():
    config = SimulationConfig.level03_randomized_ecological_policy()
    assert config.ecological_policy_randomized_each_step is True


def test_level03_policy_shuffle_preset():
    config = SimulationConfig.level03_policy_shuffle()
    assert config.ecological_policy_shuffle is True


def test_level03_viability_sweep_base_preset():
    config = SimulationConfig.level03_viability_sweep_base()
    assert config.ecology_topology == "patches"
    assert config.viability_mode == "dormancy_recovery"


def test_level03_phase_search_base_preset():
    config = SimulationConfig.level03_phase_search_base()
    assert config.ecology_topology == "patches"


def test_level03_perturbation_base_preset():
    config = SimulationConfig.level03_perturbation_base()
    assert config.ecology_topology == "patches"
    assert config.perturbations == ()


def test_all_level03_presets_accept_overrides_and_are_constructible():
    presets = [
        SimulationConfig.level03_no_environmental_effect,
        SimulationConfig.level03_frozen_ecological_policy,
        SimulationConfig.level03_randomized_ecological_policy,
        SimulationConfig.level03_policy_shuffle,
        SimulationConfig.level03_viability_sweep_base,
        SimulationConfig.level03_phase_search_base,
        SimulationConfig.level03_perturbation_base,
    ]
    for preset in presets:
        config = preset(seed=99, population_size=15, n_steps=7)
        assert config.seed == 99
        assert config.population_size == 15
        assert config.n_steps == 7
