"""Level 1.3, Work Package F (Section 11): institutional conversion
detection.

Context-loss disclosure (same caveat as B/C/D/E): the verbatim Section
11 spec text is not recoverable in this session's context after
compaction. ``core/rng.py::STREAM_REGISTRY``'s own docstring lists this
work package among "Work Packages B/F/G/H ... purely observer-side
measurement over already-generated state [drawing] no random numbers
of their own" -- so, as with Work Package B, this module is a read-only
measurement layer over ``EventLog``, never a new generative mechanism,
and is built accordingly: pure functions, zero RNG, zero config-flag
gating (nothing to disable -- there is no new behavior for a flag to
gate).

Absent the verbatim text, "institutional conversion" is read as its
established meaning in the historical-institutionalism literature this
project's own dissertation source sits within (Streeck & Thelen 2005;
Mahoney & Thelen 2010's typology of gradual institutional change): an
institution that persists in FORM -- the same rule, never dissolved,
never formally replaced -- while its FUNCTION -- what it is actually,
predominantly used for -- changes. This is explicitly distinct from
what this codebase already measures elsewhere: formal replacement
(``RuleDissolutionEvent`` + a later independent adoption -- already
observable directly from the event log) and mere accumulation of new
rules alongside old ones (no measurement needed beyond counting active
rules). Conversion is the one path-dependence-relevant transition NOT
already directly legible from existing event types, which is why it
gets its own detection module here.

Operationalization, reusing (not duplicating the *meaning* of, though
the interval-building helpers below are intentionally re-derived
locally rather than importing ``observer/sequencing_diagnostics.py``'s
private helpers, to keep the two observer modules independently
readable) the same six governance "function families" Work Package B
established (``delegation``, ``monitoring``, ``sanctioning``,
``accountability``, ``contribution``, ``coordination``):

1. For each rule, build a chronological list of every family-exercising
   event that touches it (not just the FIRST touch per family, as Work
   Package B's ``generalized_rule`` series uses -- conversion needs
   relative VOLUME, not just presence, to identify which family
   currently dominates).
2. Compute that rule's "dominant family" in a trailing window of
   ``window_steps`` at every step of its active lifetime, requiring at
   least ``min_window_activity`` touches in the window before any
   family is called dominant (an under-active window says nothing about
   which function is in use).
3. The rule's "founding family" is the first dominant family that
   window reaches once enough activity has accumulated after adoption.
4. A conversion is recorded the first time a DIFFERENT family becomes,
   and then remains, dominant for at least ``min_persistence_steps``
   consecutive steps -- the persistence requirement exists so a single
   noisy window flip is not mistaken for a genuine functional shift.

A rule that is dissolved and never reconstituted cannot convert (there
is no "later" for its function to have changed into) -- conversion is
by construction a property of institutional PERSISTENCE, mirroring the
Work Package C/D framing that entrenchment and legitimacy are also
properties of institutions that persist rather than get replaced."""

from __future__ import annotations

from collections import Counter

import numpy as np

from abm_governance.core.events import EventLog

#: Same six governance function families Work Package B's
#: ``generalized_rule`` series uses -- see this module's own docstring
#: for why the vocabulary is shared but the two modules' helper
#: functions are not.
FUNCTION_FAMILIES: tuple[str, ...] = (
    "delegation", "monitoring", "sanctioning", "accountability", "contribution", "coordination",
)

DEFAULT_WINDOW_STEPS = 50
DEFAULT_MIN_WINDOW_ACTIVITY = 3
DEFAULT_MIN_PERSISTENCE_STEPS = 20


class ConversionRecord:
    """One detected conversion: rule ``rule_id`` (adopted at
    ``adopt_step`` on ``patch_id``) shifted from predominantly serving
    ``founding_family`` to predominantly serving ``converted_family``,
    with the shift confirmed (sustained for ``min_persistence_steps``)
    as of ``detected_step``."""

    __slots__ = ("rule_id", "patch_id", "adopt_step", "founding_family", "converted_family", "detected_step")

    def __init__(self, rule_id, patch_id, adopt_step, founding_family, converted_family, detected_step):
        self.rule_id = rule_id
        self.patch_id = patch_id
        self.adopt_step = adopt_step
        self.founding_family = founding_family
        self.converted_family = converted_family
        self.detected_step = detected_step

    def __eq__(self, other):
        if not isinstance(other, ConversionRecord):
            return NotImplemented
        return (
            self.rule_id, self.patch_id, self.adopt_step,
            self.founding_family, self.converted_family, self.detected_step,
        ) == (
            other.rule_id, other.patch_id, other.adopt_step,
            other.founding_family, other.converted_family, other.detected_step,
        )

    def __repr__(self):
        return (
            f"ConversionRecord(rule_id={self.rule_id}, patch_id={self.patch_id}, "
            f"adopt_step={self.adopt_step}, founding_family={self.founding_family!r}, "
            f"converted_family={self.converted_family!r}, detected_step={self.detected_step})"
        )


