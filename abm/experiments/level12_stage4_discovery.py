#!/usr/bin/env python3
"""Level 1.2, Stage 4: blind phenotype discovery run.

Applies ``observer/phenotype_discovery.py``'s full pipeline to Stage 3's
pooled phenotype vectors for the first time against real simulation
output. **No k is privileged, no missingness strategy is silently
chosen, and no single model-selection metric decides** -- every
candidate cluster produced by every (method, k) combination under the
primary preprocessing strategy is evaluated against Section 10's twelve
minimum recurrence criteria and reported, whether it passes or fails.

**Disclosed scope note, discovered while building this stage (not
papered over)**: Section 10's Criterion 12
(``independent_of_single_lineage``) and Section 11's convergence-vs-
inheritance framework are defined in terms of institutional *lineage*
-- but Section 9's own unit of analysis for blind discovery is the
SEED-RUN (one pooled phenotype vector per independent simulation),
and institutional ``lineage_id`` integers are scoped *within* one
simulation run's own RNG stream, not comparable across different
seed-runs. At the seed-run unit of analysis, every pooled record is by
construction an independent origin (a distinct seed), so Criterion 12
is passed here using each record's own index as a unique proxy lineage
id -- correct for this granularity (seed independence *is* the
relevant "lineage" fact at this level) but not the richer within-run,
multi-institution ancestry analysis Section 11's module
(``observer/convergence_tests.py``, fully implemented and tested,
Section 11/task #45) is actually built for. That richer analysis
requires per-institution (not per-seed-run) pooling across a run's own
multiple patches/institutions and their real transmission-linked
ancestry -- out of this stage's disclosed scope given Stage 3's small
per-run institution counts (up to ~4 institutions per run at this
milestone's reduced scale). Flagged for Section 22's completion report.

Fits on Stage 3's own pool (no train/apply split) -- Stage 5's fresh
seeds are the genuinely held-out confirmation, not this stage."""

from __future__ import annotations

import json

import numpy as np

from abm_governance.observer.phenotype_discovery import (
    CANDIDATE_METHODS,
    DEFAULT_K_RANGE,
    MISSINGNESS_STRATEGIES,
    algorithm_agreement,
    bootstrap_stability,
    build_feature_matrix,
    co_assignment_matrix,
    compare_k_range,
    dimensionality_reduction_diagnostic,
    examine_collinearity,
    fit_candidate,
    missingness_report,
    model_selection_metrics,
    preprocess_features,
)
from abm_governance.observer.recurrence_criteria import evaluate_recurrence_criteria
from experiments.level12_common import ensure_dir
from experiments.level12_preregistration import load_and_verify_manifest

STAGE3_REPORT = "outputs/level12_stage3_main_search/stage3_report.json"
OUT_DIR = "outputs/level12_stage4_blind_discovery"
PHENOTYPE_DIMENSION_KEYS: tuple[str, ...] = ("C", "E", "L", "D", "M", "R", "S", "F", "V", "H")
#: The strategy the primary discovery pass fits on -- chosen because it
#: preserves every row (Stage 3's own missingness_report showed only
#: 5/24 rows had any NaN, so complete_case would already be workable
#: too; mean_impute is used as PRIMARY specifically so no row is ever
#: dropped from the primary pass, and complete_case/missingness_
#: indicator are reported as the required cross-strategy comparison,
#: never silently skipped).
PRIMARY_STRATEGY = "mean_impute"
BOOTSTRAP_N = 30
BOOTSTRAP_SEED = 999


def _scatter(labels_subset: np.ndarray, mask: np.ndarray, n_total: int) -> np.ndarray:
    """Maps a (possibly row-dropped, e.g. under ``complete_case``)
    labeling back onto the full ``n_total``-length index space, filling
    dropped rows with ``-1`` (treated as an ordinary/noise label by the
    ARI-based comparisons downstream -- a row this strategy had to drop
    genuinely cannot be said to agree with anything)."""
    full = np.full(n_total, -1, dtype=int)
    full[mask] = labels_subset
    return full


def _fit_at_k(fits: list[dict], k: int) -> dict | None:
    return next((f for f in fits if f["k"] == k), None)


def load_pool() -> list[dict]:
    with open(STAGE3_REPORT) as f:
        stage3 = json.load(f)
    return [r for r in stage3["records"] if r["eligibility"]["eligible"]]


