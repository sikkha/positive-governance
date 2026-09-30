#!/usr/bin/env python3
"""Level 1.3b visualizations (Section 21/23, task #125).

Reads the already-committed JSON outputs of every Level 1.3b stage
(``outputs/level13b_stage*/*.json``, ``outputs/level13b_bargaining_
activation_audit/stage1_diagnostic.json``, ``outputs/level13b_test_
requirements_audit/results.json``) -- does not re-run any of them,
mirroring Level 1.3's own ``make_level13_visualizations.py`` precedent
exactly.

No chart title or axis label uses any forbidden vocabulary
(``tests/test_level13_sem_firewall_extension.py``'s ``FORBIDDEN_
LEVEL13_TERMS``, reused unmodified by Level 1.3b -- mechanically
confirmed absent from this script's own source, see this module's own
disclosure below on why the experiment-script terminology guard's own
glob does not reach visualization scripts by name) -- every label is drawn
from this milestone's own observer-side vocabulary (S_obs/Z_obs,
``low_feasibility``/``medium_feasibility``/``high_feasibility``,
entrenchment/legitimacy/conversion_incidence dimension names) or plain
descriptive terms (seed, population, cell, window). No figure treats
any k, any ordering, or any channel as a privileged/preferred choice --
every k in a fitted range and every named condition is plotted
identically wherever shown.

**Disclosed scope**: 16 of Section 21/23's suggested ~12-16 figures,
covering every Level 1.3b Work Package and every Stage 0-10 script.
Findings are plotted as recorded, without rendering any decision-gate
verdict of their own -- that synthesis is task #126's own job.

**Disclosed, pre-existing gap in the terminology guard's own reach,
not introduced here**: ``tests/test_level13b_sem_firewall_extension.
py``'s glob (``level13b_*.py``) matches only files whose name STARTS
with that prefix -- ``make_level13b_visualizations.py`` does not match
(exactly as Level 1.3's own ``make_level13_visualizations.py`` was
never matched by its own milestone's equivalent glob either; this is
an existing project-wide convention gap, not a Level 1.3b-specific
oversight). Checked manually instead, mechanically, before this
docstring was written: `FORBIDDEN_LEVEL13_TERMS` against this file's
own stripped source returns zero offenders."""

from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT_DIR = "outputs/level13b_figures"

PATHS = {
    "stage0": "outputs/level13b_stage0_frozen_compatibility/stage0_report.json",
    "stage1": "outputs/level13b_bargaining_activation_audit/stage1_diagnostic.json",
    "stage2": "outputs/level13b_stage2_bargaining_calibration/calibration_report.json",
    "stage3": "outputs/level13b_stage3_matched_sequencing_factorial/stage3_report.json",
    "stage4": "outputs/level13b_stage4_homogeneous_discovery/stage4_report.json",
    "stage4_records": "outputs/level13b_stage4_homogeneous_discovery/records.json",
    "stage5": "outputs/level13b_stage5_temporal_persistence/stage5_report.json",
    "stage6": "outputs/level13b_stage6_history_erasure/stage6_report.json",
    "stage7": "outputs/level13b_stage7_model_comparison/stage7_report.json",
    "stage8": "outputs/level13b_stage8_fresh_confirmation/stage8_report.json",
    "stage9": "outputs/level13b_stage9_measurement_audit/stage9_report.json",
    "stage10": "outputs/level13b_stage10_ecological_control_scale_shock/stage10_report.json",
    "audit": "outputs/level13b_test_requirements_audit/results.json",
}

STRATUM_ORDER = ["low_feasibility", "medium_feasibility", "high_feasibility"]
STRATUM_COLORS = {"low_feasibility": "#c0392b", "medium_feasibility": "#f1c40f", "high_feasibility": "#27ae60"}
INTERVENTION_COLORS = {
    "pressure_memory_only": "#2980b9", "legitimacy_history_only": "#8e44ad",
    "entrenchment_only": "#d35400", "all_history": "#2c3e50",
}
VARIANT_COLORS = {"removed": "#c0392b", "reversed": "#8e44ad", "equalized": "#16a085"}


