#!/usr/bin/env python3
"""Level 1.3, Stage 2 (task #97): calibration without phenotype labels.

Freezes the ACTUAL Level 1.3 ecological feasibility cut points (tercile
``low_cut``/``high_cut`` over ``expected_pressure_ratio``) from this
milestone's own 30-point Latin Hypercube ecological design, using
``experiments/level13_common.py``'s machinery (task #93) -- task #93
built and tested that machinery; this stage is the first to actually
CALL it at the milestone's own preregistered scale and freeze the
result, before any Stage 3-9 run uses it.

**"Without phenotype labels" is this stage's own defining constraint**,
restated here as a structural fact, not just a name: this script
imports nothing from ``observer/phenotype_discovery.py``,
``observer/level13_phenotype.py``, or any recurrence/clustering module
-- ``tests/test_level13_stage2_calibration.py`` checks this directly
against the script's own source, not merely by convention. Ex-ante
ecological feasibility is a property of the ecological substrate alone
(``observer/feasibility_ratios.py``, Section 6), computed before any
institutional/phenotype question is asked -- mirrors Level 1.2b's own
Work Package C precedent (``level12b_stage_c_feasibility_map.py``) and
Section 6.2's own explicit "never a governance/cluster/SEM label"
prohibition.

Same freeze-then-hash pattern every prior Level 1.2/1.2b/1.3 design has
used (``build_design``/``design_hash``/``write_design``/``load_and_
verify_design``)."""

from __future__ import annotations

import hashlib
import json
import os

from experiments.level13_common import build_ecological_feasibility_design

OUT_DIR = "outputs/level13_stage2_calibration"
N_POINTS = 30  # matches the frozen preregistration manifest's own stage2_calibration_without_phenotype_labels commitment.
N_STEPS = 200


def build_design(n_points: int = N_POINTS, n_steps: int = N_STEPS) -> dict:
    return build_ecological_feasibility_design(n_points=n_points, n_steps=n_steps)


def design_hash(design: dict) -> str:
    payload = json.dumps(design, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_design(out_dir: str = OUT_DIR) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    design = build_design()
    digest = design_hash(design)
    with open(f"{out_dir}/design.json", "w") as f:
        json.dump(design, f, indent=2, sort_keys=True, default=str)
    with open(f"{out_dir}/design_hash.txt", "w") as f:
        f.write(digest + "\n")
    return {"design": design, "hash": digest}


def load_and_verify_design(out_dir: str = OUT_DIR) -> dict:
    with open(f"{out_dir}/design.json") as f:
        design = json.load(f)
    with open(f"{out_dir}/design_hash.txt") as f:
        stored_hash = f.read().strip()
    recomputed = design_hash(design)
    if recomputed != stored_hash:
        raise ValueError(
            f"Stage 2 calibration design at {out_dir}/design.json has been altered since it was frozen "
            f"(stored hash {stored_hash}, recomputed hash {recomputed})."
        )
    return {"design": design, "hash": recomputed}


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    result = write_design()
    design = result["design"]
    print(f"Level 1.3 Stage 2 calibration frozen at {OUT_DIR}/design.json")
    print(f"hash: {result['hash']}")
    print(f"stratum_cut_points: {design['stratum_cut_points']}")
    print(f"stratum_counts: {design['stratum_counts']}")
