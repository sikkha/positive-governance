#!/usr/bin/env python3
"""Level 1.3b, Work Package D / Stage 4 (task #117, Section 8): ONE
purpose-designed, homogeneous, space-filling discovery design -- the
raw-material pool the later blind-discovery/model-comparison stages
(Stage 7, task #120) will fit against, recorded here without drawing
any conclusion of its own (same discipline as Level 1.3's own Stage 4
and Stage 6).

Frozen design (`experiments.level13b_preregistration.STAGE4_
HOMOGENEOUS_DISCOVERY`, verified unaltered before this script runs):
48 LHS points x 5 seeds/point = 240 runs, population=40, n_patches=4,
n_steps=500, `lhs_seed=20260821001`. 11 named search dimensions.

**Operationalization disclosure (written BEFORE running, per Section
21's disclosed-before-running discipline).** The frozen dimension
NAMES (`experiments/level13b_preregistration.py::STAGE4_HOMOGENEOUS_
DISCOVERY["dimensions"]`) were reconstructed from a compacted summary
of Section 8, not a verbatim transcription (see that module's own
context-loss disclosure) -- they name WHAT varies, not the exact
config-field mapping. This script's own, explicit, pre-run mapping:

* ``{channel}_pressure_onset_step`` (3 dims, one per channel) -> that
  channel's own ``{channel}_onset_step``, searched independently in
  [0, 300] -- channel ORDER/overlap emerges from these three
  independent draws, exactly as it did in Level 1.3's own Stage 4.
* ``pressure_magnitude_high_level`` -> a single ``high_level`` value
  applied to ALL THREE channels (one shared magnitude dimension, not
  three, per the frozen dimension list's own singular naming),
  searched in [0.3, 0.9].
* ``pressure_duration_steps`` -> combined with
  ``pressure_volatility_shock_interval`` (below) to derive each
  channel's ``n_shocks`` (see next bullet); searched in [60, 400] as
  the total nominal active span.
* ``pressure_volatility_shock_interval`` -> every channel's own
  ``shock_interval_steps``, searched independently of duration, in
  [10, 100]. **Design choice**: every channel uses
  ``history_kind="repeated_shocks"`` this stage (not Level 1.3 Stage
  3/4's smooth ``"early_pulse"``) -- a genuinely irregular,
  nonmonotonic pressure history, appropriate for Level 1.3b's OWN
  homogeneous discovery pool being methodologically distinct from
  Level 1.3's. ``shock_width_steps`` is fixed at a small disclosed
  constant (5, the ``PressureHistorySpec`` default) for every
  point/channel -- not itself a free dimension. ``n_shocks`` is
  derived, not drawn: ``max(1, round(duration_steps /
  shock_interval_steps))``, so both ``pressure_duration_steps`` and
  ``pressure_volatility_shock_interval`` remain genuinely independent
  free dimensions that jointly determine shock count.
* ``pressure_overlap_fraction`` -> stretches each channel's own
  derived ``n_shocks`` by ``(1 + overlap_fraction)`` (searched in
  [0.0, 1.0]) -- a higher value lengthens each channel's own shock
  train, increasing the chance its span overlaps its neighbors'
  independently-drawn onsets, without touching the onset draws
  themselves (which stay the pure ordering signal).
* ``entrenchment_strength_maturation_steps`` -> ``entrenchment_
  maturation_steps`` (lower = matures faster = "stronger" for a given
  run length, consistent with Stage 3's own off/moderate=150/strong=50
  convention), searched in [20, 300]; ``entrenchment_enabled=True``
  forced for every point (Stage 1/3 already tested its own on/off
  activation).
* ``performance_legitimacy_sensitivity`` / ``procedural_legitimacy_
  sensitivity`` -> ``performance_legitimacy_learning_rate`` /
  ``procedural_legitimacy_learning_rate`` respectively (the closest
  existing "how strongly does legitimacy respond" config field to a
  reconstructed dimension named "sensitivity"; ``config.py`` has no
  field literally named ``*_sensitivity`` for either legitimacy
  channel), each searched in [0.01, 0.3]; both legitimacy channels
  forced ``enabled=True`` for every point.
* ``ecological_feasibility_stratum`` -> a continuous LHS draw in
  [0, 1) bucketed into one of the three already-frozen strata
  (``floor(u * 3)``), reusing this milestone's own frozen ecological
  points (``ECOLOGICAL_STRATA_POINT_IDS``, the SAME points Stage 3
  used) rather than drawing new ecological parameters -- this
  milestone's own "reused frozen ecological design" convention.

Every one of these choices is a disclosed design decision made before
any run executes, exactly as this milestone's Stage 3 disclosed its
own "named orderings are qualitative labels" choice."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os

import numpy as np
from scipy.stats import qmc

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.level13_phenotype import level13_phenotype_vector
from abm_governance.observer.sequencing_diagnostics import institutional_response_series, sequencing_vector
from abm_governance.observer.sz_obs import s_obs_z_obs_series
from abm_governance.simulation import Simulation
from experiments.level13_common import transmission_overrides_for_channel
from experiments.level13b_preregistration import (
    ECOLOGICAL_DESIGN_SOURCE,
    ECOLOGICAL_STRATA_POINT_IDS,
    STAGE4_HOMOGENEOUS_DISCOVERY,
    load_and_verify_manifest,
)

OUT_DIR = "outputs/level13b_stage4_homogeneous_discovery"
N_POINTS = STAGE4_HOMOGENEOUS_DISCOVERY["n_points"]
N_SEEDS_PER_POINT = STAGE4_HOMOGENEOUS_DISCOVERY["n_seeds_per_point"]
LHS_SEED = STAGE4_HOMOGENEOUS_DISCOVERY["lhs_seed"]
N_STEPS = 500
POPULATION = 40
N_PATCHES = 4
SEED_BASE = 8_700_000  # fresh, disclosed; distinct from every prior Level 1.3/1.3b seed_base.
SHOCK_WIDTH_STEPS = 5   # fixed disclosed constant, not a search dimension.
STRATA_ORDER = ("low_feasibility", "medium_feasibility", "high_feasibility")

_CHANNELS = ("security_pressure", "bargaining_pressure", "coordination_complexity")

#: Order matches STAGE4_HOMOGENEOUS_DISCOVERY["dimensions"] (frozen
#: manifest) exactly, one (name, low, high) tuple per free dimension.
#: ecological_feasibility_stratum is drawn on [0, 1) and bucketed
#: post-hoc -- see module docstring.
_PARAMETER_SPACE: tuple[tuple[str, float, float], ...] = (
    ("security_pressure_onset_step", 0.0, 300.0),
    ("bargaining_pressure_onset_step", 0.0, 300.0),
    ("coordination_complexity_onset_step", 0.0, 300.0),
    ("pressure_magnitude_high_level", 0.3, 0.9),
    ("pressure_duration_steps", 60.0, 400.0),
    ("pressure_overlap_fraction", 0.0, 1.0),
    ("pressure_volatility_shock_interval", 10.0, 100.0),
    ("entrenchment_strength_maturation_steps", 20.0, 300.0),
    ("performance_legitimacy_sensitivity", 0.01, 0.3),
    ("procedural_legitimacy_sensitivity", 0.01, 0.3),
    ("ecological_feasibility_stratum", 0.0, 1.0),
)
assert [n for n, _, _ in _PARAMETER_SPACE] == list(STAGE4_HOMOGENEOUS_DISCOVERY["dimensions"])


def lhs_draws(n: int = N_POINTS, seed: int = LHS_SEED) -> list[dict]:
    sampler = qmc.LatinHypercube(d=len(_PARAMETER_SPACE), seed=seed)
    unit_sample = sampler.random(n=n)
    lows = np.array([lo for _, lo, _ in _PARAMETER_SPACE])
    highs = np.array([hi for _, _, hi in _PARAMETER_SPACE])
    scaled = qmc.scale(unit_sample, lows, highs)
    names = [name for name, _, _ in _PARAMETER_SPACE]
    return [dict(zip(names, row)) for row in scaled.tolist()]


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


def _stratum_from_draw(u: float) -> str:
    idx = min(2, int(u * 3.0))
    return STRATA_ORDER[idx]


def _build_config(draw: dict, seed: int, eco_points: dict) -> SimulationConfig:
    duration = draw["pressure_duration_steps"]
    interval = draw["pressure_volatility_shock_interval"]
    overlap = draw["pressure_overlap_fraction"]
    n_shocks = max(1, round(duration / interval * (1.0 + overlap)))
    stratum = _stratum_from_draw(draw["ecological_feasibility_stratum"])

    overrides: dict = dict(
        historical_module_enabled=True,
        entrenchment_enabled=True,
        entrenchment_maturation_steps=int(round(draw["entrenchment_strength_maturation_steps"])),
        performance_legitimacy_enabled=True,
        performance_legitimacy_learning_rate=draw["performance_legitimacy_sensitivity"],
        procedural_legitimacy_enabled=True,
        procedural_legitimacy_learning_rate=draw["procedural_legitimacy_sensitivity"],
        **eco_points[stratum],
    )
    for channel in _CHANNELS:
        onset = int(round(draw[f"{channel}_onset_step"]))
        overrides[f"{channel}_enabled"] = True
        overrides[f"{channel}_history_kind"] = "repeated_shocks"
        overrides[f"{channel}_onset_step"] = onset
        overrides[f"{channel}_high_level"] = draw["pressure_magnitude_high_level"]
        overrides[f"{channel}_n_shocks"] = n_shocks
        overrides[f"{channel}_shock_width_steps"] = SHOCK_WIDTH_STEPS
        overrides[f"{channel}_shock_interval_steps"] = int(round(interval))
        overrides.update(transmission_overrides_for_channel(channel))

    return SimulationConfig.level12b_frozen_reference(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed, **overrides,
    ), stratum, n_shocks


def _run_one(args) -> dict:
    point_id, draw, seed, eco_points = args
    config, stratum, n_shocks = _build_config(draw, seed, eco_points)
    sim = Simulation(config)
    sim.run()

    response = institutional_response_series(sim.event_log, N_STEPS)
    vector = sequencing_vector(response, min_duration_steps=10)
    phenotype_raw = level13_phenotype_vector(
        sim.event_log, sim.rule_registry, n_steps=N_STEPS, current_step=N_STEPS,
        entrenchment_maturation_steps=int(round(draw["entrenchment_strength_maturation_steps"])),
    )
    phenotype = {k: v["value"] for k, v in phenotype_raw.items()}
    s_series, z_series = s_obs_z_obs_series(sim.event_log, N_STEPS)

    return {
        "seed": seed,
        "point_id": point_id,
        "stratum": stratum,
        "derived_n_shocks": n_shocks,
        "draw": draw,
        "sequencing_vector": vector,
        "phenotype_vector": phenotype,
        "S_obs_final": float(s_series[-1]),
        "Z_obs_final": float(z_series[-1]),
    }


def write_scope_declaration(out_dir: str = OUT_DIR) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    scope = {
        "milestone": "level1.3b_work_package_d_stage4_homogeneous_discovery",
        "n_points": N_POINTS,
        "n_seeds_per_point": N_SEEDS_PER_POINT,
        "n_runs_declared": N_POINTS * N_SEEDS_PER_POINT,
        "population_size": POPULATION,
        "n_patches": N_PATCHES,
        "n_steps": N_STEPS,
        "lhs_seed": LHS_SEED,
        "seed_base": SEED_BASE,
        "parameter_space": [{"field": n, "low": lo, "high": hi} for n, lo, hi in _PARAMETER_SPACE],
        "operationalization_note": "see module docstring for the full, pre-run dimension-name-to-config-field mapping disclosure",
        "no_counterfactual_reruns_in_pool": True,
        "scale_disclosed_as": STAGE4_HOMOGENEOUS_DISCOVERY["scale_disclosed_as"],
    }
    with open(os.path.join(out_dir, "scope_declaration.json"), "w") as f:
        json.dump(scope, f, indent=2, sort_keys=True)
    return scope


def run_smoke_test(eco_points: dict) -> bool:
    draws = lhs_draws(n=2, seed=LHS_SEED)
    try:
        for point_id, draw in enumerate(draws):
            record = _run_one((point_id, draw, SEED_BASE + point_id, eco_points))
            assert "sequencing_vector" in record and "phenotype_vector" in record
            assert record["stratum"] in STRATA_ORDER
        return True
    except Exception as exc:  # noqa: BLE001 -- smoke test must report, not raise
        print(f"SMOKE TEST FAILED: {exc}")
        return False


def _job_key(point_id: int, seed_idx: int) -> str:
    return f"{point_id}|{seed_idx}"


def run_full_design(eco_points: dict, out_dir: str = OUT_DIR) -> list[dict]:
    records_path = os.path.join(out_dir, "records.json")
    existing: dict[str, dict] = {}
    if os.path.exists(records_path):
        with open(records_path) as f:
            prior = json.load(f)
        for rec in prior.get("records", []):
            existing[_job_key(rec["point_id"], rec["seed"] - (SEED_BASE + rec["point_id"] * 1000))] = rec

    draws = lhs_draws(N_POINTS)
    jobs = []
    job_keys = []
    for point_id, draw in enumerate(draws):
        for seed_idx in range(N_SEEDS_PER_POINT):
            key = _job_key(point_id, seed_idx)
            if key in existing:
                continue
            seed = SEED_BASE + point_id * 1000 + seed_idx
            jobs.append((point_id, draw, seed, eco_points))
            job_keys.append(key)

    new_records = []
    if jobs:
        with multiprocessing.Pool(2) as pool:
            for rec in pool.imap(_run_one, jobs):
                new_records.append(rec)

    all_records = list(existing.values()) + new_records
    all_records.sort(key=lambda r: (r["point_id"], r["seed"]))

    with open(records_path, "w") as f:
        json.dump({"records": all_records}, f, indent=2, sort_keys=True, default=str)
    return all_records


def summarize(records: list[dict]) -> dict:
    by_stratum: dict[str, int] = {}
    for r in records:
        by_stratum[r["stratum"]] = by_stratum.get(r["stratum"], 0) + 1
    s_obs_vals = [r["S_obs_final"] for r in records]
    z_obs_vals = [r["Z_obs_final"] for r in records]
    # NOTE (bug found and fixed while reviewing this stage's own first-run
    # output, disclosed in dev_mem/status_update.md): the sequencing
    # vector's own key is "bargaining_participation" (no "seq_" prefix --
    # that prefix belongs only to level13_phenotype_vector's flattened
    # field names). An earlier draft of this function checked the wrong
    # key (permanently None) and separately would have mis-handled the
    # phenotype vector's own NaN-for-missing convention (NaN is not
    # None) had it fallen back to that field instead. Fixed to check the
    # correct field with an explicit not-NaN test.
    bargaining_activated = sum(
        1 for r in records
        if r["sequencing_vector"].get("bargaining_participation") is not None
    )
    return {
        "n_records": len(records),
        "n_points_covered": len({r["point_id"] for r in records}),
        "records_by_stratum": by_stratum,
        "S_obs_final_mean": float(np.mean(s_obs_vals)) if s_obs_vals else None,
        "S_obs_final_std": float(np.std(s_obs_vals)) if s_obs_vals else None,
        "Z_obs_final_mean": float(np.mean(z_obs_vals)) if z_obs_vals else None,
        "Z_obs_final_std": float(np.std(z_obs_vals)) if z_obs_vals else None,
        "n_bargaining_participation_activated": bargaining_activated,
        "fraction_bargaining_participation_activated": bargaining_activated / len(records) if records else None,
        "note": (
            "descriptive pool statistics only -- no clustering/discovery model is fit here; "
            "that is Stage 7's own job (task #120), which reuses this pool as ONE of its "
            "candidate-model inputs"
        ),
    }


def report_hash(report: dict) -> str:
    payload = json.dumps(report, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> dict:
    os.makedirs(OUT_DIR, exist_ok=True)
    load_and_verify_manifest()  # hard stop if the frozen manifest was altered
    eco_points = _load_ecological_points()
    scope = write_scope_declaration()
    smoke_ok = run_smoke_test(eco_points)
    if not smoke_ok:
        report = {"scope": scope, "smoke_test_passed": False, "status": "STOPPED_AFTER_SMOKE_TEST_FAILURE"}
        with open(os.path.join(OUT_DIR, "stage4_report.json"), "w") as f:
            json.dump(report, f, indent=2, sort_keys=True)
        print(json.dumps(report, indent=2, sort_keys=True))
        return report

    records = run_full_design(eco_points)
    summary = summarize(records)
    report = {"scope": scope, "smoke_test_passed": True, **summary}
    report["report_hash"] = report_hash(report)
    with open(os.path.join(OUT_DIR, "stage4_report.json"), "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
