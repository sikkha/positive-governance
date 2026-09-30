"""Level 1.3b, Stage 9 (task #122): tests for ``experiments/level13b_
stage9_measurement_audit.py``. Small-scale mechanics using real, freshly
-simulated component records (2-4 runs) -- the real 240-run archived
result lives in ``outputs/level13b_stage9_measurement_audit/
recomputed_records.json``, produced by running the script directly."""

from __future__ import annotations

import json
import os

import numpy as np
import pytest

from experiments import level13b_stage9_measurement_audit as stage9
from experiments.level13b_stage4_homogeneous_discovery import _load_ecological_points, lhs_draws


def _small_records(n=4):
    eco_points = _load_ecological_points()
    draws = lhs_draws(n=n, seed=1)
    return [stage9._job((i, draw, 9_990_000 + i, eco_points)) for i, draw in enumerate(draws)]


class TestAllComponents:
    def test_eight_distinct_components_disjoint_s_and_z(self):
        """4 S_obs response dims + performance_legitimacy (5) + 2 Z_obs
        response dims + procedural_legitimacy (3) = 8 total. (This
        module's own docstring says "7 distinct dimensions total" --
        a minor pre-existing counting slip in that prose; the actual
        ALL_COMPONENTS tuple, and every function that uses it, is
        correct and is what this test checks against.)"""
        from abm_governance.observer.sz_obs import S_OBS_RESPONSE_DIMENSIONS, Z_OBS_RESPONSE_DIMENSIONS
        assert len(stage9.ALL_COMPONENTS) == 8
        assert set(S_OBS_RESPONSE_DIMENSIONS) & set(Z_OBS_RESPONSE_DIMENSIONS) == set()


class TestJob:
    def test_job_returns_all_seven_components_and_recomputed_scores(self):
        records = _small_records(n=1)
        r = records[0]
        assert set(r["components"].keys()) == set(stage9.ALL_COMPONENTS)
        assert isinstance(r["S_obs_recomputed"], float)
        assert isinstance(r["Z_obs_recomputed"], float)


class TestPearsonAndRawCorrelation:
    def test_pearson_of_identical_arrays_is_one(self):
        a = np.array([1.0, 2.0, 3.0, 4.0])
        assert np.isclose(stage9._pearson(a, a), 1.0)

    def test_pearson_returns_nan_for_constant_array(self):
        a = np.array([1.0, 1.0, 1.0])
        b = np.array([1.0, 2.0, 3.0])
        assert np.isnan(stage9._pearson(a, b))

    def test_raw_correlation_on_small_pool_is_a_finite_or_nan_float(self):
        records = _small_records(n=4)
        corr = stage9.raw_correlation(records)
        assert isinstance(corr, float)


class TestPartialCorrelationAndWithinBetween:
    def test_partial_correlation_returns_strata_list(self):
        records = _small_records(n=4)
        result = stage9.partial_correlation_controlling_stratum(records)
        assert "partial_correlation" in result
        assert isinstance(result["strata"], list)

    def test_within_and_between_point_correlation_shape(self):
        records = _small_records(n=4)
        result = stage9.within_and_between_point_correlation(records)
        assert "within_point_correlation" in result
        assert "between_point_correlation" in result
        assert result["n_points"] == 4


class TestFactorStructureAndLeaveOneOut:
    def test_factor_structure_analysis_returns_eight_component_names(self):
        records = _small_records(n=4)
        result = stage9.factor_structure_analysis(records)
        assert result["component_names"] == list(stage9.ALL_COMPONENTS)
        assert len(result["pc1_loadings"]) == 8

    def test_leave_one_out_variant_covers_all_seven_components(self):
        records = _small_records(n=4)
        result = stage9.leave_one_out_variant(records)
        assert set(result["leave_one_out_correlations"].keys()) == set(stage9.ALL_COMPONENTS)


class TestVariants:
    def test_non_normalized_variant_returns_both_correlations(self):
        records = _small_records(n=4)
        result = stage9.non_normalized_variant(records)
        assert "sum_variant_correlation" in result and "mean_variant_correlation_for_comparison" in result

    def test_equal_weight_variant_returns_both_correlations(self):
        records = _small_records(n=4)
        result = stage9.equal_weight_variant(records)
        assert "equal_weight_correlation" in result and "pca_weighted_correlation" in result

    def test_opportunity_denominated_variant_returns_a_correlation(self):
        records = _small_records(n=4)
        result = stage9.opportunity_denominated_variant(records)
        assert "opportunity_denominated_correlation" in result


class TestVerifyAgainstArchive:
    def test_exact_reproduction_true_on_the_real_archive(self):
        if not os.path.exists(stage9.STAGE4_RECORDS_PATH):
            pytest.skip("Stage 4 archive not present in this environment")
        recomputed_path = os.path.join(stage9.OUT_DIR, "recomputed_records.json")
        if not os.path.exists(recomputed_path):
            pytest.skip("Stage 9 recomputed_records.json not present in this environment")
        with open(recomputed_path) as f:
            recomputed = json.load(f)["records"]
        consistency = stage9.verify_against_archive(recomputed)
        assert consistency["exact_reproduction"] is True


class TestActualOutputIfPresent:
    def test_saved_report_shows_exact_reproduction_and_disjoint_axes(self):
        path = os.path.join(stage9.OUT_DIR, "stage9_report.json")
        if not os.path.exists(path):
            pytest.skip("Stage 9 saved report not present in this environment")
        with open(path) as f:
            report = json.load(f)
        assert report["consistency_check_against_stage4_archive"]["exact_reproduction"] is True
        assert report["structural_fact_measurement_overlap"]["shared_dimensions"] == []
        assert report["redefinition_status"].startswith("observer/sz_obs.py was NOT modified")
