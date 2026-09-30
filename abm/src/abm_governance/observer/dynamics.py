"""Reusable dynamical diagnostics (Level 0.1, Work Package F).

These are descriptive statistics over an already-computed metrics time
series (e.g. the ``cooperation_rate`` column of a run's ``metrics.csv``).
None of them *decide* that a trajectory is a fixed point, a limit cycle, a
metastable regime, a collapse, or a recovery — they are the raw
ingredients a human (or a later, explicitly-scoped milestone) would need
to make that call. See "Operational criteria" below for what this project
currently requires before any such label is used, and note that none of
those labels are applied automatically anywhere in this codebase.

Operational criteria (documentation, not implemented classifiers)
-------------------------------------------------------------------
Per the milestone brief: "do not label a trajectory an attractor or limit
cycle merely because it fluctuates." Before this project uses any of the
following words about a trajectory or an ensemble of trajectories, the
claim should be supported by evidence resembling:

* **Fixed point** — rolling mean and rolling variance both converge (e.g.
  the coefficient of variation of the rolling mean across the trailing
  window falls and stays below a small, pre-registered threshold) and stay
  converged for a substantial trailing fraction of the run, across
  multiple seeds and multiple perturbation-recovery trials, not one run.
* **Limit cycle** — the (detrended) autocorrelation function shows a
  clear, repeating peak at a consistent, non-trivial lag across multiple
  seeds, *and* the periodogram shows concentrated power at the
  corresponding frequency rather than a broadband/noisy spectrum.
* **Metastable regime** — the trajectory spends extended, clearly
  separated intervals in one or more empirically-discovered regions
  (see :func:`regime_time_fraction`), with detectable transitions between
  them (see :func:`change_point_candidates`), and the regions/transition
  pattern reproduce (not necessarily identically) across seeds.
* **Collapse** — a sustained, large-magnitude drop in a headline
  observable (e.g. cooperation rate, population resources) that does not
  recover within the observation window, ideally following a scheduled
  perturbation (see ``core/perturbation.py``) so the triggering shock is
  known rather than inferred.
* **Recovery** — following a collapse or a scheduled perturbation, the
  observable returns to (or within a documented tolerance of) its
  pre-shock distribution and *stays there* for a trailing window at least
  as long as the shock's own duration.
* **Attractor** (in the dynamical-systems sense, encompassing the above)
  — convergence (of a single trajectory, or of the *distribution* of
  endpoints across many seeds/initial conditions — see
  :func:`endpoint_dispersion`) to a specific region of state space that is
  robust to small perturbations of initial conditions, demonstrated across
  an ensemble, not asserted from a single run.

This project does not yet claim any of the above for the Level 0.1
system — see ``dev_mem/status_update.md`` for what the recorded baseline
ensemble actually shows.
"""

from __future__ import annotations

import numpy as np


def rolling_mean(series: np.ndarray, window: int) -> np.ndarray:
    """Trailing rolling mean; the first ``window - 1`` entries use
    whatever history is available (a growing window), so the output has
    the same length as the input."""
    series = np.asarray(series, dtype=float)
    if window < 1:
        raise ValueError("window must be >= 1")
    out = np.empty_like(series)
    for i in range(len(series)):
        lo = max(0, i - window + 1)
        out[i] = np.nanmean(series[lo : i + 1])
    return out


def rolling_variance(series: np.ndarray, window: int) -> np.ndarray:
    series = np.asarray(series, dtype=float)
    if window < 1:
        raise ValueError("window must be >= 1")
    out = np.empty_like(series)
    for i in range(len(series)):
        lo = max(0, i - window + 1)
        out[i] = np.nanvar(series[lo : i + 1])
    return out


def autocorrelation(series: np.ndarray, max_lag: int) -> np.ndarray:
    """Sample autocorrelation function at lags ``0..max_lag`` (inclusive),
    ``acf[0] == 1.0`` by construction. Returns ``NaN`` at all lags if the
    series has zero variance (a literal, unfluctuating constant)."""
    series = np.asarray(series, dtype=float)
    n = len(series)
    if n < 2:
        return np.full(max_lag + 1, np.nan)
    centered = series - series.mean()
    var = np.sum(centered**2)
    if var == 0:
        return np.full(max_lag + 1, np.nan)
    acf = np.empty(max_lag + 1)
    for lag in range(max_lag + 1):
        if lag >= n:
            acf[lag] = np.nan
            continue
        acf[lag] = np.sum(centered[: n - lag] * centered[lag:]) / var
    return acf


