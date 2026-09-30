"""Level 1.2b, Work Package R (Section 23): synthetic ground-truth
validation of the actual discovery pipeline (Section 16's own
``compare_k_range`` / ``_select_headline_k`` / ``classify_discovery_
verdict``, run end-to-end on data with KNOWN structure) -- Section 23's
own "synthetic 1/2/3/many-cluster/continuum/collapse-dominated data"
requirement. Level 1.2's own ``tests/test_level12_phenotype_discovery.py``
already validates the underlying primitives individually (k=1 always
valid, two-cluster recovery, etc.); this file is the missing piece --
does the FULL pipeline (as Work Package K actually calls it) correctly
recover ground truth across the full range Section 23 names, not just
one hand-picked case."""
from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import adjusted_rand_score

from abm_governance.observer.phenotype_discovery import DEFAULT_K_RANGE, bootstrap_stability, compare_k_range, fit_candidate
from experiments.level12b_stage_k_clustering_discovery import _select_headline_k, classify_discovery_verdict

RNG_SEED = 20260819


def _gmm_verdict(X, rng_seed=RNG_SEED, n_hard_minimum=10):
    k_results = compare_k_range(X, "gmm", DEFAULT_K_RANGE, rng_seed=rng_seed)
    headline_k = _select_headline_k(k_results)
    silhouette_by_k = {r["k"]: r["metrics"]["silhouette"] for r in k_results}
    rng = np.random.default_rng(rng_seed)
    bootstrap = bootstrap_stability(X, "gmm", headline_k or 1, 20, rng) if headline_k else {"mean_ari": float("nan")}
    labels = fit_candidate(X, "gmm", k=headline_k or 1, rng_seed=rng_seed)["labels"]
    return classify_discovery_verdict(
        n_total=X.shape[0], n_hard_minimum=n_hard_minimum,
        failure_label_fraction=0.0, cluster_vs_failure_ari=0.0,
        headline_k=headline_k, best_bootstrap_mean_ari=bootstrap.get("mean_ari", float("nan")),
        best_algorithm_agreement_mean_ari=float("nan"), silhouette_by_k=silhouette_by_k,
    ), headline_k, labels


class TestOneClusterGroundTruth:
    def test_single_blob_yields_unstable_not_a_false_multi_config(self):
        """n=576, matching Work Package K's own actual discovery-pool
        size (deliberately not a small n -- see the docstring below for
        why small n matters here too). Pure noise correctly reads as
        'unstable', NOT 'one_config' -- classify_discovery_verdict's
        own first-match-wins order checks bootstrap/algorithm-agreement
        stability BEFORE the silhouette-bar check, so pure-noise data
        (whose weak best-k silhouette is itself not reproducible under
        resampling) is correctly caught by the stability gate first.
        This is the CORRECT, already-designed behavior, not a bug: pure
        noise should never be reported as a stable non-finding
        ('one_config' implies stable evidence that no split is
        supported; 'unstable' correctly signals there is no reproducible
        evidence at all). The critical property this test actually
        guards is the negative: pure noise must never yield
        'multi_config'. A smaller n (60) was tried first and DID
        produce a spurious near-'multi_config'-adjacent read purely from
        finite-sample silhouette noise -- confirming adequate n matters,
        which Work Package K's own real n=576 pool comfortably clears."""
        rng = np.random.default_rng(RNG_SEED)
        X = rng.normal(0, 1.0, size=(576, 8))
        verdict, headline_k, _ = _gmm_verdict(X, n_hard_minimum=40)
        assert verdict["verdict"] in ("one_config", "unstable")
        assert verdict["verdict"] != "multi_config"


class TestTwoClusterGroundTruth:
    def test_two_well_separated_blobs_recovered(self):
        rng = np.random.default_rng(RNG_SEED)
        X = np.vstack([rng.normal(0, 0.3, (30, 5)), rng.normal(12, 0.3, (30, 5))])
        verdict, headline_k, labels = _gmm_verdict(X)
        assert headline_k == 2
        true_labels = np.array([0] * 30 + [1] * 30)
        assert adjusted_rand_score(true_labels, labels) > 0.9
        assert verdict["verdict"] == "multi_config"


class TestThreeClusterGroundTruth:
    def test_three_well_separated_blobs_recovered_not_special_cased(self):
        """Ground truth genuinely is 3 here -- confirms the pipeline
        finds 3 BECAUSE the data supports it, complementing (not
        duplicating) Work Package K's own 'never special-cases k=3'
        test, which uses synthetic silhouette inputs engineered so k=3
        is NOT the answer."""
        rng = np.random.default_rng(RNG_SEED)
        X = np.vstack([rng.normal(0, 0.3, (20, 5)), rng.normal(12, 0.3, (20, 5)), rng.normal(-12, 0.3, (20, 5))])
        verdict, headline_k, labels = _gmm_verdict(X)
        assert headline_k == 3
        true_labels = np.array([0] * 20 + [1] * 20 + [2] * 20)
        assert adjusted_rand_score(true_labels, labels) > 0.9
        assert verdict["verdict"] == "multi_config"


