"""Level 1.1b, Work Package C: coordination acceptance audit.

Investigates the Level 1.1 "72/72" proposal-to-acceptance result
(``docs/level1.1_scientific_note.md`` §4) end-to-end: confirms bilateral
evaluation happens independently per proposal (a fresh draw, gated by the
*recipient* rule's own members' propensity, distinct from the proposer's
side, which is deemed to accept by construction — see
``rules/coordination.py``'s module docstring), confirms rejection events
are logged distinctly from acceptance events (not merged or silently
dropped), and adds hand-computed unit tests for every reachable outcome:
both-sides-effectively-accept, first-attempt-rejects-then-window-expires,
a proposal to a since-deactivated counterpart rule, a duplicate-proposal
guard, and the fund-independence of link formation/activity (only the
*mutual-assistance transfer amount* is fund-limited, never acceptance or
whether an activity step happens at all).

**Finding:** the "72/72" result is not a missing rejection pathway or a
bug. At Level 1.1's default ``coordination_proposal_window_steps=5``, a
pending proposal gets up to 5 independent per-step acceptance draws
before its window expires — at the default
``interpatch_acceptance_propensity ~ N(0.5, 0.2)`` (clipped, averaged
over the recipient rule's members), each single attempt succeeds only
about half the time, but the probability of *at least one* success
within 5 attempts is close to 1 - 0.5**5 ≈ 0.97. "72/72" is therefore a
plausible (if fortunate) draw from an ~90-97%-per-proposal eventual-
success distribution, not evidence that rejection cannot occur — this
module's own reproduction below recovers genuine window-expiry
rejections at the very same default parameters, just at other seeds. See
``experiments/level11b_coordination_calibration.py`` for the full sweep
and ``core/config.py::SimulationConfig.level11b_coordination_nondegenerate``
for a preset (``coordination_proposal_window_steps=1``, single-attempt)
where acceptance and rejection are both common."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog
from abm_governance.rules import coordination as rc
from abm_governance.rules.shared_rule import RuleParameters, SharedRule
from abm_governance.simulation import Simulation


def _agent(agent_id, patch_id=0, resources=20.0, **overrides):
    a = Agent(
        agent_id=agent_id, resources=resources, coercive_capability=0.0, policy=make_policy("tit_for_tat"),
        observation_accuracy=1.0, learning_rate=0.1, forgiveness=0.1, risk_sensitivity=0.5, exit_cost=0.1,
    )
    a.patch_id = patch_id
    a.ecological_policy = EcologicalPolicy(0.5, 0.3, 0.0)
    a.interpatch_proposal_probability = 0.0
    a.interpatch_acceptance_propensity = 0.5
    for k, v in overrides.items():
        setattr(a, k, v)
    return a


def _rule(rule_id, patch_id, members, fund=0.0):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    r = SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=next(iter(members)), rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )
    r.fund = fund
    return r


def _base_setup(recipient_propensity, fund_a=0.0, fund_b=0.0):
    agents = {
        0: _agent(0, patch_id=0), 1: _agent(1, patch_id=0),
        2: _agent(2, patch_id=1, interpatch_acceptance_propensity=recipient_propensity),
        3: _agent(3, patch_id=1, interpatch_acceptance_propensity=recipient_propensity),
    }
    rule_a = _rule(0, 0, members=(0, 1), fund=fund_a)
    rule_b = _rule(1, 1, members=(2, 3), fund=fund_b)
    registry = {0: rule_a, 1: rule_b}
    return agents, registry


class TestBilateralAcceptance:
    def test_recipient_side_evaluated_independently_of_proposer_side(self):
        """The proposer's own side is deemed to accept by construction
        (it initiated the proposal) -- only the recipient's members'
        mean interpatch_acceptance_propensity gates the accept/reject
        draw. Confirmed directly: a recipient with propensity=1.0 always
        accepts regardless of what the proposer's own (irrelevant to
        this draw) propensity is set to."""
        agents, registry = _base_setup(recipient_propensity=1.0)
        pending = {(0, 1): rc._PendingCoordinationProposal(
            patch_id_from=0, patch_id_to=1, rule_id_from=0, rule_id_to=1,
            kind="information_exchange", proposer=0, opened_step=0,
        )}
        link_registry: dict = {}
        config = SimulationConfig.level11b_substreams(interpatch_coordination_enabled=True)
        rng = np.random.default_rng(0)
        log = EventLog()
        id_state = {"next_link_id": 0}
        rc.coordination_round(1, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert len(log.coordination_links) == 1
        assert log.coordination_links[0].accepted is True
        assert len(link_registry) == 1
        assert pending == {}

    def test_recipient_rejects_every_attempt_then_window_expires(self):
        """propensity=0.0 -> the recipient's draw fails on every single
        attempt (rng.random() < 0.0 is never true) -- distinct from
        'never evaluated'. ``window_expired`` is
        ``(step - opened_step) >= (window_steps - 1)``, so with
        ``window_steps=3`` (opened at step 0) the proposal must stay
        pending (no event logged) after its first evaluation (step 1:
        1 >= 2 is False), and get a distinctly-reasoned window_expired
        rejection on its second (step 2: 2 >= 2 is True) -- i.e. exactly
        ``window_steps - 1`` evaluation attempts occur before expiry."""
        agents, registry = _base_setup(recipient_propensity=0.0)
        pending = {(0, 1): rc._PendingCoordinationProposal(
            patch_id_from=0, patch_id_to=1, rule_id_from=0, rule_id_to=1,
            kind="information_exchange", proposer=0, opened_step=0,
        )}
        link_registry: dict = {}
        config = SimulationConfig.level11b_substreams(interpatch_coordination_enabled=True, coordination_proposal_window_steps=3)
        rng = np.random.default_rng(0)
        log = EventLog()
        id_state = {"next_link_id": 0}

        rc.coordination_round(1, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert log.coordination_links == []  # still pending, no event yet
        assert (0, 1) in pending

        rc.coordination_round(2, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert len(log.coordination_links) == 1
        assert log.coordination_links[0].accepted is False
        assert log.coordination_links[0].reason == "window_expired"
        assert (0, 1) not in pending
        assert link_registry == {}

    def test_counterpart_rule_no_longer_active_rejected_immediately(self):
        """A pending proposal whose target rule has since been removed
        from the registry (dissolved) is rejected immediately, with its
        own distinct reason -- never silently treated as an ordinary
        propensity-based rejection, and never left pending forever."""
        agents, registry = _base_setup(recipient_propensity=1.0)
        del registry[1]  # counterpart rule no longer active
        pending = {(0, 1): rc._PendingCoordinationProposal(
            patch_id_from=0, patch_id_to=1, rule_id_from=0, rule_id_to=1,
            kind="information_exchange", proposer=0, opened_step=0,
        )}
        link_registry: dict = {}
        config = SimulationConfig.level11b_substreams(interpatch_coordination_enabled=True)
        rng = np.random.default_rng(0)
        log = EventLog()
        id_state = {"next_link_id": 0}
        rc.coordination_round(1, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert len(log.coordination_links) == 1
        assert log.coordination_links[0].accepted is False
        assert log.coordination_links[0].reason == "counterpart_rule_no_longer_active"
        assert pending == {}
        assert link_registry == {}

    def test_already_linked_patch_never_generates_a_duplicate_proposal(self):
        """A patch that already has an active link (or a pending
        proposal) is excluded from the new-proposal pass entirely -- even
        when its members' interpatch_proposal_probability is 1.0 (a
        certain-to-propose configuration if it *were* eligible)."""
        agents, registry = _base_setup(recipient_propensity=1.0)
        for a in agents.values():
            a.interpatch_proposal_probability = 1.0
        link_registry = {
            0: rc.CoordinationLink(
                link_id=0, patch_id_a=0, patch_id_b=1, rule_id_a=0, rule_id_b=1,
                kind="information_exchange", proposed_step=0, accepted_step=0,
            )
        }
        pending: dict = {}
        config = SimulationConfig.level11b_substreams(
            interpatch_coordination_enabled=True, coordination_proposal_probability=1.0,
            coordination_activity_probability=0.0, coordination_dissolution_probability=0.0,
        )
        rng = np.random.default_rng(0)
        log = EventLog()
        id_state = {"next_link_id": 1}
        rc.coordination_round(1, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert log.coordination_proposals == []
        assert pending == {}


class TestFundIndependence:
    def test_zero_fund_does_not_block_link_activity_only_caps_transfer(self):
        """Fund balance never gates whether a link forms or whether an
        activity step happens -- ``coordination_cost_per_step`` is paid
        as ``min(cost_each, rule.fund)`` (a documented no-op when a side
        has no fund, never a hard failure), and a mutual_assistance
        transfer amount is capped by available fund (possibly to exactly
        0.0), never blocking the activity event itself from being
        logged."""
        agents, registry = _base_setup(recipient_propensity=1.0, fund_a=0.0, fund_b=0.0)
        link_registry = {
            0: rc.CoordinationLink(
                link_id=0, patch_id_a=0, patch_id_b=1, rule_id_a=0, rule_id_b=1,
                kind="mutual_assistance", proposed_step=0, accepted_step=0,
            )
        }
        pending: dict = {}
        config = SimulationConfig.level11b_substreams(
            interpatch_coordination_enabled=True, coordination_activity_probability=1.0,
            coordination_dissolution_probability=0.0, coordination_cost_per_step=5.0,
            coordination_assistance_occupancy_threshold=1.0,  # every occupancy value qualifies
        )
        rng = np.random.default_rng(0)
        log = EventLog()
        id_state = {"next_link_id": 1}
        rc.coordination_round(1, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert len(log.coordination_activity) == 1
        activity = log.coordination_activity[0]
        assert activity.resource_transferred == pytest.approx(0.0)  # capped by empty funds
        assert activity.cost == pytest.approx(0.0)  # min(5.0, 0.0) + min(5.0, 0.0)
        assert registry[0].fund == pytest.approx(0.0)
        assert registry[1].fund == pytest.approx(0.0)


class TestInfoAccuracyIsDescriptiveNotGating:
    def test_high_info_error_does_not_prevent_or_alter_activity(self):
        """coordination_info_error_std controls the *reported*
        info_accuracy field on a CoordinationActivityEvent -- it is never
        read to decide whether the activity step happens, whether the
        link survives, or how much is transferred. Documented explicitly
        here since the milestone brief anticipated an
        'info-error-induced accept or reject' pathway that this
        implementation does not have (activity occurs or not purely per
        coordination_activity_probability; kind/threshold/fund logic
        alone determines any transfer amount)."""
        agents, registry = _base_setup(recipient_propensity=1.0)
        link_registry = {
            0: rc.CoordinationLink(
                link_id=0, patch_id_a=0, patch_id_b=1, rule_id_a=0, rule_id_b=1,
                kind="information_exchange", proposed_step=0, accepted_step=0,
            )
        }
        pending: dict = {}
        config = SimulationConfig.level11b_substreams(
            interpatch_coordination_enabled=True, coordination_activity_probability=1.0,
            coordination_dissolution_probability=0.0, coordination_info_error_std=100.0,  # extreme noise
        )
        rng = np.random.default_rng(0)
        log = EventLog()
        id_state = {"next_link_id": 1}
        rc.coordination_round(1, registry, agents, None, link_registry, pending, config, rng, log, id_state)
        assert len(log.coordination_activity) == 1  # activity still happened despite extreme info error
        assert 0.0 <= log.coordination_activity[0].info_accuracy <= 1.0  # clipped, but merely descriptive


class TestHistoricalResultReproducedAndExplained:
    """Reproduces the exact 'level11_coordination_only-like' condition
    the historical 72/72 result came from (Level 1.1's default
    coordination_proposal_window_steps=5), across several seeds, and
    confirms genuine window-expiry rejections DO occur at some of them --
    i.e. the pathway exists and fires; the specific historical run simply
    did not happen to hit it. See
    experiments/level11b_coordination_calibration.py for the fuller
    sweep this is a compact, always-run regression version of."""

    def test_rejections_occur_at_default_window_across_seeds(self):
        any_rejection = False
        any_acceptance = False
        for seed in range(6):
            config = SimulationConfig.level11b_substreams(
                population_size=40, n_patches=3, n_steps=200, seed=seed,
                delegation_enabled=False, discretion_enabled=False, accountability_enabled=False,
                contribution_mode="none",
            )
            log = Simulation(config).run().event_log
            if any(not e.accepted and e.reason == "window_expired" for e in log.coordination_links):
                any_rejection = True
            if any(e.accepted for e in log.coordination_links):
                any_acceptance = True
        assert any_acceptance, "expected at least some acceptances across seeds at default calibration"
        assert any_rejection, (
            "expected at least one genuine window_expired rejection across seeds at default "
            "calibration -- if this ever fails, the rejection pathway may have regressed"
        )

    def test_nondegenerate_preset_produces_both_outcomes_reliably(self):
        config = SimulationConfig.level11b_coordination_nondegenerate(
            population_size=40, n_patches=3, n_steps=250, seed=0,
            delegation_enabled=False, discretion_enabled=False, accountability_enabled=False,
            contribution_mode="none",
        )
        assert config.coordination_proposal_window_steps == 1
        log = Simulation(config).run().event_log
        n_accepted = sum(1 for e in log.coordination_links if e.accepted)
        n_rejected = sum(1 for e in log.coordination_links if not e.accepted)
        n_dissolved = len(log.coordination_dissolutions)
        # Nondegenerate: acceptance, rejection, AND dissolution all occur
        # -- nothing here is mechanically certain in either direction.
        assert n_accepted > 0
        assert n_rejected > 0
        assert n_dissolved > 0
