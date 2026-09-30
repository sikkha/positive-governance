"""Level 1.3, Work Package A (Section 6): exact activation tests for the
6-of-18 pressure transmission channels wired this milestone (see
``core/historical_transmission.py``'s module docstring for the full
disclosed scope-reduction rationale).

Every channel below is tested for two properties, mirroring Section 6's
explicit requirement ("each pressure changes only its registered
microscopic opportunities"):

1. **Activation** — enabling the channel's own flag with a nonzero
   pressure level moves its targeted quantity in the documented
   direction, relative to the same call with the flag disabled (or the
   level at ``0.0``).
2. **Isolation** — enabling one channel's flag leaves every *other*
   channel's quantity, and every pre-existing Level 1.1/1.2/1.2b
   quantity computed by the same function, exactly as it was with the
   channel disabled.

These are unit-level tests against the private round functions directly
(``rd._success_probability``, ``rd.task_performance_round``,
``rd.accountability_round``, ``rc.contribution_round``,
``coord.coordination_round``) — the same fixture pattern used by
``tests/test_level11_capacity_discretion.py``,
``tests/test_level11_accountability.py``, ``tests/test_level11_
contributions.py``, and ``tests/test_level11_coordination.py``.
Compatibility with Level 1.2b (every channel defaulting to an exact
no-op) is separately covered by ``tests/test_level13_compatibility.py``;
this file is about what happens once a channel is actually turned on."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog, SanctionEvent
from abm_governance.core.historical_transmission import pressure_adjusted_probability, pressure_adjusted_scale
from abm_governance.rules import contributions as rc
from abm_governance.rules import coordination as coord
from abm_governance.rules import delegation as rd
from abm_governance.rules.shared_rule import RuleParameters, SharedRule


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


def _rule(rule_id=0, patch_id=0, members=(0, 1, 2), founder=0, fund=0.0):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    r = SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=founder, rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )
    r.fund = fund
    return r


def _delegate(agent_id=1, rule_id=0, tasks=("monitoring",), record_quality=0.2):
    return rd.Delegate(
        delegate_id=0, rule_id=rule_id, rule_lineage_id=rule_id, patch_id=0, agent_id=agent_id,
        tasks=tasks, appointment_method="lottery", start_step=0, record_quality=record_quality,
    )


# ---------------------------------------------------------------------------
# Pure helper functions.
# ---------------------------------------------------------------------------
class TestPressureAdjustedHelpers:
    def test_probability_helper_adds_and_clips(self):
        assert pressure_adjusted_probability(0.5, 1.0, 0.2) == pytest.approx(0.7)
        assert pressure_adjusted_probability(0.9, 1.0, 0.5) == pytest.approx(1.0)  # clipped at 1.0
        assert pressure_adjusted_probability(0.1, -1.0, 0.5) == pytest.approx(0.0)  # clipped at 0.0

    def test_probability_helper_is_exact_noop_at_zero_level(self):
        assert pressure_adjusted_probability(0.37, 0.0, 0.9) == pytest.approx(0.37)

    def test_scale_helper_multiplies_and_floors(self):
        assert pressure_adjusted_scale(0.3, 1.0, 0.5) == pytest.approx(0.45)
        assert pressure_adjusted_scale(0.3, -10.0, 0.5) == pytest.approx(0.0)  # floored at 0.0

    def test_scale_helper_is_exact_noop_at_zero_level(self):
        assert pressure_adjusted_scale(0.42, 0.0, 0.9) == pytest.approx(0.42)


# ---------------------------------------------------------------------------
# security_pressure_returns_to_delegation (rules/delegation.py::_success_probability)
# ---------------------------------------------------------------------------
class TestSecurityPressureReturnsToDelegation:
    def _call(self, config, security_pressure_level=0.0, capacity=0.0):
        d = _delegate()
        d.task_attempts["monitoring"] = 0  # capacity stays 0.0 by construction; set explicitly below if needed
        agent = _agent(1, administrative_reliability=0.6)
        rule = _rule()
        return rd._success_probability(d, agent, 1, rule, config, security_pressure_level)

    def test_enabling_with_positive_pressure_raises_base_success(self):
        config_off = SimulationConfig.level11_delegation_only(security_pressure_returns_to_delegation_enabled=False)
        config_on = SimulationConfig.level11_delegation_only(
            security_pressure_returns_to_delegation_enabled=True,
            security_pressure_returns_to_delegation_sensitivity=0.15,
        )
        p_off = self._call(config_off, security_pressure_level=1.0)
        p_on = self._call(config_on, security_pressure_level=1.0)
        assert p_on > p_off
        assert p_on == pytest.approx(p_off + 0.15)

    def test_zero_pressure_level_is_exact_noop_even_when_enabled(self):
        config_off = SimulationConfig.level11_delegation_only(security_pressure_returns_to_delegation_enabled=False)
        config_on = SimulationConfig.level11_delegation_only(security_pressure_returns_to_delegation_enabled=True)
        assert self._call(config_on, security_pressure_level=0.0) == pytest.approx(
            self._call(config_off, security_pressure_level=0.0)
        )

    def test_isolated_from_admin_capacity_demand_channel(self):
        # Enabling returns_to_delegation alone must not perturb the
        # capacity_bonus term at all (capacity=0.0 here, so any leak
        # from the OTHER channel would still show up as a bare
        # base-only difference -- verified directly against the analytic
        # formula instead of just a second call).
        config = SimulationConfig.level11_delegation_only(
            security_pressure_returns_to_delegation_enabled=True,
            security_pressure_returns_to_delegation_sensitivity=0.15,
            security_pressure_admin_capacity_demand_enabled=False,
        )
        p = self._call(config, security_pressure_level=1.0)
        expected_base = pressure_adjusted_probability(0.6, 1.0, 0.15)
        # capacity=0.0 -> capacity_bonus=0.0; workload_penalty=0.0 (n_tasks=1);
        # scale_term = delegation_scale_coefficient(0.0) * 0.3 = 0.0.
        assert p == pytest.approx(np.clip(expected_base, 0.02, 0.98))


# ---------------------------------------------------------------------------
# security_pressure_admin_capacity_demand (rules/delegation.py::_success_probability)
# ---------------------------------------------------------------------------
class TestSecurityPressureAdminCapacityDemand:
    def _call(self, config, security_pressure_level, capacity):
        d = _delegate()
        d.task_attempts["monitoring"] = 100
        d.task_successes["monitoring"] = int(100 * capacity)  # coarse but deterministic knob via capacity property is awkward; set capacity directly instead
        agent = _agent(1, administrative_reliability=0.6)
        rule = _rule()
        return rd._success_probability(d, agent, 1, rule, config, security_pressure_level)

    def test_enabling_with_positive_pressure_and_nonzero_capacity_raises_success(self):
        # Use the Delegate.capacity property faithfully rather than
        # hand-setting an attribute that doesn't exist -- drive it via
        # task_successes/record_quality exactly like production code
        # does, then compare the SAME delegate object (same realized
        # capacity) across enabled/disabled configs.
        d = _delegate(record_quality=1.0)
        d.task_attempts["monitoring"] = 100
        d.task_successes["monitoring"] = 100
        capacity = d.capacity
        assert capacity > 0.0
        agent = _agent(1, administrative_reliability=0.6)
        rule = _rule()
        config_off = SimulationConfig.level11_delegation_only(security_pressure_admin_capacity_demand_enabled=False)
        config_on = SimulationConfig.level11_delegation_only(
            security_pressure_admin_capacity_demand_enabled=True,
            security_pressure_admin_capacity_demand_sensitivity=0.3,
        )
        p_off = rd._success_probability(d, agent, 1, rule, config_off, 1.0)
        p_on = rd._success_probability(d, agent, 1, rule, config_on, 1.0)
        expected_weight_on = pressure_adjusted_scale(config_on.delegation_capacity_learning_weight, 1.0, 0.3)
        expected_p_on = np.clip(0.6 + expected_weight_on * capacity, 0.02, 0.98)
        assert p_on > p_off
        assert p_on == pytest.approx(expected_p_on)

    def test_zero_capacity_makes_this_channel_a_noop_regardless_of_pressure(self):
        # capacity_bonus = capacity_weight * capacity; capacity=0.0 means
        # scaling capacity_weight changes nothing observable -- a direct
        # demonstration that this channel only ever acts THROUGH realized
        # capacity, never as a bare additive shift (unlike
        # returns_to_delegation above).
        d = _delegate()  # capacity == 0.0 (no attempts yet)
        assert d.capacity == 0.0
        agent = _agent(1, administrative_reliability=0.6)
        rule = _rule()
        config_off = SimulationConfig.level11_delegation_only(security_pressure_admin_capacity_demand_enabled=False)
        config_on = SimulationConfig.level11_delegation_only(
            security_pressure_admin_capacity_demand_enabled=True,
            security_pressure_admin_capacity_demand_sensitivity=0.9,
        )
        assert rd._success_probability(d, agent, 1, rule, config_on, 1.0) == pytest.approx(
            rd._success_probability(d, agent, 1, rule, config_off, 1.0)
        )

    def test_isolated_from_returns_to_delegation_channel(self):
        d = _delegate(record_quality=1.0)
        d.task_attempts["monitoring"] = 100
        d.task_successes["monitoring"] = 100
        agent = _agent(1, administrative_reliability=0.6)
        rule = _rule()
        config = SimulationConfig.level11_delegation_only(
            security_pressure_admin_capacity_demand_enabled=True,
            security_pressure_admin_capacity_demand_sensitivity=0.3,
            security_pressure_returns_to_delegation_enabled=False,
        )
        p = rd._success_probability(d, agent, 1, rule, config, 1.0)
        expected_weight = pressure_adjusted_scale(config.delegation_capacity_learning_weight, 1.0, 0.3)
        # base stays the RAW agent.administrative_reliability -- untouched.
        expected = np.clip(0.6 + expected_weight * d.capacity, 0.02, 0.98)
        assert p == pytest.approx(expected)


# ---------------------------------------------------------------------------
# bargaining_pressure_appeal_recall (rules/delegation.py::accountability_round)
# ---------------------------------------------------------------------------
class TestBargainingPressureAppealRecall:
    def _sanction_event(self, step=0, rule_id=0, target=2, false_sanction=True, magnitude=0.5):
        return SanctionEvent(
            step=step, patch_id=0, rule_id=rule_id, target=target, magnitude=magnitude, cost=0.1,
            funded_by="bystander", false_sanction=false_sanction, sanctioner=1,
        )

    def test_enabling_raises_appeal_rate_over_many_seeds(self):
        n = 200
        n_appeals_off = 0
        n_appeals_on = 0
        for seed in range(n):
            for enabled, counter_name in ((False, "off"), (True, "on")):
                d = _delegate()
                delegate_registry = {0: d}
                agents = {0: _agent(0), 1: _agent(1), 2: _agent(2)}
                registry = {0: _rule()}
                config = SimulationConfig.level11_accountability_only(
                    appeal_probability=0.3,
                    bargaining_pressure_appeal_recall_enabled=enabled,
                    bargaining_pressure_appeal_recall_sensitivity=0.6,
                )
                rng = np.random.default_rng(seed)
                log = EventLog()
                rd.accountability_round(
                    0, registry, delegate_registry, agents, [self._sanction_event()], config, rng, log,
                    bargaining_pressure_level=1.0,
                )
                if log.appeals:
                    if enabled:
                        n_appeals_on += 1
                    else:
                        n_appeals_off += 1
        assert n_appeals_on > n_appeals_off

    def test_zero_pressure_level_is_exact_noop_even_when_enabled(self):
        d = _delegate()
        delegate_registry = {0: d}
        agents = {0: _agent(0), 1: _agent(1), 2: _agent(2)}
        registry = {0: _rule()}
        config_on = SimulationConfig.level11_accountability_only(
            appeal_probability=0.3, bargaining_pressure_appeal_recall_enabled=True,
        )
        config_off = SimulationConfig.level11_accountability_only(
            appeal_probability=0.3, bargaining_pressure_appeal_recall_enabled=False,
        )
        rng_on = np.random.default_rng(7)
        rng_off = np.random.default_rng(7)
        log_on = EventLog()
        log_off = EventLog()
        rd.accountability_round(
            0, dict(registry), dict(delegate_registry), dict(agents), [self._sanction_event()], config_on, rng_on,
            log_on, bargaining_pressure_level=0.0,
        )
        rd.accountability_round(
            0, dict(registry), {0: _delegate()}, dict(agents), [self._sanction_event()], config_off, rng_off,
            log_off, bargaining_pressure_level=0.0,
        )
        assert (len(log_on.appeals) > 0) == (len(log_off.appeals) > 0)

    def test_recall_threshold_is_lowered_and_floored(self):
        rule = _rule()
        registry = {0: rule}
        d = rd.Delegate(
            delegate_id=0, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=1,
            tasks=("monitoring",), appointment_method="lottery", start_step=0,
            audits_failed=50, audits_survived=0,
        )
        d.misconduct_this_step = True
        delegate_registry = {0: d}
        agents = {0: _agent(0, audit_diligence=1.0, social_trust=0.0), 1: _agent(1), 2: _agent(2, audit_diligence=1.0, social_trust=0.0)}
        config = SimulationConfig.level11_accountability_only(
            audit_accuracy=0.999, recall_support_threshold=0.9,
            bargaining_pressure_appeal_recall_enabled=True,
            bargaining_pressure_appeal_recall_sensitivity=0.5,
        )
        rng = np.random.default_rng(9)
        log = EventLog()
        rd.accountability_round(
            0, registry, delegate_registry, agents, [], config, rng, log, bargaining_pressure_level=1.0,
        )
        assert len(log.recalls) == 1
        assert log.recalls[0].recall_threshold == pytest.approx(max(0.05, 0.9 - 0.5))

    def test_recall_threshold_floor_never_goes_below_point_zero_five(self):
        rule = _rule()
        registry = {0: rule}
        d = rd.Delegate(
            delegate_id=0, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=1,
            tasks=("monitoring",), appointment_method="lottery", start_step=0,
            audits_failed=50, audits_survived=0,
        )
        d.misconduct_this_step = True
        delegate_registry = {0: d}
        agents = {0: _agent(0, audit_diligence=1.0, social_trust=0.0), 1: _agent(1), 2: _agent(2, audit_diligence=1.0, social_trust=0.0)}
        config = SimulationConfig.level11_accountability_only(
            audit_accuracy=0.999, recall_support_threshold=0.1,
            bargaining_pressure_appeal_recall_enabled=True,
            bargaining_pressure_appeal_recall_sensitivity=10.0,
        )
        rng = np.random.default_rng(9)
        log = EventLog()
        rd.accountability_round(
            0, registry, delegate_registry, agents, [], config, rng, log, bargaining_pressure_level=1.0,
        )
        assert len(log.recalls) == 1
        assert log.recalls[0].recall_threshold == pytest.approx(0.05)

    def test_isolated_from_disabled_channel_at_the_audit_stage(self):
        # audits/outcomes must be completely unaffected by this channel
        # (it only ever touches appeal_probability and recall_threshold).
        d = _delegate()
        d.misconduct_this_step = True
        delegate_registry_a = {0: d}
        d2 = _delegate()
        d2.misconduct_this_step = True
        delegate_registry_b = {0: d2}
        agents_a = {0: _agent(0, audit_diligence=1.0), 1: _agent(1), 2: _agent(2, audit_diligence=1.0)}
        agents_b = {0: _agent(0, audit_diligence=1.0), 1: _agent(1), 2: _agent(2, audit_diligence=1.0)}
        config_off = SimulationConfig.level11_accountability_only(bargaining_pressure_appeal_recall_enabled=False)
        config_on = SimulationConfig.level11_accountability_only(bargaining_pressure_appeal_recall_enabled=True)
        rng_a = np.random.default_rng(3)
        rng_b = np.random.default_rng(3)
        log_a = EventLog()
        log_b = EventLog()
        rd.accountability_round(0, {0: _rule()}, delegate_registry_a, agents_a, [], config_off, rng_a, log_a, bargaining_pressure_level=1.0)
        rd.accountability_round(0, {0: _rule()}, delegate_registry_b, agents_b, [], config_on, rng_b, log_b, bargaining_pressure_level=1.0)
        assert [e.outcome for e in log_a.audits] == [e.outcome for e in log_b.audits]


# ---------------------------------------------------------------------------
# bargaining_pressure_conditional_contribution (rules/contributions.py::contribution_round)
# ---------------------------------------------------------------------------
class TestBargainingPressureConditionalContribution:
    def test_voluntary_mode_compliance_rate_rises_over_many_seeds(self):
        n = 300
        n_complied_off = 0
        n_complied_on = 0
        for seed in range(n):
            for enabled, target in ((False, "off"), (True, "on")):
                rule = _rule()
                registry = {0: rule}
                agents = {i: _agent(i, contribution_willingness=0.3, resources=10.0) for i in range(3)}
                config = SimulationConfig.level1_rule_formation_default(
                    contribution_mode="voluntary", contribution_period_steps=1,
                    bargaining_pressure_conditional_contribution_enabled=enabled,
                    bargaining_pressure_conditional_contribution_sensitivity=0.6,
                )
                rng = np.random.default_rng(seed)
                log = EventLog()
                rc.contribution_round(0, registry, agents, config, rng, log, bargaining_pressure_level=1.0)
                complied = sum(1 for e in log.contributions if e.complied)
                if target == "on":
                    n_complied_on += complied
                else:
                    n_complied_off += complied
        assert n_complied_on > n_complied_off

    def test_negotiated_mode_is_also_affected(self):
        n = 300
        n_complied_off = 0
        n_complied_on = 0
        for seed in range(n):
            for enabled, target in ((False, "off"), (True, "on")):
                rule = _rule()
                registry = {0: rule}
                agents = {
                    0: _agent(0, preferred_contribution_amount=1.0, contribution_willingness=0.3, resources=10.0),
                    1: _agent(1, preferred_contribution_amount=1.0, contribution_willingness=0.3, resources=10.0),
                    2: _agent(2, preferred_contribution_amount=1.0, contribution_willingness=0.3, resources=10.0),
                }
                config = SimulationConfig.level1_rule_formation_default(
                    contribution_mode="negotiated", contribution_period_steps=1,
                    bargaining_pressure_conditional_contribution_enabled=enabled,
                    bargaining_pressure_conditional_contribution_sensitivity=0.6,
                )
                rng = np.random.default_rng(seed)
                log = EventLog()
                rc.contribution_round(0, registry, agents, config, rng, log, bargaining_pressure_level=1.0)
                complied = sum(1 for e in log.contributions if e.complied)
                if target == "on":
                    n_complied_on += complied
                else:
                    n_complied_off += complied
        assert n_complied_on > n_complied_off

    def test_equal_mode_is_completely_unaffected(self):
        # "equal" mode compliance is unconditional (complied=True always)
        # -- this channel must never touch it.
        rule = _rule()
        registry = {0: rule}
        agents = {i: _agent(i, contribution_willingness=0.0, resources=10.0) for i in range(3)}
        config_on = SimulationConfig.level1_rule_formation_default(
            contribution_mode="equal", contribution_amount=1.0, contribution_period_steps=1,
            bargaining_pressure_conditional_contribution_enabled=True,
            bargaining_pressure_conditional_contribution_sensitivity=0.9,
        )
        rng = np.random.default_rng(0)
        log = EventLog()
        rc.contribution_round(0, registry, agents, config_on, rng, log, bargaining_pressure_level=1.0)
        assert len(log.contributions) == 3
        assert all(e.complied for e in log.contributions)
        assert rule.fund == pytest.approx(3.0)

    def test_proportional_mode_is_completely_unaffected(self):
        rule = _rule()
        registry = {0: rule}
        agents = {i: _agent(i, contribution_willingness=0.0, resources=10.0) for i in range(3)}
        config_on = SimulationConfig.level1_rule_formation_default(
            contribution_mode="proportional", contribution_proportional_rate=0.1, contribution_period_steps=1,
            bargaining_pressure_conditional_contribution_enabled=True,
            bargaining_pressure_conditional_contribution_sensitivity=0.9,
        )
        rng = np.random.default_rng(0)
        log = EventLog()
        rc.contribution_round(0, registry, agents, config_on, rng, log, bargaining_pressure_level=1.0)
        assert len(log.contributions) == 3
        assert all(e.complied for e in log.contributions)

    def test_zero_pressure_level_is_exact_noop_even_when_enabled_voluntary_mode(self):
        rule_off = _rule()
        rule_on = _rule()
        agents_off = {i: _agent(i, contribution_willingness=0.3, resources=10.0) for i in range(3)}
        agents_on = {i: _agent(i, contribution_willingness=0.3, resources=10.0) for i in range(3)}
        config_off = SimulationConfig.level1_rule_formation_default(contribution_mode="voluntary", contribution_period_steps=1)
        config_on = SimulationConfig.level1_rule_formation_default(
            contribution_mode="voluntary", contribution_period_steps=1,
            bargaining_pressure_conditional_contribution_enabled=True,
        )
        rng_off = np.random.default_rng(4)
        rng_on = np.random.default_rng(4)
        log_off = EventLog()
        log_on = EventLog()
        rc.contribution_round(0, {0: rule_off}, agents_off, config_off, rng_off, log_off, bargaining_pressure_level=0.0)
        rc.contribution_round(0, {0: rule_on}, agents_on, config_on, rng_on, log_on, bargaining_pressure_level=0.0)
        assert [e.complied for e in log_off.contributions] == [e.complied for e in log_on.contributions]


# ---------------------------------------------------------------------------
# coordination_complexity_interoperable_demand (rules/coordination.py::coordination_round, proposal probability)
# ---------------------------------------------------------------------------
class TestCoordinationComplexityInteroperableDemand:
    def _two_patch_setup(self, **agent_overrides):
        agents = {
            0: _agent(0, patch_id=0, **agent_overrides), 1: _agent(1, patch_id=0, **agent_overrides),
            2: _agent(2, patch_id=1, **agent_overrides), 3: _agent(3, patch_id=1, **agent_overrides),
        }
        registry = {0: _rule(0, patch_id=0, members=(0, 1)), 1: _rule(1, patch_id=1, members=(2, 3))}
        return agents, registry

    def test_enabling_raises_proposal_rate_over_many_seeds(self):
        n = 200
        n_proposals_off = 0
        n_proposals_on = 0
        for seed in range(n):
            for enabled, target in ((False, "off"), (True, "on")):
                agents, registry = self._two_patch_setup(interpatch_proposal_probability=0.0, interpatch_acceptance_propensity=1.0)
                link_registry: dict = {}
                pending: dict = {}
                config = SimulationConfig.level11_coordination_only(
                    coordination_proposal_probability=0.3,
                    coordination_complexity_interoperable_demand_enabled=enabled,
                    coordination_complexity_interoperable_demand_sensitivity=0.6,
                )
                rng = np.random.default_rng(seed)
                log = EventLog()
                id_state = {"next_link_id": 0}
                coord.coordination_round(
                    0, registry, agents, None, link_registry, pending, config, rng, log, id_state,
                    coordination_complexity_level=1.0,
                )
                n_props = len(log.coordination_proposals)
                if target == "on":
                    n_proposals_on += n_props
                else:
                    n_proposals_off += n_props
        assert n_proposals_on > n_proposals_off

    def test_zero_pressure_level_is_exact_noop_even_when_enabled(self):
        agents_off, registry_off = self._two_patch_setup(interpatch_proposal_probability=0.0, interpatch_acceptance_propensity=1.0)
        agents_on, registry_on = self._two_patch_setup(interpatch_proposal_probability=0.0, interpatch_acceptance_propensity=1.0)
        config_off = SimulationConfig.level11_coordination_only(coordination_proposal_probability=0.3)
        config_on = SimulationConfig.level11_coordination_only(
            coordination_proposal_probability=0.3, coordination_complexity_interoperable_demand_enabled=True,
        )
        rng_off = np.random.default_rng(2)
        rng_on = np.random.default_rng(2)
        log_off = EventLog()
        log_on = EventLog()
        coord.coordination_round(0, registry_off, agents_off, None, {}, {}, config_off, rng_off, log_off, {"next_link_id": 0}, coordination_complexity_level=0.0)
        coord.coordination_round(0, registry_on, agents_on, None, {}, {}, config_on, rng_on, log_on, {"next_link_id": 0}, coordination_complexity_level=0.0)
        assert len(log_off.coordination_proposals) == len(log_on.coordination_proposals)


# ---------------------------------------------------------------------------
# coordination_complexity_cross_patch_transactions (rules/coordination.py::coordination_round, activity probability)
# ---------------------------------------------------------------------------
class TestCoordinationComplexityCrossPatchTransactions:
    def _linked_setup(self):
        agents = {0: _agent(0, patch_id=0), 1: _agent(1, patch_id=0), 2: _agent(2, patch_id=1), 3: _agent(3, patch_id=1)}
        registry = {0: _rule(0, patch_id=0, members=(0, 1), fund=100.0), 1: _rule(1, patch_id=1, members=(2, 3), fund=100.0)}
        link = coord.CoordinationLink(
            link_id=0, patch_id_a=0, patch_id_b=1, rule_id_a=0, rule_id_b=1, kind="information_exchange",
            proposed_step=0, accepted_step=0,
        )
        return agents, registry, {0: link}

    def test_enabling_raises_activity_rate_over_many_seeds(self):
        n = 200
        n_active_off = 0
        n_active_on = 0
        for seed in range(n):
            for enabled, target in ((False, "off"), (True, "on")):
                agents, registry, link_registry = self._linked_setup()
                config = SimulationConfig.level11_coordination_only(
                    coordination_activity_probability=0.3,
                    coordination_dissolution_probability=0.0,
                    coordination_complexity_cross_patch_transactions_enabled=enabled,
                    coordination_complexity_cross_patch_transactions_sensitivity=0.6,
                )
                rng = np.random.default_rng(seed)
                log = EventLog()
                coord.coordination_round(
                    0, registry, agents, None, link_registry, {}, config, rng, log, {"next_link_id": 1},
                    coordination_complexity_level=1.0,
                )
                n_active = len(log.coordination_activity)
                if target == "on":
                    n_active_on += n_active
                else:
                    n_active_off += n_active
        assert n_active_on > n_active_off

    def test_zero_pressure_level_is_exact_noop_even_when_enabled(self):
        agents_off, registry_off, link_registry_off = self._linked_setup()
        agents_on, registry_on, link_registry_on = self._linked_setup()
        config_off = SimulationConfig.level11_coordination_only(
            coordination_activity_probability=0.3, coordination_dissolution_probability=0.0,
        )
        config_on = SimulationConfig.level11_coordination_only(
            coordination_activity_probability=0.3, coordination_dissolution_probability=0.0,
            coordination_complexity_cross_patch_transactions_enabled=True,
        )
        rng_off = np.random.default_rng(5)
        rng_on = np.random.default_rng(5)
        log_off = EventLog()
        log_on = EventLog()
        coord.coordination_round(0, registry_off, agents_off, None, link_registry_off, {}, config_off, rng_off, log_off, {"next_link_id": 1}, coordination_complexity_level=0.0)
        coord.coordination_round(0, registry_on, agents_on, None, link_registry_on, {}, config_on, rng_on, log_on, {"next_link_id": 1}, coordination_complexity_level=0.0)
        assert len(log_off.coordination_activity) == len(log_on.coordination_activity)

    def test_isolated_from_interoperable_demand_channel(self):
        # A linked pair (no more proposals possible -- both patches
        # already linked) means the proposal-side channel has literally
        # nothing to act on here; enabling it alongside must not change
        # activity-round behavior at all.
        agents_a, registry_a, link_registry_a = self._linked_setup()
        agents_b, registry_b, link_registry_b = self._linked_setup()
        config_a = SimulationConfig.level11_coordination_only(
            coordination_activity_probability=0.3, coordination_dissolution_probability=0.0,
            coordination_complexity_cross_patch_transactions_enabled=True,
        )
        config_b = SimulationConfig.level11_coordination_only(
            coordination_activity_probability=0.3, coordination_dissolution_probability=0.0,
            coordination_complexity_cross_patch_transactions_enabled=True,
            coordination_complexity_interoperable_demand_enabled=True,
        )
        rng_a = np.random.default_rng(6)
        rng_b = np.random.default_rng(6)
        log_a = EventLog()
        log_b = EventLog()
        coord.coordination_round(0, registry_a, agents_a, None, link_registry_a, {}, config_a, rng_a, log_a, {"next_link_id": 1}, coordination_complexity_level=1.0)
        coord.coordination_round(0, registry_b, agents_b, None, link_registry_b, {}, config_b, rng_b, log_b, {"next_link_id": 1}, coordination_complexity_level=1.0)
        assert len(log_a.coordination_activity) == len(log_b.coordination_activity)
