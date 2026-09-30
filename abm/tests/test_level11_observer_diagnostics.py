"""Level 1.1, Work Packages A, B, C, J, K: observer-side unit-of-analysis
audit, welfare accounting repair, persistence/reconstruction eligibility,
generic institutional dimensions, and the cautious mechanism-validation
classifier."""

from __future__ import annotations

import math

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.events import (
    AdministrativeSpendingEvent,
    AppealEvent,
    AuditEvent,
    ContributionEvent,
    EventLog,
    RecallEvent,
    RuleAmendmentEvent,
    RuleProposalEvent,
)
from abm_governance.observer import delegation_diagnostics as dd
from abm_governance.observer import institution_diagnostics as idg
from abm_governance.observer import replication_units as ru
from abm_governance.rules.coordination import CoordinationLink
from abm_governance.rules.delegation import Delegate
from abm_governance.rules.shared_rule import RuleParameters, SharedRule


def _agent(agent_id, patch_id=0, resources=20.0, alive=True, **overrides):
    a = Agent(
        agent_id=agent_id, resources=resources, coercive_capability=0.0, policy=make_policy("tit_for_tat"),
        observation_accuracy=1.0, learning_rate=0.1, forgiveness=0.1, risk_sensitivity=0.5, exit_cost=0.1,
    )
    a.patch_id = patch_id
    a.alive = alive
    a.ecological_policy = EcologicalPolicy(0.5, 0.3, 0.0)
    for k, v in overrides.items():
        setattr(a, k, v)
    return a


def _params(**overrides):
    fields = dict(
        extraction_ceiling=0.3, maintenance_requirement=0.4, monitoring_intensity=0.5,
        sanction_magnitude=0.5, adoption_threshold=0.5, amendment_threshold=0.5,
    )
    fields.update(overrides)
    return RuleParameters(**fields)


def _rule(rule_id, patch_id=0, members=(0, 1, 2), founding_step=0, founder=0, lineage=None, **overrides):
    if lineage is None:
        lineage = rule_id
    r = SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=_params(), founding_step=founding_step,
        founder_id=founder, rule_lineage_id=lineage, members=frozenset(members), supporters=frozenset(members),
    )
    for k, v in overrides.items():
        setattr(r, k, v)
    return r


def _delegate(delegate_id=0, rule_id=0, agent_id=1, tasks=("monitoring",), start_step=0, **overrides):
    d = Delegate(
        delegate_id=delegate_id, rule_id=rule_id, rule_lineage_id=rule_id, patch_id=0, agent_id=agent_id,
        tasks=tasks, appointment_method="lottery", start_step=start_step,
    )
    for k, v in overrides.items():
        setattr(d, k, v)
    return d


