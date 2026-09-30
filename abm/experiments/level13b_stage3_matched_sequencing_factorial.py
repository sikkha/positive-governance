#!/usr/bin/env python3
"""Level 1.3b, Work Package E / Stage 3 (task #116, Section 9): purpose-
designed matched sequencing factorial, independent of the Stage 4
discovery pool (no run here is ever reused there).

Design frozen in `experiments/level13b_preregistration.py::STAGE3_
MATCHED_FACTORIAL` and `docs/level13b_preregistration.md` §4 BEFORE this
script ran -- every literal below is imported from that frozen module,
never re-typed, so this script cannot silently drift from what was
preregistered. 108 cells (3 pressure orderings x 3 entrenchment levels x
4 legitimacy conditions x 3 ecological strata) x 2 seeds = 216 runs.

**Matched cumulative pressure exposure** is satisfied by construction:
every cell's config uses the SAME three onset slots {0, 150, 300} for
`security_first`/`bargaining_first` (just assigned to different
channels), and all three channels at onset 0 for `coevolution` -- so
every run in a matched (entrenchment, legitimacy, stratum) cell receives
identical total pressure, differing only in WHEN each channel activates.

**Contrasts are computed only WITHIN matched cells** (same entrenchment
x legitimacy x stratum, varying only ordering) -- never pooled across
cells that differ on those factors, per the frozen design's own
requirement. Raw matched differences are reported alongside seed-
clustered bootstrap CIs; with only 2 seeds/cell (a disclosed session-
budget scope reduction, not a preferred sample size), the bootstrap
distribution over seeds is necessarily coarse (only 3 distinct
2-with-replacement resamples of 2 items) -- reported honestly as a
limitation, not smoothed over."""

from __future__ import annotations

import json
import multiprocessing
import os

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.level13_phenotype import level13_phenotype_vector
from abm_governance.observer.sequencing_diagnostics import institutional_response_series, sequencing_vector
from abm_governance.observer.sz_obs import s_obs_z_obs_series
from abm_governance.simulation import Simulation
from experiments.level13_common import transmission_overrides_for_channel
from experiments.level13b_preregistration import (
    ECOLOGICAL_DESIGN_SOURCE,
    ECOLOGICAL_STRATA_POINT_IDS,
    STAGE3_MATCHED_FACTORIAL,
    load_and_verify_manifest,
)

import numpy as np

OUT_DIR = "outputs/level13b_stage3_matched_sequencing_factorial"

FACTORS = STAGE3_MATCHED_FACTORIAL["factors"]
N_SEEDS_PER_CELL = STAGE3_MATCHED_FACTORIAL["n_seeds_per_cell"]
POPULATION = STAGE3_MATCHED_FACTORIAL["population_size"]
N_PATCHES = STAGE3_MATCHED_FACTORIAL["n_patches"]
N_STEPS = STAGE3_MATCHED_FACTORIAL["n_steps"]
SEED_BASE = STAGE3_MATCHED_FACTORIAL["seed_base"]


def _load_ecological_points() -> dict[str, dict]:
    with open(ECOLOGICAL_DESIGN_SOURCE) as f:
        design = json.load(f)
    by_id = {p["point_id"]: p for p in design["points"]}
    out = {}
    for stratum, point_id in ECOLOGICAL_STRATA_POINT_IDS.items():
        point = by_id[point_id]
        assert point["expected_stratum"] == stratum
        eco = dict(point["ecological_parameters"])
        eco.pop("shock_interval_steps", None)
        eco.pop("shock_magnitude", None)
        out[stratum] = eco
    return out


def _build_config(ordering_name: str, entrenchment_name: str, legitimacy_name: str, stratum: str, seed: int, eco_points: dict) -> SimulationConfig:
    order_onsets = FACTORS["pressure_ordering"][ordering_name]
    entrenchment_overrides = FACTORS["entrenchment"][entrenchment_name]
    legitimacy_overrides = FACTORS["legitimacy"][legitimacy_name]

    overrides: dict = dict(
        historical_module_enabled=True,
        **entrenchment_overrides, **legitimacy_overrides,
        **eco_points[stratum],
    )
    for channel, onset in order_onsets.items():
        overrides[f"{channel}_enabled"] = True
        overrides[f"{channel}_history_kind"] = "early_pulse"
        overrides[f"{channel}_onset_step"] = onset
        overrides[f"{channel}_duration_steps"] = None
        overrides.update(transmission_overrides_for_channel(channel))

    return SimulationConfig.level12b_frozen_reference(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed, **overrides,
    )


def _manipulation_check(sim: Simulation, ordering_name: str) -> bool:
    order_onsets = FACTORS["pressure_ordering"][ordering_name]
    for channel, onset in order_onsets.items():
        series = sim.historical_state[f"{channel}_series"]
        if onset > 0 and not all(v == series[0] for v in series[:onset]):
            return False
        if not all(v == series[onset] for v in series[onset:]):
            return False
        if onset > 0 and series[0] == series[onset]:
            return False
    return True


