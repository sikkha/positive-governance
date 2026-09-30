#!/usr/bin/env python3
"""Level 1.0, Stage 3: confirmatory comparison of the three prospectively
selected Stage 2 candidates.

For each selected candidate (persistent-proto-institution,
founder-dependent/short-lived, no-institution/failed-adoption -- any
category Stage 2 did not produce is skipped, never manufactured): 24
seeds, 800 steps, full per-seed raw trajectories retained (not just
endpoint means), plus a small local parameter-neighborhood robustness
check (each continuous institutional parameter nudged +-10%, 5 seeds
each) confirming the classification is not a single-point numerical
accident.
"""

from __future__ import annotations

import json

from experiments.level1_common import build_config, ensure_dir, run_and_summarize
from experiments.level1_stage2_search import _CONTINUOUS_RANGES

OUT_DIR = "outputs/level1_stage3_confirmatory"
N_SEEDS = 24
N_STEPS = 800
NEIGHBORHOOD_SEEDS = 5
NEIGHBORHOOD_FRACTION = 0.10


def _neighborhood_points(overrides: dict) -> list[dict]:
    points = []
    for name in _CONTINUOUS_RANGES:
        if name not in overrides:
            continue
        lo, hi = _CONTINUOUS_RANGES[name]
        span = hi - lo
        for sign in (-1, 1):
            nudged = dict(overrides)
            nudged[name] = float(min(hi, max(lo, overrides[name] + sign * NEIGHBORHOOD_FRACTION * span)))
            points.append({"perturbed_field": name, "sign": sign, "overrides": nudged})
    return points


def run(selection_path: str = "outputs/level1_stage2_search/stage3_candidate_selection.json") -> dict:
    ensure_dir(OUT_DIR)
    with open(selection_path) as f:
        selection = json.load(f)
    candidate_key = selection["candidate_key"]

    report = {"candidate_key": candidate_key, "candidates": {}}
    for name, sel in selection["selection"].items():
        if sel is None:
            report["candidates"][name] = {"status": "not_available_at_stage2", "reason": "no Stage 2 point produced this label; not manufactured per instruction"}
            continue
        overrides = sel["overrides"]
        trajectories = []
        for seed in range(N_SEEDS):
            config = build_config(candidate_key, overrides, seed=2000 + seed, n_steps=N_STEPS)
            out = run_and_summarize(config)
            trajectories.append({"seed": seed, **out})

        neighborhood = []
        for point in _neighborhood_points(overrides):
            for seed in range(NEIGHBORHOOD_SEEDS):
                config = build_config(candidate_key, point["overrides"], seed=3000 + seed, n_steps=N_STEPS)
                out = run_and_summarize(config)
                neighborhood.append({
                    "perturbed_field": point["perturbed_field"], "sign": point["sign"],
                    "seed": seed, "classifications": out["classifications"],
                })

        report["candidates"][name] = {
            "status": "confirmed", "point_id": sel["point_id"], "overrides": overrides,
            "n_seeds": N_SEEDS, "n_steps": N_STEPS,
            "trajectories": trajectories, "neighborhood_checks": neighborhood,
        }
        print(f"stage3 candidate {name} done ({N_SEEDS} seeds + {len(neighborhood)} neighborhood runs)", flush=True)

    with open(f"{OUT_DIR}/stage3_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
