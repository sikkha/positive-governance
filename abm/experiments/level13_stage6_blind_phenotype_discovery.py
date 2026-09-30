#!/usr/bin/env python3
"""Level 1.3, Stage 6 (task #101): blind phenotype discovery.

Per the frozen preregistration manifest's own
``stage6_blind_phenotype_discovery`` commitment, this stage "pools
Stage 3-5's phenotype vectors through ``observer/phenotype_discovery.py``
unmodified; no new simulation runs" -- unlike Level 1.2b's own Work
Package K/L, this stage never re-simulates anything: Stage 3 (72 runs),
Stage 4 (96 runs), and Stage 5 (48 runs -- 16 matched base/erased/
reversed triples) already recorded a Work Package H ``level13_phenotype_
vector`` for every completed run, on disk. This script pools all 216,
verifies the source files against their own recorded ``report_hash``
(tamper-evident, mirroring every other freeze-then-hash artifact this
milestone uses), and runs them through Level 1.2's already-built,
already-tested clustering pipeline exactly as Level 1.2b's Work Package
K did -- nothing about the underlying clustering machinery
(``build_feature_matrix``, ``preprocess_features``, ``compare_k_range``,
``fit_candidate``, ``model_selection_metrics``, ``bootstrap_stability``,
``algorithm_agreement``) is reimplemented here.

**Adapter step, disclosed.** Stage 3/4/5's own ``records.json`` store
each run's phenotype vector already flattened to ``{dimension: float}``
(for JSON compactness), not the ``{dimension: {"value": ..., "construct_
type": ...}}`` shape ``build_feature_matrix`` expects (the shape
``level13_phenotype_vector`` itself actually returns, before Stage 3/4/5
flattened it). This script re-wraps each flattened record back into
that shape before calling ``build_feature_matrix`` -- a pure format
adapter, not a reinterpretation of any value.

**Provenance is carried for diagnostics, never used in the fit.** Each
pooled row is tagged with its source (``stage3``, ``stage4``,
``stage5_base``, ``stage5_erased``, ``stage5_reversed``) purely for a
post-hoc "does clustering just recover which stage a run came from"
structure-recovery check (the Level 1.3 analog of Level 1.2b Work
Package K's own IC-family-recovery check) -- the label is never fed to
any clustering call itself (Section 9's own "generate first, measure
second, discover third" discipline).

**Scope, relative to Work Package K.** No re-simulation means no
temporal-window-stability snapshot (Stage 3/4/5 only ever captured an
end-of-run vector) and no parameter-neighborhood leave-one-point-out
check (Level 1.3's pooled runs come from three structurally different
designs -- a factorial, an LHS search, and matched counterfactual
triples -- with no single "institutional point" axis common to all
three the way Level 1.2b's one frozen design had). Both are disclosed
omissions, not silent ones.

**No six-way verdict is rendered here.** Section 23's six-way decision
gate (``experiments/level13_preregistration.py::DECISION_GATE_
OUTCOMES``) is explicitly task #108's own job, synthesized across this
stage's clustering structure AND Stage 7's fresh confirmation, Stage
8's S_obs/Z_obs mapping, and Stage 9's robustness checks -- rendering a
verdict from clustering structure alone here would pre-empt evidence
this milestone's own staging says to gather first. This script reports
cluster-count/stability/robustness diagnostics only."""

from __future__ import annotations

import hashlib
import json
import os

import numpy as np
from sklearn.metrics import adjusted_rand_score

from abm_governance.observer.level13_phenotype import LEVEL13_DIMENSION_KEYS
from abm_governance.observer.phenotype_discovery import (
    CANDIDATE_METHODS,
    DEFAULT_K_RANGE,
    MISSINGNESS_STRATEGIES,
    algorithm_agreement,
    bootstrap_stability,
    build_feature_matrix,
    compare_k_range,
    examine_collinearity,
    fit_candidate,
    missingness_report,
    model_selection_metrics,
    preprocess_features,
)

OUT_DIR = "outputs/level13_stage6_blind_phenotype_discovery"
STAGE3_PATH = "outputs/level13_stage3_sequencing_entrenchment_factorial/records.json"
STAGE4_PATH = "outputs/level13_stage4_open_pressure_history_search/records.json"
STAGE5_PATH = "outputs/level13_stage5_causal_counterfactuals/records.json"

