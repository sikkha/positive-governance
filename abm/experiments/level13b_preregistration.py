#!/usr/bin/env python3
"""Level 1.3b, task #114 (Section 16): the milestone-level
preregistration manifest.

Mirrors ``experiments/level13_preregistration.py``'s exact freeze-then-
hash pattern (``build_manifest``/``manifest_hash``/``write_manifest``/
``load_and_verify_manifest``) -- every analysis-affecting decision Level
1.3b's Stage 0-10 program will use is collected here, imported live from
the modules that already implement a piece of it wherever one exists,
and frozen with a SHA-256 hash BEFORE any Stage 3+ run executes (Stage 0
and Work Packages A-C, tasks #110-113, are audit/diagnostic/calibration
work that necessarily precedes and informs this freeze, exactly as
Level 1.3's own Stage 1-2 preceded ITS preregistration).

**Context-loss disclosure.** This session's working context carries
Level 1.3b's own governing specification only via a compacted summary
of an earlier turn (the verbatim Section 18/19 wording is not
recoverable here) -- the same disclosed situation this project has
handled before (`observer/sequencing_diagnostics.py`, `experiments/
level13_preregistration.py`). :data:`HYPOTHESES` and :data:`DECISION_
GATE_OUTCOMES` below are reconstructed from that summary at the level
of outline/content it preserved, not a verbatim transcription -- stated
here, before any Stage 3+ run, precisely so they cannot be quietly
reworded later to fit whatever a run turns up, and so a future session
auditing this file knows exactly what confidence to place in its wording
vs. its substance.

**Disclosed scope reductions**, all decided BEFORE the corresponding
stage runs, per Section 21: every sample size in :data:`STAGE_SAMPLE_
SIZES` below is scaled to this session's compute budget (2 CPUs), not to
any publication target."""

from __future__ import annotations

import hashlib
import json
import os

from abm_governance.core.rng import RNG_REGISTRY_VERSION
from experiments.level13_stage2_calibration import OUT_DIR as LEVEL13_STAGE2_OUT_DIR  # noqa: F401 (documents provenance)

OUT_DIR = "outputs/level13b_preregistration"

#: Section 6/7 Work Package B/C findings, frozen here as the calibration
#: this milestone's Stage 3+ runs will actually use -- see
#: `docs/level1.3b_bargaining_activation_audit.md` and `outputs/
#: level13b_stage2_bargaining_calibration/calibration_report.json` for
#: the full evidentiary basis. The headline result: NO generative
#: parameter change was needed -- the Work Package B construction fix
#: alone is sufficient to put `bargaining_participation` activation at
#: exactly 0.5 in all three ecological strata, at the untouched Level
#: 1.1/1.2b defaults.
BARGAINING_CALIBRATION: dict = {
    "contribution_amount": 0.2,          # Level 1.1 default, unchanged -- swept 0.02-0.2, no measurable effect
    "contribution_period_steps": 10,     # Level 1.1 default, unchanged
    "sequencing_min_duration_steps": 10,  # unchanged from every Level 1.3 stage script
    "activation_fraction_at_defaults": {"low_feasibility": 0.5, "medium_feasibility": 0.5, "high_feasibility": 0.5},
    "evidence_source": "outputs/level13b_stage2_bargaining_calibration/calibration_report.json",
    "audit_source": "docs/level1.3b_bargaining_activation_audit.md",
    "note": (
        "response_cost had zero measurable effect in [0.02, 0.2] (resources are already too deeply "
        "negative post-collapse for the ask size to matter); activation is driven by the interaction "
        "of contribution_period_steps and sequencing_min_duration_steps, not by response cost -- a "
        "disclosed null result on one of Section 7's licensed levers, not hidden."
    ),
}

#: Section 3-reused: one representative ecological point per stratum,
#: from Level 1.3's own frozen Stage 2 design -- see `experiments/
#: level13b_stage2_bargaining_calibration.py`'s own docstring.
ECOLOGICAL_STRATA_POINT_IDS: dict[str, int] = {
    "low_feasibility": 0, "medium_feasibility": 2, "high_feasibility": 1,
}
ECOLOGICAL_DESIGN_SOURCE = "outputs/level13_stage2_calibration/design.json"

