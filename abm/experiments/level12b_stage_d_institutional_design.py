#!/usr/bin/env python3
"""Level 1.2b, Work Package D (Section 8): institutional search design.

A space-filling (Latin Hypercube) sample over institutional/mechanism
parameters, generated and hashed BEFORE any ecological crossing (Work
Package E) or any simulation run. Section 8 is explicit: no 3 packages,
no selection by resemblance to any expected trajectory, and weak/
moderate/strong values used only as a documented sampling range, never
bundled into a normative "package" (there is no `_build_package()`
function here, only independent per-dimension draws — every one of the
21 dimensions below varies on its own Latin Hypercube axis, never in a
fixed bundle with any other).

**Section 8's named dimensions -> config fields** (21 total; Section 8
names slightly fewer conceptual categories, several of which this model
represents with more than one config field — every mapping is disclosed
here, none tuned to produce any particular outcome):

- proposal/adoption thresholds -> ``proposal_probability_mean``,
  ``preferred_adoption_threshold_mean``
- delegation probability -> ``delegate_selection_support_threshold``
- authority concentration -> ``appropriation_opportunity_scale``
  (how much unilateral action a delegate is enabled to take, distinct
  from ``appropriation_fraction_of_fund``'s own "appropriation params"
  role below)
- admin learning -> ``delegation_capacity_learning_weight``
- memory retention/transfer -> ``institutional_memory_retention``,
  ``institutional_memory_transfer_to_new_delegate``
- monitoring allocation -> ``willingness_to_monitor_mean``
- detection accuracy -> ``monitoring_detection_accuracy``
- appeal/recall thresholds -> ``appeal_probability``,
  ``recall_support_threshold``
- contribution params -> ``contribution_proportional_rate``
- appropriation params -> ``appropriation_fraction_of_fund``
- transmission fidelity -> ``transmission_failure_probability``
  (inverse framing: HIGHER failure probability is LOWER fidelity,
  disclosed here rather than inverting the axis silently)
- mutation -> ``transmission_mutation_std``
- recombination -> ``transmission_recombination_probability``
- migration sensitivity -> ``migration_propensity_mean``
- coordination acceptance -> ``coordination_proposal_probability``
- coordination retry -> ``coordination_proposal_window_steps``
- scaling cost -> ``scaling_admin_overhead_per_patch``
- admin overload -> ``delegation_scale_coefficient``

Every mechanism flag this sample's fields belong to
(``rule_formation_enabled`` implicitly via ``level12_complete``,
``delegation_enabled``, ``discretion_enabled``, ``accountability_enabled``,
``institutional_fund_contribution_rate`` > 0 for contributions,
``interpatch_coordination_enabled``, ``institutional_transmission_enabled``,
``migration_enabled``, ``institutional_scaling_enabled``) is turned ON for
every point in this design (Section 8's "broad" framing applied to
mechanism *activation*, mirroring Work Package C's own "broad but
fixed" institutional baseline, here inverted: institutional structure is
what varies, ecology is what stays fixed at a single reasonable point
for this design's own runs, if any are needed for secondary validation).

``rng_mode="mechanism_substreams"`` is used for every config this module
builds, per Section 8's own explicit requirement."""

from __future__ import annotations

import hashlib
import json
import os

import numpy as np
from scipy.stats import qmc

from abm_governance.core.config import SimulationConfig
from abm_governance.observer import delegation_diagnostics as dd
from abm_governance.simulation import Simulation
from experiments.level11_common import all_delegates, all_links, all_rules

OUT_DIR = "outputs/level12b_stage_d_institutional_design"
N_INSTITUTIONAL_POINTS = 60
LHS_SEED = 20260818  # fixed, disclosed -- same root as Work Package C, not tuned

