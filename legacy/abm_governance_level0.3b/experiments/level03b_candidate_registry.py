#!/usr/bin/env python3
"""Level 0.3b, Work Package C: prospective candidate-selection registry.

Selects up to three candidate parameter points -- interior-persistent,
oscillatory-or-intermittent, near-collapse/transition -- from the
combined Work Package B reanalysis (the original 16-point Level 0.3
search) and the prespecified supplemental search (32 points, run only
because Work Package B found no eligible interior/nonstationary candidate
-- see ``dev_mem/status_update.md``), using **only** the prespecified
ecological/dynamical criteria below. Selection never reads, and this
module never computes, any social co-operation statistic, any similarity
measure to the dissertation's governance trajectories, or any causal
result (causal interventions have not even been run yet at the point this
script executes in the milestone's work-package order).

Once written, ``outputs/level03b_candidate_registry/candidate_registry.json``
is the single source of truth for every downstream confirmation, causal,
robustness, and perturbation script in this milestone -- none of them
re-select candidates; they all read this file. `test_candidate_registry_
immutability` (``tests/test_level03b_candidates.py``) checks that a second
call to this module with unchanged inputs reproduces the identical
registry (deterministic selection), and this module is never invoked a
second time with different logic after being read downstream in this
milestone.
"""

from __future__ import annotations

import json
import os

import pandas as pd

from experiments.niche_phase_search import _INT_PARAMS

REANALYSIS_POINT_LEVEL = "outputs/level03b_phase_search_reanalysis/point_level_reanalysis.csv"
SUPPLEMENTAL_POINT_LEVEL = "outputs/level03b_supplemental_search/supplemental_point_level.csv"
DESIGN_ORIGINAL = "outputs/niche_phase_search/niche_phase_search_design.csv"
DESIGN_SUPPLEMENTAL = "outputs/level03b_supplemental_search/supplemental_design.csv"

#: Interior-persistent eligibility: at least this many of 3 exploratory
#: seeds must individually satisfy the revised interior criterion.
INTERIOR_MIN_SEEDS_OF_3 = 2
#: Oscillatory/intermittent eligibility: at least one seed must satisfy
#: the respective revised criterion (oscillatory tried first; per the
#: milestone's explicit instruction, if none qualifies, fall back to
#: intermittent rather than manufacturing an oscillatory candidate).
NONSTATIONARY_MIN_SEEDS = 1


def _load_combined_points() -> pd.DataFrame:
    original = pd.read_csv(REANALYSIS_POINT_LEVEL)
    original["source"] = "original_16pt_reanalysis"
    original["design_path"] = DESIGN_ORIGINAL

    supplemental = pd.read_csv(SUPPLEMENTAL_POINT_LEVEL)
    supplemental["source"] = "supplemental_32pt_search"
    supplemental["design_path"] = DESIGN_SUPPLEMENTAL
    supplemental["agreement_fraction"] = supplemental.apply(
        lambda r: max(json.loads(r["label_counts"]).values()) / r["n_seeds"], axis=1
    )
    supplemental["mean_mean_occupancy"] = supplemental["mean_mean_occupancy"]

    keep_cols = [
        "point_id", "source", "design_path", "n_seeds", "plurality_new_label",
        "agreement_fraction", "n_interior_persistent_seeds", "n_oscillatory_seeds",
        "n_intermittent_seeds", "mean_mean_occupancy", "mean_terminal_occupancy",
    ]
    original_slim = original[[c for c in keep_cols if c in original.columns]].copy()
    supplemental_slim = supplemental[[c for c in keep_cols if c in supplemental.columns]].copy()
    combined = pd.concat([original_slim, supplemental_slim], ignore_index=True)
    combined["combined_key"] = combined["source"] + ":" + combined["point_id"].astype(str)
    return combined


def _point_parameters(source: str, point_id: int) -> dict:
    path = DESIGN_ORIGINAL if source == "original_16pt_reanalysis" else DESIGN_SUPPLEMENTAL
    design = pd.read_csv(path)
    row = design[design.point_id == point_id].iloc[0]
    params = {}
    for c in design.columns:
        if c == "point_id":
            continue
        params[c] = int(row[c]) if c in _INT_PARAMS else (str(row[c]) if c == "fitness_mode" else float(row[c]))
    return params