def detrended_autocorrelation(series: np.ndarray, max_lag: int) -> np.ndarray:
    """Autocorrelation of the first-differenced series (a simple,
    transparent detrending step — removes a linear trend's dominant
    contribution to the ACF without fitting a model)."""
    series = np.asarray(series, dtype=float)
    if len(series) < 3:
        return np.full(max_lag + 1, np.nan)
    diffed = np.diff(series)
    return autocorrelation(diffed, max_lag)


def periodogram(series: np.ndarray, sampling_period: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """Power spectral density via a straightforward FFT-based periodogram
    (Welch/scipy not required — this is a short, transparent
    implementation adequate for an exploratory look at whether power
    concentrates at a non-trivial frequency)."""
    series = np.asarray(series, dtype=float)
    n = len(series)
    if n < 2:
        return np.array([]), np.array([])
    centered = series - series.mean()
    freqs = np.fft.rfftfreq(n, d=sampling_period)
    power = (np.abs(np.fft.rfft(centered)) ** 2) / n
    return freqs, power


def stationarity_heuristic(series: np.ndarray, n_windows: int = 5) -> dict:
    """A lightweight, explicitly informal stationarity *indicator* — not a
    substitute for a real unit-root test (e.g. ADF), which this project
    does not implement to avoid an extra heavy dependency for a milestone
    that only needs a first-pass signal. Splits the series into
    ``n_windows`` contiguous chunks and reports the coefficient of
    variation of the chunk means and of the chunk variances: values close
    to 0 suggest stability across the run; large values suggest the
    series' level or spread is drifting."""
    series = np.asarray(series, dtype=float)
    if n_windows < 2 or len(series) < n_windows * 2:
        return {"chunk_mean_cv": float("nan"), "chunk_var_cv": float("nan"), "n_windows": n_windows}
    chunks = np.array_split(series, n_windows)
    chunk_means = np.array([c.mean() for c in chunks])
    chunk_vars = np.array([c.var() for c in chunks])

    def _cv(x: np.ndarray) -> float:
        m = np.mean(x)
        return float(np.std(x) / abs(m)) if m != 0 else float("nan")

    return {"chunk_mean_cv": _cv(chunk_means), "chunk_var_cv": _cv(chunk_vars), "n_windows": n_windows}


def change_point_candidates(series: np.ndarray, window: int = 10, z_threshold: float = 3.0) -> list[int]:
    """Simple rolling-mean-shift detector: flags step indices where the
    difference between the trailing rolling mean and the *next* window's
    rolling mean, standardized by the series' overall standard deviation,
    exceeds ``z_threshold``. Deliberately simple (no changepoint library
    dependency) — these are *candidates* for visual/manual follow-up, not
    a validated segmentation."""
    series = np.asarray(series, dtype=float)
    n = len(series)
    if n < 2 * window:
        return []
    overall_std = series.std()
    if overall_std == 0:
        return []
    candidates = []
    for i in range(window, n - window):
        before = series[i - window : i].mean()
        after = series[i : i + window].mean()
        z = abs(after - before) / overall_std
        if z >= z_threshold:
            candidates.append(i)
    return candidates


def regime_time_fraction(series: np.ndarray, n_bins: int = 5) -> dict:
    """Fraction of steps spent in each of ``n_bins`` equal-width bins
    spanning the series' own observed range — an empirical, run-specific
    partition (not a fixed, pre-imposed classification) of "which region
    of the observable's range was the system in, and how much of the
    time." Returns bin edges alongside the fractions."""
    series = np.asarray(series, dtype=float)
    if len(series) == 0:
        return {"bin_edges": [], "fractions": []}
    lo, hi = float(series.min()), float(series.max())
    if lo == hi:
        return {"bin_edges": [lo, hi], "fractions": [1.0]}
    edges = np.linspace(lo, hi, n_bins + 1)
    counts, _ = np.histogram(series, bins=edges)
    fractions = (counts / counts.sum()).tolist()
    return {"bin_edges": edges.tolist(), "fractions": fractions}


def endpoint_dispersion(endpoint_values: np.ndarray) -> dict:
    """Summary of how dispersed a set of per-seed *endpoint* (or
    terminal-window-mean) values are — the between-seed counterpart to a
    single trajectory's within-run variance. Wide dispersion here means
    different seeds settle in different places; narrow dispersion is a
    (necessary, not sufficient) precondition for calling a region an
    attractor."""
    values = np.asarray(endpoint_values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return {"n": 0, "mean": float("nan"), "std": float("nan"), "iqr": float("nan"), "min": float("nan"), "max": float("nan")}
    return {
        "n": int(len(values)),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "iqr": float(np.percentile(values, 75) - np.percentile(values, 25)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
    }