#: (field name, low, high) -- order fixes the Latin Hypercube's column
#: order. Every bound straddles that field's own ``SimulationConfig``
#: default. "weak/moderate/strong" is realized purely as continuous
#: position within each bound, never as three discrete labeled levels
#: and never bundled across dimensions into a package.
PARAMETER_SPACE: tuple[tuple[str, float, float], ...] = (
    ("proposal_probability_mean", 0.001, 0.15),                 # default 0.01
    ("preferred_adoption_threshold_mean", 0.1, 0.9),             # default 0.5
    ("delegate_selection_support_threshold", 0.1, 0.9),          # default 0.5
    ("appropriation_opportunity_scale", 0.0, 2.0),               # default 1.0
    ("delegation_capacity_learning_weight", 0.0, 0.8),           # default 0.3
    ("institutional_memory_retention", 0.0, 1.0),                # default 0.3
    ("institutional_memory_transfer_to_new_delegate", 0.0, 1.0), # default 0.5
    ("willingness_to_monitor_mean", 0.02, 0.9),                  # default 0.3
    ("monitoring_detection_accuracy", 0.3, 1.0),                 # default 0.8
    ("appeal_probability", 0.0, 0.9),                            # default 0.3
    ("recall_support_threshold", 0.1, 0.9),                      # default 0.5
    ("contribution_proportional_rate", 0.0, 0.15),               # default 0.02
    ("appropriation_fraction_of_fund", 0.0, 0.6),                # default 0.2
    ("transmission_failure_probability", 0.0, 0.6),              # default 0.1
    ("transmission_mutation_std", 0.0, 0.3),                     # default 0.05
    ("transmission_recombination_probability", 0.0, 0.6),        # default 0.1
    ("migration_propensity_mean", 0.0, 0.6),                     # default 0.15
    ("coordination_proposal_probability", 0.0, 0.3),             # default 0.02
    ("coordination_proposal_window_steps", 1.0, 15.0),           # default 5 (rounded to int at config-build time)
    ("scaling_admin_overhead_per_patch", -0.2, 0.5),              # default 0.05
    ("delegation_scale_coefficient", -0.3, 0.3),                 # default 0.0
)

#: A single, reasonable, non-extreme ecological point used ONLY for this
#: design's own secondary-validation runs (Section 8's "use the audited
#: Level 1.1b classifier only for secondary validation" — never for the
#: main discovery pipeline, which is Work Package E's joint design).
_SECONDARY_VALIDATION_ECOLOGY = dict(
    patch_regen_rate=0.5, patch_capacity=500.0, patch_initial_fraction=0.5,
    subsistence_cost=0.3, ecological_harvest_unit=5.0, maintenance_efficiency=0.7,
)


def build_design() -> dict:
    """Latin Hypercube sample over :data:`PARAMETER_SPACE`. Deterministic
    given :data:`LHS_SEED`."""
    sampler = qmc.LatinHypercube(d=len(PARAMETER_SPACE), seed=LHS_SEED)
    unit_sample = sampler.random(n=N_INSTITUTIONAL_POINTS)
    lows = np.array([lo for _, lo, _ in PARAMETER_SPACE])
    highs = np.array([hi for _, _, hi in PARAMETER_SPACE])
    scaled = qmc.scale(unit_sample, lows, highs)
    names = [name for name, _, _ in PARAMETER_SPACE]

    points = []
    for point_id, row in enumerate(scaled.tolist()):
        draw = dict(zip(names, row))
        points.append({"point_id": point_id, "institutional_parameters": draw})

    return {
        "milestone": "level1.2b_institutional_search_design_work_package_d",
        "n_institutional_points": N_INSTITUTIONAL_POINTS,
        "lhs_seed": LHS_SEED,
        "parameter_space": [{"field": n, "low": lo, "high": hi} for n, lo, hi in PARAMETER_SPACE],
        "points": points,
        "selection_method": "space_filling_latin_hypercube_no_resemblance_based_selection",
        "n_packages": 0,
    }


