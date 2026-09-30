#!/usr/bin/env python3
"""Level 1.2b, Work Package L, stage 3 (Section 17): the actual
prospective-confirmation analysis -- combines stage 1's fresh 384-run
confirmation pool with stage 2's re-derived discovery-pool feature
matrix and runs every test the frozen registry (stage 0) committed to,
under the null-replication framing that registry disclosed (Section
16's own ``continuum`` verdict means no discrete candidate classes
were confirmed, so no test here claims to validate N independent
institutional-phenotype candidates).

**``tests_applied_to_every_candidate`` (Work Package I manifest),
operationalized here:**

1. ``recurrence_across_seeds_points_and_initial_condition_families`` --
   Section 16's own discovery procedure (:func:`_independent_discovery`
   below, reusing every clustering primitive Work Package K used)
   rerun on the confirmation pool's OWN feature matrix, pooled across
   its entire fresh design (24 joint points x 8 seeds x 2 IC
   families) -- not a per-point/per-seed micro-analysis, which would
   be badly underpowered at this sample size; the IC-family dimension
   specifically is additionally checked via ``cluster_vs_ic_family_ari``
   (does the confirmation-pool's own clustering just rediscover IC
   family membership).
2. ``assignment_stability`` -- the frozen headline_k GMM (refit on the
   discovery pool per the registry's own ``frozen_diagnostic_
   partition``) applied out-of-sample to the confirmation pool,
   compared via ARI against the confirmation pool's own independently
   refit headline_k partition.
3. ``feature_profile_stability`` -- per-cluster mean raw feature
   vectors under the SAME frozen assignment rule, compared between
   the discovery pool (in-sample) and the confirmation pool
   (out-of-sample) cluster-by-cluster (label indices correspond
   directly since it is the same model/rule applied to both -- no
   cluster-matching ambiguity).
4. ``held_out_predictiveness`` -- ``held_out_log_likelihood`` (already
   Section 9.3 machinery, same call convention Level 1.2's own Stage 5
   confirmation used), discovery pool as training, confirmation pool
   genuinely out-of-sample.
5. ``unclassified_outcome_rate`` -- fraction of the confirmation pool
   Work Package J's own ``classify_all_outcome`` could not classify.
6. ``failure_transition_rate`` -- fraction of the confirmation pool
   whose ``classify_failure_trajectory`` route is anything other than
   ``no_collapse_observed`` (i.e. the run's own trajectory showed a
   transition into the collapse definition at some point, whether or
   not it ended there)."""

from __future__ import annotations

import json
import os

import numpy as np
from sklearn.metrics import adjusted_rand_score

from abm_governance.observer.phenotype_discovery import (
    CANDIDATE_METHODS,
    DEFAULT_K_RANGE,
    algorithm_agreement,
    bootstrap_stability,
    build_feature_matrix,
    compare_k_range,
    fit_candidate,
    held_out_log_likelihood,
    missingness_report,
    preprocess_features,
)
from experiments.level12b_stage_e_joint_discovery import IC_FAMILIES
from experiments.level12b_stage_i_preregistration_manifest import CONFIRMATION_RULES
from experiments.level12b_stage_k_clustering_discovery import (
    DIMENSION_KEYS,
    N_BOOTSTRAP,
    PRIMARY_MISSINGNESS_STRATEGY,
    RNG_SEED,
    _select_headline_k,
    classify_discovery_verdict,
)
from experiments.level12b_stage_l0_confirmation_registry import load_and_verify_confirmation_registry

OUT_DIR = "outputs/level12b_stage_l3_prospective_confirmation"

#: Section 17's closed confirmation-verdict vocabulary, first-match-
#: wins. A continuum discovery verdict makes ``null_replicated`` the
#: preregistered primary expectation (see stage 0's registry); this is
#: NOT a claim that nothing interesting was found -- it means the
#: absence of a stable multi-config structure recurred on independent
#: data, which is itself the confirmatory result.
CONFIRMATION_VERDICT_LABELS: tuple[str, ...] = (
    "insufficient_confirmation_data", "null_replicated", "unexpected_recurring_structure",
)


def classify_confirmation_verdict(*, n_total: int, n_hard_minimum: int, independent_replication_verdict: str | None) -> dict:
    """1. ``insufficient_confirmation_data`` -- below the hard-minimum
    run count.
    2. ``unexpected_recurring_structure`` -- the confirmation pool's OWN
    independent discovery replication reached ``multi_config`` despite
    the source discovery's ``continuum`` verdict -- a disclosed anomaly,
    never silently reclassified as success.
    3. ``null_replicated`` -- the default/expected outcome: no stable
    multi_config structure recurred, consistent with Section 16's own
    continuum finding."""
    if n_total < n_hard_minimum:
        return {"verdict": "insufficient_confirmation_data", "reasons": [f"n_total={n_total} < hard_minimum={n_hard_minimum}"]}
    if independent_replication_verdict == "multi_config":
        return {"verdict": "unexpected_recurring_structure", "reasons": ["independent_replication_verdict=multi_config despite source discovery's continuum verdict"]}
    return {"verdict": "null_replicated", "reasons": [f"independent_replication_verdict={independent_replication_verdict} (not multi_config)"]}


