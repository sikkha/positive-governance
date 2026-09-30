"""Level 1.3, Work Package E (Section 10): history erasure and sequence
reversal counterfactuals.

Context-loss disclosure (read this before trusting the design below):
this module was written after this session's context was compacted at
least once. The verbatim Section 10 spec text is no longer available;
what survives is (a) ``core/rng.py::STREAM_REGISTRY``'s own docstring,
which lists Work Packages B/F/G/H as "purely observer-side measurement
... draw no random numbers of their own" but does NOT list E in that
set nor reserve E a named substream, and (b) the general Level 1.3
scaffold (frozen-reference compatibility, master-flag-gated additions).
Absent the verbatim text, this module is built on the most literal,
defensible reading of the work package's own name -- "history erasure
and sequence reversal counterfactuals" -- as two pure, deterministic
array transforms applied to an already-generated pressure series,
combined with the matched-seed construction machinery added to
``Simulation.__init__`` in this same task (the
``historical_pressure_series_override`` parameter). This interpretive
choice is disclosed here and in ``dev_mem/status_update.md`` rather
than presented as certain recovery of the original spec.

Why these are pure transforms and not a new generative mechanism:
both functions below take a concrete, already-realized ``np.ndarray``
(read back from a completed run's ``sim.historical_state[state_key]``)
and return a new array -- they consume no RNG, mutate no simulation
state, and are not called anywhere inside ``Simulation`` itself. This
is why neither function appears in ``STREAM_REGISTRY`` and why the
Section 3 structural guard (``test_no_other_generative_module_
references_historical_flags_yet``) does not need a new allowlist entry
for this file: it never reads any ``*_enabled`` flag.

The matched-pair construction pattern this module is designed for:

    base_sim = Simulation(base_config)   # base_config.seed == S
    base_sim.run()
    realized = base_sim.historical_state["security_pressure"]

    counterfactual_series = erase_pressure_from(realized, step=onset_step)
    # or: reverse_pressure_order(realized)

    cf_sim = Simulation(
        base_config,  # same seed S -> identical population/agent RNG draws
        historical_pressure_series_override={"security_pressure": counterfactual_series},
    )
    cf_sim.run()

Because ``base_config`` and the override run share the same ``seed``,
every RNG stream OTHER than ``historical_pressure_generation`` itself
(population initialization, social interaction, rule formation, ...)
draws identically in both runs regardless of what is overridden, since
each named stream is its own independent ``SeedSequence`` spawn. Any
divergence in downstream institutional outcomes is then attributable
to the counterfactual manipulation, not to confounded re-randomization
in an unrelated mechanism.

One caveat within the ``historical_pressure_generation`` stream itself:
overriding a channel makes ``Simulation.__init__`` skip that channel's
draw from the shared ``pressure_rng`` entirely (see the override branch
in ``Simulation.__init__``), which shifts the draws consumed by any
OTHER, non-overridden, still-generated channel later in the same loop
(security -> bargaining -> coordination order). This is harmless --
still fully reproducible, still deterministic -- for the two matched-
pair shapes this module is designed for: (a) exactly one pressure
channel enabled in ``base_config`` (nothing else to shift), or (b)
every enabled channel supplied via the override dict together (no
generation happens on ``pressure_rng`` in either run, so there is
nothing to shift). It is a real, disclosed limitation for a THIRD
shape -- overriding only some of several simultaneously-enabled
channels -- where the non-overridden channel(s) would generate a
different series in the override run than they did in the base run.
Callers doing multi-channel counterfactual work should prefer shape
(b) (override every enabled channel, even the ones left at their
realized/unmodified shape) to sidestep this entirely.

This exact exercise -- run pairs at experimental scale and analyze the
resulting divergence -- is Stage 5 (task #100, "causal historical
counterfactuals (matched-seed)"), not this module; this module
supplies only the two transform primitives and leaves the experimental
design to that later stage.

Two counterfactual families:

``erase_pressure_from``
    "What if the pressure that in fact arrived at ``step`` had never
    arrived?" -- everything before ``step`` is left untouched (the
    institutional history up to that point is not rewritten), and
    everything from ``step`` onward is flattened to ``floor_level``,
    removing the shock/pressure episode entirely rather than merely
    delaying or damping it.

``reverse_pressure_order``
    "What if this channel's pressure had arrived in the opposite
    temporal order?" -- a full time-reversal of the series
    (``series[::-1]``). This is the single-channel building block for
    testing sequencing effects: applying it to one channel while
    leaving others at their realized shape produces a run where that
    one channel's *order* (not its total pressure, not its volatility
    -- ``sum`` and the multiset of values are exactly preserved) is
    inverted relative to the other channels, isolating order as the
    manipulated variable.

``equalize_pressure_series`` (added Level 1.3b, task #118/Stage 5)
    "What if this channel's pressure had arrived smoothly rather than
    in a pulse/shock/staggered pattern?" -- every entry is replaced by
    the series' own mean, so ``sum``/cumulative exposure is preserved
    EXACTLY (matching this milestone's own Section 9 "matched
    cumulative pressure exposure" convention, Stage 3's own contrast
    discipline) while every trace of temporal STRUCTURE -- onset
    timing, ordering relative to other channels, shock/pulse shape --
    is removed. Where ``reverse_pressure_order`` isolates order while
    preserving shape, ``equalize_pressure_series`` is the complementary
    isolation: it removes order (and shape) entirely while preserving
    only total exposure, the natural counterfactual for asking whether
    institutional response depends on pressure HISTORY at all, or only
    on its running total."""

from __future__ import annotations

import numpy as np


def erase_pressure_from(series: np.ndarray, step: int, floor_level: float = 0.0) -> np.ndarray:
    """Return a copy of ``series`` with every entry from index ``step``
    onward replaced by ``floor_level`` -- i.e. the counterfactual in
    which the pressure episode realized at/after ``step`` never
    occurred. Entries before ``step`` are returned unchanged.

    ``step`` may be 0 (erase the entire series) or >= ``len(series)``
    (a full no-op copy, since there is nothing at or after that index).
    Negative ``step`` is not a supported counterfactual and raises.
    """
    if step < 0:
        raise ValueError(f"step must be >= 0, got {step}")
    out = np.array(series, dtype=float, copy=True)
    out[step:] = floor_level
    return out


def reverse_pressure_order(series: np.ndarray) -> np.ndarray:
    """Return a time-reversed copy of ``series``: the value realized at
    the last step becomes the value at step 0 and vice versa. The
    multiset of values (and therefore ``sum``/``mean``/``std``) is
    exactly preserved -- only temporal order changes, isolating
    sequencing as the manipulated variable."""
    out = np.array(series, dtype=float, copy=True)
    return out[::-1].copy()


def equalize_pressure_series(series: np.ndarray) -> np.ndarray:
    """Return a constant series at ``series``'s own mean -- the
    counterfactual "what if this exact total exposure had arrived
    smoothly instead of with this temporal shape?" ``sum`` (cumulative
    exposure) is preserved exactly (up to floating-point summation
    order); every temporal feature (onset, duration, shock structure,
    ordering relative to other channels) is removed. See module
    docstring's "Two counterfactual families" section (now three) for
    the full disclosure of what this isolates relative to
    ``reverse_pressure_order``."""
    out = np.array(series, dtype=float, copy=True)
    if out.size == 0:
        return out
    return np.full_like(out, float(np.mean(out)))
