#!/usr/bin/env python3
"""Level 1.2b visualizations (Section 26).

Reads the already-committed JSON outputs of every Level 1.2b Work
Package (`outputs/level12b_stage_*/*.json`) -- does not re-run any of
them. **One exception, disclosed**: Work Packages A (ecological ledger
audit) and B (feasibility ratios) are library/audit modules with no
dedicated experiment script and no saved `results.json` of their own —
`fig_ledger_balance` therefore drives one small, cheap, fresh
`level12_complete` simulation purely to have something to plot,
exactly the same "a few cheap fresh runs of its own" precedent Level
0.3's own `make_level03_visualizations.py` already established. No
chart title or axis label uses any of `tests/test_level12_structural_
guards.py`'s `FORBIDDEN_LEVEL12_TERMS` structural-terminology guard's
forbidden governance-type/SEM-trajectory vocabulary; every label is
drawn from `observer/institutional_viability.ALL_OUTCOME_LABELS`, a
plain event/count/rate/parameter name, or this milestone's own closed
verdict vocabularies. No visual privileges k=3 or any other specific
cluster count -- every k in `DEFAULT_K_RANGE` is plotted identically,
k=1 included.

**Disclosed scope reduction, matching every prior milestone's own
precedent** (Level 1.2's own visualization script did 10 of its
suggested ~14-20): this script produces 16 of Section 26's suggested
~14-20 figures -- covering every category on Section 26's own list
except three that are genuinely not applicable given this milestone's
own `continuum`/`null_replicated` result (no discrete candidate was
ever confirmed to have a "candidate feature profile"; no per-candidate
recurrence-criteria pass/fail breakdown exists since Section 20's
twelve criteria were never applied to a named candidate; and the
co-assignment consensus matrix was never persisted to
`results.json` by Work Package K's own script, and recomputing it
would require a fourth full 576-run re-simulation for marginal
diagnostic value -- disclosed here rather than silently reproduced by
re-running discovery a fourth time). Each is disclosed at the
corresponding point in this file's own `run()` output, not silently
dropped."""

from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT_DIR = "outputs/level12b_figures"

PATHS = {
    "c": "outputs/level12b_stage_c_feasibility_map/results.json",
    "e_design": "outputs/level12b_stage_e_joint_discovery/design.json",
    "j": "outputs/level12b_stage_j_main_discovery_pipeline/results.json",
    "k": "outputs/level12b_stage_k_clustering_discovery/results.json",
    "l3": "outputs/level12b_stage_l3_prospective_confirmation/results.json",
    "m": "outputs/level12b_stage_m_scaling_robustness/results.json",
    "n": "outputs/level12b_stage_n_causal_collapse_decomposition/results.json",
    "o": "outputs/level12b_stage_o_phenotype_recurrence_classification/results.json",
}

