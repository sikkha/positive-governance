"""Level 0.3, Work Package B: the independent ecological policy
representation and its local, occupancy-only decision rule."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.ecological_policy import (
    EcologicalPolicy,
    decide_ecological_action,
    mutate_ecological_policy,
    sample_ecological_policy,
)


def test_ecological_policy_rejects_out_of_range_traits():
    EcologicalPolicy(0.0, 0.0, 0.0)  # boundary values OK
    EcologicalPolicy(1.0, 1.0, 1.0)
    with pytest.raises(ValueError):
        EcologicalPolicy(-0.1, 0.5, 0.5)
    with pytest.raises(ValueError):
        EcologicalPolicy(0.5, 1.1, 0.5)
    with pytest.raises(ValueError):
        EcologicalPolicy(0.5, 0.5, -0.01)


def test_ecological_policy_is_frozen():
    policy = EcologicalPolicy(0.5, 0.5, 0.5)
    with pytest.raises(Exception):
        policy.extraction_propensity = 0.9  # type: ignore[misc]


def test_sample_ecological_policy_clips_to_valid_range():
    rng = np.random.default_rng(0)
    for _ in range(500):
        policy = sample_ecological_policy(
            extraction_mean=0.9, extraction_std=1.0,  # deliberately wide, to exercise clipping
            maintenance_mean=0.1, maintenance_std=1.0,
            scarcity_mean=0.5, scarcity_std=1.0,
            rng=rng,
        )
        assert 0.0 <= policy.extraction_propensity <= 1.0
        assert 0.0 <= policy.maintenance_propensity <= 1.0
        assert 0.0 <= policy.scarcity_sensitivity <= 1.0


def test_sample_ecological_policy_deterministic_given_seeded_rng():
    a = sample_ecological_policy(0.5, 0.1, 0.3, 0.1, 0.3, 0.1, np.random.default_rng(42))
    b = sample_ecological_policy(0.5, 0.1, 0.3, 0.1, 0.3, 0.1, np.random.default_rng(42))
    assert a == b


def test_mutate_ecological_policy_never_reads_the_original_policy():
    """Mutation is documented as a fresh redraw, mirroring social mutation
    -- so its signature must not even accept the pre-mutation policy as
    an argument, structurally guaranteeing the new policy is independent
    of the old one."""
    import inspect

    params = set(inspect.signature(mutate_ecological_policy).parameters)
    assert not any("policy" == p or "old" in p for p in params)


def test_mutate_ecological_policy_produces_valid_policy():
    rng = np.random.default_rng(0)
    policy = mutate_ecological_policy(0.5, 0.1, 0.3, 0.1, 0.3, 0.1, rng)
    assert isinstance(policy, EcologicalPolicy)
    assert 0.0 <= policy.extraction_propensity <= 1.0


# -- decide_ecological_action: the local decision equations -----------------

def test_decide_ecological_action_matches_hand_computed_case_zero_scarcity_sensitivity():
    # scarcity_sensitivity=0 -> both multipliers are exactly 1.0 regardless
    # of occupancy, so h = extraction_propensity * harvest_unit and
    # m = maintenance_propensity * maintenance_unit exactly.
    policy = EcologicalPolicy(extraction_propensity=0.4, maintenance_propensity=0.6, scarcity_sensitivity=0.0)
    h, m = decide_ecological_action(policy, local_occupancy=0.2, harvest_unit=10.0, maintenance_unit=5.0)
    assert h == pytest.approx(0.4 * 10.0)
    assert m == pytest.approx(0.6 * 5.0)
    # occupancy shouldn't matter at all when scarcity_sensitivity=0
    h2, m2 = decide_ecological_action(policy, local_occupancy=0.9, harvest_unit=10.0, maintenance_unit=5.0)
    assert h2 == pytest.approx(h)
    assert m2 == pytest.approx(m)


def test_decide_ecological_action_matches_hand_computed_case_with_scarcity():
    # occupancy=0.3 -> scarcity=0.7; scarcity_sensitivity=0.5
    # extraction_multiplier = max(0, 1 - 0.5*0.7) = 0.65
    # maintenance_multiplier = 1 + 0.5*0.7 = 1.35
    policy = EcologicalPolicy(extraction_propensity=1.0, maintenance_propensity=1.0, scarcity_sensitivity=0.5)
    h, m = decide_ecological_action(policy, local_occupancy=0.3, harvest_unit=10.0, maintenance_unit=10.0)
    assert h == pytest.approx(10.0 * 0.65)
    assert m == pytest.approx(10.0 * 1.35)


def test_decide_ecological_action_extraction_never_negative():
    # scarcity_sensitivity=1.0, occupancy=0.0 -> scarcity=1.0 ->
    # extraction_multiplier = max(0, 1-1*1) = 0.0, never negative even at
    # extreme parameter combinations.
    policy = EcologicalPolicy(extraction_propensity=1.0, maintenance_propensity=1.0, scarcity_sensitivity=1.0)
    h, m = decide_ecological_action(policy, local_occupancy=0.0, harvest_unit=10.0, maintenance_unit=10.0)
    assert h == pytest.approx(0.0)
    assert m >= 0.0


def test_decide_ecological_action_zero_propensities_yield_zero_action():
    policy = EcologicalPolicy(extraction_propensity=0.0, maintenance_propensity=0.0, scarcity_sensitivity=0.5)
    h, m = decide_ecological_action(policy, local_occupancy=0.5, harvest_unit=10.0, maintenance_unit=10.0)
    assert h == pytest.approx(0.0)
    assert m == pytest.approx(0.0)


def test_decide_ecological_action_reads_only_its_own_arguments():
    """Structural local-information check: the decision function's
    signature exposes no channel for global occupancy, cooperation rate,
    or any other cross-patch/population quantity -- only the agent's own
    policy and its own patch's occupancy."""
    import inspect

    params = list(inspect.signature(decide_ecological_action).parameters)
    assert params == ["policy", "local_occupancy", "harvest_unit", "maintenance_unit"]
