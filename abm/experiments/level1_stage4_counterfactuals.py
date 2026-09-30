#!/usr/bin/env python3
"""Level 1.0, Stage 4: institutional counterfactuals across the
milestone's 11 named conditions, matched seeds, continuous paired
effects.

The base institutional parameter point used for every condition that
needs one (2-6, 9-11) is Stage 3's confirmed "persistent-proto-
institution" candidate (the point that actually produced a persistent
proto-institution in Stage 2/3) -- if Stage 2/3 found none, this script
falls back to the milestone's own ``level1_rule_formation_default``
preset and records that fallback explicitly (never silently).
"""

from __future__ import annotations

import json

from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation
from experiments.level1_common import ensure_dir, load_candidate_ecological_params, run_and_summarize

OUT_DIR = "outputs/level1_stage4_counterfactuals"
N_SEEDS = 20
N_STEPS = 600
CANDIDATE_KEY = "interior_persistent"
REMOVAL_STEP = N_STEPS // 2


def _base_eco() -> dict:
    eco = load_candidate_ecological_params(CANDIDATE_KEY)
    eco["ecology_topology"] = "patches"
    eco["rule_formation_enabled"] = True
    return eco


def _load_institutional_overrides() -> tuple[dict, str]:
    try:
        with open("outputs/level1_stage3_confirmatory/stage3_report.json") as f:
            report = json.load(f)
        cand = report["candidates"].get("persistent_proto_institution")
        if cand is not None and cand.get("status") == "confirmed":
            return cand["overrides"], "stage3_persistent_proto_institution_candidate"
    except FileNotFoundError:
        pass
    return {"monitoring_mode": "voluntary", "sanction_mode": "voluntary"}, "fallback_level1_rule_formation_default"


def _config(overrides: dict, seed: int) -> SimulationConfig:
    merged = _base_eco()
    merged.update(overrides)
    return SimulationConfig(seed=seed, n_steps=N_STEPS, **merged)


def _run_formed_then_removed(overrides: dict, seed: int) -> dict:
    """Condition 9: the institution forms and operates normally until
    ``REMOVAL_STEP``, then every active rule at every patch is force-
    dissolved and no new proposal can ever again be adopted (every
    agent's ``proposal_probability`` and ``willingness_to_join`` are
    zeroed from that step forward) -- a controlled removal, not a
    dissolution the mechanism itself decided on."""
    config = _config(overrides, seed)
    sim = Simulation(config)
    metrics_rows = []
    for step in range(config.n_steps):
        if step == REMOVAL_STEP:
            for rule in list(sim.rule_registry.values()):
                for aid in list(rule.members):
                    agent = sim.agents_by_id.get(aid)
                    if agent is not None:
                        agent.rule_member_of = None
                rule.active = False
                rule.dissolved = True
                rule.dissolution_step = step
                rule.dissolution_reason = "experimentally_removed"
            sim.rule_registry.clear()
            for agent in sim.agents:
                agent.proposal_probability = 0.0
                agent.willingness_to_join = 0.0
        row = sim._run_one_step(step)
        metrics_rows.append(row)
    final_step = config.n_steps - 1
    from abm_governance.observer import institution_diagnostics as idg
    all_rules = list(sim.rule_registry.values()) + list(sim._last_dissolved_rule_by_patch.values())
    metrics = idg.summarize_institutional_metrics(sim.agents, sim.event_log, all_rules, final_step)
    classifications = []
    for pid in sim.patch_system.patches:
        rule = sim.rule_registry.get(pid) or sim._last_dissolved_rule_by_patch.get(pid)
        cls = idg.classify_rule(rule, sim.event_log, pid, final_step)
        classifications.append({"patch_id": pid, "label": cls["label"], "duration_steps": cls["duration_steps"]})
    last_row = metrics_rows[-1]
    ecological_outcomes = {
        "final_occupancy": last_row.get("patch_occupancy_mean", float("nan")),
        "final_total_resources": sum(a.resources for a in sim.agents if a.alive),
        "cumulative_extraction": sum(p.cumulative_extraction for p in sim.patch_system.patches.values()),
        "cumulative_maintenance_invested": sum(p.cumulative_maintenance_invested for p in sim.patch_system.patches.values()),
        "cumulative_unmet_extraction_demand": sum(p.cumulative_unmet_extraction_demand for p in sim.patch_system.patches.values()),
        "n_patches_at_zero_resources": sum(1 for p in sim.patch_system.patches.values() if p.resources <= 0.0),
    }
    return {"metrics": metrics, "classifications": classifications, "ecological_outcomes": ecological_outcomes,
            "n_alive_at_end": sum(1 for a in sim.agents if a.alive)}


