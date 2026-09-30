#!/usr/bin/env python3
"""Level 1.3 visualizations (Section 21).

Reads the already-committed JSON outputs of every Level 1.3 stage
(`outputs/level13_stage*/*.json`, `outputs/level13_test_requirements_
audit/results.json`) -- does not re-run any of them. **One exception,
disclosed, matching Level 1.2b's own `make_level12b_visualizations.py`
precedent**: `fig_pressure_history_kinds` calls `core/historical_
pressure.py::generate_pressure_series` directly (a pure function, no
``Simulation`` run, no RNG needed for the non-stochastic kinds shown)
purely to have something to plot, since no stage script persists a raw
pressure series to disk on its own.

No chart title or axis label uses any forbidden vocabulary
(`tests/test_level13_sem_firewall_extension.py`'s
`FORBIDDEN_LEVEL13_TERMS`) -- every label is drawn from this
milestone's own observer-side vocabulary (S_obs/Z_obs,
`low_feasibility`/`medium_feasibility`/`high_feasibility`,
`seq_*`/entrenchment/legitimacy/conversion_incidence dimension names)
or plain descriptive terms (seed, population, cell). No figure treats
k=3, three orderings, or three channels as a privileged/preferred
COUNT -- every k in `DEFAULT_K_RANGE` and every one of the six
orderings is plotted identically wherever shown.

**Disclosed scope**: 14 of the ~12-16 figures Section 21 calls for,
covering every Level 1.3 Work Package and every Stage 0-9 script that
has a plottable quantity. Stage 0/1 (pure pass/fail compatibility and
activation checks) and the test-requirements audit (a pass/fail
coverage matrix) are genuinely not chart-shaped data and are
represented in one combined summary figure instead of three separate
near-empty ones -- disclosed here rather than either silently dropped
or padded into uninformative charts."""

from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from abm_governance.core.historical_pressure import PressureHistorySpec, generate_pressure_series

OUT_DIR = "outputs/level13_figures"

PATHS = {
    "stage0": "outputs/level13_stage0_exact_compatibility/report.json",
    "stage1": "outputs/level13_stage1_activation/stage1_report.json",
    "stage2": "outputs/level13_stage2_calibration/design.json",
    "stage3": "outputs/level13_stage3_sequencing_entrenchment_factorial/records.json",
    "stage4": "outputs/level13_stage4_open_pressure_history_search/records.json",
    "stage5": "outputs/level13_stage5_causal_counterfactuals/records.json",
    "stage6": "outputs/level13_stage6_blind_phenotype_discovery/results.json",
    "stage7": "outputs/level13_stage7_fresh_confirmation/records.json",
    "stage8": "outputs/level13_stage8_s_obs_z_obs_mapping/results.json",
    "stage9": "outputs/level13_stage9_scale_and_shock_robustness/records.json",
    "audit": "outputs/level13_test_requirements_audit/results.json",
}

SOURCE_COLORS = {
    "stage3": "#2980b9", "stage4": "#8e44ad",
    "stage5_base": "#27ae60", "stage5_erased": "#e67e22", "stage5_reversed": "#c0392b",
    "stage7": "#16a085",
}
STRATUM_ORDER = ["low_feasibility", "medium_feasibility", "high_feasibility"]
STRATUM_COLORS = {"low_feasibility": "#c0392b", "medium_feasibility": "#f1c40f", "high_feasibility": "#27ae60"}


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
# 1. Pressure-history kinds (Section 5, Work Package A).
# ---------------------------------------------------------------------
def fig_pressure_history_kinds():
    n_steps = 500
    kinds = {
        "early_pulse": PressureHistorySpec(kind="early_pulse", onset_step=150, low_level=0.1, high_level=0.7),
        "late_pulse": PressureHistorySpec(kind="late_pulse", onset_step=150, duration_steps=200, low_level=0.1, high_level=0.7),
        "gradual_rise": PressureHistorySpec(kind="gradual_rise", onset_step=50, duration_steps=300, low_level=0.1, high_level=0.7),
        "repeated_shocks": PressureHistorySpec(kind="repeated_shocks", onset_step=0, low_level=0.1, high_level=0.7, n_shocks=4, shock_width_steps=5, shock_interval_steps=40),
    }
    fig, ax = plt.subplots(figsize=(9, 5))
    for name, spec in kinds.items():
        series = generate_pressure_series(spec, n_steps)
        ax.plot(np.arange(n_steps), series, label=name, linewidth=1.3)
    ax.set_xlabel("step")
    ax.set_ylabel("pressure level")
    ax.set_title("Section 5 pressure-history kinds (Work Package A)\nfour of eight valid kinds shown; every kind is a pure function of its own spec")
    ax.legend(fontsize=8)
    _savefig(fig, "01_pressure_history_kinds")