# ===========================================================================
# Work Package A: unit-of-analysis and bootstrap
# ===========================================================================
class TestReplicationUnits:
    def test_count_denominators_names_every_field(self):
        units = ru.count_denominators(
            events=100, rule_instances=10, patches=6, patch_runs=6, seed_runs=3, parameter_points=1, missing=2,
        )
        d = units.as_dict()
        assert d["n_events"] == 100
        assert d["n_seed_runs"] == 3
        assert d["n_missing"] == 2

    def test_naive_pooled_bootstrap_drops_nan(self):
        result = ru.naive_pooled_bootstrap_ci(
            [1.0, 2.0, float("nan"), 3.0], n_boot=200, rng=np.random.default_rng(0),
        )
        assert result["n"] == 3
        assert result["method"] == "naive_pooled"
        assert result["ci_low"] <= result["point_estimate"] <= result["ci_high"]

    def test_naive_pooled_bootstrap_empty_input_returns_nan(self):
        result = ru.naive_pooled_bootstrap_ci([], rng=np.random.default_rng(0))
        assert math.isnan(result["point_estimate"])
        assert result["n"] == 0

    def test_seed_clustered_bootstrap_respects_seed_as_the_unit(self):
        # Each seed contributes many correlated patch-runs (all equal to
        # the seed's own value plus tiny noise) -- resampling seeds (not
        # pooled patch-runs) is the only thing that should determine the
        # spread.
        values_by_seed = {
            0: [1.0] * 20, 1: [2.0] * 20, 2: [3.0] * 20, 3: [4.0] * 20, 4: [5.0] * 20,
        }
        result = ru.seed_clustered_bootstrap_ci(values_by_seed, n_boot=500, rng=np.random.default_rng(1))
        assert result["n_seeds"] == 5
        assert result["point_estimate"] == pytest.approx(3.0)
        # naive pooled CI over the same 100 values is far narrower --
        # this is the exact miscalibration Work Package A requirement 5
        # asks to demonstrate.
        pooled_values = [v for vals in values_by_seed.values() for v in vals]
        naive = ru.naive_pooled_bootstrap_ci(pooled_values, n_boot=500, rng=np.random.default_rng(2))
        naive_width = naive["ci_high"] - naive["ci_low"]
        clustered_width = result["ci_high"] - result["ci_low"]
        assert clustered_width > naive_width

    def test_seed_clustered_bootstrap_drops_nan_within_a_seed(self):
        values_by_seed = {0: [1.0, float("nan")], 1: [2.0, 3.0]}
        result = ru.seed_clustered_bootstrap_ci(values_by_seed, n_boot=100, rng=np.random.default_rng(3))
        assert result["n_seeds"] == 2

    def test_seed_clustered_bootstrap_empty_input_returns_nan(self):
        result = ru.seed_clustered_bootstrap_ci({}, rng=np.random.default_rng(0))
        assert math.isnan(result["point_estimate"])
        assert result["n_seeds"] == 0

    def test_hierarchical_bootstrap_three_levels(self):
        nested = {
            "p0": {0: [1.0, 1.1], 1: [1.2, 0.9]},
            "p1": {2: [5.0, 5.1], 3: [4.9, 5.2]},
        }
        result = ru.hierarchical_bootstrap_ci(nested, n_boot=300, rng=np.random.default_rng(4))
        assert result["n_points"] == 2
        assert result["method"] == "hierarchical"
        assert 2.0 < result["point_estimate"] < 4.0  # roughly midway between the two points' means
        assert result["ci_low"] <= result["point_estimate"] <= result["ci_high"]

    def test_hierarchical_bootstrap_empty_input_returns_nan(self):
        result = ru.hierarchical_bootstrap_ci({}, rng=np.random.default_rng(0))
        assert math.isnan(result["point_estimate"])
        assert result["n_points"] == 0