def _independent_discovery(X_conf: np.ndarray, feature_names: list[str], ic_families_conf: list[str], n_hard_minimum: int) -> dict:
    """Reruns Section 16's own discovery procedure on the confirmation
    pool's OWN feature matrix, as its own completely independent
    discovery attempt -- mirrors Work Package K's ``run()`` body
    exactly (same primitives, same RNG_SEED, same verdict thresholds),
    never adjusted after seeing the confirmation pool's own result."""
    prep = preprocess_features(X_conf, X_conf, PRIMARY_MISSINGNESS_STRATEGY)
    X = prep["X_train"]
    n_total = X.shape[0]
    rng = np.random.default_rng(RNG_SEED)

    k_results_by_method = {
        method: compare_k_range(X, method, DEFAULT_K_RANGE, rng_seed=RNG_SEED)
        for method in CANDIDATE_METHODS if method != "hdbscan"
    }
    from abm_governance.observer.phenotype_discovery import model_selection_metrics as _msm
    hdbscan_fit = fit_candidate(X, "hdbscan", rng_seed=RNG_SEED)
    hdbscan_fit["metrics"] = _msm(X, hdbscan_fit["labels"], hdbscan_fit.get("model"), "hdbscan")

    headline_k = _select_headline_k(k_results_by_method["gmm"])
    silhouette_by_k = {r["k"]: r["metrics"]["silhouette"] for r in k_results_by_method["gmm"]}

    labels_gmm = fit_candidate(X, "gmm", k=headline_k or 1, rng_seed=RNG_SEED)["labels"]
    labels_by_method = {"gmm": labels_gmm}
    if headline_k:
        labels_by_method["hierarchical"] = fit_candidate(X, "hierarchical", k=headline_k, rng_seed=RNG_SEED)["labels"]
    labels_by_method["hdbscan"] = hdbscan_fit["labels"]
    agreement = algorithm_agreement(labels_by_method)
    agreement_aris = [v["ari"] for v in agreement.values() if v["ari"] == v["ari"]]
    mean_agreement_ari = float(np.mean(agreement_aris)) if agreement_aris else float("nan")

    bootstrap = bootstrap_stability(X, "gmm", headline_k or 1, N_BOOTSTRAP, rng) if headline_k else {"mean_ari": float("nan")}

    ic_binary = np.array([1 if f == "heterogeneous_proto_institution" else 0 for f in ic_families_conf])
    cluster_vs_ic_ari = float(adjusted_rand_score(ic_binary, labels_gmm)) if headline_k else float("nan")

    v_demo_idx = feature_names.index("V_demographic")
    collapse_proxy = (X_conf[:, v_demo_idx] <= 0.05).astype(int)
    cluster_vs_failure_ari = float(adjusted_rand_score(collapse_proxy, labels_gmm)) if headline_k else float("nan")
    failure_label_fraction = float(np.mean(collapse_proxy)) if len(collapse_proxy) else float("nan")

    verdict = classify_discovery_verdict(
        n_total=n_total, n_hard_minimum=n_hard_minimum,
        failure_label_fraction=failure_label_fraction, cluster_vs_failure_ari=cluster_vs_failure_ari,
        headline_k=headline_k, best_bootstrap_mean_ari=bootstrap.get("mean_ari", float("nan")),
        best_algorithm_agreement_mean_ari=mean_agreement_ari, silhouette_by_k=silhouette_by_k,
    )
    return {
        "n_total": n_total, "headline_k": headline_k, "silhouette_by_k": silhouette_by_k,
        "mean_algorithm_agreement_ari": mean_agreement_ari,
        "bootstrap_mean_ari": bootstrap.get("mean_ari", float("nan")),
        "cluster_vs_ic_family_ari": cluster_vs_ic_ari,
        "cluster_vs_failure_proxy_ari": cluster_vs_failure_ari,
        "failure_proxy_fraction": failure_label_fraction,
        "verdict": verdict,
    }


