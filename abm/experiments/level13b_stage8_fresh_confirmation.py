#!/usr/bin/env python3
"""Level 1.3b, Work Package I / Stage 8 (task #121, Section 13):
independent fresh confirmation -- a DISJOINT LHS design (fresh design
seed, fresh simulation seeds -- never overlapping Stage 4's own points
or seed range) run through the EXACT SAME generative construction as
Stage 4 (imported directly from ``experiments.level13b_stage4_
homogeneous_discovery`` -- ``_build_config``, ``_run_one``,
``_load_ecological_points``, ``lhs_draws``, ``_PARAMETER_SPACE`` all
reused unmodified, per the frozen ``STAGE8_FRESH_CONFIRMATION``'s own
``frozen_before_scoring: ["preprocessing", "phenotype_fields", ...]``
requirement -- the whole point of a fresh-confirmation stage is that
NOTHING about how a point is built or measured is allowed to differ
from the discovery stage, only WHICH points and seeds are drawn).

**`no_refitting_before_primary_scoring` / `no_post_hoc_parameter_
selection` (frozen, both `True`).** Stage 7's leading discrete
candidate (`gmm_k1_to_8` at k=8, `covariance_type="full"`, tied
exactly with `unequal_covariance_mixtures`) and its own k=1 baseline
are both DETERMINISTICALLY RECONSTRUCTED here by refitting on STAGE
4's OWN training data only (same X, same standardization, same
`random_state=0` Stage 7 already used) -- this is not "refitting
before scoring" in the sense the frozen rule prohibits (which means:
never refit on Stage 8's OWN fresh data before computing the primary
score); `GaussianMixture.fit` is a deterministic function of its
inputs, so re-deriving the exact same fitted model from the exact same
training data it was already fit on is equivalent to loading a
persisted copy of it (Stage 7's own script did not persist the model
object itself, since it isn't JSON-serializable -- disclosed here
rather than silently re-fit differently). Stage 8's own fresh 96-point
X is standardized using ONLY Stage 4's frozen training mean/std
(`observer.phenotype_discovery.preprocess_features`'s own train/apply
split, exactly as designed for this), never refit on Stage 8 data.

**The actual generalization-gap test (Section 13/H7, the same
"per-run held-out log-likelihood, k=1 vs. leading k" comparison
convention Level 1.3's own Stage 7 already used):** score BOTH the
frozen k=1 (no-cluster-structure) GMM and the frozen leading k=8 GMM
on Stage 8's fresh, standardized data; report each model's total and
per-run log-likelihood on this genuinely fresh data, and their
DIFFERENCE. If k=8 generalizes no better than k=1 (or worse) on fresh
data, the k=8 structure was fit to Stage 4's own idiosyncrasies, not a
reproducible discrete pattern -- direct evidence for Section 17's
decision gate, not a verdict rendered by this script itself. The
frozen leading CONTINUOUS candidate (`pca_factor_continuum`, fit on
Stage 4's training data only) is applied the same way: reconstruction
error on Stage 8's fresh data using ONLY the frozen PCA transform."""

from __future__ import annotations

import json
import multiprocessing
import os

import numpy as np
from sklearn.mixture import GaussianMixture

from abm_governance.observer.phenotype_discovery import preprocess_features
from experiments.level13b_preregistration import STAGE8_FRESH_CONFIRMATION, load_and_verify_manifest
from experiments.level13b_stage4_homogeneous_discovery import (
    N_PATCHES, N_STEPS, POPULATION, _load_ecological_points, _run_one, lhs_draws,
)
from experiments.level13b_stage7_model_comparison import STAGE4_RECORDS_PATH, STATIC_DIMS, _feature_matrix

