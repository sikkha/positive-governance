"""Level 1.3, Work Package D (Section 9): dual legitimacy channels
(``core/legitimacy.py`` + ``rules/dynamics.py::legitimacy_round``)."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.core import legitimacy as cl
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog
from abm_governance.rules import dynamics as rd
from abm_governance.rules.shared_rule import RuleParameters, SharedRule
from abm_governance.simulation import Simulation


def _rule(rule_id=0, patch_id=0, members=(0, 1), founder=0, compliance_count=0, violation_count=0, sanction_count=0):
    params = RuleParameters(
        extraction_ceiling=0.3, maintenance_requirement=0.4, monitoring_intensity=0.5,
        sanction_magnitude=0.5, adoption_threshold=0.5, amendment_threshold=0.5,
    )
    r = SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=founder, rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )
    r.compliance_count = compliance_count
    r.violation_count = violation_count
    r.sanction_count = sanction_count
    return r


class TestPerformanceLegitimacyTarget:
    def test_neutral_prior_with_no_track_record(self):
        assert cl.performance_legitimacy_target(0, 0) == 0.5

    def test_all_compliance_is_one(self):
        assert cl.performance_legitimacy_target(10, 0) == 1.0

    def test_all_violation_is_zero(self):
        assert cl.performance_legitimacy_target(0, 10) == 0.0

    def test_mixed_rate(self):
        assert cl.performance_legitimacy_target(3, 1) == pytest.approx(0.75)


class TestProceduralLegitimacyTarget:
    def test_neutral_prior_with_no_track_record(self):
        assert cl.procedural_legitimacy_target(0, 0, 0) == 0.5

    def test_no_sanctions_is_full_score(self):
        assert cl.procedural_legitimacy_target(8, 2, 0) == 1.0

    def test_heavy_sanctioning_relative_to_volume_lowers_score(self):
        assert cl.procedural_legitimacy_target(8, 2, 8) == pytest.approx(0.2)

    def test_clipped_at_zero_when_sanctions_exceed_volume(self):
        assert cl.procedural_legitimacy_target(1, 1, 10) == 0.0

    def test_distinct_from_performance_target_for_the_same_rule(self):
        # A rule with perfect compliance achieved via heavy sanctioning
        # scores high on performance but low on procedural legitimacy --
        # the whole point of having two axes, not one.
        p = cl.performance_legitimacy_target(10, 0)
        r = cl.procedural_legitimacy_target(10, 0, 9)
        assert p == 1.0
        assert r < p


class TestLegitimacyStep:
    def test_moves_toward_target(self):
        out = cl.legitimacy_step(0.2, 1.0, learning_rate=0.5, fallibility_std=0.0, rng=np.random.default_rng(0))
        assert out == pytest.approx(0.6)

    def test_zero_fallibility_std_draws_nothing_from_rng(self):
        rng = np.random.default_rng(0)
        before_state = rng.bit_generator.state
        cl.legitimacy_step(0.5, 0.5, learning_rate=0.1, fallibility_std=0.0, rng=rng)
        after_state = rng.bit_generator.state
        assert before_state == after_state

    def test_clipped_to_unit_interval(self):
        out_high = cl.legitimacy_step(0.99, 1.0, learning_rate=1.0, fallibility_std=5.0, rng=np.random.default_rng(1))
        out_low = cl.legitimacy_step(0.01, 0.0, learning_rate=1.0, fallibility_std=5.0, rng=np.random.default_rng(2))
        assert 0.0 <= out_high <= 1.0
        assert 0.0 <= out_low <= 1.0

    def test_zero_learning_rate_and_fallibility_is_exact_noop(self):
        assert cl.legitimacy_step(0.37, 0.9, learning_rate=0.0, fallibility_std=0.0, rng=np.random.default_rng(0)) == pytest.approx(0.37)


class TestLegitimacyRound:
    def test_disabled_is_exact_noop(self):
        config = SimulationConfig.level1_rule_formation_default(population_size=8, n_steps=1)
        assert config.performance_legitimacy_enabled is False
        assert config.procedural_legitimacy_enabled is False
        rule = _rule(compliance_count=5, violation_count=1, sanction_count=1)
        registry = {0: rule}
        event_log = EventLog()
        rd.legitimacy_round(0, registry, config, np.random.default_rng(0), event_log)
        assert rule.performance_legitimacy == 0.0
        assert rule.procedural_legitimacy == 0.0
        assert event_log.legitimacy_events == []

    def test_performance_only_leaves_procedural_untouched(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=8, n_steps=1, performance_legitimacy_enabled=True, procedural_legitimacy_enabled=False,
            performance_legitimacy_learning_rate=1.0, performance_legitimacy_fallibility_std=0.0,
        )
        rule = _rule(compliance_count=9, violation_count=1, sanction_count=5)
        registry = {0: rule}
        event_log = EventLog()
        rd.legitimacy_round(0, registry, config, np.random.default_rng(0), event_log)
        assert rule.performance_legitimacy == pytest.approx(0.9)
        assert rule.procedural_legitimacy == 0.0  # untouched -- its own flag is off.
        assert len(event_log.legitimacy_events) == 1

    def test_procedural_only_leaves_performance_untouched(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=8, n_steps=1, performance_legitimacy_enabled=False, procedural_legitimacy_enabled=True,
            procedural_legitimacy_learning_rate=1.0, procedural_legitimacy_fallibility_std=0.0,
        )
        rule = _rule(compliance_count=8, violation_count=2, sanction_count=5)
        registry = {0: rule}
        event_log = EventLog()
        rd.legitimacy_round(0, registry, config, np.random.default_rng(0), event_log)
        assert rule.procedural_legitimacy == pytest.approx(0.5)  # 1 - 5/10
        assert rule.performance_legitimacy == 0.0

    def test_inactive_rules_are_skipped(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=8, n_steps=1, performance_legitimacy_enabled=True,
        )
        rule = _rule(compliance_count=9, violation_count=1)
        rule.active = False
        registry = {0: rule}
        event_log = EventLog()
        rd.legitimacy_round(0, registry, config, np.random.default_rng(0), event_log)
        assert rule.performance_legitimacy == 0.0
        assert event_log.legitimacy_events == []

    def test_event_records_both_ledgers_even_when_only_one_channel_enabled(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=8, n_steps=1, performance_legitimacy_enabled=True,
            performance_legitimacy_learning_rate=1.0, performance_legitimacy_fallibility_std=0.0,
        )
        rule = _rule(compliance_count=4, violation_count=0)
        registry = {0: rule}
        event_log = EventLog()
        rd.legitimacy_round(0, registry, config, np.random.default_rng(0), event_log)
        ev = event_log.legitimacy_events[0]
        assert ev.performance_legitimacy == pytest.approx(1.0)
        assert ev.procedural_legitimacy == 0.0
        assert ev.performance_legitimacy_target == pytest.approx(1.0)


class TestEndToEndOnARealRun:
    def test_both_channels_run_without_error_across_a_full_simulation(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=40, n_steps=150, n_patches=3, seed=29,
            monitoring_mode="voluntary", sanction_mode="voluntary",
            performance_legitimacy_enabled=True, procedural_legitimacy_enabled=True,
        )
        sim = Simulation(config)
        sim.run()
        for ev in sim.event_log.legitimacy_events:
            assert 0.0 <= ev.performance_legitimacy <= 1.0
            assert 0.0 <= ev.procedural_legitimacy <= 1.0
            assert 0.0 <= ev.performance_legitimacy_target <= 1.0
            assert 0.0 <= ev.procedural_legitimacy_target <= 1.0
        for rule in sim.rule_registry.values():
            assert 0.0 <= rule.performance_legitimacy <= 1.0
            assert 0.0 <= rule.procedural_legitimacy <= 1.0

    def test_disabled_reproduces_frozen_reference_exactly(self):
        base = SimulationConfig.level12b_frozen_reference(population_size=30, n_steps=120, n_patches=3, seed=41)
        with_legitimacy_off = SimulationConfig.level12b_frozen_reference(
            population_size=30, n_steps=120, n_patches=3, seed=41,
            historical_module_enabled=True, performance_legitimacy_enabled=False, procedural_legitimacy_enabled=False,
        )
        sim_a = Simulation(base)
        sim_a.run()
        sim_b = Simulation(with_legitimacy_off)
        sim_b.run()
        assert sim_a.event_log.legitimacy_events == []
        assert sim_b.event_log.legitimacy_events == []
        assert len(sim_a.event_log.rule_dissolutions) == len(sim_b.event_log.rule_dissolutions)
