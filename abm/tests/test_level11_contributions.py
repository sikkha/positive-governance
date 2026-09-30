"""Level 1.1, Work Package H: collective contributions, administrative
spending, and dissolution fund disposition -- exact ledger tests."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog
from abm_governance.rules import contributions as rc
from abm_governance.rules.shared_rule import RuleParameters, SharedRule
from abm_governance.simulation import Simulation


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


class TestContributionModeNone:
    def test_none_mode_never_collects(self):
        rule = _rule()
        registry = {0: rule}
        agents = {0: _agent(0), 1: _agent(1), 2: _agent(2)}
        config = SimulationConfig.level1_rule_formation_default(contribution_mode="none")
        rng = np.random.default_rng(0)
        log = EventLog()
        rc.contribution_round(0, registry, agents, config, rng, log)
        assert log.contributions == []
        assert rule.fund == 0.0


class TestEqualMode:
    def test_equal_mode_collects_fixed_amount_from_every_member(self):
        rule = _rule()
        registry = {0: rule}
        agents = {0: _agent(0, resources=10.0), 1: _agent(1, resources=10.0), 2: _agent(2, resources=10.0)}
        config = SimulationConfig.level1_rule_formation_default(contribution_mode="equal", contribution_amount=1.5, contribution_period_steps=1)
        rng = np.random.default_rng(0)
        log = EventLog()
        rc.contribution_round(0, registry, agents, config, rng, log)
        assert len(log.contributions) == 3
        assert all(e.complied for e in log.contributions)
        assert rule.fund == pytest.approx(4.5)
        assert all(a.resources == pytest.approx(8.5) for a in agents.values())

    def test_only_runs_on_configured_period(self):
        rule = _rule()
        registry = {0: rule}
        agents = {0: _agent(0), 1: _agent(1), 2: _agent(2)}
        config = SimulationConfig.level1_rule_formation_default(contribution_mode="equal", contribution_period_steps=10)
        rng = np.random.default_rng(0)
        log = EventLog()
        rc.contribution_round(3, registry, agents, config, rng, log)
        assert log.contributions == []
        rc.contribution_round(10, registry, agents, config, rng, log)
        assert len(log.contributions) == 3


class TestVoluntaryMode:
    def test_zero_willingness_never_complies(self):
        rule = _rule()
        registry = {0: rule}
        agents = {i: _agent(i, contribution_willingness=0.0) for i in range(3)}
        config = SimulationConfig.level1_rule_formation_default(contribution_mode="voluntary", contribution_period_steps=1)
        rng = np.random.default_rng(0)
        log = EventLog()
        rc.contribution_round(0, registry, agents, config, rng, log)
        assert all(not e.complied for e in log.contributions)
        assert rule.fund == 0.0

    def test_certain_willingness_always_complies(self):
        rule = _rule()
        registry = {0: rule}
        agents = {i: _agent(i, contribution_willingness=1.0, resources=10.0) for i in range(3)}
        config = SimulationConfig.level1_rule_formation_default(
            contribution_mode="voluntary", contribution_amount=2.0, contribution_period_steps=1,
        )
        rng = np.random.default_rng(0)
        log = EventLog()
        rc.contribution_round(0, registry, agents, config, rng, log)
        assert all(e.complied for e in log.contributions)
        assert rule.fund == pytest.approx(6.0)

    def test_compliance_independent_of_violation_tolerance(self):
        # Contribution compliance and ecological-rule compliance are two
        # separate ledgers -- a member with violation_tolerance=0.0 (very
        # rule-abiding ecologically) can still refuse to contribute, and
        # vice versa.
        rule = _rule(members=(0,))
        registry = {0: rule}
        agent = _agent(0, violation_tolerance=0.0, contribution_willingness=0.0, resources=10.0)
        config = SimulationConfig.level1_rule_formation_default(contribution_mode="voluntary", contribution_period_steps=1)
        rng = np.random.default_rng(0)
        log = EventLog()
        rc.contribution_round(0, registry, {0: agent}, config, rng, log)
        assert log.contributions[0].complied is False


class TestProportionalMode:
    def test_proportional_asks_a_fraction_of_current_resources(self):
        rule = _rule(members=(0,))
        registry = {0: rule}
        agent = _agent(0, resources=100.0)
        config = SimulationConfig.level1_rule_formation_default(
            contribution_mode="proportional", contribution_proportional_rate=0.1, contribution_period_steps=1,
        )
        rng = np.random.default_rng(0)
        log = EventLog()
        rc.contribution_round(0, registry, {0: agent}, config, rng, log)
        assert log.contributions[0].amount_asked == pytest.approx(10.0)
        assert agent.resources == pytest.approx(90.0)


class TestNegotiatedMode:
    def test_negotiated_amount_is_mean_of_preferences(self):
        rule = _rule()
        registry = {0: rule}
        agents = {
            0: _agent(0, preferred_contribution_amount=1.0, contribution_willingness=1.0, resources=10.0),
            1: _agent(1, preferred_contribution_amount=3.0, contribution_willingness=1.0, resources=10.0),
            2: _agent(2, preferred_contribution_amount=5.0, contribution_willingness=1.0, resources=10.0),
        }
        config = SimulationConfig.level1_rule_formation_default(contribution_mode="negotiated", contribution_period_steps=1)
        rng = np.random.default_rng(0)
        log = EventLog()
        rc.contribution_round(0, registry, agents, config, rng, log)
        for e in log.contributions:
            assert e.amount_asked == pytest.approx(3.0)


class TestAdministrativeSpending:
    def test_prefers_fund_over_personal_resources(self):
        rule = _rule(fund=5.0)
        payer = _agent(0, resources=20.0)
        log = EventLog()
        paid = rc.pay_administrative_cost(0, 0, rule, delegate_id=1, payer=payer, category="monitoring", amount=3.0, event_log=log)
        assert paid == pytest.approx(3.0)
        assert rule.fund == pytest.approx(2.0)
        assert payer.resources == pytest.approx(20.0)
        assert log.administrative_spending[0].funded_by == "collective_fund"

    def test_falls_back_to_personal_resources_when_fund_insufficient(self):
        rule = _rule(fund=1.0)
        payer = _agent(0, resources=20.0)
        log = EventLog()
        rc.pay_administrative_cost(0, 0, rule, delegate_id=1, payer=payer, category="monitoring", amount=3.0, event_log=log)
        assert rule.fund == pytest.approx(1.0)  # untouched -- amount exceeds fund, so paid personally instead
        assert payer.resources == pytest.approx(17.0)
        assert log.administrative_spending[0].funded_by == "delegate_personal"

    def test_never_drives_payer_resources_negative(self):
        rule = _rule(fund=0.0)
        payer = _agent(0, resources=2.0)
        log = EventLog()
        paid = rc.pay_administrative_cost(0, 0, rule, delegate_id=1, payer=payer, category="overhead", amount=10.0, event_log=log)
        assert paid == pytest.approx(2.0)
        assert payer.resources == pytest.approx(0.0)

    def test_zero_amount_pays_nothing_and_logs_nothing(self):
        rule = _rule(fund=5.0)
        payer = _agent(0, resources=5.0)
        log = EventLog()
        paid = rc.pay_administrative_cost(0, 0, rule, delegate_id=1, payer=payer, category="overhead", amount=0.0, event_log=log)
        assert paid == 0.0
        assert log.administrative_spending == []


class TestDissolutionFundDisposition:
    def test_distributed_to_members_splits_evenly(self):
        rule = _rule(fund=9.0)
        rule.dissolved = True
        rule.dissolution_step = 5
        agents = {0: _agent(0, resources=0.0), 1: _agent(1, resources=0.0), 2: _agent(2, resources=0.0)}
        config = SimulationConfig.level1_rule_formation_default(fund_dissolution_disposition="distributed_to_members")
        log = EventLog()
        rc.resolve_dissolution_fund(5, rule, frozenset((0, 1, 2)), agents, config, log)
        assert rule.fund == 0.0
        assert all(a.resources == pytest.approx(3.0) for a in agents.values())
        assert log.fund_dissolutions[0].disposition == "distributed_to_members"
        assert log.fund_dissolutions[0].amount == pytest.approx(9.0)

    def test_lost_removes_balance_from_circulation(self):
        rule = _rule(fund=9.0)
        agents = {0: _agent(0, resources=0.0)}
        config = SimulationConfig.level1_rule_formation_default(fund_dissolution_disposition="lost")
        log = EventLog()
        rc.resolve_dissolution_fund(5, rule, frozenset((0,)), agents, config, log)
        assert rule.fund == 0.0
        assert agents[0].resources == 0.0
        assert log.fund_dissolutions[0].disposition == "lost"

    def test_retained_for_reconstruction_preserves_the_balance(self):
        rule = _rule(fund=9.0)
        agents = {0: _agent(0, resources=0.0)}
        config = SimulationConfig.level1_rule_formation_default(fund_dissolution_disposition="retained_for_reconstruction")
        log = EventLog()
        rc.resolve_dissolution_fund(5, rule, frozenset((0,)), agents, config, log)
        assert rule.fund == pytest.approx(9.0)  # preserved, not zeroed
        assert log.fund_dissolutions[0].disposition == "retained_for_reconstruction"

    def test_zero_fund_disposes_nothing(self):
        rule = _rule(fund=0.0)
        agents = {0: _agent(0)}
        config = SimulationConfig.level1_rule_formation_default(fund_dissolution_disposition="distributed_to_members")
        log = EventLog()
        rc.resolve_dissolution_fund(5, rule, frozenset((0,)), agents, config, log)
        assert log.fund_dissolutions == []

    def test_no_living_recipients_still_zeroes_fund_and_logs_zero_recipients(self):
        rule = _rule(fund=9.0)
        agents = {0: _agent(0)}
        agents[0].alive = False
        config = SimulationConfig.level1_rule_formation_default(fund_dissolution_disposition="distributed_to_members")
        log = EventLog()
        rc.resolve_dissolution_fund(5, rule, frozenset((0,)), agents, config, log)
        assert rule.fund == 0.0
        assert log.fund_dissolutions[0].n_recipients == 0


class TestFullResourceLedgerIdentity:
    def test_full_run_ledger_identity_with_contributions_and_dissolutions(self):
        config = SimulationConfig.level11_complete(
            population_size=50, n_steps=250, n_patches=3, seed=21, contribution_mode="voluntary",
        )
        sim = Simulation(config)
        sim.run()
        contributed = sum(e.amount_paid for e in sim.event_log.contributions)
        spent = sum(e.amount for e in sim.event_log.administrative_spending if e.funded_by == "collective_fund")
        appropriated = sum(e.amount for e in sim.event_log.appropriations)
        recovered = sum(e.recovered_funds for e in sim.event_log.recalls)
        transferred_net = sum(0.0 for _ in sim.event_log.coordination_activity)  # transfers move fund<->fund, net 0 across both rules
        disposed = sum(e.amount for e in sim.event_log.fund_dissolutions if e.disposition != "retained_for_reconstruction")
        remaining_fund = sum(r.fund for r in sim.rule_registry.values())
        retained = sum(e.amount for e in sim.event_log.fund_dissolutions if e.disposition == "retained_for_reconstruction")
        # Everything that ever entered a fund (contributions + recovered
        # appropriations - the coordination cost, which leaves the fund
        # system entirely) must equal what left it (spending +
        # appropriation + disposed-at-dissolution) plus what remains.
        coordination_cost = sum(e.total_cost for e in sim.coordination_link_registry.values())
        inflow = contributed + recovered
        outflow = spent + appropriated + disposed + coordination_cost
        assert inflow - outflow == pytest.approx(remaining_fund - retained, abs=1e-6)
