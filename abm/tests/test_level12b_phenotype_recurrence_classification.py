"""Level 1.2b, Work Package O (Section 20): tests for
``experiments/level12b_stage_o_phenotype_recurrence_classification.py``."""
from __future__ import annotations

import json
import math
import os

import pytest

from experiments.level12b_stage_o_phenotype_recurrence_classification import (
    CAUTIOUS_LABELS,
    EXPLANATORY_CATEGORIES,
    MIN_MEMBERS_FOR_DIVERSITY_INTERPRETATION,
    _environmental_forcing_diversity,
    attractor_label_permitted,
    classify_overall_recurrence_label,
)


class TestClassifyOverallRecurrenceLabel:
    def test_unclassified_below_hard_minimum(self):
        result = classify_overall_recurrence_label(n_total=5, n_hard_minimum=40, discovery_verdict="continuum", confirmation_verdict="null_replicated")
        assert result["label"] == "unclassified"

    def test_unclassified_when_one_config(self):
        result = classify_overall_recurrence_label(n_total=576, n_hard_minimum=40, discovery_verdict="one_config", confirmation_verdict="null_replicated")
        assert result["label"] == "unclassified"

    def test_failure_when_discovery_failure_dominated(self):
        result = classify_overall_recurrence_label(n_total=576, n_hard_minimum=40, discovery_verdict="failure_dominated", confirmation_verdict=None)
        assert result["label"] == "failure"

    def test_transient_when_discovery_unstable(self):
        result = classify_overall_recurrence_label(n_total=576, n_hard_minimum=40, discovery_verdict="unstable", confirmation_verdict=None)
        assert result["label"] == "transient"

    def test_continuum_when_discovery_continuum(self):
        result = classify_overall_recurrence_label(n_total=576, n_hard_minimum=40, discovery_verdict="continuum", confirmation_verdict="null_replicated")
        assert result["label"] == "continuum"

    def test_confirmed_when_multi_config_and_confirmation_reproduces(self):
        result = classify_overall_recurrence_label(n_total=576, n_hard_minimum=40, discovery_verdict="multi_config", confirmation_verdict="unexpected_recurring_structure")
        assert result["label"] == "confirmed"

    def test_boundary_when_multi_config_and_confirmation_null_replicated(self):
        result = classify_overall_recurrence_label(n_total=576, n_hard_minimum=40, discovery_verdict="multi_config", confirmation_verdict="null_replicated")
        assert result["label"] == "boundary"

    def test_candidate_when_multi_config_and_confirmation_not_yet_run(self):
        result = classify_overall_recurrence_label(n_total=576, n_hard_minimum=40, discovery_verdict="multi_config", confirmation_verdict="insufficient_confirmation_data")
        assert result["label"] == "candidate"

    def test_label_always_in_closed_vocabulary(self):
        for kwargs in [
            {"n_total": 1, "n_hard_minimum": 40, "discovery_verdict": "continuum", "confirmation_verdict": "null_replicated"},
            {"n_total": 576, "n_hard_minimum": 40, "discovery_verdict": "multi_config", "confirmation_verdict": "unexpected_recurring_structure"},
            {"n_total": 576, "n_hard_minimum": 40, "discovery_verdict": "weird_unrecognized_value", "confirmation_verdict": None},
        ]:
            result = classify_overall_recurrence_label(**kwargs)
            assert result["label"] in CAUTIOUS_LABELS

    def test_never_returns_attractor(self):
        """CAUTIOUS_LABELS itself must never contain 'attractor' --
        Section 20's own hard rule."""
        assert "attractor" not in CAUTIOUS_LABELS


class TestAttractorLabelPermitted:
    def test_not_permitted_when_population_never_recovers(self):
        result = attractor_label_permitted({"population_recovery_rate": 0.0, "ecological_recovery_rate": 0.875})
        assert result["permitted"] is False

    def test_permitted_when_both_dimensions_majority_recover(self):
        result = attractor_label_permitted({"population_recovery_rate": 0.7, "ecological_recovery_rate": 0.8})
        assert result["permitted"] is True

    def test_not_permitted_on_nan_input(self):
        result = attractor_label_permitted({"population_recovery_rate": float("nan"), "ecological_recovery_rate": float("nan")})
        assert result["permitted"] is False


class TestEnvironmentalForcingDiversity:
    def test_insufficient_members_below_floor(self):
        members = [{"joint_point_id": 1, "ic_family": "a", "expected_stratum": "low_feasibility"}]
        result = _environmental_forcing_diversity(members)
        assert result["interpretation"] == "insufficient_members_for_interpretation"

    def test_consistent_with_forcing_when_low_diversity(self):
        members = [{"joint_point_id": 1, "ic_family": "a", "expected_stratum": "low_feasibility"} for _ in range(10)]
        result = _environmental_forcing_diversity(members)
        assert result["interpretation"] == "consistent_with_environmental_forcing"

    def test_against_forcing_when_high_diversity(self):
        members = [{"joint_point_id": i, "ic_family": "a", "expected_stratum": "low_feasibility"} for i in range(10)]
        result = _environmental_forcing_diversity(members)
        assert result["interpretation"] == "against_environmental_forcing"

    def test_no_members_degenerate(self):
        result = _environmental_forcing_diversity([])
        assert result["n_members"] == 0
        assert math.isnan(result["distinct_joint_points_fraction"])

    def test_floor_is_positive(self):
        assert MIN_MEMBERS_FOR_DIVERSITY_INTERPRETATION > 0


class TestActualExperimentOutputIfPresent:
    def test_results_meet_section_20_structural_requirements(self):
        path = "outputs/level12b_stage_o_phenotype_recurrence_classification/results.json"
        if not os.path.exists(path):
            pytest.skip("Work Package O output not present in this environment")
        with open(path) as f:
            report = json.load(f)
        assert report["overall_classification"]["label"] in CAUTIOUS_LABELS
        assert report["attractor_label_assigned"] is False
        assert set(report["explanatory_categories_evaluated"]) == set(EXPLANATORY_CATEGORIES)
        assert "attractor" not in json.dumps(report["overall_classification"]).lower()
        assert report["source_design_hash"]
        assert report["preregistration_manifest_hash"]
