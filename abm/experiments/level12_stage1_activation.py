#!/usr/bin/env python3
"""Level 1.2, Stage 1: mechanism activation.

Confirms each of the five Work Package B/C/D/F generative mechanisms
actually fires (produces > 0 of its own defining events) when its
governing config flag is enabled, and produces *zero* of those events
when left at its Level-1.1b-compatible default -- the first, most basic
experimental claim this milestone can make, before any comparison or
search. Mirrors ``experiments/level11_stage1_activation.py``'s own
established pattern exactly.

``institution_extinctions`` is deliberately excluded from the
zero/nonzero mechanism-activation checks below: Work Package A's
institution-lifecycle bookkeeping (``rules/institution.py::
institution_lifecycle_round``) is unconditional diffing of already-
existing rule dissolution against the institution registry, not gated
by any of the five flags this stage tests -- it can fire at baseline
whenever a rule dissolves under ordinary Level 1.0/1.1 mechanics, which
is expected and correct, not a mechanism-activation failure.

**Finding surfaced by this stage's own first run, documented rather
than papered over**: ``n_membership_exits`` is NOT gated by
``membership_exit_enabled`` alone. ``rules/migration.py::
migration_round`` emits a ``MembershipExitEvent(..., reason="migration")``
as a *structural* consequence of an agent physically relocating (leaving
the old patch's rule membership is mechanical, not a separate decision)
-- distinct from ``membership_exit_round``'s own
``membership_exit_enabled``-gated ``reason="dissatisfaction"`` events.
So ``level12_migration_only`` (migration on, membership-exit mechanism
off) correctly produces nonzero ``n_membership_exits`` -- this is
migration's own structural consequence, not a membership-exit-mechanism
activation leak. ``EXPECTED_NONZERO``/``EXPECTED_ZERO`` below are
written to reflect this real gating boundary rather than the naive
one-flag-per-counter assumption.

Session-budget scope reduction (disclosed, matching Stage 0's frozen
commitment in ``outputs/level12_stage0_preregistration/manifest.json``):
8 seeds per condition, population 40, 4 patches, 350 steps."""

from __future__ import annotations

import json

from abm_governance.core.config import SimulationConfig
from experiments.level12_common import ensure_dir, run_and_summarize
from experiments.level12_preregistration import load_and_verify_manifest

OUT_DIR = "outputs/level12_stage1_activation"
N_SEEDS = 8
N_STEPS = 350
POPULATION = 40
N_PATCHES = 4

#: Shared base -- interpatch coordination active (a prerequisite for
#: observation/transmission/scaling) and rule formation active, every
#: Level 1.2 mechanism flag left at its Level-1.1b-compatible default
#: (False) unless a condition below explicitly adds it.
_BASE = dict(
    population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES,
    interpatch_coordination_enabled=True, coordination_proposal_probability=0.3,
)

CONDITIONS = {
    "level12_baseline": lambda seed: SimulationConfig.level1_rule_formation_default(seed=seed, **_BASE),
    "level12_observation_only": lambda seed: SimulationConfig.level1_rule_formation_default(
        seed=seed, institutional_observation_enabled=True, **_BASE,
    ),
    "level12_transmission_only": lambda seed: SimulationConfig.level1_rule_formation_default(
        seed=seed, institutional_transmission_enabled=True, **_BASE,
    ),
    # Migration structurally produces MembershipExitEvent(reason="migration")
    # as a mechanical consequence of relocating -- see module docstring.
    "level12_migration_only": lambda seed: SimulationConfig.level1_rule_formation_default(
        seed=seed, migration_enabled=True, **_BASE,
    ),
    "level12_membership_exit_only": lambda seed: SimulationConfig.level1_rule_formation_default(
        seed=seed, membership_exit_enabled=True, **_BASE,
    ),
    "level12_scaling_only": lambda seed: SimulationConfig.level1_rule_formation_default(
        seed=seed, institutional_scaling_enabled=True, **_BASE,
    ),
    "level12_complete": lambda seed: SimulationConfig.level1_rule_formation_default(
        seed=seed, institutional_observation_enabled=True, institutional_transmission_enabled=True,
        migration_enabled=True, membership_exit_enabled=True, institutional_scaling_enabled=True, **_BASE,
    ),
}

#: Which event counters each condition is expected to be non-zero for
#: (across at least one of the 8 seeds -- never "every seed").
EXPECTED_NONZERO = {
    "level12_baseline": [],
    "level12_observation_only": ["n_local_institution_observations"],
    "level12_transmission_only": ["n_institution_component_transmissions"],
    # n_membership_exits included: migration structurally produces
    # MembershipExitEvent(reason="migration") -- see module docstring.
    "level12_migration_only": ["n_migrations", "n_membership_exits"],
    "level12_membership_exit_only": ["n_membership_exits"],
    "level12_scaling_only": ["n_coordination_scale_changes"],
    "level12_complete": [
        "n_local_institution_observations", "n_institution_component_transmissions",
        "n_migrations", "n_membership_exits", "n_coordination_scale_changes",
    ],
}

#: Counters that must be exactly zero for whichever mechanisms are OFF
#: in a given condition (``institution_extinctions`` excluded -- see
#: module docstring).
_ALL_GATED = (
    "n_local_institution_observations", "n_institution_component_transmissions",
    "n_migrations", "n_membership_exits", "n_coordination_scale_changes",
)
EXPECTED_ZERO = {
    name: [c for c in _ALL_GATED if c not in EXPECTED_NONZERO[name]]
    for name in CONDITIONS
}


def run() -> dict:
    ensure_dir(OUT_DIR)
    load_and_verify_manifest()  # hard stop if Stage 0's frozen manifest was altered
    report = {"n_seeds": N_SEEDS, "n_steps": N_STEPS, "population": POPULATION, "n_patches": N_PATCHES, "conditions": {}}
    for name, builder in CONDITIONS.items():
        seed_results = []
        for seed in range(N_SEEDS):
            config = builder(2000 + seed)
            out = run_and_summarize(config)
            seed_results.append({k: v for k, v in out.items() if k.startswith("n_")})
        totals = {k: sum(r[k] for r in seed_results) for k in seed_results[0]}
        any_nonzero = {k: any(r[k] > 0 for r in seed_results) for k in seed_results[0]}
        checks = {
            "expected_nonzero_confirmed": {k: any_nonzero.get(k, False) for k in EXPECTED_NONZERO[name]},
            "expected_zero_confirmed": {k: totals.get(k, 0) == 0 for k in EXPECTED_ZERO[name]},
        }
        report["conditions"][name] = {"totals": totals, "checks": checks, "per_seed": seed_results}
        all_nonzero_ok = all(checks["expected_nonzero_confirmed"].values())
        all_zero_ok = all(checks["expected_zero_confirmed"].values())
        print(
            f"{name}: nonzero_confirmed={all_nonzero_ok} zero_confirmed={all_zero_ok} totals={totals}",
            flush=True,
        )
    with open(f"{OUT_DIR}/stage1_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
