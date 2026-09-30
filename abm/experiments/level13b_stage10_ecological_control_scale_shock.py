#!/usr/bin/env python3
"""Level 1.3b, Work Package K / Stage 10 (task #123, Section 15):
ecological control + scale/shock robustness -- the final experimental
stage.

**Part 1 -- scale/shock robustness runs.** Mirrors Level 1.3's own
Stage 9 (`experiments/level13_stage9_scale_and_shock_robustness.py`)
exactly: a 2x2 population x n_patches cross (`[40, 80]` x `[3, 6]`), 6
seeds/cell = 24 runs, every channel using `"repeated_shocks"` (not the
clean `"early_pulse"` step every earlier Level 1.3b stage used) with
the same disclosed `n_shocks=4` override (avoiding even the appearance
of this milestone's own "no privileged count of three" discipline
touching an experimental parameter). Reuses Stage 3's own institutional
-substrate construction (`level12b_frozen_reference()` + entrenchment +
both legitimacy channels + Work Package A transmission sub-flags),
`security_first`-style staggered onsets so the three shock-trains
remain distinguishable.

**Part 2 -- ecological-accounting ledger (`WORK_PACKAGE_K_ACCOUNTING`,
Section 15: "reused from Level 1.2b -- no new machinery").** No new
accounting machinery is added to `observer/feasibility_ratios.py`
(unmodified, per the frozen commitment); this stage instead reuses
FIELDS this milestone's own Stage 3 already computed
(`mean_resources_final_step`, `manipulation_check_passed`) and this
stage's own new 24 runs, applying the frozen `reporting_required`
views (`pooled`, `by_stratum`, `eligible_only`, `collapse_as_outcome`)
to BOTH pools -- disclosed scope: this is not a re-processing of every
run from every earlier stage (Stage 4/5/6/8's own records do not carry
a live per-run resource figure to classify by), but the two pools
where the needed field already exists.

**Collapse criterion, disclosed before computing anything**:
`mean_resources_final_step < 0`. Chosen because Stage 3's own 216
records are cleanly BIMODAL on this exact threshold with no ambiguous
middle ground (144/216 cluster tightly in [-598, -50]; the other 72/216
are all strictly positive, up to +1411) -- a threshold the data itself
suggests, not an arbitrarily tuned cutoff. **Collapsed runs are
RETAINED in every pooled/by-stratum figure below, never discarded** --
`eligible_only` is reported as an ADDITIONAL, separate, narrower view
(`manipulation_check_passed=True` -- i.e. the pressure/entrenchment/
legitimacy manipulation actually registered as intended -- collapse
status is not itself part of the eligibility filter, precisely so
`collapse_as_outcome` and `eligible_only` remain two independent,
not-nested lenses on the same complete ledger)."""

from __future__ import annotations

import json
import os

import numpy as np

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
    WORK_PACKAGE_K_ACCOUNTING,
    load_and_verify_manifest,
)

OUT_DIR = "outputs/level13b_stage10_ecological_control_scale_shock"
STAGE3_RECORDS_PATH = "outputs/level13b_stage3_matched_sequencing_factorial/records.json"
N_STEPS = 500
N_SEEDS = 6
SEED_BASE = 9_300_000  # fresh, disclosed; distinct from every prior Level 1.3b seed_base.
SCALE_CONDITIONS = ((40, 3), (40, 6), (80, 3), (80, 6))  # (population, n_patches)
N_SHOCKS = 4  # disclosed override of PressureHistorySpec's own class default (3) -- see module docstring.
SHOCK_WIDTH_STEPS = 20
SHOCK_INTERVAL_STEPS = 60
ONSET_GAP_STEPS = 50  # staggers the 3 channels' first shock so trains remain distinguishable.
REPRESENTATIVE_ENTRENCHMENT = "moderate"
REPRESENTATIVE_LEGITIMACY = "dual"
REPRESENTATIVE_STRATUM = "medium_feasibility"
CHANNELS = ("security_pressure", "bargaining_pressure", "coordination_complexity")
COLLAPSE_THRESHOLD = 0.0


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


