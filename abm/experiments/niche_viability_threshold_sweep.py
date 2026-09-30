#!/usr/bin/env python3
"""Level 0.3, Work Package G: viability-threshold experiment.

Retains the Level 0.2 viability state machine unchanged (see
``simulation.py::_viability_round``); this experiment's purpose is to
find *where the mechanism becomes causally active* under the patches
topology (i.e. at what deficit-duration / distress-threshold combination
agents actually start entering distress, dormancy, and (in
``removal_replacement`` mode) replacement) -- not to maximize removals or
to tune toward any particular outcome.

Staged design (avoids the full high-dimensional product, per the
milestone's explicit allowance): a small, deliberately coarse grid over
``distress_threshold`` x ``viability_deficit_steps_threshold`` x
``viability_mode``, a handful of seeds per point. Reported per point:
number of agents entering distress/dormancy over the run, number
recovering vs. (in ``removal_replacement`` mode) removed, the duration
distribution of each state (reconstructed from paired
enter/exit ``ViabilityTransitionEvent``s per agent), and the population's
ecological-policy and social-policy composition **before** (the initial,
as-constructed population) vs. **after** (the final living population)
the run, so a compositional shift attributable to viability filtering
(as opposed to imitation/mutation) can at least be inspected.

**Scale note (documented reduction).** ``distress_threshold in {2.0, 8.0}``
x ``viability_deficit_steps_threshold in {5, 20}`` x
``viability_mode in {"none", "dormancy_recovery", "removal_replacement"}``
(the threshold pair is only meaningful for the two non-"none" modes, so
"none" is run once per threshold pair for completeness but the threshold
values themselves have no effect in that mode) x ``N_SEEDS`` seeds each
-- a small, staged grid, not the milestone's full "as needed" language
taken to its maximum; ``run()`` accepts a custom grid for a
larger follow-up sweep.
"""

from __future__ import annotations

import itertools
import json
import os

import numpy as np
import pandas as pd

from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation

N_SEEDS = 5
POPULATION_SIZE = 24
N_STEPS = 200
N_PATCHES = 4
MEAN_DEGREE = 4

DISTRESS_THRESHOLDS = (2.0, 8.0)
DEFICIT_STEP_THRESHOLDS = (5, 20)
VIABILITY_MODES = ("none", "dormancy_recovery", "removal_replacement")


def _initial_composition(sim: Simulation) -> dict:
    """Population composition as constructed, before ``run()`` mutates
    anything (imitation/mutation/replacement all happen inside
    ``run()``) -- the "before filtering" snapshot."""
    ext = np.array([a.ecological_policy.extraction_propensity for a in sim.agents])
    maint = np.array([a.ecological_policy.maintenance_propensity for a in sim.agents])
    scar = np.array([a.ecological_policy.scarcity_sensitivity for a in sim.agents])
    from collections import Counter

    return {
        "n_agents": len(sim.agents),
        "social_policy_counts": dict(Counter(a.policy.name for a in sim.agents)),
        "extraction_propensity_mean": float(ext.mean()),
        "maintenance_propensity_mean": float(maint.mean()),
        "scarcity_sensitivity_mean": float(scar.mean()),
    }


def _final_composition(result) -> dict:
    from collections import Counter

    living = [a for a in result.final_agents if a.alive]
    if not living:
        return {"n_agents": 0, "social_policy_counts": {}, "extraction_propensity_mean": float("nan"),
                "maintenance_propensity_mean": float("nan"), "scarcity_sensitivity_mean": float("nan")}
    ext = np.array([a.ecological_policy.extraction_propensity for a in living])
    maint = np.array([a.ecological_policy.maintenance_propensity for a in living])
    scar = np.array([a.ecological_policy.scarcity_sensitivity for a in living])
    return {
        "n_agents": len(living),
        "social_policy_counts": dict(Counter(a.policy.name for a in living)),
        "extraction_propensity_mean": float(ext.mean()),
        "maintenance_propensity_mean": float(maint.mean()),
        "scarcity_sensitivity_mean": float(scar.mean()),
    }


def _state_durations(event_log, from_state: str, to_state_matcher) -> list[int]:
    """Reconstruct per-agent durations spent in ``from_state`` by pairing
    each transition *into* ``from_state`` with that same agent's next
    transition *out* of it (whichever state it goes to next -- recovery,
    further decline, or removal). An agent still in ``from_state`` at the
    end of the run (no matching exit event) is excluded, not imputed with
    a guessed duration."""
    events = sorted(event_log.viability_transitions, key=lambda e: (e.agent, e.step))
    by_agent: dict[int, list] = {}
    for e in events:
        by_agent.setdefault(e.agent, []).append(e)
    durations = []
    for agent_events in by_agent.values():
        for i, e in enumerate(agent_events):
            if e.to_state != from_state:
                continue
            if i + 1 < len(agent_events):
                exit_event = agent_events[i + 1]
                durations.append(exit_event.step - e.step)
    return durations


