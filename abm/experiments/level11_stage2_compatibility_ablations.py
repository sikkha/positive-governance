#!/usr/bin/env python3
"""Level 1.1, Stage 2: exact-compatibility check + mechanism ablations.

Part A confirms ``level10_compat`` (every Level 1.1 flag left at its
no-op default) is byte-for-byte identical, per seed, to
``level1_rule_formation_default`` -- the same claim
``tests/test_level11_compatibility.py`` makes at unit-test scale, run
here at experiment scale (20 seeds) as this stage's own confirmatory
record.

Part B runs ``level11_complete`` against four single-mechanism
ablations (``level11_no_memory``, ``level11_no_accountability``,
``level11_no_admin_cost``, ``level11_no_interpatch_coordination``) on
matched seeds and reports each ablation's functional effect (Work
Package J) on final occupancy, final total resources, and total
appropriated resources -- exploratory only (Stage 2, not Stage 4's
confirmatory replication); no claim here is treated as confirmed without
Stage 4 re-running it on fresh seeds.

Session-budget scope reduction (disclosed): 20 seeds for the
compatibility check, 10 matched seeds per ablation; population 40, 3
patches, 350 steps.
"""

from __future__ import annotations

import json

import numpy as np

from abm_governance.core.config import SimulationConfig
from abm_governance.observer import delegation_diagnostics as dd
from abm_governance.simulation import Simulation
from experiments.level11_common import ensure_dir, run_and_summarize


def _metrics_identical(metrics_a: list[dict], metrics_b: list[dict]) -> bool:
    """Row-by-row, field-by-field comparison with NaN treated as equal to
    NaN (``np.nan == np.nan`` is ``False`` in plain Python/dict equality,
    which would otherwise make an ordinary occupancy/welfare NaN cell
    register as a false mismatch -- mirrors
    ``tests/test_level11_compatibility.py``'s own comparison)."""
    if len(metrics_a) != len(metrics_b):
        return False
    for row_a, row_b in zip(metrics_a, metrics_b):
        if row_a.keys() != row_b.keys():
            return False
        for key in row_a:
            v1, v2 = row_a[key], row_b[key]
            if isinstance(v1, float) and np.isnan(v1):
                if not (isinstance(v2, float) and np.isnan(v2)):
                    return False
            elif v1 != v2:
                return False
    return True

OUT_DIR = "outputs/level11_stage2_compatibility_ablations"
N_SEEDS_COMPAT = 20
N_SEEDS_ABLATION = 10
N_STEPS = 350
POPULATION = 40
N_PATCHES = 3


def _run_compatibility_check() -> dict:
    mismatches = []
    for seed in range(N_SEEDS_COMPAT):
        cfg_a = SimulationConfig.level1_rule_formation_default(
            population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=2000 + seed,
        )
        cfg_b = SimulationConfig.level10_compat(
            population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=2000 + seed,
        )
        result_a = Simulation(cfg_a).run()
        result_b = Simulation(cfg_b).run()
        identical = _metrics_identical(result_a.metrics, result_b.metrics)
        if not identical:
            mismatches.append(seed)
    return {
        "n_seeds": N_SEEDS_COMPAT,
        "n_mismatches": len(mismatches),
        "mismatched_seeds": mismatches,
        "byte_for_byte_identical": len(mismatches) == 0,
    }


ABLATIONS = {
    "level11_no_memory": SimulationConfig.level11_no_memory,
    "level11_no_accountability": SimulationConfig.level11_no_accountability,
    "level11_no_admin_cost": SimulationConfig.level11_no_admin_cost,
    "level11_no_interpatch_coordination": SimulationConfig.level11_no_interpatch_coordination,
}


def _run_ablations() -> dict:
    complete_runs = []
    ablation_runs = {name: [] for name in ABLATIONS}
    for seed in range(N_SEEDS_ABLATION):
        real_seed = 3000 + seed
        cfg_complete = SimulationConfig.level11_complete(
            population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=real_seed,
        )
        complete_runs.append(run_and_summarize(cfg_complete))
        for name, builder in ABLATIONS.items():
            cfg = builder(population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=real_seed)
            ablation_runs[name].append(run_and_summarize(cfg))

    def _extract(runs, path):
        vals = []
        for r in runs:
            v = r
            for key in path:
                v = v[key] if isinstance(v, dict) else getattr(v, key)
            vals.append(v)
        return vals

    outcome_paths = {
        "final_occupancy": ("ecological_outcomes", "final_occupancy"),
        "final_total_resources": ("ecological_outcomes", "final_total_resources"),
        "total_appropriated_resources": ("delegation_metrics", "effective_constraint", "total_appropriated_resources"),
        "total_administrative_cost": ("delegation_metrics", "administrative_extraction", "total_administrative_cost"),
    }
    complete_values = {name: _extract(complete_runs, path) for name, path in outcome_paths.items()}
    effects = {}
    for name in ABLATIONS:
        effects[name] = {}
        for outcome_name, path in outcome_paths.items():
            ablation_values = _extract(ablation_runs[name], path)
            effects[name][outcome_name] = dd.functional_effect(ablation_values, complete_values[outcome_name])
    return {
        "n_seeds": N_SEEDS_ABLATION,
        "complete_values": complete_values,
        "effects_vs_complete": effects,
    }


def run() -> dict:
    ensure_dir(OUT_DIR)
    print("Part A: compatibility check...", flush=True)
    compat = _run_compatibility_check()
    print(f"compatibility: {compat}", flush=True)
    print("Part B: ablations...", flush=True)
    ablations = _run_ablations()
    for name, effect in ablations["effects_vs_complete"].items():
        print(f"{name}: {effect}", flush=True)
    report = {"compatibility_check": compat, "ablations": ablations}
    with open(f"{OUT_DIR}/stage2_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
