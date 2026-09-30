"""Level 0.2, Work Package I: dynamical classification discipline.

Every classification function here is tested on hand-built synthetic
metrics-row series (so the exact expected episodes are known in advance)
plus a sensitivity check that changing the threshold changes the
classification result — the milestone brief requires every threshold to
be sensitivity-tested, not just present."""

from __future__ import annotations

from abm_governance.observer.classification import (
    behavioural_convergence_episodes,
    collapse_episodes,
    depletion_flags,
    population_failure,
    recovery_episodes,
)


def _rows(occupancy, unmet_demand=None, policy_diversity=None, distressed=None, dormant=None):
    n = len(occupancy)
    unmet_demand = unmet_demand or [1.0] * n
    policy_diversity = policy_diversity or [0.0] * n
    distressed = distressed or [0] * n
    dormant = dormant or [0] * n
    return [
        {
            "step": i,
            "environment_fraction_of_capacity": occupancy[i],
            "unmet_extraction_demand": unmet_demand[i],
            "policy_diversity_bits": policy_diversity[i],
            "distressed_population": distressed[i],
            "dormant_population": dormant[i],
        }
        for i in range(n)
    ]


def test_depletion_flags_hand_computed():
    rows = _rows([0.5, 0.03, 0.02, 0.5, 0.5])
    flags = depletion_flags(rows, occupancy_threshold=0.05)
    assert flags == [False, True, True, False, False]


def test_collapse_episode_requires_min_duration_and_sustained_unmet_demand():
    occupancy = [0.5] + [0.01] * 25 + [0.5]
    rows = _rows(occupancy)
    episodes = collapse_episodes(rows, occupancy_threshold=0.05, min_duration=20)
    assert len(episodes) == 1
    assert episodes[0].duration == 25

    # Too short: no episode.
    occupancy_short = [0.5] + [0.01] * 5 + [0.5]
    rows_short = _rows(occupancy_short)
    assert collapse_episodes(rows_short, occupancy_threshold=0.05, min_duration=20) == []


def test_collapse_episode_not_triggered_without_sustained_unmet_demand():
    occupancy = [0.5] + [0.01] * 25 + [0.5]
    unmet = [1.0] + [0.0] * 25 + [1.0]  # depleted, but nobody wants anything: not "collapse"
    rows = _rows(occupancy, unmet_demand=unmet)
    assert collapse_episodes(rows, occupancy_threshold=0.05, min_duration=20) == []
    # With the unmet-demand requirement turned off, the same depletion
    # stretch does qualify.
    episodes = collapse_episodes(
        rows, occupancy_threshold=0.05, min_duration=20, require_sustained_unmet_demand=False
    )
    assert len(episodes) == 1


def test_recovery_episode_requires_prior_depletion():
    # Sustained high occupancy the whole time, never depleted first: not a
    # "recovery" by this definition (nothing to recover from).
    occupancy_never_depleted = [0.8] * 30
    rows = _rows(occupancy_never_depleted)
    assert recovery_episodes(rows, min_duration=10) == []

    # Depleted, then recovers and stays up for long enough.
    occupancy = [0.01] * 5 + [0.8] * 20
    rows2 = _rows(occupancy)
    episodes = recovery_episodes(rows2, min_duration=10)
    assert len(episodes) == 1
    assert episodes[0].duration == 20


def test_population_failure_threshold_and_sensitivity():
    rows = _rows([0.5] * 10, distressed=[0, 1, 2, 3, 5, 5, 5, 5, 5, 5], dormant=[0] * 10)
    result_low_threshold = population_failure(rows, n_agents=10, fraction_threshold=0.3)
    result_high_threshold = population_failure(rows, n_agents=10, fraction_threshold=0.9)
    assert result_low_threshold["ever_crossed"] is True
    assert result_high_threshold["ever_crossed"] is False
    assert result_low_threshold["peak_fraction"] == 0.5


def test_behavioural_convergence_episode_hand_computed():
    entropy = [1.5] * 5 + [0.05] * 25
    rows = _rows([0.5] * 30, policy_diversity=entropy)
    episodes = behavioural_convergence_episodes(rows, entropy_threshold=0.1, min_duration=20)
    assert len(episodes) == 1
    assert episodes[0].start_step == 5
    assert episodes[0].duration == 25

    # Sensitivity: a tighter entropy threshold that the data never
    # actually reaches yields no episode.
    assert behavioural_convergence_episodes(rows, entropy_threshold=0.01, min_duration=20) == []