def run(
    out_root: str,
    n_seeds: int = N_SEEDS,
    population_size: int = POPULATION_SIZE,
    n_steps: int = N_STEPS,
    distress_thresholds=DISTRESS_THRESHOLDS,
    deficit_step_thresholds=DEFICIT_STEP_THRESHOLDS,
    viability_modes=VIABILITY_MODES,
) -> dict:
    os.makedirs(out_root, exist_ok=True)
    seeds = list(range(n_seeds))
    point_rows = []
    failures = []

    grid = []
    for mode in viability_modes:
        if mode == "none":
            grid.append((mode, distress_thresholds[0], deficit_step_thresholds[0]))
        else:
            for dt, ds in itertools.product(distress_thresholds, deficit_step_thresholds):
                grid.append((mode, dt, ds))

    for mode, distress_threshold, deficit_steps in grid:
        for seed in seeds:
            try:
                config = SimulationConfig.level03_viability_sweep_base(
                    seed=seed, population_size=population_size, n_steps=n_steps,
                    n_patches=N_PATCHES, mean_degree=MEAN_DEGREE,
                    viability_mode=mode, distress_threshold=distress_threshold,
                    viability_deficit_steps_threshold=deficit_steps,
                )
                sim = Simulation(config)
                before = _initial_composition(sim)
                result = sim.run()
                after = _final_composition(result)
            except Exception as exc:  # pragma: no cover - defensive, reported not swallowed
                failures.append(
                    {"mode": mode, "distress_threshold": distress_threshold, "deficit_steps": deficit_steps,
                     "seed": seed, "error": f"{type(exc).__name__}: {exc}"}
                )
                continue

            transitions = result.event_log.viability_transitions
            n_entered_distress = sum(1 for e in transitions if e.to_state == "distressed")
            n_entered_dormant = sum(1 for e in transitions if e.to_state == "dormant")
            n_recovered = sum(1 for e in transitions if e.to_state == "active" and e.cause == "resources_recovered")
            n_removed = len(result.event_log.replacements)
            distress_durations = _state_durations(result.event_log, "distressed", None)
            dormant_durations = _state_durations(result.event_log, "dormant", None)

            point_rows.append(
                {
                    "mode": mode, "distress_threshold": distress_threshold, "deficit_steps": deficit_steps,
                    "seed": seed,
                    "n_entered_distress": n_entered_distress, "n_entered_dormant": n_entered_dormant,
                    "n_recovered": n_recovered, "n_removed": n_removed,
                    "distress_duration_mean": float(np.mean(distress_durations)) if distress_durations else float("nan"),
                    "distress_duration_n": len(distress_durations),
                    "dormant_duration_mean": float(np.mean(dormant_durations)) if dormant_durations else float("nan"),
                    "dormant_duration_n": len(dormant_durations),
                    "before_extraction_propensity_mean": before["extraction_propensity_mean"],
                    "after_extraction_propensity_mean": after["extraction_propensity_mean"],
                    "before_maintenance_propensity_mean": before["maintenance_propensity_mean"],
                    "after_maintenance_propensity_mean": after["maintenance_propensity_mean"],
                    "before_n_agents": before["n_agents"], "after_n_agents": after["n_agents"],
                    "before_social_policy_counts": json.dumps(before["social_policy_counts"]),
                    "after_social_policy_counts": json.dumps(after["social_policy_counts"]),
                }
            )

    points = pd.DataFrame(point_rows)
    points_path = os.path.join(out_root, "niche_viability_sweep_points.csv")
    points.to_csv(points_path, index=False)

    # -- per-(mode, threshold-pair) aggregate across seeds -----------------
    agg_rows = []
    if not points.empty:
        for (mode, dt, ds), group in points.groupby(["mode", "distress_threshold", "deficit_steps"]):
            agg_rows.append(
                {
                    "mode": mode, "distress_threshold": dt, "deficit_steps": ds, "n_seeds": len(group),
                    "mean_entered_distress": float(group["n_entered_distress"].mean()),
                    "mean_entered_dormant": float(group["n_entered_dormant"].mean()),
                    "mean_recovered": float(group["n_recovered"].mean()),
                    "mean_removed": float(group["n_removed"].mean()),
                    "mechanism_active": bool((group["n_entered_distress"] > 0).any()),
                }
            )
    aggregate = pd.DataFrame(agg_rows)
    aggregate_path = os.path.join(out_root, "niche_viability_sweep_aggregate.csv")
    aggregate.to_csv(aggregate_path, index=False)

    summary = {
        "design": {
            "n_seeds": len(seeds), "population_size": population_size, "n_steps": n_steps,
            "distress_thresholds": list(distress_thresholds), "deficit_step_thresholds": list(deficit_step_thresholds),
            "viability_modes": list(viability_modes), "n_grid_points": len(grid),
        },
        "n_failures": len(failures),
        "failures": failures,
        "n_points_with_mechanism_active": int(aggregate["mechanism_active"].sum()) if not aggregate.empty else 0,
        "n_points_total": int(len(aggregate)),
    }
    summary_path = os.path.join(out_root, "niche_viability_sweep_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print(f"[niche_viability_threshold_sweep] points: {points_path}")
    print(f"[niche_viability_threshold_sweep] aggregate: {aggregate_path}")
    print(f"[niche_viability_threshold_sweep] summary: {summary_path}")
    print(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=str, default="outputs/niche_viability_threshold_sweep")
    parser.add_argument("--n-seeds", type=int, default=N_SEEDS)
    args = parser.parse_args()
    run(args.out, n_seeds=args.n_seeds)
