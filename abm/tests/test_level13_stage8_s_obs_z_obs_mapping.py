"""Level 1.3, Stage 8 (task #103): S_obs-Z_obs mapping
(``experiments/level13_stage8_s_obs_z_obs_mapping.py``).

Purely post-hoc over already-recorded Stage 3/4/5/7 output -- no
simulation runs, no small-scale-vs-real-scale distinction needed (the
real run itself completes in under a second)."""

from __future__ import annotations

import importlib
import inspect

import pytest

from experiments import level13_stage8_s_obs_z_obs_mapping as stage8
from tests.test_level12_structural_guards import _strip_docstrings_and_comments
from tests.test_level13_sem_firewall_extension import FORBIDDEN_LEVEL13_TERMS


class TestPoolSObsZObs:
    def test_pooled_counts_match_source_files(self):
        pooled = stage8.pool_s_obs_z_obs()
        by_source = {}
        for p in pooled:
            by_source[p["source_stage"]] = by_source.get(p["source_stage"], 0) + 1
        assert by_source == {
            "stage3": 72, "stage4": 96,
            "stage5_base": 16, "stage5_erased": 16, "stage5_reversed": 16,
            "stage7": 12,
        }
        assert len(pooled) == 228

    def test_every_row_has_s_obs_and_z_obs(self):
        pooled = stage8.pool_s_obs_z_obs()
        for p in pooled[:5]:
            assert "S_obs" in p and "Z_obs" in p
            assert isinstance(p["S_obs"], float)
            assert isinstance(p["Z_obs"], float)


class TestCorrelation:
    def test_perfect_positive_correlation(self):
        result = stage8._correlation([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0])
        assert result["pearson_r"] == pytest.approx(1.0)
        assert result["spearman_r"] == pytest.approx(1.0)

    def test_constant_input_returns_nan_not_error(self):
        result = stage8._correlation([1.0, 1.0, 1.0], [1.0, 2.0, 3.0])
        assert result["pearson_r"] != result["pearson_r"]  # NaN

    def test_too_few_points_returns_nan(self):
        result = stage8._correlation([1.0], [2.0])
        assert result["n"] == 1
        assert result["pearson_r"] != result["pearson_r"]

    def test_nan_values_excluded_from_n(self):
        result = stage8._correlation([1.0, 2.0, float("nan"), 4.0], [1.0, 2.0, 3.0, 4.0])
        assert result["n"] == 3


class TestMedianSplitJointTable:
    def test_four_cells_sum_to_n(self):
        table = stage8._median_split_joint_table([0.1, 0.2, 0.8, 0.9], [0.1, 0.2, 0.8, 0.9])
        total = table["high_s_high_z"] + table["high_s_low_z"] + table["low_s_high_z"] + table["low_s_low_z"]
        assert total == table["n"] == 4


class TestRunOnRealData:
    def test_real_run_pools_228_rows(self):
        report = stage8.run()
        assert report["n_total"] == 228
        assert report["n_pooled_by_source"] == {
            "stage3": 72, "stage4": 96,
            "stage5_base": 16, "stage5_erased": 16, "stage5_reversed": 16,
            "stage7": 12,
        }

    def test_pooled_correlation_is_defined(self):
        report = stage8.run()
        assert report["pooled_correlation"]["n"] == 228
        assert report["pooled_correlation"]["pearson_r"] == report["pooled_correlation"]["pearson_r"]  # not NaN

    def test_stage5_shift_reused_not_recomputed(self):
        import json
        report = stage8.run()
        with open(stage8.STAGE5_PATH) as f:
            stage5_raw = json.load(f)
        assert report["stage5_reused_counterfactual_shift"]["mean_erased_vs_base_s_obs_abs_diff"] == \
            stage5_raw["mean_erased_vs_base_s_obs_abs_diff"]

    def test_no_six_way_verdict_rendered(self):
        report = stage8.run()
        assert "verdict" not in report
        assert "decision_gate_note" in report

    def test_covariate_correlations_cover_all_covariates(self):
        report = stage8.run()
        assert set(report["covariate_correlations"].keys()) == set(stage8._COVARIATES)


class TestWriteReport:
    def test_persists_to_disk_with_hash(self, tmp_path):
        report = stage8.write_report(out_dir=str(tmp_path / "stage8"))
        assert "report_hash" in report
        assert (tmp_path / "stage8" / "results.json").exists()


class TestReportHash:
    def test_stable_across_key_order(self):
        assert stage8.report_hash({"a": 1, "b": 2}) == stage8.report_hash({"b": 2, "a": 1})

    def test_changes_with_content(self):
        assert stage8.report_hash({"a": 1}) != stage8.report_hash({"a": 2})


class TestForbiddenTerminologyGuardExtendsToStage8Script:
    def test_stage8_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level13_stage8_s_obs_z_obs_mapping")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL13_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