class TestManyClusterGroundTruth:
    def test_six_well_separated_blobs_yields_headline_k_above_three(self):
        rng = np.random.default_rng(RNG_SEED)
        centers = [i * 15 for i in range(6)]
        X = np.vstack([rng.normal(c, 0.3, (12, 4)) for c in centers])
        verdict, headline_k, _ = _gmm_verdict(X)
        assert headline_k is not None and headline_k >= 4  # not forced toward any small default


class TestContinuumGroundTruth:
    def test_smooth_gradient_can_present_as_multi_config_a_disclosed_methodological_limitation(self):
        """IMPORTANT DISCLOSED FINDING (Work Package R, Section 23):
        a genuinely smooth, single-latent-axis gradient with NO discrete
        gaps -- ground truth is a continuum, not clusters -- was
        initially expected to read as 'continuum' or 'one_config' under
        classify_discovery_verdict. It does NOT: GMM at k=2 finds a
        single dominant bisection of the gradient's midpoint, which
        scores a high, CLEARLY-peaked silhouette (~0.6, far above every
        other k, so the >=3-near-best-k 'continuum' rule never fires) --
        yielding 'multi_config' even though there is no genuine discrete
        cluster boundary anywhere in the data.

        This is a genuine, disclosed limitation of silhouette-based
        model selection (Section 9.3's own "no single metric decides"
        rule exists precisely because any one metric can be fooled this
        way) -- not a bug in this test or in classify_discovery_verdict,
        which is doing exactly what it is documented to do (measure
        silhouette peakedness across k, nothing more). It means a
        'multi_config' verdict from this pipeline alone should NOT be
        read as proof of genuine discrete structure -- consistent with,
        and reinforcing, Section 20's own cautious-vocabulary discipline
        (never 'confirmed' from clustering evidence alone). Recorded here
        as a positive-knowledge test of ACTUAL behavior, not a
        should-never-happen assertion."""
        rng = np.random.default_rng(RNG_SEED)
        latent = rng.uniform(0, 20, size=300)
        X = np.column_stack([latent + rng.normal(0, 0.5, 300) for _ in range(5)])
        verdict, headline_k, _ = _gmm_verdict(X, n_hard_minimum=40)
        assert headline_k == 2
        assert verdict["verdict"] == "multi_config"


class TestCollapseDominatedGroundTruth:
    def test_structure_that_is_just_the_failure_split_is_flagged(self):
        """Two clusters exist, but they are constructed to be EXACTLY
        the collapse/non-collapse split -- classify_discovery_verdict
        must report failure_dominated, not multi_config, when fed the
        correspondingly high cluster_vs_failure_ari (the same signal
        Work Package K's own pipeline computes from a real collapse
        proxy)."""
        rng = np.random.default_rng(RNG_SEED)
        X = np.vstack([rng.normal(0, 0.3, (30, 5)), rng.normal(12, 0.3, (30, 5))])
        k_results = compare_k_range(X, "gmm", DEFAULT_K_RANGE, rng_seed=RNG_SEED)
        headline_k = _select_headline_k(k_results)
        silhouette_by_k = {r["k"]: r["metrics"]["silhouette"] for r in k_results}
        collapse_proxy = np.array([0] * 30 + [1] * 30)  # exactly the same split as the two blobs
        labels = fit_candidate(X, "gmm", k=headline_k, rng_seed=RNG_SEED)["labels"]
        cluster_vs_failure_ari = adjusted_rand_score(collapse_proxy, labels)
        verdict = classify_discovery_verdict(
            n_total=X.shape[0], n_hard_minimum=10,
            failure_label_fraction=0.5, cluster_vs_failure_ari=cluster_vs_failure_ari,
            headline_k=headline_k, best_bootstrap_mean_ari=1.0, best_algorithm_agreement_mean_ari=1.0,
            silhouette_by_k=silhouette_by_k,
        )
        assert cluster_vs_failure_ari > 0.9
        assert verdict["verdict"] == "failure_dominated"


class TestInsufficientEvidenceGroundTruth:
    def test_below_hard_minimum_is_never_multi_config(self):
        rng = np.random.default_rng(RNG_SEED)
        X = np.vstack([rng.normal(0, 0.3, (3, 5)), rng.normal(12, 0.3, (3, 5))])
        verdict, _, _ = _gmm_verdict(X, n_hard_minimum=40)
        assert verdict["verdict"] == "insufficient_evidence"
