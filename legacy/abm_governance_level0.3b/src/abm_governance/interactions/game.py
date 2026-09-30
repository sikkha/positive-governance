"""Elementary interaction grammar: an iterated prisoner's-dilemma payoff
matrix plus an optional costly-punishment stage.

This module is pure game theory: functions of joint *actions* (and, for
punishment, of resources/costs), never of any agent "identity" or
macro-level label. It defines what happens as the consequence of an
elementary interaction — it does not decide what agents should do (that is
the policy's job, see ``agents/policy.py``) and it has no notion of what
kind of political system, if any, the population resembles.
"""

from __future__ import annotations

from dataclasses import dataclass

COOPERATE = 1
DEFECT = 0


@dataclass(frozen=True)
class PayoffMatrix:
    """Standard 2x2 prisoner's-dilemma payoffs.

    T (temptation) > R (reward) > P (punishment) >= S (sucker); validated by
    :class:`abm_governance.core.config.SimulationConfig`, not here, so this
    class can also be used directly in unit tests with arbitrary payoffs.
    """

    temptation: float
    reward: float
    punishment: float
    sucker: float

    def payoff(self, action_a: int, action_b: int) -> tuple[float, float]:
        """Return ``(payoff_a, payoff_b)`` for one bilateral encounter."""
        if action_a == COOPERATE and action_b == COOPERATE:
            return self.reward, self.reward
        if action_a == COOPERATE and action_b == DEFECT:
            return self.sucker, self.temptation
        if action_a == DEFECT and action_b == COOPERATE:
            return self.temptation, self.sucker
        if action_a == DEFECT and action_b == DEFECT:
            return self.punishment, self.punishment
        raise ValueError(f"actions must be 0/1, got {action_a!r}, {action_b!r}")


def apply_punishment(
    punisher_resources: float,
    target_resources: float,
    cost: float,
    penalty: float,
) -> tuple[float, float]:
    """Apply one costly-punishment act.

    The punisher pays ``cost`` out of their own resources; the target loses
    ``penalty``. Neither side's resources are clipped here — resource floors
    (e.g. exit/death at Level 0 there is no death, only exit) are a
    simulation-level policy, not a game-grammar concern.
    """
    if cost < 0 or penalty < 0:
        raise ValueError("cost and penalty must be >= 0")
    return punisher_resources - cost, target_resources - penalty
