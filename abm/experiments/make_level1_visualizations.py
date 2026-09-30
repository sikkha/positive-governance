#!/usr/bin/env python3
"""Level 1.0 visualizations.

Reads the already-committed outputs of every Level 1.0 Stage script
(does not re-run any of them). Every figure with a value derived across
multiple seeds/points shows its sample size explicitly and, where
applicable, an uncertainty band or interval -- never a single
representative run passed off as typical, and never only the
favorable-looking (persistent) outcomes without the founder-dependent/
short-lived/failed ones alongside. No chart title asserts a mature-
governance concept -- only the milestone's own cautious label vocabulary
(``observer/institution_diagnostics.py::VALID_LABELS``).
"""

from __future__ import annotations

import json
import os
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT_DIR = "outputs/level1_figures"
STAGE2_DIR = "outputs/level1_stage2_search"
STAGE3_PATH = "outputs/level1_stage3_confirmatory/stage3_report.json"
STAGE4_PATH = "outputs/level1_stage4_counterfactuals/stage4_report.json"
SHOCKS_PATH = "outputs/level1_shocks/shocks_report.json"
CALIBRATION_PATH = "outputs/level1_stage1_calibration/calibration_report.json"

LABEL_COLORS = {
    "no_proposal": "#999999",
    "proposal_rejected": "#c9b458",
    "short_lived_convention": "#f4a261",
    "founder_dependent_arrangement": "#e76f51",
    "proto_institution": "#2a9d8f",
    "persistent_proto_institution": "#264653",
    "dissolved": "#a4133c",
    "reconstructed": "#5e548e",
    "unclassified": "#cccccc",
}


def _load(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _label_counter(records):
    c = Counter()
    for r in records:
        for cl in r["classifications"]:
            c[cl["label"]] += 1
    return c


def fig01_stage1_mechanism_activation():
    data = _load(CALIBRATION_PATH)
    if not data:
        return
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    mechanisms = ["n_proposals", "n_adoptions", "n_rejections", "n_compliant_events",
                  "n_violated_events", "n_monitorings", "n_sanctions", "n_dissolutions"]
    conditions = list(data.keys())
    x = np.arange(len(conditions))
    for ax, group in zip(axes.flat, [mechanisms[:2], mechanisms[2:4], mechanisms[4:6], mechanisms[6:8]]):
        width = 0.35
        for i, m in enumerate(group):
            vals = [data[c][m] for c in conditions]
            ax.bar(x + i * width, vals, width, label=m)
        ax.set_xticks(x + width / 2)
        ax.set_xticklabels(conditions, rotation=20, ha="right", fontsize=7)
        ax.legend(fontsize=7)
        ax.set_yscale("symlog")
    fig.suptitle(f"Stage 1: mechanism activation counts, {5} seeds/condition, 400 steps\n"
                 "(every mechanism fires; none is permanently inactive or mechanically certain)")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig01_stage1_mechanism_activation.png", dpi=130)
    plt.close(fig)


def fig02_stage2_label_distribution_primary():
    records = _load(f"{STAGE2_DIR}/search_records_interior_persistent.json")
    if not records:
        return
    counts = _label_counter(records)
    fig, ax = plt.subplots(figsize=(9, 5))
    labels = sorted(counts, key=lambda l: -counts[l])
    ax.bar(labels, [counts[l] for l in labels], color=[LABEL_COLORS.get(l, "gray") for l in labels])
    ax.set_ylabel("patch-run count")
    n_points = len(set(r["point_id"] for r in records))
    n_seeds = len(set(r["seed"] for r in records))
    ax.set_title(f"Stage 2 (interior_persistent): Work Package K label distribution\n"
                 f"{n_points} points x {n_seeds} seeds, all patches, all outcomes shown")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig02_stage2_label_distribution_primary.png", dpi=130)
    plt.close(fig)


def fig03_stage2_label_distribution_by_candidate():
    cands = {
        "interior_persistent": _load(f"{STAGE2_DIR}/search_records_interior_persistent.json"),
        "nonstationary": _load(f"{STAGE2_DIR}/search_records_nonstationary_secondary.json"),
        "near_collapse": _load(f"{STAGE2_DIR}/search_records_near_collapse_secondary.json"),
    }
    cands = {k: v for k, v in cands.items() if v}
    if not cands:
        return
    all_labels = sorted({l for recs in cands.values() for l in _label_counter(recs)})
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(all_labels))
    width = 0.8 / len(cands)
    for i, (name, recs) in enumerate(cands.items()):
        counts = _label_counter(recs)
        n_points = len(set(r["point_id"] for r in recs))
        n_seeds = len(set(r["seed"] for r in recs))
        fracs = [counts.get(l, 0) / max(1, sum(counts.values())) for l in all_labels]
        ax.bar(x + i * width, fracs, width, label=f"{name} ({n_points}pt x {n_seeds}sd)")
    ax.set_xticks(x + width)
    ax.set_xticklabels(all_labels, rotation=30, ha="right")
    ax.set_ylabel("fraction of patch-runs")
    ax.set_title("Stage 2: label distribution by registered ecological candidate\n"
                 "(all 3 registered candidates from the Level 0.3b causal-worsening finding)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig03_stage2_label_distribution_by_candidate.png", dpi=130)
    plt.close(fig)