def run() -> dict:
    registry_verified = load_and_verify_confirmation_registry()
    registry = registry_verified["registry"]
    headline_k = registry["frozen_diagnostic_partition"]["k"]

    with open("outputs/level12b_stage_l1_confirmation_pool/results.json") as f:
        confirmation_pool = json.load(f)
    with open("outputs/level12b_stage_l2_discovery_pool_refit/results.json") as f:
        discovery_pool = json.load(f)

    conf_records = confirmation_pool["records"]
    X_conf, feature_names = build_feature_matrix([r["phenotype_vector"] for r in conf_records], DIMENSION_KEYS)
    ic_families_conf = [r["ic_family"] for r in conf_records]

    X_disc, _ = build_feature_matrix([r["vector_end"] for r in discovery_pool["records"]], DIMENSION_KEYS)

    n_hard_minimum = CONFIRMATION_RULES["hard_minimum"]["total_runs"]

    # 1. recurrence: independent replication of Section 16's own
    # discovery procedure, run fresh on the confirmation pool alone.
    independent_replication = _independent_discovery(X_conf, feature_names, ic_families_conf, n_hard_minimum)

    # 2-4. assignment stability / feature-profile stability / held-out
    # predictiveness: the frozen headline_k rule (refit on the
    # discovery pool, exactly reproducing Work Package K's own
    # headline fit) applied out-of-sample to the confirmation pool.
    prep = preprocess_features(X_disc, X_conf, PRIMARY_MISSINGNESS_STRATEGY)
    frozen_fit = fit_candidate(prep["X_train"], "gmm", k=headline_k, rng_seed=RNG_SEED)
    discovery_frozen_labels = frozen_fit["labels"]
    confirmation_frozen_labels = frozen_fit["model"].predict(prep["X_apply"])

    prep_conf_own = preprocess_features(X_conf, X_conf, PRIMARY_MISSINGNESS_STRATEGY)
    own_fit = fit_candidate(prep_conf_own["X_train"], "gmm", k=headline_k, rng_seed=RNG_SEED)
    assignment_stability_ari = float(adjusted_rand_score(confirmation_frozen_labels, own_fit["labels"]))

    feature_profile_similarities = {}
    for c in range(headline_k):
        disc_mask = discovery_frozen_labels == c
        conf_mask = confirmation_frozen_labels == c
        if disc_mask.sum() == 0 or conf_mask.sum() == 0:
            feature_profile_similarities[c] = float("nan")
            continue
        disc_mean = np.nanmean(X_disc[disc_mask], axis=0)
        conf_mean = np.nanmean(X_conf[conf_mask], axis=0)
        # nan-safe cosine similarity over dimensions defined in both.
        both_defined = ~(np.isnan(disc_mean) | np.isnan(conf_mean))
        if both_defined.sum() < 2 or np.linalg.norm(disc_mean[both_defined]) == 0 or np.linalg.norm(conf_mean[both_defined]) == 0:
            feature_profile_similarities[c] = float("nan")
            continue
        cos = float(np.dot(disc_mean[both_defined], conf_mean[both_defined]) / (
            np.linalg.norm(disc_mean[both_defined]) * np.linalg.norm(conf_mean[both_defined])
        ))
        feature_profile_similarities[c] = cos
    defined_sims = [v for v in feature_profile_similarities.values() if v == v]
    mean_feature_profile_similarity = float(np.mean(defined_sims)) if defined_sims else float("nan")

    held_out_ll = held_out_log_likelihood(prep["X_train"], prep["X_apply"], headline_k, rng_seed=RNG_SEED)

    # 5-6. unclassified-outcome rate / failure-transition rate.
    n_total_conf = confirmation_pool["n_runs_completed"]
    unclassified_outcome_rate = confirmation_pool["all_outcome_summary"].get("unclassified", 0) / n_total_conf if n_total_conf else float("nan")
    n_failure_transition = sum(1 for r in conf_records if r["failure_trajectory"]["route"] != "no_collapse_observed")
    failure_transition_rate = n_failure_transition / n_total_conf if n_total_conf else float("nan")

    confirmation_verdict = classify_confirmation_verdict(
        n_total=n_total_conf, n_hard_minimum=n_hard_minimum,
        independent_replication_verdict=independent_replication["verdict"]["verdict"],
    )

    report = {
        "confirmation_registry_hash": registry_verified["hash"],
        "confirmation_design_hash": registry["confirmation_design_hash"],
        "source_design_hash": registry["source_design_hash"],
        "preregistration_manifest_hash": registry["preregistration_manifest_hash"],
        "n_confirmation_runs": n_total_conf,
        "n_discovery_runs_refit": discovery_pool["n_records"],
        "headline_k": headline_k,
        "recurrence_across_seeds_points_and_ic_families": independent_replication,
        "assignment_stability_ari": assignment_stability_ari,
        "feature_profile_stability": {
            "per_cluster_cosine_similarity": {str(k): v for k, v in feature_profile_similarities.items()},
            "mean_cosine_similarity": mean_feature_profile_similarity,
        },
        "held_out_predictiveness_log_likelihood": held_out_ll,
        "unclassified_outcome_rate": unclassified_outcome_rate,
        "failure_transition_rate": failure_transition_rate,
        "all_outcome_summary": confirmation_pool["all_outcome_summary"],
        "failure_trajectory_summary": confirmation_pool["failure_trajectory_summary"],
        "candidate_status": registry["candidate_status"],
        "confirmation_verdict": confirmation_verdict,
    }
    return report


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    report = run()
    with open(f"{OUT_DIR}/results.json", "w") as f:
        json.dump(report, f, indent=2, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print(f"Work Package L: n_confirmation_runs={report['n_confirmation_runs']}, headline_k={report['headline_k']}")
    print(f"independent replication verdict: {report['recurrence_across_seeds_points_and_ic_families']['verdict']}")
    print(f"assignment_stability_ari={report['assignment_stability_ari']:.3f}, held_out_ll={report['held_out_predictiveness_log_likelihood']:.1f}")
    print(f"confirmation verdict: {report['confirmation_verdict']}")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
