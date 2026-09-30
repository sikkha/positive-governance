"""Level 0.3 integration tests: the central social/ecological separation
principle, exact per-agent and per-patch ledger identities, ecological
lineage propagation under both inheritance modes, exact Level-0.2
compatibility, deterministic replay under the patches topology, and a
structural check against reintroducing governance terminology into the
new Level 0.3 code.
"""

from __future__ import annotations

import math

import pytest

from abm_governance.agents.agent import FORBIDDEN_ATTRIBUTE_SUBSTRINGS, Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EcologicalActionEvent, EcologicalImitationEvent, EcologicalMutationEvent
from abm_governance.simulation import Simulation


def _metrics_equal_nan_safe(rows_a: list[dict], rows_b: list[dict]) -> bool:
    """Row-by-row, key-by-key comparison treating NaN == NaN (unlike
    Python's default float equality) -- needed because under the patches
    topology ``environment_resources`` (a global-pool-only column) is NaN
    on every step by construction, which would otherwise make an
    ordinary ``==`` comparison report every pair of runs as "different"
    even when they are bit-for-bit identical."""
    if len(rows_a) != len(rows_b):
        return False
    for ra, rb in zip(rows_a, rows_b):
        if ra.keys() != rb.keys():
            return False
        for k in ra:
            va, vb = ra[k], rb[k]
            if isinstance(va, float) and isinstance(vb, float) and va != va and vb != vb:
                continue  # both NaN
            if va != vb:
                return False
    return True


# ---------------------------------------------------------------------
# Exact ledger identities (Work Package C)
# ---------------------------------------------------------------------

def test_ecological_round_agent_ledger_identity_hand_computed():
    """Directly exercise ``Simulation._ecological_round`` in isolation
    (bypassing the full interaction loop) with fully controlled ecological
    policies and a single patch, and verify the exact per-agent identity:
    resources_after == resources_before + actual_extraction -
    requested_maintenance - search_cost."""
    config = SimulationConfig.level03_patches_default(
        seed=0, population_size=2, n_patches=1, n_steps=1, mean_degree=1,
        ecological_search_cost=0.5,
        maintenance_efficiency=0.4,
        ecological_harvest_unit=10.0,
        ecological_maintenance_unit=10.0,
    )
    sim = Simulation(config)
    # Force deterministic, distinct ecological policies (bypassing the
    # random draw so the expected requested h/m are hand-computable).
    sim.agents[0].ecological_policy = EcologicalPolicy(
        extraction_propensity=1.0, maintenance_propensity=0.0, scarcity_sensitivity=0.0
    )
    sim.agents[1].ecological_policy = EcologicalPolicy(
        extraction_propensity=0.0, maintenance_propensity=1.0, scarcity_sensitivity=0.0
    )
    patch = next(iter(sim.patch_system.patches.values()))
    patch.resources = 5.0  # deliberately scarce, forces rationing of extraction

    resources_before = {a.agent_id: a.resources for a in sim.agents}
    sim._ecological_round(step=0)

    events = {e.agent: e for e in sim.event_log.ecological_actions}
    assert set(events) == {0, 1}

    # Agent 0 requested h=10 (extraction_propensity=1 * harvest_unit=10,
    # scarcity_sensitivity=0 so occupancy doesn't matter), m=0.
    e0 = events[0]
    assert e0.requested_extraction == pytest.approx(10.0)
    assert e0.requested_maintenance == pytest.approx(0.0)
    # Agent 1 requested h=0, m=10 (maintenance_propensity=1 * unit=10).
    e1 = events[1]
    assert e1.requested_extraction == pytest.approx(0.0)
    assert e1.requested_maintenance == pytest.approx(10.0)

    # Only agent 0 competes for the patch's 5.0 available stock (agent 1
    # requested zero extraction) -> agent 0 gets the full 5.0 (no rationing
    # needed against a single non-zero requester).
    assert e0.actual_extraction == pytest.approx(5.0)

    for agent in sim.agents:
        e = events[agent.agent_id]
        expected_resources = (
            resources_before[agent.agent_id] + e.actual_extraction - e.requested_maintenance - e.ecological_search_cost
        )
        assert agent.resources == pytest.approx(expected_resources)

    # search_cost=0.5 is charged only to an agent that actually *requested*
    # positive extraction (agent 0), not to a pure-maintenance agent.
    assert e0.ecological_search_cost == pytest.approx(0.5)
    assert e1.ecological_search_cost == pytest.approx(0.0)


