#!/usr/bin/env python3
"""Level 1.1b, Work Package G: functional shock recovery.

Level 1.1 reported a 10/10 reappointment rate after recall and called
this "recovery" — but reappointment (a rule's office being refilled)
and functional recovery (the new office-holder's actual capacity/
performance returning to at least pre-shock levels) are different
claims, and Level 1.1 never measured the second one. This script does,
using `level11_complete` at its own unchanged defaults (accountability
+ recall on — recall is the "shock" this milestone means), matched
seeds, `mechanism_substreams` mode.

Definitions, all computed purely from `EventLog` ground truth:

* A "shock" is a `DelegateRemovalEvent` with `reason == "recalled"`.
  `final_capacity` (the generative layer's own `Delegate.capacity`
  property, evaluated at the moment of removal) is the pre-shock
  reference level.
* "Reappointed": a `DelegateAppointmentEvent` for the same `rule_id`
  occurs within `REAPPOINTMENT_WINDOW_STEPS` steps after the shock.
* "Functional recovery" (post-shock capacity): the successor
  delegate's own `TaskPerformanceEvent.capacity_before`, taken as the
  LAST observed value within `RECOVERY_WINDOW_STEPS` steps of its own
  appointment (i.e. "capacity reached by the end of the recovery
  window," not an average over it — a successor removed early within
  the window contributes whatever its last observed capacity was
  before removal, not a value from after it stopped holding office).
  `recovery_gap = post_shock_capacity - pre_shock_capacity` (a bounded
  difference in [-1, 1], not a ratio — `capacity` is itself bounded in
  [0, 1] and can sit very close to 0 at the moment of a shock, which
  makes a ratio numerically explode and become uninterpretable; a
  bounded absolute difference stays well-behaved everywhere and is
  never undefined). Two threshold reads are reported side by side
  (`recovery_gap >= 0.0` "full — matched or exceeded pre-shock level"
  and `recovery_gap >= -0.05` "within-tolerance — allows a small step-
  to-step noise band") because a single arbitrary cutoff would
  understate how much information the continuous gap itself carries —
  the milestone's instruction is to not overclaim a single number, not
  to replace one single number with a different single number.
* Task-completion-rate recovery is reported as a second, independent
  performance dimension (successes / attempts) alongside capacity, in
  the same pre/post-shock windows, since capacity is a slow state
  variable while completion rate is the more immediate realized
  outcome.

Every rate here is a SINGLE-CONDITION descriptive estimate (this is not
a treatment-vs-control contrast — there is no ablation being compared),
so the seed-clustered bootstrap resamples per-seed rates directly (seed
as the primary independent unit, per-seed rate treated as one
datapoint, unweighted across seeds regardless of how many shocks that
seed happened to produce) rather than a paired difference.
"""

from __future__ import annotations

import json
import os

import numpy as np

from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation

BOOTSTRAP_SEED = 20264  # distinct from WP-D's 20261, WP-E's 20262, WP-F's 20263
N_BOOTSTRAP = 5000

N_SEEDS = 15
POPULATION_SIZE = 40
N_PATCHES = 3
N_STEPS = 400
REAPPOINTMENT_WINDOW_STEPS = 30
RECOVERY_WINDOW_STEPS = 40
#: recovery_gap = post_shock_capacity - pre_shock_capacity thresholds.
RECOVERY_GAP_THRESHOLDS = {"full": 0.0, "within_tolerance": -0.05}


def _completion_rate(events) -> float | None:
    attempts = len(events)
    if attempts == 0:
        return None
    successes = sum(1 for e in events if e.outcome == "success")
    return successes / attempts


