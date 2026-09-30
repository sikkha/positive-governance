#!/usr/bin/env python3
"""Level 1.3, Stage 9 (task #104): scale and shock robustness -- the
final experimental stage.

Per the frozen preregistration manifest's own `stage9_scale_and_shock_
robustness` commitment: 6 seeds, population conditions `[40, 80]`,
n_patches conditions `[3, 6]` -- a 2x2 scale cross, 4 cells x 6 seeds =
24 runs. The manifest's own note explains WHY this axis was excluded
from Stage 2's ecological feasibility calibration: `population_patch_
ratio_selector` was Level 1.2b's own DESIGN-TIME selector (a [0,1] draw
thresholded to pick one of two discrete population/patch combinations,
`experiments/level12b_stage_c_feasibility_map.py`'s own machinery) --
never a live `SimulationConfig` field -- used only to build an LHS
design point; it has no meaning here, where this stage instead varies
population_size and n_patches DIRECTLY per its own preregistered
conditions, exactly as the manifest already specifies.

**"Shock" robustness, folded into the same 24 runs rather than given a
separate budget.** The preregistered commitment names only a seed count
and the two scale axes, no separate shock-specific sample size -- every
run in this stage uses `"repeated_shocks"` as every channel's own
pressure-history kind (`core/historical_pressure.py`'s own
non-monotonic, irregular-shape kind) instead of the clean
`"early_pulse"` step every earlier stage used, so the SAME 24 runs test
both axes at once: does institutional response to pressure remain
qualitatively similar (1) across scale, and (2) under a structurally
different (repeated, non-monotonic) pressure shape rather than a single
clean step.

**Disclosed choice: `n_shocks=4`, not the class default of 3.** ``core/
historical_pressure.py``'s own `PressureHistorySpec.n_shocks` class
default is `3` -- a pre-existing Work Package A default, not chosen by
this stage. To avoid even the appearance of this milestone's own
Section 2 "no privileged/preferred count of three" discipline touching
an experimental design choice, this script explicitly overrides
`n_shocks=4` for every run rather than relying on that default value
(the prohibition governs outcome-count claims like the six-way decision
gate, not a shock-count parameter -- but overriding costs nothing and
removes the question entirely).

**Reuses Stage 3's own institutional-substrate config shape** (all
three Section 5 channels + their Work Package A transmission sub-flags
+ entrenchment + both legitimacy channels, on `level12b_frozen_
reference()`) -- the same fix already verified end-to-end in Stage 3/4/
5/7 -- with `security_pressure_onset_step` staggered per Stage 3's own
`_ONSET_GAP_STEPS` convention (still not a privileged-count claim, see
that module's own disclosure) so all three shock-trains are
distinguishable rather than perfectly superimposed."""

from __future__ import annotations

import hashlib
import json
import os

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.level13_phenotype import level13_phenotype_vector
from abm_governance.observer.sequencing_diagnostics import institutional_response_series, sequencing_vector
from abm_governance.observer.sz_obs import s_obs_z_obs_summary
from abm_governance.simulation import Simulation
from experiments.level13_common import transmission_overrides_for_channel
from experiments.level13_preregistration import load_and_verify_manifest

OUT_DIR = "outputs/level13_stage9_scale_and_shock_robustness"
N_SEEDS_PER_CELL = 6
N_STEPS = 500
SEED_BASE = 10_000_000
ENTRENCHMENT_MATURATION_STEPS = 100
N_SHOCKS = 4  # see module docstring's disclosed-choice note.
SHOCK_WIDTH_STEPS = 5
SHOCK_INTERVAL_STEPS = 40

POPULATION_CONDITIONS: tuple[int, ...] = (40, 80)
N_PATCHES_CONDITIONS: tuple[int, ...] = (3, 6)

_CHANNELS = ("security_pressure", "bargaining_pressure", "coordination_complexity")
_ONSET_GAP_STEPS = (0, 100, 200)


def _build_config(population_size: int, n_patches: int, seed: int) -> SimulationConfig:
    overrides: dict = dict(
        historical_module_enabled=True, entrenchment_enabled=True,
        entrenchment_maturation_steps=ENTRENCHMENT_MATURATION_STEPS,
        performance_legitimacy_enabled=True, procedural_legitimacy_enabled=True,
    )
    for channel, onset in zip(_CHANNELS, _ONSET_GAP_STEPS):
        overrides[f"{channel}_enabled"] = True
        overrides[f"{channel}_history_kind"] = "repeated_shocks"
        overrides[f"{channel}_onset_step"] = onset
        overrides[f"{channel}_n_shocks"] = N_SHOCKS
        overrides[f"{channel}_shock_width_steps"] = SHOCK_WIDTH_STEPS
        overrides[f"{channel}_shock_interval_steps"] = SHOCK_INTERVAL_STEPS
        overrides.update(transmission_overrides_for_channel(channel))
    return SimulationConfig.level12b_frozen_reference(
        population_size=population_size, n_steps=N_STEPS, n_patches=n_patches, seed=seed,
        **overrides,
    )


