"""Level 1.2b, Work Package I (Section 14): tests for
``experiments/level12b_stage_i_preregistration_manifest.py``."""
from __future__ import annotations

import json
import os

import pytest

from experiments.level12b_stage_i_preregistration_manifest import (
    build_manifest,
    load_and_verify_manifest,
    manifest_hash,
)


class TestManifestCompleteness:
    """Section 14's own enumerated required fields."""

    REQUIRED_KEYS = (
        "feasibility_ratio_definitions", "ecological_bounds", "ecological_strata", "institutional_bounds",
        "initial_condition_families", "run_arithmetic", "burn_in_windows", "feature_dictionary",
        "missing_data_rules", "recurrence_criteria", "clustering_commitments", "confirmation_rules",
        "scale_robustness_grid", "stop_conditions", "compute_budget_decisions",
    )

    def test_every_required_field_present(self):
        manifest = build_manifest()
        for key in self.REQUIRED_KEYS:
            assert key in manifest, f"manifest missing required Section 14 field: {key}"

    def test_versioned(self):
        manifest = build_manifest()
        assert manifest["version"]
        assert "level1.2b" in manifest["version"]

    def test_deterministic(self):
        assert build_manifest() == build_manifest()


class TestImportedNotHandCopied:
    """Spot checks that key values are pulled live from the modules
    they describe, not hand-duplicated (so they cannot silently drift)."""

    def test_run_arithmetic_matches_work_package_e(self):
        from experiments.level12b_stage_e_joint_discovery import (
            N_IC_FAMILIES,
            N_JOINT_POINTS_PREFERRED,
            SEEDS_PER_POINT_PREFERRED,
        )

        manifest = build_manifest()
        assert manifest["run_arithmetic"]["preferred"]["total_runs"] == (
            N_JOINT_POINTS_PREFERRED * SEEDS_PER_POINT_PREFERRED * N_IC_FAMILIES
        )

    def test_clustering_commitments_match_phenotype_discovery(self):
        from abm_governance.observer.phenotype_discovery import CANDIDATE_METHODS, DEFAULT_K_RANGE

        manifest = build_manifest()
        assert manifest["clustering_commitments"]["candidate_methods"] == list(CANDIDATE_METHODS)
        assert manifest["clustering_commitments"]["k_range"] == list(DEFAULT_K_RANGE)

    def test_feature_dictionary_matches_phenotype_feature_audit(self):
        from abm_governance.observer.phenotype_feature_audit import PHENOTYPE_FEATURE_AUDIT

        manifest = build_manifest()
        assert set(manifest["feature_dictionary"].keys()) == set(PHENOTYPE_FEATURE_AUDIT.keys())

    def test_recurrence_criteria_references_work_package_h_spec_hash(self):
        out_dir = "outputs/level12b_stage_h_recurrence_spec"
        if not os.path.exists(f"{out_dir}/recurrence_spec_hash.txt"):
            pytest.skip("Work Package H recurrence spec not present in this environment")
        with open(f"{out_dir}/recurrence_spec_hash.txt") as f:
            expected_hash = f.read().strip()
        manifest = build_manifest()
        assert manifest["recurrence_criteria"]["source_spec_hash"] == expected_hash

    def test_ecological_strata_references_work_package_e_design_hash(self):
        out_dir = "outputs/level12b_stage_e_joint_discovery"
        if not os.path.exists(f"{out_dir}/design_hash.txt"):
            pytest.skip("Work Package E design not present in this environment")
        with open(f"{out_dir}/design_hash.txt") as f:
            expected_hash = f.read().strip()
        manifest = build_manifest()
        assert manifest["ecological_strata"]["source_design_hash"] == expected_hash


class TestConfirmationRulesAndScaleGrid:
    def test_confirmation_arithmetic_matches_task_description(self):
        manifest = build_manifest()
        rules = manifest["confirmation_rules"]
        assert rules["preferred"]["total_runs"] == 24 * 8 * 2
        assert rules["hard_minimum"]["total_runs"] == 18 * 6 * 2
        assert "seed_disjointness_rule" in rules
        assert len(rules["tests_applied_to_every_candidate"]) >= 5

    def test_scale_grid_arithmetic_matches_task_description(self):
        manifest = build_manifest()
        grid = manifest["scale_robustness_grid"]
        assert grid["runs_per_candidate_or_null_baseline"] == 2 * 2 * 2 * 4
        assert grid["scale_invariance_required"] is False


class TestStopConditionsAndComputeBudget:
    def test_stop_conditions_nonempty_and_stringy(self):
        manifest = build_manifest()
        assert len(manifest["stop_conditions"]) >= 3
        assert all(isinstance(s, str) and len(s) > 20 for s in manifest["stop_conditions"])

    def test_compute_budget_decisions_disclose_work_package_g_reduction(self):
        manifest = build_manifest()
        decisions = manifest["compute_budget_decisions"]
        assert "work_package_g_temporal_representation" in decisions
        assert "12" in decisions["work_package_g_temporal_representation"]


class TestHashingAndPersistence:
    def test_hash_deterministic(self):
        manifest = build_manifest()
        assert manifest_hash(manifest) == manifest_hash(manifest)
        assert manifest_hash(manifest) == manifest_hash(build_manifest())

    def test_json_serializable(self):
        manifest = build_manifest()
        json.dumps(manifest, default=str)  # must not raise

    def test_save_load_verify_roundtrip(self, tmp_path):
        import experiments.level12b_stage_i_preregistration_manifest as pm

        result = pm.write_manifest(out_dir=str(tmp_path))
        verified = load_and_verify_manifest(out_dir=str(tmp_path))
        assert verified["hash"] == result["hash"]
        # compare via JSON round-trip semantics: tuples in the in-memory
        # manifest (e.g. burn-in windows_included) become lists once
        # read back from disk, exactly as intended -- the hash (checked
        # above) is what actually guards content integrity.
        assert verified["manifest"] == json.loads(json.dumps(result["manifest"], default=str))

    def test_tampering_detected(self, tmp_path):
        import experiments.level12b_stage_i_preregistration_manifest as pm

        pm.write_manifest(out_dir=str(tmp_path))
        with open(f"{tmp_path}/manifest.json") as f:
            manifest = json.load(f)
        manifest["version"] = "tampered"
        with open(f"{tmp_path}/manifest.json", "w") as f:
            json.dump(manifest, f)
        with pytest.raises(ValueError):
            load_and_verify_manifest(out_dir=str(tmp_path))


class TestActualSavedManifestIfPresent:
    def test_saved_manifest_matches_its_own_hash(self):
        out_dir = "outputs/level12b_stage_i_preregistration_manifest"
        if not os.path.exists(f"{out_dir}/manifest.json"):
            pytest.skip("Work Package I manifest not present in this environment")
        verified = load_and_verify_manifest(out_dir)
        assert verified["manifest"]["version"] == "level1.2b-preregistration-manifest-v1"
