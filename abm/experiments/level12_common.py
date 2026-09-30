"""Level 1.2: shared helpers for Stage 1-7 experiment scripts.

Mirrors ``experiments/level11_common.py``'s own "one canonical run +
summarize function" discipline. Reports every Level 1.2 generative
event type's raw count separately (never merged into one activity
score), plus the institution registry's own ever-formed/active-at-end
counts (Section 8's ``classify_all_outcome`` inputs)."""

from __future__ import annotations

import os

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.institutional_phenotype import institutional_phenotype_vector
from abm_governance.observer.institutional_viability import (
    classify_all_outcome,
    sustained_system_eligibility,
)
from abm_governance.simulation import Simulation


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def build_rule_by_patch(sim: Simulation) -> dict:
    """Patch-id-keyed rule dict combining currently-active rules with the
    last-dissolved rule for any patch that has none active right now --
    the same "active, else last dissolved" combination
    ``experiments/level11_common.py::all_rules`` flattens to a list;
    here it stays patch-id-keyed since that is what
    ``observer/institutional_phenotype.py``'s functions expect."""
    rule_by_patch = dict(sim._last_dissolved_rule_by_patch)
    rule_by_patch.update(sim.rule_registry)
    return rule_by_patch


def compute_phenotype_vector(sim: Simulation, config: SimulationConfig, window: tuple[int, int] | None = None) -> dict:
    """Assembles every input ``institutional_phenotype_vector`` needs
    from a completed (or in-progress) ``Simulation``'s own state --
    observer-only, called after ``sim.run()``, never during generative
    rounds."""
    rule_by_patch = build_rule_by_patch(sim)
    n_patches = len(sim.patch_system.patches) if sim.patch_system is not None else 0
    current_step = config.n_steps - 1
    return institutional_phenotype_vector(
        event_log=sim.event_log, rule_by_patch=rule_by_patch, institution_registry=sim.institution_registry,
        delegate_registry=sim.delegate_registry, patch_system=sim.patch_system,
        coordination_components=sim._coordination_components, n_patches=n_patches,
        initial_population=config.population_size, current_step=current_step, window=window,
    )


def compute_eligibility(sim: Simulation, config: SimulationConfig, phenotype_vector: dict, outcome: dict) -> dict:
    """Section 8B eligibility screen for one completed run, using
    already-computed quantities (``outcome`` is this run's
    ``run_and_summarize`` output)."""
    n_post_burn_in_observations = max(0, config.n_steps - config.n_steps // 10)  # crude burn-in proxy: last 90% of steps
    surviving_population = sum(1 for a in sim.agents if a.alive)
    max_duration = 0
    for r in sim.institution_registry.values():
        end = r.extinction_time if r.extinction_time is not None else config.n_steps - 1
        max_duration = max(max_duration, end - r.creation_time)
    terminal_state_valid = outcome["all_outcome_label"] != "unclassified"
    return sustained_system_eligibility(
        n_post_burn_in_observations, surviving_population, phenotype_vector, max_duration, terminal_state_valid,
    )


#: The six Level 1.2 event-log attributes this module reports counts
#: for, restated once here so every stage script counts the same set
#: identically (rather than each re-listing them ad hoc).
LEVEL12_EVENT_LOG_ATTRS: tuple[str, ...] = (
    "local_institution_observations",
    "institution_component_transmissions",
    "migrations",
    "membership_exits",
    "institution_extinctions",
    "coordination_scale_changes",
)


def run_and_summarize(config: SimulationConfig, return_sim: bool = False):
    """Run one Level 1.2 configuration and return every Stage 1-7 script
    needs: raw per-event-type counts, institution-registry-derived
    ever-formed/active-at-end counts, and an all-outcome classification
    (Section 8A) for this one run. ``return_sim=True`` additionally
    returns the completed ``Simulation`` object itself (needed by
    scripts that go on to compute a phenotype vector or temporal
    features from the same run, e.g. Stage 2+) as ``(summary, sim)``."""
    sim = Simulation(config)
    sim.run()
    log = sim.event_log
    counts = {f"n_{attr}": len(getattr(log, attr)) for attr in LEVEL12_EVENT_LOG_ATTRS}

    n_ever_formed = len(sim.institution_registry)
    active_records = [r for r in sim.institution_registry.values() if not r.extinct]
    n_active_at_end = len(active_records)
    max_jurisdiction_size = max((len(r.active_jurisdiction) for r in active_records), default=0)

    n_alive = sum(1 for a in sim.agents if a.alive)
    population_alive_fraction = n_alive / len(sim.agents) if sim.agents else float("nan")
    ecological_fraction = float("nan")
    if sim.patch_system is not None and sim.patch_system.patches:
        capacities = [p.capacity for p in sim.patch_system.patches.values() if p.capacity]
        resources = [p.resources for p in sim.patch_system.patches.values()]
        if capacities and sum(capacities) > 0:
            ecological_fraction = sum(resources) / sum(capacities)

    outcome_label = classify_all_outcome(
        n_ever_formed, n_active_at_end, population_alive_fraction, ecological_fraction, max_jurisdiction_size,
    )

    summary = {
        **counts,
        "n_institutions_ever_formed": n_ever_formed,
        "n_institutions_active_at_end": n_active_at_end,
        "max_jurisdiction_size": max_jurisdiction_size,
        "population_alive_fraction": population_alive_fraction,
        "ecological_resource_fraction": ecological_fraction,
        "all_outcome_label": outcome_label,
    }
    if return_sim:
        return summary, sim
    return summary
