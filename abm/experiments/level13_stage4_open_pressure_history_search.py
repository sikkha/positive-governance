#!/usr/bin/env python3
"""Level 1.3, Stage 4 (task #99): open pressure-history search (LHS).

Where Stage 3 (task #98) held pressure SHAPE fixed (a clean step
function) and varied only ORDER across a small enumerated factorial,
this stage does the opposite: a genuinely open Latin Hypercube search
over each of the three Section 5 pressure channels' own timing,
magnitude, and duration, all three channels varying simultaneously and
continuously -- 3 parameters (onset step, peak magnitude, duration) x 3
channels = 9 search dimensions, each channel using the same
``"early_pulse"`` kind Stage 3 used (a clean low-to-high-then-optionally-
decaying step, ``core/historical_pressure.py``'s own
``generate_pressure_series``), but now with the pulse's own duration
itself a free search dimension rather than fixed at "permanent."

**Design choice, disclosed**: ``entrenchment_enabled`` and both
legitimacy channels are held ON (not searched) for every run in this
stage -- Stage 1/3 already tested those flags' own on/off activation
and factorial interaction with sequencing order; this stage's own job
is to open up the CONTINUOUS pressure-history space specifically, with
every other Level 1.3 mechanism left active so nothing in the
generative substrate is artificially suppressed while that space is
explored.

24 LHS points x 4 seeds/point = 96 runs (matching the frozen
preregistration manifest's ``stage4_open_pressure_history_search_lhs``
commitment: population 40, 4 patches, 500 steps).

Like Stage 3, this script records raw material (each run's Work Package
B sequencing vector and Work Package H phenotype vector) for the later
discovery pipeline (Stage 6, task #101) rather than drawing any
conclusion itself -- ``outputs/level13_stage4_open_pressure_history_
search/records.json``, hashed.

**Two bugs found and fixed (task #109, disclosed in full in
``dev_mem/status_update.md``), the same two as Stage 3's own -- see
that module's docstring for the full account.** (1) transmission
sub-flags never set (pressure state varied but never touched agent
behavior), and (2) built on the wrong substrate preset (bare
``level1_rule_formation_default()``, Level 1.1 mechanisms all off, so
even fixing (1) alone would still have nothing for pressure to act on)
which also silently left ``rng_mode`` at ``legacy_single_stream``,
violating the frozen manifest's own ``RNG_COMMITMENTS``. Fixed by
switching to ``level12b_frozen_reference()`` plus the transmission
sub-flags. The original (bugged) 96-run output was archived to
``outputs/level13_stage4_open_pressure_history_search/records_pre_
transmission_fix.json`` for the audit trail before this stage was
re-run with both fixes."""

from __future__ import annotations

import hashlib
import json
import os

import numpy as np
from scipy.stats import qmc

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.level13_phenotype import level13_phenotype_vector
from abm_governance.observer.sequencing_diagnostics import institutional_response_series, sequencing_vector
from abm_governance.simulation import Simulation
from experiments.level13_common import transmission_overrides_for_channel
from experiments.level13_preregistration import load_and_verify_manifest

OUT_DIR = "outputs/level13_stage4_open_pressure_history_search"
N_POINTS = 24
N_SEEDS_PER_POINT = 4
N_STEPS = 500
POPULATION = 40
N_PATCHES = 4
LHS_SEED = 20260820002  # fresh, disclosed; distinct from every earlier Level 1.3 LHS seed.
SEED_BASE = 6_000_000
ENTRENCHMENT_MATURATION_STEPS = 100

_CHANNELS = ("security_pressure", "bargaining_pressure", "coordination_complexity")

#: Per-channel search space: (onset_step, high_level, duration_steps).
#: low_level is left at its Level 1.3 default (0.1) for every channel --
#: this stage searches WHEN, HOW STRONG, and HOW LONG, not the floor.
_PARAMETER_SPACE: tuple[tuple[str, float, float], ...] = tuple(
    field
    for channel in _CHANNELS
    for field in (
        (f"{channel}_onset_step", 0.0, 400.0),
        (f"{channel}_high_level", 0.3, 0.9),
        (f"{channel}_duration_steps", 50.0, 500.0),
    )
)