OUT_DIR = "outputs/level13b_stage8_fresh_confirmation"
N_POINTS = STAGE8_FRESH_CONFIRMATION["n_points"]
N_SEEDS_PER_POINT = STAGE8_FRESH_CONFIRMATION["n_seeds_per_point"]
LHS_SEED = 20260821008  # fresh, disclosed, disjoint from Stage 4's 20260821001.
SEED_BASE = 8_950_000   # fresh, disclosed, disjoint from every prior Level 1.3b seed_base/point range.
LEADING_K = 8
NULL_K = 1
RNG_SEED = 0


def write_scope_declaration(out_dir: str = OUT_DIR) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    scope = {
        "milestone": "level1.3b_work_package_i_stage8_fresh_confirmation",
        "n_points": N_POINTS, "n_seeds_per_point": N_SEEDS_PER_POINT, "n_runs_declared": N_POINTS * N_SEEDS_PER_POINT,
        "lhs_seed": LHS_SEED, "seed_base": SEED_BASE,
        "disjoint_from_stage4": {"stage4_lhs_seed": 20260821001, "stage4_seed_range_start": 8_700_000},
        "population_size": POPULATION, "n_patches": N_PATCHES, "n_steps": N_STEPS,
        "frozen_before_scoring": STAGE8_FRESH_CONFIRMATION["frozen_before_scoring"],
        "no_refitting_before_primary_scoring": True,
        "no_post_hoc_parameter_selection": True,
        "scale_disclosed_as": STAGE8_FRESH_CONFIRMATION["scale_disclosed_as"],
    }
    with open(os.path.join(out_dir, "scope_declaration.json"), "w") as f:
        json.dump(scope, f, indent=2, sort_keys=True)
    return scope


def run_smoke_test(eco_points: dict) -> bool:
    try:
        draws = lhs_draws(n=2, seed=LHS_SEED)
        record = _run_one((0, draws[0], SEED_BASE, eco_points))
        assert "phenotype_vector" in record
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"SMOKE TEST FAILED: {exc}")
        return False


def run_all(eco_points: dict) -> list[dict]:
    draws = lhs_draws(N_POINTS, seed=LHS_SEED)
    jobs = [
        (point_id, draw, SEED_BASE + point_id * 1000 + seed_idx, eco_points)
        for point_id, draw in enumerate(draws)
        for seed_idx in range(N_SEEDS_PER_POINT)
    ]
    with multiprocessing.Pool(2) as pool:
        return list(pool.imap(_run_one, jobs))


def _reconstruct_frozen_stage4_fit(k: int) -> dict:
    """Deterministically reconstructs the exact model Stage 7 already
    fit on Stage 4's training data (see module docstring for why this
    is equivalent to loading a persisted copy, not a fresh refit).
    Returns the fitted model plus the standardization stats needed to
    apply it to new data (never refit on that new data)."""
    with open(STAGE4_RECORDS_PATH) as f:
        stage4_records = json.load(f)["records"]
    X_raw = _feature_matrix(stage4_records, STATIC_DIMS)
    assert not np.isnan(X_raw).any()
    prep = preprocess_features(X_raw, X_raw, strategy="complete_case", standardize=True)
    X_train = prep["X_train"]
    n, d = X_train.shape
    covariance_type = "full" if n > k * d else "diag"
    model = GaussianMixture(n_components=k, covariance_type=covariance_type, random_state=RNG_SEED)
    model.fit(X_train)
    return {"model": model, "standardize_mean": prep["standardize_mean"], "standardize_std": prep["standardize_std"], "covariance_type": covariance_type}


def _reconstruct_frozen_pca() -> dict:
    from sklearn.decomposition import PCA
    with open(STAGE4_RECORDS_PATH) as f:
        stage4_records = json.load(f)["records"]
    X_raw = _feature_matrix(stage4_records, STATIC_DIMS)
    prep = preprocess_features(X_raw, X_raw, strategy="complete_case", standardize=True)
    pca = PCA(n_components=1)
    pca.fit(prep["X_train"])
    return {"pca": pca, "standardize_mean": prep["standardize_mean"], "standardize_std": prep["standardize_std"]}


