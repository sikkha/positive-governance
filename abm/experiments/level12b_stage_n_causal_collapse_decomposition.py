#!/usr/bin/env python3
"""Level 1.2b, Work Package N (Section 19): causal collapse
decomposition. Matched-seed, mechanism-substream causal experiments on
13 factors -- migration rate/on-off/cost/congestion, patch regen,
capacity, extraction unit, subsistence, maintenance efficiency, admin
cost, transmission cost, coordination cost, scale-overload -- a
"limited preregistered ... sequential design" (Section 19's own
wording): each factor gets its own matched-seed paired ablation (low
vs. high, or off vs. on), run once, sequentially across factors, NOT a
full 2^13 factorial (which would be both combinatorially intractable
and would conflate multiple simultaneous changes, defeating the
"exactly one factor differs" causal-attribution logic this design
depends on) -- exactly Level 1.2's own Section 13 precedent
(``experiments/level12_stage13_causal_ablations.py``), generalized
from 2 factors to 13 and reusing its own paired-comparison /
Wilcoxon-signed-rank pattern directly.

**Primary outcomes** (Section 19's own list), all four computed from a
SINGLE simulation pass per arm via
``feasibility_ratios.run_with_realized_balance_tracking`` (Section 6.3,
already built and tested -- not re-derived here):
1. ``ecological_resource_fraction`` -- final patch-resource / patch-
   capacity ratio.
2. ``cumulative_unmet_extraction_demand`` -- Section 6.3's own summary
   field, direct reuse.
3. ``fraction_of_steps_below_one`` -- Section 6.3's own "time below
   feasibility ratio 1" diagnostic, direct reuse (the realized
   supply/demand ratio, not any ex-ante expected quantity).
4. Collapse / fragmentation / sustained-system PROBABILITY -- per arm,
   the fraction of that arm's ``N_SEEDS_PER_ABLATION`` runs landing in
   the relevant ``classify_all_outcome`` label (or, for sustained-
   system, the fraction meeting ``sustained_system_eligibility``) --
   reusing Section 8's already-built classification primitives
   directly, the same ones Work Package J's main discovery pipeline
   uses.

**Field mapping, disclosed.** Every ablated factor maps to an existing
``SimulationConfig`` field; two required a documented interpretive
choice rather than a literal 1:1 name match:
- "migration congestion" -> ``migration_capacity_per_patch`` (``None``
  = uncongested/unconstrained, the codebase's own documented default,
  vs. a tight cap of 2 members/patch = congested).
- "transmission cost" -> ``transmission_base_probability``. Component-
  wise institutional transmission (Section 3, Work Package C) carries
  NO direct resource-cost field in this codebase (only probability/
  mutation/recombination/failure parameters) -- a lower base
  probability is the closest available analogue to a "more costly"
  (harder-to-achieve) transmission channel, disclosed here rather than
  silently treated as a literal cost ablation.
- "admin cost" -> ``delegation_task_cost`` (the delegate's own
  per-task resource cost -- distinct from ``coordination_cost_per_
  step``, which is its own separate factor below), matching this
  codebase's own existing ``level11_no_admin_cost`` preset's choice of
  what "administrative cost" means.

**Base configuration**: population=32, n_patches=4, n_steps=700 --
Work Package M's own null-baseline structural parameters, every Level
1.2 mechanism active at its ordinary default (``SimulationConfig.
level12_complete`` plus the same delegation/discretion/accountability/
interpatch-coordination overrides Work Package E's own ``_build_
config`` uses) -- so any ablation's effect is measured against the
SAME baseline every other Work Package this milestone used, not a
freshly chosen one.

**Stop condition, honored explicitly (Section 19's own wording): "do
not recalibrate main discovery results afterward."** This script's
own results are never fed back into Work Package E's design, Work
Package I's manifest, or any other already-frozen artifact -- reported
as-is, exactly once, after Work Packages E through M."""

from __future__ import annotations

import json
import os

from scipy.stats import wilcoxon

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.feasibility_ratios import RealizedBalanceStep, _events_by_step, _summarize_realized_balance
from abm_governance.observer.institutional_phenotype import institutional_phenotype_vector
from abm_governance.observer.institutional_viability import classify_all_outcome, sustained_system_eligibility
from abm_governance.simulation import Simulation
from experiments.level12b_stage_i_preregistration_manifest import load_and_verify_manifest

