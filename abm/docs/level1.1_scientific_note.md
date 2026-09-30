# Level 1.1 Scientific Findings — Delegation, Administrative Capacity, and Institutional Scale

## 1. Implementation facts

Delegation (Work Package D), administrative capacity (E), discretion/
appropriation (F), accountability/constraint (G), collective
contributions (H), and minimal interpatch coordination (I) are all
implemented, generative-layer, structurally guarded against every
forbidden governance-type term, and byte-for-byte inert when disabled
(verified on 20 seeds, §2). Observer-side: Work Package A
(`observer/replication_units.py`, seed-clustered/hierarchical
bootstrap), B (welfare accounting repair), C (persistence/reconstruction
eligibility), J (nine separate institutional dimensions), K (a cautious,
duration-gated, 12-label mechanism-validation classifier). 144 new
tests, all passing; full suite 739 passed / 2 skipped / 5 failed (the
five pre-existing, disclosed `test_level03b_pipeline.py` artifact-gap
failures — see `dev_mem/status_update.md`'s session-7 entry — unchanged
by this milestone).

## 2. Preflight and compatibility — summary

Starting baseline: 594 passed / 2 skipped / 5 failed, a disclosed
environment/artifact-availability gap (three deep Level 0.2/0.3/0.3b
pipeline output directories missing from this session's mirrored
`outputs/`), not a code defect — see `dev_mem/status_update.md`.
`level10_compat` (every Level 1.1 flag at its no-op default) was
confirmed byte-for-byte identical to `level1_rule_formation_default`,
per-seed, across the full simulation `metrics` history, on 20 fresh
seeds (`outputs/level11_stage2_compatibility_ablations/stage2_report.json`
→ `compatibility_check.byte_for_byte_identical: true`,
`n_mismatches: 0`).

## 3. A production bug found and fixed during Work Package E's own
   verification

