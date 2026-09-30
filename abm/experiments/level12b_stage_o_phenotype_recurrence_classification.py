#!/usr/bin/env python3
"""Level 1.2b, Work Package O (Section 20): phenotype recurrence and
convergence classification. Applies Work Package H's own audited
recurrence/convergence criteria to whatever structure Work Packages K
and L actually found, distinguishing six candidate explanations for
observed similarity (shared-lineage persistence / independent
structural convergence / environmentally forced similarity / temporary
similarity / measurement compression / failure-state similarity), uses
ONLY the cautious closed vocabulary Section 20 specifies (candidate /
confirmed / transient / failure / boundary / continuum / unclassified)
for its own top-level label, and never assigns an "attractor" label
without direct basin/perturbation/return evidence.

**No new simulation is run by this Work Package.** Every input is
already-computed evidence from Work Packages E/K/L/M's own saved
reports plus two cheap (no-simulation) diagnostics computed here
directly from Work Package L's already-derived discovery-pool feature
matrix (``examine_collinearity``, ``dimensionality_reduction_
diagnostic`` -- both already-built Section 9.1/9.2 primitives, reused
unmodified).

**One evidence gap, disclosed rather than silently worked around**:
``shared_lineage_persistence`` and a literal (not proxied)
``independent_structural_convergence`` test both require per-run
``rule_lineage_id`` data (Work Package H's own ``compose_global_
lineage_id`` machinery), which none of Work Package E/J/K/L/M's saved
outputs persisted -- obtaining it would require a FOURTH full 576-run
re-simulation of Work Package E's design. Given Work Package K's own
``continuum`` verdict and Work Package L's own ``null_replicated``
confirmation already establish that no discrete, well-separated
candidate structure exists to explain via shared ancestry in the first
place, a further expensive re-simulation to test a more granular
explanation for structure that was not confirmed to exist is judged
low-value and is NOT performed here -- disclosed explicitly rather
than silently skipped. ``mean_algorithm_agreement_ari``/
``bootstrap_stability``/Work Package L's own ``assignment_stability_
ari`` are used as an explicit, labeled PROXY for independent
structural convergence (do independently-fit fits agree with each
other), not a substitute for a genuine lineage-based permutation
test.

**Attractor-label discipline, honored directly from evidence.** Work
Package M's own ``functional_recovery`` data showed population-
fraction recovery ``False`` for ALL 32 scaling-robustness runs (0%)
and ecological-fraction recovery ``True`` for 28/32 (87.5%) -- mixed,
and the population dimension shows NO basin-of-attraction return
evidence at all. Per Section 20's own rule, no "attractor" label is
assigned anywhere in this Work Package's output; both figures are
reported, not just the more favorable one."""

from __future__ import annotations

import json
import os

import numpy as np

from abm_governance.observer.phenotype_discovery import (
    build_feature_matrix,
    dimensionality_reduction_diagnostic,
    examine_collinearity,
    fit_candidate,
    preprocess_features,
)
from experiments.level12b_stage_e_joint_discovery import load_and_verify_design
from experiments.level12b_stage_k_clustering_discovery import DIMENSION_KEYS, PRIMARY_MISSINGNESS_STRATEGY, RNG_SEED
from experiments.level12b_stage_l0_confirmation_registry import load_and_verify_confirmation_registry

OUT_DIR = "outputs/level12b_stage_o_phenotype_recurrence_classification"

#: Section 20's own six candidate explanations for observed cross-run
#: phenotype similarity.
EXPLANATORY_CATEGORIES: tuple[str, ...] = (
    "shared_lineage_persistence", "independent_structural_convergence", "environmentally_forced_similarity",
    "temporary_similarity", "measurement_compression", "failure_state_similarity",
)

#: Section 20's own cautious, closed top-level vocabulary -- no other
#: word (especially never "attractor") is used as a top-level label
#: anywhere in this Work Package's output.
CAUTIOUS_LABELS: tuple[str, ...] = ("candidate", "confirmed", "transient", "failure", "boundary", "continuum", "unclassified")

#: Evidence bars for the proxy independent-convergence check and the
#: environmental-forcing diversity check -- disclosed, not tuned to
#: produce a particular answer.
CONVERGENCE_PROXY_ARI_BAR = 0.3
ENVIRONMENTAL_FORCING_DIVERSITY_FLOOR = 0.5  # fraction of distinct joint points among cluster members


