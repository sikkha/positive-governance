#!/usr/bin/env python3
"""Level 0.2, Work Package J: perturbation experiment at the ecological
boundary.

Reads the boundary-region parameter points selected by
``experiments/phase_sweep.py`` (``outputs/phase_sweep_level02/
sweep_manifest.json``'s ``boundary_points_selected`` — chosen purely on
ecological grounds, never by cooperation level, per Work Package E), and,
for each one, runs a matched perturbed-vs-unperturbed pair across many
seeds for each of three implemented shock kinds (resource_depletion,
subsistence_increase, regeneration_reduction — see
``core/perturbation.py``'s module docstring for why random edge loss and
high-resource-agent removal are not implemented at this milestone: they
would require extending the perturbation interface to also receive the
live graph/agent list, which was out of scope for this pass; documented
here as a known limitation, not silently dropped).

Per the milestone's explicit instruction, this experiment is run at a
**nondegenerate boundary region**, not the permanently-collapsed Level-0.1
default. Measures immediate response, participation response, policy
response, network response, recovery/non-recovery (via
``observer/classification.py::recovery_episodes``, applied to the
post-shock window), and between-seed variation.
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
from abm_governance.observer.classification import recovery_episodes
from abm_governance.observer.ecological_balance import run_balance_summary
from abm_governance.observer.network_diagnostics import relationship_turnover_rate
from abm_governance.observer.participation import participation_bias_summary
from abm_governance.simulation import Simulation

SHOCK_KINDS: dict[str, dict] = {
    "resource_depletion": {"magnitude": 0.6},
    "subsistence_increase": {"magnitude": 1.0},
    "regeneration_reduction": {"magnitude": 0.85},
}

#: Run shape: enough pre-shock steps for the system to settle into its
#: boundary dynamics, a shock window, and a long post-shock window to
#: give recovery (if any) time to show up.
PRE_SHOCK_STEPS = 100
SHOCK_DURATION = 20
POST_SHOCK_STEPS = 200
N_STEPS = PRE_SHOCK_STEPS + SHOCK_DURATION + POST_SHOCK_STEPS
POPULATION_SIZE = 30


@dataclasses.dataclass
class RunSpec:
    boundary_point_id: str
    shock_kind: str  # "none" for the unperturbed control
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
    if spec.shock_kind != "none":
        magnitude = SHOCK_KINDS[spec.shock_kind]["magnitude"]
        kwargs["perturbations"] = (
            {"start_step": PRE_SHOCK_STEPS, "duration": SHOCK_DURATION, "kind": spec.shock_kind, "magnitude": magnitude},
        )
    return SimulationConfig(**kwargs)


def _run_one(spec: RunSpec) -> dict:
    start = time.time()
    record = {
        "boundary_point_id": spec.boundary_point_id,
        "shock_kind": spec.shock_kind,
        "seed": spec.seed,
        "status": "failed",
        "error": None,
        "wall_time_s": None,
    }
    try:
        config = _build_config(spec)
        result = Simulation(config).run()
        metrics = result.metrics

        pre = metrics[:PRE_SHOCK_STEPS]
        during = metrics[PRE_SHOCK_STEPS:PRE_SHOCK_STEPS + SHOCK_DURATION]
        post = metrics[PRE_SHOCK_STEPS + SHOCK_DURATION:]

        def _mean(rows, key):
            vals = np.array([r.get(key, math.nan) for r in rows], dtype=float)
            finite = vals[~np.isnan(vals)]
            return float(np.mean(finite)) if len(finite) else math.nan

        record["status"] = "ok"
        # Immediate response: occupancy and unmet-demand shift from
        # pre-shock mean to the shock window's mean.
        record["pre_mean_occupancy"] = _mean(pre, "environment_fraction_of_capacity")
        record["during_mean_occupancy"] = _mean(during, "environment_fraction_of_capacity")
        record["post_mean_occupancy"] = _mean(post, "environment_fraction_of_capacity")
        record["pre_unmet_demand"] = _mean(pre, "unmet_extraction_demand")
        record["during_unmet_demand"] = _mean(during, "unmet_extraction_demand")
        record["post_unmet_demand"] = _mean(post, "unmet_extraction_demand")
        # Participation response.
        record["pre_participation_rate"] = _mean(pre, "p_interaction_given_opportunity")
        record["during_participation_rate"] = _mean(during, "p_interaction_given_opportunity")
        record["post_participation_rate"] = _mean(post, "p_interaction_given_opportunity")
        # Policy (behavioural) response.
        record["pre_policy_diversity_bits"] = _mean(pre, "policy_diversity_bits")
        record["during_policy_diversity_bits"] = _mean(during, "policy_diversity_bits")
        record["post_policy_diversity_bits"] = _mean(post, "policy_diversity_bits")
        record["pre_cooperation_rate"] = _mean(pre, "cooperation_rate")
        record["during_cooperation_rate"] = _mean(during, "cooperation_rate")
        record["post_cooperation_rate"] = _mean(post, "cooperation_rate")
        # Network response.
        record["pre_turnover"] = relationship_turnover_rate(result.event_log, 0, PRE_SHOCK_STEPS)
        record["post_turnover"] = relationship_turnover_rate(
            result.event_log, PRE_SHOCK_STEPS + SHOCK_DURATION, N_STEPS
        )
        # Recovery: does post-shock occupancy return above the depletion
        # threshold for a sustained duration? Evaluated over the whole
        # series so the episode-detector can see the pre-shock depletion
        # state it needs as its "prior depletion" reference.
        recov_eps = recovery_episodes(metrics)
        post_shock_recov_eps = [e for e in recov_eps if e.start_step >= PRE_SHOCK_STEPS]
        record["recovered_after_shock"] = bool(post_shock_recov_eps)
        record["n_recovery_episodes_after_shock"] = len(post_shock_recov_eps)

        participation = participation_bias_summary(result.event_log, start_step=PRE_SHOCK_STEPS + SHOCK_DURATION, end_step=N_STEPS)
        record["post_shock_conditional_cooperation_rate"] = participation["conditional_cooperation_rate"]
        record["post_shock_unconditional_cooperation_rate"] = participation["unconditional_cooperation_rate"]
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
    records.sort(key=lambda r: (r["boundary_point_id"], r["shock_kind"], r["seed"]))
    return records


def aggregate(records: list[dict]) -> pd.DataFrame:
    ok = [r for r in records if r["status"] == "ok"]
    fields = [
        "pre_mean_occupancy", "during_mean_occupancy", "post_mean_occupancy",
        "pre_unmet_demand", "during_unmet_demand", "post_unmet_demand",
        "pre_participation_rate", "during_participation_rate", "post_participation_rate",
        "pre_policy_diversity_bits", "during_policy_diversity_bits", "post_policy_diversity_bits",
        "pre_cooperation_rate", "during_cooperation_rate", "post_cooperation_rate",
        "pre_turnover", "post_turnover",
        "post_shock_conditional_cooperation_rate", "post_shock_unconditional_cooperation_rate",
    ]
    rows = []
    for (bp, shock) in sorted({(r["boundary_point_id"], r["shock_kind"]) for r in ok}):
        subset = [r for r in ok if r["boundary_point_id"] == bp and r["shock_kind"] == shock]
        row = {"boundary_point_id": bp, "shock_kind": shock, "n_seeds": len(subset)}
        for f in fields:
            vals = np.array([r[f] for r in subset], dtype=float)
            finite = vals[~np.isnan(vals)]
            row[f"{f}_mean"] = float(np.mean(finite)) if len(finite) else math.nan
            row[f"{f}_std"] = float(np.std(finite)) if len(finite) else math.nan
        recovered = [r["recovered_after_shock"] for r in subset]
        row["fraction_recovered"] = float(np.mean(recovered)) if recovered else math.nan
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sweep-manifest", type=str, default="outputs/phase_sweep_level02/sweep_manifest.json")
    parser.add_argument("--out", type=str, default="outputs/boundary_perturbation_level02")
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(args.sweep_manifest, "r", encoding="utf-8") as fh:
        sweep_manifest = json.load(fh)
    boundary_points = sweep_manifest["boundary_points_selected"]
    if not boundary_points:
        print("[boundary_perturbation] No boundary points found in sweep manifest — nothing to do.", file=sys.stderr)
        return 1

    specs = []
    for bp in boundary_points:
        for shock_kind in ["none"] + list(SHOCK_KINDS):
            for seed in range(args.seeds):
                specs.append(RunSpec(boundary_point_id=bp["point_id"], shock_kind=shock_kind, seed=seed, params=bp["params"]))

    if args.dry_run:
        print(f"[boundary_perturbation] would run {len(specs)} simulations "
              f"({len(boundary_points)} boundary points x {1 + len(SHOCK_KINDS)} conditions x {args.seeds} seeds), "
              f"n_steps={N_STEPS} each")
        return 0

    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()
    records = run_specs(specs, max_workers=args.workers)
    wall_time = time.time() - t0

    manifest = {
        "meta": {
            "n_steps": N_STEPS,
            "pre_shock_steps": PRE_SHOCK_STEPS,
            "shock_duration": SHOCK_DURATION,
            "post_shock_steps": POST_SHOCK_STEPS,
            "shock_kinds": SHOCK_KINDS,
            "boundary_points": boundary_points,
            "wall_time_s": wall_time,
        },
        "n_runs": len(records),
        "n_ok": sum(1 for r in records if r["status"] == "ok"),
        "n_failed": sum(1 for r in records if r["status"] == "failed"),
        "runs": records,
    }
    manifest_path = os.path.join(args.out, "boundary_perturbation_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)

    summary_df = aggregate(records)
    summary_path = os.path.join(args.out, "boundary_perturbation_summary.csv")
    summary_df.to_csv(summary_path, index=False)

    failed = [r for r in records if r["status"] == "failed"]
    if failed:
        print(f"[boundary_perturbation] WARNING: {len(failed)}/{len(records)} runs failed.", file=sys.stderr)

    print(f"[boundary_perturbation] {len(records)} runs complete ({wall_time:.1f}s).")
    print(f"  manifest: {manifest_path}")
    print(f"  summary: {summary_path}")
    return 0


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    raise SystemExit(main())