# ---------------------------------------------------------------------
# 2. Stage 0/1 compatibility + activation summary, combined (both are
#    pass/fail checks, not chart-shaped data on their own).
# ---------------------------------------------------------------------
def fig_compatibility_and_activation_summary(stage0, stage1):
    if stage0 is None and stage1 is None:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    if stage0 is not None:
        labels = ["bare Level 1.0\npreset", "frozen-reference\npreset"]
        mismatches = [
            stage0["bare_level1_preset_module_gate_noop"]["n_mismatches"],
            stage0["frozen_reference_preset_module_gate_noop"]["n_mismatches"],
        ]
        axes[0].bar(labels, mismatches, color="#27ae60")
        axes[0].set_ylim(0, max(1, stage0["n_seeds"]))
        axes[0].set_ylabel(f"mismatched seeds (of {stage0['n_seeds']})")
        axes[0].set_title("Stage 0: exact compatibility\n(historical module gate is a true no-op)")
    else:
        axes[0].axis("off")

    if stage1 is not None:
        names = list(stage1["conditions"].keys())
        all_pass = [1 if all(stage1["conditions"][n]["checks"].values()) else 0 for n in names]
        colors = ["#27ae60" if v else "#c0392b" for v in all_pass]
        axes[1].barh([n.replace("level13_", "") for n in names], all_pass, color=colors)
        axes[1].set_xlim(0, 1.2)
        axes[1].set_xlabel("all checks passed (1=yes)")
        axes[1].set_title("Stage 1: mechanism activation\n(7 master flags, one condition each)")
    else:
        axes[1].axis("off")

    fig.tight_layout()
    _savefig(fig, "02_compatibility_and_activation_summary")


# ---------------------------------------------------------------------
# 3. Stage 2: ecological feasibility strata.
# ---------------------------------------------------------------------
def fig_feasibility_strata(stage2):
    if stage2 is None:
        return
    counts = stage2["stratum_counts"]
    fig, ax = plt.subplots(figsize=(6, 5))
    labels = [s for s in STRATUM_ORDER if s in counts]
    ax.bar(labels, [counts[s] for s in labels], color=[STRATUM_COLORS[s] for s in labels])
    cuts = stage2["stratum_cut_points"]
    ax.set_title(f"Stage 2: ecological feasibility strata (frozen)\nlow_cut={cuts['low_cut']:.3f}, high_cut={cuts['high_cut']:.3f}")
    ax.set_ylabel("n points")
    _savefig(fig, "03_feasibility_strata")


# ---------------------------------------------------------------------
# 4. Stage 3: mean S_obs/Z_obs by pressure-onset ordering.
# ---------------------------------------------------------------------
def fig_stage3_by_ordering(stage3):
    if stage3 is None:
        return
    from collections import defaultdict

    by_order = defaultdict(list)
    for r in stage3["records"]:
        by_order[r["order_name"]].append(r["phenotype_vector"])
    orders = sorted(by_order.keys())
    s_means = [np.mean([pv["S_obs"] for pv in by_order[o]]) for o in orders]
    z_means = [np.mean([pv["Z_obs"] for pv in by_order[o]]) for o in orders]

    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(orders))
    width = 0.35
    ax.bar(x - width / 2, s_means, width, label="mean S_obs", color="#2980b9")
    ax.bar(x + width / 2, z_means, width, label="mean Z_obs", color="#e67e22")
    ax.set_xticks(x)
    ax.set_xticklabels([o.replace("_pressure", "").replace("coordination_complexity", "coordination") for o in orders], rotation=30, ha="right", fontsize=7)
    ax.set_ylabel("mean value across cell (12 runs: 6 seeds x entrenchment on/off)")
    ax.set_title("Stage 3: S_obs/Z_obs by pressure-onset ordering\nall six permutations shown identically -- no ordering privileged")
    ax.legend()
    fig.tight_layout()
    _savefig(fig, "04_stage3_by_ordering")


