"""Work Package C: enforcement confusion matrix, built from a hand-crafted
event sequence so every rate can be checked by manual computation."""

from __future__ import annotations

import math

import pytest

from abm_governance.core.events import EventLog, InteractionEvent, PunishmentEvent
from abm_governance.interactions.game import COOPERATE, DEFECT
from abm_governance.observer.enforcement import confusion_counts, confusion_matrix_rates, confusion_matrix_summary


def _interaction(step, a, b, action_a, action_b, observed_a_by_b, observed_b_by_a, available=True):
    return InteractionEvent(
        step=step,
        agent_a=a,
        agent_b=b,
        action_a=action_a,
        action_b=action_b,
        payoff_a=0.0,
        payoff_b=0.0,
        observed_a_by_b=observed_a_by_b,
        observed_b_by_a=observed_b_by_a,
        punishment_available=available,
    )


def test_confusion_matrix_hand_computed():
    """Four interactions, hand-classified:

    1. step 0, (0,1): a=C, b=C, both perceived correctly. No punishment.
       -> two TN cells (b sees a cooperate & doesn't punish; a sees b
       cooperate & doesn't punish).
    2. step 0, (2,3): a=D, b=C. b perceives a's defection correctly and
       punishes (2 was agent_a... let's be concrete below). a perceives b's
       cooperation correctly and doesn't punish.
       -> one TP (the punished, correctly-perceived defector), one TN.
    3. step 1, (4,5): a=C, b=D. a MISPERCEIVES b as cooperating (obs error)
       so does not punish despite b's real defection -> FN. b correctly
       perceives a's cooperation and doesn't punish -> TN.
    4. step 1, (6,7): a=C, b=C, but b MISPERCEIVES a as defecting and
       punishes anyway (observation error) -> FP. a perceives b correctly
       (cooperate) and doesn't punish -> TN.
    """
    log = EventLog()

    # 1. mutual cooperation, both correctly perceived, no punishment.
    log.add(_interaction(0, 0, 1, COOPERATE, COOPERATE, COOPERATE, COOPERATE))

    # 2. agent 2 defects, agent 3 cooperates; both perceive correctly.
    #    b (=3) punishes a (=2) for the correctly-perceived defection -> TP.
    log.add(_interaction(0, 2, 3, DEFECT, COOPERATE, DEFECT, COOPERATE))
    log.add(PunishmentEvent(step=0, punisher=3, target=2, cost_to_punisher=1.0, penalty_to_target=3.0, erroneous=False))

    # 3. agent 4 cooperates, agent 5 defects; a(=4) misperceives b's(=5)
    #    defection as cooperation (observation error) -> FN, no punishment.
    log.add(_interaction(1, 4, 5, COOPERATE, DEFECT, COOPERATE, COOPERATE))

    # 4. mutual cooperation, but b(=7) misperceives a(=6) as defecting and
    #    punishes anyway -> FP (observation-error-driven punishment).
    log.add(_interaction(1, 6, 7, COOPERATE, COOPERATE, DEFECT, COOPERATE))
    log.add(PunishmentEvent(step=1, punisher=7, target=6, cost_to_punisher=1.0, penalty_to_target=3.0, erroneous=True))

    counts = confusion_counts(log)

    # Directed observations, enumerated:
    #  (1a) b=1 observes a=0: true=C, perceived=C, punished=False -> TN
    #  (1b) a=0 observes b=1: true=C, perceived=C, punished=False -> TN
    #  (2a) b=3 observes a=2: true=D, perceived=D, punished=True  -> TP
    #  (2b) a=2 observes b=3: true=C, perceived=C, punished=False -> TN
    #  (3a) b=5 observes a=4: true=C, perceived=C, punished=False -> TN
    #  (3b) a=4 observes b=5: true=D, perceived=C, punished=False -> FN
    #  (4a) b=7 observes a=6: true=C, perceived=D, punished=True  -> FP
    #  (4b) a=6 observes b=7: true=C, perceived=C, punished=False -> TN
    assert counts["tp"] == 1
    assert counts["fp"] == 1
    assert counts["tn"] == 5
    assert counts["fn"] == 1
    assert counts["n_eligible"] == 8

    # Perception-error counts: actual-cooperation observations: 1a,1b,2b,3a,4a,4b = 6
    # of which perceived-as-defection: only 4a -> 1/6
    assert counts["n_actual_cooperate"] == 6
    assert counts["n_perceived_defect_given_coop"] == 1
    # actual-defection observations: 2a, 3b = 2; perceived-as-cooperation: 3b -> 1/2
    assert counts["n_actual_defect"] == 2
    assert counts["n_perceived_coop_given_defect"] == 1

    rates = confusion_matrix_rates(counts)
    assert rates["p_punishment_given_actual_defection"] == pytest.approx(1 / 2)  # tp / (tp+fn) = 1/2
    assert rates["p_punishment_given_actual_cooperation"] == pytest.approx(1 / 6)  # fp / (fp+tn) = 1/6
    assert rates["p_perceived_defection_given_actual_cooperation"] == pytest.approx(1 / 6)
    assert rates["p_perceived_cooperation_given_actual_defection"] == pytest.approx(1 / 2)
    # perceived-defection observations: 2a (perceived D), 4a (perceived D) = 2; punished in both -> 2/2
    assert rates["p_punishment_given_perceived_defection"] == pytest.approx(1.0)
    assert rates["punishment_precision"] == pytest.approx(1 / 2)  # tp / (tp+fp) = 1/2
    assert rates["punishment_recall"] == pytest.approx(1 / 2)


