"""Level 1.3, Stage 1 (task #96): unit/mechanism activation tests
(``experiments/level13_stage1_activation.py``).

Runs the stage's own machinery at a small scale (2 seeds, not the full
8-seed budget) to confirm mechanics -- the actual 8-seed, session-
budget-scale run and its ``outputs/level13_stage1_activation/
stage1_report.json`` record are produced by running the script directly."""

from __future__ import annotations

import importlib
import inspect

import pytest

from experiments import level13_stage1_activation as stage1
from tests.test_level12_structural_guards import _strip_docstrings_and_comments
from tests.test_level13_sem_firewall_extension import FORBIDDEN_LEVEL13_TERMS


class TestConditions:
    def test_seven_conditions(self):
        assert len(stage1.CONDITIONS) == 7

    def test_baseline_has_module_off(self):
        assert stage1.CONDITIONS["level13_baseline"]["historical_module_enabled"] is False

    def test_every_non_baseline_condition_has_module_on(self):
        for name, overrides in stage1.CONDITIONS.items():
            if name != "level13_baseline":
                assert overrides["historical_module_enabled"] is True


class TestRunOne:
    def test_baseline_produces_no_pressure_state(self):
        result = stage1._run_one("level13_baseline", stage1.CONDITIONS["level13_baseline"], seed=1)
        assert result["any_pressure_series_present"] is False
        assert result["n_legitimacy_events"] == 0

    def test_security_pressure_only_produces_a_well_formed_series(self):
        result = stage1._run_one(
            "level13_security_pressure_only", stage1.CONDITIONS["level13_security_pressure_only"], seed=1,
        )
        assert result["pressure_series_present"] is True
        assert result["pressure_series_well_formed"] is True

    def test_legitimacy_only_conditions_produce_events(self):
        for name in ("level13_performance_legitimacy_only", "level13_procedural_legitimacy_only"):
            result = stage1._run_one(name, stage1.CONDITIONS[name], seed=1)
            assert result["n_legitimacy_events"] > 0


class TestRunAtSmallScale:
    @pytest.fixture(autouse=True)
    def _small_scale(self, monkeypatch):
        # Only N_SEEDS is safe to shrink post-import: N_STEPS/POPULATION
        # are already baked into the module-level `_BASE` dict at import
        # time, so patching them here would silently desync `_BASE`'s
        # own `n_steps`/`population_size` from what `_run_one`'s
        # well-formedness check compares against (caught by this test
        # file's own first draft actually failing -- see git history/
        # status_update.md for this task's disclosed bug-and-fix).
        monkeypatch.setattr(stage1, "N_SEEDS", 2)

    def test_run_produces_a_check_for_every_condition(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stage1, "OUT_DIR", str(tmp_path / "stage1"))
        report = stage1.run()
        assert set(report["conditions"].keys()) == set(stage1.CONDITIONS.keys())

    def test_baseline_checks_pass_at_small_scale(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stage1, "OUT_DIR", str(tmp_path / "stage1"))
        report = stage1.run()
        baseline_checks = report["conditions"]["level13_baseline"]["checks"]
        assert baseline_checks["no_pressure_state_generated"] is True
        assert baseline_checks["no_legitimacy_events"] is True

    def test_pressure_channel_checks_pass_at_small_scale(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stage1, "OUT_DIR", str(tmp_path / "stage1"))
        report = stage1.run()
        for name in stage1._PRESSURE_STATE_KEY:
            checks = report["conditions"][name]["checks"]
            assert checks["pressure_series_present_every_seed"] is True
            assert checks["pressure_series_well_formed_every_seed"] is True

    def test_legitimacy_checks_pass_at_small_scale(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stage1, "OUT_DIR", str(tmp_path / "stage1"))
        report = stage1.run()
        for name in ("level13_performance_legitimacy_only", "level13_procedural_legitimacy_only"):
            checks = report["conditions"][name]["checks"]
            assert checks["legitimacy_events_present_every_seed"] is True

    def test_report_written_to_disk(self, tmp_path, monkeypatch):
        out_dir = str(tmp_path / "stage1")
        monkeypatch.setattr(stage1, "OUT_DIR", out_dir)
        stage1.run()
        assert (tmp_path / "stage1" / "stage1_report.json").exists()


class TestForbiddenTerminologyGuardExtendsToStage1Script:
    def test_stage1_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level13_stage1_activation")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL13_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
