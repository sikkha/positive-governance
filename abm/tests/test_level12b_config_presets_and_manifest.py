"""Level 1.2b, Section 24: config presets and result-manifest schema."""

from __future__ import annotations

import pytest

import abm_governance
from abm_governance.core.config import SimulationConfig
from abm_governance.observer.phenotype_discovery import CLUSTERING_PIPELINE_VERSION
from abm_governance.observer.phenotype_feature_audit import FEATURE_SCHEMA_VERSION
from abm_governance.observer.recurrence_criteria import RECURRENCE_CRITERIA_VERSION
from experiments.level12b_common import (
    RESULT_MANIFEST_FIELDS,
    build_result_manifest,
    config_hash,
)

PRESET_NAMES = (
    "level12_compat",
    "level12b_feasibility_map",
    "level12b_open_discovery",
    "level12b_confirmation",
    "level12b_failure_analysis",
    "level12b_sustained_analysis",
    "level12b_collapse_ablation",
    "level12b_scaling_robustness",
)


class TestPresetsExistAndAreCallable:
    @pytest.mark.parametrize("preset_name", PRESET_NAMES)
    def test_preset_is_a_classmethod_returning_a_config(self, preset_name):
        preset = getattr(SimulationConfig, preset_name)
        config = preset()
        assert isinstance(config, SimulationConfig)


class TestPresetsAreNoOpByDefault:
    """The core Section 24 requirement: every one of the eight presets,
    called bare, must be a byte-for-byte no-op against
    ``level12_complete()`` -- these are semantically-named entry
    points, not behavioral variants."""

    @pytest.mark.parametrize("preset_name", PRESET_NAMES)
    def test_preset_bare_call_equals_level12_complete(self, preset_name):
        preset = getattr(SimulationConfig, preset_name)
        assert preset() == SimulationConfig.level12_complete()

    @pytest.mark.parametrize("preset_name", PRESET_NAMES)
    def test_preset_inherits_mechanism_substreams(self, preset_name):
        """'causal presets use rng_mode=mechanism_substreams' holds for
        all eight by construction (inherited from level12_complete),
        not as a special case for any subset."""
        preset = getattr(SimulationConfig, preset_name)
        assert preset().rng_mode == "mechanism_substreams"

    @pytest.mark.parametrize("preset_name", PRESET_NAMES)
    def test_preset_overrides_take_precedence(self, preset_name):
        preset = getattr(SimulationConfig, preset_name)
        config = preset(population_size=999)
        assert config.population_size == 999


class TestPresetsDoNotAffectBareDefault:
    def test_bare_default_config_is_untouched(self):
        """Defining these eight new presets must not perturb
        ``SimulationConfig()``'s own defaults in any way."""
        config = SimulationConfig()
        assert config.rng_mode == "legacy_single_stream"
        assert config.institutional_observation_enabled is False


class TestNoExistingLevel12ExperimentScriptWasRefactored:
    def test_level12_complete_and_level12_compat_are_independently_defined(self):
        """level12_compat must be its own classmethod (delegating to
        level12_complete), not a rename -- level12_complete itself must
        remain callable under its original name so no already-written
        experiment script import breaks."""
        assert hasattr(SimulationConfig, "level12_complete")
        assert hasattr(SimulationConfig, "level12_compat")
        assert SimulationConfig.level12_compat() == SimulationConfig.level12_complete()


class TestConfigHash:
    def test_deterministic_for_identical_config(self):
        c1 = SimulationConfig.level12_complete()
        c2 = SimulationConfig.level12_complete()
        assert config_hash(c1) == config_hash(c2)

    def test_differs_for_different_config(self):
        c1 = SimulationConfig.level12_complete()
        c2 = SimulationConfig.level12_complete(population_size=999)
        assert config_hash(c1) != config_hash(c2)

    def test_matches_stage_e_own_construction(self):
        """config_hash must agree with experiments/level12b_stage_e_
        joint_discovery.py's own already-frozen ``_config_hash`` --
        same SHA-256-over-sorted-vars(config) construction, factored
        out here as the one shared implementation, not a divergent
        reimplementation."""
        from experiments.level12b_stage_e_joint_discovery import _config_hash

        config = SimulationConfig.level12_complete(seed=42)
        assert config_hash(config) == _config_hash(config)