def test_zero_denominator_yields_nan_not_zero():
    """No interactions at all -> every conditional probability must be
    NaN, never a silently-substituted 0.0."""
    log = EventLog()
    summary = confusion_matrix_summary(log)
    for key in (
        "p_punishment_given_actual_defection",
        "p_punishment_given_actual_cooperation",
        "p_perceived_defection_given_actual_cooperation",
        "p_perceived_cooperation_given_actual_defection",
        "p_punishment_given_perceived_defection",
        "punishment_precision",
        "punishment_recall",
    ):
        assert math.isnan(summary[key]), key
    assert summary["tp"] == 0
    assert summary["n_eligible"] == 0


def test_punishment_unavailable_interactions_excluded_from_confusion_matrix_but_not_perception_counts():
    log = EventLog()
    log.add(_interaction(0, 0, 1, DEFECT, COOPERATE, DEFECT, COOPERATE, available=False))
    counts = confusion_counts(log)
    assert counts["n_eligible"] == 0
    assert counts["tp"] == counts["fp"] == counts["tn"] == counts["fn"] == 0
    # Perception-error counts are still meaningful even when punishment is
    # structurally unavailable (they describe observation, not enforcement).
    assert counts["n_actual_cooperate"] == 1
    assert counts["n_actual_defect"] == 1


def test_only_actual_defection_observations_yields_nan_cooperation_conditional():
    log = EventLog()
    log.add(_interaction(0, 0, 1, DEFECT, DEFECT, DEFECT, DEFECT))
    counts = confusion_counts(log)
    rates = confusion_matrix_rates(counts)
    # No actual-cooperation observations exist at all in this log.
    assert counts["n_actual_cooperate"] == 0
    assert math.isnan(rates["p_punishment_given_actual_cooperation"])
    assert math.isnan(rates["p_perceived_defection_given_actual_cooperation"])


def test_step_and_end_step_windowing_is_exclusive_on_end():
    log = EventLog()
    log.add(_interaction(0, 0, 1, DEFECT, COOPERATE, DEFECT, COOPERATE))
    log.add(_interaction(5, 2, 3, DEFECT, COOPERATE, DEFECT, COOPERATE))
    counts_window = confusion_counts(log, start_step=0, end_step=5)  # step 5 excluded
    assert counts_window["n_eligible"] == 2  # one interaction = 2 directed observations
    counts_full = confusion_counts(log, start_step=0, end_step=6)
    assert counts_full["n_eligible"] == 4


def test_full_simulation_confusion_matrix_is_internally_consistent():
    from abm_governance.core.config import SimulationConfig
    from abm_governance.simulation import Simulation

    config = SimulationConfig(population_size=24, n_steps=80, seed=1)
    result = Simulation(config).run()
    summary = confusion_matrix_summary(result.event_log)
    assert summary["tp"] + summary["fp"] + summary["tn"] + summary["fn"] == summary["n_eligible"]
    # p_punishment_given_perceived_defection should be in a sane range and
    # roughly track the configured punishment_probability (0.3 default) —
    # a loose sanity bound, not a tuned expectation.
    assert 0.0 <= summary["p_punishment_given_perceived_defection"] <= 1.0
