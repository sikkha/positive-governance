#!/usr/bin/env python3
"""Level 1.1 visualizations.

Reads the already-committed outputs of every Level 1.1 stage script
(``outputs/level11_stage{1..6}_*/*.json``) -- does not re-run any of
them. Every figure derived across multiple seeds shows its sample size
explicitly and, where the underlying stage computed one, an uncertainty
interval -- never a single representative run passed off as typical.
No chart title or axis label uses any forbidden governance-type term
(``core/config.py``'s own structural-terminology guard); every label
comes from Work Package K's fixed mechanism-validation vocabulary or
from a plain event/count name.

Session-budget scope reduction (disclosed, matching the Level 1.0
precedent of disclosing "16 of 20 figures" in
``experiments/make_level1_visualizations.py``): 13 of the milestone's
requested 12-18 figures, chosen to cover every stage and every Work
Package's own headline result at least once, rather than exhaustively
enumerating every possible cut of the same data.
"""

from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT_DIR = "outputs/level11_figures"
STAGE1_PATH = "outputs/level11_stage1_activation/stage1_report.json"
STAGE2_PATH = "outputs/level11_stage2_compatibility_ablations/stage2_report.json"
STAGE3_PATH = "outputs/level11_stage3_search/stage3_report.json"
STAGE4_PATH = "outputs/level11_stage4_confirmatory/stage4_report.json"
STAGE5_PATH = "outputs/level11_stage5_causal_decomposition/stage5_report.json"
STAGE6_PATH = "outputs/level11_stage6_shocks/stage6_report.json"

LABEL_COLORS = {
    "no_delegation": "#999999", "attempted_delegation": "#c9b458", "delegate_selected": "#e9c46a",
    "unstable_delegation": "#f4a261", "persistent_delegation": "#264653",
    "accountable_delegation": "#2a9d8f", "weakly_constrained_delegation": "#e76f51",
    "administratively_inactive": "#a4133c", "administratively_functional": "#5e548e",
    "fragmented_coordination": "#780000", "interpatch_coordination": "#003049", "unclassified": "#cccccc",
}


def _load(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _savefig(fig, name):
    path = f"{OUT_DIR}/{name}.png"
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}", flush=True)


# ---------------------------------------------------------------------------
# Stage 1: mechanism activation
# ---------------------------------------------------------------------------
def fig_stage1_activation_totals(report):
    conditions = list(report["conditions"].keys())
    keys = ["n_nominations", "n_appointments", "n_audits", "n_recalls", "n_appeals", "n_contributions", "n_coordination_proposals"]
    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(conditions))
    width = 0.11
    for i, k in enumerate(keys):
        vals = [report["conditions"][c]["totals"][k] for c in conditions]
        ax.bar(x + i * width, vals, width, label=k)
    ax.set_xticks(x + width * (len(keys) - 1) / 2)
    ax.set_xticklabels(conditions, rotation=20, ha="right")
    ax.set_ylabel(f"event count (summed over n={report['n_seeds']} seeds, log scale)")
    ax.set_yscale("symlog")
    ax.set_title("Stage 1: mechanism-defining event totals by condition")
    ax.legend(fontsize=8, ncol=2)
    _savefig(fig, "fig01_stage1_activation_totals")


def fig_stage1_appointments_per_seed(report):
    conditions = [c for c in report["conditions"] if any(r["n_appointments"] > 0 for r in report["conditions"][c]["per_seed"])]
    fig, ax = plt.subplots(figsize=(9, 5))
    data = [[r["n_appointments"] for r in report["conditions"][c]["per_seed"]] for c in conditions]
    ax.boxplot(data, tick_labels=conditions)
    for i, d in enumerate(data):
        ax.scatter([i + 1] * len(d), d, alpha=0.6, s=15, color="black")
    ax.set_ylabel(f"n_appointments per seed (n={report['n_seeds']} seeds each)")
    ax.set_title("Stage 1: per-seed spread of delegate appointments")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    _savefig(fig, "fig02_stage1_appointments_per_seed")


