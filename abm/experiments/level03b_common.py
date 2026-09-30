"""Level 0.3b: shared helpers used by every Work Package D-K confirmatory
script. Centralized here so every downstream script builds configs,
captures ecological-policy composition, and computes continuous outcomes
identically -- the milestone brief's explicit concern about aggregation
artifacts applies just as much to *this* milestone's own machinery as to
Level 0.3's, so there is exactly one implementation of each, not one
lightly-diverged copy per script.
"""

from __future__ import annotations

import json
import math

import numpy as np

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.regulation_diagnostics import classify_regime
from experiments.niche_phase_search import _INT_PARAMS

BURN_IN_FRACTION = 0.2

#: Work Package F's seven required primary conditions, plus the preserved
#: (relabeled) Level 0.3 "no_effect" condition. Each maps to a dict of
#: ``SimulationConfig`` field overrides applied *on top of* the
#: candidate's own endogenous-condition parameters.
CONDITION_OVERRIDES = {
    "endogenous": {},
    "frozen": {"ecological_imitation_enabled": False, "ecological_mutation_rate": 0.0},
    "randomized": {"ecological_policy_randomized_each_step": True},
    "shuffled": {"ecological_policy_shuffle": True},
    "environment_only": {
        # Patch regeneration proceeds untouched; agents' extraction/
        # maintenance requests are structurally zero (unit=0 => h=m=0 for
        # every agent regardless of policy -- see
        # agents/ecological_policy.py::decide_ecological_action), so
        # there is no agent ecological payoff to separately disable. This
        # is the genuine environmental baseline, not a behaviorally
        # matched society with its impact switched off (that is
        # "impact_disabled" below).
        "ecological_harvest_unit": 0.0,
        "ecological_maintenance_unit": 0.0,
        "ecological_search_cost": 0.0,
    },
    "impact_disabled": {
        # Preserves Level 0.3's original "no_effect" WP-F condition
        # (ecological_actions_affect_patch=False): agents still decide,
        # still pay maintenance investment cost, still receive extraction
        # gain on their own ledger exactly as the same allocation
        # arithmetic would compute -- but the patch's own stock is left
        # untouched by either (only natural regeneration runs on the
        # patch side). Relabeled from "no_effect" per the milestone's
        # explicit instruction: agent-resource accounting stays
        # meaningful (it is still the same pure allocate_extraction
        # arithmetic), but patch-resource accounting is deliberately
        # disconnected from agent action -- this is an artificial
        # counterfactual, not a claim of a physically conserved economy.
        "ecological_actions_affect_patch": False,
    },
    "maintenance_disabled": {
        # ecological_maintenance_unit=0 => m=0 for every agent regardless
        # of maintenance_propensity (see decide_ecological_action) --
        # extraction is unaffected. Isolates whether the maintenance
        # channel specifically matters, independent of imitation/mutation.
        "ecological_maintenance_unit": 0.0,
    },
    "ecological_mutation_disabled": {
        # Imitation stays active; only mutation is switched off --
        # distinct from "frozen" (which disables both).
        "ecological_mutation_rate": 0.0,
    },
}

#: The milestone's required primary condition set (Work Package F §11).
PRIMARY_CONDITIONS = (
    "endogenous", "frozen", "randomized", "shuffled",
    "environment_only", "maintenance_disabled", "ecological_mutation_disabled",
)


def load_candidate_registry(path: str = "outputs/level03b_candidate_registry/candidate_registry.json") -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_candidate_config(
    params: dict,
    seed: int,
    n_steps: int,
    condition: str = "endogenous",
    mean_degree: int = 4,
) -> SimulationConfig:
    """Builds the ``endogenous`` (or any named counterfactual) config for
    one candidate's registered parameters. ``params`` is the candidate
    registry's own ``parameters`` dict (plain Python types)."""
    n_patches = max(1, int(params["n_patches"]))
    population_size = max(n_patches, int(params["population_size"]))
    md = min(mean_degree, population_size - 1)
    kwargs = dict(
        seed=seed,
        n_steps=n_steps,
        ecology_topology="patches",
        population_size=population_size,
        mean_degree=md,
        n_patches=n_patches,
        patch_regen_rate=float(params["patch_regen_rate"]),
        patch_capacity=float(params["patch_capacity"]),
        ecological_harvest_unit=float(params["ecological_harvest_unit"]),
        ecological_search_cost=float(params["ecological_search_cost"]),
        ecological_maintenance_unit=float(params["ecological_maintenance_unit"]),
        maintenance_efficiency=float(params["maintenance_efficiency"]),
        ecological_mutation_rate=float(params["ecological_mutation_rate"]),
        scarcity_sensitivity_mean=float(params["scarcity_sensitivity_mean"]),
        fitness_mode=str(params["fitness_mode"]),
        fitness_mode_ecological=str(params["fitness_mode"]),
    )
    kwargs.update(CONDITION_OVERRIDES.get(condition, {}))
    return SimulationConfig(**kwargs)


