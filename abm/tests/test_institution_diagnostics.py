"""Level 1.0, Work Packages J/K: observer metrics and proto-institution
classification (``observer/institution_diagnostics.py``)."""

from __future__ import annotations

from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog, MembershipEvent, RuleProposalEvent
from abm_governance.observer import institution_diagnostics as idg
from abm_governance.rules.shared_rule import RuleParameters
from abm_governance.rules.shared_rule import SharedRule
from abm_governance.simulation import Simulation


def _rule(**overrides):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    kwargs = dict(
        rule_id=0, patch_id=0, parameters=params, founding_step=0, founder_id=0,
        rule_lineage_id=0, members=frozenset({0, 1, 2}),
    )
    kwargs.update(overrides)
    return SharedRule(**kwargs)


class TestClassification:
    def test_no_proposal_ever(self):
        result = idg.classify_rule(None, EventLog(), patch_id=0, final_step=100)
        assert result["label"] == "no_proposal"

    def test_proposal_rejected(self):
        log = EventLog()
        log.rule_proposals.append(
            RuleProposalEvent(step=0, patch_id=0, proposer=0, rule_lineage_id=0, extraction_ceiling=0.3,
                               maintenance_requirement=0.4, monitoring_intensity=0.5, sanction_magnitude=0.5,
                               adoption_threshold=0.5, amendment_threshold=0.5)
        )
        result = idg.classify_rule(None, log, patch_id=0, final_step=100)
        assert result["label"] == "proposal_rejected"

    def test_short_duration_is_short_lived_convention(self):
        rule = _rule(founding_step=90, dissolved=True, dissolution_step=95)
        result = idg.classify_rule(rule, EventLog(), patch_id=0, final_step=200, min_duration_steps=30)
        assert result["label"] == "short_lived_convention"

    def test_founder_still_member_is_founder_dependent(self):
        rule = _rule(founding_step=0, members=frozenset({0, 1, 2}))  # founder (0) still a member
        log = EventLog()
        result = idg.classify_rule(rule, log, patch_id=0, final_step=200, min_duration_steps=30)
        assert result["label"] == "founder_dependent_arrangement"

    def test_valid_label_vocabulary_only(self):
        for label in ("no_proposal", "proposal_rejected", "short_lived_convention",
                      "founder_dependent_arrangement", "proto_institution",
                      "persistent_proto_institution", "dissolved", "reconstructed", "unclassified"):
            assert label in idg.VALID_LABELS
        forbidden = ("government", "state", "democracy", "authoritarian", "rule_of_law")
        for label in idg.VALID_LABELS:
            for bad in forbidden:
                assert bad not in label.lower()

    def test_reconstruction_takes_precedence_in_label(self):
        rule = _rule(
            founding_step=100, founder_id=0, members=frozenset({1, 2, 3}),
            rule_lineage_id=5, parent_rule_lineage_id=1,
        )
        log = EventLog()
        log.rule_proposals.append(
            RuleProposalEvent(step=100, patch_id=0, proposer=1, rule_lineage_id=5, extraction_ceiling=0.3,
                               maintenance_requirement=0.4, monitoring_intensity=0.5, sanction_magnitude=0.5,
                               adoption_threshold=0.5, amendment_threshold=0.5,
                               origin="mutation", parent_rule_lineage_id=1)
        )
        log.memberships.extend([
            MembershipEvent(step=101, patch_id=0, rule_id=0, agent=1, kind="join"),
            MembershipEvent(step=102, patch_id=0, rule_id=0, agent=2, kind="join"),
        ])
        result = idg.classify_rule(rule, log, patch_id=0, final_step=250, min_duration_steps=30)
        assert result["label"] == "reconstructed"


class TestLineageChain:
    def test_chain_follows_parent_links(self):
        original = _rule(rule_id=0, rule_lineage_id=1, founding_step=0)
        reconstruction = _rule(rule_id=1, rule_lineage_id=2, founding_step=100, parent_rule_lineage_id=1)
        unrelated = _rule(rule_id=2, rule_lineage_id=3, founding_step=50)
        chain = idg.lineage_chain(1, [original, reconstruction, unrelated])
        assert [r.rule_lineage_id for r in chain] == [1, 2]


class TestMetricsIntegration:
    def test_summary_has_all_categories_and_run_end_to_end(self):
        config = SimulationConfig.level1_monitoring_plus_voluntary_sanction(population_size=24, n_steps=200, seed=9)
        sim = Simulation(config)
        sim.run()
        all_rules = list(sim.rule_registry.values()) + list(sim._last_dissolved_rule_by_patch.values())
        summary = idg.summarize_institutional_metrics(sim.agents, sim.event_log, all_rules, config.n_steps - 1)
        assert set(summary.keys()) == {
            "formation", "persistence", "membership", "compliance_enforcement", "welfare", "social_effects",
        }

    def test_metrics_are_pure_no_mutation_of_inputs(self):
        config = SimulationConfig.level1_rule_formation_default(population_size=24, n_steps=100, seed=3)
        sim = Simulation(config)
        sim.run()
        all_rules = list(sim.rule_registry.values())
        before = len(sim.event_log.rule_proposals)
        idg.summarize_institutional_metrics(sim.agents, sim.event_log, all_rules, config.n_steps - 1)
        assert len(sim.event_log.rule_proposals) == before