class TestBuildResultManifest:
    def test_includes_all_twelve_required_fields(self):
        config = SimulationConfig.level12_complete(seed=7)
        manifest = build_result_manifest(config=config)
        assert set(manifest.keys()) == set(RESULT_MANIFEST_FIELDS)
        assert len(RESULT_MANIFEST_FIELDS) == 12

    def test_root_seed_and_rng_mode_and_stream_registry_version(self):
        config = SimulationConfig.level12_complete(seed=123)
        manifest = build_result_manifest(config=config)
        assert manifest["root_seed"] == 123
        assert manifest["rng_mode"] == "mechanism_substreams"
        assert manifest["stream_registry_version"] == config.rng_registry_version

    def test_code_version_matches_package(self):
        manifest = build_result_manifest(config=SimulationConfig.level12_complete())
        assert manifest["code_version"] == abm_governance.__version__

    def test_config_hash_matches_standalone_function(self):
        config = SimulationConfig.level12_complete(seed=5)
        manifest = build_result_manifest(config=config)
        assert manifest["config_hash"] == config_hash(config)

    def test_version_tags_match_their_source_modules(self):
        manifest = build_result_manifest(config=SimulationConfig.level12_complete())
        assert manifest["feature_schema_version"] == FEATURE_SCHEMA_VERSION
        assert manifest["recurrence_criteria_version"] == RECURRENCE_CRITERIA_VERSION
        assert manifest["clustering_pipeline_version"] == CLUSTERING_PIPELINE_VERSION

    def test_caller_supplied_fields_default_to_none_not_fabricated(self):
        manifest = build_result_manifest(config=SimulationConfig.level12_complete())
        assert manifest["feasibility_design_hash"] is None
        assert manifest["institutional_design_hash"] is None
        assert manifest["preregistration_hash"] is None
        assert manifest["ic_family"] is None

    def test_caller_supplied_fields_pass_through_when_given(self):
        manifest = build_result_manifest(
            config=SimulationConfig.level12_complete(),
            feasibility_design_hash="feas123",
            institutional_design_hash="inst456",
            preregistration_hash="prereg789",
            ic_family="heterogeneous_proto_institution",
        )
        assert manifest["feasibility_design_hash"] == "feas123"
        assert manifest["institutional_design_hash"] == "inst456"
        assert manifest["preregistration_hash"] == "prereg789"
        assert manifest["ic_family"] == "heterogeneous_proto_institution"

    def test_two_configs_differing_only_in_seed_give_different_manifests_only_in_root_seed_and_config_hash(self):
        c1 = SimulationConfig.level12_complete(seed=1)
        c2 = SimulationConfig.level12_complete(seed=2)
        m1 = build_result_manifest(config=c1)
        m2 = build_result_manifest(config=c2)
        differing = {k for k in RESULT_MANIFEST_FIELDS if m1[k] != m2[k]}
        assert differing == {"root_seed", "config_hash"}


class TestVersionTagsAreStable:
    """Not a behavioral test -- a change-detector. If any of these
    fails, a version tag changed without the change being deliberately
    disclosed in this test file (bump both together)."""

    def test_feature_schema_version(self):
        assert FEATURE_SCHEMA_VERSION == "phenotype_feature_schema_v1"

    def test_recurrence_criteria_version(self):
        assert RECURRENCE_CRITERIA_VERSION == "recurrence_criteria_v1"

    def test_clustering_pipeline_version(self):
        assert CLUSTERING_PIPELINE_VERSION == "clustering_pipeline_v1"
