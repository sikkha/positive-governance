"""Level 1.2, Work Package A: institutional component representation --
serialization, deterministic hashing, lineage, the four separate
distance metrics, and a direct behavioral check that
``SharedRule.institution_overrides`` is genuinely live (not merely
stored) at its wired call sites, while remaining a strict no-op when
absent (the Level 1.1b compatibility baseline already covers the
no-op case at the full-suite level; this file adds a targeted,
override-present positive check)."""

from __future__ import annotations

import copy

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import (
    VALID_CONTRIBUTION_MODES,
    VALID_DELEGATE_SELECTION_PROCEDURES,
    VALID_DELEGATION_TASKS,
    SimulationConfig,
)
from abm_governance.core.events import EventLog
from abm_governance.rules import contributions as rc
from abm_governance.rules.institution import (
    INSTITUTION_COMPONENT_NAMES,
    InstitutionComponents,
    InstitutionRecord,
    behavioral_distance,
    functional_distance,
    lineage_distance,
    sample_institution_components,
    structural_distance,
)
from abm_governance.rules.shared_rule import RuleParameters, SharedRule


def _components(**overrides) -> InstitutionComponents:
    base = dict(
        proposal_threshold=0.3,
        adoption_threshold=0.5,
        contribution_mechanism="voluntary",
        monitoring_allocation=0.4,
        sanction_procedure=0.4,
        appeal_procedure=0.2,
        recall_procedure=0.5,
        delegated_task_distribution=("monitoring",),
        administrative_fund_rule=0.1,
        authority_concentration=0.0,
        amendment_threshold=0.5,
        memory_retention=0.5,
        succession_procedure="voluntary_approval",
        coordination_link_policy=0.02,
    )
    base.update(overrides)
    return InstitutionComponents(**base)


class TestInstitutionComponentsValidity:
    def test_all_fourteen_named_fields_present(self):
        c = _components()
        d = c.as_dict()
        assert set(d.keys()) == set(INSTITUTION_COMPONENT_NAMES)
        assert len(INSTITUTION_COMPONENT_NAMES) == 14

    def test_numeric_component_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            _components(adoption_threshold=1.5)
        with pytest.raises(ValueError):
            _components(sanction_procedure=-0.1)

    def test_empty_delegated_task_distribution_rejected(self):
        with pytest.raises(ValueError):
            _components(delegated_task_distribution=())

    def test_to_overrides_excludes_ruleparameters_backed_components(self):
        c = _components()
        overrides = c.to_overrides()
        assert "adoption_threshold" not in overrides
        assert "amendment_threshold" not in overrides
        assert "monitoring_allocation" not in overrides
        assert "sanction_procedure" not in overrides
        assert set(overrides.keys()) == {
            "contribution_mechanism", "appeal_procedure", "recall_procedure",
            "delegated_task_distribution", "administrative_fund_rule",
            "memory_retention", "succession_procedure", "coordination_link_policy",
        }


class TestDeterministicHashing:
    def test_identical_components_hash_identically(self):
        a, b = _components(), _components()
        assert a.component_hash() == b.component_hash()

    def test_different_components_hash_differently(self):
        a, b = _components(), _components(adoption_threshold=0.6)
        assert a.component_hash() != b.component_hash()

    def test_hash_stable_across_repeated_calls(self):
        c = _components()
        assert c.component_hash() == c.component_hash()


class TestSerialization:
    def test_as_dict_round_trips_into_constructor(self):
        c = _components()
        d = c.as_dict()
        d["delegated_task_distribution"] = tuple(d["delegated_task_distribution"])
        c2 = InstitutionComponents(**d)
        assert c2.component_hash() == c.component_hash()


