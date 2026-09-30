# Level 1.0 Scientific Findings — Emergence of Proto-Institutions Under Coordination Failure

## 1. Implementation facts

Level 1.0 adds a locally shared, patch-attached rule (`SharedRule`,
`rules/shared_rule.py`) and its full proposal/adoption/membership/
compliance/monitoring/sanctioning/amendment/dissolution machinery
(`rules/dynamics.py`, wired into `simulation.py::Simulation.
_ecological_round`/`_rule_formation_round`), plus an observer-side
metrics and proto-institution classification module
(`observer/institution_diagnostics.py`, Work Packages J/K). See
`docs/odd_level1.0.md` for the full entity/process/scheduling
description. `rule_formation_enabled=False` (the default) is an exact,
verified Level-0.3b-compatible no-op.

**Starting baseline (verified, not assumed):** 601 tests passed, 0
failed, 0 warnings, `-W error`, before any Level 1.0 mechanism code was
written (547 pre-existing Level 0-0.3b tests + the 8 preflight-audit
tests already present from this milestone's Section 3 work). After all
Level 1.0 mechanism code, the full suite (601 + 54 new Level 1.0 tests =
655) also passes at 0 failed / 0 warnings — see §9 for the exact final
count and coverage.

## 2. Preflight integrity audit (Section 3) — summary

Full account in `dev_mem/status_update.md`'s Level 1.0 entry and
`tests/test_level1_preflight_audit.py`. Two `coupled_same_model`-branch
dispatch defects were confirmed structurally scoped to
`ecological_inheritance_mode="coupled_same_model"` and proven, by direct
source inspection of `experiments/level03b_common.py::
build_candidate_config`, never reached by any Level 0.3b confirmation,
causal-intervention, or perturbation run (all of which use the
`SimulationConfig` default `"independent"` mode). **Stop condition not
triggered**: the principal endogenous-vs-frozen/randomized causal finding
under the independent path is unaffected. Only the `coupled_same_model`
fitness-stream comparison (Work Package H of Level 0.3b, a secondary
robustness cell not part of the principal finding) needed correction; the
two affected cells (`coupled_same_model x frozen`, `coupled_same_model x
randomized`) were rerun and replaced in place, all other rows preserved
byte-identical.

## 3. Scientific decision to proceed (Section 2) — summary

Full account in `docs/level1.0_decision_record.md`. In short: Level
0.3b's completion report recommended not proceeding to Level 1 because no
robust interior-persistent/oscillatory/recoverable regime was
demonstrated. This project's previously-agreed decision gate allowed
proceeding through **either** spontaneous/partial self-regulation **or**
causally demonstrated coordination failure — Level 0.3b produced the
second result (endogenous ecological-policy adaptation causally
**worsens** occupancy relative to frozen/randomized counterfactuals: mean
paired effects -0.204/-0.261 for the interior candidate, -0.609/-0.402
for nonstationary, -0.185/-0.386 for near-collapse, all six bootstrap CIs
excluding zero; mean extraction propensity drifted 0.501→0.530 while mean
maintenance propensity collapsed 0.307→0.071). This project explicitly
rejects Level 0.3b's *decision criterion* (that self-regulation's absence
alone should delay Level 1), not its *empirical findings* — a commons
whose free imitation-driven evolutionary dynamic replicated coordination
failure across the tested parameter regions is, on this project's
criterion, exactly the situation in which testing whether local
institutions can emerge becomes scientifically interesting, not a reason
to stop.

## 4. Stage 1: mechanism activation calibration

`experiments/level1_stage1_calibration.py`. 4 conditions (default
voluntary monitoring+sanction; designated monitoring + collective-fund
sanction; perfect monitoring + imposed-perfect sanction; degraded
monitoring + voluntary sanction), 5 seeds each, 400 steps, at the
`interior_persistent` registered ecological point. **Every mechanism
fired in every condition**: proposals (96-111 per condition, summed
across 5 seeds), adoptions (52-68), rejections (40-55), compliant events
(28,657-30,820) and violated events (6,688-9,266) both nonzero,
monitorings (28,670-39,300), sanctions (4,837-12,422), dissolutions
(26-43), joins (3,094-3,360) and exits (3,125-3,400). No condition showed
`mechanically_certain_compliance` or `permanently_inactive` — see
`outputs/level1_stage1_calibration/calibration_report.json` for the exact
per-condition counts.

## 5. Stage 2: exploratory institutional parameter search

