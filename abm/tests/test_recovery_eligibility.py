"""Level 0.3b, Work Package J: hand-constructed validation tests for the
repaired perturbation-recovery diagnostic
(``recovery_eligibility``/``recovery_quality``/``assess_perturbation_
recovery``). Level 0.3's original ``perturbation_recovery`` is unchanged
and covered separately in ``tests/test_regulation_diagnostics.py``."""

from __future__ import annotations

import math

import numpy as np
import pytest

from abm_governance.observer.regulation_diagnostics import (
    assess_perturbation_recovery,
    recovery_eligibility,
    recovery_quality,
)

RNG = np.random.default_rng(2026)


def test_recovery_eligibility_typical_case_is_eligible():
    pre = 0.5 + RNG.normal(0, 0.01, 30)
    post = np.concatenate([np.full(5, 0.1), 0.5 + RNG.normal(0, 0.01, 60)])
    result = recovery_eligibility(pre, post)
    assert result["eligible"] is True
    assert result["ineligibility_reasons"] == []


def test_collapsed_pre_shock_baseline_is_ineligible():
    pre = np.full(30, 0.01)
    post = np.full(60, 0.01)
    result = recovery_eligibility(pre, post)
    assert result["eligible"] is False
    assert any("depletion threshold" in r for r in result["ineligibility_reasons"])


def test_non_displacing_shock_is_ineligible():
    pre = 0.5 + RNG.normal(0, 0.01, 30)
    post = 0.5 + RNG.normal(0, 0.01, 60)  # no real shock applied
    result = recovery_eligibility(pre, post)
    assert result["eligible"] is False
    assert any("displacement" in r for r in result["ineligibility_reasons"])


def test_short_post_shock_horizon_is_ineligible():
    pre = 0.5 + RNG.normal(0, 0.01, 30)
    post = np.full(5, 0.1)  # big displacement, but too short to test recovery
    result = recovery_eligibility(pre, post, min_post_shock_steps=20)
    assert result["eligible"] is False
    assert any("horizon" in r for r in result["ineligibility_reasons"])


def test_already_collapsing_control_is_ineligible():
    pre = 0.5 + RNG.normal(0, 0.01, 30)
    post = np.concatenate([np.full(5, 0.1), 0.5 + RNG.normal(0, 0.01, 60)])
    collapsing_control = np.linspace(0.05, 0.0, 60)  # trending down, terminal at/under threshold
    result = recovery_eligibility(pre, post, control_post_shock_series=collapsing_control)
    assert result["eligible"] is False
    assert any("collapse" in r for r in result["ineligibility_reasons"])


def test_control_check_is_skipped_not_assumed_passing_when_omitted():
    pre = 0.5 + RNG.normal(0, 0.01, 30)
    post = np.concatenate([np.full(5, 0.1), 0.5 + RNG.normal(0, 0.01, 60)])
    result = recovery_eligibility(pre, post, control_post_shock_series=None)
    assert result["eligible"] is True


def test_empty_series_is_ineligible_not_crashing():
    result = recovery_eligibility([], [])
    assert result["eligible"] is False
    assert math.isnan(result["pre_shock_mean"])


def test_sustained_recovery_is_detected():
    pre = 0.5 + RNG.normal(0, 0.01, 30)
    post = np.concatenate([np.full(5, 0.1), 0.5 + RNG.normal(0, 0.005, 60)])
    result = recovery_quality(pre, post, sustained_min_duration_steps=10)
    assert result["eligible"] is True
    assert result["recovered"] is True
    assert result["time_to_sustained_recovery"] >= result["time_to_first_reentry"]
    assert result["post_recovery_persistence_fraction"] > 0.8


def test_transient_reentry_is_not_counted_as_recovery():
    pre = 0.5 + RNG.normal(0, 0.01, 30)
    # A single-step re-entry immediately followed by staying depleted --
    # the instantaneous crossing must be recorded, but "recovered" must
    # be False.
    post = np.concatenate([np.full(5, 0.1), [0.5], np.full(30, 0.1)])
    result = recovery_quality(pre, post, sustained_min_duration_steps=10)
    assert result["eligible"] is True
    assert not math.isnan(result["time_to_first_reentry"])
    assert result["recovered"] is False
    assert math.isnan(result["time_to_sustained_recovery"])


def test_ineligible_run_reports_recovered_as_none_not_false():
    """An ineligible run must not be silently reported as
    'non-recovered' -- that would conflate 'we tested and it failed to
    recover' with 'this was not a meaningful test at all'."""
    pre = np.full(30, 0.01)
    post = np.full(60, 0.01)
    result = recovery_quality(pre, post)
    assert result["eligible"] is False
    assert result["recovered"] is None
    assert math.isnan(result["max_displacement"])


def test_zero_width_pre_shock_band_uses_the_documented_floor():
    """A perfectly flat pre-shock series (band_width == 0) must not
    produce a vacuous exact-equality recovery test -- the documented
    tolerance floor keeps the band meaningfully wide."""
    pre = np.full(30, 0.5)
    post = np.concatenate([np.full(5, 0.1), np.full(60, 0.5)])
    result = recovery_quality(pre, post, min_band_width_or_floor=0.02)
    assert result["eligible"] is True
    assert result["recovered"] is True


def test_assess_perturbation_recovery_combines_both_steps():
    pre = 0.5 + RNG.normal(0, 0.01, 30)
    post = np.concatenate([np.full(5, 0.1), 0.5 + RNG.normal(0, 0.005, 60)])
    result = assess_perturbation_recovery(pre, post)
    assert result["eligible"] is True
    assert isinstance(result["recovered"], bool)


def test_residual_distance_from_control_is_computed_when_control_given():
    pre = 0.5 + RNG.normal(0, 0.01, 30)
    post = np.concatenate([np.full(5, 0.1), 0.5 + RNG.normal(0, 0.005, 60)])
    control = 0.5 + RNG.normal(0, 0.005, 60)
    result = recovery_quality(pre, post, control_post_shock_series=control)
    assert not math.isnan(result["residual_distance_from_control"])
    assert result["residual_distance_from_control"] >= 0.0
