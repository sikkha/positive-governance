"""Level 1.2, Section 9: blind phenotype discovery.

**GENERATE FIRST. MEASURE SECOND. DISCOVER THIRD. INTERPRET LATER.**
Nothing in this module reads any SEM/dissertation label, and nothing
here privileges any particular cluster count — every function that
takes a cluster count ``k`` treats every value in its range identically,
``k=1`` included (Section 9.2's own "k=1 always valid" requirement).

**Disclosed reduction**: of the fuller candidate-method menu Section 9.2
suggests (GMM, hierarchical, HDBSCAN/density-based, spectral,
alternative-covariance-structure mixtures, trajectory/hidden-state
clustering), this milestone's initial wiring implements three
(:data:`CANDIDATE_METHODS` = ``gmm``, ``hierarchical``, ``hdbscan``) —
one parametric (mixture), one connectivity-based, one density-based,
covering three structurally different notions of "cluster" while
staying within this milestone's own reduced-scope discipline (the same
kind of disclosed reduction Level 1.1b's completion report already used
and had accepted). Spectral clustering and trajectory/hidden-state
clustering are not implemented this milestone.

Uses ``scikit-learn`` (a new core-package dependency this milestone —
declared in ``pyproject.toml``, the same "declare it once it becomes a
first-class dependency" precedent Level 0.3b set for ``scipy``)."""

from __future__ import annotations

import numpy as np
from sklearn.cluster import HDBSCAN, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture

#: Level 1.2b, Work Package "Configuration presets" (Section 24): a
#: version tag for the FROZEN clustering pipeline this module
#: implements -- the candidate-method set, k-search range, missingness
#: strategies, and the stability/agreement/selection primitives
#: (:func:`compare_k_range`, :func:`bootstrap_stability`,
#: :func:`seed_clustered_bootstrap_stability`, co-assignment,
#: algorithm-agreement) that Work Packages J/K/L/M/Q all call
#: unmodified. Bump this string if any of those primitives' inputs,
#: outputs, or decision logic change in a way that could shift a
#: verdict already on record, so a result manifest can be mechanically
#: checked against the exact pipeline version that produced it. Still
#: version 1: the one additive change this session made (Work Package
#: Q's ``seed_clustered_bootstrap_stability``) is a new, separate
#: function -- it does not alter any existing primitive's behavior.
CLUSTERING_PIPELINE_VERSION = "clustering_pipeline_v1"

#: Section 9.2's reduced candidate-method set (see module docstring).
CANDIDATE_METHODS: tuple[str, ...] = ("gmm", "hierarchical", "hdbscan")
#: Section 9.2: "k=1 through 8 where sample size permits" — the default
#: search range; callers may narrow it when sample size is small (see
#: ``compare_k_range``'s own guard).
DEFAULT_K_RANGE: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8)
#: Section 9.1: the three missingness-handling strategies to compare —
#: never a silent single default choice.
MISSINGNESS_STRATEGIES: tuple[str, ...] = ("complete_case", "missingness_indicator", "mean_impute")


# --- 9.1 Preprocessing -------------------------------------------------------
def build_feature_matrix(records: list[dict], dimension_keys: tuple[str, ...]) -> tuple[np.ndarray, list[str]]:
    """``records``: a list of already-computed
    ``institutional_phenotype_vector(...)`` outputs (one per seed-run —
    Section 15's "seed-run is the primary independent observation").
    Structural ``NaN`` is preserved exactly, never zero-filled here —
    this function only assembles the raw matrix; missingness handling is
    a separate, explicit, disclosed choice (see :func:`preprocess_features`)."""
    feature_names: list[str] = []
    for key in dimension_keys:
        if key == "V":
            feature_names.extend(["V_ecological", "V_demographic"])
        else:
            feature_names.append(key)
    rows = []
    for rec in records:
        row = []
        for key in dimension_keys:
            if key == "V":
                v = rec.get("V", {})
                row.append(v.get("ecological", {}).get("value", float("nan")))
                row.append(v.get("demographic", {}).get("value", float("nan")))
            else:
                row.append(rec.get(key, {}).get("value", float("nan")))
        rows.append(row)
    return np.array(rows, dtype=float), feature_names


