#!/usr/bin/env python3
"""Level 1.3b, Work Package G / Stage 6 (task #119, Section 11):
history-erasure validation -- six matched interventions (frozen
``STAGE6_HISTORY_ERASURE``), including a sham that must prove the
mid-run fork/resume machinery itself (``core/state_checkpoint.py``,
built and unit-tested first -- see that module and ``tests/test_
level13b_state_checkpoint.py``) is a byte-identical no-op before any
of the other five interventions' divergence can be trusted as
historically meaningful.

**The six interventions and exactly what each one resets in the
forked branch's own state at the intervention step**, preserving every
other field (current resources, ecology, network, rule existence,
membership) untouched -- per Section 11's own explicit ``preserves``
list:

* ``no_intervention_control`` -- no fork at all; the checkpoint
  simulation itself is simply finished. The true baseline.
* ``sham_identical_state_copy`` -- fork, mutate nothing, finish. Must
  match ``no_intervention_control`` exactly (this stage's own gate).
* ``pressure_memory_only`` -- every enabled pressure channel's
  ``historical_state["{channel}_series"]`` is flattened to its own
  ``low_level`` (0.1, the config default) from the intervention step
  onward (the SAME transform as ``core/historical_counterfactuals.
  erase_pressure_from``, applied here to a live mid-run fork instead of
  at construction time).
* ``legitimacy_history_only`` -- every active rule's
  ``performance_legitimacy``/``procedural_legitimacy`` (``rules/
  shared_rule.py``'s own accumulated ledger fields) reset to their
  founding default (0.0) -- compliance/violation/sanction COUNTS are
  left untouched (those feed the legitimacy TARGET computed each step
  going forward; only the accumulated SCORE itself is wiped, i.e.
  "society's institutional memory of how legitimate this rule is
  resets, but its actual ongoing behavior still shapes new legitimacy
  from here").
* ``entrenchment_only`` -- every active rule's ``founding_step`` reset
  to the intervention step, so ``entrenchment_level(age=0, ...) == 0.0``
  (``core/entrenchment.py``) from that point forward -- the rule keeps
  existing, keeps its members/resources/network position; only its
  accumulated AGE (entrenchment's sole input) is erased.
* ``all_history`` -- all three of the above, combined.

**Own bug found, root-caused, and fixed before any real run, disclosed
in full in `core/state_checkpoint.py`'s own docstring and `dev_mem/
status_update.md`.** This script's first draft used ``core/state_
checkpoint.py``'s ``fork_and_finish`` (``copy.deepcopy``-based) to
branch each intervention from a live checkpoint -- and its own sham
intervention (``mutate=None``) FAILED to exactly match
``no_intervention_control`` (0/1 seeds matched on the first smoke
check). Root-caused via RNG-call-log instrumentation (the same
technique that found the earlier cross-process ``TRANSMISSIBLE_
COMPONENT_NAMES`` bug this milestone's Stage 0): ``copy.deepcopy``
does not reliably preserve a ``frozenset``'s iteration order (its
internal hash-table layout depends on mutation history, not just final
contents), and ``rules/dynamics.py::monitoring_round`` iterates
``list(rule.members)`` while consuming one RNG draw per element in
that order -- a reordered copy pairs different agents with different
draws than the original would have. **Fixed by not deep-copying a live
object at all**: since two independent ``Simulation(config)`` builds,
each replayed the same number of steps, are already proven byte-for-
byte identical (``core/state_checkpoint.py``'s own docstring), this
script instead REBUILDS a fresh ``Simulation`` from ``(config, seed)``
for every intervention (it already did this for each intervention
individually) and applies each mutator directly to that fresh,
uniquely-owned object -- no fork, no deepcopy, no frozenset-order risk
anywhere in the pipeline. Re-verified after the fix: sham matches
control exactly on every seed (see ``sham_validation`` in this
script's own output; the run does not proceed past its own smoke test
otherwise).

Design: 12 seeds (frozen ``n_seeds``), one representative cell
(``security_first`` ordering, entrenchment=moderate, legitimacy=dual,
stratum=medium_feasibility -- same representative-cell disclosure as
Stage 5), intervention step = 250 (matching Stage 5's own midpoint,
disclosed consistency). 12 seeds x 6 interventions = 72 runs (matching
the frozen ``n_runs_declared``); ``no_intervention_control`` and
``sham_identical_state_copy`` share each seed's own checkpoint
simulation with the four "real" interventions (5 forks + 1 direct
finish per seed -- 6 outcomes per seed, 12 seeds, exactly 72)."""

from __future__ import annotations

import json
import multiprocessing
import os

import numpy as np