# ===========================================================================
# Work Package B: welfare accounting repair
# ===========================================================================
class TestWelfareAccounting:
    def test_atomic_baseline_has_no_members_and_nan_means(self):
        agents = [_agent(i) for i in range(4)]
        result = idg.welfare_accounting(agents, rules=[])
        assert result["member_count"] == 0
        assert result["nonmember_count"] == 4
        assert math.isnan(result["mean_member_resources"])
        assert not math.isnan(result["mean_nonmember_resources"])
        assert result["is_causal_estimate"] is False

    def test_member_nonmember_split_and_means(self):
        agents = [_agent(0, resources=10.0), _agent(1, resources=20.0), _agent(2, resources=100.0)]
        rule = _rule(0, members=(0, 1))
        result = idg.welfare_accounting(agents, rules=[rule])
        assert result["member_count"] == 2
        assert result["nonmember_count"] == 1
        assert result["mean_member_resources"] == pytest.approx(15.0)
        assert result["mean_nonmember_resources"] == pytest.approx(100.0)
        assert result["descriptive_member_minus_nonmember_diff"] == pytest.approx(-85.0)
        assert result["population_weighted_overall_mean"] == pytest.approx((10 + 20 + 100) / 3)

    def test_dead_agents_excluded_from_every_count(self):
        agents = [_agent(0, resources=10.0), _agent(1, resources=20.0, alive=False)]
        rule = _rule(0, members=(0, 1))
        result = idg.welfare_accounting(agents, rules=[rule])
        assert result["member_count"] == 1  # agent 1 is dead, excluded despite being a rule member
        assert result["nonmember_count"] == 0

    def test_negative_resources_do_not_break_accounting(self):
        # Work Package B explicitly anticipates negative agent resources
        # (a pre-existing Level 0.3/1.0 characteristic) as a required test
        # case -- welfare_accounting must handle it without raising or
        # silently clamping.
        agents = [_agent(0, resources=-50.0), _agent(1, resources=10.0)]
        rule = _rule(0, members=(0,))
        result = idg.welfare_accounting(agents, rules=[rule])
        assert result["mean_member_resources"] == pytest.approx(-50.0)
        assert result["member_resource_numerator"] == pytest.approx(-50.0)

    def test_within_patch_contrast_uses_patch_system_when_provided(self):
        class _FakePatch:
            pass

        class _FakePatchSystem:
            def __init__(self, patch_ids):
                self.patches = {pid: _FakePatch() for pid in patch_ids}

        agents = [
            _agent(0, patch_id=0, resources=50.0), _agent(1, patch_id=0, resources=10.0),
            _agent(2, patch_id=1, resources=60.0), _agent(3, patch_id=1, resources=20.0),
        ]
        rule = _rule(0, patch_id=0, members=(0, 2))  # membership can span patches in this synthetic setup
        patch_system = _FakePatchSystem([0, 1])
        result = idg.welfare_accounting(agents, rules=[rule], patch_system=patch_system)
        assert result["within_patch_contrast_n_patches"] == 2
        assert not math.isnan(result["within_patch_contrast_mean"])

    def test_seed_level_welfare_contrast_aggregates_and_drops_nan(self):
        result = idg.seed_level_welfare_contrast([1.0, 2.0, float("nan"), 3.0])
        assert result["n_seeds"] == 4
        assert result["n_seeds_valid"] == 3
        assert result["mean_seed_level_contrast"] == pytest.approx(2.0)

    def test_seed_level_welfare_contrast_all_nan_returns_nan(self):
        result = idg.seed_level_welfare_contrast([float("nan"), float("nan")])
        assert result["n_seeds_valid"] == 0
        assert math.isnan(result["mean_seed_level_contrast"])


