"""Level 1.0: shared helpers for Stage 1-4 experiment scripts.

Loads the Level 0.3b registered candidate ecological parameter points
(``outputs/level03b_candidate_registry/candidate_registry.json``, written
by Level 0.3b and never modified by this milestone) and provides one
canonical "run one Level 1.0 configuration, summarize with
observer/institution_diagnostics" function so every downstream Stage
script builds and reports results identically.
"""

from __future__ import annotations

import json
import os

from abm_governance.core.config import SimulationConfig
from abm_governance.observer import institution_diagnostics as idg
from abm_governance.simulation import Simulation

REGISTRY_PATH = "outputs/level03b_candidate_registry/candidate_registry.json"


def load_candidate_ecological_params(candidate_key: str) -> dict:
    """``candidate_key`` in {"interior_persistent", "nonstationary",
    "near_collapse"} -- the three Level 0.3b registered candidates, all
    three of which the milestone's decision record cites as showing
    endogenous ecological-policy adaptation causally worsening occupancy
    relative to frozen/randomized counterfactuals."""
    with open(REGISTRY_PATH) as f:
        registry = json.load(f)
    params = dict(registry["selected"][candidate_key]["parameters"])
    return params


def build_config(candidate_key: str, institutional_overrides: dict, seed: int, n_steps: int) -> SimulationConfig:
    eco = load_candidate_ecological_params(candidate_key)
    overrides = dict(eco)
    overrides.update(institutional_overrides)
    overrides["ecology_topology"] = "patches"
    overrides["rule_formation_enabled"] = True
    overrides.setdefault("monitoring_mode", "voluntary")
    overrides.setdefault("sanction_mode", "voluntary")
    return SimulationConfig(seed=seed, n_steps=n_steps, **overrides)


def run_and_summarize(config: SimulationConfig) -> dict:
    sim = Simulation(config)
    result = sim.run()
    final_step = config.n_steps - 1
    all_rules = list(sim.rule_registry.values()) + list(sim._last_dissolved_rule_by_patch.values())
    metrics = idg.summarize_institutional_metrics(sim.agents, sim.event_log, all_rules, final_step)

    classifications = []
    for pid in sim.patch_system.patches:
        rule = sim.rule_registry.get(pid) or sim._last_dissolved_rule_by_patch.get(pid)
        cls = idg.classify_rule(rule, sim.event_log, pid, final_step)
        classifications.append({"patch_id": pid, "label": cls["label"], "duration_steps": cls["duration_steps"]})

    last_row = result.metrics[-1]
    ecological_outcomes = {
        "final_occupancy": last_row.get("patch_occupancy_mean", float("nan")),
        "final_total_resources": sum(a.resources for a in sim.agents if a.alive),
        "cumulative_extraction": sum(p.cumulative_extraction for p in sim.patch_system.patches.values()),
        "cumulative_maintenance_invested": sum(p.cumulative_maintenance_invested for p in sim.patch_system.patches.values()),
        "cumulative_unmet_extraction_demand": sum(p.cumulative_unmet_extraction_demand for p in sim.patch_system.patches.values()),
        "n_patches_at_zero_resources": sum(1 for p in sim.patch_system.patches.values() if p.resources <= 0.0),
    }
    return {
        "metrics": metrics,
        "classifications": classifications,
        "ecological_outcomes": ecological_outcomes,
        "n_alive_at_end": sum(1 for a in sim.agents if a.alive),
    }


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)