class TestSampleInstitutionComponents:
    def test_deterministic_given_same_seed(self):
        rng1 = np.random.default_rng(7)
        rng2 = np.random.default_rng(7)
        c1 = sample_institution_components(
            {}, rng1, contribution_modes=VALID_CONTRIBUTION_MODES,
            succession_procedures=VALID_DELEGATE_SELECTION_PROCEDURES,
            delegation_tasks=VALID_DELEGATION_TASKS,
        )
        c2 = sample_institution_components(
            {}, rng2, contribution_modes=VALID_CONTRIBUTION_MODES,
            succession_procedures=VALID_DELEGATE_SELECTION_PROCEDURES,
            delegation_tasks=VALID_DELEGATION_TASKS,
        )
        assert c1.component_hash() == c2.component_hash()

    def test_uses_proposer_traits_when_available(self):
        rng = np.random.default_rng(3)
        c = sample_institution_components(
            {"adoption_threshold": 0.9, "sanction_procedure": 0.05}, rng,
            contribution_modes=VALID_CONTRIBUTION_MODES,
            succession_procedures=VALID_DELEGATE_SELECTION_PROCEDURES,
            delegation_tasks=VALID_DELEGATION_TASKS,
        )
        assert c.adoption_threshold == pytest.approx(0.9)
        assert c.sanction_procedure == pytest.approx(0.05)

    def test_authority_concentration_never_generatively_sampled(self):
        # Work Package F: descriptive-only, must always start at a fixed,
        # non-drawn baseline -- never influenced by the rng stream.
        rng1 = np.random.default_rng(1)
        rng2 = np.random.default_rng(999)
        c1 = sample_institution_components(
            {}, rng1, contribution_modes=VALID_CONTRIBUTION_MODES,
            succession_procedures=VALID_DELEGATE_SELECTION_PROCEDURES,
            delegation_tasks=VALID_DELEGATION_TASKS,
        )
        c2 = sample_institution_components(
            {}, rng2, contribution_modes=VALID_CONTRIBUTION_MODES,
            succession_procedures=VALID_DELEGATE_SELECTION_PROCEDURES,
            delegation_tasks=VALID_DELEGATION_TASKS,
        )
        assert c1.authority_concentration == c2.authority_concentration == 0.0


class TestInstitutionRecordLineage:
    def _record(self):
        return InstitutionRecord(
            institution_id=1, lineage_id=1, parent_institution_id=None,
            origin_mechanism="fresh_proposal", creation_time=0,
            components=_components(), active_jurisdiction=frozenset({0}),
        )

    def test_amendment_does_not_mutate_original(self):
        rec = self._record()
        new_components = _components(adoption_threshold=0.7)
        amended = rec.with_amendment(5, new_components, ("adoption_threshold",))
        assert rec.components.adoption_threshold == 0.5
        assert amended.components.adoption_threshold == 0.7
        assert rec.amendment_history == ()
        assert len(amended.amendment_history) == 1
        assert amended.amendment_history[0]["step"] == 5
        assert amended.amendment_history[0]["changed_fields"] == ["adoption_threshold"]

    def test_amendment_history_is_append_only_across_multiple_amendments(self):
        rec = self._record()
        rec = rec.with_amendment(5, _components(adoption_threshold=0.6), ("adoption_threshold",))
        rec = rec.with_amendment(9, _components(adoption_threshold=0.6, amendment_threshold=0.8), ("amendment_threshold",))
        assert len(rec.amendment_history) == 2
        assert [e["step"] for e in rec.amendment_history] == [5, 9]

    def test_transmission_record_appended_not_replaced(self):
        rec = self._record()
        rec = rec.with_transmission_record({"step": 3, "source": 1, "receiver": 2})
        rec = rec.with_transmission_record({"step": 8, "source": 2, "receiver": 3})
        assert len(rec.transmission_history) == 2

    def test_extinction_sets_time_and_reason_and_is_terminal(self):
        rec = self._record()
        assert not rec.extinct
        rec = rec.with_extinction(12, "no_members")
        assert rec.extinct
        assert rec.extinction_time == 12
        assert rec.extinction_reason == "no_members"

    def test_record_hash_changes_with_components_but_not_with_unrelated_copy(self):
        rec = self._record()
        rec2 = copy.deepcopy(rec)
        assert rec.record_hash() == rec2.record_hash()
        rec3 = rec.with_amendment(1, _components(adoption_threshold=0.99), ("adoption_threshold",))
        assert rec.record_hash() != rec3.record_hash()


