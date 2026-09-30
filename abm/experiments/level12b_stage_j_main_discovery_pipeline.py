#!/usr/bin/env python3
"""Level 1.2b, Work Package J (Section 15): main discovery pipeline --
all-outcome, failure-trajectory, and sustained-system analyses over the
Work Package E joint design (>=288-run hard minimum; this script runs
the full preferred 576, matching Work Package E's own precedent that
576 is comfortably tractable in this environment -- see
``dev_mem/status_update.md``'s compute-budget disclosures).

**Reuses, rather than re-derives, every classification primitive.**
``observer/institutional_viability.py``'s :func:`classify_all_outcome`
(Section 8A -- the closed, seven-label all-outcome vocabulary,
`collapse`/`persistent_extractive` kept as first-class non-excluded
outcomes) and :func:`sustained_system_eligibility` (Section 8B -- the
preregistered, non-normative data-sufficiency screen) were already
built and tested at Level 1.2; nothing about their logic is 1.2b-
specific, so this script imports and drives them directly rather than
reimplementing.

**Why this re-runs simulations Work Package E already ran.** Work
Package E's own ``results.json`` records exist to verify the ecological
ledger closes (Section 5.7) -- they do not carry institution-registry-
derived outcome labels or phenotype vectors, which this Work Package
needs and WP E never computed. Re-running the SAME frozen design's SAME
seeds is a legitimate, deterministic re-derivation (this project's own
determinism was directly verified earlier this session -- see
``dev_mem/status_update.md``), not a "rerun a parameter search because
the outcome differs" stop-condition violation: every config/seed pair
here is identical to WP E's own, and would reproduce WP E's own ledger
residual exactly if recomputed.

**Failure-trajectory analysis ("routes to collapse").** Alongside the
end-of-run outcome label, this script also collects a cheap in-run
population/ecological-fraction series (every
``TRAJECTORY_SNAPSHOT_INTERVAL_STEPS`` steps -- population/ecological
fractions only, NOT a full ``institutional_phenotype_vector`` call,
since that would multiply the runtime cost for no benefit here) and
classifies, via :func:`classify_failure_trajectory`, HOW a run's own
terminal outcome relates to its in-run trajectory: did it dip toward
collapse and recover, never approach collapse at all, or spend a
sustained fraction of the observed run inside the same collapse
definition ``classify_all_outcome`` uses at the end. This reuses
``classify_all_outcome``'s own collapse thresholds directly (never
redefines "collapse" a second way) and is a documented heuristic
(disclosed as such, consistent with this project's register elsewhere)
rather than a formal changepoint-detection method.

**"Collapse must stay visible."** :func:`aggregate_all_outcome_summary`
reports every one of the seven ``ALL_OUTCOME_LABELS`` explicitly, with
an explicit ``0`` for any label that did not occur -- never a report
that silently omits a zero-count or low-count outcome from its own
summary dict."""

from __future__ import annotations

import json
import os

from abm_governance.observer.institutional_phenotype import institutional_phenotype_vector
from abm_governance.observer.institutional_viability import (
    ALL_OUTCOME_LABELS,
    classify_all_outcome,
    sustained_system_eligibility,
)
from abm_governance.simulation import Simulation
from experiments.level12b_stage_e_joint_discovery import (
    IC_FAMILIES,
    _build_config,
    _inject_heterogeneous_proto_institutions,
    load_and_verify_design,
)
from experiments.level12b_stage_i_preregistration_manifest import load_and_verify_manifest

OUT_DIR = "outputs/level12b_stage_j_main_discovery_pipeline"

#: Section 15's own gate: "strong claims" from the sustained-system
#: analysis require at least this many eligible runs.
SUSTAINED_RUNS_PREFERRED_MINIMUM = 60
SUSTAINED_RUNS_HARD_MINIMUM = 40

#: Cadence for the cheap population/ecological-fraction trajectory
#: series (see module docstring -- deliberately NOT a full phenotype
#: snapshot).
TRAJECTORY_SNAPSHOT_INTERVAL_STEPS = 10

#: Reused directly from ``classify_all_outcome``'s own defaults, so
#: "collapse" means exactly the same thing here as in the terminal
#: classification -- never a second, drifted definition.
COLLAPSE_POPULATION_THRESHOLD = 0.05
COLLAPSE_ECOLOGICAL_THRESHOLD = 0.05

#: Section 15's closed failure-trajectory-route vocabulary (first-match-
#: wins, see :func:`classify_failure_trajectory`).
FAILURE_TRAJECTORY_ROUTE_LABELS: tuple[str, ...] = (
    "no_collapse_observed", "transient_dip_recovered", "collapse_onset_after_last_snapshot",
    "late_onset_collapse", "sustained_collapse",
)


