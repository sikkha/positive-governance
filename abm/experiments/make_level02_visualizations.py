#!/usr/bin/env python3
"""Level 0.2 visualizations.

Reads the aggregated outputs of ``experiments/phase_sweep.py``,
``experiments/boundary_perturbation.py``, ``experiments/
turnover_boundary_sweep.py``, and ``experiments/null_model_comparisons
.py`` (does not re-run the sweeps) and additionally runs a small number
of fresh, cheap simulations purely to obtain full per-step trajectories
for the two figures that need a time axis (population-state composition,
and the boundary perturbation/recovery trajectory) — these are the only
two figures backed by new simulation runs rather than a re-plot of
existing aggregated output, and are clearly labeled as such in their
titles/captions.

Every figure with a value derived across multiple seeds shows a
seed-quantile band or explicit error bars, never a single representative
run, per the milestone brief. No chart title asserts or implies
confirmation of any theory — titles state what is plotted, not what it
proves.
"""

from __future__ import annotations

import argparse
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.ecological_balance import ecological_region_label
from abm_governance.simulation import Simulation

REGION_COLORS = {
    "supply_dominant": "tab:green",
    "boundary": "tab:orange",
    "demand_dominant": "tab:red",
    "depleted": "tab:brown",
    "unknown": "tab:gray",
}


