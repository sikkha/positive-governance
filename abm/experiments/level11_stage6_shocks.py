#!/usr/bin/env python3
"""Level 1.1, Stage 6: institutional shocks applied to an active
delegation arrangement.

Two shock types (a documented subset of a fuller set, matching the
Level 1.0 precedent of disclosing a similar reduction in
``experiments/level1_shocks.py``): sudden delegate removal (the
currently-active delegate at every rule that has one is forcibly
removed mid-run, independent of the recall mechanism) and an
appropriation-opportunity spike (``appropriation_opportunity_scale`` is
temporarily raised for a fixed window, independent of any one delegate's
own traits). Each is applied at a fixed step in a ``level11_complete``
run and compared to a matched-seed unshocked control, measuring whether
the *delegation arrangement itself* (a new delegate eventually
appointed, task performance resuming) survives/recovers -- never whether
any specific delegate survives, since removal-by-shock is definitionally
guaranteed for the delegate-removal shock.

Session-budget scope reduction (disclosed): 10 seeds per shock type,
population 40, 3 patches, 500 steps (shock at step 250, leaving 250
steps to observe recovery).
"""

from __future__ import annotations

import json

from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation
from experiments.level11_common import ensure_dir

OUT_DIR = "outputs/level11_stage6_shocks"
N_SEEDS = 10
N_STEPS = 500
SHOCK_STEP = 250
POPULATION = 40
N_PATCHES = 3


def _config(seed: int) -> SimulationConfig:
    return SimulationConfig.level11_complete(population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed)


def _run_with_shock(seed: int, shock: str | None) -> dict:
    config = _config(seed)
    sim = Simulation(config)
    pre_shock_delegate_rule_ids: set[int] = set()
    for step in range(config.n_steps):
        if step == SHOCK_STEP and shock is not None:
            pre_shock_delegate_rule_ids = {rid for rid, d in sim.delegate_registry.items() if d.active}
            if shock == "delegate_removal":
                from abm_governance.rules.delegation import _remove_delegate
                for rid, d in list(sim.delegate_registry.items()):
                    if d.active:
                        _remove_delegate(step, d, sim.agents_by_id, "shock_forced_removal", sim.event_log)
            elif shock == "appropriation_spike":
                object.__setattr__(sim.config, "appropriation_opportunity_scale", 1.0)
                object.__setattr__(sim.config, "appropriation_fraction_of_fund", 0.8)
        if shock == "appropriation_spike" and step == SHOCK_STEP + 30:
            object.__setattr__(sim.config, "appropriation_opportunity_scale", config.appropriation_opportunity_scale)
            object.__setattr__(sim.config, "appropriation_fraction_of_fund", config.appropriation_fraction_of_fund)
        sim._run_one_step(step)

    post_shock_appointments = [e for e in sim.event_log.delegate_appointments if e.step > SHOCK_STEP]
    post_shock_task_performances = [e for e in sim.event_log.task_performances if e.step > SHOCK_STEP]
    recovered_rule_ids = {
        rid for rid, d in sim.delegate_registry.items()
        if d.active and (shock is None or rid in pre_shock_delegate_rule_ids)
    }
    return {
        "n_pre_shock_delegated_rules": len(pre_shock_delegate_rule_ids) if shock is not None else None,
        "n_post_shock_appointments": len(post_shock_appointments),
        "n_post_shock_task_performances": len(post_shock_task_performances),
        "n_rules_with_active_delegate_at_end": len(recovered_rule_ids),
        "n_active_rules_at_end": sum(1 for r in sim.rule_registry.values() if r.active),
    }


def run() -> dict:
    ensure_dir(OUT_DIR)
    report = {"n_seeds": N_SEEDS, "n_steps": N_STEPS, "shock_step": SHOCK_STEP, "shocks": {}}
    for shock in ["delegate_removal", "appropriation_spike"]:
        shocked_runs = [_run_with_shock(7000 + seed, shock) for seed in range(N_SEEDS)]
        control_runs = [_run_with_shock(7000 + seed, None) for seed in range(N_SEEDS)]
        n_recovered = sum(1 for r in shocked_runs if r["n_post_shock_appointments"] > 0)
        report["shocks"][shock] = {
            "shocked_runs": shocked_runs, "control_runs": control_runs,
            "n_seeds_with_post_shock_reappointment": n_recovered,
            "reappointment_rate": n_recovered / N_SEEDS,
        }
        print(f"{shock}: reappointment_rate={n_recovered}/{N_SEEDS}", flush=True)
    with open(f"{OUT_DIR}/stage6_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
