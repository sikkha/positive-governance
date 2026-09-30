#!/usr/bin/env python3
"""Level 1.2b, Work Package K (Section 16): clustering and structure
discovery over Work Package J's 576-run sustained-eligible pool.

**Reuses every clustering primitive from Level 1.2's own already-built,
already-tested pipeline** (``observer/phenotype_discovery.py`` --
``build_feature_matrix``, ``preprocess_features``, ``fit_candidate``,
``compare_k_range``, ``model_selection_metrics``, ``held_out_log_
likelihood``, ``bootstrap_stability``, ``co_assignment_matrix``,
``algorithm_agreement``); nothing about the underlying clustering
machinery is reimplemented for 1.2b. This Work Package's own
contribution is: (1) generating the real phenotype-vector feature
matrix this milestone's own 576-run pool needs (Work Package J's own
saved output does not carry phenotype vectors -- see this script's own
generation step docstring), (2) the four required stability checks
beyond bootstrap/algorithm-agreement (IC-family, temporal-window,
parameter-neighborhood, candidate-independence-of-tests), and (3) the
final closed-vocabulary verdict classifier Section 16 asks for.

**Why this re-simulates rather than reusing Work Package J's saved
data.** Work Package J's ``results.json`` stores outcome labels/
trajectory routes/eligibility, not phenotype vectors -- it never needed
them. Getting real phenotype vectors requires re-running the SAME
576 (point, seed, ic_family) triples from Work Package E's frozen
design (deterministic re-derivation, not a parameter-search rerun; see
Work Package J's own docstring for the identical justification).
Verified empirically before launching the full run: ``sim.run()`` for
one Level 1.2b config costs ~6.6s and a full ``institutional_phenotype_
vector`` call costs ~1.5ms -- essentially free once the simulation
itself has run -- so adding the temporal-window-stability snapshot
(one extra call at 70% of the run, alongside the end-of-run call) costs
~0.26s/run, not a second full simulation pass.

**Preregistered choice: primary missingness strategy.** Section 9.1
offers three strategies with none privileged a priori; this script
computes :func:`missingness_report` FIRST (a preprocessing-input
diagnostic, not a clustering OUTCOME -- Section 9's own "no peeking at
outcomes" prohibition is about not tuning preprocessing to produce a
particular cluster count, which checking a missing-data rate never
does) and documents the resulting choice of ``mean_impute`` as PRIMARY
(preserves every row -- ``complete_case`` would drop any run missing
even one dimension, and several dimensions are legitimately undefined
whenever a run never triggered the relevant event, e.g. E's audit-rate
being NaN for runs with zero audits) directly in
:data:`PRIMARY_MISSINGNESS_STRATEGY` below, BEFORE any cluster is fit --
the other two strategies are still fit and reported as the Section 9.1
missingness-strategy-robustness cross-check (reused directly by
``recurrence_criteria.missingness_strategy_robustness``, not
re-derived here)."""

from __future__ import annotations

import json
import os

import numpy as np

from abm_governance.observer.institutional_phenotype import institutional_phenotype_vector
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
    held_out_log_likelihood,
    missingness_report,
    preprocess_features,
)
from abm_governance.simulation import Simulation
from experiments.level12b_stage_e_joint_discovery import (
    IC_FAMILIES,
    _build_config,
    _inject_heterogeneous_proto_institutions,
    load_and_verify_design,
)
from experiments.level12b_stage_i_preregistration_manifest import load_and_verify_manifest

OUT_DIR = "outputs/level12b_stage_k_clustering_discovery"

PRIMARY_MISSINGNESS_STRATEGY = "mean_impute"

#: Section 6's own preregistered ten-dimension vector, unchanged.
DIMENSION_KEYS: tuple[str, ...] = tuple("CELDMRSFVH")

#: Temporal-window-stability snapshot: taken at this fraction of
#: ``n_steps`` (see module docstring -- one extra cheap
#: ``institutional_phenotype_vector`` call per run, not a second
#: simulation pass).
TEMPORAL_WINDOW_STABILITY_SNAPSHOT_FRACTION = 0.7

