#!/usr/bin/env python3
"""Level 0.3b, Work Package E: parameter-neighborhood robustness at the
registered candidates.

Applies ``observer/regulation_diagnostics.py::parameter_neighborhood_
robustness`` (implemented at Level 0.3, never previously run against real
output -- a documented Level 0.3 gap this milestone closes) to a local,
one-axis-at-a-time perturbation around each candidate: regeneration rate,
harvest unit, maintenance efficiency, maintenance unit, each at -10%/0/+10%
(a prespecified local design, not a full Cartesian product, per the
milestone's explicit allowance). The primary candidate uses 8 seeds/local
point at the same 600-step horizon as confirmation; secondary candidates
use a documented, smaller reduction (2 axes instead of 4, same 8
seeds/point) for compute-budget reasons.
"""

from __future__ import annotations

import json
import math
import os

import numpy as np
import pandas as pd

from abm_governance.observer.regulation_diagnostics import classify_regime, parameter_neighborhood_robustness
from abm_governance.simulation import Simulation
from experiments.level03b_common import build_candidate_config

N_STEPS = 600
N_SEEDS_PER_LOCAL_POINT = 8
LOCAL_DELTAS = (-0.10, 0.0, 0.10)
PRIMARY_AXES = ("patch_regen_rate", "ecological_harvest_unit", "maintenance_efficiency", "ecological_maintenance_unit")
SECONDARY_AXES = ("patch_regen_rate", "maintenance_efficiency")


#: Validated ranges (``core/config.py::__post_init__``) for the axes this
#: script perturbs -- a local +-10% perturbation is clamped to stay
#: within the field's own valid range rather than raising a validation
#: error. Documented, not silently widened: a candidate whose own value
#: already sits within 10% of a bound will have an asymmetric local
#: neighborhood (e.g. maintenance_efficiency=0.96 -> +10% clamps to the
#: 1.0 ceiling rather than 1.056), reported as such.
_AXIS_BOUNDS = {
    "patch_regen_rate": (0.0, 2.0),
    "maintenance_efficiency": (0.0, 1.0),
    "ecological_harvest_unit": (0.0, math.inf),
    "ecological_maintenance_unit": (0.0, math.inf),
}


def _perturbed_params(params: dict, axis: str, delta: float) -> dict:
    out = dict(params)
    low, high = _AXIS_BOUNDS.get(axis, (0.0, math.inf))
    out[axis] = float(np.clip(float(params[axis]) * (1.0 + delta), low, high))
    return out


def _run_local_point(candidate_key: str, axis: str, delta: float, params: dict, n_seeds: int, n_steps: int) -> list:
    rows = []
    for seed in range(n_seeds):
        config = build_candidate_config(params, seed=seed, n_steps=n_steps, condition="endogenous")
        result = Simulation(config).run()
        occupancy = [m["aggregate_fraction_of_capacity"] for m in result.metrics]
        classification = classify_regime(occupancy, burn_in_fraction=0.2)
        rows.append(
            {
                "candidate": candidate_key, "axis": axis, "delta": delta, "seed": seed,
                "label": classification["label"],
                "interior_criteria_met": classification["interior_criteria_met"],
                "mean_occupancy": classification["mean_occupancy"],
                "terminal_occupancy": classification["terminal_occupancy"],
            }
        )
    return rows


def run(
    out_root: str = "outputs/level03b_neighborhood_robustness",
    registry_path: str = "outputs/level03b_candidate_registry/candidate_registry.json",
    confirmation_summary_path: str = "outputs/level03b_confirmation/level03b_confirmation_summary.json",
    n_seeds: int = N_SEEDS_PER_LOCAL_POINT,
    n_steps: int = N_STEPS,
) -> dict:
    os.makedirs(out_root, exist_ok=True)
    with open(registry_path, "r", encoding="utf-8") as fh:
        registry = json.load(fh)
    with open(confirmation_summary_path, "r", encoding="utf-8") as fh:
        confirmation = json.load(fh)

    candidate_order = ["interior_persistent", "nonstationary", "near_collapse"]
    primary_key = next((k for k in candidate_order if registry["selected"].get(k)), None)

    all_rows = []
    per_candidate_summary = {}
    for key in candidate_order:
        candidate = registry["selected"].get(key)
        if candidate is None:
            continue
        # Work Package E is scoped to "each confirmed candidate" -- a
        # candidate here means any candidate that reached Work Package D's
        # confirmation stage at all (status is 'confirmed' or 'not
        # robustly confirmed', both of which ran 24 real seeds); a
        # candidate the registry never populated is skipped, but a
        # candidate that *ran* and *disappointed* is still tested for
        # robustness -- fragility is itself the required finding for
        # such a candidate, not a reason to skip it.
        cand_confirmation = confirmation["per_candidate"].get(key, {})
        target_label = cand_confirmation.get("plurality_label")
        axes = PRIMARY_AXES if key == primary_key else SECONDARY_AXES
        baseline_pass_flags = []
        for axis in axes:
            for delta in LOCAL_DELTAS:
                perturbed = _perturbed_params(candidate["parameters"], axis, delta)
                rows = _run_local_point(key, axis, delta, perturbed, n_seeds, n_steps)
                all_rows.extend(rows)
                if delta == 0.0:
                    # the delta=0.0 "local point" is the candidate itself,
                    # re-run at n_seeds (not reusing WP-D's 24-seed run) for
                    # an apples-to-apples comparison against the +-10% points.
                    baseline_pass_flags = [r["label"] == target_label for r in rows]

        # robustness, per axis: fraction of the axis's own -10%/0/+10%
        # seeds (pooled) whose label matches the candidate's own
        # confirmed plurality label.
        cand_rows = [r for r in all_rows if r["candidate"] == key]
        axis_summaries = {}
        for axis in axes:
            axis_rows = [r for r in cand_rows if r["axis"] == axis]
            pass_flags = [r["label"] == target_label for r in axis_rows]
            robustness = parameter_neighborhood_robustness(pass_flags)
            axis_summaries[axis] = robustness
        overall_pass_flags = [r["label"] == target_label for r in cand_rows]
        overall_robustness = parameter_neighborhood_robustness(overall_pass_flags)
        per_candidate_summary[key] = {
            "target_label": target_label,
            "axes_tested": list(axes),
            "n_seeds_per_local_point": n_seeds,
            "per_axis_robustness": axis_summaries,
            "overall_robustness": overall_robustness,
            "interpretation": (
                "fragile (target label occupies only a single narrow parameter vector)"
                if not overall_robustness["criterion_met"]
                else "occupies a local parameter neighborhood, not only a single point"
            ),
        }

    df = pd.DataFrame(all_rows)
    df_path = os.path.join(out_root, "neighborhood_run_level.csv")
    df.to_csv(df_path, index=False)

    summary = {
        "design": {
            "n_steps": n_steps, "n_seeds_per_local_point": n_seeds, "local_deltas": list(LOCAL_DELTAS),
            "primary_axes": list(PRIMARY_AXES), "secondary_axes": list(SECONDARY_AXES),
            "primary_candidate": primary_key,
        },
        "per_candidate": per_candidate_summary,
    }
    summary_path = os.path.join(out_root, "level03b_neighborhood_robustness_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print(f"[level03b_neighborhood_robustness] {df_path}")
    print(f"[level03b_neighborhood_robustness] {summary_path}")
    return summary


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
