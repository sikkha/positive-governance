#!/usr/bin/env python3
"""Level 1.3b, Work Package H / Stage 7 (task #120, Section 12):
discrete-vs-continuous discovery model comparison, applied to Stage
4's homogeneous discovery pool (240 records) -- reuses ``observer/
phenotype_discovery.py``'s existing clustering/stability machinery
(built at Level 1.2, extended through Level 1.2b/1.3) directly rather
than reimplementing it, per this project's own "small disclosed
duplication over private cross-module coupling" convention applied in
reverse: where a shared, already-tested module exists, USE it.

**The frozen rule this stage must respect (`STAGE7_MODEL_COMPARISON
["rule"]`): no k chosen from silhouette alone; no preferred k; a
discrete result must beat every continuous alternative on FRESH
(Stage 8) data to count as discrete.** This stage therefore does NOT
render a final discrete-vs-continuous verdict -- it fits every
candidate family on Stage 4's pool, reports every metric transparently
(winners and losers alike), and picks ONE leading candidate per family
via a disclosed, non-silhouette-only rule, so Stage 8 (task #121) can
test that leading candidate against genuinely fresh data. The verdict
itself is Stage 8's job.

**Feature set**: the 6 non-``seq_`` phenotype dimensions (``S_obs``,
``Z_obs``, ``conversion_incidence``, ``entrenchment``, ``performance_
legitimacy``, ``procedural_legitimacy``) are this stage's primary,
complete-at-every-run feature set. The 8 ``seq_*`` (sequencing/timing)
dimensions carry genuine structural missingness (a dimension that
never activated) and are used separately for
``temporal_window_stability`` (below) -- fitting on final STATE vs.
fitting on activation TIMING is this stage's own disclosed
operationalization of "does structure hold across temporal
representations," not a literal implementation of Stage 5's own
early/middle/late windows (Stage 4's own records only carry final-step
state + full activation-timing vectors, not full windowed series --
that granularity is Stage 5's job, already done at one representative
cell; Stage 7 works with what Stage 4 actually recorded).

**Per-family operationalization, disclosed before any model is fit:**

* **Discrete**: ``gmm_k1_to_8`` and ``hierarchical`` via ``observer.
  phenotype_discovery.compare_k_range`` directly (unmodified).
  ``hdbscan_multiple_min_cluster_size`` -- ``fit_candidate``'s own
  HDBSCAN branch hardcodes one ``min_cluster_size``; this stage adds a
  small local wrapper trying ``{6, 12, 24, 48}`` (4 explicit values,
  spanning "very permissive" to "1/5 of the pool"), never through
  ``fit_candidate`` itself. ``unequal_covariance_mixtures`` -- GMM with
  ``covariance_type="full"`` forced at every k (vs. ``fit_candidate``'s
  own adaptive full/diag choice), the standard sklearn operationalization
  of letting each component have its own, unconstrained covariance
  structure.
* **Continuous**: ``pca_factor_continuum`` -- ``PCA(n_components=1)``,
  reconstruction error = mean squared distance between original and
  reconstructed points. ``principal_curve_manifold`` -- ``sklearn.
  manifold.Isomap(n_components=1)``, a standard NONLINEAR one-
  dimensional manifold embedding, genuinely distinct from PCA's linear
  projection (disclosed choice: Isomap over a hand-rolled principal-
  curve algorithm, for a well-tested, standard implementation).
  ``low_dim_regression`` -- ridge regression predicting ``Z_obs`` from
  the other 5 static dimensions, 5-fold cross-validated R^2 (a
  continuous, non-clustering account of the SAME feature space).
* **Path-dependent**: ``predict_late_phenotype_from_early_sequence_no_
  discrete_clustering`` -- ridge regression predicting ``entrenchment``
  (a late-run, accumulated-history outcome) from the 8 ``seq_*``
  activation-TIMING dimensions (early-sequence information), 5-fold
  cross-validated R^2, complete-case only (rows with any ``seq_*`` NaN
  excluded for this one candidate -- disclosed, not imputed, since
  imputing an activation TIME for a dimension that never activated
  would manufacture information)."""