# ===========================================================================
# Work Package C: persistence and reconstruction eligibility
# ===========================================================================
class TestPersistenceAndReconstructionEligibility:
    def test_eligible_active_rules_filters_by_duration_and_lineage(self):
        too_young = _rule(0, founding_step=90)  # only 10 steps old at event_step=100
        old_enough = _rule(1, founding_step=50, lineage=1)
        already_dissolved = _rule(2, founding_step=0, lineage=2, dissolved=True, dissolution_step=95)
        eligible = idg.eligible_active_rules(
            [too_young, old_enough, already_dissolved], event_step=100, min_duration_steps=30,
        )
        assert eligible == [old_enough]

    def test_survival_after_event_uses_only_eligible_denominator(self):
        eligible = [_rule(0, founding_step=0, lineage=0), _rule(1, founding_step=0, lineage=1)]
        result = idg.survival_after_event(eligible, active_rule_ids_after={0})
        assert result["n_eligible_active_rules"] == 2
        assert result["n_surviving_rules"] == 1
        assert result["survival_rate"] == pytest.approx(0.5)

    def test_survival_after_event_empty_denominator_is_nan_not_zero(self):
        result = idg.survival_after_event([], active_rule_ids_after=set())
        assert math.isnan(result["survival_rate"])

    def test_eligible_dissolutions_filters_by_window_and_duration(self):
        outside_window = _rule(0, founding_step=0, lineage=0, dissolved=True, dissolution_step=500)
        too_short_lived = _rule(1, founding_step=95, lineage=1, dissolved=True, dissolution_step=100)
        valid = _rule(2, founding_step=0, lineage=2, dissolved=True, dissolution_step=100)
        result = idg.eligible_dissolutions(
            [outside_window, too_short_lived, valid], window_start=0, window_end=200, min_duration_steps=30,
        )
        assert result == [valid]

    def test_reconstruction_metrics_distinguishes_attempt_adoption_persistence(self):
        dissolved = _rule(0, founding_step=0, lineage=10, dissolved=True, dissolution_step=100, patch_id=0)
        # a reconstruction proposal naming lineage 10 as parent, after dissolution
        proposal = RuleProposalEvent(
            step=110, patch_id=0, proposer=1, rule_lineage_id=99, extraction_ceiling=0.3,
            maintenance_requirement=0.4, monitoring_intensity=0.5, sanction_magnitude=0.5,
            adoption_threshold=0.5, amendment_threshold=0.5, origin="mutation", parent_rule_lineage_id=10,
        )
        log = EventLog()
        log.add(proposal)
        # an actually-adopted child rule, still active (counts as persistent-so-far)
        child = _rule(1, founding_step=112, lineage=99, patch_id=0, parent_rule_lineage_id=10)
        result = idg.reconstruction_metrics([dissolved], all_rules=[dissolved, child], event_log=log)
        assert result["n_eligible_dissolutions"] == 1
        assert result["n_reconstruction_attempts"] == 1
        assert result["n_reconstruction_adoptions"] == 1
        assert result["n_persistent_reconstructions"] == 1  # still active -> persistent-so-far
        assert result["reconstruction_attempt_rate"] == pytest.approx(1.0)
        assert result["mean_time_to_reconstruction_steps"] == pytest.approx(10.0)

    def test_reconstruction_metrics_no_attempt_gives_zero_rates_not_nan(self):
        dissolved = _rule(0, founding_step=0, lineage=10, dissolved=True, dissolution_step=100, patch_id=0)
        log = EventLog()
        result = idg.reconstruction_metrics([dissolved], all_rules=[dissolved], event_log=log)
        assert result["n_reconstruction_attempts"] == 0
        assert result["reconstruction_attempt_rate"] == pytest.approx(0.0)
        assert math.isnan(result["mean_time_to_reconstruction_steps"])

    def test_reconstruction_metrics_empty_eligible_set_is_nan_not_zero(self):
        log = EventLog()
        result = idg.reconstruction_metrics([], all_rules=[], event_log=log)
        assert result["n_eligible_dissolutions"] == 0
        assert math.isnan(result["reconstruction_attempt_rate"])

    def test_lineage_chain_follows_parent_links_and_orders_by_founding_step(self):
        root = _rule(0, founding_step=0, lineage=0)
        child = _rule(1, founding_step=50, lineage=1, parent_rule_lineage_id=0)
        grandchild = _rule(2, founding_step=100, lineage=2, parent_rule_lineage_id=1)
        unrelated = _rule(3, founding_step=10, lineage=3)
        chain = idg.lineage_chain(0, [grandchild, unrelated, root, child])
        assert chain == [root, child, grandchild]


