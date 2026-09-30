"""A shared, bounded environmental resource pool (Level 0.1, Work Package A).

This is a deliberately minimal precursor to the full Level 5
agent-environment feedback system described in
``dev_mem/project_vision.md`` §9 — it gives the generative layer a finite
resource *substrate* so that agent resource growth has an environmental
limit, without yet introducing threat, volatility, destruction/recovery, or
population dynamics (those remain reserved for Level 5).

Chosen formulation
-------------------
The milestone brief suggests a general update of the form
``R_{t+1} = R_t + g(R_t, K) - H_t - D_t + X_t``. This module implements a
minimal, transparent special case of it, chosen because it maps cleanly
onto the existing per-interaction architecture (interactions already
happen one edge at a time within a step; there is no natural point to
compute a single aggregate ``H_t`` in advance):

    1. Extraction happens *incrementally*, one interaction at a time, as
       positive game payoffs are earned during the step (see
       ``simulation.py``). Each extraction is capped by whatever is left in
       the pool: ``extracted = min(payoff, R)``, ``R -= extracted``. This
       is exactly ``H_t`` accumulated over the step, just computed
       online rather than as one batch subtraction.
    2. Once per step, *after* that step's extraction, the pool regenerates
       logistically from its post-extraction level ``R'``:
       ``R_{t+1} = clip(R' + r * R' * (1 - R'/K), 0, K)``.

There is no separate decay term ``D_t`` on the pool itself in this minimal
model — the only sink modeled at Level 0.1 is agent subsistence, and that
is deliberately *not* recycled back into the pool (documented as a
simplification in ``core/config.py`` and ``dev_mem/project_vision.md``;
material "lost" to subsistence leaves the modeled economy rather than
returning to the environment). There is also no externality term ``X_t``
at this level — nothing yet writes to the pool except its own logistic
regeneration and agent extraction. Both are natural Level 0.2+/Level 5
extension points, not implemented here because nothing in Level 0.1
requires them.

Scientific interpretation: the pool represents a finite common resource
that all of every agent's *productive* (payoff-generating) activity draws
from — a "commons" in the classic sense, without yet modeling group
membership or coordinated harvesting rules (those arrive at Level 2). Its
carrying capacity bounds how much aggregate positive payoff the whole
population can realize per step in steady state (at most
``r * K / 4``, the logistic map's maximum sustainable throughput, achieved
at ``R = K/2``); this is what gives agent resource growth an ecological
limit instead of growing purely as a function of elapsed time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EnvironmentResourcePool:
    capacity: float
    regen_rate: float
    resources: float

    #: Running totals, purely for ledger verification / diagnostics — never
    #: read by any decision-making code.
    total_extracted: float = 0.0
    total_regenerated: float = 0.0

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("capacity must be > 0")
        if not (0.0 <= self.regen_rate <= 2.0):
            raise ValueError("regen_rate must be in [0, 2]")
        if not (0.0 <= self.resources <= self.capacity):
            raise ValueError("resources must be in [0, capacity]")

    def extract(self, amount: float) -> float:
        """Withdraw up to ``amount`` from the pool; returns the amount
        actually withdrawn, which is ``amount`` unless the pool has less
        than that available, in which case it is capped at ``resources``
        (or 0 for a non-positive request). Never raises for scarcity — a
        depleted pool simply yields less, which is the whole point."""
        actual = min(max(amount, 0.0), self.resources)
        self.resources -= actual
        self.total_extracted += actual
        return actual

    def regenerate(self) -> float:
        """Apply one step of logistic regeneration in place. Returns the
        (possibly negative-clamped-to-zero) amount added."""
        growth = self.regen_rate * self.resources * (1.0 - self.resources / self.capacity)
        new_resources = min(self.capacity, max(0.0, self.resources + growth))
        added = new_resources - self.resources
        self.resources = new_resources
        self.total_regenerated += added
        return added

    @property
    def fraction_of_capacity(self) -> float:
        return self.resources / self.capacity if self.capacity else 0.0
