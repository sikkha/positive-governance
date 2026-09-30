"""Level 1.2b, Work Package N (Section 19): tests for
``experiments/level12b_stage_n_causal_collapse_decomposition.py``."""
from __future__ import annotations

import json
import math
import os

import pytest

from experiments.level12b_stage_n_causal_collapse_decomposition import (
    FACTORS,
    N_SEEDS_PER_ABLATION,
    _paired_summary,
    _probability,
)


class TestFactorRegistry:
    def test_exactly_13_factors(self):
        assert len(FACTORS) == 13

    def test_factor_keys_are_unique(self):
        keys = [f["key"] for f in FACTORS]
        assert len(set(keys)) == len(keys)

    def test_every_factor_has_low_and_high(self):
        for f in FACTORS:
            assert "low" in f and "high" in f
            assert f["low"] != f["high"]

    def test_every_factor_has_a_config_field(self):
        for f in FACTORS:
            assert isinstance(f["field"], str) and f["field"]

    @pytest.mark.parametrize("expected_key", [
        "migration_on_off", "migration_rate", "migration_cost", "migration_congestion",
        "patch_regen", "capacity", "extraction_unit", "subsistence", "maintenance_efficiency",
        "admin_cost", "transmission_cost", "coordination_cost", "scale_overload",
    ])
    def test_expected_factor_present(self, expected_key):
        assert any(f["key"] == expected_key for f in FACTORS)


class TestPairedSummary:
    def test_mean_diff_computed_correctly(self):
        pairs = [
            {"low": {"x": 1.0}, "high": {"x": 3.0}},
            {"low": {"x": 2.0}, "high": {"x": 2.0}},
        ]
        result = _paired_summary(pairs, "x")
        assert result["mean_paired_difference_high_minus_low"] == pytest.approx(1.0)
        assert result["n_high_greater"] == 1
        assert result["n_tied"] == 1

    def test_nan_pairs_excluded(self):
        pairs = [
            {"low": {"x": float("nan")}, "high": {"x": 3.0}},
            {"low": {"x": 2.0}, "high": {"x": 4.0}},
        ]
        result = _paired_summary(pairs, "x")
        assert result["n_defined_pairs"] == 1

    def test_empty_pairs_degenerate(self):
        result = _paired_summary([], "x")
        assert result["n_defined_pairs"] == 0
        assert math.isnan(result["mean_paired_difference_high_minus_low"])


class TestProbability:
    def test_fraction_matching_predicate(self):
        pairs = [{"low": {"label": "collapse"}}, {"low": {"label": "viable"}}, {"low": {"label": "collapse"}}]
        assert _probability(pairs, "low", lambda a: a["label"] == "collapse") == pytest.approx(2 / 3)

    def test_empty_is_nan(self):
        assert math.isnan(_probability([], "low", lambda a: True))


class TestActualExperimentOutputIfPresent:
    def test_results_meet_section_19_structural_requirements(self):
        out_dir = "outputs/level12b_stage_n_causal_collapse_decomposition"
        if not os.path.exists(f"{out_dir}/results.json"):
            pytest.skip("Work Package N experiment output not present in this environment")
        with open(f"{out_dir}/results.json") as f:
            report = json.load(f)
        assert report["n_factors"] == 13
        assert report["n_total_runs"] == 13 * N_SEEDS_PER_ABLATION * 2
        assert report["preregistration_manifest_hash"]
        assert report["recalibration_note"]
        for fr in report["factor_results"]:
            assert fr["n_pairs"] == N_SEEDS_PER_ABLATION
            summary = fr["summary"]
            for key in ("ecological_resource_fraction", "cumulative_unmet_extraction_demand", "fraction_of_steps_below_one"):
                assert "mean_paired_difference_high_minus_low" in summary[key]
            for key in ("collapse_probability", "fragmentation_probability", "sustained_system_probability"):
                assert 0.0 <= summary[key]["low"] <= 1.0 or summary[key]["low"] != summary[key]["low"]
                assert 0.0 <= summary[key]["high"] <= 1.0 or summary[key]["high"] != summary[key]["high"]
