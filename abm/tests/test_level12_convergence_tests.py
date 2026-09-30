"""Level 1.2, Section 11: inheritance vs. convergence tests."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.observer import convergence_tests as ct


class TestLineageDiversityWithinCluster:
    def test_single_shared_lineage_has_zero_diversity(self):
        result = ct.lineage_diversity_within_cluster([1, 1, 1, 1])
        assert result["simpson_diversity_index"] == pytest.approx(0.0)
        assert result["dominant_lineage_fraction"] == pytest.approx(1.0)
        assert result["n_distinct_lineages"] == 1

    def test_evenly_spread_lineages_have_high_diversity(self):
        result = ct.lineage_diversity_within_cluster([1, 2, 3, 4])
        assert result["simpson_diversity_index"] == pytest.approx(0.75)
        assert result["n_distinct_lineages"] == 4

    def test_empty_is_reported_not_crashed(self):
        result = ct.lineage_diversity_within_cluster([])
        assert result["n_members"] == 0
        assert result["simpson_diversity_index"] != result["simpson_diversity_index"]  # nan


class TestIndependentOriginPermutationTest:
    def test_homogeneous_cluster_scores_low_against_diverse_pool(self):
        rng = np.random.default_rng(0)
        all_lineages = list(range(1, 101))  # 100 distinct lineages
        cluster = [7, 7, 7, 7, 7]  # all one lineage -- maximally homogeneous
        result = ct.independent_origin_permutation_test(cluster, all_lineages, n_permutations=200, rng=rng)
        assert result["fraction_null_at_least_as_diverse"] > 0.9  # nearly every random draw is MORE diverse

    def test_diverse_cluster_scores_high_against_diverse_pool(self):
        rng = np.random.default_rng(0)
        all_lineages = list(range(1, 101))
        cluster = [1, 2, 3, 4, 5]  # 5 distinct lineages, as diverse as a typical random draw
        result = ct.independent_origin_permutation_test(cluster, all_lineages, n_permutations=200, rng=rng)
        assert result["fraction_null_at_least_as_diverse"] > 0.3

    def test_oversized_cluster_reported_not_crashed(self):
        result = ct.independent_origin_permutation_test([1, 2, 3], [1, 2], n_permutations=10, rng=np.random.default_rng(0))
        assert result["n_permutations"] == 0


class TestTransmissionLinkedFraction:
    def test_fully_linked_pairs(self):
        events = [
            {"source_institution_id": 1, "target_institution_id": 2},
            {"source_institution_id": 2, "target_institution_id": 3},
            {"source_institution_id": 1, "target_institution_id": 3},
        ]
        result = ct.transmission_linked_fraction([1, 2, 3], events)
        assert result["fraction_linked"] == pytest.approx(1.0)

    def test_no_transmission_events_among_members(self):
        events = [{"source_institution_id": 99, "target_institution_id": 100}]
        result = ct.transmission_linked_fraction([1, 2, 3], events)
        assert result["fraction_linked"] == pytest.approx(0.0)

    def test_single_member_undefined(self):
        result = ct.transmission_linked_fraction([1], [])
        assert result["fraction_linked"] != result["fraction_linked"]  # nan


class TestCrossConditionRecurrence:
    def test_requires_more_than_one_condition(self):
        assert ct.cross_condition_recurrence(["a", "a", "a"])["passed"] is False
        assert ct.cross_condition_recurrence(["a", "b"])["passed"] is True


class TestClassifyConvergenceOrInheritance:
    def test_insufficient_data_below_minimum_members(self):
        diversity = ct.lineage_diversity_within_cluster([1, 2])
        perm = {"fraction_null_at_least_as_diverse": 0.5}
        trans = {"fraction_linked": 0.0}
        cond = {"passed": True, "value": 2}
        result = ct.classify_convergence_or_inheritance(diversity, perm, trans, cond, min_members_for_classification=5)
        assert result["label"] == "insufficient_data"

    def test_inherited_when_single_lineage_dominates(self):
        diversity = ct.lineage_diversity_within_cluster([1, 1, 1, 1, 2])
        perm = {"fraction_null_at_least_as_diverse": 0.1}
        trans = {"fraction_linked": 0.1}
        cond = {"passed": True, "value": 2}
        result = ct.classify_convergence_or_inheritance(diversity, perm, trans, cond)
        assert result["label"] == "inherited"

    def test_inherited_when_majority_transmission_linked_even_with_diverse_lineages(self):
        diversity = ct.lineage_diversity_within_cluster([1, 2, 3, 4, 5])
        perm = {"fraction_null_at_least_as_diverse": 0.8}
        trans = {"fraction_linked": 0.9}
        cond = {"passed": True, "value": 2}
        result = ct.classify_convergence_or_inheritance(diversity, perm, trans, cond)
        assert result["label"] == "inherited"

    def test_convergent_when_diverse_unlinked_and_cross_condition(self):
        diversity = ct.lineage_diversity_within_cluster([1, 2, 3, 4, 5])
        perm = {"fraction_null_at_least_as_diverse": 0.8}
        trans = {"fraction_linked": 0.0}
        cond = {"passed": True, "value": 2}
        result = ct.classify_convergence_or_inheritance(diversity, perm, trans, cond)
        assert result["label"] == "convergent"

    def test_ambiguous_when_diverse_but_confined_to_one_condition(self):
        diversity = ct.lineage_diversity_within_cluster([1, 2, 3, 4, 5])
        perm = {"fraction_null_at_least_as_diverse": 0.8}
        trans = {"fraction_linked": 0.0}
        cond = {"passed": False, "value": 1}
        result = ct.classify_convergence_or_inheritance(diversity, perm, trans, cond)
        assert result["label"] == "ambiguous"

    def test_every_label_in_closed_vocabulary(self):
        labels = set()
        diversity = ct.lineage_diversity_within_cluster([1, 1, 1, 1, 2])
        labels.add(ct.classify_convergence_or_inheritance(diversity, {"fraction_null_at_least_as_diverse": 0.1}, {"fraction_linked": 0.1}, {"passed": True, "value": 2})["label"])
        diversity2 = ct.lineage_diversity_within_cluster([1, 2])
        labels.add(ct.classify_convergence_or_inheritance(diversity2, {"fraction_null_at_least_as_diverse": 0.5}, {"fraction_linked": 0.0}, {"passed": True, "value": 2})["label"])
        diversity3 = ct.lineage_diversity_within_cluster([1, 2, 3, 4, 5])
        labels.add(ct.classify_convergence_or_inheritance(diversity3, {"fraction_null_at_least_as_diverse": 0.8}, {"fraction_linked": 0.0}, {"passed": True, "value": 2})["label"])
        labels.add(ct.classify_convergence_or_inheritance(diversity3, {"fraction_null_at_least_as_diverse": 0.8}, {"fraction_linked": 0.0}, {"passed": False, "value": 1})["label"])
        assert labels <= set(ct.CONVERGENCE_CLASSIFICATION_LABELS)