def test_ecological_round_patch_ledger_identity_hand_computed():
    """Per-patch identity: R_{t+1} == R_t + natural_regeneration +
    maintenance_effective - actual_extraction, using the patch's own
    cumulative counters recorded by the same ``_ecological_round`` call as
    above."""
    config = SimulationConfig.level03_patches_default(
        seed=1, population_size=2, n_patches=1, n_steps=1, mean_degree=1,
        maintenance_efficiency=0.5, ecological_harvest_unit=10.0, ecological_maintenance_unit=10.0,
        patch_regen_rate=0.5, patch_capacity=200.0,
    )
    sim = Simulation(config)
    sim.agents[0].ecological_policy = EcologicalPolicy(1.0, 0.0, 0.0)
    sim.agents[1].ecological_policy = EcologicalPolicy(0.0, 1.0, 0.0)
    patch = next(iter(sim.patch_system.patches.values()))
    patch.resources = 50.0

    r_before = patch.resources
    maint_before = patch.cumulative_maintenance_effective
    extr_before = patch.cumulative_ecological_extraction
    regen_before = patch.cumulative_regeneration

    sim._ecological_round(step=0)

    maint_effective = patch.cumulative_maintenance_effective - maint_before
    extr_actual = patch.cumulative_ecological_extraction - extr_before
    regen_actual = patch.cumulative_regeneration - regen_before

    assert patch.resources == pytest.approx(r_before + regen_actual + maint_effective - extr_actual)
    assert 0.0 <= patch.resources <= patch.capacity


def test_ecological_round_is_a_no_op_when_patch_system_is_none():
    config = SimulationConfig(population_size=10, n_steps=1, seed=0)  # global_pool topology
    sim = Simulation(config)
    assert sim.patch_system is None
    sim._ecological_round(step=0)  # must not raise, must log nothing
    assert sim.event_log.ecological_actions == []


def test_ecological_round_skips_dead_agents_and_dead_only_patches():
    """A dead agent must be excluded from both the request phase and the
    per-agent ledger-application phase; a patch whose every member is
    dead must be skipped entirely rather than raising a KeyError on an
    empty request dict."""
    config = SimulationConfig.level03_patches_default(
        seed=12, population_size=4, n_patches=2, n_steps=1, mean_degree=1,
        patch_assignment_mode="random_assignment",
    )
    sim = Simulation(config)
    # Kill every agent assigned to patch 0's members, if any; if patch 0
    # has no members under this seed, kill whichever patch does have
    # members instead -- either way, drive at least one patch to zero
    # living members.
    for patch in sim.patch_system.patches.values():
        if patch.members:
            for aid in patch.members:
                sim.agents_by_id[aid].alive = False
            break
    sim._ecological_round(step=0)  # must not raise
    logged_agents = {e.agent for e in sim.event_log.ecological_actions}
    assert all(sim.agents_by_id[aid].alive for aid in logged_agents)


def test_no_environmental_effect_counterfactual_leaves_patch_state_untouched_except_regeneration():
    """Work Package F condition 2: agents still decide and still pay/earn
    (their ledgers change), but the patch's own resources evolve as if
    only natural regeneration ran -- not as if agent extraction/
    maintenance had any effect."""
    config = SimulationConfig.level03_patches_default(
        seed=13, population_size=2, n_patches=1, n_steps=1, mean_degree=1,
        ecological_actions_affect_patch=False,
        ecological_harvest_unit=10.0, ecological_maintenance_unit=10.0,
        patch_regen_rate=0.5, patch_capacity=200.0,
    )
    sim = Simulation(config)
    sim.agents[0].ecological_policy = EcologicalPolicy(1.0, 0.0, 0.0)
    sim.agents[1].ecological_policy = EcologicalPolicy(0.0, 1.0, 0.0)
    patch = next(iter(sim.patch_system.patches.values()))
    patch.resources = 50.0
    resources_before_agents = {a.agent_id: a.resources for a in sim.agents}

    sim._ecological_round(step=0)

    # Patch resources must equal exactly what natural regeneration alone
    # would have produced from 50.0 -- untouched by the agents' extraction
    # or maintenance requests.
    expected_regen = 0.5 * 50.0 * (1.0 - 50.0 / 200.0)
    assert patch.resources == pytest.approx(50.0 + expected_regen)
    assert patch.cumulative_ecological_extraction == pytest.approx(0.0)
    assert patch.cumulative_maintenance_effective == pytest.approx(0.0)

    # But the agents' own ledgers still changed exactly as in the
    # endogenous-feedback condition (same allocation arithmetic, just not
    # applied to the patch).
    events = {e.agent: e for e in sim.event_log.ecological_actions}
    assert events[0].actual_extraction > 0.0
    assert sim.agents[0].resources != pytest.approx(resources_before_agents[0])
    assert sim.agents[1].resources != pytest.approx(resources_before_agents[1])


