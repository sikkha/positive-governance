"""Level 1.3, task #106: visualizations -- structural tests, mirroring
``tests/test_level12b_visualizations.py``'s own precedent exactly."""

from __future__ import annotations

import importlib
import inspect
import os

from tests.test_level13_sem_firewall_extension import FORBIDDEN_LEVEL13_TERMS
from tests.test_level12_structural_guards import _strip_docstrings_and_comments


class TestForbiddenTerminologyGuardExtendsToVisualizationScript:
    def test_module_free_of_forbidden_terms(self):
        """experiments/make_level13_visualizations.py is NOT matched by
        tests/test_level13_sem_firewall_extension.py's own
        ``level13_*.py`` glob (its filename starts with "make_", not
        "level13_") -- the same pre-existing gap Level 1.2b's own
        make_level12b_visualizations.py already has, checked directly
        here for the same reason."""
        module = importlib.import_module("experiments.make_level13_visualizations")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL13_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []


class TestVisualizationScriptRunsCleanlyOnCommittedOutputs:
    def test_run_produces_all_fourteen_figures_without_crashing(self):
        from experiments.make_level13_visualizations import OUT_DIR, run
        run()
        expected = [
            "01_pressure_history_kinds", "02_compatibility_and_activation_summary",
            "03_feasibility_strata", "04_stage3_by_ordering", "05_stage3_entrenchment_effect",
            "06_stage4_lhs_scatter", "07_stage5_counterfactual_shift", "08_stage6_model_selection",
            "09_stage6_stability", "10_stage7_fresh_confirmation", "11_stage8_scatter",
            "12_stage8_covariate_correlations", "13_stage9_scale_robustness",
            "14_test_requirements_coverage",
        ]
        for name in expected:
            assert os.path.exists(f"{OUT_DIR}/{name}.png"), f"missing {name}.png"

    def test_pressure_history_kinds_figure_does_not_require_a_simulation_run(self):
        """The one disclosed exception (matching Level 1.2b's own
        fig_ledger_balance precedent): this figure calls
        generate_pressure_series directly, never Simulation(...).run()."""
        import inspect as _inspect

        from experiments.make_level13_visualizations import fig_pressure_history_kinds
        source = _inspect.getsource(fig_pressure_history_kinds)
        assert "Simulation(" not in source
        assert "generate_pressure_series" in source