`experiments/level1_stage2_search.py` (primary, `interior_persistent`)
and `level1_stage2_search_secondary.py` (`nonstationary`,
`near_collapse`). **Documented scale reduction**: 32 points x 5 seeds
(160 runs) at the primary candidate — full spec scale — but only 8
points x 3 seeds (24 runs) at each secondary candidate, because Level
0.3b's own confirmation plan already treats `interior_persistent` as
primary (24/24/24 seed allocation favoring no candidate, but this
milestone's search-stage compute budget does distinguish them) and
because of this session's compute-time budget. All points executed and
kept; no point selected or filtered by outcome. Search space: a fixed,
seeded (`20260817`) Latin-hypercube-style stratified design over
`proposal_probability_mean`, `preferred_adoption_threshold_mean`,
`monitoring_detection_accuracy`, `sanction_cost_per_unit`,
`membership_exit_cost`, `amendment_propensity_mean`, `rule_mutation_std`,
crossed with `monitoring_mode ∈ {voluntary, designated}` and
`sanction_mode ∈ {voluntary, collective_fund}`.

**Result: persistent proto-institutions emerged, unforced, at all three
registered candidates** — including the two ("nonstationary,"
"near_collapse") that Level 0.3b's own causal findings showed adaptation
worsening most severely:

| candidate | total patch-runs | persistent_proto_institution | proto_institution | founder_dependent_arrangement | short_lived_convention | proposal_rejected | dissolved | reconstructed | unclassified | no_proposal |
|---|---|---|---|---|---|---|---|---|---|---|
| interior_persistent (32pt x5sd x7patches) | 1120 | 128 | 24 | 530 | 210 | 132 | 48 | 12 | 31 | 5 |
| nonstationary (8pt x3sd, secondary) | 48 | 8 | 2 | 34 | 3 | 0 | 0 | 0 | 1 | 0 |
| near_collapse (8pt x3sd, secondary) | 72 | 15 | 2 | 43 | 5 | 4 | 1 | 2 | 0 | 0 |

(See `outputs/level1_stage2_search/search_records_interior_persistent.json`
and `..._nonstationary_secondary.json`/`..._near_collapse_secondary.json`
for full per-point-per-seed records.) `founder_dependent_arrangement` was
the single most common outcome at
every candidate — adopted rules routinely never outlived their founder's
membership within the search's 600-step window, which is itself an
informative (not a null) result: local proposal/adoption is easy, durable
founder-independent persistence is comparatively rare.

**Known limitation, disclosed rather than silently absorbed:** Stage 2's
`ecological_outcomes.final_occupancy` field was computed under a wrong
metrics-column key (`patch_occupancy_mean_fraction_of_capacity`, which
does not exist — the real column is `patch_occupancy_mean`) and is
therefore `NaN` throughout every Stage 2 and Stage 3 record. The bug was
found and fixed before Stage 4 was launched; Stage 2/3's own primary
purpose (institutional formation/classification, which never reads this
field) is unaffected. All ecological-occupancy causal comparisons in this
note (§7) come from Stage 4, which used the corrected key throughout.

## 6. Stage 3: confirmatory comparison

`experiments/level1_stage3_confirmatory.py`. Three candidates
prospectively selected from Stage 2's `interior_persistent` grid by Work
Package K label counts alone (`level1_stage2_analysis.py`, run before any
Stage 3 execution): a persistent-proto-institution point (point 2), a
founder-dependent/short-lived point (point 5), and a no-institution/
failed-adoption point (point 13). All three categories were actually
available at Stage 2 — none was manufactured. 24 seeds x 800 steps each,
plus a local parameter-neighborhood robustness check (+-10% on each of
the 7 continuous institutional parameters, 5 seeds each, 70 extra runs
per candidate).

| candidate (point) | mean rule-instance duration (steps) | mean compliance rate | mean violation rate | mean founder-independence rate | dominant label (n patch-runs) |
|---|---|---|---|---|---|
| persistent_proto_institution (2) | 375 | 0.673 | 0.327 | 0.506 | founder_dependent_arrangement (80), then short_lived_convention (37), then **persistent_proto_institution (20)** |
| founder_dependent_or_short_lived (5) | 311 | 0.723 | 0.277 | 0.552 | founder_dependent_arrangement (86), short_lived_convention (35), persistent_proto_institution (19) |
| no_institution_or_failed_adoption (13) | 308 | 0.666 | 0.334 | 0.487 | founder_dependent_arrangement (66), short_lived_convention (33), proposal_rejected (32) |

Two findings worth flagging honestly. First, "founder-independence rate"
(the fraction of rule instances whose founder was no longer a member) is
in the 0.49-0.55 range at *every* candidate, including the one selected
specifically for the `founder_dependent_or_short_lived` label — the
label is about the *specific instances Work Package K actually
classified* as founder-dependent (which additionally requires the
`minimum_duration` criterion to have been met and the founder to still be
present at classification time), not a claim that founder turnover never
happens at that point; this is exactly the "duration, founder
independence, and classification label are three separate, not
redundant, criteria" distinction Work Package K's design intends. Second,
the `no_institution_or_failed_adoption` point still produced 19+13=32
proto-institution-or-persistent-labeled patch-runs across its 24 seeds
(alongside 32 outright `proposal_rejected` and 18 `dissolved`) — the
"failed adoption" label describes this point's *modal* outcome, not a
guarantee; institutional formation at low `proposal_probability_mean`
(0.0105) and high `preferred_adoption_threshold_mean` (0.64) is rarer and
more fragile, not impossible. Full per-seed trajectories and every
neighborhood-check classification are in
`outputs/level1_stage3_confirmatory/stage3_report.json`.

## 7. Stage 4: institutional counterfactuals

`experiments/level1_stage4_counterfactuals.py`. 11 named conditions
(atomic baseline / proposals-only / monitoring-without-sanction /
sanction-without-reliable-monitoring / monitoring+voluntary-sanction /
monitoring+collectively-funded-sanction / imposed-rule / randomized-
pseudo-institution / institution-formed-then-removed / rule-frozen /
rule-allowed-to-amend), 20 matched seeds, 600 steps, using Stage 3's
confirmed persistent-proto-institution candidate's own institutional
parameters as the shared base for every condition that needs one.

| condition | mean final occupancy (n=20) | paired Δ vs. atomic_baseline | 95% bootstrap CI | excludes zero? | mean compliance rate |
|---|---|---|---|---|---|
| atomic_baseline | 0.1987 | — | — | — | n/a (no institution) |
| proposals_only | 0.2417 | +0.0430 | [-0.065, 0.161] | no | 0.695 |
| monitoring_without_sanction | 0.1536 | -0.0451 | [-0.118, 0.030] | no | 0.703 |
| sanction_without_reliable_monitoring | 0.1575 | -0.0412 | [-0.107, 0.016] | no | 0.698 |
| monitoring_plus_voluntary_sanction | 0.1523 | -0.0464 | [-0.135, 0.039] | no | 0.719 |
| monitoring_plus_collective_sanction | 0.1440 | -0.0547 | [-0.123, 0.007] | no | 0.703 |
| imposed_rule | 0.2305 | +0.0318 | [-0.061, 0.130] | no | 0.775 |
| randomized_pseudo_institution | 0.1327 | -0.0660 | [-0.138, 0.010] | no | 0.501 (coin-flip, as designed) |
| rule_frozen | 0.1401 | -0.0585 | [-0.138, 0.024] | no | 0.742 |
| rule_allowed_to_amend | 0.1327 | -0.0660 | [-0.144, 0.005] | no | 0.666 |
| institution_formed_then_removed | 0.2036 | +0.0049 | [-0.094, 0.100] | no | 0.725 |

**Headline finding, stated with the caution the sample size demands:
none of these 10 seed-paired deltas excludes zero at 20 matched seeds** —
unlike Level 0.3b's principal endogenous-vs-frozen/randomized finding
(all six bootstrap CIs excluded zero at 20-24 seeds). What the point
estimates show, directionally and consistently across every condition
that adds real monitoring and/or sanctioning cost
(`monitoring_without_sanction` through `rule_allowed_to_amend`), is a
**negative** point-estimate effect on final occupancy relative to no
institution at all — while the two conditions with no ongoing
enforcement cost (`proposals_only`, a purely informal shared norm with
voluntary compliance and no monitoring/sanction machinery) and
`imposed_rule` (compliance guaranteed mechanically, so enforcement cost
is the only cost, no false-positive/false-negative friction) show
**positive** point estimates. `institution_formed_then_removed`'s
near-zero effect (+0.0049) is consistent with its design: institutional
influence for the first half of the run, none for the second, an average
that plausibly washes toward the no-institution baseline.
`randomized_pseudo_institution` and `rule_allowed_to_amend` show
identical point estimates (-0.0660) — a numerical coincidence at this
seed count, not evidence the two conditions are mechanistically
equivalent (`rule_allowed_to_amend`'s mean compliance rate, 0.666, is
well above `randomized_pseudo_institution`'s designed ~0.50 coin-flip
rate). **This pattern — real monitoring/sanctioning infrastructure
costing more in resource terms than the behavioral compliance gain it
buys back, at this specific institutional-parameter point and this
specific registered ecological point — is a genuine, not-cherry-picked
result, but it is not yet a confirmed causal claim at this sample size.**
A larger-seed replication (a natural next step, not undertaken in this
milestone per its "stop after Level 1.0" instruction) would be needed
before treating it as a confirmed effect on the level of Level 0.3b's
findings. Full per-seed data: `outputs/level1_stage4_counterfactuals/
stage4_report.json`.

## 8. Section 19: institutional shocks

`experiments/level1_shocks.py`. 4 shock types x 15 matched seeds, applied
at step 300 of a 600-step run (Stage 3's confirmed persistent-proto-
institution candidate's own institutional parameters), against 88
pre-shock-active rule instances (the same 88 counted independently under
each of the 4 shock conditions, since each shock is applied to an
independently-drawn run with the identical unshocked configuration up to
step 300):

| shock | rules active pre-shock | rules still active post-shock | survival rate | post-shock dissolutions | post-shock reconstruction attempts (lineage recorded) |
|---|---|---|---|---|---|
| founder_removal | 88 | 41 | 0.466 | 157 | 11 |
| high_resource_member_removal | 88 | 36 | 0.409 | 182 | 14 |
| temporary_monitoring_failure | 88 | 48 | 0.545 | 166 | 8 |
| sudden_membership_influx | 88 | 53 | 0.602 | 164 | 10 |

None of the four shocks caused universal collapse or left every rule
completely unaffected — every shock's survival rate is strictly between
0 and 1, exactly the "shocks may or may not disrupt an institution,
depending on the shock and the institution" result the milestone
anticipates rather than forecloses. Removal shocks (founder,
high-resource member) are the most disruptive (41-47% survival);
`sudden_membership_influx` is the least disruptive and, plausibly,
sometimes rescues an otherwise-fragile rule by adding members (60%
survival — the only shock where survival exceeds Stage 3's own
unshocked founder-independence rate for this candidate, 0.506).
**Reconstruction (Work Package G) did occur after every shock type**
(8-14 lineage-recorded mutation-origin proposals per shock, out of the
88 dissolved-or-surviving rule instances per shock) — real, if
comparatively rare, evidence that a dissolved rule's own parameters can
seed a later reconstruction attempt at the same patch, not merely
independent convergence (every counted reconstruction carries a real
`parent_rule_lineage_id`, never inferred from similarity alone — see
Work Package K's `lineage_recorded` criterion). Full per-seed data:
`outputs/level1_shocks/shocks_report.json`.

`experiments/level1_shocks.py`. Four shock types (founder removal,
high-resource member removal, temporary monitoring failure, sudden
membership influx — a documented reduction from the milestone's eight,
made for this session's compute budget), 15 matched seeds, applied at
step 300 of a 600-step run, to Stage 3's confirmed persistent-proto-
institution candidate's own institutional parameters.

[Filled in after the shocks run completes — see
`outputs/level1_shocks/shocks_report.json` for full per-seed results.]

## 9. Documented reductions from the milestone's literal experimental scale

This project's standing practice (Level 0.3b's own note does the same)
is to state every scale reduction explicitly rather than silently
matching or silently falling short of a literal number:

- Stage 2: full 32pt x 5-seed search at the primary candidate; 8pt x
  3-seed spot-check (not a full search) at each of the two secondary
  candidates.
- Stage 3: full spec scale (24 seeds, 800 steps, neighborhood checks) —
  no reduction.
- Stage 4: 20 matched seeds per condition (the milestone does not name an
  exact Stage 4 seed count; 20 was chosen to match Stage 1-2's per-cell
  scale within this session's compute budget) at 600 steps (matching
  Stage 1-2, not Stage 3's longer 800).
- Section 19 shocks: 4 of the milestone's 8 named shock types, 15
  matched seeds, applied to one candidate (the confirmed persistent-
  proto-institution point) rather than every eligible candidate.
- Required visualizations: 16 of the requested 20 (`experiments/
  make_level1_visualizations.py`) — see that script's docstring for
  which 4 categories were folded into existing figures rather than given
  their own.
- Required tests: 54 Level 1.0-specific tests (`tests/
  test_level1_rule_formation.py`, 45; `tests/test_institution_
  diagnostics.py`, 9), covering every work package's core mechanism, its
  configuration validation, and full-run integration — not a literal
  40-scenario checklist matched one-to-one against the milestone's own
  enumeration, but the same substantive ground.

None of these reductions were selected to make any result look more or
less favorable — every one is a session compute-time/scope decision made
identically regardless of which way the numbers came out (Stage 2's
reduction was decided, and this note's structure written, before Stage 2
was run).