def _cheap_state_fractions(sim: Simulation) -> dict:
    """Population/ecological fractions computed directly from live
    ``sim`` state (no event-log scanning, no ``institutional_phenotype_
    vector`` call) -- identical formula to
    ``experiments/level12_common.py::run_and_summarize``'s own, reused
    for consistency rather than redefined."""
    n_alive = sum(1 for a in sim.agents if a.alive)
    population_alive_fraction = (n_alive / len(sim.agents)) if sim.agents else float("nan")
    ecological_fraction = float("nan")
    if sim.patch_system is not None and sim.patch_system.patches:
        capacities = [p.capacity for p in sim.patch_system.patches.values() if p.capacity]
        resources = [p.resources for p in sim.patch_system.patches.values()]
        if capacities and sum(capacities) > 0:
            ecological_fraction = sum(resources) / sum(capacities)
    return {"population_alive_fraction": population_alive_fraction, "ecological_resource_fraction": ecological_fraction}


def classify_failure_trajectory(
    series: list[dict], final_outcome_label: str,
    collapse_population_threshold: float = COLLAPSE_POPULATION_THRESHOLD,
    collapse_ecological_threshold: float = COLLAPSE_ECOLOGICAL_THRESHOLD,
) -> dict:
    """Section 15's "failure-trajectory analysis (routes to collapse)".
    First-match-wins over the closed vocabulary above:

    1. ``no_collapse_observed`` -- final outcome is not ``collapse`` and
       no snapshot ever fell inside the collapse definition.
    2. ``transient_dip_recovered`` -- final outcome is not ``collapse``
       but at least one snapshot did fall inside it (dipped and
       recovered, or dipped near the very end and the terminal state
       happened to be computed just past the dip).
    3. ``collapse_onset_after_last_snapshot`` -- final outcome IS
       ``collapse`` but no snapshot observed it -- a snapshot-resolution
       limitation (collapse occurred strictly between the last snapshot
       and the run's final step), disclosed as its own label rather
       than silently merged into another route.
    4. ``late_onset_collapse`` -- final outcome is ``collapse`` and
       fewer than half the snapshots show it (onset concentrated near
       the end).
    5. ``sustained_collapse`` -- final outcome is ``collapse`` and at
       least half the snapshots show it (collapse persisted for a
       meaningful fraction of the observed run, not just a terminal
       instant)."""
    n = len(series)
    collapsed_flags = [
        s["population_alive_fraction"] <= collapse_population_threshold
        or s["ecological_resource_fraction"] <= collapse_ecological_threshold
        for s in series
    ]
    n_collapsed = sum(collapsed_flags)
    fraction_collapsed = (n_collapsed / n) if n else float("nan")
    first_collapse_step = next((series[i]["step"] for i, f in enumerate(collapsed_flags) if f), None)

    if final_outcome_label != "collapse":
        route = "no_collapse_observed" if n_collapsed == 0 else "transient_dip_recovered"
    elif n_collapsed == 0:
        route = "collapse_onset_after_last_snapshot"
    elif fraction_collapsed >= 0.5:
        route = "sustained_collapse"
    else:
        route = "late_onset_collapse"

    return {
        "route": route, "n_snapshots": n, "n_collapsed_snapshots": n_collapsed,
        "fraction_snapshots_collapsed": fraction_collapsed, "first_collapse_step": first_collapse_step,
    }


