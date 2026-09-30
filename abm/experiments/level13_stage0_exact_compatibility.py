#!/usr/bin/env python3
"""Level 1.3, Stage 0 (task #95, preregistered in
``experiments/level13_preregistration.py``): exact compatibility
experiment, >=20 matched seeds.

Confirms ``level12b_frozen_reference()`` (every Level 1.3 flag left at
its no-op default) is byte-for-byte identical, per seed, to the same
config with ``historical_module_enabled=True`` but every OTHER Level
1.3 sub-flag still off -- the same claim ``tests/
test_level13_compatibility.py``'s ``TestExactCompatibilityWhenHistorical
ModuleDisabled`` makes at unit-test scale (Section 3 item 7), run here
at experiment scale (20 matched seeds, per this milestone's own
preregistered Stage 0 commitment) as this stage's own confirmatory
record before any Stage 1-9 run executes.

Two matched-seed comparisons, not one, both testing the SAME "the
module gate is a true no-op" claim from two different starting
presets, because a single base config's result could not rule out a
preset-specific coincidence:

1. ``level1_rule_formation_default(historical_module_enabled=False)``
   vs. the same base config with ``historical_module_enabled=True`` and
   every one of the six sub-flags (security/bargaining/coordination
   pressure, entrenchment, performance/procedural legitimacy) still
   ``False`` -- starting from Level 1.0's bare rule-formation baseline.
2. ``level12b_frozen_reference()`` (every Level 1.3 flag at its no-op
   default -- already unit-proven identical to ``level12_complete()``,
   ``tests/test_level13_compatibility.py::TestFrozenReferencePreset``)
   vs. the same preset with ``historical_module_enabled=True`` and every
   sub-flag still ``False`` -- starting from the full-featured Level
   1.2b baseline instead.

Both together are ``TestExactCompatibilityWhenHistoricalModuleDisabled``
(Section 3 item 7)'s claim, run here at experiment scale (20 matched
seeds per comparison, per this milestone's own preregistered Stage 0
commitment) as this stage's own confirmatory record before any Stage
1-9 run executes -- not a substitute for Section 3's own AST-based
structural guard, which proves the SAME claim is structurally
impossible to violate, not merely empirically unobserved in these 40
runs.

**Bug caught and fixed during this task's own development**: the first
draft of comparison 1 mistakenly paired ``level1_rule_formation_
default()`` against ``level12b_frozen_reference()`` directly (copying
Level 1.1's own Stage 2 script's comparison pattern without checking it
transfers) -- those two presets are NOT expected to be identical at
Level 1.3 (``level12b_frozen_reference()`` enables every Level 1.0-1.2b
mechanism ``level1_rule_formation_default()`` leaves off, by design),
so every one of 20 seeds correctly mismatched. This was a test-design
error, not a system bug -- caught by actually running the script rather
than assuming it would pass, and fixed by comparing each preset only
against ITS OWN historical-module-gated variant, never across presets.

Session-budget scope reduction (disclosed): 20 seeds (this milestone's
preregistered minimum, not reduced further), population 30, 3 patches,
200 steps -- matching ``STAGE_SAMPLE_SIZES["stage0_exact_
compatibility"]`` in the frozen preregistration manifest exactly.

**Second bug caught and fixed (task #109, disclosed in full in
``dev_mem/status_update.md``).** Comparison 1's two configs never set
``rng_mode`` explicitly, so they silently ran under
``level1_rule_formation_default()``'s own class default
(``legacy_single_stream``) -- violating the frozen preregistration
manifest's own ``RNG_COMMITMENTS`` ("mandatory for every Stage 0-9 run;
legacy_single_stream is never used this milestone"). Comparison 2 was
unaffected (``level12b_frozen_reference()`` already sets
``mechanism_substreams`` internally). Found while auditing every Level
1.3 stage script's ``rng_mode`` after a related transmission-flag bug
surfaced during Stage 5's own sanity check. Fixed by forcing
``rng_mode="mechanism_substreams"`` on both of comparison 1's configs;
re-run with the fix (results below are the re-run, not the original)."""

from __future__ import annotations

import json
import os

import numpy as np

from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation
from experiments.level13_preregistration import load_and_verify_manifest

OUT_DIR = "outputs/level13_stage0_exact_compatibility"
N_SEEDS = 20
POPULATION = 30
N_PATCHES = 3
N_STEPS = 200
SEED_BASE = 3_000_000


