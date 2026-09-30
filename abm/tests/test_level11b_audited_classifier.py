"""Level 1.1b, Work Package H: audited classifier vs. historical
classifier.

`observer/delegation_diagnostics.classify_delegation` (the "historical"
classifier, byte-for-byte unchanged from Level 1.1) can call a rule
"accountable_delegation" from a recall that succeeded by vote but
recovered zero funds, or from an appeal that "succeeded" by wrongly
overturning a genuinely justified sanction. `classify_delegation_audited`
applies Work Package E's realized-detection/realized-recovery/
genuinely-corrective-appeal standard instead. This module tests the two
classifiers directly against synthetic rule/delegate/event-log fixtures,
confirming they diverge exactly where the milestone predicts and agree
everywhere else (every non-accountability branch is untouched)."""

from __future__ import annotations

import pytest

from abm_governance.core.events import AppealEvent, AuditEvent, EventLog, RecallEvent
from abm_governance.observer import delegation_diagnostics as dd
from abm_governance.rules import delegation as rd
from abm_governance.rules.shared_rule import RuleParameters, SharedRule

FINAL_STEP = 200


def _rule(rule_id=0, patch_id=0, members=(0, 1, 2, 3)):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    return SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=0, rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )


def _delegate_with_misconduct(delegate_id=0, rule_id=0, start_step=0, tenure=100):
    d = rd.Delegate(
        delegate_id=delegate_id, rule_id=rule_id, rule_lineage_id=rule_id, patch_id=0, agent_id=delegate_id,
        tasks=("resource_accounting",), appointment_method="lottery", start_step=start_step,
    )
    d.task_attempts = {"resource_accounting": 20}
    d.task_successes = {"resource_accounting": 10}
    d.appropriated_total = 5.0  # any_misconduct = True
    d.removal_step = start_step + tenure
    d.active = False
    return d


