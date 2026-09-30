#!/usr/bin/env python3
"""Level 1.2b, Work Package C (Section 7): the feasibility-map experiment.

**GENERATE FIRST. MEASURE SECOND.** This script builds the ecological
parameter design, saves and hashes it, THEN runs every simulation — no
run's outcome is seen before the full design is frozen on disk. Nothing
in this script clusters, classifies institutional phenotypes, computes
correlations between institutional parameters and outcomes, or selects/
excludes runs based on how "interesting" their outcome looks. Its only
analysis is the one Section 7 explicitly asks for: whether the ex-ante
feasibility ratios (Work Package B) predict realized ecological pressure
(Work Package B's Section 6.3 diagnostics), plus the collapse/saturation
envelope-failure stop condition.

**Institutional design: broad but fixed.** Every run in this script uses
identical, non-tuned institutional settings — ``SimulationConfig.
level12_complete``'s own defaults (every Level 1.1/1.2 mechanism active
at its documented default parameter value, none of them selected for
resemblance to any particular institutional outcome). Only the nine
ecological/shock/population-density dimensions below vary. Institutional
*variation* is Work Package D/E's question, not this one's.

**Nine swept dimensions** (Section 7 names eight; "shock frequency" and
"shock magnitude" are swept as two separate Latin Hypercube columns
here, both realizing the one named "shock frequency/magnitude"
dimension): ``patch_regen_rate``, ``patch_capacity``,
``patch_initial_fraction``, ``subsistence_cost``,
``ecological_harvest_unit``, ``maintenance_efficiency``,
``shock_interval_steps``, ``shock_magnitude``, and a
``population_patch_ratio_selector`` continuous draw thresholded at 0.5
into exactly two discrete (population_size, n_patches) combinations —
Section 7's own "≥2 population/patch combos" requirement, satisfied
categorically rather than by a third multiplicative factor (this
design's total run count is ``n_parameter_points * seeds_per_point``,
not ``n_parameter_points * seeds_per_point * 2``).

**Run arithmetic** (Section 7, saved as explicit fields in the design
file per the milestone spec): ``n_parameter_points=30``,
``seeds_per_point=4``, ``total_runs=120``, ``n_steps=400`` — every
figure here meets or exceeds Section 7's own stated minimums
(``>=30``/``>=4``/``>=400``/``>=2``); none is a disclosed reduction.
"""

from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np
from scipy.stats import qmc

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.feasibility_ratios import (
    expected_pressure_ratio,
    run_with_realized_balance_tracking,
    structural_feasibility_ratio,
)

OUT_DIR = "outputs/level12b_stage_c_feasibility_map"
N_PARAMETER_POINTS = 30
SEEDS_PER_POINT = 4
TOTAL_RUNS = N_PARAMETER_POINTS * SEEDS_PER_POINT  # 120
N_STEPS = 400
LHS_SEED = 20260818  # fixed, disclosed -- this session's calendar date, not tuned

#: (field name, low, high) -- order fixes the Latin Hypercube's column
#: order. Every bound straddles that field's own ``SimulationConfig``
#: default, fixed here before any run, never adjusted after seeing
#: results (Section 7's own explicit "generate the design before any
#: outcome is observed" requirement).
PARAMETER_SPACE: tuple[tuple[str, float, float], ...] = (
    ("patch_regen_rate", 0.05, 1.2),          # default 0.5 -- spans near-zero (structurally infeasible) to fast
    ("patch_capacity", 80.0, 1500.0),         # default 500.0
    ("patch_initial_fraction", 0.05, 0.95),   # default 0.5 -- near-empty to near-full starts
    ("subsistence_cost", 0.02, 0.9),          # default 0.3
    ("ecological_harvest_unit", 0.5, 12.0),   # default 5.0
    ("maintenance_efficiency", 0.05, 1.0),    # default 0.7
    ("shock_interval_steps", 25.0, 400.0),    # recurring resource_depletion shock every N steps (400 = at most one/run)
    ("shock_magnitude", 0.0, 0.6),            # fraction of current patch stock removed per shock (0 = no shock)
    ("population_patch_ratio_selector", 0.0, 1.0),  # thresholded at 0.5, see POPULATION_PATCH_COMBOS below
)

#: The two discrete (population_size, n_patches) combinations Section
#: 7's "≥2 population/patch combos" requirement asks for -- deliberately
#: different densities (5 agents/patch vs. 15 agents/patch), not just
#: different absolute scale at the same density.
POPULATION_PATCH_COMBOS: tuple[tuple[int, int], ...] = (
    (20, 4),   # sparse: 5 agents/patch
    (60, 4),   # dense: 15 agents/patch
)


