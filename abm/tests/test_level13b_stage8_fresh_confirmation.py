"""Level 1.3b, Stage 8 (task #121): tests for ``experiments/level13b_
stage8_fresh_confirmation.py``. Small-scale mechanics (2 real runs at
Stage 8's own disjoint seed range) plus a skip-if-absent read of the
real saved report -- the real 96-run archived result lives in
``outputs/level13b_stage8_fresh_confirmation/records.json``, produced
by running the script directly."""

from __future__ import annotations

import json
import os

import pytest

from experiments import level13b_stage8_fresh_confirmation as stage8
from experiments.level13b_stage4_homogeneous_discovery import _load_ecological_points, lhs_draws


class TestSeedAndDesignDisjointness:
    def test_lhs_seed_disjoint_from_stage4(self):
        assert stage8.LHS_SEED != 20260821001

    def test_seed_base_disjoint_from_stage4_and_does_not_overlap_its_range(self):
        stage4_seed_base = 8_700_000
        stage4_max_seed = stage4_seed_base + 48 * 1000 + 5  # n_points * 1000 + n_seeds_per_point, generous bound
        assert stage8.SEED_BASE != stage4_seed_base
        assert stage8.SEED_BASE > stage4_max_seed or stage8.SEED_BASE + stage8.N_POINTS * stage8.N_SEEDS_PER_POINT < stage4_seed_base


class TestRunSmokeTest:
    def test_smoke_test_passes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stage8, "OUT_DIR", str(tmp_path))
        eco_points = _load_ecological_points()
        assert stage8.run_smoke_test(eco_points) is True


class TestReconstructFrozenStage4Fit:
    def test_reconstruction_is_deterministic(self):
        if not os.path.exists(stage8.STAGE4_RECORDS_PATH):
            pytest.skip("Stage 4 archive not present in this environment")
        a = stage8._reconstruct_frozen_stage4_fit(1)
        b = stage8._reconstruct_frozen_stage4_fit(1)
        assert a["covariance_type"] == b["covariance_type"]
        assert (a["standardize_mean"] == b["standardize_mean"]).all()


class TestScoreFreshData:
    def test_score_fresh_data_on_two_real_runs(self):
        if not os.path.exists(stage8.STAGE4_RECORDS_PATH):
            pytest.skip("Stage 4 archive not present in this environment")
        eco_points = _load_ecological_points()
        draws = lhs_draws(n=2, seed=stage8.LHS_SEED)
        from experiments.level13b_stage4_homogeneous_discovery import _run_one
        records = [_run_one((i, draw, stage8.SEED_BASE + i, eco_points)) for i, draw in enumerate(draws)]
        scoring = stage8.score_fresh_data(records)
        assert scoring["n_records"] == 2
        assert "per_run_log_likelihood_gap_k8_minus_k1" in scoring["generalization_gap_test"]


class TestActualOutputIfPresent:
    def test_saved_report_has_expected_shape(self):
        path = os.path.join(stage8.OUT_DIR, "stage8_report.json")
        if not os.path.exists(path):
            pytest.skip("Stage 8 saved report not present in this environment")
        with open(path) as f:
            report = json.load(f)
        assert report["smoke_test_passed"] is True
        gap = report["generalization_gap_test"]
        assert "per_run_log_likelihood_gap_k8_minus_k1" in gap
