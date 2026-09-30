"""Level 0.3, Work Package I: a deliberately conservative, observer-side
diagnostic module for asking whether a candidate run's ecological
trajectory shows evidence of *endogenous regulation* — never whether it
matches a predetermined governance type or macrotype.

Every function here is a pure function of already-computed trajectory
arrays / scalar summary statistics (never of live simulation state), and
none of them are read by any decision function in ``simulation.py`` or
``agents/`` — the same read-only observer/generative boundary as every
other module in this package (``dev_mem/project_vision.md`` §5).

**Why seven separate criteria, and why none of them alone is sufficient.**
A trajectory that merely *flattens* (stops changing much) is not evidence
of self-regulation — it could just as easily mean the population died,
the pool saturated, or the run window was too short to see collapse. The
milestone brief is explicit that a term borrowed from dynamical-systems
theory implying a proven, provably-stable fixed point must never be used
for a merely-observed flat window. This module instead reports seven
independent,
individually-falsifiable criteria (interior persistence, feedback
dependence, perturbation recovery, parameter-neighborhood robustness,
nontriviality, micro-macro linkage, and a nonstationary-alternatives
classification) with their own exact definitions, explicit duration/
threshold requirements, and documented degenerate-case behaviour
(``math.nan``, never a silently substituted pass/fail). **This module
never combines the seven into one composite score or one verdict** — the
milestone brief's completion-report questions ask, separately, whether
*any* candidate satisfies *each* criterion; collapsing them would erase
exactly the distinction the brief cares about (e.g. "coexistence without
demonstrated feedback dependence" vs. "feedback-dependent interior
persistence" are different, and only the second is any kind of evidence
for self-regulation).

**Cautious vocabulary only.** The only labels this module ever assigns
are: ``"depleted"``, ``"abundant"``, ``"interior-persistent"``,
``"oscillatory"``, ``"intermittent"``, ``"spatially-polarized"``,
``"recovering"``, ``"non-recovering"``, and ``"unclassified"`` (the
explicit fallback when no other label's conditions are met — never
forced). These are observer-side descriptions of a numeric trajectory's
shape, not agent concepts, not governance types, and not a claim that the
label is permanent or the phenomenon is a stable "regime" in any stronger
sense than "this is what the observed window looked like."
"""

from __future__ import annotations

import math

import numpy as np
from scipy.signal import find_peaks

#: Work Package I, criterion 1 (interior persistence). Occupancy strictly
#: between these two bounds (fraction of a patch's/pool's capacity) counts
#: as "interior"; at or below the lower bound is treated as depleted, at
#: or above the upper bound as abundant/saturated. Documented, overridable
#: — not derived from any run's own data.
DEFAULT_INTERIOR_LOWER_BOUND = 0.05
DEFAULT_INTERIOR_UPPER_BOUND = 0.95
#: Minimum number of *consecutive* interior steps required before
#: "interior persistence" is asserted at all -- a single interior step
#: proves nothing about sustained coexistence.
DEFAULT_INTERIOR_MIN_DURATION_STEPS = 20

#: Work Package I, criterion 2/5 (feedback dependence / nontriviality). A
#: counterfactual's persistence statistic must be at least this fraction
#: lower than the candidate's own to count as "weaker."
DEFAULT_WEAKER_RELATIVE_REDUCTION = 0.2
#: Criterion 2 requires at least this fraction of the supplied
#: counterfactual conditions to show a weaker statistic.
DEFAULT_FEEDBACK_DEPENDENCE_MIN_FRACTION = 0.5

#: Work Package I, criterion 3 (perturbation recovery). The post-shock
#: series is considered "recovered" once it re-enters the pre-shock
#: [min, max] band widened by this fraction of the band's own width (a
#: tolerance against the pre-shock band itself being noisy, not a claim
#: that the shock's effect vanished entirely).
DEFAULT_RECOVERY_TOLERANCE_FRACTION = 0.1

#: Work Package I, criterion 4 (parameter-neighborhood robustness). The
#: minimum fraction of neighboring seeds/parameter points that must
#: individually satisfy interior persistence for the neighborhood itself
#: to be called robust.
DEFAULT_ROBUSTNESS_MIN_FRACTION = 0.5

#: Work Package I, criterion 6 (micro-macro linkage). Minimum |Pearson r|
#: and minimum sample size for a linkage to be asserted at all.
DEFAULT_LINKAGE_MIN_ABS_CORRELATION = 0.3
DEFAULT_LINKAGE_MIN_N = 5

#: Work Package I, criterion 7 (nonstationary alternatives). An
#: "oscillatory" classification requires at least this many sign changes
#: of the mean-detrended series per 100 steps; "intermittent" requires the
#: rolling-window variance's own coefficient of variation to exceed this
#: threshold (bursty, not steadily oscillating).
DEFAULT_OSCILLATION_MIN_CROSSINGS_PER_100_STEPS = 4.0
DEFAULT_INTERMITTENCY_MIN_VARIANCE_CV = 1.0
DEFAULT_NONSTATIONARY_WINDOW_STEPS = 20


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else math.nan


# ---------------------------------------------------------------------
# Criterion 1: interior persistence.
# ---------------------------------------------------------------------
def interior_persistence(
    occupancy_series,
    lower_bound: float = DEFAULT_INTERIOR_LOWER_BOUND,
    upper_bound: float = DEFAULT_INTERIOR_UPPER_BOUND,
    min_duration_steps: int = DEFAULT_INTERIOR_MIN_DURATION_STEPS,
) -> dict:
    """Longest run of consecutive steps with ``lower_bound < occupancy <
    upper_bound``. ``criterion_met`` requires that longest run to be
    ``>= min_duration_steps``. Degenerate on an empty series (returns
    ``math.nan``/``False``, never a fabricated pass)."""
    arr = np.asarray(occupancy_series, dtype=float)
    n = len(arr)
    if n == 0:
        return {
            "n_steps": 0,
            "longest_interior_run": math.nan,
            "fraction_interior": math.nan,
            "min_duration_required": min_duration_steps,
            "criterion_met": False,
        }
    interior = (arr > lower_bound) & (arr < upper_bound)
    longest = 0
    current = 0
    for flag in interior:
        if flag:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return {
        "n_steps": n,
        "longest_interior_run": int(longest),
        "fraction_interior": float(np.mean(interior)),
        "min_duration_required": min_duration_steps,
        "criterion_met": longest >= min_duration_steps,
    }


