#!/usr/bin/env python3
"""Work Package E: reproducible multi-seed ensemble / ablation runner.

This is the machinery the milestone brief asked the batch scaffold to
grow into: explicit seed lists, a reproducible named configuration grid
("conditions" and "ablations"), deterministic parallel execution, one run
directory per (condition, seed), a JSON experiment manifest, aggregated
distributional summaries (not just endpoint means), and failure reporting
that never discards completed runs.

Design notes
------------
* **Determinism under parallelism.** Every run is fully self-contained: it
  is defined entirely by its own ``SimulationConfig`` (which embeds its own
  seed) and consumes no shared mutable state. Submitting the same
  (condition, seed) set to a process pool with 1 worker or N workers must
  therefore produce bit-identical per-run results — only the *order* in
  which results arrive back (and are written into the manifest list) can
  differ, and the aggregation step sorts before summarizing so even that
  has no effect on the aggregated output. This is checked directly by
  ``tests/test_ensemble.py::test_parallel_and_serial_execution_agree``.
* **Failure isolation.** Each run is wrapped in its own try/except inside
  the worker function, so one crashing configuration cannot lose the
  results of runs that already completed; failures are recorded in the
  manifest with their error message and excluded from aggregation (with a
  loud warning if a whole condition has zero surviving runs).
* **Distributional, not just endpoint-mean, reporting.** ``aggregate``
  writes both an endpoint-quantile summary (final-step value across seeds,
  per condition) and a step-wise trajectory-quantile summary (so plots can
  show bands, not just single lines) — see the milestone brief's explicit
  objection to endpoint-mean-only reporting.

This script does not select or filter runs based on whether they resemble
any particular macro-pattern — every configured run is executed and kept,
per dev_mem/project_vision.md's anomaly-preserving philosophy.

Usage
-----
    python experiments/ensemble.py --out outputs/ensemble_level01 \\
        --seeds 30 --steps 500 --workers 8

This runs the 3 required baseline-comparison conditions and all 7 required
ablations, 30 seeds each (240 runs total), and writes aggregated summaries.
Use ``--dry-run`` to print the planned run grid without executing anything.
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
from typing import Mapping

import numpy as np
import pandas as pd

from abm_governance.core.config import SimulationConfig
from abm_governance.core.export import export_results
from abm_governance.observer.enforcement import confusion_matrix_summary
from abm_governance.observer.network_diagnostics import relationship_turnover_rate
from abm_governance.simulation import Simulation

# ---------------------------------------------------------------------------
# The required condition / ablation grid
# ---------------------------------------------------------------------------

#: The 3 conditions required for the baseline comparison (milestone brief,
#: Work Package E). "ecologically_closed" isolates the ecology effect alone
#: (relationship dynamics still legacy); "closed_ecology_turnover" is the
#: full Level 0.1 default (both mechanisms on).
BASELINE_CONDITIONS: dict[str, dict] = {
    "original_compat": {"ecology_enabled": False, "relationship_dynamics_enabled": False},
    "ecologically_closed": {"ecology_enabled": True, "relationship_dynamics_enabled": False},
    "closed_ecology_turnover": {"ecology_enabled": True, "relationship_dynamics_enabled": True},
}

#: The 7 required ablations, each a one-mechanism-at-a-time deviation from
#: the full Level 0.1 model ("closed_ecology_turnover" above). Every
#: ablation is expressed as ordinary config fields — no ad hoc code paths —
#: so each one is fully visible in the exported config.yaml for its runs.
ABLATIONS: dict[str, dict] = {
    # memory_length must be >= 1 (config-validated); 1 is the closest
    # config-expressible approximation to "no memory" — an agent that
    # remembers only the single most recent interaction with a partner,
    # rather than the full memory_length=10 default history.
    "no_memory": {"ecology_enabled": True, "relationship_dynamics_enabled": True, "memory_length": 1},
    "no_punishment": {"ecology_enabled": True, "relationship_dynamics_enabled": True, "punishment_enabled": False},
    # Perfect, noiseless observation.
    "no_observation_error": {
        "ecology_enabled": True,
        "relationship_dynamics_enabled": True,
        "observation_accuracy_mean": 1.0,
        "observation_accuracy_std": 0.0,
    },
    "no_imitation": {"ecology_enabled": True, "relationship_dynamics_enabled": True, "imitation_enabled": False},
    "no_mutation": {"ecology_enabled": True, "relationship_dynamics_enabled": True, "mutation_rate": 0.0},
    "no_relationship_exit": {
        "ecology_enabled": True,
        "relationship_dynamics_enabled": True,
        "relationship_exit_enabled": False,
    },
    # Removing ecological closure entirely removes scarcity as such (no
    # pool, no extraction cap, no subsistence charge, no distress) while
    # relationship dynamics stay on — the ecology-specific counterpart of
    # "original_compat" above, which also turns off relationship dynamics.
    "no_ecological_scarcity": {"ecology_enabled": False, "relationship_dynamics_enabled": True},
}

#: Columns worth tracking distributionally (endpoint + trajectory). Kept to
#: a documented, meaningful subset rather than every metrics column.
TRACKED_COLUMNS = [
    "cooperation_rate",
    "mean_resources",
    "resource_gini",
    "environment_resources",
    "environment_fraction_of_capacity",
    "network_density",
    "component_count",
    "largest_component_share",
    "isolated_agent_count",
    "mean_relationship_age",
    "policy_diversity_bits",
    "erroneous_punishment_rate",
]

QUANTILES = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]


# ---------------------------------------------------------------------------
# Run execution
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class RunSpec:
    condition: str
    seed: int
    overrides: Mapping
    n_steps: int
    out_dir: str


def _build_config(spec: RunSpec) -> SimulationConfig:
    return SimulationConfig(seed=spec.seed, n_steps=spec.n_steps, **dict(spec.overrides))


def _run_one(spec: RunSpec) -> dict:
    """Execute exactly one (condition, seed) run. Module-level (not a
    closure/method) so it is picklable for ``ProcessPoolExecutor``. Never
    raises — failures are captured and returned as a manifest record so a
    batch of futures can be drained in a simple loop without any run being
    silently lost."""
    start = time.time()
    record = {
        "condition": spec.condition,
        "seed": spec.seed,
        "n_steps": spec.n_steps,
        "out_dir": spec.out_dir,
        "overrides": dict(spec.overrides),
        "status": "failed",
        "error": None,
        "wall_time_s": None,
    }
    try:
        config = _build_config(spec)
        result = Simulation(config).run()
        export_results(result, spec.out_dir)

        final_row = dict(result.metrics[-1])
        confusion = confusion_matrix_summary(result.event_log)
        turnover = relationship_turnover_rate(result.event_log, start_step=0, end_step=spec.n_steps)

        record["status"] = "ok"
        record["final_metrics"] = {k: final_row.get(k) for k in TRACKED_COLUMNS}
        record["confusion_matrix"] = confusion
        record["relationship_turnover_rate"] = turnover
        record["final_total_resources"] = sum(a.resources for a in result.final_agents)
    except Exception as exc:  # noqa: BLE001 - deliberately broad: never lose the batch
        record["error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    record["wall_time_s"] = time.time() - start
    return record


def build_run_grid(
    conditions: dict[str, dict], seeds: list[int], n_steps: int, out_root: str
) -> list[RunSpec]:
    specs = []
    for name, overrides in conditions.items():
        for seed in seeds:
            out_dir = os.path.join(out_root, "runs", name, f"seed_{seed:04d}")
            specs.append(RunSpec(condition=name, seed=seed, overrides=overrides, n_steps=n_steps, out_dir=out_dir))
    return specs


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def run_ensemble(
    specs: list[RunSpec],
    out_root: str,
    max_workers: int,
) -> list[dict]:
    os.makedirs(out_root, exist_ok=True)
    records: list[dict] = []

    if max_workers <= 1:
        for spec in specs:
            records.append(_run_one(spec))
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_run_one, spec) for spec in specs]
            for future in concurrent.futures.as_completed(futures):
                records.append(future.result())

    # Sort for a stable, execution-order-independent manifest and
    # aggregation input (see module docstring: parallel vs. serial must
    # agree, and a stable sort key is what makes that easy to assert).
    records.sort(key=lambda r: (r["condition"], r["seed"]))
    return records


def write_manifest(records: list[dict], out_root: str, meta: dict) -> str:
    manifest = {
        "meta": meta,
        "n_runs": len(records),
        "n_ok": sum(1 for r in records if r["status"] == "ok"),
        "n_failed": sum(1 for r in records if r["status"] == "failed"),
        "runs": records,
    }
    path = os.path.join(out_root, "manifest.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)
    failed = [r for r in records if r["status"] == "failed"]
    if failed:
        print(f"[ensemble] WARNING: {len(failed)}/{len(records)} runs failed. See manifest for details.", file=sys.stderr)
    by_condition: dict[str, int] = {}
    for r in records:
        if r["status"] == "ok":
            by_condition[r["condition"]] = by_condition.get(r["condition"], 0) + 1
    for name in sorted({r["condition"] for r in records}):
        if by_condition.get(name, 0) == 0:
            print(f"[ensemble] WARNING: condition {name!r} has ZERO successful runs.", file=sys.stderr)
    return path


# ---------------------------------------------------------------------------
# Aggregation: distributions, not just endpoint means
# ---------------------------------------------------------------------------


def aggregate_endpoint_summary(records: list[dict]) -> pd.DataFrame:
    """Per-condition quantile summary of each tracked column's *final-step*
    value across seeds — the milestone brief's explicit requirement to
    report distributions/quantiles rather than only endpoint means."""
    rows = []
    ok = [r for r in records if r["status"] == "ok"]
    for condition in sorted({r["condition"] for r in ok}):
        cond_records = [r for r in ok if r["condition"] == condition]
        n = len(cond_records)
        for col in TRACKED_COLUMNS:
            values = np.array([r["final_metrics"].get(col, math.nan) for r in cond_records], dtype=float)
            finite = values[~np.isnan(values)]
            row = {"condition": condition, "column": col, "n_seeds": n, "n_finite": len(finite)}
            row["mean"] = float(np.mean(finite)) if len(finite) else math.nan
            row["std"] = float(np.std(finite)) if len(finite) else math.nan
            for q in QUANTILES:
                row[f"q{int(q * 100):02d}"] = float(np.quantile(finite, q)) if len(finite) else math.nan
            rows.append(row)
    return pd.DataFrame(rows)


def aggregate_relationship_turnover(records: list[dict]) -> pd.DataFrame:
    ok = [r for r in records if r["status"] == "ok"]
    rows = []
    for condition in sorted({r["condition"] for r in ok}):
        values = np.array([r["relationship_turnover_rate"] for r in ok if r["condition"] == condition], dtype=float)
        rows.append(
            {
                "condition": condition,
                "n_seeds": len(values),
                "mean": float(np.mean(values)) if len(values) else math.nan,
                "std": float(np.std(values)) if len(values) else math.nan,
                "min": float(np.min(values)) if len(values) else math.nan,
                "max": float(np.max(values)) if len(values) else math.nan,
            }
        )
    return pd.DataFrame(rows)


def aggregate_confusion_matrix(records: list[dict]) -> pd.DataFrame:
    """Per-condition mean +- std of each confusion-matrix conditional rate
    across seeds (each seed's own rate is already NaN-safe per
    observer/enforcement.py; NaN seeds are excluded from the mean via
    nanmean/nanstd, and the surviving count is reported explicitly)."""
    ok = [r for r in records if r["status"] == "ok"]
    rate_keys = [
        "p_punishment_given_actual_defection",
        "p_punishment_given_actual_cooperation",
        "p_perceived_defection_given_actual_cooperation",
        "p_perceived_cooperation_given_actual_defection",
        "p_punishment_given_perceived_defection",
    ]
    rows = []
    for condition in sorted({r["condition"] for r in ok}):
        cond_records = [r for r in ok if r["condition"] == condition]
        row = {"condition": condition, "n_seeds": len(cond_records)}
        for key in rate_keys:
            values = np.array([r["confusion_matrix"].get(key, math.nan) for r in cond_records], dtype=float)
            finite = values[~np.isnan(values)]
            row[f"{key}_mean"] = float(np.mean(finite)) if len(finite) else math.nan
            row[f"{key}_n_finite"] = int(len(finite))
        rows.append(row)
    return pd.DataFrame(rows)


def aggregate_trajectories(specs_by_condition: dict[str, list[RunSpec]], columns: list[str]) -> dict[str, pd.DataFrame]:
    """Step-wise quantile bands per condition, read back from each run's
    exported metrics.csv (kept separate from the in-memory manifest record,
    which only carries the final-step row, to avoid holding every seed's
    entire trajectory in memory during parallel execution)."""
    out: dict[str, pd.DataFrame] = {}
    for condition, specs in specs_by_condition.items():
        frames = []
        for spec in specs:
            csv_path = os.path.join(spec.out_dir, "metrics.csv")
            if not os.path.exists(csv_path):
                continue  # failed run; skip without losing the others
            df = pd.read_csv(csv_path)
            # Level 0.3: metrics.csv is now considerably wider (patch/
            # ecological/joint-action columns) than when this loop was
            # written. `pd.read_csv` on a frame this wide returns one
            # internal block *per column* (unconsolidated); any further
            # column insert on top of that trips pandas' internal
            # block-fragmentation heuristic (a PerformanceWarning, not a
            # correctness issue) -- `.copy()` consolidates to a single
            # block first, so the subsequent column assignment is cheap
            # and silent.
            df = df.copy()
            df["seed"] = spec.seed
            frames.append(df)
        if not frames:
            continue
        combined = pd.concat(frames, ignore_index=True)
        rows = []
        for step, group in combined.groupby("step"):
            row = {"step": step, "n_seeds": group["seed"].nunique()}
            for col in columns:
                if col not in group:
                    continue
                values = group[col].to_numpy(dtype=float)
                finite = values[~np.isnan(values)]
                row[f"{col}_mean"] = float(np.mean(finite)) if len(finite) else math.nan
                for q in (0.1, 0.25, 0.5, 0.75, 0.9):
                    row[f"{col}_q{int(q * 100):02d}"] = float(np.quantile(finite, q)) if len(finite) else math.nan
            rows.append(row)
        out[condition] = pd.DataFrame(rows).sort_values("step").reset_index(drop=True)
    return out


def aggregate(specs: list[RunSpec], records: list[dict], out_root: str) -> dict[str, str]:
    paths: dict[str, str] = {}

    endpoint_summary = aggregate_endpoint_summary(records)
    p = os.path.join(out_root, "endpoint_summary.csv")
    endpoint_summary.to_csv(p, index=False)
    paths["endpoint_summary"] = p

    turnover_summary = aggregate_relationship_turnover(records)
    p = os.path.join(out_root, "relationship_turnover_summary.csv")
    turnover_summary.to_csv(p, index=False)
    paths["relationship_turnover_summary"] = p

    confusion_summary = aggregate_confusion_matrix(records)
    p = os.path.join(out_root, "confusion_matrix_summary.csv")
    confusion_summary.to_csv(p, index=False)
    paths["confusion_matrix_summary"] = p

    specs_by_condition: dict[str, list[RunSpec]] = {}
    for spec in specs:
        specs_by_condition.setdefault(spec.condition, []).append(spec)
    trajectories = aggregate_trajectories(specs_by_condition, TRACKED_COLUMNS)
    traj_dir = os.path.join(out_root, "trajectories")
    os.makedirs(traj_dir, exist_ok=True)
    for condition, df in trajectories.items():
        p = os.path.join(traj_dir, f"{condition}.csv")
        df.to_csv(p, index=False)
        paths[f"trajectory_{condition}"] = p

    return paths


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=str, default="outputs/ensemble_level01")
    parser.add_argument("--seeds", type=int, default=30, help="number of seeds per condition (0..N-1)")
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--conditions-only", action="store_true", help="skip the 7 ablations, run only the 3 baseline conditions")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conditions = dict(BASELINE_CONDITIONS)
    if not args.conditions_only:
        conditions.update(ABLATIONS)
    seeds = list(range(args.seeds))

    specs = build_run_grid(conditions, seeds, args.steps, args.out)

    if args.dry_run:
        print(f"[ensemble] would run {len(specs)} simulations across {len(conditions)} conditions x {len(seeds)} seeds:")
        for name in conditions:
            print(f"  - {name}: {conditions[name]}")
        return 0

    meta = {
        "git_commit": _git_commit(),
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "n_steps": args.steps,
        "seeds": seeds,
        "conditions": conditions,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "max_workers": args.workers,
    }

    t0 = time.time()
    records = run_ensemble(specs, args.out, max_workers=args.workers)
    meta["wall_time_s"] = time.time() - t0

    manifest_path = write_manifest(records, args.out, meta)
    agg_paths = aggregate(specs, records, args.out)

    print(f"[ensemble] {len(records)} runs complete ({meta['wall_time_s']:.1f}s). Manifest: {manifest_path}")
    for key, path in agg_paths.items():
        print(f"  - {key}: {path}")
    return 0


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    raise SystemExit(main())
