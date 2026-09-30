#!/usr/bin/env python3
"""Level 0.3, Work Package H: phase-space search without target shaping.

A reproducible Latin Hypercube design (``scipy.stats.qmc.LatinHypercube``,
same tool ``experiments/phase_sweep.py`` already uses for the Level 0.2
ecological-phase search, for consistency) over the milestone's named
parameter axes:

* ``patch_regen_rate``, ``patch_capacity``, ``n_patches``
* ``population_size`` (a proxy for agent-to-patch density, reported
  post-hoc as ``population_size / n_patches`` rather than sampled
  directly, since it must stay an integer >= ``mean_degree + 1``)
* ``ecological_harvest_unit`` (extraction benefit),
  ``ecological_search_cost`` (extraction effort cost)
* ``ecological_maintenance_unit`` (maintenance cost scale),
  ``maintenance_efficiency``
* ``ecological_mutation_rate``, ``scarcity_sensitivity_mean``
* ``fitness_mode`` (categorical — the continuous LHS coordinate for this
  axis is binned into the four existing modes)

Points are **never** selected, retried, or filtered by their resulting
cooperation rate, ecological outcome, or any other observed quantity —
every point the LHS design produces is run and reported, including
"boring" ones. Outcome region labels
(``observer/regulation_diagnostics.py::nonstationary_classification``)
are computed strictly post-hoc, purely for describing the sampled space
after the fact; they play no role in point selection and this module
never stops early because a desired cluster count appears.

**Scale note (documented reduction).** The milestone brief asks for
">= 48 points if runtime permits" and "8-10 seeds per point." This
module defaults to ``N_POINTS = 16``, ``SEEDS_PER_POINT = 3`` — a
deliberate compute-budget reduction, not a claim that fewer points would
be preferred; ``run()`` accepts both as overrides for a larger follow-up
sweep, and the reduction is stated again in the scientific note and the
milestone completion report.
"""

from __future__ import annotations

import dataclasses
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import qmc

from abm_governance.agents.fitness import VALID_FITNESS_MODES
from abm_governance.core.config import SimulationConfig
from abm_governance.observer.regulation_diagnostics import (
    interior_persistence,
    nonstationary_classification,
)
from abm_governance.simulation import Simulation

N_POINTS = 16
SEEDS_PER_POINT = 3
N_STEPS = 250
MEAN_DEGREE = 4

PARAM_NAMES = [
    "patch_regen_rate", "patch_capacity", "n_patches", "population_size",
    "ecological_harvest_unit", "ecological_search_cost", "ecological_maintenance_unit",
    "maintenance_efficiency", "ecological_mutation_rate", "scarcity_sensitivity_mean", "fitness_mode_bin",
]
PARAM_LOWS = [0.1, 200.0, 2, 16, 1.0, 0.0, 1.0, 0.2, 0.0, 0.0, 0.0]
PARAM_HIGHS = [1.0, 1000.0, 8, 48, 15.0, 3.0, 15.0, 1.0, 0.1, 1.0, 1.0]
_INT_PARAMS = {"n_patches", "population_size"}


def design_matrix(n_points: int, rng_seed: int) -> pd.DataFrame:
    """Reproducible LHS design, given a fixed integer seed -- the same
    (n_points, rng_seed) pair always produces the same matrix."""
    sampler = qmc.LatinHypercube(d=len(PARAM_NAMES), seed=rng_seed)
    unit_sample = sampler.random(n=n_points)
    scaled = qmc.scale(unit_sample, PARAM_LOWS, PARAM_HIGHS)
    df = pd.DataFrame(scaled, columns=PARAM_NAMES)
    for col in _INT_PARAMS:
        df[col] = df[col].round().astype(int)
    df["fitness_mode"] = df["fitness_mode_bin"].apply(
        lambda x: VALID_FITNESS_MODES[min(int(x * len(VALID_FITNESS_MODES)), len(VALID_FITNESS_MODES) - 1)]
    )
    df = df.drop(columns=["fitness_mode_bin"])
    df["point_id"] = range(n_points)
    return df