# ---------------------------------------------------------------------
# Criteria 2 & 5: feedback dependence / nontriviality. Structurally
# identical relative-reduction computation; kept as two named functions
# because the milestone brief treats them as conceptually distinct
# questions (2: "is the candidate's own feedback loop doing the work,
# across all four WP-F counterfactuals" vs. 5: "specifically, does the
# bare environmental equation without any agent effect reproduce the same
# behaviour") even though the arithmetic is the same relative-reduction
# test applied to a different, single-vs-multiple, counterfactual set.
# ---------------------------------------------------------------------
def _relative_reduction(candidate_stat: float, counterfactual_stat: float) -> float:
    if candidate_stat is None or math.isnan(candidate_stat) or candidate_stat <= 0:
        return math.nan
    if counterfactual_stat is None or math.isnan(counterfactual_stat):
        return math.nan
    return (candidate_stat - counterfactual_stat) / candidate_stat


def feedback_dependence(
    candidate_stat: float,
    counterfactual_stats: dict,
    weaker_relative_reduction: float = DEFAULT_WEAKER_RELATIVE_REDUCTION,
    min_fraction: float = DEFAULT_FEEDBACK_DEPENDENCE_MIN_FRACTION,
) -> dict:
    """``candidate_stat``: the endogenous-feedback run's own persistence
    statistic (e.g. ``interior_persistence(...)["fraction_interior"]``).
    ``counterfactual_stats``: mapping of WP-F condition name -> the
    matched (same seed/params) counterfactual run's same statistic. A
    counterfactual counts as "weaker" when its relative reduction from
    the candidate exceeds ``weaker_relative_reduction``.
    ``criterion_met`` requires at least ``min_fraction`` of the *provided*
    counterfactuals to be weaker -- an empty ``counterfactual_stats`` is
    an unevaluable criterion (``math.nan``/``False``), not an automatic
    pass."""
    if not counterfactual_stats:
        return {
            "candidate_stat": candidate_stat,
            "n_counterfactuals": 0,
            "n_weaker": math.nan,
            "fraction_weaker": math.nan,
            "per_condition_relative_reduction": {},
            "criterion_met": False,
        }
    reductions = {name: _relative_reduction(candidate_stat, stat) for name, stat in counterfactual_stats.items()}
    weaker_flags = {name: (not math.isnan(r) and r > weaker_relative_reduction) for name, r in reductions.items()}
    n = len(counterfactual_stats)
    n_weaker = sum(weaker_flags.values())
    fraction_weaker = n_weaker / n
    return {
        "candidate_stat": candidate_stat,
        "n_counterfactuals": n,
        "n_weaker": n_weaker,
        "fraction_weaker": fraction_weaker,
        "per_condition_relative_reduction": reductions,
        "criterion_met": fraction_weaker >= min_fraction,
    }


def nontriviality(
    candidate_stat: float,
    no_effect_stat: float,
    min_relative_reduction: float = DEFAULT_WEAKER_RELATIVE_REDUCTION,
) -> dict:
    """Specifically: does the bare environmental equation (WP-F's "no
    environmental effect" counterfactual — agents still decide/pay/earn,
    but the patch itself evolves under natural regeneration alone)
    reproduce the same interior-persistence statistic as the candidate?
    If ``no_effect_stat`` is not meaningfully lower, the candidate's
    apparent persistence could be explained by the environmental equation
    alone and is *not* evidence of a genuinely agent-driven effect."""
    reduction = _relative_reduction(candidate_stat, no_effect_stat)
    criterion_met = (not math.isnan(reduction)) and reduction > min_relative_reduction
    return {
        "candidate_stat": candidate_stat,
        "no_effect_stat": no_effect_stat,
        "relative_reduction": reduction,
        "min_relative_reduction_required": min_relative_reduction,
        "criterion_met": criterion_met,
    }


# ---------------------------------------------------------------------
# Criterion 3: perturbation recovery.
# ---------------------------------------------------------------------
def perturbation_recovery(
    pre_shock_series,
    post_shock_series,
    tolerance_fraction: float = DEFAULT_RECOVERY_TOLERANCE_FRACTION,
) -> dict:
    """``pre_shock_series``: occupancy in the window immediately before
    the shock (defines the "pre-shock range" [min, max]).
    ``post_shock_series``: occupancy from the shock onward. Recovery is
    defined as the first post-shock step whose value falls back inside
    the pre-shock [min, max] band, widened on each side by
    ``tolerance_fraction`` of the band's own width (a tolerance against a
    naturally noisy pre-shock baseline, not a claim the shock's effect
    fully vanished). Degenerate (``math.nan``/``False``) when either
    series is empty, or when the pre-shock band has zero width (in which
    case "recovery" would be a vacuous exact-equality test)."""
    pre = np.asarray(pre_shock_series, dtype=float)
    post = np.asarray(post_shock_series, dtype=float)
    if len(pre) == 0 or len(post) == 0:
        return {
            "recovered": False,
            "recovery_time_steps": math.nan,
            "immediate_shock_magnitude": math.nan,
            "time_to_minimum": math.nan,
            "overshoot": math.nan,
            "pre_shock_min": math.nan,
            "pre_shock_max": math.nan,
        }
    pre_min, pre_max = float(pre.min()), float(pre.max())
    band_width = pre_max - pre_min
    tol = tolerance_fraction * band_width
    lower, upper = pre_min - tol, pre_max + tol

    immediate_shock_magnitude = float(pre[-1] - post[0])
    time_to_minimum = int(np.argmin(post))
    minimum_value = float(post[time_to_minimum])

    recovery_time = math.nan
    recovered = False
    if band_width > 0:
        for i, value in enumerate(post):
            if lower <= value <= upper:
                recovery_time = i
                recovered = True
                break
    overshoot = float(max(0.0, float(post.max()) - pre_max, pre_min - float(post.min())))

    return {
        "recovered": recovered,
        "recovery_time_steps": recovery_time,
        "immediate_shock_magnitude": immediate_shock_magnitude,
        "time_to_minimum": time_to_minimum,
        "minimum_value": minimum_value,
        "overshoot": overshoot,
        "pre_shock_min": pre_min,
        "pre_shock_max": pre_max,
    }


# ---------------------------------------------------------------------
# Criterion 4: parameter-neighborhood robustness.
# ---------------------------------------------------------------------
def parameter_neighborhood_robustness(
    pass_flags,
    min_fraction: float = DEFAULT_ROBUSTNESS_MIN_FRACTION,
) -> dict:
    """``pass_flags``: one boolean per seed/neighboring parameter point,
    each already the result of applying some other criterion (typically
    :func:`interior_persistence`'s own ``criterion_met``) to that point.
    Degenerate (``math.nan``/``False``) on an empty list."""
    flags = list(pass_flags)
    n = len(flags)
    if n == 0:
        return {"n_neighbors": 0, "n_passing": math.nan, "fraction_passing": math.nan, "criterion_met": False}
    n_passing = sum(1 for f in flags if f)
    fraction = n_passing / n
    return {
        "n_neighbors": n,
        "n_passing": n_passing,
        "fraction_passing": fraction,
        "min_fraction_required": min_fraction,
        "criterion_met": fraction >= min_fraction,
    }


