"""Level 1.3b, Work Package B (Section 6): standing regression guard for
the ``_contribution_compliance_series`` construction bug found and fixed
during this milestone's preflight/Work-Package-B audit — see
``docs/level1.3b_bargaining_activation_audit.md`` for the full account,
and ``dev_mem/status_update.md``'s 2026-08-21 entry for the discovery
narrative.

**The bug.** ``bargaining_participation``'s series (``_contribution_
compliance_series``) was zero-filled on every step that was not a
contribution-assessment round, unlike every other ``institutional_
response_series`` dimension (which HOLDS state across an active
interval). Since contribution rounds only run every
``contribution_period_steps`` (default 10) steps, and every Level 1.3/
1.3b stage script passes ``sequencing_vector(..., min_duration_steps=10)``
— exactly equal to that period — the series could never have 2
consecutive steps at/above threshold, so ``first_sustained_crossing``
was mathematically guaranteed to return ``None`` for this one dimension,
independent of the true compliance rate. This is why
``seq_bargaining_participation`` was ``NaN`` in 100% (216/216) of Level
1.3's pooled discovery runs.

**The fix.** ``_contribution_compliance_series`` now HOLDS (forward-
fills) the most recently assessed compliance ratio across the
intervening steps, exactly matching how every other dimension already
represents "current institutional state" via ``_interval_counts``.

This file tests the CONSTRUCTION fix in isolation (this is a regression
guard against the construction bug recurring, not a claim about the
true generative compliance rate — that is a separate, disclosed,
resource-collapse-driven finding covered in the audit doc itself, not
retested here)."""

from __future__ import annotations

import numpy as np
import pytest

from abm_governance.core.events import ContributionEvent, EventLog
from abm_governance.core.historical_pressure import first_sustained_crossing
from abm_governance.observer import sequencing_diagnostics as sd


def _contribution(step, agent, complied, patch_id=0, rule_id=0):
    return ContributionEvent(
        step=step, patch_id=patch_id, rule_id=rule_id, agent=agent, mode="voluntary",
        amount_asked=1.0, amount_paid=(1.0 if complied else 0.0), complied=complied, fund_after=1.0,
    )


class TestComplianceSeriesIsHeldNotZeroFilled:
    def test_hand_computed_microcase_three_rounds_ten_step_period(self):
        """Hand-computed microcase (Stage 1's own required discipline):
        3 contribution rounds at steps 0, 10, 20 (period=10), 2 agents
        each round, n_steps=25. Round 0: 1/2 comply -> 0.5. Round 10:
        2/2 comply -> 1.0. Round 20: 0/2 comply -> 0.0. Expected series,
        computed by hand: steps [0..9] = 0.5 (held from round 0), steps
        [10..19] = 1.0 (held from round 10), steps [20..24] = 0.0 (held
        from round 20)."""
        log = EventLog()
        log.add(_contribution(0, agent=0, complied=True))
        log.add(_contribution(0, agent=1, complied=False))
        log.add(_contribution(10, agent=0, complied=True))
        log.add(_contribution(10, agent=1, complied=True))
        log.add(_contribution(20, agent=0, complied=False))
        log.add(_contribution(20, agent=1, complied=False))
        series = sd.institutional_response_series(log, n_steps=25)
        bp = series["bargaining_participation"]
        expected = np.array([0.5] * 10 + [1.0] * 10 + [0.0] * 5)
        assert bp == pytest.approx(expected)

    def test_steps_before_first_round_hold_zero(self):
        log = EventLog()
        log.add(_contribution(5, agent=0, complied=True))
        series = sd.institutional_response_series(log, n_steps=8)
        bp = series["bargaining_participation"]
        assert list(bp[:5]) == [0.0] * 5
        assert bp[5] == pytest.approx(1.0)
        assert bp[7] == pytest.approx(1.0)  # held forward, not zero-filled

    def test_no_contributions_at_all_gives_all_zero_not_nan(self):
        log = EventLog()
        series = sd.institutional_response_series(log, n_steps=5)
        assert list(series["bargaining_participation"]) == [0.0] * 5


class TestSustainedCrossingCanNowRegister:
    """The decisive regression case: before the fix, this exact
    construction made a sustained crossing mathematically impossible
    regardless of compliance rate, at the period-matched
    ``min_duration_steps=10`` every Level 1.3/1.3b stage script uses."""

    def test_perfect_compliance_every_round_registers_a_sustained_crossing(self):
        log = EventLog()
        period = 10
        n_steps = 500
        for step in range(0, n_steps, period):
            log.add(_contribution(step, agent=0, complied=True))
            log.add(_contribution(step, agent=1, complied=True))
        series = sd.institutional_response_series(log, n_steps=n_steps)
        vector = sd.sequencing_vector(series, min_duration_steps=10)
        assert vector["bargaining_participation"] is not None
        # first held-window covers steps [0, 9]; threshold 0.3 crossed at step 0.
        assert vector["bargaining_participation"] == 0

    def test_before_the_fix_this_same_series_would_have_been_none(self):
        """Direct proof the OLD (zero-fill) construction was the actual
        defect, not a fixture artifact: reconstructing the pre-fix
        series by hand (nonzero only at assessment steps, zero
        elsewhere) and feeding it straight to ``first_sustained_
        crossing`` still returns ``None`` under the real
        ``min_duration_steps=10`` every stage script uses -- confirming
        the fix in ``_contribution_compliance_series`` (not a change to
        ``first_sustained_crossing`` itself, which is untouched and
        correctly generic) is what closes the gap."""
        n_steps = 500
        period = 10
        pre_fix_series = np.zeros(n_steps)
        for step in range(0, n_steps, period):
            pre_fix_series[step] = 1.0  # 100% compliance, zero-filled between rounds
        assert first_sustained_crossing(pre_fix_series, threshold=0.3, min_duration_steps=10) is None

    def test_genuinely_low_compliance_still_does_not_register(self):
        """The construction fix does not manufacture activation out of
        nothing -- a genuinely low, sustained compliance rate (below
        threshold every round) still correctly never crosses."""
        log = EventLog()
        period = 10
        n_steps = 200
        for step in range(0, n_steps, period):
            log.add(_contribution(step, agent=0, complied=False))
            log.add(_contribution(step, agent=1, complied=False))
            log.add(_contribution(step, agent=2, complied=False))
            log.add(_contribution(step, agent=3, complied=True))  # 1/4 = 0.25 < 0.3 threshold
        series = sd.institutional_response_series(log, n_steps=n_steps)
        vector = sd.sequencing_vector(series, min_duration_steps=10)
        assert vector["bargaining_participation"] is None
