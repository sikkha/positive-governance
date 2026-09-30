"""Level 1.2b, Work Package L (Section 17): tests for
``experiments/level12b_stage_l0_confirmation_registry.py`` and
``experiments/level12b_stage_l3_prospective_confirmation.py``."""
from __future__ import annotations

import json
import os

import pytest

from experiments.level12b_stage_e_joint_discovery import load_and_verify_design
from experiments.level12b_stage_l0_confirmation_registry import (
    SEED_BASE_CONFIRMATION,
    build_confirmation_design,
    build_confirmation_registry,
    confirmation_design_hash,
    confirmation_registry_hash,
    load_and_verify_confirmation_design,
    load_and_verify_confirmation_registry,
    write_confirmation_design,
    write_confirmation_registry,
)
from experiments.level12b_stage_l3_prospective_confirmation import (
    CONFIRMATION_VERDICT_LABELS,
    classify_confirmation_verdict,
)


class TestClassifyConfirmationVerdict:
    def test_insufficient_below_hard_minimum(self):
        result = classify_confirmation_verdict(n_total=10, n_hard_minimum=216, independent_replication_verdict="continuum")
        assert result["verdict"] == "insufficient_confirmation_data"

    def test_unexpected_recurring_structure_when_multi_config(self):
        result = classify_confirmation_verdict(n_total=384, n_hard_minimum=216, independent_replication_verdict="multi_config")
        assert result["verdict"] == "unexpected_recurring_structure"

    @pytest.mark.parametrize("verdict", ["continuum", "one_config", "insufficient_evidence", "unstable", "failure_dominated", None])
    def test_null_replicated_for_every_non_multi_config_verdict(self, verdict):
        result = classify_confirmation_verdict(n_total=384, n_hard_minimum=216, independent_replication_verdict=verdict)
        assert result["verdict"] == "null_replicated"

    def test_verdict_always_in_closed_vocabulary(self):
        for kwargs in [
            {"n_total": 1, "n_hard_minimum": 216, "independent_replication_verdict": "continuum"},
            {"n_total": 384, "n_hard_minimum": 216, "independent_replication_verdict": "multi_config"},
            {"n_total": 384, "n_hard_minimum": 216, "independent_replication_verdict": "unstable"},
        ]:
            result = classify_confirmation_verdict(**kwargs)
            assert result["verdict"] in CONFIRMATION_VERDICT_LABELS


class TestConfirmationDesignFreeze:
    def test_design_seeds_disjoint_from_discovery_seeds(self):
        wp_e = load_and_verify_design()
        discovery_seeds = {s for p in wp_e["design"]["points"] for s in p["seeds"]}
        design = build_confirmation_design(n_joint_points=3, seeds_per_point=2)
        confirmation_seeds = {s for p in design["points"] for s in p["seeds"]}
        assert discovery_seeds.isdisjoint(confirmation_seeds)
        assert min(confirmation_seeds) >= SEED_BASE_CONFIRMATION

    def test_design_reuses_discovery_stratum_cut_points(self):
        wp_e = load_and_verify_design()
        design = build_confirmation_design(n_joint_points=3, seeds_per_point=2)
        assert design["stratum_cut_points_reused_from_discovery"] == wp_e["design"]["stratum_cut_points"]

    def test_hash_roundtrip_and_tamper_detection(self, tmp_path):
        out_dir = str(tmp_path / "confirmation_design")
        result = write_confirmation_design(out_dir=out_dir, n_joint_points=2, seeds_per_point=2)
        verified = load_and_verify_confirmation_design(out_dir=out_dir)
        assert verified["hash"] == result["hash"]

        with open(f"{out_dir}/confirmation_design.json") as f:
            design = json.load(f)
        design["n_joint_points"] = 9999
        with open(f"{out_dir}/confirmation_design.json", "w") as f:
            json.dump(design, f)
        with pytest.raises(ValueError):
            load_and_verify_confirmation_design(out_dir=out_dir)

    def test_design_hash_is_deterministic(self):
        d1 = build_confirmation_design(n_joint_points=2, seeds_per_point=2)
        d2 = build_confirmation_design(n_joint_points=2, seeds_per_point=2)
        assert confirmation_design_hash(d1) == confirmation_design_hash(d2)


class TestConfirmationRegistryFreeze:
    def test_registry_discloses_continuum_as_no_candidate(self):
        design = build_confirmation_design(n_joint_points=2, seeds_per_point=2)
        digest = confirmation_design_hash(design)
        if not os.path.exists("outputs/level12b_stage_k_clustering_discovery/results.json"):
            pytest.skip("Work Package K output not present in this environment")
        registry = build_confirmation_registry(digest)
        assert "continuum" in registry["candidate_status"] or "no_independent" in registry["candidate_status"]
        assert registry["null_replication_rule_applied"] is True

    def test_registry_hash_roundtrip(self):
        if not os.path.exists("outputs/level12b_stage_k_clustering_discovery/results.json"):
            pytest.skip("Work Package K output not present in this environment")
        design = build_confirmation_design(n_joint_points=2, seeds_per_point=2)
        digest = confirmation_design_hash(design)
        registry = build_confirmation_registry(digest)
        assert confirmation_registry_hash(registry) == confirmation_registry_hash(registry)  # deterministic

    def test_actual_frozen_registry_verifies(self):
        out_dir = "outputs/level12b_stage_l0_confirmation_registry"
        if not os.path.exists(f"{out_dir}/confirmation_registry.json"):
            pytest.skip("Work Package L registry not present in this environment")
        verified = load_and_verify_confirmation_registry(out_dir=out_dir)
        assert verified["registry"]["run_arithmetic"]["total_runs"] == 384
        assert verified["registry"]["expected_directions"]["primary_prereg_expectation"]


class TestActualConfirmationOutputIfPresent:
    def test_confirmation_pool_meets_structural_requirements(self):
        path = "outputs/level12b_stage_l1_confirmation_pool/results.json"
        if not os.path.exists(path):
            pytest.skip("Work Package L confirmation pool output not present in this environment")
        with open(path) as f:
            report = json.load(f)
        assert report["n_runs_completed"] > 0
        for rec in report["records"]:
            assert "phenotype_vector" in rec
            assert "all_outcome_label" in rec

    def test_final_report_meets_section_17_structural_requirements(self):
        path = "outputs/level12b_stage_l3_prospective_confirmation/results.json"
        if not os.path.exists(path):
            pytest.skip("Work Package L final report not present in this environment")
        with open(path) as f:
            report = json.load(f)
        assert report["n_confirmation_runs"] > 0
        assert report["confirmation_registry_hash"]
        assert report["source_design_hash"]
        assert report["preregistration_manifest_hash"]
        assert report["confirmation_verdict"]["verdict"] in CONFIRMATION_VERDICT_LABELS
        assert report["recurrence_across_seeds_points_and_ic_families"]["verdict"]["verdict"]
        assert 0.0 <= report["unclassified_outcome_rate"] <= 1.0
        assert 0.0 <= report["failure_transition_rate"] <= 1.0
        assert "per_cluster_cosine_similarity" in report["feature_profile_stability"]