def _in_scope(patch_id: int, patch_ids: frozenset[int] | None) -> bool:
    return patch_ids is None or patch_id in patch_ids


def _rule_lifetimes(event_log: EventLog, patch_ids: frozenset[int] | None):
    """rule_id -> (adopt_step, patch_id, dissolve_step_or_None). Locally
    re-derived (see module docstring) rather than imported from
    ``sequencing_diagnostics.py``."""
    lifetimes: dict[int, list] = {}
    for e in event_log.rule_adoptions:
        if _in_scope(e.patch_id, patch_ids):
            lifetimes[e.rule_id] = [e.step, e.patch_id, None]
    for e in event_log.rule_dissolutions:
        if e.rule_id in lifetimes:
            lifetimes[e.rule_id][2] = e.step
    return lifetimes


def _rule_family_touches(event_log: EventLog, patch_ids: frozenset[int] | None) -> dict[int, list[tuple[int, str]]]:
    """rule_id -> chronologically-sorted list of every (step, family)
    event touching that rule -- EVERY occurrence, not just the first per
    family (see module docstring: conversion needs relative volume)."""
    touches: dict[int, list[tuple[int, str]]] = {}

    def _record(rid: int, family: str, step: int) -> None:
        touches.setdefault(rid, []).append((step, family))

    for e in event_log.delegate_appointments:
        if _in_scope(e.patch_id, patch_ids):
            _record(e.rule_id, "delegation", e.step)
    for e in event_log.monitorings:
        if _in_scope(e.patch_id, patch_ids):
            _record(e.rule_id, "monitoring", e.step)
    for e in event_log.sanctions:
        if _in_scope(e.patch_id, patch_ids):
            _record(e.rule_id, "sanctioning", e.step)
    for e in event_log.audits:
        if _in_scope(e.patch_id, patch_ids):
            _record(e.rule_id, "accountability", e.step)
    for e in event_log.recalls:
        if _in_scope(e.patch_id, patch_ids):
            _record(e.rule_id, "accountability", e.step)
    for e in event_log.appeals:
        if _in_scope(e.patch_id, patch_ids):
            _record(e.rule_id, "accountability", e.step)
    for e in event_log.contributions:
        if _in_scope(e.patch_id, patch_ids):
            _record(e.rule_id, "contribution", e.step)
    for e in event_log.coordination_proposals:
        if _in_scope(e.patch_id_from, patch_ids):
            _record(e.rule_id_from, "coordination", e.step)
        if _in_scope(e.patch_id_to, patch_ids):
            _record(e.rule_id_to, "coordination", e.step)

    for rid in touches:
        touches[rid].sort(key=lambda st: st[0])
    return touches


def _dominant_family_series(
    touches: list[tuple[int, str]], lo: int, hi: int, window_steps: int, min_window_activity: int,
) -> list[str | None]:
    """Sliding-window dominant-family value at every step in
    ``[lo, hi)``, ``None`` where fewer than ``min_window_activity``
    touches fall in the trailing window. O(len(touches) + (hi - lo))."""
    out: list[str | None] = []
    window: Counter = Counter()
    left = 0  # index of the oldest touch currently counted in `window`
    right = 0  # index of the next touch not yet added to `window`
    n = len(touches)
    for t in range(lo, hi):
        window_lo = t - window_steps + 1
        while right < n and touches[right][0] <= t:
            window[touches[right][1]] += 1
            right += 1
        while left < right and touches[left][0] < window_lo:
            family = touches[left][1]
            window[family] -= 1
            if window[family] <= 0:
                del window[family]
            left += 1
        if not window:
            out.append(None)
            continue
        family, count = window.most_common(1)[0]
        out.append(family if count >= min_window_activity else None)
    return out