# ---------------------------------------------------------------------
# Criterion 6: micro-macro linkage.
# ---------------------------------------------------------------------
def micro_macro_linkage(
    trait_values,
    outcome_values,
    min_abs_correlation: float = DEFAULT_LINKAGE_MIN_ABS_CORRELATION,
    min_n: int = DEFAULT_LINKAGE_MIN_N,
) -> dict:
    """Pearson correlation, across matched seeds/parameter points (same
    parameters, different ecological-policy composition or different
    seed), between a scalar ecological-trait summary (e.g. population
    mean ``maintenance_propensity``) and a scalar macro-outcome (e.g.
    ``interior_persistence(...)["fraction_interior"]``). This is
    deliberately correlational within *matched* points (not a pooled
    cross-condition correlation, which ``docs/level0.2_scientific_note.md``
    and this milestone's statistical-reporting requirements both warn
    against conflating with a causal, within-condition relationship) --
    it is one *input* to, not a replacement for, the paired
    counterfactual evidence :func:`feedback_dependence` and
    :func:`nontriviality` provide. Degenerate (``math.nan``) below
    ``min_n`` matched points, or when either series is constant (zero
    variance makes a correlation coefficient undefined, not zero)."""
    x = np.asarray(trait_values, dtype=float)
    y = np.asarray(outcome_values, dtype=float)
    n = len(x)
    if n != len(y) or n < min_n:
        return {"n": n, "correlation": math.nan, "criterion_met": False}
    if np.std(x) == 0 or np.std(y) == 0:
        return {"n": n, "correlation": math.nan, "criterion_met": False}
    r = float(np.corrcoef(x, y)[0, 1])
    return {
        "n": n,
        "correlation": r,
        "min_abs_correlation_required": min_abs_correlation,
        "criterion_met": abs(r) >= min_abs_correlation,
    }


# ---------------------------------------------------------------------
# Criterion 7: nonstationary alternatives -- a cautious classification,
# never forced to "interior-persistent"/an equilibrium label.
# ---------------------------------------------------------------------
def nonstationary_classification(
    occupancy_series,
    lower_bound: float = DEFAULT_INTERIOR_LOWER_BOUND,
    upper_bound: float = DEFAULT_INTERIOR_UPPER_BOUND,
    window_steps: int = DEFAULT_NONSTATIONARY_WINDOW_STEPS,
    oscillation_min_crossings_per_100_steps: float = DEFAULT_OSCILLATION_MIN_CROSSINGS_PER_100_STEPS,
    intermittency_min_variance_cv: float = DEFAULT_INTERMITTENCY_MIN_VARIANCE_CV,
    cross_patch_series=None,
) -> dict:
    """Assigns exactly one cautious label, in this documented priority
    order (checked top to bottom; the first that matches wins -- ties are
    intentional, not accidental, since e.g. a run that is both mostly
    depleted *and* has a few oscillatory swings is more informatively
    reported as "depleted" first):

    1. ``"depleted"`` -- mean occupancy at or below ``lower_bound``.
    2. ``"abundant"`` -- mean occupancy at or above ``upper_bound``.
    3. ``"spatially-polarized"`` -- (only if ``cross_patch_series`` is
       given: one series per patch) the *cross-patch* variance at the
       final step is higher than at the first step by more than a
       factor of 2, i.e. patches are diverging from each other over the
       run, rather than each individually tracking the same trajectory.
    4. ``"oscillatory"`` -- the mean-detrended series crosses zero more
       than ``oscillation_min_crossings_per_100_steps`` times per 100
       steps.
    5. ``"intermittent"`` -- the coefficient of variation of
       non-overlapping ``window_steps``-step windows' own variances
       exceeds ``intermittency_min_variance_cv`` (bursty: some windows
       far more volatile than others, unlike oscillation's roughly
       steady crossing rate).
    6. ``"interior-persistent"`` -- passes :func:`interior_persistence`
       with this function's own ``lower_bound``/``upper_bound``.
    7. ``"unclassified"`` -- the explicit fallback when none of the
       above match; never silently defaults to a stronger label.

    Degenerate on an empty series: returns ``"unclassified"`` with every
    supporting statistic ``math.nan``.
    """
    arr = np.asarray(occupancy_series, dtype=float)
    n = len(arr)
    if n == 0:
        return {
            "label": "unclassified",
            "n_steps": 0,
            "mean_occupancy": math.nan,
            "zero_crossings_per_100_steps": math.nan,
            "window_variance_cv": math.nan,
        }

    mean_occ = float(np.mean(arr))
    detrended = arr - mean_occ
    signs = np.sign(detrended)
    signs = signs[signs != 0]
    crossings = int(np.sum(np.diff(signs) != 0)) if len(signs) > 1 else 0
    crossings_per_100 = crossings / n * 100.0

    window_variances = []
    for start in range(0, n - window_steps + 1, window_steps):
        window = arr[start : start + window_steps]
        window_variances.append(float(np.var(window)))
    if len(window_variances) >= 2 and np.mean(window_variances) > 0:
        variance_cv = float(np.std(window_variances) / np.mean(window_variances))
    else:
        variance_cv = math.nan

    spatially_polarized = False
    if cross_patch_series is not None and len(cross_patch_series) > 1:
        patch_arr = np.asarray(cross_patch_series, dtype=float)  # shape (n_patches, n_steps)
        if patch_arr.shape[1] >= 2:
            var_first = float(np.var(patch_arr[:, 0]))
            var_last = float(np.var(patch_arr[:, -1]))
            # Patches starting from exactly-equal occupancy (var_first==0)
            # can never satisfy a *relative* "grew by a factor" test --
            # any measurable end-of-run spread from a perfectly equal
            # start is itself the divergence signal, tested against a
            # small absolute floor instead.
            if var_first > 0:
                spatially_polarized = var_last > 2.0 * var_first
            else:
                spatially_polarized = var_last > 1e-6

    if mean_occ <= lower_bound:
        label = "depleted"
    elif mean_occ >= upper_bound:
        label = "abundant"
    elif spatially_polarized:
        label = "spatially-polarized"
    elif crossings_per_100 > oscillation_min_crossings_per_100_steps:
        label = "oscillatory"
    elif not math.isnan(variance_cv) and variance_cv > intermittency_min_variance_cv:
        label = "intermittent"
    elif interior_persistence(arr, lower_bound, upper_bound)["criterion_met"]:
        label = "interior-persistent"
    else:
        label = "unclassified"

    return {
        "label": label,
        "n_steps": n,
        "mean_occupancy": mean_occ,
        "zero_crossings_per_100_steps": crossings_per_100,
        "window_variance_cv": variance_cv,
        "spatially_polarized": spatially_polarized,
    }