class TestAccountableDelegationDowngrades:
    def test_recall_succeeded_but_zero_funds_recovered_is_downgraded(self):
        """The historical classifier's own field is RecallEvent.succeeded
        (a vote outcome) -- it never checks recovered_funds. A recall
        that wins the vote but claws back nothing should NOT count as
        realized accountability under the audited standard."""
        rule = _rule()
        delegate = _delegate_with_misconduct()
        log = EventLog()
        log.add(AuditEvent(
            step=10, patch_id=0, rule_id=0, delegate_id=0, auditor=1,
            actual_misconduct_occurred=True, found_misconduct=True, outcome="true_positive", cost=0.1,
        ))
        log.add(RecallEvent(
            step=11, patch_id=0, rule_id=0, delegate_id=0, trigger_auditor=1,
            n_eligible=3, n_supporters=2, support_fraction=0.67, recall_threshold=0.5,
            succeeded=True, recovered_funds=0.0,
        ))

        historical = dd.classify_delegation(rule, [delegate], [], log, FINAL_STEP)
        audited = dd.classify_delegation_audited(rule, [delegate], [], log, FINAL_STEP)

        assert historical["label"] == "accountable_delegation"
        assert audited["label"] != "accountable_delegation"
        assert audited["label"] == "weakly_constrained_delegation"

    def test_unjustified_appeal_overturn_is_downgraded(self):
        """was_false_sanction=False, upheld=True is an UNJUSTIFIED
        overturn (the appeals process let a guilty party off) -- the
        historical classifier's n_appeals_upheld only checks `upheld`,
        crediting this toward "accountable_delegation" anyway. The
        audited classifier must not."""
        rule = _rule()
        delegate = _delegate_with_misconduct()
        log = EventLog()
        # An audit occurred (any outcome) so the historical n_audits>0
        # weakly-constrained branch is reachable, but no true-positive.
        log.add(AuditEvent(
            step=10, patch_id=0, rule_id=0, delegate_id=0, auditor=1,
            actual_misconduct_occurred=False, found_misconduct=False, outcome="true_negative", cost=0.1,
        ))
        log.add(AppealEvent(
            step=12, patch_id=0, rule_id=0, delegate_id=0, appellant=2, original_sanction_step=11,
            was_false_sanction=False, upheld=True, refund=0.5, cost=0.05,
        ))

        historical = dd.classify_delegation(rule, [delegate], [], log, FINAL_STEP)
        audited = dd.classify_delegation_audited(rule, [delegate], [], log, FINAL_STEP)

        assert historical["label"] == "accountable_delegation"
        assert audited["label"] != "accountable_delegation"

    def test_genuine_true_positive_plus_recovered_recall_agrees_on_both(self):
        """The clean case both classifiers should agree on: a real
        true-positive detection AND a recall that actually recovered
        funds -- realized accountability by any reasonable standard."""
        rule = _rule()
        delegate = _delegate_with_misconduct()
        log = EventLog()
        log.add(AuditEvent(
            step=10, patch_id=0, rule_id=0, delegate_id=0, auditor=1,
            actual_misconduct_occurred=True, found_misconduct=True, outcome="true_positive", cost=0.1,
        ))
        log.add(RecallEvent(
            step=11, patch_id=0, rule_id=0, delegate_id=0, trigger_auditor=1,
            n_eligible=3, n_supporters=2, support_fraction=0.67, recall_threshold=0.5,
            succeeded=True, recovered_funds=3.0,
        ))

        historical = dd.classify_delegation(rule, [delegate], [], log, FINAL_STEP)
        audited = dd.classify_delegation_audited(rule, [delegate], [], log, FINAL_STEP)

        assert historical["label"] == "accountable_delegation"
        assert audited["label"] == "accountable_delegation"

    def test_genuinely_justified_appeal_correction_agrees_on_both(self):
        """was_false_sanction=True, upheld=True is a genuinely
        corrective outcome -- both classifiers should credit it,
        given a true-positive audit is also present."""
        rule = _rule()
        delegate = _delegate_with_misconduct()
        log = EventLog()
        log.add(AuditEvent(
            step=10, patch_id=0, rule_id=0, delegate_id=0, auditor=1,
            actual_misconduct_occurred=True, found_misconduct=True, outcome="true_positive", cost=0.1,
        ))
        log.add(AppealEvent(
            step=12, patch_id=0, rule_id=0, delegate_id=0, appellant=2, original_sanction_step=11,
            was_false_sanction=True, upheld=True, refund=0.5, cost=0.05,
        ))

        historical = dd.classify_delegation(rule, [delegate], [], log, FINAL_STEP)
        audited = dd.classify_delegation_audited(rule, [delegate], [], log, FINAL_STEP)

        assert historical["label"] == "accountable_delegation"
        assert audited["label"] == "accountable_delegation"


class TestNonAccountabilityBranchesAreUnchanged:
    """Every branch classify_delegation_audited did not touch --
    duration-gating, no-delegation, coordination -- must produce
    IDENTICAL labels to the historical classifier."""

    def test_short_tenure_delegate_selected_agrees(self):
        rule = _rule()
        delegate = rd.Delegate(
            delegate_id=0, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=0,
            tasks=("resource_accounting",), appointment_method="lottery", start_step=190,
        )
        historical = dd.classify_delegation(rule, [delegate], [], EventLog(), FINAL_STEP)
        audited = dd.classify_delegation_audited(rule, [delegate], [], EventLog(), FINAL_STEP)
        assert historical["label"] == audited["label"] == "delegate_selected"

    def test_no_delegation_at_all_agrees(self):
        historical = dd.classify_delegation(None, [], [], EventLog(), FINAL_STEP)
        audited = dd.classify_delegation_audited(None, [], [], EventLog(), FINAL_STEP)
        assert historical["label"] == audited["label"] == "no_delegation"

    def test_no_misconduct_persistent_delegation_agrees(self):
        rule = _rule()
        delegate = rd.Delegate(
            delegate_id=0, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=0,
            tasks=("resource_accounting",), appointment_method="lottery", start_step=0,
        )
        delegate.task_attempts = {"resource_accounting": 100}
        delegate.task_successes = {"resource_accounting": 80}
        delegate.removal_step = 150
        delegate.active = False
        historical = dd.classify_delegation(rule, [delegate], [], EventLog(), FINAL_STEP)
        audited = dd.classify_delegation_audited(rule, [delegate], [], EventLog(), FINAL_STEP)
        assert historical["label"] == audited["label"] == "persistent_delegation"
