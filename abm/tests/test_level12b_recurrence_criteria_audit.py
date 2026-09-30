"""Level 1.2b, Work Package H (Section 13): tests for
``observer/recurrence_criteria_audit.py``, the ``convergence_tests.py``
lineage-collision fix, and
``experiments/level12b_stage_h_recurrence_spec.py``'s versioned,
saved+hashed spec."""
from __future__ import annotations

import json
import os

import numpy as np
import pytest

from abm_governance.observer import convergence_tests as ct
from abm_governance.observer import recurrence_criteria as rc
from abm_governance.observer import recurrence_criteria_audit as rca


class TestAuditCompleteness:
    def test_all_twelve_criteria_audited(self):
        result = rca.audit_completeness_check()
        assert result["all_criteria_audited"] is True
        assert result["missing_from_audit"] == []
        assert result["extra_in_audit"] == []
        assert len(result["audited_criteria"]) == 12

    def test_audited_set_matches_source_names_exactly(self):
        assert set(rca.RECURRENCE_CRITERIA_AUDIT.keys()) == set(rc.RECURRENCE_CRITERIA_NAMES)

    def test_every_entry_has_the_section_13_required_fields(self):
        required = {"construct", "unit_of_analysis", "min_sample_size", "redundant_with", "feasible_under_1_2b_design", "feasibility_note"}
        for name, entry in rca.RECURRENCE_CRITERIA_AUDIT.items():
            missing = required - set(entry.keys())
            assert not missing, f"{name} missing required audit fields: {missing}"

    def test_lineage_criterion_flagged_as_the_fixed_finding(self):
        entry = rca.RECURRENCE_CRITERIA_AUDIT["independent_of_single_lineage"]
        assert "FIXED" in entry["feasible_under_1_2b_design"] or entry["feasible_under_1_2b_design"] == "conditional -- FIXED this Work Package"
        assert "collide" in entry["feasibility_note"] or "collision" in entry["feasibility_note"].lower()


class TestSimilarityLevelTaxonomy:
    def test_four_levels_present(self):
        assert set(rca.SIMILARITY_LEVEL_TAXONOMY.keys()) == {
            "within_run_lineage", "cross_run_structural_similarity", "independent_convergence", "component_homology_vs_analogy",
        }

    def test_every_level_names_its_operationalization(self):
        for name, entry in rca.SIMILARITY_LEVEL_TAXONOMY.items():
            assert entry["operationalized_by"], f"{name} has no operationalizing function listed"
            assert "definition" in entry
            assert "distinguishes_from" in entry


class TestExtractDefaultThresholds:
    def test_matches_live_function_defaults(self):
        thresholds = rca.extract_default_thresholds()
        assert thresholds["minimum_cluster_size"]["min_size"] == 5
        assert thresholds["independent_of_single_lineage"]["max_single_lineage_fraction"] == 0.7
        assert thresholds["non_degenerate_cluster_fraction"] == {"min_fraction": 0.02, "max_fraction": 0.95}

    def test_json_serializable(self):
        thresholds = rca.extract_default_thresholds()
        json.dumps(thresholds)  # must not raise

    def test_all_twelve_covered(self):
        thresholds = rca.extract_default_thresholds()
        assert set(thresholds.keys()) == set(rc.RECURRENCE_CRITERIA_NAMES)


class TestLineageCollisionFixRegression:
    """The core verification: demonstrates the bug the audit found (raw
    per-run lineage ids collide across seed-runs) and confirms the
    fix (composed keys) avoids it."""

    def test_raw_lineage_ids_collide_across_runs_without_composition(self):
        """Two DIFFERENT seed-runs, each independently allocating
        lineage id 0 to their own first institution -- pooling the raw
        integers makes them look identical, which is wrong."""
        run_a_lineage_ids = [0, 1]  # seed-run A's own two lineages
        run_b_lineage_ids = [0, 1]  # seed-run B's own two lineages (independent, unrelated)
        pooled_raw = run_a_lineage_ids + run_b_lineage_ids
        # naive diversity treats "0" from run A and "0" from run B as
        # the SAME lineage -- only 2 distinct values across 4 members,
        # which understates true diversity (4 genuinely independent
        # lineages exist).
        diversity_naive = ct.lineage_diversity_within_cluster(pooled_raw)
        assert diversity_naive["n_distinct_lineages"] == 2

    def test_composed_keys_avoid_the_collision(self):
        run_a_lineage_ids = [0, 1]
        run_b_lineage_ids = [0, 1]
        composed = (
            [ct.compose_global_lineage_id("seed_a", lid) for lid in run_a_lineage_ids]
            + [ct.compose_global_lineage_id("seed_b", lid) for lid in run_b_lineage_ids]
        )
        diversity_fixed = ct.lineage_diversity_within_cluster(composed)
        # now correctly resolves as 4 distinct lineages -- the collision is gone.
        assert diversity_fixed["n_distinct_lineages"] == 4

    def test_compose_global_lineage_id_is_deterministic_and_distinguishes_runs(self):
        assert ct.compose_global_lineage_id(3, 0) == ct.compose_global_lineage_id(3, 0)
        assert ct.compose_global_lineage_id(3, 0) != ct.compose_global_lineage_id(41, 0)