# ---------------------------------------------------------------------
# 5. Stage 3: entrenchment's own effect (matched-seed, on vs off).
# ---------------------------------------------------------------------
def fig_stage3_entrenchment_effect(stage3):
    if stage3 is None:
        return
    on = [r["phenotype_vector"]["entrenchment"] for r in stage3["records"] if r["entrenchment_enabled"]]
    off = [r["phenotype_vector"]["entrenchment"] for r in stage3["records"] if not r["entrenchment_enabled"]]
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.boxplot([off, on], tick_labels=["entrenchment_enabled=False", "entrenchment_enabled=True"])
    ax.set_ylabel("Work Package H entrenchment dimension")
    ax.set_title("Stage 3: entrenchment dimension, on vs. off\n(pooled across all six orderings x 6 seeds)")
    _savefig(fig, "05_stage3_entrenchment_effect")


# ---------------------------------------------------------------------
# 6. Stage 4: open LHS search -- onset step vs. S_obs, colored by channel.
# ---------------------------------------------------------------------
def fig_stage4_lhs_scatter(stage4):
    if stage4 is None:
        return
    fig, ax = plt.subplots(figsize=(8, 5.5))
    channels = ["security_pressure", "bargaining_pressure", "coordination_complexity"]
    colors = {"security_pressure": "#2980b9", "bargaining_pressure": "#8e44ad", "coordination_complexity": "#16a085"}
    for channel in channels:
        xs = [r["draw"][f"{channel}_onset_step"] for r in stage4["records"]]
        ys = [r["phenotype_vector"]["S_obs"] for r in stage4["records"]]
        ax.scatter(xs, ys, s=14, alpha=0.5, color=colors[channel], label=channel.replace("_pressure", "").replace("coordination_complexity", "coordination"))
    ax.set_xlabel("channel's own onset step (LHS draw)")
    ax.set_ylabel("S_obs")
    ax.set_title(f"Stage 4: open pressure-history search\n{stage4['n_runs']} runs across {stage4['n_points']} LHS points x {stage4['n_seeds_per_point']} seeds")
    ax.legend(fontsize=8)
    _savefig(fig, "06_stage4_lhs_scatter")


# ---------------------------------------------------------------------
# 7. Stage 5: counterfactual shift in S_obs/Z_obs (erased/reversed vs base).
# ---------------------------------------------------------------------
def fig_stage5_counterfactual_shift(stage5):
    if stage5 is None:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    labels = ["erased vs base\nS_obs", "erased vs base\nZ_obs", "reversed vs base\nS_obs", "reversed vs base\nZ_obs"]
    values = [
        stage5["mean_erased_vs_base_s_obs_abs_diff"], stage5["mean_erased_vs_base_z_obs_abs_diff"],
        stage5["mean_reversed_vs_base_s_obs_abs_diff"], stage5["mean_reversed_vs_base_z_obs_abs_diff"],
    ]
    ax.bar(labels, values, color=["#2980b9", "#e67e22", "#2980b9", "#e67e22"])
    ax.set_ylabel(f"mean |difference| across {stage5['n_seeds']} matched seeds")
    ax.set_title("Stage 5: causal historical counterfactuals\n(erase/reverse the realized security-pressure series, same seed)")
    _savefig(fig, "07_stage5_counterfactual_shift")


