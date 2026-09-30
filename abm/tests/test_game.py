"""Hand-computed payoff and punishment arithmetic checks."""

from __future__ import annotations

import pytest

from abm_governance.interactions.game import COOPERATE, DEFECT, PayoffMatrix, apply_punishment


@pytest.fixture
def matrix() -> PayoffMatrix:
    return PayoffMatrix(temptation=5.0, reward=3.0, punishment=1.0, sucker=0.0)


def test_mutual_cooperation_pays_reward(matrix):
    assert matrix.payoff(COOPERATE, COOPERATE) == (3.0, 3.0)


def test_mutual_defection_pays_punishment(matrix):
    assert matrix.payoff(DEFECT, DEFECT) == (1.0, 1.0)


def test_defector_gets_temptation_cooperator_gets_sucker(matrix):
    assert matrix.payoff(DEFECT, COOPERATE) == (5.0, 0.0)
    assert matrix.payoff(COOPERATE, DEFECT) == (0.0, 5.0)


def test_payoff_rejects_invalid_actions(matrix):
    with pytest.raises(ValueError):
        matrix.payoff(2, COOPERATE)


def test_apply_punishment_exact_arithmetic():
    punisher_res, target_res = apply_punishment(
        punisher_resources=10.0, target_resources=10.0, cost=1.5, penalty=4.0
    )
    assert punisher_res == pytest.approx(8.5)
    assert target_res == pytest.approx(6.0)


def test_apply_punishment_rejects_negative_cost_or_penalty():
    with pytest.raises(ValueError):
        apply_punishment(10.0, 10.0, cost=-1.0, penalty=1.0)
    with pytest.raises(ValueError):
        apply_punishment(10.0, 10.0, cost=1.0, penalty=-1.0)


def test_apply_punishment_can_drive_resources_negative_unclipped():
    # Clipping/floors are a simulation-level policy, not a game-grammar concern.
    punisher_res, target_res = apply_punishment(1.0, 1.0, cost=5.0, penalty=5.0)
    assert punisher_res == -4.0
    assert target_res == -4.0