OUT_DIR = "outputs/level12b_stage_n_causal_collapse_decomposition"

POPULATION = 32
N_PATCHES = 4
N_STEPS = 700
N_SEEDS_PER_ABLATION = 8
#: Disjoint from every other Work Package's own seed range this
#: milestone (Work Package E: 9,000,000+; Work Package L confirmation:
#: 15,000,000+; Work Package M scaling: 18,000,000+).
SEED_BASE = 21_000_000

#: 13 factors, first-listed-order preserved from Section 19's own
#: wording. Each entry: ``field`` (the SimulationConfig field ablated),
#: ``low``/``high`` values, and ``extra_overrides`` (mechanism switches
#: that must be True for the ablated field to have any effect at all --
#: e.g. ablating migration_cost is meaningless with migration_enabled
#: left at its default False).
FACTORS: tuple[dict, ...] = (
    {"key": "migration_on_off", "field": "migration_enabled", "low": False, "high": True, "extra_overrides": {}},
    {"key": "migration_rate", "field": "migration_propensity_mean", "low": 0.05, "high": 0.4, "extra_overrides": {"migration_enabled": True}},
    {"key": "migration_cost", "field": "migration_cost", "low": 0.0, "high": 4.0, "extra_overrides": {"migration_enabled": True}},
    {"key": "migration_congestion", "field": "migration_capacity_per_patch", "low": None, "high": 2, "extra_overrides": {"migration_enabled": True}},
    {"key": "patch_regen", "field": "patch_regen_rate", "low": 0.2, "high": 1.0, "extra_overrides": {}},
    {"key": "capacity", "field": "patch_capacity", "low": 200.0, "high": 1000.0, "extra_overrides": {}},
    {"key": "extraction_unit", "field": "ecological_harvest_unit", "low": 2.0, "high": 10.0, "extra_overrides": {}},
    {"key": "subsistence", "field": "subsistence_cost", "low": 0.1, "high": 0.6, "extra_overrides": {}},
    {"key": "maintenance_efficiency", "field": "maintenance_efficiency", "low": 0.3, "high": 1.0, "extra_overrides": {}},
    {"key": "admin_cost", "field": "delegation_task_cost", "low": 0.0, "high": 0.2, "extra_overrides": {}},
    {"key": "transmission_cost", "field": "transmission_base_probability", "low": 0.01, "high": 0.2, "extra_overrides": {"institutional_transmission_enabled": True}},
    {"key": "coordination_cost", "field": "coordination_cost_per_step", "low": 0.0, "high": 0.2, "extra_overrides": {}},
    {"key": "scale_overload", "field": "scaling_admin_overhead_per_patch", "low": 0.0, "high": 0.2, "extra_overrides": {"institutional_scaling_enabled": True}},
)


def _base_kwargs(seed: int) -> dict:
    return dict(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed,
        rng_mode="mechanism_substreams",
        delegation_enabled=True, discretion_enabled=True, accountability_enabled=True,
        interpatch_coordination_enabled=True, institutional_fund_contribution_rate=0.05,
    )


def _build_arm_config(factor: dict, value, seed: int) -> SimulationConfig:
    overrides = dict(factor["extra_overrides"])
    overrides[factor["field"]] = value
    return SimulationConfig.level12_complete(**_base_kwargs(seed), **overrides)


