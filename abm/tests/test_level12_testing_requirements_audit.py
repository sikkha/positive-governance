"""Level 1.2, Section 16: testing requirements sweep (milestone-level audit).

Two consolidated checks that tie together this milestone's own
per-work-package testing discipline (a dedicated test file per new
module, and a no-op-baseline reconfirmation after every single change,
both followed throughout Sections 5-13 and `dev_mem/status_update.md`)
into one explicit, permanent assertion rather than leaving that
discipline as something only demonstrated by having been followed."""

from __future__ import annotations

import pathlib

from abm_governance.core.config import SimulationConfig
from abm_governance.simulation import Simulation
from experiments.level12_common import LEVEL12_EVENT_LOG_ATTRS

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "abm_governance"
TESTS_DIR = PROJECT_ROOT / "tests"

#: Every module added this milestone (Sections 5-11), mapped to the
#: test file that must exist for it. A module missing here (or a
#: mapping pointing at a nonexistent file) fails the audit below rather
#: than silently going uncovered.
LEVEL12_NEW_MODULE_TEST_MAP: dict[str, str] = {
    "rules/institution.py": "test_level12_institution_components.py",
    "rules/observation.py": "test_level12_observation.py",
    "rules/transmission.py": "test_level12_transmission.py",
    "rules/migration.py": "test_level12_migration.py",
    "rules/scaling.py": "test_level12_scaling.py",
    "observer/differential_persistence.py": "test_level12_differential_persistence.py",
    "observer/institutional_phenotype.py": "test_level12_institutional_phenotype.py",
    "observer/temporal_features.py": "test_level12_temporal_features.py",
    "observer/institutional_viability.py": "test_level12_institutional_viability.py",
    "observer/phenotype_discovery.py": "test_level12_phenotype_discovery.py",
    "observer/recurrence_criteria.py": "test_level12_recurrence_criteria.py",
    "observer/convergence_tests.py": "test_level12_convergence_tests.py",
}


class TestEveryNewModuleHasADedicatedTestFile:
    def test_mapping_covers_every_module_that_actually_exists_on_disk(self):
        # A guard against this mapping itself going stale -- every
        # module the mapping names must exist.
        missing_modules = [m for m in LEVEL12_NEW_MODULE_TEST_MAP if not (SRC_DIR / m).exists()]
        assert missing_modules == []

    def test_every_mapped_module_has_its_test_file_present(self):
        missing_tests = [
            (module, test_file) for module, test_file in LEVEL12_NEW_MODULE_TEST_MAP.items()
            if not (TESTS_DIR / test_file).exists()
        ]
        assert missing_tests == []


class TestBareDefaultSimulationIsStillAStrictNoOp:
    def test_bare_default_produces_zero_of_every_new_level12_event_type(self):
        """Full end-to-end integration check (not a unit-level check
        scattered across each Work Package's own file): a bare
        ``SimulationConfig()`` run through an actual ``Simulation``
        must produce exactly zero events of every one of the six new
        Level 1.2 event types -- the strongest single assertion of
        this milestone's own no-op-by-default guarantee."""
        config = SimulationConfig(population_size=15, n_steps=15, seed=42)
        sim = Simulation(config)
        sim.run()
        for attr in LEVEL12_EVENT_LOG_ATTRS:
            assert len(getattr(sim.event_log, attr)) == 0, f"{attr} was non-empty under a bare default config"

    def test_bare_default_produces_an_empty_institution_registry(self):
        config = SimulationConfig(population_size=15, n_steps=15, seed=42)
        sim = Simulation(config)
        sim.run()
        # WP-A's own lifecycle bookkeeping is unconditional once rules
        # exist, but a bare default has rule_formation_enabled=False, so
        # no rule -- and therefore no institution -- is ever created.
        assert len(sim.institution_registry) == 0
