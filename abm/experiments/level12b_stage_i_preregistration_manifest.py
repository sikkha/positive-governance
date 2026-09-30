#!/usr/bin/env python3
"""Level 1.2b, Work Package I (Section 14): the milestone-level
preregistration manifest.

Assembles every analysis-affecting decision this milestone's
experimental program uses into one frozen, versioned, SHA-256-hashed
document -- mirroring the exact freeze-then-hash pattern
``experiments/level12_preregistration.py`` (Level 1.2's own Stage 0)
already established, and the same pattern every 1.2b Work Package's own
design/spec has already used individually (WP C/D/E's ``design.json``+
hash, WP H's ``recurrence_spec.json``+hash). Section 14's own
contribution is not inventing new content -- it is COLLECTING what
Work Packages B through H already froze (imported live from each
module/script, never hand-copied, so this manifest cannot silently
drift from the code/artifacts it describes) plus freezing the two
pieces that do not yet have a home: the Section 17 confirmation-rule
commitments and the Section 18 scale-robustness grid, both BEFORE
their own Work Packages (I/J, tasks #70/#71) generate any outcome.

**"Every output stores the hash"**: any script for a still-pending
Work Package (confirmation, scaling robustness, discovery/clustering)
should import :data:`PREREGISTRATION_MANIFEST_HASH_PLACEHOLDER_NOTE`
-- no: should call :func:`load_and_verify_manifest` and include the
returned hash in its own saved report, exactly as this module recommends
below. Work Packages C through H's OWN already-frozen artifacts
(``design.json``/``recurrence_spec.json`` etc.) were generated and
hashed BEFORE this manifest existed, in each Work Package's own
already-established convention; this manifest does not retroactively
rewrite them (Section 20-style stop condition: a frozen artifact is
never edited after the fact merely to add a cross-reference) -- instead
every one of those artifacts' own hash is embedded HERE, in this
manifest, so the full provenance chain is still reconstructable from
this one document without altering any prior Work Package's output."""

from __future__ import annotations

import hashlib
import json
import os

from abm_governance.observer.phenotype_discovery import (
    CANDIDATE_METHODS,
    DEFAULT_K_RANGE,
    MISSINGNESS_STRATEGIES,
)
from abm_governance.observer.recurrence_criteria_audit import SIMILARITY_LEVEL_TAXONOMY
from experiments.level12b_stage_c_feasibility_map import PARAMETER_SPACE as ECOLOGICAL_PARAMETER_SPACE
from experiments.level12b_stage_d_institutional_design import PARAMETER_SPACE as INSTITUTIONAL_PARAMETER_SPACE
from experiments.level12b_stage_e_joint_discovery import (
    IC_FAMILIES,
    N_IC_FAMILIES,
    N_JOINT_POINTS_HARD_MINIMUM,
    N_JOINT_POINTS_PREFERRED,
    N_PATCHES,
    N_STEPS,
    POPULATION_SIZE,
    SEEDS_PER_POINT_HARD_MINIMUM,
    SEEDS_PER_POINT_PREFERRED,
)
from experiments.level12b_stage_e_joint_discovery import load_and_verify_design as _load_wp_e_design
from experiments.level12b_stage_g_temporal_representation import BURN_IN_SENSITIVITY_DEFINITIONS
from experiments.level12b_stage_h_recurrence_spec import load_and_verify_recurrence_spec as _load_wp_h_spec

OUT_DIR = "outputs/level12b_stage_i_preregistration_manifest"

MANIFEST_VERSION = "level1.2b-preregistration-manifest-v1"

#: Section 17's own preferred/hard-minimum arithmetic (task #70's own
#: description) -- frozen HERE, before Work Package J (task #70)
#: generates any confirmation outcome. The fuller candidate-specific
#: registry (candidate defs/preprocessing/assignment rules/uncertainty
#: ranges/expected directions) is necessarily built later, once Section
#: 16's discovery/clustering (task #69) has actually produced candidates
#: to confirm -- this entry freezes everything that does NOT depend on
#: which candidates discovery finds: the run arithmetic, the disjoint-
#: seed policy, and the fixed battery of tests every candidate (or the
#: null result) will be run through.
CONFIRMATION_RULES: dict = {
    "preferred": {"n_joint_points": 24, "seeds_per_point": 8, "n_ic_families": 2, "total_runs": 384},
    "hard_minimum": {"n_joint_points": 18, "seeds_per_point": 6, "n_ic_families": 2, "total_runs": 216},
    "seed_disjointness_rule": "every confirmation seed must be disjoint from every Work Package E discovery seed -- fresh seeds only, never reused",
    "tests_applied_to_every_candidate": [
        "recurrence_across_seeds_points_and_initial_condition_families",
        "assignment_stability",
        "feature_profile_stability",
        "held_out_predictiveness",
        "unclassified_outcome_rate",
        "failure_transition_rate",
    ],
    "null_replication_rule": "if Section 16 discovery supports no candidates, confirmation replicates the null result rather than manufacturing a candidate to test",
}