def _run_with_tracking(config: SimulationConfig):
    """A local variant of ``feasibility_ratios.run_with_realized_
    balance_tracking`` that ALSO returns the live ``Simulation`` object
    (needed here for institution/delegate-registry-derived outcomes
    that ``SimulationResult`` does not carry) rather than only the
    ``SimulationResult``/``RealizedBalanceSummary`` pair that function
    returns. Reuses that function's own summary/event-grouping helpers
    directly (``_summarize_realized_balance``, ``_events_by_step``,
    ``RealizedBalanceStep``) -- only the thin per-step regeneration-
    wrapping loop is duplicated, since the original function does not
    expose the ``sim`` it wraps to its own caller."""
    sim = Simulation(config)
    per_step_regen: dict[int, float] = {}
    current_step = [-1]
    orig_run_one_step = sim._run_one_step

    def wrapped_run_one_step(step: int):
        current_step[0] = step
        return orig_run_one_step(step)

    sim._run_one_step = wrapped_run_one_step
    for patch in sim.patch_system.patches.values():
        orig_regen = patch.regenerate

        def wrapped_regen(orig=orig_regen):
            added = orig()
            per_step_regen[current_step[0]] = per_step_regen.get(current_step[0], 0.0) + added
            return added

        patch.regenerate = wrapped_regen

    sim.run()

    eco_by_step = _events_by_step(sim.event_log.ecological_actions)
    subsistence_by_step = _events_by_step(sim.event_log.subsistence)
    per_step = []
    for step in sorted(per_step_regen.keys()):
        eco_events = eco_by_step.get(step, [])
        subsistence_events = subsistence_by_step.get(step, [])
        requested = sum(e.requested_extraction for e in eco_events) + sum(e.total_cost for e in subsistence_events)
        fulfilled = sum(e.actual_extraction for e in eco_events)
        supply = per_step_regen[step]
        ratio = (supply / requested) if requested > 0.0 else None
        per_step.append(RealizedBalanceStep(step=step, realized_supply=supply, realized_requested_demand=requested, realized_fulfilled_extraction=fulfilled, ratio=ratio))
    balance = _summarize_realized_balance(per_step, sim.patch_system)
    return sim, balance