def test_policy_shuffle_preserves_marginal_distribution_of_ecological_policies():
    """Work Package F 'replay/policy-shuffle' counterfactual: the exact
    multiset of ecological policies must be preserved, only their
    assignment to agents changes."""
    config = SimulationConfig.level03_patches_default(
        seed=14, population_size=20, n_patches=4, n_steps=1, ecological_policy_shuffle=True,
    )
    unshuffled_config = SimulationConfig.level03_patches_default(
        seed=14, population_size=20, n_patches=4, n_steps=1, ecological_policy_shuffle=False,
    )
    shuffled = Simulation(config)
    unshuffled = Simulation(unshuffled_config)
    shuffled_multiset = sorted(
        (a.ecological_policy.extraction_propensity, a.ecological_policy.maintenance_propensity, a.ecological_policy.scarcity_sensitivity)
        for a in shuffled.agents
    )
    unshuffled_multiset = sorted(
        (a.ecological_policy.extraction_propensity, a.ecological_policy.maintenance_propensity, a.ecological_policy.scarcity_sensitivity)
        for a in unshuffled.agents
    )
    assert shuffled_multiset == unshuffled_multiset
    # And every shuffled agent's lineage id was reset to its own agent_id
    # (the shuffle is not itself a lineage-propagation event).
    for a in shuffled.agents:
        assert a.ecological_policy_lineage_id == a.agent_id


# ---------------------------------------------------------------------
# The central social/ecological separation principle (all four joint
# combinations must be possible)
# ---------------------------------------------------------------------

def test_socially_cooperative_agent_can_overextract():
    """A social always_cooperate agent with a high extraction_propensity
    and zero maintenance_propensity must still be able to extract heavily
    -- social cooperation must never be equated with ecological
    maintenance."""
    config = SimulationConfig.level03_patches_default(
        seed=2, population_size=2, n_patches=1, n_steps=1, mean_degree=1,
        ecological_harvest_unit=10.0, patch_capacity=500.0, patch_initial_fraction=1.0,
    )
    sim = Simulation(config)
    sim.agents[0].policy = make_policy("always_cooperate")
    sim.agents[0].ecological_policy = EcologicalPolicy(
        extraction_propensity=1.0, maintenance_propensity=0.0, scarcity_sensitivity=0.0
    )
    sim._ecological_round(step=0)
    event = sim.event_log.ecological_actions[0]
    assert event.actual_extraction > 0.0
    assert event.requested_maintenance == pytest.approx(0.0)


def test_socially_defective_agent_can_maintain():
    """A social always_defect agent with zero extraction_propensity and a
    high maintenance_propensity must still be able to invest in
    maintenance -- ecological maintenance must never imply social
    cooperation."""
    config = SimulationConfig.level03_patches_default(
        seed=3, population_size=2, n_patches=1, n_steps=1, mean_degree=1,
        ecological_maintenance_unit=10.0, maintenance_efficiency=1.0,
        patch_capacity=500.0, patch_initial_fraction=0.5,
    )
    sim = Simulation(config)
    sim.agents[0].policy = make_policy("always_defect")
    sim.agents[0].ecological_policy = EcologicalPolicy(
        extraction_propensity=0.0, maintenance_propensity=1.0, scarcity_sensitivity=0.0
    )
    resources_before = sim.agents[0].resources
    sim._ecological_round(step=0)
    event = sim.event_log.ecological_actions[0]
    assert event.requested_maintenance > 0.0
    assert event.actual_extraction == pytest.approx(0.0)
    # Maintenance is an immediate individual cost, paid regardless of any
    # extraction gain.
    assert sim.agents[0].resources == pytest.approx(resources_before - event.requested_maintenance)