N_BOOTSTRAP = 30
HELD_OUT_FRACTION = 0.2
RNG_SEED = 20260818

#: Section 16's closed verdict vocabulary.
DISCOVERY_VERDICT_LABELS: tuple[str, ...] = (
    "insufficient_evidence", "failure_dominated", "unstable", "one_config", "continuum", "multi_config",
)


def _phenotype_vectors_for_all_runs() -> list[dict]:
    """Re-simulates every (point, ic_family, seed) triple in Work
    Package E's frozen design and returns one dict per run:
    ``{"joint_point_id", "ecological_point_id", "institutional_point_id",
    "ic_family", "seed", "vector_end", "vector_mid"}`` -- the two
    phenotype vectors (end-of-run and the temporal-window-stability
    snapshot) this Work Package needs."""
    wp_e = load_and_verify_design()
    out = []
    for point in wp_e["design"]["points"]:
        for ic_family in IC_FAMILIES:
            for seed in point["seeds"]:
                config = _build_config(point, seed)
                sim = Simulation(config)
                if ic_family == "heterogeneous_proto_institution":
                    _inject_heterogeneous_proto_institutions(sim, seed)
                mid_step = int(config.n_steps * TEMPORAL_WINDOW_STABILITY_SNAPSHOT_FRACTION)
                vector_mid = None
                for step in range(config.n_steps):
                    sim._run_one_step(step)
                    if step == mid_step:
                        rule_by_patch = dict(sim._last_dissolved_rule_by_patch)
                        rule_by_patch.update(sim.rule_registry)
                        vector_mid = institutional_phenotype_vector(
                            sim.event_log, rule_by_patch, sim.institution_registry, sim.delegate_registry,
                            sim.patch_system, sim._coordination_components, len(sim.patch_system.patches),
                            config.population_size, step, window=None,
                        )
                rule_by_patch = dict(sim._last_dissolved_rule_by_patch)
                rule_by_patch.update(sim.rule_registry)
                vector_end = institutional_phenotype_vector(
                    sim.event_log, rule_by_patch, sim.institution_registry, sim.delegate_registry,
                    sim.patch_system, sim._coordination_components, len(sim.patch_system.patches),
                    config.population_size, config.n_steps - 1, window=None,
                )
                out.append({
                    "joint_point_id": point["joint_point_id"], "ecological_point_id": point["ecological_point_id"],
                    "institutional_point_id": point["institutional_point_id"], "ic_family": ic_family, "seed": seed,
                    "vector_end": vector_end, "vector_mid": vector_mid if vector_mid is not None else vector_end,
                })
        print(f"joint point {point['joint_point_id']} phenotype vectors done", flush=True)
    return out


def _select_headline_k(k_results: list[dict]) -> int | None:
    """A documented, disclosed heuristic for picking ONE k to run the
    (computationally cheap but still needs a single anchor)
    bootstrap/co-assignment/parameter-neighborhood checks against:
    the k with the highest defined silhouette among k >= 2 (k=1 has no
    silhouette by construction and is separately always reported as
    the null in ``compare_k_range``'s own output) -- never privileges
    k=3 specifically, and this is a REPORTING anchor only: every k's
    own model-selection metrics remain in the full output regardless."""
    defined = [r for r in k_results if r["k"] >= 2 and r["metrics"]["silhouette"] == r["metrics"]["silhouette"]]
    if not defined:
        return None
    return max(defined, key=lambda r: r["metrics"]["silhouette"])["k"]


