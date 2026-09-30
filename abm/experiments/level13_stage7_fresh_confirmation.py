#!/usr/bin/env python3
"""Level 1.3, Stage 7 (task #102): fresh confirmation.

Per the frozen preregistration manifest's own `stage7_fresh_
confirmation` commitment: 12 fresh seeds, never reused from Stage 3-6,
population 40, 4 patches, 500 steps. The scientific question this
stage answers: does the cluster structure Stage 6 discovered on the
pooled Stage 3-5 data generalize to genuinely new runs the fit never
saw, or was it an artifact of that particular pool?

**Design reuse, not reinvention.** The 12 fresh runs use Stage 4's own
already-built, already-tested machinery verbatim
(`level13_stage4_open_pressure_history_search`'s `_PARAMETER_SPACE`,
`lhs_draws`, `_run_one`) -- same 9-dimensional open pressure-history
LHS space, same population/patches/steps shape Stage 4 itself used
(`population=40, n_patches=4, n_steps=500` is Stage 4's own design,
which is also this stage's own preregistered shape) -- with a FRESH,
disclosed LHS seed and simulation-seed range, disjoint from every
earlier Level 1.3 stage's own seed range (Stage 3: 5,000,000+;
Stage 4: 6,000,000-6,023,003; Stage 5: 7,000,000+).

**Out-of-sample confirmation, not a re-fit.** Stage 6's own pooled
216-run fit (`level13_stage6_blind_phenotype_discovery`) is re-derived
here exactly as recorded (same pooling, same missingness strategy, same
frozen `headline_k` read back from Stage 6's own hash-verified
`results.json` -- never re-selected) to reproduce the SAME fitted GMM
model and preprocessing transform, then `observer/phenotype_
discovery.py`'s own `preprocess_features(X_train, X_apply, ...)` (its
own docstring: "X_apply may be ... a fresh confirmation batch") applies
that FROZEN transform to the 12 fresh points, and `held_out_log_
likelihood` scores them under the frozen model -- genuinely
out-of-sample, never fit on the fresh data itself. This is the
"confirmation" precedent this project already established
(`experiments/level12b_stage_l2_discovery_pool_refit.py`'s own role for
Level 1.2b, and Level 1.2's own Stage 5 "prospective confirmation, fresh
seeds", task #51), reused here rather than invented fresh.

**No six-way decision-gate verdict is rendered here** -- same explicit
deferral as Stage 6's own docstring: Section 23's classification
(task #108) synthesizes this stage's out-of-sample fit quality
alongside Stage 6, 8, and 9's own evidence."""

from __future__ import annotations

import hashlib
import json
import os

from abm_governance.observer.phenotype_discovery import (
    build_feature_matrix,
    fit_candidate,
    held_out_log_likelihood,
    preprocess_features,
)
from experiments import level13_stage4_open_pressure_history_search as stage4
from experiments import level13_stage6_blind_phenotype_discovery as stage6
from experiments.level13_preregistration import load_and_verify_manifest

OUT_DIR = "outputs/level13_stage7_fresh_confirmation"
N_POINTS = 12
N_SEEDS_PER_POINT = 1
#: Fresh, disclosed; distinct from Stage 4's own 20260820002 and every
#: other Level 1.3 LHS seed.
LHS_SEED = 20260820005
#: Disjoint from every earlier Level 1.3 stage's simulation-seed range
#: (Stage 3: 5,000,000+; Stage 4: 6,000,000-6,023,003; Stage 5:
#: 7,000,000-7,000,015).
SEED_BASE = 9_000_000


def draw_fresh_points(n_points: int = N_POINTS, seed: int = LHS_SEED) -> list[dict]:
    return stage4.lhs_draws(n=n_points, seed=seed)


def run_fresh_points(n_points: int = N_POINTS, n_seeds_per_point: int = N_SEEDS_PER_POINT) -> list[dict]:
    draws = draw_fresh_points(n_points)
    records = []
    for point_id, draw in enumerate(draws):
        for s in range(n_seeds_per_point):
            records.append(stage4._run_one(point_id, draw, SEED_BASE + point_id * 1000 + s))
    return records


def _stage6_fit():
    """Re-derives Stage 6's own pooled training feature matrix,
    preprocessing transform, and fitted GMM model -- reading Stage 6's
    hash-verified `headline_k` back rather than re-selecting it, so this
    stage's own confirmation is scored against the SAME model Stage 6
    actually reported, not a fresh (potentially different) refit."""
    stage6_report = stage6._load_and_verify(f"{stage6.OUT_DIR}/results.json")
    headline_k = stage6_report["headline_k"]

    pooled = stage6.pool_records()
    pool_vectors = [p["vector"] for p in pooled]
    X_pool, feature_names = build_feature_matrix(pool_vectors, stage6.LEVEL13_DIMENSION_KEYS)
    prep_pool = preprocess_features(X_pool, X_pool, stage6.PRIMARY_MISSINGNESS_STRATEGY)

    model = None
    if headline_k:
        model = fit_candidate(prep_pool["X_train"], "gmm", k=headline_k, rng_seed=stage6.RNG_SEED)["model"]

    return {
        "headline_k": headline_k,
        "feature_names": feature_names,
        "X_pool_raw": X_pool,
        "prep_pool": prep_pool,
        "model": model,
        "stage6_report_hash": stage6_report.get("report_hash"),
    }