#: Section 9/WP E, Stage 3: purpose-designed matched factorial, INDEPENDENT
#: of the Stage 4 discovery pool (never reused runs). Named orderings are
#: qualitative labels for which pressure channel(s) lead, not all 3! = 6
#: permutations (Level 1.3's own Stage 3 already covered full
#: permutations; this milestone's own Stage 3 instead crosses a smaller,
#: named ordering set against entrenchment/legitimacy/ecology, per
#: Section 9's own narrower factor list).
STAGE3_MATCHED_FACTORIAL: dict = {
    "factors": {
        "pressure_ordering": {
            "security_first": {"security_pressure": 0, "bargaining_pressure": 150, "coordination_complexity": 300},
            "bargaining_first": {"bargaining_pressure": 0, "security_pressure": 150, "coordination_complexity": 300},
            "coevolution": {"security_pressure": 0, "bargaining_pressure": 0, "coordination_complexity": 0},
        },
        "entrenchment": {
            "off": {"entrenchment_enabled": False},
            "moderate": {"entrenchment_enabled": True, "entrenchment_maturation_steps": 150},
            "strong": {"entrenchment_enabled": True, "entrenchment_maturation_steps": 50},
        },
        "legitimacy": {
            "neither": {"performance_legitimacy_enabled": False, "procedural_legitimacy_enabled": False},
            "performance_only": {"performance_legitimacy_enabled": True, "procedural_legitimacy_enabled": False},
            "procedural_only": {"performance_legitimacy_enabled": False, "procedural_legitimacy_enabled": True},
            "dual": {"performance_legitimacy_enabled": True, "procedural_legitimacy_enabled": True},
        },
        "ecological_stratum": list(ECOLOGICAL_STRATA_POINT_IDS.keys()),
    },
    "n_cells": 3 * 3 * 4 * 3,
    "n_seeds_per_cell": 2,
    "n_runs_declared": 3 * 3 * 4 * 3 * 2,
    "matched_cumulative_pressure_exposure": (
        "every cell shares the SAME total pressure-onset budget (onsets in {0,150,300} used exactly "
        "once each across the three channels for security_first/bargaining_first; coevolution uses "
        "onset 0 for all three, by construction an equal, not merely float-tolerant-equal, exposure "
        "case) -- required contrasts computed only WITHIN matched entrenchment/legitimacy/stratum cells "
        "across the three orderings, never pooled across cells that differ on those factors"
    ),
    "primary_outcomes": [
        "bargaining_participation_sustained_crossing_step", "S_obs", "Z_obs",
        "realized_compliance_rate", "mean_resources_final_third",
        "n_active_rules_final_step", "entrenchment_index_final_step",
        "cross_founder_reconstruction_count",
    ],
    "uncertainty_method": "seed-clustered bootstrap CIs (resample whole seeds, not individual runs, within each matched cell) -- raw matched differences reported alongside, never pooled means alone",
    "population_size": 40, "n_patches": 3, "n_steps": 500, "seed_base": 8_300_000,
}

#: Section 8/WP D, Stage 4: ONE homogeneous, purpose-designed,
#: space-filling discovery design -- disclosed reduced scale (minimum
#: declared by Section 8 itself: 48 points x 5 seeds = 240 runs).
STAGE4_HOMOGENEOUS_DISCOVERY: dict = {
    "design_type": "latin_hypercube_space_filling_single_design",
    "dimensions": [
        "security_pressure_onset_step", "bargaining_pressure_onset_step", "coordination_complexity_onset_step",
        "pressure_magnitude_high_level", "pressure_duration_steps",
        "pressure_overlap_fraction", "pressure_volatility_shock_interval",
        "entrenchment_strength_maturation_steps",
        "performance_legitimacy_sensitivity", "procedural_legitimacy_sensitivity",
        "ecological_feasibility_stratum",
    ],
    "n_points": 48,
    "n_seeds_per_point": 5,
    "n_runs_declared": 48 * 5,
    "scale_disclosed_as": "Section 8's own stated MINIMUM (48 points x 5 seeds = 240 runs), not the preferred 72-96 x 6-8 -- disclosed here, before running, per this milestone's own session-budget-scaling discipline",
    "identical_across_every_point": [
        "run_length_n_steps=500", "population_size=40", "n_patches=4",
        "init_conditions", "observer_window_definition", "eligibility_rule",
        "phenotype_construction", "missingness_treatment",
    ],
    "no_counterfactual_reruns_in_pool": True,
    "counterfactual_dataset_is_separate": "stage6_history_erasure_validation (task #119)",
    "lhs_seed": 20260821001,
    "resumable_manifest": True,
    "multiprocessing": True,
}

