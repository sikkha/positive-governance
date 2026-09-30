"""Level 1.3, task #93: ecological control integration (feasibility
strata) for Level 1.3 designs.

Level 1.3 introduces no new ecological config field and no change to
the regeneration/consumption equations — ``observer/feasibility_
ratios.py`` (Level 1.2b, Section 6) is used here entirely UNMODIFIED,
against Level 1.3 configs, exactly as it was against Level 1.2b's own.
This module's job is narrow: give Level 1.3's own upcoming experiment
designs (Stages 2-4, 9) the SAME feasibility-stratification discipline
Level 1.2b's discovery design (``experiments/level12b_stage_e_joint_
discovery.py``) already established, factored out here as reusable
functions instead of the closure Level 1.2b redefined inline in each of
its own stage scripts (Section 9 there, Work Package E) — same
semantics, same three-label vocabulary, same tercile-cut-point
convention, single source of truth for Level 1.3's own scripts to share.

**This is integration, not a new empirical calibration.** The actual
Level 1.3 cut points (computed from Level 1.3's own design's ecological
draws) are frozen by Stage 2 (task #97, "calibration without phenotype
labels"), not here — this module only provides the machinery Stage 2
will call, plus a smoke-tested example design so the machinery itself
is proven correct before any stage depends on it.

**Naming discipline (unchanged from Level 1.2b):** ``low_feasibility``/
``medium_feasibility``/``high_feasibility``/``undefined`` are the only
labels this module ever produces — no governance-outcome, cluster, or
SEM-trajectory-adjacent vocabulary, matching ``feasibility_ratios.py``'s
own explicit prohibition."""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import qmc

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.feasibility_ratios import expected_pressure_ratio
from experiments.level12b_stage_c_feasibility_map import PARAMETER_SPACE as ECOLOGICAL_PARAMETER_SPACE

#: Work Package A's own two representative transmission sub-flags per
#: pressure channel (``core/historical_transmission.py``'s module
#: docstring) -- each channel's master ``*_enabled`` flag only gates
#: whether its pressure STATE series is generated at all; it is these
#: sub-flags, independently defaulted to ``False`` in ``config.py``,
#: that must ALSO be on for that pressure to have any behavioral
#: consequence via the transmission channels in ``rules/delegation.py``
#: / ``rules/contributions.py`` / ``rules/coordination.py``.
#:
#: **Bug this fixes (disclosed in ``dev_mem/status_update.md``,
#: task #109):** Stage 3 and Stage 4's first-draft ``_build_config``
#: functions, and Stage 5's first-draft ``_base_config``, set only the
#: master flag per enabled channel -- confirmed empirically (a Stage 5
#: matched base/erased/reversed sanity check produced byte-identical
#: event logs and S_obs/Z_obs despite genuinely different realized
#: pressure series) that this left every pressure channel a pure
#: observer-side no-op for institutional behavior in those stages'
#: original runs. This helper centralizes the correct wiring so every
#: Level 1.3 stage script that wants a channel to actually matter turns
#: on the SAME two sub-flags the same way, rather than each stage
#: hand-typing its own subset and risking the same silent omission
#: again.
TRANSMISSION_SUBFLAGS_BY_CHANNEL: dict[str, tuple[str, str]] = {
    "security_pressure": (
        "security_pressure_returns_to_delegation_enabled",
        "security_pressure_admin_capacity_demand_enabled",
    ),
    "bargaining_pressure": (
        "bargaining_pressure_conditional_contribution_enabled",
        "bargaining_pressure_appeal_recall_enabled",
    ),
    "coordination_complexity": (
        "coordination_complexity_cross_patch_transactions_enabled",
        "coordination_complexity_interoperable_demand_enabled",
    ),
}


def transmission_overrides_for_channel(channel: str) -> dict[str, bool]:
    """Both of Work Package A's own transmission sub-flags for
    ``channel``, set ``True`` -- the config surface that must ALSO be
    on (in addition to that channel's own master ``*_enabled`` flag,
    never instead of it) for the pressure to have any behavioral
    consequence. Sensitivities are left at their ``config.py`` defaults
    (all small positive values, disclosed there as chosen so an
    activation test can observe SOME effect the moment the flag is
    flipped) -- this helper only ever turns the sub-flags on, never
    tunes their magnitude."""
    return {flag: True for flag in TRANSMISSION_SUBFLAGS_BY_CHANNEL[channel]}

#: A fresh, disclosed LHS seed distinct from every Level 1.2b stage's
#: own (``experiments/level12b_stage_c_feasibility_map.py``'s
#: ``LHS_SEED``, ``experiments/level12b_stage_e_joint_discovery.py``'s
#: ``LHS_SEED_ECOLOGICAL``/``LHS_SEED_INSTITUTIONAL``) so Level 1.3's
#: own draws are independent, not a silent reuse of an earlier
#: milestone's random stream.
LHS_SEED_ECOLOGICAL_LEVEL13 = 20260820001

#: population_patch_ratio_selector is EXCLUDED here, mirroring Work
#: Package E's own exclusion in level12b_stage_e_joint_discovery.py:
#: population/patch structure is a scaling-robustness question (Level
#: 1.3's own Stage 9, task #104), not part of the ecological
#: feasibility axis itself.
ECOLOGICAL_SPACE_FOR_LEVEL13: tuple = tuple(
    t for t in ECOLOGICAL_PARAMETER_SPACE if t[0] != "population_patch_ratio_selector"
)


