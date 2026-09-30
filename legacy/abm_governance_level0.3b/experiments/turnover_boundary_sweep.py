#!/usr/bin/env python3
"""Level 0.2, Work Package G: relationship turnover near the ecological
phase boundary.

Within each boundary region selected by ``experiments/phase_sweep.py``
(``outputs/phase_sweep_level02/sweep_manifest.json``'s
``boundary_points_selected``), sweeps relationship-dynamics parameters
one axis at a time (exit_cost, search_cost, connection_accept_base_prob,
mean_degree, and the relationship_exit_enabled on/off ablation) around
the Level-0.2-default values, holding the boundary point's ecological
parameters fixed. A one-axis-at-a-time local sweep, not a full factorial
across all five axes simultaneously (5+ levels each would be hundreds of
combinations per boundary point) — documented as a scope choice, not a
silent reduction.

Measures, per configuration (aggregated across seeds): turnover/
relationship-lifetime (``relationship_turnover_rate``,
``mean_relationship_age``), edge survival/component structure
(``component_count``, ``largest_component_share``), isolation
(``isolated_agent_count``), reconnection (``edges_added_count``,
``proposal_accepted_count``), policy assortativity, and — as an explicit,
documented approximation (there is no per-interaction relationship-age
stamp in the event log; adding one was out of scope for this pass) — the
run-level Pearson correlation between the per-step mean relationship age
and per-step cooperation_rate time series, as a proxy for "cooperation
conditional on partner stability." Also reports whether relational
sorting (policy_assortativity) changes materially across the swept axis.

Per the milestone brief: "Do not tune turnover merely to maximize network
movement" — this script does not select or report a "best" turnover
configuration; it reports the full swept range's outcomes for the reader
to interpret.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import json
import math
import os
import sys
import time
import traceback

import numpy as np
import pandas as pd

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.network_diagnostics import relationship_turnover_rate
from abm_governance.simulation import Simulation

N_STEPS = 250
POPULATION_SIZE = 30

#: One-axis-at-a-time sweep levels. Each entry overrides exactly one
#: SimulationConfig field away from its Level-0.2 default, holding
#: everything else (except the boundary point's own ecological
#: parameters) fixed.
AXIS_SWEEPS: dict[str, list] = {
    "exit_cost": [0.2, 1.0, 3.0],
    "search_cost": [0.05, 0.2, 0.8],
    "connection_accept_base_prob": [0.3, 0.7, 0.95],
    "mean_degree": [2, 4, 8],
    "relationship_exit_enabled": [True, False],
}


@dataclasses.dataclass
class RunSpec:
    boundary_point_id: str
    axis: str
    value: object
    seed: int
    params: dict


def _build_config(spec: RunSpec) -> SimulationConfig:
    kwargs = dict(
        population_size=POPULATION_SIZE,
        n_steps=N_STEPS,
        seed=spec.seed,
        mean_degree=4,
        ecology_enabled=True,
        relationship_dynamics_enabled=True,
        payoff_punishment=1.0,
        payoff_sucker=0.0,
        environment_initial_fraction=0.5,
        viability_mode="none",
        fitness_mode="cumulative_resources",
        **spec.params,
    )
    kwargs[spec.axis] = spec.value
    return SimulationConfig(**kwargs)


def _run_one(spec: RunSpec) -> dict:
    start = time.time()
    record = {
        "boundary_point_id": spec.boundary_point_id,
        "axis": spec.axis,
        "value": spec.value,
        "seed": spec.seed,
        "status": "failed",
        "error": None,
    }
    try:
        config = _build_config(spec)
        result = Simulation(config).run()
        metrics = result.metrics

        ages = np.array([r.get("mean_relationship_age", math.nan) for r in metrics], dtype=float)
        coop = np.array([r.get("cooperation_rate", math.nan) for r in metrics], dtype=float)
        finite_mask = ~(np.isnan(ages) | np.isnan(coop))
        if finite_mask.sum() >= 3 and np.std(ages[finite_mask]) > 0 and np.std(coop[finite_mask]) > 0:
            corr = float(np.corrcoef(ages[finite_mask], coop[finite_mask])[0, 1])
        else:
            corr = math.nan

        record["status"] = "ok"
        record["relationship_turnover_rate"] = relationship_turnover_rate(result.event_log, 0, N_STEPS)
        record["mean_relationship_age_final"] = metrics[-1].get("mean_relationship_age")
        record["component_count_final"] = metrics[-1].get("component_count")
        record["largest_component_share_final"] = metrics[-1].get("largest_component_share")
        record["isolated_agent_count_final"] = metrics[-1].get("isolated_agent_count")
        record["policy_assortativity_final"] = metrics[-1].get("policy_assortativity")
        record["edges_added_total"] = sum(1 for e in result.event_log.edges_added)
        record["edges_removed_total"] = sum(1 for e in result.event_log.edges_removed)
        record["proposal_accepted_total"] = sum(1 for e in result.event_log.connection_proposals if e.accepted)
        record["age_cooperation_correlation"] = corr
        record["final_cooperation_rate"] = metrics[-1].get("cooperation_rate")
        record["final_mean_occupancy"] = metrics[-1].get("environment_fraction_of_capacity")
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    record["wall_time_s"] = time.time() - start
    return record


def run_specs(specs: list[RunSpec], max_workers: int) -> list[dict]:
    records: list[dict] = []
    if max_workers <= 1:
        for spec in specs:
            records.append(_run_one(spec))
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_run_one, spec) for spec in specs]
            for future in concurrent.futures.as_completed(futures):
                records.append(future.result())
    records.sort(key=lambda r: (r["boundary_point_id"], r["axis"], str(r["value"]), r["seed"]))
    return records


def aggregate(records: list[dict]) -> pd.DataFrame:
    ok = [r for r in records if r["status"] == "ok"]
    fields = [
        "relationship_turnover_rate", "mean_relationship_age_final", "component_count_final",
        "largest_component_share_final", "isolated_agent_count_final", "policy_assortativity_final",
        "edges_added_total", "edges_removed_total", "proposal_accepted_total",
        "age_cooperation_correlation", "final_cooperation_rate", "final_mean_occupancy",
    ]
    rows = []
    keys = sorted({(r["boundary_point_id"], r["axis"], str(r["value"])) for r in ok})
    for bp, axis, value_str in keys:
        subset = [r for r in ok if r["boundary_point_id"] == bp and r["axis"] == axis and str(r["value"]) == value_str]
        row = {"boundary_point_id": bp, "axis": axis, "value": subset[0]["value"], "n_seeds": len(subset)}
        for f in fields:
            vals = np.array([r[f] for r in subset], dtype=float)
            finite = vals[~np.isnan(vals)]
            row[f"{f}_mean"] = float(np.mean(finite)) if len(finite) else math.nan
            row[f"{f}_std"] = float(np.std(finite)) if len(finite) else math.nan
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sweep-manifest", type=str, default="outputs/phase_sweep_level02/sweep_manifest.json")
    parser.add_argument("--out", type=str, default="outputs/turnover_boundary_level02")
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(args.sweep_manifest, "r", encoding="utf-8") as fh:
        sweep_manifest = json.load(fh)
    boundary_points = sweep_manifest["boundary_points_selected"]
    if not boundary_points:
        print("[turnover_boundary_sweep] No boundary points found — nothing to do.", file=sys.stderr)
        return 1

    specs = []
    for bp in boundary_points:
        for axis, values in AXIS_SWEEPS.items():
            for value in values:
                for seed in range(args.seeds):
                    specs.append(RunSpec(boundary_point_id=bp["point_id"], axis=axis, value=value, seed=seed, params=bp["params"]))

    if args.dry_run:
        print(f"[turnover_boundary_sweep] would run {len(specs)} simulations "
              f"({len(boundary_points)} boundary points x "
              f"{sum(len(v) for v in AXIS_SWEEPS.values())} axis-values x {args.seeds} seeds)")
        return 0

    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()
    records = run_specs(specs, max_workers=args.workers)
    wall_time = time.time() - t0

    manifest = {
        "meta": {"n_steps": N_STEPS, "axis_sweeps": AXIS_SWEEPS, "boundary_points": boundary_points, "wall_time_s": wall_time},
        "n_runs": len(records),
        "n_ok": sum(1 for r in records if r["status"] == "ok"),
        "n_failed": sum(1 for r in records if r["status"] == "failed"),
        "runs": records,
    }
    manifest_path = os.path.join(args.out, "turnover_boundary_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)

    summary_df = aggregate(records)
    summary_path = os.path.join(args.out, "turnover_boundary_summary.csv")
    summary_df.to_csv(summary_path, index=False)

    failed = [r for r in records if r["status"] == "failed"]
    if failed:
        print(f"[turnover_boundary_sweep] WARNING: {len(failed)}/{len(records)} runs failed.", file=sys.stderr)

    print(f"[turnover_boundary_sweep] {len(records)} runs complete ({wall_time:.1f}s).")
    print(f"  manifest: {manifest_path}")
    print(f"  summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
