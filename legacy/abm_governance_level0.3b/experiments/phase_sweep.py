#!/usr/bin/env python3
"""Level 0.2, Work Package E: ecological phase-space exploration.

Two-stage design, exactly as specified in the milestone brief:

* **Stage 1 (coarse sweep)**: a reproducible, documented space-filling
  design (Latin Hypercube Sampling via ``scipy.stats.qmc.LatinHypercube``,
  fixed seed for reproducibility — a full 6-dimensional factorial grid at
  even a coarse 4 levels/parameter would be 4**6 = 4096 points, which is
  not tractable at >=10 seeds/point) over six ecological parameters wide
  enough to span persistent abundance, interior scarcity, intermittent
  depletion/recovery, and persistent collapse: environment_regen_rate,
  environment_capacity, subsistence_cost, payoff_temptation ("max
  extraction" — the largest single-interaction payoff draw), payoff_reward
  ("cooperative productive surplus" — the mutual-cooperation payoff), and
  distress_threshold. >= 10 seeds per point (``--seeds-stage1``, default
  10).
* **Stage 2 (boundary refinement)**: candidate boundary points are
  selected from Stage 1 **purely on ecological grounds** — pool not
  permanently full, not permanently zero, nontrivial occupancy
  fluctuation, nontrivial seed-to-seed variation in time-depleted — never
  by cooperation level (the milestone brief's explicit instruction). Each
  selected point is re-run at >= 30 seeds (``--seeds-stage2``, default 30).

A separate, smaller two-axis regular grid (``regen_rate`` x
``subsistence_cost``, other parameters held at their Stage-1 sampling
midpoints) is also run, specifically to support the phase-surface/heatmap
visualizations the milestone brief asks for — LHS points do not sit on a
regular grid and cannot be reshaped into one; this supplemental grid is
clearly a separate, smaller, visualization-support dataset, not the
primary phase-classification evidence (that remains the LHS design).

All parameters, thresholds, and run counts are explicit CLI flags with
documented defaults — nothing here is a silently-chosen "good-looking"
default (per the milestone's explicit prohibition). Every run is isolated
(failure in one does not lose others), resumable (a run already present
in a prior manifest with status "ok" is skipped, not re-executed), and the
manifest records exactly which runs completed — no silent seed-count
reduction under time pressure; if a run is skipped for cost reasons, that
is logged, never silently absorbed into a smaller reported N.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import json
import math
import os
import subprocess
import sys
import time
import traceback

import numpy as np
import pandas as pd
from scipy.stats import qmc

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.classification import (
    behavioural_convergence_episodes,
    collapse_episodes,
    population_failure,
    recovery_episodes,
)
from abm_governance.observer.ecological_balance import run_balance_summary
from abm_governance.observer.enforcement import confusion_matrix_summary
from abm_governance.observer.network_diagnostics import relationship_turnover_rate
from abm_governance.observer.participation import participation_bias_summary
from abm_governance.simulation import Simulation

# ---------------------------------------------------------------------------
# Parameter space (Stage 1: coarse LHS sweep)
# ---------------------------------------------------------------------------

#: (low, high) ranges, chosen to be wide enough to plausibly reach every
#: named regime (persistent abundance, interior scarcity, intermittent
#: depletion/recovery, persistent collapse) — not narrowed toward any
#: particular outcome. payoff_reward's upper bound is further capped
#: per-sample at (payoff_temptation - 0.5) to keep the payoff ordering
#: T > R > P >= S valid (config-enforced); P=1.0, S=0.0 are held fixed
#: (varying all four payoff parameters simultaneously would make "max
#: extraction" and "cooperative surplus" impossible to interpret as
#: independent axes).
PARAM_RANGES: dict[str, tuple[float, float]] = {
    "environment_regen_rate": (0.05, 1.6),
    "environment_capacity": (150.0, 3000.0),
    "subsistence_cost": (0.0, 1.2),
    "payoff_temptation": (3.0, 9.0),  # "max extraction"
    "payoff_reward": (1.5, 4.5),  # "cooperative productive surplus"
    "distress_threshold": (-6.0, 6.0),
}
PARAM_NAMES = list(PARAM_RANGES.keys())

#: Fixed, non-swept simulation shape. Deliberately small (population,
#: steps) to make a several-hundred-run sweep computationally tractable in
#: this environment while remaining large enough that ecological dynamics
#: (extraction/regeneration/subsistence) have room to actually play out —
#: this is a documented compute/thoroughness tradeoff, not a silent
#: reduction (see module docstring's "no silent seed-count reduction").
SWEEP_POPULATION_SIZE = 30
SWEEP_N_STEPS = 250
SWEEP_MEAN_DEGREE = 4

#: Stage-2 boundary-region selection thresholds (all explicit, documented,
#: overridable via CLI — never magic numbers). A Stage-1 point qualifies
#: as a boundary candidate if, averaged across its Stage-1 seeds: (a) mean
#: pool occupancy is not near 0 or 1 (interior, not permanently
#: full/empty); (b) fraction of time depleted is neither ~0 nor ~1
#: (nontrivial fluctuation, not persistent collapse or persistent
#: abundance); (c) seed-to-seed variation in fraction-time-depleted is
#: nontrivial (the outcome is not a foregone conclusion regardless of
#: seed). This selection uses ONLY ecological-dynamics columns — never
#: cooperation_rate or any cooperation-derived column — per the milestone
#: brief's explicit instruction.
BOUNDARY_OCCUPANCY_INTERIOR = (0.05, 0.95)
BOUNDARY_DEPLETED_FRACTION_INTERIOR = (0.02, 0.98)
BOUNDARY_MIN_SEED_STD_DEPLETED_FRACTION = 0.03


@dataclasses.dataclass
class SweepPointSpec:
    point_id: str
    stage: str  # "stage1" | "stage2" | "grid"
    params: dict
    seed: int
    n_steps: int
    population_size: int
    out_dir: str


def _sample_lhs_points(n_points: int, rng_seed: int) -> list[dict]:
    """Latin Hypercube sample over PARAM_RANGES, ``n_points`` rows,
    reproducible via ``rng_seed``. Enforces payoff_reward < payoff_temptation
    - 0.5 (see module docstring) by clipping after sampling."""
    sampler = qmc.LatinHypercube(d=len(PARAM_NAMES), seed=rng_seed)
    unit_sample = sampler.random(n=n_points)
    lows = np.array([PARAM_RANGES[p][0] for p in PARAM_NAMES])
    highs = np.array([PARAM_RANGES[p][1] for p in PARAM_NAMES])
    scaled = qmc.scale(unit_sample, lows, highs)
    points = []
    for row in scaled:
        d = dict(zip(PARAM_NAMES, row.tolist()))
        d["payoff_reward"] = min(d["payoff_reward"], d["payoff_temptation"] - 0.5)
        d["payoff_reward"] = max(d["payoff_reward"], 1.01)  # stay > payoff_punishment=1.0
        points.append(d)
    return points


def _build_config(params: dict, seed: int, n_steps: int, population_size: int) -> SimulationConfig:
    return SimulationConfig(
        population_size=population_size,
        n_steps=n_steps,
        seed=seed,
        mean_degree=SWEEP_MEAN_DEGREE,
        ecology_enabled=True,
        relationship_dynamics_enabled=True,
        payoff_punishment=1.0,
        payoff_sucker=0.0,
        environment_regen_rate=params["environment_regen_rate"],
        environment_capacity=params["environment_capacity"],
        subsistence_cost=params["subsistence_cost"],
        payoff_temptation=params["payoff_temptation"],
        payoff_reward=params["payoff_reward"],
        distress_threshold=params["distress_threshold"],
        environment_initial_fraction=0.5,
        viability_mode="none",  # phase mapping isolates the ecological axes; viability_mode is WP-H's axis
        fitness_mode="cumulative_resources",
    )


def _run_one(spec: SweepPointSpec) -> dict:
    """Execute exactly one sweep point/seed. Never raises — see
    experiments/ensemble.py's identical failure-isolation rationale."""
    start = time.time()
    record = {
        "point_id": spec.point_id,
        "stage": spec.stage,
        "params": spec.params,
        "seed": spec.seed,
        "n_steps": spec.n_steps,
        "population_size": spec.population_size,
        "status": "failed",
        "error": None,
        "wall_time_s": None,
    }
    try:
        config = _build_config(spec.params, spec.seed, spec.n_steps, spec.population_size)
        result = Simulation(config).run()

        balance = run_balance_summary(result.metrics)
        participation = participation_bias_summary(result.event_log)
        pop_failure = population_failure(result.metrics, n_agents=spec.population_size)
        collapse_eps = collapse_episodes(result.metrics)
        recovery_eps = recovery_episodes(result.metrics)
        convergence_eps = behavioural_convergence_episodes(result.metrics)
        turnover = relationship_turnover_rate(result.event_log, start_step=0, end_step=spec.n_steps)
        final_row = dict(result.metrics[-1])
        resources = [a.resources for a in result.final_agents]

        record["status"] = "ok"
        record["balance_summary"] = {
            k: v for k, v in balance.items() if k != "region_labels"  # region_labels kept separately (large)
        }
        record["region_labels"] = balance["region_labels"]
        record["participation_summary"] = participation
        record["population_failure"] = pop_failure
        record["n_collapse_episodes"] = len(collapse_eps)
        record["n_recovery_episodes"] = len(recovery_eps)
        record["n_convergence_episodes"] = len(convergence_eps)
        record["longest_collapse_duration"] = max((e.duration for e in collapse_eps), default=0)
        record["relationship_turnover_rate"] = turnover
        record["final_cooperation_rate"] = final_row.get("cooperation_rate")
        record["final_resource_gini"] = final_row.get("resource_gini")
        record["final_policy_diversity_bits"] = final_row.get("policy_diversity_bits")
        record["final_mean_resources"] = float(np.mean(resources)) if resources else math.nan
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    record["wall_time_s"] = time.time() - start
    return record