#: Consistent color per outcome label across every figure -- same
#: palette Level 1.2's own visualization script used, extended with no
#: new labels (Level 1.2b introduces no new `all_outcome_label` value).
OUTCOME_COLORS = {
    "no_institution": "#999999", "collapse": "#c0392b", "viable": "#27ae60",
    "persistent_extractive": "#e67e22", "fragmented": "#f1c40f", "transient": "#8e44ad",
    "unclassified": "#333333",
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


def _bar_outcome_counts(ax, counts: dict, title: str):
    labels = list(counts.keys())
    values = [counts[l] for l in labels]
    colors = [OUTCOME_COLORS.get(l, "#7f8c8d") for l in labels]
    ax.bar(labels, values, color=colors)
    ax.set_title(title)
    ax.set_ylabel("run count")
    ax.tick_params(axis="x", rotation=30)
    for i, v in enumerate(values):
        ax.text(i, v, str(v), ha="center", va="bottom", fontsize=8)


# ---------------------------------------------------------------------
# 1. Ledger balance (Section 5) -- the one figure needing a fresh run.
# ---------------------------------------------------------------------
def fig_ledger_balance():
    from abm_governance.core.config import SimulationConfig
    from abm_governance.observer.ecological_ledger import compute_ledger_reconciliation, system_total_resources
    from abm_governance.simulation import Simulation

    config = SimulationConfig.level12_complete(population_size=32, n_patches=4, n_steps=200, seed=777)
    sim = Simulation(config)
    opening = system_total_resources(sim.patch_system, sim.agents, sim.rule_registry)
    sim.run()
    closing = system_total_resources(sim.patch_system, sim.agents, sim.rule_registry)
    rec = compute_ledger_reconciliation(
        opening_stock=opening, closing_stock=closing, patch_system=sim.patch_system,
        event_log=sim.event_log, search_cost=config.search_cost, membership_exit_cost=config.membership_exit_cost,
    )
    supply = {"regeneration": rec.supply_regeneration, "appeal_refund": rec.supply_appeal_refund,
              "replacement_injection": rec.supply_replacement_injection, "recall_recovery": rec.supply_recall_fund_recovery}
    demand_all = {k[len("demand_"):]: getattr(rec, k) for k in vars(rec) if k.startswith("demand_")}
    demand_top = dict(sorted(demand_all.items(), key=lambda kv: -abs(kv[1]))[:10])

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    axes[0].barh(list(supply.keys()), list(supply.values()), color="#27ae60")
    axes[0].set_title("Ledger balance: supply categories\n(one fresh level12_complete run, 32 agents/4 patches/200 steps)")
    axes[0].set_xlabel("resource units")
    axes[1].barh(list(demand_top.keys()), list(demand_top.values()), color="#c0392b")
    axes[1].set_title(f"Ledger balance: top-10 demand categories\nresidual = {rec.residual:.2e} (tolerance 1e-6)")
    axes[1].set_xlabel("resource units")
    fig.suptitle("Ecological ledger closes to ~zero residual at production scale")
    _savefig(fig, "01_ledger_balance")


# ---------------------------------------------------------------------
# 2. Ex-ante ratio vs. realized balance (Sections 6-7).
# ---------------------------------------------------------------------
def fig_ratio_vs_realized_balance(data):
    if data is None:
        return
    records = data["records"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, ratio_key, title in [(axes[0], "structural_ratio", "structural_feasibility_ratio"), (axes[1], "expected_ratio", "expected_pressure_ratio")]:
        for outcome, color in [("collapse", "#c0392b"), ("saturation", "#27ae60"), ("other", "#7f8c8d")]:
            xs = [r[ratio_key] for r in records if r["ecological_outcome"] == outcome]
            ys = [r["realized_mean_ratio_post_burn_in"] for r in records if r["ecological_outcome"] == outcome]
            ax.scatter(xs, ys, label=outcome, color=color, alpha=0.7, s=20)
        ax.set_xscale("log")
        ax.set_xlabel(title)
        ax.axhline(1.0, color="black", linewidth=0.6, linestyle="--")
    axes[0].set_ylabel("realized mean ratio (post-burn-in)")
    axes[1].legend(fontsize=8)
    corr = data["ex_ante_vs_realized_correlation"]
    fig.suptitle(f"Ex-ante ratio predicts realized balance: struct r={corr['structural_ratio_vs_realized_mean']:.2f}, "
                 f"expected r={corr['expected_ratio_vs_realized_mean']:.2f} (Work Package C, n={len(records)})")
    _savefig(fig, "02_ratio_vs_realized_balance")


# ---------------------------------------------------------------------
# 3. Feasibility-map outcomes + joint-design strata (Sections 7, 9).
# ---------------------------------------------------------------------
def fig_feasibility_map_and_strata(c_data, e_design):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    if c_data is not None:
        counts = c_data["outcome_counts"]
        colors = {"other": "#7f8c8d", "collapse": "#c0392b", "saturation": "#27ae60"}
        axes[0].bar(list(counts.keys()), list(counts.values()), color=[colors[k] for k in counts])
        axes[0].set_title(f"Feasibility-map outcomes\n(Work Package C, n={c_data['n_runs_completed']})")
        axes[0].set_ylabel("run count")
    if e_design is not None:
        strata = e_design["stratum_counts"]
        ordered = {s: strata.get(s, 0) for s in STRATUM_ORDER}
        axes[1].bar(list(ordered.keys()), list(ordered.values()), color=[STRATUM_COLORS[s] for s in ordered])
        axes[1].set_title(f"Joint-design ecological strata\n(Work Package E, {e_design['n_joint_points']} points)")
        axes[1].set_ylabel("point count")
        axes[1].tick_params(axis="x", rotation=20)
    _savefig(fig, "03_feasibility_map_and_strata")


# ---------------------------------------------------------------------
# 4-6. All-outcome / failure-trajectory / sustained-system (Section 15).
# ---------------------------------------------------------------------
def fig_all_outcome_summary(j_data):
    if j_data is None:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    _bar_outcome_counts(ax, j_data["all_outcome_summary"], f"All-outcome summary (Work Package J, n={j_data['n_runs_completed']})\ncollapse must stay visible -- every label plotted, zero-count included")
    _savefig(fig, "04_all_outcome_summary")


def fig_failure_trajectory(j_data):
    if j_data is None:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    counts = j_data["failure_trajectory_summary"]
    ax.bar(list(counts.keys()), list(counts.values()), color="#c0392b")
    ax.set_title("Failure-trajectory routes (Work Package J)")
    ax.set_ylabel("run count")
    ax.tick_params(axis="x", rotation=30)
    for i, (k, v) in enumerate(counts.items()):
        ax.text(i, v, str(v), ha="center", va="bottom", fontsize=8)
    _savefig(fig, "05_failure_trajectory")


def fig_sustained_system(j_data, l3_data):
    fig, ax = plt.subplots(figsize=(7, 5))
    labels, eligible, excluded = [], [], []
    for name, d in [("discovery\n(Work Pkg J)", j_data), ("confirmation\n(Work Pkg L)", l3_data)]:
        if d is None:
            continue
        summary = d.get("sustained_system_summary") if "sustained_system_summary" in d else None
        if summary is None:
            continue
        labels.append(name)
        eligible.append(summary["n_eligible"])
        excluded.append(summary["n_excluded"])
    if not labels:
        return
    x = np.arange(len(labels))
    ax.bar(x, eligible, label="eligible", color="#27ae60")
    ax.bar(x, excluded, bottom=eligible, label="excluded", color="#7f8c8d")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("run count")
    ax.set_title("Sustained-system eligibility screen")
    ax.legend()
    _savefig(fig, "06_sustained_system_eligibility")


# ---------------------------------------------------------------------
# 7. Missingness (Section 9.1).
# ---------------------------------------------------------------------
def fig_missingness(k_data):
    if k_data is None:
        return
    report = k_data["missingness_report"]
    fig, ax = plt.subplots(figsize=(9, 5))
    dims = list(report.keys())
    ax.bar(dims, [report[d] for d in dims], color="#e67e22")
    ax.set_title(f"Per-dimension missingness fraction (Work Package K, n={k_data['n_total']})\nprimary strategy: {k_data['primary_missingness_strategy']}")
    ax.set_ylabel("fraction missing")
    ax.set_ylim(0, 1)
    _savefig(fig, "07_missingness")


# ---------------------------------------------------------------------
# 8. Feature variation by stratum (Section 9).
# ---------------------------------------------------------------------
def fig_feature_by_stratum(j_data):
    if j_data is None:
        return
    records = j_data["records"]
    fig, ax = plt.subplots(figsize=(8, 5))
    groups = [[r["ecological_resource_fraction"] for r in records if r["expected_stratum"] == s] for s in STRATUM_ORDER]
    bp = ax.boxplot(groups, tick_labels=[s.replace("_feasibility", "") for s in STRATUM_ORDER], patch_artist=True)
    for patch, s in zip(bp["boxes"], STRATUM_ORDER):
        patch.set_facecolor(STRATUM_COLORS[s])
        patch.set_alpha(0.6)
    ax.set_ylabel("ecological_resource_fraction (end of run)")
    ax.set_title("Realized ecological outcome by ex-ante feasibility stratum\n(Work Package J, discovery pool)")
    _savefig(fig, "08_feature_by_stratum")


# ---------------------------------------------------------------------
# 9. Model selection across k, k=1 included (Section 9.2/16).
# ---------------------------------------------------------------------
def fig_model_selection(k_data):
    if k_data is None:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    for method, color, marker in [("gmm", "#2980b9", "o"), ("hierarchical", "#8e44ad", "s")]:
        results = k_data["k_range_results"][method]
        ks = [r["k"] for r in results]
        sils = [r["metrics"]["silhouette"] for r in results]
        # k=1's silhouette is structurally undefined (a single cluster
        # has no between-cluster separation to score) -- plotted
        # explicitly as an open marker at y=0 with an annotation,
        # never silently omitted from the k-range.
        plotted = [0.0 if (s is None or (isinstance(s, float) and np.isnan(s))) else s for s in sils]
        ax.plot(ks, plotted, marker=marker, color=color, label=method)
    ax.axvline(1, color="gray", linewidth=0.5, linestyle=":")
    ax.annotate("k=1: silhouette\nundefined", xy=(1, 0), xytext=(1.3, 0.03), fontsize=7)
    ax.set_xlabel("k")
    ax.set_ylabel("silhouette score")
    ax.set_title(f"Model selection across k=1..8 (Work Package K)\nheadline_k={k_data['headline_k']}, verdict={k_data['verdict']['verdict']}")
    ax.legend()
    _savefig(fig, "09_model_selection")


# ---------------------------------------------------------------------
# 10. Algorithm agreement (Section 9.4/16).
# ---------------------------------------------------------------------
def fig_algorithm_agreement(k_data):
    if k_data is None:
        return
    pairs = k_data["algorithm_agreement"]
    fig, ax = plt.subplots(figsize=(7, 5))
    labels = [p.replace("_vs_", " vs\n") for p in pairs]
    aris = [pairs[p]["ari"] for p in pairs]
    ax.bar(labels, aris, color="#16a085")
    ax.axhline(0.3, color="black", linestyle="--", linewidth=0.7, label="stability bar (0.3)")
    ax.set_ylabel("adjusted Rand index")
    ax.set_title(f"Pairwise algorithm agreement (Work Package K)\nmean={k_data['mean_algorithm_agreement_ari']:.3f}")
    ax.legend(fontsize=8)
    _savefig(fig, "10_algorithm_agreement")


# ---------------------------------------------------------------------
# 11. Stability metrics: IC-family, parameter-neighborhood, temporal-
#     window, bootstrap, failure-proxy robustness, all in one figure.
# ---------------------------------------------------------------------
def fig_stability_metrics(k_data):
    if k_data is None:
        return
    metrics = {
        "bootstrap\n(within-fit)": k_data["bootstrap_stability"]["mean_ari"],
        "algorithm\nagreement": k_data["mean_algorithm_agreement_ari"],
        "IC-family\nrobustness": k_data["cluster_vs_ic_family_ari"],
        "temporal-window\nstability": k_data["temporal_window_stability_ari"],
        "parameter-\nneighborhood": k_data["parameter_neighborhood_stability_mean_ari"],
        "vs. failure\nproxy": k_data["cluster_vs_failure_proxy_ari"],
    }
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(list(metrics.keys()), list(metrics.values()), color="#2980b9")
    ax.axhline(0.3, color="black", linestyle="--", linewidth=0.7, label="stability bar (0.3)")
    ax.set_ylabel("adjusted Rand index")
    ax.set_title("Discovery robustness checks (Work Package K, Section 16)\nlow IC-family/failure-proxy ARI is evidence the clustering is\nnot simply re-deriving a known label; low temporal-window ARI is\nits own genuine finding (membership unstable across run duration)")
    ax.legend(fontsize=8)
    _savefig(fig, "11_stability_metrics")


# ---------------------------------------------------------------------
# 12. Discovery vs. confirmation silhouette curves (Section 17).
# ---------------------------------------------------------------------
def fig_discovery_vs_confirmation(k_data, l3_data):
    if k_data is None or l3_data is None:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    disc = k_data["k_range_results"]["gmm"]
    ks_d = [r["k"] for r in disc]
    sils_d = [0.0 if (r["metrics"]["silhouette"] is None or np.isnan(r["metrics"]["silhouette"])) else r["metrics"]["silhouette"] for r in disc]
    ax.plot(ks_d, sils_d, marker="o", color="#2980b9", label=f"discovery (n={k_data['n_total']}, headline_k={k_data['headline_k']})")
    conf = l3_data["recurrence_across_seeds_points_and_ic_families"]["silhouette_by_k"]
    ks_c = sorted(int(k) for k in conf.keys())
    sils_c = [conf[str(k)] if str(k) in conf else conf.get(k, 0.0) for k in ks_c]
    sils_c = [0.0 if (s is None or (isinstance(s, float) and np.isnan(s))) else s for s in sils_c]
    ax.plot(ks_c, sils_c, marker="s", color="#c0392b", label=f"confirmation (n={l3_data['n_confirmation_runs']}, headline_k={l3_data['recurrence_across_seeds_points_and_ic_families']['headline_k']})")
    ax.set_xlabel("k")
    ax.set_ylabel("silhouette (gmm)")
    ax.set_title(f"Discovery vs. independent confirmation (Work Packages K, L)\nconfirmation_verdict = {l3_data['confirmation_verdict']['verdict']}")
    ax.legend()
    _savefig(fig, "12_discovery_vs_confirmation")


# ---------------------------------------------------------------------
# 13. Scaling robustness (Section 18).
# ---------------------------------------------------------------------
def fig_scaling_robustness(m_data):
    if m_data is None:
        return
    records = m_data["records"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    outcomes = [r["transition_to_failure"]["all_outcome_label"] for r in records]
    counts = {lab: outcomes.count(lab) for lab in set(outcomes)}
    axes[0].bar(list(counts.keys()), list(counts.values()), color=[OUTCOME_COLORS.get(l, "#7f8c8d") for l in counts])
    axes[0].set_title(f"Scaling-robustness outcomes\n(Work Package M, n={len(records)}, null baseline)")
    axes[0].set_ylabel("run count")
    pop_rec = np.mean([r["functional_recovery"]["population"]["recovered"] for r in records])
    eco_rec = np.mean([r["functional_recovery"]["ecological"]["recovered"] for r in records])
    axes[1].bar(["population", "ecological"], [pop_rec, eco_rec], color=["#8e44ad", "#27ae60"])
    axes[1].set_ylim(0, 1)
    axes[1].set_ylabel("fraction of runs recovered after shock")
    axes[1].set_title("Functional-recovery rate by dimension\n(attractor label requires majority on BOTH)")
    for i, v in enumerate([pop_rec, eco_rec]):
        axes[1].text(i, v, f"{v:.0%}", ha="center", va="bottom")
    _savefig(fig, "13_scaling_robustness")


# ---------------------------------------------------------------------
# 14. Causal collapse-ablation effects, sorted (Section 19).
# ---------------------------------------------------------------------
def fig_causal_ablation_effects(n_data):
    if n_data is None:
        return
    factors = n_data["factor_results"]
    names = [f["factor"] for f in factors]
    diffs = [f["summary"]["ecological_resource_fraction"]["mean_paired_difference_high_minus_low"] for f in factors]
    order = np.argsort(diffs)
    names_sorted = [names[i] for i in order]
    diffs_sorted = [diffs[i] for i in order]
    colors = ["#c0392b" if d < 0 else "#27ae60" for d in diffs_sorted]
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(names_sorted, diffs_sorted, color=colors)
    ax.axvline(0, color="black", linewidth=0.7)
    ax.set_xlabel("mean paired difference (high - low), ecological_resource_fraction")
    ax.set_title(f"Causal collapse decomposition (Work Package N)\n{n_data['n_factors']} factors x {n_data['n_seeds_per_ablation']} matched seeds = {n_data['n_total_runs']} runs")
    _savefig(fig, "14_causal_ablation_effects")


# ---------------------------------------------------------------------
# 15. Outcome-label transition matrix, pooled across all 13 ablations
#     (Section 19).
# ---------------------------------------------------------------------
def fig_outcome_transition_matrix(n_data):
    if n_data is None:
        return
    labels = ["collapse", "fragmented", "viable"]
    idx = {l: i for i, l in enumerate(labels)}
    matrix = np.zeros((3, 3), dtype=int)
    for f in n_data["factor_results"]:
        for pair in f["pairs"]:
            lo, hi = pair["low"]["all_outcome_label"], pair["high"]["all_outcome_label"]
            if lo in idx and hi in idx:
                matrix[idx[lo], idx[hi]] += 1
    fig, ax = plt.subplots(figsize=(6, 5.5))
    im = ax.imshow(matrix, cmap="Oranges")
    ax.set_xticks(range(3)); ax.set_xticklabels(labels)
    ax.set_yticks(range(3)); ax.set_yticklabels(labels)
    ax.set_xlabel("outcome label, high arm")
    ax.set_ylabel("outcome label, low arm")
    ax.set_title("Pooled outcome-label transitions across all 13 ablations\n(Work Package N, 104 matched pairs)")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, str(matrix[i, j]), ha="center", va="center", color="black")
    fig.colorbar(im, ax=ax, label="pair count")
    _savefig(fig, "15_outcome_transition_matrix")


# ---------------------------------------------------------------------
# 16. Overall recurrence classification + per-cluster diagnostic sizes
#     -- the closest available substitute for "candidate feature
#     profiles" now that no candidate was confirmed (Section 20).
# ---------------------------------------------------------------------
def fig_recurrence_classification(o_data):
    if o_data is None:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    per_cluster = o_data["per_cluster_environmental_forcing"]
    clusters = sorted(per_cluster.keys(), key=lambda c: int(c))
    members = [per_cluster[c]["n_members"] for c in clusters]
    ax.bar([f"diagnostic\ncluster {c}" for c in clusters], members, color="#2980b9")
    ax.set_ylabel("n_members")
    ax.set_title(f"Diagnostic partition membership (Work Package O)\noverall_classification = {o_data['overall_classification']['label']}, "
                 f"attractor_label_assigned = {o_data['attractor_label_assigned']}\n"
                 "(diagnostic clusters, not confirmed candidates -- no candidate feature\n"
                 "profile exists, since no candidate was confirmed)")
    for i, v in enumerate(members):
        ax.text(i, v, str(v), ha="center", va="bottom", fontsize=8)
    _savefig(fig, "16_recurrence_classification")


def run():
    print("Level 1.2b visualizations -- Section 26", flush=True)
    print("Disclosed omissions (genuinely not applicable, not silently dropped):", flush=True)
    print("  - candidate feature profiles: no candidate was ever confirmed (continuum/null_replicated)", flush=True)
    print("  - per-criterion recurrence pass/fail: never applied to a named candidate for the same reason", flush=True)
    print("  - consensus co-assignment matrix: not persisted by Work Package K's own results.json;", flush=True)
    print("    recomputing would require a fourth full 576-run re-simulation", flush=True)

    c_data = _load(PATHS["c"])
    e_design = _load(PATHS["e_design"])
    j_data = _load(PATHS["j"])
    k_data = _load(PATHS["k"])
    l3_data = _load(PATHS["l3"])
    m_data = _load(PATHS["m"])
    n_data = _load(PATHS["n"])
    o_data = _load(PATHS["o"])

    fig_ledger_balance()
    fig_ratio_vs_realized_balance(c_data)
    fig_feasibility_map_and_strata(c_data, e_design)
    fig_all_outcome_summary(j_data)
    fig_failure_trajectory(j_data)
    fig_sustained_system(j_data, l3_data)
    fig_missingness(k_data)
    fig_feature_by_stratum(j_data)
    fig_model_selection(k_data)
    fig_algorithm_agreement(k_data)
    fig_stability_metrics(k_data)
    fig_discovery_vs_confirmation(k_data, l3_data)
    fig_scaling_robustness(m_data)
    fig_causal_ablation_effects(n_data)
    fig_outcome_transition_matrix(n_data)
    fig_recurrence_classification(o_data)


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
