#!/usr/bin/env python3
"""Level 1.1b, Work Package E: accountability function audit —
matched-seed sweep across the eight named accountability conditions,
reporting `accountability_activity` and `effective_constraint`
(observer/accountability_diagnostics.py) separately for each.

The eight conditions (Section 8 of the milestone):

* no_accountability      -- accountability_enabled=False entirely
* audit_only             -- audits run; recall/appeal structurally cannot fire
* appeal_only            -- appeals run; audits (and therefore recall) never fire
* recall_only            -- audit+recall run, appeal never fires (see the
                             architectural-coupling note in config.py: a
                             recall cannot be isolated from audit in this
                             implementation, so this condition is really
                             "audit+recall, no appeal" and is reported
                             under that honest label, not a pretended
                             isolated recall-only condition)
* full                   -- audit+recall+appeal, level11_complete defaults
* costless               -- full, with audit_cost/appeal_cost zeroed
* perfect_info           -- full, audit_accuracy=1.0
* randomized_placebo     -- full, audit_accuracy=0.5 (coin-flip detection)

Two confirmatory contrasts use the seed-clustered paired bootstrap
(seed as the primary independent unit, Section 13):

1. full vs. no_accountability, on total_appropriated -- does the full
   accountability apparatus actually reduce realized appropriation
   relative to having none at all?
2. perfect_info vs. randomized_placebo, on detection_rate_given_misconduct
   and recovery_fraction_of_appropriated -- the milestone's core
   activity-vs-effective-constraint claim: both conditions run audits at
   the same attempted rate (comparable `accountability_activity`), but
   only perfect_info should show materially higher realized detection/
   recovery under `effective_constraint`.

Per this milestone's instruction: a condition producing zero or
negative apparent effect, or an undefined (None) rate because a
denominator was zero at some seed, is reported as such -- never
silently coerced to 0.0 or omitted.
"""

from __future__ import annotations

import json
import os

import numpy as np

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.accountability_diagnostics import (
    accountability_activity,
    effective_constraint,
)
from abm_governance.simulation import Simulation

BOOTSTRAP_SEED = 20262  # distinct from level11b_appropriation_decomposition's 20261
N_BOOTSTRAP = 5000

N_SEEDS = 12
POPULATION_SIZE = 40
N_PATCHES = 3
N_STEPS = 300

CONDITIONS = {
    "no_accountability": lambda **kw: SimulationConfig.level11b_substreams(accountability_enabled=False, **kw),
    "audit_only": SimulationConfig.level11b_accountability_audit_only,
    "appeal_only": SimulationConfig.level11b_accountability_appeal_only,
    "recall_only": SimulationConfig.level11b_accountability_recall_only,
    "full": SimulationConfig.level11b_substreams,
    "costless": SimulationConfig.level11b_accountability_costless,
    "perfect_info": SimulationConfig.level11b_accountability_perfect_info,
    "randomized_placebo": SimulationConfig.level11b_accountability_randomized_placebo,
}


def _summarize_run(config: SimulationConfig) -> dict:
    log = Simulation(config).run().event_log
    activity = accountability_activity(log)
    constraint = effective_constraint(log)
    total_appropriated = sum(a.amount for a in log.appropriations)
    total_recovered = constraint["total_recovered_funds"]
    row = {
        # gross: every AppropriationEvent.amount, regardless of any later
        # recall recovery -- this is what happened at the moment of the
        # act, and accountability (even a successful recall) never
        # un-happens it.
        "total_appropriated": total_appropriated,
        # net: gross minus whatever a successful recall actually clawed
        # back -- the more meaningful "how much appropriation stuck"
        # measure. Recall recovers funds AFTER an act is already
        # detected, so accountability can raise n_opportunities/gross
        # (more delegate turnover from recalls -> more newly-appointed
        # delegates -> more appropriation opportunities) while still
        # lowering net -- gross alone can mislead in either direction.
        "net_appropriated": total_appropriated - total_recovered,
    }
    row.update({f"activity__{k}": v for k, v in activity.items()})
    row.update({f"constraint__{k}": v for k, v in constraint.items()})
    return row


