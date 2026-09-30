"""Level 1.2, Stage 4: blind phenotype discovery run -- helper + structural tests."""

from __future__ import annotations

import importlib
import inspect

import numpy as np
import pytest

from experiments import level12_stage4_discovery as stage4
from tests.test_level12_structural_guards import FORBIDDEN_LEVEL12_TERMS, _strip_docstrings_and_comments


class TestScatter:
    def test_scatter_places_subset_labels_at_masked_positions(self):
        mask = np.array([True, False, True, True])
        subset_labels = np.array([0, 1, 1])
        full = stage4._scatter(subset_labels, mask, n_total=4)
        assert full.tolist() == [0, -1, 1, 1]

    def test_scatter_fills_dropped_rows_with_negative_one(self):
        mask = np.array([True, True, False])
        full = stage4._scatter(np.array([0, 0]), mask, n_total=3)
        assert full[2] == -1


class TestFitAtK:
    def test_finds_matching_k(self):
        fits = [{"k": 1, "x": "a"}, {"k": 2, "x": "b"}]
        assert stage4._fit_at_k(fits, 2)["x"] == "b"

    def test_returns_none_when_absent(self):
        fits = [{"k": 1}]
        assert stage4._fit_at_k(fits, 5) is None


class TestLoadPoolAndRunOnRealStage3Output:
    def test_load_pool_only_includes_eligible_records(self):
        records = stage4.load_pool()
        assert all(r["eligibility"]["eligible"] for r in records)
        assert len(records) > 0

    def test_full_run_produces_a_report_with_expected_top_level_keys(self):
        report = stage4.run()
        for key in (
            "n_pooled_records", "candidate_methods", "k_range_evaluated", "missingness_report",
            "gmm_fits_summary", "hierarchical_fits_summary", "hdbscan_fit_summary",
            "n_candidate_clusters_evaluated", "n_candidates_meeting_all_12_criteria", "candidates",
        ):
            assert key in report

    def test_every_candidate_reports_a_full_12_criterion_breakdown(self):
        report = stage4.run()
        for c in report["candidates"]:
            assert len(c["evaluation"]["criteria"]) == 12

    def test_no_candidate_is_forced_toward_meeting_all_criteria(self):
        # Structural guard on this stage's own honesty: with Stage 3's
        # small, collapse-dominated pool, it is expected (not a bug) that
        # few or zero candidates meet all 12 criteria -- this test only
        # confirms the count is computed consistently with the raw data,
        # never silently inflated.
        report = stage4.run()
        recomputed = sum(1 for c in report["candidates"] if c["evaluation"]["meets_all_minimum_criteria"])
        assert recomputed == report["n_candidates_meeting_all_12_criteria"]


class TestForbiddenTerminologyGuardExtendsToStage4Script:
    def test_stage4_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level12_stage4_discovery")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL12_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