# =======================================================================
# Level 0.3b, Work Package A: audited, burn-in-aware regime classifier.
#
# ``nonstationary_classification`` above (Level 0.3's original classifier)
# is left **unmodified** -- it is still what every already-committed Level
# 0.3 output file (phase-search labels, causal-intervention diagnostics)
# was computed with, and this module preserves that history rather than
# silently rewriting it in place. Everything below is a *new*,
# independently-versioned classifier
# (:data:`CLASSIFIER_VERSION`/:func:`classify_regime`) built in response to
# a documented audit finding: the original classifier (a) never excluded
# any initialization transient before classifying, (b) used a raw
# mean-detrended zero-crossing count as its sole oscillation test, which
# cannot distinguish three large, sustained cycles from three-and-a-half
# high-frequency noise wiggles of arbitrarily small amplitude, and (c)
# checked ``interior-persistent`` only *after* ``oscillatory``/
# ``intermittent``, which -- combined with (b) -- meant a trajectory only
# had to cross its own mean a few times to be called "oscillatory" even
# while sitting quietly inside the interior band the whole run.
#
# **Deliberate, disclosed deviation from the milestone brief's prose
# listing order.** The brief lists candidate categories in the order
# Depleted / Abundant / Interior-persistent / Oscillatory / Intermittent /
# Unclassified. Read literally as a first-match-wins priority order, this
# would mean any trajectory that oscillates *entirely within* the interior
# band (e.g. cycling between occupancy 0.3 and 0.7) is swallowed into
# "interior-persistent" before the oscillatory check is ever reached --
# exactly the kind of information loss Work Package A's own explicit
# ``sustained multi-cycle oscillation`` validation test (see
# ``tests/test_regulation_diagnostics.py``) would otherwise be unable to
# exercise, since such a hand-constructed series necessarily stays
# strictly inside [0, 1]. ``classify_regime`` therefore checks
# depleted -> abundant -> **oscillatory -> intermittent** ->
# interior-persistent -> unclassified: a trajectory is only ever labelled
# "interior-persistent" once it has *failed* the strict, multi-criterion
# oscillatory/intermittent tests, so genuine sustained cycling is never
# silently absorbed into the "boring and stable" label merely because it
# happens to stay in bounds. This choice is recorded here, in
# ``dev_mem/status_update.md``'s Level 0.3b entry, and in
# ``docs/level0.3b_validation_note.md`` -- it is a disclosed interpretive
# judgment call, not a silent rewrite of the brief.
# =======================================================================

#: Bumped whenever the decision logic, default thresholds, or the set of
#: supporting diagnostics in this section changes. Recorded verbatim in
#: every Level 0.3b candidate-registry and reanalysis output row so a
#: reanalysis can always be traced to the exact classifier version that
#: produced it.
CLASSIFIER_VERSION = "0.3b-v1"

#: Work Package A1: default burn-in exclusion -- the first
#: ``DEFAULT_BURN_IN_FRACTION`` of a series' steps are never used by any
#: classification decision below (only ever reported alongside the
#: analyzed window for transparency).
DEFAULT_BURN_IN_FRACTION = 0.2

#: Work Package A2. Deliberately distinct from the legacy
#: ``DEFAULT_INTERIOR_LOWER_BOUND``/``DEFAULT_INTERIOR_UPPER_BOUND``
#: above: those two describe "interior" for the *legacy* interior-
#: persistence criterion (criterion 1, still used unmodified by WP-F/H's
#: already-committed Level 0.3 outputs); ``DEFAULT_DEPLETION_THRESHOLD``/
#: ``DEFAULT_ABUNDANCE_THRESHOLD`` describe the depleted/abundant *bands*
#: for the new classifier and reuse the same numeric convention already
#: established by ``observer/niche_metrics.py::patch_occupancy_summary``'s
#: own depleted/abundant thresholds, for consistency across the codebase.
DEFAULT_DEPLETION_THRESHOLD = 0.05
DEFAULT_ABUNDANCE_THRESHOLD = 0.8
#: Minimum post-burn-in steps required before "depleted"/"abundant" can be
#: asserted at all (criterion duration requirement, A2).
DEFAULT_MIN_REGIME_DURATION_STEPS = 20
#: "No sustained recovery above [the depletion] threshold" (A2, Depleted)
#: is operationalized as: no more than this fraction of the post-burn-in
#: window may sit outside the depleted/abundant band respectively.
DEFAULT_MAX_OUT_OF_BAND_FRACTION = 0.05
#: Interior-persistent: minimum fraction of post-burn-in steps required
#: inside [lower_bound, upper_bound].
DEFAULT_INTERIOR_MIN_FRACTION = 0.6
#: Interior-persistent: "limited secular trend" -- the fitted linear
#: trend's total change over the window, as a fraction of the window's
#: own observed range, must not exceed this to count as "limited".
DEFAULT_INTERIOR_MAX_TREND_FRACTION = 0.3
#: Oscillatory: minimum median peak-to-trough amplitude (in the same
#: units as the occupancy series, i.e. a fraction of capacity) for a
#: detected cycle to count as real movement rather than numerical noise.
DEFAULT_OSCILLATION_MIN_AMPLITUDE = 0.05
#: Oscillatory: minimum number of *completed* cycles (peak+trough pairs /
#: 2) required, both overall and independently in each half of the
#: analyzed window (the "persistence across multiple windows" requirement).
DEFAULT_OSCILLATION_MIN_CYCLES = 3
#: Oscillatory: minimum autocorrelation at the best (non-zero) lag,
#: evidence of a genuine repeating structure rather than a random walk
#: that happens to have a few large swings.
DEFAULT_OSCILLATION_MIN_AUTOCORRELATION = 0.25
#: Intermittent: minimum number of depleted/interior/abundant band
#: transitions (after collapsing dwells shorter than
#: ``intermittent_min_dwell_steps``) required, on top of failing the
#: stricter oscillatory test.
DEFAULT_INTERMITTENT_MIN_TRANSITIONS = 2
DEFAULT_INTERMITTENT_MIN_DWELL_STEPS = 10


#: Shared floating-point tolerance for "this variance/power is zero"
#: checks below. A literal ``== 0`` comparison is unsafe here: a series
#: that is mathematically constant (e.g. ``np.full(200, 0.01)``) can still
#: carry a nonzero floating-point variance on the order of 1e-33 to 1e-36
#: purely from repeated float64 subtraction, which -- left unguarded --
#: would divide a near-zero (but nonzero) centered signal by a near-zero
#: variance and report spurious near-1.0 "autocorrelation" on a perfectly
#: flat series (caught during Work Package A4 test construction).
_NEAR_ZERO_ATOL = 1e-9


