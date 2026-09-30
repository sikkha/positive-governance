"""Level 1.2b, Work Package B: ex ante ecological feasibility ratios
(Section 6).

Observer-only (read-only diagnostics) — never imported by ``rules/`` or
``simulation.py``. Computes three distinct ratios, each with a distinct
epistemic status per Section 6:

1. :func:`structural_feasibility_ratio` (Section 6.1) — a purely
   *structural* ratio computable from configuration alone, before any
   simulation runs: the ecology's maximum sustainable physical supply
   divided by the population's minimum *mandatory* burden. Never uses
   optimistic assumptions about endogenous institutional cooperation
   (the numerator is a physical ceiling; the denominator is the bare
   subsistence floor every agent pays regardless of institutional
   behavior).

2. :func:`expected_pressure_ratio` (Section 6.2) — an *expected*-pressure
   ratio using preregistered, neutral behavioral assumptions (the
   configured mean trait values, evaluated at a neutral mid-capacity
   occupancy) to estimate expected aggregate requested demand, not just
   the mandatory floor. Never uses realized simulation outcomes. If a
   Monte Carlo cross-check is requested, it draws from a dedicated
   observer-only RNG stream that is never the simulation's own
   ``core/rng.py`` stream registry and never affects simulation dynamics.

3. :func:`realized_balance_timeseries` (Section 6.3) — a purely
   *diagnostic* function computed from a completed run's own realized
   outcomes. Never fed back into experimental design; Section 6.3 is
   explicit that this is an outcome measurement, not a design variable.

**Naming discipline (Sections 3/21 SEM firewall):** none of these
functions compute, store, or return any governance-outcome label,
cluster assignment, or SEM-trajectory-adjacent term. ``ρ_struct``/
``ρ_expected``/``ρ_realized`` are purely physical/behavioral-expectation
quantities computed before (or independent of) any institutional-
phenotype question. They are never called a "governance score", a
"viability index", or any label resembling one — per Section 6.2's own
explicit prohibition.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

#: Section 6.1/6.2: the maximum-sustainable-yield occupancy fraction for
#: the model's logistic regeneration ``growth = r * quality * R * (1 -
#: R/K)`` is exactly ``R = K/2`` (elementary calculus on the logistic
#: growth curve — ``d(growth)/dR = r*quality*(1 - 2R/K) = 0`` at
#: ``R=K/2``), giving ``growth_max = r * quality * K / 4``. This is the
#: same "maximum sustainable yield" concept used in fisheries/renewable-
#: resource economics, applied here with no tuning toward any particular
#: institutional outcome — it is a fact about the regeneration function
#: alone.
_MSY_OCCUPANCY_FRACTION = 0.5

#: Section 6.2: a preregistered *neutral* occupancy assumption for
#: estimating expected extraction/maintenance requests under the
#: documented ``decide_ecological_action`` equations
#: (``agents/ecological_policy.py``) — deliberately the same midpoint as
#: the MSY occupancy above, so neither ratio's assumptions favor a
#: particular ecological regime (neither "abundance" nor "scarcity").
_NEUTRAL_EXPECTED_OCCUPANCY = 0.5

#: Section 6.2: patch quality is drawn once per patch from
#: ``Normal(1.0, patch_quality_std)`` clipped to non-negative
#: (``core/config.py``'s own documented default), so its expectation is
#: (to a first-order, exact-at-std=0 approximation) 1.0 regardless of
#: ``patch_quality_std`` — the distribution is symmetric around 1.0 and
#: clipping only removes a symmetric-ish lower tail for typical std
#: values. Declared as a named constant, not silently hardcoded, so this
#: approximation is visible and auditable.
_EXPECTED_PATCH_QUALITY = 1.0

#: Section 6.2: the fixed, disclosed seed root for this module's
#: dedicated observer-only Monte Carlo RNG stream. Deliberately NOT
#: derived from ``config.seed`` or any part of ``core/rng.py``'s
#: ``STREAM_REGISTRY`` -- this RNG never influences simulation dynamics
#: and its draws are not reproduced by re-running the simulation itself.
_OBSERVER_MONTE_CARLO_SEED_ROOT = 0x12B_FEA5


def _max_sustainable_regeneration(*, n_patches: int, patch_regen_rate: float, patch_capacity: float) -> float:
    """Section 6.1/6.2 shared numerator: total maximum-sustainable-yield
    regeneration summed across all patches, at expected patch quality."""
    per_patch_msy = patch_regen_rate * _EXPECTED_PATCH_QUALITY * patch_capacity / 4.0
    return n_patches * per_patch_msy


@dataclass(frozen=True)
class StructuralFeasibilityResult:
    """Section 6.1 result. ``ratio`` is ``max_sustainable_supply /
    minimum_mandatory_burden``; values > 1 mean the ecology's physical
    ceiling exceeds the population's bare survival floor, values < 1 mean
    it structurally cannot, even before any behavioral or institutional
    question is asked."""

    max_sustainable_supply: float
    minimum_mandatory_burden: float
    ratio: float


def structural_feasibility_ratio(config: Any) -> StructuralFeasibilityResult:
    """Section 6.1: ``ρ_struct = max sustainable exogenous supply /
    minimum mandatory burden``.

    - Numerator: total maximum-sustainable-yield regeneration across all
      patches (a physical ceiling on what the ecology can supply
      indefinitely without net depletion — never an optimistic
      assumption about endogenous cooperation, since it does not depend
      on any agent's behavior at all).
    - Denominator: ``population_size * subsistence_cost`` — the bare
      per-step survival cost every living agent pays regardless of
      institutional structure, extraction behavior, or cooperation.
      Deliberately excludes extraction, administrative, monitoring,
      sanctioning, coordination, and every other discretionary or
      institutionally-contingent cost: those depend on behavior and
      institutional choices this ratio must not presuppose (Section
      6.1's "never optimistic endogenous cooperation" also cuts the
      other way here — this ratio also never *pessimistically* assumes
      maximal discretionary spending; it isolates the one truly
      mandatory floor).

    Pure function of configuration; requires no simulation run and no
    RNG. Undefined (``math.nan``) when the mandatory burden is exactly
    zero (e.g. ``subsistence_cost=0`` or ``population_size=0``), per
    the same "never replace an undefined denominator with zero"
    discipline as Section 22's structural-missingness requirement.
    """
    max_sustainable_supply = _max_sustainable_regeneration(
        n_patches=config.n_patches, patch_regen_rate=config.patch_regen_rate, patch_capacity=config.patch_capacity
    )
    minimum_mandatory_burden = config.population_size * config.subsistence_cost
    ratio = max_sustainable_supply / minimum_mandatory_burden if minimum_mandatory_burden > 0.0 else math.nan
    return StructuralFeasibilityResult(
        max_sustainable_supply=max_sustainable_supply,
        minimum_mandatory_burden=minimum_mandatory_burden,
        ratio=ratio,
    )


def _expected_h_m(config: Any, *, occupancy: float) -> tuple[float, float]:
    """Closed-form expectation of one agent's per-step ``(h, m)`` under
    ``decide_ecological_action``'s documented equations
    (``agents/ecological_policy.py``), using the CONFIGURED MEAN trait
    values as point estimates for
    ``E[extraction_propensity]``/``E[maintenance_propensity]``/
    ``E[scarcity_sensitivity]``. This is an approximation: the true traits
    are drawn from ``Normal(mean, std)`` clipped to ``[0, 1]``, so the
    clipped distribution's true mean can differ slightly from the
    configured ``mean`` parameter when ``std`` is large relative to the
    distance from ``mean`` to the ``[0, 1]`` boundary. See
    :func:`monte_carlo_expected_h_m` for an empirical cross-check using a
    dedicated observer-only RNG, and Section 6.2's required sensitivity
    analysis."""
    scarcity = 1.0 - occupancy
    h = config.extraction_propensity_mean * config.ecological_harvest_unit * max(
        0.0, 1.0 - config.scarcity_sensitivity_mean * scarcity
    )
    m = config.maintenance_propensity_mean * config.ecological_maintenance_unit * (
        1.0 + config.scarcity_sensitivity_mean * scarcity
    )
    return h, m


def monte_carlo_expected_h_m(
    config: Any, *, occupancy: float = _NEUTRAL_EXPECTED_OCCUPANCY, n_samples: int = 2000, rng_seed: int | None = None
) -> dict[str, float]:
    """Section 6.2's dedicated observer-only Monte Carlo cross-check for
    :func:`_expected_h_m`'s closed-form approximation. Draws
    ``n_samples`` independent ``(extraction_propensity,
    maintenance_propensity, scarcity_sensitivity)`` triples from exactly
    the same clipped-Normal distributions
    ``sample_ecological_policy``/``decide_ecological_action`` use, via a
    RNG stream that is dedicated to this observer function and is never
    part of ``core/rng.py``'s ``STREAM_REGISTRY`` and never reused by, or
    reproduced from, the simulation itself.

    Returns a dict with keys ``h_mean``, ``h_std``, ``m_mean``, ``m_std``,
    ``n_samples`` — for comparison against the closed-form
    :func:`_expected_h_m` values as part of Section 6.2's required
    sensitivity analysis (see ``level1.2b_feasibility_method.md``)."""
    seed = rng_seed if rng_seed is not None else _OBSERVER_MONTE_CARLO_SEED_ROOT
    rng = np.random.default_rng(seed)
    extraction_propensity = np.clip(rng.normal(config.extraction_propensity_mean, config.extraction_propensity_std, n_samples), 0.0, 1.0)
    maintenance_propensity = np.clip(rng.normal(config.maintenance_propensity_mean, config.maintenance_propensity_std, n_samples), 0.0, 1.0)
    scarcity_sensitivity = np.clip(rng.normal(config.scarcity_sensitivity_mean, config.scarcity_sensitivity_std, n_samples), 0.0, 1.0)
    scarcity = 1.0 - occupancy
    h_samples = extraction_propensity * config.ecological_harvest_unit * np.maximum(0.0, 1.0 - scarcity_sensitivity * scarcity)
    m_samples = maintenance_propensity * config.ecological_maintenance_unit * (1.0 + scarcity_sensitivity * scarcity)
    return {
        "h_mean": float(np.mean(h_samples)),
        "h_std": float(np.std(h_samples)),
        "m_mean": float(np.mean(m_samples)),
        "m_std": float(np.std(m_samples)),
        "n_samples": n_samples,
    }


@dataclass(frozen=True)
class ExpectedPressureResult:
    """Section 6.2 result. ``ratio`` is ``expected_sustainable_supply /
    expected_aggregate_requested_demand``. ``supply_including_maintenance``
    and ``ratio_including_maintenance`` are the required sensitivity
    variant that additionally credits expected agent-driven maintenance
    investment as supply (Section 6.2's own "sensitivity analysis
    required")."""

    expected_sustainable_supply: float
    expected_aggregate_requested_demand: float
    expected_extraction_per_agent: float
    ratio: float
    supply_including_maintenance: float
    ratio_including_maintenance: float
    monte_carlo: dict[str, float] | None = None


def expected_pressure_ratio(
    config: Any, *, monte_carlo_cross_check: bool = False, monte_carlo_samples: int = 2000, monte_carlo_seed: int | None = None
) -> ExpectedPressureResult:
    """Section 6.2: ``ρ_expected = expected sustainable supply / expected
    aggregate requested demand``, using preregistered neutral
    expectations (never realized simulation outcomes, never any
    governance/cluster/SEM label).

    - Numerator (primary): identical to
      :func:`structural_feasibility_ratio`'s numerator — the physical MSY
      ceiling. A sensitivity variant additionally adds expected
      maintenance investment's effective contribution (bounded below by
      0, not capacity-clipped in expectation — a documented idealization,
      since capacity-clipping is state-dependent and cannot be resolved
      in closed form without a realized trajectory).
    - Denominator: ``population_size * (subsistence_cost +
      E[h])`` where ``E[h]`` is the expected per-agent extraction
      request at the neutral occupancy assumption (Section 6.2's own
      preregistered midpoint, matching the MSY numerator's occupancy).
      Deliberately excludes institutionally-contingent costs
      (administrative spending, monitoring, sanctioning, coordination):
      those depend on whether/how institutions form, which is exactly
      the question Level 1.2b's discovery pipeline must not presuppose
      an answer to when stratifying its own design.

    Set ``monte_carlo_cross_check=True`` to also compute an empirical
    estimate of ``E[h]``/``E[m]`` via :func:`monte_carlo_expected_h_m`
    (dedicated observer-only RNG) for comparison against the closed-form
    value, per Section 6.2's required sensitivity analysis.
    """
    expected_sustainable_supply = _max_sustainable_regeneration(
        n_patches=config.n_patches, patch_regen_rate=config.patch_regen_rate, patch_capacity=config.patch_capacity
    )
    expected_h, expected_m = _expected_h_m(config, occupancy=_NEUTRAL_EXPECTED_OCCUPANCY)
    expected_aggregate_requested_demand = config.population_size * (config.subsistence_cost + expected_h)
    ratio = (
        expected_sustainable_supply / expected_aggregate_requested_demand
        if expected_aggregate_requested_demand > 0.0
        else math.nan
    )

    expected_maintenance_effective = config.maintenance_efficiency * config.population_size * expected_m
    supply_including_maintenance = expected_sustainable_supply + expected_maintenance_effective
    ratio_including_maintenance = (
        supply_including_maintenance / expected_aggregate_requested_demand
        if expected_aggregate_requested_demand > 0.0
        else math.nan
    )

    monte_carlo = None
    if monte_carlo_cross_check:
        monte_carlo = monte_carlo_expected_h_m(
            config, occupancy=_NEUTRAL_EXPECTED_OCCUPANCY, n_samples=monte_carlo_samples, rng_seed=monte_carlo_seed
        )

    return ExpectedPressureResult(
        expected_sustainable_supply=expected_sustainable_supply,
        expected_aggregate_requested_demand=expected_aggregate_requested_demand,
        expected_extraction_per_agent=expected_h,
        ratio=ratio,
        supply_including_maintenance=supply_including_maintenance,
        ratio_including_maintenance=ratio_including_maintenance,
        monte_carlo=monte_carlo,
    )


# ---------------------------------------------------------------------------
# Section 6.3: realized balance diagnostics (outcome only, never a design
# variable).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RealizedBalanceStep:
    step: int
    realized_supply: float
    realized_requested_demand: float
    realized_fulfilled_extraction: float
    ratio: float | None  # None when requested_demand == 0 (structural missingness, never coerced to 0)


@dataclass
class RealizedBalanceSummary:
    """Section 6.3's required diagnostics, computed from a completed
    run's own event log plus the per-step regeneration record collected
    by :func:`run_with_realized_balance_tracking` (never fed back into
    experimental design)."""

    per_step: list[RealizedBalanceStep] = field(default_factory=list)
    fraction_of_steps_below_one: float = math.nan
    longest_deficit_episode_steps: int = 0
    cumulative_unmet_extraction_demand: float = 0.0
    n_deficit_episodes: int = 0
    mean_ratio_post_burn_in: float = math.nan
    patch_heterogeneity_final_cv: float = math.nan  # coefficient of variation of per-patch resources, final step


def _events_by_step(events: list, step_attr: str = "step") -> dict[int, list]:
    by_step: dict[int, list] = {}
    for e in events:
        by_step.setdefault(getattr(e, step_attr), []).append(e)
    return by_step


def run_with_realized_balance_tracking(config: Any) -> tuple[Any, RealizedBalanceSummary]:
    """Run a fresh ``patches``-topology :class:`Simulation` while
    recording each step's realized physical regeneration -- the one
    quantity ``ResourcePatch.regenerate()`` computes but discards its
    return value for (only the whole-run cumulative counter is kept),
    per ``environment/patches.py``.

    This function does NOT modify ``Simulation``/``ResourcePatch`` at
    all: it wraps each patch's already-public, deterministic (no RNG),
    side-effect-free-to-observe ``regenerate`` bound method for the
    duration of one run, purely to capture its return value into a
    per-step accumulator alongside the step counter the wrapped
    ``Simulation._run_one_step`` is executing. No simulation behavior
    changes — the wrapped methods still do exactly what they did before,
    every value they compute and every mutation they make is identical;
    only an external observation is added. Diagnostic use only, per
    Section 6.3 — the returned :class:`RealizedBalanceSummary` is never
    consumed by any experimental-design code.
    """
    # Imported here, not at module level, to keep this observer module's
    # own import graph acyclic with ``simulation.py`` (which imports
    # observer.metrics, not this module) -- avoids any risk of this
    # becoming a circular-import surface as the module set grows.
    from abm_governance.simulation import Simulation

    sim = Simulation(config)
    if sim.patch_system is None:
        raise ValueError(
            "run_with_realized_balance_tracking requires ecology_topology='patches' "
            "(Level 1.2b's exclusive scope, per Work Package A's own module docstring)"
        )

    per_step_regen: dict[int, float] = {}
    current_step: list[int] = [-1]

    orig_run_one_step = sim._run_one_step

    def wrapped_run_one_step(step: int):
        current_step[0] = step
        return orig_run_one_step(step)

    sim._run_one_step = wrapped_run_one_step

    for patch in sim.patch_system.patches.values():
        orig_regen = patch.regenerate

        def wrapped_regen(orig=orig_regen):
            added = orig()
            per_step_regen[current_step[0]] = per_step_regen.get(current_step[0], 0.0) + added
            return added

        patch.regenerate = wrapped_regen

    result = sim.run()

    eco_by_step = _events_by_step(result.event_log.ecological_actions)
    subsistence_by_step = _events_by_step(result.event_log.subsistence)

    per_step: list[RealizedBalanceStep] = []
    for step in sorted(per_step_regen.keys()):
        eco_events = eco_by_step.get(step, [])
        subsistence_events = subsistence_by_step.get(step, [])
        requested = sum(e.requested_extraction for e in eco_events) + sum(e.total_cost for e in subsistence_events)
        fulfilled = sum(e.actual_extraction for e in eco_events)
        supply = per_step_regen[step]
        ratio = (supply / requested) if requested > 0.0 else None
        per_step.append(
            RealizedBalanceStep(
                step=step, realized_supply=supply, realized_requested_demand=requested,
                realized_fulfilled_extraction=fulfilled, ratio=ratio,
            )
        )

    summary = _summarize_realized_balance(per_step, sim.patch_system)
    return result, summary


def _summarize_realized_balance(per_step: list[RealizedBalanceStep], patch_system: Any) -> RealizedBalanceSummary:
    defined_ratios = [(s.step, s.ratio) for s in per_step if s.ratio is not None]
    n_defined = len(defined_ratios)

    fraction_below_one = (
        sum(1 for _, r in defined_ratios if r < 1.0) / n_defined if n_defined > 0 else math.nan
    )

    longest_episode = 0
    current_episode = 0
    n_episodes = 0
    in_episode = False
    for _, r in defined_ratios:
        if r < 1.0:
            current_episode += 1
            longest_episode = max(longest_episode, current_episode)
            if not in_episode:
                n_episodes += 1
                in_episode = True
        else:
            current_episode = 0
            in_episode = False

    cumulative_unmet = sum(
        max(0.0, s.realized_requested_demand - s.realized_fulfilled_extraction) for s in per_step
    )

    # Post-burn-in mean: preregistered primary window (Section 12) is the
    # second half of the run — a documented, simple default; Work
    # Package G (task #65) formalizes preregistered burn-in windows for
    # the main discovery pipeline. This summary uses the same default so
    # early results are comparable to the eventual preregistered window.
    if n_defined > 0:
        halfway_index = n_defined // 2
        post_burn_in_ratios = [r for _, r in defined_ratios[halfway_index:]]
        mean_ratio_post_burn_in = float(np.mean(post_burn_in_ratios)) if post_burn_in_ratios else math.nan
    else:
        mean_ratio_post_burn_in = math.nan

    final_resources = [p.resources for p in patch_system.patches.values()]
    if len(final_resources) > 1 and np.mean(final_resources) > 0:
        cv = float(np.std(final_resources) / np.mean(final_resources))
    else:
        cv = math.nan

    return RealizedBalanceSummary(
        per_step=per_step,
        fraction_of_steps_below_one=fraction_below_one,
        longest_deficit_episode_steps=longest_episode,
        cumulative_unmet_extraction_demand=cumulative_unmet,
        n_deficit_episodes=n_episodes,
        mean_ratio_post_burn_in=mean_ratio_post_burn_in,
        patch_heterogeneity_final_cv=cv,
    )
