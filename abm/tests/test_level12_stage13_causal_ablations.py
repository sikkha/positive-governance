"""Level 1.2, Section 13: causal ablations -- helper + structural tests."""

from __future__ import annotations

import importlib
import inspect

from experiments import level12_stage13_causal_ablations as stage13
from tests.test_level12_structural_guards import FORBIDDEN_LEVEL12_TERMS, _strip_docstrings_and_comments


class TestSummarizePairs:
    def test_counts_favor_and_transitions_correctly(self):
        pairs = [
            {"key_a": 0.1, "key_b": 0.3, "la": "collapse", "lb": "fragmented"},
            {"key_a": 0.5, "key_b": 0.2, "la": "viable", "lb": "collapse"},
            {"key_a": 0.4, "key_b": 0.4, "la": "collapse", "lb": "collapse"},
        ]
        result = stage13._summarize_pairs(pairs, "key_a", "key_b", "la", "lb")
        assert result["n_b_greater_ecological_fraction"] == 1
        assert result["n_a_greater_ecological_fraction"] == 1
        assert result["n_tied"] == 1
        assert result["n_outcome_label_transitions"] == 2

    def test_mean_paired_difference_is_signed_b_minus_a(self):
        pairs = [{"key_a": 0.1, "key_b": 0.3, "la": "x", "lb": "x"}]
        result = stage13._summarize_pairs(pairs, "key_a", "key_b", "la", "lb")
        assert result["mean_paired_difference"] > 0

    def test_handles_all_zero_diffs_without_crashing(self):
        pairs = [{"key_a": 0.2, "key_b": 0.2, "la": "x", "lb": "x"} for _ in range(3)]
        result = stage13._summarize_pairs(pairs, "key_a", "key_b", "la", "lb")
        assert result["wilcoxon_signed_rank"]["p_value"] is None


class TestConfigConstruction:
    def test_migration_ablation_pair_shares_same_seed(self):
        kwargs = stage13._base_kwargs(9000)
        assert kwargs["seed"] == 9000
        assert "migration_enabled" not in kwargs  # set separately by each ablation's own two conditions

    def test_regen_bounds_match_stage3_parameter_space_bounds(self):
        from experiments.level12_stage3_search import PARAMETER_SPACE
        regen_bounds = next((lo, hi) for name, lo, hi in PARAMETER_SPACE if name == "patch_regen_rate")
        assert (stage13.REGEN_RATE_LOW, stage13.REGEN_RATE_HIGH) == regen_bounds


class TestForbiddenTerminologyGuardExtendsToStage13Script:
    def test_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level12_stage13_causal_ablations")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL12_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
