"""Level 1.2, Section 9: blind phenotype discovery pipeline."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.observer import phenotype_discovery as pd


def _record(C=0.5, E=0.5, L=0.5, D=0.5, M=0.5, R=0.5, S=0.5, F=0.5, V_eco=0.5, V_demo=0.5, H=0.5):
    return {
        "C": {"value": C}, "E": {"value": E}, "L": {"value": L}, "D": {"value": D},
        "M": {"value": M}, "R": {"value": R}, "S": {"value": S}, "F": {"value": F},
        "V": {"ecological": {"value": V_eco}, "demographic": {"value": V_demo}}, "H": {"value": H},
    }


DIMS = ("C", "E", "L", "D", "M", "R", "S", "F", "V", "H")


class TestBuildFeatureMatrix:
    def test_shape_and_v_split_into_two_columns(self):
        X, names = pd.build_feature_matrix([_record()], DIMS)
        assert X.shape == (1, 11)  # 9 scalar dims + V split into 2
        assert "V_ecological" in names and "V_demographic" in names

    def test_missing_dimension_preserved_as_nan(self):
        rec = _record()
        rec["C"]["value"] = float("nan")
        X, names = pd.build_feature_matrix([rec], DIMS)
        assert np.isnan(X[0, names.index("C")])


class TestMissingnessReport:
    def test_reports_fraction_per_feature(self):
        recs = [_record(C=1.0), _record(C=float("nan")), _record(C=2.0)]
        X, names = pd.build_feature_matrix(recs, DIMS)
        report = pd.missingness_report(X, names)
        assert report["C"] == pytest.approx(1 / 3)


class TestPreprocessFeatures:
    def test_complete_case_drops_rows_with_any_nan(self):
        recs = [_record(C=1.0), _record(C=float("nan"))]
        X, names = pd.build_feature_matrix(recs, DIMS)
        result = pd.preprocess_features(X, X, "complete_case")
        assert result["X_train"].shape[0] == 1

    def test_mean_impute_never_leaves_nan(self):
        recs = [_record(C=1.0), _record(C=float("nan")), _record(C=3.0)]
        X, names = pd.build_feature_matrix(recs, DIMS)
        result = pd.preprocess_features(X, X, "mean_impute")
        assert not np.isnan(result["X_train"]).any()

    def test_missingness_indicator_doubles_column_count(self):
        recs = [_record(C=1.0), _record(C=float("nan"))]
        X, names = pd.build_feature_matrix(recs, DIMS)
        result = pd.preprocess_features(X, X, "missingness_indicator")
        assert result["X_train"].shape[1] == X.shape[1] * 2

    def test_standardization_fit_on_train_only(self):
        X_train, _ = pd.build_feature_matrix([_record(C=0.0), _record(C=10.0)], DIMS)
        X_apply, _ = pd.build_feature_matrix([_record(C=100.0)], DIMS)
        result = pd.preprocess_features(X_train, X_apply, "mean_impute", standardize=True)
        # Applying train-fit standardization to a wildly different apply
        # set should NOT re-center apply to mean 0 -- it should reflect
        # train's own mean/std.
        assert result["X_apply"][0, 0] > 1.0  # far from train's mean in train's own std units

    def test_unknown_strategy_rejected(self):
        X, _ = pd.build_feature_matrix([_record()], DIMS)
        with pytest.raises(ValueError):
            pd.preprocess_features(X, X, "not_a_strategy")


class TestCollinearityAndPCA:
    def test_collinearity_matrix_shape(self):
        recs = [_record(C=float(i)) for i in range(10)]
        X, names = pd.build_feature_matrix(recs, DIMS)
        result = pd.examine_collinearity(X, names)
        assert len(result["correlation_matrix"]) == len(names)

    def test_pca_is_marked_diagnostic_only(self):
        recs = [_record(C=float(i), E=float(i) * 2) for i in range(10)]
        X, _ = pd.build_feature_matrix(recs, DIMS)
        result = pd.dimensionality_reduction_diagnostic(X, n_components=2)
        assert result["diagnostic_only"] is True
        assert len(result["explained_variance_ratio"]) <= 2


class TestFitCandidateAndKRange:
    def _clustered_X(self):
        rng = np.random.default_rng(0)
        cluster_a = rng.normal(0.0, 0.05, size=(15, 3))
        cluster_b = rng.normal(5.0, 0.05, size=(15, 3))
        return np.vstack([cluster_a, cluster_b])

    def test_k1_always_valid_for_gmm_and_hierarchical(self):
        X = self._clustered_X()
        for method in ("gmm", "hierarchical"):
            fit = pd.fit_candidate(X, method, k=1)
            assert set(fit["labels"].tolist()) == {0}

    def test_gmm_recovers_two_well_separated_clusters(self):
        X = self._clustered_X()
        fit = pd.fit_candidate(X, "gmm", k=2)
        assert len(set(fit["labels"].tolist())) == 2

    def test_hdbscan_never_takes_k_and_permits_noise(self):
        X = self._clustered_X()
        fit = pd.fit_candidate(X, "hdbscan")
        assert "k" in fit and fit["method"] == "hdbscan"
        # noise label -1 is a legitimate possible output, not an error
        assert set(fit["labels"].tolist()) <= set(range(-1, 10))

    def test_unknown_method_rejected(self):
        with pytest.raises(ValueError):
            pd.fit_candidate(self._clustered_X(), "kmeans_plus_plus")

    def test_compare_k_range_never_skips_k1_or_privileges_k3(self):
        X = self._clustered_X()
        results = pd.compare_k_range(X, "gmm", k_range=(1, 2, 3, 4))
        ks = [r["k"] for r in results]
        assert 1 in ks
        assert len(results) == 4  # k=3 gets no special treatment -- same count of results as any other k

    def test_compare_k_range_respects_sample_size(self):
        X = self._clustered_X()[:3]
        results = pd.compare_k_range(X, "gmm", k_range=(1, 2, 3, 4, 5, 6, 7, 8))
        assert all(r["k"] <= 3 for r in results)


class TestModelSelectionMetrics:
    def test_no_single_metric_decides_multiple_reported(self):
        rng = np.random.default_rng(1)
        X = np.vstack([rng.normal(0, 0.1, (10, 2)), rng.normal(5, 0.1, (10, 2))])
        fit = pd.fit_candidate(X, "gmm", k=2)
        metrics = pd.model_selection_metrics(X, fit["labels"], fit["model"], "gmm")
        for key in ("silhouette", "calinski_harabasz", "davies_bouldin", "cluster_size_balance", "bic", "aic"):
            assert key in metrics

    def test_single_cluster_yields_nan_silhouette(self):
        X = np.random.default_rng(2).normal(0, 1, (10, 2))
        labels = np.zeros(10, dtype=int)
        metrics = pd.model_selection_metrics(X, labels)
        assert np.isnan(metrics["silhouette"])

    def test_held_out_log_likelihood_uses_genuinely_separate_data(self):
        rng = np.random.default_rng(3)
        X_train = rng.normal(0, 1, (30, 2))
        X_heldout = rng.normal(0, 1, (10, 2))
        ll = pd.held_out_log_likelihood(X_train, X_heldout, k=1)
        assert ll == ll  # not NaN


class TestConsensus:
    def test_co_assignment_matrix_diagonal_is_one(self):
        labels_list = [np.array([0, 0, 1, 1]), np.array([0, 0, 1, 1])]
        co = pd.co_assignment_matrix(labels_list)
        assert np.allclose(np.diag(co), 1.0)

    def test_noise_points_never_co_assigned(self):
        labels_list = [np.array([-1, -1, 1, 1])]
        co = pd.co_assignment_matrix(labels_list)
        assert co[0, 1] == 0.0

    def test_variation_of_information_zero_for_identical_partitions(self):
        a = np.array([0, 0, 1, 1, 2, 2])
        assert pd.variation_of_information(a, a) == pytest.approx(0.0, abs=1e-9)

    def test_variation_of_information_positive_for_different_partitions(self):
        a = np.array([0, 0, 1, 1])
        b = np.array([0, 1, 0, 1])
        assert pd.variation_of_information(a, b) > 0.0

    def test_bootstrap_stability_high_for_well_separated_clusters(self):
        rng = np.random.default_rng(4)
        X = np.vstack([rng.normal(0, 0.05, (20, 2)), rng.normal(10, 0.05, (20, 2))])
        result = pd.bootstrap_stability(X, "gmm", k=2, n_bootstrap=5, rng=np.random.default_rng(5))
        assert result["mean_ari"] > 0.5

    def test_algorithm_agreement_reports_pairwise_ari_and_vi(self):
        labels_by_method = {"gmm": np.array([0, 0, 1, 1]), "hierarchical": np.array([0, 0, 1, 1])}
        agreement = pd.algorithm_agreement(labels_by_method)
        assert "gmm_vs_hierarchical" in agreement
        assert agreement["gmm_vs_hierarchical"]["ari"] == pytest.approx(1.0)