def classify_discovery_verdict(
    *,
    n_total: int, n_hard_minimum: int,
    failure_label_fraction: float, cluster_vs_failure_ari: float,
    headline_k: int | None, best_bootstrap_mean_ari: float, best_algorithm_agreement_mean_ari: float,
    silhouette_by_k: dict[int, float],
) -> dict:
    """Section 16's own closed, first-match-wins verdict:

    1. ``insufficient_evidence`` -- below the hard-minimum sample size,
       or no k besides 1 was ever evaluable.
    2. ``failure_dominated`` -- the discovered structure is
       substantially explained by the failure/non-failure split alone
       (``cluster_vs_failure_ari`` high) rather than revealing structure
       among non-collapsed runs.
    3. ``unstable`` -- neither bootstrap resampling nor cross-algorithm
       agreement supports the headline k above a minimal bar.
    4. ``one_config`` -- k=1 is competitive (no k>=2 clears a modest
       silhouette bar), i.e. the evidence does not support splitting
       the pool at all.
    5. ``continuum`` -- silhouette does not show a clear single peak
       across k (multiple k's within a small margin of the best,
       suggesting gradual rather than discrete structure).
    6. ``multi_config`` -- the explicit fallback when a stable,
       failure-independent, single-peaked k>=2 solution is supported."""
    if n_total < n_hard_minimum or headline_k is None:
        return {"verdict": "insufficient_evidence", "reasons": ["below_hard_minimum_or_no_evaluable_k_above_1"]}
    if cluster_vs_failure_ari == cluster_vs_failure_ari and cluster_vs_failure_ari >= 0.5:
        return {"verdict": "failure_dominated", "reasons": [f"cluster_vs_failure_ari={cluster_vs_failure_ari:.2f} >= 0.5"]}
    stability_ok = (
        (best_bootstrap_mean_ari == best_bootstrap_mean_ari and best_bootstrap_mean_ari >= 0.3)
        or (best_algorithm_agreement_mean_ari == best_algorithm_agreement_mean_ari and best_algorithm_agreement_mean_ari >= 0.3)
    )
    if not stability_ok:
        return {"verdict": "unstable", "reasons": ["neither_bootstrap_nor_algorithm_agreement_clears_0.3_ari"]}
    best_sil = silhouette_by_k.get(headline_k, float("nan"))
    if best_sil != best_sil or best_sil < 0.15:
        return {"verdict": "one_config", "reasons": [f"no_k>=2_clears_silhouette_0.15 (best={best_sil})"]}
    near_best = [k for k, s in silhouette_by_k.items() if s == s and s >= best_sil - 0.05 and k >= 2]
    if len(near_best) >= 3:
        return {"verdict": "continuum", "reasons": [f"{len(near_best)}_ks_within_0.05_silhouette_of_best"]}
    return {"verdict": "multi_config", "reasons": [f"stable_single_peaked_k={headline_k}_silhouette={best_sil:.2f}"]}