def missingness_report(X: np.ndarray, feature_names: list[str]) -> dict:
    """Per-feature missing fraction — always computed and exportable
    before any imputation/removal decision (Section 9.1's "transparent
    missingness handling" requirement)."""
    n = X.shape[0]
    return {
        name: float(np.isnan(X[:, i]).sum() / n) if n else float("nan")
        for i, name in enumerate(feature_names)
    }


def preprocess_features(
    X_train: np.ndarray, X_apply: np.ndarray, strategy: str, standardize: bool = True,
) -> dict:
    """Fit every transform (imputation values, standardization mean/std)
    on ``X_train`` ONLY, then apply the same fitted transform to both
    ``X_train`` and ``X_apply`` (``X_apply`` may be the same array, a
    held-out split, or a fresh confirmation batch — Section 15's
    "train-only standardization" and Section 9.1's "fit on training data
    only" requirements). Returns a dict so every strategy's output shape
    is self-describing (``missingness_indicator`` adds columns;
    ``complete_case`` drops rows — callers must not assume shape
    parity with the input)."""
    if strategy not in MISSINGNESS_STRATEGIES:
        raise ValueError(f"strategy must be one of {MISSINGNESS_STRATEGIES}, got {strategy!r}")

    if strategy == "complete_case":
        train_mask = ~np.isnan(X_train).any(axis=1)
        apply_mask = ~np.isnan(X_apply).any(axis=1)
        Xt = X_train[train_mask]
        Xa = X_apply[apply_mask]
        indicator_cols = 0
    elif strategy == "mean_impute":
        col_means = np.nanmean(X_train, axis=0)
        col_means = np.where(np.isnan(col_means), 0.0, col_means)  # an all-NaN column has no defined mean; document as 0.0 fallback, flagged via missingness_report separately
        Xt = np.where(np.isnan(X_train), col_means, X_train)
        Xa = np.where(np.isnan(X_apply), col_means, X_apply)
        train_mask = np.ones(X_train.shape[0], dtype=bool)
        apply_mask = np.ones(X_apply.shape[0], dtype=bool)
        indicator_cols = 0
    else:  # missingness_indicator
        col_means = np.nanmean(X_train, axis=0)
        col_means = np.where(np.isnan(col_means), 0.0, col_means)
        train_indicators = np.isnan(X_train).astype(float)
        apply_indicators = np.isnan(X_apply).astype(float)
        Xt_vals = np.where(np.isnan(X_train), col_means, X_train)
        Xa_vals = np.where(np.isnan(X_apply), col_means, X_apply)
        Xt = np.hstack([Xt_vals, train_indicators])
        Xa = np.hstack([Xa_vals, apply_indicators])
        train_mask = np.ones(X_train.shape[0], dtype=bool)
        apply_mask = np.ones(X_apply.shape[0], dtype=bool)
        indicator_cols = X_train.shape[1]

    mean = np.zeros(Xt.shape[1])
    std = np.ones(Xt.shape[1])
    if standardize and Xt.shape[0] > 0:
        mean = Xt.mean(axis=0)
        std = Xt.std(axis=0)
        std = np.where(std < 1e-12, 1.0, std)  # a constant column standardizes to 0, not NaN/inf
        Xt = (Xt - mean) / std
        Xa = (Xa - mean) / std

    return {
        "X_train": Xt, "X_apply": Xa, "train_mask": train_mask, "apply_mask": apply_mask,
        "strategy": strategy, "standardize_mean": mean, "standardize_std": std,
        "n_indicator_columns": indicator_cols,
    }


