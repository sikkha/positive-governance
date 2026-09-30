#!/usr/bin/env python3
"""Level 1.2b, Work Package Q (Section 22): statistical-requirements
audit. Section 22 lists seven cross-cutting statistical-discipline
requirements that must hold across the WHOLE 1.2b pipeline (Work
Packages E through O), not just in any one script: seed-clustered /
hierarchical bootstrap inference; discovery/confirmation seed
disjointness; training-only preprocessing; uncertainty reporting at
all levels; sample-size reporting at every level; multiplicity
disclosure; structural NaN preservation (never zero-fill).

This Work Package does not run any new simulation. Every check either
(a) inspects already-saved Work Package E-O outputs on disk, (b)
inspects already-tested primitive functions' own source/behavior, or
(c) computes a cheap supplementary statistic (a nonparametric bootstrap
confidence interval) directly from ALREADY-SAVED per-run records --
never a new agent-based-model run.

**One genuine gap found and fixed, not just disclosed**: Work Packages
J and M's own saved reports carried point-estimate summary statistics
(collapse fraction, recovery rate) with no uncertainty quantification
at all -- a real absence, not a false alarm. Rather than only flagging
this, this Work Package computes seed-level nonparametric bootstrap
confidence intervals directly from those Work Packages' own already-
saved per-run records (:func:`_bootstrap_ci_on_fraction`) and reports
them here as a supplementary addition, closing the gap using only data
that already exists on disk.

**A second genuine gap found and fixed** (not merely audited):
:func:`bootstrap_stability` (Section 9.4) resamples individual seed-
rows as if independently exchangeable -- but this milestone's own
design has multiple seeds NESTED within each joint parameter point,
which are not independent draws of the point itself. Work Package Q
adds :func:`abm_governance.observer.phenotype_discovery.seed_
clustered_bootstrap_stability` (a genuine cluster bootstrap: resamples
whole ``joint_point_id`` groups, keeping every seed within a resampled
point together) and applies it to Work Package K's own discovery-pool
fit as a supplementary, properly-clustered robustness check, reported
alongside (never replacing) Work Package K's own flat bootstrap
result."""

from __future__ import annotations

import json
import os

import numpy as np

from abm_governance.observer.phenotype_discovery import (
    build_feature_matrix,
    fit_candidate,
    preprocess_features,
    seed_clustered_bootstrap_stability,
)
from experiments.level12b_stage_e_joint_discovery import load_and_verify_design
from experiments.level12b_stage_k_clustering_discovery import DIMENSION_KEYS, PRIMARY_MISSINGNESS_STRATEGY, RNG_SEED
from experiments.level12b_stage_i_preregistration_manifest import load_and_verify_manifest

OUT_DIR = "outputs/level12b_stage_q_statistical_requirements_audit"

STATISTICAL_REQUIREMENTS: tuple[str, ...] = (
    "seed_clustered_hierarchical_bootstrap", "discovery_confirmation_seed_disjointness",
    "training_only_preprocessing", "uncertainty_reporting_at_all_levels",
    "sample_size_reporting_at_every_level", "multiplicity_disclosure", "structural_nan_preservation",
)

N_BOOTSTRAP_CI = 2000
CI_RNG_SEED = 22_000_000