def classify_overall_recurrence_label(*, n_total: int, n_hard_minimum: int, discovery_verdict: str | None, confirmation_verdict: str | None) -> dict:
    """First-match-wins, over Section 20's own closed vocabulary:
    1. ``unclassified`` -- below the hard minimum, no discovery
       verdict, or discovery found no split worth reporting
       (``one_config``) -- there is nothing here to classify.
    2. ``failure`` -- discovery's own structure is substantially just
       the failure/non-failure split.
    3. ``transient`` -- discovery's own structure did not clear the
       stability bar (``unstable``).
    4. ``continuum`` -- discovery's own verdict was itself a continuum
       (this milestone's actual result).
    5. ``confirmed`` -- discovery found ``multi_config`` AND an
       independent confirmation pool ALSO found recurring structure.
    6. ``boundary`` -- discovery found ``multi_config`` but the
       independent confirmation pool did not reproduce it -- sits
       between "candidate" and "confirmed", disclosed as such.
    7. ``candidate`` -- discovery found ``multi_config`` and
       confirmation has not yet been run against it."""
    if n_total < n_hard_minimum or discovery_verdict is None or discovery_verdict == "one_config":
        return {"label": "unclassified", "reasons": ["below_hard_minimum_or_no_discovery_verdict_or_one_config"]}
    if discovery_verdict == "failure_dominated":
        return {"label": "failure", "reasons": ["discovery_verdict=failure_dominated"]}
    if discovery_verdict == "unstable":
        return {"label": "transient", "reasons": ["discovery_verdict=unstable"]}
    if discovery_verdict == "continuum":
        return {"label": "continuum", "reasons": ["discovery_verdict=continuum"]}
    if discovery_verdict == "multi_config" and confirmation_verdict == "unexpected_recurring_structure":
        return {"label": "confirmed", "reasons": ["discovery=multi_config, confirmation independently reproduced structure"]}
    if discovery_verdict == "multi_config" and confirmation_verdict == "null_replicated":
        return {"label": "boundary", "reasons": ["discovery=multi_config, but confirmation did not reproduce it"]}
    if discovery_verdict == "multi_config":
        return {"label": "candidate", "reasons": [f"discovery=multi_config, confirmation_verdict={confirmation_verdict} (not yet tested or inconclusive)"]}
    return {"label": "unclassified", "reasons": [f"unrecognized discovery_verdict={discovery_verdict!r}"]}


def attractor_label_permitted(functional_recovery_summary: dict) -> dict:
    """Section 20's own rule: no "attractor" label without direct
    basin/perturbation/return evidence. Requires BOTH tracked
    dimensions (population, ecological) to show a majority-recovered
    rate -- a single favorable dimension is not sufficient, since an
    attractor claim is about the SYSTEM'S state, not one variable."""
    pop_rate = functional_recovery_summary.get("population_recovery_rate", float("nan"))
    eco_rate = functional_recovery_summary.get("ecological_recovery_rate", float("nan"))
    permitted = (pop_rate == pop_rate and pop_rate >= 0.5) and (eco_rate == eco_rate and eco_rate >= 0.5)
    return {
        "permitted": permitted, "population_recovery_rate": pop_rate, "ecological_recovery_rate": eco_rate,
        "rationale": (
            "both dimensions must show majority recovery for an attractor claim; "
            f"population={pop_rate}, ecological={eco_rate}"
        ),
    }


#: Below this member count, a diversity fraction is too noisy to
#: interpret directionally (a singleton cluster trivially has
#: diversity_fraction=1.0, which would otherwise misleadingly read as
#: "against environmental forcing").
MIN_MEMBERS_FOR_DIVERSITY_INTERPRETATION = 5


def _environmental_forcing_diversity(members: list[dict]) -> dict:
    n = len(members)
    if n == 0:
        return {"n_members": 0, "distinct_joint_points_fraction": float("nan"), "distinct_ic_families": 0, "distinct_strata": 0, "interpretation": "no_members"}
    distinct_points = len({m["joint_point_id"] for m in members})
    distinct_ic = len({m["ic_family"] for m in members})
    distinct_strata = len({m["expected_stratum"] for m in members})
    diversity_fraction = distinct_points / n
    if n < MIN_MEMBERS_FOR_DIVERSITY_INTERPRETATION:
        interpretation = "insufficient_members_for_interpretation"
    elif diversity_fraction >= ENVIRONMENTAL_FORCING_DIVERSITY_FLOOR:
        interpretation = "against_environmental_forcing"
    else:
        interpretation = "consistent_with_environmental_forcing"
    return {
        "n_members": n, "distinct_joint_points": distinct_points, "distinct_joint_points_fraction": diversity_fraction,
        "distinct_ic_families": distinct_ic, "distinct_strata": distinct_strata, "interpretation": interpretation,
    }


