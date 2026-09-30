"""Level 1.3, task #94 (Section 15): the milestone-level preregistration
manifest (``experiments/level13_preregistration.py``)."""

from __future__ import annotations

import importlib
import inspect
import json

import pytest

from experiments import level13_preregistration as prereg
from tests.test_level13_sem_firewall_extension import FORBIDDEN_LEVEL13_TERMS
from tests.test_level12_structural_guards import _strip_docstrings_and_comments


class TestBuildManifest:
    def test_manifest_is_deterministic(self):
        a = prereg.build_manifest()
        b = prereg.build_manifest()
        assert a == b

    def test_manifest_covers_all_ten_stages(self):
        manifest = prereg.build_manifest()
        stages = manifest["stage_sample_sizes"]
        for name in (
            "stage0_exact_compatibility", "stage1_mechanism_activation",
            "stage2_calibration_without_phenotype_labels", "stage3_sequencing_x_entrenchment_factorial",
            "stage4_open_pressure_history_search_lhs", "stage5_causal_historical_counterfactuals_matched_seed",
            "stage6_blind_phenotype_discovery", "stage7_fresh_confirmation",
            "stage8_s_obs_z_obs_mapping", "stage9_scale_and_shock_robustness",
        ):
            assert name in stages

    def test_covers_all_seven_mechanism_flags(self):
        manifest = prereg.build_manifest()
        assert len(manifest["mechanism_activation_flags"]) == 7
        assert "historical_module_enabled" in manifest["mechanism_activation_flags"]

    def test_discovery_commitments_match_source_module_constants_exactly(self):
        from abm_governance.observer.level13_phenotype import LEVEL13_DIMENSION_KEYS
        from abm_governance.observer.phenotype_discovery import CANDIDATE_METHODS, DEFAULT_K_RANGE, MISSINGNESS_STRATEGIES
        manifest = prereg.build_manifest()
        commitments = manifest["discovery_pipeline_commitments"]
        assert commitments["candidate_methods"] == list(CANDIDATE_METHODS)
        assert commitments["k_range"] == list(DEFAULT_K_RANGE)
        assert commitments["missingness_strategies"] == list(MISSINGNESS_STRATEGIES)
        assert commitments["level13_dimension_keys"] == list(LEVEL13_DIMENSION_KEYS)

    def test_sz_obs_commitments_match_source_module_constants_exactly(self):
        from abm_governance.observer.sz_obs import S_OBS_RESPONSE_DIMENSIONS, Z_OBS_RESPONSE_DIMENSIONS
        manifest = prereg.build_manifest()
        commitments = manifest["sz_obs_commitments"]
        assert commitments["s_obs_response_dimensions"] == list(S_OBS_RESPONSE_DIMENSIONS)
        assert commitments["z_obs_response_dimensions"] == list(Z_OBS_RESPONSE_DIMENSIONS)

    def test_rng_mode_is_mechanism_substreams(self):
        manifest = prereg.build_manifest()
        assert manifest["rng_commitments"]["rng_mode"] == "mechanism_substreams"

    def test_rng_registry_version_matches_core_rng(self):
        from abm_governance.core.rng import RNG_REGISTRY_VERSION
        manifest = prereg.build_manifest()
        assert manifest["rng_commitments"]["rng_registry_version"] == RNG_REGISTRY_VERSION


class TestDecisionGateOutcomes:
    def test_exactly_six_outcomes(self):
        assert len(prereg.DECISION_GATE_OUTCOMES) == 6

    def test_do_not_prefer_e_is_one_of_the_six(self):
        assert prereg.DECISION_GATE_DO_NOT_PREFER in prereg.DECISION_GATE_OUTCOMES

    def test_do_not_prefer_e_is_transient_differentiation(self):
        # Disclosed provenance: docs/level1.3_theoretical_translation.md
        # §6's own recovered sentence, and this session's own
        # status_update.md record disambiguating "do not prefer E" (the
        # outcome) from Work Package E (the counterfactual work
        # package) -- transcribed, not reconstructed.
        assert prereg.DECISION_GATE_DO_NOT_PREFER == "E_transient_differentiation"

    def test_every_outcome_has_a_nonempty_description(self):
        for key, description in prereg.DECISION_GATE_OUTCOMES.items():
            assert isinstance(description, str)
            assert len(description) > 0

    def test_manifest_includes_the_full_decision_gate(self):
        manifest = prereg.build_manifest()
        assert manifest["decision_gate_outcomes"] == prereg.DECISION_GATE_OUTCOMES
        assert manifest["decision_gate_do_not_prefer"] == "E_transient_differentiation"


class TestManifestHash:
    def test_hash_is_stable_across_key_order(self):
        m1 = {"a": 1, "b": 2}
        m2 = {"b": 2, "a": 1}
        assert prereg.manifest_hash(m1) == prereg.manifest_hash(m2)

    def test_hash_changes_when_content_changes(self):
        m1 = {"a": 1}
        m2 = {"a": 2}
        assert prereg.manifest_hash(m1) != prereg.manifest_hash(m2)

    def test_real_manifest_hash_is_deterministic(self):
        manifest = prereg.build_manifest()
        assert prereg.manifest_hash(manifest) == prereg.manifest_hash(manifest)


class TestWriteAndVerifyManifest:
    def test_write_then_verify_round_trips(self, tmp_path):
        out_dir = str(tmp_path / "level13_prereg")
        written = prereg.write_manifest(out_dir=out_dir)
        verified = prereg.load_and_verify_manifest(out_dir=out_dir)
        assert verified["hash"] == written["hash"]
        assert verified["manifest"] == written["manifest"]

    def test_tampering_with_manifest_content_is_detected(self, tmp_path):
        out_dir = str(tmp_path / "level13_prereg")
        prereg.write_manifest(out_dir=out_dir)
        with open(f"{out_dir}/manifest.json") as f:
            manifest = json.load(f)
        manifest["stage_sample_sizes"]["stage4_open_pressure_history_search_lhs"]["n_points"] = 999
        with open(f"{out_dir}/manifest.json", "w") as f:
            json.dump(manifest, f)
        with pytest.raises(ValueError, match="altered"):
            prereg.load_and_verify_manifest(out_dir=out_dir)


class TestForbiddenTerminologyGuardExtendsToPreregistrationScript:
    def test_preregistration_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level13_preregistration")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL13_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