def _burn_in_window(n_steps: int, burn_in_fraction: float, burn_in_steps) -> tuple:
    """Returns ``(start, end)`` for the post-burn-in analysis window
    (``end == n_steps``; slice as ``series[start:end]``). An explicit
    ``burn_in_steps`` overrides ``burn_in_fraction`` when given. Both are
    clamped so the window is never negative-length."""
    if n_steps == 0:
        return 0, 0
    if burn_in_steps is not None:
        start = min(max(int(burn_in_steps), 0), n_steps)
    else:
        start = min(int(round(burn_in_fraction * n_steps)), n_steps)
    return start, n_steps


# ---------------------------------------------------------------------
# Work Package A3: supporting diagnostics. Each is independently testable
# and independently exported; none of them alone determines a label (see
# ``classify_regime`` below).
# ---------------------------------------------------------------------
def linear_trend(series) -> dict:
    """Least-squares slope (per step, in the series' own units) and R^2
    of the best-fit line. Degenerate on <2 points (slope 0.0/nan R^2 for
    exactly one point, both nan for zero points) or a perfectly constant
    series (R^2 undefined, not fabricated as 0 or 1)."""
    arr = np.asarray(series, dtype=float)
    n = len(arr)
    if n == 0:
        return {"slope": math.nan, "r_squared": math.nan}
    if n < 2:
        return {"slope": 0.0, "r_squared": math.nan}
    x = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(x, arr, 1)
    fitted = slope * x + intercept
    ss_tot = float(np.sum((arr - np.mean(arr)) ** 2))
    if abs(ss_tot) < _NEAR_ZERO_ATOL:
        return {"slope": float(slope), "r_squared": math.nan}
    ss_res = float(np.sum((arr - fitted) ** 2))
    return {"slope": float(slope), "r_squared": 1.0 - ss_res / ss_tot}


def rolling_variance(series, window: int) -> np.ndarray:
    """Variance of each length-``window`` sliding sub-window. Empty array
    if the series is shorter than ``window`` or ``window <= 0``."""
    arr = np.asarray(series, dtype=float)
    n = len(arr)
    if window <= 0 or n < window:
        return np.array([])
    return np.array([float(np.var(arr[i : i + window])) for i in range(0, n - window + 1)])


def detect_peaks_and_troughs(series, prominence: float = 0.0) -> dict:
    """Thin wrapper over ``scipy.signal.find_peaks`` applied to the series
    (peaks) and its negation (troughs), with an explicit minimum
    prominence -- the parameter that keeps small numerical wiggles from
    registering as extrema at all. Degenerate (all-empty) for <3 points,
    the minimum ``find_peaks`` needs to detect anything."""
    arr = np.asarray(series, dtype=float)
    if len(arr) < 3:
        return {
            "peak_indices": np.array([], dtype=int),
            "trough_indices": np.array([], dtype=int),
            "peak_prominences": np.array([]),
            "trough_prominences": np.array([]),
        }
    peak_idx, peak_props = find_peaks(arr, prominence=prominence)
    trough_idx, trough_props = find_peaks(-arr, prominence=prominence)
    return {
        "peak_indices": peak_idx,
        "trough_indices": trough_idx,
        "peak_prominences": peak_props.get("prominences", np.array([])),
        "trough_prominences": trough_props.get("prominences", np.array([])),
    }


def peak_to_trough_amplitude(series, prominence: float = 0.0) -> dict:
    """Median absolute value-difference between every pair of
    time-adjacent detected extrema (peaks and troughs, interleaved in
    time order) -- a robust amplitude estimate that a raw min/max of the
    whole series would overstate under a single outlier step, and that a
    plain standard deviation would understate under a slow secular trend.
    ``n_extrema`` is exported alongside so a caller can distinguish "no
    amplitude because nothing varies" from "no amplitude because too few
    extrema were even detected"."""
    arr = np.asarray(series, dtype=float)
    pt = detect_peaks_and_troughs(arr, prominence=prominence)
    all_idx = sorted(list(pt["peak_indices"]) + list(pt["trough_indices"]))
    n_extrema = len(all_idx)
    if n_extrema < 2:
        return {"median_amplitude": 0.0, "n_extrema": n_extrema}
    amplitudes = [abs(float(arr[all_idx[i + 1]] - arr[all_idx[i]])) for i in range(n_extrema - 1)]
    return {"median_amplitude": float(np.median(amplitudes)), "n_extrema": n_extrema}


def autocorrelation(series, max_lag: int) -> np.ndarray:
    """Pearson-style autocorrelation at lags ``1..min(max_lag, n-1)``
    (lag 0, always 1.0 by construction, is intentionally excluded --
    every caller here wants evidence of *repeating* structure, not the
    trivial self-correlation). Degenerate: empty array for <3 points; an
    all-zero array for a constant series (correlation is mathematically
    undefined for zero variance, but reporting "no detectable
    correlation" rather than nan is the conservative choice for a series
    that provably has no oscillatory structure at all)."""
    arr = np.asarray(series, dtype=float)
    n = len(arr)
    if n < 3:
        return np.array([])
    mean = np.mean(arr)
    var = np.var(arr)
    max_lag = min(max_lag, n - 1)
    if max_lag < 1:
        return np.array([])
    if abs(var) < _NEAR_ZERO_ATOL:
        return np.zeros(max_lag)
    centered = arr - mean
    return np.array(
        [float(np.sum(centered[: n - lag] * centered[lag:]) / (n * var)) for lag in range(1, max_lag + 1)]
    )


def dominant_spectral_power_ratio(series) -> dict:
    """Fraction of total non-DC spectral power (real FFT) concentrated in
    the single dominant frequency bin -- close to 1.0 for a clean
    single-frequency oscillation, close to ``1/n_bins`` for a flat,
    noise-like spectrum. ``dominant_period_steps`` is exported for
    cross-checking against the peak-counting period estimate. Degenerate
    (all-nan) for <4 points or an exactly-constant series (zero total
    power)."""
    arr = np.asarray(series, dtype=float)
    n = len(arr)
    if n < 4:
        return {"dominant_frequency_index": math.nan, "dominant_period_steps": math.nan, "power_ratio": math.nan}
    spectrum = np.abs(np.fft.rfft(arr - np.mean(arr))) ** 2
    spectrum = spectrum[1:]  # drop the DC bin
    total_power = float(np.sum(spectrum))
    if len(spectrum) == 0 or total_power < _NEAR_ZERO_ATOL:
        return {"dominant_frequency_index": math.nan, "dominant_period_steps": math.nan, "power_ratio": math.nan}
    dominant_idx = int(np.argmax(spectrum))
    freq_index = dominant_idx + 1
    return {
        "dominant_frequency_index": freq_index,
        "dominant_period_steps": float(n / freq_index),
        "power_ratio": float(spectrum[dominant_idx] / total_power),
    }


def _band_of(value: float, lower_bound: float, upper_bound: float) -> str:
    if value <= lower_bound:
        return "depleted"
    if value >= upper_bound:
        return "abundant"
    return "interior"