def _build_config(population: int, n_patches: int, seed: int, eco_points: dict) -> SimulationConfig:
    entrenchment_overrides = STAGE3_MATCHED_FACTORIAL["factors"]["entrenchment"][REPRESENTATIVE_ENTRENCHMENT]
    legitimacy_overrides = STAGE3_MATCHED_FACTORIAL["factors"]["legitimacy"][REPRESENTATIVE_LEGITIMACY]
    overrides = dict(
        historical_module_enabled=True, **entrenchment_overrides, **legitimacy_overrides,
        **eco_points[REPRESENTATIVE_STRATUM],
    )
    for i, channel in enumerate(CHANNELS):
        overrides[f"{channel}_enabled"] = True
        overrides[f"{channel}_history_kind"] = "repeated_shocks"
        overrides[f"{channel}_onset_step"] = i * ONSET_GAP_STEPS
        overrides[f"{channel}_n_shocks"] = N_SHOCKS
        overrides[f"{channel}_shock_width_steps"] = SHOCK_WIDTH_STEPS
        overrides[f"{channel}_shock_interval_steps"] = SHOCK_INTERVAL_STEPS
        overrides.update(transmission_overrides_for_channel(channel))
    return SimulationConfig.level12b_frozen_reference(
        population_size=population, n_steps=N_STEPS, n_patches=n_patches, seed=seed, **overrides,
    )


def _run_one(args) -> dict:
    population, n_patches, seed, eco_points = args
    config = _build_config(population, n_patches, seed, eco_points)
    sim = Simulation(config)
    sim.run()

    response = institutional_response_series(sim.event_log, N_STEPS)
    vector = sequencing_vector(response, min_duration_steps=10)
    phenotype_raw = level13_phenotype_vector(
        sim.event_log, sim.rule_registry, n_steps=N_STEPS, current_step=N_STEPS,
        entrenchment_maturation_steps=100,
    )
    phenotype = {k: v["value"] for k, v in phenotype_raw.items()}
    s_series, z_series = s_obs_z_obs_series(sim.event_log, N_STEPS)

    # Disclosed operationalization, distinct from Stage 3's own manipulation
    # check (which verifies an "early_pulse" step-function shape --
    # meaningless for this stage's "repeated_shocks" series): here,
    # "manipulation check passed" means at least one institutional
    # response dimension registered a sustained crossing at all -- i.e.
    # the run was not degenerate/inert. Reported per-pool, never merged
    # with Stage 3's own differently-defined field of the same name.
    manipulation_check_passed = any(v is not None for v in vector.values())
    mean_resources_final_step = float(np.mean([a.resources for a in sim.agents_by_id.values()]))

    return {
        "population": population, "n_patches": n_patches, "seed": seed,
        "S_obs": float(s_series[-1]), "Z_obs": float(z_series[-1]),
        "manipulation_check_passed": manipulation_check_passed,
        "mean_resources_final_step": mean_resources_final_step,
        "phenotype_vector": phenotype,
        "n_contribution_events": len(sim.event_log.contributions),
    }


def write_scope_declaration(out_dir: str = OUT_DIR) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    scope = {
        "milestone": "level1.3b_work_package_k_stage10_ecological_control_scale_shock",
        "scale_conditions": [{"population": p, "n_patches": n} for p, n in SCALE_CONDITIONS],
        "n_seeds": N_SEEDS, "n_runs_declared": len(SCALE_CONDITIONS) * N_SEEDS,
        "pressure_history_kind": "repeated_shocks", "n_shocks_disclosed_override": N_SHOCKS,
        "representative_cell": {"entrenchment": REPRESENTATIVE_ENTRENCHMENT, "legitimacy": REPRESENTATIVE_LEGITIMACY, "stratum": REPRESENTATIVE_STRATUM},
        "n_steps": N_STEPS, "seed_base": SEED_BASE,
        "collapse_threshold": COLLAPSE_THRESHOLD,
        "collapse_criterion": "mean_resources_final_step < 0.0 -- see module docstring for why this exact threshold, chosen from Stage 3's own bimodal distribution",
        "accounting_scope_reduction": (
            "ledger reporting applies to this stage's 24 new runs plus Stage 3's own 216 archived runs "
            "(both carry mean_resources_final_step/manipulation_check_passed) -- not a re-processing of "
            "every run from every stage, disclosed in full in the module docstring"
        ),
    }
    with open(os.path.join(out_dir, "scope_declaration.json"), "w") as f:
        json.dump(scope, f, indent=2, sort_keys=True)
    return scope


def run_smoke_test(eco_points: dict) -> bool:
    try:
        record = _run_one((40, 3, SEED_BASE, eco_points))
        assert "S_obs" in record and "mean_resources_final_step" in record
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"SMOKE TEST FAILED: {exc}")
        return False


def run_all(eco_points: dict) -> list[dict]:
    records = []
    for population, n_patches in SCALE_CONDITIONS:
        for i in range(N_SEEDS):
            records.append(_run_one((population, n_patches, SEED_BASE + i, eco_points)))
    return records