def build_design() -> dict:
    """Latin Hypercube sample over :data:`PARAMETER_SPACE`, scaled to
    each field's bounds, crossed with :data:`SEEDS_PER_POINT` seeds per
    point. Deterministic given :data:`LHS_SEED`. Returns the full design
    dict (including the explicit run-arithmetic fields Section 7 asks be
    saved), not just the raw points."""
    sampler = qmc.LatinHypercube(d=len(PARAMETER_SPACE), seed=LHS_SEED)
    unit_sample = sampler.random(n=N_PARAMETER_POINTS)
    lows = np.array([lo for _, lo, _ in PARAMETER_SPACE])
    highs = np.array([hi for _, _, hi in PARAMETER_SPACE])
    scaled = qmc.scale(unit_sample, lows, highs)
    names = [name for name, _, _ in PARAMETER_SPACE]

    points = []
    for point_id, row in enumerate(scaled.tolist()):
        draw = dict(zip(names, row))
        selector = draw.pop("population_patch_ratio_selector")
        combo = POPULATION_PATCH_COMBOS[0] if selector < 0.5 else POPULATION_PATCH_COMBOS[1]
        points.append({
            "point_id": point_id,
            "ecological_parameters": draw,
            "population_size": combo[0],
            "n_patches": combo[1],
            "seeds": [7_000_000 + point_id * 1000 + s for s in range(SEEDS_PER_POINT)],
        })

    n_combo_0 = sum(1 for p in points if p["population_size"] == POPULATION_PATCH_COMBOS[0][0])
    n_combo_1 = N_PARAMETER_POINTS - n_combo_0

    return {
        "milestone": "level1.2b_ecological_feasibility_envelope_work_package_c",
        "n_parameter_points": N_PARAMETER_POINTS,
        "seeds_per_point": SEEDS_PER_POINT,
        "total_runs": TOTAL_RUNS,
        "n_steps": N_STEPS,
        "lhs_seed": LHS_SEED,
        "parameter_space": [{"field": n, "low": lo, "high": hi} for n, lo, hi in PARAMETER_SPACE],
        "population_patch_combos": [list(c) for c in POPULATION_PATCH_COMBOS],
        "n_points_per_combo": {"combo_0": n_combo_0, "combo_1": n_combo_1},
        "points": points,
        "institutional_design": "broad_but_fixed: SimulationConfig.level12_complete defaults, identical across all points",
    }