def band_transitions(series, lower_bound: float, upper_bound: float, min_dwell_steps: int = 1) -> dict:
    """Run-length-encodes the series into depleted/interior/abundant
    bands, then collapses any dwell shorter than ``min_dwell_steps`` into
    its preceding segment (re-merging adjacent same-label segments this
    creates) before counting transitions -- a single-step band excursion
    is treated as noise, not a genuine regime switch. Degenerate: zero
    transitions and no segments for an empty series."""
    arr = np.asarray(series, dtype=float)
    n = len(arr)
    if n == 0:
        return {"n_transitions": 0, "segments": []}
    labels = [_band_of(v, lower_bound, upper_bound) for v in arr]
    segments = []
    start = 0
    for i in range(1, n + 1):
        if i == n or labels[i] != labels[start]:
            segments.append([labels[start], i - start])
            start = i
    collapsed = []
    for seg in segments:
        if collapsed and seg[1] < min_dwell_steps:
            collapsed[-1][1] += seg[1]
        else:
            collapsed.append(list(seg))
    merged = []
    for seg in collapsed:
        if merged and merged[-1][0] == seg[0]:
            merged[-1][1] += seg[1]
        else:
            merged.append(seg)
    return {"n_transitions": max(0, len(merged) - 1), "segments": [(s[0], s[1]) for s in merged]}