PRIMARY_MISSINGNESS_STRATEGY = "mean_impute"
N_BOOTSTRAP = 30
HELD_OUT_FRACTION = 0.2
#: Fresh, disclosed; distinct from every earlier Level 1.3/1.2b RNG/LHS
#: seed (Work Package K's own clustering RNG_SEED is 20260818). Must
#: fit sklearn's uint32 random_state range, unlike the Level 1.3 LHS
#: seeds above (scipy's own qmc.LatinHypercube seed accepts a wider
#: range) -- kept small deliberately for that reason.
RNG_SEED = 20260820


def _load_and_verify(path: str) -> dict:
    """Recomputes the same ``report_hash`` each source stage's own
    ``write_report``/``write_stage0_report`` used, comparing against the
    value stored on disk -- tamper-evident pooling, matching every other
    freeze-then-hash artifact in this milestone."""
    with open(path) as f:
        report = json.load(f)
    stored_hash = report.get("report_hash")
    check = dict(report)
    check.pop("report_hash", None)
    payload = json.dumps(check, sort_keys=True, default=str)
    recomputed = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if stored_hash is not None and recomputed != stored_hash:
        raise ValueError(f"{path}: report_hash mismatch (file may have been altered since it was written)")
    return report


def _wrap(flat_vector: dict) -> dict:
    """Re-wraps a Stage 3/4/5 flattened ``{dimension: float}`` phenotype
    vector back into the ``{dimension: {"value": float}}`` shape
    ``build_feature_matrix`` expects."""
    return {k: {"value": v} for k, v in flat_vector.items()}


def pool_records() -> list[dict]:
    stage3 = _load_and_verify(STAGE3_PATH)
    stage4 = _load_and_verify(STAGE4_PATH)
    stage5 = _load_and_verify(STAGE5_PATH)

    pooled = []
    for r in stage3["records"]:
        pooled.append({"source_stage": "stage3", "seed": r["seed"], "vector": _wrap(r["phenotype_vector"])})
    for r in stage4["records"]:
        pooled.append({"source_stage": "stage4", "seed": r["seed"], "vector": _wrap(r["phenotype_vector"])})
    for r in stage5["records"]:
        for run_type in ("base", "erased", "reversed"):
            pooled.append({
                "source_stage": f"stage5_{run_type}", "seed": r["seed"],
                "vector": _wrap(r[run_type]["phenotype_vector"]),
            })
    return pooled


def _select_headline_k(k_results: list[dict]) -> int | None:
    """Same documented heuristic Level 1.2b's Work Package K used (the
    k with the highest defined silhouette among k >= 2) -- re-derived
    locally rather than importing a private name from
    ``level12b_stage_k_clustering_discovery.py``, matching this
    project's established small-disclosed-duplication precedent. Never
    privileges k=3 specifically; every k's own metrics remain in the
    full output regardless of which one is selected as this report's
    single stability-check anchor."""
    defined = [r for r in k_results if r["k"] >= 2 and r["metrics"]["silhouette"] == r["metrics"]["silhouette"]]
    if not defined:
        return None
    return max(defined, key=lambda r: r["metrics"]["silhouette"])["k"]


