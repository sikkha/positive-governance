#!/usr/bin/env python3
"""Level 1.3, Stage 3 (task #98): sequencing x entrenchment factorial.

The first stage that actually probes this milestone's core scientific
question: does the ORDER in which security/bargaining/coordination
pressure arrives produce reproducible institutional differentiation,
and does entrenchment (Work Package C) change that?

**Design.** Crosses:

- **Pressure-onset ORDER**: all 3! = 6 permutations of which of the
  three Section 5 pressure channels (security, bargaining, coordination
  complexity) activates first/second/third, each channel using the
  ``"early_pulse"`` history kind with ``duration_steps=None`` (a clean,
  permanent low-to-high step at its own ``onset_step``, staying high for
  the remainder of the run -- see ``core/historical_pressure.py``'s own
  ``generate_pressure_series``) and onset steps ``{0, 150, 300}``
  assigned according to that permutation, leaving 200 steps after the
  last-activating channel for institutional response to unfold. Six
  orderings is simply Section 5's own pre-existing three-channel design
  enumerated combinatorially -- NOT a claim that three is a privileged
  or expected outcome COUNT (Section 2's "the number three" prohibition
  governs the decision gate's own outcome labeling, preregistered in
  ``experiments/level13_preregistration.py::DECISION_GATE_OUTCOMES``,
  not the mundane fact that this model has three pressure channels by
  Work Package A's own already-built design).
- **``entrenchment_enabled``**: on/off (Work Package C).

12 cells x 6 seeds/cell = 72 runs (matching the frozen preregistration
manifest's ``stage3_sequencing_x_entrenchment_factorial`` commitment:
population 40, 3 patches, 500 steps).

**Manipulation check, not yet an outcome claim.** Every run's OWN
realized ``historical_state`` series is checked against its intended
onset order (deterministic given config for the ``"early_pulse"`` kind
-- no RNG involved in the pressure series itself) -- this confirms the
experimental manipulation was correctly APPLIED, not that it produced
any particular institutional effect. Whether sequencing/entrenchment
actually produces differentiation is a Stage 6-8 discovery-pipeline
question, deliberately deferred -- this script only runs the factorial
and records each run's Work Package B sequencing vector and Work
Package H phenotype vector as raw material for that later analysis
(``outputs/level13_stage3_sequencing_entrenchment_factorial/
records.json`` is exactly the kind of pool Stage 6, task #101, is
preregistered to consume alongside Stage 4-5's own runs).

**Two bugs found and fixed (task #109, disclosed in full in
``dev_mem/status_update.md``), both caught before any Stage 6-8
discovery analysis ever read this stage's output.**

1. **Transmission sub-flags never set.** This script's first draft set
   only each channel's master ``*_enabled`` flag, never Work Package
   A's own per-channel transmission sub-flags (``experiments/
   level13_common.py``'s ``transmission_overrides_for_channel``) --
   those default OFF, so pressure never touched agent behavior.
2. **Wrong substrate preset.** Even with the sub-flags fixed, the
   first draft built on bare ``level1_rule_formation_default()``
   (Level 1.1's delegation/discretion/accountability/contribution/
   interpatch-coordination mechanisms all off by that preset's own
   design) -- Work Package A's transmission channels nudge quantities
   (delegate task-success probability, contribution compliance,
   coordination-proposal probability) that only exist when those Level
   1.1 mechanisms are active, so there was still nothing for pressure
   to act on. This also meant ``rng_mode`` was silently
   ``legacy_single_stream``, violating the frozen manifest's own
   ``RNG_COMMITMENTS`` ("mandatory for every Stage 0-9 run") and
   undermining the "attributable to the manipulation alone" causal
   logic every matched-seed comparison in this milestone relies on.

Both were caught by an empirical sanity check (byte-identical base
vs. counterfactual event logs) run against the Stage 5 script before
its own real execution, then traced back to Stage 3/4's already-
completed runs by auditing every Level 1.3 stage script's config
construction. Fixed by switching to ``level12b_frozen_reference()``
(brings ``rng_mode="mechanism_substreams"`` and the full Level 1.1/1.2b
institutional substrate) plus the transmission sub-flags. The original
(bugged) 72-run output was archived to ``outputs/level13_stage3_
sequencing_entrenchment_factorial/records_pre_transmission_fix.json``
for the audit trail before this stage was re-run with both fixes."""

from __future__ import annotations

import hashlib
import itertools
import json
import os

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.level13_phenotype import level13_phenotype_vector
from abm_governance.observer.sequencing_diagnostics import institutional_response_series, sequencing_vector
from abm_governance.simulation import Simulation
from experiments.level13_common import transmission_overrides_for_channel
from experiments.level13_preregistration import load_and_verify_manifest

