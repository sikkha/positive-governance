#!/usr/bin/env python3
"""Level 0.1 ensemble visualizations (milestone brief's visualization
requirements): multi-seed cooperation bands, environment+agent resources,
policy diversity over time, relationship-turnover/component structure,
punishment confusion-matrix rates, and ablation outcome distributions.

Reads exclusively from a completed ``experiments/ensemble.py`` output
directory (trajectory CSVs, endpoint_summary.csv, confusion_matrix_summary
.csv, manifest.json) — it re-plots existing aggregated results, it does
not re-run any simulations. Every axis is labeled with its unit/meaning
and its denominator where relevant, per the milestone brief.

Usage:
    python experiments/make_visualizations.py --ensemble-dir outputs/ensemble_level01
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

BASELINE_CONDITIONS = ["original_compat", "ecologically_closed", "closed_ecology_turnover"]
BASELINE_LABELS = {
    "original_compat": "Original compat mode (Level 0)",
    "ecologically_closed": "Ecologically closed (0.1, no rel. dynamics)",
    "closed_ecology_turnover": "Closed ecology + relationship turnover (0.1 default)",
}
COLORS = {
    "original_compat": "tab:blue",
    "ecologically_closed": "tab:orange",
    "closed_ecology_turnover": "tab:green",
}

CONFUSION_RATE_KEYS = [
    ("p_punishment_given_actual_defection_mean", "P(punish | actually defected)\n[TP / (TP+FN)]"),
    ("p_punishment_given_actual_cooperation_mean", "P(punish | actually cooperated)\n[FP / (FP+TN)]  <- false-positive rate"),
    ("p_perceived_defection_given_actual_cooperation_mean", "P(perceived defect | actually cooperated)"),
    ("p_perceived_cooperation_given_actual_defection_mean", "P(perceived cooperate | actually defected)"),
    ("p_punishment_given_perceived_defection_mean", "P(punish | perceived defection)"),
]


def _load_trajectory(ensemble_dir: str, condition: str) -> pd.DataFrame | None:
    path = os.path.join(ensemble_dir, "trajectories", f"{condition}.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


def plot_cooperation_bands(ensemble_dir: str, out_path: str) -> str | None:
    fig, ax = plt.subplots(figsize=(9, 5))
    plotted = False
    for condition in BASELINE_CONDITIONS:
        df = _load_trajectory(ensemble_dir, condition)
        if df is None:
            continue
        plotted = True
        color = COLORS[condition]
        ax.plot(df["step"], df["cooperation_rate_q50"], color=color, label=BASELINE_LABELS[condition], linewidth=1.5)
        ax.fill_between(df["step"], df["cooperation_rate_q10"], df["cooperation_rate_q90"], color=color, alpha=0.15)
    if not plotted:
        plt.close(fig)
        return None
    ax.set_xlabel("simulation step")
    ax.set_ylabel("cooperation rate\n(fraction of interaction-actions that were Cooperate, this step)")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title("Cooperation rate across seeds (median, 10th-90th pct band; n=30 seeds/condition)")
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_resources(ensemble_dir: str, out_path: str) -> str | None:
    fig, axes = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
    plotted = False
    for condition in BASELINE_CONDITIONS:
        df = _load_trajectory(ensemble_dir, condition)
        if df is None:
            continue
        plotted = True
        color = COLORS[condition]
        if "environment_resources_q50" in df:
            axes[0].plot(df["step"], df["environment_resources_q50"], color=color, label=BASELINE_LABELS[condition])
            axes[0].fill_between(
                df["step"], df["environment_resources_q10"], df["environment_resources_q90"], color=color, alpha=0.15
            )
        axes[1].plot(df["step"], df["mean_resources_q50"], color=color, label=BASELINE_LABELS[condition])
        axes[1].fill_between(df["step"], df["mean_resources_q10"], df["mean_resources_q90"], color=color, alpha=0.15)
    if not plotted:
        plt.close(fig)
        return None
    axes[0].set_ylabel("shared environment pool\n(resource units; NaN/absent in compat mode)")
    axes[0].set_title("Environment resource pool and agent mean resources across seeds (median, 10-90th pct band)")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3)
    axes[1].set_ylabel("mean agent resources\n(resource units, across living agents)")
    axes[1].set_xlabel("simulation step")
    axes[1].axhline(0, color="black", linewidth=0.6, linestyle="--")
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_policy_diversity(ensemble_dir: str, out_path: str) -> str | None:
    fig, ax = plt.subplots(figsize=(9, 5))
    plotted = False
    for condition in BASELINE_CONDITIONS:
        df = _load_trajectory(ensemble_dir, condition)
        if df is None:
            continue
        plotted = True
        color = COLORS[condition]
        ax.plot(df["step"], df["policy_diversity_bits_q50"], color=color, label=BASELINE_LABELS[condition])
        ax.fill_between(
            df["step"], df["policy_diversity_bits_q10"], df["policy_diversity_bits_q90"], color=color, alpha=0.15
        )
    if not plotted:
        plt.close(fig)
        return None
    ax.set_xlabel("simulation step")
    ax.set_ylabel("policy diversity\n(Shannon entropy, base-2 bits, over living agents' policy names)")
    ax.set_title("Behavioural-policy diversity across seeds (median, 10-90th pct band)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_network_structure(ensemble_dir: str, out_path: str) -> str | None:
    fig, axes = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
    plotted = False
    for condition in BASELINE_CONDITIONS:
        df = _load_trajectory(ensemble_dir, condition)
        if df is None:
            continue
        plotted = True
        color = COLORS[condition]
        axes[0].plot(df["step"], df["largest_component_share_q50"], color=color, label=BASELINE_LABELS[condition])
        axes[1].plot(df["step"], df["isolated_agent_count_q50"], color=color, label=BASELINE_LABELS[condition])
    if not plotted:
        plt.close(fig)
        return None
    axes[0].set_ylabel("largest connected component\n(fraction of all agents, median across seeds)")
    axes[0].set_ylim(-0.02, 1.02)
    axes[0].set_title("Network structure across seeds (median)")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3)
    axes[1].set_ylabel("isolated agents\n(count with degree 0, median across seeds)")
    axes[1].set_xlabel("simulation step")
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_confusion_matrix_rates(ensemble_dir: str, out_path: str) -> str | None:
    path = os.path.join(ensemble_dir, "confusion_matrix_summary.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    conditions = list(df["condition"])
    n_cond = len(conditions)
    n_rate = len(CONFUSION_RATE_KEYS)
    x = np.arange(n_cond)
    width = 0.8 / n_rate

    fig, ax = plt.subplots(figsize=(13, 6))
    for i, (key, label) in enumerate(CONFUSION_RATE_KEYS):
        values = df[key].to_numpy(dtype=float)
        ax.bar(x + i * width - 0.4 + width / 2, np.nan_to_num(values, nan=0.0), width=width, label=label)
        # Mark NaN (undefined, zero-denominator) bars explicitly rather
        # than silently plotting them as 0.
        for xi, v in zip(x + i * width - 0.4 + width / 2, values):
            if np.isnan(v):
                ax.text(xi, 0.01, "NaN", ha="center", va="bottom", fontsize=6, rotation=90, color="red")

    ax.set_xticks(x)
    ax.set_xticklabels(conditions, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("conditional probability (mean across seeds; explicit denominator per legend entry)")
    ax.set_title("Enforcement confusion-matrix conditional rates by condition (n=30 seeds each; NaN = zero denominator)")
    ax.legend(fontsize=7, loc="upper right")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_ablation_outcomes(ensemble_dir: str, out_path: str, column: str = "cooperation_rate") -> str | None:
    manifest_path = os.path.join(ensemble_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path) as fh:
        manifest = json.load(fh)

    by_condition: dict[str, list[float]] = {}
    for r in manifest["runs"]:
        if r["status"] != "ok":
            continue
        by_condition.setdefault(r["condition"], []).append(r["final_metrics"].get(column, float("nan")))

    order = [c for c in by_condition if c not in BASELINE_CONDITIONS]
    order = BASELINE_CONDITIONS + sorted(order)
    data = [np.array([v for v in by_condition.get(c, []) if v == v]) for c in order]

    fig, ax = plt.subplots(figsize=(12, 6))
    bp = ax.boxplot(data, tick_labels=order, showmeans=True)
    for i, c in enumerate(order):
        if c in COLORS:
            bp["boxes"][i].set_color(COLORS[c])
    ax.set_xticklabels(order, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel(f"final-step {column}\n(one point per seed, n=30 seeds/condition; box=IQR, whiskers=1.5xIQR)")
    ax.set_title(f"Ablation comparison: distribution of final-step {column} across seeds")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def make_all(ensemble_dir: str) -> dict[str, str]:
    fig_dir = os.path.join(ensemble_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)
    outputs: dict[str, str] = {}

    jobs = [
        ("cooperation_bands", lambda: plot_cooperation_bands(ensemble_dir, os.path.join(fig_dir, "cooperation_bands.png"))),
        ("resources", lambda: plot_resources(ensemble_dir, os.path.join(fig_dir, "resources.png"))),
        ("policy_diversity", lambda: plot_policy_diversity(ensemble_dir, os.path.join(fig_dir, "policy_diversity.png"))),
        ("network_structure", lambda: plot_network_structure(ensemble_dir, os.path.join(fig_dir, "network_structure.png"))),
        (
            "confusion_matrix_rates",
            lambda: plot_confusion_matrix_rates(ensemble_dir, os.path.join(fig_dir, "confusion_matrix_rates.png")),
        ),
        (
            "ablation_outcomes_cooperation",
            lambda: plot_ablation_outcomes(
                ensemble_dir, os.path.join(fig_dir, "ablation_outcomes_cooperation.png"), "cooperation_rate"
            ),
        ),
        (
            "ablation_outcomes_resources",
            lambda: plot_ablation_outcomes(
                ensemble_dir, os.path.join(fig_dir, "ablation_outcomes_resources.png"), "mean_resources"
            ),
        ),
    ]
    for name, job in jobs:
        path = job()
        if path:
            outputs[name] = path
    return outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ensemble-dir", type=str, default="outputs/ensemble_level01")
    args = parser.parse_args()
    result = make_all(args.ensemble_dir)
    for name, path in result.items():
        print(f"[make_visualizations] {name}: {path}")