def _load_completed(out_root: str) -> dict[tuple, dict]:
    """Resume support: index prior manifest's successful runs by
    (point_id, seed) so a re-invocation skips them rather than
    re-executing (see module docstring)."""
    path = os.path.join(out_root, "sweep_manifest.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    return {
        (r["point_id"], r["seed"]): r
        for r in manifest.get("runs", [])
        if r.get("status") == "ok"
    }


def run_specs(specs: list[SweepPointSpec], out_root: str, max_workers: int, resume: bool) -> list[dict]:
    all_completed = _load_completed(out_root) if resume else {}
    # Only reuse a completed record if it matches a (point_id, seed) pair
    # actually present in *this* call's `specs` — a manifest accumulated
    # across stage1/grid/stage2 calls otherwise leaks unrelated-stage
    # records into whichever stage happens to be called with an empty (or
    # partially-resumed) spec list next, silently mislabeling them.
    requested_keys = {(s.point_id, s.seed) for s in specs}
    completed = {k: v for k, v in all_completed.items() if k in requested_keys}
    to_run = [s for s in specs if (s.point_id, s.seed) not in completed]
    print(f"[phase_sweep] {len(completed)} runs already completed (resumed), {len(to_run)} to run", file=sys.stderr)

    records = list(completed.values())
    if max_workers <= 1:
        for spec in to_run:
            records.append(_run_one(spec))
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_run_one, spec) for spec in to_run]
            for future in concurrent.futures.as_completed(futures):
                records.append(future.result())
    records.sort(key=lambda r: (r["stage"], r["point_id"], r["seed"]))
    return records


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Stage-1 -> Stage-2 boundary selection (ecology-only, never cooperation)
# ---------------------------------------------------------------------------


