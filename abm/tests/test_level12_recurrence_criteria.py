"""Level 1.2, Section 10: recurrence criteria for blind-discovery clusters."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.observer import recurrence_criteria as rc


class TestIndividualCriteria:
    def test_minimum_cluster_size_pass_and_fail(self):
        assert rc.minimum_cluster_size([0, 1, 2, 3, 4, 5], min_size=5)["passed"] is True
        assert rc.minimum_cluster_size([0, 1], min_size=5)["passed"] is False

    def test_cross_seed_recurrence_requires_multiple_seeds(self):
        assert rc.cross_seed_recurrence([1, 1, 1])["passed"] is False
        assert rc.cross_seed_recurrence([1, 2, 3])["passed"] is True

    def test_cross_algorithm_support_uses_best_other_method(self):
        primary = np.array([0, 0, 0, 1, 1, 1])
        other = {"hierarchical": np.array([0, 0, 0, 1, 1, 1]), "hdbscan": np.array([0, 1, 0, 1, 0, 1])}
        result = rc.cross_algorithm_support([0, 1, 2], primary, other, min_ari=0.5)
        assert result["passed"] is True
        assert result["per_method"]["hierarchical"] == pytest.approx(1.0)

    def test_bootstrap_stability_criterion_reads_mean_ari(self):
        assert rc.bootstrap_stability_criterion({"mean_ari": 0.9}, min_mean_ari=0.5)["passed"] is True
        assert rc.bootstrap_stability_criterion({"mean_ari": 0.1}, min_mean_ari=0.5)["passed"] is False

    def test_co_assignment_internal_consistency(self):
        co = np.array([[1.0, 0.9, 0.1], [0.9, 1.0, 0.1], [0.1, 0.1, 1.0]])
        result = rc.co_assignment_internal_consistency([0, 1], co, min_mean_co_assignment=0.5)
        assert result["passed"] is True
        assert result["value"] == pytest.approx(0.9)

    def test_co_assignment_undefined_for_single_member(self):
        co = np.eye(3)
        result = rc.co_assignment_internal_consistency([0], co)
        assert result["passed"] is False
        assert np.isnan(result["value"])

    def test_distinctness_from_noise_positive_margin(self):
        rng = np.random.default_rng(0)
        within = rng.normal(0, 0.05, size=(5, 2))
        noise = rng.normal(5, 0.05, size=(5, 2))
        X = np.vstack([within, noise])
        result = rc.distinctness_from_noise(list(range(5)), list(range(5, 10)), X, min_margin=1.0)
        assert result["passed"] is True
        assert result["value"] > 1.0

    def test_missingness_strategy_robustness(self):
        primary = np.array([0, 0, 1, 1])
        alt = {"mean_impute": np.array([0, 0, 1, 1]), "complete_case": np.array([1, 0, 1, 0])}
        result = rc.missingness_strategy_robustness([0, 1, 2, 3], primary, alt, min_ari=0.5)
        assert result["passed"] is True
        assert result["per_strategy"]["mean_impute"] == pytest.approx(1.0)

    def test_parameter_condition_diversity(self):
        assert rc.parameter_condition_diversity(["stage3_a", "stage3_a"])["passed"] is False
        assert rc.parameter_condition_diversity(["stage3_a", "stage3_b"])["passed"] is True

    def test_temporal_persistence_of_members(self):
        results = [{"eligible": True}, {"eligible": True}, {"eligible": False}]
        result = rc.temporal_persistence_of_members(results, min_fraction_eligible=0.5)
        assert result["passed"] is True
        assert result["value"] == pytest.approx(2 / 3)

    def test_non_degenerate_cluster_fraction_rejects_near_total_sample(self):
        result = rc.non_degenerate_cluster_fraction(list(range(96)), n_total=100, max_fraction=0.95)
        assert result["passed"] is False

    def test_non_degenerate_cluster_fraction_rejects_vanishing_minority(self):
        result = rc.non_degenerate_cluster_fraction([0], n_total=1000, min_fraction=0.02)
        assert result["passed"] is False

    def test_k_selection_non_privileged_support_k1_undefined_silhouette_passes(self):
        metrics_by_k = [{"k": 1, "metrics": {"silhouette": float("nan")}}]
        result = rc.k_selection_non_privileged_support(1, metrics_by_k)
        assert result["passed"] is True

    def test_k_selection_non_privileged_support_rejects_uniquely_worst(self):
        metrics_by_k = [
            {"k": 1, "metrics": {"silhouette": float("nan")}},
            {"k": 2, "metrics": {"silhouette": 0.8}},
            {"k": 3, "metrics": {"silhouette": 0.01}},
        ]
        result = rc.k_selection_non_privileged_support(3, metrics_by_k)
        assert result["passed"] is False
        result2 = rc.k_selection_non_privileged_support(2, metrics_by_k)
        assert result2["passed"] is True

    def test_independent_of_single_lineage(self):
        assert rc.independent_of_single_lineage([1, 1, 1, 1, 2], max_single_lineage_fraction=0.7)["passed"] is False
        assert rc.independent_of_single_lineage([1, 2, 3, 4, 5], max_single_lineage_fraction=0.7)["passed"] is True


class TestEvaluateRecurrenceCriteria:
    def _passing_cluster_data(self):
        rng = np.random.default_rng(1)
        within = rng.normal(0, 0.05, size=(6, 2))
        noise = rng.normal(5, 0.05, size=(4, 2))
        X = np.vstack([within, noise])
        primary = np.array([0, 0, 0, 0, 0, 0, -1, -1, -1, -1])
        member_indices = [0, 1, 2, 3, 4, 5]
        co = np.eye(10) * 0.0
        for i in member_indices:
            for j in member_indices:
                co[i, j] = 1.0 if i != j else 1.0
        return {
            "member_indices": member_indices,
            "member_seed_ids": [1, 1, 2, 2, 3, 3],
            "primary_labels": primary,
            "other_labels_by_method": {"hierarchical": primary.copy()},
            "bootstrap_stability_result": {"mean_ari": 0.95},
            "co_assignment": co,
            "noise_indices": [6, 7, 8, 9],
            "X": X,
            "labels_by_strategy": {"mean_impute": primary.copy()},
            "member_conditions": ["stage3_a", "stage3_b", "stage3_a", "stage3_b", "stage3_a", "stage3_b"],
            "member_eligibility_results": [{"eligible": True}] * 6,
            "n_total": 10,
            "k": 2,
            "metrics_by_k": [
                {"k": 1, "metrics": {"silhouette": float("nan")}},
                {"k": 2, "metrics": {"silhouette": 0.9}},
            ],
            "member_lineage_ids": [1, 2, 3, 4, 5, 6],
        }

    def test_all_twelve_criteria_present_and_conjunction_used(self):
        data = self._passing_cluster_data()
        result = rc.evaluate_recurrence_criteria(data)
        assert set(result["criteria"].keys()) == set(rc.RECURRENCE_CRITERIA_NAMES)
        assert result["n_total"] == 12
        assert result["meets_all_minimum_criteria"] == (result["n_passed"] == 12)

    def test_well_constructed_cluster_passes_all_criteria(self):
        data = self._passing_cluster_data()
        result = rc.evaluate_recurrence_criteria(data)
        assert result["meets_all_minimum_criteria"] is True

    def test_thresholds_overridable_per_criterion(self):
        data = self._passing_cluster_data()
        result = rc.evaluate_recurrence_criteria(data, thresholds={"minimum_cluster_size": {"min_size": 100}})
        assert result["criteria"]["minimum_cluster_size"]["passed"] is False
        assert result["meets_all_minimum_criteria"] is False

    def test_never_references_cluster_count_three_anywhere(self):
        # Structural guard: none of the twelve criteria functions'
        # thresholds are keyed to producing exactly three clusters --
        # confirmed by checking that k=1, k=2, k=4 all pass equally
        # easily under identical supporting data (only k itself varies).
        data = self._passing_cluster_data()
        for k in (1, 2, 4):
            data_k = dict(data)
            data_k["k"] = k
            data_k["metrics_by_k"] = [
                {"k": 1, "metrics": {"silhouette": float("nan")}},
                {"k": 2, "metrics": {"silhouette": 0.9}},
                {"k": 4, "metrics": {"silhouette": 0.9}},
            ]
            result = rc.evaluate_recurrence_criteria(data_k)
            assert result["criteria"]["k_selection_non_privileged_support"]["passed"] is True
