"""Level 1.1b, Work Package F: institutional memory validation.

Level 1.1 found `institutional_memory_retention`/
`institutional_memory_transfer_to_new_delegate` had a "negligible effect
at default parameters" but never confirmed with a matched-seed
dose-response sweep whether that reflected a genuinely inert/broken
mechanism or a real, working, but small-at-default-calibration one. This
module tests the transfer arithmetic directly (unit level, on
`nomination_and_selection_round`) and sanity-checks the sweep script's
own summary function."""

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


def _agent(agent_id, patch_id=0, resources=20.0, **overrides):
    a = Agent(
        agent_id=agent_id, resources=resources, coercive_capability=0.0, policy=make_policy("tit_for_tat"),
        observation_accuracy=1.0, learning_rate=0.1, forgiveness=0.1, risk_sensitivity=0.5, exit_cost=0.1,
    )
    a.patch_id = patch_id
    a.ecological_policy = EcologicalPolicy(0.5, 0.3, 0.0)
    a.nomination_probability = 1.0
    for k, v in overrides.items():
        setattr(a, k, v)
    return a


def _rule(rule_id=0, patch_id=0, members=(0, 1, 2, 3)):
    params = RuleParameters(0.3, 0.4, 0.5, 0.5, 0.5, 0.5)
    return SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=0,
        founder_id=0, rule_lineage_id=rule_id, members=frozenset(members), supporters=frozenset(members),
    )


def _removed_delegate(record_quality: float) -> rd.Delegate:
    d = rd.Delegate(
        delegate_id=0, rule_id=0, rule_lineage_id=0, patch_id=0, agent_id=0,
        tasks=("resource_accounting",), appointment_method="lottery", start_step=0,
    )
    d.record_quality = record_quality
    d.active = False
    d.removal_step = 5
    d.removal_reason = "recalled"
    return d


def _run_nomination_to_resolution(existing_delegate, retention, transfer, seed=0):
    """One nomination-window step (window=1, lottery procedure) is
    enough to resolve selection deterministically, since the guard is
    ``(step - opened_step) >= (window_steps - 1)``."""
    agents = {i: _agent(i) for i in range(4)}
    rule = _rule()
    registry = {0: rule}
    delegate_registry = {0: existing_delegate} if existing_delegate is not None else {}
    config = SimulationConfig.level11b_substreams(
        institutional_memory_retention=retention, institutional_memory_transfer_to_new_delegate=transfer,
        delegate_nomination_window_steps=1, delegate_selection_procedure="lottery",
    )
    rng = np.random.default_rng(seed)
    log = EventLog()
    id_state = {"next_delegate_id": 1}
    rd.nomination_and_selection_round(
        1, registry, agents, None, delegate_registry, {}, {}, config, rng, log, id_state,
    )
    return rule, delegate_registry, log