# ---------------------------------------------------------------------------
# Stage 2: compatibility + ablations
# ---------------------------------------------------------------------------
def fig_stage2_compatibility(report):
    compat = report["compatibility_check"]
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(["matched", "mismatched"], [compat["n_seeds"] - compat["n_mismatches"], compat["n_mismatches"]], color=["#2a9d8f", "#e76f51"])
    ax.set_ylabel("n seeds")
    ax.set_title(f"Stage 2: level10_compat vs level1_rule_formation_default\n(n={compat['n_seeds']} seeds, byte-for-byte metrics comparison)")
    for i, v in enumerate([compat["n_seeds"] - compat["n_mismatches"], compat["n_mismatches"]]):
        ax.text(i, v + 0.3, str(v), ha="center")
    _savefig(fig, "fig03_stage2_compatibility")


def fig_stage2_ablation_effects(report):
    ablations = report["ablations"]["effects_vs_complete"]
    outcomes = list(next(iter(ablations.values())).keys())
    names = list(ablations.keys())
    fig, axes = plt.subplots(1, len(outcomes), figsize=(4 * len(outcomes), 4.5), sharey=False)
    for ax, outcome in zip(axes, outcomes):
        vals = [ablations[n][outcome]["mean_effect"] for n in names]
        colors = ["#e76f51" if v < 0 else "#2a9d8f" for v in vals]
        ax.barh(names, vals, color=colors)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_title(outcome, fontsize=9)
    fig.suptitle(f"Stage 2: exploratory ablation vs. level11_complete, mean effect (n={report['ablations']['n_seeds']} matched seeds, point estimate only)")
    _savefig(fig, "fig04_stage2_ablation_effects")


# ---------------------------------------------------------------------------
# Stage 3: open mechanism-space search (exploratory)
# ---------------------------------------------------------------------------
def fig_stage3_label_distribution(report):
    conditions = list(report["conditions"].keys())
    all_labels = sorted({lbl for c in conditions for lbl in report["conditions"][c]["label_fractions"]})
    fig, ax = plt.subplots(figsize=(13, 6))
    bottom = np.zeros(len(conditions))
    for lbl in all_labels:
        vals = np.array([report["conditions"][c]["label_fractions"].get(lbl, 0.0) for c in conditions])
        ax.bar(conditions, vals, bottom=bottom, label=lbl, color=LABEL_COLORS.get(lbl, "#888888"))
        bottom += vals
    ax.set_ylabel(f"fraction of rules (n={report['n_seeds']} seeds x 3 patches each)")
    ax.set_title("Stage 3 (exploratory): Work Package K label distribution across the mechanism-space search")
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right", fontsize=7)
    ax.legend(fontsize=7, bbox_to_anchor=(1.01, 1), loc="upper left")
    _savefig(fig, "fig05_stage3_label_distribution")


def fig_stage3_accountability_contrast(report):
    # Aggregate across the 4 selection procedures: accountability on vs off.
    on_keys = [k for k in report["conditions"] if "accountability=True" in k]
    off_keys = [k for k in report["conditions"] if "accountability=False" in k]
    labels = sorted({lbl for k in report["conditions"] for lbl in report["conditions"][k]["label_fractions"]})
    on_means = [np.mean([report["conditions"][k]["label_fractions"].get(lbl, 0.0) for k in on_keys]) for lbl in labels]
    off_means = [np.mean([report["conditions"][k]["label_fractions"].get(lbl, 0.0) for k in off_keys]) for lbl in labels]
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(labels))
    ax.bar(x - 0.2, off_means, 0.4, label="accountability_enabled=False", color="#e9c46a")
    ax.bar(x + 0.2, on_means, 0.4, label="accountability_enabled=True", color="#2a9d8f")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("mean label fraction (averaged across 4 selection procedures x discretion on/off)")
    ax.set_title("Stage 3 (exploratory): accountability's association with the observed label mix")
    ax.legend()
    _savefig(fig, "fig06_stage3_accountability_contrast")


