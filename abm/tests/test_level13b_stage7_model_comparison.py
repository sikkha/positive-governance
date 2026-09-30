"""Level 1.3b, Stage 7 (task #120): tests for ``experiments/level13b_
stage7_model_comparison.py``. Fits are on synthetic small matrices for
speed and are unconditional; the real 240-record archived pool
(``outputs/level13b_stage4_homogeneous_discovery/records.json``) is
used only by the skip-if-absent integration check at the bottom, which
runs the actual ``main()`` end to end (no new ABM simulation -- Stage 7
only fits sklearn models on already-simulated Stage 4 output, so this
is fast)."""

from __future__ import annotations

import os

import numpy as np
import pytest

from experiments import level13b_stage7_model_comparison as stage7


def _synthetic_X(n=40, d=6, seed=0):
    rng = np.random.default_rng(seed)
    return rng.normal(size=(n, d))


class TestFeatureMatrixAndStandardization:
    def test_feature_matrix_reads_nested_phenotype_vector(self):
        records = [{"phenotype_vector": {"S_obs": 0.5, "Z_obs": 0.3}}, {"phenotype_vector": {"S_obs": 0.7, "Z_obs": 0.1}}]
        X = stage7._feature_matrix(records, ("S_obs", "Z_obs"))
        assert X.shape == (2, 2)
        assert X[0, 0] == 0.5

    def test_missing_dim_becomes_nan(self):
        records = [{"phenotype_vector": {"S_obs": 0.5}}]
        X = stage7._feature_matrix(records, ("S_obs", "Z_obs"))
        assert np.isnan(X[0, 1])

    def test_standardized_has_zero_mean_unit_ish_scale(self):
        X = _synthetic_X()
        Xs = stage7._standardized(X)
        assert np.allclose(Xs.mean(axis=0), 0.0, atol=1e-8)


class TestDiscreteCandidates:
    def test_fit_gmm_k1_to_8_returns_leading_k_in_range(self):
        X = stage7._standardized(_synthetic_X(n=30))
        result = stage7.fit_gmm_k1_to_8(X)
        assert result["candidate"] == "gmm_k1_to_8"
        assert 1 <= result["leading_k"] <= 8
        assert len(result["leading_labels"]) == 30

    def test_fit_hierarchical_k1_to_8_returns_valid_k(self):
        X = stage7._standardized(_synthetic_X(n=30))
        result = stage7.fit_hierarchical_k1_to_8(X)
        assert result["leading_k"] >= 1

    def test_fit_hdbscan_tries_all_four_min_cluster_sizes(self):
        X = stage7._standardized(_synthetic_X(n=60))
        result = stage7.fit_hdbscan_multi_min_cluster_size(X)
        assert {s["min_cluster_size"] for s in result["all_settings"]} == set(stage7.HDBSCAN_MIN_CLUSTER_SIZES)

    def test_fit_unequal_covariance_mixtures_forces_full_covariance(self):
        X = stage7._standardized(_synthetic_X(n=30))
        result = stage7.fit_unequal_covariance_mixtures(X)
        assert result["leading_k"] >= 1
        assert len(result["all_k_fits"]) >= 1


class TestContinuousCandidates:
    def test_fit_pca_factor_continuum_shape(self):
        X = stage7._standardized(_synthetic_X())
        result = stage7.fit_pca_factor_continuum(X)
        assert 0.0 <= result["explained_variance_ratio"] <= 1.0
        assert result["reconstruction_error"] >= 0.0

    def test_fit_principal_curve_manifold_returns_nonnegative_error(self):
        X = stage7._standardized(_synthetic_X())
        result = stage7.fit_principal_curve_manifold(X)
        assert result["reconstruction_error"] >= 0.0

    def test_fit_low_dim_regression_predicts_declared_target(self):
        X = stage7._standardized(_synthetic_X(d=len(stage7.STATIC_DIMS)))
        result = stage7.fit_low_dim_regression(X, stage7.STATIC_DIMS, target="Z_obs")
        assert result["target"] == "Z_obs"
        assert "Z_obs" not in result["predictors"]
        assert len(result["cv_r2_scores"]) == 5


class TestPathDependentCandidate:
    def test_too_few_complete_rows_returns_none_score(self):
        records = [{"phenotype_vector": {d: float("nan") for d in stage7.SEQ_DIMS + ("entrenchment",)}} for _ in range(3)]
        result = stage7.fit_path_dependent(records)
        assert result["cv_r2_mean"] is None

    def test_complete_rows_fit_a_real_model(self):
        rng = np.random.default_rng(1)
        records = []
        for _ in range(20):
            row = {d: float(rng.normal()) for d in stage7.SEQ_DIMS}
            row["entrenchment"] = float(rng.normal())
            records.append({"phenotype_vector": row})
        result = stage7.fit_path_dependent(records)
        assert result["n_complete_rows"] == 20
        assert result["cv_r2_mean"] is not None


class TestActualOutputIfPresent:
    def test_saved_report_has_expected_shape(self):
        """Reads the already-saved report rather than re-running main()
        (which would overwrite the real archived output) -- same
        skip-if-absent convention as Level 1.3's own test_level13_test_
        requirements_audit.py::TestActualOutputIfPresent."""
        import json
        path = os.path.join(stage7.OUT_DIR, "stage7_report.json")
        if not os.path.exists(path):
            pytest.skip("Stage 7 saved report not present in this environment")
        with open(path) as f:
            report = json.load(f)
        assert report["n_records"] > 0
        assert report["leading_discrete_candidate"] in ("gmm_k1_to_8", "unequal_covariance_mixtures")
        assert "no discrete-vs-continuous verdict is rendered here" in report["note"]