While preparing Stage 2's ablation set, the `level11_no_memory` vs.
`level11_complete` matched-seed contrast produced an exact `0.0` mean
effect on every one of four outcome variables across 10 seeds — an
implausibly clean null for a config field documented as feeding into
task-success probability. Direct inspection confirmed the cause:
`SharedRule.institutional_memory` was *read* at delegate-replacement
time (`rules/delegation.py`) but never *written* anywhere in the
codebase, so it stayed at its `0.0` default for the entire run
regardless of `institutional_memory_retention`, making Work Package E
requirement 7 ("a configurable fraction of the outgoing delegate's
realized record quality is absorbed") an unimplemented no-op. Fixed:
`rule.institutional_memory` is now set at the moment of replacement from
the outgoing delegate's own `record_quality`, scaled by
`institutional_memory_retention`. Verified causally wired end-to-end
with exaggerated parameters (`institutional_memory_retention=1.0`,
`institutional_memory_transfer_to_new_delegate=1.0` vs. `retention=0.0`):
the two runs diverge at step 280 on the same seed. At the *default*
parameters (`retention=0.3`, `transfer=0.5`), the mechanism is confirmed
present and functioning (`rule.institutional_memory` becomes non-zero
during a run — e.g. `0.0033` observed at one rule at the end of a 350-
step run) but its effect on the four Stage 2 outcome variables remains
too small to be detected at 10 matched seeds — reported as a genuine
near-null finding, not further chased (Stage 2/5's own seed budgets are
not designed to resolve effects this small; a dedicated, much larger-n
study would be needed, out of this session's scope). One test
(`tests/test_level11_delegation.py::
test_replacement_appends_predecessor_to_history_and_carries_memory`)
was updated to match the corrected mechanism rather than the pre-fix
placeholder behavior it had been asserting.

## 4. Stage 1: mechanism activation

5 conditions × 8 seeds, population 40, 3 patches, 350 steps
(`outputs/level11_stage1_activation/`). Every mechanism fired at least
once across seeds when its flag was enabled, and produced exactly zero
of its own defining events when disabled — every `expected_nonzero`/
`expected_zero` check in the stage's own report passed. Headline totals
for `level11_complete` (summed over 8 seeds): 1677 nominations, 898
appointments, **882 removals** (essentially matching appointments —
delegate tenure is short by default), 3484 task attempts, 368
appropriations, 5990 audits, 1535 recall votes (881 succeeded), 3221
appeals, 7393 contribution decisions, 72 coordination proposals (72
links formed).

**A genuine, unanticipated finding, reported honestly rather than
tuned away:** at this project's default parameters, accountability is
aggressive — audits are frequent and recall support clears the default
threshold often enough (881 of 1535 recall votes, 57%) that delegate
turnover is very high (882 removals against 898 appointments across 8
seeds × 350 steps — a mean tenure far short of a full run). This is not
a bug (the mechanism itself is doing exactly what it is specified to
do — imperfect audits, Laplace-smoothed recall support, no hidden-
information use) but a property of the *default calibration* of
`audit_probability_scale`/`recall_support_threshold`/`audit_accuracy`
against this project's other default agent traits. It is reported here
as a scientific finding about this configuration, not corrected by
adjusting defaults specifically to produce a more "stable-looking"
result.

## 5. Stage 2: compatibility + exploratory ablations

20 (compatibility) / 10 matched (ablations) seeds
(`outputs/level11_stage2_compatibility_ablations/`). Compatibility: see
§2. Ablations (`level11_complete` vs. one mechanism removed at a time,
mean effect, point estimate only — exploratory, not confirmatory):
`level11_no_memory` — effect indistinguishable from zero on all four
outcomes at this seed count (§3); `level11_no_accountability` — modestly
higher final total resources (+621) and administrative cost (+7.0, i.e.
removing accountability's own audit/appeal cost is more than offset by
other dynamics) but small/uncertain effects elsewhere;
`level11_no_admin_cost` — higher total appropriated resources (+17.2)
and lower administrative cost (-10.9, mechanically expected since task
costs are zeroed); `level11_no_interpatch_coordination` — small positive
effects across the board. **Important limitation, disclosed rather than
glossed over:** because every mechanism draws from the single shared RNG
stream, disabling a mechanism does not hold the rest of the run's random
draws constant — it shifts every subsequent draw's position in the
stream, so an ablation's "effect" reflects both the mechanism's own
structural absence *and* the resulting downstream RNG-stream shift, not
a clean single-factor manipulation. Stage 5 (§7) reports the same
family of contrasts with proper seed-clustered bootstrap uncertainty
intervals; this limitation applies there too and is the reason this
note treats even Stage 5's "confirmed" results as descriptive of *this
implementation's* matched-seed behavior, not as an isolated ceteris-
paribus causal estimate in the strict experimental-design sense.

## 6. Stage 3 (exploratory) → Stage 4 (confirmatory): selection
   procedure vs. discretion/accountability

Stage 3 crossed 4 selection procedures × discretion on/off ×
accountability on/off × 6 seeds
(`outputs/level11_stage3_search/stage3_report.json`), reporting only
Work Package K label-fraction distributions (never merged into a score,
never a governance-type claim). A pattern held across all four
procedures: with discretion and accountability both off, the label mix
is 83-94% `persistent_delegation`; with both on, it shifts to a mix
dominated by `accountable_delegation` (56-67%), never
`persistent_delegation`. Selection procedure itself made almost no
difference — the discretion+accountability combination is what drives
the shift.

Stage 4 re-ran this one contrast (`lottery` selection, procedure shown
not to matter) on 20 entirely fresh seeds with a seed-clustered
bootstrap 95% CI
(`outputs/level11_stage4_confirmatory/stage4_report.json`):
`accountable_delegation` fraction 0.65 [0.53, 0.75] with both mechanisms
active vs. 0.0 [0.0, 0.0] with both off; `persistent_delegation` fraction
0.0 [0.0, 0.0] active vs. 0.917 [0.85, 0.97] off. The two conditions'
CIs do not overlap in either direction — **confirmed** by this stage's
own criterion. Read narrowly: this says accountability's own presence
(catching and recalling/upholding-appeal-against misconduct) is what
moves a rule's classification from "long-lived, unchallenged" to
"long-lived, actively contested" in this implementation, at these
defaults — not a claim about which state is scientifically preferable
or about any real-world governance form.

## 7. Stage 5: causal decomposition

Four contrasts × 5 outcomes × 15 matched seeds, seed-clustered bootstrap
95% CIs (`outputs/level11_stage5_causal_decomposition/stage5_report.json`;
see the RNG-stream-shift caveat in §5, which applies equally here).
CIs excluding zero (i.e., this session's own bar for "detected" at this
seed count): discretion's removal *reduces* total appropriated resources
by 1.99 [1.42, 2.68] (mechanically expected — no discretion, no
appropriation opportunity, though the ablation was not literally zero
because `discretion_enabled=False` still leaves near-zero residual
noise-floor); removing admin cost *increases* total appropriated
resources by 15.10 [12.52, 17.78]; removing interpatch coordination
*increases* total appropriated resources by 4.10 [2.07, 6.37].
Accountability's own removal showed no outcome with a CI excluding
zero at this seed count (closest: total appropriated resources, point
estimate +0.30, CI [-0.03, 0.62] — directionally consistent with more
appropriation when unaccountable, but not confirmed here). No contrast
produced a CI excluding zero for `final_occupancy` or
`final_total_resources` at 15 seeds — ecological-level effects of these
mechanisms, if any, are smaller than this session's seed budget can
resolve.

## 8. Stage 6: institutional shocks

Two shock types × 10 seeds × 500 steps, shock at step 250
(`outputs/level11_stage6_shocks/stage6_report.json`), a documented
subset of a fuller shock catalog (matching the Level 1.0 precedent of
disclosing a similar reduction). `delegate_removal` (every active
delegate forcibly removed, independent of the recall mechanism) and
`appropriation_spike` (appropriation opportunity/fraction temporarily
maximized for 30 steps): **both shock types showed a 10/10 seed
reappointment rate** — a new delegate was appointed at least once after
the shock in every single seed tested. This is a real, if narrow,
finding: the delegation *arrangement* (not any specific delegate) is
robust to both tested shock types at this population/patch scale within
the observation window — it says nothing about whether the
*post-shock* delegate performs as well, is appropriated from again, or
whether a much larger/rarer shock would break the pattern.

## 9. Documented reductions from the milestone's literal scale

Every experimental stage above used 6-20 seeds per condition rather than
a publication-scale sweep (typically 50-200+), population 40 and 3
patches (vs. this project's own larger-scale Level 1.0 runs), and 350-500
steps. Stage 3's search covered 16 of a much larger possible mechanism-
space grid (selection procedure × discretion × accountability only, not
crossed with contribution mode or coordination). Stage 6 covered 2 of a
larger conceivable shock catalog. Visualizations: 12 of the requested
12-18 (see `docs/level1.1_completion_report.md`). All reductions are
disclosed here and in each experiment script's own docstring, matching
this project's own established convention (`experiments/level1_shocks.py`
disclosing 4 of 8 shock types; `experiments/make_level1_visualizations.py`
disclosing 16 of 20 figures).
