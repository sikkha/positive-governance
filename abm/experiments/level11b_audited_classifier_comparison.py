#!/usr/bin/env python3
"""Level 1.1b, Work Package H: audited classifier vs. historical
classifier.

Level 1.1's `observer/delegation_diagnostics.classify_delegation`
("the historical classifier") labels a rule "accountable_delegation"
whenever misconduct occurred AND a recall vote succeeded OR an appeal
was upheld -- without checking whether the recall/audit that triggered
it was a REALIZED true-positive detection, and without checking whether
an upheld appeal was a genuinely corrective outcome
(`was_false_sanction=True`) rather than an unjustified overturn of a
real sanction. Work Package E's `effective_constraint` observer function
exists precisely to make this distinction; Work Package H's job is to
apply that same ground-truth standard to the classifier itself
(`classify_delegation_audited`, `observer/delegation_diagnostics.py`)
and measure how often the two classifiers actually disagree, across the
same accountability conditions Work Package E already characterized.

This script runs matched seeds across six accountability conditions
(the same named presets from `experiments/level11b_accountability_conditions.py`,
minus `no_accountability`/`appeal_only` which cannot reach
"accountable_delegation" by construction -- appeal_only has no audits at
all, so realized_accountability is always False there for both
classifiers, an uninformative comparison), classifies every patch's
rule under BOTH classifiers, and reports:

* n_historical_accountable / n_audited_accountable per condition (does
  the audited classifier assign "accountable_delegation" less often?)
* n_downgraded: rules the historical classifier called
  "accountable_delegation" that the audited classifier does NOT (the
  key quantity -- historical-classifier accountability claims the
  ground-truth-corrected classifier does not support).
* downgrade_rate = n_downgraded / n_historical_accountable (`None` when
  the historical classifier never called anything "accountable" in that
  condition at all -- an undefined rate, never coerced to 0).

Expectation this script tests rather than assumes: the downgrade rate
should be small under `perfect_info` (a true-positive detection nearly
always accompanies whatever the historical classifier already counted)
and larger under `randomized_placebo` (audit_accuracy=0.5 means many
recalls/appeals the historical classifier credits were not actually
grounded in a real detection) -- if the data does not show this pattern,
that is reported as found, not assumed into the write-up.
"""

from __future__ import annotations

import json
import os

import numpy as np

from abm_governance.core.config import SimulationConfig
from abm_governance.observer import delegation_diagnostics as dd
from abm_governance.simulation import Simulation
from experiments.level11_common import all_delegates, all_links, all_rules

BOOTSTRAP_SEED = 20265  # distinct from WP-D/E/F/G's 20261-20264
N_BOOTSTRAP = 5000

#: n_patches is scaled up from other WP-D/E/F/G scripts' default of 3
#: specifically because this script's unit of classification is "one
#: label per patch's rule lineage per run" (see ``experiments/
#: level11_common.py::run_and_summarize``'s own convention) -- more
#: patches means more independent classified-rule datapoints per run,
#: which this comparison's downgrade-rate denominators need.
N_SEEDS = 15
POPULATION_SIZE = 60
N_PATCHES = 6
N_STEPS = 300

CONDITIONS = {
    "default_full": SimulationConfig.level11b_substreams,
    "audit_only": SimulationConfig.level11b_accountability_audit_only,
    "recall_only": SimulationConfig.level11b_accountability_recall_only,
    "costless": SimulationConfig.level11b_accountability_costless,
    "perfect_info": SimulationConfig.level11b_accountability_perfect_info,
    "randomized_placebo": SimulationConfig.level11b_accountability_randomized_placebo,
}


def _classify_all_rules(config: SimulationConfig) -> dict:
    sim = Simulation(config)
    sim.run()
    final_step = config.n_steps - 1
    rules = all_rules(sim)
    delegates = all_delegates(sim)
    links = all_links(sim)

    n_historical_accountable = 0
    n_audited_accountable = 0
    n_downgraded = 0  # historical == accountable_delegation, audited != accountable_delegation
    n_upgraded = 0  # the reverse -- audited says accountable, historical doesn't (sanity: should be 0/rare)
    n_rules_classified = 0
    label_pairs = []

    for pid in sim.patch_system.patches:
        rule = sim.rule_registry.get(pid) or sim._last_dissolved_rule_by_patch.get(pid)
        rule_lineage_id = rule.rule_lineage_id if rule is not None else None
        delegates_at_rule = [d for d in delegates if rule_lineage_id is not None and d.rule_lineage_id == rule_lineage_id]
        links_at_rule = [ln for ln in links if rule is not None and pid in (ln.patch_id_a, ln.patch_id_b)]

        historical = dd.classify_delegation(rule, delegates_at_rule, links_at_rule, sim.event_log, final_step)
        audited = dd.classify_delegation_audited(rule, delegates_at_rule, links_at_rule, sim.event_log, final_step)
        n_rules_classified += 1
        label_pairs.append((historical["label"], audited["label"]))

        if historical["label"] == "accountable_delegation":
            n_historical_accountable += 1
            if audited["label"] != "accountable_delegation":
                n_downgraded += 1
        if audited["label"] == "accountable_delegation":
            n_audited_accountable += 1
            if historical["label"] != "accountable_delegation":
                n_upgraded += 1

    n_agree = sum(1 for h, a in label_pairs if h == a)

    return {
        "n_rules_classified": n_rules_classified,
        "n_agree": n_agree,
        "agreement_rate": (n_agree / n_rules_classified) if n_rules_classified else None,
        "n_historical_accountable": n_historical_accountable,
        "n_audited_accountable": n_audited_accountable,
        "n_downgraded": n_downgraded,
        "n_upgraded": n_upgraded,
        "downgrade_rate": (n_downgraded / n_historical_accountable) if n_historical_accountable else None,
    }


