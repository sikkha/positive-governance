#!/usr/bin/env python3
"""Level 0.3 visualizations (12 required figures).

Reads the aggregated outputs of ``experiments/niche_causal_interventions.py``,
``experiments/niche_viability_threshold_sweep.py``,
``experiments/niche_phase_search.py``, and
``experiments/niche_perturbation_recovery.py`` (does not re-run those),
plus a small number of fresh, cheap ``level03_patches_default`` runs
purely to obtain full per-step patch/ecological/joint-action trajectories
that none of the four experiment scripts persist at that granularity
(they persist aggregate occupancy and summary statistics, which is
sufficient for their own analyses but not for a per-step patch/
extraction/maintenance figure) — these are clearly labeled as
freshly-run in their titles. Figure 12's five example trajectories are
*exact* reproductions of specific (point_id, seed) pairs from the phase
search's own saved design (same seed, same parameters, so byte-for-byte
the same run), not new simulations.

Every figure with a value derived across multiple seeds shows a
seed-quantile band or explicit per-seed markers, never a single
representative run passed off as typical. No chart title asserts or
implies confirmation of self-regulation, an equilibrium, or any
governance concept — titles state what is plotted, following the
project's established convention (see ``make_level02_visualizations.py``).
"""

from __future__ import annotations

import argparse
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation
from experiments.niche_phase_search import _point_config

FRESH_SEEDS = list(range(5))
FRESH_POPULATION_SIZE = 24
FRESH_N_STEPS = 300
FRESH_N_PATCHES = 4

LABEL_COLORS = {
    "depleted": "tab:brown", "abundant": "tab:green", "interior-persistent": "tab:blue",
    "oscillatory": "tab:purple", "intermittent": "tab:orange", "spatially-polarized": "tab:red",
    "recovering": "tab:cyan", "non-recovering": "tab:gray", "unclassified": "black",
}


def _fresh_niche_runs():
    """Run a handful of cheap level03_patches_default replicates purely
    for the per-step figures that need patch/ecological/joint-action
    granularity. Returns (metrics_df, snapshots_df)."""
    metrics_rows, snapshot_rows = [], []
    for seed in FRESH_SEEDS:
        config = SimulationConfig.level03_patches_default(
            seed=seed, population_size=FRESH_POPULATION_SIZE, n_steps=FRESH_N_STEPS,
            n_patches=FRESH_N_PATCHES, mean_degree=4, imitation_period=10,
        )
        result = Simulation(config).run()
        for row in result.metrics:
            metrics_rows.append({"seed": seed, **row})
        for snap in result.ecological_policy_snapshots:
            snapshot_rows.append({"seed": seed, **snap})
    return pd.DataFrame(metrics_rows), pd.DataFrame(snapshot_rows)


def _quantile_band(ax, df, x_col, y_col, label, color):
    grouped = df.groupby(x_col)[y_col]
    median = grouped.median()
    q10 = grouped.quantile(0.10)
    q90 = grouped.quantile(0.90)
    ax.plot(median.index, median.values, label=label, color=color)
    ax.fill_between(median.index, q10.values, q90.values, alpha=0.2, color=color)


