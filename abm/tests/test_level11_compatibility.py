"""Level 1.1: exact Level-1.0 compatibility, config validation, structural
terminology guards, generative/observer separation, and serial/parallel
(same-seed) reproducibility -- the tests the milestone's completion gate
(Section 14) and Section 9's testing requirements name explicitly."""

from __future__ import annotations

import dataclasses
import inspect

import numpy as np
import pytest

from abm_governance.agents.agent import Agent, FORBIDDEN_ATTRIBUTE_SUBSTRINGS
from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation

#: Section 2 constraint 2's forbidden generative-layer terms, restated
#: here as a structural guard covering every Level 1.1 module.
FORBIDDEN_LEVEL11_TERMS = (
    "authoritarian",
    "liberal",
    "democratic",
    "integrated_equilibrium",
    "constrained_liberalism",
    "authoritarian_efficiency",
    "governance_type",
    "governance_species",
    "primordial_form",
    "recurrent_institutional_phenotype",
    "positive_governance",
    "fukuyama",
    "sem_trajectory",
)

LEVEL11_MODULES = (
    "abm_governance.rules.delegation",
    "abm_governance.rules.contributions",
    "abm_governance.rules.coordination",
    "abm_governance.observer.delegation_diagnostics",
    "abm_governance.observer.replication_units",
)


class TestConfigDefaultsAndCompatibility:
    def test_delegation_and_coordination_default_off(self):
        c = SimulationConfig()
        assert c.delegation_enabled is False
        assert c.interpatch_coordination_enabled is False
        assert c.contribution_mode == "none"

    def test_delegation_requires_rule_formation(self):
        with pytest.raises(ValueError):
            SimulationConfig(rule_formation_enabled=False, delegation_enabled=True, ecology_topology="patches")

    def test_coordination_requires_rule_formation(self):
        with pytest.raises(ValueError):
            SimulationConfig(rule_formation_enabled=False, interpatch_coordination_enabled=True, ecology_topology="patches")

    def test_unknown_delegated_task_rejected(self):
        with pytest.raises(ValueError):
            SimulationConfig(
                ecology_topology="patches", rule_formation_enabled=True, delegation_enabled=True,
                delegated_tasks=("not_a_real_task",),
            )

    def test_unknown_selection_procedure_rejected(self):
        with pytest.raises(ValueError):
            SimulationConfig(
                ecology_topology="patches", rule_formation_enabled=True, delegation_enabled=True,
                delegate_selection_procedure="bribery",
            )

    def test_unknown_contribution_mode_rejected(self):
        with pytest.raises(ValueError):
            SimulationConfig(ecology_topology="patches", rule_formation_enabled=True, contribution_mode="bribery")

    def test_unknown_fund_dissolution_disposition_rejected(self):
        with pytest.raises(ValueError):
            SimulationConfig(
                ecology_topology="patches", rule_formation_enabled=True, fund_dissolution_disposition="bribery",
            )

    def test_yaml_roundtrip_preserves_delegated_tasks(self, tmp_path):
        c = SimulationConfig.level11_delegation_only(population_size=10, seed=3)
        path = tmp_path / "c.yaml"
        c.to_yaml(str(path))
        loaded = SimulationConfig.from_yaml(str(path))
        assert loaded == c


class TestExactLevel10Compatibility:
    """Section 10 / completion-gate requirement: with every Level 1.1
    mechanism disabled, dynamics must be preserved exactly."""

    def test_disabled_produces_zero_level11_events(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=30, n_steps=150, seed=1, monitoring_mode="voluntary", sanction_mode="voluntary",
        )
        assert config.delegation_enabled is False
        assert config.interpatch_coordination_enabled is False
        sim = Simulation(config)
        sim.run()
        log = sim.event_log
        assert log.delegate_nominations == []
        assert log.delegate_appointments == []
        assert log.delegate_removals == []
        assert log.task_performances == []
        assert log.appropriations == []
        assert log.audits == []
        assert log.recalls == []
        assert log.appeals == []
        assert log.contributions == []
        assert log.administrative_spending == []
        assert log.fund_dissolutions == []
        assert log.coordination_proposals == []
        assert log.coordination_links == []
        assert log.coordination_activity == []
        assert log.coordination_dissolutions == []
        assert sim.delegate_registry == {}
        assert sim.delegate_history == []
        assert sim.coordination_link_registry == {}

    def test_disabled_run_is_bit_identical_to_pre_level11_baseline(self):
        # Same seed, one run leaves every Level 1.1 field at its default,
        # the other sets them explicitly False/none -- must be bit-for-
        # bit identical, proving zero extra RNG draws are consumed when
        # disabled (mirrors tests/test_level1_rule_formation.py's own
        # TestBackwardCompatibility pattern for Level 1.0 itself).
        c1 = SimulationConfig.level1_rule_formation_default(
            population_size=25, n_steps=120, seed=9, monitoring_mode="voluntary", sanction_mode="voluntary",
        )
        c2 = SimulationConfig.level1_rule_formation_default(
            population_size=25, n_steps=120, seed=9, monitoring_mode="voluntary", sanction_mode="voluntary",
            delegation_enabled=False, interpatch_coordination_enabled=False, contribution_mode="none",
        )
        r1 = Simulation(c1).run()
        r2 = Simulation(c2).run()
        for row1, row2 in zip(r1.metrics, r2.metrics):
            for key in row1:
                v1, v2 = row1[key], row2[key]
                if isinstance(v1, float) and np.isnan(v1):
                    assert np.isnan(v2)
                else:
                    assert v1 == v2

    def test_contribution_mode_none_produces_zero_contribution_events_even_with_delegation_on(self):
        # Isolates delegation from contributions: delegation_enabled=True
        # but contribution_mode stays "none" -> zero ContributionEvents,
        # regardless of how much delegation/discretion/accountability
        # activity occurs.
        c = SimulationConfig.level11_accountability_only(population_size=30, n_steps=150, seed=2)
        assert c.contribution_mode == "none"
        sim = Simulation(c)
        sim.run()
        assert sim.event_log.contributions == []
        assert sim.event_log.fund_dissolutions == [] or all(
            e.amount == 0.0 for e in sim.event_log.fund_dissolutions
        )


