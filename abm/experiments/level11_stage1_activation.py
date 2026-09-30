#!/usr/bin/env python3
"""Level 1.1, Stage 1: mechanism activation.

Confirms each Work Package D-I mechanism actually fires (produces > 0 of
its own defining events) when its governing config flag is enabled, and
produces *zero* of those events when left at the Level-1.0-compatible
default -- the first, most basic experimental claim this milestone can
make, before any comparison or search. Session-budget scope reduction
(disclosed): 8 seeds per condition, population 40, 3 patches, 350 steps
-- far short of a publication-scale sweep, but sufficient to demonstrate
each mechanism is reachable and inert-by-default across multiple
independent seeds, which is this stage's only purpose.
"""

from __future__ import annotations

import json

from abm_governance.core.config import SimulationConfig
from experiments.level11_common import ensure_dir, run_and_summarize

OUT_DIR = "outputs/level11_stage1_activation"
N_SEEDS = 8
N_STEPS = 350
POPULATION = 40
N_PATCHES = 3

CONDITIONS = {
    "level10_compat": lambda seed: SimulationConfig.level10_compat(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed,
    ),
    "level11_delegation_only": lambda seed: SimulationConfig.level11_delegation_only(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed,
    ),
    "level11_accountability_only": lambda seed: SimulationConfig.level11_accountability_only(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed,
    ),
    "level11_coordination_only": lambda seed: SimulationConfig.level11_coordination_only(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed,
    ),
    "level11_complete": lambda seed: SimulationConfig.level11_complete(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed,
    ),
}

#: Which activity counters each condition is expected to be non-zero for
#: (across at least one seed -- Constraint 4/9 forbids mechanical
#: certainty, so "fires at least once across 8 seeds," never "every
#: seed," is the honest claim).
EXPECTED_NONZERO = {
    "level10_compat": [],
    "level11_delegation_only": ["n_nominations", "n_appointments", "n_task_performances"],
    "level11_accountability_only": ["n_appointments", "n_audits", "n_recalls", "n_appeals"],
    "level11_coordination_only": ["n_coordination_proposals"],
    "level11_complete": [
        "n_nominations", "n_appointments", "n_task_performances", "n_audits", "n_recalls",
        "n_contributions", "n_coordination_proposals",
    ],
}
#: Counters that must be exactly zero for the *disabled* mechanism in
#: every condition where that mechanism is off.
EXPECTED_ZERO = {
    "level10_compat": [
        "n_nominations", "n_appointments", "n_task_performances", "n_audits", "n_recalls",
        "n_appeals", "n_contributions", "n_coordination_proposals",
    ],
    "level11_delegation_only": ["n_audits", "n_recalls", "n_appeals", "n_contributions", "n_coordination_proposals"],
    "level11_accountability_only": ["n_contributions", "n_coordination_proposals"],
    "level11_coordination_only": ["n_nominations", "n_appointments", "n_task_performances", "n_contributions"],
}


def run() -> dict:
    ensure_dir(OUT_DIR)
    report = {"n_seeds": N_SEEDS, "n_steps": N_STEPS, "population": POPULATION, "n_patches": N_PATCHES, "conditions": {}}
    for name, builder in CONDITIONS.items():
        seed_results = []
        for seed in range(N_SEEDS):
            config = builder(1000 + seed)
            out = run_and_summarize(config)
            seed_results.append({k: v for k, v in out.items() if k.startswith("n_")})
        totals = {k: sum(r[k] for r in seed_results) for k in seed_results[0]}
        any_nonzero = {k: any(r[k] > 0 for r in seed_results) for k in seed_results[0]}
        checks = {
            "expected_nonzero_confirmed": {
                k: any_nonzero.get(k, False) for k in EXPECTED_NONZERO.get(name, [])
            },
            "expected_zero_confirmed": {
                k: totals.get(k, 0) == 0 for k in EXPECTED_ZERO.get(name, [])
            },
        }
        report["conditions"][name] = {"totals": totals, "checks": checks, "per_seed": seed_results}
        all_nonzero_ok = all(checks["expected_nonzero_confirmed"].values())
        all_zero_ok = all(checks["expected_zero_confirmed"].values())
        print(
            f"{name}: nonzero_confirmed={all_nonzero_ok} zero_confirmed={all_zero_ok} "
            f"totals={totals}", flush=True,
        )
    with open(f"{OUT_DIR}/stage1_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
