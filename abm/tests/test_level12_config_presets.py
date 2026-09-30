"""Level 1.2, Section 17: config presets."""

from __future__ import annotations

from abm_governance.core.config import SimulationConfig


class TestLevel12Complete:
    def test_all_five_mechanism_flags_enabled(self):
        config = SimulationConfig.level12_complete()
        assert config.institutional_observation_enabled is True
        assert config.institutional_transmission_enabled is True
        assert config.migration_enabled is True
        assert config.membership_exit_enabled is True
        assert config.institutional_scaling_enabled is True

    def test_inherits_level11_complete_mechanisms(self):
        config = SimulationConfig.level12_complete()
        assert config.delegation_enabled is True
        assert config.discretion_enabled is True
        assert config.accountability_enabled is True
        assert config.interpatch_coordination_enabled is True

    def test_rng_mode_is_mechanism_substreams_by_default(self):
        assert SimulationConfig.level12_complete().rng_mode == "mechanism_substreams"

    def test_overrides_take_precedence(self):
        config = SimulationConfig.level12_complete(migration_enabled=False)
        assert config.migration_enabled is False
        assert config.institutional_observation_enabled is True  # unaffected


class TestLevel12IsolationPresets:
    def test_observation_only_isolates_work_package_b(self):
        config = SimulationConfig.level12_observation_only()
        assert config.institutional_observation_enabled is True
        assert config.institutional_transmission_enabled is False
        assert config.migration_enabled is False
        assert config.membership_exit_enabled is False
        assert config.institutional_scaling_enabled is False
        assert config.interpatch_coordination_enabled is True

    def test_transmission_only_isolates_work_package_c(self):
        config = SimulationConfig.level12_transmission_only()
        assert config.institutional_transmission_enabled is True
        assert config.institutional_observation_enabled is False
        assert config.migration_enabled is False

    def test_migration_only_isolates_work_package_d_migration(self):
        config = SimulationConfig.level12_migration_only()
        assert config.migration_enabled is True
        assert config.membership_exit_enabled is False
        assert config.institutional_observation_enabled is False

    def test_membership_exit_only_isolates_work_package_d_exit(self):
        config = SimulationConfig.level12_membership_exit_only()
        assert config.membership_exit_enabled is True
        assert config.migration_enabled is False

    def test_scaling_only_isolates_work_package_f(self):
        config = SimulationConfig.level12_scaling_only()
        assert config.institutional_scaling_enabled is True
        assert config.migration_enabled is False
        assert config.interpatch_coordination_enabled is True


class TestPresetsDoNotAffectBareDefault:
    def test_bare_default_config_is_untouched(self):
        config = SimulationConfig()
        assert config.institutional_observation_enabled is False
        assert config.institutional_transmission_enabled is False
        assert config.migration_enabled is False
        assert config.membership_exit_enabled is False
        assert config.institutional_scaling_enabled is False
        assert config.rng_mode == "legacy_single_stream"
