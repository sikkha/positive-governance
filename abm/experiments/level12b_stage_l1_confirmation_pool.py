#!/usr/bin/env python3
"""Level 1.2b, Work Package L, stage 1 (Section 17): generate the
fresh 384-run confirmation pool (preferred: 24 joint points x 8 seeds
x 2 IC families), disjoint from every Work Package E discovery seed
(``level12b_stage_l0_confirmation_registry``'s own frozen design).

**Reuses Work Package J's own ``_run_one`` unmodified.** Work Package
L's confirmation points share the exact same dict shape as Work
Package E's design points (``joint_point_id``/``ecological_parameters``/
``institutional_parameters``/``population_size``/``n_patches``/``seeds``
etc. -- see stage 0's ``build_confirmation_design``), so Work Package
J's ``_run_one(point, seed, ic_family)`` -- which already computes the
all-outcome label, failure-trajectory route, sustained-eligibility
screen, and end-of-run phenotype vector in one simulation pass -- runs
against confirmation points with zero modification. This is exactly
what Section 17 asks for (recurrence of outcome classification,
unclassified-outcome rate, failure-transition rate) plus the raw
phenotype vector Work Package L's own stage 3 needs for the clustering-
side confirmation tests (assignment stability, feature-profile
stability, held-out predictiveness)."""

from __future__ import annotations

import json
import os

from experiments.level12b_stage_j_main_discovery_pipeline import (
    _run_one,
    aggregate_all_outcome_summary,
    aggregate_failure_trajectory_summary,
    aggregate_sustained_system_summary,
)
from experiments.level12b_stage_e_joint_discovery import IC_FAMILIES
from experiments.level12b_stage_l0_confirmation_registry import (
    load_and_verify_confirmation_design,
    load_and_verify_confirmation_registry,
)

OUT_DIR = "outputs/level12b_stage_l1_confirmation_pool"


def run() -> dict:
    design_verified = load_and_verify_confirmation_design()
    registry_verified = load_and_verify_confirmation_registry()
    design = design_verified["design"]

    records = []
    failures = []
    for point in design["points"]:
        for ic_family in IC_FAMILIES:
            for seed in point["seeds"]:
                try:
                    records.append(_run_one(point, seed, ic_family))
                except Exception as exc:  # noqa: BLE001 -- preserve failed runs, never silently drop
                    failures.append({"joint_point_id": point["joint_point_id"], "ic_family": ic_family, "seed": seed, "error": str(exc)})
        print(f"confirmation joint point {point['joint_point_id']} ({point['expected_stratum']}) done", flush=True)

    report = {
        "confirmation_design_hash": design_verified["hash"],
        "confirmation_registry_hash": registry_verified["hash"],
        "n_runs_completed": len(records),
        "n_runs_failed": len(failures),
        "failures": failures,
        "preferred_target_met": len(records) >= design["total_runs"],
        "all_outcome_summary": aggregate_all_outcome_summary(records),
        "failure_trajectory_summary": aggregate_failure_trajectory_summary(records),
        "sustained_system_summary": aggregate_sustained_system_summary(records),
        "records": records,
    }
    return report


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    report = run()
    with open(f"{OUT_DIR}/results.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"Work Package L confirmation pool: {report['n_runs_completed']} runs completed, {report['n_runs_failed']} failed")
    print(f"all-outcome summary: {report['all_outcome_summary']}")
    print(f"failure-trajectory summary: {report['failure_trajectory_summary']}")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