def initial_composition(sim) -> dict:
    """Mean ecological-policy traits and social-policy counts *before*
    ``run()`` mutates anything -- mirrors
    ``niche_viability_threshold_sweep.py``'s established "before" capture."""
    ext = [a.ecological_policy.extraction_propensity for a in sim.agents]
    mnt = [a.ecological_policy.maintenance_propensity for a in sim.agents]
    scr = [a.ecological_policy.scarcity_sensitivity for a in sim.agents]
    return {
        "n_agents": len(sim.agents),
        "extraction_propensity_mean": float(np.mean(ext)) if ext else math.nan,
        "maintenance_propensity_mean": float(np.mean(mnt)) if mnt else math.nan,
        "scarcity_sensitivity_mean": float(np.mean(scr)) if scr else math.nan,
    }


def final_composition(result) -> dict:
    """Same, from the final *living* population."""
    alive = [a for a in result.final_agents if getattr(a, "alive", True)]
    ext = [a.ecological_policy.extraction_propensity for a in alive]
    mnt = [a.ecological_policy.maintenance_propensity for a in alive]
    scr = [a.ecological_policy.scarcity_sensitivity for a in alive]
    return {
        "n_agents": len(alive),
        "extraction_propensity_mean": float(np.mean(ext)) if ext else math.nan,
        "maintenance_propensity_mean": float(np.mean(mnt)) if mnt else math.nan,
        "scarcity_sensitivity_mean": float(np.mean(scr)) if scr else math.nan,
    }


def continuous_outcomes(result, burn_in_fraction: float = BURN_IN_FRACTION) -> dict:
    """Work Package G's required continuous outcome set, computed from one
    already-run ``SimulationResult``. Every outcome is a plain float
    (``math.nan`` on a degenerate/empty series, never a fabricated value)."""
    metrics = result.metrics
    n = len(metrics)
    start = int(round(burn_in_fraction * n)) if n else 0
    post = metrics[start:]

    occupancy = np.array([m["aggregate_fraction_of_capacity"] for m in post], dtype=float)
    depleted_frac = np.array([m.get("fraction_patches_depleted", math.nan) for m in post], dtype=float)
    abundant_frac = np.array([m.get("fraction_patches_abundant", math.nan) for m in post], dtype=float)
    gini = np.array([m.get("patch_occupancy_spatial_gini", math.nan) for m in post], dtype=float)
    extraction = np.array([m.get("ecological_actual_extraction_total", math.nan) for m in post], dtype=float)
    maintenance_eff = np.array([m.get("ecological_maintenance_effective_total", math.nan) for m in post], dtype=float)
    shortfall = np.array([m.get("ecological_extraction_shortfall_total", math.nan) for m in post], dtype=float)

    classification = classify_regime(occupancy, burn_in_fraction=0.0)  # already burn-in-excluded above

    def _nanmean(a):
        return float(np.nanmean(a)) if len(a) and not np.all(np.isnan(a)) else math.nan

    def _nansum(a):
        return float(np.nansum(a)) if len(a) and not np.all(np.isnan(a)) else math.nan

    n_patches_final = post[-1].get("n_patches", math.nan) if post else math.nan
    n_depleted_final = post[-1].get("n_patches_depleted", math.nan) if post else math.nan
    patch_survival_fraction = (
        1.0 - (n_depleted_final / n_patches_final)
        if post and n_patches_final and not math.isnan(n_patches_final) and n_patches_final > 0
        else math.nan
    )

    cumulative_extraction = _nansum(extraction)
    cumulative_maintenance = _nansum(maintenance_eff)
    return {
        "post_burn_in_mean_occupancy": _nanmean(occupancy),
        "terminal_window_mean_occupancy": float(np.mean(occupancy[-min(20, len(occupancy)):])) if len(occupancy) else math.nan,
        "post_burn_in_min_occupancy": float(np.min(occupancy)) if len(occupancy) else math.nan,
        "cumulative_depletion_duration_steps": float(np.sum(occupancy <= 0.05)) if len(occupancy) else math.nan,
        "area_under_occupancy_curve": _nansum(occupancy),
        "patch_survival_fraction": patch_survival_fraction,
        "cumulative_unmet_demand": _nansum(shortfall),
        "cumulative_extraction": cumulative_extraction,
        "cumulative_effective_maintenance": cumulative_maintenance,
        "maintenance_to_extraction_ratio": (
            cumulative_maintenance / cumulative_extraction
            if cumulative_extraction and not math.isnan(cumulative_extraction) and cumulative_extraction > 0
            else math.nan
        ),
        "mean_patch_occupancy_gini": _nanmean(gini),
        "mean_fraction_patches_depleted": _nanmean(depleted_frac),
        "mean_fraction_patches_abundant": _nanmean(abundant_frac),
        "classify_regime_label": classification["label"],
        "classify_regime": classification,
    }