def run() -> dict:
    pooled = pool_records()
    records = [p["vector"] for p in pooled]
    source_stages = [p["source_stage"] for p in pooled]

    X, feature_names = build_feature_matrix(records, LEVEL13_DIMENSION_KEYS)
    missingness = missingness_report(X, feature_names)
    collinearity = examine_collinearity(X, feature_names)

    prep = preprocess_features(X, X, PRIMARY_MISSINGNESS_STRATEGY)
    Xp = prep["X_train"]
    n_total = Xp.shape[0]

    k_results_by_method = {
        method: compare_k_range(Xp, method, DEFAULT_K_RANGE, rng_seed=RNG_SEED)
        for method in CANDIDATE_METHODS if method != "hdbscan"
    }
    hdbscan_fit = fit_candidate(Xp, "hdbscan", rng_seed=RNG_SEED)
    hdbscan_fit["metrics"] = model_selection_metrics(Xp, hdbscan_fit["labels"], hdbscan_fit.get("model"), "hdbscan")

    headline_k = _select_headline_k(k_results_by_method["gmm"])
    silhouette_by_k = {r["k"]: r["metrics"]["silhouette"] for r in k_results_by_method["gmm"]}

    rng = np.random.default_rng(RNG_SEED)
    bootstrap = bootstrap_stability(Xp, "gmm", headline_k or 1, N_BOOTSTRAP, rng) if headline_k else {"mean_ari": float("nan")}

    labels_by_method = {"gmm": fit_candidate(Xp, "gmm", k=headline_k or 1, rng_seed=RNG_SEED)["labels"]}
    if headline_k:
        labels_by_method["hierarchical"] = fit_candidate(Xp, "hierarchical", k=headline_k, rng_seed=RNG_SEED)["labels"]
    labels_by_method["hdbscan"] = hdbscan_fit["labels"]
    agreement = algorithm_agreement(labels_by_method)
    agreement_aris = [v["ari"] for v in agreement.values() if v["ari"] == v["ari"]]
    mean_agreement_ari = float(np.mean(agreement_aris)) if agreement_aris else float("nan")

    # Structure-recovery diagnostic (Level 1.3's analog of Work Package
    # K's own IC-family-recovery check): does the headline clustering
    # just recover which of Stage 3/4/5 a run came from, rather than
    # revealing structure orthogonal to the pooling design?
    stage_labels = np.array(source_stages)[prep["apply_mask"]]
    cluster_vs_source_stage_ari = (
        float(adjusted_rand_score(stage_labels, labels_by_method["gmm"])) if headline_k else float("nan")
    )

    # missingness-strategy robustness (Section 9.1).
    missingness_strategy_aris = {}
    primary_labels_full = np.full(n_total, -1)
    primary_labels_full[prep["apply_mask"]] = labels_by_method["gmm"]
    for strategy in MISSINGNESS_STRATEGIES:
        if strategy == PRIMARY_MISSINGNESS_STRATEGY:
            continue
        p = preprocess_features(X, X, strategy)
        # "complete_case" can legitimately drop every pooled row here --
        # at least one Level 1.3 dimension is plausibly all-NaN across
        # all 216 runs from three heterogeneous designs (e.g. a response
        # type that never triggers within any of them) -- disclosed
        # degenerate case, not a bug: report NaN rather than fitting a
        # 0-sample model.
        if p["X_train"].shape[0] == 0:
            missingness_strategy_aris[strategy] = float("nan")
            continue
        strategy_labels_full = np.full(n_total, -1)
        strategy_labels_full[p["apply_mask"]] = fit_candidate(p["X_train"], "gmm", k=headline_k or 1, rng_seed=RNG_SEED)["labels"]
        common_mask = p["apply_mask"] & prep["apply_mask"]
        if common_mask.sum() < 2:
            missingness_strategy_aris[strategy] = float("nan")
            continue
        missingness_strategy_aris[strategy] = float(adjusted_rand_score(
            primary_labels_full[common_mask], strategy_labels_full[common_mask],
        ))

    return {
        "milestone": "level1.3_stage6_blind_phenotype_discovery",
        "source_files": {"stage3": STAGE3_PATH, "stage4": STAGE4_PATH, "stage5": STAGE5_PATH},
        "n_pooled_by_source": {s: source_stages.count(s) for s in sorted(set(source_stages))},
        "n_total": n_total,
        "feature_names": feature_names,
        "primary_missingness_strategy": PRIMARY_MISSINGNESS_STRATEGY,
        "missingness_report": missingness,
        "collinearity": {"feature_names": collinearity["feature_names"], "n_complete_rows": collinearity["n_complete_rows"]},
        "k_range_results": {
            method: [{"k": r["k"], "metrics": r["metrics"]} for r in results]
            for method, results in k_results_by_method.items()
        },
        "hdbscan_result": {
            "k": hdbscan_fit["k"], "metrics": hdbscan_fit["metrics"],
            "n_noise": int((hdbscan_fit["labels"] == -1).sum()),
        },
        "headline_k": headline_k,
        "silhouette_by_k": silhouette_by_k,
        "bootstrap_stability": dict(bootstrap),
        "algorithm_agreement": agreement,
        "mean_algorithm_agreement_ari": mean_agreement_ari,
        "cluster_vs_source_stage_ari": cluster_vs_source_stage_ari,
        "missingness_strategy_robustness_ari": missingness_strategy_aris,
        "candidate_independence_note": (
            "candidate clusters from the same fit are not independent statistical tests -- "
            "this report's own metrics are descriptive of one fit's structure, never p-value-style per-cluster claims"
        ),
        "decision_gate_note": (
            "no six-way decision-gate verdict is rendered here -- Section 23's classification "
            "(task #108) synthesizes this stage alongside Stage 7-9's own evidence"
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
    with open(f"{out_dir}/results.json", "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    result = write_report()
    print(f"Level 1.3 Stage 6: n_total={result['n_total']}, headline_k={result['headline_k']}")
    print(f"pooled by source: {result['n_pooled_by_source']}")
    print(f"report written to {OUT_DIR}/results.json")
