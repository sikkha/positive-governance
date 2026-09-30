#!/usr/bin/env python3
"""Level 0.3b visualizations (16 required figures).

Reads the already-committed outputs of every Level 0.3b Work Package
script (does not re-run any of them) plus a small, clearly-labeled number
of fresh deterministic reproductions -- exact reruns of already-recorded
``(parameters, seed)`` pairs -- purely to recover full per-step
trajectories that the aggregate CSVs do not persist. This mirrors Level
0.3's own ``make_level03_visualizations.py`` precedent.

Every figure with a value derived across multiple seeds shows sample size
explicitly (in the title or a text annotation) and, where applicable, a
seed-quantile band, individual seed markers, or an explicit uncertainty
interval -- never a single representative run passed off as typical, and
never only the favorable-looking runs. No chart title asserts or implies
confirmation of self-regulation, an equilibrium, or any governance
concept.
"""

from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from abm_governance.simulation import Simulation
from experiments.level03b_common import build_candidate_config, load_candidate_registry
from experiments.level03b_phase_search_reanalysis import N_STEPS as REANALYSIS_N_STEPS
from experiments.level03b_phase_search_reanalysis import _reproduce_trajectory
from experiments.niche_phase_search import _point_config

OUT_DIR = "outputs/level03b_figures"

LABEL_COLORS = {
    "depleted": "tab:brown", "abundant": "tab:green", "interior-persistent": "tab:blue",
    "oscillatory": "tab:purple", "intermittent": "tab:orange", "unclassified": "black",
}
CONDITION_COLORS = {
    "endogenous": "tab:blue", "frozen": "tab:gray", "randomized": "tab:red",
    "shuffled": "tab:orange", "environment_only": "tab:green",
    "impact_disabled": "tab:cyan", "maintenance_disabled": "tab:purple",
    "ecological_mutation_disabled": "tab:pink",
}


def _savefig(fig, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"[make_level03b_visualizations] {path}")


# ---------------------------------------------------------------------
# Fig 1: confusion matrix, old label (Level 0.3) vs. new label (0.3b).
# ---------------------------------------------------------------------
def fig01_confusion_matrix(run_level: pd.DataFrame):
    ct = pd.crosstab(run_level["old_label"], run_level["new_label"])
    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(ct.values, cmap="Blues")
    ax.set_xticks(range(len(ct.columns)))
    ax.set_xticklabels(ct.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(ct.index)))
    ax.set_yticklabels(ct.index)
    for i in range(ct.shape[0]):
        for j in range(ct.shape[1]):
            v = ct.values[i, j]
            if v:
                ax.text(j, i, str(v), ha="center", va="center",
                        color="white" if v > ct.values.max() / 2 else "black")
    ax.set_xlabel("new label (classify_regime, 0.3b-v1)")
    ax.set_ylabel("old label (Level 0.3 nonstationary_classification)")
    ax.set_title(f"Fig 1: label confusion matrix, original 48 phase-search runs (n=48)")
    fig.colorbar(im, ax=ax, label="n runs")
    _savefig(fig, "fig01_confusion_matrix.png")


# ---------------------------------------------------------------------
# Fig 2/3: revised label distributions, run level and point level, both
# batches (original 16pt + supplemental 32pt).
# ---------------------------------------------------------------------
def fig02_label_distribution_run_level(run_level: pd.DataFrame, supplemental_outcomes: pd.DataFrame):
    orig = run_level["new_label"].value_counts()
    supp = supplemental_outcomes["new_label"].value_counts()
    labels = sorted(set(orig.index) | set(supp.index))
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - 0.2, [orig.get(l, 0) for l in labels], width=0.4,
           label=f"original 16-pt search (n={len(run_level)} runs)", color="tab:blue")
    ax.bar(x + 0.2, [supp.get(l, 0) for l in labels], width=0.4,
           label=f"supplemental 32-pt search (n={len(supplemental_outcomes)} runs)", color="tab:orange")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("n point-seed runs")
    ax.set_title("Fig 2: revised regime-label distribution, run level")
    ax.legend()
    _savefig(fig, "fig02_label_distribution_run_level.png")


