"""Level 1.3b, task #125: visualizations -- structural tests, mirroring
``tests/test_level13_visualizations.py``'s own precedent exactly."""

from __future__ import annotations

import importlib
import inspect
import os

from tests.test_level12_structural_guards import _strip_docstrings_and_comments
from tests.test_level13_sem_firewall_extension import FORBIDDEN_LEVEL13_TERMS


class TestForbiddenTerminologyGuardExtendsToVisualizationScript:
    def test_module_free_of_forbidden_terms(self):
        """experiments/make_level13b_visualizations.py is NOT matched by
        tests/test_level13b_sem_firewall_extension.py's own
        ``level13b_*.py`` glob (its filename starts with "make_", not
        "level13b_") -- the same pre-existing gap Level 1.3's own
        make_level13_visualizations.py already has, checked directly
        here for the same reason."""
        module = importlib.import_module("experiments.make_level13b_visualizations")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL13_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []


class TestVisualizationScriptRunsCleanlyOnCommittedOutputs:
    def test_run_produces_all_sixteen_figures_without_crashing(self):
        import pytest
        from experiments.make_level13b_visualizations import OUT_DIR, PATHS, run

        if not os.path.exists(PATHS["stage4_records"]):
            pytest.skip("Level 1.3b stage outputs not present in this environment")

        run()
        expected = [
            "01_stage0_compatibility_and_cross_process", "02_stage1_hand_computed_microcase",
            "03_stage2_calibration_activation", "04_stage3_pairwise_contrasts",
            "05_stage4_lhs_scatter", "06_stage4_pool_summary",
            "07_stage5_persistence_classification", "08_stage5_counterfactual_persistence",
            "09_stage6_sham_and_divergence", "10_stage7_bic_curve", "11_stage7_stability",
            "12_stage8_generalization_gap", "13_stage9_correlation_robustness",
            "14_stage9_factor_structure", "15_stage10_scale_and_ledger",
            "16_test_requirements_coverage",
        ]
        for name in expected:
            assert os.path.exists(f"{OUT_DIR}/{name}.png"), f"missing {name}.png"


class TestNoFigureRendersItsOwnVerdict:
    def test_source_never_asserts_a_decision_gate_outcome(self):
        """This milestone's own stopping rule: do not silently promote a
        verdict anywhere outside task #126's own decision gate. None of
        this script's own figure titles/labels may reference a
        DECISION_GATE_OUTCOMES key."""
        from experiments.level13b_preregistration import DECISION_GATE_OUTCOMES
        module = importlib.import_module("experiments.make_level13b_visualizations")
        source = inspect.getsource(module).lower()
        for key in DECISION_GATE_OUTCOMES:
            assert key.lower() not in source, f"decision-gate key {key!r} leaked into visualization script"
