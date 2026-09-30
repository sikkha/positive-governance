#!/usr/bin/env python3
"""Level 1.3b, Work Package C / Stage 2 (Section 7): mechanism-only
calibration sweep to find a region where `bargaining_participation`
activates in ~20-80% of eligible runs -- never mechanically guaranteed,
never absent everywhere -- represented across ecological strata.

**Levers swept, all explicitly licensed by Section 7, chosen per Work
Package B's own disposition** (`docs/level1.3b_bargaining_activation_
audit.md` §4: "response cost" and "participation-opportunity frequency"
are the mechanistically correct levers, since realized compliance is
dominated by resource insolvency, not unwillingness):

- **response cost**: `contribution_amount` in {0.2 (Level 1.1 default),
  0.1, 0.05, 0.02}.
- **participation-opportunity frequency**: `contribution_period_steps`
  in {10 (default), 5}.
- **sustained-crossing duration** (a Section 7-licensed lever distinct
  from "the threshold," which Section 6 explicitly forbids touching as
  a sole fix): `min_duration_steps` in {10, 5, 3}, evaluated FOR FREE
  post-hoc from the same run (it is a `sequencing_vector` analysis
  parameter, not a simulation input) -- reported alongside, not treated
  as this sweep's primary calibration axis.

**Never selected via S_obs/Z_obs/clustering/dissertation resemblance**:
this script computes ONLY `sequencing_vector`'s own bargaining-
participation activation (crossed / not crossed) -- no S_obs, no Z_obs,
no phenotype vector, no clustering is computed anywhere in this file.

**Ecological strata**: reuses Level 1.3's own already-frozen Stage 2
30-point ecological design (`outputs/level13_stage2_calibration/
design.json`) rather than drawing a new one -- one representative point
per stratum (`low_feasibility`=point 0, `medium_feasibility`=point 2,
`high_feasibility`=point 1), matching this project's "single frozen
design, reused downstream" convention (`experiments/level13_common.py`'s
own docstring).

**Scope, disclosed before running** (Section 21): 3 strata x 4 response
costs x 2 periods x 4 seeds = 96 runs, all on the Stage-3-representative
pressure/entrenchment shape (population 40, 3 patches, 500 steps) held
fixed so only the licensed levers vary. A single-seed smoke test runs
first and must pass before the full 96-run sweep executes."""

from __future__ import annotations

import json
import multiprocessing
import os

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.sequencing_diagnostics import institutional_response_series, sequencing_vector
from abm_governance.simulation import Simulation
from experiments.level13_common import transmission_overrides_for_channel

OUT_DIR = "outputs/level13b_stage2_bargaining_calibration"
FROZEN_DESIGN_PATH = "outputs/level13_stage2_calibration/design.json"

N_STEPS = 500
POPULATION = 40
N_PATCHES = 3
SEED_BASE = 8_100_000
N_SEEDS = 4

RESPONSE_COSTS = (0.2, 0.1, 0.05, 0.02)
PERIODS = (10, 5)
MIN_DURATION_STEPS_VALUES = (10, 5, 3)
TARGET_STRATA_POINT_IDS = {"low_feasibility": 0, "medium_feasibility": 2, "high_feasibility": 1}

_ORDER = ("security_pressure", "bargaining_pressure", "coordination_complexity")
_ONSETS = (0, 150, 300)


def _load_ecological_points() -> dict[str, dict]:
    with open(FROZEN_DESIGN_PATH) as f:
        design = json.load(f)
    by_id = {p["point_id"]: p for p in design["points"]}
    out = {}
    for stratum, point_id in TARGET_STRATA_POINT_IDS.items():
        point = by_id[point_id]
        assert point["expected_stratum"] == stratum, (stratum, point["expected_stratum"])
        eco = dict(point["ecological_parameters"])
        eco.pop("shock_interval_steps", None)
        eco.pop("shock_magnitude", None)
        out[stratum] = eco
    return out


def write_scope_declaration() -> dict:
    os.makedirs(OUT_DIR, exist_ok=True)
    n_runs = len(TARGET_STRATA_POINT_IDS) * len(RESPONSE_COSTS) * len(PERIODS) * N_SEEDS
    scope = {
        "milestone": "level1.3b_work_package_c_stage2_bargaining_calibration",
        "levers_swept": {
            "response_cost_contribution_amount": list(RESPONSE_COSTS),
            "participation_frequency_contribution_period_steps": list(PERIODS),
            "sustained_crossing_duration_min_duration_steps_post_hoc": list(MIN_DURATION_STEPS_VALUES),
        },
        "levers_held_fixed": [
            "pressure_onset_order (security, bargaining, coordination_complexity)",
            "pressure_magnitude_and_kind (early_pulse, level12b_frozen_reference defaults)",
            "transmission_sensitivity (bargaining_pressure_conditional_contribution_sensitivity, config default)",
            "entrenchment_enabled=True, entrenchment_maturation_steps=100",
        ],
        "ecological_strata": list(TARGET_STRATA_POINT_IDS.keys()),
        "ecological_design_source": FROZEN_DESIGN_PATH,
        "n_seeds_per_cell": N_SEEDS,
        "seed_base": SEED_BASE,
        "n_cells": len(TARGET_STRATA_POINT_IDS) * len(RESPONSE_COSTS) * len(PERIODS),
        "n_runs_declared": n_runs,
        "target_activation_fraction_range": [0.2, 0.8],
        "selection_rule_disclosed": (
            "region frozen for downstream use = cells where activation_fraction "
            "at min_duration_steps=10 falls in [0.2, 0.8], selected using ONLY "
            "bargaining_participation activation counts -- never S_obs, Z_obs, "
            "clustering, or dissertation resemblance"
        ),
        "population_size": POPULATION, "n_patches": N_PATCHES, "n_steps": N_STEPS,
    }
    with open(os.path.join(OUT_DIR, "scope_declaration.json"), "w") as f:
        json.dump(scope, f, indent=2, sort_keys=True)
    return scope