def ecological_lhs_draws(n: int, seed: int = LHS_SEED_ECOLOGICAL_LEVEL13) -> list[dict]:
    """Latin Hypercube sample over :data:`ECOLOGICAL_SPACE_FOR_LEVEL13`,
    scaled to each field's bounds — identical mechanics to Level 1.2b's
    own ``_lhs_draws`` helper (re-derived locally rather than imported,
    matching this project's established precedent of small, disclosed
    duplication over cross-milestone private-name coupling — see
    ``observer/institutional_conversion.py``'s own docstring for the
    same precedent)."""
    space = ECOLOGICAL_SPACE_FOR_LEVEL13
    sampler = qmc.LatinHypercube(d=len(space), seed=seed)
    unit_sample = sampler.random(n=n)
    lows = np.array([lo for _, lo, _ in space])
    highs = np.array([hi for _, _, hi in space])
    scaled = qmc.scale(unit_sample, lows, highs)
    names = [name for name, _, _ in space]
    return [dict(zip(names, row)) for row in scaled.tolist()]


def compute_stratum_cut_points(ratios: list[float]) -> tuple[float, float]:
    """Tercile cut points over the FINITE subset of ``ratios`` — Level
    1.2b's own convention exactly (``low_cut``/``high_cut`` at the 1/3
    and 2/3 order statistics), returned as ``(nan, nan)`` if fewer than
    3 finite ratios are available to cut (matching the "insufficient
    finite ratios" fallback that convention already documents)."""
    finite = sorted(r for r in ratios if math.isfinite(r))
    if len(finite) < 3:
        return float("nan"), float("nan")
    low_cut = finite[len(finite) // 3]
    high_cut = finite[(2 * len(finite)) // 3]
    return low_cut, high_cut


def feasibility_stratum(ratio: float, low_cut: float, high_cut: float) -> str:
    """Classify one ex-ante ``expected_pressure_ratio`` value against
    frozen cut points -- the single canonical version of the closure
    Level 1.2b's own stage scripts each redefined inline
    (``level12b_stage_e_joint_discovery.py``, ``level12b_stage_l0_
    confirmation_registry.py``), identical semantics and labels."""
    if not math.isfinite(ratio) or not math.isfinite(low_cut):
        return "undefined"
    if ratio <= low_cut:
        return "low_feasibility"
    if ratio <= high_cut:
        return "medium_feasibility"
    return "high_feasibility"


def build_ecological_feasibility_design(
    n_points: int, seed: int = LHS_SEED_ECOLOGICAL_LEVEL13,
    population_size: int = 32, n_patches: int = 4, n_steps: int = 700,
) -> dict:
    """One reusable Level 1.3 ecological feasibility design: ``n_points``
    Latin-Hypercube ecological draws, each scored with ``expected_
    pressure_ratio`` against a throwaway ``level12b_frozen_reference()``
    base config (every Level 1.3 mechanism left off — the ratio is a
    property of the ecological substrate alone, never of which Level
    1.3 mechanism is later layered on top; see this module's own
    docstring and the invariant test in ``tests/test_level13_
    feasibility_integration.py`` confirming Level 1.3 fields never move
    this ratio), tercile-stratified. Downstream Level 1.3 stage scripts
    (Stages 2-4, 9) call this directly rather than each re-deriving
    their own LHS/stratification logic, exactly mirroring how Level
    1.2b's own Work Packages D/F/G/H all consumed Work Package E's one
    frozen design rather than re-sampling."""
    eco_draws = ecological_lhs_draws(n_points, seed)
    ratios = []
    for draw in eco_draws:
        eco = dict(draw)
        eco.pop("shock_interval_steps", None)
        eco.pop("shock_magnitude", None)
        cfg = SimulationConfig.level12b_frozen_reference(
            population_size=population_size, n_patches=n_patches, n_steps=n_steps, seed=1, **eco,
        )
        ratios.append(expected_pressure_ratio(cfg).ratio)

    low_cut, high_cut = compute_stratum_cut_points(ratios)
    points = []
    for point_id in range(n_points):
        stratum = feasibility_stratum(ratios[point_id], low_cut, high_cut)
        points.append({
            "point_id": point_id,
            "ecological_parameters": eco_draws[point_id],
            "expected_pressure_ratio": ratios[point_id],
            "expected_stratum": stratum,
        })

    stratum_counts: dict[str, int] = {}
    for p in points:
        stratum_counts[p["expected_stratum"]] = stratum_counts.get(p["expected_stratum"], 0) + 1

    return {
        "milestone": "level1.3_ecological_feasibility_integration",
        "n_points": n_points,
        "lhs_seed": seed,
        "population_size": population_size,
        "n_patches": n_patches,
        "n_steps": n_steps,
        "stratum_cut_points": {"low_cut": low_cut, "high_cut": high_cut},
        "stratum_counts": stratum_counts,
        "points": points,
        "stratification_basis": "ex_ante_expected_pressure_ratio_only_never_realized_outcomes",
    }
