#!/usr/bin/env python3
"""Level 1.3b, Work Package F / Stage 5 (task #118, Section 10):
temporal-persistence and hysteresis diagnostics, applied to real runs
for the first time (``observer/historical_persistence.py`` itself was
built and unit-tested first -- see that module and ``tests/test_
level13b_historical_persistence.py``).

Frozen inputs verified before running: the manifest hash
(``load_and_verify_manifest``) and ``STAGE5_TEMPORAL_PERSISTENCE``'s
own windows/diagnostics/classification-categories.

**Two-part design, disclosed before running:**

**Part A -- ordering-differentiation persistence (H3).** Reuses Stage
3's own ``security_first`` vs ``coevolution`` orderings (the two most
different qualitative sequences in Stage 3's factorial) at ONE
representative cell (``entrenchment=moderate``, ``legitimacy=dual``,
``stratum=medium_feasibility`` -- a single disclosed cell, not the
full Stage 3 factorial; Stage 3 already covered the factorial at
final-step resolution, this stage's own job is the WINDOWED
trajectory a single cell needs to answer persistence, not to re-run
the whole design), 16 seeds/ordering (matching Level 1.3's own Stage
5 seed count). Unlike Stage 3, this records the FULL S_obs/Z_obs
series (available post-hoc from the event log for every step, not
just the final one) so :func:`trajectory_distance` and
:func:`condition_rank_stability` can be computed windowed, and
:func:`classify_persistence` applied per seed to the security_first-
vs-coevolution gap trajectory.

**Part B -- causal counterfactual persistence (H5, the three named
"persistence_after_pressure_*" diagnostics).** For the SAME 16
``security_first`` seeds from Part A (reused, not re-run -- identical
config/seed), three matched counterfactual re-runs override ALL THREE
pressure channels together (shape (b) from ``core/historical_
counterfactuals.py``'s own disclosed caveat -- sidesteps the partial-
override RNG-shift gap entirely): ``removed`` (``erase_pressure_from``
at step 250, the run's temporal midpoint), ``reversed``
(``reverse_pressure_order``), ``equalized`` (``equalize_pressure_
series``, the new Level 1.3b transform). 16 seeds x 3 counterfactuals
= 48 new runs; combined with Part A's reused 16 security_first base
runs, this answers "does divergence from base persist across windows,
or does it fade by the late window" for each intervention -- the
exact question the frozen dict's ``persistence_after_pressure_
removal/reversal/equalization`` diagnostics name.

Total unique simulation runs this stage: 16 (security_first) + 16
(coevolution) + 48 (3 counterfactuals x 16 reused-seed security_first
runs) = 80."""

from __future__ import annotations

import json
import multiprocessing
import os

import numpy as np

from abm_governance.core.config import SimulationConfig
from abm_governance.core.historical_counterfactuals import (
    equalize_pressure_series,
    erase_pressure_from,
    reverse_pressure_order,
)
from abm_governance.observer.historical_persistence import (
    classify_persistence,
    condition_rank_stability,
    convergence_divergence_slope,
    early_to_middle_displacement,
    late_window_variance,
    middle_to_late_displacement,
    trajectory_distance,
    windowed_mean,
)
from abm_governance.observer.sz_obs import s_obs_z_obs_series
from abm_governance.simulation import Simulation
from experiments.level13_common import transmission_overrides_for_channel
from experiments.level13b_preregistration import (
    ECOLOGICAL_DESIGN_SOURCE,
    ECOLOGICAL_STRATA_POINT_IDS,
    STAGE3_MATCHED_FACTORIAL,
    load_and_verify_manifest,
)

OUT_DIR = "outputs/level13b_stage5_temporal_persistence"
N_SEEDS = 16
POPULATION = 40
N_PATCHES = 3
N_STEPS = 500
SEED_BASE = 8_900_000  # fresh, disclosed; distinct from every prior Level 1.3/1.3b seed_base.
INTERVENTION_STEP = 250  # run's temporal midpoint, disclosed before running.
REPRESENTATIVE_ENTRENCHMENT = "moderate"
REPRESENTATIVE_LEGITIMACY = "dual"
REPRESENTATIVE_STRATUM = "medium_feasibility"
CHANNELS = ("security_pressure", "bargaining_pressure", "coordination_complexity")
_TRANSFORMS = {
    "removed": lambda s: erase_pressure_from(s, step=INTERVENTION_STEP),
    "reversed": reverse_pressure_order,
    "equalized": equalize_pressure_series,
}


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