def _load(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _savefig(fig, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = f"{OUT_DIR}/{name}.png"
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}", flush=True)


# ---------------------------------------------------------------------
# 1. Stage 0: exact compatibility + cross-process determinism (Section 4/6).
# ---------------------------------------------------------------------
def fig_stage0_compatibility_and_cross_process(stage0):
    if stage0 is None:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    a = stage0["comparison_a_level12b_historical_off"]
    axes[0].bar(["matched", "mismatched"], [a["n_seeds"] - a["n_mismatches"], a["n_mismatches"]], color=["#27ae60", "#c0392b"])
    axes[0].set_title(f"Comparison A: {a['n_seeds']} seeds\nbyte_for_byte_identical={a['byte_for_byte_identical']}")
    axes[0].set_ylabel("n seeds")

    c = stage0["comparison_c_cross_process_determinism_post_fix"]
    axes[1].bar(["identical launches", "distinct outputs"], [c["n_launches"] - (c["n_distinct_outputs"] - 1), c["n_distinct_outputs"] - 1], color=["#27ae60", "#c0392b"])
    axes[1].set_title(f"Comparison C: {c['n_launches']} independent process launches\nall_launches_identical={c['all_launches_identical']} (post cross-process-hash fix)")
    axes[1].set_ylabel("n launches")

    fig.suptitle("Stage 0: frozen compatibility + cross-process determinism")
    fig.tight_layout()
    _savefig(fig, "01_stage0_compatibility_and_cross_process")


# ---------------------------------------------------------------------
# 2. Stage 1: hand-computed bargaining-participation microcase (Section 7).
# ---------------------------------------------------------------------
def fig_stage1_hand_computed_microcase(stage1):
    if stage1 is None:
        return
    microcase = stage1["hand_computed_microcase"]
    series = microcase["computed_series_first_10_steps"] + [1.0] * 0
    fig, ax = plt.subplots(figsize=(9, 4))
    expected = [0.5] * 10 + [1.0] * 10 + [0.0] * 5
    ax.step(range(len(expected)), expected, where="post", label="hand-computed expectation", linewidth=2, color="#2c3e50")
    ax.axvspan(0, 10, alpha=0.08, color="#2980b9")
    ax.axvspan(10, 20, alpha=0.08, color="#27ae60")
    ax.axvspan(20, 25, alpha=0.08, color="#c0392b")
    ax.set_xlabel("step")
    ax.set_ylabel("held bargaining_participation series value")
    ax.set_title(
        "Stage 1 hand-computed microcase (3 rounds: 1/2, 2/2, 0/2 comply)\n"
        f"matches implementation={microcase['hand_computed_expected_series_matches_implementation']}, "
        f"sustained_crossing_step={microcase['sustained_crossing_step']}"
    )
    ax.legend()
    _savefig(fig, "02_stage1_hand_computed_microcase")


# ---------------------------------------------------------------------
# 3. Stage 2: activation fraction by cell (Section 8, Work Package C).
# ---------------------------------------------------------------------
def fig_stage2_calibration_activation(stage2):
    if stage2 is None:
        return
    cells = stage2["cell_summaries"]
    fig, ax = plt.subplots(figsize=(11, 6))
    labels = [f"{c['stratum'][:3]}\nrc={c['response_cost']}\np={c['period']}" for c in cells]
    values = [c["activation_fraction_min_duration_steps_10"] for c in cells]
    colors = [STRATUM_COLORS[c["stratum"]] for c in cells]
    ax.bar(range(len(cells)), values, color=colors)
    ax.axhspan(0.2, 0.8, alpha=0.1, color="#2980b9", label="target range [0.2, 0.8]")
    ax.set_xticks(range(len(cells)))
    ax.set_xticklabels(labels, fontsize=6, rotation=90)
    ax.set_ylabel("bargaining_participation activation fraction\n(min_duration_steps=10)")
    ax.set_title(f"Stage 2 calibration: {stage2['n_cells_total']} cells, {stage2['n_cells_in_target_range']} in target range")
    ax.legend()
    fig.tight_layout()
    _savefig(fig, "03_stage2_calibration_activation")


# ---------------------------------------------------------------------
# 4. Stage 3: pairwise ordering-contrast distribution (Section 9).
# ---------------------------------------------------------------------
def fig_stage3_contrasts(stage3):
    if stage3 is None:
        return
    contrasts = stage3["contrasts"]
    s_diffs = [c["raw_S_obs_diff"] for c in contrasts]
    z_diffs = [c["raw_Z_obs_diff"] for c in contrasts]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].hist(s_diffs, bins=20, color="#2980b9", alpha=0.85)
    axes[0].axvline(0, color="#c0392b", linewidth=1)
    axes[0].set_xlabel("raw S_obs difference (ordering A - ordering B)")
    axes[0].set_title(f"{len(contrasts)} matched pairwise contrasts")
    axes[1].hist(z_diffs, bins=20, color="#8e44ad", alpha=0.85)
    axes[1].axvline(0, color="#c0392b", linewidth=1)
    axes[1].set_xlabel("raw Z_obs difference (ordering A - ordering B)")
    fig.suptitle(f"Stage 3: matched sequencing factorial ({stage3['n_records']} records, all_manipulation_checks_passed={stage3['all_manipulation_checks_passed']})")
    fig.tight_layout()
    _savefig(fig, "04_stage3_pairwise_contrasts")