def fig03_label_distribution_point_level(point_level: pd.DataFrame, supplemental_point_level: pd.DataFrame):
    orig = point_level["plurality_new_label"].value_counts()
    supp = supplemental_point_level["plurality_new_label"].value_counts()
    labels = sorted(set(orig.index) | set(supp.index))
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - 0.2, [orig.get(l, 0) for l in labels], width=0.4,
           label=f"original (n={len(point_level)} points)", color="tab:blue")
    ax.bar(x + 0.2, [supp.get(l, 0) for l in labels], width=0.4,
           label=f"supplemental (n={len(supplemental_point_level)} points)", color="tab:orange")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("n parameter points (plurality label)")
    ax.set_title("Fig 3: revised regime-label distribution, parameter-point level\n"
                  "(denominator = points, not runs; a point is not robust merely because 1/3 seeds got a label)")
    ax.legend()
    _savefig(fig, "fig03_label_distribution_point_level.png")


# ---------------------------------------------------------------------
# Fig 4: the questionable Level 0.3 "oscillatory" example, reclassified.
# ---------------------------------------------------------------------
def fig04_oscillatory_example(run_level: pd.DataFrame, design: pd.DataFrame):
    row = run_level[(run_level.point_id == 0) & (run_level.seed == 0)].iloc[0]
    point_row = design.set_index("point_id").loc[0]
    point_row = dict(point_row)
    point_row["seed"] = 0
    occupancy, _ = _reproduce_trajectory(point_row)
    burn_in = int(round(0.2 * len(occupancy)))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(occupancy, color="tab:purple")
    ax.axvspan(0, burn_in, color="gray", alpha=0.2, label="burn-in (excluded)")
    ax.set_xlabel("step")
    ax.set_ylabel("aggregate occupancy fraction")
    ax.set_title(
        f"Fig 4: point_id=0, seed=0 -- Level 0.3's displayed 'oscillatory' example, reclassified\n"
        f"old label: {row['old_label']} -> new label: {row['new_label']} "
        f"(n_completed_cycles={row['new_n_completed_cycles']:.0f}, "
        f"amplitude={row['new_peak_to_trough_amplitude']:.4f}, "
        f"trend_slope={row['new_trend_slope']:.5f}, "
        f"best_lag_autocorr={row['new_best_lag_autocorrelation']:.3f})"
    )
    ax.legend()
    _savefig(fig, "fig04_oscillatory_example_reclassified.png")


# ---------------------------------------------------------------------
# Fig 5: confirmed candidate trajectories (a sample of the 24 confirmation
# seeds per candidate, freshly reproduced -- confirmation_run_level.csv
# does not persist full trajectories, only summary statistics).
# ---------------------------------------------------------------------
def fig05_confirmed_candidate_trajectories(registry: dict, n_sample_seeds: int = 6, n_steps: int = 600):
    candidate_order = ["interior_persistent", "nonstationary", "near_collapse"]
    present = [k for k in candidate_order if registry["selected"].get(k)]
    fig, axes = plt.subplots(len(present), 1, figsize=(9, 3.2 * len(present)), sharex=True)
    if len(present) == 1:
        axes = [axes]
    for ax, key in zip(axes, present):
        params = registry["selected"][key]["parameters"]
        for seed in range(n_sample_seeds):
            config = build_candidate_config(params, seed=seed, n_steps=n_steps, condition="endogenous")
            result = Simulation(config).run()
            occ = [m["aggregate_fraction_of_capacity"] for m in result.metrics]
            ax.plot(occ, alpha=0.7, linewidth=1)
        burn_in = int(round(0.2 * n_steps))
        ax.axvspan(0, burn_in, color="gray", alpha=0.15)
        ax.set_title(f"{key} (sample of {n_sample_seeds} of 24 confirmation seeds, endogenous condition)")
        ax.set_ylabel("occupancy")
    axes[-1].set_xlabel("step")
    fig.suptitle("Fig 5: confirmed-candidate occupancy trajectories (fresh deterministic reproduction)")
    fig.tight_layout()
    _savefig(fig, "fig05_confirmed_candidate_trajectories.png")