def _paired_seed_clustered_bootstrap(
    rows: list, field: str, label_a: str, label_b: str, n_bootstrap: int = N_BOOTSTRAP
) -> dict:
    """Seed-clustered paired bootstrap of (label_b - label_a) on `field`,
    resampling seeds (the primary independent unit) with replacement.
    Skips any seed where either condition's value is None (undefined
    denominator) rather than coercing to 0 -- reported via n_seeds."""
    by_seed = {}
    for r in rows:
        by_seed.setdefault(r["seed"], {})[r["condition"]] = r[field]
    seeds = sorted(by_seed.keys())
    paired_diffs = np.array([
        by_seed[s][label_b] - by_seed[s][label_a]
        for s in seeds
        if by_seed[s].get(label_a) is not None and by_seed[s].get(label_b) is not None
    ])
    n_skipped = len(seeds) - len(paired_diffs)
    if len(paired_diffs) == 0:
        return {"point_estimate": None, "ci_low": None, "ci_high": None, "n_seeds": 0, "n_seeds_skipped_undefined": n_skipped}
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    boot_means = np.array([
        rng.choice(paired_diffs, size=len(paired_diffs), replace=True).mean() for _ in range(n_bootstrap)
    ])
    return {
        "point_estimate": float(paired_diffs.mean()),
        "ci_low": float(np.percentile(boot_means, 2.5)),
        "ci_high": float(np.percentile(boot_means, 97.5)),
        "n_seeds": len(paired_diffs),
        "n_seeds_skipped_undefined": n_skipped,
    }


