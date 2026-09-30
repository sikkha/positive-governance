#!/usr/bin/env python3
"""Level 1.3, Stage 1 (task #96): unit/mechanism activation tests.

Confirms each of the 7 master Level 1.3 config flags actually produces
an observable effect when enabled, and produces NONE of that effect
when left at its Level-1.2b-compatible default (``False``) -- mirrors
``experiments/level12_stage1_activation.py``'s own established
"nonzero-when-on, zero-when-off" pattern, adapted to what each Level
1.3 mechanism actually makes observable:

- ``security_pressure_enabled``/``bargaining_pressure_enabled``/
  ``coordination_complexity_enabled`` (Section 5): each channel's own
  pressure SERIES exists (``historical_state[state_key]`` populated,
  finite, length ``n_steps``) when its flag is on, and ``historical_
  state`` is empty (baseline has the module itself off entirely, so it
  is ``None``) when off. This tests Section 5's own activation claim
  only.

- **Disclosed scope note**: Work Package A's own downstream
  TRANSMISSION sub-flags (``security_pressure_returns_to_delegation_
  enabled``, ``security_pressure_admin_capacity_demand_enabled``, and
  their bargaining-/coordination-complexity-pressure counterparts) are
  a SECOND, finer-grained activation layer this stage does not test --
  a pressure series can exist (Section 5 flag on) with zero behavioral
  consequence unless its own transmission sub-flag is ALSO on. This
  stage's preregistered scope is the 7 master flags in
  ``experiments/level13_preregistration.py::MECHANISM_ACTIVATION_
  FLAGS``; the transmission sub-flags are exercised functionally by
  ``tests/test_level13_pressure_transmission.py`` (Work Package A's own
  exact-activation unit tests), not at this stage's experiment scale.

- ``entrenchment_enabled`` (Work Package C): a MATCHED-SEED comparison
  (not a standalone nonzero check, since entrenchment modifies an
  EXISTING counter's magnitude rather than creating a new event type)
  -- the mean ``RuleAmendmentEvent.effective_amendment_threshold``
  across all amendment events, entrenchment-on vs. the SAME seeds'
  baseline (entrenchment off), must be strictly higher on at least one
  seed with amendment activity (entrenchment only ever RAISES the
  effective threshold, per ``core/entrenchment.py``'s own design; it
  never lowers it).

- ``performance_legitimacy_enabled``/``procedural_legitimacy_enabled``
  (Work Package D): ``len(event_log.legitimacy_events) > 0`` when on;
  exactly ``0`` when off (matches ``level13_baseline``, since both
  legitimacy flags are off there by construction).

Session-budget scope reduction (disclosed, matching the frozen
preregistration manifest's ``stage1_mechanism_activation`` commitment
exactly): 8 seeds per condition, population 40, 3 patches, 300 steps.

**Bug caught and fixed (task #109, disclosed in full in
``dev_mem/status_update.md``).** ``_BASE`` never set ``rng_mode``
explicitly, so this stage's first-draft 56-run execution silently ran
under ``level1_rule_formation_default()``'s own class default
(``legacy_single_stream``) -- violating the frozen preregistration
manifest's own ``RNG_COMMITMENTS`` ("mandatory for every Stage 0-9 run;
legacy_single_stream is never used this milestone"). This stage's own
claims (pressure-series presence/well-formedness, entrenchment
threshold elevation, legitimacy event counts) do not depend on
cross-mechanism RNG-stream isolation the way Stage 3/5's causal
comparisons do, so the ORIGINAL result was very likely still correct
in substance -- but re-run anyway for full manifest compliance and
consistency with every other stage, rather than leaving one stage's
own record under a mode the manifest says is never used."""

from __future__ import annotations

import json
import math
import os

from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation
from experiments.level13_preregistration import load_and_verify_manifest

OUT_DIR = "outputs/level13_stage1_activation"
N_SEEDS = 8
N_STEPS = 300
POPULATION = 40
N_PATCHES = 3
SEED_BASE = 4_000_000

_BASE = dict(
    population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES,
    monitoring_mode="voluntary", sanction_mode="voluntary",
    rng_mode="mechanism_substreams",
)