# ---------------------------------------------------------------------
# Figure 1: ecological phase map (supplemental regular grid heatmap)
# ---------------------------------------------------------------------
def fig_phase_map(sweep_dir: str, out_path: str) -> str | None:
    path = os.path.join(sweep_dir, "grid_summary.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    regen_vals = sorted(df["environment_regen_rate"].unique())
    subs_vals = sorted(df["subsistence_cost"].unique())
    grid = np.full((len(subs_vals), len(regen_vals)), np.nan)
    for i, s in enumerate(subs_vals):
        for j, r in enumerate(regen_vals):
            row = df[(df["subsistence_cost"] == s) & (df["environment_regen_rate"] == r)]
            if len(row):
                grid[i, j] = row.iloc[0]["mean_occupancy_mean"]

    fig, ax = plt.subplots(figsize=(8, 6.5))
    im = ax.imshow(grid, origin="lower", aspect="auto", cmap="YlGnBu", vmin=0, vmax=1)
    ax.set_xticks(range(len(regen_vals)))
    ax.set_xticklabels([f"{v:.2f}" for v in regen_vals], rotation=45)
    ax.set_yticks(range(len(subs_vals)))
    ax.set_yticklabels([f"{v:.2f}" for v in subs_vals])
    ax.set_xlabel("environment_regen_rate")
    ax.set_ylabel("subsistence_cost")
    n_seeds = int(df["n_seeds"].iloc[0]) if len(df) else 0
    ax.set_title(
        f"Ecological phase map: mean pool occupancy\nby regen rate and subsistence cost\n"
        f"(regular grid, n={n_seeds} seeds/cell, other params\nat Stage-1 sampling midpoints)",
        fontsize=10,
    )
    fig.colorbar(im, ax=ax, label="mean environment_fraction_of_capacity across the run")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 2: pool occupancy / unmet demand by ecological region
# ---------------------------------------------------------------------
def fig_occupancy_unmet_demand(sweep_dir: str, out_path: str) -> str | None:
    path = os.path.join(sweep_dir, "stage1_summary.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    labels = [
        ecological_region_label(row["mean_occupancy_mean"], row["mean_b_t_realized_mean"])
        for _, row in df.iterrows()
    ]
    df = df.assign(region_label=labels)

    fig, ax = plt.subplots(figsize=(8, 6))
    for label, group in df.groupby("region_label"):
        ax.errorbar(
            group["mean_occupancy_mean"], group["fraction_time_depleted_mean"],
            xerr=group["mean_occupancy_std"], yerr=group["fraction_time_depleted_std"],
            fmt="o", label=label, color=REGION_COLORS.get(label, "black"), alpha=0.8, capsize=2,
        )
    ax.set_xlabel("mean pool occupancy across the run (fraction of capacity; error bars = seed std)")
    ax.set_ylabel("fraction of run steps at/below the depletion-occupancy threshold (seed std)")
    ax.set_title(
        "Stage-1 coarse sweep: mean occupancy vs. fraction of time depleted,\n"
        "per parameter point, coloured by observer-side ecological region label\n"
        "(n=10 seeds/point; labels are descriptive, not governance categories)"
    )
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 3: active/distressed/dormant/nonviable populations over time
# (fresh trajectory runs: this is the only way to get a full time series
# of population-state composition, which the sweep only ever aggregated).
# ---------------------------------------------------------------------
def fig_population_states(sweep_dir: str, out_path: str, n_seeds: int = 15, n_steps: int = 200) -> str | None:
    manifest_path = os.path.join(sweep_dir, "sweep_manifest.json")
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    boundary_points = manifest["boundary_points_selected"]
    if not boundary_points:
        return None
    params = boundary_points[0]["params"]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, viability_mode in zip(axes, ["dormancy_recovery", "removal_replacement"]):
        series = {"active": [], "distressed": [], "dormant": []}
        for seed in range(n_seeds):
            config = SimulationConfig(
                population_size=30, n_steps=n_steps, seed=seed, mean_degree=4,
                ecology_enabled=True, relationship_dynamics_enabled=True,
                payoff_punishment=1.0, payoff_sucker=0.0, environment_initial_fraction=0.5,
                viability_mode=viability_mode, viability_deficit_steps_threshold=10,
                viability_max_dormant_steps=15, fitness_mode="cumulative_resources",
                **params,
            )
            result = Simulation(config).run()
            for key in series:
                series[key].append([r[f"{key}_population"] for r in result.metrics])
        steps = np.arange(n_steps)
        for key, color in zip(series, ["tab:green", "tab:orange", "tab:red"]):
            arr = np.array(series[key])
            q10, q50, q90 = np.quantile(arr, [0.1, 0.5, 0.9], axis=0)
            ax.plot(steps, q50, color=color, label=key)
            ax.fill_between(steps, q10, q90, color=color, alpha=0.15)
        ax.set_title(f"viability_mode={viability_mode}")
        ax.set_xlabel("step")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel(f"agent count (median, 10-90th pct band; n={n_seeds} seeds)")
    axes[0].legend(fontsize=8)
    fig.suptitle(
        "Population viability-state composition over time at the boundary ecological\n"
        "region (fresh trajectory runs, not re-plotted from the sweep aggregate)"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 4: conditional vs. unconditional cooperation by ecological region
# ---------------------------------------------------------------------
def fig_conditional_vs_unconditional(null_model_dir: str, out_path: str) -> str | None:
    path = os.path.join(null_model_dir, "null_model_summary.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    subset = df[(df["slice"] == "region_x_fitness_mode") & (df["factor_value"] == "cumulative_resources")]
    if not len(subset):
        return None
    subset = subset.sort_values("mean_occupancy_mean")

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(subset))
    width = 0.35
    ax.bar(x - width / 2, subset["conditional_cooperation_rate_mean"], width, yerr=subset["conditional_cooperation_rate_std"],
           label="conditional on interaction (legacy metric)", color="tab:blue", capsize=3)
    ax.bar(x + width / 2, subset["unconditional_cooperation_rate_mean"], width, yerr=subset["unconditional_cooperation_rate_std"],
           label="unconditional per opportunity", color="tab:red", capsize=3)
    ax.set_xticks(x)
    ax.set_xticklabels(subset["region"])
    ax.set_ylabel("cooperation rate (mean +- std across n=15 seeds)")
    ax.set_ylim(0, 1.05)
    ax.set_title(
        "Conditional vs. unconditional cooperation by ecological region\n"
        "(fitness_mode=cumulative_resources, viability_mode=none; a large gap\n"
        "indicates the conditional metric is inflated by selective participation)"
    )
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 5: outcomes by fitness mode, faceted by region
# ---------------------------------------------------------------------
def fig_outcomes_by_fitness_mode(null_model_dir: str, out_path: str) -> str | None:
    path = os.path.join(null_model_dir, "null_model_summary.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    subset = df[df["slice"] == "region_x_fitness_mode"]
    if not len(subset):
        return None
    regions = sorted(subset["region"].unique())
    modes = ["cumulative_resources", "recent_payoff", "resource_delta", "viability_adjusted"]

    fig, axes = plt.subplots(1, len(regions), figsize=(5 * len(regions), 5), sharey=True)
    if len(regions) == 1:
        axes = [axes]
    for ax, region in zip(axes, regions):
        rows = subset[subset["region"] == region].set_index("factor_value").reindex(modes)
        ax.bar(modes, rows["conditional_cooperation_rate_mean"], yerr=rows["conditional_cooperation_rate_std"], capsize=3, color="tab:purple")
        ax.set_title(region)
        ax.set_xticks(range(len(modes)))
        ax.set_xticklabels(modes, rotation=30, ha="right", fontsize=8)
        ax.grid(alpha=0.3, axis="y")
    axes[0].set_ylabel("conditional cooperation rate (mean +- std, n=15 seeds)")
    axes[0].set_ylim(0, 1.05)
    fig.suptitle("Cooperation outcome by imitation fitness-signal mode, faceted by ecological region")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 6: outcomes by viability mode (at the boundary region)
# ---------------------------------------------------------------------
def fig_outcomes_by_viability_mode(null_model_dir: str, out_path: str) -> str | None:
    path = os.path.join(null_model_dir, "null_model_summary.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    subset = df[df["slice"] == "viability_mode_x_fitness_mode"].copy()
    if not len(subset):
        return None
    subset[["viability_mode", "fitness_mode"]] = subset["factor_value"].str.split("|", expand=True)
    modes = ["none", "dormancy_recovery", "removal_replacement"]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for fm, color in zip(["cumulative_resources", "resource_delta"], ["tab:blue", "tab:green"]):
        rows = subset[subset["fitness_mode"] == fm].set_index("viability_mode").reindex(modes)
        axes[0].plot(modes, rows["conditional_cooperation_rate_mean"], marker="o", label=fm, color=color)
        axes[0].fill_between(
            modes,
            rows["conditional_cooperation_rate_mean"] - rows["conditional_cooperation_rate_std"],
            rows["conditional_cooperation_rate_mean"] + rows["conditional_cooperation_rate_std"],
            alpha=0.15, color=color,
        )
        axes[1].plot(modes, rows["total_removals_mean"], marker="o", label=fm, color=color)
    axes[0].set_ylabel("conditional cooperation rate (mean +- std, n=15 seeds)")
    axes[0].set_title("Cooperation by viability mode")
    axes[0].set_ylim(0, 1.05)
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3)
    axes[1].set_ylabel("mean agent removals per run (n=15 seeds)")
    axes[1].set_title("Removals by viability mode\n(0 by construction for viability_mode=none/dormancy_recovery)")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.3)
    fig.suptitle("Outcomes by viability mode at the boundary ecological region")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 7: policy diversity by ecological region
# ---------------------------------------------------------------------
def fig_policy_diversity_by_region(null_model_dir: str, out_path: str) -> str | None:
    path = os.path.join(null_model_dir, "null_model_summary.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    subset = df[(df["slice"] == "region_x_fitness_mode") & (df["factor_value"] == "cumulative_resources")]
    if not len(subset):
        return None
    subset = subset.sort_values("mean_occupancy_mean")

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(subset["region"], subset["final_policy_diversity_bits_mean"], yerr=subset["final_policy_diversity_bits_std"], capsize=4, color="tab:cyan")
    ax.set_ylabel("final-step policy diversity (Shannon entropy, bits; mean +- std, n=15 seeds)")
    ax.set_title("Behavioural-policy diversity at run end, by ecological region\n(fitness_mode=cumulative_resources)")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 8: relationship turnover near the phase boundary
# ---------------------------------------------------------------------
def fig_turnover_near_boundary(turnover_dir: str, out_path: str) -> str | None:
    path = os.path.join(turnover_dir, "turnover_boundary_summary.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    axes_to_plot = ["exit_cost", "search_cost", "connection_accept_base_prob", "mean_degree"]
    boundary_points = sorted(df["boundary_point_id"].unique())

    fig, axes = plt.subplots(1, len(axes_to_plot), figsize=(4.5 * len(axes_to_plot), 5), sharey=True)
    for ax, axis in zip(axes, axes_to_plot):
        for bp, color in zip(boundary_points, ["tab:blue", "tab:orange"]):
            rows = df[(df["axis"] == axis) & (df["boundary_point_id"] == bp)].sort_values("value")
            ax.errorbar(rows["value"], rows["relationship_turnover_rate_mean"], yerr=rows["relationship_turnover_rate_std"],
                        marker="o", label=bp, color=color, capsize=3)
        ax.set_title(axis)
        ax.set_xlabel(axis)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("relationship turnover rate (mean +- std, n=10 seeds)")
    axes[0].legend(fontsize=8)
    fig.suptitle(
        "Relationship turnover across one-axis-at-a-time local sweeps,\n"
        "at each selected ecological boundary region"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------
# Figure 9: boundary perturbation / recovery trajectories (fresh runs)
# ---------------------------------------------------------------------
def fig_boundary_perturbation_trajectories(sweep_dir: str, out_path: str, n_seeds: int = 20) -> str | None:
    manifest_path = os.path.join(sweep_dir, "sweep_manifest.json")
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    boundary_points = manifest["boundary_points_selected"]
    if not boundary_points:
        return None

    pre, dur, post = 100, 20, 150
    n_steps = pre + dur + post

    fig, axes = plt.subplots(1, len(boundary_points), figsize=(7 * len(boundary_points), 5), sharey=True)
    if len(boundary_points) == 1:
        axes = [axes]
    for ax, bp in zip(axes, boundary_points):
        params, point_id = bp["params"], bp["point_id"]
        # Plot the shocked condition first, unperturbed control last (drawn
        # on top, dashed): pre-shock steps use identical seeds and consume
        # no extra RNG draws before the shock fires, so the two conditions'
        # trajectories are bit-identical up to the shock window by
        # construction (see core/perturbation.py) — drawing the control
        # last, dashed, and thicker keeps it visible wherever the two *do*
        # diverge, instead of being silently hidden under the shocked
        # condition's solid line and band.
        for shock_kind, color, style, lw, z in [
            ("resource_depletion", "tab:red", "-", 1.5, 2),
            ("none", "tab:gray", "--", 2.2, 3),
        ]:
            traj = []
            for seed in range(n_seeds):
                kwargs = dict(
                    population_size=30, n_steps=n_steps, seed=seed, mean_degree=4,
                    ecology_enabled=True, relationship_dynamics_enabled=True,
                    payoff_punishment=1.0, payoff_sucker=0.0, environment_initial_fraction=0.5,
                    viability_mode="none", fitness_mode="cumulative_resources",
                    **params,
                )
                if shock_kind != "none":
                    kwargs["perturbations"] = ({"start_step": pre, "duration": dur, "kind": shock_kind, "magnitude": 0.6},)
                result = Simulation(SimulationConfig(**kwargs)).run()
                traj.append([r["environment_fraction_of_capacity"] for r in result.metrics])
            arr = np.array(traj)
            steps = np.arange(n_steps)
            q10, q50, q90 = np.quantile(arr, [0.1, 0.5, 0.9], axis=0)
            label = "unperturbed control" if shock_kind == "none" else f"{shock_kind} shock"
            ax.plot(steps, q50, color=color, label=label, linestyle=style, linewidth=lw, zorder=z)
            ax.fill_between(steps, q10, q90, color=color, alpha=0.15, zorder=z - 1)
        ax.axvspan(pre, pre + dur, color="black", alpha=0.08, label="shock window")
        ax.set_xlabel("step")
        ax.set_title(point_id)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel(f"pool occupancy (fraction of capacity; median, 10-90th pct band, n={n_seeds} seeds)")
    fig.suptitle(
        "Pool occupancy trajectory around a shock, at each selected boundary region\n"
        "(fresh trajectory runs; identical seeds pre-shock by construction; "
        "no claim of recovery is made unless observed)"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def fig_cooperation_ecology_causality(causality_dir: str, out_path: str) -> str | None:
    cs_path = os.path.join(causality_dir, "cross_sectional_by_point.csv")
    pooled_path = os.path.join(causality_dir, "pooled_confounded_correlation.json")
    lag_path = os.path.join(causality_dir, "time_lagged_summary.csv")
    if not (os.path.exists(cs_path) and os.path.exists(pooled_path)):
        return None
    cross_sectional = pd.read_csv(cs_path)
    with open(pooled_path, "r", encoding="utf-8") as fh:
        pooled = json.load(fh)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    ax = axes[0]
    within = cross_sectional["pearson_coop_vs_mean_occupancy"].dropna().to_numpy()
    ax.hist(within, bins=15, color="tab:blue", alpha=0.75, label="within-point (across seeds,\nparameters held fixed)")
    ax.axvline(0.0, color="black", linewidth=1, linestyle=":")
    ax.axvline(
        pooled.get("pooled_pearson_coop_vs_mean_occupancy", float("nan")),
        color="tab:red", linewidth=2, linestyle="--",
        label="pooled across points\n(confounded by parameters)",
    )
    ax.set_xlabel("Pearson r(final cooperation, mean pool occupancy)")
    ax.set_ylabel(f"count of phase-sweep points (n={len(within)})")
    ax.set_title("Cooperation-occupancy association:\nwithin-point vs. pooled-across-points")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    ax = axes[1]
    if os.path.exists(lag_path):
        lag_df = pd.read_csv(lag_path)
        regions = lag_df["region"].tolist()
        level_means = lag_df["coop_conditional_vs_occupancy_level_best_corr_mean"].to_numpy()
        level_stds = lag_df["coop_conditional_vs_occupancy_level_best_corr_std"].to_numpy()
        diff_means = lag_df["coop_conditional_vs_occupancy_diff_best_corr_mean"].to_numpy()
        diff_stds = lag_df["coop_conditional_vs_occupancy_diff_best_corr_std"].to_numpy()
        x = np.arange(len(regions))
        width = 0.35
        ax.bar(x - width / 2, level_means, width, yerr=level_stds, label="raw level", color="tab:gray", capsize=3)
        ax.bar(x + width / 2, diff_means, width, yerr=diff_stds, label="first-differenced\n(trend removed)", color="tab:purple", capsize=3)
        ax.axhline(0.0, color="black", linewidth=1)
        ax.set_xticks(x)
        ax.set_xticklabels(regions)
        ax.set_ylabel("best-lag correlation\n(mean ± std across seeds)")
        ax.set_title("Cooperation-occupancy lag correlation\nby ecological region")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3, axis="y")
    else:
        ax.axis("off")

    fig.suptitle(
        "Cooperation and ecological state: association strength does not by itself indicate\n"
        "which (if either) drives the other, and the pooled figure is a parameter confound"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sweep-dir", type=str, default="outputs/phase_sweep_level02")
    parser.add_argument("--boundary-perturbation-dir", type=str, default="outputs/boundary_perturbation_level02")
    parser.add_argument("--turnover-dir", type=str, default="outputs/turnover_boundary_level02")
    parser.add_argument("--null-model-dir", type=str, default="outputs/null_model_comparisons_level02")
    parser.add_argument("--causality-dir", type=str, default="outputs/cooperation_ecology_causality_level02")
    parser.add_argument("--out", type=str, default="outputs/figures_level02")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    results = {}
    results["01_ecological_phase_map"] = fig_phase_map(args.sweep_dir, os.path.join(args.out, "01_ecological_phase_map.png"))
    results["02_occupancy_unmet_demand_by_phase"] = fig_occupancy_unmet_demand(
        args.sweep_dir, os.path.join(args.out, "02_occupancy_unmet_demand_by_phase.png")
    )
    results["03_population_states_over_time"] = fig_population_states(
        args.sweep_dir, os.path.join(args.out, "03_population_states_over_time.png")
    )
    results["04_conditional_vs_unconditional_cooperation"] = fig_conditional_vs_unconditional(
        args.null_model_dir, os.path.join(args.out, "04_conditional_vs_unconditional_cooperation.png")
    )
    results["05_outcomes_by_fitness_mode"] = fig_outcomes_by_fitness_mode(
        args.null_model_dir, os.path.join(args.out, "05_outcomes_by_fitness_mode.png")
    )
    results["06_outcomes_by_viability_mode"] = fig_outcomes_by_viability_mode(
        args.null_model_dir, os.path.join(args.out, "06_outcomes_by_viability_mode.png")
    )
    results["07_policy_diversity_by_region"] = fig_policy_diversity_by_region(
        args.null_model_dir, os.path.join(args.out, "07_policy_diversity_by_region.png")
    )
    results["08_turnover_near_boundary"] = fig_turnover_near_boundary(
        args.turnover_dir, os.path.join(args.out, "08_turnover_near_boundary.png")
    )
    results["09_boundary_perturbation_trajectories"] = fig_boundary_perturbation_trajectories(
        args.sweep_dir, os.path.join(args.out, "09_boundary_perturbation_trajectories.png")
    )
    results["10_cooperation_ecology_causality"] = fig_cooperation_ecology_causality(
        args.causality_dir, os.path.join(args.out, "10_cooperation_ecology_causality.png")
    )

    for name, path in results.items():
        status = "OK" if path else "SKIPPED (missing input data)"
        print(f"[make_level02_visualizations] {name}: {status}")
    return 0


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    raise SystemExit(main())
