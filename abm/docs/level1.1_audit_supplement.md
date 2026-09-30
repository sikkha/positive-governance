# Level 1.1 Audit Supplement — Work Packages A, B, C

This supplement documents the required pre-mechanism audit of Level
1.0's own observer/accounting layer, performed before any Level 1.1
generative mechanism was implemented, per this milestone's own
preflight requirement.

## Work Package A: unit-of-analysis and denominator audit

**Finding:** Level 1.0's own experiment scripts and this project's
earlier milestones frequently report patch-run-level values as if each
patch within a seed were an independent replicate. It is not: patches
within the same seed share one realized RNG trajectory's
population-level draws (imitation events, network structure, shocks),
so treating them as independent understates uncertainty.

**Demonstration (`tests/test_level11_observer_diagnostics.py::
TestReplicationUnits::test_seed_clustered_bootstrap_respects_seed_as_the_unit`):**
constructed synthetic data with 5 seeds, each contributing 20 perfectly
correlated patch-runs (100 total values pooled). A naive pooled
bootstrap over all 100 values produces a measurably *narrower* 95% CI
than a seed-clustered bootstrap over the 5 true seed-level means — the
exact miscalibration this work package exists to demonstrate and
correct.

**Delivered:** `observer/replication_units.py` — `ReplicationUnits` /
`count_denominators` (one denominator per nesting level, always exported
alongside a rate per this milestone's own requirement),
`naive_pooled_bootstrap_ci` (kept only as the incorrect comparison),
`seed_clustered_bootstrap_ci` (the corrected default — seed is the unit
resampled), `hierarchical_bootstrap_ci` (parameter point → seed →
patch, three levels). Used directly in Stage 4 and Stage 5's own
confirmatory-grade uncertainty intervals (`docs/level1.1_scientific_note.md`
§6-7). Retroactive re-analysis of already-published Level 1.0 figures
using these corrected intervals was judged out of this session's scope
(see Limitations, `docs/odd_level1.1.md` §15) — the tool is delivered and
tested, not yet applied backward.

## Work Package B: welfare accounting repair

**Finding:** Level 1.0's `welfare_metrics` reports member/nonmember
resource means without an explicit denominator-validity flag, and treats
any member/nonmember contrast as if self-evidently interesting without
ever labeling it as non-causal (membership is self-selected, not
randomly assigned).

**Delivered:** `observer/institution_diagnostics.py::welfare_accounting`
— full export: member/nonmember counts, numerators, explicit
`member_denominator_valid`/`nonmember_denominator_valid` booleans, a
population-weighted overall mean, a within-patch contrast (when a
`patch_system` is supplied), and — critically — every contrast is
labeled `is_causal_estimate: False` with an explicit note directing the
reader to a matched-seed counterfactual design for anything stronger.
An atomic baseline (`rules=[]`) correctly reports `member_count=0` and
NaN member-side means, never a misleading `0.0`
(`tests/test_level11_observer_diagnostics.py::TestWelfareAccounting::
test_atomic_baseline_has_no_members_and_nan_means`).

**Negative-resource handling, confirmed a pre-existing characteristic,
not a Level 1.1 defect:** a smoke run of `level11_complete` showed
`min(agent.resources) ≈ -57.4`. Investigated by running
`level1_rule_formation_default` (Level 1.0 code only,
min ≈ -119.2) and `level03_patches_default` (Level 0.3, no Level 1.x
code at all, min ≈ -522.1) — both also produce negative resources,
confirming this traces to `_ecological_round`'s maintenance-investment
accounting (uncapped by current resources), a Level 0.3/1.0
characteristic entirely unrelated to this milestone. Work Package B
explicitly anticipates this scenario as a required test case
(`tests/test_level11_observer_diagnostics.py::TestWelfareAccounting::
test_negative_resources_do_not_break_accounting`); `welfare_accounting`
handles it correctly without clamping or raising, and every new Level
1.1 resource-accounting function (`pay_administrative_cost`,
appropriation, contribution payment) already guards with
`max(0.0, ...)` so a negative-resource agent's admin/appropriation/
contribution interactions never manufacture resources.

## Work Package C: persistence and reconstruction eligibility

**Finding:** Level 1.0's own `persistence_metrics` does not filter by a
minimum-duration/lineage-valid eligibility criterion before computing
survival rates or reconstruction-related counts, risking an unfiltered
denominator (a rule that existed for one step counted the same as one
that existed for 300).

**Delivered:** `observer/institution_diagnostics.py::eligible_active_rules`
(founding_step ≤ event_step, not-yet-dissolved-as-of-event_step, valid
lineage id, met minimum duration) and `survival_after_event` (survival
rate over that eligible set only, never an unfiltered rule count) for
Work Package C requirement 2; `eligible_dissolutions` (dissolved within a
window, met minimum duration at dissolution, valid lineage) and
`reconstruction_metrics` (attempt/adoption/persistence, each requiring a
real `parent_rule_lineage_id` — never inferred from parameter similarity
alone) for requirements 3-5; `lineage_chain` for tracing a full lineage
across dissolution/reconstruction pairs. All empty-denominator cases
return NaN, never a misleading `0.0`
(`tests/test_level11_observer_diagnostics.py::
TestPersistenceAndReconstructionEligibility::
test_reconstruction_metrics_empty_eligible_set_is_nan_not_zero`).

## Summary

All three work packages were audited before any Level 1.1 generative
mechanism was written, delivered as tested, additive observer-layer
functions (46 dedicated tests,
`tests/test_level11_observer_diagnostics.py`), and used directly by
Stage 4/5's own confirmatory-grade statistics. No Level 1.0 generative
code was modified; the one genuine defect found during this audit phase
(negative resources) was confirmed pre-existing and out of scope to
"fix," consistent with this milestone's instruction to preserve exact
Level 0.x/1.0 compatibility.
