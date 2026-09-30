"""Level 1.1, Work Package A: unit-of-analysis and denominator audit.

Level 1.0 (and every earlier milestone) frequently reports patch-runs,
but patches are nested within seeds, and seeds are nested within
parameter points. Treating patches within the same seed as independent
experimental replicates understates uncertainty — the same seed's patches
share a single realized RNG trajectory's population-level draws (network
structure, imitation events, shocks), so they are correlated, not
independent. This module gives every Level 1.1 experiment script (and,
retroactively, a Level 1.0 audit supplement — see
``docs/level1.0_audit_supplement.md``) a reusable, tested way to declare
which unit is the actual independent replicate and to compute confidence
intervals that respect that nesting.

Nothing here is generative-layer code — pure functions over already-
collected numeric data (arrays, DataFrames), read-only, exactly like
every other observer module.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

#: The nesting this project's experiments actually use, coarsest to
#: finest — declared once so every script names units the same way.
UNIT_HIERARCHY = ("experimental_condition", "parameter_point", "seed_run", "patch_run", "rule_instance", "event")


@dataclass(frozen=True)
class ReplicationUnits:
    """One denominator per level of the nesting actually present in a
    given dataset — exported alongside every rate this project reports
    (Section 8 requirement 4: "Always show: n parameter points; n seeds;
    n patches; n eligible institutions; n events; missing denominator
    counts")."""

    n_events: int = 0
    n_rule_instances: int = 0
    n_patches: int = 0
    n_patch_runs: int = 0
    n_seed_runs: int = 0
    n_parameter_points: int = 0
    n_conditions: int = 1
    n_missing: int = 0

    def as_dict(self) -> dict:
        return {
            "n_events": self.n_events, "n_rule_instances": self.n_rule_instances,
            "n_patches": self.n_patches, "n_patch_runs": self.n_patch_runs,
            "n_seed_runs": self.n_seed_runs, "n_parameter_points": self.n_parameter_points,
            "n_conditions": self.n_conditions, "n_missing": self.n_missing,
        }


def count_denominators(
    *,
    events: int = 0,
    rule_instances: int = 0,
    patches: int = 0,
    patch_runs: int = 0,
    seed_runs: int = 0,
    parameter_points: int = 0,
    conditions: int = 1,
    missing: int = 0,
) -> ReplicationUnits:
    """Thin, explicit constructor — kept as its own function (rather than
    calling ``ReplicationUnits(...)`` directly everywhere) so every call
    site names its denominators as keyword arguments, making a missing
    one impossible to overlook silently."""
    return ReplicationUnits(
        n_events=events, n_rule_instances=rule_instances, n_patches=patches, n_patch_runs=patch_runs,
        n_seed_runs=seed_runs, n_parameter_points=parameter_points, n_conditions=conditions, n_missing=missing,
    )


# ---------------------------------------------------------------------------
# Bootstrap confidence intervals: naive (for comparison only), seed-
# clustered, and hierarchical (parameter point -> seed -> patch).
# ---------------------------------------------------------------------------
def naive_pooled_bootstrap_ci(
    values: list[float] | np.ndarray,
    n_boot: int = 2000,
    ci: float = 0.95,
    rng: np.random.Generator | None = None,
    statistic=np.mean,
) -> dict:
    """An ordinary bootstrap over *pooled* values (e.g. every patch-run
    across every seed, treated as if independently exchangeable) —
    provided **only** as the incorrect comparison Work Package A
    requirement 5 asks for ("naive patch-level confidence intervals are
    incorrectly narrow"), never as this project's own recommended
    method. See :func:`seed_clustered_bootstrap_ci` for the corrected
    version."""
    rng = rng or np.random.default_rng(0)
    values = np.asarray([v for v in values if v is not None and not (isinstance(v, float) and np.isnan(v))], dtype=float)
    if values.size == 0:
        return {"point_estimate": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"), "n": 0, "method": "naive_pooled"}
    boot = np.empty(n_boot)
    n = values.size
    for b in range(n_boot):
        sample = values[rng.integers(0, n, size=n)]
        boot[b] = statistic(sample)
    alpha = (1.0 - ci) / 2.0
    return {
        "point_estimate": float(statistic(values)),
        "ci_low": float(np.quantile(boot, alpha)),
        "ci_high": float(np.quantile(boot, 1.0 - alpha)),
        "n": int(n),
        "method": "naive_pooled",
    }


def seed_clustered_bootstrap_ci(
    values_by_seed: dict,
    n_boot: int = 2000,
    ci: float = 0.95,
    rng: np.random.Generator | None = None,
    within_seed_statistic=np.mean,
    across_seed_statistic=np.mean,
) -> dict:
    """The corrected unit of analysis (Work Package A requirement 1-2):
    resample *seeds* with replacement (the actual independent
    experimental unit), aggregating each resampled seed's own patch-runs
    with ``within_seed_statistic`` first — patches within a seed are
    never independently resampled. ``values_by_seed`` maps
    ``seed -> list[float]`` (that seed's patch-run-level values, may
    contain NaN, which is dropped within each seed before aggregation)."""
    rng = rng or np.random.default_rng(0)
    seed_ids = list(values_by_seed.keys())
    seed_means = []
    for sid in seed_ids:
        vals = np.asarray(
            [v for v in values_by_seed[sid] if v is not None and not (isinstance(v, float) and np.isnan(v))],
            dtype=float,
        )
        if vals.size == 0:
            continue
        seed_means.append(float(within_seed_statistic(vals)))
    seed_means = np.asarray(seed_means, dtype=float)
    if seed_means.size == 0:
        return {
            "point_estimate": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"),
            "n_seeds": 0, "method": "seed_clustered",
        }
    n_seeds = seed_means.size
    boot = np.empty(n_boot)
    for b in range(n_boot):
        sample = seed_means[rng.integers(0, n_seeds, size=n_seeds)]
        boot[b] = across_seed_statistic(sample)
    alpha = (1.0 - ci) / 2.0
    return {
        "point_estimate": float(across_seed_statistic(seed_means)),
        "ci_low": float(np.quantile(boot, alpha)),
        "ci_high": float(np.quantile(boot, 1.0 - alpha)),
        "n_seeds": int(n_seeds),
        "method": "seed_clustered",
    }


def hierarchical_bootstrap_ci(
    nested_values: dict,
    n_boot: int = 2000,
    ci: float = 0.95,
    rng: np.random.Generator | None = None,
) -> dict:
    """Three-level hierarchical bootstrap: parameter point -> seed ->
    patch (Work Package A requirement 3). ``nested_values`` maps
    ``parameter_point -> {seed -> [patch_run_values]}``. Each bootstrap
    replicate resamples parameter points with replacement, then within
    each resampled point resamples seeds with replacement, then within
    each resampled seed resamples patch-runs with replacement — the full
    nesting, rather than collapsing any one level early."""
    rng = rng or np.random.default_rng(0)
    point_ids = list(nested_values.keys())
    if not point_ids:
        return {"point_estimate": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"), "n_points": 0, "method": "hierarchical"}

    def _point_mean(point_id) -> float | None:
        seed_dict = nested_values[point_id]
        seed_ids = list(seed_dict.keys())
        if not seed_ids:
            return None
        resampled_seed_ids = [seed_ids[i] for i in rng.integers(0, len(seed_ids), size=len(seed_ids))]
        seed_level_means = []
        for sid in resampled_seed_ids:
            patch_vals = np.asarray(
                [v for v in seed_dict[sid] if v is not None and not (isinstance(v, float) and np.isnan(v))], dtype=float,
            )
            if patch_vals.size == 0:
                continue
            resampled_patches = patch_vals[rng.integers(0, patch_vals.size, size=patch_vals.size)]
            seed_level_means.append(float(np.mean(resampled_patches)))
        if not seed_level_means:
            return None
        return float(np.mean(seed_level_means))

    # Point estimate: no resampling, plain nested means.
    plain_point_means = []
    for pid in point_ids:
        seed_dict = nested_values[pid]
        seed_means = []
        for sid, vals in seed_dict.items():
            arr = np.asarray([v for v in vals if v is not None and not (isinstance(v, float) and np.isnan(v))], dtype=float)
            if arr.size:
                seed_means.append(float(np.mean(arr)))
        if seed_means:
            plain_point_means.append(float(np.mean(seed_means)))
    point_estimate = float(np.mean(plain_point_means)) if plain_point_means else float("nan")

    boot = []
    for _ in range(n_boot):
        resampled_point_ids = [point_ids[i] for i in rng.integers(0, len(point_ids), size=len(point_ids))]
        point_means = [m for m in (_point_mean(pid) for pid in resampled_point_ids) if m is not None]
        if point_means:
            boot.append(float(np.mean(point_means)))
    if not boot:
        return {
            "point_estimate": point_estimate, "ci_low": float("nan"), "ci_high": float("nan"),
            "n_points": len(point_ids), "method": "hierarchical",
        }
    boot_arr = np.asarray(boot, dtype=float)
    alpha = (1.0 - ci) / 2.0
    return {
        "point_estimate": point_estimate,
        "ci_low": float(np.quantile(boot_arr, alpha)),
        "ci_high": float(np.quantile(boot_arr, 1.0 - alpha)),
        "n_points": len(point_ids),
        "method": "hierarchical",
    }