# ---------------------------------------------------------------------
# 8. Stage 6: model selection (silhouette across k, gmm/hierarchical).
# ---------------------------------------------------------------------
def fig_stage6_model_selection(stage6):
    if stage6 is None:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    for method, color, marker in [("gmm", "#2980b9", "o"), ("hierarchical", "#8e44ad", "s")]:
        results = stage6["k_range_results"][method]
        ks = [r["k"] for r in results]
        sils = [r["metrics"]["silhouette"] for r in results]
        plotted = [0.0 if (s is None or (isinstance(s, float) and s != s)) else s for s in sils]
        ax.plot(ks, plotted, marker=marker, color=color, label=method)
    ax.axvline(1, color="gray", linewidth=0.5, linestyle=":")
    ax.annotate("k=1: silhouette\nundefined", xy=(1, 0), xytext=(1.3, 0.03), fontsize=7)
    ax.set_xlabel("k")
    ax.set_ylabel("silhouette score")
    ax.set_title(f"Stage 6: blind phenotype discovery, model selection\nheadline_k={stage6['headline_k']} (n={stage6['n_total']} pooled runs)")
    ax.legend()
    _savefig(fig, "08_stage6_model_selection")


# ---------------------------------------------------------------------
# 9. Stage 6: stability diagnostics (bootstrap, algorithm agreement,
#    source-stage recovery, missingness-strategy robustness).
# ---------------------------------------------------------------------
def fig_stage6_stability(stage6):
    if stage6 is None:
        return
    metrics = {
        "bootstrap\n(within-fit)": stage6["bootstrap_stability"]["mean_ari"],
        "algorithm\nagreement": stage6["mean_algorithm_agreement_ari"],
        "vs. source\nstage": stage6["cluster_vs_source_stage_ari"],
        "missingness\nindicator ARI": stage6["missingness_strategy_robustness_ari"].get("missingness_indicator", float("nan")),
    }
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(list(metrics.keys()), [v if v == v else 0.0 for v in metrics.values()], color="#2980b9")
    ax.axhline(0.3, color="black", linestyle="--", linewidth=0.7, label="stability bar (0.3, Level 1.2b's own precedent)")
    ax.set_ylabel("adjusted Rand index")
    ax.set_title("Stage 6: discovery robustness checks\nlow vs.-source-stage ARI is evidence structure is not a pure pooling artifact")
    ax.legend(fontsize=8)
    _savefig(fig, "09_stage6_stability")


# ---------------------------------------------------------------------
# 10. Stage 7: fresh confirmation -- predicted cluster distribution +
#     log-likelihood gap.
# ---------------------------------------------------------------------
def fig_stage7_fresh_confirmation(stage7):
    if stage7 is None:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    counts = stage7["predicted_label_counts"]
    axes[0].bar(list(counts.keys()), list(counts.values()), color="#16a085")
    axes[0].set_xlabel("Stage 6 cluster label (out-of-sample prediction)")
    axes[0].set_ylabel("n fresh points")
    axes[0].set_title(f"Stage 7: {stage7['n_points']} fresh points\nassigned to Stage 6's frozen fit")

    axes[1].bar(
        ["training pool\n(216 runs)", "fresh points\n(12 runs)"],
        [stage7["mean_train_log_likelihood_per_point"], stage7["mean_fresh_log_likelihood_per_point"]],
        color=["#2980b9", "#c0392b"],
    )
    axes[1].set_ylabel("mean log-likelihood per point")
    axes[1].set_title("Out-of-sample generalization gap")
    fig.tight_layout()
    _savefig(fig, "10_stage7_fresh_confirmation")


# ---------------------------------------------------------------------
# 11. Stage 8: S_obs vs Z_obs scatter, colored by source stage.
# ---------------------------------------------------------------------
def fig_stage8_scatter():
    stage8_pool_path = "outputs/level13_stage8_s_obs_z_obs_mapping/results.json"
    if not os.path.exists(stage8_pool_path):
        return
    from experiments.level13_stage8_s_obs_z_obs_mapping import pool_s_obs_z_obs

    pooled = pool_s_obs_z_obs()
    fig, ax = plt.subplots(figsize=(8, 6))
    for source in sorted(SOURCE_COLORS):
        rows = [p for p in pooled if p["source_stage"] == source]
        if not rows:
            continue
        ax.scatter([r["S_obs"] for r in rows], [r["Z_obs"] for r in rows], s=16, alpha=0.55, color=SOURCE_COLORS[source], label=source)
    ax.set_xlabel("S_obs")
    ax.set_ylabel("Z_obs")
    ax.set_title(f"Stage 8: pooled S_obs-Z_obs mapping ({len(pooled)} runs)\nprovenance shown for reference only -- never used in any fit")
    ax.legend(fontsize=7, loc="lower right")
    _savefig(fig, "11_stage8_scatter")