def design_hash(design: dict) -> str:
    payload = json.dumps(design, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_design(out_dir: str = OUT_DIR) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    design = build_design()
    digest = design_hash(design)
    with open(f"{out_dir}/design.json", "w") as f:
        json.dump(design, f, indent=2, sort_keys=True, default=str)
    with open(f"{out_dir}/design_hash.txt", "w") as f:
        f.write(digest + "\n")
    return {"design": design, "hash": digest}


def load_and_verify_design(out_dir: str = OUT_DIR) -> dict:
    with open(f"{out_dir}/design.json") as f:
        design = json.load(f)
    with open(f"{out_dir}/design_hash.txt") as f:
        stored_hash = f.read().strip()
    recomputed = design_hash(design)
    if recomputed != stored_hash:
        raise ValueError(
            f"Work Package D institutional design at {out_dir}/design.json has been altered "
            f"since it was frozen (stored hash {stored_hash}, recomputed hash {recomputed})."
        )
    return {"design": design, "hash": recomputed}


def build_config_for_point(
    point: dict, *, seed: int, population_size: int = 40, n_patches: int = 4, n_steps: int = 400,
) -> SimulationConfig:
    """Build a config for one institutional point at the fixed secondary-
    validation ecological point. ``coordination_proposal_window_steps``
    is rounded to the nearest int (the sampled field, before rounding,
    stays a float in the saved design)."""
    params = dict(point["institutional_parameters"])
    params["coordination_proposal_window_steps"] = int(round(params["coordination_proposal_window_steps"]))
    return SimulationConfig.level12_complete(
        population_size=population_size, n_patches=n_patches, n_steps=n_steps, seed=seed,
        delegation_enabled=True, discretion_enabled=True, accountability_enabled=True,
        interpatch_coordination_enabled=True, institutional_fund_contribution_rate=0.05,
        **_SECONDARY_VALIDATION_ECOLOGY,
        **params,
    )


# ---------------------------------------------------------------------------
# Section 8: "use the audited Level 1.1b classifier only for secondary
# validation" -- diagnostic label-diversity check only. Never used to
# select, exclude, or reweight any point; never fed into Work Package
# E's crossing with ecology.
# ---------------------------------------------------------------------------

#: A fixed subset of the 60 points, sampled deterministically (every
#: 6th point -> 10 points), used only for this secondary-validation
#: check -- not a claim these 10 are representative of anything beyond
#: "the swept space produces more than one classifier label."
_SECONDARY_VALIDATION_POINT_STRIDE = 6


def run_secondary_validation(design: dict | None = None, n_seeds: int = 2) -> dict:
    """For a fixed stride-sampled subset of institutional points, runs
    the simulation and applies BOTH the audited and historical Level
    1.1b delegation classifiers (``observer/delegation_diagnostics.py``)
    to every patch's rule, reporting label-diversity and audited-vs-
    historical disagreement counts. Diagnostic only -- Section 8 is
    explicit this may never filter or select points."""
    if design is None:
        design = build_design()
    sampled_points = design["points"][::_SECONDARY_VALIDATION_POINT_STRIDE]

    historical_labels: dict[str, int] = {}
    audited_labels: dict[str, int] = {}
    n_downgraded = 0
    n_rules_classified = 0

    for point in sampled_points:
        for seed_idx in range(n_seeds):
            seed = 8_000_000 + point["point_id"] * 100 + seed_idx
            config = build_config_for_point(point, seed=seed, population_size=24, n_patches=3, n_steps=150)
            sim = Simulation(config)
            sim.run()
            final_step = config.n_steps - 1
            rules = all_rules(sim)
            delegates = all_delegates(sim)
            links = all_links(sim)
            for pid in sim.patch_system.patches:
                rule = sim.rule_registry.get(pid) or sim._last_dissolved_rule_by_patch.get(pid)
                rule_lineage_id = rule.rule_lineage_id if rule is not None else None
                delegates_at_rule = [d for d in delegates if rule_lineage_id is not None and d.rule_lineage_id == rule_lineage_id]
                links_at_rule = [ln for ln in links if rule is not None and pid in (ln.patch_id_a, ln.patch_id_b)]
                historical = dd.classify_delegation(rule, delegates_at_rule, links_at_rule, sim.event_log, final_step)
                audited = dd.classify_delegation_audited(rule, delegates_at_rule, links_at_rule, sim.event_log, final_step)
                n_rules_classified += 1
                historical_labels[historical["label"]] = historical_labels.get(historical["label"], 0) + 1
                audited_labels[audited["label"]] = audited_labels.get(audited["label"], 0) + 1
                if historical["label"] == "accountable_delegation" and audited["label"] != "accountable_delegation":
                    n_downgraded += 1

    return {
        "n_points_sampled": len(sampled_points),
        "n_seeds_per_point": n_seeds,
        "n_rules_classified": n_rules_classified,
        "historical_label_distribution": historical_labels,
        "audited_label_distribution": audited_labels,
        "n_downgraded_historical_to_audited": n_downgraded,
        "note": "diagnostic only -- never used to select, exclude, or reweight any design point",
    }


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    result = write_design()
    print(f"Work Package D institutional design frozen at {OUT_DIR}/design.json")
    print(f"design hash: {result['hash']}")
    print(f"n_institutional_points={result['design']['n_institutional_points']}")
    validation = run_secondary_validation(result["design"])
    with open(f"{OUT_DIR}/secondary_validation.json", "w") as f:
        json.dump(validation, f, indent=2, default=str)
    print(f"secondary validation (label diversity, diagnostic only): {validation}")
