# Level 1.1b Validation Note: Causal and Measurement Validation

**Status:** Work Packages A–H complete. This note synthesizes the confirmatory
statistical read each work package's own experiment script promised ("see
docs/level1.1b_validation_note.md for the confirmatory read"). It does not
repeat every number already in `dev_mem/status_update.md`'s per-work-package
entries — those are the primary record — but gives the single-document
narrative a reader needs before deciding what Level 1.2 should do with
Level 1.1's original findings.

**What this milestone was, and was not, for.** Level 1.1 built delegation,
administrative capacity, discretion, accountability, voluntary contributions,
interpatch coordination, institutional memory, and shock/replacement
dynamics, and reported a headline finding — accountability + discretion
together shift the mechanism-validation classifier's output from
`persistent_delegation` to `accountable_delegation` — alongside six
methodological limitations. Level 1.1b's entire scope was resolving those six
limitations (plus two more identified along the way, E and H) with rigorous,
matched-seed, seed-clustered-bootstrap causal infrastructure. **It did not
add any new governance mechanism, did not search for governance phenotypes,
and did not test whether the dissertation's three SEM trajectories have
emerged.** Every work package below stayed inside that boundary.

## Work Package A — RNG substream architecture

**Problem:** Level 1.1's single shared `numpy.random.Generator` meant
ablating one mechanism (e.g. disabling `interpatch_coordination_enabled`)
silently changed the draw sequence — and therefore the trajectory — of every
other mechanism sharing that stream, even ones the ablation was not supposed
to touch. This made every prior ablation comparison not strictly
ceteris-paribus.

**Fix:** `rng_mode="mechanism_substreams"` gives each of 20 named mechanisms
its own independent `Generator`, spawned once via
`numpy.random.SeedSequence(seed).spawn()`. `rng_mode="legacy_single_stream"`
(the default) preserves Level 1.1's exact byte-for-byte behavior for
backward compatibility and regression testing. Two real, previously-unknown
bugs were found and fixed while building this: (1) `build_agents()` routed
three mechanism-conditional trait blocks through the shared `rng` even in
substream mode — a genuine isolation gap, now split into
`delegation_rng`/`contribution_rng`/`coordination_rng`; (2) a cross-process
nondeterminism bug in `observer/network_diagnostics.py::policy_assortativity`
caused by an internal unordered `set()` combined with Python's per-process
string-hash randomization — fixed by passing an explicit sorted mapping into
`networkx`'s assortativity computation, confirmed via 8/8 repeat fresh-process
runs.

**Verdict:** every Work Package C–H causal experiment in this milestone runs
under `mechanism_substreams` for exactly this reason. 26 new tests.

## Work Package B — artifact-independent testing

**Problem:** 5 of 744 tests failed on a fresh checkout because they depended
on historical output artifacts (`outputs/level03b_confirmation/`, a
`niche_phase_search` corpus) that are not committed to the repository — not
a code defect, but an undisclosed test-suite fragility.

**Fix:** precise `pytest.mark.skipif` reasons distinguish "artifact
genuinely absent, skip with a stated reason" from any other failure mode,
plus new in-fixture/pure-function companion tests that exercise the same
code paths without requiring the missing artifacts. Also fixed a real bug:
`level03b_phase_search_reanalysis.run(n_steps=...)` silently ignored its own
argument.

**Verdict:** zero test failures on an artifact-free checkout (770 passed, 6
skipped, 0 failed after this work package) — the milestone's own completion
condition for this work package, met exactly.

## Work Package C — coordination acceptance audit

**Problem:** Level 1.1 reported 72/72 (100%) interpatch-coordination
proposal acceptance with no causal account of why.

**Finding:** the default `coordination_proposal_window_steps=5` lets a
pending proposal retry its acceptance draw once per step for up to 5
attempts before its window expires. At the default
`interpatch_acceptance_propensity ~ N(0.5, 0.2)`, a single attempt succeeds
about half the time, but the probability of *at least one* success within 5
independent attempts is `1 - 0.5^5 ≈ 0.97` — this is what produced the
historical 72/72 result. A 54-run calibration sweep (`window_steps ∈
{5,3,1} × n_patches ∈ {3,5,8}`) confirmed genuine rejections occur at the
very same default parameters when pooling more seeds (94.7–91.3% empirical
acceptance, not literally 100%), and that `coordination_proposal_window_
steps=1` (new `level11b_coordination_nondegenerate` preset, the default
itself left unchanged) produces a non-degenerate 35–65% acceptance range by
removing the retry structure. **Not a bug — a documented, now-explained
property of a legitimate calibration.**

## Work Package D — appropriation opportunity vs. conduct decomposition

