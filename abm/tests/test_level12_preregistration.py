"""Level 1.2, Section 12, Stage 0: preregistration manifest."""

from __future__ import annotations

import importlib
import inspect
import json
import re

import pytest

from experiments import level12_preregistration as prereg
from tests.test_level12_structural_guards import FORBIDDEN_LEVEL12_TERMS, _strip_docstrings_and_comments


class TestBuildManifest:
    def test_manifest_is_deterministic(self):
        a = prereg.build_manifest()
        b = prereg.build_manifest()
        assert a == b

    def test_manifest_covers_all_seven_stages(self):
        manifest = prereg.build_manifest()
        stages = manifest["stage_sample_sizes"]
        for name in (
            "stage1_mechanism_activation", "stage2_small_open_pilot", "stage3_main_open_search",
            "stage4_blind_discovery_run", "stage5_prospective_confirmation",
            "stage6_scaling_robustness", "stage7_perturbation_transition",
        ):
            assert name in stages

    def test_discovery_commitments_match_source_module_constants_exactly(self):
        from abm_governance.observer.phenotype_discovery import CANDIDATE_METHODS, DEFAULT_K_RANGE, MISSINGNESS_STRATEGIES
        manifest = prereg.build_manifest()
        commitments = manifest["discovery_pipeline_commitments"]
        assert commitments["candidate_methods"] == list(CANDIDATE_METHODS)
        assert commitments["k_range"] == list(DEFAULT_K_RANGE)
        assert commitments["missingness_strategies"] == list(MISSINGNESS_STRATEGIES)

    def test_recurrence_rule_is_conjunction_not_majority_vote(self):
        manifest = prereg.build_manifest()
        assert "conjunction" in manifest["recurrence_and_convergence_commitments"]["recurrence_rule"].lower()

    def test_rng_mode_is_mechanism_substreams(self):
        manifest = prereg.build_manifest()
        assert manifest["rng_commitments"]["rng_mode"] == "mechanism_substreams"


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
        out_dir = str(tmp_path / "stage0")
        written = prereg.write_manifest(out_dir=out_dir)
        verified = prereg.load_and_verify_manifest(out_dir=out_dir)
        assert verified["hash"] == written["hash"]
        assert verified["manifest"] == written["manifest"]

    def test_tampering_with_manifest_content_is_detected(self, tmp_path):
        out_dir = str(tmp_path / "stage0")
        prereg.write_manifest(out_dir=out_dir)
        with open(f"{out_dir}/manifest.json") as f:
            manifest = json.load(f)
        manifest["stage_sample_sizes"]["stage3_main_open_search"]["n_seeds"] = 999
        with open(f"{out_dir}/manifest.json", "w") as f:
            json.dump(manifest, f)
        with pytest.raises(ValueError, match="altered"):
            prereg.load_and_verify_manifest(out_dir=out_dir)


class TestForbiddenTerminologyGuardExtendsToPreregistrationScript:
    def test_preregistration_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level12_preregistration")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL12_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