def _build_config(stratum: str, response_cost: float, period: int, seed: int, eco_points: dict) -> SimulationConfig:
    overrides: dict = dict(
        historical_module_enabled=True, entrenchment_enabled=True, entrenchment_maturation_steps=100,
        contribution_amount=response_cost, contribution_period_steps=period,
        **eco_points[stratum],
    )
    for channel, onset in zip(_ORDER, _ONSETS):
        overrides[f"{channel}_enabled"] = True
        overrides[f"{channel}_history_kind"] = "early_pulse"
        overrides[f"{channel}_onset_step"] = onset
        overrides[f"{channel}_duration_steps"] = None
        overrides.update(transmission_overrides_for_channel(channel))
    return SimulationConfig.level12b_frozen_reference(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed, **overrides,
    )


def _run_one(args) -> dict:
    stratum, response_cost, period, seed, eco_points = args
    config = _build_config(stratum, response_cost, period, seed, eco_points)
    sim = Simulation(config)
    sim.run()
    response = institutional_response_series(sim.event_log, N_STEPS)
    contrib_events = list(sim.event_log.contributions)
    n_total = len(contrib_events)
    n_complied = sum(1 for e in contrib_events if e.complied)
    activation = {
        f"min_duration_steps_{md}": sequencing_vector(response, min_duration_steps=md)["bargaining_participation"] is not None
        for md in MIN_DURATION_STEPS_VALUES
    }
    return {
        "stratum": stratum, "response_cost": response_cost, "period": period, "seed": seed,
        "realized_compliance_rate": (n_complied / n_total) if n_total else None,
        "n_contribution_events": n_total,
        **activation,
    }


def run_smoke_test(eco_points: dict) -> bool:
    """One-seed smoke test per cell's own extreme corner (cheapest
    response cost, most frequent participation) -- must complete without
    error before the full sweep runs, per Section 21."""
    result = _run_one(("low_feasibility", RESPONSE_COSTS[-1], PERIODS[-1], SEED_BASE, eco_points))
    ok = result["n_contribution_events"] > 0
    with open(os.path.join(OUT_DIR, "smoke_test.json"), "w") as f:
        json.dump({"passed": ok, "result": result}, f, indent=2, sort_keys=True)
    return ok


def run_full_sweep(eco_points: dict) -> list[dict]:
    jobs = []
    for stratum in TARGET_STRATA_POINT_IDS:
        for rc in RESPONSE_COSTS:
            for period in PERIODS:
                for i in range(N_SEEDS):
                    seed = SEED_BASE + i + 1
                    jobs.append((stratum, rc, period, seed, eco_points))

    results_path = os.path.join(OUT_DIR, "sweep_results.json")
    existing: list[dict] = []
    done_keys = set()
    if os.path.exists(results_path):
        with open(results_path) as f:
            existing = json.load(f)
        done_keys = {(r["stratum"], r["response_cost"], r["period"], r["seed"]) for r in existing}

    remaining = [j for j in jobs if (j[0], j[1], j[2], j[3]) not in done_keys]
    if remaining:
        n_workers = min(2, multiprocessing.cpu_count())
        with multiprocessing.Pool(n_workers) as pool:
            new_results = pool.map(_run_one, remaining)
        existing.extend(new_results)
        with open(results_path, "w") as f:
            json.dump(existing, f, indent=2, sort_keys=True)
    return existing


def summarize(results: list[dict]) -> dict:
    cells: dict = {}
    for r in results:
        key = (r["stratum"], r["response_cost"], r["period"])
        cells.setdefault(key, []).append(r)

    cell_summaries = []
    for (stratum, rc, period), rows in sorted(cells.items()):
        n = len(rows)
        summary = {
            "stratum": stratum, "response_cost": rc, "period": period, "n_seeds": n,
            "mean_realized_compliance_rate": sum(x["realized_compliance_rate"] or 0.0 for x in rows) / n,
        }
        for md in MIN_DURATION_STEPS_VALUES:
            key_name = f"min_duration_steps_{md}"
            frac = sum(1 for x in rows if x[key_name]) / n
            summary[f"activation_fraction_{key_name}"] = frac
        cell_summaries.append(summary)

    frozen_region = [
        c for c in cell_summaries
        if 0.2 <= c["activation_fraction_min_duration_steps_10"] <= 0.8
    ]
    strata_represented = sorted({c["stratum"] for c in frozen_region})

    return {
        "cell_summaries": cell_summaries,
        "frozen_region_candidates": frozen_region,
        "frozen_region_strata_represented": strata_represented,
        "n_cells_total": len(cell_summaries),
        "n_cells_in_target_range": len(frozen_region),
    }


def main() -> dict:
    eco_points = _load_ecological_points()
    scope = write_scope_declaration()
    smoke_ok = run_smoke_test(eco_points)
    if not smoke_ok:
        report = {"scope": scope, "smoke_test_passed": False, "status": "STOPPED_AFTER_SMOKE_TEST_FAILURE"}
        with open(os.path.join(OUT_DIR, "calibration_report.json"), "w") as f:
            json.dump(report, f, indent=2, sort_keys=True)
        print(json.dumps(report, indent=2, sort_keys=True))
        return report

    results = run_full_sweep(eco_points)
    summary = summarize(results)
    report = {
        "scope": scope, "smoke_test_passed": True,
        "n_runs_completed": len(results),
        **summary,
    }
    with open(os.path.join(OUT_DIR, "calibration_report.json"), "w") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