# ---------------------------------------------------------------------
# Fig 6: parameter-neighborhood robustness (already-computed WP-E output).
# ---------------------------------------------------------------------
def fig06_neighborhood_robustness(neighborhood_summary: dict):
    rows = []
    for cand, entry in neighborhood_summary["per_candidate"].items():
        for axis, stat in entry["per_axis_robustness"].items():
            rows.append({"candidate": cand, "axis": axis, "fraction_passing": stat["fraction_passing"],
                         "n_neighbors": stat["n_neighbors"], "criterion_met": stat["criterion_met"]})
    df = pd.DataFrame(rows)
    candidates = df["candidate"].unique()
    fig, ax = plt.subplots(figsize=(10, 5))
    width = 0.8 / max(len(candidates), 1)
    axes_all = sorted(df["axis"].unique())
    for i, cand in enumerate(candidates):
        sub = df[df.candidate == cand].set_index("axis").reindex(axes_all)
        x = np.arange(len(axes_all)) + i * width
        ax.bar(x, sub["fraction_passing"].fillna(0), width=width, label=cand)
    ax.axhline(0.5, color="red", linestyle="--", linewidth=1, label="50% criterion")
    ax.set_xticks(np.arange(len(axes_all)) + width * (len(candidates) - 1) / 2)
    ax.set_xticklabels(axes_all, rotation=30, ha="right")
    ax.set_ylabel("fraction of local-neighbor seeds reproducing the confirmed label")
    ax.set_title("Fig 6: parameter-neighborhood robustness (+-10%/0 perturbation, 8 seeds/local point)")
    ax.legend()
    _savefig(fig, "fig06_neighborhood_robustness.png")


# ---------------------------------------------------------------------
# Fig 7: causal-condition trajectories for the primary candidate.
# ---------------------------------------------------------------------
def fig07_causal_condition_trajectories(registry: dict, n_sample_seeds: int = 3, n_steps: int = 600):
    candidate_order = ["interior_persistent", "nonstationary", "near_collapse"]
    primary_key = next((k for k in candidate_order if registry["selected"].get(k)), None)
    params = registry["selected"][primary_key]["parameters"]
    conditions = ["endogenous", "frozen", "randomized", "environment_only"]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for condition in conditions:
        for seed in range(n_sample_seeds):
            config = build_candidate_config(params, seed=seed, n_steps=n_steps, condition=condition)
            result = Simulation(config).run()
            occ = [m["aggregate_fraction_of_capacity"] for m in result.metrics]
            ax.plot(occ, color=CONDITION_COLORS.get(condition, "black"), alpha=0.6, linewidth=1,
                    label=condition if seed == 0 else None)
    burn_in = int(round(0.2 * n_steps))
    ax.axvspan(0, burn_in, color="gray", alpha=0.1)
    ax.set_xlabel("step")
    ax.set_ylabel("occupancy")
    ax.set_title(f"Fig 7: causal-condition occupancy trajectories, primary candidate ({primary_key}),\n"
                 f"{n_sample_seeds} sample seeds/condition (fresh deterministic reproduction)")
    ax.legend()
    _savefig(fig, "fig07_causal_condition_trajectories.png")