OUT_DIR = "outputs/level13_stage3_sequencing_entrenchment_factorial"
N_SEEDS_PER_CELL = 6
N_STEPS = 500
POPULATION = 40
N_PATCHES = 3
SEED_BASE = 5_000_000
ENTRENCHMENT_MATURATION_STEPS = 100

_CHANNELS = ("security_pressure", "bargaining_pressure", "coordination_complexity")
_ONSET_GAP_STEPS = (0, 150, 300)

#: All 3! = 6 orderings, named by which channel goes first/second/third
#: -- see module docstring for the "not a privileged count" disclosure.
ORDERINGS: dict[str, tuple[str, ...]] = {
    "_".join(perm): perm for perm in itertools.permutations(_CHANNELS)
}


def _build_config(order_name: str, entrenchment_enabled: bool, seed: int) -> SimulationConfig:
    order = ORDERINGS[order_name]
    overrides: dict = dict(
        historical_module_enabled=True, entrenchment_enabled=entrenchment_enabled,
        entrenchment_maturation_steps=ENTRENCHMENT_MATURATION_STEPS,
    )
    for channel, onset in zip(order, _ONSET_GAP_STEPS):
        overrides[f"{channel}_enabled"] = True
        overrides[f"{channel}_history_kind"] = "early_pulse"
        overrides[f"{channel}_onset_step"] = onset
        overrides[f"{channel}_duration_steps"] = None
        overrides.update(transmission_overrides_for_channel(channel))
    # level12b_frozen_reference (not the bare level1_rule_formation_
    # default() the first draft used) so delegation/discretion/
    # accountability/contribution/interpatch-coordination -- the
    # institutional substrate Work Package A's transmission channels
    # actually act on -- are active, and rng_mode="mechanism_substreams"
    # is set (the frozen manifest's own RNG_COMMITMENTS). See module
    # docstring's "Bug found and fixed" note (task #109).
    return SimulationConfig.level12b_frozen_reference(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed,
        **overrides,
    )


def _manipulation_check(sim: Simulation, order_name: str) -> bool:
    """Confirms each channel's OWN realized series is at ``low_level``
    strictly before its intended onset and at ``high_level`` from onset
    through the end of the run -- the manipulation as applied, not any
    downstream effect."""
    order = ORDERINGS[order_name]
    for channel, onset in zip(order, _ONSET_GAP_STEPS):
        series = sim.historical_state[f"{channel}_series"]
        if onset > 0 and not all(v == series[0] for v in series[:onset]):
            return False
        if not all(v == series[onset] for v in series[onset:]):
            return False
        if onset > 0 and series[0] == series[onset]:
            return False  # low_level and high_level must actually differ for this to be a real check.
    return True


def _run_one(order_name: str, entrenchment_enabled: bool, seed: int) -> dict:
    config = _build_config(order_name, entrenchment_enabled, seed)
    sim = Simulation(config)
    sim.run()

    response = institutional_response_series(sim.event_log, N_STEPS)
    vector = sequencing_vector(response, min_duration_steps=10)
    phenotype = level13_phenotype_vector(
        sim.event_log, sim.rule_registry, n_steps=N_STEPS, current_step=N_STEPS,
        entrenchment_maturation_steps=ENTRENCHMENT_MATURATION_STEPS,
    )
    return {
        "seed": seed,
        "order_name": order_name,
        "entrenchment_enabled": entrenchment_enabled,
        "manipulation_check_passed": _manipulation_check(sim, order_name),
        "sequencing_vector": vector,
        "phenotype_vector": {k: v["value"] for k, v in phenotype.items()},
    }


def run(n_seeds_per_cell: int = N_SEEDS_PER_CELL) -> dict:
    load_and_verify_manifest()  # hard stop if the frozen manifest was altered
    records = []
    for order_name in ORDERINGS:
        for entrenchment_enabled in (False, True):
            for s in range(n_seeds_per_cell):
                records.append(_run_one(order_name, entrenchment_enabled, SEED_BASE + s))

    n_manipulation_failures = sum(1 for r in records if not r["manipulation_check_passed"])
    report = {
        "milestone": "level1.3_stage3_sequencing_entrenchment_factorial",
        "n_orderings": len(ORDERINGS),
        "n_seeds_per_cell": n_seeds_per_cell,
        "n_runs": len(records),
        "population_size": POPULATION,
        "n_patches": N_PATCHES,
        "n_steps": N_STEPS,
        "n_manipulation_check_failures": n_manipulation_failures,
        "all_manipulation_checks_passed": n_manipulation_failures == 0,
        "records": records,
    }
    return report


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
    print(f"Level 1.3 Stage 3: {result['n_runs']} runs, manipulation checks passed={result['all_manipulation_checks_passed']}")
    print(f"report written to {OUT_DIR}/records.json")