CONDITIONS: dict[str, dict] = {
    "level13_baseline": dict(historical_module_enabled=False),
    "level13_security_pressure_only": dict(historical_module_enabled=True, security_pressure_enabled=True),
    "level13_bargaining_pressure_only": dict(historical_module_enabled=True, bargaining_pressure_enabled=True),
    "level13_coordination_complexity_only": dict(historical_module_enabled=True, coordination_complexity_enabled=True),
    "level13_entrenchment_only": dict(historical_module_enabled=True, entrenchment_enabled=True),
    "level13_performance_legitimacy_only": dict(historical_module_enabled=True, performance_legitimacy_enabled=True),
    "level13_procedural_legitimacy_only": dict(historical_module_enabled=True, procedural_legitimacy_enabled=True),
}

_PRESSURE_STATE_KEY = {
    "level13_security_pressure_only": "security_pressure_series",
    "level13_bargaining_pressure_only": "bargaining_pressure_series",
    "level13_coordination_complexity_only": "coordination_complexity_series",
}


def _run_one(name: str, overrides: dict, seed: int) -> dict:
    config = SimulationConfig.level1_rule_formation_default(seed=seed, **_BASE, **overrides)
    sim = Simulation(config)
    sim.run()

    result: dict = {"seed": seed}

    if name in _PRESSURE_STATE_KEY:
        state_key = _PRESSURE_STATE_KEY[name]
        series = None if sim.historical_state is None else sim.historical_state.get(state_key)
        result["pressure_series_present"] = series is not None
        result["pressure_series_well_formed"] = (
            series is not None and len(series) == N_STEPS and all(math.isfinite(v) for v in series)
        )

    if name == "level13_baseline":
        result["any_pressure_series_present"] = sim.historical_state is not None and bool(sim.historical_state)

    if name in ("level13_baseline", "level13_entrenchment_only"):
        result["amendment_thresholds"] = [ev.effective_amendment_threshold for ev in sim.event_log.rule_amendments]

    if name in ("level13_performance_legitimacy_only", "level13_procedural_legitimacy_only", "level13_baseline"):
        result["n_legitimacy_events"] = len(sim.event_log.legitimacy_events)

    return result


def run() -> dict:
    load_and_verify_manifest()  # hard stop if the frozen manifest was altered
    report: dict = {"n_seeds": N_SEEDS, "n_steps": N_STEPS, "population": POPULATION, "n_patches": N_PATCHES, "conditions": {}}

    all_seed_results: dict[str, list[dict]] = {}
    for name, overrides in CONDITIONS.items():
        all_seed_results[name] = [_run_one(name, overrides, SEED_BASE + s) for s in range(N_SEEDS)]

    baseline_results = all_seed_results["level13_baseline"]

    for name, seed_results in all_seed_results.items():
        checks: dict[str, bool] = {}

        if name == "level13_baseline":
            checks["no_pressure_state_generated"] = not any(r["any_pressure_series_present"] for r in seed_results)
            checks["no_legitimacy_events"] = all(r["n_legitimacy_events"] == 0 for r in seed_results)
        elif name in _PRESSURE_STATE_KEY:
            checks["pressure_series_present_every_seed"] = all(r["pressure_series_present"] for r in seed_results)
            checks["pressure_series_well_formed_every_seed"] = all(r["pressure_series_well_formed"] for r in seed_results)
        elif name == "level13_entrenchment_only":
            elevated_on_at_least_one_seed = False
            for on_result, off_result in zip(seed_results, baseline_results):
                on_vals, off_vals = on_result["amendment_thresholds"], off_result["amendment_thresholds"]
                if on_vals and off_vals:
                    on_mean = sum(on_vals) / len(on_vals)
                    off_mean = sum(off_vals) / len(off_vals)
                    if on_mean > off_mean:
                        elevated_on_at_least_one_seed = True
            checks["elevated_effective_threshold_vs_matched_baseline_at_least_one_seed"] = elevated_on_at_least_one_seed
            checks["at_least_one_amendment_across_seeds"] = sum(len(r["amendment_thresholds"]) for r in seed_results) > 0
        elif name in ("level13_performance_legitimacy_only", "level13_procedural_legitimacy_only"):
            checks["legitimacy_events_present_every_seed"] = all(r["n_legitimacy_events"] > 0 for r in seed_results)

        report["conditions"][name] = {"checks": checks, "per_seed": seed_results}
        print(f"{name}: checks={checks}", flush=True)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(f"{OUT_DIR}/stage1_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
