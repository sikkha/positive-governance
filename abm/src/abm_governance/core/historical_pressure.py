"""Level 1.3, Section 5: core historical variables.

Three exogenous, continuous pressure signals -- security/territorial
pressure (``W_t``), bargaining/constraint pressure (``B_t``), and
impersonal coordination complexity (``X_t``) -- as configurable TIME
SERIES, never static labels (Section 5's own explicit requirement).
This module owns only the SIGNAL itself: how a pressure history is
specified and generated. What the signal is allowed to affect
(Work Package A, Section 6) and how institutional response timing is
measured against it (Work Package B, Section 7) live elsewhere,
deliberately -- this module has no knowledge of agents, rules, or
institutions, and imports nothing from them.

Every pressure history kind Section 5 requires is implemented as one
parameterization of a single, small, auditable generator function
(:func:`generate_pressure_series`) rather than one bespoke function per
kind -- easier to verify no kind secretly does something the others
don't. All ten pressure-history history kinds are pure functions of
``(spec, n_steps)`` except ``"stochastic_reproducible"``, which
additionally consumes a caller-supplied, mechanism-specific RNG stream
(``core/rng.py``'s own ``"historical_pressure_generation"`` substream --
never a fresh unseeded draw).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

#: Section 5's required history kinds. "early_pulse"/"late_pulse" are
#: the SAME underlying pulse mechanism as each other (a single elevated
#: window against a low baseline) -- they are kept as two distinct
#: named kinds, per Section 5's own explicit list, purely so a caller's
#: *intent* ("early" vs "late" in the run) is legible from the kind
#: name itself, with ``onset_step`` still the actual authority over
#: where the pulse falls. "repeated_shocks" and "stochastic_
#: reproducible" are the two kinds capable of nonmonotonic/irregular
#: shapes; every other kind is monotonic or constant by construction.
VALID_PRESSURE_HISTORY_KINDS = (
    "constant_low",
    "constant_high",
    "early_pulse",
    "late_pulse",
    "gradual_rise",
    "gradual_decline",
    "repeated_shocks",
    "stochastic_reproducible",
)


@dataclass(frozen=True)
class PressureHistorySpec:
    """A complete, self-contained specification for one pressure
    channel's time series. Deliberately flat/primitive-only (mirrors
    every other mechanism's config-field convention in this codebase)
    so it round-trips through ``SimulationConfig``'s existing
    ``to_dict``/``to_yaml`` machinery without any special-casing."""

    kind: str = "constant_low"
    #: Baseline pressure level (used by every kind as the "off"/trough
    #: value).
    low_level: float = 0.1
    #: Peak/elevated pressure level ("constant_high", pulse peaks,
    #: shock peaks, and the endpoint of gradual_rise / start of
    #: gradual_decline).
    high_level: float = 0.5
    #: First step at which a pulse/rise/decline/shock-train begins.
    #: Ignored by "constant_low"/"constant_high".
    onset_step: int = 0
    #: Length, in steps, of a pulse's elevated window (``early_pulse``/
    #: ``late_pulse``) or of the rise/decline ramp itself
    #: (``gradual_rise``/``gradual_decline``). ``None`` means "to the
    #: end of the run" for a pulse, or "the entire remaining run" for a
    #: ramp.
    duration_steps: int | None = None
    #: Per-step exponential decay applied to the elevated portion AFTER
    #: a pulse's window closes (0.0 = the signal drops back to
    #: ``low_level`` immediately at the window's end; values in (0, 1)
    #: give a gradual fade governed by ``high - (high - low) * (1 -
    #: decay_rate) ** steps_since_window_end``, floored at
    #: ``low_level``).
    decay_rate: float = 0.0
    #: Std of the Gaussian noise added each step under
    #: "stochastic_reproducible" only (mean ``low_level``, floored at
    #: 0.0 so a pressure signal is never negative).
    volatility_std: float = 0.0
    #: "repeated_shocks" only: how many elevated pulses.
    n_shocks: int = 3
    #: "repeated_shocks" only: width, in steps, of each individual
    #: shock's elevated window.
    shock_width_steps: int = 5
    #: "repeated_shocks" only: steps between the START of one shock and
    #: the start of the next.
    shock_interval_steps: int = 20

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.kind not in VALID_PRESSURE_HISTORY_KINDS:
            errors.append(f"pressure history kind must be one of {VALID_PRESSURE_HISTORY_KINDS}, got {self.kind!r}")
        if self.low_level < 0:
            errors.append("pressure low_level must be >= 0")
        if self.high_level < self.low_level:
            errors.append("pressure high_level must be >= low_level")
        if self.onset_step < 0:
            errors.append("pressure onset_step must be >= 0")
        if self.duration_steps is not None and self.duration_steps < 1:
            errors.append("pressure duration_steps must be >= 1 when set")
        if not (0.0 <= self.decay_rate <= 1.0):
            errors.append("pressure decay_rate must be in [0, 1]")
        if self.volatility_std < 0:
            errors.append("pressure volatility_std must be >= 0")
        if self.n_shocks < 0:
            errors.append("pressure n_shocks must be >= 0")
        if self.shock_width_steps < 1:
            errors.append("pressure shock_width_steps must be >= 1")
        if self.shock_interval_steps < 1:
            errors.append("pressure shock_interval_steps must be >= 1")
        return errors


def generate_pressure_series(
    spec: PressureHistorySpec, n_steps: int, rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Deterministic (except under ``"stochastic_reproducible"``, where
    it is deterministic GIVEN ``rng``'s state) length-``n_steps`` array.

    ``rng`` must be supplied (and must be the caller's own
    ``"historical_pressure_generation"`` substream -- see
    ``Simulation.__init__``) whenever ``spec.kind ==
    "stochastic_reproducible"``; every other kind ignores it entirely,
    so passing ``None`` for a non-stochastic kind is always safe and
    never silently falls back to an unseeded source.
    """
    errors = spec.validate()
    if errors:
        raise ValueError("; ".join(errors))
    if n_steps < 1:
        raise ValueError("n_steps must be >= 1")

    steps = np.arange(n_steps)
    low, high = spec.low_level, spec.high_level

    if spec.kind == "constant_low":
        return np.full(n_steps, low, dtype=float)
    if spec.kind == "constant_high":
        return np.full(n_steps, high, dtype=float)

    if spec.kind in ("early_pulse", "late_pulse"):
        duration = spec.duration_steps if spec.duration_steps is not None else max(1, n_steps - spec.onset_step)
        window_end = spec.onset_step + duration
        series = np.full(n_steps, low, dtype=float)
        in_window = (steps >= spec.onset_step) & (steps < window_end)
        series[in_window] = high
        after = steps >= window_end
        if spec.decay_rate > 0.0 and np.any(after):
            steps_since = (steps[after] - window_end + 1).astype(float)
            decayed = low + (high - low) * ((1.0 - spec.decay_rate) ** steps_since)
            series[after] = np.maximum(decayed, low)
        return series

    if spec.kind == "gradual_rise":
        duration = spec.duration_steps if spec.duration_steps is not None else max(1, n_steps - spec.onset_step)
        series = np.full(n_steps, low, dtype=float)
        ramp_end = min(n_steps, spec.onset_step + duration)
        if ramp_end > spec.onset_step:
            frac = (steps[spec.onset_step:ramp_end] - spec.onset_step) / max(1, duration - 1) if duration > 1 else np.zeros(ramp_end - spec.onset_step)
            series[spec.onset_step:ramp_end] = low + (high - low) * frac
        if ramp_end < n_steps:
            series[ramp_end:] = high
        return series

    if spec.kind == "gradual_decline":
        duration = spec.duration_steps if spec.duration_steps is not None else max(1, n_steps - spec.onset_step)
        series = np.full(n_steps, high, dtype=float)
        ramp_end = min(n_steps, spec.onset_step + duration)
        if ramp_end > spec.onset_step:
            frac = (steps[spec.onset_step:ramp_end] - spec.onset_step) / max(1, duration - 1) if duration > 1 else np.zeros(ramp_end - spec.onset_step)
            series[spec.onset_step:ramp_end] = high - (high - low) * frac
        if ramp_end < n_steps:
            series[ramp_end:] = low
        # Steps before onset stay at the pre-decline baseline (high),
        # consistent with "decline FROM high starting at onset".
        series[:spec.onset_step] = high
        return series

    if spec.kind == "repeated_shocks":
        series = np.full(n_steps, low, dtype=float)
        for i in range(spec.n_shocks):
            shock_start = spec.onset_step + i * spec.shock_interval_steps
            shock_end = shock_start + spec.shock_width_steps
            if shock_start >= n_steps:
                break
            lo, hi = max(0, shock_start), min(n_steps, shock_end)
            if lo < hi:
                series[lo:hi] = high
        return series

    if spec.kind == "stochastic_reproducible":
        if rng is None:
            raise ValueError('rng is required for kind="stochastic_reproducible"')
        noise = rng.normal(loc=0.0, scale=spec.volatility_std, size=n_steps)
        return np.maximum(low + noise, 0.0)

    raise ValueError(f"unhandled pressure history kind: {spec.kind!r}")  # pragma: no cover -- guarded by validate()