# ---------------------------------------------------------------------
# Fig 8: continuous paired-effect distributions (seed-level Delta).
# ---------------------------------------------------------------------
def fig08_paired_effect_distributions(causal_run_level: pd.DataFrame):
    outcome = "post_burn_in_mean_occupancy"
    candidates = causal_run_level["candidate"].unique()
    counterfactuals = [c for c in causal_run_level["condition"].unique() if c != "endogenous"]
    fig, axes = plt.subplots(1, len(candidates), figsize=(5.5 * len(candidates), 5), sharey=True)
    if len(candidates) == 1:
        axes = [axes]
    for ax, cand in zip(axes, candidates):
        sub = causal_run_level[causal_run_level.candidate == cand]
        endo = sub[sub.condition == "endogenous"].set_index("seed")[outcome]
        diffs, labels = [], []
        for cf in counterfactuals:
            cf_series = sub[sub.condition == cf].set_index("seed")[outcome]
            common = endo.index.intersection(cf_series.index)
            if len(common) == 0:
                continue
            diffs.append((endo.loc[common] - cf_series.loc[common]).values)
            labels.append(f"{cf}\n(n={len(common)})")
        if diffs:
            ax.violinplot(diffs, showmeans=True)
            ax.set_xticks(range(1, len(labels) + 1))
            ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
        ax.axhline(0.0, color="gray", linestyle="--", linewidth=1)
        ax.set_title(cand)
    axes[0].set_ylabel(f"seed-level paired difference: endogenous - counterfactual\n({outcome})")
    fig.suptitle("Fig 8: continuous paired-effect distributions (seed-level Delta, all matched seeds shown)")
    fig.tight_layout()
    _savefig(fig, "fig08_paired_effect_distributions.png")


# ---------------------------------------------------------------------
# Fig 9: extraction/maintenance propensity effects by condition, reusing
# WP-H's fitness-stream run (fitness_stream="ecological" = the project's
# actual default stream) since it already covers
# endogenous/frozen/randomized/environment_only for the primary candidate
# -- no fresh simulation needed.
# ---------------------------------------------------------------------
def fig09_extraction_maintenance_by_condition(fitness_stream_run_level: pd.DataFrame):
    df = fitness_stream_run_level[fitness_stream_run_level.fitness_stream == "ecological"].copy()
    df["extraction_change"] = df["extraction_propensity_after"] - df["extraction_propensity_before"]
    df["maintenance_change"] = df["maintenance_propensity_after"] - df["maintenance_propensity_before"]
    conditions = sorted(df["condition"].unique())
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax, col, title in zip(axes, ["extraction_change", "maintenance_change"],
                               ["extraction propensity change", "maintenance propensity change"]):
        means = [df[df.condition == c][col].mean() for c in conditions]
        sems = [df[df.condition == c][col].std(ddof=1) / max(1, np.sqrt((df.condition == c).sum())) for c in conditions]
        ns = [(df.condition == c).sum() for c in conditions]
        ax.bar(conditions, means, yerr=sems, capsize=4,
               color=[CONDITION_COLORS.get(c, "gray") for c in conditions])
        ax.axhline(0.0, color="black", linewidth=0.8)
        ax.set_title(title)
        ax.set_xticks(range(len(conditions)))
        ax.set_xticklabels(conditions, rotation=30, ha="right")
        for i, n in enumerate(ns):
            ax.text(i, 0, f"n={n}", ha="center", va="bottom", fontsize=7)
    fig.suptitle("Fig 9: mean ecological-policy propensity change by causal condition, primary candidate\n"
                 "(ecological fitness stream, WP-H data; error bars = SEM)")
    fig.tight_layout()
    _savefig(fig, "fig09_extraction_maintenance_by_condition.png")


# ---------------------------------------------------------------------
# Fig 10: propensity evolution (before/after), confirmation data.
# ---------------------------------------------------------------------
def fig10_propensity_evolution(confirmation_run_level: pd.DataFrame):
    candidates = confirmation_run_level["candidate"].unique()
    fig, axes = plt.subplots(1, len(candidates), figsize=(5 * len(candidates), 5), sharey=True)
    if len(candidates) == 1:
        axes = [axes]
    for ax, cand in zip(axes, candidates):
        sub = confirmation_run_level[confirmation_run_level.candidate == cand]
        data = [sub["extraction_propensity_before"], sub["extraction_propensity_after"],
                sub["maintenance_propensity_before"], sub["maintenance_propensity_after"]]
        ax.boxplot(data, tick_labels=["extr.\nbefore", "extr.\nafter", "maint.\nbefore", "maint.\nafter"])
        ax.set_title(f"{cand} (n={len(sub)} confirmation seeds)")
    axes[0].set_ylabel("propensity")
    fig.suptitle("Fig 10: ecological-policy propensity evolution, before vs. after (24 confirmation seeds/candidate)")
    fig.tight_layout()
    _savefig(fig, "fig10_propensity_evolution.png")


