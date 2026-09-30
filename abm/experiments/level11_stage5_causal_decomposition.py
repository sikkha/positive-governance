#!/usr/bin/env python3
"""Level 1.1, Stage 5: causal decomposition via matched-seed
counterfactuals.

Isolates each mechanism's own causal contribution by comparing
``level11_complete`` against a single-mechanism ablation on the *same*
seed (same underlying RNG trajectory up to the point the ablated
mechanism's own draws are skipped), using
``observer/delegation_diagnostics.py::functional_effect`` and
``observer/replication_units.py::seed_clustered_bootstrap_ci`` for an
uncertainty interval around each contrast -- distinct from Stage 2's
un-interval'd point estimates (Stage 2 is exploratory; this stage adds
the confirmatory-grade uncertainty quantification Work Package A
requires before any causal claim is reported).

Session-budget scope reduction (disclosed): 15 matched seeds per
contrast (more than Stage 2's 10, since this stage's own claims carry
uncertainty intervals rather than a bare point estimate); population 40,
3 patches, 350 steps.
"""

from __future__ import annotations

import json

from abm_governance.core.config import SimulationConfig
from experiments.level11_common import ensure_dir, run_and_summarize
from abm_governance.observer import replication_units as ru

OUT_DIR = "outputs/level11_stage5_causal_decomposition"
N_SEEDS = 15
N_STEPS = 350
POPULATION = 40
N_PATCHES = 3

CONTRASTS = {
    "discretion_effect": (
        SimulationConfig.level11_complete,
        lambda **kw: SimulationConfig.level11_complete(discretion_enabled=False, **kw),
    ),
    "accountability_effect": (
        SimulationConfig.level11_complete,
        SimulationConfig.level11_no_accountability,
    ),
    "admin_cost_effect": (
        SimulationConfig.level11_complete,
        SimulationConfig.level11_no_admin_cost,
    ),
    "interpatch_coordination_effect": (
        SimulationConfig.level11_complete,
        SimulationConfig.level11_no_interpatch_coordination,
    ),
}

OUTCOME_PATHS = {
    "final_occupancy": ("ecological_outcomes", "final_occupancy"),
    "final_total_resources": ("ecological_outcomes", "final_total_resources"),
    "total_appropriated_resources": ("delegation_metrics", "effective_constraint", "total_appropriated_resources"),
    "mean_member_resources": ("welfare_accounting", "mean_member_resources"),
    "population_weighted_overall_mean": ("welfare_accounting", "population_weighted_overall_mean"),
}


def _extract(run_out, path):
    v = run_out
    for key in path:
        v = v[key]
    return v


def run() -> dict:
    ensure_dir(OUT_DIR)
    report = {"n_seeds": N_SEEDS, "n_steps": N_STEPS, "contrasts": {}}
    for name, (full_builder, ablated_builder) in CONTRASTS.items():
        full_by_outcome = {k: [] for k in OUTCOME_PATHS}
        ablated_by_outcome = {k: [] for k in OUTCOME_PATHS}
        for seed in range(N_SEEDS):
            real_seed = 5000 + seed
            cfg_full = full_builder(population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=real_seed)
            cfg_ablated = ablated_builder(population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=real_seed)
            out_full = run_and_summarize(cfg_full)
            out_ablated = run_and_summarize(cfg_ablated)
            for outcome_name, path in OUTCOME_PATHS.items():
                full_by_outcome[outcome_name].append(_extract(out_full, path))
                ablated_by_outcome[outcome_name].append(_extract(out_ablated, path))

        contrast_result = {}
        for outcome_name in OUTCOME_PATHS:
            deltas_by_seed = {
                seed: [ablated_by_outcome[outcome_name][seed] - full_by_outcome[outcome_name][seed]]
                for seed in range(N_SEEDS)
            }
            ci = ru.seed_clustered_bootstrap_ci(deltas_by_seed, n_boot=1000)
            excludes_zero = (ci["ci_low"] > 0) or (ci["ci_high"] < 0)
            contrast_result[outcome_name] = {
                "mean_delta_ablated_minus_full": ci["point_estimate"],
                "ci_low": ci["ci_low"], "ci_high": ci["ci_high"], "n_seeds": ci["n_seeds"],
                "excludes_zero": excludes_zero,
            }
        report["contrasts"][name] = contrast_result
        print(f"{name}: {contrast_result}", flush=True)

    with open(f"{OUT_DIR}/stage5_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