def detect_conversions(
    event_log: EventLog,
    n_steps: int,
    patch_ids: frozenset[int] | None = None,
    window_steps: int = DEFAULT_WINDOW_STEPS,
    min_window_activity: int = DEFAULT_MIN_WINDOW_ACTIVITY,
    min_persistence_steps: int = DEFAULT_MIN_PERSISTENCE_STEPS,
) -> list[ConversionRecord]:
    """Scan every rule adopted during this run (within ``patch_ids`` if
    given) for at most one conversion each: the first sustained shift
    away from its founding dominant function family. Returns records in
    ascending ``detected_step`` order (ties broken by ``rule_id``)."""
    lifetimes = _rule_lifetimes(event_log, patch_ids)
    touches_by_rule = _rule_family_touches(event_log, patch_ids)
    records: list[ConversionRecord] = []

    for rule_id, (adopt_step, patch_id, dissolve_step) in lifetimes.items():
        lo = max(0, adopt_step)
        hi = n_steps if dissolve_step is None else min(n_steps, dissolve_step + 1)
        if hi <= lo:
            continue
        touches = touches_by_rule.get(rule_id, [])
        series = _dominant_family_series(touches, lo, hi, window_steps, min_window_activity)

        founding_family = next((f for f in series if f is not None), None)
        if founding_family is None:
            continue  # never accumulated enough activity to have a founding function at all.

        run_family = None
        run_start = None
        run_length = 0
        for offset, family in enumerate(series):
            if family is not None and family != founding_family:
                if family == run_family:
                    run_length += 1
                else:
                    run_family = family
                    run_start = lo + offset
                    run_length = 1
                if run_length >= min_persistence_steps:
                    records.append(ConversionRecord(
                        rule_id=rule_id, patch_id=patch_id, adopt_step=adopt_step,
                        founding_family=founding_family, converted_family=run_family, detected_step=run_start,
                    ))
                    break
            else:
                run_family = None
                run_start = None
                run_length = 0

    records.sort(key=lambda r: (r.detected_step, r.rule_id))
    return records


def conversion_incidence_series(
    event_log: EventLog,
    n_steps: int,
    patch_ids: frozenset[int] | None = None,
    window_steps: int = DEFAULT_WINDOW_STEPS,
    min_window_activity: int = DEFAULT_MIN_WINDOW_ACTIVITY,
    min_persistence_steps: int = DEFAULT_MIN_PERSISTENCE_STEPS,
) -> np.ndarray:
    """Fraction, at every step, of currently-active rules (within
    ``patch_ids`` if given) that have converted by that step -- one
    summary series in the same style as
    ``sequencing_diagnostics.institutional_response_series``'s eight
    dimensions, suitable to feed the same downstream observer/phenotype
    pipeline."""
    lifetimes = _rule_lifetimes(event_log, patch_ids)
    records = detect_conversions(
        event_log, n_steps, patch_ids, window_steps, min_window_activity, min_persistence_steps,
    )
    converted_from_step: dict[int, int] = {r.rule_id: r.detected_step for r in records}

    active_starts = [adopt for adopt, _pid, _dis in lifetimes.values()]
    active_ends = [dis for _adopt, _pid, dis in lifetimes.values()]
    converted_starts = [converted_from_step[rid] for rid in lifetimes if rid in converted_from_step]
    converted_ends = [lifetimes[rid][2] for rid in lifetimes if rid in converted_from_step]

    active_counts = _interval_counts(active_starts, active_ends, n_steps)
    converted_counts = _interval_counts(converted_starts, converted_ends, n_steps)
    return _safe_divide(converted_counts, active_counts)


def _interval_counts(starts, ends, n_steps: int) -> np.ndarray:
    """Same closed-interval diff-array sweep as
    ``sequencing_diagnostics._interval_counts`` (re-derived locally --
    see module docstring)."""
    delta = np.zeros(n_steps + 1, dtype=float)
    for s, e in zip(starts, ends):
        s = max(0, int(s))
        if s >= n_steps:
            continue
        if e is None:
            delta[s] += 1.0
            continue
        e = int(e)
        if e < s:
            continue
        delta[s] += 1.0
        delta[min(n_steps, e + 1)] -= 1.0
    return np.cumsum(delta[:n_steps])


def _safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    out = np.zeros_like(numerator, dtype=float)
    nonzero = denominator > 0
    out[nonzero] = numerator[nonzero] / denominator[nonzero]
    return out
