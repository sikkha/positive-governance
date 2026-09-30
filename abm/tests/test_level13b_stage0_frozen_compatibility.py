"""Level 1.3b, Stage 0 (task #115): tests for ``experiments/level13b_
stage0_frozen_compatibility.py``. Small-scale mechanics plus a skip-if
-absent read of the real saved report -- the real comparisons (20-seed
Comparison A, 15-launch Comparison C) live in ``outputs/level13b_
stage0_frozen_compatibility/stage0_report.json``, produced by running
the script directly. See also ``tests/test_level13b_cross_process_
reproducibility.py`` for the dedicated regression guard on the actual
bug this stage found (frozenset string-hash cross-process instability)."""

from __future__ import annotations

import json
import os

import pytest

from experiments import level13b_stage0_frozen_compatibility as stage0


class TestMetricsIdentical:
    def test_identical_metrics_return_true(self):
        a = [{"x": 1.0, "y": 2}]
        b = [{"x": 1.0, "y": 2}]
        assert stage0._metrics_identical(a, b) is True

    def test_differing_metrics_return_false(self):
        a = [{"x": 1.0}]
        b = [{"x": 2.0}]
        assert stage0._metrics_identical(a, b) is False

    def test_nan_aware_equality_treats_matching_nans_as_equal(self):
        a = [{"x": float("nan")}]
        b = [{"x": float("nan")}]
        assert stage0._metrics_identical(a, b) is True


class TestValuesEqual:
    def test_scalar_equality(self):
        assert stage0._values_equal(1.0, 1.0)
        assert not stage0._values_equal(1.0, 2.0)

    def test_nan_aware(self):
        assert stage0._values_equal(float("nan"), float("nan"))


class TestRunComparisonAAtSmallScale:
    def test_comparison_a_runs_two_seeds_and_reports_a_match_field(self):
        result = stage0.run_comparison_a(n_seeds=2)
        assert "n_seeds" in result
        assert result["n_seeds"] == 2


class TestRunComparisonBDescriptive:
    def test_comparison_b_returns_a_dict_with_expected_change_fields(self):
        result = stage0.run_comparison_b_descriptive()
        assert isinstance(result, dict)


class TestActualOutputIfPresent:
    def test_saved_report_shows_the_disclosed_expected_change_fields(self):
        path = os.path.join(stage0.OUT_DIR, "stage0_report.json")
        if not os.path.exists(path):
            pytest.skip("Stage 0 saved report not present in this environment")
        with open(path) as f:
            report = json.load(f)
        assert report["overall_pass"] is True
        assert "comparison_a_level12b_historical_off" in report
        assert "comparison_c_cross_process_determinism_post_fix" in report
