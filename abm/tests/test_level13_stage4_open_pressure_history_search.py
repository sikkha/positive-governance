"""Level 1.3, Stage 4 (task #99): open pressure-history search (LHS)
(``experiments/level13_stage4_open_pressure_history_search.py``).

Runs the stage's own machinery at small scale to confirm mechanics --
the actual 96-run, session-budget-scale run and its ``outputs/
level13_stage4_open_pressure_history_search/records.json`` record are
produced by running the script directly."""

from __future__ import annotations

import importlib
import inspect

from experiments import level13_stage4_open_pressure_history_search as stage4
from tests.test_level12_structural_guards import _strip_docstrings_and_comments
from tests.test_level13_sem_firewall_extension import FORBIDDEN_LEVEL13_TERMS


class TestParameterSpace:
    def test_nine_dimensions(self):
        assert len(stage4._PARAMETER_SPACE) == 9

    def test_three_fields_per_channel(self):
        for channel in stage4._CHANNELS:
            fields = [f for f, _, _ in stage4._PARAMETER_SPACE if f.startswith(channel)]
            assert len(fields) == 3
            assert f"{channel}_onset_step" in fields
            assert f"{channel}_high_level" in fields
            assert f"{channel}_duration_steps" in fields


class TestLhsDraws:
    def test_correct_count_and_fields(self):
        draws = stage4.lhs_draws(n=10, seed=1)
        assert len(draws) == 10
        field_names = {name for name, _, _ in stage4._PARAMETER_SPACE}
        for draw in draws:
            assert set(draw.keys()) == field_names

    def test_deterministic_given_same_seed(self):
        d1 = stage4.lhs_draws(n=8, seed=42)
        d2 = stage4.lhs_draws(n=8, seed=42)
        assert d1 == d2

    def test_values_within_bounds(self):
        draws = stage4.lhs_draws(n=20, seed=3)
        bounds = {name: (lo, hi) for name, lo, hi in stage4._PARAMETER_SPACE}
        for draw in draws:
            for field, value in draw.items():
                lo, hi = bounds[field]
                assert lo <= value <= hi


class TestBuildConfig:
    def test_every_channel_enabled_and_entrenchment_legitimacy_on(self):
        draws = stage4.lhs_draws(n=1, seed=1)
        config = stage4._build_config(draws[0], seed=1)
        for channel in stage4._CHANNELS:
            assert getattr(config, f"{channel}_enabled") is True
            assert getattr(config, f"{channel}_history_kind") == "early_pulse"
        assert config.entrenchment_enabled is True
        assert config.performance_legitimacy_enabled is True
        assert config.procedural_legitimacy_enabled is True


class TestRunOne:
    def test_returns_expected_shape(self):
        draws = stage4.lhs_draws(n=1, seed=1)
        record = stage4._run_one(0, draws[0], seed=1)
        assert set(record.keys()) == {"seed", "point_id", "draw", "sequencing_vector", "phenotype_vector"}
        assert len(record["sequencing_vector"]) == 8
        assert len(record["phenotype_vector"]) == 14


class TestRunAtSmallScale:
    def test_small_scale_run_produces_correct_run_count(self):
        report = stage4.run(n_points=3, n_seeds_per_point=1)
        assert report["n_runs"] == 3
        assert report["n_points"] == 3

    def test_write_report_persists_to_disk(self, tmp_path):
        out_dir = str(tmp_path / "stage4")
        report = stage4.write_report(out_dir=out_dir, n_points=2, n_seeds_per_point=1)
        assert "report_hash" in report
        assert (tmp_path / "stage4" / "records.json").exists()


class TestReportHash:
    def test_stable_across_key_order(self):
        assert stage4.report_hash({"a": 1, "b": 2}) == stage4.report_hash({"b": 2, "a": 1})

    def test_changes_with_content(self):
        assert stage4.report_hash({"a": 1}) != stage4.report_hash({"a": 2})


class TestForbiddenTerminologyGuardExtendsToStage4Script:
    def test_stage4_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level13_stage4_open_pressure_history_search")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL13_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
