"""Level 1.3, Work Package G (Section 12): observer-side S_obs/Z_obs
measurement layer.

Per ``docs/level1.3_theoretical_translation.md`` §2 and
``dev_mem/project_vision.md`` §5's structural firewall (restated in
that doc, not repeated here to avoid duplicating vocabulary this
project's own guard treats as sensitive): ``S_obs``/``Z_obs`` are
observer-side, post-hoc, model-ANALOGOUS measurements built from this
ABM's own simulated event history. They are not the dissertation's
survey-derived latent variables, do not use the dissertation's item
wording or fitted factor loadings, and are never read by any generative
mechanism anywhere in this codebase (see ``tests/test_level13_
compatibility.py``'s structural guard, and this module's own zero-flag-
footprint design below, which is why no allowlist entry is needed for
it there).

Context-loss disclosure (same caveat as every other Level 1.3 work
package this session): the verbatim Section 12 text is not recoverable
after this session's compaction. What is recoverable and IS treated as
authoritative here is ``docs/level1.3_theoretical_translation.md``'s
own correspondence table entry (written earlier in this session, while
the source text was still in context): the dissertation's two SEM
constructs feed a governance-equilibrium relationship between an
administrative/coordinative-capacity axis and a negotiated/reciprocal-
constraint axis. Given that framing but not the dissertation's own
specific item list, this module builds both axes purely by RE-USING
series this project has ALREADY computed for other, independently-
justified reasons in Work Packages B and D (never invented fresh for
this purpose, and never fit to reproduce any particular external
number):

``S_obs`` (capacity/coordination axis) is the unweighted mean, at each
step, of: Work Package B's ``delegation``, ``administrative_function``,
``monitoring``, and ``interpatch_coordination`` series, plus this
module's own ``performance_legitimacy_series`` (a rule that reliably
delivers -- Work Package D's "performance" legitimacy channel -- is the
same kind of capacity-to-govern-effectively signal, so it is included
here rather than only under Z).

``Z_obs`` (negotiated-constraint axis) is the unweighted mean, at each
step, of: Work Package B's ``accountability`` and
``bargaining_participation`` series, plus this module's own
``procedural_legitimacy_series`` (consent obtained through fair
process, not raw output, is exactly what a constraint-on-power axis is
about).

This is a disclosed, deliberately simple design choice (equal weights,
not a fitted measurement model) -- the point is a defensible, legible,
non-circular observer construct built from mechanisms this project
already independently justified, NOT a recreation of the dissertation's
specific factor structure. Both `*_legitimacy_series` helpers read
``EventLog.legitimacy_events`` directly and are well-defined (all-zero)
whether or not the underlying legitimacy channels were ever enabled --
this module reads no ``*_enabled`` config flag anywhere, matching the
"purely observer-side ... no random numbers of their own" scope
``core/rng.py`` documents for Work Packages B/F/G/H."""

from __future__ import annotations

import numpy as np

from abm_governance.core.events import EventLog
from abm_governance.observer.sequencing_diagnostics import institutional_response_series

#: The Work Package B dimensions folded into each axis. Kept as module-
#: level constants (not hardcoded inline) so a downstream reader can see
#: the composite's exact membership without reading the function body.
S_OBS_RESPONSE_DIMENSIONS: tuple[str, ...] = (
    "delegation", "administrative_function", "monitoring", "interpatch_coordination",
)
Z_OBS_RESPONSE_DIMENSIONS: tuple[str, ...] = (
    "accountability", "bargaining_participation",
)


def _in_scope(patch_id: int, patch_ids: frozenset[int] | None) -> bool:
    return patch_ids is None or patch_id in patch_ids