def fig04_stage2_proposal_probability_vs_adoption_rate():
    records = _load(f"{STAGE2_DIR}/search_records_interior_persistent.json")
    if not records:
        return
    by_point = {}
    for r in records:
        by_point.setdefault(r["point_id"], {"overrides": r["overrides"], "adoptions": 0, "proposals": 0})
        by_point[r["point_id"]]["adoptions"] += r["metrics"]["formation"]["n_adoptions"]
        by_point[r["point_id"]]["proposals"] += r["metrics"]["formation"]["n_proposals"]
    xs = [v["overrides"]["proposal_probability_mean"] for v in by_point.values()]
    ys = [v["adoptions"] / v["proposals"] if v["proposals"] else np.nan for v in by_point.values()]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(xs, ys)
    ax.set_xlabel("proposal_probability_mean")
    ax.set_ylabel("adoption rate (adoptions/proposals), summed over 5 seeds")
    ax.set_title(f"Stage 2: proposal probability vs. adoption rate ({len(by_point)} points)")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig04_stage2_proposal_probability_vs_adoption_rate.png", dpi=130)
    plt.close(fig)


def fig05_stage3_persistence_lifetimes():
    report = _load(STAGE3_PATH)
    if not report:
        return
    fig, ax = plt.subplots(figsize=(9, 5))
    any_data = False
    for name, cand in report["candidates"].items():
        if cand.get("status") != "confirmed":
            continue
        lifetimes = []
        for traj in cand["trajectories"]:
            for cls in traj["classifications"]:
                if cls["duration_steps"] is not None:
                    lifetimes.append(cls["duration_steps"])
        if not lifetimes:
            continue
        any_data = True
        ax.hist(lifetimes, bins=20, alpha=0.5, label=f"{name} (n={len(lifetimes)} patch-runs)")
    if not any_data:
        plt.close(fig)
        return
    ax.set_xlabel("rule instance duration (steps)")
    ax.set_ylabel("count")
    ax.set_title(f"Stage 3: rule-instance lifetime distributions, {report.get('candidate_key')}, 24 seeds/candidate, 800 steps")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig05_stage3_persistence_lifetimes.png", dpi=130)
    plt.close(fig)


def fig06_stage3_compliance_violation_rate():
    report = _load(STAGE3_PATH)
    if not report:
        return
    names, comply, violate, n = [], [], [], []
    for name, cand in report["candidates"].items():
        if cand.get("status") != "confirmed":
            continue
        rates_c = [t["metrics"]["compliance_enforcement"]["compliance_rate"] for t in cand["trajectories"]]
        rates_v = [t["metrics"]["compliance_enforcement"]["violation_rate"] for t in cand["trajectories"]]
        rates_c = [r for r in rates_c if r == r]
        rates_v = [r for r in rates_v if r == r]
        if not rates_c:
            continue
        names.append(name)
        comply.append(np.mean(rates_c))
        violate.append(np.mean(rates_v))
        n.append(len(rates_c))
    if not names:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(names))
    ax.bar(x - 0.2, comply, 0.4, label="mean compliance rate")
    ax.bar(x + 0.2, violate, 0.4, label="mean violation rate")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{nm}\n(n={ni} seeds)" for nm, ni in zip(names, n)], fontsize=8)
    ax.set_title("Stage 3: mean compliance vs. violation rate by candidate\n(adoption does not mechanically create universal compliance)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig06_stage3_compliance_violation_rate.png", dpi=130)
    plt.close(fig)


