"""Imperfect observation.

Each agent's read of a partner's true action is correct only with
probability equal to that *observing* agent's own ``observation_accuracy``
(a heterogeneous, per-agent trait — see ``agents/agent.py``). This is the
sole source of noise between "what happened" (the ground-truth action
recorded in the event log) and "what an agent believes happened" (what
gets written into that agent's memory and reputation estimate).
"""

from __future__ import annotations

import numpy as np

from abm_governance.interactions.game import COOPERATE, DEFECT


def observe_action(true_action: int, observation_accuracy: float, rng: np.random.Generator) -> int:
    """Return the (possibly flipped) action an observer with the given
    ``observation_accuracy`` perceives.

    ``observation_accuracy == 1.0`` always returns ``true_action`` exactly.
    ``observation_accuracy == 0.0`` always returns the flipped action.
    """
    if not (0.0 <= observation_accuracy <= 1.0):
        raise ValueError("observation_accuracy must be in [0, 1]")
    if true_action not in (COOPERATE, DEFECT):
        raise ValueError("true_action must be 0 or 1")
    if rng.random() < observation_accuracy:
        return true_action
    return DEFECT if true_action == COOPERATE else COOPERATE