#: Section 10/WP F, Stage 5: temporal-persistence diagnostics.
STAGE5_TEMPORAL_PERSISTENCE: dict = {
    "windows_as_fraction_of_run_length": {
        "early": [0.0, 0.2], "middle": [0.4, 0.6], "late": [0.8, 1.0], "final_sustained": [0.9, 1.0],
    },
    "diagnostics_required": [
        "early_to_middle_displacement", "middle_to_late_displacement",
        "late_window_variance", "convergence_divergence_slope",
        "cluster_assignment_stability_across_windows", "trajectory_distance",
        "persistence_after_pressure_removal", "persistence_after_pressure_reversal",
        "persistence_after_pressure_equalization",
    ],
    "classification_categories": [
        "pressure_dependent_response", "historical_hysteresis",
        "entrenched_path_dependence", "transient_differentiation", "no_detectable_differentiation",
    ],
    "module": "observer/historical_persistence.py (to be created, task #118)",
    "rule": "never classify from final-step values alone -- every category above requires the windowed trajectory, not a single snapshot",
}

#: Section 11/WP G, Stage 6: history-erasure validation -- six matched
#: interventions, including a sham to prove serialization/copy machinery
#: alone does not alter a run.
STAGE6_HISTORY_ERASURE: dict = {
    "interventions": [
        "pressure_memory_only", "legitimacy_history_only", "entrenchment_only",
        "all_history", "sham_identical_state_copy", "no_intervention_control",
    ],
    "sham_purpose": "prove the serialization/copy machinery itself is a byte-identical no-op before trusting any of the other five interventions' divergence as historically meaningful",
    "preserves": ["current_visible_structure", "current_resources", "current_ecology", "current_network"],
    "measures": ["trajectory_divergence_across_all_windows", "not_final_S_obs_Z_obs_alone"],
    "n_seeds": 12,
    "n_runs_declared": 6 * 12,
}

#: Section 12/WP H, Stage 7: discrete vs. continuous vs. path-dependent
#: discovery-model comparison.
STAGE7_MODEL_COMPARISON: dict = {
    "discrete_candidates": ["gmm_k1_to_8", "hierarchical", "hdbscan_multiple_min_cluster_size", "unequal_covariance_mixtures"],
    "continuous_candidates": ["pca_factor_continuum", "principal_curve_manifold", "low_dim_regression"],
    "path_dependent_candidates": ["predict_late_phenotype_from_early_sequence_no_discrete_clustering"],
    "comparison_metrics": [
        "held_out_likelihood", "reconstruction_error", "predictive_performance",
        "bootstrap_stability", "cross_algorithm_stability", "cross_point_stability",
        "cross_seed_stability", "temporal_window_stability", "ecological_stratum_stability",
        "missingness_strategy_stability",
    ],
    "rule": "no k chosen from silhouette alone; no preferred k; a discrete result must beat every continuous alternative on FRESH (Stage 8) data to count as discrete",
}

#: Section 13/WP I, Stage 8: substantially larger DISJOINT fresh
#: confirmation -- disclosed reduced scale (Section 13's own stated
#: minimum: 24 points x 4 seeds = 96 runs).
STAGE8_FRESH_CONFIRMATION: dict = {
    "n_points": 24, "n_seeds_per_point": 4, "n_runs_declared": 96,
    "scale_disclosed_as": "Section 13's own stated MINIMUM (24 x 4 = 96), not the preferred 36-48 x 4-6",
    "disjoint_design_seed": True, "disjoint_sim_seed": True,
    "frozen_before_scoring": [
        "preprocessing", "phenotype_fields", "observer_thresholds",
        "clustering_or_manifold_model_from_stage7",
    ],
    "no_refitting_before_primary_scoring": True,
    "no_post_hoc_parameter_selection": True,
}

#: Section 14/WP J, Stage 9: S_obs/Z_obs measurement audit.
STAGE9_MEASUREMENT_AUDIT: dict = {
    "candidate_explanations": [
        "genuine_coupling", "shared_construction", "common_ecological_driver",
        "common_normalization", "activity_volume_confounding", "presence_absence_confounding",
        "measurement_overlap",
    ],
    "calculations_required": [
        "raw_correlation", "partial_correlation_controlling_ecological_stratum",
        "within_point_correlation", "between_point_correlation",
        "factor_structure_analysis", "equal_weight_variant", "leave_one_out_variant",
        "non_normalized_variant", "opportunity_denominated_variant",
    ],
    "rule": "do not redefine S_obs/Z_obs to manufacture independence; if measurement-induced, correct transparently, version it, preserve both the original and corrected variant",
}