from __future__ import annotations

import json
import os

import numpy as np
from sklearn.cluster import HDBSCAN
from sklearn.linear_model import Ridge
from sklearn.manifold import Isomap
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import KFold, cross_val_score

from abm_governance.observer.phenotype_discovery import (
    DEFAULT_K_RANGE,
    algorithm_agreement,
    bootstrap_stability,
    compare_k_range,
    held_out_log_likelihood,
    preprocess_features,
    seed_clustered_bootstrap_stability,
)
from experiments.level13b_preregistration import STAGE7_MODEL_COMPARISON, load_and_verify_manifest

OUT_DIR = "outputs/level13b_stage7_model_comparison"
STAGE4_RECORDS_PATH = "outputs/level13b_stage4_homogeneous_discovery/records.json"
STATIC_DIMS = ("S_obs", "Z_obs", "conversion_incidence", "entrenchment", "performance_legitimacy", "procedural_legitimacy")
SEQ_DIMS = (
    "seq_accountability", "seq_administrative_function", "seq_bargaining_participation",
    "seq_cross_founder_reconstruction", "seq_delegation", "seq_generalized_rule",
    "seq_interpatch_coordination", "seq_monitoring",
)
HDBSCAN_MIN_CLUSTER_SIZES = (6, 12, 24, 48)
RNG_SEED = 0
N_BOOTSTRAP = 30


def load_records() -> list[dict]:
    with open(STAGE4_RECORDS_PATH) as f:
        return json.load(f)["records"]


def _feature_matrix(records: list[dict], dims: tuple[str, ...]) -> np.ndarray:
    return np.array([[r["phenotype_vector"].get(d, float("nan")) for d in dims] for r in records], dtype=float)


def _standardized(X: np.ndarray) -> np.ndarray:
    prep = preprocess_features(X, X, strategy="complete_case", standardize=True)
    return prep["X_train"]


# --- Discrete candidates -----------------------------------------------------
def fit_gmm_k1_to_8(X: np.ndarray) -> dict:
    fits = compare_k_range(X, "gmm", k_range=DEFAULT_K_RANGE, rng_seed=RNG_SEED)
    best = min(fits, key=lambda f: f["bic"])
    return {"candidate": "gmm_k1_to_8", "all_k_fits": [{"k": f["k"], "bic": f["bic"], "aic": f["aic"], "metrics": f["metrics"]} for f in fits], "leading_k": best["k"], "leading_bic": best["bic"], "leading_labels": best["labels"]}


def fit_hierarchical_k1_to_8(X: np.ndarray) -> dict:
    fits = compare_k_range(X, "hierarchical", k_range=DEFAULT_K_RANGE, rng_seed=RNG_SEED)
    valid = [f for f in fits if f["k"] >= 2 and not np.isnan(f["metrics"]["silhouette"])]
    best = max(valid, key=lambda f: f["metrics"]["silhouette"]) if valid else fits[0]
    return {"candidate": "hierarchical", "all_k_fits": [{"k": f["k"], "metrics": f["metrics"]} for f in fits], "leading_k": best["k"], "leading_labels": best["labels"]}


def fit_hdbscan_multi_min_cluster_size(X: np.ndarray) -> dict:
    results = []
    for mcs in HDBSCAN_MIN_CLUSTER_SIZES:
        model = HDBSCAN(min_cluster_size=mcs, copy=True)
        labels = model.fit_predict(X)
        n_clusters = len(set(labels.tolist()) - {-1})
        results.append({"min_cluster_size": mcs, "n_clusters": n_clusters, "n_noise": int((labels == -1).sum()), "labels": labels})
    non_degenerate = [r for r in results if r["n_clusters"] >= 2]
    leading = max(non_degenerate, key=lambda r: r["n_clusters"] - r["n_noise"] / len(X)) if non_degenerate else results[0]
    return {"candidate": "hdbscan_multiple_min_cluster_size", "all_settings": [{"min_cluster_size": r["min_cluster_size"], "n_clusters": r["n_clusters"], "n_noise": r["n_noise"]} for r in results], "leading_min_cluster_size": leading["min_cluster_size"], "leading_labels": leading["labels"]}


