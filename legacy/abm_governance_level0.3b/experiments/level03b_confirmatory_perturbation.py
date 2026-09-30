#!/usr/bin/env python3
"""Level 0.3b, Work Package K: confirmatory perturbation experiment at the
registered candidates, using the repaired Work Package J eligibility
screen and recovery definition
(``observer/regulation_diagnostics.py::assess_perturbation_recovery``).

Reuses the seven shock implementations and the ``alive=False`` +
edge-severance "removal" operationalization from Level 0.3's
``niche_perturbation_recovery.py`` unchanged (imported directly, not
duplicated) -- only the config-building (candidate-specific, via
``level03b_common.build_candidate_config``) and the recovery diagnostic
(eligibility-screened, sustained-recovery-aware) are new.

The primary candidate gets all seven shocks at >= 20 seeds, with the
endogenous-vs-``frozen`` "does recovery need the feedback loop"
comparison for two shocks (documented reduction, same as Level 0.3's own
WP-J precedent). Secondary candidates get the four priority shocks the
milestone brief names (``local_patch_depletion``, ``regen_reduction``,
``remove_high_extraction_agents``, ``remove_high_maintenance_agents``) at
a documented, smaller seed count, endogenous only.

Per the milestone's explicit instruction, a candidate whose own baseline
fails the eligibility screen for a given shock/seed is *not* silently
scored as recovered or non-recovered for that run -- ``eligible: False``
rows are retained in the output and reported in the eligibility-fraction
summary, never dropped or coerced.
"""

from __future__ import annotations

import json
import math
import os

import numpy as np
import pandas as pd

from abm_governance.observer.regulation_diagnostics import assess_perturbation_recovery
from abm_governance.simulation import Simulation
from experiments.level03b_common import build_candidate_config
from experiments.niche_perturbation_recovery import SHOCK_TYPES, _apply_shock, _maybe_restore_temporary_shock

N_STEPS = 600
SHOCK_STEP = 300
PRE_SHOCK_WINDOW = 40
PRIMARY_N_SEEDS = 20
SECONDARY_N_SEEDS = 8
PRIORITY_SHOCKS = (
    "local_patch_depletion", "regen_reduction", "remove_high_extraction_agents", "remove_high_maintenance_agents",
)
PRIMARY_FROZEN_COMPARISON_SHOCKS = ("local_patch_depletion", "remove_random_agents")


def _run_with_optional_shock(config, shock_type, shock_seed: int, n_steps: int, shock_step: int) -> list:
    sim = Simulation(config)
    shock_rng = np.random.default_rng(shock_seed)
    metrics = []
    for step in range(n_steps):
        _maybe_restore_temporary_shock(sim, step)
        if shock_type is not None and step == shock_step:
            _apply_shock(sim, shock_type, shock_rng, step)
        metrics.append(sim._run_one_step(step))
    return metrics


def _candidate_shocks(is_primary: bool) -> tuple:
    return SHOCK_TYPES if is_primary else PRIORITY_SHOCKS