def _analyze_shocks(log) -> dict:
    """Pure function of an already-collected ``EventLog`` -- the
    testable core of :func:`_summarize_run`, factored out so
    ``tests/test_level11b_functional_shock_recovery.py`` can exercise
    the reappointment/recovery-gap arithmetic directly on a small
    synthetic log instead of only via a full simulation run."""
    removals = [e for e in log.delegate_removals if e.reason == "recalled"]
    appointments_by_rule: dict[int, list] = {}
    for e in log.delegate_appointments:
        appointments_by_rule.setdefault(e.rule_id, []).append(e)
    for lst in appointments_by_rule.values():
        lst.sort(key=lambda e: e.step)

    perf_by_delegate: dict[int, list] = {}
    for e in log.task_performances:
        perf_by_delegate.setdefault(e.delegate_id, []).append(e)
    for lst in perf_by_delegate.values():
        lst.sort(key=lambda e: e.step)

    shocks = []
    for removal in removals:
        pre_shock_capacity = removal.final_capacity
        pre_shock_window_events = [
            e for e in perf_by_delegate.get(removal.delegate_id, [])
            if removal.step - RECOVERY_WINDOW_STEPS <= e.step <= removal.step
        ]
        pre_shock_completion_rate = _completion_rate(pre_shock_window_events)

        successor = None
        for appt in appointments_by_rule.get(removal.rule_id, []):
            if appt.predecessor_delegate_id == removal.delegate_id and 0 < (appt.step - removal.step) <= REAPPOINTMENT_WINDOW_STEPS:
                successor = appt
                break
        reappointed = successor is not None

        post_shock_capacity = None
        post_shock_completion_rate = None
        recovery_gap = None
        if reappointed:
            window_events = [
                e for e in perf_by_delegate.get(successor.delegate_id, [])
                if e.step <= successor.step + RECOVERY_WINDOW_STEPS
            ]
            if window_events:
                post_shock_capacity = window_events[-1].capacity_before
                post_shock_completion_rate = _completion_rate(window_events)
                recovery_gap = post_shock_capacity - pre_shock_capacity

        shocks.append({
            "pre_shock_capacity": pre_shock_capacity,
            "pre_shock_completion_rate": pre_shock_completion_rate,
            "reappointed": reappointed,
            "post_shock_capacity": post_shock_capacity,
            "post_shock_completion_rate": post_shock_completion_rate,
            "recovery_gap": recovery_gap,
        })

    n_shocks = len(shocks)
    n_reappointed = sum(1 for s in shocks if s["reappointed"])
    gaps = [s["recovery_gap"] for s in shocks if s["recovery_gap"] is not None]
    n_gap_undefined_among_reappointed = sum(
        1 for s in shocks if s["reappointed"] and s["recovery_gap"] is None
    )
    recovered_counts = {
        key: sum(1 for g in gaps if g >= threshold) for key, threshold in RECOVERY_GAP_THRESHOLDS.items()
    }
    pre_rates = [s["pre_shock_completion_rate"] for s in shocks if s["pre_shock_completion_rate"] is not None]
    post_rates = [
        s["post_shock_completion_rate"] for s in shocks
        if s["reappointed"] and s["post_shock_completion_rate"] is not None
    ]

    return {
        "n_shocks": n_shocks,
        "n_reappointed": n_reappointed,
        "reappointment_rate": (n_reappointed / n_shocks) if n_shocks else None,
        "n_recovery_gap_defined": len(gaps),
        "n_gap_undefined_among_reappointed": n_gap_undefined_among_reappointed,
        "mean_recovery_gap": (sum(gaps) / len(gaps)) if gaps else None,
        "median_recovery_gap": (float(np.median(gaps)) if gaps else None),
        "full_recovery_rate_among_reappointed_with_defined_gap": (
            recovered_counts["full"] / len(gaps) if gaps else None
        ),
        "within_tolerance_recovery_rate_among_reappointed_with_defined_gap": (
            recovered_counts["within_tolerance"] / len(gaps) if gaps else None
        ),
        "mean_pre_shock_completion_rate": (sum(pre_rates) / len(pre_rates)) if pre_rates else None,
        "mean_post_shock_completion_rate": (sum(post_rates) / len(post_rates)) if post_rates else None,
    }


def _summarize_run(config: SimulationConfig) -> dict:
    log = Simulation(config).run().event_log
    return _analyze_shocks(log)


def _seed_clustered_bootstrap_single_sample(per_seed_values: list, n_bootstrap: int = N_BOOTSTRAP) -> dict:
    """Bootstrap CI on the unweighted mean of one value per seed
    (seed as the primary independent unit) -- not a paired-condition
    contrast, since this work package has no ablation to contrast
    against."""
    vals = np.array([v for v in per_seed_values if v is not None])
    n_skipped = len(per_seed_values) - len(vals)
    if len(vals) == 0:
        return {"point_estimate": None, "ci_low": None, "ci_high": None, "n_seeds": 0, "n_seeds_skipped_undefined": n_skipped}
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    boot_means = np.array([rng.choice(vals, size=len(vals), replace=True).mean() for _ in range(n_bootstrap)])
    return {
        "point_estimate": float(vals.mean()),
        "ci_low": float(np.percentile(boot_means, 2.5)),
        "ci_high": float(np.percentile(boot_means, 97.5)),
        "n_seeds": len(vals),
        "n_seeds_skipped_undefined": n_skipped,
    }