# ---------------------------------------------------------------------
# Fig 11: patch survival / spatial inequality, confirmation data.
# ---------------------------------------------------------------------
def fig11_patch_survival_inequality(confirmation_run_level: pd.DataFrame):
    candidates = confirmation_run_level["candidate"].unique()
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    axes[0].boxplot([confirmation_run_level[confirmation_run_level.candidate == c]["patch_survival_fraction"]
                      for c in candidates], tick_labels=list(candidates))
    axes[0].set_title("patch survival fraction")
    axes[1].boxplot([confirmation_run_level[confirmation_run_level.candidate == c]["mean_patch_occupancy_gini"]
                      for c in candidates], tick_labels=list(candidates))
    axes[1].set_title("mean patch-occupancy spatial Gini")
    for ax in axes:
        ax.set_xticklabels(candidates, rotation=20, ha="right")
    fig.suptitle("Fig 11: patch survival and spatial inequality, 24 confirmation seeds/candidate")
    fig.tight_layout()
    _savefig(fig, "fig11_patch_survival_inequality.png")


# ---------------------------------------------------------------------
# Fig 12: micro-macro linkage scatter (pooled correlational, per
# candidate, using the same confirmation data the WP-I summary was
# computed from).
# ---------------------------------------------------------------------
def fig12_micro_macro_linkage(confirmation_run_level: pd.DataFrame, linkage_summary: dict):
    candidates = confirmation_run_level["candidate"].unique()
    fig, axes = plt.subplots(1, len(candidates), figsize=(5 * len(candidates), 5))
    if len(candidates) == 1:
        axes = [axes]
    for ax, cand in zip(axes, candidates):
        sub = confirmation_run_level[confirmation_run_level.candidate == cand]
        ax.scatter(sub["maintenance_propensity_after"], sub["patch_survival_fraction"], alpha=0.7)
        corr = linkage_summary["pooled_correlational_linkage_within_candidate"].get(cand, {}).get(
            "maintenance_propensity_after__vs__patch_survival_fraction", {}
        ).get("correlation")
        ax.set_xlabel("maintenance propensity (final)")
        ax.set_ylabel("patch survival fraction")
        title = f"{cand} (n={len(sub)})"
        if corr is not None:
            title += f"\nr={corr:.2f}"
        ax.set_title(title)
    fig.suptitle("Fig 12: micro-macro linkage -- pooled correlational (across-seed) evidence\n"
                 "(correlational only; see Fig 8/9 for the stronger intervention-based evidence)")
    fig.tight_layout()
    _savefig(fig, "fig12_micro_macro_linkage.png")


# ---------------------------------------------------------------------
# Fig 13/14: WP-K confirmatory perturbation figures.
# ---------------------------------------------------------------------
def fig13_perturbation_trajectories(trajectories: pd.DataFrame, recovery: pd.DataFrame):
    candidate_order = ["interior_persistent", "nonstationary", "near_collapse"]
    present = [c for c in candidate_order if c in trajectories["candidate"].unique()]
    primary = present[0] if present else None
    shocks_available = sorted(trajectories[trajectories.candidate == primary]["shock_type"].unique()) if primary else []
    shown_shocks = shocks_available[:3]
    fig, axes = plt.subplots(1, len(shown_shocks), figsize=(5.5 * max(1, len(shown_shocks)), 5), sharey=True)
    if len(shown_shocks) == 1:
        axes = [axes]
    for ax, shock in zip(axes, shown_shocks):
        sub = trajectories[(trajectories.candidate == primary) & (trajectories.shock_type == shock)
                            & (trajectories.condition == "endogenous") & (trajectories.arm == "shocked")]
        rec = recovery[(recovery.candidate == primary) & (recovery.shock_type == shock)
                        & (recovery.condition == "endogenous")]
        for seed, grp in sub.groupby("seed"):
            elig_row = rec[rec.seed == seed]
            eligible = bool(elig_row["eligible"].iloc[0]) if not elig_row.empty else None
            color = "tab:blue" if eligible else ("tab:red" if eligible is False else "gray")
            ax.plot(grp["step"], grp["occupancy"], color=color, alpha=0.5, linewidth=0.8)
        ax.set_title(f"{shock}\n(blue=eligible, red=ineligible)")
        ax.set_xlabel("step")
    axes[0].set_ylabel("occupancy")
    fig.suptitle(f"Fig 13: confirmatory perturbation trajectories, primary candidate ({primary})")
    fig.tight_layout()
    _savefig(fig, "fig13_perturbation_trajectories.png")


