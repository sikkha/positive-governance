"""Generic, configurable perturbation interface (Level 0.1, Work Package G).

A perturbation is a temporary, externally-scheduled shock with no political
interpretation attached to it — it exists to test whether the Level 0.1
system recovers, partially recovers, or fails to recover from a disturbance,
which is a prerequisite for ever meaningfully discussing "collapse" or
"recovery" (see ``observer/dynamics.py`` for the diagnostics that make that
judgement, and ``dev_mem/status_update.md`` for the operational criteria
required before using those words).

Two minimal shock kinds are implemented, matching two of the examples in
the milestone brief:

* ``resource_depletion`` — an instantaneous, one-off removal of a fraction
  of the environment pool's current resources, applied once at the
  perturbation's start step. This is the closest concrete realization of a
  "D_t"-style environmental loss term (see
  ``environment/resource_pool.py``): unlike ordinary agent-linked
  extraction, a depletion shock removes resources from the pool without
  crediting any agent.
* ``observation_noise_increase`` — for the perturbation's whole duration,
  every agent's *effective* observation accuracy this step is reduced by
  ``magnitude`` (floored at 0), increasing the perceived-vs-actual action
  mismatch rate system-wide.

Only one minimal perturbation *experiment* is run at this milestone (see
``experiments/perturbation_experiment.py``), after the baseline system is
otherwise stable, per the milestone brief.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from abm_governance.core.events import PerturbationEvent
from abm_governance.environment.resource_pool import EnvironmentResourcePool


@dataclass(frozen=True)
class PerturbationSpec:
    start_step: int
    duration: int
    kind: str
    magnitude: float

    @property
    def end_step(self) -> int:
        """Exclusive: the shock is active for steps in [start_step, end_step)."""
        return self.start_step + self.duration

    def is_active(self, step: int) -> bool:
        return self.start_step <= step < self.end_step


def specs_from_config(perturbations) -> list[PerturbationSpec]:
    return [PerturbationSpec(**dict(p)) for p in perturbations]


def apply_instantaneous_effects(
    spec: PerturbationSpec,
    step: int,
    pool: EnvironmentResourcePool | None,
    rng: np.random.Generator,
) -> None:
    """Apply the one-off, start-of-window effect of a perturbation, if it
    has one. Only ``resource_depletion`` currently does; called once, on
    the exact step the perturbation begins."""
    if step != spec.start_step:
        return
    if spec.kind == "resource_depletion" and pool is not None:
        pool.extract(pool.resources * spec.magnitude)
    # "observation_noise_increase" has no instantaneous effect: it is
    # applied continuously via effective_observation_accuracy below.


def effective_observation_accuracy(base_accuracy: float, active_specs: list[PerturbationSpec]) -> float:
    """Base accuracy reduced by any currently-active
    ``observation_noise_increase`` perturbations (summed, then floored at
    0 — magnitudes are not expected to be stacked in practice, but summing
    is the simplest, most transparent rule if they are)."""
    reduction = sum(s.magnitude for s in active_specs if s.kind == "observation_noise_increase")
    return max(0.0, base_accuracy - reduction)


def effective_subsistence_cost(base_cost: float, active_specs: list[PerturbationSpec]) -> float:
    """Level 0.2, Work Package J: base per-agent subsistence charge scaled
    up by any currently-active ``subsistence_increase`` perturbations.
    ``magnitude`` is a *fractional* increase (consistent with
    ``resource_depletion``'s magnitude also being a fraction — see module
    docstring), summed across simultaneously-active specs, e.g.
    magnitude=0.5 applied alone means a 50% higher subsistence charge for
    the perturbation's duration."""
    fractional_increase = sum(s.magnitude for s in active_specs if s.kind == "subsistence_increase")
    return base_cost * (1.0 + fractional_increase)


def effective_regen_rate(base_regen_rate: float, active_specs: list[PerturbationSpec]) -> float:
    """Level 0.2, Work Package J: base logistic regeneration rate scaled
    down by any currently-active ``regeneration_reduction`` perturbations.
    ``magnitude`` is the fractional reduction (e.g. magnitude=0.8 means
    regeneration proceeds at 20% of its normal rate for the
    perturbation's duration), floored at 0 so an oversized magnitude
    cannot invert regeneration into growth."""
    fractional_reduction = sum(s.magnitude for s in active_specs if s.kind == "regeneration_reduction")
    return max(0.0, base_regen_rate * (1.0 - fractional_reduction))


def boundary_events(specs: list[PerturbationSpec], step: int, n_steps: int) -> list[PerturbationEvent]:
    """PerturbationEvents to emit at this step: a 'start' marker on the
    exact step a shock begins, an 'end' marker on the step immediately
    after it lapses (only if that step still falls within the run)."""
    events = []
    for spec in specs:
        if step == spec.start_step:
            events.append(PerturbationEvent(step=step, kind=spec.kind, magnitude=spec.magnitude, phase="start"))
        if step == spec.end_step and spec.end_step < n_steps:
            events.append(PerturbationEvent(step=step, kind=spec.kind, magnitude=spec.magnitude, phase="end"))
    return events
