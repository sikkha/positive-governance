#!/usr/bin/env python3
"""Batch / multi-seed execution scaffold.

Level 0 does not (yet) run a full sensitivity analysis, but the
architecture must already support one (dev_mem/project_vision.md, section
9). This script runs a small grid of (seed x parameter) combinations and
writes one output directory per run plus a concatenated summary CSV of
final-step metrics, so distributional / sweep analysis has something to
build on immediately.

This script does not select or filter runs based on whether they resemble
any particular macro-pattern. Every combination in the grid is run and
recorded — cherry-picking "interesting" seeds would violate the
anomaly-preserving philosophy in dev_mem/project_vision.md.

Usage:
    python experiments/batch_run.py --out outputs/batch_default --seeds 5
"""

from __future__ import annotations

import argparse
import dataclasses
import itertools
import os

import pandas as pd

from abm_governance.core.config import SimulationConfig
from abm_governance.core.export import export_results
from abm_governance.simulation import Simulation


def default_grid() -> dict[str, list]:
    """A small illustrative parameter grid. Extend freely — this is a
    starting scaffold, not a fixed experiment design."""
    return {
        "punishment_enabled": [True, False],
        "topology": ["watts_strogatz", "erdos_renyi"],
    }


def run_batch(out_dir: str, n_seeds: int, n_steps: int, grid: dict[str, list]) -> pd.DataFrame:
    os.makedirs(out_dir, exist_ok=True)
    keys = list(grid.keys())
    combos = list(itertools.product(*grid.values())) if grid else [()]

    summary_rows = []
    run_index = 0
    for seed in range(n_seeds):
        for combo in combos:
            overrides = dict(zip(keys, combo))
            config = dataclasses.replace(SimulationConfig(), seed=seed, n_steps=n_steps, **overrides)
            run_out = os.path.join(out_dir, f"run_{run_index:04d}")
            result = Simulation(config).run()
            export_results(result, run_out)

            final_row = dict(result.metrics[-1])
            final_row.update(overrides)
            final_row["seed"] = seed
            final_row["run_dir"] = run_out
            summary_rows.append(final_row)
            run_index += 1

    summary = pd.DataFrame(summary_rows)
    summary_path = os.path.join(out_dir, "batch_summary.csv")
    summary.to_csv(summary_path, index=False)
    print(f"[batch_run] {len(summary_rows)} runs complete. Summary: {summary_path}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=str, default="outputs/batch_default")
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--steps", type=int, default=200)
    args = parser.parse_args()

    run_batch(args.out, n_seeds=args.seeds, n_steps=args.steps, grid=default_grid())
    return 0


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    raise SystemExit(main())