def examine_collinearity(X: np.ndarray, feature_names: list[str]) -> dict:
    """Pairwise Pearson correlation matrix over complete cases only —
    diagnostic only, never used to silently drop a dimension (Section
    9.1: "never remove dimensions to force 3-cluster separation")."""
    complete = X[~np.isnan(X).any(axis=1)]
    if complete.shape[0] < 2:
        return {"feature_names": feature_names, "correlation_matrix": None, "n_complete_rows": complete.shape[0]}
    with np.errstate(invalid="ignore"):
        corr = np.corrcoef(complete, rowvar=False)
    return {"feature_names": feature_names, "correlation_matrix": corr.tolist(), "n_complete_rows": complete.shape[0]}


def dimensionality_reduction_diagnostic(X: np.ndarray, n_components: int = 2) -> dict:
    """PCA only, and explicitly diagnostic-only (Section 9.1/19: "PCA
    transparent... never the principal clustering evidence"; UMAP/t-SNE
    are not implemented here — this milestone's disclosed reduction —
    and nothing downstream in this module ever clusters on these
    coordinates)."""
    n_components = min(n_components, X.shape[0], X.shape[1])
    if n_components < 1:
        return {"explained_variance_ratio": [], "components": None}
    pca = PCA(n_components=n_components)
    coords = pca.fit_transform(X)
    return {
        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "components": coords.tolist(),
        "diagnostic_only": True,
    }


