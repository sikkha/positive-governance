"""Level 1.2b, Work Package K (Section 16): tests for
``experiments/level12b_stage_k_clustering_discovery.py``."""
from __future__ import annotations

import json
import math
import os

import pytest

from experiments.level12b_stage_k_clustering_discovery import (
    DISCOVERY_VERDICT_LABELS,
    PRIMARY_MISSINGNESS_STRATEGY,
    _select_headline_k,
    classify_discovery_verdict,
)


class TestSelectHeadlineK:
    def test_picks_highest_silhouette_among_k_geq_2(self):
        k_results = [
            {"k": 1, "metrics": {"silhouette": float("nan")}},
            {"k": 2, "metrics": {"silhouette": 0.2}},
            {"k": 3, "metrics": {"silhouette": 0.5}},
            {"k": 4, "metrics": {"silhouette": 0.3}},
        ]
        assert _select_headline_k(k_results) == 3

    def test_none_when_all_undefined(self):
        k_results = [{"k": 1, "metrics": {"silhouette": float("nan")}}, {"k": 2, "metrics": {"silhouette": float("nan")}}]
        assert _select_headline_k(k_results) is None

    def test_never_special_cases_k_equals_3(self):
        """k=3 wins here only because it happens to have the best
        silhouette in this specific input -- not because the function
        special-cases it; a permuted input with k=3 scoring worst must
        not pick k=3."""
        k_results = [
            {"k": 2, "metrics": {"silhouette": 0.9}},
            {"k": 3, "metrics": {"silhouette": 0.1}},
            {"k": 4, "metrics": {"silhouette": 0.2}},
        ]
        assert _select_headline_k(k_results) == 2


def _base_kwargs(**overrides):
    base = dict(
        n_total=576, n_hard_minimum=40,
        failure_label_fraction=0.3, cluster_vs_failure_ari=0.1,
        headline_k=3, best_bootstrap_mean_ari=0.6, best_algorithm_agreement_mean_ari=0.6,
        silhouette_by_k={1: float("nan"), 2: 0.2, 3: 0.5, 4: 0.25},
    )
    base.update(overrides)
    return base


class TestClassifyDiscoveryVerdict:
    def test_insufficient_evidence_below_hard_minimum(self):
        result = classify_discovery_verdict(**_base_kwargs(n_total=10))
        assert result["verdict"] == "insufficient_evidence"

    def test_insufficient_evidence_when_no_k_evaluable(self):
        result = classify_discovery_verdict(**_base_kwargs(headline_k=None))
        assert result["verdict"] == "insufficient_evidence"

    def test_failure_dominated_when_cluster_recreates_failure_split(self):
        result = classify_discovery_verdict(**_base_kwargs(cluster_vs_failure_ari=0.9))
        assert result["verdict"] == "failure_dominated"

    def test_unstable_when_neither_bootstrap_nor_agreement_clears_bar(self):
        result = classify_discovery_verdict(**_base_kwargs(best_bootstrap_mean_ari=0.1, best_algorithm_agreement_mean_ari=0.05))
        assert result["verdict"] == "unstable"

    def test_stable_via_bootstrap_alone_is_enough(self):
        result = classify_discovery_verdict(**_base_kwargs(best_bootstrap_mean_ari=0.6, best_algorithm_agreement_mean_ari=float("nan")))
        assert result["verdict"] != "unstable"

    def test_one_config_when_no_k_clears_silhouette_bar(self):
        result = classify_discovery_verdict(**_base_kwargs(silhouette_by_k={1: float("nan"), 2: 0.05, 3: 0.1}))
        assert result["verdict"] == "one_config"

    def test_continuum_when_many_ks_are_near_the_best(self):
        result = classify_discovery_verdict(**_base_kwargs(
            headline_k=3, silhouette_by_k={2: 0.48, 3: 0.5, 4: 0.49, 5: 0.47},
        ))
        assert result["verdict"] == "continuum"

    def test_multi_config_when_single_peaked_and_stable(self):
        result = classify_discovery_verdict(**_base_kwargs(
            headline_k=3, silhouette_by_k={2: 0.1, 3: 0.5, 4: 0.15},
        ))
        assert result["verdict"] == "multi_config"

    def test_verdict_always_in_closed_vocabulary(self):
        for overrides in [
            {"n_total": 5}, {"cluster_vs_failure_ari": 0.9}, {"best_bootstrap_mean_ari": 0.0, "best_algorithm_agreement_mean_ari": 0.0},
            {"silhouette_by_k": {}}, {},
        ]:
            result = classify_discovery_verdict(**_base_kwargs(**overrides))
            assert result["verdict"] in DISCOVERY_VERDICT_LABELS


class TestPrimaryMissingnessStrategyPreregistered:
    def test_primary_strategy_is_one_of_the_three(self):
        from abm_governance.observer.phenotype_discovery import MISSINGNESS_STRATEGIES

        assert PRIMARY_MISSINGNESS_STRATEGY in MISSINGNESS_STRATEGIES

    def test_primary_strategy_never_drops_rows(self):
        """mean_impute (the chosen primary) must never drop a row --
        the documented reason for choosing it over complete_case."""
        import numpy as np

        from abm_governance.observer.phenotype_discovery import preprocess_features

        X = np.array([[1.0, float("nan")], [2.0, 3.0], [float("nan"), 5.0]])
        result = preprocess_features(X, X, PRIMARY_MISSINGNESS_STRATEGY)
        assert result["apply_mask"].sum() == X.shape[0]


class TestActualExperimentOutputIfPresent:
    def test_results_meet_section_16_structural_requirements(self):
        out_dir = "outputs/level12b_stage_k_clustering_discovery"
        if not os.path.exists(f"{out_dir}/results.json"):
            pytest.skip("Work Package K experiment output not present in this environment")
        with open(f"{out_dir}/results.json") as f:
            report = json.load(f)
        assert report["n_total"] > 0
        assert report["source_design_hash"]
        assert report["preregistration_manifest_hash"]
        assert report["verdict"]["verdict"] in DISCOVERY_VERDICT_LABELS
        assert set(report["k_range_results"].keys()) == {"gmm", "hierarchical"}
        for method_results in report["k_range_results"].values():
            ks = [r["k"] for r in method_results]
            assert 1 in ks  # k=1 always evaluated as the valid null
        assert "hdbscan_result" in report
        assert report["candidate_independence_note"]
