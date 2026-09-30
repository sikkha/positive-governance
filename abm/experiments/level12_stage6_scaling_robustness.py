#!/usr/bin/env python3
"""Level 1.2, Stage 6: scaling / initial-condition robustness.

Tests whether Stages 3-5's near-universal-collapse finding is scale-
dependent or holds across population/patch-count conditions. Varies
SCALE only (population, patch count) — every other generative
parameter is held at its default, deliberately NOT re-running Stage 3's
own 8-dimensional parameter sweep at each scale (that would be a much
larger, separate study; this stage's own scope is robustness-to-scale
of the already-observed dynamic, not a second full search).

**Disclosed scope reduction**: Stage 0's frozen manifest commits to
`population_conditions: [40, 80]`, `n_patches_conditions: [3, 6]`
(4 combinations) and `n_seeds: 6`. Interpreted here as 2 seeds per
combination (8 total runs) rather than a literal, unevenly-divisible
6/4 split — recorded before running, matching Stage 3/5's own
disclosed-interpretation precedent. `n_steps` is additionally reduced
to 300 (from Stage 3/5's 500) specifically to bound the population=80
condition's runtime within this session's compute budget."""

from __future__ import annotations

import json

from abm_governance.core.config import SimulationConfig
from experiments.level12_common import ensure_dir, run_and_summarize
from experiments.level12_preregistration import load_and_verify_manifest

OUT_DIR = "outputs/level12_stage6_scaling_robustness"
POPULATION_CONDITIONS: tuple[int, ...] = (40, 80)
N_PATCHES_CONDITIONS: tuple[int, ...] = (3, 6)
N_SEEDS_PER_CONDITION = 2
N_STEPS = 300
SEED_BASE = 7000


def _build_config(population: int, n_patches: int, seed_idx: int, condition_id: int) -> SimulationConfig:
    return SimulationConfig.level11_complete(
        population_size=population, n_steps=N_STEPS, n_patches=n_patches,
        seed=SEED_BASE + condition_id * 100 + seed_idx, rng_mode="mechanism_substreams",
        institutional_observation_enabled=True, institutional_transmission_enabled=True,
        migration_enabled=True, membership_exit_enabled=True, institutional_scaling_enabled=True,
    )


def run() -> dict:
    ensure_dir(OUT_DIR)
    load_and_verify_manifest()  # hard stop if Stage 0's frozen manifest was altered

    conditions = []
    for condition_id, population in enumerate(POPULATION_CONDITIONS):
        for n_patches in N_PATCHES_CONDITIONS:
            conditions.append({"condition_id": len(conditions), "population": population, "n_patches": n_patches})

    per_condition = []
    for cond in conditions:
        seed_results = []
        for seed_idx in range(N_SEEDS_PER_CONDITION):
            config = _build_config(cond["population"], cond["n_patches"], seed_idx, cond["condition_id"])
            out = run_and_summarize(config)
            seed_results.append({
                "seed": config.seed, "all_outcome_label": out["all_outcome_label"],
                "population_alive_fraction": out["population_alive_fraction"],
                "ecological_resource_fraction": out["ecological_resource_fraction"],
                "n_institutions_ever_formed": out["n_institutions_ever_formed"],
                "n_institutions_active_at_end": out["n_institutions_active_at_end"],
            })
        outcome_counts = {}
        for r in seed_results:
            outcome_counts[r["all_outcome_label"]] = outcome_counts.get(r["all_outcome_label"], 0) + 1
        per_condition.append({**cond, "seed_results": seed_results, "outcome_label_counts": outcome_counts})
        print(f"population={cond['population']} n_patches={cond['n_patches']}: {outcome_counts}", flush=True)

    report = {
        "population_conditions": list(POPULATION_CONDITIONS), "n_patches_conditions": list(N_PATCHES_CONDITIONS),
        "n_seeds_per_condition": N_SEEDS_PER_CONDITION, "n_steps": N_STEPS,
        "per_condition": per_condition,
    }
    with open(f"{OUT_DIR}/stage6_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