def _metrics_identical(metrics_a: list[dict], metrics_b: list[dict]) -> bool:
    """Row-by-row, field-by-field comparison with NaN treated as equal
    to NaN -- mirrors ``tests/test_level13_compatibility.py``'s own
    comparison and ``experiments/level11_stage2_compatibility_
    ablations.py``'s precedent for this exact pattern."""
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


def _run_one_comparison(cfg_a: SimulationConfig, cfg_b: SimulationConfig) -> bool:
    result_a = Simulation(cfg_a).run()
    result_b = Simulation(cfg_b).run()
    return _metrics_identical(result_a.metrics, result_b.metrics)


_EVERY_SUBFLAG_OFF = dict(
    security_pressure_enabled=False, bargaining_pressure_enabled=False, coordination_complexity_enabled=False,
    entrenchment_enabled=False, performance_legitimacy_enabled=False, procedural_legitimacy_enabled=False,
)


def run_stage0(n_seeds: int = N_SEEDS) -> dict:
    bare_preset_mismatches = []
    frozen_reference_preset_mismatches = []

    for i in range(n_seeds):
        seed = SEED_BASE + i

        # Comparison 1: bare Level 1.0 rule-formation baseline. rng_mode
        # is forced to "mechanism_substreams" (the frozen manifest's own
        # RNG_COMMITMENTS: mandatory for every Stage 0-9 run,
        # legacy_single_stream never used this milestone) -- see this
        # module's own docstring "Second bug" note (task #109) for the
        # disclosure; level1_rule_formation_default()'s own default
        # (legacy_single_stream) would otherwise silently violate that
        # commitment for this comparison only (comparison 2 was already
        # compliant, since level12b_frozen_reference() sets it).
        cfg_bare_off = SimulationConfig.level1_rule_formation_default(
            population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed,
            rng_mode="mechanism_substreams", historical_module_enabled=False,
        )
        cfg_bare_on_but_empty = SimulationConfig.level1_rule_formation_default(
            population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed,
            rng_mode="mechanism_substreams", historical_module_enabled=True, **_EVERY_SUBFLAG_OFF,
        )
        if not _run_one_comparison(cfg_bare_off, cfg_bare_on_but_empty):
            bare_preset_mismatches.append(seed)

        # Comparison 2: full-featured Level 1.2b frozen-reference baseline.
        cfg_frozen_off = SimulationConfig.level12b_frozen_reference(
            population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed,
            historical_module_enabled=False,
        )
        cfg_frozen_on_but_empty = SimulationConfig.level12b_frozen_reference(
            population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed,
            historical_module_enabled=True, **_EVERY_SUBFLAG_OFF,
        )
        if not _run_one_comparison(cfg_frozen_off, cfg_frozen_on_but_empty):
            frozen_reference_preset_mismatches.append(seed)

    return {
        "milestone": "level1.3_stage0_exact_compatibility",
        "n_seeds": n_seeds,
        "population_size": POPULATION,
        "n_patches": N_PATCHES,
        "n_steps": N_STEPS,
        "bare_level1_preset_module_gate_noop": {
            "n_mismatches": len(bare_preset_mismatches),
            "mismatched_seeds": bare_preset_mismatches,
            "byte_for_byte_identical": len(bare_preset_mismatches) == 0,
        },
        "frozen_reference_preset_module_gate_noop": {
            "n_mismatches": len(frozen_reference_preset_mismatches),
            "mismatched_seeds": frozen_reference_preset_mismatches,
            "byte_for_byte_identical": len(frozen_reference_preset_mismatches) == 0,
        },
        "overall_pass": (
            len(bare_preset_mismatches) == 0 and len(frozen_reference_preset_mismatches) == 0
        ),
    }


def write_stage0_report(out_dir: str = OUT_DIR, n_seeds: int = N_SEEDS) -> dict:
    verified = load_and_verify_manifest()  # hard stop if the frozen manifest was altered -- see its own docstring.
    report = run_stage0(n_seeds)
    report["preregistration_manifest_hash"] = verified["hash"]
    os.makedirs(out_dir, exist_ok=True)
    with open(f"{out_dir}/report.json", "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    result = write_stage0_report()
    print(f"Level 1.3 Stage 0 exact compatibility: pass={result['overall_pass']} ({result['n_seeds']} seeds)")
    print(f"report written to {OUT_DIR}/report.json")