**Problem:** Level 1.1's `level11_no_admin_cost` ablation found *increased*
total appropriated resources with no way to say whether that reflected more
*opportunity* (funds simply available) or more *conduct* (delegates more
willing to appropriate).

**Fix:** new `AppropriationOpportunityEvent` fires on every opportunity
(`discretion_enabled and rule.fund > 0.0`), not only on an actual
appropriation. A 12-matched-seed, seed-clustered bootstrap (5000 resamples,
`BOOTSTRAP_SEED=20261`) gave a clean answer: `n_opportunities` (+97/seed, CI
[60, 140]) and `mean_fund_before_at_opportunity` (+1.40, CI [1.19, 1.60])
both exclude zero — opportunities became more frequent and larger.
`attempt_propensity_given_opportunity`'s CI ([−0.010, +0.037]) **includes
zero**, and `mean_conditional_intensity_given_attempt` is mechanically
identical (a fixed config constant, not a behavioral quantity). **Verdict,
stated per the milestone's explicit instruction: the increased appropriation
under `no_admin_cost` is an opportunity/resource-availability effect, with
no confirmed change in delegate willingness or aggressiveness — it must not
be described as delegates "behaving worse."**

## Work Package E — accountability activity vs. effective constraint

**Problem:** Level 1.1's classifier used `config.accountability_enabled` (a
flag) as a proxy for "the delegate is accountable," conflating whether
accountability machinery *ran* with whether it *worked*.

**Fix:** `audit_enabled`/`recall_enabled`/`appeal_enabled` sub-flags (with
the architectural coupling — recall requires an audit finding to trigger it
— documented rather than worked around); new `observer/accountability_
diagnostics.py` with `accountability_activity()` (descriptive counts) and
`effective_constraint()` (realized-outcome-only: true-positive detections,
funds actually recovered, genuinely corrective appeals; every
denominator-undefined rate returns `None`, never `0.0`).

**Confirmatory sweep** (12 matched seeds, 8 named conditions,
`BOOTSTRAP_SEED=20262`): net appropriation (gross minus recovered funds)
against the `no_accountability` baseline was statistically indistinguishable
under `randomized_placebo` (audit_accuracy=0.5; point=+0.004, CI [−0.525,
+0.605], includes zero) but significantly *lower* under `perfect_info`
(audit_accuracy=1.0; point=−0.541, CI [−0.922, −0.139], excludes zero).
**Verdict: activity alone does not detectably reduce net appropriation;
accurate detection does — the exact distinction Level 1.1's classifier could
not draw.** Two anomalies surfaced and reported unchanged: gross
appropriation is *higher* under full accountability than none at all
(recall-driven delegate turnover raises opportunity count, not conduct); and
`perfect_info`/`randomized_placebo` did not produce matched audit-activity
volumes as originally designed (a genuine detection→recall→replacement→
more-audits feedback loop, not an experimental confound this milestone
introduced).

## Work Package F — institutional memory validation

**Problem:** Level 1.1 called institutional memory's effect "negligible at
default parameters" without a dose-response sweep to confirm this was a real
small effect rather than an inert/broken mechanism.

**Fix:** 15-matched-seed sweep across 5 `(retention, transfer)` conditions
from `no_memory` (0.0, 0.5) to a `max_dose` ceiling (1.0, 1.0),
`BOOTSTRAP_SEED=20263`. Manipulation check passed (nonzero dose delivered at
default parameters, CI excludes zero). **Refined finding**: the paired
design is powerful enough to detect even the default condition's effect on
end-capacity as statistically nonzero (CI [+0.00030, +0.00047]) — but its
practical magnitude is only **0.22%** relative to baseline capacity, versus
**25.0%** at the `max_dose` ceiling (also CI-excludes-zero). **Verdict:
institutional memory is a real, working, monotonically dose-responsive
mechanism — correctly negligible in *practical* (not *statistical*) terms at
Level 1.1's chosen default calibration, not inert or broken.**

## Work Package G — functional shock recovery

**Problem:** Level 1.1 reported a 10/10 reappointment rate after recall and
called it "recovery" without measuring whether the successor's realized
capacity or performance actually returned to pre-shock levels.

**Fix:** 15-matched-seed run, `BOOTSTRAP_SEED=20264`, defining a "shock" as a
recall-triggered removal, "reappointed" as a same-rule appointment within 30
steps, and "functional recovery" via a bounded `recovery_gap =
post_shock_capacity − pre_shock_capacity` (not a ratio — capacity sits near
zero often enough at shock time that a ratio numerically explodes).
**Result:** reappointment_rate = 97.5% (CI [96.4%, 98.4%]) — reproducing
Level 1.1's near-100% finding almost exactly — while full functional
recovery (gap≥0) is only 32.2% (CI [30.4%, 34.5%]) and within-tolerance
recovery (gap≥−0.05) only 53.6% (CI [52.0%, 55.2%]); `mean_recovery_gap` is
−0.10 (CI excludes zero, negative) — capacity is systematically lower after
a shock. Completion rate, by contrast, is statistically unchanged (0.492 vs.
0.492) — a **mechanistic, not anomalous, explanation**: `Delegate.capacity`
includes an `experience_term` that necessarily restarts at 0 for every new
office-holder's own tenure regardless of predecessor quality, so capacity
structurally cannot fully recover within a short window even though
completion rate (agent-trait-driven) does. **Verdict: reappointment and
functional recovery are confirmed to be genuinely distinct quantities that
diverge substantially — Level 1.1's "10/10 = recovery" framing measured only
the first.**