# ---------------------------------------------------------------------
# 5. Stage 4: homogeneous discovery LHS pool, S_obs vs Z_obs by stratum
#    (Section 8, Work Package D).
# ---------------------------------------------------------------------
def fig_stage4_lhs_scatter(stage4_records):
    if stage4_records is None:
        return
    records = stage4_records["records"]
    fig, ax = plt.subplots(figsize=(7, 6))
    for stratum in STRATUM_ORDER:
        xs = [r["S_obs_final"] for r in records if r["stratum"] == stratum]
        ys = [r["Z_obs_final"] for r in records if r["stratum"] == stratum]
        ax.scatter(xs, ys, label=stratum, color=STRATUM_COLORS[stratum], alpha=0.7, s=25)
    ax.set_xlabel("S_obs (final)")
    ax.set_ylabel("Z_obs (final)")
    ax.set_title(f"Stage 4: {len(records)}-run homogeneous discovery pool\n(48 LHS points x 5 seeds, repeated_shocks pressure)")
    ax.legend()
    _savefig(fig, "05_stage4_lhs_scatter")


# ---------------------------------------------------------------------
# 6. Stage 4: pool-level summary (records by stratum, bargaining
#    activation fraction).
# ---------------------------------------------------------------------
def fig_stage4_pool_summary(stage4):
    if stage4 is None:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    by_stratum = stage4["records_by_stratum"]
    strata = [s for s in STRATUM_ORDER if s in by_stratum]
    axes[0].bar(strata, [by_stratum[s] for s in strata], color=[STRATUM_COLORS[s] for s in strata])
    axes[0].set_ylabel("n records")
    axes[0].set_title(f"Records by stratum (n={stage4['n_records']})")

    axes[1].bar(["activated", "not activated"], [
        stage4["n_bargaining_participation_activated"],
        stage4["n_records"] - stage4["n_bargaining_participation_activated"],
    ], color=["#27ae60", "#95a5a6"])
    axes[1].set_title(f"bargaining_participation activation\nfraction={stage4['fraction_bargaining_participation_activated']:.3f}")
    fig.suptitle("Stage 4 homogeneous discovery pool summary")
    fig.tight_layout()
    _savefig(fig, "06_stage4_pool_summary")


# ---------------------------------------------------------------------
# 7. Stage 5: per-seed persistence classification counts (Section 10).
# ---------------------------------------------------------------------
def fig_stage5_persistence_classification(stage5):
    if stage5 is None:
        return
    counts = stage5["classification_counts_across_16_seeds"]
    fig, ax = plt.subplots(figsize=(8, 5))
    labels = sorted(counts.keys())
    ax.bar(labels, [counts[l] for l in labels], color="#2980b9")
    ax.set_ylabel("n seeds (of 16)")
    ax.set_title("Stage 5, Part A: security_first-vs-coevolution\nper-seed persistence classification (H3)")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    _savefig(fig, "07_stage5_persistence_classification")


