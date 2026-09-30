"""Level 1.1b, Work Package D: appropriation opportunity vs. conduct
decomposition.

Level 1.1's `level11_no_admin_cost` ablation found that removing
administrative *cost* increased total appropriated resources, but could
not say whether that was because *opportunity* changed (funds simply sat
around larger/longer once nothing was spent maintaining the rule) or
*conduct* changed (delegates became more likely to attempt appropriation,
or attempted a larger fraction, once administrative cost was zero) —
because `AppropriationEvent` only fires on an actual appropriation, with
no record of opportunities that existed but were not acted on.

This module tests the fix (`AppropriationOpportunityEvent`, logged for
EVERY opportunity — `discretion_enabled and rule.fund > 0.0` —
regardless of whether the delegate attempted anything) and the matched-
seed decomposition it enables."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog
from abm_governance.rules import delegation as rd
from abm_governance.rules.shared_rule import RuleParameters, SharedRule
from abm_governance.simulation import Simulation


def _agent(agent_id, patch_id=0, resources=20.0, **overrides):
    a = Agent(
        agent_id=agent_id, resources=resources, coercive_capability=0.0, policy=make_policy("tit_for_tat"),
        observation_accuracy=1.0, learning_rate=0.1, forgiveness=0.1, risk_sensitivity=0.5, exit_cost=0.1,
    )
    a.patch_id = patch_id
    a.ecological_policy = EcologicalPolicy(0.5, 0.3, 0.0)
    a.administrative_reliability = 0.9
    a.appropriation_propensity = 0.5
    a.effort_reduction_propensity = 0.0
    for k, v in overrides.items():
        setattr(a, k, v)
    return a


def _rule(rule_id=0, patch_id=0, members=(0, 1, 2), fund=10.0):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    r = SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=0, rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )
    r.fund = fund
    return r


def _delegate(delegate_id, agent_id, rule_id, tasks=("resource_accounting",)):
    return rd.Delegate(
        delegate_id=delegate_id, rule_id=rule_id, rule_lineage_id=rule_id, patch_id=0,
        agent_id=agent_id, tasks=tuple(tasks), appointment_method="lottery", start_step=0,
    )


class TestOpportunityEventFiresRegardlessOfAttempt:
    def test_zero_propensity_logs_opportunity_but_never_attempts(self):
        agent = _agent(0, resources=5.0, appropriation_propensity=0.0)
        agents = {0: agent}
        rule = _rule(fund=10.0)
        registry = {0: rule}
        delegate = _delegate(0, 0, 0)
        delegate_registry = {0: delegate}
        config = SimulationConfig.level11_complete(delegation_task_cost=0.0)
        rng = np.random.default_rng(0)
        log = EventLog()
        rd.task_performance_round(0, registry, delegate_registry, agents, config, rng, log)
        assert len(log.appropriation_opportunities) == 1
        opp = log.appropriation_opportunities[0]
        assert opp.attempted is False
        assert opp.attempted_amount == pytest.approx(0.0)
        assert opp.realized_amount == pytest.approx(0.0)
        assert opp.fraction_of_opportunity == pytest.approx(0.0)
        assert opp.fund_before == pytest.approx(10.0)
        assert log.appropriations == []  # no actual appropriation
        assert rule.fund == pytest.approx(10.0)  # untouched

    def test_certain_propensity_logs_opportunity_and_attempts(self):
        agent = _agent(0, resources=5.0, appropriation_propensity=1.0)
        agents = {0: agent}
        rule = _rule(fund=10.0)
        registry = {0: rule}
        delegate = _delegate(0, 0, 0)
        delegate_registry = {0: delegate}
        config = SimulationConfig.level11_complete(appropriation_opportunity_scale=1.0, appropriation_fraction_of_fund=0.3, delegation_task_cost=0.0)
        rng = np.random.default_rng(0)
        log = EventLog()
        rd.task_performance_round(0, registry, delegate_registry, agents, config, rng, log)
        assert len(log.appropriation_opportunities) == 1
        opp = log.appropriation_opportunities[0]
        assert opp.attempted is True
        assert opp.attempted_amount == pytest.approx(3.0)
        assert opp.realized_amount == pytest.approx(3.0)
        assert opp.fraction_of_opportunity == pytest.approx(0.3)
        assert len(log.appropriations) == 1
        assert log.appropriations[0].amount == pytest.approx(3.0)
        assert rule.fund == pytest.approx(7.0)
        assert agent.resources == pytest.approx(8.0)

    def test_no_fund_means_no_opportunity_event_at_all(self):
        """fund == 0.0 -> not even an opportunity existed -- distinct from
        'opportunity existed but declined' (propensity=0 case above),
        which DOES log an opportunity event with attempted=False."""
        agent = _agent(0, appropriation_propensity=1.0)
        agents = {0: agent}
        rule = _rule(fund=0.0)
        registry = {0: rule}
        delegate = _delegate(0, 0, 0)
        delegate_registry = {0: delegate}
        config = SimulationConfig.level11_complete()
        rng = np.random.default_rng(0)
        log = EventLog()
        rd.task_performance_round(0, registry, delegate_registry, agents, config, rng, log)
        assert log.appropriation_opportunities == []
        assert log.appropriations == []


class TestLedgerIdentities:
    def test_realized_equals_attempted_amount_always(self):
        # No partial-failure mode exists in this implementation --
        # attempted_amount and realized_amount must always be equal.
        for propensity in (0.0, 0.3, 0.7, 1.0):
            agent = _agent(0, appropriation_propensity=propensity)
            agents = {0: agent}
            rule = _rule(fund=15.0)
            registry = {0: rule}
            delegate_registry = {0: _delegate(0, 0, 0)}
            config = SimulationConfig.level11_complete()
            for seed in range(5):
                rng = np.random.default_rng(seed)
                log = EventLog()
                rd.task_performance_round(0, registry, delegate_registry, agents, config, rng, log)
                for opp in log.appropriation_opportunities:
                    assert opp.attempted_amount == pytest.approx(opp.realized_amount)

    def test_fund_and_agent_resources_close_exactly_on_attempt(self):
        agent = _agent(0, resources=5.0, appropriation_propensity=1.0)
        agents = {0: agent}
        rule = _rule(fund=10.0)
        registry = {0: rule}
        delegate_registry = {0: _delegate(0, 0, 0)}
        config = SimulationConfig.level11_complete(appropriation_opportunity_scale=1.0, appropriation_fraction_of_fund=0.4, delegation_task_cost=0.0)
        rng = np.random.default_rng(0)
        log = EventLog()
        fund_before = rule.fund
        resources_before = agent.resources
        rd.task_performance_round(0, registry, delegate_registry, agents, config, rng, log)
        opp = log.appropriation_opportunities[0]
        assert rule.fund == pytest.approx(fund_before - opp.realized_amount)
        assert agent.resources == pytest.approx(resources_before + opp.realized_amount)


class TestOpportunityVsConductDecomposition:
    """Matched-seed substream counterfactual: level11_no_admin_cost vs.
    level11_complete under mechanism_substreams mode. Direct answer to
    the Level 1.1 ambiguity (removing admin cost increased appropriation
    -- opportunity or conduct?)."""

    def test_appropriation_propensity_trait_unaffected_by_admin_cost_ablation(self):
        # appropriation_propensity is drawn once at population
        # construction (delegation_rng, per Work Package A) and never
        # modified by admin-cost dynamics -- confirms conduct's *input*
        # (the fixed trait) cannot itself be the channel; only p_appropriate
        # (opportunity_scale x propensity, config-level, also unaffected
        # by cost) or the realized attempt/amount could differ.
        base_kwargs = dict(population_size=30, n_patches=3, n_steps=1, seed=10)
        baseline = Simulation(SimulationConfig.level11_complete(**base_kwargs, rng_mode="mechanism_substreams")).agents
        no_cost = Simulation(SimulationConfig.level11_no_admin_cost(**base_kwargs, rng_mode="mechanism_substreams")).agents
        baseline_propensities = sorted(a.appropriation_propensity for a in baseline)
        no_cost_propensities = sorted(a.appropriation_propensity for a in no_cost)
        assert baseline_propensities == pytest.approx(no_cost_propensities)

    def test_opportunity_and_conduct_separately_measurable_across_seeds(self):
        rows = []
        for seed in range(6):
            base_kwargs = dict(population_size=30, n_patches=3, n_steps=120, seed=seed, rng_mode="mechanism_substreams")
            for label, cfg in (
                ("baseline", SimulationConfig.level11_complete(**base_kwargs)),
                ("no_admin_cost", SimulationConfig.level11_no_admin_cost(**base_kwargs)),
            ):
                log = Simulation(cfg).run().event_log
                opps = log.appropriation_opportunities
                n_opportunities = len(opps)
                n_attempts = sum(1 for o in opps if o.attempted)
                total_realized = sum(o.realized_amount for o in opps)
                rows.append({
                    "seed": seed, "condition": label,
                    "n_opportunities": n_opportunities, "n_attempts": n_attempts,
                    "attempt_rate_given_opportunity": (n_attempts / n_opportunities) if n_opportunities else float("nan"),
                    "total_realized": total_realized,
                })
        # Both conditions must actually produce measurable opportunity
        # and attempt counts for the decomposition to be meaningful at
        # all (a degenerate all-zero run would make "opportunity vs
        # conduct" unanswerable, not merely inconvenient).
        baseline_rows = [r for r in rows if r["condition"] == "baseline"]
        no_cost_rows = [r for r in rows if r["condition"] == "no_admin_cost"]
        assert sum(r["n_opportunities"] for r in baseline_rows) > 0
        assert sum(r["n_opportunities"] for r in no_cost_rows) > 0
        # The two conditions' opportunity and attempt-rate figures are
        # reported here as descriptive quantities, not asserted to differ
        # in a particular direction -- that comparison belongs to the
        # experiment script / validation note, not a unit test.
