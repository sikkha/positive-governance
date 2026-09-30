"""Level 1.3b, Stage 4 (task #117): tests for ``experiments/level13b_
stage4_homogeneous_discovery.py``. Small-scale mechanics only -- the
real 240-run archived pool lives in ``outputs/level13b_stage4_
homogeneous_discovery/records.json``, produced by running the script
directly."""

from __future__ import annotations

from experiments import level13b_stage4_homogeneous_discovery as stage4


def _eco_points():
    return stage4._load_ecological_points()


class TestParameterSpace:
    def test_eleven_dimensions_matching_frozen_manifest_order(self):
        from experiments.level13b_preregistration import STAGE4_HOMOGENEOUS_DISCOVERY
        assert [n for n, _, _ in stage4._PARAMETER_SPACE] == list(STAGE4_HOMOGENEOUS_DISCOVERY["dimensions"])
        assert len(stage4._PARAMETER_SPACE) == 11

    def test_every_bound_is_low_less_than_high(self):
        for _name, lo, hi in stage4._PARAMETER_SPACE:
            assert lo < hi


class TestLhsDraws:
    def test_lhs_draws_returns_n_dicts_with_all_dimension_keys(self):
        draws = stage4.lhs_draws(n=5, seed=1)
        assert len(draws) == 5
        names = {n for n, _, _ in stage4._PARAMETER_SPACE}
        for draw in draws:
            assert set(draw.keys()) == names

    def test_lhs_draws_is_deterministic_given_seed(self):
        a = stage4.lhs_draws(n=4, seed=42)
        b = stage4.lhs_draws(n=4, seed=42)
        assert a == b

    def test_draws_respect_declared_bounds(self):
        draws = stage4.lhs_draws(n=10, seed=7)
        for name, lo, hi in stage4._PARAMETER_SPACE:
            for draw in draws:
                assert lo <= draw[name] <= hi


class TestStratumFromDraw:
    def test_bucketing_covers_all_three_strata(self):
        assert stage4._stratum_from_draw(0.0) == "low_feasibility"
        assert stage4._stratum_from_draw(0.5) == "medium_feasibility"
        assert stage4._stratum_from_draw(0.999) == "high_feasibility"


class TestBuildConfigAndRunOne:
    def test_build_config_derives_n_shocks_and_returns_stratum(self):
        eco_points = _eco_points()
        draws = stage4.lhs_draws(n=1, seed=1)
        config, stratum, n_shocks = stage4._build_config(draws[0], seed=1, eco_points=eco_points)
        assert stratum in stage4.STRATA_ORDER
        assert n_shocks >= 1
        assert config.entrenchment_enabled is True
        for channel in stage4._CHANNELS:
            assert getattr(config, f"{channel}_history_kind") == "repeated_shocks"
            assert getattr(config, f"{channel}_n_shocks") == n_shocks

    def test_run_one_returns_expected_shape(self):
        eco_points = _eco_points()
        draws = stage4.lhs_draws(n=1, seed=stage4.LHS_SEED)
        record = stage4._run_one((0, draws[0], stage4.SEED_BASE, eco_points))
        assert "sequencing_vector" in record and "phenotype_vector" in record
        assert record["stratum"] in stage4.STRATA_ORDER
        assert "S_obs_final" in record and "Z_obs_final" in record


class TestRunSmokeTest:
    def test_smoke_test_passes(self):
        eco_points = _eco_points()
        assert stage4.run_smoke_test(eco_points) is True


class TestSummarize:
    def test_summarize_uses_the_correct_bargaining_key_no_seq_prefix(self):
        """Regression guard for the bug this stage's own docstring
        discloses: the sequencing vector's key is
        'bargaining_participation', never 'seq_bargaining_participation'
        -- summarize() must read the correct, unprefixed key."""
        eco_points = _eco_points()
        draws = stage4.lhs_draws(n=2, seed=stage4.LHS_SEED)
        records = [
            stage4._run_one((i, draw, stage4.SEED_BASE + i, eco_points))
            for i, draw in enumerate(draws)
        ]
        summary = stage4.summarize(records)
        assert summary["n_records"] == 2
        assert 0 <= summary["n_bargaining_participation_activated"] <= 2
        # Directly confirm summarize() is reading the real, unprefixed key.
        for r in records:
            assert "seq_bargaining_participation" not in r["sequencing_vector"]


class TestReportHash:
    def test_stable_across_key_order(self):
        assert stage4.report_hash({"a": 1, "b": 2}) == stage4.report_hash({"b": 2, "a": 1})

    def test_changes_with_content(self):
        assert stage4.report_hash({"a": 1}) != stage4.report_hash({"a": 2})
