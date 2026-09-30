"""Level 1.2, Section 7: temporal phenotype representation.

Pure, read-only functions over an **already-collected** time series of
periodic ``observer/institutional_phenotype.py`` snapshots — this module
never drives a ``Simulation`` itself (that orchestration belongs to the
experiment layer, ``experiments/level12_*.py``/``experiments/level12b_*.py``,
consistent with how every prior level's experiment scripts — not the
observer package — own simulation-stepping loops). A snapshot is
``{"step": int, "vector": <institutional_phenotype_vector(...) output>}``.

**Static vs. dynamic features kept distinguishable**: functions here
return either "static" fields (a single window's mean/variance — a
property of that window alone) or "dynamic" fields (trend, lag-1
autocorrelation, transition counts, persistence, shock recovery —
properties of *change* within or across windows), and every returned
dict labels which kind it is via a ``"feature_kind"`` field, per
Section 7's own requirement, extended by Level 1.2b Work Package G
(Section 12) to explicitly require static and dynamic feature sets be
analyzable both separately and jointly — see
``group_features_by_kind`` below.

**Never clusters raw autocorrelated time rows.** This module computes
scalar SUMMARY features per window; nothing here or downstream (Section
9's discovery pipeline) clusters directly on a raw per-step time series
— every clustering input is a fixed-length feature vector.

**Reuses ``observer/regulation_diagnostics.py``'s already-built, already-
tested statistical primitives (``linear_trend``, ``autocorrelation``,
``_burn_in_window``, and — added for Work Package G — ``interior_
persistence``, ``band_transitions``, ``perturbation_recovery``) rather
than re-deriving them.** Those three additions were built for a
different milestone (Level 0.3's occupancy-regulation diagnostics) and
ship with occupancy-specific default bounds (``[0.05, 0.95]``) that do
NOT generally apply to phenotype dimensions (R can exceed 1, H is an
unbounded structural distance, etc.) — so this module never uses their
defaults. Instead, every "stability band" here is derived from the
window's OWN mean/std (a documented heuristic, disclosed as such,
consistent with this project's established register for a
reasonable-but-not-uniquely-correct choice), so the same machinery
generalizes across all ten heterogeneous dimensions without hardcoding
an occupancy-fraction assumption into a phenotype feature."""

from __future__ import annotations

import math

import numpy as np

from abm_governance.observer.regulation_diagnostics import (
    _burn_in_window,
    autocorrelation,
    band_transitions,
    interior_persistence,
    linear_trend,
    perturbation_recovery,
)

#: Section 7's named window types, extended by Work Package G (Section
#: 12) with two additions: "post_burn_in" — the *entire* post-burn-in
#: range as one window, distinct from its early/middle/late thirds,
#: needed for Section 12's own explicit "post-burn-in mean" feature;
#: and "pre_shock" — the symmetric counterpart to "post_shock", needed
#: for shock-recovery features (which compare a pre-shock baseline
#: against the post-shock series). "pre_shock"/"shock"/"post_shock"
#: require an externally-supplied shock step (this module has no
#: notion of when a perturbation occurred — that lives in
#: ``core/perturbation.py``/event log data the caller already has);
#: the rest are always computable from ``n_steps`` and
#: ``burn_in_fraction`` alone.
WINDOW_NAMES: tuple[str, ...] = (
    "post_burn_in", "early_post_burn_in", "middle", "late", "terminal", "pre_shock", "shock", "post_shock",
)


