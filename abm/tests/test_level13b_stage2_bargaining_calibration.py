"""Level 1.3b, Stage 2 (task #113): tests for ``experiments/level13b_
stage2_bargaining_calibration.py``. Small-scale mechanics (1-2 real
runs) -- the real full sweep (3 strata x 4 response costs x 2 periods x
4 seeds) lives in ``outputs/level13b_stage2_bargaining_calibration/
sweep_results.json``, produced by running the script directly."""

from __future__ import annotations

import json
import os

import pytest

from experiments import level13b_stage2_bargaining_calibration as stage2


def _eco_points():
    return stage2._load_ecological_points()


class TestLoadEcologicalPoints:
    def test_three_strata_present(self):
        points = _eco_points()
        assert set(points.keys()) == {"low_feasibility", "medium_feasibility", "high_feasibility"}


class TestBuildConfigAndRunOne:
    def test_build_config_applies_response_cost_and_period(self):
        eco_points = _eco_points()
        config = stage2._build_config("low_feasibility", 0.2, 10, 1, eco_points)
        assert config.contribution_amount == 0.2
        assert config.contribution_period_steps == 10
        assert config.entrenchment_enabled is True

    def test_run_one_returns_activation_flags_for_every_min_duration_value(self):
        eco_points = _eco_points()
        result = stage2._run_one(("low_feasibility", stage2.RESPONSE_COSTS[-1], stage2.PERIODS[-1], stage2.SEED_BASE, eco_points))
        for md in stage2.MIN_DURATION_STEPS_VALUES:
            assert f"min_duration_steps_{md}" in result
        assert "realized_compliance_rate" in result


class TestRunSmokeTest:
    def test_smoke_test_passes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stage2, "OUT_DIR", str(tmp_path))
        eco_points = _eco_points()
        assert stage2.run_smoke_test(eco_points) is True
        assert (tmp_path / "smoke_test.json").exists()


class TestSummarize:
    def test_summarize_groups_by_cell(self):
        eco_points = _eco_points()
        results = [
            stage2._run_one(("low_feasibility", stage2.RESPONSE_COSTS[-1], stage2.PERIODS[-1], stage2.SEED_BASE, eco_points)),
            stage2._run_one(("low_feasibility", stage2.RESPONSE_COSTS[-1], stage2.PERIODS[-1], stage2.SEED_BASE + 1, eco_points)),
        ]
        summary = stage2.summarize(results)
        assert len(summary["cell_summaries"]) == 1
        assert summary["cell_summaries"][0]["n_seeds"] == 2


class TestWriteScopeDeclaration:
    def test_scope_declares_selection_rule_uses_only_bargaining_participation(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stage2, "OUT_DIR", str(tmp_path))
        scope = stage2.write_scope_declaration()
        assert "bargaining_participation" in scope["selection_rule_disclosed"]
        assert "S_obs, Z_obs" in scope["selection_rule_disclosed"] or "S_obs" in scope["selection_rule_disclosed"]


class TestActualOutputIfPresent:
    def test_saved_calibration_report_has_cell_summaries(self):
        path = os.path.join(stage2.OUT_DIR, "calibration_report.json")
        if not os.path.exists(path):
            pytest.skip("Stage 2 saved report not present in this environment")
        with open(path) as f:
            report = json.load(f)
        assert "cell_summaries" in report
        assert len(report["cell_summaries"]) > 0