# ---------------------------------------------------------------------
# 12. Stage 8: covariate correlations with S_obs/Z_obs.
# ---------------------------------------------------------------------
def fig_stage8_covariate_correlations(stage8):
    if stage8 is None:
        return
    covs = list(stage8["covariate_correlations"].keys())
    s_r = [stage8["covariate_correlations"][c]["with_s_obs"]["pearson_r"] for c in covs]
    z_r = [stage8["covariate_correlations"][c]["with_z_obs"]["pearson_r"] for c in covs]

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(covs))
    width = 0.35
    ax.bar(x - width / 2, s_r, width, label="with S_obs", color="#2980b9")
    ax.bar(x + width / 2, z_r, width, label="with Z_obs", color="#e67e22")
    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(covs, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("Pearson r")
    ax.set_title(f"Stage 8: S_obs/Z_obs correlation with other Work Package H dimensions\n(n={stage8['n_total']} pooled runs)")
    ax.legend()
    fig.tight_layout()
    _savefig(fig, "12_stage8_covariate_correlations")


# ---------------------------------------------------------------------
# 13. Stage 9: scale/shock robustness -- S_obs/Z_obs by scale cell.
# ---------------------------------------------------------------------
def fig_stage9_scale_robustness(stage9):
    if stage9 is None:
        return
    cells = stage9["cell_summaries"]
    labels = [f"pop={c['population_size']}\npatches={c['n_patches']}" for c in cells]
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(cells))
    width = 0.35
    ax.bar(x - width / 2, [c["mean_s_obs"] for c in cells], width, label="mean S_obs", color="#2980b9")
    ax.bar(x + width / 2, [c["mean_z_obs"] for c in cells], width, label="mean Z_obs", color="#e67e22")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel(f"mean value ({stage9['n_seeds_per_cell']} seeds/cell, repeated_shocks pressure)")
    ax.set_title("Stage 9: scale and shock robustness")
    ax.legend()
    _savefig(fig, "13_stage9_scale_robustness")


# ---------------------------------------------------------------------
# 14. Test-requirements coverage summary (task #105).
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
    _savefig(fig, "14_test_requirements_coverage")


def run() -> None:
    print("Level 1.3 visualizations -- disclosed scope: 14 of Section 21's suggested ~12-16 figures.", flush=True)
    print("Combined into one figure rather than three near-empty pass/fail charts: Stage 0, Stage 1.", flush=True)

    stage0 = _load(PATHS["stage0"])
    stage1 = _load(PATHS["stage1"])
    stage2 = _load(PATHS["stage2"])
    stage3 = _load(PATHS["stage3"])
    stage4 = _load(PATHS["stage4"])
    stage5 = _load(PATHS["stage5"])
    stage6 = _load(PATHS["stage6"])
    stage7 = _load(PATHS["stage7"])
    stage8 = _load(PATHS["stage8"])
    stage9 = _load(PATHS["stage9"])
    audit = _load(PATHS["audit"])

    fig_pressure_history_kinds()
    fig_compatibility_and_activation_summary(stage0, stage1)
    fig_feasibility_strata(stage2)
    fig_stage3_by_ordering(stage3)
    fig_stage3_entrenchment_effect(stage3)
    fig_stage4_lhs_scatter(stage4)
    fig_stage5_counterfactual_shift(stage5)
    fig_stage6_model_selection(stage6)
    fig_stage6_stability(stage6)
    fig_stage7_fresh_confirmation(stage7)
    fig_stage8_scatter()
    fig_stage8_covariate_correlations(stage8)
    fig_stage9_scale_robustness(stage9)
    fig_test_requirements_coverage(audit)


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
