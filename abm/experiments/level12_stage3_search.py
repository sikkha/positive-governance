#!/usr/bin/env python3
"""Level 1.2, Stage 3: main open evolutionary search.

The milestone's main data-generating run. **GENERATE FIRST. MEASURE
SECOND. DISCOVER THIRD. INTERPRET LATER.** — this script samples a
parameter space and runs simulations; it does not cluster, does not
compute correlations between parameters and outcomes, and does not
select or exclude runs based on how "interesting" or "expected" their
outcome looks. Its only output is a pool of per-run phenotype vectors
and eligibility screens for Stage 4 (blind discovery) to consume
unmodified.

**Parameter space** (8 dimensions, sampled via a Latin Hypercube design
-- the "literal space-filling parameter-range design" Work Package G's
own status-update entry explicitly deferred to this stage): spans
Work Package G's named environmental-heterogeneity dimensions
(``patch_regen_rate``, ``patch_quality_std``,
``patch_quality_spatial_correlation``, ``scaling_admin_overhead_per_patch``,
``coordination_proposal_probability``) plus three Work Package B/C/D
mechanism-strength parameters (``migration_cost``,
``observation_noise_std``, ``transmission_base_probability``) --
Section 12's own instruction that the search vary generative mechanism
parameters broadly, not just environmental ones. Every bound is a
defensible range straddling that field's own default (see
``PARAMETER_SPACE`` below) and was fixed in this file BEFORE any Stage
3 run -- never adjusted afterward to change which region of the space
was sampled.

**Disclosed scale reduction**: Stage 0's frozen manifest
(``outputs/level12_stage0_preregistration/manifest.json``) commits to
``n_seeds: 24`` and ``n_parameter_draws: 12`` for this stage; those two
numbers are interpreted here as 24 TOTAL runs = 12 draws x 2 seeds per
draw (not 12 x 24 = 288), a session-compute-budget reduction from a
fuller per-draw seed count, recorded here -- in this file, before this
stage's own run -- rather than adjusted after seeing results.

**Stage 2's own finding informs this design without constraining its
outcome**: ``migration_cost`` is included as a swept dimension
specifically because Stage 2 found ecological collapse was migration-
associated at one fixed cost value (1.0, the config default) -- Stage 3
spans a wide range around it ([0.0, 3.0]) so whether collapse is
cost-dependent or scale-invariant can be OBSERVED, not assumed either
way."""

from __future__ import annotations

import json

import numpy as np
from scipy.stats import qmc

from abm_governance.core.config import SimulationConfig
from experiments.level12_common import compute_eligibility, compute_phenotype_vector, ensure_dir, run_and_summarize
from experiments.level12_preregistration import load_and_verify_manifest

OUT_DIR = "outputs/level12_stage3_main_search"
N_PARAMETER_DRAWS = 12
N_SEEDS_PER_DRAW = 2
N_STEPS = 500
POPULATION = 40
N_PATCHES = 4
LHS_SEED = 20260818  # fixed, disclosed -- this session's calendar date, not tuned

#: (field name, low, high) -- order fixes the Latin Hypercube's column
#: order. Bounds documented per-field below; every one straddles that
#: field's own ``SimulationConfig`` default rather than being centered
#: on any value expected to produce a particular outcome.
PARAMETER_SPACE: tuple[tuple[str, float, float], ...] = (
    ("patch_regen_rate", 0.2, 1.0),                    # default 0.5
    ("patch_quality_std", 0.0, 0.3),                   # default 0.0
    ("patch_quality_spatial_correlation", 0.0, 0.8),   # default 0.0
    ("scaling_admin_overhead_per_patch", -0.2, 0.5),   # default 0.05 (WP-G's disclosed economies/diseconomies relaxation)
    ("coordination_proposal_probability", 0.02, 0.5),  # default 0.02
    ("migration_cost", 0.0, 3.0),                      # default 1.0 -- see module docstring
    ("observation_noise_std", 0.0, 0.4),               # default 0.15
    ("transmission_base_probability", 0.0, 0.3),       # default 0.05
)

