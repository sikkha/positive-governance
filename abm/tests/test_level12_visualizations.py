"""Level 1.2, Section 19: visualizations -- structural tests."""

from __future__ import annotations

import importlib
import inspect
import os

from tests.test_level12_structural_guards import FORBIDDEN_LEVEL12_TERMS, _strip_docstrings_and_comments


class TestForbiddenTerminologyGuardExtendsToVisualizationScript:
    def test_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.make_level12_visualizations")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL12_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []


class TestVisualizationScriptRunsCleanlyOnCommittedOutputs:
    def test_run_produces_all_ten_figures_without_crashing(self):
        from experiments.make_level12_visualizations import OUT_DIR, run
        run()
        expected = [
            "01_stage1_mechanism_activation", "02_stage2_outcome_distribution",
            "03_stage3_regen_rate_vs_ecological_fraction", "04_stage3_outcome_distribution",
            "05_stage4_criteria_pass_distribution", "06_stage4_vs_stage5_replication",
            "07_stage5_held_out_log_likelihood", "08_stage6_scaling_grid",
            "09_stage13_migration_ablation", "10_stage13_regen_rate_ablation",
        ]
        for name in expected:
            assert os.path.exists(f"{OUT_DIR}/{name}.png"), f"missing {name}.png"
