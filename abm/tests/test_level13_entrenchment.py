"""Level 1.3, Work Package C (Section 8): continuous institutional
entrenchment (``core/entrenchment.py`` + its wiring into
``rules/dynamics.py::amendment_round``/``dissolution_round``)."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core import entrenchment as ce
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog
from abm_governance.environment.patches import PatchSystem, ResourcePatch
from abm_governance.rules import dynamics as rd
from abm_governance.rules.shared_rule import RuleParameters, SharedRule
from abm_governance.simulation import Simulation


def _agent(agent_id, patch_id=0, resources=20.0, **overrides):
    a = Agent(
        agent_id=agent_id, resources=resources, coercive_capability=0.0, policy=make_policy("tit_for_tat"),
        observation_accuracy=1.0, learning_rate=0.1, forgiveness=0.1, risk_sensitivity=0.5, exit_cost=0.1,
    )
    a.patch_id = patch_id
    a.ecological_policy = EcologicalPolicy(0.5, 0.3, 0.0)
    for k, v in overrides.items():
        setattr(a, k, v)
    return a


def _rule(rule_id=0, patch_id=0, members=(0, 1), founder=0, founding_step=0, **param_overrides):
    params = RuleParameters(
        extraction_ceiling=0.3, maintenance_requirement=0.4, monitoring_intensity=0.5,
        sanction_magnitude=0.5, adoption_threshold=0.5, amendment_threshold=0.5,
    )
    if param_overrides:
        kwargs = params.as_dict()
        kwargs.update(param_overrides)
        params = RuleParameters(**kwargs)
    return SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=founding_step,
        founder_id=founder, rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )


def _build_patch_sim(n_agents=8, **agent_overrides):
    agents = [_agent(i, patch_id=0, resources=20.0, willingness_to_join=0.9, **agent_overrides) for i in range(n_agents)]
    agents_by_id = {a.agent_id: a for a in agents}
    patch = ResourcePatch(patch_id=0, capacity=100.0, regen_rate=0.1, resources=50.0, members=frozenset(agents_by_id.keys()))
    patch_system = PatchSystem(patches={0: patch}, agent_patch={a.agent_id: 0 for a in agents})
    return agents, agents_by_id, patch_system


class TestEntrenchmentLevel:
    def test_zero_age_is_zero(self):
        assert ce.entrenchment_level(0, 100) == 0.0

    def test_ramps_linearly(self):
        assert ce.entrenchment_level(50, 100) == pytest.approx(0.5)

    def test_caps_at_one(self):
        assert ce.entrenchment_level(500, 100) == 1.0

    def test_never_negative(self):
        assert ce.entrenchment_level(-5, 100) == 0.0

    def test_nonpositive_maturation_treated_as_instantaneous(self):
        assert ce.entrenchment_level(1, 0) == 1.0
        assert ce.entrenchment_level(0, 0) == 0.0


class TestEntrenchmentAdjustedThreshold:
    def test_raises_threshold_proportionally(self):
        assert ce.entrenchment_adjusted_threshold(0.5, 1.0, 0.3) == pytest.approx(0.8)

    def test_zero_entrenchment_is_exact_noop(self):
        assert ce.entrenchment_adjusted_threshold(0.42, 0.0, 0.9) == pytest.approx(0.42)

    def test_capped_below_one(self):
        assert ce.entrenchment_adjusted_threshold(0.9, 1.0, 5.0) == pytest.approx(0.999)
        assert ce.entrenchment_adjusted_threshold(0.9, 1.0, 5.0) < 1.0


class TestEntrenchmentSurvivalProbability:
    def test_zero_entrenchment_is_zero_probability(self):
        assert ce.entrenchment_survival_probability(0.0, 0.9) == 0.0

    def test_scales_with_entrenchment(self):
        assert ce.entrenchment_survival_probability(0.5, 0.4) == pytest.approx(0.2)

    def test_capped_below_one(self):
        assert ce.entrenchment_survival_probability(1.0, 5.0) == pytest.approx(0.9)
        assert ce.entrenchment_survival_probability(1.0, 5.0) < 1.0

    def test_never_negative(self):
        assert ce.entrenchment_survival_probability(1.0, -3.0) == 0.0


class TestAmendmentRoundThresholdEffect:
    def test_disabled_is_exact_noop_vs_baseline_behavior(self):
        config = SimulationConfig.level1_rule_formation_default(population_size=8, n_steps=1)
        assert config.entrenchment_enabled is False
        agents, agents_by_id, _ = _build_patch_sim()
        for a in agents:
            a.amendment_propensity = 1.0
            a.willingness_to_join = 0.9
        rule = _rule(members=tuple(a.agent_id for a in agents), amendment_threshold=0.1, founding_step=0)
        registry = {0: rule}
        event_log = EventLog()
        rd.amendment_round(500, registry, agents_by_id, config, np.random.default_rng(0), event_log)
        assert len(event_log.rule_amendments) == 1
        ev = event_log.rule_amendments[0]
        # Always logged (an "additional record" per the field's own
        # docstring), and equal to the rule's own nominal threshold when
        # entrenchment is disabled -- never raised.
        assert ev.effective_amendment_threshold == pytest.approx(0.1)

    def test_entrenchment_raises_the_effective_threshold_and_can_flip_adoption(self):
        # amendment_threshold=0.5, support achievable ~0.9 at best (all
        # members willing) -- with a maturation of 10 steps and
        # sensitivity 0.3, a rule aged 100 steps is fully entrenched
        # (entrenchment=1.0), raising the effective threshold to 0.8.
        for enabled, age, expect_threshold in ((False, 100, 0.5), (True, 100, 0.8), (True, 0, 0.5)):
            config = SimulationConfig.level1_rule_formation_default(
                population_size=8, n_steps=1, entrenchment_enabled=enabled,
                entrenchment_maturation_steps=10, entrenchment_amendment_threshold_sensitivity=0.3,
            )
            agents, agents_by_id, _ = _build_patch_sim()
            for a in agents:
                a.amendment_propensity = 1.0
                a.willingness_to_join = 0.9
            rule = _rule(members=tuple(a.agent_id for a in agents), amendment_threshold=0.5, founding_step=0)
            registry = {0: rule}
            event_log = EventLog()
            rd.amendment_round(age, registry, agents_by_id, config, np.random.default_rng(1), event_log)
            assert len(event_log.rule_amendments) == 1
            assert event_log.rule_amendments[0].effective_amendment_threshold == pytest.approx(expect_threshold)


class TestAmendmentRoundDissolutionSurvival:
    def test_young_rule_always_dissolves_even_when_entrenchment_enabled(self):
        # age=0 -> entrenchment=0.0 -> survive_p=0.0 -> identical to disabled.
        config = SimulationConfig.level1_rule_formation_default(
            population_size=8, n_steps=1, rule_dissolution_support_floor=0.9,
            entrenchment_enabled=True, entrenchment_maturation_steps=200, entrenchment_dissolution_survival_sensitivity=0.9,
        )
        agents, agents_by_id, _ = _build_patch_sim()
        for a in agents:
            a.amendment_propensity = 1.0
            a.willingness_to_join = 0.01
        rule = _rule(members=tuple(a.agent_id for a in agents), amendment_threshold=0.99, founding_step=0)
        registry = {0: rule}
        event_log = EventLog()
        last_dissolved = {}
        rd.amendment_round(0, registry, agents_by_id, config, np.random.default_rng(0), event_log, last_dissolved)
        assert 0 not in registry
        assert rule.dissolution_reason == "support_below_floor"

    def test_mature_entrenched_rule_survives_more_often_than_a_young_one(self):
        n = 60
        n_survived_young = 0
        n_survived_old = 0
        for seed in range(n):
            for age, counter in ((0, "young"), (500, "old")):
                config = SimulationConfig.level1_rule_formation_default(
                    population_size=8, n_steps=1, rule_dissolution_support_floor=0.9,
                    entrenchment_enabled=True, entrenchment_maturation_steps=100,
                    entrenchment_dissolution_survival_sensitivity=0.9,
                )
                agents, agents_by_id, _ = _build_patch_sim()
                for a in agents:
                    a.amendment_propensity = 1.0
                    a.willingness_to_join = 0.01
                rule = _rule(members=tuple(a.agent_id for a in agents), amendment_threshold=0.99, founding_step=0)
                registry = {0: rule}
                event_log = EventLog()
                last_dissolved = {}
                rd.amendment_round(age, registry, agents_by_id, config, np.random.default_rng(seed), event_log, last_dissolved)
                survived = 0 in registry
                if counter == "young" and survived:
                    n_survived_young += 1
                if counter == "old" and survived:
                    n_survived_old += 1
        assert n_survived_young == 0  # entrenchment=0 at age 0 -- deterministically dissolves.
        assert n_survived_old > 0


class TestDissolutionRoundEntrenchmentSurvival:
    def test_requires_entrenchment_rng_when_enabled(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=8, n_steps=1, rule_dissolution_membership_floor=0.5, entrenchment_enabled=True,
        )
        agents, agents_by_id, patch_system = _build_patch_sim()
        registry = {0: _rule(patch_id=0, members=(0,))}
        agents_by_id[0].rule_member_of = 0
        with pytest.raises(ValueError):
            rd.dissolution_round(0, registry, agents_by_id, patch_system, config, EventLog(), {})

    def test_disabled_behaves_exactly_like_pre_level13_dissolution(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=8, n_steps=1, rule_dissolution_membership_floor=0.5,
        )
        assert config.entrenchment_enabled is False
        agents, agents_by_id, patch_system = _build_patch_sim()
        registry = {0: _rule(patch_id=0, members=(0,), founding_step=0)}
        agents_by_id[0].rule_member_of = 0
        last_dissolved = {}
        rd.dissolution_round(500, registry, agents_by_id, patch_system, config, EventLog(), last_dissolved)
        assert registry == {}
        assert last_dissolved[0].dissolution_reason == "membership_below_floor"

    def test_young_rule_with_membership_breach_always_dissolves(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=8, n_steps=1, rule_dissolution_membership_floor=0.5,
            entrenchment_enabled=True, entrenchment_maturation_steps=100, entrenchment_dissolution_survival_sensitivity=0.9,
        )
        agents, agents_by_id, patch_system = _build_patch_sim()
        registry = {0: _rule(patch_id=0, members=(0,), founding_step=0)}
        agents_by_id[0].rule_member_of = 0
        last_dissolved = {}
        rd.dissolution_round(0, registry, agents_by_id, patch_system, config, EventLog(), last_dissolved, entrenchment_rng=np.random.default_rng(0))
        assert registry == {}  # age 0 -> entrenchment 0 -> deterministic dissolution.

    def test_mature_rule_can_survive_a_membership_breach(self):
        n = 60
        n_survived = 0
        for seed in range(n):
            config = SimulationConfig.level1_rule_formation_default(
                population_size=8, n_steps=1, rule_dissolution_membership_floor=0.5,
                entrenchment_enabled=True, entrenchment_maturation_steps=100, entrenchment_dissolution_survival_sensitivity=0.9,
            )
            agents, agents_by_id, patch_system = _build_patch_sim()
            registry = {0: _rule(patch_id=0, members=(0,), founding_step=0)}
            agents_by_id[0].rule_member_of = 0
            last_dissolved = {}
            rd.dissolution_round(
                500, registry, agents_by_id, patch_system, config, EventLog(), last_dissolved,
                entrenchment_rng=np.random.default_rng(seed),
            )
            if 0 in registry:
                n_survived += 1
        assert n_survived > 0

    def test_entrenchment_survival_never_reaches_certainty(self):
        # Even at maximal age and sensitivity, dissolution must remain
        # POSSIBLE (Work Package C's own "must not make deactivation
        # impossible" invariant) -- run many seeds and confirm at least
        # one still dissolves.
        n = 80
        n_dissolved = 0
        for seed in range(n):
            config = SimulationConfig.level1_rule_formation_default(
                population_size=8, n_steps=1, rule_dissolution_membership_floor=0.5,
                entrenchment_enabled=True, entrenchment_maturation_steps=1, entrenchment_dissolution_survival_sensitivity=100.0,
            )
            agents, agents_by_id, patch_system = _build_patch_sim()
            registry = {0: _rule(patch_id=0, members=(0,), founding_step=0)}
            agents_by_id[0].rule_member_of = 0
            last_dissolved = {}
            rd.dissolution_round(
                10_000, registry, agents_by_id, patch_system, config, EventLog(), last_dissolved,
                entrenchment_rng=np.random.default_rng(seed),
            )
            if 0 not in registry:
                n_dissolved += 1
        assert n_dissolved > 0


class TestEndToEndOnARealRun:
    def test_entrenchment_runs_without_error_across_a_run_long_enough_to_mature(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=40, n_steps=250, n_patches=3, seed=23,
            entrenchment_enabled=True, entrenchment_maturation_steps=30,
            entrenchment_amendment_threshold_sensitivity=0.3, entrenchment_dissolution_survival_sensitivity=0.5,
        )
        sim = Simulation(config)
        sim.run()
        # No crash is the primary assertion; if any amendment fired, its
        # logged effective threshold must be a valid probability-like
        # value >= the rule's own nominal amendment_threshold (0.5 by
        # this preset's own trait defaults is not guaranteed, so just
        # check well-formedness).
        for ev in sim.event_log.rule_amendments:
            assert 0.0 <= ev.effective_amendment_threshold <= 1.0

    def test_disabled_reproduces_frozen_reference_exactly(self):
        # Sanity cross-check specific to this task's new code paths,
        # complementing (not replacing) tests/test_level13_compatibility.py's
        # broader AST-based guarantee.
        base = SimulationConfig.level12b_frozen_reference(population_size=30, n_steps=120, n_patches=3, seed=31)
        with_entrenchment_off = SimulationConfig.level12b_frozen_reference(
            population_size=30, n_steps=120, n_patches=3, seed=31,
            historical_module_enabled=True, entrenchment_enabled=False,
        )
        sim_a = Simulation(base)
        sim_a.run()
        sim_b = Simulation(with_entrenchment_off)
        sim_b.run()
        assert len(sim_a.event_log.rule_amendments) == len(sim_b.event_log.rule_amendments)
        assert len(sim_a.event_log.rule_dissolutions) == len(sim_b.event_log.rule_dissolutions)
        for ea, eb in zip(sim_a.event_log.rule_dissolutions, sim_b.event_log.rule_dissolutions):
            assert ea.reason == eb.reason
            assert ea.step == eb.step