#: Section 18's own grid (task #71's own description) -- frozen HERE,
#: before Work Package K (task #71) runs.
SCALE_ROBUSTNESS_GRID: dict = {
    "population_sizes": 2,
    "patch_counts": 2,
    "network_modularity_levels": 2,
    "seeds": 4,
    "runs_per_candidate_or_null_baseline": 32,  # 2 x 2 x 2 x 4
    "measured": [
        "ecological_state", "phenotype_assignment", "administrative_workload", "scale",
        "migration", "fragmentation", "functional_recovery", "transition_to_failure",
    ],
    "scale_invariance_required": False,
    "note": "Section 18 explicitly does not require scale invariance -- a candidate whose behavior changes with scale is a reported finding, not a disqualification",
}

#: 1.2b-specific stop conditions -- distinct from (and does not
#: supersede) Level 1.2's own Section 20 stop conditions, which govern
#: that separate milestone's own stages.
STOP_CONDITIONS: tuple[str, ...] = (
    "a frozen design/spec/manifest is never edited after its own hash was computed; every stage script that "
    "consumes one calls that artifact's own load_and_verify_* function, which raises rather than warns on mismatch",
    "Section 5.7's ledger-closure gate: no feasibility mapping or discovery proceeds on any run whose ecological "
    "ledger residual is not within documented floating-point tolerance",
    "a Work Package's hard-minimum sample size is a floor, not a target -- a run count below hard minimum is a "
    "hard stop for that Work Package's own completion claim, never silently accepted as 'close enough'",
    "clustering results (Section 9.3/16) never determine burn-in fraction, missingness strategy, or feature "
    "selection after the fact -- those are fixed before any candidate cluster is examined",
    "no generative object anywhere in 1.2b code is named after governance-phenotype/trajectory/SEM-adjacent "
    "terms (the SEM firewall, extended to every new module this milestone adds)",
    "a disclosed scope reduction (e.g. Work Package G's 12-seed-run pipeline validation subset) is recorded in "
    "the reducing script's own output at the time of the reduction, never adjusted afterward to match results",
)

#: Disclosed compute-budget decisions already made this milestone, plus
#: the standing policy for decisions not yet made.
COMPUTE_BUDGET_DECISIONS: dict = {
    "work_package_e_joint_discovery": "ran the full PREFERRED design (576 runs), no reduction required",
    "work_package_g_temporal_representation": (
        "validated the full Section 12 feature pipeline on a disclosed 12-seed-run subset of Work Package E's "
        "own frozen design (3 points x 2 seeds x 2 IC families), rather than collecting per-step phenotype "
        "snapshots for the full 576-run pool -- recorded in that script's own report['scope'] field, not "
        "left implicit; see dev_mem/status_update.md's Work Package G entry for the full disclosure"
    ),
    "standing_policy": (
        "every future Work Package states its own scope decision (preferred vs. hard-minimum vs. a further "
        "disclosed reduction) in its own script/report at the time it runs, matched against this manifest's "
        "already-frozen preferred/hard-minimum arithmetic -- a reduction below hard minimum is a stop condition "
        "(see STOP_CONDITIONS), not a silent adjustment"
    ),
}


def _feasibility_ratio_definitions() -> dict:
    """Named, not re-derived -- Work Package B's own functions are the
    single source of truth for these formulas; this manifest records
    only their names/roles, reusing ``feasibility_ratios.py``'s own
    docstrings as the source of meaning rather than restating the math
    here where it could drift out of sync."""
    from abm_governance.observer import feasibility_ratios as fr

    def _first_paragraph(func) -> str:
        doc = " ".join(line.strip() for line in func.__doc__.strip().split("\n"))
        return doc.split("  - ")[0].split(". - ")[0].strip()

    return {
        "structural_feasibility_ratio": _first_paragraph(fr.structural_feasibility_ratio),
        "expected_pressure_ratio": _first_paragraph(fr.expected_pressure_ratio),
        "monte_carlo_expected_h_m": _first_paragraph(fr.monte_carlo_expected_h_m),
    }