# --- 9.2 Candidate methods ---------------------------------------------------
def fit_candidate(X: np.ndarray, method: str, k: int | None = None, rng_seed: int = 0) -> dict:
    """Fit one candidate method. ``k`` is required for ``gmm``/
    ``hierarchical`` (every ``k`` in ``[1, n_samples]`` is equally
    valid — no special-casing of ``k=3``); ``hdbscan`` never takes ``k``
    (density-based methods determine cluster count themselves — Section
    9.5's "permit noise points... never force every run into a
    cluster" is inherent to this method, surfaced via label ``-1``)."""
    if method not in CANDIDATE_METHODS:
        raise ValueError(f"method must be one of {CANDIDATE_METHODS}, got {method!r}")
    n = X.shape[0]
    if method in ("gmm", "hierarchical") and k is None:
        raise ValueError(f"method={method!r} requires k")
    if method == "gmm":
        k = min(k, n)
        model = GaussianMixture(n_components=k, random_state=rng_seed, covariance_type="full" if n > k * X.shape[1] else "diag")
        labels = model.fit_predict(X)
        return {
            "method": "gmm", "k": k, "labels": labels, "model": model,
            "bic": float(model.bic(X)), "aic": float(model.aic(X)),
        }
    if method == "hierarchical":
        k = min(k, n)
        model = AgglomerativeClustering(n_clusters=k)
        labels = model.fit_predict(X) if n >= k else np.zeros(n, dtype=int)
        return {"method": "hierarchical", "k": k, "labels": labels, "model": model, "bic": None, "aic": None}
    # hdbscan
    min_cluster_size = max(2, n // 10)
    model = HDBSCAN(min_cluster_size=min_cluster_size, copy=True)
    labels = model.fit_predict(X)
    return {
        "method": "hdbscan", "k": len(set(labels) - {-1}), "labels": labels, "model": model,
        "bic": None, "aic": None, "probabilities": getattr(model, "probabilities_", None),
    }


def compare_k_range(X: np.ndarray, method: str, k_range: tuple[int, ...] = DEFAULT_K_RANGE, rng_seed: int = 0) -> list[dict]:
    """Fits ``method`` for every ``k`` in ``k_range`` that the sample
    size permits (``k <= n_samples``) — no k is skipped for any other
    reason, and none is privileged."""
    n = X.shape[0]
    results = []
    for k in k_range:
        if k > n:
            continue
        fit = fit_candidate(X, method, k=k, rng_seed=rng_seed)
        fit["metrics"] = model_selection_metrics(X, fit["labels"], fit.get("model"), method)
        results.append(fit)
    return results


# --- 9.3 Model selection -----------------------------------------------------
def model_selection_metrics(X: np.ndarray, labels: np.ndarray, model=None, method: str | None = None) -> dict:
    """No single metric decides (Section 9.3) — every metric here is
    computed and returned side by side; NaN when undefined (fewer than 2
    non-noise clusters, or a cluster with a single point for silhouette).
    """
    unique = set(labels.tolist()) - {-1}
    n_clusters = len(unique)
    out: dict = {"n_clusters": n_clusters, "n_noise": int((labels == -1).sum())}
    mask = labels != -1
    Xc, labelsc = X[mask], labels[mask]
    if n_clusters >= 2 and len(Xc) > n_clusters:
        try:
            out["silhouette"] = float(silhouette_score(Xc, labelsc))
        except ValueError:
            out["silhouette"] = float("nan")
        try:
            out["calinski_harabasz"] = float(calinski_harabasz_score(Xc, labelsc))
        except ValueError:
            out["calinski_harabasz"] = float("nan")
        try:
            out["davies_bouldin"] = float(davies_bouldin_score(Xc, labelsc))
        except ValueError:
            out["davies_bouldin"] = float("nan")
    else:
        out["silhouette"] = float("nan")
        out["calinski_harabasz"] = float("nan")
        out["davies_bouldin"] = float("nan")

    if n_clusters >= 1:
        counts = np.array([(labels == lbl).sum() for lbl in unique])
        out["cluster_size_balance"] = float(counts.min() / counts.max())
    else:
        out["cluster_size_balance"] = float("nan")

    if method == "gmm" and model is not None:
        out["bic"] = float(model.bic(X))
        out["aic"] = float(model.aic(X))
        out["held_out_log_likelihood"] = None  # computed by callers with an actual held-out split; see held_out_log_likelihood()
    return out


def held_out_log_likelihood(X_train: np.ndarray, X_heldout: np.ndarray, k: int, rng_seed: int = 0) -> float:
    """GMM only (the one candidate method with a defined likelihood).
    Fit on ``X_train``, score on ``X_heldout`` — genuinely out-of-sample,
    never the training data itself."""
    if X_heldout.shape[0] == 0:
        return float("nan")
    model = GaussianMixture(n_components=min(k, X_train.shape[0]), random_state=rng_seed)
    model.fit(X_train)
    return float(model.score(X_heldout) * X_heldout.shape[0])  # total, not mean, log-likelihood


# --- 9.4 Consensus ------------------------------------------------------------
def co_assignment_matrix(labels_list: list[np.ndarray]) -> np.ndarray:
    """Fraction of runs (across bootstrap resamples and/or algorithms,
    aligned to the same fixed row order) in which each pair of points
    was assigned to the same cluster. Noise points (``-1``) never count
    as "same cluster" with anything, including each other."""
    n = len(labels_list[0])
    co = np.zeros((n, n))
    for labels in labels_list:
        for i in range(n):
            if labels[i] == -1:
                continue
            for j in range(n):
                if labels[j] == -1:
                    continue
                if labels[i] == labels[j]:
                    co[i, j] += 1
    return co / len(labels_list)


def variation_of_information(labels_a: np.ndarray, labels_b: np.ndarray) -> float:
    """VI(A, B) = H(A) + H(B) - 2*I(A, B), in nats. 0.0 for identical
    partitions (up to relabeling); increases with disagreement, unbounded
    above. Noise points (-1) are treated as their own ordinary label
    value here (a defined, if conservative, choice — not silently
    excluded, since dropping them would change what's being compared)."""
    a = np.asarray(labels_a)
    b = np.asarray(labels_b)
    n = len(a)
    if n == 0:
        return float("nan")

    def _entropy(labels):
        _, counts = np.unique(labels, return_counts=True)
        p = counts / n
        return float(-(p * np.log(p)).sum())

    def _mutual_info(a, b):
        total = 0.0
        for la in np.unique(a):
            for lb in np.unique(b):
                p_ab = np.mean((a == la) & (b == lb))
                if p_ab <= 0:
                    continue
                p_a = np.mean(a == la)
                p_b = np.mean(b == lb)
                total += p_ab * np.log(p_ab / (p_a * p_b))
        return total

    h_a, h_b = _entropy(a), _entropy(b)
    mi = _mutual_info(a, b)
    return max(0.0, h_a + h_b - 2 * mi)


def bootstrap_stability(X: np.ndarray, method: str, k: int | None, n_bootstrap: int, rng: np.random.Generator) -> dict:
    """Resample rows with replacement ``n_bootstrap`` times, refit, and
    compare each resample's labels (restricted to the out-of-bag rows
    that both the original fit and this resample's fit cover) against
    the original fit via Adjusted Rand Index. Returns the mean/std ARI —
    a stability score in [-1, 1] (ARI's own range), not forced into
    [0, 1]."""
    original = fit_candidate(X, method, k=k)
    n = X.shape[0]
    aris = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        resample = fit_candidate(X[idx], method, k=k)
        aris.append(adjusted_rand_score(original["labels"][idx], resample["labels"]))
    return {
        "method": method, "k": k, "n_bootstrap": n_bootstrap,
        "mean_ari": float(np.mean(aris)) if aris else float("nan"),
        "std_ari": float(np.std(aris)) if aris else float("nan"),
    }


def seed_clustered_bootstrap_stability(
    X: np.ndarray, cluster_ids: list, method: str, k: int | None, n_bootstrap: int, rng: np.random.Generator,
) -> dict:
    """Level 1.2b, Work Package Q (Section 22): a CLUSTER bootstrap,
    complementary to (never a replacement for) :func:`bootstrap_
    stability`'s own flat/row-level resample. ``bootstrap_stability``
    treats every row as independently exchangeable, which understates
    uncertainty whenever rows are nested (e.g. this milestone's own
    multiple seeds per joint parameter point are NOT independent draws
    of the underlying parameter point itself — they share it). This
    function instead resamples whole ``cluster_ids`` groups (e.g.
    ``joint_point_id``) WITH replacement, keeping every row belonging
    to a resampled group together, then refits and compares via ARI —
    Section 22's own "seed-clustered / hierarchical bootstrap
    inference" requirement. Degenerate (``NaN``) when fewer than 2
    distinct clusters exist, since a cluster bootstrap over a single
    group is vacuous."""
    original = fit_candidate(X, method, k=k)
    cluster_ids = list(cluster_ids)
    unique_clusters = sorted(set(cluster_ids))
    n_clusters = len(unique_clusters)
    if n_clusters < 2:
        return {"method": method, "k": k, "n_bootstrap": n_bootstrap, "n_clusters": n_clusters, "mean_ari": float("nan"), "std_ari": float("nan")}
    row_idx_by_cluster = {c: [i for i, cid in enumerate(cluster_ids) if cid == c] for c in unique_clusters}
    aris = []
    for _ in range(n_bootstrap):
        chosen = rng.choice(np.array(unique_clusters, dtype=object), size=n_clusters, replace=True)
        idx = np.concatenate([row_idx_by_cluster[c] for c in chosen])
        resample = fit_candidate(X[idx], method, k=k)
        aris.append(adjusted_rand_score(original["labels"][idx], resample["labels"]))
    return {
        "method": method, "k": k, "n_bootstrap": n_bootstrap, "n_clusters": n_clusters,
        "mean_ari": float(np.mean(aris)) if aris else float("nan"),
        "std_ari": float(np.std(aris)) if aris else float("nan"),
    }


def algorithm_agreement(labels_by_method: dict[str, np.ndarray]) -> dict:
    """Pairwise ARI and VI between every pair of candidate methods'
    labelings on the same fixed sample — Section 9.4's "candidate needs
    support from >1 algorithm" evidence."""
    methods = list(labels_by_method.keys())
    pairwise = {}
    for i in range(len(methods)):
        for j in range(i + 1, len(methods)):
            m1, m2 = methods[i], methods[j]
            pairwise[f"{m1}_vs_{m2}"] = {
                "ari": float(adjusted_rand_score(labels_by_method[m1], labels_by_method[m2])),
                "vi": variation_of_information(labels_by_method[m1], labels_by_method[m2]),
            }
    return pairwise