def lhs_draws(n: int = N_POINTS, seed: int = LHS_SEED) -> list[dict]:
    sampler = qmc.LatinHypercube(d=len(_PARAMETER_SPACE), seed=seed)
    unit_sample = sampler.random(n=n)
    lows = np.array([lo for _, lo, _ in _PARAMETER_SPACE])
    highs = np.array([hi for _, _, hi in _PARAMETER_SPACE])
    scaled = qmc.scale(unit_sample, lows, highs)
    names = [name for name, _, _ in _PARAMETER_SPACE]
    return [dict(zip(names, row)) for row in scaled.tolist()]


def _build_config(draw: dict, seed: int) -> SimulationConfig:
    overrides: dict = dict(
        historical_module_enabled=True, entrenchment_enabled=True,
        entrenchment_maturation_steps=ENTRENCHMENT_MATURATION_STEPS,
        performance_legitimacy_enabled=True, procedural_legitimacy_enabled=True,
    )
    for channel in _CHANNELS:
        overrides[f"{channel}_enabled"] = True
        overrides[f"{channel}_history_kind"] = "early_pulse"
        overrides[f"{channel}_onset_step"] = int(round(draw[f"{channel}_onset_step"]))
        overrides[f"{channel}_high_level"] = draw[f"{channel}_high_level"]
        overrides[f"{channel}_duration_steps"] = int(round(draw[f"{channel}_duration_steps"]))
        overrides.update(transmission_overrides_for_channel(channel))
    # level12b_frozen_reference (not the bare level1_rule_formation_
    # default() the first draft used) so the institutional substrate
    # Work Package A's transmission channels act on is active, and
    # rng_mode="mechanism_substreams" is set (the frozen manifest's own
    # RNG_COMMITMENTS). See module docstring's "Bug found and fixed"
    # note (task #109).
    return SimulationConfig.level12b_frozen_reference(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed,
        **overrides,
    )


def _run_one(point_id: int, draw: dict, seed: int) -> dict:
    config = _build_config(draw, seed)
    sim = Simulation(config)
    sim.run()

    response = institutional_response_series(sim.event_log, N_STEPS)
    vector = sequencing_vector(response, min_duration_steps=10)
    phenotype = level13_phenotype_vector(
        sim.event_log, sim.rule_registry, n_steps=N_STEPS, current_step=N_STEPS,
        entrenchment_maturation_steps=ENTRENCHMENT_MATURATION_STEPS,
    )
    return {
        "seed": seed,
        "point_id": point_id,
        "draw": draw,
        "sequencing_vector": vector,
        "phenotype_vector": {k: v["value"] for k, v in phenotype.items()},
    }


def run(n_points: int = N_POINTS, n_seeds_per_point: int = N_SEEDS_PER_POINT) -> dict:
    load_and_verify_manifest()  # hard stop if the frozen manifest was altered
    draws = lhs_draws(n_points)
    records = []
    for point_id, draw in enumerate(draws):
        for s in range(n_seeds_per_point):
            records.append(_run_one(point_id, draw, SEED_BASE + point_id * 1000 + s))

    report = {
        "milestone": "level1.3_stage4_open_pressure_history_search",
        "n_points": n_points,
        "n_seeds_per_point": n_seeds_per_point,
        "n_runs": len(records),
        "population_size": POPULATION,
        "n_patches": N_PATCHES,
        "n_steps": N_STEPS,
        "lhs_seed": LHS_SEED,
        "parameter_space": [{"field": n, "low": lo, "high": hi} for n, lo, hi in _PARAMETER_SPACE],
        "records": records,
    }
    return report


def report_hash(report: dict) -> str:
    payload = json.dumps(report, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_report(out_dir: str = OUT_DIR, n_points: int = N_POINTS, n_seeds_per_point: int = N_SEEDS_PER_POINT) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    report = run(n_points, n_seeds_per_point)
    digest = report_hash(report)
    report["report_hash"] = digest
    with open(f"{out_dir}/records.json", "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    result = write_report()
    print(f"Level 1.3 Stage 4: {result['n_runs']} runs across {result['n_points']} LHS points")
    print(f"report written to {OUT_DIR}/records.json")