def performance_legitimacy_series(
    event_log: EventLog, n_steps: int, patch_ids: frozenset[int] | None = None,
) -> np.ndarray:
    """Mean ``performance_legitimacy`` across every ``LegitimacyEvent``
    logged at each step (population-wide, or restricted to
    ``patch_ids``). All-zero for every step with no logged events at
    all -- including every step of a run where Work Package D's
    performance channel was never enabled, which is the intended,
    flag-free behavior (see module docstring)."""
    sums = np.zeros(n_steps, dtype=float)
    counts = np.zeros(n_steps, dtype=float)
    for e in event_log.legitimacy_events:
        if 0 <= e.step < n_steps and _in_scope(e.patch_id, patch_ids):
            sums[e.step] += e.performance_legitimacy
            counts[e.step] += 1.0
    out = np.zeros(n_steps, dtype=float)
    nonzero = counts > 0
    out[nonzero] = sums[nonzero] / counts[nonzero]
    return out


def procedural_legitimacy_series(
    event_log: EventLog, n_steps: int, patch_ids: frozenset[int] | None = None,
) -> np.ndarray:
    """Mean ``procedural_legitimacy`` across every ``LegitimacyEvent``
    logged at each step -- see ``performance_legitimacy_series`` for the
    identical all-zero/flag-free behavior."""
    sums = np.zeros(n_steps, dtype=float)
    counts = np.zeros(n_steps, dtype=float)
    for e in event_log.legitimacy_events:
        if 0 <= e.step < n_steps and _in_scope(e.patch_id, patch_ids):
            sums[e.step] += e.procedural_legitimacy
            counts[e.step] += 1.0
    out = np.zeros(n_steps, dtype=float)
    nonzero = counts > 0
    out[nonzero] = sums[nonzero] / counts[nonzero]
    return out


def s_obs_series(event_log: EventLog, n_steps: int, patch_ids: frozenset[int] | None = None) -> np.ndarray:
    """The capacity/coordination axis -- see module docstring for the
    exact composite membership and rationale."""
    response = institutional_response_series(event_log, n_steps, patch_ids)
    components = [response[name] for name in S_OBS_RESPONSE_DIMENSIONS]
    components.append(performance_legitimacy_series(event_log, n_steps, patch_ids))
    return np.mean(np.stack(components, axis=0), axis=0)


def z_obs_series(event_log: EventLog, n_steps: int, patch_ids: frozenset[int] | None = None) -> np.ndarray:
    """The negotiated-constraint axis -- see module docstring for the
    exact composite membership and rationale."""
    response = institutional_response_series(event_log, n_steps, patch_ids)
    components = [response[name] for name in Z_OBS_RESPONSE_DIMENSIONS]
    components.append(procedural_legitimacy_series(event_log, n_steps, patch_ids))
    return np.mean(np.stack(components, axis=0), axis=0)


def s_obs_z_obs_series(
    event_log: EventLog, n_steps: int, patch_ids: frozenset[int] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Convenience wrapper computing both axes from one call -- shares
    no state between the two beyond the (idempotent, side-effect-free)
    ``institutional_response_series`` call each makes independently."""
    return s_obs_series(event_log, n_steps, patch_ids), z_obs_series(event_log, n_steps, patch_ids)


def s_obs_z_obs_summary(
    event_log: EventLog, n_steps: int, patch_ids: frozenset[int] | None = None, window_steps: int | None = None,
) -> dict[str, float]:
    """A single end-of-run scalar pair, ``{"S_obs": ..., "Z_obs": ...}``
    -- the mean of each axis's series over its trailing ``window_steps``
    (default: the full run). Intended as one candidate feature pair for
    Work Package H's downstream, outcome-blind discovery pipeline; this
    function does not itself select features or fit anything -- it only
    reduces a time series to one summary number, the same reduction
    ``first_sustained_crossing``'s callers already apply to Work Package
    B's own series elsewhere in this project."""
    s_series, z_series = s_obs_z_obs_series(event_log, n_steps, patch_ids)
    lo = 0 if window_steps is None else max(0, n_steps - window_steps)
    return {"S_obs": float(np.mean(s_series[lo:])), "Z_obs": float(np.mean(z_series[lo:]))}