## Work Package H — audited classifier vs. historical classifier

**Problem:** the historical `classify_delegation` labels a rule
`"accountable_delegation"` from any vote-succeeded recall regardless of
whether funds were recovered, and from any upheld appeal regardless of
whether it was a genuinely corrective outcome or an unjustified overturn of
a real sanction.

**Fix:** new `classify_delegation_audited`, a structural copy requiring a
realized true-positive detection and (funds-recovering recall OR genuinely
corrective appeal) — mirroring Work Package E's `effective_constraint`
standard, applied at the classifier level. `classify_delegation` itself is
byte-for-byte unchanged.

**Result** (15 matched seeds, 6 accountability conditions, `n_patches=6`,
`BOOTSTRAP_SEED=20265`, 90 classified rules per condition): downgrade rates
— `default_full`=0%, `audit_only`=undefined (recall/appeal both structurally
disabled, so `"accountable_delegation"` is unreachable by either classifier
by construction), `costless`=3.3%, `recall_only`=5.6%, `perfect_info`=1.4%,
`randomized_placebo`=20% (on a small denominator — 5/90 rules — reported
with that caveat explicit, not smoothed over). The ordering is broadly
consistent with lower detection accuracy producing a higher downgrade rate,
though the placebo estimate is weakly powered.

## Cross-cutting observations

- No work package's confirmatory result depended on the RNG-mode choice
  changing the qualitative conclusion — every causal contrast used
  `mechanism_substreams` throughout, consistent with Work Package A's own
  purpose.
- Every seed-clustered bootstrap in this milestone used a distinct
  `BOOTSTRAP_SEED` (20261–20265) purely for the resampling procedure itself,
  never affecting which underlying simulation seeds were run.
- Every undefined-denominator case across all eight work packages returns
  `None`, never `0.0` or `1.0` — verified by dedicated tests in every new
  test file this milestone added.
- Two genuinely new mechanistic bugs were found and fixed (Work Package A's
  `build_agents()` isolation gap and `policy_assortativity`'s cross-process
  nondeterminism) that were not part of the original six documented
  limitations — both are corrections to the *generative* or *observer*
  layer's own correctness, not phenotype-search additions, and are reported
  here for completeness.

## Recommendation for Level 1.2

Level 1.1's headline classifier-shift finding (accountability + discretion
together move a rule from `persistent_delegation` to `accountable_delegation`)
survives Work Package H's audit largely intact at this project's own default
parameters (`default_full`'s downgrade rate = 0%) — the specific historical
runs that produced that finding are not directly known to have relied on any
of the corrected edge cases, though this note does not re-run Level 1.1's
own exact historical seeds to confirm that directly (a possible follow-up,
not performed here). Level 1.2 should:

1. Use `rng_mode="mechanism_substreams"` for any new causal-isolation work,
   reserving `legacy_single_stream` only for exact Level 1.1 replication.
2. Use `classify_delegation_audited`, not `classify_delegation`, for any
   classification Level 1.2 treats as evidentiary — the historical
   classifier remains available for direct Level 1.1 comparison, but should
   not be the basis for new claims.
3. Distinguish accountability *activity* from *effective constraint*, and
   reappointment from *functional recovery*, in any reporting — both
   distinctions are now infrastructure (`observer/accountability_
   diagnostics.py`, the `recovery_gap` pattern in
   `experiments/level11b_functional_shock_recovery.py`), not one-off
   findings specific to this milestone.
4. Treat institutional memory's default calibration as intentionally
   conservative, not inert — if Level 1.2's phenotype search wants a
   parameter space where institutional memory's effect is more salient, the
   `max_dose` end of this milestone's grid is a documented, tested starting
   point.
5. Read `randomized_placebo`'s Work Package H downgrade-rate estimate as
   directional, not confirmed at high power — a dedicated higher-seed-count
   follow-up would be needed before treating 20% as a precise figure.

This note, together with `dev_mem/status_update.md`'s per-work-package
entries and `docs/config_reference.md`'s config-surface documentation, is
the complete record of what Level 1.1b changed, found, and did not find.