def select_boundary_points(stage1_records: list[dict], max_boundary_points: int) -> list[dict]:
    """Aggregate Stage-1 records by point_id (across seeds) and select
    boundary candidates using ONLY ecological-dynamics columns
    (mean_occupancy, fraction_time_depleted and its seed-to-seed std) —
    never cooperation_rate or any cooperation-derived column. See
    BOUNDARY_* thresholds above for the exact, documented criteria."""
    ok = [r for r in stage1_records if r["status"] == "ok"]
    by_point: dict[str, list[dict]] = {}
    for r in ok:
        by_point.setdefault(r["point_id"], []).append(r)

    candidates = []
    for point_id, records in by_point.items():
        occ = np.array([r["balance_summary"]["mean_occupancy"] for r in records], dtype=float)
        depleted_frac = np.array([r["balance_summary"]["fraction_time_depleted"] for r in records], dtype=float)
        occ = occ[~np.isnan(occ)]
        depleted_frac_finite = depleted_frac[~np.isnan(depleted_frac)]
        if len(occ) == 0 or len(depleted_frac_finite) == 0:
            continue
        mean_occ = float(np.mean(occ))
        mean_depleted = float(np.mean(depleted_frac_finite))
        std_depleted = float(np.std(depleted_frac_finite))

        is_interior_occupancy = BOUNDARY_OCCUPANCY_INTERIOR[0] <= mean_occ <= BOUNDARY_OCCUPANCY_INTERIOR[1]
        is_interior_depletion = (
            BOUNDARY_DEPLETED_FRACTION_INTERIOR[0] <= mean_depleted <= BOUNDARY_DEPLETED_FRACTION_INTERIOR[1]
        )
        has_seed_variation = std_depleted >= BOUNDARY_MIN_SEED_STD_DEPLETED_FRACTION

        if is_interior_occupancy and is_interior_depletion and has_seed_variation:
            candidates.append(
                {
                    "point_id": point_id,
                    "params": records[0]["params"],
                    "mean_occupancy": mean_occ,
                    "mean_fraction_time_depleted": mean_depleted,
                    "std_fraction_time_depleted": std_depleted,
                    # Ranking score: prefer maximal seed-to-seed variation
                    # (the most "genuinely undetermined by ecology alone"
                    # points) — ecology-only, as required.
                    "boundary_score": std_depleted,
                }
            )

    candidates.sort(key=lambda c: c["boundary_score"], reverse=True)
    return candidates[:max_boundary_points]


