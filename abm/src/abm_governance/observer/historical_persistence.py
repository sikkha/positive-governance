"""Level 1.3b, Work Package F / Stage 5 (task #118, Section 10):
temporal-persistence and hysteresis diagnostics.

Purely observer-side (reads only an already-computed time series plus
``n_steps``; no RNG, no simulation state, no config) -- same posture as
``observer/sequencing_diagnostics.py`` and ``observer/sz_obs.py``.

**The rule this module exists to enforce (Section 10's own explicit
requirement, restated in the frozen preregistration's ``STAGE5_
TEMPORAL_PERSISTENCE["rule"]``): never classify persistence from a
final-step value alone.** Every function here operates on WINDOWS
(early/middle/late/final_sustained fractions of the run, frozen in
``experiments.level13b_preregistration.STAGE5_TEMPORAL_PERSISTENCE``,
imported here as the single source of truth rather than re-declared),
not on ``series[-1]``.

**Two diagnostics operationalized beyond their bare name, disclosed
here before any run uses them:**

* ``convergence_divergence_slope`` operates on a single trajectory's
  own three window means (early, middle, late) as an ordered sequence
  -- a positive slope means the observable kept rising across the run
  (still changing, not yet settled); a slope near zero with low
  ``late_window_variance`` is this module's own operational signature
  of "settled" (used by :func:`classify_persistence` below), not by
  itself "convergence" in the sense of two different CONDITIONS
  converging toward each other -- that cross-condition question is
  :func:`trajectory_distance`'s job, computed on a PAIR of series.
* ``cluster_assignment_stability_across_windows`` has no cluster model
  to draw on yet at Stage 5 (fitting one is explicitly Stage 7/task
  #120's own job, downstream of this stage). This module instead
  operationalizes the same underlying question -- "does the qualitative
  ranking among conditions stay stable across windows?" -- via
  :func:`condition_rank_stability`: a Spearman rank correlation between
  a fixed set of conditions' window-mean ORDERING in one window vs. the
  next, computed on Stage 5's own matched conditions directly, not on
  cluster labels. Disclosed here as a distinct, honestly-substituted
  proxy, not a literal implementation of the reconstructed dimension
  name."""

from __future__ import annotations

import numpy as np

from experiments.level13b_preregistration import STAGE5_TEMPORAL_PERSISTENCE

WINDOW_FRACTIONS: dict[str, tuple[float, float]] = {
    name: tuple(bounds) for name, bounds in STAGE5_TEMPORAL_PERSISTENCE["windows_as_fraction_of_run_length"].items()
}

CLASSIFICATION_CATEGORIES: tuple[str, ...] = tuple(STAGE5_TEMPORAL_PERSISTENCE["classification_categories"])


def window_bounds(n_steps: int, window_name: str) -> tuple[int, int]:
    """Integer half-open ``[lo, hi)`` step bounds for ``window_name``,
    derived from :data:`WINDOW_FRACTIONS`. ``hi`` is clamped to
    ``n_steps``; ``lo`` is always ``< hi`` for ``n_steps >= 1``."""
    if n_steps < 1:
        raise ValueError("n_steps must be >= 1")
    lo_frac, hi_frac = WINDOW_FRACTIONS[window_name]
    lo = int(round(lo_frac * n_steps))
    hi = max(lo + 1, int(round(hi_frac * n_steps)))
    return lo, min(hi, n_steps)


def windowed_mean(series: np.ndarray, n_steps: int, window_name: str) -> float:
    lo, hi = window_bounds(n_steps, window_name)
    return float(np.mean(np.asarray(series, dtype=float)[lo:hi]))


def windowed_variance(series: np.ndarray, n_steps: int, window_name: str) -> float:
    lo, hi = window_bounds(n_steps, window_name)
    return float(np.var(np.asarray(series, dtype=float)[lo:hi]))


def early_to_middle_displacement(series: np.ndarray, n_steps: int) -> float:
    """``mean(middle window) - mean(early window)``."""
    return windowed_mean(series, n_steps, "middle") - windowed_mean(series, n_steps, "early")


def middle_to_late_displacement(series: np.ndarray, n_steps: int) -> float:
    """``mean(late window) - mean(middle window)``."""
    return windowed_mean(series, n_steps, "late") - windowed_mean(series, n_steps, "middle")


def late_window_variance(series: np.ndarray, n_steps: int) -> float:
    return windowed_variance(series, n_steps, "late")


def convergence_divergence_slope(series: np.ndarray, n_steps: int) -> float:
    """Least-squares slope of the three window means
    (early=0, middle=1, late=2) against window index. See module
    docstring for what this does and does not mean -- a single-
    trajectory settling diagnostic, not a cross-condition convergence
    test (that is :func:`trajectory_distance`)."""
    means = [windowed_mean(series, n_steps, w) for w in ("early", "middle", "late")]
    x = np.array([0.0, 1.0, 2.0])
    slope, _intercept = np.polyfit(x, np.array(means), deg=1)
    return float(slope)