def _base_config(ordering_name: str, seed: int, eco_points: dict) -> SimulationConfig:
    order_onsets = STAGE3_MATCHED_FACTORIAL["factors"]["pressure_ordering"][ordering_name]
    entrenchment_overrides = STAGE3_MATCHED_FACTORIAL["factors"]["entrenchment"][REPRESENTATIVE_ENTRENCHMENT]
    legitimacy_overrides = STAGE3_MATCHED_FACTORIAL["factors"]["legitimacy"][REPRESENTATIVE_LEGITIMACY]
    overrides = dict(
        historical_module_enabled=True, **entrenchment_overrides, **legitimacy_overrides,
        **eco_points[REPRESENTATIVE_STRATUM],
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


def _run_base(ordering_name: str, seed: int, eco_points: dict) -> dict:
    config = _base_config(ordering_name, seed, eco_points)
    sim = Simulation(config)
    sim.run()
    s_series, z_series = s_obs_z_obs_series(sim.event_log, N_STEPS)
    # Keyed by Simulation's own state_key format ("{channel}_series"),
    # not the bare channel name -- historical_pressure_series_override
    # is matched against state_key, not the channel prefix (see
    # Simulation.__init__).
    realized = {
        f"{ch}_series": np.array(sim.historical_state[f"{ch}_series"], dtype=float, copy=True)
        for ch in CHANNELS if sim.historical_state and f"{ch}_series" in sim.historical_state
    }
    return {
        "ordering": ordering_name, "seed": seed, "variant": "base",
        "S_obs_series": s_series.tolist(), "Z_obs_series": z_series.tolist(),
        "realized_pressure_series": {ch: series.tolist() for ch, series in realized.items()},
    }


def _run_counterfactual(seed: int, variant: str, base_record: dict, eco_points: dict) -> dict:
    config = _base_config("security_first", seed, eco_points)
    override = {
        ch: _TRANSFORMS[variant](np.array(series, dtype=float))
        for ch, series in base_record["realized_pressure_series"].items()
    }
    sim = Simulation(config, historical_pressure_series_override=override)
    sim.run()
    s_series, z_series = s_obs_z_obs_series(sim.event_log, N_STEPS)
    return {
        "ordering": "security_first", "seed": seed, "variant": variant,
        "S_obs_series": s_series.tolist(), "Z_obs_series": z_series.tolist(),
    }


def _job_part_a(args):
    ordering_name, seed, eco_points = args
    return _run_base(ordering_name, seed, eco_points)


def _job_part_b(args):
    seed, variant, base_record, eco_points = args
    return _run_counterfactual(seed, variant, base_record, eco_points)


def write_scope_declaration(out_dir: str = OUT_DIR) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    scope = {
        "milestone": "level1.3b_work_package_f_stage5_temporal_persistence",
        "part_a": {"orderings": ["security_first", "coevolution"], "n_seeds": N_SEEDS, "n_runs": 2 * N_SEEDS},
        "part_b": {"base_ordering": "security_first", "variants": list(_TRANSFORMS.keys()), "n_seeds": N_SEEDS, "n_runs": N_SEEDS * len(_TRANSFORMS)},
        "n_runs_total_unique": 2 * N_SEEDS + N_SEEDS * len(_TRANSFORMS),
        "intervention_step": INTERVENTION_STEP,
        "representative_cell": {"entrenchment": REPRESENTATIVE_ENTRENCHMENT, "legitimacy": REPRESENTATIVE_LEGITIMACY, "stratum": REPRESENTATIVE_STRATUM},
        "population_size": POPULATION, "n_patches": N_PATCHES, "n_steps": N_STEPS, "seed_base": SEED_BASE,
        "disclosed_scope_reduction": (
            "single representative cell (not the full Stage 3 factorial) -- Stage 3 already covered the "
            "factorial at final-step resolution; this stage's job is windowed trajectories at that one cell, "
            "not a full factorial re-run"
        ),
    }
    with open(os.path.join(out_dir, "scope_declaration.json"), "w") as f:
        json.dump(scope, f, indent=2, sort_keys=True)
    return scope


def run_smoke_test(eco_points: dict) -> bool:
    try:
        base = _run_base("security_first", SEED_BASE, eco_points)
        assert len(base["S_obs_series"]) == N_STEPS
        assert set(base["realized_pressure_series"].keys()) == {f"{ch}_series" for ch in CHANNELS}
        cf = _run_counterfactual(SEED_BASE, "removed", base, eco_points)
        assert len(cf["S_obs_series"]) == N_STEPS
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"SMOKE TEST FAILED: {exc}")
        return False


def run_all(eco_points: dict) -> dict:
    part_a_jobs = [
        (ordering, SEED_BASE + i, eco_points)
        for ordering in ("security_first", "coevolution")
        for i in range(N_SEEDS)
    ]
    with multiprocessing.Pool(2) as pool:
        part_a_records = list(pool.imap(_job_part_a, part_a_jobs))

    base_by_seed = {r["seed"]: r for r in part_a_records if r["ordering"] == "security_first"}
    part_b_jobs = [
        (SEED_BASE + i, variant, base_by_seed[SEED_BASE + i], eco_points)
        for i in range(N_SEEDS)
        for variant in _TRANSFORMS
    ]
    with multiprocessing.Pool(2) as pool:
        part_b_records = list(pool.imap(_job_part_b, part_b_jobs))

    return {"part_a": part_a_records, "part_b": part_b_records}


