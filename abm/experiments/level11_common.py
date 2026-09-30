"""Level 1.1: shared helpers for Stage 1-6 experiment scripts.

Mirrors ``experiments/level1_common.py``'s own "one canonical run +
summarize function" discipline so every downstream Level 1.1 stage
script builds and reports results identically. Uses plain
``SimulationConfig(...)`` construction directly (not the Level 0.3b
candidate-registry ecological parameters Level 1.0's scripts load) --
Level 1.1's own scope is the delegation/administrative/accountability/
coordination layer, not a re-run of the ecological calibration question
Level 1.0 already settled; ecological parameters are left at
``SimulationConfig``'s own defaults throughout.
"""

from __future__ import annotations

import os

from abm_governance.core.config import SimulationConfig
from abm_governance.observer import delegation_diagnostics as dd
from abm_governance.observer import institution_diagnostics as idg
from abm_governance.simulation import Simulation


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def all_rules(sim: Simulation) -> list:
    return list(sim.rule_registry.values()) + list(sim._last_dissolved_rule_by_patch.values())


def all_delegates(sim: Simulation) -> list:
    return list(sim.delegate_registry.values()) + sim.delegate_history


def all_links(sim: Simulation) -> list:
    return list(sim.coordination_link_registry.values())


def run_and_summarize(config: SimulationConfig) -> dict:
    """Run one Level 1.1 configuration and return every observer-side
    export this milestone's stages need, keeping every Work Package's
    dimensions separate (never merged into one score)."""
    sim = Simulation(config)
    result = sim.run()
    final_step = config.n_steps - 1
    rules = all_rules(sim)
    delegates = all_delegates(sim)
    links = all_links(sim)

    institutional_metrics = idg.summarize_institutional_metrics(sim.agents, sim.event_log, rules, final_step)
    delegation_metrics = dd.summarize_delegation_metrics(delegates, rules, links, sim.event_log)
    welfare = idg.welfare_accounting(sim.agents, rules, sim.patch_system)

    rule_classifications = []
    for pid in sim.patch_system.patches:
        rule = sim.rule_registry.get(pid) or sim._last_dissolved_rule_by_patch.get(pid)
        rule_lineage_id = rule.rule_lineage_id if rule is not None else None
        delegates_at_rule = [d for d in delegates if rule_lineage_id is not None and d.rule_lineage_id == rule_lineage_id]
        links_at_rule = [ln for ln in links if rule is not None and pid in (ln.patch_id_a, ln.patch_id_b)]
        cls = dd.classify_delegation(rule, delegates_at_rule, links_at_rule, sim.event_log, final_step)
        rule_classifications.append({"patch_id": pid, **cls})

    ecological_outcomes = {
        "final_occupancy": result.metrics[-1].get("patch_occupancy_mean", float("nan")) if result.metrics else float("nan"),
        "final_total_resources": sum(a.resources for a in sim.agents if a.alive),
        "n_alive_at_end": sum(1 for a in sim.agents if a.alive),
    }

    return {
        "n_nominations": len(sim.event_log.delegate_nominations),
        "n_appointments": len(sim.event_log.delegate_appointments),
        "n_removals": len(sim.event_log.delegate_removals),
        "n_task_performances": len(sim.event_log.task_performances),
        "n_appropriations": len(sim.event_log.appropriations),
        "n_audits": len(sim.event_log.audits),
        "n_recalls": len(sim.event_log.recalls),
        "n_recalls_succeeded": sum(1 for e in sim.event_log.recalls if e.succeeded),
        "n_appeals": len(sim.event_log.appeals),
        "n_contributions": len(sim.event_log.contributions),
        "n_coordination_proposals": len(sim.event_log.coordination_proposals),
        "n_coordination_links": len(sim.event_log.coordination_links),
        "n_active_coordination_links_at_end": sum(1 for ln in links if ln.active),
        "institutional_metrics": institutional_metrics,
        "delegation_metrics": delegation_metrics,
        "welfare_accounting": welfare,
        "rule_classifications": rule_classifications,
        "ecological_outcomes": ecological_outcomes,
    }
