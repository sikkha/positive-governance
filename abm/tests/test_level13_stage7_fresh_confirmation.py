"""Level 1.3, Stage 7 (task #102): fresh confirmation
(``experiments/level13_stage7_fresh_confirmation.py``).

Runs the stage's own machinery at small scale (2 fresh points) to
confirm mechanics -- the actual 12-point real run and its ``outputs/
level13_stage7_fresh_confirmation/records.json`` record are produced by
running the script directly. A fully-NaN pooled column (``seq_
bargaining_participation``, same one Stage 6 disclosed) triggers the
same benign ``RuntimeWarning: Mean of empty slice`` suppressed
identically to ``tests/test_level13_stage6_blind_phenotype_
discovery.py``."""

from __future__ import annotations

import importlib
import inspect
import warnings

import pytest

from experiments import level13_stage7_fresh_confirmation as stage7
from tests.test_level12_structural_guards import _strip_docstrings_and_comments
from tests.test_level13_sem_firewall_extension import FORBIDDEN_LEVEL13_TERMS


class TestSeedDisjointness:
    """This stage's own core requirement: fresh seeds, never reused
    from Stage 3-6."""

    def test_lhs_seed_distinct_from_every_earlier_level13_lhs_seed(self):
        from experiments import level13_common, level13_stage4_open_pressure_history_search as stage4
        assert stage7.LHS_SEED not in {level13_common.LHS_SEED_ECOLOGICAL_LEVEL13, stage4.LHS_SEED}

    def test_seed_range_disjoint_from_earlier_stages(self):
        # Stage 3: 5,000,000+ (72 runs); Stage 4: 6,000,000-6,023,003;
        # Stage 5: 7,000,000-7,000,015.
        fresh_seeds = {stage7.SEED_BASE + i * 1000 for i in range(stage7.N_POINTS)}
        earlier = set(range(5_000_000, 5_000_100)) | set(range(6_000_000, 6_024_000)) | set(range(7_000_000, 7_000_100))
        assert fresh_seeds.isdisjoint(earlier)


class TestDrawFreshPoints:
    def test_correct_count_and_deterministic(self):
        d1 = stage7.draw_fresh_points(n_points=5, seed=1)
        d2 = stage7.draw_fresh_points(n_points=5, seed=1)
        assert len(d1) == 5
        assert d1 == d2


class TestStage6Fit:
    def test_returns_headline_k_and_a_fitted_model(self):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Mean of empty slice")
            fit = stage7._stage6_fit()
        assert fit["headline_k"] is not None
        assert fit["model"] is not None
        assert fit["prep_pool"]["X_train"].shape[0] == 216


class TestRunAtSmallScale:
    def test_small_scale_run_produces_correct_point_count(self, monkeypatch):
        monkeypatch.setattr(stage7, "N_POINTS", 2)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Mean of empty slice")
            report = stage7.run()
        assert report["n_points"] == 2
        assert len(report["fresh_records"]) == 2
        assert len(report["predicted_cluster_labels"]) == 2

    def test_write_report_persists_to_disk(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stage7, "N_POINTS", 1)
        out_dir = str(tmp_path / "stage7")
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Mean of empty slice")
            report = stage7.write_report(out_dir=out_dir)
        assert "report_hash" in report
        assert (tmp_path / "stage7" / "records.json").exists()

    def test_no_six_way_verdict_rendered(self, monkeypatch):
        monkeypatch.setattr(stage7, "N_POINTS", 1)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Mean of empty slice")
            report = stage7.run()
        assert "verdict" not in report
        assert "decision_gate_note" in report


class TestReportHash:
    def test_stable_across_key_order(self):
        assert stage7.report_hash({"a": 1, "b": 2}) == stage7.report_hash({"b": 2, "a": 1})

    def test_changes_with_content(self):
        assert stage7.report_hash({"a": 1}) != stage7.report_hash({"a": 2})


class TestForbiddenTerminologyGuardExtendsToStage7Script:
    def test_stage7_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level13_stage7_fresh_confirmation")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL13_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