def cumulative_exposure(series: np.ndarray) -> float:
    """Total exposure -- Section 5's own "matched cumulative exposure"
    notion: :math:`\\sum_t W_t`."""
    return float(np.sum(series))


def rescale_to_target_exposure(series: np.ndarray, target_exposure: float) -> np.ndarray:
    """Uniformly rescale a nonnegative series so its cumulative
    exposure equals ``target_exposure`` exactly, preserving the
    series' own temporal SHAPE (relative timing of highs/lows is
    unchanged -- only magnitude is scaled). Used by Stage 3's paired
    sequence-reversal / matched-cumulative-exposure experiment designs
    (Section 15) to hold total exposure equal across two conditions
    while their temporal order differs; not used by
    :func:`generate_pressure_series` itself.

    A series that already sums to exactly zero cannot be rescaled to a
    nonzero target (there is no shape to preserve) and is returned
    unchanged in that degenerate case -- callers building matched pairs
    must not pass an all-zero base series when a nonzero target is
    required.
    """
    if target_exposure < 0:
        raise ValueError("target_exposure must be >= 0")
    total = float(np.sum(series))
    if total == 0.0:
        return np.array(series, dtype=float, copy=True)
    return np.asarray(series, dtype=float) * (target_exposure / total)


def first_sustained_crossing(series: np.ndarray, threshold: float, min_duration_steps: int) -> int | None:
    """Generic observer-side "first sustained activation" primitive:
    the first step at which ``series`` is at or above ``threshold`` for
    at least ``min_duration_steps`` CONSECUTIVE steps (a single spike
    that immediately falls back below threshold does not count -- this
    is Section 7's own "preregistered sustained-duration criterion,"
    applied here generically so every institutional-response series
    Work Package B measures shares one audited implementation rather
    than N bespoke ones). Returns ``None`` if no such run exists
    anywhere in ``series`` (Section 7: "do not assign a sequencing
    category where either activation is absent").

    This function knows nothing about pressure, security, bargaining,
    or institutions -- it is a pure sequence primitive, reused
    identically by Work Package B for every one of its eight tracked
    institutional-response series.
    """
    if min_duration_steps < 1:
        raise ValueError("min_duration_steps must be >= 1")
    series = np.asarray(series)
    above = series >= threshold
    run_length = 0
    for i, is_above in enumerate(above):
        run_length = run_length + 1 if is_above else 0
        if run_length >= min_duration_steps:
            return i - min_duration_steps + 1
    return None
