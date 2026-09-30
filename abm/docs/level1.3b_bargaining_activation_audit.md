# Level 1.3b — Bargaining-Activation Audit (Section 6, Work Package B)

**Status: complete. Traces the full pressure -> transmission -> agent
response -> event -> observer -> feature chain for
`seq_bargaining_participation`, per Section 6's own checklist, and
answers its own governing question: was this a code defect (fix +
regression test) or genuine inactivity (build a transparent
activation-probability-vs-parameter response curve, never "merely lower
the threshold")? Both.**

## 1. The question, restated

Level 1.3's own pooled discovery input (`docs/level1.3_discovery_
methods.md` §3) shows `seq_bargaining_participation` (the sequencing
dimension for the `bargaining_participation` institutional-response
series) as `NaN` in **216 of 216** pooled runs — a complete-case
missingness rate of 100%. Section 6 requires this milestone to determine
exactly why before either fixing it or building around it, auditing
"event generation, threshold, duration, denominator, aggregation,
observer timing, missing-value assignment, eligibility, ecological
suppression, membership requirements, institutional prerequisites,
probability calibration, naming/field mismatch" as candidate causes.

## 2. Method

1. Full preflight read of every Level 1.1b/1.2/1.2b/1.3 doc naming this
   dimension, plus direct inspection of the raw Level 1.3 output JSON
   (not just prose summaries) confirming the 216/216 figure.
2. Direct code reading of the full causal chain: `core/historical_
   pressure.py` (pressure signal) -> `core/historical_transmission.py`
   (`pressure_adjusted_probability`) -> `rules/contributions.py::
   contribution_round` (agent decision + `ContributionEvent`) ->
   `observer/sequencing_diagnostics.py` (`_contribution_compliance_
   series` -> `institutional_response_series` -> `sequencing_vector`) ->
   `core/historical_pressure.py::first_sustained_crossing`.
3. Instrumented, byte-identical-behavior simulation runs (`experiments/
   level13b_stage1_bargaining_audit.py`) on a Stage-3-representative and
   a Stage-4-representative config, monkeypatching `contribution_round`
   to additionally record per-decision willingness/pressure/resource
   state before delegating unchanged to the real function.
4. A hand-computed microcase (3 contribution rounds, exact values worked
   out by hand, checked against the implementation) — Stage 1's own
   required discipline, also standing as `tests/test_level13b_
   bargaining_activation_construction.py`'s first test.

## 3. Finding 1 (dominant, deterministic, fully sufficient alone): an
   observer sampling-cadence / sustained-duration construction defect

`_contribution_compliance_series` built its per-step series from
`event_log.contributions` alone: `total[step] += 1` and `complied[step]
+= 1` only on steps where a `ContributionEvent` was actually logged.
`contribution_round` only runs every `config.contribution_period_steps`
steps (default **10**) — a strict no-op every other step. The old
implementation then ran the result through `_safe_divide`, which
zero-fills wherever the denominator is 0 — i.e. **every one of the 9
steps between assessment rounds got an explicit `0.0`**, not a
held/last-known value.

This is inconsistent with every other one of the eight
`institutional_response_series` dimensions. `delegation`,
`administrative_function`, `monitoring`, `accountability`, and
`interpatch_coordination` are all built from `_interval_counts`
and/or `_distinct_ids_per_step`, which represent *currently active
state*, held continuously across an interval — not *activity at this
instant*. `bargaining_participation` was the one dimension built the
other way, silently.

**Why this guarantees `None`, regardless of true compliance.**
`first_sustained_crossing(series, threshold, min_duration_steps)`
requires `min_duration_steps` **consecutive** steps at/above threshold
(`core/historical_pressure.py`, unchanged, correctly generic — this is
not a bug in that function). Every Level 1.3 and Level 1.3b stage script
that calls `sequencing_vector` (`level13_stage{3,4,5,9}_*.py`, all four
checked directly) passes `min_duration_steps=10` — **exactly equal** to
`contribution_period_steps=10`. Since two contribution-assessment steps
are never consecutive under this period, the old zero-filled series
could never sustain 2 (let alone 10) consecutive steps above threshold.

**Proved empirically**, not just argued: a synthetic series with **100%
compliance on every single one of 50 contribution rounds across a full
500-step run** still returns `None` under the old construction:

```
first_sustained_crossing(series, threshold=0.3, min_duration_steps=10) -> None
```

(`tests/test_level13b_bargaining_activation_construction.py::
TestSustainedCrossingCanNowRegister::test_before_the_fix_this_same_
series_would_have_been_none`). This rules out every non-construction
explanation on its own: it is not a threshold problem (100% clears any
plausible threshold), not a duration-criterion problem in the usual
sense (the criterion is internally consistent — it is `min_duration_
steps` colliding with the *sampling cadence* of the underlying series),
not an eligibility/membership/institutional-prerequisite problem (the
synthetic series has none of that machinery involved at all), and not a
probability-calibration problem.

**Disposition: code defect. Fixed.** `_contribution_compliance_series`
(`observer/sequencing_diagnostics.py`) now holds (forward-fills) the
most recently assessed ratio across the intervening steps, exactly
matching how every other dimension already represents current
institutional state. Steps before the first assessment round still hold
`0.0` (no information yet), matching every other dimension's
zero-before-onset convention. `first_sustained_crossing` itself was
**not** touched — it was already correct and generic; the bug was
entirely in what series was being fed to it.

**Regression guard:** `tests/test_level13b_bargaining_activation_
construction.py` (6 tests) — a hand-computed microcase, a
before/after-onset holding check, a no-contributions-gives-zero-not-NaN
check, the decisive 100%-compliance regression case (now registers a
crossing at step 0), a direct proof that feeding the *old* construction
the same series still returns `None` (isolating the fix to the series
construction, not `first_sustained_crossing`), and a check that
genuinely low sustained compliance still correctly never crosses (the
fix does not manufacture activation out of nothing). The existing
`tests/test_level13_sequencing_diagnostics.py::TestBargainingParticipation
Series` test (which only checks step 1 of a 1-round, 3-step fixture) is
unaffected by the fix and still passes unmodified.

## 4. Finding 2 (secondary, genuine, disclosed — not a defect to patch
   around): willingness/solvency conflation compounded by resource
   collapse

Even with Finding 1 fixed, realized bargaining-participation compliance
on both representative configs remains far below the 0.3 threshold on
average — this is a genuine mechanism result, not a measurement
artifact, and Section 6 explicitly forbids treating genuine inactivity
by "merely lowering the threshold."

**The transmission channel is correctly wired and has a real effect.**
`bargaining_pressure_conditional_contribution_enabled` nudges the
compliance draw's effective willingness via `pressure_adjusted_
probability` — confirmed via direct measurement, not assumed: mean
effective willingness across all instrumented decisions was **0.537**
(Stage-3-representative) and **0.623** (Stage-4-representative),
meaningfully above the 0.5 trait baseline, at mean realized
`bargaining_pressure_level` of **0.387** and **0.439** respectively.
Willingness-only (ignoring solvency), **58%** and **78%** of decisions
would comply. The pressure channel is doing exactly what Work Package A
built it to do.

**But the `ContributionEvent.complied` field conflates two different
things.** In `contribution_round`: `complied = rng.random() < willingness`
is the true behavioral draw, but the event's own field is set to
`complied and amount_paid > 0.0`, where `amount_paid = min(amount_asked,
max(0.0, member.resources))`. An agent who genuinely drew "willing" but
has zero or negative resources is recorded identically to an agent who
was simply unwilling.

**Resources collapse deeply negative over a run**, consistent with this
project's already-documented, recurring near-universal ecological-
collapse dynamic (Level 1.2/1.2b/1.3 alike): mean resources per run
third ranged from **-95 (early) to -344 (late)** on the Stage-3-
representative config, and **-73 (early) to -410 (late)** on Stage-4-
representative — **90% and 88%** of all instrumented contribution
decisions occurred with the agent already at zero/negative resources.
Realized (willingness-AND-solvency) compliance is correspondingly
crushed: **6.7%** (Stage 3) and **7.5%** (Stage 4) of contribution
events overall, versus the 58%/78% willingness-only rate above.

**A genuinely informative, disclosed nuance the post-fix construction
surfaces**: realized compliance is not uniform across a run — it is
highest in the earliest round(s), before resource collapse takes hold,
and degrades thereafter. Per-round realized compliance, first 8 rounds:

| run | round 10 | round 20 | round 30 | round 40 | round 50 | round 60 | round 70 | round 80 |
|---|---|---|---|---|---|---|---|---|
| Stage 3-representative | 0.067 | 0.286 | 0.094 | 0.067 | 0.111 | 0.097 | 0.097 | 0.097 |
| Stage 4-representative | **0.571** | 0.214 | 0.167 | 0.200 | 0.125 | 0.071 | 0.067 | 0.061 |

On the Stage-4-representative config, round 10's 57.1% (4/7, before
resource collapse had progressed far) clears the 0.3 threshold and is
held for the full 10-step window `[10, 19]`, so `sequencing_vector` now
(post-fix) registers `bargaining_participation`'s sustained crossing at
step **10**. The Stage-3-representative config's own first round (6.7%,
1/15) never clears threshold, and no later round does either once
collapse sets in, so it still registers `None`. **This is real,
disclosed evidence that Finding 1's fix alone is already sufficient to
activate `bargaining_participation` in some configurations/seeds** — the
mechanism is not universally, structurally inactive — while confirming
Finding 2 (resource-collapse-driven solvency suppression) is a real,
independent force that keeps most configurations/seeds below threshold
regardless of Finding 1.

**Disposition: not a defect — a genuine, disclosed finding.** The
`complied` field's own semantics (a behavioral outcome that legitimately
depends on both willingness and ability to pay) are defensible as
written; the finding is that under the current mechanism-parameter
settings, solvency dominates willingness as the binding constraint on
realized participation for most of a run's duration. This directly
determines Work Package C's calibration direction (Section 6 of this
doc's own report): the licensed levers most directly responsive to this
finding are **response cost** (`contribution_amount`, currently 0.2 per
round, asked against agents whose resources are frequently already
negative) and **participation-opportunity frequency**
(`contribution_period_steps`) — not the threshold, and not the
duration criterion, both of which Section 7 already governs separately
from this finding.

## 5. Evidence table (Section 5's required format, applied to this
   audit's own claims)

| Claim | Evidence | Design type | Uncertainty available? | Reproduced? | 1.3b disposition |
|---|---|---|---|---|---|
| `_contribution_compliance_series` zero-fills between assessment rounds | Direct source read, `observer/sequencing_diagnostics.py` (pre-fix) | Code inspection | N/A (deterministic code) | Yes — read directly, then fixed | Confirmed; fixed |
| Zero-fill + `min_duration_steps=10` == `contribution_period_steps=10` makes sustained crossing impossible regardless of compliance rate | Synthetic 100%-compliance series test | Deterministic unit test | N/A | Yes, `tests/test_level13b_bargaining_activation_construction.py` | Confirmed; root cause 1 (dominant) |
| Transmission channel (`bargaining_pressure_conditional_contribution_enabled`) is correctly wired | Instrumented full-simulation runs, mean effective willingness vs. 0.5 baseline | Empirical, 2 representative configs | Single-run point estimates, not a sampled distribution — disclosed limitation | Yes, both configs | Ruled out as a cause |
| Realized compliance collapses to single digits due to resource insolvency, not unwillingness | Instrumented runs: willingness-only 58%/78% vs. realized 6.7%/7.5%; 88-90% of decisions under negative resources | Empirical, 2 representative configs | Single-run point estimates; consistent with prior milestones' independently-replicated collapse finding | Yes, both configs | Confirmed; root cause 2 (secondary, genuine) |
| Post-fix, activation CAN register in some configs (Stage-4-representative, round 10) | Direct per-round compliance breakdown + `sequencing_vector` output | Empirical, 1 representative config | Single seed — not yet a sampled rate; Work Package C's own sweep (task #113) is the powered follow-up | Yes | Confirmed; motivates, does not substitute for, Work Package C |

## 6. What this rules out

- **Naming/field mismatch**: ruled out. `bargaining_participation` (the
  sequencing dimension) is correctly, exclusively fed by
  `_contribution_compliance_series`, which is correctly fed by
  `event_log.contributions` — there is no separate `appeal_recall`
  confusion (that channel feeds `accountability_round`'s appeal
  probability and shows up in the `accountability` dimension instead,
  confirmed by direct code read of `rules/delegation.py`).
- **Eligibility/membership/institutional prerequisites**: ruled out as
  the primary cause — every representative run has active rules with
  members and a `contribution_mode` other than `"none"` throughout
  (confirmed by `level12b_frozen_reference()`'s own defaults and direct
  event-log inspection); the suppression is a downstream resource
  problem, not an upstream eligibility gate.
- **Probability calibration of the transmission channel itself**: ruled
  out — the channel measurably moves effective willingness in the
  correct direction and magnitude; the bottleneck is downstream of the
  willingness draw entirely.
- **Aggregation formula**: ruled out — `complied / total` per step is
  computed correctly; the defect was in how gaps between steps were
  filled, not in the ratio itself.

## 7. Next

Work Package C (task #113) sweeps the two levers identified in §4
(response cost, participation-opportunity frequency — plus pressure
magnitude/duration and transmission sensitivity, all explicitly licensed
by Section 7) to find a region where bargaining participation activates
in ~20-80% of eligible runs, never mechanically guaranteed and never
absent everywhere, frozen into `docs/level13b_preregistration.md` before
any phenotype discovery reuses this dimension.
