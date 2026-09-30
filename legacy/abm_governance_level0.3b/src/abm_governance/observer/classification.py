"""Dynamical classification discipline (Level 0.2, Work Package I).

Every classification here is: (1) operationally defined by an explicit,
documented, overridable threshold — never a bare magic number; (2)
computed entirely from observer-layer data (a run's metrics series and/or
event log) — never fed back into, or read by, any generative decision
function; (3) duration-based where the milestone brief asks for
persistence, not a one-step trigger. This module intentionally does not
use the word "attractor" anywhere, and no caller should either, unless it
has *separately* established all three of: convergence (the system
reaches the candidate state), persistence (it stays there absent further
input), and perturbation recovery (it returns there after a shock) — see
``docs/level0.2_scientific_note.md`` for the explicit test each Work
Package J result must pass before that word is used in any report.

All functions take plain data (a list of per-step metric dicts, as
produced by ``observer/metrics.py::compute_step_metrics``, and/or an
:class:`~abm_governance.core.events.EventLog`) and explicit threshold
parameters with documented defaults; nothing here reads global config or
mutates its inputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

DEFAULT_DEPLETION_OCCUPANCY_THRESHOLD = 0.05
DEFAULT_COLLAPSE_MIN_DURATION = 20
DEFAULT_RECOVERY_OCCUPANCY_THRESHOLD = 0.05
DEFAULT_RECOVERY_MIN_DURATION = 10
DEFAULT_POPULATION_FAILURE_FRACTION = 0.5
DEFAULT_CONVERGENCE_ENTROPY_THRESHOLD = 0.1
DEFAULT_CONVERGENCE_MIN_DURATION = 20


def _occupancy_series(metrics_rows: list[dict]) -> list[float]:
    return [r.get("environment_fraction_of_capacity", math.nan) for r in metrics_rows]


def depletion_flags(
    metrics_rows: list[dict],
    occupancy_threshold: float = DEFAULT_DEPLETION_OCCUPANCY_THRESHOLD,
) -> list[bool]:
    """Depletion: pool occupancy at/below ``occupancy_threshold`` this
    step. Instantaneous, per-step — see :func:`collapse_episodes` for the
    duration-gated "ecological collapse" classification built on top of
    this."""
    return [
        (not math.isnan(occ)) and occ <= occupancy_threshold
        for occ in _occupancy_series(metrics_rows)
    ]


@dataclass(frozen=True)
class Episode:
    """A contiguous run of steps satisfying some condition."""

    start_step: int
    end_step: int  # exclusive
    duration: int


def _episodes_from_flags(flags: list[bool], steps: list[int]) -> list[Episode]:
    episodes: list[Episode] = []
    start = None
    for i, flag in enumerate(flags):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            episodes.append(Episode(steps[start], steps[i], i - start))
            start = None
    if start is not None:
        episodes.append(Episode(steps[start], steps[-1] + 1, len(flags) - start))
    return episodes


def collapse_episodes(
    metrics_rows: list[dict],
    occupancy_threshold: float = DEFAULT_DEPLETION_OCCUPANCY_THRESHOLD,
    min_duration: int = DEFAULT_COLLAPSE_MIN_DURATION,
    require_sustained_unmet_demand: bool = True,
) -> list[Episode]:
    """Ecological collapse: a contiguous run of >= ``min_duration`` steps
    that are all "depleted" (see :func:`depletion_flags`) *and*, if
    ``require_sustained_unmet_demand`` (default), during which
    ``unmet_extraction_demand`` was positive on every one of those steps —
    persistent depletion with no slack, as opposed to a pool that happens
    to sit at zero occupancy while nobody wants to extract anything from
    it (which would not be "collapse" in any behaviourally meaningful
    sense). Returns every qualifying episode, not just the first."""
    depleted = depletion_flags(metrics_rows, occupancy_threshold)
    steps = [r["step"] for r in metrics_rows]
    if require_sustained_unmet_demand:
        unmet = [r.get("unmet_extraction_demand", math.nan) for r in metrics_rows]
        depleted = [
            d and (not math.isnan(u)) and u > 0.0 for d, u in zip(depleted, unmet)
        ]
    raw_episodes = _episodes_from_flags(depleted, steps)
    return [e for e in raw_episodes if e.duration >= min_duration]


def recovery_episodes(
    metrics_rows: list[dict],
    depletion_occupancy_threshold: float = DEFAULT_DEPLETION_OCCUPANCY_THRESHOLD,
    recovery_occupancy_threshold: float = DEFAULT_RECOVERY_OCCUPANCY_THRESHOLD,
    min_duration: int = DEFAULT_RECOVERY_MIN_DURATION,
) -> list[Episode]:
    """Recovery: a contiguous run of >= ``min_duration`` steps with
    occupancy strictly above ``recovery_occupancy_threshold``, that
    immediately follows at least one step at/below
    ``depletion_occupancy_threshold``. (Using two threshold parameters,
    rather than one, avoids classifying noise right at a single boundary
    value as alternating depletion/recovery — pass the same value for
    both if that distinction is not wanted.)"""
    occ = _occupancy_series(metrics_rows)
    steps = [r["step"] for r in metrics_rows]
    # `was_depleted` latches True the first time occupancy drops to/below
    # the depletion threshold and stays True afterward — it is *not*
    # cleared just because occupancy is currently above the recovery
    # threshold (a "recovery" episode's own steps must themselves still
    # count as "occurred after a depletion"). A later depletion dip
    # naturally starts a fresh above-threshold episode anyway, because
    # `above` (and therefore the flag) goes False during that dip —
    # `_episodes_from_flags` splits the episode there without any extra
    # bookkeeping needed.
    was_depleted = False
    above_flags: list[bool] = []
    for o in occ:
        above = (not math.isnan(o)) and o > recovery_occupancy_threshold
        above_flags.append(above and was_depleted)
        if (not math.isnan(o)) and o <= depletion_occupancy_threshold:
            was_depleted = True
    raw_episodes = _episodes_from_flags(above_flags, steps)
    return [e for e in raw_episodes if e.duration >= min_duration]


def population_failure(
    metrics_rows: list[dict],
    n_agents: int,
    fraction_threshold: float = DEFAULT_POPULATION_FAILURE_FRACTION,
) -> dict:
    """Population failure: the fraction of the population that is
    distressed or dormant reaches ``fraction_threshold`` at any step.
    Reports the peak fraction and whether/when the threshold was first
    crossed, rather than a single boolean, since "did it ever happen" and
    "how close did it get" are both scientifically relevant."""
    if n_agents <= 0:
        return {"ever_crossed": False, "first_step": None, "peak_fraction": math.nan}
    fractions = []
    for r in metrics_rows:
        distressed = r.get("distressed_population", math.nan)
        dormant = r.get("dormant_population", math.nan)
        if math.isnan(distressed) or math.isnan(dormant):
            fractions.append(math.nan)
            continue
        fractions.append((distressed + dormant) / n_agents)
    finite = [(i, f) for i, f in enumerate(fractions) if not math.isnan(f)]
    crossed = [(metrics_rows[i]["step"], f) for i, f in finite if f >= fraction_threshold]
    peak = max((f for _, f in finite), default=math.nan)
    return {
        "ever_crossed": bool(crossed),
        "first_step": crossed[0][0] if crossed else None,
        "peak_fraction": peak,
    }


def behavioural_convergence_episodes(
    metrics_rows: list[dict],
    entropy_threshold: float = DEFAULT_CONVERGENCE_ENTROPY_THRESHOLD,
    min_duration: int = DEFAULT_CONVERGENCE_MIN_DURATION,
) -> list[Episode]:
    """Behavioural convergence: a contiguous run of >= ``min_duration``
    steps with ``policy_diversity_bits`` at/below ``entropy_threshold``
    (near-zero Shannon entropy over living agents' policy names — i.e.
    the population is behaviourally almost homogeneous). This is a purely
    descriptive statement about *policy-label* diversity; it makes no
    claim about *why* diversity fell (genuine behavioural convergence,
    demographic filtering removing the agents who held other policies, or
    the observer-side measurement itself compressing a more heterogeneous
    underlying reality — that distinction is exactly what Work Package F's
    reporting is required to separately test, not something this function
    can determine on its own)."""
    entropy = [r.get("policy_diversity_bits", math.nan) for r in metrics_rows]
    steps = [r["step"] for r in metrics_rows]
    flags = [(not math.isnan(e)) and e <= entropy_threshold for e in entropy]
    raw_episodes = _episodes_from_flags(flags, steps)
    return [e for e in raw_episodes if e.duration >= min_duration]