def select_candidates(combined: pd.DataFrame) -> dict:
    eligible_interior = combined[combined["n_interior_persistent_seeds"] >= INTERIOR_MIN_SEEDS_OF_3].copy()
    eligible_oscillatory = combined[combined["n_oscillatory_seeds"] >= NONSTATIONARY_MIN_SEEDS].copy()
    eligible_intermittent = combined[combined["n_intermittent_seeds"] >= NONSTATIONARY_MIN_SEEDS].copy()

    rejected = []
    selected = {}

    # -- Candidate 1: interior-persistent. Tie-break, in order: more
    # individually-passing seeds first, then lowest (source, point_id) for
    # a fully deterministic, outcome-blind tie-break (not "which point
    # looks nicest"). --------------------------------------------------
    if not eligible_interior.empty:
        eligible_interior = eligible_interior.sort_values(
            ["n_interior_persistent_seeds", "source", "point_id"], ascending=[False, True, True]
        )
        chosen = eligible_interior.iloc[0]
        selected["interior_persistent"] = {
            "source": chosen["source"],
            "point_id": int(chosen["point_id"]),
            "n_interior_persistent_seeds_of_3": int(chosen["n_interior_persistent_seeds"]),
            "agreement_fraction": float(chosen["agreement_fraction"]),
            "mean_occupancy_exploratory": float(chosen["mean_mean_occupancy"]),
            "eligibility_rule": f">= {INTERIOR_MIN_SEEDS_OF_3} of 3 exploratory seeds satisfy classify_regime's interior-persistent criterion",
        }
        for _, r in eligible_interior.iloc[1:].iterrows():
            rejected.append(
                {
                    "candidate_type": "interior_persistent", "source": r["source"], "point_id": int(r["point_id"]),
                    "reason": "eligible but not selected -- lower n_interior_persistent_seeds or tie-broken by (source, point_id) order, not by outcome preference",
                }
            )
    else:
        selected["interior_persistent"] = None

    # -- Candidate 2: oscillatory, falling back to intermittent. --------
    if not eligible_oscillatory.empty:
        eligible_oscillatory = eligible_oscillatory.sort_values(
            ["n_oscillatory_seeds", "source", "point_id"], ascending=[False, True, True]
        )
        chosen = eligible_oscillatory.iloc[0]
        selected["nonstationary"] = {
            "type": "oscillatory",
            "source": chosen["source"],
            "point_id": int(chosen["point_id"]),
            "n_oscillatory_seeds_of_3": int(chosen["n_oscillatory_seeds"]),
            "eligibility_rule": f">= {NONSTATIONARY_MIN_SEEDS} of 3 exploratory seeds satisfy classify_regime's oscillatory criterion",
        }
    elif not eligible_intermittent.empty:
        eligible_intermittent = eligible_intermittent.sort_values(
            ["n_intermittent_seeds", "source", "point_id"], ascending=[False, True, True]
        )
        chosen = eligible_intermittent.iloc[0]
        selected["nonstationary"] = {
            "type": "intermittent",
            "source": chosen["source"],
            "point_id": int(chosen["point_id"]),
            "n_intermittent_seeds_of_3": int(chosen["n_intermittent_seeds"]),
            "eligibility_rule": (
                f"no point satisfied the oscillatory criterion (0 of {len(combined)} points searched across both "
                f"batches had any oscillatory seed); falling back to intermittent per the milestone's explicit "
                f"instruction not to manufacture an oscillatory candidate -- "
                f">= {NONSTATIONARY_MIN_SEEDS} of 3 exploratory seeds satisfy classify_regime's intermittent criterion"
            ),
        }
    else:
        selected["nonstationary"] = None

    # -- Candidate 3: near-collapse/transition. Prespecified metric:
    # smallest |mean_occupancy - depletion_threshold| among points whose
    # mean_occupancy is still above the depletion threshold (i.e. sitting
    # just above the collapse boundary, not already fully collapsed) --
    # ecological proximity to a transition, never a preferred behavioral
    # label. Points already selected above are excluded. -----------------
    already_selected_keys = set()
    if selected.get("interior_persistent"):
        already_selected_keys.add((selected["interior_persistent"]["source"], selected["interior_persistent"]["point_id"]))
    if selected.get("nonstationary"):
        already_selected_keys.add((selected["nonstationary"]["source"], selected["nonstationary"]["point_id"]))

    depletion_threshold = 0.05
    remaining = combined[combined["mean_mean_occupancy"] > depletion_threshold].copy()
    remaining = remaining[
        ~remaining.apply(lambda r: (r["source"], int(r["point_id"])) in already_selected_keys, axis=1)
    ]
    remaining["distance_to_depletion_threshold"] = (remaining["mean_mean_occupancy"] - depletion_threshold).abs()
    remaining = remaining.sort_values(["distance_to_depletion_threshold", "source", "point_id"])
    if not remaining.empty:
        chosen = remaining.iloc[0]
        selected["near_collapse"] = {
            "source": chosen["source"],
            "point_id": int(chosen["point_id"]),
            "mean_occupancy_exploratory": float(chosen["mean_mean_occupancy"]),
            "distance_to_depletion_threshold": float(chosen["distance_to_depletion_threshold"]),
            "eligibility_rule": (
                "smallest |mean_occupancy - depletion_threshold(0.05)| among points with mean_occupancy > "
                "depletion_threshold, i.e. ecologically closest to the collapse boundary without having already "
                "collapsed -- selected by proximity to transition, not by any behavioral or social co-operation outcome"
            ),
        }
    else:
        selected["near_collapse"] = None

    return {"selected": selected, "rejected": rejected}


