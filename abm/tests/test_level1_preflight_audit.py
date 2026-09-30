"""Level 1.0, mandatory preflight integrity audit (milestone spec §3).

Level 0.3b documented, but did not fix, two dispatch anomalies in
``simulation.py::_adaptation_round``'s ``coupled_same_model`` branch:

1. The branch was gated on ``config.imitation_enabled`` only -- setting
   ``config.ecological_imitation_enabled=False`` alone (the natural way
   to "freeze ecology") had no effect under coupled mode, because that
   flag was never read inside the branch. Freezing ecology required also
   freezing social imitation.
2. The branch never checked ``config.ecological_policy_randomized_each_
   step`` before copying a peer's ecological policy onto the agent's
   stored field -- a behaviorally inert but state-mutating and
   misleadingly-logged copy, since a randomized agent's per-step decision
   never reads the stored field anyway.

This file (a) proves the *scope* of the defects is confined to
``ecological_inheritance_mode="coupled_same_model"`` and never reached by
any Level 0.3b confirmation/causal-intervention/perturbation run (all of
which use the default ``"independent"`` mode -- see
``test_all_level03b_confirmatory_configs_use_the_unaffected_independent_
inheritance_mode`` below), and (b) reproduces both defects' *absence*
under the Level 1.0 fix with regression tests that assert the corrected,
independently-gated behavior. See `docs/level1.0_decision_record.md` and
`dev_mem/status_update.md`'s Level 1.0 entry for the full preflight
report."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from abm_governance.agents.adaptation import coupled_dual_imitation_round
from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation


def _make_agent(agent_id, extraction, maintenance, scarcity, resources=10.0):
    return Agent(
        agent_id=agent_id,
        resources=resources,
        coercive_capability=1.0,
        policy=make_policy("always_cooperate" if agent_id % 2 == 0 else "always_defect"),
        observation_accuracy=0.9,
        learning_rate=0.1,
        forgiveness=0.1,
        risk_sensitivity=0.5,
        exit_cost=1.0,
        memory_length=5,
        ecological_policy=EcologicalPolicy(extraction, maintenance, scarcity),
    )


def _population(n=12):
    rng_seed = np.random.default_rng(0)
    agents = []
    for i in range(n):
        agents.append(
            _make_agent(
                i,
                extraction=float(rng_seed.uniform(0.1, 0.9)),
                maintenance=float(rng_seed.uniform(0.1, 0.9)),
                scarcity=float(rng_seed.uniform(0.1, 0.9)),
                resources=float(rng_seed.uniform(5.0, 50.0)),
            )
        )
    return agents


# ---------------------------------------------------------------------
# Scope of the defects: every Level 0.3b confirmatory/causal/perturbation
# script builds candidate configs via level03b_common.build_candidate_config,
# which never sets ecological_inheritance_mode -- it therefore always
# stays at the SimulationConfig default ("independent"), which never
# enters the coupled_same_model branch at all. This is the basis for the
# preflight report's conclusion that the principal 0.3b causal finding
# (endogenous vs. frozen/randomized, all on the independent path) is
# unaffected by either defect.
# ---------------------------------------------------------------------
def test_all_level03b_confirmatory_configs_use_the_unaffected_independent_inheritance_mode():
    from experiments import level03b_common

    source = inspect.getsource(level03b_common.build_candidate_config)
    assert "ecological_inheritance_mode" not in source
    default_config = SimulationConfig()
    assert default_config.ecological_inheritance_mode == "independent"
    # Directly construct a candidate config the way every Level 0.3b
    # confirmation/causal/perturbation script does and confirm it is not
    # coupled -- i.e. _adaptation_round's `coupled` flag would be False.
    params = {
        "n_patches": 3, "population_size": 16, "patch_regen_rate": 0.5, "patch_capacity": 400.0,
        "ecological_harvest_unit": 5.0, "ecological_search_cost": 0.5, "ecological_maintenance_unit": 5.0,
        "maintenance_efficiency": 0.7, "ecological_mutation_rate": 0.02, "scarcity_sensitivity_mean": 0.3,
        "fitness_mode": "cumulative_resources",
    }
    config = level03b_common.build_candidate_config(params, seed=0, n_steps=10, condition="endogenous")
    assert config.ecological_inheritance_mode == "independent"


# ---------------------------------------------------------------------
# Defect 1 regression: ecological_imitation_enabled=False must freeze
# ONLY the ecological copy under coupled mode, not social imitation too.
# ---------------------------------------------------------------------
def test_coupled_mode_ecological_imitation_enabled_false_freezes_ecology_not_social():
    config = SimulationConfig.level03_patches_default(
        seed=11, population_size=20, n_steps=60, imitation_period=3,
        ecological_inheritance_mode="coupled_same_model",
        ecological_imitation_enabled=False,
        ecological_mutation_rate=0.0,
    )
    assert config.imitation_enabled is True  # social imitation left at its default (enabled)
    result = Simulation(config).run()
    assert result.event_log.ecological_imitations == [], (
        "ecological_imitation_enabled=False must produce zero ecological-imitation events "
        "under coupled mode -- this is exactly the pre-fix defect (freezing ecology required "
        "also freezing social imitation)"
    )
    assert result.event_log.imitations, (
        "social imitation must still occur -- freezing ecology alone must not silently "
        "freeze social imitation too"
    )


# ---------------------------------------------------------------------
# Defect 2 regression: ecological_policy_randomized_each_step=True must
# suppress the ecological copy/event under coupled mode.
# ---------------------------------------------------------------------
def test_coupled_mode_randomized_ecology_suppresses_ecological_copy_and_event():
    config = SimulationConfig.level03_patches_default(
        seed=12, population_size=20, n_steps=60, imitation_period=3,
        ecological_inheritance_mode="coupled_same_model",
        ecological_policy_randomized_each_step=True,
    )
    result = Simulation(config).run()
    assert result.event_log.ecological_imitations == [], (
        "randomized ecological policy must suppress the (behaviorally inert but "
        "previously still-applied) ecological copy under coupled mode"
    )
    assert result.event_log.imitations, "social imitation must be unaffected by the randomized-ecology flag"


# ---------------------------------------------------------------------
# The fix also incidentally enables an intervention that was previously
# impossible: freezing SOCIAL imitation while leaving ecological
# imitation active under coupled mode (imitation_enabled=False,
# ecological_imitation_enabled=True). Per the audit requirement "verify
# that each intervention changes only its intended mechanism," this must
# work symmetrically.
# ---------------------------------------------------------------------
def test_coupled_mode_imitation_enabled_false_freezes_social_not_ecology():
    config = SimulationConfig.level03_patches_default(
        seed=13, population_size=20, n_steps=60, imitation_period=3,
        ecological_inheritance_mode="coupled_same_model",
        imitation_enabled=False,
    )
    result = Simulation(config).run()
    assert result.event_log.imitations == [], "imitation_enabled=False must produce zero social imitation events"
    assert result.event_log.ecological_imitations, (
        "ecological imitation must still occur under coupled mode when only social "
        "imitation is disabled -- each flag must gate only its own mechanism"
    )


# ---------------------------------------------------------------------
# Unaffected-cell regression: when neither gating flag would have
# changed anything (both apply_social and apply_ecological True -- the
# ordinary "endogenous" coupled condition), behavior must be identical to
# before the fix: every accepted decision applies and logs BOTH sides,
# from the same model agent, at the same step (this is exactly what
# tests/test_level03_niche_construction.py::
# test_coupled_inheritance_mode_ties_social_and_ecological_to_the_same_
# model_agent already asserts and continues to pass unmodified -- see
# that file). This test adds a determinism check on top: two runs with
# an identical seed under the unaffected configuration must be bit-exact.
# ---------------------------------------------------------------------
def test_coupled_mode_unaffected_configuration_is_still_deterministic():
    def run_once():
        config = SimulationConfig.level03_patches_default(
            seed=14, population_size=16, n_steps=40, imitation_period=5,
            ecological_inheritance_mode="coupled_same_model",
        )
        result = Simulation(config).run()
        return [
            (e.step, e.agent, e.model_agent, e.new_extraction_propensity, e.new_maintenance_propensity)
            for e in result.event_log.ecological_imitations
        ]

    assert run_once() == run_once()


# ---------------------------------------------------------------------
# Function-level regression: the shared peer draw + Fermi decision (and
# hence the social-imitation outcome) must be byte-identical regardless
# of apply_ecological -- the fix must not perturb the RNG stream used for
# the shared decision itself, only which side(s) get applied afterward.
# ---------------------------------------------------------------------
def test_coupled_dual_imitation_round_social_outcome_independent_of_apply_ecological_flag():
    agents_a = _population(14)
    agents_b = [
        _make_agent(a.agent_id, a.ecological_policy.extraction_propensity,
                    a.ecological_policy.maintenance_propensity, a.ecological_policy.scarcity_sensitivity,
                    a.resources)
        for a in agents_a
    ]
    rng_a = np.random.default_rng(999)
    rng_b = np.random.default_rng(999)

    social_events_a, ecological_events_a = coupled_dual_imitation_round(
        agents_a, rng_a, step=0, apply_social=True, apply_ecological=True,
    )
    social_events_b, ecological_events_b = coupled_dual_imitation_round(
        agents_b, rng_b, step=0, apply_social=True, apply_ecological=False,
    )

    key = lambda e: (e.step, e.agent, e.model_agent, e.old_policy, e.new_policy)  # noqa: E731
    assert [key(e) for e in social_events_a] == [key(e) for e in social_events_b]
    assert ecological_events_a  # the shared decision did accept for at least one agent
    assert ecological_events_b == []  # but the ecological side was suppressed


# ---------------------------------------------------------------------
# Default-argument compatibility: calling coupled_dual_imitation_round
# without apply_social/apply_ecological must reproduce the exact pre-fix
# unconditional-both-copy behavior (both default True).
# ---------------------------------------------------------------------
def test_coupled_dual_imitation_round_legacy_call_defaults_to_applying_both_sides():
    sig = inspect.signature(coupled_dual_imitation_round)
    assert sig.parameters["apply_social"].default is True
    assert sig.parameters["apply_ecological"].default is True

    agents = _population(10)
    rng = np.random.default_rng(42)
    social_events, ecological_events = coupled_dual_imitation_round(agents, rng, step=0)
    social_keys = {(e.step, e.agent) for e in social_events}
    ecological_keys = {(e.step, e.agent) for e in ecological_events}
    assert social_keys == ecological_keys, "legacy call (no explicit flags) must apply both sides together"


# ---------------------------------------------------------------------
# environment_only and endogenous cells under coupled mode were never
# affected (neither flag is touched by either condition's overrides) --
# confirm this structurally against the actual override table.
# ---------------------------------------------------------------------
def test_environment_only_and_endogenous_condition_overrides_do_not_touch_imitation_gating_flags():
    from experiments.level03b_common import CONDITION_OVERRIDES

    for condition in ("endogenous", "environment_only"):
        overrides = CONDITION_OVERRIDES[condition]
        assert "ecological_imitation_enabled" not in overrides
        assert "ecological_policy_randomized_each_step" not in overrides
        assert "imitation_enabled" not in overrides
