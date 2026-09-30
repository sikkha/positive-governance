#!/usr/bin/env python3
"""Level 0.2, Work Package H: null models and causal factorial comparisons.

Rather than an intractable full Cartesian product over every mechanism
switch (viability_mode x fitness_mode x punishment x relationship_
dynamics x ecological_region would be 3x4x2x2x3 = 144 cells before even
adding seeds), this script runs the four 2-way factorial slices the
milestone brief explicitly requires at minimum, each holding every
mechanism *not* under test at its Level-0.2 default:

* ``viability_mode x fitness_mode`` (at the boundary ecological region)
* ``ecological_region x fitness_mode``
* ``ecological_region x punishment_enabled``
* ``ecological_region x relationship_dynamics_enabled`` (turnover on/off)

"ecological_region" here means one of three representative parameter
sets — "abundant" and "depleted" (read from
``outputs/phase_sweep_level02/stage1_summary.csv``: the Stage-1 point
with the highest mean occupancy, and one with a fully-depleted mean
occupancy of exactly 0, respectively) and "boundary" (the first
boundary point ``experiments/phase_sweep.py`` selected) — not a
predetermined governance macrotype; these are ecological-parameter
presets chosen purely for their observed pool-occupancy regime.

Every cell is run at >= ``--seeds`` (default 15) seeds; effect
distributions across seeds are reported (mean/std, not a single-seed
point estimate) for every tracked outcome column, per the milestone
brief's anti-endpoint-mean-only requirement carried over from Level 0.1's
ensemble runner.
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
from abm_governance.observer.ecological_balance import run_balance_summary
from abm_governance.observer.enforcement import confusion_matrix_summary
from abm_governance.observer.network_diagnostics import relationship_turnover_rate
from abm_governance.observer.participation import participation_bias_summary
from abm_governance.observer.viability import population_state_summary
from abm_governance.simulation import Simulation

N_STEPS = 200
POPULATION_SIZE = 30

VIABILITY_MODES = ["none", "dormancy_recovery", "removal_replacement"]
FITNESS_MODES = ["cumulative_resources", "recent_payoff", "resource_delta", "viability_adjusted"]


def _load_regions(sweep_dir: str) -> dict[str, dict]:
    stage1 = pd.read_csv(os.path.join(sweep_dir, "stage1_summary.csv"))
    with open(os.path.join(sweep_dir, "sweep_manifest.json"), "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    boundary_points = manifest["boundary_points_selected"]
    if not boundary_points:
        raise RuntimeError("no boundary points in sweep manifest; run experiments/phase_sweep.py first")

    param_cols = [
        "environment_regen_rate", "environment_capacity", "subsistence_cost",
        "payoff_temptation", "payoff_reward", "distress_threshold",
    ]
    abundant_row = stage1.sort_values("mean_occupancy_mean", ascending=False).iloc[0]
    depleted_candidates = stage1[stage1["mean_occupancy_mean"] == 0]
    depleted_row = (depleted_candidates if len(depleted_candidates) else stage1.sort_values("mean_occupancy_mean")).iloc[0]

    return {
        "abundant": {c: float(abundant_row[c]) for c in param_cols},
        "depleted": {c: float(depleted_row[c]) for c in param_cols},
        "boundary": dict(boundary_points[0]["params"]),
    }


@dataclasses.dataclass
class RunSpec:
    slice_name: str
    region: str
    factor_value: object
    seed: int
    overrides: dict


def _build_config(spec: RunSpec, region_params: dict) -> SimulationConfig:
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
        punishment_enabled=True,
        **region_params,
    )
    kwargs.update(spec.overrides)
    return SimulationConfig(**kwargs)


def _run_one(spec: RunSpec, region_params: dict) -> dict:
    start = time.time()
    record = {
        "slice": spec.slice_name,
        "region": spec.region,
        "factor_value": spec.factor_value,
        "seed": spec.seed,
        "status": "failed",
        "error": None,
    }
    try:
        config = _build_config(spec, region_params)
        result = Simulation(config).run()
        balance = run_balance_summary(result.metrics)
        participation = participation_bias_summary(result.event_log)
        pop_summary = population_state_summary(result.event_log, n_steps=N_STEPS)
        confusion = confusion_matrix_summary(result.event_log)
        turnover = relationship_turnover_rate(result.event_log, 0, N_STEPS)
        final_row = dict(result.metrics[-1])

        record["status"] = "ok"
        record["mean_occupancy"] = balance["mean_occupancy"]
        record["fraction_time_depleted"] = balance["fraction_time_depleted"]
        record["conditional_cooperation_rate"] = participation["conditional_cooperation_rate"]
        record["unconditional_cooperation_rate"] = participation["unconditional_cooperation_rate"]
        record["participation_rate"] = participation["participation_rate"]
        record["total_removals"] = pop_summary["total_removals"]
        record["total_recoveries"] = pop_summary["total_recoveries"]
        record["p_punishment_given_actual_defection"] = confusion["p_punishment_given_actual_defection"]
        record["relationship_turnover_rate"] = turnover
        record["final_resource_gini"] = final_row.get("resource_gini")
        record["final_policy_diversity_bits"] = final_row.get("policy_diversity_bits")
        record["final_mean_resources"] = final_row.get("mean_resources")
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    record["wall_time_s"] = time.time() - start
    return record


def build_slices(regions: dict[str, dict], seeds: int) -> list[RunSpec]:
    specs: list[RunSpec] = []

    # Slice 1: viability_mode x fitness_mode, at the boundary region only.
    for vm in VIABILITY_MODES:
        for fm in FITNESS_MODES:
            for seed in range(seeds):
                specs.append(
                    RunSpec(
                        slice_name="viability_mode_x_fitness_mode",
                        region="boundary",
                        factor_value=f"{vm}|{fm}",
                        seed=seed,
                        overrides={"viability_mode": vm, "fitness_mode": fm},
                    )
                )

    # Slice 2: ecological_region x fitness_mode.
    for region in regions:
        for fm in FITNESS_MODES:
            for seed in range(seeds):
                specs.append(
                    RunSpec(
                        slice_name="region_x_fitness_mode",
                        region=region,
                        factor_value=fm,
                        seed=seed,
                        overrides={"fitness_mode": fm},
                    )
                )

    # Slice 3: ecological_region x punishment_enabled.
    for region in regions:
        for punishment in (True, False):
            for seed in range(seeds):
                specs.append(
                    RunSpec(
                        slice_name="region_x_punishment",
                        region=region,
                        factor_value=punishment,
                        seed=seed,
                        overrides={"punishment_enabled": punishment},
                    )
                )

    # Slice 4: ecological_region x relationship_dynamics (turnover on/off).
    for region in regions:
        for turnover_on in (True, False):
            for seed in range(seeds):
                specs.append(
                    RunSpec(
                        slice_name="region_x_relationship_turnover",
                        region=region,
                        factor_value=turnover_on,
                        seed=seed,
                        overrides={"relationship_dynamics_enabled": turnover_on},
                    )
                )

    return specs


def run_specs(specs: list[RunSpec], regions: dict[str, dict], max_workers: int) -> list[dict]:
    records: list[dict] = []
    if max_workers <= 1:
        for spec in specs:
            records.append(_run_one(spec, regions[spec.region]))
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_run_one, spec, regions[spec.region]) for spec in specs]
            for future in concurrent.futures.as_completed(futures):
                records.append(future.result())
    records.sort(key=lambda r: (r["slice"], r["region"], str(r["factor_value"]), r["seed"]))
    return records


def aggregate(records: list[dict]) -> pd.DataFrame:
    ok = [r for r in records if r["status"] == "ok"]
    fields = [
        "mean_occupancy", "fraction_time_depleted", "conditional_cooperation_rate",
        "unconditional_cooperation_rate", "participation_rate", "total_removals", "total_recoveries",
        "p_punishment_given_actual_defection", "relationship_turnover_rate",
        "final_resource_gini", "final_policy_diversity_bits", "final_mean_resources",
    ]
    rows = []
    keys = sorted({(r["slice"], r["region"], str(r["factor_value"])) for r in ok})
    for slice_name, region, fv_str in keys:
        subset = [r for r in ok if r["slice"] == slice_name and r["region"] == region and str(r["factor_value"]) == fv_str]
        row = {"slice": slice_name, "region": region, "factor_value": subset[0]["factor_value"], "n_seeds": len(subset)}
        for f in fields:
            vals = np.array([r[f] for r in subset], dtype=float)
            finite = vals[~np.isnan(vals)]
            row[f"{f}_mean"] = float(np.mean(finite)) if len(finite) else math.nan
            row[f"{f}_std"] = float(np.std(finite)) if len(finite) else math.nan
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sweep-dir", type=str, default="outputs/phase_sweep_level02")
    parser.add_argument("--out", type=str, default="outputs/null_model_comparisons_level02")
    parser.add_argument("--seeds", type=int, default=15)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    regions = _load_regions(args.sweep_dir)
    specs = build_slices(regions, args.seeds)

    if args.dry_run:
        print(f"[null_model_comparisons] would run {len(specs)} simulations across 4 factorial slices")
        for slice_name in sorted({s.slice_name for s in specs}):
            n = sum(1 for s in specs if s.slice_name == slice_name)
            print(f"  - {slice_name}: {n} runs")
        return 0

    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()
    records = run_specs(specs, regions, max_workers=args.workers)
    wall_time = time.time() - t0

    manifest = {
        "meta": {"n_steps": N_STEPS, "regions": regions, "seeds_per_cell": args.seeds, "wall_time_s": wall_time},
        "n_runs": len(records),
        "n_ok": sum(1 for r in records if r["status"] == "ok"),
        "n_failed": sum(1 for r in records if r["status"] == "failed"),
        "runs": records,
    }
    manifest_path = os.path.join(args.out, "null_model_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)

    summary_df = aggregate(records)
    summary_path = os.path.join(args.out, "null_model_summary.csv")
    summary_df.to_csv(summary_path, index=False)

    failed = [r for r in records if r["status"] == "failed"]
    if failed:
        print(f"[null_model_comparisons] WARNING: {len(failed)}/{len(records)} runs failed.", file=sys.stderr)

    print(f"[null_model_comparisons] {len(records)} runs complete ({wall_time:.1f}s).")
    print(f"  manifest: {manifest_path}")
    print(f"  summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
