# ODD-style Model Description — Level 1.1 Addendum

This document extends `docs/odd_level1.0.md` (read it first) with exactly
what Level 1.1 added: endogenous delegation, administrative capacity,
delegate discretion/appropriation, accountability/constraint, opt-in
collective contributions, and minimal interpatch coordination. Nothing in
Level 0–1.0's description is superseded; everything below is additive,
and at every Level 1.1 flag left at its default (`delegation_enabled`,
`interpatch_coordination_enabled` both `False`, `contribution_mode`
`"none"`) produces byte-for-byte identical dynamics to
`level1_rule_formation_default` (verified on 20 seeds, see
`docs/level1.1_scientific_note.md` §2 and
`tests/test_level11_compatibility.py::TestExactLevel10Compatibility`).

## 1. Purpose

Test whether an already-adopted local rule (Level 1.0) can go further:
delegate some of its own enforcement/record-keeping/coordination work to
a member rather than every member doing it directly, whether that
delegate's administrative capacity is something that must be built up
from realized performance (never granted as a static trait), whether the
delegate's own discretion over collective resources creates a genuine
opportunity for appropriation, whether members can detect and constrain
that discretion (audit, appeal, recall), whether members will fund
administration through opt-in contributions, and whether two patches'
own rules can coordinate with each other at all. This is explicitly
*not* an attempt to reproduce the dissertation's three governance
trajectories, install a successful administrative state, or search for
a "recurrent institutional phenotype" — see
`core/config.py`'s `FORBIDDEN_LEVEL11_TERMS` and the structural guard in
`tests/test_level11_compatibility.py::TestStructuralTerminologyGuard`.
Delegation never occurring, a delegate never acquiring capacity,
discretion never being exercised, accountability never catching
anything, contributions never being paid, and coordination links never
forming are all equally valid Level 1.1 results — see Work Package K's
cautious 12-label classification vocabulary in §7.

## 2. New entities and state variables

**`Delegate`** (`rules/delegation.py`) — one rule's currently-active (or
removed, kept for history) delegate: `delegate_id`, `rule_id`,
`rule_lineage_id`, `patch_id`, `agent_id`, `tasks` (a subset of
`{"monitoring", "resource_accounting", "sanction_execution",
"maintenance_coordination", "interpatch_communication"}`),
`appointment_method`, `start_step`, `candidate_set`,
`selector_population`, `support_fraction`, `predecessor_delegate_id`,
`active`, `removal_step`, `removal_reason`. Realized-performance state
(never a copy of any `Agent` trait): `task_attempts`/`task_successes`
(per task), `record_quality` (rises on success, decays on failure or
inactivity), `appropriated_total`, `misconduct_count`,
`effort_withheld_count`, `audits_survived`/`audits_failed`,
`appeals_upheld_against`/`appeals_rejected_against`,
`misconduct_this_step`. The `capacity` property
(`0.5*completion_rate + 0.3*record_quality + 0.2*experience_term`) is
computed *only* from this realized history — the delegate's initial
`administrative_reliability` trait never appears in it directly (it only
shapes the per-task success draw itself, alongside capacity).

**`CoordinationLink`** (`rules/coordination.py`) — a bilateral link
between two patches' own active rules: `link_id`, `patch_id_a/b`,
`rule_id_a/b`, `kind` (one of `information_exchange`,
`ecological_restraint`, `shared_monitoring`, `mutual_assistance`,
`shared_records`), `proposed_step`, `accepted_step`, `active`,
`dissolved`, `dissolution_step/reason`, `total_resource_transferred`,
`total_cost`, `n_activity_steps`.

**`SharedRule.institutional_memory`** (new field, `[0, 1]`, default
`0.0`) — a rule-level retained-knowledge scalar, distinct from any one
delegate's own `record_quality`. Written only at the moment of delegate
replacement (`rules/delegation.py::nomination_and_selection_round`):
`institutional_memory = clip(outgoing_delegate.record_quality *
config.institutional_memory_retention, 0, 1)`, then a fraction of *that*
(`institutional_memory_transfer_to_new_delegate`) is granted to the
incoming delegate as a starting `record_quality` bonus. Never written
anywhere else; stays at `0.0` for a rule's first-ever delegate (nothing
to inherit yet).

**`Agent`** (11 new fields, `agents/agent.py`, all inert-by-default):
`nomination_probability` (0.0), `perceived_competence` (0.5),
`social_trust` (0.5), `administrative_reliability` (0.6),
`appropriation_propensity` (0.1), `effort_reduction_propensity` (0.1),
`audit_diligence` (0.2), `contribution_willingness` (0.5),
`preferred_contribution_amount` (0.1), `interpatch_proposal_probability`
(0.0), `interpatch_acceptance_propensity` (0.5).

**New `EventLog` types (16):** `DelegateNominationEvent`,
`DelegateAppointmentEvent`, `DelegateRemovalEvent`,
`TaskPerformanceEvent`, `AppropriationEvent`, `AuditEvent`, `RecallEvent`,
`AppealEvent`, `ContributionEvent`, `AdministrativeSpendingEvent`,
`FundDissolutionEvent`, `CoordinationProposalEvent`,
`CoordinationLinkEvent`, `CoordinationActivityEvent`,
`CoordinationDissolutionEvent`.

