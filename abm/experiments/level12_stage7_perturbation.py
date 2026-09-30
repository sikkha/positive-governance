#!/usr/bin/env python3
"""Level 1.2, Stage 7: perturbation / transition analysis.

Applies a mid-run shock and observes whether a run's ``all_outcome_
label`` transitions as a result, and whether the ecological/population
trajectory recovers after the shock ends.

**Disclosed constraint, discovered while building this stage (not
worked around)**: the pre-existing generic perturbation interface
(``core/perturbation.py``, Level 0.1/0.2) implements four shock kinds,
but two of them (``resource_depletion``, ``regeneration_reduction``)
only touch ``Simulation.pool`` (the single-pool, non-patches
environment) — gated `if self.pool is not None` in
``simulation.py::_run_one_step``. Level 1.2 always runs with
``ecology_topology="patches"`` (``self.pool is None``), so those two
kinds are structural no-ops for every Level 1.2 condition. The two
remaining kinds, ``observation_noise_increase`` and
``subsistence_increase``, act on agents directly and are NOT pool-
gated — those are this stage's two perturbation types, which
conveniently matches Stage 0's frozen `n_perturbation_types: 2`
commitment exactly, rather than being chosen to make that number work.

**Disclosed scope reduction**: Stage 0 commits to `n_seeds: 6` for this
stage; interpreted as 3 seeds per perturbation type (2 types x 3 = 6
total), matching the literal number exactly this time. Population 40,
4 patches, 400 steps (between Stage 2's 400 and Stage 3/5's 500,
chosen so there is room for a meaningful pre-shock baseline period,
the shock itself, and a post-shock recovery-observation window within
one run)."""

from __future__ import annotations

import json

from abm_governance.core.config import SimulationConfig
from experiments.level12_common import ensure_dir, run_and_summarize
from experiments.level12_preregistration import load_and_verify_manifest

OUT_DIR = "outputs/level12_stage7_perturbation"
POPULATION = 40
N_PATCHES = 4
N_STEPS = 400
N_SEEDS_PER_TYPE = 3
SEED_BASE = 8000

#: Shock window: starts after a substantial pre-shock baseline, lasts
#: 40 steps, leaving 160 steps of post-shock observation before the
#: run ends -- chosen once, before running, not tuned to any outcome.
SHOCK_START_STEP = 200
SHOCK_DURATION = 40
SHOCK_MAGNITUDE = 0.6

PERTURBATION_TYPES: tuple[str, ...] = ("observation_noise_increase", "subsistence_increase")


def _build_config(perturbation_kind: str, seed_idx: int, type_idx: int, with_shock: bool) -> SimulationConfig:
    perturbations = ()
    if with_shock:
        perturbations = (
            {"start_step": SHOCK_START_STEP, "duration": SHOCK_DURATION, "kind": perturbation_kind, "magnitude": SHOCK_MAGNITUDE},
        )
    return SimulationConfig.level11_complete(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES,
        seed=SEED_BASE + type_idx * 100 + seed_idx, rng_mode="mechanism_substreams",
        institutional_observation_enabled=True, institutional_transmission_enabled=True,
        migration_enabled=True, membership_exit_enabled=True, institutional_scaling_enabled=True,
        perturbations=perturbations,
    )


def run() -> dict:
    ensure_dir(OUT_DIR)
    load_and_verify_manifest()  # hard stop if Stage 0's frozen manifest was altered

    results = []
    for type_idx, kind in enumerate(PERTURBATION_TYPES):
        for seed_idx in range(N_SEEDS_PER_TYPE):
            shocked_config = _build_config(kind, seed_idx, type_idx, with_shock=True)
            unshocked_config = _build_config(kind, seed_idx, type_idx, with_shock=False)
            shocked_out = run_and_summarize(shocked_config)
            unshocked_out = run_and_summarize(unshocked_config)
            transitioned = shocked_out["all_outcome_label"] != unshocked_out["all_outcome_label"]
            results.append({
                "perturbation_kind": kind, "seed_idx": seed_idx, "seed": shocked_config.seed,
                "shocked_outcome_label": shocked_out["all_outcome_label"],
                "unshocked_outcome_label": unshocked_out["all_outcome_label"],
                "transitioned": transitioned,
                "shocked_ecological_resource_fraction": shocked_out["ecological_resource_fraction"],
                "unshocked_ecological_resource_fraction": unshocked_out["ecological_resource_fraction"],
                "shocked_population_alive_fraction": shocked_out["population_alive_fraction"],
                "unshocked_population_alive_fraction": unshocked_out["population_alive_fraction"],
            })
            print(
                f"{kind} seed_idx={seed_idx}: shocked={shocked_out['all_outcome_label']} "
                f"unshocked={unshocked_out['all_outcome_label']} transitioned={transitioned}", flush=True,
            )

    n_transitioned = sum(1 for r in results if r["transitioned"])
    by_kind = {}
    for kind in PERTURBATION_TYPES:
        kind_results = [r for r in results if r["perturbation_kind"] == kind]
        by_kind[kind] = {
            "n_transitioned": sum(1 for r in kind_results if r["transitioned"]),
            "n_total": len(kind_results),
        }

    report = {
        "perturbation_types": list(PERTURBATION_TYPES), "n_seeds_per_type": N_SEEDS_PER_TYPE,
        "shock_start_step": SHOCK_START_STEP, "shock_duration": SHOCK_DURATION, "shock_magnitude": SHOCK_MAGNITUDE,
        "n_total_pairs": len(results), "n_transitioned": n_transitioned,
        "transition_rate_by_perturbation_type": by_kind,
        "results": results,
    }
    with open(f"{OUT_DIR}/stage7_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Stage 7 perturbation: {n_transitioned}/{len(results)} shocked/unshocked pairs transitioned outcome label. by_kind={by_kind}", flush=True)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