def fig14_recovery_time_residual_distance(recovery: pd.DataFrame):
    eligible = recovery[recovery["eligible"] == True]  # noqa: E712
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    if not eligible.empty and eligible["time_to_sustained_recovery"].notna().any():
        axes[0].hist(eligible["time_to_sustained_recovery"].dropna(), bins=20, color="tab:blue")
    axes[0].set_title(f"time to sustained recovery (n_eligible={len(eligible)})")
    axes[0].set_xlabel("steps post-shock")
    if not eligible.empty and eligible["residual_distance_from_control"].notna().any():
        axes[1].hist(eligible["residual_distance_from_control"].dropna(), bins=20, color="tab:orange")
    axes[1].set_title("residual distance from matched control at end of run")
    axes[1].set_xlabel("|occupancy difference|")
    fig.suptitle(
        f"Fig 14: recovery-time and residual-distance distributions "
        f"(n_total_rows={len(recovery)}, n_eligible={len(eligible)}, "
        f"n_ineligible={len(recovery) - len(eligible)})"
    )
    fig.tight_layout()
    _savefig(fig, "fig14_recovery_time_residual_distance.png")


# ---------------------------------------------------------------------
# Fig 15/16: example trajectories of validated / reclassified regimes.
# ---------------------------------------------------------------------
def fig15_regime_examples(run_level: pd.DataFrame, supplemental_outcomes: pd.DataFrame, design: pd.DataFrame,
                           supplemental_design: pd.DataFrame):
    combined = pd.concat([
        run_level.assign(source="original")[["point_id", "seed", "new_label", "source"]],
        supplemental_outcomes.assign(source="supplemental")[["point_id", "seed", "new_label", "source"]],
    ], ignore_index=True)
    examples = []
    for label in ["depleted", "abundant", "unclassified", "interior-persistent", "intermittent", "oscillatory"]:
        match = combined[combined.new_label == label]
        if not match.empty:
            examples.append(match.iloc[0])
    if not examples:
        print("[make_level03b_visualizations] fig15: no regime examples found, skipping")
        return
    fig, axes = plt.subplots(len(examples), 1, figsize=(8, 2.6 * len(examples)), sharex=True)
    if len(examples) == 1:
        axes = [axes]
    for ax, ex in zip(axes, examples):
        d = design if ex["source"] == "original" else supplemental_design
        point_row = dict(d.set_index("point_id").loc[int(ex["point_id"])])
        point_row["seed"] = int(ex["seed"])
        occupancy, _ = _reproduce_trajectory(point_row)
        ax.plot(occupancy, color=LABEL_COLORS.get(ex["new_label"], "black"))
        ax.axvspan(0, int(round(0.2 * len(occupancy))), color="gray", alpha=0.15)
        ax.set_title(f"{ex['new_label']} -- {ex['source']} point_id={int(ex['point_id'])}, seed={int(ex['seed'])}")
        ax.set_ylabel("occupancy")
    axes[-1].set_xlabel("step")
    fig.suptitle("Fig 15: example trajectories of every regime label found (never every named category is forced)")
    fig.tight_layout()
    _savefig(fig, "fig15_regime_examples.png")