## 3. Process overview and scheduling

`Simulation._run_one_step` now calls, in order, after
`_rule_formation_round` (Level 1.0's own round, unchanged):
`_delegation_round(step)` — `rule_delegation.accountability_round` (audit
existing misconduct/recall/appeals against *last* step's realized
behavior), then `rule_delegation.nomination_and_selection_round`
(nomination accumulation, and selection resolution once the nomination
window expires), then `rule_delegation.task_performance_round` (this
step's task attempts, capacity update, discretion draws) — followed by
`_coordination_round(step)` (`rule_coordination.coordination_round`:
proposal, bilateral acceptance, activity, dissolution). Rule dissolution
(inside `_rule_formation_round`) additionally now triggers
`rule_delegation.handle_rule_dissolution_removals` and
`rule_contributions.resolve_dissolution_fund` for any lineage that
dissolved that step, and `_rule_formation_round` ends with a
`rule_contributions.contribution_round` call (period-gated, a no-op
unless `contribution_mode != "none"`). Every one of these calls is a
strict no-op (consumes zero RNG draws) when its governing flag is at its
default — verified bit-for-bit on 20 seeds (§2 above).

## 4. Delegation: nomination, evaluation, selection, removal (Work
   Package D)

At most one active delegate per rule (documented simplification, same
discipline as Level 1.0's "at most one active rule per patch"). Each
eligible member nominates with probability `nomination_probability`
(coin-flip self- vs. random-fellow-member nomination). Once the
nomination window (`delegate_nomination_window_steps`) expires with at
least one candidate, every eligible member scores every candidate via
`_candidate_evaluation_score` — a weighted sum of prior-capacity-as-
reliability (neutral 0.5 when the candidate has never held office),
`perceived_competence`, `social_trust`, relative `resources`, and a
(always non-positive) cost-aversion term, passed through a noisy
sigmoid comparison (the project's "documented heuristic, not solved
expected-utility optimum" register — see `agents/adaptation.py`'s own
discipline). Four selection procedures
(`delegate_selection_procedure`): `lottery` (uniform draw among
candidates, appoints unconditionally), `plurality_support` (most-
supported candidate, only if support > 0), `voluntary_approval`/
`threshold_acceptance` (only candidates clearing
`delegate_selection_support_threshold` are eligible; appointing nobody
is a legitimate, observed outcome — Stage 1 confirms `unclassified`/no-
selection outcomes occur). Removal happens via accountability (recall,
§6) or rule dissolution (`handle_rule_dissolution_removals`); the
outgoing delegate's full record is preserved in
`Simulation.delegate_history`, never overwritten silently.

## 5. Administrative capacity (Work Package E)

`Delegate.capacity` starts at `0.0` for every fresh delegate (task
completion rate and record_quality both start uninformative). It rises
with realized successes, decays under inactivity
(`delegation_inactivity_decay_rate`, applied when a rule has zero
members some step) or repeated failure. `institutional_memory` (§2)
provides the only channel by which a successor can start with anything
better than a blank record.

## 6. Discretion, appropriation, and accountability (Work Packages F/G)

A strict no-op unless `discretion_enabled`. Each task attempt, the
delegate's agent-level `appropriation_propensity`/
`effort_reduction_propensity` drive independent per-step draws
(`appropriation_opportunity_scale`/`effort_reduction_opportunity_scale`)
for fund appropriation (`appropriation_fraction_of_fund` of the rule's
current fund, resource-accounted exactly: fund decrease == delegate
resource increase) and effort withholding (task recorded as `"withheld"`,
never attempted). Misconduct is possible but never mechanically certain
(Stage 1/tests confirm both outcomes reachable across seeds at
`appropriation_propensity=0.5`).

Accountability (`accountability_enabled`) adds, once per step per
delegate: member audits (`audit_diligence * audit_probability_scale`
draw per non-delegate member; an *imperfect* confusion-matrix outcome
via `audit_accuracy` — never reads the hidden ground-truth misconduct
flag directly), a recall vote triggered by any audit finding (support
driven only by the delegate's own Laplace-smoothed audit-history finding
rate plus each voter's `1 - social_trust`, never the hidden ground truth
— the delegate itself is excluded from its own recall electorate), and
appeals against this step's fresh `SanctionEvent`s (Level 1.0's own
mechanism, reused rather than duplicated).

## 7. Collective contributions and administrative spending (Work
   Package H)

A strict no-op while `contribution_mode == "none"` (default). Four
active modes (`equal`/`voluntary`/`proportional`/`negotiated`),
assessed every `contribution_period_steps`. Compliance is driven by
`contribution_willingness`, deliberately distinct from
`violation_tolerance` (ecological-rule compliance). All administrative
spending (`pay_administrative_cost`) prefers the rule's own
`fund` and falls back to the payer's personal resources only when the
fund cannot cover it — the same `fund` ledger Level 1.0's own
`sanction_mode="collective_fund"` already used, kept as the single
account both feed. Dissolution disposes of any remaining fund exactly
once (`distributed_to_members`/`lost`/`retained_for_reconstruction`),
logged via `FundDissolutionEvent`.

