"""Level 1.3b, Stage 10 (task #123): tests for ``experiments/level13b_
stage10_ecological_control_scale_shock.py``. Small-scale mechanics
using a real run plus synthetic ledger fixtures -- the real 24-run
archived result lives in ``outputs/level13b_stage10_ecological_control_
scale_shock/records.json``, produced by running the script directly."""

from __future__ import annotations

import json
import os

import pytest

from experiments import level13b_stage10_ecological_control_scale_shock as stage10


def _eco_points():
    return stage10._load_ecological_points()


class TestScaleConditions:
    def test_four_scale_cells(self):
        assert len(stage10.SCALE_CONDITIONS) == 4
        assert (40, 3) in stage10.SCALE_CONDITIONS and (80, 6) in stage10.SCALE_CONDITIONS


class TestBuildConfigAndRunOne:
    def test_build_config_uses_repeated_shocks_and_disclosed_n_shocks(self):
        eco_points = _eco_points()
        config = stage10._build_config(40, 3, 1, eco_points)
        for channel in stage10.CHANNELS:
            assert getattr(config, f"{channel}_history_kind") == "repeated_shocks"
            assert getattr(config, f"{channel}_n_shocks") == stage10.N_SHOCKS

    def test_run_one_returns_expected_shape(self):
        eco_points = _eco_points()
        record = stage10._run_one((40, 3, stage10.SEED_BASE, eco_points))
        assert "S_obs" in record and "mean_resources_final_step" in record
        assert "manipulation_check_passed" in record


class TestRunSmokeTest:
    def test_smoke_test_passes(self):
        eco_points = _eco_points()
        assert stage10.run_smoke_test(eco_points) is True


class TestLedgerViews:
    def test_ledger_views_pooled_and_by_stratum_shape(self):
        records = [
            {"mean_resources_final_step": -10.0, "manipulation_check_passed": True, "S_obs": 0.6, "Z_obs": 0.4, "stratum": "low_feasibility"},
            {"mean_resources_final_step": 5.0, "manipulation_check_passed": True, "S_obs": 0.7, "Z_obs": 0.5, "stratum": "high_feasibility"},
            {"mean_resources_final_step": -3.0, "manipulation_check_passed": False, "S_obs": 0.5, "Z_obs": 0.3, "stratum": "low_feasibility"},
        ]
        views = stage10._ledger_views(records, stratum_key="stratum")
        assert views["pooled"]["n_complete_outcome_ledger"] == 3
        assert views["pooled"]["n_collapsed"] == 2
        assert views["by_stratum"]["low_feasibility"]["n"] == 2
        assert views["eligible_only"]["n"] == 2
        assert views["collapse_as_outcome"]["collapse_rate_pooled"] == views["pooled"]["collapse_rate"]

    def test_ledger_views_no_stratum_key_omits_by_stratum(self):
        records = [{"mean_resources_final_step": 1.0, "manipulation_check_passed": True, "S_obs": 0.5, "Z_obs": 0.4}]
        views = stage10._ledger_views(records, stratum_key=None)
        assert views["by_stratum"] is None

    def test_collapse_threshold_is_strictly_less_than_zero(self):
        records = [
            {"mean_resources_final_step": 0.0, "manipulation_check_passed": True, "S_obs": 0.5, "Z_obs": 0.4, "stratum": "low_feasibility"},
        ]
        views = stage10._ledger_views(records, stratum_key="stratum")
        assert views["pooled"]["n_collapsed"] == 0  # exactly 0.0 is NOT collapsed (threshold is strict <)


class TestScaleRobustnessSummary:
    def test_summary_covers_all_four_cells(self):
        eco_points = _eco_points()
        records = [stage10._run_one((40, 3, stage10.SEED_BASE, eco_points))]
        # scale_robustness_summary iterates SCALE_CONDITIONS regardless of coverage; a partial
        # records list still produces all four cell keys (some empty).
        for population, n_patches in stage10.SCALE_CONDITIONS:
            if population != 40 or n_patches != 3:
                records.append({"population": population, "n_patches": n_patches, "S_obs": 0.0, "Z_obs": 0.0, "manipulation_check_passed": True})
        summary = stage10.scale_robustness_summary(records)
        assert set(summary.keys()) == {f"pop{p}_patches{n}" for p, n in stage10.SCALE_CONDITIONS}


class TestActualOutputIfPresent:
    def test_saved_report_shows_both_ledgers(self):
        path = os.path.join(stage10.OUT_DIR, "stage10_report.json")
        if not os.path.exists(path):
            pytest.skip("Stage 10 saved report not present in this environment")
        with open(path) as f:
            report = json.load(f)
        assert "ledger_this_stage_24_runs" in report
        assert "ledger_stage3_216_runs" in report
        assert report["ledger_stage3_216_runs"]["by_stratum"] is not None