def run() -> dict:
    registry_verified = load_and_verify_confirmation_registry()
    registry = registry_verified["registry"]
    headline_k = registry["frozen_diagnostic_partition"]["k"]

    with open("outputs/level12b_stage_k_clustering_discovery/results.json") as f:
        wp_k = json.load(f)
    with open("outputs/level12b_stage_l3_prospective_confirmation/results.json") as f:
        wp_l = json.load(f)
    with open("outputs/level12b_stage_m_scaling_robustness/results.json") as f:
        wp_m = json.load(f)
    with open("outputs/level12b_stage_l2_discovery_pool_refit/results.json") as f:
        discovery_pool = json.load(f)
    wp_e = load_and_verify_design()
    stratum_by_point = {p["joint_point_id"]: p["expected_stratum"] for p in wp_e["design"]["points"]}

    records = discovery_pool["records"]
    for r in records:
        r["expected_stratum"] = stratum_by_point[r["joint_point_id"]]

    X_disc, feature_names = build_feature_matrix([r["vector_end"] for r in records], DIMENSION_KEYS)
    prep = preprocess_features(X_disc, X_disc, PRIMARY_MISSINGNESS_STRATEGY)
    fit = fit_candidate(prep["X_train"], "gmm", k=headline_k, rng_seed=RNG_SEED)
    labels = fit["labels"]

    collinearity = examine_collinearity(prep["X_train"], feature_names)
    pca = dimensionality_reduction_diagnostic(prep["X_train"], n_components=min(5, prep["X_train"].shape[1]))
    cum_var = np.cumsum(pca["explained_variance_ratio"]) if pca["explained_variance_ratio"] else []
    n_components_for_90pct = int(next((i + 1 for i, c in enumerate(cum_var) if c >= 0.9), len(cum_var))) if len(cum_var) else 0
    measurement_compression = {
        "pca_explained_variance_ratio": pca["explained_variance_ratio"],
        "n_components_for_90pct_variance": n_components_for_90pct,
        "n_raw_dimensions": len(feature_names),
        "interpretation": (
            "consistent_with_measurement_compression" if n_components_for_90pct <= max(1, len(feature_names) // 3)
            else "against_measurement_compression"
        ),
    }

    functional_recovery_summary = {
        "population_recovery_rate": sum(1 for r in wp_m["records"] if r["functional_recovery"]["population"]["recovered"]) / len(wp_m["records"]),
        "ecological_recovery_rate": sum(1 for r in wp_m["records"] if r["functional_recovery"]["ecological"]["recovered"]) / len(wp_m["records"]),
    }
    attractor = attractor_label_permitted(functional_recovery_summary)

    per_cluster = {}
    for c in range(headline_k):
        members = [r for r, lab in zip(records, labels) if lab == c]
        per_cluster[str(c)] = {
            "n_members": len(members),
            "environmentally_forced_similarity": _environmental_forcing_diversity(members),
        }

    failure_state_similarity = {
        "cluster_vs_failure_proxy_ari": wp_k["cluster_vs_failure_proxy_ari"],
        "interpretation": "consistent_with_failure_state_similarity" if wp_k["cluster_vs_failure_proxy_ari"] == wp_k["cluster_vs_failure_proxy_ari"] and wp_k["cluster_vs_failure_proxy_ari"] >= 0.5 else "against_failure_state_similarity",
    }
    temporary_similarity = {
        "temporal_window_stability_ari": wp_k["temporal_window_stability_ari"],
        "interpretation": "consistent_with_temporary_similarity" if wp_k["temporal_window_stability_ari"] == wp_k["temporal_window_stability_ari"] and wp_k["temporal_window_stability_ari"] < CONVERGENCE_PROXY_ARI_BAR else "against_temporary_similarity",
    }
    independent_structural_convergence_proxy = {
        "mean_algorithm_agreement_ari": wp_k["mean_algorithm_agreement_ari"],
        "bootstrap_mean_ari_in_pool": wp_k["bootstrap_stability"].get("mean_ari"),
        "assignment_stability_ari_out_of_sample": wp_l["assignment_stability_ari"],
        "interpretation": (
            "consistent_with_independent_convergence" if wp_l["assignment_stability_ari"] >= CONVERGENCE_PROXY_ARI_BAR
            else "weak_or_no_evidence_of_independent_convergence"
        ),
        "caveat": "a PROXY (do independent fits/algorithms agree) -- not a literal lineage-based permutation test; see module docstring's disclosed evidence gap",
    }
    shared_lineage_persistence = {
        "evaluated": False,
        "reason": "requires per-run rule_lineage_id data not persisted by any prior Work Package's saved output; a fourth full 576-run re-simulation was judged low-value given the already-established continuum/null-replication result -- disclosed scope reduction, see module docstring",
    }

    overall = classify_overall_recurrence_label(
        n_total=wp_k["n_total"], n_hard_minimum=40,
        discovery_verdict=wp_k["verdict"]["verdict"], confirmation_verdict=wp_l["confirmation_verdict"]["verdict"],
    )

    report = {
        "source_design_hash": registry["source_design_hash"],
        "preregistration_manifest_hash": registry["preregistration_manifest_hash"],
        "headline_k": headline_k,
        "cautious_vocabulary": list(CAUTIOUS_LABELS),
        "overall_classification": overall,
        "attractor_label_assigned": False,
        "attractor_label_evidence": attractor,
        "explanatory_categories_evaluated": list(EXPLANATORY_CATEGORIES),
        "shared_lineage_persistence": shared_lineage_persistence,
        "independent_structural_convergence_proxy": independent_structural_convergence_proxy,
        "temporary_similarity": temporary_similarity,
        "measurement_compression": measurement_compression,
        "failure_state_similarity": failure_state_similarity,
        "per_cluster_environmental_forcing": per_cluster,
        "collinearity_n_complete_rows": collinearity["n_complete_rows"],
    }
    return report


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    report = run()
    with open(f"{OUT_DIR}/results.json", "w") as f:
        json.dump(report, f, indent=2, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print(f"Work Package O: overall_classification={report['overall_classification']}")
    print(f"attractor_label_assigned={report['attractor_label_assigned']}")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