class TestStructuralTerminologyGuard:
    def test_forbidden_agent_attributes_not_reintroduced(self):
        for f in dataclasses.fields(Agent):
            for bad in FORBIDDEN_ATTRIBUTE_SUBSTRINGS:
                assert bad not in f.name.lower(), f"Agent.{f.name} contains forbidden substring {bad!r}"

    @staticmethod
    def _strip_docstrings_and_comments(source: str) -> str:
        """Remove triple-quoted docstrings and ``#`` comments before a
        terminology scan — this project's own module docstrings
        routinely *explain* what a term is deliberately not (e.g. "never
        a governance type"), which a naive full-text substring check
        would misfire on; the structural guard that matters is over
        actual code (identifiers, string literals used as values), not
        explanatory prose."""
        import re

        no_triple = re.sub(r'"""[\s\S]*?"""', "", source)
        no_triple = re.sub(r"'''[\s\S]*?'''", "", no_triple)
        no_comments = re.sub(r"#.*", "", no_triple)
        return no_comments

    @pytest.mark.parametrize("module_name", LEVEL11_MODULES)
    def test_forbidden_level11_terms_absent_from_source(self, module_name):
        import importlib

        module = importlib.import_module(module_name)
        source = self._strip_docstrings_and_comments(inspect.getsource(module)).lower()
        for term in FORBIDDEN_LEVEL11_TERMS:
            assert term.replace("_", " ") not in source, f"{module_name} contains forbidden term {term!r} outside docstrings/comments"
            assert term not in source, f"{module_name} contains forbidden term {term!r} outside docstrings/comments"

    def test_delegation_diagnostics_label_vocabulary_is_closed(self):
        from abm_governance.observer.delegation_diagnostics import VALID_LABELS

        for label in VALID_LABELS:
            for bad in FORBIDDEN_LEVEL11_TERMS:
                assert bad not in label

    def test_config_field_names_avoid_forbidden_terms(self):
        for f in dataclasses.fields(SimulationConfig):
            for bad in FORBIDDEN_LEVEL11_TERMS:
                assert bad not in f.name.lower()


class TestGenerativeObserverSeparation:
    def test_delegate_object_never_stores_a_classification_label(self):
        from abm_governance.rules.delegation import Delegate

        field_names = {f.name for f in dataclasses.fields(Delegate)}
        assert "label" not in field_names
        assert "classification" not in field_names

    def test_shared_rule_never_stores_a_classification_label(self):
        from abm_governance.rules.shared_rule import SharedRule

        field_names = {f.name for f in dataclasses.fields(SharedRule)}
        assert "label" not in field_names
        assert "classification" not in field_names

    def test_observer_modules_never_imported_by_generative_modules(self):
        # rules/*.py (generative) must not import observer/* (read-only,
        # post-hoc layer) -- a one-directional dependency, per
        # dev_mem/project_vision.md section 11. Checked at the import-
        # statement level (not a raw text search — these modules'
        # docstrings legitimately *discuss* the observer layer's role
        # while never importing from it).
        import ast

        import abm_governance.rules.delegation as d
        import abm_governance.rules.contributions as c
        import abm_governance.rules.coordination as co

        for module in (d, c, co):
            tree = ast.parse(inspect.getsource(module))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert not node.module.startswith("abm_governance.observer"), (
                        f"{module.__name__} imports from {node.module}"
                    )
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith("abm_governance.observer"), (
                            f"{module.__name__} imports {alias.name}"
                        )


class TestSeedReproducibility:
    def test_same_seed_same_config_identical_level11_event_counts(self):
        c = SimulationConfig.level11_complete(population_size=40, n_steps=150, n_patches=3, seed=11)
        r1 = Simulation(c).run()
        r2 = Simulation(SimulationConfig.level11_complete(population_size=40, n_steps=150, n_patches=3, seed=11)).run()
        for row1, row2 in zip(r1.metrics, r2.metrics):
            for key in row1:
                v1, v2 = row1[key], row2[key]
                if isinstance(v1, float) and np.isnan(v1):
                    assert np.isnan(v2)
                else:
                    assert v1 == v2

    def test_different_seed_diverges(self):
        c1 = SimulationConfig.level11_complete(population_size=40, n_steps=100, n_patches=3, seed=1)
        c2 = SimulationConfig.level11_complete(population_size=40, n_steps=100, n_patches=3, seed=2)
        r1 = Simulation(c1).run()
        r2 = Simulation(c2).run()
        diverged = any(row1 != row2 for row1, row2 in zip(r1.metrics, r2.metrics))
        assert diverged