def run(out_root: str = "outputs/level11b_functional_shock_recovery", n_seeds: int = N_SEEDS) -> dict:
    os.makedirs(out_root, exist_ok=True)
    per_seed_rows = []
    for seed in range(n_seeds):
        config = SimulationConfig.level11b_substreams(
            population_size=POPULATION_SIZE, n_patches=N_PATCHES, n_steps=N_STEPS, seed=seed,
        )
        row = {"seed": seed}
        row.update(_summarize_run(config))
        per_seed_rows.append(row)

    fields = [
        "n_shocks", "n_reappointed", "reappointment_rate", "n_recovery_gap_defined",
        "n_gap_undefined_among_reappointed", "mean_recovery_gap", "median_recovery_gap",
        "full_recovery_rate_among_reappointed_with_defined_gap",
        "within_tolerance_recovery_rate_among_reappointed_with_defined_gap",
        "mean_pre_shock_completion_rate", "mean_post_shock_completion_rate",
    ]
    bootstrap = {
        f: _seed_clustered_bootstrap_single_sample([r[f] for r in per_seed_rows]) for f in fields
    }

    total_shocks = sum(r["n_shocks"] for r in per_seed_rows)
    total_reappointed = sum(r["n_reappointed"] for r in per_seed_rows)
    pooled_reappointment_rate = (total_reappointed / total_shocks) if total_shocks else None

    summary = {
        "design": {
            "n_seeds": n_seeds, "population_size": POPULATION_SIZE, "n_patches": N_PATCHES, "n_steps": N_STEPS,
            "reappointment_window_steps": REAPPOINTMENT_WINDOW_STEPS, "recovery_window_steps": RECOVERY_WINDOW_STEPS,
            "recovery_gap_thresholds": RECOVERY_GAP_THRESHOLDS,
        },
        "per_seed": per_seed_rows,
        "pooled_totals": {
            "total_shocks": total_shocks, "total_reappointed": total_reappointed,
            "pooled_reappointment_rate": pooled_reappointment_rate,
        },
        "seed_clustered_bootstrap": bootstrap,
    }

    reap = bootstrap["reappointment_rate"]
    full_rec = bootstrap["full_recovery_rate_among_reappointed_with_defined_gap"]
    tol_rec = bootstrap["within_tolerance_recovery_rate_among_reappointed_with_defined_gap"]
    gap = bootstrap["mean_recovery_gap"]
    pre_c = bootstrap["mean_pre_shock_completion_rate"]
    post_c = bootstrap["mean_post_shock_completion_rate"]
    summary["interpretation"] = (
        f"Pooled across all seeds: {total_reappointed}/{total_shocks} recall shocks were reappointed "
        f"within {REAPPOINTMENT_WINDOW_STEPS} steps (pooled rate={pooled_reappointment_rate}). "
        f"Seed-clustered (mean-of-per-seed-rate, n_seeds={reap['n_seeds']}): reappointment_rate "
        f"point={reap['point_estimate']}, CI=[{reap['ci_low']}, {reap['ci_high']}]. "
        f"THIS IS NOT THE SAME QUANTITY AS FUNCTIONAL RECOVERY. Among reappointed successors with a "
        f"defined recovery_gap (n_seeds={gap['n_seeds'] if gap['n_seeds'] else 0}, "
        f"n_gap_undefined_among_reappointed pooled="
        f"{sum(r['n_gap_undefined_among_reappointed'] for r in per_seed_rows)}): mean_recovery_gap "
        f"(post_shock_capacity - pre_shock_capacity) point={gap['point_estimate']}, "
        f"CI=[{gap['ci_low']}, {gap['ci_high']}]. Full recovery (gap>=0, matched or exceeded pre-shock "
        f"capacity) rate: point={full_rec['point_estimate']}, CI=[{full_rec['ci_low']}, "
        f"{full_rec['ci_high']}]. Within-tolerance recovery (gap>=-0.05) rate: "
        f"point={tol_rec['point_estimate']}, CI=[{tol_rec['ci_low']}, {tol_rec['ci_high']}]. "
        f"Completion-rate dimension: mean_pre_shock_completion_rate point={pre_c['point_estimate']}, "
        f"mean_post_shock_completion_rate point={post_c['point_estimate']}. If the reappointment-rate "
        "estimate above sits substantially higher than the full/within-tolerance recovery rates, that gap "
        "IS the concrete demonstration this work package was commissioned to produce: reappointment "
        "measures whether an office got refilled, not whether the office-holder's realized administrative "
        "capacity or task-completion performance actually returned to (or exceeded) its pre-shock level. "
        "Read the actual point estimates and CIs above -- including whether either interval crosses the "
        "other's -- before asserting the gap is large, small, or statistically distinguishable; this text "
        "does not assert a specific conclusion so it stays accurate regardless of which way the numbers "
        "land. See docs/level1.1b_validation_note.md for the confirmatory read."
    )

    summary_path = os.path.join(out_root, "level11b_functional_shock_recovery_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)
    print(f"[level11b_functional_shock_recovery] {summary_path}")
    print(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