PHENOTYPE_DIMENSION_KEYS: tuple[str, ...] = ("C", "E", "L", "D", "M", "R", "S", "F", "V", "H")


def build_parameter_draws() -> list[dict]:
    """Latin Hypercube sample over ``PARAMETER_SPACE``, scaled to each
    field's bounds. Deterministic given ``LHS_SEED`` -- calling this
    twice yields identical draws."""
    sampler = qmc.LatinHypercube(d=len(PARAMETER_SPACE), seed=LHS_SEED)
    unit_sample = sampler.random(n=N_PARAMETER_DRAWS)
    lows = np.array([lo for _, lo, _ in PARAMETER_SPACE])
    highs = np.array([hi for _, _, hi in PARAMETER_SPACE])
    scaled = qmc.scale(unit_sample, lows, highs)
    names = [name for name, _, _ in PARAMETER_SPACE]
    return [dict(zip(names, row.tolist())) for row in scaled]


def _build_config(draw: dict, draw_id: int, seed_idx: int) -> SimulationConfig:
    seed = 4000 + draw_id * 100 + seed_idx
    return SimulationConfig.level11_complete(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed,
        rng_mode="mechanism_substreams",
        institutional_observation_enabled=True, institutional_transmission_enabled=True,
        migration_enabled=True, membership_exit_enabled=True, institutional_scaling_enabled=True,
        **draw,
    )


def run() -> dict:
    ensure_dir(OUT_DIR)
    load_and_verify_manifest()  # hard stop if Stage 0's frozen manifest was altered

    draws = build_parameter_draws()
    records = []
    failures = []
    for draw_id, draw in enumerate(draws):
        for seed_idx in range(N_SEEDS_PER_DRAW):
            config = _build_config(draw, draw_id, seed_idx)
            try:
                summary, sim = run_and_summarize(config, return_sim=True)
                phenotype_vector = compute_phenotype_vector(sim, config)
                eligibility = compute_eligibility(sim, config, phenotype_vector, summary)
                records.append({
                    "draw_id": draw_id, "seed_idx": seed_idx, "seed": config.seed,
                    "parameter_condition": f"draw_{draw_id}", "parameters": draw,
                    "all_outcome_label": summary["all_outcome_label"],
                    "n_institutions_ever_formed": summary["n_institutions_ever_formed"],
                    "n_institutions_active_at_end": summary["n_institutions_active_at_end"],
                    "population_alive_fraction": summary["population_alive_fraction"],
                    "ecological_resource_fraction": summary["ecological_resource_fraction"],
                    "eligibility": eligibility, "phenotype_vector": phenotype_vector,
                })
            except Exception as exc:  # noqa: BLE001 -- record, never silently drop a failed draw
                failures.append({"draw_id": draw_id, "seed_idx": seed_idx, "error": str(exc)})
            print(f"draw {draw_id} seed_idx {seed_idx}: {'ok' if not failures or failures[-1].get('draw_id') != draw_id or failures[-1].get('seed_idx') != seed_idx else 'FAILED'}", flush=True)

    outcome_distribution = {}
    for r in records:
        outcome_distribution[r["all_outcome_label"]] = outcome_distribution.get(r["all_outcome_label"], 0) + 1

    report = {
        "n_parameter_draws": N_PARAMETER_DRAWS, "n_seeds_per_draw": N_SEEDS_PER_DRAW,
        "n_total_runs": len(draws) * N_SEEDS_PER_DRAW, "n_completed": len(records), "n_failed": len(failures),
        "parameter_space": [{"name": n, "low": lo, "high": hi} for n, lo, hi in PARAMETER_SPACE],
        "failures": failures, "outcome_label_distribution": outcome_distribution,
        "n_eligible": sum(1 for r in records if r["eligibility"]["eligible"]),
        "records": records,
    }
    with open(f"{OUT_DIR}/stage3_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(
        f"Stage 3 search: {report['n_completed']}/{report['n_total_runs']} runs completed, "
        f"{report['n_failed']} failed. outcome_label_distribution={outcome_distribution} "
        f"n_eligible={report['n_eligible']}", flush=True,
    )
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