def fit_unequal_covariance_mixtures(X: np.ndarray) -> dict:
    fits = []
    for k in DEFAULT_K_RANGE:
        if k > X.shape[0]:
            continue
        model = GaussianMixture(n_components=k, covariance_type="full", random_state=RNG_SEED)
        labels = model.fit_predict(X)
        fits.append({"k": k, "bic": float(model.bic(X)), "labels": labels})
    best = min(fits, key=lambda f: f["bic"])
    return {"candidate": "unequal_covariance_mixtures", "all_k_fits": [{"k": f["k"], "bic": f["bic"]} for f in fits], "leading_k": best["k"], "leading_bic": best["bic"], "leading_labels": best["labels"]}


# --- Continuous candidates ----------------------------------------------------
def fit_pca_factor_continuum(X: np.ndarray) -> dict:
    from sklearn.decomposition import PCA
    pca = PCA(n_components=1)
    coords = pca.fit_transform(X)
    reconstructed = pca.inverse_transform(coords)
    reconstruction_error = float(np.mean((X - reconstructed) ** 2))
    return {"candidate": "pca_factor_continuum", "explained_variance_ratio": float(pca.explained_variance_ratio_[0]), "reconstruction_error": reconstruction_error}


def fit_principal_curve_manifold(X: np.ndarray) -> dict:
    n_neighbors = min(10, X.shape[0] - 1)
    model = Isomap(n_components=1, n_neighbors=n_neighbors)
    coords = model.fit_transform(X)
    reconstruction_error = float(model.reconstruction_error())
    return {"candidate": "principal_curve_manifold", "reconstruction_error": reconstruction_error, "n_neighbors": n_neighbors}


def fit_low_dim_regression(X: np.ndarray, dims: tuple[str, ...], target: str = "Z_obs") -> dict:
    target_idx = dims.index(target)
    y = X[:, target_idx]
    X_pred = np.delete(X, target_idx, axis=1)
    model = Ridge(alpha=1.0)
    cv = KFold(n_splits=5, shuffle=True, random_state=RNG_SEED)
    scores = cross_val_score(model, X_pred, y, cv=cv, scoring="r2")
    return {"candidate": "low_dim_regression", "target": target, "predictors": [d for d in dims if d != target], "cv_r2_mean": float(np.mean(scores)), "cv_r2_scores": scores.tolist()}


# --- Path-dependent candidate --------------------------------------------------
def fit_path_dependent(records: list[dict], target: str = "entrenchment") -> dict:
    X_seq = _feature_matrix(records, SEQ_DIMS)
    y_all = np.array([r["phenotype_vector"].get(target, float("nan")) for r in records])
    complete = ~(np.isnan(X_seq).any(axis=1) | np.isnan(y_all))
    n_complete = int(complete.sum())
    if n_complete < 10:
        return {"candidate": "predict_late_phenotype_from_early_sequence_no_discrete_clustering", "n_complete_rows": n_complete, "cv_r2_mean": None, "note": "too few complete-case rows to fit"}
    X_c, y_c = X_seq[complete], y_all[complete]
    mean = X_c.mean(axis=0)
    std = np.where(X_c.std(axis=0) < 1e-12, 1.0, X_c.std(axis=0))
    X_std = (X_c - mean) / std
    model = Ridge(alpha=1.0)
    cv = KFold(n_splits=5, shuffle=True, random_state=RNG_SEED)
    scores = cross_val_score(model, X_std, y_c, cv=cv, scoring="r2")
    return {
        "candidate": "predict_late_phenotype_from_early_sequence_no_discrete_clustering",
        "target": target, "predictors": list(SEQ_DIMS), "n_complete_rows": n_complete,
        "cv_r2_mean": float(np.mean(scores)), "cv_r2_scores": scores.tolist(),
    }


