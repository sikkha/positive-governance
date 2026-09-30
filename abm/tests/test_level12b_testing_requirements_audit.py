"""Level 1.2b, Work Package R (Section 23): tests for
``experiments/level12b_stage_r_testing_requirements_audit.py``."""
from __future__ import annotations

import json
import os

import pytest

from experiments.level12b_stage_r_testing_requirements_audit import (
    COVERAGE_MATRIX,
    run,
    verify_coverage_matrix,
)

#: The literal enumerated category set Section 23 names (mirrored here,
#: independently of COVERAGE_MATRIX's own keys, so a future accidental
#: rename/drop of a category in COVERAGE_MATRIX is caught by a test
#: failure rather than silently shrinking coverage).
EXPECTED_SECTION_23_CATEGORIES = frozenset(
    {
        "ledger_identities", "ratios", "strata", "run_count_arithmetic",
        "hashing_versioning", "feature_numerators_denominators", "missingness",
        "temporal_windows", "aggregation", "recurrence_audit", "lineage",
        "k_equals_1", "synthetic_cluster_ground_truth", "permutation_invariance",
        "bootstrap_matching", "consensus_co_assignment", "training_only_preprocessing",
        "discovery_confirmation_separation", "ic_pairing",
        "population_resource_conservation", "mechanism_substream_isolation",
        "serial_parallel_equivalence", "cross_process_reproducibility",
        "sem_firewall", "terminology_guard",
    }
)


class TestCoverageMatrixCategorySet:
    def test_matrix_covers_every_expected_section_23_category(self):
        assert set(COVERAGE_MATRIX.keys()) == EXPECTED_SECTION_23_CATEGORIES

    def test_every_entry_lists_at_least_one_file_and_one_function(self):
        for category, spec in COVERAGE_MATRIX.items():
            assert spec["files"], category
            assert spec["functions"], category


class TestVerifyCoverageMatrixMechanics:
    def test_every_category_verifies_as_pass(self):
        """The whole point of this Work Package: every citation in
        COVERAGE_MATRIX must be mechanically confirmed to exist, not
        merely asserted -- this test is the actual gate."""
        findings = verify_coverage_matrix()
        failing = [c for c, v in findings.items() if v["status"] != "pass"]
        assert failing == [], f"stale coverage citations: {failing}"

    def test_a_fabricated_file_is_correctly_flagged_as_failing(self, monkeypatch):
        """Negative control: verify_coverage_matrix must actually be
        capable of catching a bad citation, not vacuously pass
        everything regardless of input."""
        import experiments.level12b_stage_r_testing_requirements_audit as mod

        monkeypatch.setitem(
            mod.COVERAGE_MATRIX,
            "__fabricated_test_category__",
            {"files": ["tests/this_file_does_not_exist_anywhere.py"], "functions": ["nonexistent_fn"]},
        )
        findings = mod.verify_coverage_matrix()
        assert findings["__fabricated_test_category__"]["status"] == "fail"

    def test_a_fabricated_wrong_function_name_is_correctly_flagged(self, monkeypatch):
        import experiments.level12b_stage_r_testing_requirements_audit as mod

        monkeypatch.setitem(
            mod.COVERAGE_MATRIX,
            "__fabricated_test_category_2__",
            {"files": ["tests/test_level12b_ecological_ledger.py"], "functions": ["this_function_name_does_not_exist_xyz"]},
        )
        findings = mod.verify_coverage_matrix()
        assert findings["__fabricated_test_category_2__"]["status"] == "fail"


class TestRun:
    def test_run_reports_all_categories_covered(self):
        report = run()
        assert report["n_categories"] == len(EXPECTED_SECTION_23_CATEGORIES)
        assert report["all_categories_covered"] is True
        assert report["missing_categories"] == []


class TestActualOutputIfPresent:
    def test_saved_results_report_full_coverage(self):
        path = "outputs/level12b_stage_r_testing_requirements_audit/results.json"
        if not os.path.exists(path):
            pytest.skip("Work Package R output not present in this environment")
        with open(path) as f:
            report = json.load(f)
        assert report["all_categories_covered"] is True
        assert report["missing_categories"] == []
        assert report["n_categories"] == len(EXPECTED_SECTION_23_CATEGORIES)