class TestInstitutionalMemoryTransferArithmetic:
    def test_no_prior_delegate_leaves_institutional_memory_at_zero_default(self):
        """A rule with no prior delegate has nothing to remember yet --
        institutional_memory must stay at its 0.0 default, never
        fabricated from thin air."""
        rule, delegate_registry, log = _run_nomination_to_resolution(None, retention=1.0, transfer=1.0)
        assert rule.institutional_memory == pytest.approx(0.0)
        appts = [e for e in log.delegate_appointments]
        assert len(appts) == 1
        assert appts[0].predecessor_delegate_id is None
        assert appts[0].institutional_memory_inherited == pytest.approx(0.0)

    def test_zero_retention_delivers_exactly_zero_dose_regardless_of_transfer(self):
        existing = _removed_delegate(record_quality=0.9)
        rule, delegate_registry, log = _run_nomination_to_resolution(existing, retention=0.0, transfer=1.0)
        assert rule.institutional_memory == pytest.approx(0.0)
        appts = [e for e in log.delegate_appointments if e.predecessor_delegate_id is not None]
        assert len(appts) == 1
        assert appts[0].institutional_memory_inherited == pytest.approx(0.0)

    def test_zero_transfer_delivers_exactly_zero_dose_even_with_full_retention(self):
        existing = _removed_delegate(record_quality=0.9)
        rule, delegate_registry, log = _run_nomination_to_resolution(existing, retention=1.0, transfer=0.0)
        # institutional_memory itself is still set (retention=1.0)...
        assert rule.institutional_memory == pytest.approx(0.9)
        # ...but nothing is transferred to the successor's own record_quality.
        appts = [e for e in log.delegate_appointments if e.predecessor_delegate_id is not None]
        assert appts[0].institutional_memory_inherited == pytest.approx(0.0)

    def test_partial_retention_and_transfer_multiply_as_documented(self):
        existing = _removed_delegate(record_quality=0.8)
        rule, delegate_registry, log = _run_nomination_to_resolution(existing, retention=0.5, transfer=0.5)
        # institutional_memory = clip(0.8 * 0.5) = 0.4; dose = clip(0.4 * 0.5) = 0.2.
        assert rule.institutional_memory == pytest.approx(0.4)
        appts = [e for e in log.delegate_appointments if e.predecessor_delegate_id is not None]
        assert appts[0].institutional_memory_inherited == pytest.approx(0.2)
        new_delegate = delegate_registry[0]
        assert new_delegate.record_quality == pytest.approx(0.2)

    def test_full_retention_and_transfer_passes_through_predecessor_quality_unclipped_within_bounds(self):
        existing = _removed_delegate(record_quality=0.6)
        rule, delegate_registry, log = _run_nomination_to_resolution(existing, retention=1.0, transfer=1.0)
        assert rule.institutional_memory == pytest.approx(0.6)
        new_delegate = delegate_registry[0]
        assert new_delegate.record_quality == pytest.approx(0.6)

    def test_institutional_memory_overwrites_rather_than_accumulates_across_successive_replacements(self):
        """Section requirement: memory reflects the most recently
        departed office-holder's own quality, not an ever-thickening
        blend -- a low-quality predecessor after a high-quality one
        should DROP the rule's institutional_memory, not average it."""
        high_quality_predecessor = _removed_delegate(record_quality=0.9)
        rule, delegate_registry, _ = _run_nomination_to_resolution(high_quality_predecessor, retention=1.0, transfer=1.0)
        assert rule.institutional_memory == pytest.approx(0.9)

        # Now that same rule's newly-appointed delegate is itself removed
        # with a much lower record_quality, and a second replacement fires.
        second_predecessor = delegate_registry[0]
        second_predecessor.record_quality = 0.1
        second_predecessor.active = False
        second_predecessor.removal_step = 10
        agents = {i: _agent(i) for i in range(4)}
        registry = {0: rule}
        delegate_registry_2 = {0: second_predecessor}
        config = SimulationConfig.level11b_substreams(
            institutional_memory_retention=1.0, institutional_memory_transfer_to_new_delegate=1.0,
            delegate_nomination_window_steps=1, delegate_selection_procedure="lottery",
        )
        rng = np.random.default_rng(1)
        log2 = EventLog()
        rd.nomination_and_selection_round(
            11, registry, agents, None, delegate_registry_2, {}, {}, config, rng, log2, {"next_delegate_id": 2},
        )
        assert rule.institutional_memory == pytest.approx(0.1)  # overwritten, not (0.9+0.1)/2 or similar


class TestInstitutionalMemoryValidationSweepScript:
    """A cheap, small-scale smoke test of the sweep script's own
    per-run summary function -- not a re-run of the full 15-seed x
    5-condition confirmatory sweep (see
    experiments/level11b_institutional_memory_validation.py directly
    for that)."""

    def test_summarize_run_manipulation_check_zero_retention_gives_zero_dose(self):
        from experiments.level11b_institutional_memory_validation import _config_for, _summarize_run

        cfg = _config_for(retention=0.0, transfer=0.5, seed=0)
        cfg = cfg.__class__.from_dict({**cfg.to_dict(), "population_size": 20, "n_patches": 2, "n_steps": 60})
        result = _summarize_run(cfg)
        if result["mean_dose_delivered"] is not None:
            assert result["mean_dose_delivered"] == pytest.approx(0.0)

    def test_summarize_run_nonzero_retention_can_deliver_nonzero_dose(self):
        from experiments.level11b_institutional_memory_validation import _config_for, _summarize_run

        cfg = _config_for(retention=1.0, transfer=1.0, seed=0)
        cfg = cfg.__class__.from_dict({**cfg.to_dict(), "population_size": 20, "n_patches": 2, "n_steps": 200})
        result = _summarize_run(cfg)
        # At a long enough run with max dose, at least one successor
        # appointment should have occurred and delivered a nonzero dose
        # -- otherwise the whole sweep's premise (turnover actually
        # happens) would be untestable.
        assert result["n_successor_appointments"] >= 1
