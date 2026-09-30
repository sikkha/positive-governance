"""Level 0.3, Work Package I: the seven-criterion endogenous-regulation
diagnostic module -- hand-constructed trajectories exercising each
criterion's exact definition and its documented degenerate-case
behaviour."""

from __future__ import annotations

import math

import numpy as np
import pytest

from abm_governance.observer.regulation_diagnostics import (
    feedback_dependence,
    interior_persistence,
    micro_macro_linkage,
    nonstationary_classification,
    nontriviality,
    parameter_neighborhood_robustness,
    perturbation_recovery,
)


# -- criterion 1: interior persistence -------------------------------------

def test_interior_persistence_hand_constructed_pass():
    series = [0.5] * 30  # constant, well inside (0.05, 0.95), 30 steps
    row = interior_persistence(series, min_duration_steps=20)
    assert row["longest_interior_run"] == 30
    assert row["fraction_interior"] == pytest.approx(1.0)
    assert row["criterion_met"] is True


def test_interior_persistence_hand_constructed_fail_too_short():
    series = [0.0] * 10 + [0.5] * 10 + [0.0] * 10  # only 10 consecutive interior
    row = interior_persistence(series, min_duration_steps=20)
    assert row["longest_interior_run"] == 10
    assert row["criterion_met"] is False


def test_interior_persistence_boundary_values_are_excluded():
    # exactly at the bounds (0.05, 0.95) is NOT interior (strict inequality)
    series = [0.05, 0.95] * 20
    row = interior_persistence(series, lower_bound=0.05, upper_bound=0.95, min_duration_steps=1)
    assert row["longest_interior_run"] == 0
    assert row["criterion_met"] is False


def test_interior_persistence_degenerate_empty_series():
    row = interior_persistence([])
    assert row["n_steps"] == 0
    assert math.isnan(row["longest_interior_run"])
    assert row["criterion_met"] is False


# -- criteria 2/5: feedback dependence / nontriviality ---------------------

def test_feedback_dependence_hand_constructed_all_weaker():
    candidate = 0.8
    counterfactuals = {"no_effect": 0.1, "frozen": 0.2, "randomized": 0.3, "shuffled": 0.15}
    row = feedback_dependence(candidate, counterfactuals, weaker_relative_reduction=0.2)
    assert row["n_counterfactuals"] == 4
    assert row["n_weaker"] == 4
    assert row["fraction_weaker"] == pytest.approx(1.0)
    assert row["criterion_met"] is True


def test_feedback_dependence_hand_constructed_none_weaker():
    candidate = 0.5
    counterfactuals = {"no_effect": 0.55, "frozen": 0.6}  # both HIGHER, not weaker
    row = feedback_dependence(candidate, counterfactuals)
    assert row["n_weaker"] == 0
    assert row["criterion_met"] is False


def test_feedback_dependence_degenerate_empty_counterfactuals():
    row = feedback_dependence(0.5, {})
    assert row["n_counterfactuals"] == 0
    assert row["criterion_met"] is False
    assert math.isnan(row["fraction_weaker"])


def test_feedback_dependence_degenerate_zero_candidate_stat():
    row = feedback_dependence(0.0, {"no_effect": 0.0})
    assert math.isnan(row["per_condition_relative_reduction"]["no_effect"])
    assert row["criterion_met"] is False


def test_nontriviality_hand_constructed():
    row = nontriviality(candidate_stat=0.9, no_effect_stat=0.1)
    assert row["relative_reduction"] == pytest.approx((0.9 - 0.1) / 0.9)
    assert row["criterion_met"] is True

    row_same = nontriviality(candidate_stat=0.9, no_effect_stat=0.85)
    assert row_same["criterion_met"] is False


# -- criterion 3: perturbation recovery ------------------------------------

def test_perturbation_recovery_hand_constructed_recovers():
    pre_shock = [0.5, 0.52, 0.48, 0.5]  # band [0.48, 0.52]
    post_shock = [0.1, 0.2, 0.35, 0.49, 0.5]  # recovers at index 3 (0.49 in widened band)
    row = perturbation_recovery(pre_shock, post_shock, tolerance_fraction=0.1)
    assert row["recovered"] is True
    assert row["recovery_time_steps"] == 3
    assert row["time_to_minimum"] == 0
    assert row["immediate_shock_magnitude"] == pytest.approx(0.5 - 0.1)


def test_perturbation_recovery_hand_constructed_never_recovers():
    pre_shock = [0.5, 0.5]
    post_shock = [0.1, 0.05, 0.02, 0.01]  # monotonically collapsing, never returns
    row = perturbation_recovery(pre_shock, post_shock)
    assert row["recovered"] is False
    assert math.isnan(row["recovery_time_steps"])


def test_perturbation_recovery_degenerate_empty_series():
    row = perturbation_recovery([], [0.1, 0.2])
    assert row["recovered"] is False
    assert math.isnan(row["immediate_shock_magnitude"])


def test_perturbation_recovery_degenerate_zero_width_band():
    # pre-shock perfectly constant -> zero band width -> recovery test is
    # vacuous and must not be silently treated as "recovered".
    row = perturbation_recovery([0.5, 0.5, 0.5], [0.1, 0.2, 0.5])
    assert row["recovered"] is False


