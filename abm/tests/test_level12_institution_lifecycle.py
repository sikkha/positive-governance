"""Level 1.2, Work Package A: institution lifecycle tracking
(``rules/institution.py::institution_lifecycle_round`` and its wiring
into ``Simulation._institution_lifecycle_round``) -- creation, amendment
detection, and extinction, derived from the pre-existing
``SharedRule``/``rule_registry`` state each step."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog
from abm_governance.rules.institution import components_from_rule, institution_lifecycle_round
from abm_governance.rules.shared_rule import RuleParameters, SharedRule
from abm_governance.simulation import Simulation


def _rule(rule_id=0, patch_id=0, lineage_id=0, members=(0, 1, 2), institution_overrides=None):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    return SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=0, rule_lineage_id=lineage_id, members=frozenset(members),
        supporters=frozenset(members), institution_overrides=institution_overrides,
    )


class TestInstitutionLifecycleRoundUnit:
    def test_new_rule_creates_a_fresh_institution_record(self):
        registry = {}
        rule = _rule()
        institution_lifecycle_round(0, {0: rule}, registry, SimulationConfig.level1_rule_formation_default(), EventLog())
        assert 0 in registry
        rec = registry[0]
        assert rec.institution_id == 0
        assert rec.lineage_id == 0
        assert rec.parent_institution_id is None
        assert rec.origin_mechanism == "fresh_proposal"
        assert not rec.extinct

    def test_amendment_detected_when_override_changes(self):
        registry = {}
        config = SimulationConfig.level1_rule_formation_default()
        rule = _rule()
        institution_lifecycle_round(0, {0: rule}, registry, config, EventLog())
        assert registry[0].amendment_history == ()

        rule.institution_overrides = {"contribution_mechanism": "equal"}
        institution_lifecycle_round(1, {0: rule}, registry, config, EventLog())
        assert len(registry[0].amendment_history) == 1
        assert "contribution_mechanism" in registry[0].amendment_history[0]["changed_fields"]

    def test_extinction_recorded_once_and_stops_tracking_amendments(self):
        registry = {}
        config = SimulationConfig.level1_rule_formation_default()
        rule = _rule()
        log = EventLog()
        institution_lifecycle_round(0, {0: rule}, registry, config, log)

        rule.dissolved = True
        rule.dissolution_step = 5
        rule.dissolution_reason = "no_members"
        institution_lifecycle_round(5, {0: rule}, registry, config, log)
        assert registry[0].extinct
        assert registry[0].extinction_time == 5
        assert registry[0].extinction_reason == "no_members"
        assert len(log.institution_extinctions) == 1

        # A further "amendment" after dissolution must not resurrect it.
        rule.institution_overrides = {"contribution_mechanism": "equal"}
        institution_lifecycle_round(6, {0: rule}, registry, config, log)
        assert registry[0].extinct
        assert registry[0].amendment_history == ()
        assert len(log.institution_extinctions) == 1

    def test_reconstruction_links_parent_by_lineage(self):
        registry = {}
        config = SimulationConfig.level1_rule_formation_default()
        parent_rule = _rule(rule_id=0, lineage_id=0)
        institution_lifecycle_round(0, {0: parent_rule}, registry, config, EventLog())

        child_rule = _rule(rule_id=1, lineage_id=1)
        child_rule.parent_rule_lineage_id = 0
        institution_lifecycle_round(1, {0: parent_rule, 1: child_rule}, registry, config, EventLog())
        assert registry[1].origin_mechanism == "reconstruction"
        assert registry[1].parent_institution_id == 0

    def test_components_from_rule_reflects_live_overrides(self):
        config = SimulationConfig.level1_rule_formation_default(contribution_mode="voluntary")
        rule = _rule(institution_overrides={"contribution_mechanism": "equal"})
        c = components_from_rule(rule, config)
        assert c.contribution_mechanism == "equal"
        rule2 = _rule(institution_overrides=None)
        c2 = components_from_rule(rule2, config)
        assert c2.contribution_mechanism == "voluntary"


class TestSimulationIntegration:
    def test_institution_registry_populates_during_a_run(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=20, n_steps=40, n_patches=3, seed=3,
            proposal_probability_mean=0.2, proposal_probability_std=0.02,
        )
        sim = Simulation(config)
        sim.run()
        assert len(sim.institution_registry) >= 1
        # Every currently-active rule must have a tracked, non-extinct
        # institution record; every institution record for a rule_id no
        # longer in rule_registry must be marked extinct.
        for rule_id, rule in sim.rule_registry.items():
            rec = sim.institution_registry[rule_id]
            assert rec.extinct == rule.dissolved

    def test_extinct_institutions_have_no_further_amendments_after_extinction_time(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=20, n_steps=60, n_patches=3, seed=11,
            proposal_probability_mean=0.3, proposal_probability_std=0.02,
        )
        sim = Simulation(config)
        sim.run()
        extinct = [r for r in sim.institution_registry.values() if r.extinct]
        for rec in extinct:
            for entry in rec.amendment_history:
                assert entry["step"] <= rec.extinction_time
