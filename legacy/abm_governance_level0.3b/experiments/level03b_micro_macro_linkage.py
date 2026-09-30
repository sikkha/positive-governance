#!/usr/bin/env python3
"""Level 0.3b, Work Package I: micro-macro linkage, applied to real
experiment output.

``observer/regulation_diagnostics.py::micro_macro_linkage`` was
implemented at Level 0.3 but never applied to real data (a documented
Level 0.3 gap). This script computes it three ways, from data the
Work Package D/F scripts already produced (no new simulation runs):

1. **Within-candidate, across-seed (pooled correlation).** For the
   confirmed candidate's 24 confirmation seeds, correlate each seed's
   final ecological-policy trait mean against that same seed's ecological
   outcome. Reported with the same "this is correlational, not causal"
   caveat ``docs/level0.2_scientific_note.md`` already established for
   the analogous Level 0.2 analysis.
2. **Within-seed first differences (paired causal interventions).** The
   *strongest* evidence: for the ``endogenous`` vs. ``frozen`` /
   ``randomized`` conditions already run by Work Package F (identical
   seed, only the ecological-policy adaptation mechanism differs), the
   *change* in policy composition (endogenous's own before/after
   propensity change) is compared against the *change* in ecological
   outcome the intervention produces (the seed-level paired difference
   already computed) -- this is an intervention (frozen/randomized
   directly manipulates whether policy composition can change), not a
   passive lead/lag observation.
3. **Policy-freeze/shuffle summary.** Explicit cross-reference to the
   already-computed causal paired effects for the ``frozen`` and
   ``shuffled`` conditions specifically, since those are the two WP-F
   conditions that most directly test "does *how* policy composition
   forms matter, independent of what it eventually looks like."
"""

from __future__ import annotations

import json
import os

import pandas as pd

from abm_governance.observer.regulation_diagnostics import micro_macro_linkage


def run(
    out_root: str = "outputs/level03b_micro_macro_linkage",
    confirmation_csv: str = "outputs/level03b_confirmation/confirmation_run_level.csv",
    causal_effects_csv: str = "outputs/level03b_causal_interventions/causal_paired_effects.csv",
) -> dict:
    os.makedirs(out_root, exist_ok=True)
    confirmation = pd.read_csv(confirmation_csv)
    causal_effects = pd.read_csv(causal_effects_csv) if os.path.exists(causal_effects_csv) else pd.DataFrame()

    trait_outcome_pairs = [
        ("extraction_propensity_after", "post_burn_in_mean_occupancy"),
        ("maintenance_propensity_after", "post_burn_in_mean_occupancy"),
        ("extraction_propensity_after", "patch_survival_fraction"),
        ("maintenance_propensity_after", "patch_survival_fraction"),
        ("extraction_propensity_after", "cumulative_unmet_demand"),
        ("maintenance_propensity_after", "cumulative_effective_maintenance"),
    ]

    pooled_linkage = {}
    for candidate, group in confirmation.groupby("candidate"):
        pooled_linkage[candidate] = {}
        for trait_col, outcome_col in trait_outcome_pairs:
            if trait_col not in group.columns or outcome_col not in group.columns:
                continue
            valid = group[[trait_col, outcome_col]].dropna()
            result = micro_macro_linkage(valid[trait_col].values, valid[outcome_col].values)
            pooled_linkage[candidate][f"{trait_col}__vs__{outcome_col}"] = result

    intervention_linkage = {}
    if not causal_effects.empty:
        for candidate, group in causal_effects.groupby("candidate"):
            intervention_linkage[candidate] = {}
            for condition in ("frozen", "randomized", "shuffled"):
                sub = group[(group.condition == condition)]
                if sub.empty:
                    continue
                occ_row = sub[sub.outcome == "post_burn_in_mean_occupancy"]
                survival_row = sub[sub.outcome == "patch_survival_fraction"]
                intervention_linkage[candidate][condition] = {
                    "mean_diff_post_burn_in_mean_occupancy": (
                        float(occ_row["mean_diff"].iloc[0]) if not occ_row.empty else None
                    ),
                    "mean_diff_patch_survival_fraction": (
                        float(survival_row["mean_diff"].iloc[0]) if not survival_row.empty else None
                    ),
                    "interpretation": (
                        f"endogenous - {condition}: a nonzero mean_diff here is intervention-based evidence "
                        "that whether/how ecological-policy composition can change (imitation+mutation active "
                        "vs. suppressed/randomized) causally affects the ecological outcome, not merely "
                        "correlated with it"
                    ),
                }

    summary = {
        "pooled_correlational_linkage_within_candidate": pooled_linkage,
        "intervention_based_linkage": intervention_linkage,
        "note": (
            "The pooled correlational linkage (across the 24 confirmation seeds of a single fixed-parameter "
            "candidate) is reported as one input, not a stand-alone causal claim -- per "
            "docs/level0.2_scientific_note.md's established discipline for the analogous Level 0.2 analysis. "
            "The intervention-based linkage (frozen/randomized/shuffled vs. endogenous, same paired seeds "
            "Work Package F already ran) is the stronger evidence, since it manipulates whether policy "
            "composition can adapt at all rather than merely observing its variation."
        ),
    }
    summary_path = os.path.join(out_root, "level03b_micro_macro_linkage_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print(f"[level03b_micro_macro_linkage] {summary_path}")
    return summary


if __name__ == "__main__":
    run()