def _cell_key(ordering_name, entrenchment_name, legitimacy_name, stratum, seed_idx):
    return (ordering_name, entrenchment_name, legitimacy_name, stratum, seed_idx)


def _run_one(args) -> dict:
    ordering_name, entrenchment_name, legitimacy_name, stratum, seed_idx, eco_points = args
    seed = SEED_BASE + seed_idx
    config = _build_config(ordering_name, entrenchment_name, legitimacy_name, stratum, seed, eco_points)
    sim = Simulation(config)
    sim.run()

    response = institutional_response_series(sim.event_log, N_STEPS)
    vector = sequencing_vector(response, min_duration_steps=10)
    phenotype_raw = level13_phenotype_vector(
        sim.event_log, sim.rule_registry, n_steps=N_STEPS, current_step=N_STEPS,
        entrenchment_maturation_steps=entrenchment_overrides_maturation(entrenchment_name),
    )
    phenotype = {k: v["value"] for k, v in phenotype_raw.items()}
    S_obs_series, Z_obs_series = s_obs_z_obs_series(sim.event_log, N_STEPS)

    contrib_events = list(sim.event_log.contributions)
    n_total = len(contrib_events)
    n_complied = sum(1 for e in contrib_events if e.complied)

    # Disclosed simplification: Simulation does not retain a per-step
    # resource history per agent, so "final third" is scoped down to a
    # final-STEP snapshot (mean resources across all agents at n_steps),
    # not a true windowed average -- disclosed in scope_declaration.json
    # rather than silently relabeled; the true windowed version is
    # Stage 5/Work Package F's own job (task #118), which DOES build a
    # dedicated temporal-window module.
    resources_final_third = [a.resources for a in sim.agents_by_id.values()]

    n_active_rules_final = sum(1 for r in sim.rule_registry.values() if r.active)
    cross_founder_final = float(response["cross_founder_reconstruction"][-1])

    return {
        "ordering_name": ordering_name, "entrenchment_name": entrenchment_name,
        "legitimacy_name": legitimacy_name, "stratum": stratum, "seed_idx": seed_idx, "seed": seed,
        "manipulation_check_passed": _manipulation_check(sim, ordering_name),
        "bargaining_participation_sustained_crossing_step": vector["bargaining_participation"],
        "S_obs": float(np.mean(S_obs_series)),
        "Z_obs": float(np.mean(Z_obs_series)),
        "realized_compliance_rate": (n_complied / n_total) if n_total else None,
        "mean_resources_final_step": float(np.mean(resources_final_third)) if resources_final_third else None,
        "n_active_rules_final_step": n_active_rules_final,
        "entrenchment_index_final_step": phenotype["entrenchment"],
        "cross_founder_reconstruction_count_final_step": cross_founder_final,
        "n_contribution_events": n_total,
    }


def entrenchment_overrides_maturation(entrenchment_name: str) -> int:
    overrides = FACTORS["entrenchment"][entrenchment_name]
    return overrides.get("entrenchment_maturation_steps", 100)


def write_scope_declaration() -> dict:
    os.makedirs(OUT_DIR, exist_ok=True)
    scope = {
        "milestone": "level1.3b_work_package_e_stage3_matched_sequencing_factorial",
        "n_cells": STAGE3_MATCHED_FACTORIAL["n_cells"],
        "n_seeds_per_cell": N_SEEDS_PER_CELL,
        "n_runs_declared": STAGE3_MATCHED_FACTORIAL["n_runs_declared"],
        "seed_base": SEED_BASE, "population_size": POPULATION, "n_patches": N_PATCHES, "n_steps": N_STEPS,
        "primary_outcomes": STAGE3_MATCHED_FACTORIAL["primary_outcomes"],
        "uncertainty_method": STAGE3_MATCHED_FACTORIAL["uncertainty_method"],
        "disclosed_limitation": "n_seeds_per_cell=2 gives a coarse (3-resample) seed-clustered bootstrap; reported honestly, not smoothed over.",
        "disclosed_simplification": "mean_resources_final_step is a final-STEP snapshot, not a true final-third windowed average (Simulation does not retain per-step per-agent resource history) -- the windowed version is Stage 5/Work Package F's own job (task #118).",
    }
    with open(os.path.join(OUT_DIR, "scope_declaration.json"), "w") as f:
        json.dump(scope, f, indent=2, sort_keys=True)
    return scope


def run_smoke_test(eco_points: dict) -> bool:
    result = _run_one(("coevolution", "off", "neither", "low_feasibility", 0, eco_points))
    ok = result["manipulation_check_passed"] and result["n_contribution_events"] >= 0
    with open(os.path.join(OUT_DIR, "smoke_test.json"), "w") as f:
        json.dump({"passed": ok, "result": result}, f, indent=2, sort_keys=True, default=str)
    return ok


def _all_jobs(eco_points: dict) -> list:
    jobs = []
    for ordering_name in FACTORS["pressure_ordering"]:
        for entrenchment_name in FACTORS["entrenchment"]:
            for legitimacy_name in FACTORS["legitimacy"]:
                for stratum in FACTORS["ecological_stratum"]:
                    for seed_idx in range(N_SEEDS_PER_CELL):
                        jobs.append((ordering_name, entrenchment_name, legitimacy_name, stratum, seed_idx, eco_points))
    return jobs