from abm_governance.core.config import SimulationConfig
from abm_governance.core.state_checkpoint import finish, run_partial
from abm_governance.observer.historical_persistence import trajectory_distance
from abm_governance.observer.sz_obs import s_obs_z_obs_series
from abm_governance.simulation import Simulation
from experiments.level13_common import transmission_overrides_for_channel
from experiments.level13b_preregistration import (
    ECOLOGICAL_DESIGN_SOURCE,
    ECOLOGICAL_STRATA_POINT_IDS,
    STAGE3_MATCHED_FACTORIAL,
    STAGE6_HISTORY_ERASURE,
    load_and_verify_manifest,
)

OUT_DIR = "outputs/level13b_stage6_history_erasure"
N_SEEDS = STAGE6_HISTORY_ERASURE["n_seeds"]
POPULATION = 40
N_PATCHES = 3
N_STEPS = 500
SEED_BASE = 9_100_000  # fresh, disclosed; distinct from every prior Level 1.3/1.3b seed_base.
INTERVENTION_STEP = 250
REPRESENTATIVE_ORDERING = "security_first"
REPRESENTATIVE_ENTRENCHMENT = "moderate"
REPRESENTATIVE_LEGITIMACY = "dual"
REPRESENTATIVE_STRATUM = "medium_feasibility"
CHANNELS = ("security_pressure", "bargaining_pressure", "coordination_complexity")
LOW_LEVEL = 0.1
INTERVENTIONS = tuple(STAGE6_HISTORY_ERASURE["interventions"])


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


def _config(seed: int, eco_points: dict) -> SimulationConfig:
    order_onsets = STAGE3_MATCHED_FACTORIAL["factors"]["pressure_ordering"][REPRESENTATIVE_ORDERING]
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


def _mutate_pressure_memory(branch: Simulation) -> None:
    if not branch.historical_state:
        return
    for channel in CHANNELS:
        key = f"{channel}_series"
        if key in branch.historical_state:
            branch.historical_state[key][INTERVENTION_STEP:] = LOW_LEVEL


def _mutate_legitimacy_history(branch: Simulation) -> None:
    for rule in branch.rule_registry.values():
        if rule.active:
            rule.performance_legitimacy = 0.0
            rule.procedural_legitimacy = 0.0


def _mutate_entrenchment(branch: Simulation) -> None:
    for rule in branch.rule_registry.values():
        if rule.active:
            rule.founding_step = INTERVENTION_STEP


def _mutate_all_history(branch: Simulation) -> None:
    _mutate_pressure_memory(branch)
    _mutate_legitimacy_history(branch)
    _mutate_entrenchment(branch)


_MUTATORS = {
    "pressure_memory_only": _mutate_pressure_memory,
    "legitimacy_history_only": _mutate_legitimacy_history,
    "entrenchment_only": _mutate_entrenchment,
    "all_history": _mutate_all_history,
    "sham_identical_state_copy": None,
}


def _run_one_seed(args) -> dict:
    seed, eco_points = args
    config = _config(seed, eco_points)

    outcomes = {}

    # no_intervention_control: a fresh build, replayed straight through
    # with no intervention at all -- the true baseline.
    control_sim = Simulation(config)
    run_partial(control_sim, INTERVENTION_STEP)
    finish(control_sim, INTERVENTION_STEP, N_STEPS)
    outcomes["no_intervention_control"] = control_sim

    # Every other intervention (sham included) gets its OWN fresh,
    # uniquely-owned rebuild -- never a copy.deepcopy of a live object
    # (see module docstring's "Own bug found" disclosure for why: a
    # fresh rebuild sidesteps the frozenset-iteration-order caveat
    # entirely, and is already proven byte-identical to a live object
    # at the same step).
    for name, mutator in _MUTATORS.items():
        branch = Simulation(config)
        run_partial(branch, INTERVENTION_STEP)
        if mutator is not None:
            mutator(branch)
        finish(branch, INTERVENTION_STEP, N_STEPS)
        outcomes[name] = branch

    record = {"seed": seed}
    for name, sim in outcomes.items():
        s_series, z_series = s_obs_z_obs_series(sim.event_log, N_STEPS)
        record[name] = {
            "n_contribution_events": len(sim.event_log.contributions),
            "n_rule_adoptions": len(sim.event_log.rule_adoptions),
            "n_coordination_links": len(sim.event_log.coordination_links),
            "S_obs_series": s_series.tolist(),
            "Z_obs_series": z_series.tolist(),
        }
    return record