class TestDistanceMetricsAreSeparate:
    def test_structural_distance_zero_for_identical_bundles(self):
        assert structural_distance(_components(), _components()) == 0.0

    def test_structural_distance_symmetric_and_positive_for_different_bundles(self):
        a, b = _components(), _components(adoption_threshold=0.9, contribution_mechanism="proportional")
        d_ab = structural_distance(a, b)
        d_ba = structural_distance(b, a)
        assert d_ab == pytest.approx(d_ba)
        assert d_ab > 0.0

    def test_lineage_distance_shared_lineage_is_zero(self):
        base_kwargs = dict(parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components())
        a = InstitutionRecord(institution_id=1, lineage_id=5, **base_kwargs)
        b = InstitutionRecord(institution_id=2, lineage_id=5, **base_kwargs)
        assert lineage_distance(a, b) == 0.0

    def test_lineage_distance_parent_child_is_intermediate(self):
        a = InstitutionRecord(institution_id=1, lineage_id=1, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components())
        b = InstitutionRecord(institution_id=2, lineage_id=2, parent_institution_id=1, origin_mechanism="component_transmission", creation_time=1, components=_components())
        assert lineage_distance(a, b) == 0.25
        assert lineage_distance(b, a) == 0.25

    def test_lineage_distance_unrelated_is_one(self):
        a = InstitutionRecord(institution_id=1, lineage_id=1, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components())
        b = InstitutionRecord(institution_id=2, lineage_id=2, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components())
        assert lineage_distance(a, b) == 1.0

    def test_behavioral_distance_ignores_none_entries(self):
        assert behavioral_distance({"a": 0.5, "b": None}, {"a": 0.7, "b": 0.9}) == pytest.approx(0.2)

    def test_behavioral_distance_nan_when_nothing_comparable(self):
        assert np.isnan(behavioral_distance({"a": None}, {"a": None}))

    def test_functional_distance_independent_of_behavioral_distance(self):
        # Same event rates (behavioral identical) but different functional
        # outcomes -- the two metrics must be able to disagree.
        beh = behavioral_distance({"compliance_rate": 0.8}, {"compliance_rate": 0.8})
        func = functional_distance({"ecological_viability": 0.9}, {"ecological_viability": 0.1})
        assert beh == 0.0
        assert func == pytest.approx(0.8)


# --- Behavioral liveness of SharedRule.institution_overrides ---------------


def _agent(agent_id, patch_id=0, resources=20.0, **overrides):
    a = Agent(
        agent_id=agent_id, resources=resources, coercive_capability=0.0, policy=make_policy("tit_for_tat"),
        observation_accuracy=1.0, learning_rate=0.1, forgiveness=0.1, risk_sensitivity=0.5, exit_cost=0.1,
    )
    a.patch_id = patch_id
    a.ecological_policy = EcologicalPolicy(0.5, 0.3, 0.0)
    for k, v in overrides.items():
        setattr(a, k, v)
    return a


def _rule(rule_id=0, patch_id=0, members=(0, 1, 2), founder=0, fund=0.0, institution_overrides=None):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    r = SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=founder, rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )
    r.fund = fund
    r.institution_overrides = institution_overrides
    return r


class TestInstitutionOverridesAreLiveNotJustStored:
    def test_no_override_matches_global_config_mode(self):
        rule = _rule(institution_overrides=None)
        registry = {0: rule}
        agents = {0: _agent(0), 1: _agent(1), 2: _agent(2)}
        config = SimulationConfig.level1_rule_formation_default(contribution_mode="equal", contribution_amount=1.0, contribution_period_steps=1)
        log = EventLog()
        rc.contribution_round(0, registry, agents, config, np.random.default_rng(0), log)
        assert all(ev.mode == "equal" for ev in log.contributions)

    def test_override_changes_effective_mode_even_though_global_mode_differs(self):
        # Global config mode is "none" (a strict no-op globally), but this
        # one institution's override makes it "equal" -- proving the
        # override is read, not merely stored inertly.
        rule = _rule(institution_overrides={"contribution_mechanism": "equal"})
        registry = {0: rule}
        agents = {0: _agent(0, resources=10.0), 1: _agent(1, resources=10.0), 2: _agent(2, resources=10.0)}
        config = SimulationConfig.level1_rule_formation_default(contribution_mode="none", contribution_amount=1.0, contribution_period_steps=1)
        log = EventLog()
        rc.contribution_round(0, registry, agents, config, np.random.default_rng(0), log)
        assert len(log.contributions) == 3
        assert all(ev.mode == "equal" for ev in log.contributions)
        assert rule.fund == pytest.approx(3.0)

    def test_two_institutions_same_step_can_run_different_mechanisms(self):
        # No shared "governance type" tag anywhere -- two co-existing
        # institutions with independently different mechanisms, purely
        # via their own override dicts.
        rule_a = _rule(rule_id=0, patch_id=0, members=(0,), institution_overrides={"contribution_mechanism": "equal"})
        rule_b = _rule(rule_id=1, patch_id=1, members=(1,), institution_overrides={"contribution_mechanism": "voluntary"})
        registry = {0: rule_a, 1: rule_b}
        agents = {0: _agent(0, resources=10.0, contribution_willingness=1.0), 1: _agent(1, patch_id=1, resources=10.0, contribution_willingness=0.0)}
        config = SimulationConfig.level1_rule_formation_default(contribution_mode="none", contribution_amount=1.0, contribution_period_steps=1)
        log = EventLog()
        rc.contribution_round(0, registry, agents, config, np.random.default_rng(0), log)
        modes = {ev.rule_id: ev.mode for ev in log.contributions}
        assert modes[0] == "equal"
        assert modes[1] == "voluntary"