def fig07_stage3_neighborhood_robustness():
    report = _load(STAGE3_PATH)
    if not report:
        return
    fig, axes = plt.subplots(1, max(1, len(report["candidates"])), figsize=(6 * max(1, len(report["candidates"])), 5), squeeze=False)
    axes = axes[0]
    for ax, (name, cand) in zip(axes, report["candidates"].items()):
        if cand.get("status") != "confirmed":
            ax.set_visible(False)
            continue
        counts = Counter()
        for run in cand.get("neighborhood_checks", []):
            for cls in run["classifications"]:
                counts[cls["label"]] += 1
        if not counts:
            continue
        labels = sorted(counts, key=lambda l: -counts[l])
        ax.bar(labels, [counts[l] for l in labels], color=[LABEL_COLORS.get(l, "gray") for l in labels])
        ax.set_title(f"{name}\nneighborhood checks (n={sum(counts.values())} patch-runs)")
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=7)
    fig.suptitle("Stage 3: label stability under +-10% parameter-neighborhood perturbation")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig07_stage3_neighborhood_robustness.png", dpi=130)
    plt.close(fig)


def fig08_stage4_final_occupancy_by_condition():
    report = _load(STAGE4_PATH)
    if not report:
        return
    fig, ax = plt.subplots(figsize=(11, 6))
    names, means, cis, ns = [], [], [], []
    for name, cond in report["conditions"].items():
        vals = [r["ecological_outcomes"]["final_occupancy"] for r in cond["runs"] if r["ecological_outcomes"]["final_occupancy"] == r["ecological_outcomes"]["final_occupancy"]]
        if not vals:
            continue
        names.append(name)
        means.append(np.mean(vals))
        se = np.std(vals, ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else 0.0
        cis.append(1.96 * se)
        ns.append(len(vals))
    order = np.argsort(means)
    names = [names[i] for i in order]
    means = [means[i] for i in order]
    cis = [cis[i] for i in order]
    ns = [ns[i] for i in order]
    ax.barh(names, means, xerr=cis, capsize=3)
    for i, n in enumerate(ns):
        ax.text(0.01, i, f"n={n}", va="center", fontsize=7)
    ax.set_xlabel("final mean patch occupancy (fraction of capacity), +-95% CI")
    ax.set_title(f"Stage 4: final ecological occupancy across all 11 institutional counterfactuals\n"
                 f"({report['n_seeds']} matched seeds, {report['n_steps']} steps)")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig08_stage4_final_occupancy_by_condition.png", dpi=130)
    plt.close(fig)


def fig09_stage4_paired_effect_vs_atomic_baseline():
    report = _load(STAGE4_PATH)
    if not report:
        return
    baseline_runs = {r["seed"]: r["ecological_outcomes"]["final_occupancy"] for r in report["conditions"]["atomic_baseline"]["runs"]}
    fig, ax = plt.subplots(figsize=(10, 6))
    names, means, los, his = [], [], [], []
    rng = np.random.default_rng(0)
    for name, cond in report["conditions"].items():
        if name == "atomic_baseline":
            continue
        diffs = []
        for r in cond["runs"]:
            b = baseline_runs.get(r["seed"])
            v = r["ecological_outcomes"]["final_occupancy"]
            if b == b and v == v:
                diffs.append(v - b)
        if not diffs:
            continue
        diffs = np.array(diffs)
        boots = [np.mean(rng.choice(diffs, size=len(diffs), replace=True)) for _ in range(2000)]
        names.append(name)
        means.append(np.mean(diffs))
        los.append(np.percentile(boots, 2.5))
        his.append(np.percentile(boots, 97.5))
    order = np.argsort(means)
    names = [names[i] for i in order]
    means = [means[i] for i in order]
    los = [los[i] for i in order]
    his = [his[i] for i in order]
    y = np.arange(len(names))
    ax.errorbar(means, y, xerr=[np.array(means) - np.array(los), np.array(his) - np.array(means)], fmt="o", capsize=3)
    ax.axvline(0.0, color="gray", linestyle="--")
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("paired Delta final occupancy vs. atomic_baseline (seed-matched), 95% bootstrap CI")
    ax.set_title(f"Stage 4: seed-paired institutional effect on final occupancy ({report['n_seeds']} matched seeds)")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig09_stage4_paired_effect_vs_atomic_baseline.png", dpi=130)
    plt.close(fig)


def fig10_stage4_welfare_member_vs_nonmember():
    report = _load(STAGE4_PATH)
    if not report:
        return
    fig, ax = plt.subplots(figsize=(11, 6))
    names, member_means, nonmember_means = [], [], []
    for name, cond in report["conditions"].items():
        mm = [r["metrics"]["welfare"]["mean_member_resources"] for r in cond["runs"]]
        nm = [r["metrics"]["welfare"]["mean_nonmember_resources"] for r in cond["runs"]]
        mm = [v for v in mm if v == v]
        nm = [v for v in nm if v == v]
        if not mm and not nm:
            continue
        names.append(name)
        member_means.append(np.mean(mm) if mm else np.nan)
        nonmember_means.append(np.mean(nm) if nm else np.nan)
    x = np.arange(len(names))
    ax.bar(x - 0.2, member_means, 0.4, label="mean member resources")
    ax.bar(x + 0.2, nonmember_means, 0.4, label="mean non-member resources")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
    ax.set_title(f"Stage 4: welfare (member vs. non-member) by condition ({report['n_seeds']} seeds/condition)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig10_stage4_welfare_member_vs_nonmember.png", dpi=130)
    plt.close(fig)


def fig11_stage4_monitoring_confusion_rates():
    report = _load(STAGE4_PATH)
    if not report:
        return
    fig, ax = plt.subplots(figsize=(11, 6))
    names, tp, fp = [], [], []
    for name, cond in report["conditions"].items():
        tps = [r["metrics"]["compliance_enforcement"]["monitoring_true_positive_rate"] for r in cond["runs"]]
        fps = [r["metrics"]["compliance_enforcement"]["monitoring_false_positive_rate_observed"] for r in cond["runs"]]
        tps = [v for v in tps if v == v]
        fps = [v for v in fps if v == v]
        if not tps and not fps:
            continue
        names.append(name)
        tp.append(np.mean(tps) if tps else np.nan)
        fp.append(np.mean(fps) if fps else np.nan)
    x = np.arange(len(names))
    ax.bar(x - 0.2, tp, 0.4, label="mean true-positive rate")
    ax.bar(x + 0.2, fp, 0.4, label="mean false-positive rate")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
    ax.set_title(f"Stage 4: monitoring confusion-matrix rates by condition ({report['n_seeds']} seeds/condition)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig11_stage4_monitoring_confusion_rates.png", dpi=130)
    plt.close(fig)


def fig12_stage4_sanction_cost_and_false_sanction_rate():
    report = _load(STAGE4_PATH)
    if not report:
        return
    fig, ax = plt.subplots(figsize=(11, 6))
    names, cost, false_rate = [], [], []
    for name, cond in report["conditions"].items():
        c = [r["metrics"]["compliance_enforcement"]["total_sanction_cost"] for r in cond["runs"]]
        fr = [r["metrics"]["compliance_enforcement"]["false_sanction_rate"] for r in cond["runs"]]
        fr = [v for v in fr if v == v]
        if not c:
            continue
        names.append(name)
        cost.append(np.mean(c))
        false_rate.append(np.mean(fr) if fr else np.nan)
    ax2 = ax.twinx()
    x = np.arange(len(names))
    ax.bar(x - 0.2, cost, 0.4, color="tab:blue", label="mean total sanction cost")
    ax2.bar(x + 0.2, false_rate, 0.4, color="tab:red", label="mean false-sanction rate")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("mean total sanction cost", color="tab:blue")
    ax2.set_ylabel("mean false-sanction rate", color="tab:red")
    ax.set_title(f"Stage 4: sanction cost and false-sanction rate by condition ({report['n_seeds']} seeds/condition)")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig12_stage4_sanction_cost_and_false_sanction_rate.png", dpi=130)
    plt.close(fig)


def fig13_stage4_social_vs_institutional_independence():
    report = _load(STAGE4_PATH)
    if not report:
        return
    fig, ax = plt.subplots(figsize=(8, 6))
    xs, ys, labels = [], [], []
    for name, cond in report["conditions"].items():
        comply = [r["metrics"]["compliance_enforcement"]["compliance_rate"] for r in cond["runs"]]
        coop = [r["metrics"]["social_effects"]["member_cooperation_rate"] for r in cond["runs"]]
        comply = [v for v in comply if v == v]
        coop = [v for v in coop if v == v]
        if not comply or not coop:
            continue
        xs.append(np.mean(comply))
        ys.append(np.mean(coop))
        labels.append(name)
    ax.scatter(xs, ys)
    for x, y, l in zip(xs, ys, labels):
        ax.annotate(l, (x, y), fontsize=6, rotation=15)
    ax.set_xlabel("mean institutional compliance rate")
    ax.set_ylabel("mean member social cooperation rate")
    ax.set_title("Stage 4: institutional compliance vs. social cooperation, by condition\n(reported side by side -- never mixed into one ledger)")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig13_stage4_social_vs_institutional_independence.png", dpi=130)
    plt.close(fig)


def fig14_stage4_formed_then_removed_survival():
    report = _load(STAGE4_PATH)
    if not report:
        return
    cond = report["conditions"].get("institution_formed_then_removed")
    if not cond:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    labels_after = Counter()
    for r in cond["runs"]:
        for cls in r["classifications"]:
            labels_after[cls["label"]] += 1
    labels = sorted(labels_after, key=lambda l: -labels_after[l])
    ax.bar(labels, [labels_after[l] for l in labels], color=[LABEL_COLORS.get(l, "gray") for l in labels])
    ax.set_title(f"Stage 4: patch labels after forced institution removal at step {report['removal_step']}\n(n={report['n_seeds']} seeds)")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig14_stage4_formed_then_removed_survival.png", dpi=130)
    plt.close(fig)


def fig15_shocks_survival_rate():
    report = _load(SHOCKS_PATH)
    if not report:
        return
    fig, ax = plt.subplots(figsize=(9, 5))
    shocks = list(report["shocks"].keys())
    rates = []
    ns = []
    for s in shocks:
        runs = report["shocks"][s]
        active = sum(r["n_active_pre_shock"] for r in runs)
        survived = sum(r["n_survived_post_shock"] for r in runs)
        rates.append(survived / active if active else np.nan)
        ns.append(active)
    ax.bar(shocks, rates)
    for i, n in enumerate(ns):
        ax.text(i, (rates[i] or 0) + 0.02, f"n={n} rules", ha="center", fontsize=7)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("fraction of pre-shock-active rules still active post-shock")
    ax.set_title(f"Section 19: institutional shock survival rate by shock type ({report['n_seeds']} seeds/shock)")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig15_shocks_survival_rate.png", dpi=130)
    plt.close(fig)


def fig16_shocks_reconstruction_counts():
    report = _load(SHOCKS_PATH)
    if not report:
        return
    fig, ax = plt.subplots(figsize=(9, 5))
    shocks = list(report["shocks"].keys())
    recon = [sum(r["n_reconstructions_post_shock"] for r in report["shocks"][s]) for s in shocks]
    dissolved = [sum(r["n_post_shock_dissolutions"] for r in report["shocks"][s]) for s in shocks]
    x = np.arange(len(shocks))
    ax.bar(x - 0.2, dissolved, 0.4, label="post-shock dissolutions")
    ax.bar(x + 0.2, recon, 0.4, label="post-shock reconstruction attempts (lineage recorded)")
    ax.set_xticks(x)
    ax.set_xticklabels(shocks, rotation=20, ha="right", fontsize=8)
    ax.set_title(f"Section 19: post-shock dissolution and reconstruction counts ({report['n_seeds']} seeds/shock)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig16_shocks_reconstruction_counts.png", dpi=130)
    plt.close(fig)


ALL_FIGURES = [
    fig01_stage1_mechanism_activation,
    fig02_stage2_label_distribution_primary,
    fig03_stage2_label_distribution_by_candidate,
    fig04_stage2_proposal_probability_vs_adoption_rate,
    fig05_stage3_persistence_lifetimes,
    fig06_stage3_compliance_violation_rate,
    fig07_stage3_neighborhood_robustness,
    fig08_stage4_final_occupancy_by_condition,
    fig09_stage4_paired_effect_vs_atomic_baseline,
    fig10_stage4_welfare_member_vs_nonmember,
    fig11_stage4_monitoring_confusion_rates,
    fig12_stage4_sanction_cost_and_false_sanction_rate,
    fig13_stage4_social_vs_institutional_independence,
    fig14_stage4_formed_then_removed_survival,
    fig15_shocks_survival_rate,
    fig16_shocks_reconstruction_counts,
]


def run():
    os.makedirs(OUT_DIR, exist_ok=True)
    made = []
    for fn in ALL_FIGURES:
        before = set(os.listdir(OUT_DIR))
        fn()
        after = set(os.listdir(OUT_DIR))
        if after - before:
            made.append(fn.__name__)
    print(f"wrote {len(made)}/{len(ALL_FIGURES)} figures to {OUT_DIR}: {made}")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