def fig16_reclassified_examples(run_level: pd.DataFrame, design: pd.DataFrame):
    changed = run_level[(run_level.label_changed) & (run_level.new_label.isin(["unclassified"]))]
    examples = changed.head(3)
    if examples.empty:
        print("[make_level03b_visualizations] fig16: no reclassified-to-unclassified examples found, skipping")
        return
    fig, axes = plt.subplots(len(examples), 1, figsize=(8, 2.6 * len(examples)), sharex=True)
    if len(examples) == 1:
        axes = [axes]
    for ax, (_, ex) in zip(axes, examples.iterrows()):
        point_row = dict(design.set_index("point_id").loc[int(ex["point_id"])])
        point_row["seed"] = int(ex["seed"])
        occupancy, _ = _reproduce_trajectory(point_row)
        ax.plot(occupancy, color="black")
        ax.axvspan(0, int(round(0.2 * len(occupancy))), color="gray", alpha=0.15)
        ax.set_title(f"point_id={int(ex['point_id'])}, seed={int(ex['seed'])}: "
                     f"old='{ex['old_label']}' -> new='{ex['new_label']}' ({ex['reason_for_change']})")
        ax.set_ylabel("occupancy")
    axes[-1].set_xlabel("step")
    fig.suptitle("Fig 16: examples reclassified from a named regime to unclassified/transient under the audit")
    fig.tight_layout()
    _savefig(fig, "fig16_reclassified_to_unclassified_examples.png")


def run():
    os.makedirs(OUT_DIR, exist_ok=True)

    run_level = pd.read_csv("outputs/level03b_phase_search_reanalysis/run_level_reanalysis.csv")
    point_level = pd.read_csv("outputs/level03b_phase_search_reanalysis/point_level_reanalysis.csv")
    design = pd.read_csv("outputs/niche_phase_search/niche_phase_search_design.csv")
    supplemental_outcomes = pd.read_csv("outputs/level03b_supplemental_search/supplemental_outcomes.csv")
    supplemental_point_level = pd.read_csv("outputs/level03b_supplemental_search/supplemental_point_level.csv")
    supplemental_design = pd.read_csv("outputs/level03b_supplemental_search/supplemental_design.csv")
    registry = load_candidate_registry()
    confirmation_run_level = pd.read_csv("outputs/level03b_confirmation/confirmation_run_level.csv")
    causal_run_level = pd.read_csv("outputs/level03b_causal_interventions/causal_run_level.csv")
    fitness_stream_run_level = pd.read_csv("outputs/level03b_fitness_stream/fitness_stream_run_level.csv")
    with open("outputs/level03b_neighborhood_robustness/level03b_neighborhood_robustness_summary.json") as fh:
        neighborhood_summary = json.load(fh)
    with open("outputs/level03b_micro_macro_linkage/level03b_micro_macro_linkage_summary.json") as fh:
        linkage_summary = json.load(fh)

    fig01_confusion_matrix(run_level)
    fig02_label_distribution_run_level(run_level, supplemental_outcomes)
    fig03_label_distribution_point_level(point_level, supplemental_point_level)
    fig04_oscillatory_example(run_level, design)
    fig05_confirmed_candidate_trajectories(registry)
    fig06_neighborhood_robustness(neighborhood_summary)
    fig07_causal_condition_trajectories(registry)
    fig08_paired_effect_distributions(causal_run_level)
    fig09_extraction_maintenance_by_condition(fitness_stream_run_level)
    fig10_propensity_evolution(confirmation_run_level)
    fig11_patch_survival_inequality(confirmation_run_level)
    fig12_micro_macro_linkage(confirmation_run_level, linkage_summary)

    perturbation_traj_path = "outputs/level03b_confirmatory_perturbation/confirmatory_perturbation_trajectories.csv"
    perturbation_rec_path = "outputs/level03b_confirmatory_perturbation/confirmatory_perturbation_recovery.csv"
    if os.path.exists(perturbation_traj_path) and os.path.exists(perturbation_rec_path):
        trajectories = pd.read_csv(perturbation_traj_path)
        recovery = pd.read_csv(perturbation_rec_path)
        fig13_perturbation_trajectories(trajectories, recovery)
        fig14_recovery_time_residual_distance(recovery)
    else:
        print("[make_level03b_visualizations] WP-K output not found -- skipping fig13/fig14")

    fig15_regime_examples(run_level, supplemental_outcomes, design, supplemental_design)
    fig16_reclassified_examples(run_level, design)

    print(f"[make_level03b_visualizations] done -- see {OUT_DIR}/")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
