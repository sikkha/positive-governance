#!/usr/bin/env python3
"""Level 1.0, Stage 1: mechanism activation calibration.

Small runs verifying every Level 1.0 mechanism actually fires at least
once (proposals, adoption AND rejection, voluntary membership,
compliance AND violation, imperfect monitoring, occasional sanctions,
dissolution, and at least the *possibility* of founder-independent
persistence) at the milestone's default trait means/stds -- not
calibrated for any particular ecological outcome, only enough to avoid
either permanent inactivity or mechanical certainty (Constraint 8/9).
Writes ``outputs/level1_stage1_calibration/calibration_report.json``.
"""

from __future__ import annotations

import json

from experiments.level1_common import build_config, ensure_dir, run_and_summarize

OUT_DIR = "outputs/level1_stage1_calibration"

CONDITIONS = {
    "default_voluntary": {"monitoring_mode": "voluntary", "sanction_mode": "voluntary"},
    "designated_collective_fund": {
        "monitoring_mode": "designated", "sanction_mode": "collective_fund",
        "institutional_fund_contribution_rate": 0.1,
    },
    "perfect_imposed_sanction": {"monitoring_mode": "perfect", "sanction_mode": "imposed_perfect"},
    "sanction_without_reliable_monitoring": {
        "monitoring_mode": "voluntary", "sanction_mode": "voluntary",
        "monitoring_detection_accuracy": 0.5, "monitoring_false_positive_rate": 0.45,
    },
}

N_SEEDS = 5
N_STEPS = 400


def run() -> dict:
    ensure_dir(OUT_DIR)
    report = {}
    for name, overrides in CONDITIONS.items():
        cell = {
            "n_proposals": 0, "n_adoptions": 0, "n_rejections": 0,
            "n_compliant_events": 0, "n_violated_events": 0,
            "n_monitorings": 0, "n_sanctions": 0, "n_dissolutions": 0,
            "n_joins": 0, "n_exits": 0, "seeds_run": [],
        }
        for seed in range(N_SEEDS):
            config = build_config("interior_persistent", overrides, seed=seed, n_steps=N_STEPS)
            from abm_governance.simulation import Simulation
            sim = Simulation(config)
            sim.run()
            cell["n_proposals"] += len(sim.event_log.rule_proposals)
            cell["n_adoptions"] += len(sim.event_log.rule_adoptions)
            cell["n_rejections"] += len(sim.event_log.rule_rejections)
            cell["n_compliant_events"] += sum(1 for e in sim.event_log.compliances if e.complied)
            cell["n_violated_events"] += sum(1 for e in sim.event_log.compliances if e.violated)
            cell["n_monitorings"] += len(sim.event_log.monitorings)
            cell["n_sanctions"] += len(sim.event_log.sanctions)
            cell["n_dissolutions"] += len(sim.event_log.rule_dissolutions)
            cell["n_joins"] += sum(1 for e in sim.event_log.memberships if e.kind == "join")
            cell["n_exits"] += sum(1 for e in sim.event_log.memberships if e.kind == "exit")
            cell["seeds_run"].append(seed)
        cell["mechanically_certain_compliance"] = cell["n_violated_events"] == 0
        cell["permanently_inactive"] = cell["n_proposals"] == 0
        report[name] = cell

    with open(f"{OUT_DIR}/calibration_report.json", "w") as f:
        json.dump(report, f, indent=2)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    r = run()
    print(json.dumps(r, indent=2))