def run() -> dict:
    load_and_verify_manifest()  # hard stop if the frozen manifest was altered
    # N_POINTS/N_SEEDS_PER_POINT referenced by NAME here (not via
    # run_fresh_points()'s own default parameter values, which are
    # bound once at function-definition time) so a test's
    # monkeypatch.setattr(stage7, "N_POINTS", ...) is actually honored
    # -- the same function-default-vs-monkeypatch desync Stage 1's own
    # `_BASE` dict precedent (task #96) already warned about, here at
    # the parameter-default level instead.
    fresh_records = run_fresh_points(N_POINTS, N_SEEDS_PER_POINT)
    fresh_vectors = [stage6._wrap(r["phenotype_vector"]) for r in fresh_records]

    from abm_governance.observer.level13_phenotype import LEVEL13_DIMENSION_KEYS
    X_fresh_raw, feature_names = build_feature_matrix(fresh_vectors, LEVEL13_DIMENSION_KEYS)

    fit = _stage6_fit()
    prep_pool = fit["prep_pool"]
    prep_fresh = preprocess_features(fit["X_pool_raw"], X_fresh_raw, stage6.PRIMARY_MISSINGNESS_STRATEGY)
    X_fresh = prep_fresh["X_apply"]

    predicted_labels = None
    mean_train_log_likelihood_per_point = float("nan")
    mean_fresh_log_likelihood_per_point = float("nan")
    if fit["model"] is not None:
        predicted_labels = fit["model"].predict(X_fresh).tolist()
        mean_train_log_likelihood_per_point = float(fit["model"].score(prep_pool["X_train"]))
        total_fresh_ll = held_out_log_likelihood(prep_pool["X_train"], X_fresh, fit["headline_k"], rng_seed=stage6.RNG_SEED)
        mean_fresh_log_likelihood_per_point = (
            total_fresh_ll / X_fresh.shape[0] if X_fresh.shape[0] else float("nan")
        )

    label_counts: dict[str, int] = {}
    if predicted_labels is not None:
        for lab in predicted_labels:
            label_counts[str(lab)] = label_counts.get(str(lab), 0) + 1

    return {
        "milestone": "level1.3_stage7_fresh_confirmation",
        "n_points": N_POINTS,
        "n_seeds_per_point": N_SEEDS_PER_POINT,
        "population_size": stage4.POPULATION,
        "n_patches": stage4.N_PATCHES,
        "n_steps": stage4.N_STEPS,
        "lhs_seed": LHS_SEED,
        "seed_base": SEED_BASE,
        "stage6_headline_k": fit["headline_k"],
        "stage6_report_hash": fit["stage6_report_hash"],
        "predicted_cluster_labels": predicted_labels,
        "predicted_label_counts": label_counts,
        "mean_train_log_likelihood_per_point": mean_train_log_likelihood_per_point,
        "mean_fresh_log_likelihood_per_point": mean_fresh_log_likelihood_per_point,
        "log_likelihood_gap": (
            mean_train_log_likelihood_per_point - mean_fresh_log_likelihood_per_point
            if mean_train_log_likelihood_per_point == mean_train_log_likelihood_per_point
            and mean_fresh_log_likelihood_per_point == mean_fresh_log_likelihood_per_point
            else float("nan")
        ),
        "fresh_records": [
            {"point_id": r["point_id"], "seed": r["seed"], "draw": r["draw"],
             "sequencing_vector": r["sequencing_vector"], "phenotype_vector": r["phenotype_vector"]}
            for r in fresh_records
        ],
        "decision_gate_note": (
            "no six-way decision-gate verdict is rendered here -- Section 23's classification "
            "(task #108) synthesizes this stage alongside Stage 6/8/9's own evidence"
        ),
    }


def report_hash(report: dict) -> str:
    payload = json.dumps(report, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_report(out_dir: str = OUT_DIR) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    report = run()
    digest = report_hash(report)
    report["report_hash"] = digest
    with open(f"{out_dir}/records.json", "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    result = write_report()
    print(f"Level 1.3 Stage 7: {result['n_points']} fresh points, stage6_headline_k={result['stage6_headline_k']}")
    print(f"predicted label counts: {result['predicted_label_counts']}")
    print(f"mean log-likelihood/point: train={result['mean_train_log_likelihood_per_point']:.3f} "
          f"fresh={result['mean_fresh_log_likelihood_per_point']:.3f}")
    print(f"report written to {OUT_DIR}/records.json")
