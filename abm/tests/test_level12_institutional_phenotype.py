"""Level 1.2, Section 6: the observer-side institutional phenotype
vector X = (C, E, L, D, M, R, S, F, V, H)."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog
from abm_governance.environment.patches import PatchSystem, ResourcePatch
from abm_governance.observer import institutional_phenotype as ip
from abm_governance.rules import delegation as rd
from abm_governance.rules.institution import InstitutionComponents, InstitutionRecord
from abm_governance.rules.shared_rule import RuleParameters, SharedRule
from abm_governance.simulation import Simulation


def _components(**overrides):
    base = dict(
        proposal_threshold=0.3, adoption_threshold=0.5, contribution_mechanism="voluntary",
        monitoring_allocation=0.4, sanction_procedure=0.4, appeal_procedure=0.2, recall_procedure=0.5,
        delegated_task_distribution=("monitoring",), administrative_fund_rule=0.1, authority_concentration=0.0,
        amendment_threshold=0.5, memory_retention=0.5, succession_procedure="voluntary_approval",
        coordination_link_policy=0.02,
    )
    base.update(overrides)
    return InstitutionComponents(**base)


def _rule(rule_id, patch_id, members, memory=0.0, amendment_count=0, founding_step=0):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    r = SharedRule(rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=founding_step, founder_id=members[0] if members else -1, rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members))
    r.institutional_memory = memory
    r.amendment_count = amendment_count
    return r


class TestNoOpAndMissingnessDiscipline:
    def test_no_active_delegates_yields_nan_capacity(self):
        rec = ip.realized_administrative_capacity({})
        assert np.isnan(rec["value"])

    def test_no_audits_yields_nan_effective_constraint(self):
        rec = ip.effective_constraint_dimension(EventLog())
        assert np.isnan(rec["value"])

    def test_fewer_than_two_institutions_yields_nan_heterogeneity(self):
        rec = ip.within_community_heterogeneity({0: InstitutionRecord(institution_id=0, lineage_id=0, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components())})
        assert np.isnan(rec["value"])

    def test_zero_institutions_yields_zero_reach_not_nan(self):
        rec = ip.institutional_scale_reach({}, n_patches=4)
        assert rec["value"] == 0.0  # a well-defined absence, not missing data


class TestLegitimacyVoluntarySupport:
    def test_full_membership_reports_support_one(self):
        ps = PatchSystem(patches={0: ResourcePatch(patch_id=0, capacity=100.0, regen_rate=0.5, resources=50.0, members=frozenset({1, 2}))}, agent_patch={1: 0, 2: 0})
        rule = _rule(0, 0, (1, 2))
        rec = ip.legitimacy_voluntary_support({0: rule}, ps)
        assert rec["value"] == pytest.approx(1.0)

    def test_partial_membership_reports_fraction(self):
        ps = PatchSystem(patches={0: ResourcePatch(patch_id=0, capacity=100.0, regen_rate=0.5, resources=50.0, members=frozenset({1, 2, 3, 4}))}, agent_patch={1: 0, 2: 0, 3: 0, 4: 0})
        rule = _rule(0, 0, (1, 2))
        rec = ip.legitimacy_voluntary_support({0: rule}, ps)
        assert rec["value"] == pytest.approx(0.5)


class TestWithinCommunityHeterogeneity:
    def test_identical_institutions_have_zero_heterogeneity(self):
        registry = {
            0: InstitutionRecord(institution_id=0, lineage_id=0, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components()),
            1: InstitutionRecord(institution_id=1, lineage_id=1, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components()),
        }
        rec = ip.within_community_heterogeneity(registry)
        assert rec["value"] == pytest.approx(0.0)

    def test_different_institutions_have_positive_heterogeneity(self):
        registry = {
            0: InstitutionRecord(institution_id=0, lineage_id=0, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components(adoption_threshold=0.1)),
            1: InstitutionRecord(institution_id=1, lineage_id=1, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components(adoption_threshold=0.9)),
        }
        rec = ip.within_community_heterogeneity(registry)
        assert rec["value"] > 0.0

    def test_extinct_institutions_excluded(self):
        registry = {
            0: InstitutionRecord(institution_id=0, lineage_id=0, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components(), extinction_time=5, extinction_reason="x"),
            1: InstitutionRecord(institution_id=1, lineage_id=1, parent_institution_id=None, origin_mechanism="fresh_proposal", creation_time=0, components=_components(adoption_threshold=0.9)),
        }
        rec = ip.within_community_heterogeneity(registry)
        assert np.isnan(rec["value"])  # only one surviving


class TestNeverMergedIntoOneScore:
    def test_vector_returns_ten_separate_top_level_keys(self):
        vector = ip.institutional_phenotype_vector(
            EventLog(), {}, {}, {}, None, {}, n_patches=1, initial_population=10, current_step=0,
        )
        assert set(vector.keys()) == set("CELDMRSFVH")

    def test_no_composite_score_key_anywhere(self):
        vector = ip.institutional_phenotype_vector(
            EventLog(), {}, {}, {}, None, {}, n_patches=1, initial_population=10, current_step=0,
        )
        for dim, record in vector.items():
            keys = set(record.keys())
            assert "score" not in keys
            assert "fitness" not in keys


class TestSimulationIntegration:
    def test_vector_computable_after_a_full_run(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=20, n_steps=60, n_patches=3, seed=21,
            proposal_probability_mean=0.3, proposal_probability_std=0.02,
            delegation_enabled=True, interpatch_coordination_enabled=True, coordination_proposal_probability=0.3,
            institutional_scaling_enabled=True,
        )
        sim = Simulation(config)
        sim.run()
        vector = ip.institutional_phenotype_vector(
            sim.event_log, sim.rule_registry, sim.institution_registry, sim.delegate_registry,
            sim.patch_system, sim._coordination_components, config.n_patches, config.population_size,
            config.n_steps,
        )
        assert set(vector.keys()) == set("CELDMRSFVH")
        for dim, record in vector.items():
            if dim == "V":
                assert "ecological" in record and "demographic" in record
            else:
                assert "numerator" in record and "denominator" in record and "value" in record