def design_hash(design: dict) -> str:
    payload = json.dumps(design, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_design(out_dir: str = OUT_DIR) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    design = build_design()
    digest = design_hash(design)
    with open(f"{out_dir}/design.json", "w") as f:
        json.dump(design, f, indent=2, sort_keys=True, default=str)
    with open(f"{out_dir}/design_hash.txt", "w") as f:
        f.write(digest + "\n")
    return {"design": design, "hash": digest}


def load_and_verify_design(out_dir: str = OUT_DIR) -> dict:
    with open(f"{out_dir}/design.json") as f:
        design = json.load(f)
    with open(f"{out_dir}/design_hash.txt") as f:
        stored_hash = f.read().strip()
    recomputed = design_hash(design)
    if recomputed != stored_hash:
        raise ValueError(
            f"Work Package C feasibility-map design at {out_dir}/design.json has been altered "
            f"since it was frozen (stored hash {stored_hash}, recomputed hash {recomputed})."
        )
    return {"design": design, "hash": recomputed}


def _build_perturbations(point: dict, n_steps: int) -> tuple:
    interval = max(1, int(round(point["ecological_parameters"]["shock_interval_steps"])))
    magnitude = point["ecological_parameters"]["shock_magnitude"]
    if magnitude <= 0.0:
        return ()
    specs = []
    start = interval
    while start < n_steps:
        specs.append({"start_step": start, "duration": 1, "kind": "resource_depletion", "magnitude": magnitude})
        start += interval
    return tuple(specs)


def _build_config(point: dict, seed: int) -> SimulationConfig:
    eco = dict(point["ecological_parameters"])
    eco.pop("shock_interval_steps", None)
    eco.pop("shock_magnitude", None)
    perturbations = _build_perturbations(point, N_STEPS)
    return SimulationConfig.level12_complete(
        population_size=point["population_size"], n_patches=point["n_patches"], n_steps=N_STEPS, seed=seed,
        perturbations=perturbations,
        **eco,
    )


#: Section 7's own stop condition: if every point's realized outcome is
#: collapse (realized supply persistently and severely short of realized
#: demand) or saturation (realized supply persistently and comfortably
#: in excess of realized demand, never in deficit), report envelope
#: failure rather than proceeding. Uses Work Package B's own Section 6.3
#: realized-balance diagnostics directly (mean post-burn-in ratio,
#: fraction of steps in deficit) -- not a reconstructed occupancy proxy.
#: Thresholds are generous (not tuned to avoid triggering) --
#: "structurally uninformative", not "imperfect".
_COLLAPSE_MEAN_RATIO_CEILING = 0.1
_COLLAPSE_FRACTION_BELOW_ONE_FLOOR = 0.9
_SATURATION_MEAN_RATIO_FLOOR = 3.0


def _classify_ecological_outcome(mean_ratio_post_burn_in: float, fraction_below_one: float) -> str:
    if math.isnan(mean_ratio_post_burn_in) or math.isnan(fraction_below_one):
        return "other"  # structural missingness (e.g. zero demand every step) -- never coerced into a label
    if mean_ratio_post_burn_in <= _COLLAPSE_MEAN_RATIO_CEILING and fraction_below_one >= _COLLAPSE_FRACTION_BELOW_ONE_FLOOR:
        return "collapse"
    if mean_ratio_post_burn_in >= _SATURATION_MEAN_RATIO_FLOOR and fraction_below_one == 0.0:
        return "saturation"
    return "other"


def run() -> dict:
    verified = load_and_verify_design()
    design = verified["design"]

    records = []
    failures = []
    for point in design["points"]:
        for seed in point["seeds"]:
            config = _build_config(point, seed)
            struct = structural_feasibility_ratio(config)
            expected = expected_pressure_ratio(config)
            try:
                result, realized = run_with_realized_balance_tracking(config)
            except Exception as exc:  # noqa: BLE001 -- record, never silently drop a failed run
                failures.append({"point_id": point["point_id"], "seed": seed, "error": str(exc)})
                continue

            outcome = _classify_ecological_outcome(
                mean_ratio_post_burn_in=realized.mean_ratio_post_burn_in,
                fraction_below_one=realized.fraction_of_steps_below_one,
            )

            records.append({
                "point_id": point["point_id"], "seed": seed,
                "population_size": point["population_size"], "n_patches": point["n_patches"],
                "structural_ratio": struct.ratio, "expected_ratio": expected.ratio,
                "expected_ratio_including_maintenance": expected.ratio_including_maintenance,
                "realized_fraction_below_one": realized.fraction_of_steps_below_one,
                "realized_longest_deficit_episode": realized.longest_deficit_episode_steps,
                "realized_n_deficit_episodes": realized.n_deficit_episodes,
                "realized_cumulative_unmet_demand": realized.cumulative_unmet_extraction_demand,
                "realized_mean_ratio_post_burn_in": realized.mean_ratio_post_burn_in,
                "realized_patch_heterogeneity_final_cv": realized.patch_heterogeneity_final_cv,
                "ecological_outcome": outcome,
            })
            print(
                f"point {point['point_id']} seed {seed}: struct={struct.ratio:.3f} expected={expected.ratio:.3f} "
                f"outcome={outcome}",
                flush=True,
            )

    outcome_counts: dict[str, int] = {}
    for r in records:
        outcome_counts[r["ecological_outcome"]] = outcome_counts.get(r["ecological_outcome"], 0) + 1

    envelope_failure = len(records) > 0 and outcome_counts.get("other", 0) == 0 and (
        set(outcome_counts.keys()) <= {"collapse", "saturation"}
    )

    correlation = _predictive_correlation(records)

    report = {
        "design_hash": verified["hash"],
        "n_runs_completed": len(records),
        "n_runs_failed": len(failures),
        "failures": failures,
        "outcome_counts": outcome_counts,
        "envelope_failure": envelope_failure,
        "ex_ante_vs_realized_correlation": correlation,
        "records": records,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(f"{OUT_DIR}/results.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


def _predictive_correlation(records: list[dict]) -> dict:
    """Section 7's own required analysis: do the ex-ante ratios predict
    realized pressure? Pearson correlation between each ex-ante ratio and
    the realized post-burn-in mean ratio, computed only over records with
    both quantities finite (structural missingness preserved, never
    coerced to 0 -- Section 22)."""
    pairs_struct = [
        (r["structural_ratio"], r["realized_mean_ratio_post_burn_in"]) for r in records
        if math.isfinite(r["structural_ratio"]) and math.isfinite(r["realized_mean_ratio_post_burn_in"])
    ]
    pairs_expected = [
        (r["expected_ratio"], r["realized_mean_ratio_post_burn_in"]) for r in records
        if math.isfinite(r["expected_ratio"]) and math.isfinite(r["realized_mean_ratio_post_burn_in"])
    ]

    def _pearson(pairs):
        if len(pairs) < 3:
            return None
        xs = np.array([p[0] for p in pairs])
        ys = np.array([p[1] for p in pairs])
        if np.std(xs) == 0 or np.std(ys) == 0:
            return None
        return float(np.corrcoef(xs, ys)[0, 1])

    return {
        "structural_ratio_vs_realized_mean": _pearson(pairs_struct),
        "expected_ratio_vs_realized_mean": _pearson(pairs_expected),
        "n_pairs_structural": len(pairs_struct),
        "n_pairs_expected": len(pairs_expected),
    }


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    design_result = write_design()
    print(f"Work Package C design frozen at {OUT_DIR}/design.json")
    print(f"design hash: {design_result['hash']}")
    report_result = run()
    print(f"n_runs_completed={report_result['n_runs_completed']} n_runs_failed={report_result['n_runs_failed']}")
    print(f"outcome_counts={report_result['outcome_counts']}")
    print(f"envelope_failure={report_result['envelope_failure']}")
    print(f"ex_ante_vs_realized_correlation={report_result['ex_ante_vs_realized_correlation']}")