def build_conditions(inst_overrides: dict) -> dict:
    return {
        "atomic_baseline": {"rule_formation_enabled": False},
        "proposals_only": {**inst_overrides, "monitoring_mode": "none", "sanction_mode": "none"},
        "monitoring_without_sanction": {**inst_overrides, "monitoring_mode": "voluntary", "sanction_mode": "none"},
        "sanction_without_reliable_monitoring": {
            **inst_overrides, "monitoring_mode": "voluntary", "sanction_mode": "voluntary",
            "monitoring_detection_accuracy": 0.5, "monitoring_false_positive_rate": 0.45,
        },
        "monitoring_plus_voluntary_sanction": {**inst_overrides, "monitoring_mode": "voluntary", "sanction_mode": "voluntary"},
        "monitoring_plus_collective_sanction": {
            **inst_overrides, "monitoring_mode": "voluntary", "sanction_mode": "collective_fund",
            "institutional_fund_contribution_rate": 0.1,
        },
        "imposed_rule": {
            "institution_imposed_mode": True, "monitoring_mode": "perfect", "sanction_mode": "imposed_perfect",
        },
        "randomized_pseudo_institution": {
            **inst_overrides, "randomized_pseudo_institution_mode": True,
            "monitoring_mode": "voluntary", "sanction_mode": "voluntary",
        },
        "rule_frozen": {
            **inst_overrides, "monitoring_mode": "voluntary", "sanction_mode": "voluntary",
            "amendment_propensity_mean": 0.0, "amendment_propensity_std": 0.0,
            "rule_dissolution_membership_floor": 0.0, "rule_dissolution_support_floor": 0.0,
            "rule_inactive_dissolution_steps": N_STEPS * 10,
        },
        "rule_allowed_to_amend": {
            **inst_overrides, "monitoring_mode": "voluntary", "sanction_mode": "voluntary",
            "amendment_propensity_mean": 0.05,
        },
    }


def run() -> dict:
    ensure_dir(OUT_DIR)
    inst_overrides, provenance = _load_institutional_overrides()
    conditions = build_conditions(inst_overrides)
    report = {"provenance": provenance, "institutional_overrides_used": inst_overrides, "n_seeds": N_SEEDS,
              "n_steps": N_STEPS, "removal_step": REMOVAL_STEP, "conditions": {}}

    for name, overrides in conditions.items():
        runs = []
        for seed in range(N_SEEDS):
            config = _config(overrides, seed=4000 + seed)
            out = run_and_summarize(config)
            runs.append({"seed": seed, **out})
        report["conditions"][name] = {"overrides": overrides, "runs": runs}
        print(f"stage4 condition {name} done ({N_SEEDS} seeds)", flush=True)

    # institution_formed_then_removed: custom stepping, same matched seeds.
    runs = []
    for seed in range(N_SEEDS):
        out = _run_formed_then_removed(inst_overrides, seed=4000 + seed)
        runs.append({"seed": seed, **out})
    report["conditions"]["institution_formed_then_removed"] = {"overrides": inst_overrides, "runs": runs}
    print("stage4 condition institution_formed_then_removed done", flush=True)

    with open(f"{OUT_DIR}/stage4_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