#: Section 15/WP K: Level 1.2b ecological-accounting/feasibility
#: machinery, continued unmodified.
WORK_PACKAGE_K_ACCOUNTING: dict = {
    "reused_from": "level1.2b (observer/feasibility_ratios.py, ecological ledger fields) -- no new machinery this milestone",
    "every_run_reports": ["full_outcome_ledger", "collapse_runs_retained_not_discarded"],
    "denominators_distinguished": [
        "complete_outcome_ledger", "institutionally_eligible_analysis_denominator",
    ],
    "reporting_required": ["pooled", "by_stratum", "eligible_only", "collapse_as_outcome"],
}

#: Section 18: 8 primary hypotheses -- reconstructed from this session's
#: own compacted summary of the outline (bargaining activation, ordering,
#: persistence, entrenchment, history, legitimacy, replication,
#: discreteness), stated here as full, falsifiable, disclosed-as-
#: reconstructed hypotheses. H8 is explicitly allowed to fail even if
#: H1-H7 all hold.
HYPOTHESES: dict[str, str] = {
    "H1_bargaining_activation": "bargaining_participation activates (a sustained crossing is registered) in a nondegenerate share of eligible runs once the Work Package B construction fix is applied, without further generative calibration",
    "H2_ordering_effect": "the temporal ORDER in which pressure channels activate produces measurable, reproducible variation in institutional response (S_obs, Z_obs, and/or the sequencing vector), holding total pressure exposure matched",
    "H3_temporal_persistence": "differentiation observed mid-run persists (does not fully reconverge) through the final-sustained window, distinguishing genuine path dependence from transient response",
    "H4_entrenchment_moderation": "entrenchment strength (off/moderate/strong) moderates how much differentiation persists once established -- stronger entrenchment predicts less late-run reconvergence",
    "H5_history_matters_causally": "erasing or reversing pressure history (Stage 6, matched interventions, sham-controlled) produces trajectory divergence beyond what the sham (identical-state-copy) intervention alone produces",
    "H6_legitimacy_channel_effect": "performance and/or procedural legitimacy channels measurably affect S_obs/Z_obs and/or persistence, independent of entrenchment",
    "H7_fresh_replication": "whatever structure (discrete, continuous, or path-dependent) Stage 4's discovery finds, generalizes to Stage 8's disjoint fresh confirmation at better than Level 1.3's own -1.29-vs--6.05 generalization gap",
    "H8_discreteness": "the discovered structure is genuinely discrete (beats every continuous alternative on fresh data per Stage 7's rule) -- explicitly allowed to fail even if H1-H7 all hold, since Level 1.3's own evidence already leans continuum",
}

#: Section 19: 8-way decision gate -- reconstructed from this session's
#: own compacted summary (verbatim Section 19 wording not recoverable
#: after context compaction), disclosed as reconstructed rather than
#: transcribed, exactly as this module's own docstring states.
DECISION_GATE_OUTCOMES: dict[str, str] = {
    "A_no_effect": "no reproducible historical/sequencing effect detected at all",
    "B_pressure_responsive_nonhistorical": "institutions respond to pressure MAGNITUDE but not to its temporal ORDER or history -- current-state-dependent, not path-dependent",
    "C_transient": "differentiation appears but does not persist -- families/gradient reconverge given enough steps (Stage 5's own diagnostic)",
    "D_persistent_continuum": "persistent path dependence on a CONTINUOUS gradient, not separable discrete families",
    "E_two_families": "persistent path dependence into exactly two reproducible discrete families",
    "F_three_families": "persistent path dependence into exactly three reproducible discrete families",
    "G_four_or_more_families": "persistent path dependence into four or more reproducible discrete families",
    "H_inconclusive": "evidence does not clearly support any of A-G (e.g. contradictory stage results, failed frozen-compatibility, disqualifying generalization gap with no clear discrete-vs-continuum resolution)",
}
DECISION_GATE_DO_NOT_PREFER: str = "F_three_families"
DECISION_GATE_NOTE: str = (
    "\"do not prefer F\" (the number three) governs the DISCOVERY PIPELINE'S OWN DEFAULT, exactly as "
    "Level 1.3's own DECISION_GATE_NOTE governed E there -- no Stage 3-10 script may special-case or "
    "bias toward three discrete families; every outcome, F included, remains legitimate if the data "
    "support it. Family-to-dissertation-trajectory mapping is explicitly deferred until AFTER blind "
    "discovery (Stage 4), fresh confirmation (Stage 8), and the S_obs-Z_obs audit (Stage 9) are all "
    "frozen, per this milestone's own Section 19 requirement."
)