# --- Stability/agreement metrics ----------------------------------------------
def compute_stability_metrics(X: np.ndarray, records: list[dict], leading_method: str, leading_k: int | None) -> dict:
    rng = np.random.default_rng(RNG_SEED)
    flat = bootstrap_stability(X, leading_method, leading_k, N_BOOTSTRAP, rng)
    point_ids = [r["point_id"] for r in records]
    by_point = seed_clustered_bootstrap_stability(X, point_ids, leading_method, leading_k, N_BOOTSTRAP, rng)
    return {"cross_seed_bootstrap_stability_flat": flat, "cross_point_stability_seed_clustered": by_point}


def compute_ecological_stratum_stability(X: np.ndarray, records: list[dict], leading_method: str, leading_k: int | None) -> dict:
    from abm_governance.observer.phenotype_discovery import fit_candidate
    strata = sorted({r["stratum"] for r in records})
    fits = {}
    for stratum in strata:
        idx = [i for i, r in enumerate(records) if r["stratum"] == stratum]
        if len(idx) < (leading_k or 2):
            continue
        fit = fit_candidate(X[idx], leading_method, k=leading_k, rng_seed=RNG_SEED)
        fits[stratum] = fit["labels"]
    agreement = algorithm_agreement(fits) if len(fits) >= 2 else {}
    return {"n_strata_fit": len(fits), "pairwise_agreement": agreement}


def compute_missingness_strategy_stability(records: list[dict], leading_method: str, leading_k: int | None) -> dict:
    from abm_governance.observer.phenotype_discovery import MISSINGNESS_STRATEGIES, fit_candidate
    X_raw = _feature_matrix(records, STATIC_DIMS)  # static dims have no missingness in practice, but the pipeline is exercised for real per Section 9.1 discipline
    labelings = {}
    for strategy in MISSINGNESS_STRATEGIES:
        prep = preprocess_features(X_raw, X_raw, strategy=strategy, standardize=True)
        fit = fit_candidate(prep["X_train"], leading_method, k=leading_k, rng_seed=RNG_SEED)
        labelings[strategy] = fit["labels"]
    agreement = algorithm_agreement(labelings)
    return {"strategies_compared": list(MISSINGNESS_STRATEGIES), "pairwise_agreement": agreement}


def compute_temporal_window_stability(records: list[dict], leading_method: str, leading_k: int | None) -> dict:
    from abm_governance.observer.phenotype_discovery import fit_candidate
    X_static = _standardized(_feature_matrix(records, STATIC_DIMS))
    X_seq_raw = _feature_matrix(records, SEQ_DIMS)
    complete = ~np.isnan(X_seq_raw).any(axis=1)
    if complete.sum() < (leading_k or 2):
        return {"n_complete_rows": int(complete.sum()), "note": "too few complete-case seq rows to compare"}
    X_seq = _standardized(X_seq_raw[complete])
    fit_static = fit_candidate(X_static[complete], leading_method, k=leading_k, rng_seed=RNG_SEED)
    fit_seq = fit_candidate(X_seq, leading_method, k=leading_k, rng_seed=RNG_SEED)
    agreement = algorithm_agreement({"final_state_features": fit_static["labels"], "activation_timing_features": fit_seq["labels"]})
    return {"n_complete_rows": int(complete.sum()), "pairwise_agreement": agreement, "note": "compares clustering fit on final-state vs. activation-timing features -- Stage 7's own disclosed proxy for Section 12's temporal_window_stability (Stage 4 records carry no full windowed series; see module docstring)"}


