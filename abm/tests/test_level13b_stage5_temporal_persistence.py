"""Level 1.3b, Stage 5 (task #118): tests for ``experiments/level13b_
stage5_temporal_persistence.py``. Small-scale mechanics only (1-2 real
runs) -- the real 80-run archived result lives in ``outputs/level13b_
stage5_temporal_persistence/records.json``, produced by running the
script directly."""

from __future__ import annotations

from experiments import level13b_stage5_temporal_persistence as stage5


def _eco_points():
    return stage5._load_ecological_points()


class TestBaseConfigAndRunBase:
    def test_base_config_assigns_representative_cell_overrides(self):
        eco_points = _eco_points()
        config = stage5._base_config("security_first", 1, eco_points)
        assert config.entrenchment_maturation_steps == 150  # "moderate" entrenchment override, frozen
        assert config.entrenchment_enabled is True
        assert config.performance_legitimacy_enabled is True
        assert config.procedural_legitimacy_enabled is True

    def test_run_base_keys_realized_pressure_series_by_state_key_not_bare_channel(self):
        """Regression guard for this stage's own disclosed bug: dict
        keys must be '{channel}_series', never the bare channel name --
        Simulation.__init__ matches historical_pressure_series_override
        against state_key, not the channel prefix."""
        eco_points = _eco_points()
        base = stage5._run_base("security_first", stage5.SEED_BASE, eco_points)
        assert set(base["realized_pressure_series"].keys()) == {f"{ch}_series" for ch in stage5.CHANNELS}
        for ch in stage5.CHANNELS:
            assert ch not in base["realized_pressure_series"]
        assert len(base["S_obs_series"]) == stage5.N_STEPS
        assert len(base["Z_obs_series"]) == stage5.N_STEPS


class TestRunCounterfactual:
    def test_each_transform_produces_a_full_length_series(self):
        eco_points = _eco_points()
        base = stage5._run_base("security_first", stage5.SEED_BASE, eco_points)
        for variant in stage5._TRANSFORMS:
            cf = stage5._run_counterfactual(stage5.SEED_BASE, variant, base, eco_points)
            assert len(cf["S_obs_series"]) == stage5.N_STEPS
            assert cf["variant"] == variant


class TestRunSmokeTest:
    def test_smoke_test_passes(self):
        eco_points = _eco_points()
        assert stage5.run_smoke_test(eco_points) is True


class TestAnalyze:
    def test_analyze_on_a_minimal_two_seed_pool(self):
        eco_points = _eco_points()
        part_a = [
            stage5._run_base(ordering, stage5.SEED_BASE + i, eco_points)
            for ordering in ("security_first", "coevolution")
            for i in range(2)
        ]
        base_by_seed = {r["seed"]: r for r in part_a if r["ordering"] == "security_first"}
        part_b = [
            stage5._run_counterfactual(seed, variant, base_by_seed[seed], eco_points)
            for seed in base_by_seed
            for variant in stage5._TRANSFORMS
        ]
        analysis = stage5.analyze({"part_a": part_a, "part_b": part_b})
        assert analysis["n_part_a_runs"] == 4
        assert analysis["n_part_b_runs"] == 2 * len(stage5._TRANSFORMS)
        assert len(analysis["per_seed_ordering_persistence"]) == 2
        assert set(analysis["counterfactual_persistence_by_variant"].keys()) == set(stage5._TRANSFORMS.keys())


class TestBaseBySeedLookup:
    def test_finds_the_security_first_record_for_a_given_seed(self):
        eco_points = _eco_points()
        part_a = [stage5._run_base("security_first", stage5.SEED_BASE, eco_points)]
        found = stage5.base_by_seed_lookup(part_a, stage5.SEED_BASE)
        assert found["seed"] == stage5.SEED_BASE
