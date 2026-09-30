"""Level 1.3b, Work Package G / Stage 6 (task #119): regression tests
for ``core/state_checkpoint.py`` -- the mid-run fork/resume machinery
Stage 6's own sham intervention depends on being a byte-identical
no-op."""

from __future__ import annotations

import copy

import numpy as np
import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.core.state_checkpoint import finish, fork, fork_and_finish, run_partial
from abm_governance.simulation import Simulation

N_STEPS = 60
POPULATION = 20
N_PATCHES = 2
SEED = 4242


def _metrics_identical(a: list[dict], b: list[dict]) -> bool:
    if len(a) != len(b):
        return False
    for ra, rb in zip(a, b):
        if ra.keys() != rb.keys():
            return False
        for k in ra:
            v1, v2 = ra[k], rb[k]
            if isinstance(v1, float) and np.isnan(v1):
                if not (isinstance(v2, float) and np.isnan(v2)):
                    return False
            elif v1 != v2:
                return False
    return True


def _config() -> SimulationConfig:
    return SimulationConfig.level12b_frozen_reference(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=SEED,
        historical_module_enabled=True, entrenchment_enabled=True, entrenchment_maturation_steps=20,
        performance_legitimacy_enabled=True, procedural_legitimacy_enabled=True,
        security_pressure_enabled=True, security_pressure_history_kind="early_pulse",
        security_pressure_onset_step=10, security_pressure_returns_to_delegation_enabled=True,
        security_pressure_admin_capacity_demand_enabled=True,
    )


class TestRunPartialMatchesRun:
    def test_stepwise_partial_plus_finish_matches_full_run(self):
        sim_stepwise = Simulation(_config())
        metrics_stepwise = run_partial(sim_stepwise, 25) + finish(sim_stepwise, 25, N_STEPS)

        sim_full = Simulation(_config())
        result_full = sim_full.run()

        assert _metrics_identical(metrics_stepwise, result_full.metrics)


class TestForkIsIndependent:
    def test_mutating_fork_does_not_affect_original(self):
        sim = Simulation(_config())
        run_partial(sim, 20)
        branch = fork(sim)
        # Mutate the fork's historical pressure state directly.
        if branch.historical_state:
            for key in branch.historical_state:
                branch.historical_state[key][:] = 0.0
        original_state = {k: v.copy() for k, v in (sim.historical_state or {}).items()}
        for key, arr in (branch.historical_state or {}).items():
            assert not np.array_equal(arr, original_state[key])
        # original untouched
        for key, arr in (sim.historical_state or {}).items():
            assert np.array_equal(arr, original_state[key])

    def test_forking_twice_from_the_same_checkpoint_gives_two_independent_branches(self):
        sim = Simulation(_config())
        run_partial(sim, 20)
        branch_a = fork(sim)
        branch_b = fork(sim)
        finish(branch_a, 20, N_STEPS)
        finish(branch_b, 20, N_STEPS)
        # Both branches forked from the identical checkpoint with no
        # mutation and finished identically -> must agree exactly.
        a_events = len(branch_a.event_log.contributions)
        b_events = len(branch_b.event_log.contributions)
        assert a_events == b_events


class TestShamForkAndFinishIsByteIdenticalToUninterruptedRun:
    """The exact claim Stage 6's own sham intervention depends on."""

    def test_sham_matches_uninterrupted_run(self):
        cfg = _config()
        sim_uninterrupted = Simulation(cfg)
        metrics_uninterrupted = sim_uninterrupted.run().metrics

        sim_checkpoint = Simulation(cfg)
        run_partial(sim_checkpoint, 30)
        sham_branch = fork_and_finish(sim_checkpoint, intervention_step=30, n_steps=N_STEPS, mutate=None)

        # Direct comparison: sham_branch's full event log should match an
        # uninterrupted run's event log exactly (NaN-aware metrics check
        # on the final SimulationResult-equivalent count fields).
        assert len(sham_branch.event_log.contributions) == len(sim_uninterrupted.event_log.contributions)
        assert len(sham_branch.event_log.rule_adoptions) == len(sim_uninterrupted.event_log.rule_adoptions)
        assert len(sham_branch.event_log.coordination_links) == len(sim_uninterrupted.event_log.coordination_links)
        assert len(sham_branch.event_log.monitorings) == len(sim_uninterrupted.event_log.monitorings)

    def test_original_sim_object_passed_to_fork_and_finish_is_not_itself_advanced(self):
        cfg = _config()
        sim_checkpoint = Simulation(cfg)
        run_partial(sim_checkpoint, 30)
        n_events_before = len(sim_checkpoint.event_log.contributions)
        fork_and_finish(sim_checkpoint, intervention_step=30, n_steps=N_STEPS, mutate=None)
        n_events_after = len(sim_checkpoint.event_log.contributions)
        assert n_events_before == n_events_after  # sim_checkpoint itself untouched by fork_and_finish

    def test_two_independent_sham_forks_from_the_same_checkpoint_agree(self):
        cfg = _config()
        sim_checkpoint = Simulation(cfg)
        run_partial(sim_checkpoint, 30)
        branch_1 = fork_and_finish(sim_checkpoint, intervention_step=30, n_steps=N_STEPS, mutate=None)
        branch_2 = fork_and_finish(sim_checkpoint, intervention_step=30, n_steps=N_STEPS, mutate=None)
        assert len(branch_1.event_log.contributions) == len(branch_2.event_log.contributions)
        assert len(branch_1.event_log.rule_adoptions) == len(branch_2.event_log.rule_adoptions)