def run(
    out_root: str = "outputs/level03b_confirmatory_perturbation",
    registry_path: str = "outputs/level03b_candidate_registry/candidate_registry.json",
    n_steps: int = N_STEPS,
    shock_step: int = SHOCK_STEP,
    primary_n_seeds: int = PRIMARY_N_SEEDS,
    secondary_n_seeds: int = SECONDARY_N_SEEDS,
) -> dict:
    os.makedirs(out_root, exist_ok=True)
    with open(registry_path, "r", encoding="utf-8") as fh:
        registry = json.load(fh)

    candidate_order = ["interior_persistent", "nonstationary", "near_collapse"]
    primary_key = next((k for k in candidate_order if registry["selected"].get(k)), None)

    trajectory_rows = []
    recovery_rows = []
    failures = []
    design_notes = {}

    for key in candidate_order:
        candidate = registry["selected"].get(key)
        if candidate is None:
            continue
        params = candidate["parameters"]
        is_primary = key == primary_key
        n_seeds = primary_n_seeds if is_primary else secondary_n_seeds
        shocks = _candidate_shocks(is_primary)
        frozen_shocks = PRIMARY_FROZEN_COMPARISON_SHOCKS if is_primary else ()
        design_notes[key] = {
            "role": "primary" if is_primary else "secondary", "n_seeds": n_seeds, "shocks": list(shocks),
            "frozen_comparison_shocks": list(frozen_shocks),
        }

        for shock_type in shocks:
            for seed in range(n_seeds):
                conditions = ("endogenous", "frozen") if shock_type in frozen_shocks else ("endogenous",)
                for condition in conditions:
                    control_occupancy = None
                    for arm, apply_shock in (("control", False), ("shocked", True)):
                        try:
                            config = build_candidate_config(
                                params, seed=seed, n_steps=n_steps, condition=("frozen" if condition == "frozen" else "endogenous")
                            )
                            metrics = _run_with_optional_shock(
                                config,
                                shock_type if apply_shock else None,
                                shock_seed=seed * 1000 + hash((key, shock_type)) % 1000,
                                n_steps=n_steps, shock_step=shock_step,
                            )
                        except Exception as exc:  # pragma: no cover - defensive, reported not swallowed
                            failures.append(
                                {"candidate": key, "shock_type": shock_type, "condition": condition, "seed": seed,
                                 "arm": arm, "error": f"{type(exc).__name__}: {exc}"}
                            )
                            continue
                        occ = [m["aggregate_fraction_of_capacity"] for m in metrics]
                        for row, occ_val in zip(metrics, occ):
                            trajectory_rows.append(
                                {
                                    "candidate": key, "shock_type": shock_type, "condition": condition,
                                    "seed": seed, "arm": arm, "step": row["step"], "occupancy": occ_val,
                                }
                            )
                        if not apply_shock:
                            control_occupancy = occ
                        else:
                            pre = occ[max(0, shock_step - PRE_SHOCK_WINDOW) : shock_step]
                            post = occ[shock_step:]
                            control_post = control_occupancy[shock_step:] if control_occupancy is not None else None
                            diag = assess_perturbation_recovery(pre, post, control_post_shock_series=control_post)
                            recovery_rows.append(
                                {"candidate": key, "shock_type": shock_type, "condition": condition, "seed": seed, **diag}
                            )

    trajectories = pd.DataFrame(trajectory_rows)
    trajectories_path = os.path.join(out_root, "confirmatory_perturbation_trajectories.csv")
    trajectories.to_csv(trajectories_path, index=False)

    recovery = pd.DataFrame(recovery_rows)
    recovery_path = os.path.join(out_root, "confirmatory_perturbation_recovery.csv")
    recovery.to_csv(recovery_path, index=False)

    aggregate = {}
    if not recovery.empty:
        for (cand, shock_type, condition), group in recovery.groupby(["candidate", "shock_type", "condition"]):
            eligible = group[group["eligible"] == True]  # noqa: E712
            aggregate[f"{cand}__{shock_type}__{condition}"] = {
                "n_seeds": len(group),
                "n_eligible": len(eligible),
                "fraction_eligible": float(len(eligible) / len(group)) if len(group) else math.nan,
                "fraction_recovered_of_eligible": (
                    float(eligible["recovered"].mean()) if len(eligible) and eligible["recovered"].notna().any() else None
                ),
                "mean_time_to_sustained_recovery": (
                    float(eligible["time_to_sustained_recovery"].dropna().mean())
                    if len(eligible) and eligible["time_to_sustained_recovery"].notna().any() else None
                ),
                "mean_overshoot": float(eligible["overshoot"].mean()) if len(eligible) else None,
                "ineligibility_reasons_seen": sorted(
                    set(r for reasons in group["ineligibility_reasons"] for r in (reasons or []))
                ),
            }

    summary = {
        "design": {
            "n_steps": n_steps, "shock_step": shock_step, "pre_shock_window": PRE_SHOCK_WINDOW,
            "candidates": design_notes,
            "scale_reduction_note": (
                "secondary candidates use 4 priority shocks (local_patch_depletion, regen_reduction, "
                "remove_high_extraction_agents, remove_high_maintenance_agents) at 8 seeds instead of the full 7 "
                "shocks at >=20 seeds, and skip the endogenous-vs-frozen comparison entirely -- a documented "
                "compute-budget reduction; the primary candidate runs the full spec."
            ),
        },
        "n_failures": len(failures),
        "failures": failures,
        "recovery_by_candidate_shock_condition": aggregate,
    }
    summary_path = os.path.join(out_root, "level03b_confirmatory_perturbation_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print(f"[level03b_confirmatory_perturbation] {trajectories_path}")
    print(f"[level03b_confirmatory_perturbation] {recovery_path}")
    print(f"[level03b_confirmatory_perturbation] {summary_path}")
    return summary


if __name__ == "__main__":
    run()
