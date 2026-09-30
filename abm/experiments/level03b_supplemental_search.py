#!/usr/bin/env python3
"""Level 0.3b, prespecified supplemental search (see milestone spec §8).

Invoked only because Work Package B's reanalysis of the existing 48
Level 0.3 phase-search runs found **zero** eligible interior-persistent or
oscillatory/intermittent candidates at the parameter-point level (see
`dev_mem/status_update.md`'s Level 0.3b entry, recorded *before* this
script was run). This is the single prespecified supplemental batch —
no further batches are added regardless of this batch's outcome, per the
milestone's explicit "do not repeatedly add batches until a desired
candidate appears" instruction.

Design, fixed in advance (this docstring/the status_update.md entry are
the pre-registration record):

* Fixed LHS design seed ``20260817`` + a documented, distinct salt
  (``201`` added by ``qmc.LatinHypercube(..., seed=DESIGN_SEED)`` using
  ``DESIGN_SEED = 20260817201`` -- a fresh, but fixed and disclosed,
  design point, *not* a re-roll of Level 0.3's own ``20260817`` design
  seed with the same points).
* The *same* 11 parameter ranges (``PARAM_LOWS``/``PARAM_HIGHS``) Level
  0.3's ``niche_phase_search.py`` already used, imported directly from
  that module rather than restated -- no range was widened, narrowed, or
  shifted in response to any outcome.
* One batch only: 32 parameter points, 3 screening seeds/point, 250-step
  horizon (same horizon as the original search).
* Points are classified with the audited classifier
  (``classify_regime``) exactly as Work Package B's reanalysis was; no
  point is retried, excluded, or resampled by its outcome.
"""

from __future__ import annotations

import json
import os

import pandas as pd
from scipy.stats import qmc

from abm_governance.observer.regulation_diagnostics import CLASSIFIER_VERSION, classify_regime
from abm_governance.simulation import Simulation
from experiments.niche_phase_search import PARAM_HIGHS, PARAM_LOWS, PARAM_NAMES, _INT_PARAMS, _point_config
from abm_governance.agents.fitness import VALID_FITNESS_MODES

N_POINTS = 32
SEEDS_PER_POINT = 3
N_STEPS = 250
#: Distinct from Level 0.3's own ``20260817`` phase-search design seed --
#: a fresh, but fixed and disclosed-in-advance, LHS design.
DESIGN_SEED = 20260817201


def design_matrix(n_points: int, rng_seed: int) -> pd.DataFrame:
    """Identical construction to ``niche_phase_search.design_matrix`` (same
    parameter names/ranges), duplicated here rather than imported so this
    module's design is fully self-contained and legible on its own."""
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


def run(
    out_root: str = "outputs/level03b_supplemental_search",
    n_points: int = N_POINTS,
    seeds_per_point: int = SEEDS_PER_POINT,
    n_steps: int = N_STEPS,
    design_seed: int = DESIGN_SEED,
) -> dict:
    os.makedirs(out_root, exist_ok=True)
    design = design_matrix(n_points, design_seed)
    design_path = os.path.join(out_root, "supplemental_design.csv")
    design.to_csv(design_path, index=False)

    rows = []
    failures = []
    for _, point_row in design.iterrows():
        for seed in range(seeds_per_point):
            try:
                config = _point_config(point_row, seed, n_steps)
                result = Simulation(config).run()
            except Exception as exc:  # pragma: no cover - defensive, reported not swallowed
                failures.append(
                    {"point_id": int(point_row["point_id"]), "seed": seed, "error": f"{type(exc).__name__}: {exc}"}
                )
                continue
            occupancy = [m["aggregate_fraction_of_capacity"] for m in result.metrics]
            classification = classify_regime(occupancy, burn_in_fraction=0.2)
            final_row = result.metrics[-1]
            row = {
                "point_id": int(point_row["point_id"]),
                "seed": seed,
                "final_aggregate_occupancy": final_row["aggregate_fraction_of_capacity"],
                "final_cooperation_rate": final_row["cooperation_rate"],
            }
            row.update({f"new_{k}": v for k, v in classification.items() if k != "band_segments"})
            for c in PARAM_NAMES[:-1] + ["fitness_mode"]:
                row[c] = point_row[c] if c in point_row else None
            rows.append(row)

    outcomes = pd.DataFrame(rows)
    outcomes_path = os.path.join(out_root, "supplemental_outcomes.csv")
    outcomes.to_csv(outcomes_path, index=False)

    point_rows = []
    for point_id, group in outcomes.groupby("point_id"):
        n_seeds = len(group)
        label_counts = group["new_label"].value_counts().to_dict()
        plurality_label = group["new_label"].value_counts().idxmax()
        n_interior = int((group["new_label"] == "interior-persistent").sum())
        n_oscillatory = int((group["new_label"] == "oscillatory").sum())
        n_intermittent = int((group["new_label"] == "intermittent").sum())
        point_rows.append(
            {
                "point_id": int(point_id),
                "n_seeds": n_seeds,
                "plurality_new_label": plurality_label,
                "label_counts": json.dumps(label_counts),
                "n_interior_persistent_seeds": n_interior,
                "n_oscillatory_seeds": n_oscillatory,
                "n_intermittent_seeds": n_intermittent,
                "mean_mean_occupancy": float(group["new_mean_occupancy"].mean(skipna=True)),
                "mean_terminal_occupancy": float(group["new_terminal_occupancy"].mean(skipna=True)),
            }
        )
    point_level = pd.DataFrame(point_rows)
    point_level_path = os.path.join(out_root, "supplemental_point_level.csv")
    point_level.to_csv(point_level_path, index=False)

    n_interior_eligible_points = int((point_level["n_interior_persistent_seeds"] >= 2).sum())
    n_oscillatory_eligible_points = int((point_level["n_oscillatory_seeds"] >= 1).sum())
    n_intermittent_eligible_points = int((point_level["n_intermittent_seeds"] >= 1).sum())

    summary = {
        "classifier_version": CLASSIFIER_VERSION,
        "design": {
            "n_points": n_points,
            "seeds_per_point": seeds_per_point,
            "n_steps": n_steps,
            "design_seed": design_seed,
            "param_ranges_source": "experiments.niche_phase_search.PARAM_LOWS/PARAM_HIGHS (unchanged)",
            "batches_run": 1,
            "prespecification_note": (
                "This is the single prespecified supplemental batch (milestone spec section 8); "
                "the design, ranges, and seed were fixed and recorded in dev_mem/status_update.md "
                "before this script was executed. No second batch will be run regardless of outcome."
            ),
        },
        "n_runs": len(rows),
        "n_failures": len(failures),
        "failures": failures,
        "run_level_new_label_counts": outcomes["new_label"].value_counts().to_dict() if not outcomes.empty else {},
        "point_level_plurality_label_counts": point_level["plurality_new_label"].value_counts().to_dict()
        if not point_level.empty
        else {},
        "n_points_interior_eligible_at_least_2_of_3_seeds": n_interior_eligible_points,
        "n_points_with_any_oscillatory_seed": n_oscillatory_eligible_points,
        "n_points_with_any_intermittent_seed": n_intermittent_eligible_points,
    }
    summary_path = os.path.join(out_root, "level03b_supplemental_search_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print(f"[level03b_supplemental_search] design: {design_path}")
    print(f"[level03b_supplemental_search] outcomes: {outcomes_path}")
    print(f"[level03b_supplemental_search] point-level: {point_level_path}")
    print(f"[level03b_supplemental_search] summary: {summary_path}")
    print(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
