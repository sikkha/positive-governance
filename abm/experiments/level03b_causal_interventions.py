#!/usr/bin/env python3
"""Level 0.3b, Work Packages F/G: repaired causal counterfactuals at the
registered candidates, with continuous (not just binary) paired outcomes.

For each registered candidate, runs all 7 primary conditions
(``endogenous``, ``frozen``, ``randomized``, ``shuffled``,
``environment_only``, ``maintenance_disabled``,
``ecological_mutation_disabled``) plus the preserved, relabeled
``impact_disabled`` (Level 0.3's original ``no_effect``), paired by
identical seed (same seed -> same initial network/patch assignment/
ecological-policy draw across every condition, except where a condition's
own definition necessarily changes what that seed produces, e.g.
``randomized``). The primary candidate uses >= 20 matched seeds; secondary
candidates use >= 12 (documented, per the milestone's own acceptable
secondary-candidate design).

For every seed, every Work Package G continuous outcome is computed for
every condition, and the seed-level paired difference
``endogenous - counterfactual`` is stored (never only condition means) --
paired mean/median, a percentile bootstrap CI, sign proportion, and
dispersion are reported per (candidate, condition, outcome).
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from abm_governance.observer.regulation_diagnostics import feedback_dependence, interior_persistence, nontriviality
from abm_governance.simulation import Simulation
from experiments.level03b_common import PRIMARY_CONDITIONS, build_candidate_config, continuous_outcomes

ALL_CONDITIONS = PRIMARY_CONDITIONS + ("impact_disabled",)
N_STEPS = 600
PRIMARY_N_SEEDS = 20
SECONDARY_N_SEEDS = 12
N_BOOTSTRAP = 2000

CONTINUOUS_OUTCOME_COLUMNS = [
    "post_burn_in_mean_occupancy", "terminal_window_mean_occupancy", "post_burn_in_min_occupancy",
    "cumulative_depletion_duration_steps", "area_under_occupancy_curve", "patch_survival_fraction",
    "cumulative_unmet_demand", "cumulative_extraction", "cumulative_effective_maintenance",
    "maintenance_to_extraction_ratio", "mean_patch_occupancy_gini",
]


def _run_candidate(candidate_key: str, params: dict, n_seeds: int, n_steps: int) -> pd.DataFrame:
    rows = []
    for seed in range(n_seeds):
        for condition in ALL_CONDITIONS:
            config = build_candidate_config(params, seed=seed, n_steps=n_steps, condition=condition)
            result = Simulation(config).run()
            occupancy = [m["aggregate_fraction_of_capacity"] for m in result.metrics]
            tail = occupancy[-max(1, n_steps // 2):]
            persistence = interior_persistence(tail)
            outcomes = continuous_outcomes(result)
            row = {
                "candidate": candidate_key, "seed": seed, "condition": condition,
                "fraction_interior_legacy": persistence["fraction_interior"],
                "label": outcomes["classify_regime_label"],
            }
            for c in CONTINUOUS_OUTCOME_COLUMNS:
                row[c] = outcomes[c]
            rows.append(row)
    return pd.DataFrame(rows)


def _paired_effects(df: pd.DataFrame, candidate_key: str) -> pd.DataFrame:
    """Seed-level paired differences endogenous - counterfactual, for
    every non-endogenous condition and every continuous outcome column."""
    sub = df[df["candidate"] == candidate_key]
    endo = sub[sub["condition"] == "endogenous"].set_index("seed")
    rows = []
    for condition in ALL_CONDITIONS:
        if condition == "endogenous":
            continue
        cf = sub[sub["condition"] == condition].set_index("seed")
        common_seeds = sorted(set(endo.index) & set(cf.index))
        for outcome in CONTINUOUS_OUTCOME_COLUMNS:
            diffs = []
            for s in common_seeds:
                e_val, c_val = endo.loc[s, outcome], cf.loc[s, outcome]
                if pd.isna(e_val) or pd.isna(c_val):
                    continue
                diffs.append(e_val - c_val)
            if not diffs:
                continue
            diffs = np.array(diffs, dtype=float)
            rng = np.random.default_rng(abs(hash((candidate_key, condition, outcome))) % (2**32))
            boot_means = [
                float(np.mean(rng.choice(diffs, size=len(diffs), replace=True))) for _ in range(N_BOOTSTRAP)
            ]
            ci_low, ci_high = float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5))
            rows.append(
                {
                    "candidate": candidate_key, "condition": condition, "outcome": outcome,
                    "n_seeds": len(diffs), "mean_diff": float(np.mean(diffs)), "median_diff": float(np.median(diffs)),
                    "std_diff": float(np.std(diffs)), "ci_low": ci_low, "ci_high": ci_high,
                    "fraction_positive": float(np.mean(diffs > 0)), "fraction_negative": float(np.mean(diffs < 0)),
                    "fraction_zero": float(np.mean(diffs == 0)),
                }
            )
    return pd.DataFrame(rows)


def run(
    out_root: str = "outputs/level03b_causal_interventions",
    registry_path: str = "outputs/level03b_candidate_registry/candidate_registry.json",
    n_steps: int = N_STEPS,
    primary_n_seeds: int = PRIMARY_N_SEEDS,
    secondary_n_seeds: int = SECONDARY_N_SEEDS,
) -> dict:
    os.makedirs(out_root, exist_ok=True)
    with open(registry_path, "r", encoding="utf-8") as fh:
        registry = json.load(fh)

    # The primary candidate is the interior-persistent one if it exists
    # (the milestone's own framing treats it as primary); otherwise the
    # nonstationary candidate; otherwise near_collapse.
    candidate_order = ["interior_persistent", "nonstationary", "near_collapse"]
    primary_key = next((k for k in candidate_order if registry["selected"].get(k)), None)

    all_run_rows = []
    all_effect_rows = []
    design_notes = {}
    for key in candidate_order:
        candidate = registry["selected"].get(key)
        if candidate is None:
            continue
        n_seeds = primary_n_seeds if key == primary_key else secondary_n_seeds
        design_notes[key] = {"role": "primary" if key == primary_key else "secondary", "n_seeds": n_seeds}
        df = _run_candidate(key, candidate["parameters"], n_seeds, n_steps)
        all_run_rows.append(df)
        effects = _paired_effects(df, key)
        all_effect_rows.append(effects)

    run_level = pd.concat(all_run_rows, ignore_index=True) if all_run_rows else pd.DataFrame()
    run_level_path = os.path.join(out_root, "causal_run_level.csv")
    run_level.to_csv(run_level_path, index=False)

    effects = pd.concat(all_effect_rows, ignore_index=True) if all_effect_rows else pd.DataFrame()
    effects_path = os.path.join(out_root, "causal_paired_effects.csv")
    effects.to_csv(effects_path, index=False)

    # -- legacy binary criteria (feedback_dependence/nontriviality), kept
    # for continuity with Level 0.3's own diagnostic vocabulary, computed
    # from fraction_interior_legacy (the same statistic Level 0.3 used) so
    # this milestone's finding can be directly compared to it. ------------
    binary_summary = {}
    for key in candidate_order:
        candidate = registry["selected"].get(key)
        if candidate is None:
            continue
        sub = run_level[run_level["candidate"] == key]
        endo_stat = float(sub[sub.condition == "endogenous"]["fraction_interior_legacy"].mean())
        counterfactual_stats = {
            c: float(sub[sub.condition == c]["fraction_interior_legacy"].mean())
            for c in ALL_CONDITIONS if c != "endogenous"
        }
        fd = feedback_dependence(endo_stat, counterfactual_stats)
        nt = nontriviality(endo_stat, counterfactual_stats.get("impact_disabled", float("nan")))
        binary_summary[key] = {
            "endogenous_fraction_interior": endo_stat,
            "counterfactual_fraction_interior": counterfactual_stats,
            "feedback_dependence": fd,
            "nontriviality": nt,
        }

    summary = {
        "design": {
            "n_steps": n_steps, "conditions": list(ALL_CONDITIONS), "primary_candidate": primary_key,
            "candidates": design_notes,
            "pairing_note": (
                "seeds are paired by identical integer seed across conditions for the same candidate; "
                "'randomized' necessarily produces a different per-step ecological-decision draw sequence "
                "by definition (fresh i.i.d. draw every step) even under the same seed -- see module docstring."
            ),
        },
        "binary_criteria_legacy_comparison": binary_summary,
        "n_paired_effect_rows": len(effects),
    }
    summary_path = os.path.join(out_root, "level03b_causal_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print(f"[level03b_causal_interventions] {run_level_path}")
    print(f"[level03b_causal_interventions] {effects_path}")
    print(f"[level03b_causal_interventions] {summary_path}")
    return summary


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