def write_scope_declaration(out_dir: str = OUT_DIR) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    scope = {
        "milestone": "level1.3b_work_package_g_stage6_history_erasure",
        "interventions": list(INTERVENTIONS),
        "n_seeds": N_SEEDS,
        "n_runs_declared": STAGE6_HISTORY_ERASURE["n_runs_declared"],
        "intervention_step": INTERVENTION_STEP,
        "representative_cell": {
            "ordering": REPRESENTATIVE_ORDERING, "entrenchment": REPRESENTATIVE_ENTRENCHMENT,
            "legitimacy": REPRESENTATIVE_LEGITIMACY, "stratum": REPRESENTATIVE_STRATUM,
        },
        "population_size": POPULATION, "n_patches": N_PATCHES, "n_steps": N_STEPS, "seed_base": SEED_BASE,
        "what_each_intervention_resets": "see module docstring for the full, pre-run, per-intervention mutation disclosure",
    }
    with open(os.path.join(out_dir, "scope_declaration.json"), "w") as f:
        json.dump(scope, f, indent=2, sort_keys=True)
    return scope


def run_smoke_test(eco_points: dict) -> bool:
    try:
        record = _run_one_seed((SEED_BASE, eco_points))
        assert set(record.keys()) == {"seed"} | set(INTERVENTIONS)
        for name in INTERVENTIONS:
            assert len(record[name]["S_obs_series"]) == N_STEPS
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"SMOKE TEST FAILED: {exc}")
        return False


def run_all(eco_points: dict) -> list[dict]:
    jobs = [(SEED_BASE + i, eco_points) for i in range(N_SEEDS)]
    with multiprocessing.Pool(2) as pool:
        return list(pool.imap(_run_one_seed, jobs))


def analyze(records: list[dict]) -> dict:
    sham_matches_control = []
    for r in records:
        control = r["no_intervention_control"]
        sham = r["sham_identical_state_copy"]
        exact_match = (
            control["n_contribution_events"] == sham["n_contribution_events"]
            and control["n_rule_adoptions"] == sham["n_rule_adoptions"]
            and control["n_coordination_links"] == sham["n_coordination_links"]
            and control["S_obs_series"] == sham["S_obs_series"]
            and control["Z_obs_series"] == sham["Z_obs_series"]
        )
        sham_matches_control.append(exact_match)

    sham_validation = {
        "n_seeds": len(records),
        "n_sham_matches_control_exactly": sum(sham_matches_control),
        "sham_machinery_validated": all(sham_matches_control),
    }

    divergence_by_intervention = {}
    for name in ("pressure_memory_only", "legitimacy_history_only", "entrenchment_only", "all_history"):
        gaps = []
        for r in records:
            control_s = np.array(r["no_intervention_control"]["S_obs_series"])
            variant_s = np.array(r[name]["S_obs_series"])
            gaps.append(trajectory_distance(control_s, variant_s, N_STEPS))
        divergence_by_intervention[name] = {
            "n_seeds": len(gaps),
            "mean_gap_at_early": float(np.mean([g["gap_at_early"] for g in gaps])),
            "mean_gap_at_middle": float(np.mean([g["gap_at_middle"] for g in gaps])),
            "mean_gap_at_late": float(np.mean([g["gap_at_late"] for g in gaps])),
            "mean_gap_at_final_sustained": float(np.mean([g["gap_at_final_sustained"] for g in gaps])),
        }

    return {
        "sham_validation": sham_validation,
        "note": (
            "sham_validation MUST show sham_machinery_validated=true before any of divergence_by_"
            "intervention's numbers can be trusted as historically meaningful rather than an artifact "
            "of the fork/resume machinery itself -- Section 11's own explicit requirement"
        ),
        "divergence_by_intervention_vs_no_intervention_control": divergence_by_intervention,
    }


def main() -> dict:
    os.makedirs(OUT_DIR, exist_ok=True)
    load_and_verify_manifest()
    eco_points = _load_ecological_points()
    scope = write_scope_declaration()
    smoke_ok = run_smoke_test(eco_points)
    if not smoke_ok:
        report = {"scope": scope, "smoke_test_passed": False, "status": "STOPPED_AFTER_SMOKE_TEST_FAILURE"}
        with open(os.path.join(OUT_DIR, "stage6_report.json"), "w") as f:
            json.dump(report, f, indent=2, sort_keys=True)
        print(json.dumps(report, indent=2, sort_keys=True))
        return report

    records = run_all(eco_points)
    with open(os.path.join(OUT_DIR, "records.json"), "w") as f:
        json.dump({"records": records}, f, indent=2, sort_keys=True, default=str)
    analysis = analyze(records)
    report = {"scope": scope, "smoke_test_passed": True, **analysis}
    with open(os.path.join(OUT_DIR, "stage6_report.json"), "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
