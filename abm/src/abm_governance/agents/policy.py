"""Interpretable, causally-inspectable behavioural policies.

Every policy here is a small, readable finite-state / conditional-rule
controller — never an opaque model. Given an agent's own memory of a
specific partner (a bounded, possibly noisy/decayed record of that
partner's past *observed* actions — see ``agents/observation.py`` and
``agents/agent.py``), a policy returns the next elementary action to take
toward that partner: :data:`abm_governance.interactions.game.COOPERATE` or
:data:`abm_governance.interactions.game.DEFECT`.

Policies never see governance-level labels, only local interaction history.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Deque, Sequence

import numpy as np

from abm_governance.interactions.game import COOPERATE, DEFECT

VALID_POLICY_NAMES = (
    "always_cooperate",
    "always_defect",
    "tit_for_tat",
    "generous_tit_for_tat",
    "grim",
    "random",
)


class Policy:
    """Base class. Subclasses implement :meth:`decide`."""

    name: str = "base"

    def decide(self, partner_history: Sequence[int], rng: np.random.Generator) -> int:
        """Return the action to take toward a partner.

        Parameters
        ----------
        partner_history:
            This agent's own (possibly noisy) memory of the partner's past
            actions, oldest first, most recent last. Empty on first
            encounter.
        rng:
            This agent's RNG stream, for policies with a stochastic
            component.
        """
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"{self.__class__.__name__}()"


class AlwaysCooperate(Policy):
    name = "always_cooperate"

    def decide(self, partner_history: Sequence[int], rng: np.random.Generator) -> int:
        return COOPERATE


class AlwaysDefect(Policy):
    name = "always_defect"

    def decide(self, partner_history: Sequence[int], rng: np.random.Generator) -> int:
        return DEFECT


class TitForTat(Policy):
    """Cooperate on the first move; thereafter mirror the partner's last
    (observed) action."""

    name = "tit_for_tat"

    def decide(self, partner_history: Sequence[int], rng: np.random.Generator) -> int:
        if not partner_history:
            return COOPERATE
        return partner_history[-1]


@dataclass
class GenerousTitForTat(Policy):
    """Like tit-for-tat, but forgives an observed defection with probability
    ``forgiveness_probability`` (independent of the agent's memory-decay
    forgiveness parameter, which governs how memory itself fades)."""

    name = "generous_tit_for_tat"
    forgiveness_probability: float = 0.1

    def decide(self, partner_history: Sequence[int], rng: np.random.Generator) -> int:
        if not partner_history:
            return COOPERATE
        last = partner_history[-1]
        if last == DEFECT and rng.random() < self.forgiveness_probability:
            return COOPERATE
        return last


class Grim(Policy):
    """Cooperate until the partner is ever observed to defect; defect
    unconditionally thereafter (a "grim trigger")."""

    name = "grim"

    def decide(self, partner_history: Sequence[int], rng: np.random.Generator) -> int:
        if DEFECT in partner_history:
            return DEFECT
        return COOPERATE


@dataclass
class RandomPolicy(Policy):
    name = "random"
    p_cooperate: float = 0.5

    def decide(self, partner_history: Sequence[int], rng: np.random.Generator) -> int:
        return COOPERATE if rng.random() < self.p_cooperate else DEFECT


_POLICY_CLASSES = {
    "always_cooperate": AlwaysCooperate,
    "always_defect": AlwaysDefect,
    "tit_for_tat": TitForTat,
    "generous_tit_for_tat": GenerousTitForTat,
    "grim": Grim,
    "random": RandomPolicy,
}


def make_policy(name: str) -> Policy:
    if name not in _POLICY_CLASSES:
        raise ValueError(f"Unknown policy {name!r}; valid: {VALID_POLICY_NAMES}")
    return _POLICY_CLASSES[name]()