def _manipulation_check(sim: Simulation, population_size: int, n_patches: int) -> bool:
    """Confirms (1) the scale condition was actually applied, and (2)
    every channel's own realized series is genuinely non-constant (the
    minimum bar for "a repeated-shocks history was actually generated",
    not a claim about its downstream effect)."""
    if sim.config.population_size != population_size or len(sim.patch_system.patches) != n_patches:
        return False
    for channel in _CHANNELS:
        series = sim.historical_state[f"{channel}_series"]
        if len(set(series.tolist())) < 2:
            return False
    return True


def _run_one(population_size: int, n_patches: int, seed: int) -> dict:
    config = _build_config(population_size, n_patches, seed)
    sim = Simulation(config)
    sim.run()

    response = institutional_response_series(sim.event_log, N_STEPS)
    vector = sequencing_vector(response, min_duration_steps=10)
    phenotype = level13_phenotype_vector(
        sim.event_log, sim.rule_registry, n_steps=N_STEPS, current_step=N_STEPS,
        entrenchment_maturation_steps=ENTRENCHMENT_MATURATION_STEPS,
    )
    sz = s_obs_z_obs_summary(sim.event_log, N_STEPS)
    return {
        "seed": seed,
        "population_size": population_size,
        "n_patches": n_patches,
        "manipulation_check_passed": _manipulation_check(sim, population_size, n_patches),
        "sequencing_vector": vector,
        "phenotype_vector": {k: v["value"] for k, v in phenotype.items()},
        "s_obs": sz["S_obs"],
        "z_obs": sz["Z_obs"],
    }


def run(n_seeds_per_cell: int = N_SEEDS_PER_CELL) -> dict:
    load_and_verify_manifest()  # hard stop if the frozen manifest was altered
    records = []
    for population_size in POPULATION_CONDITIONS:
        for n_patches in N_PATCHES_CONDITIONS:
            for s in range(n_seeds_per_cell):
                records.append(_run_one(population_size, n_patches, SEED_BASE + s))

    n_manipulation_failures = sum(1 for r in records if not r["manipulation_check_passed"])

    cell_summaries = []
    for population_size in POPULATION_CONDITIONS:
        for n_patches in N_PATCHES_CONDITIONS:
            cell_records = [r for r in records if r["population_size"] == population_size and r["n_patches"] == n_patches]
            n = len(cell_records)
            cell_summaries.append({
                "population_size": population_size, "n_patches": n_patches, "n_seeds": n,
                "mean_s_obs": sum(r["s_obs"] for r in cell_records) / n if n else float("nan"),
                "mean_z_obs": sum(r["z_obs"] for r in cell_records) / n if n else float("nan"),
                "mean_entrenchment": sum(r["phenotype_vector"]["entrenchment"] for r in cell_records) / n if n else float("nan"),
            })

    return {
        "milestone": "level1.3_stage9_scale_and_shock_robustness",
        "n_seeds_per_cell": n_seeds_per_cell,
        "n_cells": len(POPULATION_CONDITIONS) * len(N_PATCHES_CONDITIONS),
        "n_runs": len(records),
        "n_steps": N_STEPS,
        "population_conditions": list(POPULATION_CONDITIONS),
        "n_patches_conditions": list(N_PATCHES_CONDITIONS),
        "pressure_history_kind": "repeated_shocks",
        "n_shocks": N_SHOCKS,
        "all_manipulation_checks_passed": n_manipulation_failures == 0,
        "n_manipulation_failures": n_manipulation_failures,
        "cell_summaries": cell_summaries,
        "records": records,
        "decision_gate_note": (
            "no six-way decision-gate verdict is rendered here -- Section 23's classification "
            "(task #108) synthesizes this stage alongside Stage 6/7/8's own evidence"
        ),
    }


def report_hash(report: dict) -> str:
    payload = json.dumps(report, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_report(out_dir: str = OUT_DIR, n_seeds_per_cell: int = N_SEEDS_PER_CELL) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    report = run(n_seeds_per_cell)
    digest = report_hash(report)
    report["report_hash"] = digest
    with open(f"{out_dir}/records.json", "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    result = write_report()
    print(f"Level 1.3 Stage 9: {result['n_runs']} runs across {result['n_cells']} scale cells, "
          f"manipulation checks passed={result['all_manipulation_checks_passed']}")
    for cell in result["cell_summaries"]:
        print(f"  pop={cell['population_size']} patches={cell['n_patches']}: "
              f"S_obs={cell['mean_s_obs']:.3f} Z_obs={cell['mean_z_obs']:.3f}")
    print(f"report written to {OUT_DIR}/records.json")