def run(out_root: str = "outputs/level03b_candidate_registry") -> dict:
    os.makedirs(out_root, exist_ok=True)
    combined = _load_combined_points()
    selection = select_candidates(combined)

    registry = {
        "classifier_version": "0.3b-v1",
        "source_experiments": [
            "experiments/level03b_phase_search_reanalysis.py (original 16-point Level 0.3 search, reanalyzed)",
            "experiments/level03b_supplemental_search.py (prespecified 32-point supplemental search)",
        ],
        "selection_criteria": {
            "interior_persistent": f">= {INTERIOR_MIN_SEEDS_OF_3} of 3 exploratory seeds individually satisfy classify_regime's interior-persistent criterion; ties broken by more passing seeds, then lowest (source, point_id) -- never by outcome preference",
            "oscillatory_or_intermittent": f">= {NONSTATIONARY_MIN_SEEDS} exploratory seed satisfies the oscillatory criterion; if none exists across both batches, fall back to intermittent under the same rule; if neither exists, record that no nonstationary candidate qualified",
            "near_collapse": "smallest |mean_occupancy - depletion_threshold| among non-collapsed points, excluding points already selected above -- ecological proximity to transition, not a preferred behavioral outcome",
        },
        "exclusion_rules": [
            "selection never reads social co-operation, sanctioning, or any social-game statistic",
            "selection never compares a point to the dissertation's three governance trajectories",
            "selection never reads any causal-intervention or perturbation-recovery result (none exist yet at this point in the milestone's work-package order)",
            "once selected and written to this file, a candidate is not replaced because its later causal/confirmation results are disappointing",
        ],
        "n_points_searched_total": int(len(combined)),
        "n_points_searched_original": int((combined["source"] == "original_16pt_reanalysis").sum()),
        "n_points_searched_supplemental": int((combined["source"] == "supplemental_32pt_search").sum()),
        "selected": selection["selected"],
        "rejected_candidates": selection["rejected"],
        "confirmation_plan": {
            "seeds_per_candidate": {"primary_interior_persistent": 24, "secondary_nonstationary": 24, "secondary_near_collapse": 24},
            "n_steps": 600,
            "burn_in_fraction": 0.2,
            "primary_and_secondary_outcomes": [
                "seed-level label distribution and agreement (Work Package D)",
                "post-burn-in mean/minimum/terminal occupancy, trend, depletion/abundance duration (Work Package D)",
                "parameter-neighborhood robustness (Work Package E)",
                "causal-intervention continuous paired effects vs. 7 counterfactual conditions (Work Packages F/G)",
                "fitness-stream sensitivity at the primary candidate (Work Package H)",
                "micro-macro linkage (Work Package I)",
                "perturbation-recovery eligibility and recovery quality (Work Packages J/K)",
            ],
        },
    }
    for key in ("interior_persistent", "nonstationary", "near_collapse"):
        if registry["selected"].get(key):
            source = registry["selected"][key]["source"]
            point_id = registry["selected"][key]["point_id"]
            registry["selected"][key]["parameters"] = _point_parameters(source, point_id)

    registry_path = os.path.join(out_root, "candidate_registry.json")
    with open(registry_path, "w", encoding="utf-8") as fh:
        json.dump(registry, fh, indent=2, default=str)

    print(f"[level03b_candidate_registry] {registry_path}")
    print(json.dumps({"selected": registry["selected"]}, indent=2, default=str))
    return registry


if __name__ == "__main__":
    run()