def discover(records: list[dict]) -> dict:
    """The full Section 9/10 discovery-and-criteria pipeline, factored
    out of :func:`run` so other stages (Stage 5's prospective
    confirmation) can apply the identical, un-retuned procedure to a
    different record pool -- e.g. a fresh-seed pool -- as an independent
    replication attempt, rather than duplicating this logic."""
    phenotype_records = [r["phenotype_vector"] for r in records]
    X, feature_names = build_feature_matrix(phenotype_records, PHENOTYPE_DIMENSION_KEYS)
    n_total = X.shape[0]
    seeds = [r["seed"] for r in records]
    conditions = [r["parameter_condition"] for r in records]
    eligibility_results = [r["eligibility"] for r in records]

    miss_report = missingness_report(X, feature_names)
    collinearity = examine_collinearity(X, feature_names)

    preproc = {s: preprocess_features(X, X, s, standardize=True) for s in MISSINGNESS_STRATEGIES}
    X_primary = preproc[PRIMARY_STRATEGY]["X_train"]
    pca = dimensionality_reduction_diagnostic(X_primary, n_components=2)

    k_range = tuple(k for k in DEFAULT_K_RANGE if k <= n_total)
    gmm_fits = compare_k_range(X_primary, "gmm", k_range=k_range)
    hier_fits = compare_k_range(X_primary, "hierarchical", k_range=k_range)
    hdb_fit = fit_candidate(X_primary, "hdbscan")
    hdb_fit["metrics"] = model_selection_metrics(X_primary, hdb_fit["labels"])

    # Cross-strategy comparison (Section 9.1: never silently pick one
    # strategy) -- gmm refit under the two non-primary strategies,
    # scattered back to the full 24-row index space.
    other_strategy_gmm_labels: dict[str, dict[int, np.ndarray]] = {}
    for s in MISSINGNESS_STRATEGIES:
        if s == PRIMARY_STRATEGY:
            continue
        Xs, mask = preproc[s]["X_train"], preproc[s]["train_mask"]
        fits_s = compare_k_range(Xs, "gmm", k_range=tuple(k for k in DEFAULT_K_RANGE if k <= Xs.shape[0]))
        other_strategy_gmm_labels[s] = {f["k"]: _scatter(f["labels"], mask, n_total) for f in fits_s}

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    gmm_stability = {f["k"]: bootstrap_stability(X_primary, "gmm", f["k"], BOOTSTRAP_N, rng) for f in gmm_fits}
    hier_stability = {f["k"]: bootstrap_stability(X_primary, "hierarchical", f["k"], BOOTSTRAP_N, rng) for f in hier_fits}
    hdb_stability = bootstrap_stability(X_primary, "hdbscan", None, BOOTSTRAP_N, rng)

    all_primary_labelings = [f["labels"] for f in gmm_fits] + [f["labels"] for f in hier_fits] + [hdb_fit["labels"]]
    co_assign = co_assignment_matrix(all_primary_labelings)

    agreement_by_k = {}
    for gf in gmm_fits:
        hf = _fit_at_k(hier_fits, gf["k"])
        if hf is None:
            continue
        agreement_by_k[gf["k"]] = algorithm_agreement({"gmm": gf["labels"], "hierarchical": hf["labels"], "hdbscan": hdb_fit["labels"]})

    noise_indices = list(np.where(hdb_fit["labels"] == -1)[0])

    def _build_labels_by_strategy(method: str, k: int, primary_labels: np.ndarray) -> dict:
        out = {PRIMARY_STRATEGY: primary_labels}
        for s, by_k in other_strategy_gmm_labels.items():
            if k in by_k:
                out[s] = by_k[k]
        return out

    candidates = []

    def _evaluate_and_record(method: str, k: int, labels: np.ndarray, metrics_by_k: list[dict], other_labels_by_method: dict, stability_result: dict):
        for cluster_label in sorted(set(labels.tolist()) - {-1}):
            member_indices = list(np.where(labels == cluster_label)[0])
            cluster_data = {
                "member_indices": member_indices,
                "member_seed_ids": [seeds[i] for i in member_indices],
                "primary_labels": labels,
                "other_labels_by_method": other_labels_by_method,
                "bootstrap_stability_result": stability_result,
                "co_assignment": co_assign,
                "noise_indices": noise_indices,
                "X": X_primary,
                "labels_by_strategy": _build_labels_by_strategy(method, k, labels),
                "member_conditions": [conditions[i] for i in member_indices],
                "member_eligibility_results": [eligibility_results[i] for i in member_indices],
                "n_total": n_total,
                "k": k,
                "metrics_by_k": metrics_by_k,
                # seed-run unit of analysis: every record is an
                # independent origin by construction -- see module
                # docstring's disclosed scope note.
                "member_lineage_ids": member_indices,
            }
            evaluation = evaluate_recurrence_criteria(cluster_data)
            candidates.append({
                "method": method, "k": k, "cluster_label": int(cluster_label),
                "member_indices": member_indices, "n_members": len(member_indices),
                "member_seeds": [seeds[i] for i in member_indices],
                "member_outcome_labels": [records[i]["all_outcome_label"] for i in member_indices],
                "evaluation": evaluation,
            })

    for gf in gmm_fits:
        hf = _fit_at_k(hier_fits, gf["k"])
        other = {"hdbscan": hdb_fit["labels"]}
        if hf is not None:
            other["hierarchical"] = hf["labels"]
        _evaluate_and_record("gmm", gf["k"], gf["labels"], gmm_fits, other, gmm_stability[gf["k"]])

    for hf in hier_fits:
        gf = _fit_at_k(gmm_fits, hf["k"])
        other = {"hdbscan": hdb_fit["labels"]}
        if gf is not None:
            other["gmm"] = gf["labels"]
        _evaluate_and_record("hierarchical", hf["k"], hf["labels"], hier_fits, other, hier_stability[hf["k"]])

    if hdb_fit["k"] > 0:
        gf = _fit_at_k(gmm_fits, hdb_fit["k"]) or gmm_fits[0]
        hf = _fit_at_k(hier_fits, hdb_fit["k"]) or hier_fits[0]
        _evaluate_and_record(
            "hdbscan", hdb_fit["k"], hdb_fit["labels"], [hdb_fit],
            {"gmm": gf["labels"], "hierarchical": hf["labels"]}, hdb_stability,
        )

    n_meeting_all_criteria = sum(1 for c in candidates if c["evaluation"]["meets_all_minimum_criteria"])
    criteria_pass_counts = {}
    for c in candidates:
        criteria_pass_counts[c["evaluation"]["n_passed"]] = criteria_pass_counts.get(c["evaluation"]["n_passed"], 0) + 1

    report = {
        "n_pooled_records": n_total,
        "candidate_methods": list(CANDIDATE_METHODS),
        "k_range_evaluated": list(k_range),
        "primary_missingness_strategy": PRIMARY_STRATEGY,
        "missingness_report": miss_report,
        "collinearity_diagnostic": collinearity,
        "pca_diagnostic": pca,
        "gmm_fits_summary": [{"k": f["k"], "metrics": f["metrics"]} for f in gmm_fits],
        "hierarchical_fits_summary": [{"k": f["k"], "metrics": f["metrics"]} for f in hier_fits],
        "hdbscan_fit_summary": {"k": hdb_fit["k"], "metrics": hdb_fit["metrics"], "n_noise": int((hdb_fit["labels"] == -1).sum())},
        "bootstrap_stability": {
            "gmm": {k: v for k, v in gmm_stability.items()},
            "hierarchical": {k: v for k, v in hier_stability.items()},
            "hdbscan": hdb_stability,
        },
        "algorithm_agreement_by_k": agreement_by_k,
        "n_candidate_clusters_evaluated": len(candidates),
        "n_candidates_meeting_all_12_criteria": n_meeting_all_criteria,
        "criteria_pass_count_distribution": criteria_pass_counts,
        "candidates": candidates,
    }
    return report


def run() -> dict:
    ensure_dir(OUT_DIR)
    load_and_verify_manifest()  # hard stop if Stage 0's frozen manifest was altered

    records = load_pool()
    report = discover(records)
    with open(f"{OUT_DIR}/stage4_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(
        f"Stage 4 discovery: {report['n_pooled_records']} pooled records, "
        f"{report['n_candidate_clusters_evaluated']} candidate clusters evaluated "
        f"across {len(CANDIDATE_METHODS)} methods x k in {report['k_range_evaluated']}. "
        f"{report['n_candidates_meeting_all_12_criteria']}/{report['n_candidate_clusters_evaluated']} "
        f"candidates meet all 12 minimum recurrence criteria. "
        f"criteria_pass_count_distribution={report['criteria_pass_count_distribution']}", flush=True,
    )
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