#: Section 3/4 RNG discipline, restated as a frozen commitment,
#: continuing Level 1.3's own mechanism-substream architecture.
RNG_COMMITMENTS: dict = {
    "rng_mode": "mechanism_substreams",
    "rng_registry_version": RNG_REGISTRY_VERSION,
    "note": "mandatory for every Stage 0/3-10 run this milestone; every new stochastic operation gets its own registered deterministic substream",
}

#: Section 4: two frozen reference points every Stage 0+ compatibility
#: check compares against.
FROZEN_REFERENCES: dict = {
    "level12b_historical_off": "SimulationConfig.level12b_frozen_reference() with every Level 1.3 historical_module_enabled=False (byte-identical to Level 1.2b)",
    "corrected_level13": "SimulationConfig.level12b_frozen_reference() + Level 1.3's own corrected (post-task-#109-fix) transmission wiring, historical_module_enabled=True",
}

#: Section 25 stopping rule, restated as a frozen commitment.
STOPPING_RULE: dict = {
    "do_not_begin_level_1_4": True,
    "do_not_modify_paper_repository": True,
    "do_not_silently_promote_level13_continuum_verdict": True,
    "final_report_must_state": [
        "bargaining_repair_status", "sequence_effect_significance", "equalization_survival",
        "entrenchment_moderation", "erasure_reduction", "discrete_vs_continuous_generalization",
        "fresh_confirmation_support", "s_obs_z_obs_coupling_nature", "exact_decision_gate_outcome",
        "nulls", "anomalies", "limitations", "exact_test_and_run_counts", "next_recommended_decision",
    ],
    "succeeds_even_on": ["null_finding", "transient_finding", "nonreplicating_finding", "continuous_finding", "inconclusive_finding"],
}


def build_manifest() -> dict:
    """Assembles the full frozen manifest. Deterministic given the
    imported/literal constants above."""
    return {
        "milestone": "level1.3b_validation_of_historical_path_dependence",
        "bargaining_calibration": BARGAINING_CALIBRATION,
        "ecological_strata_point_ids": ECOLOGICAL_STRATA_POINT_IDS,
        "ecological_design_source": ECOLOGICAL_DESIGN_SOURCE,
        "stage3_matched_factorial": STAGE3_MATCHED_FACTORIAL,
        "stage4_homogeneous_discovery": STAGE4_HOMOGENEOUS_DISCOVERY,
        "stage5_temporal_persistence": STAGE5_TEMPORAL_PERSISTENCE,
        "stage6_history_erasure": STAGE6_HISTORY_ERASURE,
        "stage7_model_comparison": STAGE7_MODEL_COMPARISON,
        "stage8_fresh_confirmation": STAGE8_FRESH_CONFIRMATION,
        "stage9_measurement_audit": STAGE9_MEASUREMENT_AUDIT,
        "work_package_k_accounting": WORK_PACKAGE_K_ACCOUNTING,
        "hypotheses": HYPOTHESES,
        "decision_gate_outcomes": DECISION_GATE_OUTCOMES,
        "decision_gate_do_not_prefer": DECISION_GATE_DO_NOT_PREFER,
        "decision_gate_note": DECISION_GATE_NOTE,
        "rng_commitments": RNG_COMMITMENTS,
        "frozen_references": FROZEN_REFERENCES,
        "stopping_rule": STOPPING_RULE,
        "firewall": "no SEM/dissertation data, labels, trajectory names, or country names read anywhere in Stage 0/3-10 (Section 3)",
    }


def manifest_hash(manifest: dict) -> str:
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
    with open(f"{out_dir}/manifest.json") as f:
        manifest = json.load(f)
    with open(f"{out_dir}/manifest_hash.txt") as f:
        stored_hash = f.read().strip()
    recomputed = manifest_hash(manifest)
    if recomputed != stored_hash:
        raise ValueError(
            f"Level 1.3b preregistration manifest at {out_dir}/manifest.json has been altered since "
            f"it was frozen (stored hash {stored_hash}, recomputed hash {recomputed})."
        )
    return {"manifest": manifest, "hash": recomputed}


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    result = write_manifest()
    print(f"Level 1.3b preregistration manifest frozen at {OUT_DIR}/manifest.json")
    print(f"hash: {result['hash']}")