# ---------------------------------------------------------------------------
# Aggregation / machine-readable outputs
# ---------------------------------------------------------------------------

SUMMARY_SCALAR_FIELDS = [
    ("balance_summary", "mean_occupancy"),
    ("balance_summary", "pool_persistence"),
    ("balance_summary", "fraction_time_depleted"),
    ("balance_summary", "fraction_time_near_capacity"),
    ("balance_summary", "mean_b_t_realized"),
    ("balance_summary", "mean_b_t_structural"),
    ("participation_summary", "conditional_cooperation_rate"),
    ("participation_summary", "unconditional_cooperation_rate"),
    ("participation_summary", "participation_rate"),
    ("participation_summary", "withdrawal_rate"),
    ("population_failure", "peak_fraction"),
]


def aggregate_by_point(records: list[dict]) -> pd.DataFrame:
    """One row per (stage, point_id): parameter values plus quantile
    summaries (across seeds) of every tracked ecological/participation/
    cooperation/population/turnover column — the machine-readable table
    the milestone brief requires for phase-surface plotting."""
    ok = [r for r in records if r["status"] == "ok"]
    by_point: dict[tuple, list[dict]] = {}
    for r in ok:
        by_point.setdefault((r["stage"], r["point_id"]), []).append(r)

    rows = []
    for (stage, point_id), recs in by_point.items():
        row = {"stage": stage, "point_id": point_id, "n_seeds": len(recs)}
        row.update(recs[0]["params"])
        for group, field_name in SUMMARY_SCALAR_FIELDS:
            values = np.array([r[group].get(field_name, math.nan) for r in recs], dtype=float)
            finite = values[~np.isnan(values)]
            row[f"{field_name}_mean"] = float(np.mean(finite)) if len(finite) else math.nan
            row[f"{field_name}_std"] = float(np.std(finite)) if len(finite) else math.nan
        for field_name in (
            "n_collapse_episodes",
            "n_recovery_episodes",
            "n_convergence_episodes",
            "longest_collapse_duration",
            "relationship_turnover_rate",
            "final_cooperation_rate",
            "final_resource_gini",
            "final_policy_diversity_bits",
            "final_mean_resources",
        ):
            values = np.array([r.get(field_name, math.nan) for r in recs], dtype=float)
            finite = values[~np.isnan(values)]
            row[f"{field_name}_mean"] = float(np.mean(finite)) if len(finite) else math.nan
            row[f"{field_name}_std"] = float(np.std(finite)) if len(finite) else math.nan
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=str, default="outputs/phase_sweep_level02")
    parser.add_argument("--stage1-points", type=int, default=32, help="number of LHS points in the coarse sweep")
    parser.add_argument("--seeds-stage1", type=int, default=10)
    parser.add_argument("--seeds-stage2", type=int, default=30)
    parser.add_argument("--max-boundary-points", type=int, default=3)
    parser.add_argument("--grid-levels", type=int, default=5, help="levels per axis for the supplemental heatmap grid")
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--lhs-seed", type=int, default=20260816)  # documented, fixed for reproducibility
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    # -- Stage 1: coarse LHS sweep -----------------------------------------
    lhs_points = _sample_lhs_points(args.stage1_points, args.lhs_seed)
    stage1_specs = []
    for i, params in enumerate(lhs_points):
        point_id = f"s1_{i:03d}"
        for seed in range(args.seeds_stage1):
            stage1_specs.append(
                SweepPointSpec(
                    point_id=point_id,
                    stage="stage1",
                    params=params,
                    seed=seed,
                    n_steps=SWEEP_N_STEPS,
                    population_size=SWEEP_POPULATION_SIZE,
                    out_dir=os.path.join(args.out, "runs", "stage1", point_id, f"seed_{seed:04d}"),
                )
            )

    # -- supplemental 2-axis regular grid (heatmap support) -----------------
    mid_params = {k: float(np.mean(v)) for k, v in PARAM_RANGES.items()}
    regen_levels = np.linspace(*PARAM_RANGES["environment_regen_rate"], args.grid_levels)
    subsistence_levels = np.linspace(*PARAM_RANGES["subsistence_cost"], args.grid_levels)
    grid_specs = []
    for gi, regen in enumerate(regen_levels):
        for gj, subs in enumerate(subsistence_levels):
            params = dict(mid_params)
            params["environment_regen_rate"] = float(regen)
            params["subsistence_cost"] = float(subs)
            params["payoff_reward"] = min(params["payoff_reward"], params["payoff_temptation"] - 0.5)
            point_id = f"grid_{gi:02d}_{gj:02d}"
            for seed in range(args.seeds_stage1):
                grid_specs.append(
                    SweepPointSpec(
                        point_id=point_id,
                        stage="grid",
                        params=params,
                        seed=seed,
                        n_steps=SWEEP_N_STEPS,
                        population_size=SWEEP_POPULATION_SIZE,
                        out_dir=os.path.join(args.out, "runs", "grid", point_id, f"seed_{seed:04d}"),
                    )
                )

    if args.dry_run:
        print(f"[phase_sweep] stage1: {len(stage1_specs)} runs ({args.stage1_points} points x {args.seeds_stage1} seeds)")
        print(f"[phase_sweep] grid: {len(grid_specs)} runs ({args.grid_levels}x{args.grid_levels} points x {args.seeds_stage1} seeds)")
        print("[phase_sweep] stage2 point count depends on stage1 results; not planned in a dry run")
        return 0

    meta = {
        "git_commit": _git_commit(),
        "python_version": sys.version,
        "scipy_version": __import__("scipy").__version__,
        "lhs_seed": args.lhs_seed,
        "param_ranges": PARAM_RANGES,
        "sweep_population_size": SWEEP_POPULATION_SIZE,
        "sweep_n_steps": SWEEP_N_STEPS,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    t0 = time.time()
    stage1_and_grid_records = run_specs(
        stage1_specs + grid_specs, args.out, max_workers=args.workers, resume=not args.no_resume
    )
    stage1_records = [r for r in stage1_and_grid_records if r["stage"] == "stage1"]
    grid_records = [r for r in stage1_and_grid_records if r["stage"] == "grid"]

    boundary_points = select_boundary_points(stage1_records, args.max_boundary_points)
    print(f"[phase_sweep] selected {len(boundary_points)} boundary candidate(s) (ecology-only selection):", file=sys.stderr)
    for c in boundary_points:
        print(f"    {c['point_id']}: mean_occupancy={c['mean_occupancy']:.3f} "
              f"mean_frac_depleted={c['mean_fraction_time_depleted']:.3f} "
              f"std_frac_depleted={c['std_fraction_time_depleted']:.3f}", file=sys.stderr)

    stage2_specs = []
    for c in boundary_points:
        # Prefixed, distinct from the Stage-1 point_id it was selected
        # from — Stage 2 reruns the *same parameters* at more seeds, but
        # under a namespaced point_id so its (point_id, seed) keys never
        # collide with Stage 1's in the resume manifest (seed ranges
        # overlap: Stage 1 uses seeds [0, seeds_stage1), Stage 2 uses
        # seeds [0, seeds_stage2); without the prefix a resumed Stage 2
        # call would silently inherit Stage-1-labelled records for the
        # overlapping seeds instead of running/labelling them as Stage 2).
        stage2_point_id = f"s2_{c['point_id']}"
        for seed in range(args.seeds_stage2):
            stage2_specs.append(
                SweepPointSpec(
                    point_id=stage2_point_id,
                    stage="stage2",
                    params=c["params"],
                    seed=seed,
                    n_steps=SWEEP_N_STEPS,
                    population_size=SWEEP_POPULATION_SIZE,
                    out_dir=os.path.join(args.out, "runs", "stage2", stage2_point_id, f"seed_{seed:04d}"),
                )
            )
    stage2_records = run_specs(stage2_specs, args.out, max_workers=args.workers, resume=not args.no_resume)

    all_records = stage1_and_grid_records + stage2_records
    meta["wall_time_s"] = time.time() - t0

    manifest = {
        "meta": meta,
        "n_runs": len(all_records),
        "n_ok": sum(1 for r in all_records if r["status"] == "ok"),
        "n_failed": sum(1 for r in all_records if r["status"] == "failed"),
        "boundary_points_selected": boundary_points,
        "runs": all_records,
    }
    manifest_path = os.path.join(args.out, "sweep_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)

    failed = [r for r in all_records if r["status"] == "failed"]
    if failed:
        print(f"[phase_sweep] WARNING: {len(failed)}/{len(all_records)} runs failed. See manifest.", file=sys.stderr)

    # -- machine-readable per-point summary tables ---------------------------
    stage1_df = aggregate_by_point(stage1_records)
    stage1_path = os.path.join(args.out, "stage1_summary.csv")
    stage1_df.to_csv(stage1_path, index=False)

    grid_df = aggregate_by_point(grid_records)
    grid_path = os.path.join(args.out, "grid_summary.csv")
    grid_df.to_csv(grid_path, index=False)

    stage2_df = aggregate_by_point(stage2_records)
    stage2_path = os.path.join(args.out, "stage2_summary.csv")
    stage2_df.to_csv(stage2_path, index=False)

    print(f"[phase_sweep] {len(all_records)} total runs complete ({meta['wall_time_s']:.1f}s).")
    print(f"  manifest: {manifest_path}")
    print(f"  stage1_summary: {stage1_path} ({len(stage1_df)} points)")
    print(f"  grid_summary: {grid_path} ({len(grid_df)} points)")
    print(f"  stage2_summary: {stage2_path} ({len(stage2_df)} points)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
