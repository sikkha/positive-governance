#!/usr/bin/env python3
"""Level 1.2 visualizations.

Reads the already-committed JSON outputs of every Level 1.2 stage
script (`outputs/level12_*/*.json`) -- does not re-run any of them, and
does not run any new simulation. No chart title or axis label uses any
of `tests/test_level12_structural_guards.py`'s
`FORBIDDEN_LEVEL12_TERMS` structural-terminology guard's forbidden
governance-type/SEM-trajectory vocabulary; every label is drawn from
`observer/institutional_viability.ALL_OUTCOME_LABELS` or a plain
event/count/rate/parameter name.

Session-budget scope reduction (disclosed, matching the Level 1.0/1.1/
1.1b precedent of disclosing fewer figures than a milestone's nominal
target): 10 of Section 19's suggested ~14-20 figures -- one per stage's
own clearest headline result, plus one cross-stage summary -- rather
than exhaustively enumerating every cut of every stage's data."""

from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT_DIR = "outputs/level12_figures"

PATHS = {
    "stage1": "outputs/level12_stage1_activation/stage1_report.json",
    "stage2": "outputs/level12_stage2_pilot/stage2_report.json",
    "stage3": "outputs/level12_stage3_main_search/stage3_report.json",
    "stage4": "outputs/level12_stage4_blind_discovery/stage4_report.json",
    "stage5": "outputs/level12_stage5_prospective_confirmation/stage5_report.json",
    "stage6": "outputs/level12_stage6_scaling_robustness/stage6_report.json",
    "stage13": "outputs/level12_stage13_causal_ablations/stage13_report.json",
}

#: Consistent color per outcome label across every figure.
OUTCOME_COLORS = {
    "no_institution": "#999999", "collapse": "#c0392b", "viable": "#27ae60",
    "persistent_extractive": "#e67e22", "fragmented": "#f1c40f", "transient": "#8e44ad",
    "unclassified": "#333333",
}


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


def fig_stage1_mechanism_activation(data):
    if data is None:
        return
    conditions = data["conditions"]
    counters = ["n_local_institution_observations", "n_institution_component_transmissions", "n_migrations", "n_membership_exits", "n_coordination_scale_changes"]
    labels = [c.replace("n_", "").replace("_", "\n") for c in counters]
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(counters))
    width = 0.8 / len(conditions)
    for i, (name, cond) in enumerate(conditions.items()):
        totals = [cond["totals"].get(c, 0) for c in counters]
        ax.bar(x + i * width, totals, width, label=name)
    ax.set_xticks(x + width * (len(conditions) - 1) / 2)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("event count (8 seeds, log scale)")
    ax.set_yscale("symlog")
    ax.set_title("Stage 1: mechanism activation -- each event type fires only under its own flag")
    ax.legend(fontsize=7, ncol=2)
    _savefig(fig, "01_stage1_mechanism_activation")


def fig_stage2_outcome_distribution(data):
    if data is None:
        return
    dist = data.get("outcome_label_distribution", {})
    fig, ax = plt.subplots(figsize=(5, 4))
    labels = list(dist.keys())
    ax.bar(labels, [dist[l] for l in labels], color=[OUTCOME_COLORS.get(l, "#555") for l in labels])
    ax.set_ylabel("n seeds (of 10)")
    ax.set_title("Stage 2: small open pilot -- outcome label distribution")
    _savefig(fig, "02_stage2_outcome_distribution")


def fig_stage3_regen_vs_ecology(data):
    if data is None:
        return
    records = data["records"]
    x = [r["parameters"]["patch_regen_rate"] for r in records]
    y = [r["ecological_resource_fraction"] for r in records]
    colors = [OUTCOME_COLORS.get(r["all_outcome_label"], "#555") for r in records]
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(x, y, c=colors, s=60, edgecolor="black", linewidth=0.5)
    ax.set_xlabel("patch_regen_rate (sampled)")
    ax.set_ylabel("ecological resource fraction at end of run")
    ax.set_title("Stage 3: main open search (n=24) -- descriptive, not a fitted claim")
    handles = [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=c, markersize=8, label=l) for l, c in OUTCOME_COLORS.items() if l in {r["all_outcome_label"] for r in records}]
    ax.legend(handles=handles, fontsize=8)
    _savefig(fig, "03_stage3_regen_rate_vs_ecological_fraction")


def fig_stage3_outcome_distribution(data):
    if data is None:
        return
    dist = data.get("outcome_label_distribution", {})
    fig, ax = plt.subplots(figsize=(5, 4))
    labels = list(dist.keys())
    ax.bar(labels, [dist[l] for l in labels], color=[OUTCOME_COLORS.get(l, "#555") for l in labels])
    ax.set_ylabel("n runs (of 24)")
    ax.set_title("Stage 3: main open search -- outcome distribution across an 8-D parameter sweep")
    _savefig(fig, "04_stage3_outcome_distribution")


def fig_stage4_criteria_pass_distribution(data):
    if data is None:
        return
    dist = data.get("criteria_pass_count_distribution", {})
    fig, ax = plt.subplots(figsize=(6, 4))
    ks = sorted(int(k) for k in dist.keys())
    ax.bar([str(k) for k in ks], [dist[str(k)] for k in ks], color="#2c3e50")
    ax.axvline(x=11.5, color="red", linestyle="--", linewidth=1, label="all 12 criteria (none reached)")
    ax.set_xlabel("n of 12 recurrence criteria passed")
    ax.set_ylabel("n candidate clusters (of 76)")
    ax.set_title("Stage 4: blind discovery -- no candidate meets all 12 criteria")
    ax.legend(fontsize=8)
    _savefig(fig, "05_stage4_criteria_pass_distribution")


