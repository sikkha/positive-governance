"""Independent ecological policy representation (Level 0.3, Work Package B).

Level 0-0.2 agents have exactly one behavioral dimension: a discrete
social ``policy`` (cooperate/defect strategy). Level 0.3 adds a second,
logically independent, continuous behavioral dimension governing how an
agent treats its local resource patch — deliberately *not* derived from,
coupled to, or defaulting toward the social policy (see the milestone's
central modeling principle: "Do not equate social cooperation with
ecological maintenance").

Minimal representation chosen: three bounded continuous traits per agent,
each in ``[0, 1]``:

* ``extraction_propensity`` — how much of a fixed "harvest attempt unit"
  this agent requests per ecological decision opportunity, before any
  scarcity adjustment.
* ``maintenance_propensity`` — how much of a fixed "maintenance unit"
  this agent invests per ecological decision opportunity.
* ``scarcity_sensitivity`` — how strongly this agent's *actual* request
  responds to locally-observed patch scarcity: extraction is curtailed
  and maintenance is boosted as local occupancy falls, in proportion to
  this trait. ``0.0`` means "insensitive" — a rigid strategy that
  requests/invests the same amount regardless of local conditions (which
  can itself be a legitimate persistent strategy, e.g. a rigid
  overextractor or a rigid conservationist); ``1.0`` means "fully
  responsive."

This is a deliberate minimal design, not a claim that it is the only
defensible one — see ``dev_mem/status_update.md``'s Level-0.3 entry for
the alternatives considered. The three traits are independently
observable, independently evolvable (``imitation``/``mutation`` below,
used by ``agents/adaptation.py``), and never read any global or
population-wide quantity — :func:`decide_ecological_action` takes only
this agent's own trait values and *this agent's own local patch's*
observed occupancy, per the milestone's local-information constraint.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_TRAIT_NAMES = ("extraction_propensity", "maintenance_propensity", "scarcity_sensitivity")


@dataclass(frozen=True)
class EcologicalPolicy:
    extraction_propensity: float
    maintenance_propensity: float
    scarcity_sensitivity: float

    def __post_init__(self) -> None:
        for name in _TRAIT_NAMES:
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"EcologicalPolicy.{name} must be in [0, 1], got {value}")


def sample_ecological_policy(
    extraction_mean: float,
    extraction_std: float,
    maintenance_mean: float,
    maintenance_std: float,
    scarcity_mean: float,
    scarcity_std: float,
    rng: np.random.Generator,
) -> EcologicalPolicy:
    """Draw a fresh, independent ecological policy from the configured
    trait distributions, each clipped to ``[0, 1]``. Used both for
    initial-population assignment and for every "mutation" (see
    :func:`mutate_ecological_policy`) and every fresh i.i.d. per-step draw
    (the Work-Package-F "randomized ecological policy" counterfactual)."""
    return EcologicalPolicy(
        extraction_propensity=float(np.clip(rng.normal(extraction_mean, extraction_std), 0.0, 1.0)),
        maintenance_propensity=float(np.clip(rng.normal(maintenance_mean, maintenance_std), 0.0, 1.0)),
        scarcity_sensitivity=float(np.clip(rng.normal(scarcity_mean, scarcity_std), 0.0, 1.0)),
    )


def decide_ecological_action(
    policy: EcologicalPolicy,
    local_occupancy: float,
    harvest_unit: float,
    maintenance_unit: float,
) -> tuple[float, float]:
    """Return ``(h, m)`` — this step's requested extraction and
    maintenance investment, both ``>= 0``.

    ``local_occupancy`` must be this agent's *own patch's* fraction-of-
    capacity, observed as of the start of this decision (never a
    population-wide or cross-patch quantity — see module docstring).

    Equations (documented, not tuned toward any particular outcome)::

        scarcity = 1 - local_occupancy   # 0 = patch full, 1 = patch empty
        h = extraction_propensity * harvest_unit * max(0, 1 - scarcity_sensitivity * scarcity)
        m = maintenance_propensity * maintenance_unit * (1 + scarcity_sensitivity * scarcity)

    A ``scarcity_sensitivity=0`` agent's ``h``/``m`` do not depend on
    ``local_occupancy`` at all (a rigid strategy). A fully sensitive
    agent (``scarcity_sensitivity=1``) requests zero extraction once its
    own patch is fully empty (``local_occupancy=0`` => ``scarcity=1`` =>
    the extraction multiplier hits 0) and doubles its maintenance
    investment at that same extreme.
    """
    local_occupancy = float(np.clip(local_occupancy, 0.0, 1.0))
    scarcity = 1.0 - local_occupancy
    extraction_multiplier = max(0.0, 1.0 - policy.scarcity_sensitivity * scarcity)
    maintenance_multiplier = 1.0 + policy.scarcity_sensitivity * scarcity
    h = policy.extraction_propensity * harvest_unit * extraction_multiplier
    m = policy.maintenance_propensity * maintenance_unit * maintenance_multiplier
    return max(0.0, h), max(0.0, m)


def mutate_ecological_policy(
    extraction_mean: float,
    extraction_std: float,
    maintenance_mean: float,
    maintenance_std: float,
    scarcity_mean: float,
    scarcity_std: float,
    rng: np.random.Generator,
) -> EcologicalPolicy:
    """A mutation is a fresh, independent redraw from the same
    configured distribution the initial population uses — mirroring how
    ``agents/adaptation.py::mutation_round`` treats social-policy
    mutation as a fresh uniform redraw among named strategies, rather
    than a small perturbation of the current strategy. This keeps the
    two mutation semantics consistent (both are "low-rate random
    experimentation," not "local search") and keeps this module's public
    surface small (:func:`sample_ecological_policy` and this function are
    literally the same computation; kept as two names for call-site
    clarity in ``agents/adaptation.py``)."""
    return sample_ecological_policy(
        extraction_mean, extraction_std, maintenance_mean, maintenance_std, scarcity_mean, scarcity_std, rng
    )