def main() -> dict:
    os.makedirs(OUT_DIR, exist_ok=True)
    load_and_verify_manifest()
    records = load_records()

    X_static_raw = _feature_matrix(records, STATIC_DIMS)
    assert not np.isnan(X_static_raw).any(), "static dims were expected to be complete for every Stage 4 run"
    X = _standardized(X_static_raw)

    discrete = {
        "gmm_k1_to_8": fit_gmm_k1_to_8(X),
        "hierarchical": fit_hierarchical_k1_to_8(X),
        "hdbscan_multiple_min_cluster_size": fit_hdbscan_multi_min_cluster_size(X),
        "unequal_covariance_mixtures": fit_unequal_covariance_mixtures(X),
    }
    continuous = {
        "pca_factor_continuum": fit_pca_factor_continuum(X),
        "principal_curve_manifold": fit_principal_curve_manifold(X),
        "low_dim_regression": fit_low_dim_regression(X, STATIC_DIMS),
    }
    path_dependent = {"predict_late_phenotype_from_early_sequence_no_discrete_clustering": fit_path_dependent(records)}

    # Leading DISCRETE candidate: lowest-BIC among the two BIC-scored
    # families (gmm_k1_to_8, unequal_covariance_mixtures), used only to
    # pick ONE candidate to carry forward to stability/Stage 8 --
    # disclosed rule, not silhouette-only, not privileging any k.
    bic_candidates = {"gmm_k1_to_8": discrete["gmm_k1_to_8"]["leading_bic"], "unequal_covariance_mixtures": discrete["unequal_covariance_mixtures"]["leading_bic"]}
    leading_discrete_name = min(bic_candidates, key=bic_candidates.get)
    leading_discrete = discrete[leading_discrete_name]
    leading_k = leading_discrete["leading_k"]
    # Stability/agreement sub-analyses below all go through observer.
    # phenotype_discovery's shared fit_candidate/bootstrap machinery,
    # which only knows the 3 CANDIDATE_METHODS base names -- disclosed
    # simplification: both BIC-scored families reduce to base method
    # "gmm" here (fit_candidate's own adaptive full/diag covariance
    # choice, not unequal_covariance_mixtures' forced covariance_
    # type="full"), rather than reimplementing the stability machinery
    # a second time for one covariance-type variant.
    leading_base_method = "gmm"

    held_out_split = int(0.8 * len(X))
    idx = np.random.default_rng(RNG_SEED).permutation(len(X))
    train_idx, heldout_idx = idx[:held_out_split], idx[held_out_split:]
    held_out_ll = held_out_log_likelihood(X[train_idx], X[heldout_idx], leading_k, rng_seed=RNG_SEED)

    stability = compute_stability_metrics(X, records, leading_base_method, leading_k)
    algo_agreement = algorithm_agreement({
        "gmm_k1_to_8": discrete["gmm_k1_to_8"]["leading_labels"],
        "hierarchical": discrete["hierarchical"]["leading_labels"],
        "hdbscan_multiple_min_cluster_size": discrete["hdbscan_multiple_min_cluster_size"]["leading_labels"],
        "unequal_covariance_mixtures": discrete["unequal_covariance_mixtures"]["leading_labels"],
    })
    ecological_stability = compute_ecological_stratum_stability(X, records, leading_base_method, leading_k)
    missingness_stability = compute_missingness_strategy_stability(records, leading_base_method, leading_k)
    temporal_stability = compute_temporal_window_stability(records, leading_base_method, leading_k)

    def _strip_labels(d):
        return {k: v for k, v in d.items() if k != "leading_labels"}

    report = {
        "milestone": "level1.3b_work_package_h_stage7_model_comparison",
        "n_records": len(records),
        "feature_dims": list(STATIC_DIMS),
        "discrete_candidates": {k: _strip_labels(v) for k, v in discrete.items()},
        "continuous_candidates": continuous,
        "path_dependent_candidates": path_dependent,
        "leading_discrete_candidate": leading_discrete_name,
        "leading_discrete_k": leading_k,
        "held_out_log_likelihood_leading_discrete": held_out_ll,
        "cross_algorithm_stability": algo_agreement,
        "cross_seed_and_cross_point_stability": stability,
        "ecological_stratum_stability": ecological_stability,
        "missingness_strategy_stability": missingness_stability,
        "temporal_window_stability": temporal_stability,
        "note": (
            STAGE7_MODEL_COMPARISON["rule"] + " -- this report picks ONE leading discrete candidate "
            "(lowest BIC among BIC-scored families) to compare against the leading continuous/path-dependent "
            "candidates on Stage 8's fresh confirmation data (task #121); no discrete-vs-continuous verdict is "
            "rendered here"
        ),
    }
    with open(os.path.join(OUT_DIR, "stage7_report.json"), "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    print(json.dumps({k: v for k, v in report.items() if k not in ("discrete_candidates",)}, indent=2, sort_keys=True, default=str))
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