## 8. Interpatch coordination (Work Package I)

A strict no-op unless `interpatch_coordination_enabled`. A patch's rule
may propose a link to any other patch with an active rule ("neighboring
patch" — no adjacency topology exists elsewhere in this project, a
documented scope simplification, not a claim a richer topology would be
uninteresting); the recipient accepts independently, driven by its own
members' mean `interpatch_acceptance_propensity`. An active link costs
both sides `coordination_cost_per_step` per step (never driving a fund
negative), has a chance each step of an "activity" event
(`coordination_activity_probability`) — for `mutual_assistance` links,
this transfers resources from the less-occupied side's fund toward
whichever side is below `coordination_assistance_occupancy_threshold` —
and a chance of voluntary dissolution
(`coordination_dissolution_probability`), or forced dissolution if
either side's rule stops being active. Deliberately independent of
Work Packages D-G: `level11_coordination_only` demonstrates a link
forming and operating with no delegate ever appointed at either patch.

## 9. Work Package K's classification vocabulary

`observer/delegation_diagnostics.py::classify_delegation` returns
exactly one of: `no_delegation`, `attempted_delegation`,
`delegate_selected`, `unstable_delegation`, `persistent_delegation`,
`accountable_delegation`, `weakly_constrained_delegation`,
`administratively_inactive`, `administratively_functional`,
`fragmented_coordination`, `interpatch_coordination`, `unclassified`.
Every label names a mechanism-validation state — never a governance
type, never combined with any other Work Package J dimension into one
score. `unclassified` is a legitimate, expected outcome (observed in
Stage 3, e.g. `lottery|discretion=True|accountability=False`: ~11-17%
of rules).

## 10. Stochasticity

Every new draw in this addendum (nomination, self- vs. other-nomination
tie-break, candidate support sigmoid comparison, lottery selection,
task success, appropriation/effort-withholding opportunity, audit
diligence/accuracy, recall support sigmoid, appeal probability/accuracy,
contribution compliance, coordination proposal/acceptance/activity/
dissolution) consumes the single shared `Simulation.rng` stream
(`core/rng.py::make_rng`) — no new independent generator anywhere in
this addendum, verified by the exact bit-for-bit compatibility check
(§0/§2).

## 11. Initialization

The 11 new `Agent` traits (§2) are drawn once at `build_agents` time,
gated on `config.delegation_enabled`/`config.contribution_mode !=
"none"`/`config.interpatch_coordination_enabled` respectively (each
block a strict no-op, consuming zero extra draws, when its own gate is
off) — mirrors Level 1.0's own trait-drawing block structure exactly.

## 12. Observation

Purely additive, read-only, post-hoc — see
`observer/delegation_diagnostics.py` (Work Packages J/K),
`observer/replication_units.py` (Work Package A), and the Work Package
B/C additions to `observer/institution_diagnostics.py`. Nothing here is
ever read by any decision function in `simulation.py`/`agents/`/
`rules/` — verified by an AST-based import-direction check
(`tests/test_level11_compatibility.py::
TestGenerativeObserverSeparation`).

## 13. Compatibility

Every Level 1.1 mechanism defaults to its Level-1.0-compatible no-op;
`SimulationConfig.level10_compat()` is named explicitly for this
addendum's own use and is byte-for-byte identical, under the hood, to
`level1_rule_formation_default()` — confirmed on 20 seeds (§0). Ten
named presets cover every combination this milestone's experiments use
(`level10_compat`, `level11_delegation_only`, `level11_capacity_only`,
`level11_accountability_only`, `level11_coordination_only`,
`level11_complete`, `level11_no_memory`, `level11_no_accountability`,
`level11_no_admin_cost`, `level11_no_interpatch_coordination`).

## 14. Experiments (Level 1.1)

See `docs/level1.1_scientific_note.md` for the full six-stage program
(mechanism activation, compatibility + ablations, exploratory mechanism-
space search, confirmatory replication, causal decomposition,
institutional shocks) and its results.

## 15. Limitations

Institutional memory is a single rule-level scalar refreshed at each
replacement, not an accumulating multi-delegate archive. Task
assignment is fixed at appointment (no re-assignment mid-tenure).
Interpatch "neighboring" has no real spatial topology. Contribution
modes do not interact with each other within a single run. Recall
support and audit draws use the same noisy-sigmoid/confusion-matrix
heuristic register as Level 1.0's own monitoring/sanction decisions —
documented as a heuristic, not a solved expected-utility optimum,
throughout. All Work Package A-C observer repairs (unit-of-analysis,
welfare accounting, persistence/reconstruction eligibility) are
descriptive tools available to any future milestone, not applied
retroactively to re-analyze already-published Level 1.0 figures.
