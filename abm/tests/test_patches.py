"""Level 0.3, Work Package A: local ecological patches — exact per-patch
accounting, bounded regeneration, neutral assignment, and the pure
allocation function shared between the endogenous-feedback path and the
Work-Package-F "no environmental effect" counterfactual."""

from __future__ import annotations

import networkx as nx
import numpy as np
import pytest

from abm_governance.environment.patches import (
    PatchSystem,
    ResourcePatch,
    _assign_network_neighborhood,
    _assign_random,
    allocate_extraction,
    build_patch_system,
)


# -- allocate_extraction: pure function -------------------------------------

def test_allocate_extraction_grants_full_request_when_available_is_sufficient():
    got = allocate_extraction(available=100.0, requested={1: 10.0, 2: 20.0}, rule="proportional")
    assert got == {1: 10.0, 2: 20.0}


def test_allocate_extraction_proportional_scales_down_exactly_under_excess_demand():
    # available=10, requested {1:6, 2:8} sum=14 > 10 -> scale = 10/14
    got = allocate_extraction(available=10.0, requested={1: 6.0, 2: 8.0}, rule="proportional")
    assert got[1] == pytest.approx(6.0 * 10.0 / 14.0)
    assert got[2] == pytest.approx(8.0 * 10.0 / 14.0)
    assert sum(got.values()) == pytest.approx(10.0)


def test_allocate_extraction_proportional_is_deterministic_and_order_independent():
    a = allocate_extraction(available=5.0, requested={1: 3.0, 2: 3.0, 3: 3.0}, rule="proportional")
    b = allocate_extraction(available=5.0, requested={3: 3.0, 1: 3.0, 2: 3.0}, rule="proportional")
    assert a == b


def test_allocate_extraction_sequential_random_never_exceeds_available():
    rng = np.random.default_rng(0)
    requested = {i: 4.0 for i in range(10)}  # sum=40, available=15
    got = allocate_extraction(available=15.0, requested=requested, rule="sequential_random", rng=rng)
    assert sum(got.values()) == pytest.approx(15.0)
    assert all(0.0 <= v <= 4.0 for v in got.values())


def test_allocate_extraction_sequential_random_requires_rng():
    with pytest.raises(ValueError):
        allocate_extraction(available=5.0, requested={1: 10.0}, rule="sequential_random")


def test_allocate_extraction_zero_total_requested_returns_all_zero():
    got = allocate_extraction(available=10.0, requested={1: 0.0, 2: 0.0}, rule="proportional")
    assert got == {1: 0.0, 2: 0.0}


def test_allocate_extraction_unknown_rule_raises():
    # Rule validity is only checked once rationing is actually required
    # (sufficient supply needs no rule at all -- see the function's
    # early-return branch above) so this must oversubscribe demand to
    # actually exercise the unknown-rule branch.
    with pytest.raises(ValueError):
        allocate_extraction(available=1.0, requested={1: 5.0}, rule="not_a_rule")


def test_allocate_extraction_negative_available_treated_as_zero():
    got = allocate_extraction(available=-5.0, requested={1: 10.0}, rule="proportional")
    assert got == {1: 0.0}


# -- ResourcePatch: construction and bounds ---------------------------------

def test_patch_rejects_invalid_construction():
    with pytest.raises(ValueError):
        ResourcePatch(patch_id=0, capacity=0.0, regen_rate=0.5)
    with pytest.raises(ValueError):
        ResourcePatch(patch_id=0, capacity=100.0, regen_rate=-0.1)
    with pytest.raises(ValueError):
        ResourcePatch(patch_id=0, capacity=100.0, regen_rate=0.5, resources=150.0)
    with pytest.raises(ValueError):
        ResourcePatch(patch_id=0, capacity=100.0, regen_rate=0.5, quality=0.0)


def test_patch_bounds_hold_after_every_operation():
    patch = ResourcePatch(patch_id=0, capacity=50.0, regen_rate=1.5, resources=25.0)
    rng = np.random.default_rng(0)
    for _ in range(200):
        op = rng.choice(["extract", "request", "maintain", "regen"])
        if op == "extract":
            patch.extract(float(rng.uniform(0, 100)))
        elif op == "request":
            n = int(rng.integers(1, 5))
            patch.request_extraction({i: float(rng.uniform(0, 40)) for i in range(n)}, "proportional", rng)
        elif op == "maintain":
            n = int(rng.integers(1, 5))
            patch.apply_maintenance({i: float(rng.uniform(0, 40)) for i in range(n)}, efficiency=0.6)
        else:
            patch.regenerate()
        assert 0.0 <= patch.resources <= patch.capacity


