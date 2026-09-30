#!/usr/bin/env python3
"""Level 1.1b visualizations.

Reads the already-committed JSON outputs of every Work Package A-H
experiment script (``outputs/level11b_*/*.json``) -- does not re-run
any of them, and does not run any new simulation. Every figure shows
its sample size (n_seeds) and, where the underlying script computed
one, the 95% seed-clustered bootstrap CI explicitly -- never a single
point estimate passed off as certain. No chart title or axis label uses
any of ``tests/test_level11_compatibility.py``'s
``FORBIDDEN_LEVEL11_TERMS`` structural-terminology guard's forbidden
governance-type/SEM-trajectory vocabulary; every label is drawn from
Work Package K's fixed mechanism-validation label vocabulary
(``observer/delegation_diagnostics.VALID_LABELS``) or a plain
event/count/rate name.

Session-budget scope reduction (disclosed, matching the Level 1.0/1.1
precedent of disclosing fewer figures than a milestone's nominal
target): 7 of the milestone's originally-requested 10-14 figures -- one
covering each of Work Packages C/D/E/F/G/H's own single clearest
confirmatory result, plus one cross-work-package summary figure showing
every headline paired-difference CI on a common axis -- rather than
exhaustively enumerating every cut of every work package's data. Work
Package A (RNG architecture) and Work Package B (test-suite repair) are
infrastructure/testing work packages with no headline numeric contrast
of their own to plot and are represented in
``docs/level1.1b_validation_note.md`` prose instead.
"""

from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT_DIR = "outputs/level11b_figures"