# ---------------------------------------------------------------------
# Work Package A2: the revised classifier itself.
# ---------------------------------------------------------------------
def classify_regime(
    occupancy_series,
    burn_in_fraction: float = DEFAULT_BURN_IN_FRACTION,
    burn_in_steps=None,
    lower_bound: float = DEFAULT_INTERIOR_LOWER_BOUND,
    upper_bound: float = DEFAULT_INTERIOR_UPPER_BOUND,
    depletion_threshold: float = DEFAULT_DEPLETION_THRESHOLD,
    abundance_threshold: float = DEFAULT_ABUNDANCE_THRESHOLD,
    min_regime_duration_steps: int = DEFAULT_MIN_REGIME_DURATION_STEPS,
    max_out_of_band_fraction: float = DEFAULT_MAX_OUT_OF_BAND_FRACTION,
    interior_min_fraction: float = DEFAULT_INTERIOR_MIN_FRACTION,
    interior_max_trend_fraction: float = DEFAULT_INTERIOR_MAX_TREND_FRACTION,
    oscillation_min_amplitude: float = DEFAULT_OSCILLATION_MIN_AMPLITUDE,
    oscillation_min_cycles: float = DEFAULT_OSCILLATION_MIN_CYCLES,
    oscillation_min_autocorrelation: float = DEFAULT_OSCILLATION_MIN_AUTOCORRELATION,
    intermittent_min_transitions: int = DEFAULT_INTERMITTENT_MIN_TRANSITIONS,
    intermittent_min_dwell_steps: int = DEFAULT_INTERMITTENT_MIN_DWELL_STEPS,
) -> dict:
    """Level 0.3b, Work Package A2's audited regime classifier. Excludes
    the configured burn-in window first (A1), then applies the
    depleted -> abundant -> oscillatory -> intermittent ->
    interior-persistent -> unclassified decision sequence documented in
    this section's module-level comment (note the disclosed oscillatory/
    intermittent-before-interior-persistent ordering). Every supporting
    statistic (A3) is exported unconditionally, whatever the final label,
    so a caller can always see *why* a borderline case fell one way or
    the other -- including ``has_multi_cycle_oscillation_signature``,
    which is computed and reported even when the final label is not
    "oscillatory" (e.g. because a depleted/abundant band check fired
    first)."""
    full = np.asarray(occupancy_series, dtype=float)
    n_full = len(full)
    start, end = _burn_in_window(n_full, burn_in_fraction, burn_in_steps)
    arr = full[start:end]
    n = len(arr)

    shell = {
        "classifier_version": CLASSIFIER_VERSION,
        "n_steps_total": n_full,
        "burn_in_steps": start,
        "analyzed_window": [start, end],
        "n_steps_analyzed": n,
    }
    if n == 0:
        shell.update(
            {
                "label": "unclassified",
                "mean_occupancy": math.nan,
                "terminal_occupancy": math.nan,
                "trend_slope": math.nan,
                "trend_r_squared": math.nan,
                "strong_trend": False,
                "fraction_interior": math.nan,
                "fraction_depleted": math.nan,
                "fraction_abundant": math.nan,
                "peak_to_trough_amplitude": math.nan,
                "n_extrema": 0,
                "n_completed_cycles": math.nan,
                "best_lag_autocorrelation": math.nan,
                "dominant_period_steps": math.nan,
                "dominant_power_ratio": math.nan,
                "n_band_transitions": 0,
                "band_segments": [],
                "has_multi_cycle_oscillation_signature": False,
                "depleted_criteria_met": False,
                "abundant_criteria_met": False,
                "oscillatory_criteria_met": False,
                "intermittent_criteria_met": False,
                "interior_criteria_met": False,
            }
        )
        return shell

    mean_occ = float(np.mean(arr))
    terminal_window = arr[-min(min_regime_duration_steps, n) :]
    terminal_occ = float(np.mean(terminal_window))
    trend = linear_trend(arr)
    occ_range = max(float(np.max(arr) - np.min(arr)), 1e-9)
    strong_trend = (
        (not math.isnan(trend["slope"])) and (abs(trend["slope"]) * n / occ_range) > interior_max_trend_fraction
    )

    fraction_depleted = float(np.mean(arr <= depletion_threshold))
    fraction_abundant = float(np.mean(arr >= abundance_threshold))
    fraction_interior = float(np.mean((arr > lower_bound) & (arr < upper_bound)))

    prominence_floor = oscillation_min_amplitude * 0.5
    amp = peak_to_trough_amplitude(arr, prominence=prominence_floor)
    autocorr = autocorrelation(arr, max_lag=max(1, n // 2))
    spectral = dominant_spectral_power_ratio(arr)
    transitions = band_transitions(arr, lower_bound, upper_bound, min_dwell_steps=intermittent_min_dwell_steps)

    n_completed_cycles = amp["n_extrema"] / 2.0
    best_lag_autocorr = float(np.max(autocorr)) if len(autocorr) > 0 else math.nan

    half = n // 2
    amp_first = peak_to_trough_amplitude(arr[:half], prominence=prominence_floor) if half >= 3 else {"n_extrema": 0}
    amp_second = (
        peak_to_trough_amplitude(arr[half:], prominence=prominence_floor) if (n - half) >= 3 else {"n_extrema": 0}
    )
    min_extrema_per_half = max(1.0, oscillation_min_cycles - 1)
    persists_across_windows = (
        amp_first["n_extrema"] >= min_extrema_per_half and amp_second["n_extrema"] >= min_extrema_per_half
    )

    has_multi_cycle_oscillation_signature = bool(
        n_completed_cycles >= oscillation_min_cycles
        and amp["median_amplitude"] >= oscillation_min_amplitude
        and (not math.isnan(best_lag_autocorr))
        and best_lag_autocorr >= oscillation_min_autocorrelation
        and not strong_trend
        and persists_across_windows
    )

    depleted_ok = bool(
        terminal_occ <= depletion_threshold
        and n >= min_regime_duration_steps
        and fraction_depleted >= (1.0 - max_out_of_band_fraction)
    )
    abundant_ok = bool(
        terminal_occ >= abundance_threshold
        and n >= min_regime_duration_steps
        and fraction_abundant >= (1.0 - max_out_of_band_fraction)
    )
    oscillatory_ok = has_multi_cycle_oscillation_signature
    intermittent_ok = bool(
        (not oscillatory_ok)
        and transitions["n_transitions"] > intermittent_min_transitions
        and n >= min_regime_duration_steps
    )
    interior_ok = bool(
        (not oscillatory_ok)
        and (not intermittent_ok)
        and n >= min_regime_duration_steps
        and lower_bound < terminal_occ < upper_bound
        and fraction_interior >= interior_min_fraction
        and not strong_trend
        and fraction_depleted < max_out_of_band_fraction
        and fraction_abundant < max_out_of_band_fraction
    )

    if depleted_ok:
        label = "depleted"
    elif abundant_ok:
        label = "abundant"
    elif oscillatory_ok:
        label = "oscillatory"
    elif intermittent_ok:
        label = "intermittent"
    elif interior_ok:
        label = "interior-persistent"
    else:
        label = "unclassified"

    shell.update(
        {
            "label": label,
            "mean_occupancy": mean_occ,
            "terminal_occupancy": terminal_occ,
            "trend_slope": trend["slope"],
            "trend_r_squared": trend["r_squared"],
            "strong_trend": bool(strong_trend),
            "fraction_interior": fraction_interior,
            "fraction_depleted": fraction_depleted,
            "fraction_abundant": fraction_abundant,
            "peak_to_trough_amplitude": amp["median_amplitude"],
            "n_extrema": amp["n_extrema"],
            "n_completed_cycles": n_completed_cycles,
            "best_lag_autocorrelation": best_lag_autocorr,
            "dominant_period_steps": spectral["dominant_period_steps"],
            "dominant_power_ratio": spectral["power_ratio"],
            "n_band_transitions": transitions["n_transitions"],
            "band_segments": transitions["segments"],
            "has_multi_cycle_oscillation_signature": has_multi_cycle_oscillation_signature,
            "depleted_criteria_met": depleted_ok,
            "abundant_criteria_met": abundant_ok,
            "oscillatory_criteria_met": oscillatory_ok,
            "intermittent_criteria_met": intermittent_ok,
            "interior_criteria_met": interior_ok,
        }
    )
    return shell


# =======================================================================
# Level 0.3b, Work Package J: repaired perturbation-recovery diagnostic.
#
# ``perturbation_recovery`` above (Level 0.3's original criterion 3) is
# left unmodified for the same reason ``nonstationary_classification``
# was: it is what every already-committed Level 0.3 perturbation output
# was computed with. The functions below are new and independently
# named, built in response to a documented audit finding: the original
# function had no eligibility screen at all -- it would report a
# "recovery time" for a shock applied to an already-collapsed patch (an
# ill-defined "return" to a pre-shock band that was itself near zero
# width), and it counted the very first instantaneous re-entry into a
# tolerance-widened band as "recovered," with no requirement that the
# series actually *stay* there.
# =======================================================================

#: Work Package J eligibility screen defaults.
DEFAULT_MIN_SHOCK_DISPLACEMENT = 0.05
DEFAULT_MIN_POST_SHOCK_STEPS = 20
#: A pre-shock band narrower than this is not automatically disqualifying
#: (the original criterion's own tolerance-widening already exists for
#: exactly this case) -- but combined with a pre-shock mean at or below
#: the depletion threshold, it is one of several signals a run's
#: "recovery" would be a vacuous test against an already-collapsed
#: baseline.
DEFAULT_MIN_PRE_SHOCK_BAND_WIDTH_OR_FLOOR = 0.02
#: "Sustained residence" (recovery criterion 3): the series must remain
#: inside the tolerance-widened pre-shock band for at least this many
#: consecutive post-entry steps for recovery to count as persistent
#: rather than a single-step threshold crossing.
DEFAULT_SUSTAINED_RECOVERY_MIN_DURATION_STEPS = 10


def recovery_eligibility(
    pre_shock_series,
    post_shock_series,
    control_post_shock_series=None,
    depletion_threshold: float = DEFAULT_DEPLETION_THRESHOLD,
    min_band_width_or_floor: float = DEFAULT_MIN_PRE_SHOCK_BAND_WIDTH_OR_FLOOR,
    min_shock_displacement: float = DEFAULT_MIN_SHOCK_DISPLACEMENT,
    min_post_shock_steps: int = DEFAULT_MIN_POST_SHOCK_STEPS,
) -> dict:
    """Screens whether a (pre-shock, post-shock) pair is even a
    meaningful recovery test, per Work Package J's five eligibility
    conditions. Returns ``eligible: False`` with one or more
    human-readable ``ineligibility_reasons`` (never silently coerced to
    "recovered"/"non-recovered") when any condition fails.
    ``control_post_shock_series`` (the matched *unperturbed* control's own
    post-shock-window series) is optional; the "control not already
    collapsing" check is skipped, not assumed passing, when omitted."""
    pre = np.asarray(pre_shock_series, dtype=float)
    post = np.asarray(post_shock_series, dtype=float)
    reasons = []

    if len(pre) == 0 or len(post) == 0:
        return {
            "eligible": False,
            "ineligibility_reasons": ["empty pre-shock or post-shock series"],
            "pre_shock_mean": math.nan,
            "pre_shock_band_width": math.nan,
            "displacement": math.nan,
        }

    pre_mean = float(np.mean(pre))
    band_width = float(np.max(pre) - np.min(pre))

    if pre_mean <= depletion_threshold:
        reasons.append(
            f"pre-shock mean occupancy ({pre_mean:.4f}) is at or below the depletion threshold "
            f"({depletion_threshold}) -- there is no non-collapsed baseline to recover to"
        )

    if control_post_shock_series is not None:
        control_post = np.asarray(control_post_shock_series, dtype=float)
        if len(control_post) > 0:
            control_trend = linear_trend(control_post)
            control_terminal = float(np.mean(control_post[-min(10, len(control_post)) :]))
            if (
                control_terminal <= depletion_threshold
                and not math.isnan(control_trend["slope"])
                and control_trend["slope"] < 0
            ):
                reasons.append(
                    "the matched unperturbed control is itself already undergoing sustained collapse in this "
                    "window -- a 'recovery' relative to a collapsing control is not a meaningful comparison"
                )

    early_window = post[: min(10, len(post))]
    displacement = float(np.max(np.abs(pre_mean - early_window))) if len(early_window) else math.nan
    if math.isnan(displacement) or displacement < min_shock_displacement:
        reasons.append(
            f"maximum early post-shock displacement ({displacement}) is below the minimum-meaningful-displacement "
            f"threshold ({min_shock_displacement}) -- this shock did not measurably move the series"
        )

    if len(post) < min_post_shock_steps:
        reasons.append(
            f"post-shock horizon ({len(post)} steps) is shorter than the minimum required to test recovery "
            f"({min_post_shock_steps} steps)"
        )

    return {
        "eligible": len(reasons) == 0,
        "ineligibility_reasons": reasons,
        "pre_shock_mean": pre_mean,
        "pre_shock_band_width": band_width,
        "displacement": displacement,
    }


def recovery_quality(
    pre_shock_series,
    post_shock_series,
    control_post_shock_series=None,
    tolerance_fraction: float = DEFAULT_RECOVERY_TOLERANCE_FRACTION,
    min_band_width_or_floor: float = DEFAULT_MIN_PRE_SHOCK_BAND_WIDTH_OR_FLOOR,
    sustained_min_duration_steps: int = DEFAULT_SUSTAINED_RECOVERY_MIN_DURATION_STEPS,
    eligibility: dict = None,
) -> dict:
    """Work Package J's revised recovery definition -- distinguishes an
    instantaneous single-step threshold crossing (``time_to_first_
    reentry``) from a persistent, sustained recovery (``time_to_sustained_
    recovery``, requiring >= ``sustained_min_duration_steps`` consecutive
    post-entry steps inside the tolerance-widened pre-shock band before it
    counts). ``recovered`` reflects the *sustained* definition only. If
    ``eligibility`` is not supplied it is computed internally
    (``recovery_eligibility`` with default thresholds); an ineligible run
    returns ``recovered: None`` (neither True nor False) with every
    quality statistic ``math.nan`` -- never silently reported as
    "non-recovered", which the milestone brief explicitly distinguishes
    from "ineligible for the test at all"."""
    pre = np.asarray(pre_shock_series, dtype=float)
    post = np.asarray(post_shock_series, dtype=float)

    if eligibility is None:
        eligibility = recovery_eligibility(pre, post, control_post_shock_series, min_band_width_or_floor=min_band_width_or_floor)

    if not eligibility["eligible"]:
        return {
            "eligible": False,
            "ineligibility_reasons": eligibility["ineligibility_reasons"],
            "recovered": None,
            "max_displacement": math.nan,
            "time_to_minimum": math.nan,
            "time_to_first_reentry": math.nan,
            "time_to_sustained_recovery": math.nan,
            "post_recovery_persistence_fraction": math.nan,
            "residual_distance_from_control": math.nan,
            "overshoot": math.nan,
        }

    pre_min, pre_max = float(np.min(pre)), float(np.max(pre))
    band_width = max(pre_max - pre_min, min_band_width_or_floor)
    tol = tolerance_fraction * band_width
    lower, upper = pre_min - tol, pre_max + tol

    time_to_minimum = int(np.argmin(post))
    max_displacement = float(np.max(np.abs(post - np.mean(pre))))

    time_to_first_reentry = math.nan
    time_to_sustained_recovery = math.nan
    recovered = False
    in_band = (post >= lower) & (post <= upper)
    for i in range(len(post)):
        if in_band[i]:
            if math.isnan(time_to_first_reentry):
                time_to_first_reentry = i
            run_end = min(i + sustained_min_duration_steps, len(post))
            if run_end - i >= sustained_min_duration_steps and bool(np.all(in_band[i:run_end])):
                time_to_sustained_recovery = i
                recovered = True
                break

    if recovered:
        post_recovery = in_band[int(time_to_sustained_recovery) :]
        post_recovery_persistence_fraction = float(np.mean(post_recovery)) if len(post_recovery) else math.nan
    else:
        post_recovery_persistence_fraction = math.nan

    overshoot = float(max(0.0, float(np.max(post)) - pre_max, pre_min - float(np.min(post))))

    residual_distance_from_control = math.nan
    if control_post_shock_series is not None:
        control_post = np.asarray(control_post_shock_series, dtype=float)
        n_common = min(len(post), len(control_post))
        if n_common > 0:
            tail = max(1, min(sustained_min_duration_steps, n_common))
            residual_distance_from_control = float(
                np.mean(np.abs(post[-tail:] - control_post[-tail:]))
            )

    return {
        "eligible": True,
        "ineligibility_reasons": [],
        "recovered": recovered,
        "max_displacement": max_displacement,
        "time_to_minimum": time_to_minimum,
        "time_to_first_reentry": time_to_first_reentry,
        "time_to_sustained_recovery": time_to_sustained_recovery,
        "post_recovery_persistence_fraction": post_recovery_persistence_fraction,
        "residual_distance_from_control": residual_distance_from_control,
        "overshoot": overshoot,
    }


def assess_perturbation_recovery(
    pre_shock_series,
    post_shock_series,
    control_post_shock_series=None,
    tolerance_fraction: float = DEFAULT_RECOVERY_TOLERANCE_FRACTION,
    depletion_threshold: float = DEFAULT_DEPLETION_THRESHOLD,
    min_band_width_or_floor: float = DEFAULT_MIN_PRE_SHOCK_BAND_WIDTH_OR_FLOOR,
    min_shock_displacement: float = DEFAULT_MIN_SHOCK_DISPLACEMENT,
    min_post_shock_steps: int = DEFAULT_MIN_POST_SHOCK_STEPS,
    sustained_min_duration_steps: int = DEFAULT_SUSTAINED_RECOVERY_MIN_DURATION_STEPS,
) -> dict:
    """Convenience entry point combining :func:`recovery_eligibility` and
    :func:`recovery_quality` in one call -- what every Level 0.3b
    perturbation script actually calls."""
    eligibility = recovery_eligibility(
        pre_shock_series, post_shock_series, control_post_shock_series,
        depletion_threshold=depletion_threshold, min_band_width_or_floor=min_band_width_or_floor,
        min_shock_displacement=min_shock_displacement, min_post_shock_steps=min_post_shock_steps,
    )
    quality = recovery_quality(
        pre_shock_series, post_shock_series, control_post_shock_series,
        tolerance_fraction=tolerance_fraction, min_band_width_or_floor=min_band_width_or_floor,
        sustained_min_duration_steps=sustained_min_duration_steps, eligibility=eligibility,
    )
    return quality