def trajectory_distance(
    series_a: np.ndarray, series_b: np.ndarray, n_steps: int,
    windows: tuple[str, ...] = ("early", "middle", "late", "final_sustained"),
) -> dict[str, float]:
    """Euclidean distance between two trajectories' windowed-mean
    vectors, reported both per-window (the gap AT that window) and as
    one summary distance across all requested windows -- the basic
    building block for asking whether two matched conditions (e.g.
    Stage 3's ``security_first`` vs ``coevolution``) are converging or
    staying apart as the run progresses."""
    vec_a = np.array([windowed_mean(series_a, n_steps, w) for w in windows])
    vec_b = np.array([windowed_mean(series_b, n_steps, w) for w in windows])
    per_window = {w: float(abs(a - b)) for w, a, b in zip(windows, vec_a, vec_b)}
    return {**{f"gap_at_{w}": v for w, v in per_window.items()}, "summary_euclidean_distance": float(np.linalg.norm(vec_a - vec_b))}


def condition_rank_stability(condition_window_means: dict[str, dict[str, float]]) -> dict[str, float]:
    """Spearman rank correlation between consecutive windows' ranking
    of a fixed set of named conditions -- the disclosed proxy for
    ``cluster_assignment_stability_across_windows`` (see module
    docstring). ``condition_window_means`` maps
    ``{condition_name: {window_name: mean_value}}``. Requires >= 2
    conditions with values in the SAME set of windows; returns
    ``{"early_to_middle": r, "middle_to_late": r}`` (``r`` is ``nan``
    when fewer than 2 conditions are supplied, since rank correlation
    is undefined for a single item)."""
    conditions = list(condition_window_means.keys())
    if len(conditions) < 2:
        return {"early_to_middle": float("nan"), "middle_to_late": float("nan")}

    def _spearman(window_a: str, window_b: str) -> float:
        vals_a = np.array([condition_window_means[c][window_a] for c in conditions])
        vals_b = np.array([condition_window_means[c][window_b] for c in conditions])
        rank_a = np.argsort(np.argsort(vals_a)).astype(float)
        rank_b = np.argsort(np.argsort(vals_b)).astype(float)
        if np.std(rank_a) == 0.0 or np.std(rank_b) == 0.0:
            return float("nan")
        return float(np.corrcoef(rank_a, rank_b)[0, 1])

    return {"early_to_middle": _spearman("early", "middle"), "middle_to_late": _spearman("middle", "late")}


def classify_persistence(
    early_to_middle: float, middle_to_late: float, late_variance: float, slope: float,
    displacement_threshold: float = 0.02, variance_threshold: float = 0.005, slope_threshold: float = 0.001,
) -> str:
    """A simple, disclosed, threshold-based rule -- not a fitted
    classifier -- mapping four already-computed diagnostics to one of
    :data:`CLASSIFICATION_CATEGORIES`. Thresholds are round, disclosed
    numbers chosen before this function was ever applied to a real
    Stage 5 run (not tuned post hoc), on the same observer-side scale
    S_obs/Z_obs already occupy ([0, 1] typically).

    Rule, applied in order:

    1. Both displacements smaller than ``displacement_threshold`` in
       absolute value -> ``"no_detectable_differentiation"`` (nothing
       to persist).
    2. ``|middle_to_late|`` small AND ``late_variance`` small AND
       ``|slope|`` small (settled) but ``|early_to_middle|`` was NOT
       small -> differentiation appeared early and then held ->
       ``"entrenched_path_dependence"``.
    3. ``|middle_to_late|`` small but the trajectory is still not
       fully flat (slope or late variance above threshold) ->
       ``"historical_hysteresis"`` (persisting, but not yet as settled
       as category 2).
    4. ``|middle_to_late|`` large (still moving toward the end) and its
       SIGN opposes ``early_to_middle`` (i.e. reconverging) ->
       ``"transient_differentiation"``.
    5. Otherwise (still changing, not clearly reconverging) ->
       ``"pressure_dependent_response"`` -- the residual "still tracks
       the driving signal, no persistence verdict yet" category."""
    small_e2m = abs(early_to_middle) < displacement_threshold
    small_m2l = abs(middle_to_late) < displacement_threshold
    settled = small_m2l and late_variance < variance_threshold and abs(slope) < slope_threshold

    if small_e2m and small_m2l:
        return "no_detectable_differentiation"
    if settled and not small_e2m:
        return "entrenched_path_dependence"
    if small_m2l:
        return "historical_hysteresis"
    reconverging = (early_to_middle * middle_to_late) < 0.0
    if reconverging:
        return "transient_differentiation"
    return "pressure_dependent_response"