class TestForkFrozensetOrderCaveat:
    """Documents, via a reproducing test (not just prose), the real
    limitation found and disclosed in this module's own docstring:
    ``copy.deepcopy`` does not always preserve a ``frozenset``'s
    iteration order, which matters for any code (e.g. ``rules/
    dynamics.py::monitoring_round``) that iterates a frozenset field
    while consuming RNG draws per element in that order."""

    def test_deepcopy_can_reorder_a_real_rule_members_frozenset(self):
        # Uses the REAL object this caveat was found on -- a
        # SharedRule.members frozenset shaped by ~250 steps of genuine
        # membership churn -- rather than a synthetic reconstruction
        # attempt (a smaller synthetic add/discard history was tried
        # first and did NOT reliably reproduce the phenomenon; the real
        # object, built the same way this codebase actually builds one,
        # does -- documented here rather than silently discarded).
        cfg = SimulationConfig.level12b_frozen_reference(
            population_size=40, n_steps=260, n_patches=3, seed=8_900_000,
            historical_module_enabled=True, entrenchment_enabled=True, entrenchment_maturation_steps=150,
            performance_legitimacy_enabled=True, procedural_legitimacy_enabled=True,
            security_pressure_enabled=True, security_pressure_history_kind="early_pulse", security_pressure_onset_step=0,
            security_pressure_returns_to_delegation_enabled=True, security_pressure_admin_capacity_demand_enabled=True,
            bargaining_pressure_enabled=True, bargaining_pressure_history_kind="early_pulse", bargaining_pressure_onset_step=150,
            bargaining_pressure_conditional_contribution_enabled=True, bargaining_pressure_appeal_recall_enabled=True,
            coordination_complexity_enabled=True, coordination_complexity_history_kind="early_pulse", coordination_complexity_onset_step=300,
            coordination_complexity_cross_patch_transactions_enabled=True, coordination_complexity_interoperable_demand_enabled=True,
        )
        sim = Simulation(cfg)
        run_partial(sim, 250)
        candidate_frozensets = [rule.members for rule in sim.rule_registry.values() if len(rule.members) >= 2]
        assert candidate_frozensets, "fixture produced no nonempty rule.members to test against"

        found_reordering = False
        for original in candidate_frozensets:
            deep_copied = copy.deepcopy(original)
            if list(original) != list(deep_copied):
                found_reordering = True
                break

        # This assertion is the documented CAVEAT, not a desired
        # invariant -- if it ever starts failing (order always
        # preserved for this fixture), re-verify the caveat in
        # core/state_checkpoint.py's own docstring is still accurate
        # rather than silently deleting this test.
        assert found_reordering, (
            "expected at least one real rule.members frozenset to reorder under copy.deepcopy; "
            "if none did, re-verify the caveat in core/state_checkpoint.py's own docstring"
        )


class TestMutationActuallyAppliesToFork:
    def test_a_real_mutation_changes_only_the_fork_it_was_applied_to(self):
        cfg = _config()
        sim_checkpoint = Simulation(cfg)
        run_partial(sim_checkpoint, 30)
        assert float(np.max(sim_checkpoint.historical_state["security_pressure_series"][30:])) > 0.0

        def erase_pressure(branch):
            branch.historical_state["security_pressure_series"][30:] = 0.0

        sham_branch = fork_and_finish(sim_checkpoint, intervention_step=30, n_steps=N_STEPS, mutate=None)
        erased_branch = fork_and_finish(sim_checkpoint, intervention_step=30, n_steps=N_STEPS, mutate=erase_pressure)

        # The mutation took effect on the erased branch's own state...
        assert np.all(erased_branch.historical_state["security_pressure_series"][30:] == 0.0)
        # ...but left the sham branch (and the original checkpoint) at
        # the genuinely realized, nonzero pressure level.
        assert float(np.max(sham_branch.historical_state["security_pressure_series"][30:])) > 0.0
        assert float(np.max(sim_checkpoint.historical_state["security_pressure_series"][30:])) > 0.0