def test_all_four_social_ecological_joint_combinations_are_representable():
    """Structural check: the four combinations of {cooperate, defect} x
    {maintain, overextract} are each individually constructible and
    produce the expected sign pattern on requested extraction/maintenance
    -- i.e. no code path silently forces a correlation between the two
    dimensions."""
    combos = [
        ("always_cooperate", 1.0, 0.0),  # cooperate + overextract
        ("always_cooperate", 0.0, 1.0),  # cooperate + maintain
        ("always_defect", 1.0, 0.0),  # defect + overextract
        ("always_defect", 0.0, 1.0),  # defect + maintain
    ]
    for social_name, extraction_prop, maintenance_prop in combos:
        config = SimulationConfig.level03_patches_default(
            seed=4, population_size=2, n_patches=1, n_steps=1, mean_degree=1,
            ecological_harvest_unit=10.0, ecological_maintenance_unit=10.0,
            patch_capacity=500.0, patch_initial_fraction=0.5,
        )
        sim = Simulation(config)
        sim.agents[0].policy = make_policy(social_name)
        sim.agents[0].ecological_policy = EcologicalPolicy(extraction_prop, maintenance_prop, 0.0)
        sim._ecological_round(step=0)
        event = sim.event_log.ecological_actions[0]
        if extraction_prop > 0:
            assert event.requested_extraction > 0.0
        else:
            assert event.requested_extraction == pytest.approx(0.0)
        if maintenance_prop > 0:
            assert event.requested_maintenance > 0.0
        else:
            assert event.requested_maintenance == pytest.approx(0.0)


# ---------------------------------------------------------------------
# Learning/evolution of the ecological policy (Work Package D)
# ---------------------------------------------------------------------

def test_independent_ecological_imitation_propagates_lineage():
    config = SimulationConfig.level03_patches_default(
        seed=5, population_size=16, n_steps=60, imitation_period=5,
        ecological_inheritance_mode="independent",
    )
    result = Simulation(config).run()
    assert result.event_log.ecological_imitations, "expected at least one independent ecological imitation event"
    for e in result.event_log.ecological_imitations:
        assert e.inheritance_mode == "independent"
        assert not math.isnan(e.agent_fitness)
        assert not math.isnan(e.model_fitness)
        assert e.fitness_gap == pytest.approx(e.model_fitness - e.agent_fitness)
    final_lineages = {a.agent_id: a.ecological_policy_lineage_id for a in result.final_agents}
    # At least one agent's final ecological lineage id must differ from its
    # own agent_id (i.e. lineage actually propagated from somewhere else).
    assert any(lid != aid for aid, lid in final_lineages.items())


def test_ecological_mutation_assigns_a_fresh_never_before_used_lineage_id():
    config = SimulationConfig.level03_patches_default(
        seed=6, population_size=20, n_steps=60, imitation_period=5, ecological_mutation_rate=0.3,
    )
    result = Simulation(config).run()
    assert result.event_log.ecological_mutations
    seen_ids = {a.agent_id for a in result.final_agents}
    for e in result.event_log.ecological_mutations:
        assert e.resulting_ecological_lineage_id not in seen_ids or e.resulting_ecological_lineage_id >= config.population_size


def test_coupled_inheritance_mode_ties_social_and_ecological_to_the_same_model_agent():
    config = SimulationConfig.level03_patches_default(
        seed=7, population_size=16, n_steps=40, imitation_period=5,
        ecological_inheritance_mode="coupled_same_model",
    )
    result = Simulation(config).run()
    social_by_step_agent = {(e.step, e.agent): e.model_agent for e in result.event_log.imitations}
    eco_by_step_agent = {(e.step, e.agent): e.model_agent for e in result.event_log.ecological_imitations}
    # Every coupled ecological-imitation event must have a matching social
    # imitation event, from the *same* model agent, at the same step.
    assert eco_by_step_agent, "expected coupled imitation events"
    for key, eco_model in eco_by_step_agent.items():
        assert key in social_by_step_agent
        assert social_by_step_agent[key] == eco_model
    for e in result.event_log.ecological_imitations:
        assert e.inheritance_mode == "coupled_same_model"