def _run_arm(config: SimulationConfig) -> dict:
    sim, balance = _run_with_tracking(config)
    n_alive = sum(1 for a in sim.agents if a.alive)
    population_alive_fraction = (n_alive / len(sim.agents)) if sim.agents else float("nan")
    capacities = [p.capacity for p in sim.patch_system.patches.values() if p.capacity]
    resources = [p.resources for p in sim.patch_system.patches.values()]
    ecological_resource_fraction = (sum(resources) / sum(capacities)) if capacities and sum(capacities) > 0 else float("nan")

    active_records = [r for r in sim.institution_registry.values() if not r.extinct]
    n_ever_formed = len(sim.institution_registry)
    n_active_at_end = len(active_records)
    max_jurisdiction_size = max((len(r.active_jurisdiction) for r in active_records), default=0)
    outcome_label = classify_all_outcome(
        n_ever_formed, n_active_at_end, population_alive_fraction, ecological_resource_fraction, max_jurisdiction_size,
    )

    rule_by_patch = dict(sim._last_dissolved_rule_by_patch)
    rule_by_patch.update(sim.rule_registry)
    phenotype_vector = institutional_phenotype_vector(
        event_log=sim.event_log, rule_by_patch=rule_by_patch, institution_registry=sim.institution_registry,
        delegate_registry=sim.delegate_registry, patch_system=sim.patch_system,
        coordination_components=sim._coordination_components, n_patches=len(sim.patch_system.patches),
        initial_population=sim.config.population_size, current_step=sim.config.n_steps - 1, window=None,
    )
    n_post_burn_in_observations = max(0, sim.config.n_steps - sim.config.n_steps // 10)
    max_duration = 0
    for r in sim.institution_registry.values():
        end = r.extinction_time if r.extinction_time is not None else sim.config.n_steps - 1
        max_duration = max(max_duration, end - r.creation_time)
    eligibility = sustained_system_eligibility(
        n_post_burn_in_observations, n_alive, phenotype_vector, max_duration,
        terminal_state_valid=(outcome_label != "unclassified"),
    )

    return {
        "all_outcome_label": outcome_label,
        "sustained_eligible": eligibility["eligible"],
        "ecological_resource_fraction": ecological_resource_fraction,
        "cumulative_unmet_extraction_demand": balance.cumulative_unmet_extraction_demand,
        "fraction_of_steps_below_one": balance.fraction_of_steps_below_one,
    }


def _paired_summary(pairs: list[dict], outcome_key: str) -> dict:
    diffs = [p["high"][outcome_key] - p["low"][outcome_key] for p in pairs if p["high"][outcome_key] == p["high"][outcome_key] and p["low"][outcome_key] == p["low"][outcome_key]]
    n_high_greater = sum(1 for d in diffs if d > 0)
    n_low_greater = sum(1 for d in diffs if d < 0)
    n_tied = len(diffs) - n_high_greater - n_low_greater
    mean_diff = sum(diffs) / len(diffs) if diffs else float("nan")
    wilcoxon_result = {"statistic": None, "p_value": None, "note": "not computed"}
    try:
        if any(d != 0 for d in diffs) and len(diffs) >= 1:
            stat, p = wilcoxon(diffs)
            wilcoxon_result = {"statistic": float(stat), "p_value": float(p), "note": "n too small for a confident test; supplementary only"}
    except ValueError as exc:
        wilcoxon_result["note"] = str(exc)
    return {
        "n_defined_pairs": len(diffs), "mean_paired_difference_high_minus_low": mean_diff,
        "n_high_greater": n_high_greater, "n_low_greater": n_low_greater, "n_tied": n_tied,
        "wilcoxon_signed_rank": wilcoxon_result,
    }


def _probability(pairs: list[dict], arm: str, predicate) -> float:
    return sum(1 for p in pairs if predicate(p[arm])) / len(pairs) if pairs else float("nan")


def run_factor_ablation(factor: dict, seed_offset: int) -> dict:
    pairs = []
    for i in range(N_SEEDS_PER_ABLATION):
        seed = SEED_BASE + seed_offset * 100 + i
        low_config = _build_arm_config(factor, factor["low"], seed)
        high_config = _build_arm_config(factor, factor["high"], seed)
        pairs.append({"seed": seed, "low": _run_arm(low_config), "high": _run_arm(high_config)})

    n_outcome_transitions = sum(1 for p in pairs if p["low"]["all_outcome_label"] != p["high"]["all_outcome_label"])
    return {
        "factor": factor["key"], "field": factor["field"], "low_value": factor["low"], "high_value": factor["high"],
        "extra_overrides": factor["extra_overrides"], "n_pairs": len(pairs), "pairs": pairs,
        "n_outcome_label_transitions": n_outcome_transitions,
        "summary": {
            "ecological_resource_fraction": _paired_summary(pairs, "ecological_resource_fraction"),
            "cumulative_unmet_extraction_demand": _paired_summary(pairs, "cumulative_unmet_extraction_demand"),
            "fraction_of_steps_below_one": _paired_summary(pairs, "fraction_of_steps_below_one"),
            "collapse_probability": {
                "low": _probability(pairs, "low", lambda a: a["all_outcome_label"] == "collapse"),
                "high": _probability(pairs, "high", lambda a: a["all_outcome_label"] == "collapse"),
            },
            "fragmentation_probability": {
                "low": _probability(pairs, "low", lambda a: a["all_outcome_label"] == "fragmented"),
                "high": _probability(pairs, "high", lambda a: a["all_outcome_label"] == "fragmented"),
            },
            "sustained_system_probability": {
                "low": _probability(pairs, "low", lambda a: a["sustained_eligible"]),
                "high": _probability(pairs, "high", lambda a: a["sustained_eligible"]),
            },
        },
    }


def run() -> dict:
    wp_i = load_and_verify_manifest()  # hard stop if Work Package I's frozen manifest was altered
    factor_results = []
    for idx, factor in enumerate(FACTORS):
        result = run_factor_ablation(factor, idx)
        factor_results.append(result)
        print(
            f"factor {factor['key']} done: mean eco-fraction diff (high-low)="
            f"{result['summary']['ecological_resource_fraction']['mean_paired_difference_high_minus_low']:.4f}, "
            f"{result['n_outcome_label_transitions']}/{result['n_pairs']} outcome-label transitions",
            flush=True,
        )
    report = {
        "preregistration_manifest_hash": wp_i["hash"],
        "n_factors": len(FACTORS), "n_seeds_per_ablation": N_SEEDS_PER_ABLATION,
        "n_total_runs": len(FACTORS) * N_SEEDS_PER_ABLATION * 2,
        "recalibration_note": "results here are never fed back into Work Package E's design, Work Package I's manifest, or any other already-frozen artifact -- Section 19's own stop condition, honored as-is",
        "factor_results": factor_results,
    }
    return report


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    report = run()
    with open(f"{OUT_DIR}/results.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Work Package N: {report['n_factors']} factors, {report['n_total_runs']} total runs")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