def test_patch_extract_is_capped_and_recorded_by_category():
    patch = ResourcePatch(patch_id=0, capacity=100.0, regen_rate=0.0, resources=10.0)
    got = patch.extract(50.0, category="game")
    assert got == pytest.approx(10.0)
    assert patch.resources == pytest.approx(0.0)
    assert patch.cumulative_extraction == pytest.approx(10.0)
    assert patch.cumulative_game_extraction == pytest.approx(10.0)
    assert patch.cumulative_ecological_extraction == pytest.approx(0.0)


def test_patch_extract_non_game_category_is_recorded_as_ecological():
    patch = ResourcePatch(patch_id=0, capacity=100.0, regen_rate=0.0, resources=10.0)
    got = patch.extract(4.0, category="ecological")
    assert got == pytest.approx(4.0)
    assert patch.cumulative_game_extraction == pytest.approx(0.0)
    assert patch.cumulative_ecological_extraction == pytest.approx(4.0)


def test_patch_request_extraction_records_unmet_demand():
    patch = ResourcePatch(patch_id=0, capacity=100.0, regen_rate=0.0, resources=10.0)
    actual = patch.request_extraction({1: 6.0, 2: 8.0}, rule="proportional")
    assert sum(actual.values()) == pytest.approx(10.0)
    assert patch.resources == pytest.approx(0.0)
    assert patch.cumulative_ecological_extraction == pytest.approx(10.0)
    assert patch.cumulative_unmet_extraction_demand == pytest.approx(14.0 - 10.0)


def test_patch_apply_maintenance_matches_hand_computed_case():
    # investment sums to 10, efficiency=0.5 -> effective=5, headroom=100-90=10
    patch = ResourcePatch(patch_id=0, capacity=100.0, regen_rate=0.0, resources=90.0)
    added = patch.apply_maintenance({1: 4.0, 2: 6.0}, efficiency=0.5)
    assert added == pytest.approx(5.0)
    assert patch.resources == pytest.approx(95.0)
    assert patch.cumulative_maintenance_invested == pytest.approx(10.0)
    assert patch.cumulative_maintenance_effective == pytest.approx(5.0)


def test_patch_apply_maintenance_is_capped_by_headroom_not_by_investment():
    # investment sums to 40, efficiency=1.0 -> nominal effective=40, but
    # headroom is only 100-90=10.
    patch = ResourcePatch(patch_id=0, capacity=100.0, regen_rate=0.0, resources=90.0)
    added = patch.apply_maintenance({1: 40.0}, efficiency=1.0)
    assert added == pytest.approx(10.0)
    assert patch.resources == pytest.approx(100.0)
    assert patch.cumulative_maintenance_effective == pytest.approx(10.0)


def test_patch_regenerate_matches_hand_computed_logistic_step():
    patch = ResourcePatch(patch_id=0, capacity=200.0, regen_rate=0.5, resources=50.0)
    added = patch.regenerate()
    assert added == pytest.approx(18.75)
    assert patch.resources == pytest.approx(68.75)
    assert patch.cumulative_regeneration == pytest.approx(18.75)


def test_patch_regenerate_scaled_by_quality():
    # quality=2.0 doubles the effective regen rate.
    patch = ResourcePatch(patch_id=0, capacity=200.0, regen_rate=0.25, quality=2.0, resources=50.0)
    added = patch.regenerate()
    assert added == pytest.approx(18.75)  # same as regen_rate=0.5, quality=1.0 above


def test_patch_fraction_of_capacity():
    patch = ResourcePatch(patch_id=0, capacity=200.0, regen_rate=0.1, resources=50.0)
    assert patch.fraction_of_capacity == pytest.approx(0.25)


# -- PatchSystem aggregate properties ----------------------------------------

def test_patch_system_aggregate_properties():
    p0 = ResourcePatch(patch_id=0, capacity=100.0, regen_rate=0.1, resources=50.0, members=frozenset({1}))
    p1 = ResourcePatch(patch_id=1, capacity=200.0, regen_rate=0.1, resources=100.0, members=frozenset({2}))
    system = PatchSystem(patches={0: p0, 1: p1}, agent_patch={1: 0, 2: 1})
    assert system.total_resources == pytest.approx(150.0)
    assert system.total_capacity == pytest.approx(300.0)
    assert system.aggregate_fraction_of_capacity == pytest.approx(0.5)
    assert system.patch_of(1) is p0
    assert system.patch_of(2) is p1


# -- neutral assignment -------------------------------------------------------

def test_random_assignment_covers_every_agent_exactly_once():
    rng = np.random.default_rng(0)
    assignment = _assign_random(list(range(50)), n_patches=4, rng=rng)
    assert set(assignment.keys()) == set(range(50))
    assert all(0 <= p < 4 for p in assignment.values())