def analyze(records: dict) -> dict:
    part_a = records["part_a"]
    part_b = records["part_b"]

    by_ordering: dict[str, list[dict]] = {"security_first": [], "coevolution": []}
    for r in part_a:
        by_ordering[r["ordering"]].append(r)

    seed_order = sorted({r["seed"] for r in by_ordering["security_first"]})
    per_seed_persistence = []
    for seed in seed_order:
        sec = next(r for r in by_ordering["security_first"] if r["seed"] == seed)
        coe = next(r for r in by_ordering["coevolution"] if r["seed"] == seed)
        sec_s = np.array(sec["S_obs_series"])
        coe_s = np.array(coe["S_obs_series"])
        gap = sec_s - coe_s
        e2m = early_to_middle_displacement(gap, N_STEPS)
        m2l = middle_to_late_displacement(gap, N_STEPS)
        late_var = late_window_variance(gap, N_STEPS)
        slope = convergence_divergence_slope(gap, N_STEPS)
        label = classify_persistence(e2m, m2l, late_var, slope)
        dist = trajectory_distance(sec_s, coe_s, N_STEPS)
        per_seed_persistence.append({
            "seed": seed, "early_to_middle_gap_displacement": e2m, "middle_to_late_gap_displacement": m2l,
            "late_window_gap_variance": late_var, "convergence_divergence_slope": slope,
            "classification": label, **dist,
        })

    classification_counts: dict[str, int] = {}
    for rec in per_seed_persistence:
        classification_counts[rec["classification"]] = classification_counts.get(rec["classification"], 0) + 1

    condition_means = {
        cond: {
            w: float(np.mean([windowed_mean(np.array(r["S_obs_series"]), N_STEPS, w) for r in recs]))
            for w in ("early", "middle", "late")
        }
        for cond, recs in by_ordering.items()
    }
    rank_stability = condition_rank_stability(condition_means)

    variant_persistence = {}
    for variant in _TRANSFORMS:
        rows = [r for r in part_b if r["variant"] == variant]
        divergences = []
        for r in rows:
            base = base_by_seed_lookup(part_a, r["seed"])
            base_s = np.array(base["S_obs_series"])
            cf_s = np.array(r["S_obs_series"])
            divergences.append(trajectory_distance(base_s, cf_s, N_STEPS))
        variant_persistence[variant] = {
            "n_seeds": len(rows),
            "mean_gap_at_early": float(np.mean([d["gap_at_early"] for d in divergences])),
            "mean_gap_at_middle": float(np.mean([d["gap_at_middle"] for d in divergences])),
            "mean_gap_at_late": float(np.mean([d["gap_at_late"] for d in divergences])),
            "mean_gap_at_final_sustained": float(np.mean([d["gap_at_final_sustained"] for d in divergences])),
            "note": "gap between base security_first and this counterfactual, by window -- a nonzero, non-decaying late-window gap is evidence history/order/shape causally matters beyond the intervention step",
        }

    return {
        "n_part_a_runs": len(part_a),
        "n_part_b_runs": len(part_b),
        "per_seed_ordering_persistence": per_seed_persistence,
        "classification_counts_across_16_seeds": classification_counts,
        "condition_window_means": condition_means,
        "condition_rank_stability": rank_stability,
        "counterfactual_persistence_by_variant": variant_persistence,
    }


def base_by_seed_lookup(part_a_records: list[dict], seed: int) -> dict:
    return next(r for r in part_a_records if r["ordering"] == "security_first" and r["seed"] == seed)


def main() -> dict:
    os.makedirs(OUT_DIR, exist_ok=True)
    load_and_verify_manifest()
    eco_points = _load_ecological_points()
    scope = write_scope_declaration()
    smoke_ok = run_smoke_test(eco_points)
    if not smoke_ok:
        report = {"scope": scope, "smoke_test_passed": False, "status": "STOPPED_AFTER_SMOKE_TEST_FAILURE"}
        with open(os.path.join(OUT_DIR, "stage5_report.json"), "w") as f:
            json.dump(report, f, indent=2, sort_keys=True)
        print(json.dumps(report, indent=2, sort_keys=True))
        return report

    records = run_all(eco_points)
    with open(os.path.join(OUT_DIR, "records.json"), "w") as f:
        json.dump(records, f, indent=2, sort_keys=True, default=str)
    analysis = analyze(records)
    report = {"scope": scope, "smoke_test_passed": True, **analysis}
    with open(os.path.join(OUT_DIR, "stage5_report.json"), "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    print(json.dumps({k: v for k, v in report.items() if k not in ("per_seed_ordering_persistence",)}, indent=2, sort_keys=True, default=str))
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