# ---------------------------------------------------------------------
# 8. Stage 5: counterfactual persistence by variant and window (Section 10).
# ---------------------------------------------------------------------
def fig_stage5_counterfactual_persistence(stage5):
    if stage5 is None:
        return
    variant_data = stage5["counterfactual_persistence_by_variant"]
    windows = ["early", "middle", "late", "final_sustained"]
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(windows))
    width = 0.25
    for i, (variant, data) in enumerate(variant_data.items()):
        values = [data[f"mean_gap_at_{w}"] for w in windows]
        ax.bar(x + i * width, values, width, label=variant, color=VARIANT_COLORS.get(variant, "#333"))
    ax.set_xticks(x + width)
    ax.set_xticklabels(windows)
    ax.set_ylabel("mean |S_obs| gap vs. base security_first run")
    ax.set_title("Stage 5, Part B: counterfactual persistence by window (H5)\nnonzero, non-decaying late-window gap = history matters beyond the intervention step")
    ax.legend()
    fig.tight_layout()
    _savefig(fig, "08_stage5_counterfactual_persistence")


# ---------------------------------------------------------------------
# 9. Stage 6: sham validation + divergence by intervention (Section 11).
# ---------------------------------------------------------------------
def fig_stage6_sham_and_divergence(stage6):
    if stage6 is None:
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    sham = stage6["sham_validation"]
    axes[0].bar(["matches control", "diverges"], [sham["n_sham_matches_control_exactly"], sham["n_seeds"] - sham["n_sham_matches_control_exactly"]], color=["#27ae60", "#c0392b"])
    axes[0].set_title(f"Sham machinery validation ({sham['n_seeds']} seeds)\nsham_machinery_validated={sham['sham_machinery_validated']}")
    axes[0].set_ylabel("n seeds")

    div = stage6["divergence_by_intervention_vs_no_intervention_control"]
    windows = ["early", "middle", "late", "final_sustained"]
    x = np.arange(len(windows))
    width = 0.2
    for i, (name, data) in enumerate(div.items()):
        values = [data[f"mean_gap_at_{w}"] for w in windows]
        axes[1].bar(x + i * width, values, width, label=name, color=INTERVENTION_COLORS.get(name, "#333"))
    axes[1].set_xticks(x + 1.5 * width)
    axes[1].set_xticklabels(windows)
    axes[1].set_ylabel("mean |S_obs| gap vs. no_intervention_control")
    axes[1].set_title("History-erasure divergence by window")
    axes[1].legend(fontsize=7)

    fig.suptitle("Stage 6: history-erasure validation")
    fig.tight_layout()
    _savefig(fig, "09_stage6_sham_and_divergence")