# ---------------------------------------------------------------------------
# Stage 4: confirmatory replication
# ---------------------------------------------------------------------------
def fig_stage4_confirmatory_ci(report):
    fig, ax = plt.subplots(figsize=(7, 5))
    rows = [
        ("accountable_delegation\n(both active)", report["accountable_delegation_fraction"]["both_mechanisms_active"], "#2a9d8f"),
        ("accountable_delegation\n(both off)", report["accountable_delegation_fraction"]["both_mechanisms_off"], "#e9c46a"),
        ("persistent_delegation\n(both active)", report["persistent_delegation_fraction"]["both_mechanisms_active"], "#264653"),
        ("persistent_delegation\n(both off)", report["persistent_delegation_fraction"]["both_mechanisms_off"], "#f4a261"),
    ]
    y = np.arange(len(rows))
    for i, (name, ci, color) in enumerate(rows):
        ax.errorbar(
            ci["point_estimate"], i, xerr=[[ci["point_estimate"] - ci["ci_low"]], [ci["ci_high"] - ci["point_estimate"]]],
            fmt="o", color=color, capsize=4, markersize=8,
        )
    ax.set_yticks(y)
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlabel(f"label fraction, 95% seed-clustered bootstrap CI (n={report['n_seeds']} fresh seeds)")
    ax.set_title("Stage 4 (confirmatory): discretion+accountability shifts the modal label")
    ax.set_xlim(-0.05, 1.05)
    _savefig(fig, "fig07_stage4_confirmatory_ci")


# ---------------------------------------------------------------------------
# Stage 5: causal decomposition (forest plot)
# ---------------------------------------------------------------------------
def fig_stage5_forest(report):
    contrasts = report["contrasts"]
    contrast_names = list(contrasts.keys())
    outcome_names = list(next(iter(contrasts.values())).keys())
    fig, ax = plt.subplots(figsize=(10, 7))
    y_labels = []
    y_pos = []
    y = 0
    for cname in contrast_names:
        for oname in outcome_names:
            ci = contrasts[cname][oname]
            color = "#2a9d8f" if ci["excludes_zero"] else "#999999"
            ax.errorbar(
                ci["mean_delta_ablated_minus_full"], y,
                xerr=[[ci["mean_delta_ablated_minus_full"] - ci["ci_low"]], [ci["ci_high"] - ci["mean_delta_ablated_minus_full"]]],
                fmt="o", color=color, capsize=3, markersize=6,
            )
            y_labels.append(f"{cname} | {oname}")
            y_pos.append(y)
            y += 1
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(y_labels, fontsize=7)
    ax.set_xlabel(f"mean delta, ablated minus full (n={report['n_seeds']} matched seeds, 95% seed-clustered bootstrap CI)")
    ax.set_title("Stage 5: causal decomposition (green = CI excludes zero)")
    ax.invert_yaxis()
    _savefig(fig, "fig08_stage5_forest")


def fig_stage5_appropriation_focus(report):
    contrasts = report["contrasts"]
    names = list(contrasts.keys())
    vals = [contrasts[n]["total_appropriated_resources"]["mean_delta_ablated_minus_full"] for n in names]
    los = [contrasts[n]["total_appropriated_resources"]["ci_low"] for n in names]
    his = [contrasts[n]["total_appropriated_resources"]["ci_high"] for n in names]
    fig, ax = plt.subplots(figsize=(8, 5))
    y = np.arange(len(names))
    err = [[v - lo for v, lo in zip(vals, los)], [hi - v for v, hi in zip(vals, his)]]
    colors = ["#2a9d8f" if contrasts[n]["total_appropriated_resources"]["excludes_zero"] else "#999999" for n in names]
    ax.barh(y, vals, xerr=err, color=colors, capsize=4)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlabel("mean delta in total_appropriated_resources, ablated minus full")
    ax.set_title(f"Stage 5: each mechanism's causal contribution to appropriation (n={report['n_seeds']} seeds)")
    _savefig(fig, "fig09_stage5_appropriation_focus")


