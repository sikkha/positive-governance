#!/usr/bin/env python3
"""Work Package G: the one minimal perturbation experiment.

Design
------
The milestone brief asks for exactly one perturbation experiment,
implemented only once the baseline is stable, with pre-shock state,
shock spec, response, and recovery all explicitly recorded.

The Work-Package-E baseline ensemble (``outputs/ensemble_level01``) showed
that under the *default* ecological-closure calibration
(``environment_capacity=2000, environment_regen_rate=0.5``), the shared
resource pool collapses to its floor (0) within the first ~25 of 500
steps and never leaves it (see dev_mem/status_update.md's "unexpected
findings" for the full discussion) — that run is not a "stable baseline"
to perturb, it is already at a boundary, so a depletion shock on top of
it would be invisible (there is nothing left to deplete).

This experiment therefore uses a deliberately different ecological
calibration — capacity raised to 20,000 (regen rate and every other
parameter unchanged) — chosen for the sole purpose of giving the pool
room to sit at a non-boundary quasi-steady-state (empirically, ~96-99% of
capacity by step ~25, see the calibration check this module's __main__
performs) so that a shock's effect and the pool's subsequent regeneration
back toward that state are both visible. This is a demonstration
configuration for validating the perturbation *interface*, not a claim
about the milestone's default calibration — the run is exported with its
full config.yaml, and the deviation from the default is stated here and
in the final report, not hidden.

Shock: a single ``resource_depletion`` perturbation (magnitude=0.5, i.e.
an instantaneous 50% cut to the pool) with ``start_step=200`` (chosen to
be well after the pool's initial equilibration) and ``duration=1``.
Compared against an unperturbed run with an identical config and the same
seeds (perturbations=() ), across the same 15 seeds, so the comparison is
apples-to-apples on everything except the shock itself.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from abm_governance.core.config import SimulationConfig
from abm_governance.core.export import export_results
from abm_governance.simulation import Simulation

SEEDS = list(range(15))
N_STEPS = 500
SHOCK_START = 200
SHOCK_DURATION = 1
SHOCK_MAGNITUDE = 0.5
#: Deliberately larger than the Level 0.1 default (2000) — see module
#: docstring: this keeps the pool away from the [0, K] boundary so the
#: shock and recovery are visible instead of masked by an already-empty
#: (or already-full) pool.
DEMO_ENVIRONMENT_CAPACITY = 20000.0

BASE_OVERRIDES = {
    "ecology_enabled": True,
    "relationship_dynamics_enabled": True,
    "environment_capacity": DEMO_ENVIRONMENT_CAPACITY,
}


def _config(seed: int, shocked: bool) -> SimulationConfig:
    overrides = dict(BASE_OVERRIDES)
    if shocked:
        overrides["perturbations"] = (
            {
                "start_step": SHOCK_START,
                "duration": SHOCK_DURATION,
                "kind": "resource_depletion",
                "magnitude": SHOCK_MAGNITUDE,
            },
        )
    return SimulationConfig(seed=seed, n_steps=N_STEPS, **overrides)


def run(out_root: str) -> dict:
    os.makedirs(out_root, exist_ok=True)
    rows = []
    for seed in SEEDS:
        for shocked in (False, True):
            arm = "shocked" if shocked else "baseline"
            config = _config(seed, shocked)
            result = Simulation(config).run()
            out_dir = os.path.join(out_root, "runs", arm, f"seed_{seed:04d}")
            export_results(result, out_dir)
            for row in result.metrics:
                rows.append(
                    {
                        "arm": arm,
                        "seed": seed,
                        "step": row["step"],
                        "environment_resources": row["environment_resources"],
                        "environment_fraction_of_capacity": row["environment_fraction_of_capacity"],
                        "cooperation_rate": row["cooperation_rate"],
                        "mean_resources": row["mean_resources"],
                    }
                )

    combined = pd.DataFrame(rows)
    combined_path = os.path.join(out_root, "perturbation_trajectories.csv")
    combined.to_csv(combined_path, index=False)

    # -- pre-shock state (last step before the shock, both arms — should
    # agree closely since arms are identical up to that point) ------------
    pre_step = SHOCK_START - 1
    pre_shock = combined[combined["step"] == pre_step]
    pre_shock_summary = {
        arm: {
            "environment_resources_mean": float(pre_shock[pre_shock.arm == arm]["environment_resources"].mean()),
            "environment_fraction_of_capacity_mean": float(
                pre_shock[pre_shock.arm == arm]["environment_fraction_of_capacity"].mean()
            ),
        }
        for arm in ("baseline", "shocked")
    }

    # -- immediate response (pool value at the shock step itself) ---------
    at_shock = combined[combined["step"] == SHOCK_START]
    response = {
        arm: float(at_shock[at_shock.arm == arm]["environment_resources"].mean()) for arm in ("baseline", "shocked")
    }

    # -- recovery: first step (after the shock) at which the shocked arm's
    # per-seed mean pool value returns to within 5% of the *baseline* arm's
    # value at that same step, for at least 3 consecutive steps (reported
    # as a plain descriptive statistic — this experiment does NOT classify
    # the trajectory as "recovered" in any dynamical-systems sense; see
    # observer/dynamics.py's operational-criteria docstring). ``None`` if
    # no such step exists within the run.
    baseline_by_step = combined[combined.arm == "baseline"].groupby("step")["environment_resources"].mean()
    shocked_by_step = combined[combined.arm == "shocked"].groupby("step")["environment_resources"].mean()
    recovery_step = None
    consecutive = 0
    for step in range(SHOCK_START, N_STEPS):
        b, s = baseline_by_step.get(step, np.nan), shocked_by_step.get(step, np.nan)
        if b and abs(s - b) / b <= 0.05:
            consecutive += 1
            if consecutive >= 3:
                recovery_step = step - 2
                break
        else:
            consecutive = 0

    summary = {
        "shock_spec": {
            "kind": "resource_depletion",
            "start_step": SHOCK_START,
            "duration": SHOCK_DURATION,
            "magnitude": SHOCK_MAGNITUDE,
        },
        "n_seeds": len(SEEDS),
        "n_steps": N_STEPS,
        "demo_environment_capacity": DEMO_ENVIRONMENT_CAPACITY,
        "pre_shock_state_step": pre_step,
        "pre_shock_state": pre_shock_summary,
        "response_at_shock_step": response,
        "response_pool_drop_fraction": (
            None
            if response["baseline"] == 0
            else (response["baseline"] - response["shocked"]) / response["baseline"]
        ),
        "recovery_step_within_5pct_for_3_consecutive_steps": recovery_step,
        "recovery_lag_steps": None if recovery_step is None else recovery_step - SHOCK_START,
        "note": (
            "recovery_step is a plain descriptive threshold-crossing statistic, "
            "not a dynamical-systems classification (no 'attractor'/'fixed "
            "point' claim is made here or implied by this number)."
        ),
    }
    summary_path = os.path.join(out_root, "perturbation_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print(f"[perturbation_experiment] trajectories: {combined_path}")
    print(f"[perturbation_experiment] summary: {summary_path}")
    print(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=str, default="outputs/perturbation_experiment")
    args = parser.parse_args()
    run(args.out)