def score_fresh_data(records: list[dict]) -> dict:
    X_fresh_raw = _feature_matrix(records, STATIC_DIMS)
    complete = ~np.isnan(X_fresh_raw).any(axis=1)
    n_complete = int(complete.sum())
    X_fresh = X_fresh_raw[complete]

    frozen_k1 = _reconstruct_frozen_stage4_fit(NULL_K)
    frozen_k8 = _reconstruct_frozen_stage4_fit(LEADING_K)
    X_fresh_std_k1 = (X_fresh - frozen_k1["standardize_mean"]) / frozen_k1["standardize_std"]
    X_fresh_std_k8 = (X_fresh - frozen_k8["standardize_mean"]) / frozen_k8["standardize_std"]

    total_ll_k1 = float(frozen_k1["model"].score(X_fresh_std_k1) * n_complete)
    total_ll_k8 = float(frozen_k8["model"].score(X_fresh_std_k8) * n_complete)
    per_run_ll_k1 = total_ll_k1 / n_complete if n_complete else float("nan")
    per_run_ll_k8 = total_ll_k8 / n_complete if n_complete else float("nan")

    frozen_pca = _reconstruct_frozen_pca()
    X_fresh_std_pca = (X_fresh - frozen_pca["standardize_mean"]) / frozen_pca["standardize_std"]
    coords = frozen_pca["pca"].transform(X_fresh_std_pca)
    reconstructed = frozen_pca["pca"].inverse_transform(coords)
    pca_reconstruction_error_fresh = float(np.mean((X_fresh_std_pca - reconstructed) ** 2))

    return {
        "n_records": len(records), "n_complete_rows": n_complete,
        "generalization_gap_test": {
            "null_k1_total_log_likelihood": total_ll_k1,
            "leading_k8_total_log_likelihood": total_ll_k8,
            "null_k1_per_run_log_likelihood": per_run_ll_k1,
            "leading_k8_per_run_log_likelihood": per_run_ll_k8,
            "per_run_log_likelihood_gap_k8_minus_k1": per_run_ll_k8 - per_run_ll_k1,
            "interpretation_note": (
                "a POSITIVE gap means the k=8 structure fits fresh data better than the no-structure "
                "k=1 baseline (evidence the discrete structure generalizes); a gap near zero or negative "
                "means k=8's apparent structure was fit to Stage 4's own idiosyncrasies and does not "
                "reproduce on fresh data -- this number is reported, not interpreted into a decision-gate "
                "verdict, which is Section 17/task #126's own job"
            ),
        },
        "frozen_pca_continuum_on_fresh_data": {
            "reconstruction_error_on_fresh_standardized_data": pca_reconstruction_error_fresh,
        },
        "covariance_types_used": {"k1": frozen_k1["covariance_type"], "k8": frozen_k8["covariance_type"]},
    }


def main() -> dict:
    os.makedirs(OUT_DIR, exist_ok=True)
    load_and_verify_manifest()
    eco_points = _load_ecological_points()
    scope = write_scope_declaration()
    smoke_ok = run_smoke_test(eco_points)
    if not smoke_ok:
        report = {"scope": scope, "smoke_test_passed": False, "status": "STOPPED_AFTER_SMOKE_TEST_FAILURE"}
        with open(os.path.join(OUT_DIR, "stage8_report.json"), "w") as f:
            json.dump(report, f, indent=2, sort_keys=True)
        print(json.dumps(report, indent=2, sort_keys=True))
        return report

    records = run_all(eco_points)
    with open(os.path.join(OUT_DIR, "records.json"), "w") as f:
        json.dump({"records": records}, f, indent=2, sort_keys=True, default=str)

    scoring = score_fresh_data(records)
    report = {"scope": scope, "smoke_test_passed": True, **scoring}
    with open(os.path.join(OUT_DIR, "stage8_report.json"), "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