def fig_stage4_vs_stage5_replication(stage4, stage5):
    if stage4 is None or stage5 is None:
        return
    rep = stage5.get("independent_replication", {})
    fig, ax = plt.subplots(figsize=(5, 4))
    labels = ["Stage 4\n(n=24 pool)", "Stage 5\n(n=12 fresh pool)"]
    passed = [stage4["n_candidates_meeting_all_12_criteria"], rep.get("n_candidates_meeting_all_12_criteria", 0)]
    total = [stage4["n_candidate_clusters_evaluated"], len(rep.get("candidates", []))]
    ax.bar(labels, total, color="#bdc3c7", label="candidates evaluated")
    ax.bar(labels, passed, color="#c0392b", label="met all 12 criteria")
    ax.set_ylabel("n candidate clusters")
    ax.set_title("Independent replication: null result holds on fresh data")
    ax.legend(fontsize=8)
    _savefig(fig, "06_stage4_vs_stage5_replication")


def fig_stage5_held_out_log_likelihood(data):
    if data is None:
        return
    ll_by_k = data.get("held_out_generalization", {}).get("held_out_log_likelihood_by_k", {})
    if not ll_by_k:
        return
    ks = sorted(int(k) for k in ll_by_k.keys())
    vals = [ll_by_k[str(k)] for k in ks]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(ks, vals, marker="o", color="#2980b9")
    ax.set_xlabel("k (GMM components, fit on Stage 3, scored on Stage 5)")
    ax.set_ylabel("held-out log-likelihood")
    ax.set_title("Held-out generalization degrades sharply beyond k=3\n(small-sample overfitting signature)")
    _savefig(fig, "07_stage5_held_out_log_likelihood")


def fig_stage6_scaling_grid(data):
    if data is None:
        return
    per_cond = data["per_condition"]
    fig, ax = plt.subplots(figsize=(6, 5))
    for cond in per_cond:
        label = f"pop={cond['population']}, patches={cond['n_patches']}"
        counts = cond["outcome_label_counts"]
        collapse_frac = counts.get("collapse", 0) / cond["seed_results"].__len__()
        ax.scatter(cond["population"], cond["n_patches"], s=800 * (1 - collapse_frac) + 200, c="#c0392b" if collapse_frac == 1.0 else "#27ae60", edgecolor="black")
        ax.annotate(f"{counts.get('collapse', 0)}/{len(cond['seed_results'])}\ncollapse", (cond["population"], cond["n_patches"]), textcoords="offset points", xytext=(0, 12), ha="center", fontsize=8)
    ax.set_xlabel("population")
    ax.set_ylabel("n_patches")
    ax.set_xlim(20, 100)
    ax.set_ylim(1, 8)
    ax.set_title("Stage 6: collapse holds across the full population x patch-count grid")
    _savefig(fig, "08_stage6_scaling_grid")


def fig_stage13_migration_ablation(data):
    if data is None:
        return
    pairs = data["migration_ablation"]["pairs"]
    fig, ax = plt.subplots(figsize=(6, 5))
    for i, p in enumerate(pairs):
        a, b = p["migration_off_ecological_resource_fraction"], p["migration_on_ecological_resource_fraction"]
        ax.plot([0, 1], [a, b], marker="o", color="#c0392b" if b < a else "#27ae60", alpha=0.8)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["migration OFF", "migration ON"])
    ax.set_ylabel("ecological resource fraction")
    ax.set_title("Section 13 Ablation 1: migration on/off (matched seeds, n=8 pairs)")
    _savefig(fig, "09_stage13_migration_ablation")


def fig_stage13_regen_ablation(data):
    if data is None:
        return
    pairs = data["regen_rate_ablation"]["pairs"]
    fig, ax = plt.subplots(figsize=(6, 5))
    for p in pairs:
        a, b = p["regen_low_ecological_resource_fraction"], p["regen_high_ecological_resource_fraction"]
        ax.plot([0, 1], [a, b], marker="o", color="#27ae60" if b > a else "#c0392b", alpha=0.8)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["regen_rate = 0.2", "regen_rate = 1.0"])
    ax.set_ylabel("ecological resource fraction")
    ax.set_title("Section 13 Ablation 2: patch_regen_rate low vs. high (matched seeds, n=8 pairs)")
    _savefig(fig, "10_stage13_regen_rate_ablation")


def run():
    stage1 = _load(PATHS["stage1"])
    stage2 = _load(PATHS["stage2"])
    stage3 = _load(PATHS["stage3"])
    stage4 = _load(PATHS["stage4"])
    stage5 = _load(PATHS["stage5"])
    stage6 = _load(PATHS["stage6"])
    stage13 = _load(PATHS["stage13"])

    fig_stage1_mechanism_activation(stage1)
    fig_stage2_outcome_distribution(stage2)
    fig_stage3_regen_vs_ecology(stage3)
    fig_stage3_outcome_distribution(stage3)
    fig_stage4_criteria_pass_distribution(stage4)
    fig_stage4_vs_stage5_replication(stage4, stage5)
    fig_stage5_held_out_log_likelihood(stage5)
    fig_stage6_scaling_grid(stage6)
    fig_stage13_migration_ablation(stage13)
    fig_stage13_regen_ablation(stage13)

    print(f"Level 1.2 visualizations written to {OUT_DIR}/", flush=True)


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