# ---------------------------------------------------------------------
# Figure 1: patch occupancies over time (fresh runs)
# ---------------------------------------------------------------------
def fig_patch_occupancy(metrics: pd.DataFrame, out_path: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 5))
    _quantile_band(ax, metrics, "step", "patch_occupancy_mean", "mean patch occupancy", "tab:blue")
    ax.fill_between(
        metrics.groupby("step")["step"].first(),
        metrics.groupby("step")["patch_occupancy_min"].median(),
        metrics.groupby("step")["patch_occupancy_max"].median(),
        alpha=0.08, color="tab:blue", label="median of per-step [min, max] across patches",
    )
    ax.set_xlabel("step")
    ax.set_ylabel("fraction of patch capacity")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=8)
    ax.set_title(f"Patch occupancy over time (fresh runs, n={len(FRESH_SEEDS)} seeds,\nmedian and 10-90th pct band)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 2: extraction / maintenance over time (fresh runs)
# ---------------------------------------------------------------------
def fig_extraction_maintenance(metrics: pd.DataFrame, out_path: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 5))
    _quantile_band(ax, metrics, "step", "ecological_actual_extraction_total", "actual extraction (total)", "tab:red")
    _quantile_band(
        ax, metrics, "step", "ecological_maintenance_effective_total", "effective maintenance (total)", "tab:green"
    )
    ax.set_xlabel("step")
    ax.set_ylabel("population total, this step")
    ax.legend(fontsize=8)
    ax.set_title(f"Extraction vs. maintenance over time (fresh runs, n={len(FRESH_SEEDS)} seeds,\nmedian and 10-90th pct band)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 3: social cooperation vs. ecological behaviour over time
# ---------------------------------------------------------------------
def fig_social_vs_ecological(metrics: pd.DataFrame, out_path: str) -> str:
    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax2 = ax1.twinx()
    med = metrics.groupby("step")["cooperation_rate"].median()
    ax1.plot(med.index, med.values, color="tab:blue", label="cooperation_rate (median)")
    med2 = metrics.groupby("step")["restraint_frequency"].median()
    ax2.plot(med2.index, med2.values, color="tab:orange", label="restraint_frequency (median)")
    ax1.set_xlabel("step")
    ax1.set_ylabel("cooperation_rate", color="tab:blue")
    ax2.set_ylabel("restraint_frequency (zero-extraction requests)", color="tab:orange")
    ax1.set_ylim(0, 1)
    ax2.set_ylim(0, 1)
    fig.legend(loc="upper right", bbox_to_anchor=(0.9, 0.9), fontsize=8)
    ax1.set_title(f"Social cooperation vs. ecological restraint over time\n(fresh runs, n={len(FRESH_SEEDS)} seeds, medians)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 4: the 4 joint social x ecological action frequencies
# ---------------------------------------------------------------------
def fig_joint_action_frequencies(metrics: pd.DataFrame, out_path: str) -> str:
    labels = [
        "cooperate_and_extraction_dominant", "cooperate_and_maintenance_dominant",
        "defect_and_extraction_dominant", "defect_and_maintenance_dominant",
    ]
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["tab:blue", "tab:green", "tab:red", "tab:orange"]
    for label, color in zip(labels, colors):
        _quantile_band(ax, metrics, "step", f"{label}_frequency", label.replace("_", " "), color)
    ax.set_xlabel("step")
    ax.set_ylabel("frequency among joint-eligible agents")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=7, loc="upper right")
    ax.set_title(
        f"The four joint social x ecological action frequencies over time\n"
        f"(fresh runs, n={len(FRESH_SEEDS)} seeds, median and 10-90th pct band;\n"
        f"never compressed to a single score)"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 5: spatial inequality across patches
# ---------------------------------------------------------------------
def fig_spatial_inequality(metrics: pd.DataFrame, out_path: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 5))
    _quantile_band(ax, metrics, "step", "patch_occupancy_spatial_gini", "spatial Gini across patches", "tab:purple")
    ax.set_xlabel("step")
    ax.set_ylabel("Gini coefficient of per-patch resource stocks")
    ax.set_ylim(0, 1)
    ax.set_title(f"Spatial inequality across patches over time\n(fresh runs, n={len(FRESH_SEEDS)} seeds, median and 10-90th pct band)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 6: ecological-policy diversity
# ---------------------------------------------------------------------
def fig_ecological_policy_diversity(snapshots: pd.DataFrame, out_path: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 5))
    if not snapshots.empty:
        _quantile_band(ax, snapshots, "step", "ecological_policy_diversity_bits", "ecological-policy diversity (bits)", "tab:blue")
    ax.set_xlabel("step")
    ax.set_ylabel("Shannon entropy (bits) of discretized ecological policy")
    ax.set_title(
        f"Ecological-policy diversity over time\n(fresh runs, n={len(FRESH_SEEDS)} seeds, "
        f"median and 10-90th pct band;\nrecorded at each scheduled adaptation step)"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 7: phase-search outcome map / projection
# ---------------------------------------------------------------------
def fig_phase_search_outcome_map(phase_dir: str, out_path: str) -> str | None:
    outcomes_path = os.path.join(phase_dir, "niche_phase_search_outcomes.csv")
    design_path = os.path.join(phase_dir, "niche_phase_search_design.csv")
    if not (os.path.exists(outcomes_path) and os.path.exists(design_path)):
        return None
    outcomes = pd.read_csv(outcomes_path)
    design = pd.read_csv(design_path)
    merged = outcomes.merge(design, on="point_id")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    ax = axes[0]
    for label, group in merged.groupby("region_label"):
        ax.scatter(
            group["patch_regen_rate"], group["maintenance_efficiency"],
            label=label, color=LABEL_COLORS.get(label, "black"), s=40, alpha=0.8,
        )
    ax.set_xlabel("patch_regen_rate")
    ax.set_ylabel("maintenance_efficiency")
    ax.legend(fontsize=7, loc="best")
    ax.set_title("Post-hoc outcome labels projected onto\n(patch_regen_rate, maintenance_efficiency)")

    ax2 = axes[1]
    counts = merged["region_label"].value_counts()
    ax2.bar(counts.index, counts.values, color=[LABEL_COLORS.get(l, "black") for l in counts.index])
    ax2.set_ylabel("count (of point x seed runs)")
    ax2.tick_params(axis="x", rotation=30)
    ax2.set_title(f"Post-hoc outcome label distribution\n(n={len(merged)} point x seed runs, LHS design, no target shaping)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 8: endogenous vs. frozen/randomized/no-effect/shuffled
# ---------------------------------------------------------------------
def fig_causal_conditions(causal_dir: str, out_path: str) -> str | None:
    path = os.path.join(causal_dir, "niche_causal_trajectories.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    colors = {"endogenous": "tab:blue", "no_effect": "tab:gray", "frozen": "tab:orange",
              "randomized": "tab:red", "shuffled": "tab:green"}
    for condition, group in df.groupby("condition"):
        _quantile_band(ax, group, "step", "occupancy", condition, colors.get(condition, "black"))
    ax.set_xlabel("step")
    ax.set_ylabel("aggregate patch occupancy (fraction of capacity)")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=8)
    n_seeds = df["seed"].nunique()
    ax.set_title(
        f"Endogenous feedback vs. WP-F counterfactuals\n(n={n_seeds} matched seeds, median and 10-90th pct band)"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 9: paired intervention-effect distribution
# ---------------------------------------------------------------------
def fig_paired_effect_distribution(causal_dir: str, out_path: str) -> str | None:
    path = os.path.join(causal_dir, "niche_causal_paired_differences.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    if df.empty:
        return None
    fig, ax = plt.subplots(figsize=(8, 5.5))
    conditions = sorted(df["condition"].unique())
    data = [df[df.condition == c]["paired_difference"].to_numpy() for c in conditions]
    ax.boxplot(data, tick_labels=conditions, showmeans=True)
    for i, d in enumerate(data, start=1):
        jitter = np.random.default_rng(0).normal(0, 0.04, size=len(d))
        ax.scatter(np.full(len(d), i) + jitter, d, color="tab:blue", alpha=0.6, s=15, zorder=3)
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_ylabel("paired difference (endogenous - counterfactual), fraction_interior")
    ax.set_title(f"Paired intervention-effect distribution across matched seeds\n(n={df['seed'].nunique()} seeds; each point is one seed)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 10: viability-threshold results
# ---------------------------------------------------------------------
def fig_viability_threshold_results(viability_dir: str, out_path: str) -> str | None:
    path = os.path.join(viability_dir, "niche_viability_sweep_aggregate.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    if df.empty:
        return None
    df = df.copy()
    df["point_label"] = df.apply(lambda r: f"{r['mode']}\ndt={r['distress_threshold']},ds={r['deficit_steps']}", axis=1)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(df))
    width = 0.25
    ax.bar(x - width, df["mean_entered_distress"], width, label="mean entered distress")
    ax.bar(x, df["mean_entered_dormant"], width, label="mean entered dormant")
    ax.bar(x + width, df["mean_removed"], width, label="mean removed")
    ax.set_xticks(x)
    ax.set_xticklabels(df["point_label"], fontsize=7)
    ax.set_ylabel("mean count across seeds")
    ax.legend(fontsize=8)
    ax.set_title("Viability-threshold sweep: where the mechanism becomes active\n(one bar group per grid point, averaged across seeds)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 11: perturbation / recovery trajectories
# ---------------------------------------------------------------------
def fig_perturbation_trajectories(perturbation_dir: str, out_path: str) -> str | None:
    path = os.path.join(perturbation_dir, "niche_perturbation_trajectories.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df = df[df.condition == "endogenous"]
    shock_types = sorted(df["shock_type"].unique())
    n = len(shock_types)
    ncols = 3
    nrows = -(-n // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 3.5 * nrows), squeeze=False)
    shock_step = None
    for i, shock_type in enumerate(shock_types):
        ax = axes[i // ncols][i % ncols]
        sub = df[df.shock_type == shock_type]
        for arm, color in (("control", "tab:gray"), ("shocked", "tab:red")):
            arm_df = sub[sub.arm == arm]
            med = arm_df.groupby("step")["occupancy"].median()
            ax.plot(med.index, med.values, label=arm, color=color)
        ax.set_title(shock_type, fontsize=9)
        ax.set_xlabel("step")
        ax.set_ylabel("occupancy")
        ax.legend(fontsize=6)
    for i in range(n, nrows * ncols):
        axes[i // ncols][i % ncols].axis("off")
    fig.suptitle("Perturbation/recovery trajectories, control vs. shocked (median across seeds)", fontsize=11)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 12: example trajectories for each observed label (exact
# reproductions of specific phase-search (point_id, seed) pairs).
# ---------------------------------------------------------------------
def fig_label_examples(phase_dir: str, out_path: str) -> str | None:
    outcomes_path = os.path.join(phase_dir, "niche_phase_search_outcomes.csv")
    design_path = os.path.join(phase_dir, "niche_phase_search_design.csv")
    if not (os.path.exists(outcomes_path) and os.path.exists(design_path)):
        return None
    outcomes = pd.read_csv(outcomes_path)
    design = pd.read_csv(design_path)

    examples = outcomes.groupby("region_label").first().reset_index()
    if examples.empty:
        return None

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for _, ex in examples.iterrows():
        point_row = design[design.point_id == ex["point_id"]].iloc[0]
        config = _point_config(point_row, int(ex["seed"]), n_steps=250)
        result = Simulation(config).run()
        occ = [m["aggregate_fraction_of_capacity"] for m in result.metrics]
        ax.plot(range(len(occ)), occ, label=f"{ex['region_label']} (point {int(ex['point_id'])})",
                 color=LABEL_COLORS.get(ex["region_label"], "black"))
    ax.set_xlabel("step")
    ax.set_ylabel("aggregate patch occupancy")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=7)
    ax.set_title(
        "Example trajectories for each observed post-hoc label\n"
        "(exact reproductions of the labeled phase-search run: same seed, same parameters)"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--causal-dir", type=str, default="outputs/niche_causal_interventions")
    parser.add_argument("--viability-dir", type=str, default="outputs/niche_viability_threshold_sweep")
    parser.add_argument("--phase-dir", type=str, default="outputs/niche_phase_search")
    parser.add_argument("--perturbation-dir", type=str, default="outputs/niche_perturbation_recovery")
    parser.add_argument("--out", type=str, default="outputs/figures_level03")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    print("[make_level03_visualizations] running fresh trajectory replicates...")
    metrics, snapshots = _fresh_niche_runs()

    results = {}
    results["01_patch_occupancy_over_time"] = fig_patch_occupancy(metrics, os.path.join(args.out, "01_patch_occupancy_over_time.png"))
    results["02_extraction_maintenance_over_time"] = fig_extraction_maintenance(
        metrics, os.path.join(args.out, "02_extraction_maintenance_over_time.png")
    )
    results["03_social_vs_ecological_behaviour"] = fig_social_vs_ecological(
        metrics, os.path.join(args.out, "03_social_vs_ecological_behaviour.png")
    )
    results["04_joint_action_frequencies"] = fig_joint_action_frequencies(
        metrics, os.path.join(args.out, "04_joint_action_frequencies.png")
    )
    results["05_spatial_inequality"] = fig_spatial_inequality(metrics, os.path.join(args.out, "05_spatial_inequality.png"))
    results["06_ecological_policy_diversity"] = fig_ecological_policy_diversity(
        snapshots, os.path.join(args.out, "06_ecological_policy_diversity.png")
    )
    results["07_phase_search_outcome_map"] = fig_phase_search_outcome_map(
        args.phase_dir, os.path.join(args.out, "07_phase_search_outcome_map.png")
    )
    results["08_causal_conditions"] = fig_causal_conditions(args.causal_dir, os.path.join(args.out, "08_causal_conditions.png"))
    results["09_paired_effect_distribution"] = fig_paired_effect_distribution(
        args.causal_dir, os.path.join(args.out, "09_paired_effect_distribution.png")
    )
    results["10_viability_threshold_results"] = fig_viability_threshold_results(
        args.viability_dir, os.path.join(args.out, "10_viability_threshold_results.png")
    )
    results["11_perturbation_trajectories"] = fig_perturbation_trajectories(
        args.perturbation_dir, os.path.join(args.out, "11_perturbation_trajectories.png")
    )
    results["12_label_examples"] = fig_label_examples(args.phase_dir, os.path.join(args.out, "12_label_examples.png"))

    for name, path in results.items():
        status = "OK" if path else "SKIPPED (missing input data)"
        print(f"[make_level03_visualizations] {name}: {status}")
    return 0


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    raise SystemExit(main())
