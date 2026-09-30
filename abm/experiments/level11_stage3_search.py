#!/usr/bin/env python3
"""Level 1.1, Stage 3: open mechanism-space search (exploratory only).

Crosses delegate selection procedure (4 levels), discretion (on/off),
and accountability (on/off) -- 16 conditions -- to observe which of
Work Package K's mechanism-validation labels each combination actually
produces, across multiple seeds. This is deliberately *not* a search
for the dissertation's three governance trajectories (Constraint 3/6):
the only thing ever compared is which entries of the fixed 12-label
mechanism-validation vocabulary (``VALID_LABELS``) appear, at what
frequency -- never assembled into a single score or mapped onto any
governance-type concept.

Exploratory only (Constraint on statistical requirements): nothing here
is treated as confirmed; Stage 4 re-runs whichever pattern looks most
robust on fresh seeds before any claim is made.

Session-budget scope reduction (disclosed): 6 seeds per condition
(96 runs total), population 40, 3 patches, 350 steps.
"""

from __future__ import annotations

import itertools
import json
from collections import Counter

from abm_governance.core.config import SimulationConfig
from experiments.level11_common import ensure_dir, run_and_summarize

OUT_DIR = "outputs/level11_stage3_search"
N_SEEDS = 6
N_STEPS = 350
POPULATION = 40
N_PATCHES = 3

PROCEDURES = ("lottery", "plurality_support", "voluntary_approval", "threshold_acceptance")
DISCRETION_LEVELS = (False, True)
ACCOUNTABILITY_LEVELS = (False, True)


def _config(procedure: str, discretion: bool, accountability: bool, seed: int) -> SimulationConfig:
    overrides = {
        "population_size": POPULATION, "n_steps": N_STEPS, "n_patches": N_PATCHES, "seed": seed,
        "delegate_selection_procedure": procedure, "discretion_enabled": discretion,
        "accountability_enabled": accountability,
    }
    if accountability:
        # appeals need Level 1.0's own sanctioning active to have anything
        # to act on (same discipline as level11_accountability_only).
        overrides["monitoring_mode"] = "voluntary"
        overrides["sanction_mode"] = "voluntary"
    return SimulationConfig.level11_delegation_only(**overrides)


def run() -> dict:
    ensure_dir(OUT_DIR)
    report = {"n_seeds": N_SEEDS, "n_steps": N_STEPS, "conditions": {}}
    for procedure, discretion, accountability in itertools.product(PROCEDURES, DISCRETION_LEVELS, ACCOUNTABILITY_LEVELS):
        key = f"{procedure}|discretion={discretion}|accountability={accountability}"
        label_counts: Counter = Counter()
        n_rules_total = 0
        for seed in range(N_SEEDS):
            config = _config(procedure, discretion, accountability, 4000 + seed)
            out = run_and_summarize(config)
            for cls in out["rule_classifications"]:
                label_counts[cls["label"]] += 1
                n_rules_total += 1
        report["conditions"][key] = {
            "n_rules_observed": n_rules_total,
            "label_counts": dict(label_counts),
            "label_fractions": {k: v / n_rules_total for k, v in label_counts.items()} if n_rules_total else {},
        }
        print(f"{key}: {dict(label_counts)}", flush=True)
    with open(f"{OUT_DIR}/stage3_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
