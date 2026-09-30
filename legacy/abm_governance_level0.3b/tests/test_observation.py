"""Imperfect observation correctness."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.observation import observe_action
from abm_governance.interactions.game import COOPERATE, DEFECT


def test_perfect_accuracy_always_matches_truth():
    rng = np.random.default_rng(0)
    for _ in range(200):
        assert observe_action(COOPERATE, 1.0, rng) == COOPERATE
        assert observe_action(DEFECT, 1.0, rng) == DEFECT


def test_zero_accuracy_always_flips():
    rng = np.random.default_rng(0)
    for _ in range(200):
        assert observe_action(COOPERATE, 0.0, rng) == DEFECT
        assert observe_action(DEFECT, 0.0, rng) == COOPERATE


def test_half_accuracy_statistically_matches_within_tolerance():
    rng = np.random.default_rng(42)
    n = 20_000
    observed = [observe_action(COOPERATE, 0.5, rng) for _ in range(n)]
    correct_fraction = sum(o == COOPERATE for o in observed) / n
    assert correct_fraction == pytest.approx(0.5, abs=0.02)


def test_rejects_out_of_range_accuracy():
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        observe_action(COOPERATE, 1.5, rng)
    with pytest.raises(ValueError):
        observe_action(COOPERATE, -0.1, rng)


def test_rejects_invalid_action():
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        observe_action(2, 0.9, rng)
