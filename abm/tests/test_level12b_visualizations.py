"""Level 1.2b, Section 26: visualizations -- structural tests."""

from __future__ import annotations

import importlib
import inspect
import os

from tests.test_level12_structural_guards import FORBIDDEN_LEVEL12_TERMS, _strip_docstrings_and_comments


class TestForbiddenTerminologyGuardExtendsToVisualizationScript:
    def test_module_free_of_forbidden_terms(self):
        """experiments/make_level12b_visualizations.py is NOT matched
        by tests/test_level12_sem_firewall.py's own ``level12b_*.py``
        glob (its filename starts with "make_", not "level12b_") --
        the same pre-existing gap Level 1.2's own
        make_level12_visualizations.py already has. Checked directly
        here instead, mirroring tests/test_level12_visualizations.py's
        own precedent, rather than silently relying on a scan that
        does not actually cover this file."""
        module = importlib.import_module("experiments.make_level12b_visualizations")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL12_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []


class TestVisualizationScriptRunsCleanlyOnCommittedOutputs:
    def test_run_produces_all_sixteen_figures_without_crashing(self):
        from experiments.make_level12b_visualizations import OUT_DIR, run
        run()
        expected = [
            "01_ledger_balance", "02_ratio_vs_realized_balance", "03_feasibility_map_and_strata",
            "04_all_outcome_summary", "05_failure_trajectory", "06_sustained_system_eligibility",
            "07_missingness", "08_feature_by_stratum", "09_model_selection", "10_algorithm_agreement",
            "11_stability_metrics", "12_discovery_vs_confirmation", "13_scaling_robustness",
            "14_causal_ablation_effects", "15_outcome_transition_matrix", "16_recurrence_classification",
        ]
        for name in expected:
            assert os.path.exists(f"{OUT_DIR}/{name}.png"), f"missing {name}.png"

    def test_ledger_balance_figure_uses_a_fresh_run_with_near_zero_residual(self):
        """fig_ledger_balance is the one figure this script runs a
        fresh simulation for (Work Packages A/B have no saved
        results.json of their own) -- verify directly that the fresh
        run it drives actually reconciles, not just that a file gets
        written."""
        from abm_governance.core.config import SimulationConfig
        from abm_governance.observer.ecological_ledger import (
            LEDGER_RESIDUAL_TOLERANCE,
            compute_ledger_reconciliation,
            system_total_resources,
        )
        from abm_governance.simulation import Simulation

        config = SimulationConfig.level12_complete(population_size=32, n_patches=4, n_steps=200, seed=777)
        sim = Simulation(config)
        opening = system_total_resources(sim.patch_system, sim.agents, sim.rule_registry)
        sim.run()
        closing = system_total_resources(sim.patch_system, sim.agents, sim.rule_registry)
        rec = compute_ledger_reconciliation(
            opening_stock=opening, closing_stock=closing, patch_system=sim.patch_system,
            event_log=sim.event_log, search_cost=config.search_cost, membership_exit_cost=config.membership_exit_cost,
        )
        assert abs(rec.residual) < max(LEDGER_RESIDUAL_TOLERANCE, 1e-4)


class TestNoKPrivileging:
    def test_model_selection_figure_plots_every_k_in_default_range_identically(self):
        """Section 26's own 'no visual privileging of k=3' requirement,
        checked directly: fig_model_selection must not special-case or
        omit any k, k=1 included."""
        import json

        from abm_governance.observer.phenotype_discovery import DEFAULT_K_RANGE

        path = "outputs/level12b_stage_k_clustering_discovery/results.json"
        if not os.path.exists(path):
            import pytest
            pytest.skip("Work Package K output not present in this environment")
        with open(path) as f:
            data = json.load(f)
        ks_present = {r["k"] for r in data["k_range_results"]["gmm"]}
        assert ks_present == set(DEFAULT_K_RANGE)