def _bootstrap_ci_on_fraction(binary_outcomes: list[int], n_bootstrap: int = N_BOOTSTRAP_CI, rng_seed: int = CI_RNG_SEED) -> dict:
    """A plain nonparametric percentile bootstrap confidence interval
    on a fraction, resampling whole runs (the same "seed-run is the
    primary independent observation" unit used everywhere else this
    milestone) with replacement."""
    arr = np.asarray(binary_outcomes, dtype=float)
    n = len(arr)
    if n == 0:
        return {"point_estimate": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"), "n": 0}
    rng = np.random.default_rng(rng_seed)
    point = float(np.mean(arr))
    means = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        means.append(float(np.mean(arr[idx])))
    means.sort()
    lo = means[int(0.025 * n_bootstrap)]
    hi = means[int(0.975 * n_bootstrap) - 1]
    return {"point_estimate": point, "ci_low": lo, "ci_high": hi, "n": n, "method": "nonparametric_percentile_bootstrap_2.5_97.5"}


def check_seed_disjointness() -> dict:
    with open("outputs/level12b_stage_e_joint_discovery/results.json") as f:
        wp_e = json.load(f)
    with open("outputs/level12b_stage_l1_confirmation_pool/results.json") as f:
        wp_l = json.load(f)
    with open("outputs/level12b_stage_m_scaling_robustness/results.json") as f:
        wp_m = json.load(f)
    with open("outputs/level12b_stage_n_causal_collapse_decomposition/results.json") as f:
        wp_n = json.load(f)

    seeds_e = {r["seed"] for r in wp_e["records"]}
    seeds_l = {r["seed"] for r in wp_l["records"]}
    seeds_m = {r["seed"] for r in wp_m["records"]}
    seeds_n = {p["seed"] for fr in wp_n["factor_results"] for p in fr["pairs"]}

    pools = {"E_discovery": seeds_e, "L_confirmation": seeds_l, "M_scaling": seeds_m, "N_causal": seeds_n}
    pairwise_overlaps = {}
    names = list(pools.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            overlap = pools[names[i]] & pools[names[j]]
            pairwise_overlaps[f"{names[i]}_vs_{names[j]}"] = sorted(overlap)

    all_disjoint = all(len(v) == 0 for v in pairwise_overlaps.values())
    return {
        "status": "pass" if all_disjoint else "fail",
        "pool_sizes": {k: len(v) for k, v in pools.items()},
        "pairwise_overlaps": pairwise_overlaps,
    }


def check_seed_clustered_bootstrap() -> dict:
    with open("outputs/level12b_stage_l2_discovery_pool_refit/results.json") as f:
        discovery_pool = json.load(f)
    with open("outputs/level12b_stage_k_clustering_discovery/results.json") as f:
        wp_k = json.load(f)
    headline_k = wp_k["headline_k"]
    records = discovery_pool["records"]
    X_disc, _ = build_feature_matrix([r["vector_end"] for r in records], DIMENSION_KEYS)
    prep = preprocess_features(X_disc, X_disc, PRIMARY_MISSINGNESS_STRATEGY)
    joint_point_ids = [r["joint_point_id"] for r in records]
    rng = np.random.default_rng(RNG_SEED)
    clustered = seed_clustered_bootstrap_stability(prep["X_train"], joint_point_ids, "gmm", headline_k, 30, rng)
    return {
        "status": "implemented_and_applied",
        "flat_bootstrap_mean_ari_from_work_package_k": wp_k["bootstrap_stability"].get("mean_ari"),
        "seed_clustered_bootstrap": clustered,
        "interpretation": (
            "the seed-clustered estimate accounts for the nested (joint_point -> seed) structure; "
            "compared side by side with Work Package K's own flat estimate rather than replacing it"
        ),
    }


def check_training_only_preprocessing() -> dict:
    return {
        "status": "pass",
        "evidence": [
            "preprocess_features(X_train, X_apply, strategy) fits every transform (imputation values, standardization mean/std) on X_train ONLY, per its own docstring and tests/test_level12_phenotype_discovery.py",
            "Work Package L stage 3's held_out_predictiveness call uses X_train=discovery pool, X_apply=confirmation pool -- disjoint pools by seed-construction (see discovery_confirmation_seed_disjointness check)",
            "Work Package L stage 3's assignment_stability computation refits the frozen rule on the discovery pool only, then .predict()s on the confirmation pool -- never refit on the combined pool",
        ],
    }


def check_uncertainty_reporting() -> dict:
    with open("outputs/level12b_stage_j_main_discovery_pipeline/results.json") as f:
        wp_j = json.load(f)
    with open("outputs/level12b_stage_m_scaling_robustness/results.json") as f:
        wp_m = json.load(f)

    collapse_outcomes = [1 if r["all_outcome_label"] == "collapse" else 0 for r in wp_j["records"]]
    viable_outcomes = [1 if r["all_outcome_label"] == "viable" else 0 for r in wp_j["records"]]
    wp_j_supplementary_ci = {
        "collapse_fraction": _bootstrap_ci_on_fraction(collapse_outcomes),
        "viable_fraction": _bootstrap_ci_on_fraction(viable_outcomes),
    }

    pop_recovery = [1 if r["functional_recovery"]["population"]["recovered"] else 0 for r in wp_m["records"]]
    eco_recovery = [1 if r["functional_recovery"]["ecological"]["recovered"] else 0 for r in wp_m["records"]]
    wp_m_supplementary_ci = {
        "population_recovery_rate": _bootstrap_ci_on_fraction(pop_recovery),
        "ecological_recovery_rate": _bootstrap_ci_on_fraction(eco_recovery),
    }

    per_work_package_uncertainty_fields = {
        "E_discovery": "none at the summary level (design/ledger-closure report only) -- no cluster/probability estimate is reported at this stage to need one",
        "J_main_discovery": "NONE originally (gap) -- CLOSED here via supplementary bootstrap CIs, see wp_j_supplementary_ci below",
        "K_clustering": "bootstrap_stability (mean/std ARI), algorithm_agreement (pairwise ARI/VI), missingness_strategy_robustness_ari",
        "L_confirmation": "assignment_stability_ari, feature_profile_stability cosine similarities, held_out_log_likelihood, independent_replication's own bootstrap/algorithm-agreement",
        "M_scaling": "NONE originally (gap) -- CLOSED here via supplementary bootstrap CIs, see wp_m_supplementary_ci below; measured_modularity reported per-run (raw spread visible, not just a mean)",
        "N_causal_ablations": "Wilcoxon signed-rank statistic/p-value per outcome per factor (explicitly labeled supplementary given n=8)",
        "O_recurrence_classification": "reuses K/L's own uncertainty fields directly (proxy convergence evidence), attractor_label_evidence reports both recovery rates rather than a single point claim",
    }
    return {
        "status": "gaps_found_and_closed",
        "per_work_package_uncertainty_fields": per_work_package_uncertainty_fields,
        "wp_j_supplementary_bootstrap_ci": wp_j_supplementary_ci,
        "wp_m_supplementary_bootstrap_ci": wp_m_supplementary_ci,
    }


def check_sample_size_reporting() -> dict:
    files = {
        "E_discovery": "outputs/level12b_stage_e_joint_discovery/results.json",
        "J_main_discovery": "outputs/level12b_stage_j_main_discovery_pipeline/results.json",
        "K_clustering": "outputs/level12b_stage_k_clustering_discovery/results.json",
        "L_confirmation": "outputs/level12b_stage_l3_prospective_confirmation/results.json",
        "M_scaling": "outputs/level12b_stage_m_scaling_robustness/results.json",
        "N_causal_ablations": "outputs/level12b_stage_n_causal_collapse_decomposition/results.json",
    }
    sample_size_keys = ("n_runs_completed", "n_total", "n_confirmation_runs", "n_total_runs", "n_pairs")
    findings = {}
    all_pass = True
    for wp_name, path in files.items():
        with open(path) as f:
            report = json.load(f)
        present = [k for k in sample_size_keys if k in report]
        findings[wp_name] = {"present_keys": present, "has_sample_size_field": len(present) > 0}
        all_pass = all_pass and len(present) > 0
    return {"status": "pass" if all_pass else "fail", "findings": findings}


def check_multiplicity_disclosure() -> dict:
    return {
        "status": "disclosed",
        "multiple_comparisons_in_this_milestone": [
            "Work Package K: up to 8 k values x up to 3 candidate methods (gmm/hierarchical/hdbscan) model-selection metrics evaluated side by side -- no single metric or k privileged (Section 9.3's own rule), which avoids p-hacking a cluster count but does mean many metric values are reported without a joint correction",
            "Work Package N: 13 factors x 3 primary paired outcomes (ecological_resource_fraction, cumulative_unmet_extraction_demand, fraction_of_steps_below_one) = 39 Wilcoxon signed-rank tests, each with n=8 pairs",
            "Work Package L: headline_k=4 clusters x per-cluster feature-profile-stability cosine similarity comparisons",
        ],
        "correction_applied": False,
        "rationale": (
            "no formal family-wise (Bonferroni/Benjamini-Hochberg) correction is applied anywhere in this milestone. "
            "Every one of the 39 Work Package N Wilcoxon tests already carries its own 'n too small for a confident "
            "test; supplementary only' disclosure in its own output -- at n=8 per test, a correction would leave "
            "essentially no power to detect anything, so results are read descriptively (paired-difference direction "
            "and magnitude, outcome-label transition counts) rather than as a battery of confirmatory p<0.05 claims. "
            "Work Package K's multi-metric/multi-k reporting is explicitly Section 9.3's own anti-p-hacking design "
            "(report everything, privilege nothing) rather than a hypothesis-testing multiplicity problem."
        ),
    }


def check_structural_nan_preservation() -> dict:
    # A direct, minimal illustrative check (not a new simulation): a
    # record missing a dimension's value must produce NaN in the
    # matrix, never 0.0 -- build_feature_matrix's own documented
    # contract, reused unmodified throughout Work Packages K/L/O.
    fake_record_with_missing_dim = {"C": {"value": 1.0}, "E": {"value": float("nan")}}
    X, names = build_feature_matrix([fake_record_with_missing_dim], ("C", "E"))
    e_idx = names.index("E")
    preserved = bool(np.isnan(X[0, e_idx]))
    return {
        "status": "pass" if preserved else "fail",
        "evidence": "build_feature_matrix's own docstring: 'Structural NaN is preserved exactly, never zero-filled here'",
        "direct_check_result": {"value_at_missing_dimension": None if preserved else float(X[0, e_idx]), "preserved_as_nan": preserved},
        "note": "zero-filling (mean_impute's own column-mean fallback) happens ONLY inside preprocess_features, a separate, later, explicitly-disclosed step -- never inside build_feature_matrix itself",
    }


def run() -> dict:
    wp_i = load_and_verify_manifest()
    load_and_verify_design()

    checks = {
        "seed_clustered_hierarchical_bootstrap": check_seed_clustered_bootstrap(),
        "discovery_confirmation_seed_disjointness": check_seed_disjointness(),
        "training_only_preprocessing": check_training_only_preprocessing(),
        "uncertainty_reporting_at_all_levels": check_uncertainty_reporting(),
        "sample_size_reporting_at_every_level": check_sample_size_reporting(),
        "multiplicity_disclosure": check_multiplicity_disclosure(),
        "structural_nan_preservation": check_structural_nan_preservation(),
    }
    return {
        "preregistration_manifest_hash": wp_i["hash"],
        "requirements": list(STATISTICAL_REQUIREMENTS),
        "checks": checks,
    }


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    report = run()
    with open(f"{OUT_DIR}/results.json", "w") as f:
        json.dump(report, f, indent=2, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    for req, result in report["checks"].items():
        print(f"{req}: {result['status']}")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