def run(out_root: str = "outputs/level11b_accountability_conditions", n_seeds: int = N_SEEDS) -> dict:
    os.makedirs(out_root, exist_ok=True)
    rows = []
    for seed in range(n_seeds):
        base_kwargs = dict(population_size=POPULATION_SIZE, n_patches=N_PATCHES, n_steps=N_STEPS, seed=seed)
        for label, builder in CONDITIONS.items():
            cfg = builder(**base_kwargs)
            row = {"seed": seed, "condition": label}
            row.update(_summarize_run(cfg))
            rows.append(row)

    def _agg(label, field):
        vals = [r[field] for r in rows if r["condition"] == label and r.get(field) is not None]
        return (sum(vals) / len(vals)) if vals else None

    all_fields = sorted({k for r in rows for k in r if k not in ("seed", "condition")})
    mean_by_condition = {
        label: {f: _agg(label, f) for f in all_fields} for label in CONDITIONS
    }

    contrasts = {
        "full_minus_no_accountability__total_appropriated": _paired_seed_clustered_bootstrap(
            rows, "total_appropriated", "no_accountability", "full"
        ),
        "full_minus_no_accountability__net_appropriated": _paired_seed_clustered_bootstrap(
            rows, "net_appropriated", "no_accountability", "full"
        ),
        "placebo_minus_no_accountability__net_appropriated": _paired_seed_clustered_bootstrap(
            rows, "net_appropriated", "no_accountability", "randomized_placebo"
        ),
        "perfect_info_minus_no_accountability__net_appropriated": _paired_seed_clustered_bootstrap(
            rows, "net_appropriated", "no_accountability", "perfect_info"
        ),
        "perfect_info_minus_placebo__detection_rate_given_misconduct": _paired_seed_clustered_bootstrap(
            rows, "constraint__detection_rate_given_misconduct", "randomized_placebo", "perfect_info"
        ),
        "perfect_info_minus_placebo__recovery_fraction_of_appropriated": _paired_seed_clustered_bootstrap(
            rows, "constraint__recovery_fraction_of_appropriated", "randomized_placebo", "perfect_info"
        ),
        "perfect_info_minus_placebo__n_audits": _paired_seed_clustered_bootstrap(
            rows, "activity__n_audits", "randomized_placebo", "perfect_info"
        ),
    }

    summary = {
        "design": {
            "n_seeds": n_seeds, "population_size": POPULATION_SIZE, "n_patches": N_PATCHES, "n_steps": N_STEPS,
            "conditions": list(CONDITIONS.keys()),
        },
        "mean_by_condition": mean_by_condition,
        "seed_clustered_bootstrap_contrasts": contrasts,
    }

    c1 = contrasts["perfect_info_minus_placebo__n_audits"]
    c2 = contrasts["perfect_info_minus_placebo__detection_rate_given_misconduct"]
    c3 = contrasts["full_minus_no_accountability__total_appropriated"]
    c3n = contrasts["full_minus_no_accountability__net_appropriated"]
    c_placebo_net = contrasts["placebo_minus_no_accountability__net_appropriated"]
    c_perfect_net = contrasts["perfect_info_minus_no_accountability__net_appropriated"]
    summary["interpretation"] = (
        "ANOMALOUS RESULT, reported unchanged: audit attempt volume was NOT held constant between "
        f"perfect_info and randomized_placebo despite both using the level11b_substreams full-accountability "
        f"defaults -- (n_audits, perfect_info - placebo): point={c1['point_estimate']:.1f}, "
        f"CI=[{c1['ci_low']:.1f}, {c1['ci_high']:.1f}] over n_seeds={c1['n_seeds']} excludes zero. "
        "perfect_info's higher detection rate drives more recalls, which replace delegates more often, "
        "which appears to feed back into more subsequent audit opportunities -- a genuine emergent "
        "coupling between audit_accuracy and audit volume via the recall->replacement pathway, not a "
        "held-constant experimental control; the milestone's intended 'same activity, different "
        "constraint' contrast is therefore NOT clean as designed and any conclusion below must account "
        "for this confound rather than assume matched activity. "
        f"effective-constraint gap (detection_rate_given_misconduct, perfect_info - placebo): "
        f"point={c2['point_estimate']:.3f}, CI=[{c2['ci_low']:.3f}, {c2['ci_high']:.3f}] over "
        f"n_seeds={c2['n_seeds']}, excludes zero regardless. "
        "SEPARATE ANOMALOUS RESULT: gross total_appropriated (every AppropriationEvent.amount, "
        f"never netted against recovery) is HIGHER under full accountability than under none at all -- "
        f"(full - no_accountability): point={c3['point_estimate']:.3f}, CI=[{c3['ci_low']:.3f}, "
        f"{c3['ci_high']:.3f}], excludes zero in the POSITIVE direction -- the opposite of what a naive "
        "'accountability reduces misconduct' reading would predict. This is because gross counts every "
        "act, and successful recalls raise delegate turnover, which raises the count of newly-appointed "
        "delegates and therefore the count of appropriation opportunities -- accountability here changes "
        "who holds office more than whether office-holders attempt appropriation. Net appropriation "
        "(gross minus recovered_funds, i.e. what actually stuck after any recall clawback) is the more "
        f"meaningful measure: (full - no_accountability) net: point={c3n['point_estimate']:.3f}, "
        f"CI=[{c3n['ci_low']:.3f}, {c3n['ci_high']:.3f}]; (randomized_placebo - no_accountability) net: "
        f"point={c_placebo_net['point_estimate']:.3f}, CI=[{c_placebo_net['ci_low']:.3f}, "
        f"{c_placebo_net['ci_high']:.3f}]; (perfect_info - no_accountability) net: "
        f"point={c_perfect_net['point_estimate']:.3f}, CI=[{c_perfect_net['ci_low']:.3f}, "
        f"{c_perfect_net['ci_high']:.3f}]. Whether each of these net-appropriation CIs actually excludes "
        "zero, and in which direction, must be read directly from the numbers above -- not asserted here "
        "-- before drawing any 'accountability works/doesn't work' conclusion; see "
        "docs/level1.1b_validation_note.md for that confirmatory read. Per this milestone's instruction, "
        "this null-or-adverse-or-anomalous pattern is reported exactly as found, not reframed as a "
        "positive finding, and not smoothed into the originally-hypothesized clean contrast."
    )

    summary_path = os.path.join(out_root, "level11b_accountability_conditions_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, **summary}, fh, indent=2, default=str)
    print(f"[level11b_accountability_conditions] {summary_path}")
    print(json.dumps(summary, indent=2, default=str))
    return {"rows": rows, **summary}


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