def test_ecological_imitation_disabled_flag_produces_no_ecological_imitation_events():
    config = SimulationConfig.level03_patches_default(
        seed=8, population_size=16, n_steps=40, imitation_period=5,
        ecological_imitation_enabled=False, ecological_mutation_rate=0.0,
    )
    result = Simulation(config).run()
    assert result.event_log.ecological_imitations == []
    assert result.event_log.ecological_mutations == []
    # Social imitation is untouched by the ecological flag.
    assert result.event_log.imitations


def test_randomized_each_step_never_imitates_or_mutates_ecological_policy():
    """Work Package F 'randomized ecological policy' counterfactual: an
    agent's stored ecological_policy is never read for decisions and must
    therefore never be overwritten by imitation or mutation either."""
    config = SimulationConfig.level03_patches_default(
        seed=9, population_size=16, n_steps=40, imitation_period=5,
        ecological_policy_randomized_each_step=True, ecological_mutation_rate=0.5,
    )
    result = Simulation(config).run()
    assert result.event_log.ecological_imitations == []
    assert result.event_log.ecological_mutations == []


# ---------------------------------------------------------------------
# Exact Level-0.2 compatibility (global_pool topology is an untouched
# structural no-op)
# ---------------------------------------------------------------------

def test_global_pool_topology_never_constructs_a_patch_system():
    config = SimulationConfig(population_size=20, n_steps=15, seed=0)
    sim = Simulation(config)
    assert sim.patch_system is None
    result = sim.run()
    assert result.final_patch_system is None


def test_global_pool_topology_agents_keep_inert_ecological_defaults():
    config = SimulationConfig(population_size=10, n_steps=10, seed=0)
    result = Simulation(config).run()
    for agent in result.final_agents:
        assert agent.ecological_policy == EcologicalPolicy(0.0, 0.0, 0.0)
        assert agent.patch_id is None
        assert agent.ecological_cumulative_gain == 0.0


def test_global_pool_topology_logs_no_ecological_events_at_all():
    config = SimulationConfig(population_size=16, n_steps=40, seed=0, imitation_period=5, mutation_rate=0.2)
    result = Simulation(config).run()
    assert result.event_log.ecological_actions == []
    assert result.event_log.ecological_imitations == []
    assert result.event_log.ecological_mutations == []


def test_level02_compat_preset_is_exact_level0_pool_topology():
    config = SimulationConfig.level02_compat(seed=0, population_size=10, n_steps=5)
    assert config.ecology_topology == "global_pool"
    sim = Simulation(config)
    assert sim.patch_system is None


def test_full_suite_rng_draw_sequence_unaffected_by_ecology_topology_default():
    """A global_pool run must be bit-for-bit identical to a run of the
    exact same config with the new ecology_topology field simply omitted
    (i.e. left at its default) -- there is nothing for the field itself to
    change if unset."""
    a = Simulation(SimulationConfig(population_size=12, n_steps=20, seed=5)).run()
    b = Simulation(SimulationConfig(population_size=12, n_steps=20, seed=5, ecology_topology="global_pool")).run()
    assert a.metrics == b.metrics


# ---------------------------------------------------------------------
# Deterministic replay under the patches topology
# ---------------------------------------------------------------------

def test_patches_topology_same_seed_is_bit_for_bit_identical():
    def _run():
        config = SimulationConfig.level03_patches_default(seed=11, population_size=20, n_steps=40, imitation_period=5)
        return Simulation(config).run()

    a, b = _run(), _run()
    assert _metrics_equal_nan_safe(a.metrics, b.metrics)
    assert [e.actual_extraction for e in a.event_log.ecological_actions] == [
        e.actual_extraction for e in b.event_log.ecological_actions
    ]
    assert a.final_patch_system.total_resources == pytest.approx(b.final_patch_system.total_resources)