def _point_config(row, seed: int, n_steps: int) -> SimulationConfig:
    n_patches = max(1, int(row["n_patches"]))
    population_size = max(n_patches, int(row["population_size"]))
    mean_degree = min(MEAN_DEGREE, population_size - 1)
    return SimulationConfig.level03_phase_search_base(
        seed=seed, n_steps=n_steps, population_size=population_size, mean_degree=mean_degree,
        n_patches=n_patches, patch_regen_rate=float(row["patch_regen_rate"]),
        patch_capacity=float(row["patch_capacity"]),
        ecological_harvest_unit=float(row["ecological_harvest_unit"]),
        ecological_search_cost=float(row["ecological_search_cost"]),
        ecological_maintenance_unit=float(row["ecological_maintenance_unit"]),
        maintenance_efficiency=float(row["maintenance_efficiency"]),
        ecological_mutation_rate=float(row["ecological_mutation_rate"]),
        scarcity_sensitivity_mean=float(row["scarcity_sensitivity_mean"]),
        fitness_mode=str(row["fitness_mode"]), fitness_mode_ecological=str(row["fitness_mode"]),
    )


def run(
    out_root: str,
    n_points: int = N_POINTS,
    seeds_per_point: int = SEEDS_PER_POINT,
    n_steps: int = N_STEPS,
    design_seed: int = 20260817,
) -> dict:
    os.makedirs(out_root, exist_ok=True)
    design = design_matrix(n_points, design_seed)
    design_path = os.path.join(out_root, "niche_phase_search_design.csv")
    design.to_csv(design_path, index=False)

    rows = []
    failures = []
    for _, point_row in design.iterrows():
        for seed in range(seeds_per_point):
            try:
                config = _point_config(point_row, seed, n_steps)
                result = Simulation(config).run()
            except Exception as exc:  # pragma: no cover - defensive, reported not swallowed
                failures.append({"point_id": int(point_row["point_id"]), "seed": seed, "error": f"{type(exc).__name__}: {exc}"})
                continue
            occupancy = [m["aggregate_fraction_of_capacity"] for m in result.metrics]
            tail = occupancy[-max(1, n_steps // 2):]
            persistence = interior_persistence(tail)
            classification = nonstationary_classification(tail)
            final_row = result.metrics[-1]
            rows.append(
                {
                    "point_id": int(point_row["point_id"]), "seed": seed,
                    "population_density": population_density(point_row),
                    "final_aggregate_occupancy": final_row["aggregate_fraction_of_capacity"],
                    "final_cooperation_rate": final_row["cooperation_rate"],
                    "fraction_interior": persistence["fraction_interior"],
                    "interior_persistence_criterion_met": persistence["criterion_met"],
                    "region_label": classification["label"],
                    "n_patches_depleted_final": final_row["n_patches_depleted"],
                    "n_patches_abundant_final": final_row["n_patches_abundant"],
                }
            )

    outcomes = pd.DataFrame(rows)
    outcomes_path = os.path.join(out_root, "niche_phase_search_outcomes.csv")
    outcomes.to_csv(outcomes_path, index=False)

    # -- post-hoc region-label distribution (descriptive only; never used
    # to pick, filter, or re-run points). ---------------------------------
    if not outcomes.empty:
        label_counts = outcomes["region_label"].value_counts().to_dict()
        label_fractions = {k: v / len(outcomes) for k, v in label_counts.items()}
    else:
        label_counts, label_fractions = {}, {}

    summary = {
        "design": {
            "n_points": n_points, "seeds_per_point": seeds_per_point, "n_steps": n_steps, "design_seed": design_seed,
            "param_names": PARAM_NAMES[:-1] + ["fitness_mode"],
            "scale_reduction_note": (
                f"milestone brief suggests >=48 points and 8-10 seeds/point; this run used "
                f"{n_points} points x {seeds_per_point} seeds, documented as a deliberate "
                "compute-budget reduction (see module docstring)."
            ),
        },
        "n_runs": len(rows),
        "n_failures": len(failures),
        "failures": failures,
        "region_label_counts_post_hoc": label_counts,
        "region_label_fractions_post_hoc": label_fractions,
        "note": (
            "Region labels are purely descriptive, computed after every point was already "
            "run; no point was selected, retried, or excluded based on its outcome, and this "
            "search was not stopped early because a particular cluster count appeared."
        ),
    }
    summary_path = os.path.join(out_root, "niche_phase_search_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print(f"[niche_phase_search] design: {design_path}")
    print(f"[niche_phase_search] outcomes: {outcomes_path}")
    print(f"[niche_phase_search] summary: {summary_path}")
    print(json.dumps(summary, indent=2, default=str))
    return summary


def population_density(row) -> float:
    n_patches = max(1, int(row["n_patches"]))
    return float(row["population_size"]) / n_patches


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=str, default="outputs/niche_phase_search")
    parser.add_argument("--n-points", type=int, default=N_POINTS)
    parser.add_argument("--seeds-per-point", type=int, default=SEEDS_PER_POINT)
    args = parser.parse_args()
    run(args.out, n_points=args.n_points, seeds_per_point=args.seeds_per_point)