class TestWithinRunLineageRelatedness:
    def test_same_run_same_lineage_counted(self):
        result = ct.within_run_lineage_relatedness(
            member_seed_run_ids=[1, 1, 1], member_lineage_ids=[0, 0, 5],
        )
        # 3 same-run pairs: (0,0)->same lineage, (0,5)->diff, (0,5)->diff
        assert result["n_within_run_pairs"] == 3
        assert result["n_within_run_same_lineage_pairs"] == 1
        assert result["fraction_within_run_pairs_same_lineage"] == pytest.approx(1 / 3)

    def test_different_runs_excluded_from_within_run_computation(self):
        result = ct.within_run_lineage_relatedness(
            member_seed_run_ids=[1, 2], member_lineage_ids=[0, 0],
        )
        # different runs -- even though raw lineage ids match (0 == 0),
        # they must NOT be counted as a within-run pair at all (this is
        # exactly the cross-run collision case this function
        # deliberately excludes, not silently mishandles).
        assert result["n_within_run_pairs"] == 0
        assert np.isnan(result["fraction_within_run_pairs_same_lineage"])

    def test_degenerate_on_fewer_than_two_members(self):
        result = ct.within_run_lineage_relatedness([1], [0])
        assert result["n_within_run_pairs"] == 0
        assert np.isnan(result["fraction_within_run_pairs_same_lineage"])


class TestStageHRecurrenceSpecScript:
    def test_build_spec_includes_all_required_sections(self):
        from experiments.level12b_stage_h_recurrence_spec import build_recurrence_spec

        spec = build_recurrence_spec()
        assert spec["version"]
        assert set(spec["source_criteria_names"]) == set(rc.RECURRENCE_CRITERIA_NAMES)
        assert set(spec["criteria_audit"].keys()) == set(rc.RECURRENCE_CRITERIA_NAMES)
        assert set(spec["default_thresholds"].keys()) == set(rc.RECURRENCE_CRITERIA_NAMES)
        assert set(spec["similarity_level_taxonomy"].keys()) == {
            "within_run_lineage", "cross_run_structural_similarity", "independent_convergence", "component_homology_vs_analogy",
        }
        assert spec["audit_completeness"]["all_criteria_audited"] is True

    def test_spec_is_json_serializable(self):
        from experiments.level12b_stage_h_recurrence_spec import build_recurrence_spec

        spec = build_recurrence_spec()
        json.dumps(spec)  # must not raise

    def test_hash_deterministic(self):
        from experiments.level12b_stage_h_recurrence_spec import build_recurrence_spec, recurrence_spec_hash

        spec = build_recurrence_spec()
        assert recurrence_spec_hash(spec) == recurrence_spec_hash(spec)
        assert recurrence_spec_hash(spec) == recurrence_spec_hash(build_recurrence_spec())

    def test_save_and_hash_roundtrips(self, tmp_path):
        import experiments.level12b_stage_h_recurrence_spec as sh

        original_out_dir = sh.OUT_DIR
        try:
            sh.OUT_DIR = str(tmp_path)
            result = sh.save_and_hash()
            verified = sh.load_and_verify_recurrence_spec(str(tmp_path))
            assert verified["hash"] == result["hash"]
            assert verified["spec"] == result["spec"]
        finally:
            sh.OUT_DIR = original_out_dir

    def test_tampered_spec_is_detected(self, tmp_path):
        import experiments.level12b_stage_h_recurrence_spec as sh

        original_out_dir = sh.OUT_DIR
        try:
            sh.OUT_DIR = str(tmp_path)
            sh.save_and_hash()
            with open(f"{tmp_path}/recurrence_spec.json") as f:
                spec = json.load(f)
            spec["version"] = "tampered"
            with open(f"{tmp_path}/recurrence_spec.json", "w") as f:
                json.dump(spec, f)
            with pytest.raises(ValueError):
                sh.load_and_verify_recurrence_spec(str(tmp_path))
        finally:
            sh.OUT_DIR = original_out_dir


class TestActualSavedSpecIfPresent:
    def test_saved_spec_matches_its_own_hash(self):
        out_dir = "outputs/level12b_stage_h_recurrence_spec"
        if not os.path.exists(f"{out_dir}/recurrence_spec.json"):
            pytest.skip("Work Package H recurrence spec not present in this environment")
        from experiments.level12b_stage_h_recurrence_spec import load_and_verify_recurrence_spec

        verified = load_and_verify_recurrence_spec(out_dir)
        assert verified["spec"]["version"] == "level1.2b-recurrence-spec-v1"