def _seed_clustered_bootstrap_single_sample(per_seed_values: list, n_bootstrap: int = N_BOOTSTRAP) -> dict:
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


def run(out_root: str = "outputs/level11b_audited_classifier_comparison", n_seeds: int = N_SEEDS) -> dict:
    os.makedirs(out_root, exist_ok=True)
    rows = []
    for seed in range(n_seeds):
        base_kwargs = dict(population_size=POPULATION_SIZE, n_patches=N_PATCHES, n_steps=N_STEPS, seed=seed)
        for label, builder in CONDITIONS.items():
            cfg = builder(**base_kwargs)
            row = {"seed": seed, "condition": label}
            row.update(_classify_all_rules(cfg))
            rows.append(row)

    fields = [
        "n_rules_classified", "n_agree", "agreement_rate", "n_historical_accountable",
        "n_audited_accountable", "n_downgraded", "n_upgraded", "downgrade_rate",
    ]
    per_condition_bootstrap = {
        cond: {f: _seed_clustered_bootstrap_single_sample([r[f] for r in rows if r["condition"] == cond]) for f in fields}
        for cond in CONDITIONS
    }

    pooled = {}
    for cond in CONDITIONS:
        cond_rows = [r for r in rows if r["condition"] == cond]
        total_hist_accountable = sum(r["n_historical_accountable"] for r in cond_rows)
        total_downgraded = sum(r["n_downgraded"] for r in cond_rows)
        pooled[cond] = {
            "total_rules_classified": sum(r["n_rules_classified"] for r in cond_rows),
            "total_historical_accountable": total_hist_accountable,
            "total_audited_accountable": sum(r["n_audited_accountable"] for r in cond_rows),
            "total_downgraded": total_downgraded,
            "pooled_downgrade_rate": (total_downgraded / total_hist_accountable) if total_hist_accountable else None,
        }

    summary = {
        "design": {
            "n_seeds": n_seeds, "population_size": POPULATION_SIZE, "n_patches": N_PATCHES, "n_steps": N_STEPS,
            "conditions": list(CONDITIONS.keys()),
        },
        "per_condition_seed_clustered_bootstrap": per_condition_bootstrap,
        "pooled_by_condition": pooled,
    }

    lines = []
    for cond in CONDITIONS:
        p = pooled[cond]
        b = per_condition_bootstrap[cond]["downgrade_rate"]
        lines.append(
            f"{cond}: pooled downgrade_rate={p['pooled_downgrade_rate']} "
            f"({p['total_downgraded']}/{p['total_historical_accountable']} historical-'accountable_delegation' "
            f"rules the audited classifier does NOT also call accountable), seed-clustered "
            f"point={b['point_estimate']}, CI=[{b['ci_low']}, {b['ci_high']}] over n_seeds={b['n_seeds']}"
            f" (n_seeds_skipped_undefined={b['n_seeds_skipped_undefined']}, i.e. seeds where the historical "
            "classifier never called anything accountable in this condition)."
        )
    summary["interpretation"] = (
        "Per-condition downgrade rate (fraction of the historical classifier's own "
        "'accountable_delegation' calls that the ground-truth-corrected audited classifier does not "
        "support): " + " | ".join(lines) + " Read the ordering of these rates across conditions directly "
        "-- this text does not assert that perfect_info's rate is lower than randomized_placebo's or by how "
        "much, since that must be read from the actual numbers above, including whether the conditions' CIs "
        "overlap, not asserted in advance. See docs/level1.1b_validation_note.md for the confirmatory read "
        "and this milestone's final recommendation on which classifier (or explicit disclosure of both) "
        "Level 1.2 should use."
    )

    summary_path = os.path.join(out_root, "level11b_audited_classifier_comparison_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, **summary}, fh, indent=2, default=str)
    print(f"[level11b_audited_classifier_comparison] {summary_path}")
    print(json.dumps(summary, indent=2, default=str))
    return {"rows": rows, **summary}


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