def _run_one(point: dict, seed: int, ic_family: str) -> dict:
    config = _build_config(point, seed)
    sim = Simulation(config)
    if ic_family == "heterogeneous_proto_institution":
        _inject_heterogeneous_proto_institutions(sim, seed)

    trajectory_series = []
    for step in range(config.n_steps):
        sim._run_one_step(step)
        if step % TRAJECTORY_SNAPSHOT_INTERVAL_STEPS == 0 or step == config.n_steps - 1:
            trajectory_series.append({"step": step, **_cheap_state_fractions(sim)})

    final = trajectory_series[-1]
    active_records = [r for r in sim.institution_registry.values() if not r.extinct]
    n_ever_formed = len(sim.institution_registry)
    n_active_at_end = len(active_records)
    max_jurisdiction_size = max((len(r.active_jurisdiction) for r in active_records), default=0)

    outcome_label = classify_all_outcome(
        n_ever_formed, n_active_at_end, final["population_alive_fraction"], final["ecological_resource_fraction"],
        max_jurisdiction_size,
    )
    trajectory = classify_failure_trajectory(trajectory_series, outcome_label)

    rule_by_patch = dict(sim._last_dissolved_rule_by_patch)
    rule_by_patch.update(sim.rule_registry)
    phenotype_vector = institutional_phenotype_vector(
        event_log=sim.event_log, rule_by_patch=rule_by_patch, institution_registry=sim.institution_registry,
        delegate_registry=sim.delegate_registry, patch_system=sim.patch_system,
        coordination_components=sim._coordination_components, n_patches=len(sim.patch_system.patches),
        initial_population=config.population_size, current_step=config.n_steps - 1, window=None,
    )
    n_post_burn_in_observations = max(0, config.n_steps - config.n_steps // 10)
    surviving_population = sum(1 for a in sim.agents if a.alive)
    max_duration = 0
    for r in sim.institution_registry.values():
        end = r.extinction_time if r.extinction_time is not None else config.n_steps - 1
        max_duration = max(max_duration, end - r.creation_time)
    eligibility = sustained_system_eligibility(
        n_post_burn_in_observations, surviving_population, phenotype_vector, max_duration,
        terminal_state_valid=(outcome_label != "unclassified"),
    )

    return {
        "joint_point_id": point["joint_point_id"], "ecological_point_id": point["ecological_point_id"],
        "institutional_point_id": point["institutional_point_id"], "ic_family": ic_family, "seed": seed,
        "expected_stratum": point["expected_stratum"],
        "all_outcome_label": outcome_label,
        "failure_trajectory": trajectory,
        "sustained_eligibility": eligibility,
        "n_institutions_ever_formed": n_ever_formed, "n_institutions_active_at_end": n_active_at_end,
        "max_jurisdiction_size": max_jurisdiction_size,
        "population_alive_fraction": final["population_alive_fraction"],
        "ecological_resource_fraction": final["ecological_resource_fraction"],
        # Additive field, appended by Work Package L (Section 17):
        # Work Package J's own analysis never needed the raw vector
        # (only the derived outcome/trajectory/eligibility fields
        # above), but Work Package L's confirmation-pool feature
        # matrix does. Backward compatible -- every existing consumer
        # of this dict (Work Package J's own aggregation functions,
        # its own tests) reads specific keys and never asserts an
        # exhaustive key set, so this addition changes nothing about
        # Work Package J's already-frozen results.json or its tests.
        "phenotype_vector": phenotype_vector,
    }


def aggregate_all_outcome_summary(records: list[dict]) -> dict:
    """Section 15: "collapse must stay visible" -- every one of the
    seven closed labels appears in this summary explicitly, with an
    explicit ``0`` for any that did not occur, never silently omitted."""
    counts = {label: 0 for label in ALL_OUTCOME_LABELS}
    for r in records:
        counts[r["all_outcome_label"]] += 1
    return counts


def aggregate_failure_trajectory_summary(records: list[dict]) -> dict:
    counts = {label: 0 for label in FAILURE_TRAJECTORY_ROUTE_LABELS}
    for r in records:
        counts[r["failure_trajectory"]["route"]] += 1
    return counts


def aggregate_sustained_system_summary(records: list[dict]) -> dict:
    eligible = [r for r in records if r["sustained_eligibility"]["eligible"]]
    excluded = [r for r in records if not r["sustained_eligibility"]["eligible"]]
    reason_counts: dict[str, int] = {}
    for r in excluded:
        for reason in r["sustained_eligibility"]["reasons"]:
            key = reason.split(" (")[0]  # strip the numeric detail, keep the reason category
            reason_counts[key] = reason_counts.get(key, 0) + 1
    return {
        "n_eligible": len(eligible), "n_excluded": len(excluded), "n_total": len(records),
        "exclusion_reason_counts": reason_counts,
        "preferred_target_met": len(eligible) >= SUSTAINED_RUNS_PREFERRED_MINIMUM,
        "hard_minimum_met": len(eligible) >= SUSTAINED_RUNS_HARD_MINIMUM,
        "preferred_minimum": SUSTAINED_RUNS_PREFERRED_MINIMUM,
        "hard_minimum": SUSTAINED_RUNS_HARD_MINIMUM,
    }


def run() -> dict:
    wp_e = load_and_verify_design()
    wp_i = load_and_verify_manifest()
    design = wp_e["design"]

    records = []
    failures = []
    for point in design["points"]:
        for ic_family in IC_FAMILIES:
            for seed in point["seeds"]:
                try:
                    records.append(_run_one(point, seed, ic_family))
                except Exception as exc:  # noqa: BLE001 -- preserve failed runs, never silently drop
                    failures.append({"joint_point_id": point["joint_point_id"], "ic_family": ic_family, "seed": seed, "error": str(exc)})
        print(f"joint point {point['joint_point_id']} ({point['expected_stratum']}) done", flush=True)

    report = {
        "source_design_hash": wp_e["hash"],
        "preregistration_manifest_hash": wp_i["hash"],
        "n_runs_completed": len(records),
        "n_runs_failed": len(failures),
        "failures": failures,
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
    print(f"Work Package J: {report['n_runs_completed']} runs completed, {report['n_runs_failed']} failed")
    print(f"all-outcome summary: {report['all_outcome_summary']}")
    print(f"failure-trajectory summary: {report['failure_trajectory_summary']}")
    print(f"sustained-system summary: {report['sustained_system_summary']}")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