# -- criterion 4: parameter-neighborhood robustness ------------------------

def test_parameter_neighborhood_robustness_hand_constructed():
    flags = [True, True, True, False, False]  # 3/5 = 0.6
    row = parameter_neighborhood_robustness(flags, min_fraction=0.5)
    assert row["n_passing"] == 3
    assert row["fraction_passing"] == pytest.approx(0.6)
    assert row["criterion_met"] is True

    row_fail = parameter_neighborhood_robustness(flags, min_fraction=0.8)
    assert row_fail["criterion_met"] is False


def test_parameter_neighborhood_robustness_degenerate_empty():
    row = parameter_neighborhood_robustness([])
    assert row["n_neighbors"] == 0
    assert math.isnan(row["fraction_passing"])
    assert row["criterion_met"] is False


# -- criterion 6: micro-macro linkage ---------------------------------------

def test_micro_macro_linkage_hand_constructed_perfect_correlation():
    traits = [0.1, 0.2, 0.3, 0.4, 0.5]
    outcomes = [0.2, 0.4, 0.6, 0.8, 1.0]  # exactly 2x -> r=1.0
    row = micro_macro_linkage(traits, outcomes)
    assert row["correlation"] == pytest.approx(1.0)
    assert row["criterion_met"] is True


def test_micro_macro_linkage_degenerate_below_min_n():
    row = micro_macro_linkage([0.1, 0.2], [0.3, 0.4], min_n=5)
    assert math.isnan(row["correlation"])
    assert row["criterion_met"] is False


def test_micro_macro_linkage_degenerate_zero_variance():
    row = micro_macro_linkage([0.5, 0.5, 0.5, 0.5, 0.5], [0.1, 0.2, 0.3, 0.4, 0.5])
    assert math.isnan(row["correlation"])
    assert row["criterion_met"] is False


# -- criterion 7: nonstationary alternatives --------------------------------

def test_nonstationary_classification_depleted():
    series = [0.01] * 50
    row = nonstationary_classification(series)
    assert row["label"] == "depleted"


def test_nonstationary_classification_abundant():
    series = [0.99] * 50
    row = nonstationary_classification(series)
    assert row["label"] == "abundant"


def test_nonstationary_classification_interior_persistent():
    series = [0.5] * 50
    row = nonstationary_classification(series)
    assert row["label"] == "interior-persistent"


def test_nonstationary_classification_oscillatory():
    # Sine wave: many zero crossings around its own mean.
    t = np.linspace(0, 20 * np.pi, 200)
    series = 0.5 + 0.3 * np.sin(t)
    row = nonstationary_classification(series)
    assert row["label"] == "oscillatory"
    assert row["zero_crossings_per_100_steps"] > 4.0


def test_nonstationary_classification_intermittent():
    rng = np.random.default_rng(0)
    quiet = np.full(20, 0.5)
    burst = 0.5 + rng.normal(0, 0.3, size=20)
    quiet2 = np.full(20, 0.5)
    burst2 = 0.5 + rng.normal(0, 0.3, size=20)
    series = np.concatenate([quiet, burst, quiet2, burst2])
    row = nonstationary_classification(series, window_steps=20)
    assert row["label"] in ("intermittent", "oscillatory")  # bursty, not smoothly periodic


def test_nonstationary_classification_spatially_polarized():
    n_steps = 50
    # Two patches: start identical, diverge sharply by the end.
    patch_a = np.linspace(0.5, 0.9, n_steps)
    patch_b = np.linspace(0.5, 0.1, n_steps)
    series = (patch_a + patch_b) / 2.0  # aggregate mean stays interior/flat
    cross_patch = np.vstack([patch_a, patch_b])
    row = nonstationary_classification(series, cross_patch_series=cross_patch)
    assert row["label"] == "spatially-polarized"
    assert row["spatially_polarized"] is True


def test_nonstationary_classification_degenerate_empty_series():
    row = nonstationary_classification([])
    assert row["label"] == "unclassified"
    assert row["n_steps"] == 0
    assert math.isnan(row["mean_occupancy"])


_ALLOWED_LABELS = {
    "depleted", "abundant", "interior-persistent", "oscillatory", "intermittent",
    "spatially-polarized", "recovering", "non-recovering", "unclassified",
}


def test_nonstationary_classification_never_uses_the_word_attractor():
    """Structural guard: the module's own source text must never contain
    'attractor' -- a term implying a proven, provably-stable fixed point,
    which this deliberately conservative module never claims (see the
    module docstring's rationale) -- and every label this function can
    actually emit must be drawn from the milestone's cautious label set."""
    import inspect

    from abm_governance.observer import regulation_diagnostics

    source = inspect.getsource(regulation_diagnostics)
    assert "attractor" not in source.lower()

    rng = np.random.default_rng(0)
    for _ in range(20):
        series = rng.uniform(0.0, 1.0, size=int(rng.integers(5, 100)))
        label = nonstationary_classification(series)["label"]
        assert label in _ALLOWED_LABELS