def compute_window_bounds(
    n_steps: int, burn_in_fraction: float = 0.2, terminal_fraction: float = 0.1,
    shock_step: int | None = None, post_shock_horizon: int = 20, pre_shock_horizon: int = 20,
) -> dict[str, tuple[int, int]]:
    """Splits the post-burn-in range into three equal early/middle/late
    thirds, plus a ``terminal`` window (the final ``terminal_fraction``
    of the whole run, which may overlap "late" — deliberately: terminal
    state is its own named observation per Section 7, not merely an
    alias for "late"), plus (Work Package G, Section 12) a single
    ``post_burn_in`` window spanning the whole post-burn-in range (the
    union of early + middle + late, exported separately since Section
    12 explicitly asks for a "post-burn-in mean" as its own feature,
    not just the three thirds' means individually). ``burn_in_fraction``
    must be selected before viewing any clustering results (Section 7's
    own requirement) — enforced procedurally (Stage 0 preregistration),
    not mechanically by this function."""
    burn_in_start, _ = _burn_in_window(n_steps, burn_in_fraction, None)
    post_burn_in_len = n_steps - burn_in_start
    bounds: dict[str, tuple[int, int]] = {"post_burn_in": (burn_in_start, n_steps)}
    if post_burn_in_len <= 0:
        bounds["early_post_burn_in"] = bounds["middle"] = bounds["late"] = (burn_in_start, burn_in_start)
    else:
        third = max(1, post_burn_in_len // 3)
        early_end = burn_in_start + third
        middle_end = burn_in_start + 2 * third
        bounds["early_post_burn_in"] = (burn_in_start, early_end)
        bounds["middle"] = (early_end, middle_end)
        bounds["late"] = (middle_end, n_steps)
    terminal_start = max(burn_in_start, n_steps - max(1, int(round(terminal_fraction * n_steps))))
    bounds["terminal"] = (terminal_start, n_steps)
    if shock_step is not None:
        bounds["pre_shock"] = (max(0, shock_step - pre_shock_horizon), shock_step)
        bounds["shock"] = (shock_step, shock_step + 1)
        bounds["post_shock"] = (shock_step + 1, min(n_steps, shock_step + 1 + post_shock_horizon))
    return bounds


def _extract_series(snapshots: list[dict], dimension_key: str, window: tuple[int, int]) -> tuple[list[int], list[float]]:
    start, end = window
    steps: list[float] = []
    values: list[float] = []
    for snap in snapshots:
        step = snap["step"]
        if not (start <= step < end):
            continue
        record = snap["vector"].get(dimension_key)
        if record is None:
            continue
        value = record["value"] if dimension_key != "V" else record.get("value")
        if value is None:
            continue
        steps.append(step)
        values.append(value)
    return steps, values


def window_static_features(snapshots: list[dict], dimension_key: str, window: tuple[int, int]) -> dict:
    """Static (single-window) features: mean, variance, and the
    fraction of snapshots in this window with a defined (non-NaN) value
    (Section 7's missingness-within-window transparency)."""
    _, values = _extract_series(snapshots, dimension_key, window)
    arr = np.array([v for v in values if v == v], dtype=float)  # drop NaN
    n_total = len(values)
    n_defined = len(arr)
    return {
        "feature_kind": "static",
        "window": window,
        "n_observations": n_total,
        "n_defined": n_defined,
        "missingness_fraction": (1.0 - n_defined / n_total) if n_total else float("nan"),
        "mean": float(np.mean(arr)) if n_defined else float("nan"),
        "variance": float(np.var(arr)) if n_defined else float("nan"),
    }


def window_dynamic_features(snapshots: list[dict], dimension_key: str, window: tuple[int, int]) -> dict:
    """Dynamic (change-within-window) features: linear trend
    (slope/R^2, reusing ``regulation_diagnostics.linear_trend``) and
    lag-1 autocorrelation (``NaN`` when undefined — fewer than 3 defined
    points, or a constant series where autocorrelation reports 0.0 by
    ``regulation_diagnostics.autocorrelation``'s own convention, which
    this function passes through unchanged rather than reinterpreting)."""
    _, values = _extract_series(snapshots, dimension_key, window)
    arr = [v for v in values if v == v]
    trend = linear_trend(arr)
    ac = autocorrelation(arr, max_lag=1)
    lag1 = float(ac[0]) if len(ac) >= 1 else float("nan")
    return {
        "feature_kind": "dynamic",
        "window": window,
        "trend_slope": trend["slope"],
        "trend_r_squared": trend["r_squared"],
        "lag1_autocorrelation": lag1,
    }


def window_persistence_features(
    snapshots: list[dict], dimension_key: str, window: tuple[int, int],
    band_half_width_in_stds: float = 1.0, min_dwell_steps: int = 1,
) -> dict:
    """Work Package G (Section 12): "persistence", "transition count",
    and "longest stable episode" — three related dynamic features, all
    computed against the SAME data-derived stability band (this
    window's own mean +/- ``band_half_width_in_stds`` standard
    deviations; see module docstring for why a data-derived band is
    used instead of ``regulation_diagnostics``'s occupancy-specific
    defaults). Reuses ``regulation_diagnostics.interior_persistence``
    (for ``fraction_in_band``/``longest_stable_episode_steps``) and
    ``regulation_diagnostics.band_transitions`` (for
    ``n_transitions``), rather than re-deriving either. Degenerate
    (``NaN``/``0``) when fewer than 2 defined points exist in
    ``window`` — a band's width is undefined for 0 or 1 points."""
    _, values = _extract_series(snapshots, dimension_key, window)
    arr = [v for v in values if v == v]
    n = len(arr)
    if n < 2:
        return {
            "feature_kind": "dynamic", "window": window,
            "band_lower": float("nan"), "band_upper": float("nan"),
            "fraction_in_band": float("nan"), "longest_stable_episode_steps": 0 if n == 0 else 1,
            "n_transitions": 0, "n_observations": n,
        }
    mean = float(np.mean(arr))
    std = float(np.std(arr))
    lower = mean - band_half_width_in_stds * std
    upper = mean + band_half_width_in_stds * std
    if upper <= lower:
        # a zero-variance window (every value identical): every point is
        # trivially "in band" and there is exactly one stable episode
        # spanning the whole window -- widen the band by an epsilon
        # rather than dividing by a zero-width band downstream.
        lower, upper = lower - 1e-9, upper + 1e-9
    persistence = interior_persistence(arr, lower_bound=lower, upper_bound=upper, min_duration_steps=0)
    transitions = band_transitions(arr, lower_bound=lower, upper_bound=upper, min_dwell_steps=min_dwell_steps)
    return {
        "feature_kind": "dynamic", "window": window,
        "band_lower": lower, "band_upper": upper,
        "fraction_in_band": persistence["fraction_interior"],
        "longest_stable_episode_steps": persistence["longest_interior_run"],
        "n_transitions": transitions["n_transitions"],
        "n_observations": n,
    }


def window_shock_recovery_features(
    snapshots: list[dict], dimension_key: str, shock_step: int,
    pre_shock_horizon: int = 20, post_shock_horizon: int = 20, tolerance_fraction: float = 0.1,
) -> dict:
    """Work Package G (Section 12): "shock recovery". Directly reuses
    ``regulation_diagnostics.perturbation_recovery`` (already built and
    tested for exactly this pre-shock-band/post-shock-reentry
    computation, generic over any numeric series) applied to this
    dimension's own pre-/post-shock windows (via ``compute_window_
    bounds``'s ``pre_shock``/``post_shock`` bounds). Degenerate
    (``perturbation_recovery``'s own NaN/False fields) when either
    window has zero defined observations."""
    bounds = compute_window_bounds(
        n_steps=shock_step + post_shock_horizon + 1, shock_step=shock_step,
        post_shock_horizon=post_shock_horizon, pre_shock_horizon=pre_shock_horizon,
    )
    _, pre_values = _extract_series(snapshots, dimension_key, bounds["pre_shock"])
    _, post_values = _extract_series(snapshots, dimension_key, bounds["post_shock"])
    pre_defined = [v for v in pre_values if v == v]
    post_defined = [v for v in post_values if v == v]
    recovery = perturbation_recovery(pre_defined, post_defined, tolerance_fraction=tolerance_fraction)
    return {
        "feature_kind": "dynamic", "shock_step": shock_step,
        "pre_shock_window": bounds["pre_shock"], "post_shock_window": bounds["post_shock"],
        "n_pre_shock_observations": len(pre_defined), "n_post_shock_observations": len(post_defined),
        **recovery,
    }


def lineage_turnover(institution_registry: dict, window: tuple[int, int]) -> dict:
    """Distinct lineage ids active (created before window end, not yet
    extinct before window start) at any point during ``window``, versus
    how many were already present at the window's start — a turnover
    ratio, not merely a count. ``feature_kind: "dynamic"`` (it describes
    change across the window, not a single-instant snapshot)."""
    start, end = window
    present_at_start = set()
    present_during = set()
    for rec in institution_registry.values():
        created_before_start = rec.creation_time < start
        extinct_before_start = rec.extinct and rec.extinction_time is not None and rec.extinction_time < start
        if created_before_start and not extinct_before_start:
            present_at_start.add(rec.lineage_id)
        overlaps_window = rec.creation_time < end and (not rec.extinct or rec.extinction_time is None or rec.extinction_time >= start)
        if overlaps_window:
            present_during.add(rec.lineage_id)
    new_lineages = present_during - present_at_start
    turnover_ratio = (len(new_lineages) / len(present_at_start)) if present_at_start else float("nan")
    return {
        "feature_kind": "dynamic", "window": window,
        "n_present_at_start": len(present_at_start), "n_present_during": len(present_during),
        "n_new_lineages": len(new_lineages), "turnover_ratio": turnover_ratio,
    }


def extinction_reconstruction_counts(institution_registry: dict, window: tuple[int, int]) -> dict:
    """Count of institution extinctions and reconstructions
    (``origin_mechanism == "reconstruction"``) whose defining event falls
    within ``window``."""
    start, end = window
    n_extinctions = sum(
        1 for rec in institution_registry.values()
        if rec.extinct and rec.extinction_time is not None and start <= rec.extinction_time < end
    )
    n_reconstructions = sum(
        1 for rec in institution_registry.values()
        if rec.origin_mechanism == "reconstruction" and start <= rec.creation_time < end
    )
    return {"feature_kind": "dynamic", "window": window, "n_extinctions": n_extinctions, "n_reconstructions": n_reconstructions}


def cross_patch_heterogeneity_series(snapshots: list[dict], window: tuple[int, int]) -> dict:
    """Static feature: mean of the ``H`` dimension's own value across
    the window (H is already itself a heterogeneity measure per snapshot
    — this reports its within-window central tendency, not a second
    heterogeneity-of-heterogeneity computation)."""
    return window_static_features(snapshots, "H", window)


def detect_nonstationarity(snapshots: list[dict], dimension_key: str, n_steps: int, burn_in_fraction: float = 0.2) -> dict:
    """A documented, simple heuristic (not a formal statistical test —
    disclosed as such, consistent with this project's "documented
    heuristic, not solved optimum" register elsewhere): splits the
    post-burn-in range into two halves and reports whether the halves'
    means differ by more than one pooled standard deviation. Both
    halves' raw mean/variance are always exported alongside the
    boolean flag."""
    burn_in_start, _ = _burn_in_window(n_steps, burn_in_fraction, None)
    mid = (burn_in_start + n_steps) // 2
    first_half = window_static_features(snapshots, dimension_key, (burn_in_start, mid))
    second_half = window_static_features(snapshots, dimension_key, (mid, n_steps))
    m1, v1 = first_half["mean"], first_half["variance"]
    m2, v2 = second_half["mean"], second_half["variance"]
    nonstationary = float("nan")
    if all(x == x for x in (m1, m2, v1, v2)):
        pooled_std = math.sqrt(max(v1, v2, 1e-12))
        nonstationary = abs(m1 - m2) > pooled_std
    return {
        "feature_kind": "dynamic", "first_half": first_half, "second_half": second_half,
        "nonstationary": nonstationary,
    }


def extract_all_temporal_features(
    snapshots: list[dict], dimension_key: str, n_steps: int, burn_in_fraction: float = 0.2,
    shock_step: int | None = None, post_shock_horizon: int = 20, pre_shock_horizon: int = 20,
) -> dict:
    """The full per-dimension temporal-feature bundle for every
    computable window (``pre_shock``/``shock``/``post_shock`` only when
    ``shock_step`` is given) — static and dynamic features kept in
    clearly separate sub-keys per window, never flattened together in a
    way that would hide which is which. Work Package G (Section 12)
    additions over the original Section 7 bundle: every window also
    gets a ``"persistence"`` sub-key (``window_persistence_features``),
    and a top-level ``"shock_recovery"`` key is added when
    ``shock_step`` is given."""
    bounds = compute_window_bounds(
        n_steps, burn_in_fraction, shock_step=shock_step,
        post_shock_horizon=post_shock_horizon, pre_shock_horizon=pre_shock_horizon,
    )
    out: dict = {}
    for name, window in bounds.items():
        out[name] = {
            "static": window_static_features(snapshots, dimension_key, window),
            "dynamic": window_dynamic_features(snapshots, dimension_key, window),
            "persistence": window_persistence_features(snapshots, dimension_key, window),
        }
    out["nonstationarity"] = detect_nonstationarity(snapshots, dimension_key, n_steps, burn_in_fraction)
    if shock_step is not None:
        out["shock_recovery"] = window_shock_recovery_features(
            snapshots, dimension_key, shock_step,
            pre_shock_horizon=pre_shock_horizon, post_shock_horizon=post_shock_horizon,
        )
    return out


def group_features_by_kind(feature_bundle: dict) -> dict:
    """Work Package G (Section 12) explicit requirement: static and
    dynamic feature sets must be analyzable "separately and jointly".
    This function performs the SEPARATION half (jointly is simply the
    caller using ``feature_bundle`` as-is, unflattened, since nothing
    upstream ever merges static and dynamic into one blob to begin
    with). Takes the output of :func:`extract_all_temporal_features`
    (or a dict of ``{dimension_key: that_output}`` for a whole seed-run)
    and returns ``{"static": {...}, "dynamic": {...}}`` where every leaf
    field is routed to the side matching its ``"feature_kind"`` --
    ``persistence``/``dynamic``/``nonstationarity``/``shock_recovery``
    sub-dicts all go to ``"dynamic"``, ``static`` sub-dicts go to
    ``"static"``; ``window`` bound tuples are dropped from this
    grouped view (they are metadata, not a feature, and are already
    present in the un-grouped bundle for any caller who needs them)."""
    static_out: dict = {}
    dynamic_out: dict = {}

    def _is_single_dimension_bundle(d: dict) -> bool:
        return isinstance(d, dict) and any(k in d for k in ("nonstationarity", "shock_recovery")) or (
            isinstance(d, dict) and any(isinstance(v, dict) and "static" in v and "dynamic" in v for v in d.values())
        )

    def _route_window_entry(window_name: str, entry: dict, static_target: dict, dynamic_target: dict) -> None:
        if "static" in entry:
            static_target[window_name] = entry["static"]
        for key in ("dynamic", "persistence"):
            if key in entry:
                dynamic_target.setdefault(window_name, {})[key] = entry[key]

    def _route_single(bundle: dict, static_target: dict, dynamic_target: dict) -> None:
        for window_name, entry in bundle.items():
            if window_name in ("nonstationarity", "shock_recovery"):
                dynamic_target[window_name] = entry
                continue
            _route_window_entry(window_name, entry, static_target, dynamic_target)

    is_multi_dimension = not _is_single_dimension_bundle(feature_bundle)
    if is_multi_dimension:
        for dim_key, bundle in feature_bundle.items():
            static_out[dim_key] = {}
            dynamic_out[dim_key] = {}
            _route_single(bundle, static_out[dim_key], dynamic_out[dim_key])
    else:
        _route_single(feature_bundle, static_out, dynamic_out)
    return {"static": static_out, "dynamic": dynamic_out}