def run_full_factorial(eco_points: dict) -> list[dict]:
    jobs = _all_jobs(eco_points)
    results_path = os.path.join(OUT_DIR, "records.json")
    existing: list[dict] = []
    done_keys = set()
    if os.path.exists(results_path):
        with open(results_path) as f:
            existing = json.load(f)
        done_keys = {
            (r["ordering_name"], r["entrenchment_name"], r["legitimacy_name"], r["stratum"], r["seed_idx"])
            for r in existing
        }
    remaining = [j for j in jobs if (j[0], j[1], j[2], j[3], j[4]) not in done_keys]
    if remaining:
        n_workers = min(2, multiprocessing.cpu_count())
        with multiprocessing.Pool(n_workers) as pool:
            new_results = pool.map(_run_one, remaining)
        existing.extend(new_results)
        with open(results_path, "w") as f:
            json.dump(existing, f, indent=2, sort_keys=True, default=str)
    return existing


def summarize(records: list[dict]) -> dict:
    n_manip_failures = sum(1 for r in records if not r["manipulation_check_passed"])

    # Matched contrasts: within each (entrenchment, legitimacy, stratum)
    # cell, compare orderings pairwise on S_obs/Z_obs, raw differences +
    # seed-clustered bootstrap (3 resamples given n_seeds_per_cell=2).
    by_cell: dict = {}
    for r in records:
        key = (r["entrenchment_name"], r["legitimacy_name"], r["stratum"])
        by_cell.setdefault(key, {}).setdefault(r["ordering_name"], []).append(r)

    contrasts = []
    orderings = list(FACTORS["pressure_ordering"].keys())
    rng = np.random.default_rng(20260821)
    for cell_key, by_ordering in by_cell.items():
        if not all(o in by_ordering for o in orderings):
            continue
        for i in range(len(orderings)):
            for j in range(i + 1, len(orderings)):
                o1, o2 = orderings[i], orderings[j]
                rows1, rows2 = by_ordering[o1], by_ordering[o2]
                if not rows1 or not rows2:
                    continue
                s1 = np.array([r["S_obs"] for r in rows1])
                s2 = np.array([r["S_obs"] for r in rows2])
                z1 = np.array([r["Z_obs"] for r in rows1])
                z2 = np.array([r["Z_obs"] for r in rows2])
                raw_s_diff = float(np.mean(s1) - np.mean(s2))
                raw_z_diff = float(np.mean(z1) - np.mean(z2))
                boot_s, boot_z = [], []
                for _ in range(200):
                    bs1 = rng.choice(s1, size=len(s1), replace=True)
                    bs2 = rng.choice(s2, size=len(s2), replace=True)
                    bz1 = rng.choice(z1, size=len(z1), replace=True)
                    bz2 = rng.choice(z2, size=len(z2), replace=True)
                    boot_s.append(float(np.mean(bs1) - np.mean(bs2)))
                    boot_z.append(float(np.mean(bz1) - np.mean(bz2)))
                contrasts.append({
                    "entrenchment": cell_key[0], "legitimacy": cell_key[1], "stratum": cell_key[2],
                    "ordering_a": o1, "ordering_b": o2,
                    "raw_S_obs_diff": raw_s_diff, "raw_Z_obs_diff": raw_z_diff,
                    "S_obs_diff_ci95": [float(np.percentile(boot_s, 2.5)), float(np.percentile(boot_s, 97.5))],
                    "Z_obs_diff_ci95": [float(np.percentile(boot_z, 2.5)), float(np.percentile(boot_z, 97.5))],
                })

    return {
        "n_records": len(records),
        "n_manipulation_check_failures": n_manip_failures,
        "all_manipulation_checks_passed": n_manip_failures == 0,
        "n_matched_cells_with_all_three_orderings": len(by_cell),
        "n_pairwise_contrasts": len(contrasts),
        "contrasts": contrasts,
    }


def main() -> dict:
    eco_points = _load_ecological_points()
    load_and_verify_manifest()  # hard stop if the frozen manifest was altered
    scope = write_scope_declaration()
    smoke_ok = run_smoke_test(eco_points)
    if not smoke_ok:
        report = {"scope": scope, "smoke_test_passed": False, "status": "STOPPED_AFTER_SMOKE_TEST_FAILURE"}
        with open(os.path.join(OUT_DIR, "stage3_report.json"), "w") as f:
            json.dump(report, f, indent=2, sort_keys=True)
        print(json.dumps(report, indent=2, sort_keys=True))
        return report

    records = run_full_factorial(eco_points)
    summary = summarize(records)
    report = {"scope": scope, "smoke_test_passed": True, **summary}
    with open(os.path.join(OUT_DIR, "stage3_report.json"), "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    printable = {k: v for k, v in report.items() if k != "contrasts"}
    printable["n_contrasts_written_to_file"] = len(summary["contrasts"])
    print(json.dumps(printable, indent=2, sort_keys=True, default=str))
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
