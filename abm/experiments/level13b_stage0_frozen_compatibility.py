#!/usr/bin/env python3
"""Level 1.3b, Stage 0 (task #115, Section 4/17): frozen compatibility
against BOTH required references -- Level 1.2b with every historical
mechanism off, and the corrected (post-task-#109-fix) Level 1.3
configuration -- plus a third check this stage's own development
surfaced was necessary: genuine cross-process determinism.

**Comparison A (Level 1.2b historical-off): >=20 matched seeds,
byte-for-byte event-log/metrics identity, within one process.** Reruns
Level 1.3's own Stage 0 claim (the historical-module gate is a true
no-op) under Level 1.3b's current codebase.

**A major, previously-undisclosed finding this stage's own development
surfaced, unrelated to Work Package B**: attempting Comparison B (below)
first exposed that a FRESH run of an archived Stage 3 config/seed did
NOT always reproduce the archived phenotype -- on MANY more fields than
Work Package B's own disclosed `Z_obs`/`seq_bargaining_participation`
change could explain (e.g. `S_obs` itself, `entrenchment`). Tracing this
(RNG-call-level instrumentation across separate process launches) found
a genuine, previously-undisclosed CROSS-PROCESS reproducibility bug,
introduced at Level 1.2 and present through Level 1.3:
`rules/transmission.py::TRANSMISSIBLE_COMPONENT_NAMES` was built by
iterating a frozenset UNION of string component names directly -- Python
randomizes `str` hashing per process (`PYTHONHASHSEED`) by default, so
this constant's element ORDER varied across separate process launches
(stable within one process, different across processes), and
`institution_transmission_round`'s `rng.choice(TRANSMISSIBLE_COMPONENT_
NAMES)` silently picked a DIFFERENT component depending on which name
sat at the RNG-drawn index that process happened to have. Confirmed
empirically: 15 separate process launches of the identical seeded
`level12b_frozen_reference()` config gave 15 DIFFERENT contribution-
event counts (range 412-425) before the fix; exactly identical counts
in all 15 after it (`sorted(...)` added to the constant's construction,
`rules/transmission.py`). Full account: `docs/level1.3b_inference_
audit.md` and `tests/test_level13b_cross_process_reproducibility.py`
(the new standing regression guard, launching genuinely separate
subprocesses -- the only test methodology that COULD catch this class
of bug, since every prior "matched-seed" check in this codebase, this
stage's own Comparison A included, compares configs built and run
within a single process, sharing one hash seed by construction, and was
therefore structurally blind to this).

**Comparison B (corrected Level 1.3, reproduction against the archive):
now DESCRIPTIVE, not pass/fail.** Because the fix above changes real
simulation behavior (in institution-component transmission), a fresh
run under the FIXED codebase is no longer expected to bit-reproduce
Level 1.3's own archived Stage 3 output -- those archived numbers were
never actually canonical/reproducible to begin with (an artifact of
whatever unfixed hash seed that recording process happened to have),
so requiring a match against them would be requiring reproduction of a
bug, not of a result. This comparison is kept only as a descriptive
record of HOW MUCH the fix changes typical output (magnitude/direction
of change across all 72 archived records), not as a compatibility gate.

**Comparison C (the real frozen-compatibility proof, post-fix): >=15
genuinely separate process launches of the same seed/config, required
to agree exactly.** This is the check that actually matters going
forward -- it is what Comparison A could never test (single-process by
construction) and what Comparison B could no longer test (comparing
against a pre-fix archive). `overall_pass` is gated on Comparisons A
and C only."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.level13_phenotype import level13_phenotype_vector
from abm_governance.observer.sequencing_diagnostics import institutional_response_series, sequencing_vector
from abm_governance.simulation import Simulation
from experiments.level13_stage3_sequencing_entrenchment_factorial import (
    ENTRENCHMENT_MATURATION_STEPS,
    N_STEPS as STAGE3_N_STEPS,
    _build_config,
)

OUT_DIR = "outputs/level13b_stage0_frozen_compatibility"
ARCHIVED_STAGE3_RECORDS_PATH = "outputs/level13_stage3_sequencing_entrenchment_factorial/records.json"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

N_SEEDS_COMPARISON_A = 20
POPULATION_A = 30
N_PATCHES_A = 3
N_STEPS_A = 200
SEED_BASE_A = 9_000_000

N_LAUNCHES_COMPARISON_C = 15
COMPARISON_C_SEED = 777

_EVERY_SUBFLAG_OFF = dict(
    security_pressure_enabled=False, bargaining_pressure_enabled=False, coordination_complexity_enabled=False,
    entrenchment_enabled=False, performance_legitimacy_enabled=False, procedural_legitimacy_enabled=False,
)

_FIELDS_EXPECTED_TO_CHANGE = {"Z_obs", "seq_bargaining_participation"}

_COMPARISON_C_SCRIPT = (
    "from abm_governance.core.config import SimulationConfig\n"
    "from abm_governance.simulation import Simulation\n"
    f"cfg = SimulationConfig.level12b_frozen_reference(population_size=30, n_steps=200, n_patches=3, seed={COMPARISON_C_SEED})\n"
    "sim = Simulation(cfg)\n"
    "sim.run()\n"
    "print(len(sim.event_log.contributions), len(sim.event_log.rule_adoptions), "
    "len(sim.event_log.coordination_links), len(sim.event_log.monitorings), "
    "len(sim.event_log.delegate_appointments), len(sim.event_log.audits))\n"
)


def _metrics_identical(metrics_a: list[dict], metrics_b: list[dict]) -> bool:
    if len(metrics_a) != len(metrics_b):
        return False
    for row_a, row_b in zip(metrics_a, metrics_b):
        if row_a.keys() != row_b.keys():
            return False
        for key in row_a:
            v1, v2 = row_a[key], row_b[key]
            if isinstance(v1, float) and np.isnan(v1):
                if not (isinstance(v2, float) and np.isnan(v2)):
                    return False
            elif v1 != v2:
                return False
    return True


def run_comparison_a(n_seeds: int = N_SEEDS_COMPARISON_A) -> dict:
    mismatches = []
    for i in range(n_seeds):
        seed = SEED_BASE_A + i
        cfg_off = SimulationConfig.level12b_frozen_reference(
            population_size=POPULATION_A, n_steps=N_STEPS_A, n_patches=N_PATCHES_A, seed=seed,
            historical_module_enabled=False,
        )
        cfg_on_but_empty = SimulationConfig.level12b_frozen_reference(
            population_size=POPULATION_A, n_steps=N_STEPS_A, n_patches=N_PATCHES_A, seed=seed,
            historical_module_enabled=True, **_EVERY_SUBFLAG_OFF,
        )
        result_off = Simulation(cfg_off).run()
        result_on = Simulation(cfg_on_but_empty).run()
        if not _metrics_identical(result_off.metrics, result_on.metrics):
            mismatches.append(seed)
    return {
        "n_seeds": n_seeds,
        "n_mismatches": len(mismatches),
        "mismatched_seeds": mismatches,
        "byte_for_byte_identical": len(mismatches) == 0,
    }


def run_comparison_c(n_launches: int = N_LAUNCHES_COMPARISON_C) -> dict:
    """The real post-fix frozen-compatibility proof: N genuinely
    separate `python3 -c ...` process launches of the identical seeded
    config, required to agree exactly. Each launch gets its own,
    independently randomized `PYTHONHASHSEED` (never pinned here) --
    the point is proving the codebase no longer DEPENDS on that being
    fixed, not hiding the dependency behind an environment variable."""
    outputs = []
    for _ in range(n_launches):
        result = subprocess.run(
            [sys.executable, "-c", _COMPARISON_C_SCRIPT],
            capture_output=True, text=True, timeout=180, check=True, cwd=REPO_ROOT,
        )
        outputs.append(result.stdout.strip())
    distinct = sorted(set(outputs))
    return {
        "n_launches": n_launches,
        "seed": COMPARISON_C_SEED,
        "distinct_outputs": distinct,
        "n_distinct_outputs": len(distinct),
        "all_launches_identical": len(distinct) == 1,
    }


def _values_equal(v1, v2) -> bool:
    if isinstance(v1, float) and isinstance(v2, float):
        return v1 == v2 or (np.isnan(v1) and np.isnan(v2))
    return v1 == v2


def run_comparison_b_descriptive() -> dict:
    """Descriptive only (see module docstring) -- NOT a pass/fail gate."""
    with open(ARCHIVED_STAGE3_RECORDS_PATH) as f:
        archived = json.load(f)["records"]

    n_fields_changed_histogram: dict[str, int] = {}
    z_obs_deltas = []

    for record in archived:
        seed = record["seed"]
        order_name = record["order_name"]
        entrenchment_enabled = record["entrenchment_enabled"]
        config = _build_config(order_name, entrenchment_enabled, seed)
        sim = Simulation(config)
        sim.run()

        new_phenotype_raw = level13_phenotype_vector(
            sim.event_log, sim.rule_registry, n_steps=STAGE3_N_STEPS, current_step=STAGE3_N_STEPS,
            entrenchment_maturation_steps=ENTRENCHMENT_MATURATION_STEPS,
        )
        new_phenotype = {k: v["value"] for k, v in new_phenotype_raw.items()}
        old_phenotype = record["phenotype_vector"]

        changed_fields = [k for k in old_phenotype if not _values_equal(old_phenotype[k], new_phenotype[k])]
        for k in changed_fields:
            n_fields_changed_histogram[k] = n_fields_changed_histogram.get(k, 0) + 1
        z_obs_deltas.append(new_phenotype["Z_obs"] - old_phenotype["Z_obs"])

    return {
        "n_runs_reproduced": len(archived),
        "field_change_counts_out_of_72": n_fields_changed_histogram,
        "mean_z_obs_delta": float(np.mean(z_obs_deltas)),
        "note": (
            "descriptive only, not a pass/fail gate -- see module docstring. Many fields beyond "
            "Z_obs/seq_bargaining_participation now differ from the archive because the "
            "TRANSMISSIBLE_COMPONENT_NAMES cross-process-determinism fix legitimately changes "
            "institution-transmission outcomes; the archive was never a canonical/reproducible "
            "reference to begin with."
        ),
    }


def main() -> dict:
    os.makedirs(OUT_DIR, exist_ok=True)
    comparison_a = run_comparison_a()
    comparison_c = run_comparison_c()
    comparison_b = run_comparison_b_descriptive()

    report = {
        "milestone": "level1.3b_stage0_frozen_compatibility",
        "comparison_a_level12b_historical_off": comparison_a,
        "comparison_b_corrected_level13_reproduction_DESCRIPTIVE_ONLY": comparison_b,
        "comparison_c_cross_process_determinism_post_fix": comparison_c,
        "overall_pass": comparison_a["byte_for_byte_identical"] and comparison_c["all_launches_identical"],
        "major_finding": (
            "A genuine, previously-undisclosed cross-process reproducibility bug (rules/transmission.py "
            "TRANSMISSIBLE_COMPONENT_NAMES, introduced at Level 1.2) was found and fixed this stage. "
            "Comparison A and C are the frozen-compatibility gate; Comparison B is retained only as a "
            "descriptive record of the fix's magnitude against the (now non-canonical) Level 1.3 archive."
        ),
    }
    with open(os.path.join(OUT_DIR, "stage0_report.json"), "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
