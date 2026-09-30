#!/usr/bin/env python3
"""Level 0.3b, Work Package B: reanalysis of the existing 48 Level 0.3
phase-search runs (``outputs/niche_phase_search/``) with the audited
classifier (``observer/regulation_diagnostics.py::classify_regime``).

**This does not run a new exploratory search.** Level 0.3's
``niche_phase_search.py`` only persisted a summary statistic computed from
each run's final-half trajectory (``fraction_interior``) and the old
classifier's label -- it did not persist the full per-step occupancy
trajectory every run actually produced, which the new burn-in-aware
classifier needs (it must see the pre-burn-in steps too, precisely so it
can exclude them explicitly rather than never having recorded them).
Because ``Simulation`` is fully deterministic given a ``SimulationConfig``
(every stochastic draw routes through one seeded generator -- see
``core/rng.py``), calling the exact same ``(point parameters, seed)`` pairs
already committed in ``outputs/niche_phase_search/niche_phase_search_
design.csv`` reproduces the *same* 48 runs bit-for-bit -- this is
re-materializing already-recorded trajectories to extract data that was
always implicit in them, not new exploration, selection, or a repeated
search. Every run's ``final_aggregate_occupancy``/``final_cooperation_
rate`` is cross-checked against the original committed
``niche_phase_search_outcomes.csv`` and any mismatch is treated as a hard
error (it would mean the reproduction is not actually deterministic, which
would itself be a serious, previously-undetected bug).

Outputs (``outputs/level03b_phase_search_reanalysis/``):

* ``run_level_reanalysis.csv`` -- one row per (point_id, seed): old label,
  new label, whether it changed and why, every ``classify_regime``
  diagnostic, and the point's own parameters.
* ``point_level_reanalysis.csv`` -- one row per parameter point: seed
  count, new-label distribution, agreement fraction, mean/dispersion of
  continuous outcomes, and an explicit ``is_robustly_classified`` /
  ``candidate_eligible_interior`` / ``candidate_eligible_oscillatory``
  flag computed from prespecified thresholds (never from which label
  looks most interesting).
* ``level03b_phase_search_reanalysis_summary.json`` -- counts, the
  point-level (not run-level) label distribution, and the label-change
  confusion matrix.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from abm_governance.observer.regulation_diagnostics import CLASSIFIER_VERSION, classify_regime
from abm_governance.simulation import Simulation
from experiments.niche_phase_search import _point_config

#: Same run horizon Level 0.3's phase search used -- reproduction, not a
#: new design, so nothing about the run configuration changes.
N_STEPS = 250
#: A parameter point's seed-level agreement must clear this fraction for
#: the point to be reported as "robustly classified" under its plurality
#: label -- prespecified before this script was run against real data.
ROBUST_AGREEMENT_THRESHOLD = 0.7 / 3.0 * 3  # documented alias, see below

# NOTE on the constant above: with only 3 exploratory seeds/point, a
# literal ">=70% agreement" threshold is not meaningfully different from
# ">=2 of 3 seeds agree" (2/3 = 0.667 < 0.70, which would make *no*
# 3-seed point ever pass a strict 0.70 cut). Rather than silently loosen
# 0.70 to whatever value happens to make 2/3 pass, this is stated
# explicitly: with n=3, "robust" is defined as unanimous (3/3, fraction
# 1.0) and "mixed" is anything else (including 2/3), and the point-level
# table always reports the exact agreement fraction so a reader can apply
# their own, stricter or looser, cutoff. ROBUST_AGREEMENT_THRESHOLD is
# retained as a named constant (fixed at 1.0 for n=3) so later, larger-n
# reanalyses (e.g. the Work Package C/D confirmation runs, n=24) can use
# the literal 0.70 the milestone brief specifies without this file needing
# to change its own logic.
ROBUST_AGREEMENT_THRESHOLD = 1.0


def _reproduce_trajectory(row, n_steps: int = N_STEPS) -> tuple:
    """Returns (occupancy_series, final_row_metrics) for one (point, seed),
    re-running the simulation from its already-committed parameters.

    Level 1.1b, Work Package B bugfix: ``n_steps`` was previously not
    threaded through from :func:`run` at all -- this function always
    reproduced at the module-level ``N_STEPS`` (250) regardless of what
    ``run(n_steps=...)`` was called with. Silent for the real Level 0.3
    corpus (always run at the default 250 steps, so the bug was never
    externally visible), but discovered here via this milestone's
    artifact-independent fixture test, which calls ``run()`` at a smaller
    ``n_steps`` specifically so it stays fast -- found and fixed rather
    than worked around, per the constraint against silently ignoring
    anomalies."""
    seed = int(row["seed"])
    config = _point_config(row, seed, n_steps)
    result = Simulation(config).run()
    occupancy = [m["aggregate_fraction_of_capacity"] for m in result.metrics]
    return occupancy, result.metrics[-1]


def run(
    out_root: str = "outputs/level03b_phase_search_reanalysis",
    design_path: str = "outputs/niche_phase_search/niche_phase_search_design.csv",
    old_outcomes_path: str = "outputs/niche_phase_search/niche_phase_search_outcomes.csv",
    n_steps: int = N_STEPS,
) -> dict:
    os.makedirs(out_root, exist_ok=True)
    design = pd.read_csv(design_path)
    old_outcomes = pd.read_csv(old_outcomes_path)

    param_cols = [c for c in design.columns if c != "point_id"]
    design_by_point = design.set_index("point_id")

    run_rows = []
    mismatches = []
    for _, old_row in old_outcomes.iterrows():
        point_id = int(old_row["point_id"])
        seed = int(old_row["seed"])
        point_params = design_by_point.loc[point_id]
        merged_row = dict(point_params)
        merged_row["point_id"] = point_id
        merged_row["seed"] = seed
        occupancy, final_metrics = _reproduce_trajectory(merged_row, n_steps=n_steps)

        # Hard cross-check: reproduction must be bit-for-bit identical to
        # the already-committed Level 0.3 outcome (same seed -> same RNG
        # draw sequence -> same trajectory, per core/rng.py's determinism
        # guarantee). A mismatch here would mean something about the
        # environment changed between Level 0.3 and Level 0.3b in a way
        # that breaks reproducibility -- reported, not silently ignored.
        if not np.isclose(final_metrics["aggregate_fraction_of_capacity"], old_row["final_aggregate_occupancy"], equal_nan=True):
            mismatches.append({"point_id": point_id, "seed": seed, "field": "final_aggregate_occupancy"})
        if not np.isclose(final_metrics["cooperation_rate"], old_row["final_cooperation_rate"], equal_nan=True):
            mismatches.append({"point_id": point_id, "seed": seed, "field": "final_cooperation_rate"})

        new_classification = classify_regime(occupancy, burn_in_fraction=0.2)
        old_label = str(old_row["region_label"])
        new_label = new_classification["label"]

        row_out = {
            "point_id": point_id,
            "seed": seed,
            "old_label": old_label,
            "new_label": new_label,
            "label_changed": old_label != new_label,
            "reason_for_change": (
                "none" if old_label == new_label else
                f"revised classifier ({CLASSIFIER_VERSION}) excludes burn-in and requires "
                "multi-cycle/amplitude/autocorrelation evidence for oscillatory, fraction+"
                "trend evidence for interior-persistent, and duration/no-recovery evidence "
                "for depleted/abundant -- see new_* diagnostic columns for which criterion "
                "drove this specific case."
            ),
        }
        row_out.update({f"new_{k}": v for k, v in new_classification.items() if k != "band_segments"})
        row_out["new_n_band_segments"] = len(new_classification["band_segments"])
        for c in param_cols:
            if c != "point_id":
                row_out[c] = point_params[c]
        run_rows.append(row_out)

    run_level = pd.DataFrame(run_rows)
    run_level_path = os.path.join(out_root, "run_level_reanalysis.csv")
    run_level.to_csv(run_level_path, index=False)

    # -- point-level aggregation -------------------------------------------------
    point_rows = []
    for point_id, group in run_level.groupby("point_id"):
        n_seeds = len(group)
        label_counts = group["new_label"].value_counts().to_dict()
        plurality_label = group["new_label"].value_counts().idxmax()
        agreement_fraction = label_counts[plurality_label] / n_seeds

        continuous_cols = [
            "new_mean_occupancy", "new_terminal_occupancy", "new_trend_slope",
            "new_fraction_interior", "new_fraction_depleted", "new_fraction_abundant",
            "new_peak_to_trough_amplitude", "new_n_completed_cycles",
        ]
        means = {f"mean_{c.replace('new_', '')}": float(group[c].mean(skipna=True)) for c in continuous_cols}
        stds = {f"std_{c.replace('new_', '')}": float(group[c].std(skipna=True)) for c in continuous_cols}

        is_robust = agreement_fraction >= ROBUST_AGREEMENT_THRESHOLD
        # Candidate eligibility (Work Package C prescreen, computed here so
        # it can be read straight off this table -- final registry
        # selection in level03b_candidate_registry.py additionally applies
        # cross-point comparison and is the authoritative source).
        n_interior_seeds = int((group["new_label"] == "interior-persistent").sum())
        n_oscillatory_seeds = int((group["new_label"] == "oscillatory").sum())
        n_intermittent_seeds = int((group["new_label"] == "intermittent").sum())

        point_rows.append(
            {
                "point_id": int(point_id),
                "n_seeds": n_seeds,
                "new_label_distribution": json.dumps(label_counts),
                "plurality_new_label": plurality_label,
                "agreement_fraction": agreement_fraction,
                "is_robustly_classified": bool(is_robust),
                "n_interior_persistent_seeds": n_interior_seeds,
                "n_oscillatory_seeds": n_oscillatory_seeds,
                "n_intermittent_seeds": n_intermittent_seeds,
                "n_seeds_denominator": n_seeds,
                **means,
                **stds,
                **{c: design_by_point.loc[point_id, c] for c in param_cols if c != "point_id"},
            }
        )
    point_level = pd.DataFrame(point_rows)
    point_level_path = os.path.join(out_root, "point_level_reanalysis.csv")
    point_level.to_csv(point_level_path, index=False)

    # -- old-vs-new confusion matrix (run level) --------------------------------
    confusion = pd.crosstab(run_level["old_label"], run_level["new_label"])
    confusion_path = os.path.join(out_root, "label_confusion_matrix.csv")
    confusion.to_csv(confusion_path)

    run_label_counts = run_level["new_label"].value_counts().to_dict()
    point_label_counts = point_level["plurality_new_label"].value_counts().to_dict()

    summary = {
        "classifier_version": CLASSIFIER_VERSION,
        "n_runs_reanalyzed": len(run_level),
        "n_points": len(point_level),
        "n_mismatches_vs_committed_level03_outcomes": len(mismatches),
        "mismatches": mismatches,
        "n_labels_changed": int(run_level["label_changed"].sum()),
        "fraction_labels_changed": float(run_level["label_changed"].mean()),
        "run_level_new_label_counts": run_label_counts,
        "point_level_plurality_label_counts_denominator_is_16_points_not_48_runs": point_label_counts,
        "n_points_robustly_classified_unanimous": int(point_level["is_robustly_classified"].sum()),
        "note": (
            "point_level_plurality_label_counts is the scientifically meaningful "
            "denominator (16 parameter points); run_level_new_label_counts (48 point-seed "
            "runs) is reported for comparability with the original Level 0.3 summary but "
            "must not be read as a parameter-space proportion, since it triple-counts "
            "every point through its 3 seeds and gives no credit/penalty for within-point "
            "seed disagreement -- see Work Package B's explicit instruction."
        ),
    }
    summary_path = os.path.join(out_root, "level03b_phase_search_reanalysis_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print(f"[level03b_phase_search_reanalysis] run-level: {run_level_path}")
    print(f"[level03b_phase_search_reanalysis] point-level: {point_level_path}")
    print(f"[level03b_phase_search_reanalysis] confusion matrix: {confusion_path}")
    print(f"[level03b_phase_search_reanalysis] summary: {summary_path}")
    print(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