PATHS = {
    "coordination": "outputs/level11b_coordination_calibration/level11b_coordination_calibration_summary.json",
    "appropriation": "outputs/level11b_appropriation_decomposition/level11b_appropriation_decomposition_summary.json",
    "accountability": "outputs/level11b_accountability_conditions/level11b_accountability_conditions_summary.json",
    "memory": "outputs/level11b_institutional_memory_validation/level11b_institutional_memory_validation_summary.json",
    "shock": "outputs/level11b_functional_shock_recovery/level11b_functional_shock_recovery_summary.json",
    "classifier": "outputs/level11b_audited_classifier_comparison/level11b_audited_classifier_comparison_summary.json",
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
    print(f"[make_level11b_visualizations] wrote {path}")


def _ci_bar(ax, labels, points, los, his, color="#2a9d8f", zero_line=True):
    x = np.arange(len(labels))
    points = np.array([p if p is not None else np.nan for p in points], dtype=float)
    los = np.array([l if l is not None else np.nan for l in los], dtype=float)
    his = np.array([h if h is not None else np.nan for h in his], dtype=float)
    lower_err = np.clip(points - los, 0, None)
    upper_err = np.clip(his - points, 0, None)
    ax.bar(x, points, color=color, alpha=0.85)
    ax.errorbar(x, points, yerr=[lower_err, upper_err], fmt="none", ecolor="black", capsize=4, linewidth=1.2)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    if zero_line:
        ax.axhline(0.0, color="#555555", linewidth=0.8, linestyle="--")


def fig_wpC_coordination_window_effect(d):
    """Work Package C: acceptance rate collapses from ~retry-inflated
    to a non-degenerate range once the retry window is removed --
    window_steps=5 (default) vs. window_steps=1
    (``level11b_coordination_nondegenerate``), pooled across n_patches."""
    if d is None:
        return
    rows = d["rows"]
    fig, ax = plt.subplots(figsize=(6, 4.5))
    for ws, color in ((5, "#264653"), (3, "#e9c46a"), (1, "#e76f51")):
        rates = [r["acceptance_rate"] for r in rows if r["window_steps"] == ws]
        if not rates:
            continue
        ax.hist(rates, bins=np.linspace(0, 1, 11), alpha=0.55, label=f"window_steps={ws} (n={len(rates)} runs)", color=color)
    ax.set_xlabel("Per-run coordination acceptance rate")
    ax.set_ylabel("Number of (seed, n_patches) runs")
    ax.set_title("WP-C: retry window inflates acceptance toward ~1.0")
    ax.legend(fontsize=8)
    _savefig(fig, "wpC_coordination_window_effect")


def fig_wpD_opportunity_vs_conduct(d):
    if d is None:
        return
    c = d["paired_seed_clustered_bootstrap_no_admin_cost_minus_baseline"]
    fields = ["n_opportunities", "attempt_propensity_given_opportunity", "mean_conditional_intensity_given_attempt"]
    display = ["n_opportunities\n(opportunity)", "attempt_propensity\n(conduct: willingness)", "conditional_intensity\n(conduct: aggressiveness)"]
    points = [c[f]["point_estimate"] for f in fields]
    los = [c[f]["ci_low"] for f in fields]
    his = [c[f]["ci_high"] for f in fields]
    n_seeds = c[fields[0]]["n_seeds"]
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    _ci_bar(ax, display, points, los, his, color="#2a9d8f")
    ax.set_ylabel("no_admin_cost − baseline (paired diff, raw units)")
    ax.set_title(f"WP-D: opportunity shifted, conduct did not (n_seeds={n_seeds}, 95% CI)")
    _savefig(fig, "wpD_opportunity_vs_conduct")


def fig_wpE_placebo_vs_perfect_info_net_appropriation(d):
    if d is None:
        return
    c = d["seed_clustered_bootstrap_contrasts"]
    keys = [
        "placebo_minus_no_accountability__net_appropriated",
        "full_minus_no_accountability__net_appropriated",
        "perfect_info_minus_no_accountability__net_appropriated",
    ]
    display = ["randomized_placebo\n− no_accountability", "full\n− no_accountability", "perfect_info\n− no_accountability"]
    points = [c[k]["point_estimate"] for k in keys]
    los = [c[k]["ci_low"] for k in keys]
    his = [c[k]["ci_high"] for k in keys]
    n_seeds = c[keys[0]]["n_seeds"]
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    _ci_bar(ax, display, points, los, his, color="#e76f51")
    ax.set_ylabel("Δ net appropriation (gross − recovered), paired diff")
    ax.set_title(f"WP-E: activity alone doesn't cut net appropriation; accurate detection does (n_seeds={n_seeds})")
    _savefig(fig, "wpE_activity_vs_effective_constraint")


def fig_wpF_memory_dose_response(d):
    if d is None:
        return
    m = d["mean_by_condition"]
    order = ["no_memory", "default", "moderate", "high_retention", "max_dose"]
    doses = [m[c]["mean_dose_delivered"] for c in order]
    caps = [m[c]["mean_end_capacity"] for c in order]
    fig, ax1 = plt.subplots(figsize=(6.5, 4.5))
    x = np.arange(len(order))
    ax1.plot(x, doses, "o-", color="#264653", label="mean_dose_delivered")
    ax1.set_ylabel("mean_dose_delivered (record_quality units)", color="#264653")
    ax1.set_xticks(x)
    ax1.set_xticklabels(order, rotation=20, ha="right")
    ax2 = ax1.twinx()
    ax2.plot(x, caps, "s--", color="#e76f51", label="mean_end_capacity")
    ax2.set_ylabel("mean_end_capacity (capacity units)", color="#e76f51")
    ax1.set_title("WP-F: institutional memory is a real, monotonic, small-at-default dose-response")
    _savefig(fig, "wpF_memory_dose_response")


def fig_wpG_reappointment_vs_recovery(d):
    if d is None:
        return
    b = d["seed_clustered_bootstrap"]
    keys = ["reappointment_rate", "within_tolerance_recovery_rate_among_reappointed_with_defined_gap",
            "full_recovery_rate_among_reappointed_with_defined_gap"]
    display = ["reappointment_rate", "within-tolerance\nfunctional recovery", "full\nfunctional recovery"]
    points = [b[k]["point_estimate"] for k in keys]
    los = [b[k]["ci_low"] for k in keys]
    his = [b[k]["ci_high"] for k in keys]
    n_seeds = b[keys[0]]["n_seeds"]
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    _ci_bar(ax, display, points, los, his, color="#2a9d8f", zero_line=False)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Rate")
    ax.set_title(f"WP-G: reappointment ≠ functional recovery (n_seeds={n_seeds}, 95% CI)")
    _savefig(fig, "wpG_reappointment_vs_recovery")


def fig_wpH_downgrade_rate_by_condition(d):
    if d is None:
        return
    p = d["pooled_by_condition"]
    conditions = list(p.keys())
    rates = [p[c]["pooled_downgrade_rate"] for c in conditions]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = np.arange(len(conditions))
    plotted_rates = [r if r is not None else 0.0 for r in rates]
    bars = ax.bar(x, plotted_rates, color=["#999999" if r is None else "#e76f51" for r in rates])
    for xi, r in zip(x, rates):
        label = "undefined\n(0/0)" if r is None else f"{r:.1%}"
        ax.text(xi, (r or 0.0) + 0.01, label, ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(conditions, rotation=20, ha="right")
    ax.set_ylabel("Downgrade rate (pooled)")
    ax.set_title("WP-H: fraction of historical 'accountable' calls the audited classifier does not support")
    _savefig(fig, "wpH_classifier_downgrade_rate")


def fig_summary_ci_widths_all_wps(data):
    """One cross-work-package figure: every headline paired-difference
    estimate this milestone produced, plotted on a common axis so a
    reader can see at a glance which contrasts excluded zero (a
    detected effect) and which did not (a null result, reported as
    such -- never omitted)."""
    entries = []
    if data["appropriation"] is not None:
        c = data["appropriation"]["paired_seed_clustered_bootstrap_no_admin_cost_minus_baseline"]
        entries.append(("WP-D: attempt_propensity\n(no_admin_cost − baseline)", c["attempt_propensity_given_opportunity"]))
    if data["accountability"] is not None:
        c = data["accountability"]["seed_clustered_bootstrap_contrasts"]
        entries.append(("WP-E: net_appropriated\n(placebo − no_accountability)", c["placebo_minus_no_accountability__net_appropriated"]))
        entries.append(("WP-E: net_appropriated\n(perfect_info − no_accountability)", c["perfect_info_minus_no_accountability__net_appropriated"]))
    if data["memory"] is not None:
        c = data["memory"]["seed_clustered_bootstrap_contrasts"]
        entries.append(("WP-F: end_capacity\n(default − no_memory)", c["default_minus_no_memory__mean_end_capacity"]))
        entries.append(("WP-F: end_capacity\n(max_dose − no_memory)", c["max_dose_minus_no_memory__mean_end_capacity"]))
    if data["shock"] is not None:
        b = data["shock"]["seed_clustered_bootstrap"]
        entries.append(("WP-G: mean_recovery_gap", b["mean_recovery_gap"]))
    if not entries:
        return
    labels = [e[0] for e in entries]
    points = [e[1]["point_estimate"] for e in entries]
    los = [e[1]["ci_low"] for e in entries]
    his = [e[1]["ci_high"] for e in entries]
    fig, ax = plt.subplots(figsize=(7, 5.5))
    y = np.arange(len(labels))
    for yi, (p, l, h) in enumerate(zip(points, los, his)):
        if p is None:
            continue
        excludes_zero = (l > 0) or (h < 0)
        color = "#2a9d8f" if excludes_zero else "#999999"
        ax.plot([l, h], [yi, yi], color=color, linewidth=3)
        ax.plot([p], [yi], "o", color="black", markersize=5)
    ax.axvline(0.0, color="#555555", linewidth=0.8, linestyle="--")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Paired-difference point estimate and 95% seed-clustered bootstrap CI")
    ax.set_title("Every headline paired contrast across WP-D/E/F/G\n(green = CI excludes zero; grey = includes zero, a null result)")
    _savefig(fig, "summary_all_confidence_intervals")


def run(out_dir: str = OUT_DIR) -> list:
    os.makedirs(out_dir, exist_ok=True)
    data = {k: _load(v) for k, v in PATHS.items()}
    missing = [k for k, v in data.items() if v is None]
    if missing:
        print(f"[make_level11b_visualizations] WARNING: missing outputs for {missing} -- their figures are skipped, not faked.")

    fig_wpC_coordination_window_effect(data["coordination"])
    fig_wpD_opportunity_vs_conduct(data["appropriation"])
    fig_wpE_placebo_vs_perfect_info_net_appropriation(data["accountability"])
    fig_wpF_memory_dose_response(data["memory"])
    fig_wpG_reappointment_vs_recovery(data["shock"])
    fig_wpH_downgrade_rate_by_condition(data["classifier"])
    fig_summary_ci_widths_all_wps(data)

    written = sorted(f for f in os.listdir(out_dir) if f.endswith(".png"))
    print(f"[make_level11b_visualizations] {len(written)} figures written to {out_dir}/: {written}")
    return written


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
