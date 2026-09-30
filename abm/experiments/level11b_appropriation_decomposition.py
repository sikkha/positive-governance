#!/usr/bin/env python3
"""Level 1.1b, Work Package D: appropriation opportunity-vs-conduct
decomposition.

Level 1.1's `level11_no_admin_cost` ablation found that removing
administrative cost increased total appropriated resources
(docs/level1.1_scientific_note.md §5) but could not say whether that
reflected a change in *opportunity* (more/larger funds available to
appropriate from) or *conduct* (delegates more willing to attempt, or
attempting a larger fraction, once cost was zero) -- because the pre-
1.1b `AppropriationEvent` only fires on an actual appropriation.

This script runs matched-seed (mechanism_substreams) contrasts of
level11_complete vs. level11_no_admin_cost, and separately reports:

* opportunity (O_t): count of AppropriationOpportunityEvent rows
  (fund > 0 while discretion is enabled) -- did opportunity even change?
* attempt propensity: fraction of opportunities where attempted=True
  -- did conduct's *willingness* change?
* conditional intensity: mean fraction_of_opportunity among attempts
  -- did conduct's *magnitude* change, given an attempt happened?
* net appropriation: total realized_amount summed across the run.

Per this milestone's explicit instruction: reduced/increased net
appropriation must never be described as "improved/worsened ethics"
unless attempt propensity or conditional intensity actually changed --
a change in opportunity alone (funds larger because nothing was spent
maintaining the rule) with unchanged propensity/intensity is a resource-
availability effect, not a behavioral one.
"""

from __future__ import annotations

import json
import os

import numpy as np

from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation

#: Fixed seed for the bootstrap RESAMPLING procedure itself (Section 13:
#: seed-clustered bootstrap, seed as the primary independent unit) --
#: unrelated to, and does not affect, any SimulationConfig.seed used to
#: generate the underlying runs.
BOOTSTRAP_SEED = 20261
N_BOOTSTRAP = 5000

N_SEEDS = 12
POPULATION_SIZE = 40
N_PATCHES = 3
N_STEPS = 300


def _decompose(config: SimulationConfig) -> dict:
    log = Simulation(config).run().event_log
    opps = log.appropriation_opportunities
    n_opportunities = len(opps)
    n_attempts = sum(1 for o in opps if o.attempted)
    total_realized = sum(o.realized_amount for o in opps)
    attempted_fractions = [o.fraction_of_opportunity for o in opps if o.attempted]
    return {
        "n_opportunities": n_opportunities,
        "n_attempts": n_attempts,
        "attempt_propensity_given_opportunity": (n_attempts / n_opportunities) if n_opportunities else None,
        "mean_conditional_intensity_given_attempt": (
            sum(attempted_fractions) / len(attempted_fractions) if attempted_fractions else None
        ),
        "total_realized_appropriation": total_realized,
        "mean_fund_before_at_opportunity": (
            sum(o.fund_before for o in opps) / n_opportunities if n_opportunities else None
        ),
    }


def _paired_seed_clustered_bootstrap(rows: list, field: str, n_bootstrap: int = N_BOOTSTRAP) -> dict:
    """Seed is the primary independent unit (Section 13): resample seeds
    with replacement, and for each bootstrap sample compute the mean
    paired difference (no_admin_cost - baseline) across the resampled
    seeds. Returns the point estimate and a 95% percentile interval."""
    by_seed = {}
    for r in rows:
        by_seed.setdefault(r["seed"], {})[r["condition"]] = r[field]
    seeds = sorted(by_seed.keys())
    paired_diffs = np.array([
        by_seed[s]["no_admin_cost"] - by_seed[s]["baseline_level11_complete"]
        for s in seeds
        if by_seed[s].get("no_admin_cost") is not None and by_seed[s].get("baseline_level11_complete") is not None
    ])
    if len(paired_diffs) == 0:
        return {"point_estimate": None, "ci_low": None, "ci_high": None, "n_seeds": 0}
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    boot_means = np.array([
        rng.choice(paired_diffs, size=len(paired_diffs), replace=True).mean() for _ in range(n_bootstrap)
    ])
    return {
        "point_estimate": float(paired_diffs.mean()),
        "ci_low": float(np.percentile(boot_means, 2.5)),
        "ci_high": float(np.percentile(boot_means, 97.5)),
        "n_seeds": len(paired_diffs),
    }


def run(out_root: str = "outputs/level11b_appropriation_decomposition", n_seeds: int = N_SEEDS) -> dict:
    os.makedirs(out_root, exist_ok=True)
    rows = []
    for seed in range(n_seeds):
        base_kwargs = dict(
            population_size=POPULATION_SIZE, n_patches=N_PATCHES, n_steps=N_STEPS, seed=seed,
            rng_mode="mechanism_substreams",
        )
        for label, cfg in (
            ("baseline_level11_complete", SimulationConfig.level11_complete(**base_kwargs)),
            ("no_admin_cost", SimulationConfig.level11_no_admin_cost(**base_kwargs)),
        ):
            row = {"seed": seed, "condition": label}
            row.update(_decompose(cfg))
            rows.append(row)

    def _agg(label, field):
        vals = [r[field] for r in rows if r["condition"] == label and r[field] is not None]
        return (sum(vals) / len(vals)) if vals else None

    fields = [
        "n_opportunities", "n_attempts", "attempt_propensity_given_opportunity",
        "mean_conditional_intensity_given_attempt", "total_realized_appropriation",
        "mean_fund_before_at_opportunity",
    ]
    summary = {
        "design": {"n_seeds": n_seeds, "population_size": POPULATION_SIZE, "n_patches": N_PATCHES, "n_steps": N_STEPS},
        "mean_by_condition": {
            label: {f: _agg(label, f) for f in fields}
            for label in ("baseline_level11_complete", "no_admin_cost")
        },
    }
    summary["paired_seed_clustered_bootstrap_no_admin_cost_minus_baseline"] = {
        f: _paired_seed_clustered_bootstrap(rows, f) for f in fields
    }
    b = summary["mean_by_condition"]["baseline_level11_complete"]
    n = summary["mean_by_condition"]["no_admin_cost"]
    summary["interpretation"] = (
        f"opportunity (mean n_opportunities/seed): baseline={b['n_opportunities']:.2f} vs. "
        f"no_admin_cost={n['n_opportunities']:.2f}. "
        f"conduct/attempt-propensity: baseline={b['attempt_propensity_given_opportunity']}, "
        f"no_admin_cost={n['attempt_propensity_given_opportunity']}. "
        f"conduct/conditional-intensity: baseline={b['mean_conditional_intensity_given_attempt']}, "
        f"no_admin_cost={n['mean_conditional_intensity_given_attempt']}. "
        f"net realized appropriation/seed: baseline={b['total_realized_appropriation']:.3f}, "
        f"no_admin_cost={n['total_realized_appropriation']:.3f}. "
        "See docs/level1.1b_validation_note.md for the seed-clustered-bootstrap confirmatory "
        "read of these point estimates and the explicit opportunity-vs-conduct verdict."
    )
    summary_path = os.path.join(out_root, "level11b_appropriation_decomposition_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, **summary}, fh, indent=2, default=str)
    print(f"[level11b_appropriation_decomposition] {summary_path}")
    print(json.dumps(summary, indent=2, default=str))
    return {"rows": rows, **summary}


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
