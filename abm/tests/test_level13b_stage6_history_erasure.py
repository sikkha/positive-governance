"""Level 1.3b, Stage 6 (task #119): tests for ``experiments/level13b_
stage6_history_erasure.py``. Small-scale mechanics only (1 real seed's
worth of all 6 interventions) -- the real 72-run archived result lives
in ``outputs/level13b_stage6_history_erasure/records.json``, produced
by running the script directly.

The single most important thing this file checks: the sham machinery
validation (``no_intervention_control`` must byte-for-byte match
``sham_identical_state_copy``) -- this is the exact regression this
stage's own module docstring discloses finding and fixing a genuine
``copy.deepcopy``/``frozenset``-iteration-order bug in, so this check
is not a formality."""

from __future__ import annotations

from experiments import level13b_stage6_history_erasure as stage6


def _eco_points():
    return stage6._load_ecological_points()


class TestConfig:
    def test_config_uses_representative_cell(self):
        eco_points = _eco_points()
        config = stage6._config(stage6.SEED_BASE, eco_points)
        assert config.historical_module_enabled is True
        assert config.entrenchment_enabled is True


class TestMutators:
    def test_five_named_mutator_slots_including_sham_none(self):
        assert set(stage6._MUTATORS.keys()) == set(stage6.INTERVENTIONS) - {"no_intervention_control"}
        assert stage6._MUTATORS["sham_identical_state_copy"] is None

    def test_pressure_memory_mutator_flattens_series_from_intervention_step(self):
        from abm_governance.simulation import Simulation
        from abm_governance.core.state_checkpoint import run_partial

        eco_points = _eco_points()
        config = stage6._config(stage6.SEED_BASE, eco_points)
        branch = Simulation(config)
        run_partial(branch, stage6.INTERVENTION_STEP)
        stage6._mutate_pressure_memory(branch)
        for channel in stage6.CHANNELS:
            key = f"{channel}_series"
            if branch.historical_state and key in branch.historical_state:
                tail = branch.historical_state[key][stage6.INTERVENTION_STEP:]
                assert all(v == stage6.LOW_LEVEL for v in tail)

    def test_legitimacy_mutator_zeroes_active_rule_ledgers(self):
        from abm_governance.simulation import Simulation
        from abm_governance.core.state_checkpoint import run_partial

        eco_points = _eco_points()
        config = stage6._config(stage6.SEED_BASE, eco_points)
        branch = Simulation(config)
        run_partial(branch, stage6.INTERVENTION_STEP)
        stage6._mutate_legitimacy_history(branch)
        for rule in branch.rule_registry.values():
            if rule.active:
                assert rule.performance_legitimacy == 0.0
                assert rule.procedural_legitimacy == 0.0

    def test_entrenchment_mutator_resets_founding_step(self):
        from abm_governance.simulation import Simulation
        from abm_governance.core.state_checkpoint import run_partial

        eco_points = _eco_points()
        config = stage6._config(stage6.SEED_BASE, eco_points)
        branch = Simulation(config)
        run_partial(branch, stage6.INTERVENTION_STEP)
        stage6._mutate_entrenchment(branch)
        for rule in branch.rule_registry.values():
            if rule.active:
                assert rule.founding_step == stage6.INTERVENTION_STEP


class TestRunOneSeedAndSmokeTest:
    def test_run_one_seed_returns_all_six_interventions(self):
        eco_points = _eco_points()
        record = stage6._run_one_seed((stage6.SEED_BASE, eco_points))
        assert set(record.keys()) == {"seed"} | set(stage6.INTERVENTIONS)
        for name in stage6.INTERVENTIONS:
            assert len(record[name]["S_obs_series"]) == stage6.N_STEPS

    def test_smoke_test_passes(self):
        eco_points = _eco_points()
        assert stage6.run_smoke_test(eco_points) is True


class TestAnalyzeShamValidation:
    def test_sham_matches_control_exactly_on_a_real_seed(self):
        """The core regression guard: reproduces this stage's own
        original bug-detection path at small scale. If a future change
        reintroduces any deepcopy/fork-based branching for the sham
        intervention, this test is expected to catch it exactly the way
        Stage 6's own smoke check first did."""
        eco_points = _eco_points()
        record = stage6._run_one_seed((stage6.SEED_BASE, eco_points))
        analysis = stage6.analyze([record])
        assert analysis["sham_validation"]["sham_machinery_validated"] is True
        assert analysis["sham_validation"]["n_sham_matches_control_exactly"] == 1

    def test_divergence_by_intervention_covers_all_four_real_interventions(self):
        eco_points = _eco_points()
        record = stage6._run_one_seed((stage6.SEED_BASE, eco_points))
        analysis = stage6.analyze([record])
        assert set(analysis["divergence_by_intervention_vs_no_intervention_control"].keys()) == {
            "pressure_memory_only", "legitimacy_history_only", "entrenchment_only", "all_history",
        }