def _ledger_views(records: list[dict], stratum_key: str | None) -> dict:
    """The frozen `reporting_required` views, computed on one pool of
    records (each must carry `mean_resources_final_step` and
    `manipulation_check_passed`)."""
    n_total = len(records)
    n_collapsed = sum(1 for r in records if r["mean_resources_final_step"] < COLLAPSE_THRESHOLD)
    n_eligible = sum(1 for r in records if r["manipulation_check_passed"])
    eligible = [r for r in records if r["manipulation_check_passed"]]

    pooled = {
        "n_complete_outcome_ledger": n_total,
        "n_collapsed": n_collapsed,
        "collapse_rate": n_collapsed / n_total if n_total else float("nan"),
        "n_institutionally_eligible_analysis_denominator": n_eligible,
        "eligibility_rate": n_eligible / n_total if n_total else float("nan"),
    }

    by_stratum = None
    if stratum_key is not None and all(stratum_key in r for r in records):
        by_stratum = {}
        for stratum in sorted({r[stratum_key] for r in records}):
            group = [r for r in records if r[stratum_key] == stratum]
            n_g = len(group)
            n_collapsed_g = sum(1 for r in group if r["mean_resources_final_step"] < COLLAPSE_THRESHOLD)
            by_stratum[stratum] = {"n": n_g, "n_collapsed": n_collapsed_g, "collapse_rate": n_collapsed_g / n_g if n_g else float("nan")}

    eligible_only = {
        "n": len(eligible),
        "mean_S_obs": float(np.mean([r["S_obs"] for r in eligible])) if eligible else float("nan"),
        "mean_Z_obs": float(np.mean([r["Z_obs"] for r in eligible])) if eligible else float("nan"),
        "collapse_rate_within_eligible": (
            sum(1 for r in eligible if r["mean_resources_final_step"] < COLLAPSE_THRESHOLD) / len(eligible) if eligible else float("nan")
        ),
    }

    collapse_as_outcome = {
        "collapse_rate_pooled": n_collapsed / n_total if n_total else float("nan"),
        "mean_S_obs_collapsed": float(np.mean([r["S_obs"] for r in records if r["mean_resources_final_step"] < COLLAPSE_THRESHOLD])) if n_collapsed else float("nan"),
        "mean_S_obs_sustained": float(np.mean([r["S_obs"] for r in records if r["mean_resources_final_step"] >= COLLAPSE_THRESHOLD])) if n_collapsed < n_total else float("nan"),
        "note": "collapse itself treated as the outcome variable here -- rate and its association with S_obs, not filtered out of any other view above",
    }

    return {"pooled": pooled, "by_stratum": by_stratum, "eligible_only": eligible_only, "collapse_as_outcome": collapse_as_outcome}


def scale_robustness_summary(records: list[dict]) -> dict:
    by_cell = {}
    for population, n_patches in SCALE_CONDITIONS:
        group = [r for r in records if r["population"] == population and r["n_patches"] == n_patches]
        by_cell[f"pop{population}_patches{n_patches}"] = {
            "n": len(group),
            "mean_S_obs": float(np.mean([r["S_obs"] for r in group])),
            "mean_Z_obs": float(np.mean([r["Z_obs"] for r in group])),
            "n_manipulation_check_passed": sum(1 for r in group if r["manipulation_check_passed"]),
        }
    return by_cell


def main() -> dict:
    os.makedirs(OUT_DIR, exist_ok=True)
    load_and_verify_manifest()
    eco_points = _load_ecological_points()
    scope = write_scope_declaration()
    smoke_ok = run_smoke_test(eco_points)
    if not smoke_ok:
        report = {"scope": scope, "smoke_test_passed": False, "status": "STOPPED_AFTER_SMOKE_TEST_FAILURE"}
        with open(os.path.join(OUT_DIR, "stage10_report.json"), "w") as f:
            json.dump(report, f, indent=2, sort_keys=True)
        print(json.dumps(report, indent=2, sort_keys=True))
        return report

    records = run_all(eco_points)
    with open(os.path.join(OUT_DIR, "records.json"), "w") as f:
        json.dump({"records": records}, f, indent=2, sort_keys=True, default=str)

    with open(STAGE3_RECORDS_PATH) as f:
        stage3_records = json.load(f)

    report = {
        "scope": scope, "smoke_test_passed": True,
        "scale_shock_robustness": scale_robustness_summary(records),
        "ledger_this_stage_24_runs": _ledger_views(records, stratum_key=None),
        "ledger_stage3_216_runs": _ledger_views(stage3_records, stratum_key="stratum"),
        "work_package_k_accounting_commitment": WORK_PACKAGE_K_ACCOUNTING,
    }
    with open(os.path.join(OUT_DIR, "stage10_report.json"), "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
