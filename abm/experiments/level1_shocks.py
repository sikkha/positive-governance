#!/usr/bin/env python3
"""Level 1.0, §19: institutional shocks applied to the Stage 3 confirmed
persistent-proto-institution candidate (the milestone's own "eligible
candidate" -- a founder-dependent/short-lived arrangement is not a
sensible target for "founder removal survival," since it is already
founder-dependent by construction).

Four shock types (a documented subset of the milestone's eight, chosen to
fit this session's compute budget -- see the reductions note in
``docs/level1.0_scientific_note.md``): founder removal, high-resource
member removal, temporary monitoring-failure, and sudden membership
influx. Each is applied at a fixed step to every rule active at that step
in a run, matched seeds against an unshocked control, 600 steps.
"""

from __future__ import annotations

import json

from abm_governance.core.config import SimulationConfig
from abm_governance.observer import institution_diagnostics as idg
from abm_governance.simulation import Simulation
from experiments.level1_common import ensure_dir, load_candidate_ecological_params

OUT_DIR = "outputs/level1_shocks"
N_SEEDS = 15
N_STEPS = 600
SHOCK_STEP = 300
CANDIDATE_KEY = "interior_persistent"


def _load_institutional_overrides() -> dict:
    try:
        with open("outputs/level1_stage3_confirmatory/stage3_report.json") as f:
            report = json.load(f)
        cand = report["candidates"].get("persistent_proto_institution")
        if cand is not None and cand.get("status") == "confirmed":
            return cand["overrides"]
    except FileNotFoundError:
        pass
    return {"monitoring_mode": "voluntary", "sanction_mode": "voluntary"}


def _config(overrides: dict, seed: int) -> SimulationConfig:
    eco = load_candidate_ecological_params(CANDIDATE_KEY)
    eco["ecology_topology"] = "patches"
    eco["rule_formation_enabled"] = True
    eco.update(overrides)
    return SimulationConfig(seed=seed, n_steps=N_STEPS, **eco)


def _run_with_shock(overrides: dict, seed: int, shock: str) -> dict:
    config = _config(overrides, seed)
    sim = Simulation(config)
    pre_shock_active_rule_ids: set[int] = set()
    for step in range(config.n_steps):
        if step == SHOCK_STEP:
            pre_shock_active_rule_ids = {r.rule_id for r in sim.rule_registry.values() if r.active}
            for pid, rule in list(sim.rule_registry.items()):
                if not rule.active:
                    continue
                if shock == "founder_removal":
                    founder = sim.agents_by_id.get(rule.founder_id)
                    if founder is not None and founder.alive:
                        founder.alive = False
                        members = set(rule.members)
                        members.discard(founder.agent_id)
                        rule.members = frozenset(members)
                elif shock == "high_resource_member_removal":
                    if rule.members:
                        target_id = max(rule.members, key=lambda aid: sim.agents_by_id[aid].resources)
                        sim.agents_by_id[target_id].alive = False
                        members = set(rule.members)
                        members.discard(target_id)
                        rule.members = frozenset(members)
                elif shock == "temporary_monitoring_failure":
                    pass  # handled via config-level window below
                elif shock == "sudden_membership_influx":
                    eligible = [
                        aid for aid in sim.patch_system.patches[pid].members
                        if sim.agents_by_id[aid].alive and aid not in rule.members
                    ]
                    influx = eligible[: max(1, len(eligible) // 2)]
                    rule.members = frozenset(set(rule.members) | set(influx))
                    for aid in influx:
                        sim.agents_by_id[aid].rule_member_of = rule.rule_id
        if shock == "temporary_monitoring_failure" and SHOCK_STEP <= step < SHOCK_STEP + 30:
            # SimulationConfig is a frozen dataclass (immutable by design,
            # everywhere else in this project) -- object.__setattr__ is
            # the documented escape hatch used only here, for a
            # controlled-experiment shock, never during ordinary
            # simulation.
            object.__setattr__(sim.config, "monitoring_mode", "none")
        elif shock == "temporary_monitoring_failure" and step == SHOCK_STEP + 30:
            object.__setattr__(sim.config, "monitoring_mode", config.monitoring_mode)
        sim._run_one_step(step)

    final_step = config.n_steps - 1
    survived = [rid for rid in pre_shock_active_rule_ids if any(
        r.rule_id == rid and r.active for r in sim.rule_registry.values()
    )]
    post_shock_dissolutions = [e for e in sim.event_log.rule_dissolutions if e.step >= SHOCK_STEP]
    reconstructions = [
        e for e in sim.event_log.rule_proposals
        if e.step > SHOCK_STEP and e.origin == "mutation" and e.parent_rule_lineage_id is not None
    ]
    all_rules = list(sim.rule_registry.values()) + list(sim._last_dissolved_rule_by_patch.values())
    classifications = []
    for pid in sim.patch_system.patches:
        rule = sim.rule_registry.get(pid) or sim._last_dissolved_rule_by_patch.get(pid)
        cls = idg.classify_rule(rule, sim.event_log, pid, final_step)
        classifications.append({"patch_id": pid, "label": cls["label"]})
    return {
        "n_active_pre_shock": len(pre_shock_active_rule_ids),
        "n_survived_post_shock": len(survived),
        "n_post_shock_dissolutions": len(post_shock_dissolutions),
        "n_reconstructions_post_shock": len(reconstructions),
        "classifications_at_end": classifications,
    }


def run() -> dict:
    ensure_dir(OUT_DIR)
    overrides = _load_institutional_overrides()
    shocks = ["founder_removal", "high_resource_member_removal", "temporary_monitoring_failure", "sudden_membership_influx"]
    report = {"n_seeds": N_SEEDS, "n_steps": N_STEPS, "shock_step": SHOCK_STEP, "overrides": overrides, "shocks": {}}
    for shock in shocks:
        runs = [_run_with_shock(overrides, seed=5000 + seed, shock=shock) for seed in range(N_SEEDS)]
        report["shocks"][shock] = runs
        print(f"shock {shock} done ({N_SEEDS} seeds)", flush=True)
    with open(f"{OUT_DIR}/shocks_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