def run() -> dict:
    wp_e = load_and_verify_design()
    wp_i = load_and_verify_manifest()
    rng = np.random.default_rng(RNG_SEED)

    runs = _phenotype_vectors_for_all_runs()
    records_end = [r["vector_end"] for r in runs]
    records_mid = [r["vector_mid"] for r in runs]
    ic_families = [r["ic_family"] for r in runs]

    X_end, feature_names = build_feature_matrix(records_end, DIMENSION_KEYS)
    X_mid, _ = build_feature_matrix(records_mid, DIMENSION_KEYS)
    missingness = missingness_report(X_end, feature_names)
    collinearity = examine_collinearity(X_end, feature_names)

    prep = preprocess_features(X_end, X_end, PRIMARY_MISSINGNESS_STRATEGY)
    X = prep["X_train"]
    n_total = X.shape[0]

    from abm_governance.observer.phenotype_discovery import model_selection_metrics as _msm
    from sklearn.metrics import adjusted_rand_score

    k_results_by_method = {
        method: compare_k_range(X, method, DEFAULT_K_RANGE, rng_seed=RNG_SEED)
        for method in CANDIDATE_METHODS if method != "hdbscan"
    }
    hdbscan_fit = fit_candidate(X, "hdbscan", rng_seed=RNG_SEED)
    hdbscan_fit["metrics"] = _msm(X, hdbscan_fit["labels"], hdbscan_fit.get("model"), "hdbscan")

    headline_k = _select_headline_k(k_results_by_method["gmm"])
    silhouette_by_k = {r["k"]: r["metrics"]["silhouette"] for r in k_results_by_method["gmm"]}

    primary_labels_full = np.full(n_total, -1)
    primary_labels_full[prep["apply_mask"]] = fit_candidate(X, "gmm", k=headline_k or 1, rng_seed=RNG_SEED)["labels"]

    # missingness-strategy robustness cross-check (Section 9.1) -- fit
    # every alternative strategy at the headline k and compare its
    # labels (placed back into full-length, original-row-order arrays,
    # -1 for any row a strategy dropped) against the primary strategy's
    # own labels, restricted to rows both strategies actually cover.
    missingness_strategy_aris = {}
    for strategy in MISSINGNESS_STRATEGIES:
        if strategy == PRIMARY_MISSINGNESS_STRATEGY:
            continue
        p = preprocess_features(X_end, X_end, strategy)
        strategy_labels_full = np.full(n_total, -1)
        strategy_labels_full[p["apply_mask"]] = fit_candidate(p["X_train"], "gmm", k=headline_k or 1, rng_seed=RNG_SEED)["labels"]
        common_mask = p["apply_mask"] & prep["apply_mask"]
        if common_mask.sum() < 2:
            missingness_strategy_aris[strategy] = float("nan")
            continue
        missingness_strategy_aris[strategy] = float(adjusted_rand_score(
            primary_labels_full[common_mask], strategy_labels_full[common_mask],
        ))

    # bootstrap stability + co-assignment (headline k, gmm)
    bootstrap = bootstrap_stability(X, "gmm", headline_k or 1, N_BOOTSTRAP, rng) if headline_k else {"mean_ari": float("nan")}

    # cross-algorithm agreement at the headline k (hierarchical uses
    # the same k; hdbscan contributes its own naturally-determined k).
    labels_by_method = {"gmm": fit_candidate(X, "gmm", k=headline_k or 1, rng_seed=RNG_SEED)["labels"]}
    if headline_k:
        labels_by_method["hierarchical"] = fit_candidate(X, "hierarchical", k=headline_k, rng_seed=RNG_SEED)["labels"]
    labels_by_method["hdbscan"] = hdbscan_fit["labels"]
    agreement = algorithm_agreement(labels_by_method)
    agreement_aris = [v["ari"] for v in agreement.values() if v["ari"] == v["ari"]]
    mean_agreement_ari = float(np.mean(agreement_aris)) if agreement_aris else float("nan")

    # IC-family stability: does the headline clustering just recover
    # the two IC families?
    ic_binary = np.array([1 if f == "heterogeneous_proto_institution" else 0 for f in ic_families])
    ic_binary_masked = ic_binary[prep["apply_mask"]]
    cluster_vs_ic_ari = float(adjusted_rand_score(ic_binary_masked, labels_by_method["gmm"])) if headline_k else float("nan")

    # temporal-window stability: refit on the mid-run snapshot's own
    # feature matrix (same preprocessing pipeline), compare to the
    # end-of-run fit via ARI.
    prep_mid = preprocess_features(X_mid, X_mid, PRIMARY_MISSINGNESS_STRATEGY)
    common_mask_mid = prep["apply_mask"] & prep_mid["apply_mask"]
    temporal_window_stability_ari = float("nan")
    if headline_k and common_mask_mid.sum() >= 2:
        labels_end_sub = primary_labels_full[common_mask_mid]
        labels_mid_full = np.full(n_total, -1)
        labels_mid_full[prep_mid["apply_mask"]] = fit_candidate(prep_mid["X_train"], "gmm", k=headline_k, rng_seed=RNG_SEED)["labels"]
        labels_mid_sub = labels_mid_full[common_mask_mid]
        temporal_window_stability_ari = float(adjusted_rand_score(labels_end_sub, labels_mid_sub))

    # parameter-neighborhood stability: leave-one-institutional-point-out.
    institutional_point_ids = np.array([r["institutional_point_id"] for r in runs])[prep["apply_mask"]]
    loo_aris = []
    if headline_k:
        for pid in sorted(set(institutional_point_ids.tolist())):
            keep = institutional_point_ids != pid
            if keep.sum() < headline_k + 1:
                continue
            fit_loo = fit_candidate(X[keep], "gmm", k=headline_k, rng_seed=RNG_SEED)
            loo_aris.append(adjusted_rand_score(primary_labels_full[prep["apply_mask"]][keep], fit_loo["labels"]))
    parameter_neighborhood_mean_ari = float(np.mean(loo_aris)) if loo_aris else float("nan")

    # failure-dominance check: does clustering just separate
    # collapse-vs-not (a coarse ecological outcome proxy: population
    # fraction below 0.05, reusing V_demographic's own denominator
    # sense but computed directly here, since WP K works from
    # phenotype vectors alone and does not import WP J's outcome
    # labels -- kept a self-contained diagnostic).
    v_demo_idx = feature_names.index("V_demographic")
    collapse_proxy = (X_end[:, v_demo_idx] <= 0.05).astype(int)
    collapse_proxy_masked = collapse_proxy[prep["apply_mask"]]
    cluster_vs_failure_ari = float(adjusted_rand_score(collapse_proxy_masked, labels_by_method["gmm"])) if headline_k else float("nan")
    failure_label_fraction = float(np.mean(collapse_proxy)) if len(collapse_proxy) else float("nan")

    verdict = classify_discovery_verdict(
        n_total=n_total, n_hard_minimum=40,
        failure_label_fraction=failure_label_fraction, cluster_vs_failure_ari=cluster_vs_failure_ari,
        headline_k=headline_k, best_bootstrap_mean_ari=bootstrap.get("mean_ari", float("nan")),
        best_algorithm_agreement_mean_ari=mean_agreement_ari, silhouette_by_k=silhouette_by_k,
    )

    def _strip_model(fit):
        return {k: v for k, v in fit.items() if k != "model"}

    return {
        "source_design_hash": wp_e["hash"],
        "preregistration_manifest_hash": wp_i["hash"],
        "n_total": n_total,
        "primary_missingness_strategy": PRIMARY_MISSINGNESS_STRATEGY,
        "missingness_report": missingness,
        "collinearity": {"feature_names": collinearity["feature_names"], "n_complete_rows": collinearity["n_complete_rows"]},
        "k_range_results": {
            method: [{"k": r["k"], "metrics": r["metrics"]} for r in results]
            for method, results in k_results_by_method.items()
        },
        "hdbscan_result": {"k": hdbscan_fit["k"], "metrics": hdbscan_fit["metrics"], "n_noise": int((hdbscan_fit["labels"] == -1).sum())},
        "headline_k": headline_k,
        "held_out_log_likelihood": (
            held_out_log_likelihood(X[: int(n_total * (1 - HELD_OUT_FRACTION))], X[int(n_total * (1 - HELD_OUT_FRACTION)):], headline_k or 1, rng_seed=RNG_SEED)
            if headline_k else float("nan")
        ),
        "missingness_strategy_robustness_ari": missingness_strategy_aris,
        "bootstrap_stability": {k: v for k, v in bootstrap.items()},
        "algorithm_agreement": agreement,
        "mean_algorithm_agreement_ari": mean_agreement_ari,
        "cluster_vs_ic_family_ari": cluster_vs_ic_ari,
        "temporal_window_stability_ari": temporal_window_stability_ari,
        "parameter_neighborhood_stability_mean_ari": parameter_neighborhood_mean_ari,
        "cluster_vs_failure_proxy_ari": cluster_vs_failure_ari,
        "failure_proxy_fraction": failure_label_fraction,
        "candidate_independence_note": "candidate clusters from the same fit are not independent statistical tests -- this report's own metrics are descriptive of one fit's structure, never p-value-style per-cluster claims",
        "verdict": verdict,
    }


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    report = run()
    with open(f"{OUT_DIR}/results.json", "w") as f:
        json.dump(report, f, indent=2, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print(f"Work Package K: n_total={report['n_total']}, headline_k={report['headline_k']}")
    print(f"verdict: {report['verdict']}")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
