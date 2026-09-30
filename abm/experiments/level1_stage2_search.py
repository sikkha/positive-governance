#!/usr/bin/env python3
"""Level 1.0, Stage 2: exploratory institutional parameter search.

A reproducible space-filling search over institutional micro-parameters,
run at the Level 0.3b registered ``interior_persistent`` ecological
parameter point (the milestone's own confirmation plan already treats
this candidate as "primary" among the three -- 24 of 24/24/24 confirmation
seeds each -- so Stage 2's full-scale search is concentrated here; the
other two registered candidates, ``nonstationary`` and ``near_collapse``,
get a smaller spot-check search, run by ``level1_stage2_search_secondary.
py``, both because they are the milestone's own "secondary" candidates and
because of this session's compute-time budget -- see the Stage 2 section
of ``docs/level1.0_scientific_note.md`` for the full, honest accounting of
every scale reduction from the milestone's literal numbers).

Search space (documented, not tuned toward any particular result):
  proposal_probability_mean       in [0.005, 0.05]
  preferred_adoption_threshold_mean in [0.2, 0.7]
  monitoring_detection_accuracy   in [0.5, 0.95]
  sanction_cost_per_unit          in [0.1, 1.0]
  membership_exit_cost            in [0.0, 3.0]
  amendment_propensity_mean       in [0.0, 0.1]
  rule_mutation_std               in [0.02, 0.2]
  monitoring_mode  in {"voluntary", "designated"}
  sanction_mode    in {"voluntary", "collective_fund"}

32 points (a fixed, seeded Latin-hypercube-style stratified design -- see
``_lhs_points``), 5 seeds each, 600 steps, at the ``interior_persistent``
candidate's own registered population/patch/harvest parameters (kept
exactly as registered rather than overridden to a generic "~24-30" range,
since a registered candidate is a complete parameter vector, not just an
ecological subset -- documented explicitly here per the milestone's
"verify not assume" standard). Points are not selected or filtered by
outcome; every point's every seed is executed and kept, classified only
after the full grid completes.
"""

from __future__ import annotations

import json
import sys
import time

import numpy as np

from experiments.level1_common import build_config, ensure_dir, run_and_summarize

OUT_DIR = "outputs/level1_stage2_search"
N_POINTS = 32
N_SEEDS = 5
N_STEPS = 600
SEARCH_SEED = 20260817  # fixed, documented -- date-derived, not re-rolled

_CONTINUOUS_RANGES = {
    "proposal_probability_mean": (0.005, 0.05),
    "preferred_adoption_threshold_mean": (0.2, 0.7),
    "monitoring_detection_accuracy": (0.5, 0.95),
    "sanction_cost_per_unit": (0.1, 1.0),
    "membership_exit_cost": (0.0, 3.0),
    "amendment_propensity_mean": (0.0, 0.1),
    "rule_mutation_std": (0.02, 0.2),
}
_CATEGORICAL_CHOICES = {
    "monitoring_mode": ("voluntary", "designated"),
    "sanction_mode": ("voluntary", "collective_fund"),
}


def _lhs_points(n_points: int, rng: np.random.Generator) -> list[dict]:
    """A simple, fully-reproducible Latin-hypercube-style stratified
    design over the continuous ranges (one stratum per point per
    dimension, independently permuted per dimension), with categorical
    choices assigned round-robin then shuffled -- space-filling, not
    outcome-selected."""
    names = list(_CONTINUOUS_RANGES.keys())
    n_dims = len(names)
    strata = (np.arange(n_points)[:, None] + rng.random((n_points, n_dims))) / n_points
    for d in range(n_dims):
        rng.shuffle(strata[:, d])
    points = []
    for i in range(n_points):
        overrides = {}
        for d, name in enumerate(names):
            lo, hi = _CONTINUOUS_RANGES[name]
            overrides[name] = float(lo + strata[i, d] * (hi - lo))
        points.append(overrides)
    for name, choices in _CATEGORICAL_CHOICES.items():
        assignment = [choices[i % len(choices)] for i in range(n_points)]
        rng.shuffle(assignment)
        for i, val in enumerate(assignment):
            points[i][name] = val
    return points


def run(candidate_key: str = "interior_persistent", n_points: int = N_POINTS, n_seeds: int = N_SEEDS,
        n_steps: int = N_STEPS, search_seed: int = SEARCH_SEED, tag: str = "") -> str:
    ensure_dir(OUT_DIR)
    rng = np.random.default_rng(search_seed)
    points = _lhs_points(n_points, rng)
    records = []
    t0 = time.time()
    for point_id, overrides in enumerate(points):
        for seed in range(n_seeds):
            config = build_config(candidate_key, overrides, seed=1000 * point_id + seed, n_steps=n_steps)
            out = run_and_summarize(config)
            records.append({
                "candidate_key": candidate_key, "point_id": point_id, "seed": seed,
                "overrides": overrides, **out,
            })
        elapsed = time.time() - t0
        print(f"[{candidate_key}{tag}] point {point_id + 1}/{n_points} done, elapsed={elapsed:.1f}s", flush=True)

    out_path = f"{OUT_DIR}/search_records_{candidate_key}{tag}.json"
    with open(out_path, "w") as f:
        json.dump(records, f, indent=2, default=str)
    print(f"wrote {out_path} ({len(records)} records)")
    return out_path


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
