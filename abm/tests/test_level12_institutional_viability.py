"""Level 1.2, Section 8: failure and viability classification."""

from __future__ import annotations

import pytest

from abm_governance.observer.institutional_viability import (
    ALL_OUTCOME_LABELS,
    classify_all_outcome,
    sustained_system_eligibility,
)


class TestClassifyAllOutcome:
    def test_no_institution_ever_formed(self):
        assert classify_all_outcome(0, 0, 0.9, 0.9, 0) == "no_institution"

    def test_population_collapse(self):
        assert classify_all_outcome(1, 1, 0.01, 0.9, 1) == "collapse"

    def test_ecological_collapse(self):
        assert classify_all_outcome(1, 1, 0.9, 0.01, 1) == "collapse"

    def test_viable(self):
        assert classify_all_outcome(1, 1, 0.5, 0.5, 1) == "viable"

    def test_fragmented_multiple_uncoordinated_institutions(self):
        assert classify_all_outcome(3, 3, 0.5, 0.1, 1) == "fragmented"

    def test_persistent_extractive_single_low_ecology_survivor(self):
        assert classify_all_outcome(1, 1, 0.5, 0.1, 1) == "persistent_extractive"

    def test_transient_nothing_survives_but_no_collapse(self):
        assert classify_all_outcome(2, 0, 0.9, 0.9, 0) == "transient"

    def test_every_label_in_closed_vocabulary(self):
        results = {
            classify_all_outcome(0, 0, 0.9, 0.9, 0),
            classify_all_outcome(1, 1, 0.01, 0.9, 1),
            classify_all_outcome(1, 1, 0.5, 0.5, 1),
            classify_all_outcome(3, 3, 0.5, 0.1, 1),
            classify_all_outcome(1, 1, 0.5, 0.1, 1),
            classify_all_outcome(2, 0, 0.9, 0.9, 0),
        }
        assert results <= set(ALL_OUTCOME_LABELS)


class TestSustainedSystemEligibility:
    def test_eligible_when_all_criteria_met(self):
        vector = {"C": {"value": 0.5}, "V": {"ecological": {"value": 0.6}, "demographic": {"value": 0.5}}}
        result = sustained_system_eligibility(10, 5, vector, 20, True)
        assert result["eligible"] is True
        assert result["reasons"] == []

    def test_reports_every_failed_criterion_explicitly(self):
        vector = {"C": {"value": float("nan")}, "V": {"ecological": {"value": None}, "demographic": {"value": float("nan")}}}
        result = sustained_system_eligibility(1, 0, vector, 2, False, min_observations=5, min_duration=10)
        assert result["eligible"] is False
        assert any("insufficient_post_burn_in_observations" in r for r in result["reasons"])
        assert "zero_surviving_population" in result["reasons"]
        assert any("below_minimum_duration" in r for r in result["reasons"])
        assert "terminal_state_corrupted" in result["reasons"]
        assert "no_valid_measurements" in result["reasons"]

    def test_never_excludes_for_resembling_any_particular_governance_profile(self):
        # A run with an unusual (not SEM-like) profile still passes as
        # long as data-sufficiency criteria hold -- eligibility never
        # depends on the *shape* of the phenotype vector's values.
        vector = {"C": {"value": 0.99}, "E": {"value": 0.01}, "V": {"ecological": {"value": 0.01}, "demographic": {"value": 0.99}}}
        result = sustained_system_eligibility(10, 3, vector, 15, True)
        assert result["eligible"] is True