# ---------------------------------------------------------------------
# 10. Stage 7: BIC curve for the leading discrete candidate (Section 12).
# ---------------------------------------------------------------------
def fig_stage7_bic_curve(stage7):
    if stage7 is None:
        return
    gmm = stage7["discrete_candidates"]["gmm_k1_to_8"]
    ks = [f["k"] for f in gmm["all_k_fits"]]
    bics = [f["bic"] for f in gmm["all_k_fits"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(ks, bics, marker="o", color="#2980b9")
    ax.axvline(stage7["leading_discrete_k"], color="#c0392b", linestyle="--", label=f"leading k={stage7['leading_discrete_k']} (lowest BIC among BIC-scored families)")
    ax.set_xlabel("k")
    ax.set_ylabel("BIC")
    ax.set_title(f"Stage 7: gmm_k1_to_8 BIC by k\nheld_out_log_likelihood(leading)={stage7['held_out_log_likelihood_leading_discrete']}")
    ax.legend()
    _savefig(fig, "10_stage7_bic_curve")


# ---------------------------------------------------------------------
# 11. Stage 7: cross-algorithm agreement + ecological-stratum stability
#     (Section 12).
# ---------------------------------------------------------------------
def fig_stage7_stability(stage7):
    if stage7 is None:
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    agreement = stage7["cross_algorithm_stability"]
    pairs = sorted(agreement.keys())
    aris = [agreement[p]["ari"] for p in pairs]
    axes[0].barh([p.replace("_vs_", "\nvs.\n") for p in pairs], aris, color="#8e44ad")
    axes[0].axvline(0, color="black", linewidth=0.8)
    axes[0].set_xlabel("Adjusted Rand Index")
    axes[0].set_title("Cross-algorithm label agreement")
    axes[0].tick_params(axis="y", labelsize=6)

    strat = stage7["ecological_stratum_stability"]["pairwise_agreement"]
    pairs2 = sorted(strat.keys())
    aris2 = [strat[p]["ari"] for p in pairs2]
    axes[1].barh([p.replace("_vs_", "\nvs.\n") for p in pairs2], aris2, color="#16a085")
    axes[1].axvline(0, color="black", linewidth=0.8)
    axes[1].set_xlabel("Adjusted Rand Index")
    axes[1].set_title("Cross-ecological-stratum label agreement\n(fit independently per stratum)")
    axes[1].tick_params(axis="y", labelsize=7)

    fig.suptitle(f"Stage 7 stability: leading_discrete_candidate={stage7['leading_discrete_candidate']}")
    fig.tight_layout()
    _savefig(fig, "11_stage7_stability")


# ---------------------------------------------------------------------
# 12. Stage 8: generalization-gap test, fresh confirmation (Section 13).
# ---------------------------------------------------------------------
def fig_stage8_generalization_gap(stage8):
    if stage8 is None:
        return
    gap = stage8["generalization_gap_test"]
    fig, ax = plt.subplots(figsize=(7, 5))
    labels = ["null k=1\n(no structure)", "leading k=8"]
    values = [gap["null_k1_per_run_log_likelihood"], gap["leading_k8_per_run_log_likelihood"]]
    colors = ["#95a5a6", "#27ae60" if gap["per_run_log_likelihood_gap_k8_minus_k1"] > 0 else "#c0392b"]
    ax.bar(labels, values, color=colors)
    ax.set_ylabel("per-run held-out log-likelihood on fresh Stage 8 data")
    ax.set_title(f"Stage 8 fresh confirmation (n={stage8['n_records']})\ngap (k8 - k1) = {gap['per_run_log_likelihood_gap_k8_minus_k1']:.3f}")
    _savefig(fig, "12_stage8_generalization_gap")


# ---------------------------------------------------------------------
# 13. Stage 9: S_obs/Z_obs correlation robustness panel (Section 14).
# ---------------------------------------------------------------------
def fig_stage9_correlation_robustness(stage9):
    if stage9 is None:
        return
    variants = {
        "raw": stage9["raw_correlation"],
        "partial\n(control stratum)": stage9["partial_correlation_controlling_ecological_stratum"]["partial_correlation"],
        "within-point": stage9["within_and_between_point_correlation"]["within_point_correlation"],
        "between-point": stage9["within_and_between_point_correlation"]["between_point_correlation"],
        "sum\n(non-normalized)": stage9["non_normalized_variant"]["sum_variant_correlation"],
        "equal-weight\n(used)": stage9["equal_weight_variant"]["equal_weight_correlation"],
        "PCA-weighted": stage9["equal_weight_variant"]["pca_weighted_correlation"],
        "opportunity-\ndenominated": stage9["opportunity_denominated_variant"]["opportunity_denominated_correlation"],
    }
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(list(variants.keys()), list(variants.values()), color="#2980b9")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Pearson correlation, S_obs vs. Z_obs")
    ax.set_title("Stage 9: S_obs-Z_obs correlation across measurement variants")
    ax.tick_params(axis="x", labelsize=7, rotation=15)
    fig.tight_layout()
    _savefig(fig, "13_stage9_correlation_robustness")


# ---------------------------------------------------------------------
# 14. Stage 9: factor structure scree plot (Section 14).
# ---------------------------------------------------------------------
def fig_stage9_factor_structure(stage9):
    if stage9 is None:
        return
    fs = stage9["factor_structure_analysis"]
    ratios = fs["explained_variance_ratio"]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(range(1, len(ratios) + 1), ratios, color="#8e44ad")
    ax.set_xlabel("principal component")
    ax.set_ylabel("explained variance ratio")
    ax.set_title(f"Stage 9: PCA on {len(fs['component_names'])} raw S_obs/Z_obs components\nfirst-two-cumulative={fs['first_two_components_cumulative']:.3f}")
    fig.tight_layout()
    _savefig(fig, "14_stage9_factor_structure")


# ---------------------------------------------------------------------
# 15. Stage 10: scale/shock robustness + ecological collapse ledger
#     (Section 15, Work Package K).
# ---------------------------------------------------------------------
def fig_stage10_scale_and_ledger(stage10):
    if stage10 is None:
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    scale = stage10["scale_shock_robustness"]
    cells = sorted(scale.keys())
    s_vals = [scale[c]["mean_S_obs"] for c in cells]
    z_vals = [scale[c]["mean_Z_obs"] for c in cells]
    x = np.arange(len(cells))
    width = 0.35
    axes[0].bar(x - width / 2, s_vals, width, label="mean S_obs", color="#2980b9")
    axes[0].bar(x + width / 2, z_vals, width, label="mean Z_obs", color="#8e44ad")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(cells, rotation=20, fontsize=8)
    axes[0].set_title("Stage 10 scale/shock robustness\n(2x2 population x n_patches, repeated_shocks)")
    axes[0].legend()

    by_stratum = stage10["ledger_stage3_216_runs"]["by_stratum"]
    strata = [s for s in STRATUM_ORDER if s in by_stratum]
    axes[1].bar(strata, [by_stratum[s]["collapse_rate"] for s in strata], color=[STRATUM_COLORS[s] for s in strata])
    axes[1].set_ylim(0, 1.05)
    axes[1].set_ylabel(f"collapse rate (mean_resources_final_step < {stage10['scope']['collapse_threshold']})")
    axes[1].set_title("Ecological ledger: collapse rate by stratum\n(Stage 3's own 216-run archive)")

    fig.tight_layout()
    _savefig(fig, "15_stage10_scale_and_ledger")


# ---------------------------------------------------------------------
# 16. Test requirements coverage (Section 20/task #124).
# ---------------------------------------------------------------------
def fig_test_requirements_coverage(audit):
    if audit is None:
        return
    findings = audit["findings"]
    categories = sorted(findings.keys())
    status = [1 if findings[c]["status"] == "pass" else 0 for c in categories]
    colors = ["#27ae60" if s else "#c0392b" for s in status]
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.barh(categories, status, color=colors)
    ax.set_xlim(0, 1.2)
    ax.set_xlabel("mechanically verified as covered (1=yes)")
    ax.set_title(f"Test requirements sweep: {audit['n_categories']} categories\nall_covered={audit['all_categories_covered']}")
    fig.tight_layout()
    _savefig(fig, "16_test_requirements_coverage")


def run() -> None:
    print("Level 1.3b visualizations -- disclosed scope: 16 of Section 21/23's suggested ~12-16 figures.", flush=True)

    stage0 = _load(PATHS["stage0"])
    stage1 = _load(PATHS["stage1"])
    stage2 = _load(PATHS["stage2"])
    stage3 = _load(PATHS["stage3"])
    stage4 = _load(PATHS["stage4"])
    stage4_records = _load(PATHS["stage4_records"])
    stage5 = _load(PATHS["stage5"])
    stage6 = _load(PATHS["stage6"])
    stage7 = _load(PATHS["stage7"])
    stage8 = _load(PATHS["stage8"])
    stage9 = _load(PATHS["stage9"])
    stage10 = _load(PATHS["stage10"])
    audit = _load(PATHS["audit"])

    fig_stage0_compatibility_and_cross_process(stage0)
    fig_stage1_hand_computed_microcase(stage1)
    fig_stage2_calibration_activation(stage2)
    fig_stage3_contrasts(stage3)
    fig_stage4_lhs_scatter(stage4_records)
    fig_stage4_pool_summary(stage4)
    fig_stage5_persistence_classification(stage5)
    fig_stage5_counterfactual_persistence(stage5)
    fig_stage6_sham_and_divergence(stage6)
    fig_stage7_bic_curve(stage7)
    fig_stage7_stability(stage7)
    fig_stage8_generalization_gap(stage8)
    fig_stage9_correlation_robustness(stage9)
    fig_stage9_factor_structure(stage9)
    fig_stage10_scale_and_ledger(stage10)
    fig_test_requirements_coverage(audit)


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