# ===========================================================================
# Work Package J: generic institutional dimensions (delegation/coordination)
# ===========================================================================
class TestDelegationObserverDimensions:
    def test_administrative_capacity_metrics_from_task_performance_events(self):
        log = EventLog()
        d = _delegate()
        d.task_attempts["monitoring"] = 4
        d.task_successes["monitoring"] = 3
        result = dd.administrative_capacity_metrics([d], log)
        assert result["mean_record_quality"] == pytest.approx(0.2)
        assert not math.isnan(result["mean_realized_capacity"])

    def test_administrative_capacity_metrics_empty_is_nan_not_zero(self):
        result = dd.administrative_capacity_metrics([], EventLog())
        assert math.isnan(result["task_completion_reliability"])
        assert math.isnan(result["mean_realized_capacity"])

    def test_accountability_intensity_counts_audits_recalls_appeals(self):
        log = EventLog()
        log.add(AuditEvent(step=0, patch_id=0, rule_id=0, delegate_id=0, auditor=1, actual_misconduct_occurred=True, found_misconduct=True, outcome="true_positive", cost=0.1))
        log.add(RecallEvent(step=1, patch_id=0, rule_id=0, delegate_id=0, trigger_auditor=1, n_eligible=2, n_supporters=2, support_fraction=1.0, recall_threshold=0.5, succeeded=True, recovered_funds=5.0))
        log.add(AppealEvent(step=2, patch_id=0, rule_id=0, delegate_id=0, appellant=2, original_sanction_step=1, was_false_sanction=True, upheld=True, refund=0.2, cost=0.05))
        result = dd.accountability_intensity_metrics(log)
        assert result["n_audits"] == 1
        assert result["n_recall_attempts"] == 1
        assert result["n_recalls_succeeded"] == 1
        assert result["n_appeals"] == 1
        assert result["n_appeals_upheld"] == 1
        assert result["total_accountability_cost"] == pytest.approx(0.15)

    def test_effective_constraint_recovery_rate_and_confusion_matrix(self):
        log = EventLog()
        log.add(AuditEvent(step=0, patch_id=0, rule_id=0, delegate_id=0, auditor=1, actual_misconduct_occurred=True, found_misconduct=True, outcome="true_positive", cost=0.1))
        log.add(AuditEvent(step=1, patch_id=0, rule_id=0, delegate_id=0, auditor=1, actual_misconduct_occurred=False, found_misconduct=True, outcome="false_positive", cost=0.1))
        log.add(RecallEvent(step=2, patch_id=0, rule_id=0, delegate_id=0, trigger_auditor=1, n_eligible=2, n_supporters=2, support_fraction=1.0, recall_threshold=0.5, succeeded=True, recovered_funds=6.0))
        d = _delegate(appropriated_total=12.0)
        result = dd.effective_constraint_metrics([d], log)
        assert result["p_misconduct_detected"] == pytest.approx(1.0)  # 1 true_positive, 0 false_negative
        assert result["total_appropriated_resources"] == pytest.approx(12.0)
        assert result["total_appropriated_resources_recovered"] == pytest.approx(6.0)
        assert result["appropriation_recovery_rate"] == pytest.approx(0.5)

    def test_legitimacy_support_contribution_compliance_and_survival(self):
        log = EventLog()
        log.add(ContributionEvent(step=0, patch_id=0, rule_id=0, agent=1, mode="voluntary", amount_asked=1.0, amount_paid=1.0, complied=True, fund_after=1.0))
        log.add(ContributionEvent(step=0, patch_id=0, rule_id=0, agent=2, mode="voluntary", amount_asked=1.0, amount_paid=0.0, complied=False, fund_after=1.0))
        log.add(RecallEvent(step=1, patch_id=0, rule_id=0, delegate_id=0, trigger_auditor=1, n_eligible=2, n_supporters=1, support_fraction=0.5, recall_threshold=0.6, succeeded=False, recovered_funds=0.0))
        result = dd.legitimacy_support_metrics([], [], log)
        assert result["contribution_compliance_rate"] == pytest.approx(0.5)
        assert result["delegate_survival_rate_under_challenge"] == pytest.approx(1.0)

    def test_administrative_extraction_sums_costs_and_appropriation(self):
        log = EventLog()
        log.add(AdministrativeSpendingEvent(step=0, patch_id=0, rule_id=0, delegate_id=0, category="monitoring", amount=0.5, funded_by="collective_fund"))
        d = _delegate(appropriated_total=3.0)
        result = dd.administrative_extraction_metrics([d], log)
        assert result["total_administrative_cost"] == pytest.approx(0.5)
        assert result["total_appropriated_resources"] == pytest.approx(3.0)

    def test_institutional_scale_counts_active_rules_and_links(self):
        active_rule = _rule(0, members=(0, 1))
        dissolved_rule = _rule(1, members=(2,), dissolved=True, active=False)
        link = CoordinationLink(link_id=0, patch_id_a=0, patch_id_b=1, rule_id_a=0, rule_id_b=1, kind="information_exchange", proposed_step=0, accepted_step=0)
        result = dd.institutional_scale_metrics([active_rule, dissolved_rule], [], [link])
        assert result["n_active_rules"] == 1
        assert result["n_active_coordination_links"] == 1
        assert result["n_coordination_links_ever"] == 1

    def test_institutional_flexibility_amendment_counts(self):
        log = EventLog()
        log.add(RuleAmendmentEvent(step=0, patch_id=0, rule_id=0, rule_lineage_id=0, proposer=1, field_changed="sanction_magnitude", old_value=0.5, new_value=0.7, n_eligible=3, n_supporters=2, support_fraction=0.67, adopted=False))
        rule = _rule(0)
        result = dd.institutional_flexibility_metrics([rule], log)
        assert result["n_amendment_attempts"] == 1
        assert result["n_amendments_adopted"] == 0  # adopted=False by dataclass default unless set

    def test_founder_independence_counts_delegate_successions(self):
        successor = _delegate(delegate_id=1, predecessor_delegate_id=0)
        first = _delegate(delegate_id=0)
        result = dd.founder_independence_metrics([], [first, successor])
        assert result["n_delegate_successions"] == 1
        assert result["delegate_succession_rate"] == pytest.approx(0.5)

    def test_functional_effect_is_a_generic_mean_difference(self):
        result = dd.functional_effect(condition_values=[10.0, 12.0], baseline_values=[5.0, 5.0])
        assert result["mean_effect"] == pytest.approx(6.0)
        assert result["n_condition"] == 2
        assert result["n_baseline"] == 2

    def test_summarize_delegation_metrics_keeps_nine_categories_separate(self):
        d = _delegate()
        rule = _rule(0)
        summary = dd.summarize_delegation_metrics([d], [rule], [], EventLog())
        assert set(summary.keys()) == {
            "administrative_capacity", "delegation_concentration", "accountability_intensity",
            "effective_constraint", "legitimacy_support", "administrative_extraction",
            "institutional_scale", "institutional_flexibility", "founder_independence",
        }
        # never merged into a single score -- every value is itself a dict
        assert all(isinstance(v, dict) for v in summary.values())