def build_manifest() -> dict:
    """Assembles the full frozen manifest by importing live from every
    Work Package B-H module/script -- deterministic given the codebase
    state and the two already-frozen-on-disk artifacts (Work Package
    E's design, Work Package H's recurrence spec) this function reads."""
    from abm_governance.observer.phenotype_feature_audit import PHENOTYPE_FEATURE_AUDIT

    wp_e = _load_wp_e_design()
    wp_h = _load_wp_h_spec()

    return {
        "milestone": "level1.2b_ecological_feasibility_envelope_and_powered_blind_institutional_phenotype_rediscovery",
        "version": MANIFEST_VERSION,
        "feasibility_ratio_definitions": _feasibility_ratio_definitions(),
        "ecological_bounds": {
            "parameter_space": [list(t) for t in ECOLOGICAL_PARAMETER_SPACE],
            "population_size": POPULATION_SIZE,
            "n_patches": N_PATCHES,
        },
        "ecological_strata": {
            "cut_points": wp_e["design"]["stratum_cut_points"],
            "stratum_counts": wp_e["design"]["stratum_counts"],
            "source_design_hash": wp_e["hash"],
        },
        "institutional_bounds": {"parameter_space": [list(t) for t in INSTITUTIONAL_PARAMETER_SPACE]},
        "initial_condition_families": list(IC_FAMILIES),
        "run_arithmetic": {
            "preferred": {
                "n_joint_points": N_JOINT_POINTS_PREFERRED, "seeds_per_point": SEEDS_PER_POINT_PREFERRED,
                "n_ic_families": N_IC_FAMILIES, "n_steps": N_STEPS,
                "total_runs": N_JOINT_POINTS_PREFERRED * SEEDS_PER_POINT_PREFERRED * N_IC_FAMILIES,
            },
            "hard_minimum": {
                "n_joint_points": N_JOINT_POINTS_HARD_MINIMUM, "seeds_per_point": SEEDS_PER_POINT_HARD_MINIMUM,
                "n_ic_families": N_IC_FAMILIES, "n_steps": N_STEPS,
                "total_runs": N_JOINT_POINTS_HARD_MINIMUM * SEEDS_PER_POINT_HARD_MINIMUM * N_IC_FAMILIES,
            },
        },
        "burn_in_windows": BURN_IN_SENSITIVITY_DEFINITIONS,
        "feature_dictionary": PHENOTYPE_FEATURE_AUDIT,
        "missing_data_rules": {
            "structural_nan_discipline": "every phenotype dimension preserves NaN for a genuine zero-denominator absence -- never zero-filled (see feature_dictionary's own structural_missingness field per dimension)",
            "seed_run_level_missingness_strategies": list(MISSINGNESS_STRATEGIES),
            "strategy_fitting_rule": "every strategy is fit-on-train-only, never leaking test-fold statistics into imputation",
        },
        "recurrence_criteria": {
            "spec_version": wp_h["spec"]["version"],
            "source_spec_hash": wp_h["hash"],
            "criteria_names": wp_h["spec"]["source_criteria_names"],
            "default_thresholds": wp_h["spec"]["default_thresholds"],
            "similarity_level_taxonomy": SIMILARITY_LEVEL_TAXONOMY,
        },
        "clustering_commitments": {
            "candidate_methods": list(CANDIDATE_METHODS),
            "k_range": list(DEFAULT_K_RANGE),
            "k_selection_rule": "k=1 is always a valid null; no k is privileged (never fixed toward any particular cluster count)",
            "standardization_rule": "training-only standardization -- no test-fold statistic ever informs a fitted scaler",
            "model_selection_metrics": ["bic", "aic", "silhouette", "davies_bouldin", "calinski_harabasz", "cluster_size_balance"],
            "model_selection_rule": "no single metric decides -- every metric is computed and reported side by side",
            "candidate_independence_rule": "candidate clusters from the same fit are not independent statistical tests",
        },
        "confirmation_rules": CONFIRMATION_RULES,
        "scale_robustness_grid": SCALE_ROBUSTNESS_GRID,
        "stop_conditions": list(STOP_CONDITIONS),
        "compute_budget_decisions": COMPUTE_BUDGET_DECISIONS,
        "firewall": "no SEM/dissertation data, labels, or trajectory counts are read anywhere in this milestone's generative, observer, or experimental code (Section 3/21)",
    }


def manifest_hash(manifest: dict) -> str:
    """Deterministic SHA-256 over the manifest's canonical (sorted-key)
    JSON serialization -- key order in the source dict never affects
    the hash, only content does."""
    payload = json.dumps(manifest, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_manifest(out_dir: str = OUT_DIR) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    manifest = build_manifest()
    digest = manifest_hash(manifest)
    with open(f"{out_dir}/manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True, default=str)
    with open(f"{out_dir}/manifest_hash.txt", "w") as f:
        f.write(digest + "\n")
    return {"manifest": manifest, "hash": digest}


def load_and_verify_manifest(out_dir: str = OUT_DIR) -> dict:
    """Every subsequent Work Package (discovery/clustering, confirmation,
    scaling robustness) should call this -- not :func:`build_manifest`
    directly -- and store the returned hash in its own saved report, per
    Section 14's "every output stores the hash" requirement."""
    with open(f"{out_dir}/manifest.json") as f:
        manifest = json.load(f)
    with open(f"{out_dir}/manifest_hash.txt") as f:
        stored_hash = f.read().strip()
    recomputed = manifest_hash(manifest)
    if recomputed != stored_hash:
        raise ValueError(
            f"Level 1.2b preregistration manifest at {out_dir}/manifest.json has been altered since it was "
            f"frozen (stored hash {stored_hash}, recomputed hash {recomputed})."
        )
    return {"manifest": manifest, "hash": recomputed}


def main() -> None:
    result = write_manifest()
    print(f"Level 1.2b preregistration manifest version {result['manifest']['version']} frozen at {OUT_DIR}/manifest.json")
    print(f"hash: {result['hash']}")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
