"""Level 1.3, task #105: tests for ``experiments/level13_test_
requirements_audit.py``. Mirrors Level 1.2b's own Work Package R test
pattern (``tests/test_level12b_testing_requirements_audit.py``)."""

from __future__ import annotations

import json
import os

from experiments.level13_test_requirements_audit import (
    COVERAGE_MATRIX,
    run,
    verify_coverage_matrix,
)


class TestCoverageMatrixShape:
    def test_every_entry_lists_at_least_one_file_and_one_function(self):
        for category, spec in COVERAGE_MATRIX.items():
            assert spec["files"], category
            assert spec["functions"], category

    def test_at_least_twenty_categories(self):
        """A loose floor, not a magic number -- just confirms this
        audit is not vacuously small."""
        assert len(COVERAGE_MATRIX) >= 20


class TestVerifyCoverageMatrixMechanics:
    def test_every_category_verifies_as_pass(self):
        """The whole point of this task: every citation in
        COVERAGE_MATRIX must be mechanically confirmed to exist, not
        merely asserted -- this test is the actual gate."""
        findings = verify_coverage_matrix()
        failing = [c for c, v in findings.items() if v["status"] != "pass"]
        assert failing == [], f"stale coverage citations: {failing}"

    def test_a_fabricated_file_is_correctly_flagged_as_failing(self, monkeypatch):
        """Negative control: verify_coverage_matrix must actually be
        capable of catching a bad citation, not vacuously pass
        everything regardless of input."""
        import experiments.level13_test_requirements_audit as mod

        monkeypatch.setitem(
            mod.COVERAGE_MATRIX,
            "__fabricated_test_category__",
            {"files": ["tests/this_file_does_not_exist_anywhere.py"], "functions": ["nonexistent_fn"]},
        )
        findings = mod.verify_coverage_matrix()
        assert findings["__fabricated_test_category__"]["status"] == "fail"

    def test_a_fabricated_wrong_function_name_is_correctly_flagged(self, monkeypatch):
        import experiments.level13_test_requirements_audit as mod

        monkeypatch.setitem(
            mod.COVERAGE_MATRIX,
            "__fabricated_test_category_2__",
            {"files": ["tests/test_level13_entrenchment.py"], "functions": ["this_function_name_does_not_exist_xyz"]},
        )
        findings = mod.verify_coverage_matrix()
        assert findings["__fabricated_test_category_2__"]["status"] == "fail"


class TestRun:
    def test_run_reports_all_categories_covered(self):
        report = run()
        assert report["n_categories"] == len(COVERAGE_MATRIX)
        assert report["all_categories_covered"] is True
        assert report["missing_categories"] == []
        assert "scope_note" in report


class TestActualOutputIfPresent:
    def test_saved_results_report_full_coverage(self):
        import pytest

        path = "outputs/level13_test_requirements_audit/results.json"
        if not os.path.exists(path):
            pytest.skip("Level 1.3 test requirements audit output not present in this environment")
        with open(path) as f:
            report = json.load(f)
        assert report["all_categories_covered"] is True
        assert report["missing_categories"] == []
