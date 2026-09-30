#!/usr/bin/env python3
"""Level 0.3b, Work Package H: fitness-stream experiment at the primary
candidate.

The milestone brief's "fitness stream" axis (does ecological-policy
imitation select on total resources/payoff, or specifically on ecological
outcome?) maps directly onto the already-implemented
``ecological_inheritance_mode`` config field: under
``"independent"`` (this project's default), ecological-policy imitation
uses its own, ecological-only fitness stream
(``fitness_signal(..., stream="ecological")``, governed by
``fitness_mode_ecological``) — this is the ``"ecological"`` stream.
Under ``"coupled_same_model"``, one shared peer draw and Fermi decision,
computed on the **total** fitness stream, drives both the social and the
ecological copy together — this is the ``"total"`` stream. No new
architecture was needed; this script only crosses the two already-
implemented modes with the four most informative causal conditions.

**A real architectural interaction, discovered while building this
script, documented rather than silently patched around:**
``coupled_dual_imitation_round`` (the ``"coupled_same_model"`` engine)
does not check ``ecological_policy_randomized_each_step`` before copying
a peer's ecological policy — under the "randomized" counterfactual, the
copied *stored* policy value is still behaviorally inert (the per-step
decision reads a fresh i.i.d. draw, never the stored policy, exactly as
under "independent" mode), but the *reported* before/after ecological
policy composition under coupled+randomized would reflect imitation
noise on an already-behaviorally-irrelevant field. Also, freezing ecology
under ``"coupled_same_model"`` cannot use ``ecological_imitation_enabled``
(the coupled dispatch branch never reads that flag) — it necessarily
requires ``imitation_enabled=False``, which freezes *social* imitation
too, since the two dimensions share one decision by the coupled mode's
own design. Both are handled explicitly below (see
``_condition_overrides_for_mode``), not worked around.
"""

from __future__ import annotations

import json
import os

import pandas as pd

from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation
from experiments.level03b_common import build_candidate_config, continuous_outcomes, final_composition, initial_composition

N_STEPS = 600
N_SEEDS = 12
INHERITANCE_MODES = ("independent", "coupled_same_model")
CONDITIONS = ("endogenous", "frozen", "randomized", "environment_only")


def _condition_overrides_for_mode(condition: str, mode: str) -> dict:
    if condition == "endogenous":
        return {}
    if condition == "environment_only":
        return {"ecological_harvest_unit": 0.0, "ecological_maintenance_unit": 0.0, "ecological_search_cost": 0.0}
    if condition == "randomized":
        return {"ecological_policy_randomized_each_step": True}
    if condition == "frozen":
        if mode == "coupled_same_model":
            # See module docstring: the coupled dispatch branch is gated
            # on imitation_enabled, not ecological_imitation_enabled --
            # freezing ecology under coupling necessarily freezes social
            # imitation too.
            return {"imitation_enabled": False, "ecological_mutation_rate": 0.0}
        return {"ecological_imitation_enabled": False, "ecological_mutation_rate": 0.0}
    raise ValueError(condition)


def run(
    out_root: str = "outputs/level03b_fitness_stream",
    registry_path: str = "outputs/level03b_candidate_registry/candidate_registry.json",
    n_seeds: int = N_SEEDS,
    n_steps: int = N_STEPS,
) -> dict:
    os.makedirs(out_root, exist_ok=True)
    with open(registry_path, "r", encoding="utf-8") as fh:
        registry = json.load(fh)

    candidate_order = ["interior_persistent", "nonstationary", "near_collapse"]
    primary_key = next((k for k in candidate_order if registry["selected"].get(k)), None)
    if primary_key is None:
        raise RuntimeError("no registered candidate available for the fitness-stream experiment")
    params = registry["selected"][primary_key]["parameters"]

    rows = []
    for mode in INHERITANCE_MODES:
        for condition in CONDITIONS:
            overrides = _condition_overrides_for_mode(condition, mode)
            for seed in range(n_seeds):
                config = build_candidate_config(params, seed=seed, n_steps=n_steps, condition="endogenous")
                # apply ecological_inheritance_mode + this condition's
                # overrides on top of the candidate's own endogenous config
                import dataclasses

                config = dataclasses.replace(config, ecological_inheritance_mode=mode, **overrides)
                sim = Simulation(config)
                init = initial_composition(sim)
                result = sim.run()
                outcomes = continuous_outcomes(result)
                final = final_composition(result)
                rows.append(
                    {
                        "candidate": primary_key, "fitness_stream": ("ecological" if mode == "independent" else "total"),
                        "inheritance_mode": mode, "condition": condition, "seed": seed,
                        "label": outcomes["classify_regime_label"],
                        "post_burn_in_mean_occupancy": outcomes["post_burn_in_mean_occupancy"],
                        "patch_survival_fraction": outcomes["patch_survival_fraction"],
                        "extraction_propensity_before": init["extraction_propensity_mean"],
                        "extraction_propensity_after": final["extraction_propensity_mean"],
                        "maintenance_propensity_before": init["maintenance_propensity_mean"],
                        "maintenance_propensity_after": final["maintenance_propensity_mean"],
                    }
                )

    df = pd.DataFrame(rows)
    df_path = os.path.join(out_root, "fitness_stream_run_level.csv")
    df.to_csv(df_path, index=False)

    summary_rows = []
    for (stream, condition), group in df.groupby(["fitness_stream", "condition"]):
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
            "fitness_stream='ecological' == ecological_inheritance_mode='independent' (ecological-policy "
            "imitation selects on stream='ecological'); fitness_stream='total' == "
            "ecological_inheritance_mode='coupled_same_model' (one shared total-fitness decision drives both "
            "dimensions). Ecological fitness is not described as normatively superior anywhere in this output."
        ),
    }
    summary_path = os.path.join(out_root, "level03b_fitness_stream_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print(f"[level03b_fitness_stream] {df_path}")
    print(f"[level03b_fitness_stream] {summary_path}")
    return summary


if __name__ == "__main__":
    run()