def test_patches_topology_different_seeds_diverge():
    def _run(seed):
        config = SimulationConfig.level03_patches_default(seed=seed, population_size=20, n_steps=40, imitation_period=5)
        return Simulation(config).run()

    a, b = _run(1), _run(2)
    assert not _metrics_equal_nan_safe(a.metrics, b.metrics)


# ---------------------------------------------------------------------
# Structural prohibition of governance terminology in the new Level 0.3
# code (extends tests/test_invariants.py's existing Agent-level guard).
# ---------------------------------------------------------------------

#: Level 1.3, Work Package D (Section 9): "legitimacy" graduates, as of
#: this milestone, from an absolutely-forbidden substring to a sanctioned,
#: opt-in, CONFIG/MECHANISM-level concept -- Section 9's own title is
#: "dual legitimacy channels," and Section 22 requires a document
#: literally named for it. This is a deliberate, disclosed exception
#: (see dev_mem/project_vision.md §5's own amendment), narrowly scoped:
#: it applies ONLY to this SimulationConfig-field check. The deeper,
#: AGENT-level ban is untouched and still runtime-enforced by
#: Agent.__post_init__ (see test_agent_level_legitimacy_ban_is_
#: unaffected_by_the_config_level_exception below) -- legitimacy remains
#: an institution/rule-level ledger, never an agent's own intrinsic
#: trait or political identity (project_vision.md §7).
_LEVEL13_CONFIG_LEVEL_EXCEPTIONS = ("legitimacy",)


def test_new_config_fields_never_use_a_forbidden_substring():
    import dataclasses

    remaining_forbidden = tuple(
        s for s in FORBIDDEN_ATTRIBUTE_SUBSTRINGS if s not in _LEVEL13_CONFIG_LEVEL_EXCEPTIONS
    )
    for f in dataclasses.fields(SimulationConfig):
        lowered = f.name.lower()
        assert not any(bad in lowered for bad in remaining_forbidden), f.name


def test_agent_level_legitimacy_ban_is_unaffected_by_the_config_level_exception():
    """Positive control: the Level 1.3 config-level exception above must
    NOT weaken Agent's own runtime guard -- an Agent attribute literally
    named with "legitimacy" must still raise ValueError, exactly as
    tests/test_memory.py already asserts "legitimacy" remains in
    FORBIDDEN_ATTRIBUTE_SUBSTRINGS itself (that list is untouched; only
    this one config-field test carves out a narrow, explicit exception).
    Builds an ordinarily-valid Agent, then poisons it and re-runs
    __post_init__ directly -- avoids hand-duplicating Agent's full
    (and evolving) constructor argument list."""
    agent = Agent(
        agent_id=0, resources=1.0, coercive_capability=0.0, policy=make_policy("always_cooperate"),
        observation_accuracy=1.0, learning_rate=0.1, forgiveness=0.0, risk_sensitivity=0.0, exit_cost=0.0,
    )
    agent.legitimacy_perception = 0.0
    with pytest.raises(ValueError):
        agent.__post_init__()


def test_new_event_types_never_use_a_forbidden_substring():
    import dataclasses

    for event_cls in (EcologicalActionEvent, EcologicalImitationEvent, EcologicalMutationEvent):
        for f in dataclasses.fields(event_cls):
            lowered = f.name.lower()
            assert not any(bad in lowered for bad in FORBIDDEN_ATTRIBUTE_SUBSTRINGS), f"{event_cls.__name__}.{f.name}"


def test_valid_mode_string_literals_never_use_a_forbidden_substring():
    from abm_governance.core.config import (
        VALID_ECOLOGICAL_ALLOCATION_RULES,
        VALID_ECOLOGICAL_INHERITANCE_MODES,
        VALID_ECOLOGY_TOPOLOGIES,
        VALID_PATCH_ASSIGNMENT_MODES,
    )

    for group in (
        VALID_ECOLOGICAL_ALLOCATION_RULES,
        VALID_ECOLOGICAL_INHERITANCE_MODES,
        VALID_ECOLOGY_TOPOLOGIES,
        VALID_PATCH_ASSIGNMENT_MODES,
    ):
        for value in group:
            lowered = value.lower()
            assert not any(bad in lowered for bad in FORBIDDEN_ATTRIBUTE_SUBSTRINGS), value
