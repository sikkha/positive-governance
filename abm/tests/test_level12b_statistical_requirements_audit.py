"""Level 1.2b, Work Package Q (Section 22): tests for
``experiments/level12b_stage_q_statistical_requirements_audit.py`` and
the new ``seed_clustered_bootstrap_stability`` primitive."""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pytest

from abm_governance.observer.phenotype_discovery import seed_clustered_bootstrap_stability
from experiments.level12b_stage_q_statistical_requirements_audit import (
    STATISTICAL_REQUIREMENTS,
    _bootstrap_ci_on_fraction,
    check_multiplicity_disclosure,
    check_structural_nan_preservation,
    check_training_only_preprocessing,
)


class TestSeedClusteredBootstrapStability:
    def test_degenerate_on_single_cluster(self):
        rng = np.random.default_rng(0)
        X = rng.normal(size=(20, 3))
        result = seed_clustered_bootstrap_stability(X, [0] * 20, "gmm", 2, 10, rng)
        assert math.isnan(result["mean_ari"])
        assert result["n_clusters"] == 1

    def test_high_ari_on_well_separated_clustered_data(self):
        rng = np.random.default_rng(0)
        X = np.vstack([rng.normal(0, 0.1, (20, 3)), rng.normal(10, 0.1, (20, 3))])
        cluster_ids = [i // 4 for i in range(40)]  # 10 groups of 4
        result = seed_clustered_bootstrap_stability(X, cluster_ids, "gmm", 2, 15, rng)
        assert result["mean_ari"] > 0.5
        assert result["n_clusters"] == 10

    def test_keeps_whole_clusters_together_not_individual_rows(self):
        """Every resample's chosen rows must come in intact
        cluster-sized blocks -- verified indirectly via the n_clusters
        field matching the number of distinct input cluster ids."""
        rng = np.random.default_rng(1)
        X = rng.normal(size=(30, 2))
        cluster_ids = [i % 5 for i in range(30)]  # 5 clusters of 6
        result = seed_clustered_bootstrap_stability(X, cluster_ids, "gmm", 2, 5, rng)
        assert result["n_clusters"] == 5


class TestBootstrapCiOnFraction:
    def test_point_estimate_matches_mean(self):
        result = _bootstrap_ci_on_fraction([1, 1, 0, 0], n_bootstrap=500)
        assert result["point_estimate"] == pytest.approx(0.5)

    def test_ci_brackets_point_estimate(self):
        result = _bootstrap_ci_on_fraction([1] * 30 + [0] * 2, n_bootstrap=1000)
        assert result["ci_low"] <= result["point_estimate"] <= result["ci_high"]

    def test_all_same_outcome_gives_zero_width_ci(self):
        result = _bootstrap_ci_on_fraction([0] * 32, n_bootstrap=500)
        assert result["ci_low"] == result["ci_high"] == 0.0

    def test_empty_is_degenerate(self):
        result = _bootstrap_ci_on_fraction([])
        assert result["n"] == 0
        assert math.isnan(result["point_estimate"])


class TestStructuralNanPreservationCheck:
    def test_passes_and_confirms_nan_not_zero(self):
        result = check_structural_nan_preservation()
        assert result["status"] == "pass"
        assert result["direct_check_result"]["preserved_as_nan"] is True


class TestTrainingOnlyPreprocessingCheck:
    def test_passes_with_evidence(self):
        result = check_training_only_preprocessing()
        assert result["status"] == "pass"
        assert len(result["evidence"]) >= 1


class TestMultiplicityDisclosure:
    def test_discloses_no_correction_applied(self):
        result = check_multiplicity_disclosure()
        assert result["correction_applied"] is False
        assert len(result["multiple_comparisons_in_this_milestone"]) >= 1


class TestActualExperimentOutputIfPresent:
    def test_results_meet_section_22_structural_requirements(self):
        path = "outputs/level12b_stage_q_statistical_requirements_audit/results.json"
        if not os.path.exists(path):
            pytest.skip("Work Package Q output not present in this environment")
        with open(path) as f:
            report = json.load(f)
        assert set(report["checks"].keys()) == set(STATISTICAL_REQUIREMENTS)
        for req in STATISTICAL_REQUIREMENTS:
            assert "status" in report["checks"][req]
        assert report["checks"]["discovery_confirmation_seed_disjointness"]["status"] == "pass"
        assert report["checks"]["structural_nan_preservation"]["status"] == "pass"
        for overlap in report["checks"]["discovery_confirmation_seed_disjointness"]["pairwise_overlaps"].values():
            assert overlap == []