def test_network_neighborhood_assignment_covers_every_agent_exactly_once():
    graph = nx.watts_strogatz_graph(40, 4, 0.1, seed=1)
    rng = np.random.default_rng(1)
    assignment = _assign_network_neighborhood(list(graph.nodes()), n_patches=4, graph=graph, rng=rng)
    assert set(assignment.keys()) == set(graph.nodes())
    assert all(0 <= p < 4 for p in assignment.values())


def test_network_neighborhood_assignment_handles_disconnected_components():
    graph = nx.Graph()
    graph.add_nodes_from(range(10))
    graph.add_edges_from([(0, 1), (1, 2), (3, 4)])  # nodes 5..9 fully isolated
    rng = np.random.default_rng(2)
    assignment = _assign_network_neighborhood(list(graph.nodes()), n_patches=3, graph=graph, rng=rng)
    assert set(assignment.keys()) == set(graph.nodes())
    assert all(0 <= p < 3 for p in assignment.values())


def test_assignment_never_reads_agent_traits():
    """Neutrality check: both assignment functions' signatures take only
    agent_ids / graph / n_patches / rng -- no trait, policy, or resource
    argument exists for them to read, so this is a structural guarantee
    rather than a runtime behavioural one; this test pins that structural
    fact via introspection so a future refactor cannot silently add a
    trait-dependent argument without this test failing."""
    import inspect

    for fn in (_assign_random, _assign_network_neighborhood):
        params = set(inspect.signature(fn).parameters)
        assert params <= {"agent_ids", "n_patches", "rng", "graph"}


def test_build_patch_system_neutral_initial_fraction_and_quality():
    graph = nx.watts_strogatz_graph(20, 4, 0.1, seed=0)
    rng = np.random.default_rng(0)
    system = build_patch_system(
        agent_ids=list(graph.nodes()),
        graph=graph,
        n_patches=4,
        capacity=500.0,
        regen_rate=0.5,
        initial_fraction=0.4,
        assignment_mode="network_neighborhood",
        quality_std=0.0,
        rng=rng,
    )
    assert len(system.patches) == 4
    for patch in system.patches.values():
        assert patch.resources == pytest.approx(500.0 * 0.4)
        assert patch.quality == pytest.approx(1.0)  # quality_std=0.0 -> neutral
    assert set(system.agent_patch.keys()) == set(graph.nodes())
    # Every agent counted as a member of exactly its assigned patch.
    for pid, patch in system.patches.items():
        assert patch.members == {aid for aid, p in system.agent_patch.items() if p == pid}


def test_network_neighborhood_assignment_with_more_patches_than_agents():
    graph = nx.watts_strogatz_graph(6, 3, 0.1, seed=0)
    rng = np.random.default_rng(0)
    assignment = _assign_network_neighborhood(list(graph.nodes()), n_patches=10, graph=graph, rng=rng)
    assert set(assignment.keys()) == set(graph.nodes())
    assert all(0 <= p < 10 for p in assignment.values())


def test_build_patch_system_random_assignment_mode():
    graph = nx.watts_strogatz_graph(20, 4, 0.1, seed=0)
    rng = np.random.default_rng(0)
    system = build_patch_system(
        agent_ids=list(graph.nodes()), graph=graph, n_patches=4, capacity=100.0, regen_rate=0.5,
        initial_fraction=0.5, assignment_mode="random_assignment", quality_std=0.0, rng=rng,
    )
    assert set(system.agent_patch.keys()) == set(graph.nodes())
    assert len(system.patches) == 4


def test_build_patch_system_nonzero_quality_std_produces_patch_quality_variation():
    graph = nx.watts_strogatz_graph(20, 4, 0.1, seed=0)
    rng = np.random.default_rng(0)
    system = build_patch_system(
        agent_ids=list(graph.nodes()), graph=graph, n_patches=6, capacity=100.0, regen_rate=0.5,
        initial_fraction=0.5, assignment_mode="network_neighborhood", quality_std=0.3, rng=rng,
    )
    qualities = [p.quality for p in system.patches.values()]
    assert all(q > 0 for q in qualities)
    assert len(set(qualities)) > 1  # not all identical, unlike quality_std=0.0


def test_build_patch_system_rejects_invalid_n_patches_and_assignment_mode():
    graph = nx.watts_strogatz_graph(10, 4, 0.1, seed=0)
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        build_patch_system(
            agent_ids=list(graph.nodes()), graph=graph, n_patches=0, capacity=10.0, regen_rate=0.1,
            initial_fraction=0.5, assignment_mode="random_assignment", quality_std=0.0, rng=rng,
        )
    with pytest.raises(ValueError):
        build_patch_system(
            agent_ids=list(graph.nodes()), graph=graph, n_patches=2, capacity=10.0, regen_rate=0.1,
            initial_fraction=0.5, assignment_mode="not_a_mode", quality_std=0.0, rng=rng,
        )