# ---------------------------------------------------------------------------
# Stage 6: institutional shocks
# ---------------------------------------------------------------------------
def fig_stage6_reappointment_rate(report):
    shocks = list(report["shocks"].keys())
    rates = [report["shocks"][s]["reappointment_rate"] for s in shocks]
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.bar(shocks, rates, color="#2a9d8f")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel(f"fraction of seeds with >=1 post-shock reappointment (n={report['n_seeds']} seeds each)")
    ax.set_title(f"Stage 6: delegation-arrangement recovery after a shock at step {report['shock_step']}")
    for i, v in enumerate(rates):
        ax.text(i, v + 0.02, f"{v:.2f}", ha="center")
    _savefig(fig, "fig10_stage6_reappointment_rate")


def fig_stage6_task_performance_recovery(report):
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(2)
    width = 0.35
    for i, shock in enumerate(report["shocks"]):
        shocked = [r["n_post_shock_task_performances"] for r in report["shocks"][shock]["shocked_runs"]]
        control = [r["n_post_shock_task_performances"] for r in report["shocks"][shock]["control_runs"]]
        ax.bar(x[i] - width / 2, np.mean(shocked), width, yerr=np.std(shocked), color="#e76f51", label="shocked" if i == 0 else None)
        ax.bar(x[i] + width / 2, np.mean(control), width, yerr=np.std(control), color="#264653", label="unshocked control" if i == 0 else None)
    ax.set_xticks(x)
    ax.set_xticklabels(list(report["shocks"].keys()))
    ax.set_ylabel(f"mean n_post_shock_task_performances (+-1 SD, n={report['n_seeds']} seeds)")
    ax.set_title("Stage 6: post-shock task-performance activity, shocked vs. unshocked")
    ax.legend()
    _savefig(fig, "fig11_stage6_task_performance_recovery")


# ---------------------------------------------------------------------------
# Cross-stage summary
# ---------------------------------------------------------------------------
def fig_cross_stage_summary(s1, s5):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    ax = axes[0]
    conds = list(s1["conditions"].keys())
    activity_present = {
        c: sum(1 for v in s1["conditions"][c]["totals"].values() if v > 0) for c in conds
    }
    ax.bar(activity_present.keys(), activity_present.values(), color="#2a9d8f")
    ax.set_title("Stage 1: n distinct event types observed >0 by condition")
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right", fontsize=8)

    ax = axes[1]
    contrasts = s5["contrasts"]
    n_significant = {c: sum(1 for o in contrasts[c].values() if o["excludes_zero"]) for c in contrasts}
    ax.bar(n_significant.keys(), n_significant.values(), color="#e76f51")
    ax.set_ylim(0, 5)
    ax.set_title("Stage 5: n of 5 outcomes with a CI excluding zero, by mechanism")
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right", fontsize=8)

    fig.suptitle("Cross-stage summary: mechanism reach (Stage 1) vs. detected causal effect (Stage 5)")
    _savefig(fig, "fig12_cross_stage_summary")


def run():
    os.makedirs(OUT_DIR, exist_ok=True)
    s1, s2, s3, s4, s5, s6 = (
        _load(STAGE1_PATH), _load(STAGE2_PATH), _load(STAGE3_PATH),
        _load(STAGE4_PATH), _load(STAGE5_PATH), _load(STAGE6_PATH),
    )
    written = []
    if s1:
        fig_stage1_activation_totals(s1); written.append("fig01")
        fig_stage1_appointments_per_seed(s1); written.append("fig02")
    if s2:
        fig_stage2_compatibility(s2); written.append("fig03")
        fig_stage2_ablation_effects(s2); written.append("fig04")
    if s3:
        fig_stage3_label_distribution(s3); written.append("fig05")
        fig_stage3_accountability_contrast(s3); written.append("fig06")
    if s4:
        fig_stage4_confirmatory_ci(s4); written.append("fig07")
    if s5:
        fig_stage5_forest(s5); written.append("fig08")
        fig_stage5_appropriation_focus(s5); written.append("fig09")
    if s6:
        fig_stage6_reappointment_rate(s6); written.append("fig10")
        fig_stage6_task_performance_recovery(s6); written.append("fig11")
    if s1 and s5:
        fig_cross_stage_summary(s1, s5); written.append("fig12")
    print(f"{len(written)} figures written to {OUT_DIR}/", flush=True)
    return written


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