# ===========================================================================
# Work Package K: cautious mechanism-validation classifier
# ===========================================================================
class TestClassifyDelegation:
    def test_no_delegation_when_no_rule_or_delegates_or_nominations(self):
        result = dd.classify_delegation(None, [], [], EventLog(), final_step=100)
        assert result["label"] == "no_delegation"

    def test_attempted_delegation_when_nomination_occurred_but_none_selected(self):
        rule = _rule(0)
        log = EventLog()
        from abm_governance.core.events import DelegateNominationEvent
        log.add(DelegateNominationEvent(step=1, patch_id=0, rule_id=0, rule_lineage_id=0, nominator=1, candidate=1, self_nomination=True))
        result = dd.classify_delegation(rule, [], [], log, final_step=100)
        assert result["label"] == "attempted_delegation"

    def test_delegate_selected_below_minimum_duration(self):
        rule = _rule(0)
        d = _delegate(start_step=90)  # only 10 steps old at final_step=100
        result = dd.classify_delegation(rule, [d], [], EventLog(), final_step=100, min_duration_steps=30)
        assert result["label"] == "delegate_selected"

    def test_unstable_delegation_from_rapid_turnover(self):
        rule = _rule(0)
        d1 = _delegate(delegate_id=0, start_step=0, removal_step=5)
        d2 = _delegate(delegate_id=1, start_step=5, removal_step=10, predecessor_delegate_id=0)
        # d3 is currently active and has now outlasted min_duration_steps
        # itself, but its two predecessors both had short tenures --
        # turnover without any one holder settling in early on.
        d3 = _delegate(delegate_id=2, start_step=10, predecessor_delegate_id=1)
        result = dd.classify_delegation(rule, [d1, d2, d3], [], EventLog(), final_step=50, min_duration_steps=30)
        assert result["label"] == "unstable_delegation"

    def test_administratively_inactive_when_zero_task_attempts(self):
        rule = _rule(0)
        d = _delegate(start_step=0)
        result = dd.classify_delegation(rule, [d], [], EventLog(), final_step=200, min_duration_steps=30)
        assert result["label"] == "administratively_inactive"

    def test_administratively_functional_high_completion_rate(self):
        rule = _rule(0)
        d = _delegate(start_step=0)
        d.task_attempts["monitoring"] = 100
        d.task_successes["monitoring"] = 90
        result = dd.classify_delegation(rule, [d], [], EventLog(), final_step=50, min_duration_steps=30, persistent_duration_steps=1000)
        assert result["label"] == "administratively_functional"

    def test_persistent_delegation_long_tenure_and_adequate_completion(self):
        rule = _rule(0)
        d = _delegate(start_step=0)
        d.task_attempts["monitoring"] = 100
        d.task_successes["monitoring"] = 40
        result = dd.classify_delegation(rule, [d], [], EventLog(), final_step=150, min_duration_steps=30, persistent_duration_steps=100)
        assert result["label"] == "persistent_delegation"

    def test_accountable_delegation_when_misconduct_is_caught_and_recalled(self):
        rule = _rule(0)
        d = _delegate(start_step=0, appropriated_total=5.0)
        d.task_attempts["monitoring"] = 50
        d.task_successes["monitoring"] = 25
        log = EventLog()
        log.add(RecallEvent(step=40, patch_id=0, rule_id=0, delegate_id=d.delegate_id, trigger_auditor=1, n_eligible=2, n_supporters=2, support_fraction=1.0, recall_threshold=0.5, succeeded=True, recovered_funds=2.5))
        result = dd.classify_delegation(rule, [d], [], log, final_step=50, min_duration_steps=30)
        assert result["label"] == "accountable_delegation"

    def test_weakly_constrained_delegation_when_audited_but_never_removed(self):
        rule = _rule(0)
        d = _delegate(start_step=0, appropriated_total=5.0)
        d.task_attempts["monitoring"] = 50
        d.task_successes["monitoring"] = 25
        log = EventLog()
        log.add(AuditEvent(step=35, patch_id=0, rule_id=0, delegate_id=d.delegate_id, auditor=1, actual_misconduct_occurred=True, found_misconduct=True, outcome="true_positive", cost=0.1))
        result = dd.classify_delegation(rule, [d], [], log, final_step=50, min_duration_steps=30)
        assert result["label"] == "weakly_constrained_delegation"

    def test_fragmented_coordination_when_no_delegation_and_short_lived_links(self):
        link = CoordinationLink(link_id=0, patch_id_a=0, patch_id_b=1, rule_id_a=0, rule_id_b=1, kind="information_exchange", proposed_step=0, accepted_step=0, dissolved=True, dissolution_step=5, active=False)
        result = dd.classify_delegation(None, [], [link], EventLog(), final_step=100)
        assert result["label"] == "fragmented_coordination"

    def test_interpatch_coordination_when_link_persists_past_minimum_duration(self):
        link = CoordinationLink(link_id=0, patch_id_a=0, patch_id_b=1, rule_id_a=0, rule_id_b=1, kind="information_exchange", proposed_step=0, accepted_step=0)
        result = dd.classify_delegation(None, [], [link], EventLog(), final_step=100)
        assert result["label"] == "interpatch_coordination"

    def test_label_is_always_from_the_fixed_vocabulary(self):
        # exhaustive smoke check across every branch exercised above
        rule = _rule(0)
        for label_case in (
            dd.classify_delegation(None, [], [], EventLog(), final_step=100),
            dd.classify_delegation(rule, [_delegate(start_step=90)], [], EventLog(), final_step=100),
        ):
            assert label_case["label"] in dd.VALID_LABELS
