#!/usr/bin/env python3
"""Level 1.0 mandatory preflight audit: rerun ONLY the two Level 0.3b
Work Package H (fitness-stream) cells affected by the coupled-mode
dispatch defects fixed in ``agents/adaptation.py::
coupled_dual_imitation_round`` and ``simulation.py::_adaptation_round``
(see ``docs/level1.0_decision_record.md``) --
``(inheritance_mode="coupled_same_model", condition="frozen")`` and
``(inheritance_mode="coupled_same_model", condition="randomized")``.

Per the milestone's explicit instruction ("Rerun only the Level 0.3b
fitness-stream cells affected by these defects. Do not rerun or alter
unaffected Level 0.3b experiments."), this script:

1. Loads the already-committed ``outputs/level03b_fitness_stream/
   fitness_stream_run_level.csv`` untouched.
2. Recomputes ONLY the rows for the two affected cells, using the fixed
   simulation code, at the exact original design (``N_SEEDS=12``,
   ``N_STEPS=600``, same seeds 0-11, same registered primary candidate).
3. Replaces only those rows in the CSV (all other rows -- independent
   mode entirely, and coupled x endogenous/environment_only -- are kept
   byte-identical from the original run).
4. Recomputes the summary JSON's aggregate statistics from the corrected
   full table and records an explicit before/after comparison for the
   two affected cells so the correction is auditable, not silent.
"""

from __future__ import annotations

import dataclasses
import json
import os

import pandas as pd

from abm_governance.simulation import Simulation
from experiments.level03b_common import build_candidate_config, continuous_outcomes, final_composition, initial_composition
from experiments.level03b_fitness_stream import N_SEEDS, N_STEPS, _condition_overrides_for_mode

AFFECTED_CELLS = (("coupled_same_model", "frozen"), ("coupled_same_model", "randomized"))


def _run_cell(params, mode, condition, primary_key, n_seeds, n_steps):
    rows = []
    for seed in range(n_seeds):
        config = build_candidate_config(params, seed=seed, n_steps=n_steps, condition="endogenous")
        overrides = _condition_overrides_for_mode(condition, mode)
        config = dataclasses.replace(config, ecological_inheritance_mode=mode, **overrides)
        sim = Simulation(config)
        init = initial_composition(sim)
        result = sim.run()
        outcomes = continuous_outcomes(result)
        final = final_composition(result)
        rows.append(
            {
                "candidate": primary_key, "fitness_stream": "total", "inheritance_mode": mode,
                "condition": condition, "seed": seed,
                "label": outcomes["classify_regime_label"],
                "post_burn_in_mean_occupancy": outcomes["post_burn_in_mean_occupancy"],
                "patch_survival_fraction": outcomes["patch_survival_fraction"],
                "extraction_propensity_before": init["extraction_propensity_mean"],
                "extraction_propensity_after": final["extraction_propensity_mean"],
                "maintenance_propensity_before": init["maintenance_propensity_mean"],
                "maintenance_propensity_after": final["maintenance_propensity_mean"],
            }
        )
    return pd.DataFrame(rows)


def run(
    out_root: str = "outputs/level03b_fitness_stream",
    registry_path: str = "outputs/level03b_candidate_registry/candidate_registry.json",
    n_seeds: int = N_SEEDS,
    n_steps: int = N_STEPS,
) -> dict:
    run_level_path = os.path.join(out_root, "fitness_stream_run_level.csv")
    summary_path = os.path.join(out_root, "level03b_fitness_stream_summary.json")
    original = pd.read_csv(run_level_path)

    with open(registry_path, "r", encoding="utf-8") as fh:
        registry = json.load(fh)
    candidate_order = ["interior_persistent", "nonstationary", "near_collapse"]
    primary_key = next((k for k in candidate_order if registry["selected"].get(k)), None)
    params = registry["selected"][primary_key]["parameters"]

    comparison = {}
    corrected = original.copy()
    for mode, condition in AFFECTED_CELLS:
        before = original[(original.inheritance_mode == mode) & (original.condition == condition)].copy()
        after = _run_cell(params, mode, condition, primary_key, n_seeds, n_steps)
        comparison[f"{mode}__{condition}"] = {
            "n_seeds": len(after),
            "before_mean_occupancy": float(before["post_burn_in_mean_occupancy"].mean()) if len(before) else None,
            "after_mean_occupancy": float(after["post_burn_in_mean_occupancy"].mean()),
            "before_mean_extraction_propensity_change": float(
                (before["extraction_propensity_after"] - before["extraction_propensity_before"]).mean()
            ) if len(before) else None,
            "after_mean_extraction_propensity_change": float(
                (after["extraction_propensity_after"] - after["extraction_propensity_before"]).mean()
            ),
            "before_mean_maintenance_propensity_change": float(
                (before["maintenance_propensity_after"] - before["maintenance_propensity_before"]).mean()
            ) if len(before) else None,
            "after_mean_maintenance_propensity_change": float(
                (after["maintenance_propensity_after"] - after["maintenance_propensity_before"]).mean()
            ),
            "before_label_distribution": before["label"].value_counts().to_dict() if len(before) else {},
            "after_label_distribution": after["label"].value_counts().to_dict(),
        }
        mask = (corrected.inheritance_mode == mode) & (corrected.condition == condition)
        corrected = corrected[~mask]
        corrected = pd.concat([corrected, after], ignore_index=True)

    corrected = corrected.sort_values(["inheritance_mode", "condition", "seed"]).reset_index(drop=True)
    corrected.to_csv(run_level_path, index=False)

    summary_rows = []
    for (stream, condition), group in corrected.groupby(["fitness_stream", "condition"]):
        summary_rows.append(
            {
                "fitness_stream": stream, "condition": condition, "n_seeds": len(group),
                "mean_occupancy": float(group["post_burn_in_mean_occupancy"].mean()),
                "mean_patch_survival_fraction": float(group["patch_survival_fraction"].mean()),
                "mean_extraction_propensity_change": float(
                    (group["extraction_propensity_after"] - group["extraction_propensity_before"]).mean()
                ),
                "mean_maintenance_propensity_change": float(
                    (group["maintenance_propensity_after"] - group["maintenance_propensity_before"]).mean()
                ),
                "label_distribution": group["label"].value_counts().to_dict(),
            }
        )
    summary = {
        "design": {"n_seeds": n_seeds, "n_steps": n_steps, "primary_candidate": primary_key},
        "by_stream_and_condition": summary_rows,
        "note": (
            "fitness_stream='ecological' == ecological_inheritance_mode='independent'; fitness_stream='total' == "
            "ecological_inheritance_mode='coupled_same_model'. Ecological fitness is not described as normatively "
            "superior anywhere in this output."
        ),
        "level1_preflight_correction": {
            "affected_cells": [f"{m}__{c}" for m, c in AFFECTED_CELLS],
            "unaffected_cells_not_rerun": [
                "coupled_same_model__endogenous", "coupled_same_model__environment_only",
                "independent__endogenous", "independent__frozen", "independent__randomized",
                "independent__environment_only",
            ],
            "before_after_comparison": comparison,
            "reference": "docs/level1.0_decision_record.md; tests/test_level1_preflight_audit.py",
        },
    }
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print(f"[level1_preflight_fitness_stream_rerun] {run_level_path}")
    print(f"[level1_preflight_fitness_stream_rerun] {summary_path}")
    return summary


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
