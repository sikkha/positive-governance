# ODD-style Model Description — Level 1.0 Addendum

This document extends `docs/odd_level0.1.md`, `docs/odd_level0.2_addendum.md`,
`docs/odd_level0.3_addendum.md`, and `docs/odd_level0.3b_addendum.md` (read
all four first) with exactly what Level 1.0 added: a locally shared,
patch-attached rule (a "proto-institution" substrate) that can be
proposed, adopted, joined, complied with or violated, monitored,
sanctioned, amended, dissolved, and — possibly — reconstructed. Nothing
in Level 0–0.3b's description is superseded; everything below is
additive, and at its default setting (`rule_formation_enabled=False`)
produces byte-for-byte identical dynamics to Level 0.3b (see
"Compatibility" below, and `tests/test_level1_rule_formation.py::
TestBackwardCompatibility`).

## 1. Purpose

Test whether a locally shared rule — proposed, voluntarily adopted,
imperfectly monitored, and imperfectly enforced by ordinary agents acting
on local information alone — can become socially reproduced and resist
the same evolutionary, extraction-favoring imitation dynamic that Level
0.3b showed causally worsens ecological occupancy relative to
frozen/randomized counterfactuals (see `docs/level1.0_decision_record.md`).
This is explicitly *not* an attempt to install a successful institution,
generate the dissertation's three governance trajectories, or introduce
any state/government/democracy/authoritarianism/rule-of-law/state-capacity
concept — see `agents/agent.py::FORBIDDEN_ATTRIBUTE_SUBSTRINGS`,
`rules/__init__.py`'s naming-rationale docstring, and the structural test
`tests/test_level1_rule_formation.py::TestBackwardCompatibility::
test_forbidden_attribute_substrings_not_reintroduced`. A successful,
unsuccessful, exploitative, unstable, costly, exclusionary, or
ecologically irrelevant proto-institution is an equally valid Level 1.0
result — see Work Package K's cautious classification vocabulary in §7.

## 2. New entities and state variables

**`RuleParameters`** (`rules/shared_rule.py`, frozen) — the minimal
content of a rule: `extraction_ceiling`, `maintenance_requirement`,
`monitoring_intensity`, `sanction_magnitude` (each in `[0, 1]`,
propensity-scale, comparable to `EcologicalPolicy.extraction_propensity`/
`maintenance_propensity`), `adoption_threshold`, `amendment_threshold`
(each in `(0, 1]`). Nothing biases these toward low-extraction/
high-maintenance values — they are drawn from a proposer's own traits or
mutated from an existing lineage, never optimized for future patch
survival.

**`SharedRule`** (`rules/shared_rule.py`) — one patch's active (or
dissolved-but-retained-for-lineage) rule: `rule_id`, `patch_id`,
`parameters`, `founding_step`, `founder_id`, `rule_lineage_id`, `active`,
`members`/`supporters`/`monitors` (frozensets), `fund` (collective-fund
sanctioning only), cumulative `compliance_count`/`violation_count`/
`observation_count`/`sanction_count`/`amendment_count`,
`consecutive_empty_steps`/`consecutive_fund_depleted_steps` (dissolution
bookkeeping), `dissolved`/`dissolution_step`/`dissolution_reason`,
`parent_rule_lineage_id` (set only when this rule's own proposal was a
mutation of a specific prior lineage — Work Package G reconstruction, not
mere numerical similarity). Attached to exactly one patch; at most one
active rule per patch (a documented Level 1.0 simplification — competing
proposals that lose the same-step tie-break or fail adoption remain fully
observable via `RuleRejectionEvent`, they just never become active).

**Agents** (`agents/agent.py::Agent`) gained a block of proposal/
membership/enforcement *traits* (never roles, titles, or governance
concepts): `proposal_probability`, `preferred_extraction_ceiling`/
`_maintenance_requirement`/`_monitoring_intensity`/`_sanction_magnitude`/
`_adoption_threshold`/`_amendment_threshold` (this agent's own preferred
rule content, used only as the content of any rule *it* proposes),
`willingness_to_join`, `willingness_to_monitor`, `sanction_preference`,
`violation_tolerance`, `amendment_propensity`, and `rule_member_of`
(`int | None` — pure bookkeeping the rule-formation round itself
maintains; never read by `decide_ecological_action` or any other Level
0-0.3b decision function). At `rule_formation_enabled=False` every one of
these stays at its inert dataclass default (`proposal_probability=0.0`
above all — the single fact that guarantees zero proposals ever fire).

**New event types** (`core/events.py`): `RuleProposalEvent`,
`RuleAdoptionEvent`, `RuleRejectionEvent`, `MembershipEvent`,
`ComplianceEvent` (intended vs. actual extraction/maintenance,
`complied`/`violated`, `enforcement_altered_action`),
`MonitoringEvent` (Level-0.1-style confusion-matrix outcome:
true/false positive/negative), `SanctionEvent` (distinct from Level 0's
bilateral `PunishmentEvent` — attached to a rule/lineage, cost may be
distributed/funded, tracks `false_sanction`), `RuleAmendmentEvent`,
`RuleDissolutionEvent`.

**New observer module** (`observer/institution_diagnostics.py`, Work
Packages J/K): seven separate metric categories (formation, persistence,
membership, compliance/enforcement, welfare, social effects — deliberately
never combined into one score) and `classify_rule`/`evaluate_proto_
institution_criteria`, the conservative Work Package K diagnostic. Every
label this module can return is drawn from a fixed, cautious vocabulary
(`institution_diagnostics.VALID_LABELS`) — `no_proposal`,
`proposal_rejected`, `short_lived_convention`,
`founder_dependent_arrangement`, `proto_institution`,
`persistent_proto_institution`, `dissolved`, `reconstructed`,
`unclassified` — never a "mature governance" term.

## 3. Process overview and scheduling

Once per step, after `_ecological_round` has computed and applied every
agent's realized extraction/maintenance (Work Package I — see §5) and
logged that step's `ComplianceEvent`s:

1. **Monitoring** (`rules/dynamics.py::monitoring_round`) — every active
   rule's members are observed (or not, depending on `monitoring_mode`)
   against this step's already-realized compliance ground truth.
2. **Sanctioning** (`sanction_round`) — every monitoring-detected
   violation (true or false positive) may be sanctioned, depending on
   `sanction_mode`.
3. **Proposal and adoption** (`proposal_and_adoption_round`) — patches
   with no active rule and no pending proposal may see a new proposal
   open; patches with a pending proposal accumulate support and
   resolve (adopt/reject) once the threshold is met or the proposal
   window (`proposal_window_steps`) expires.
4. **Membership** (`membership_round`) — eligible non-members may join;
   members may voluntarily exit (paying `membership_exit_cost`).
5. **Amendment** (`amendment_round`) — an existing member may propose a
   single-field parameter change, resolved by the same local support
   process as adoption; a rejected amendment below
   `rule_dissolution_support_floor` can itself trigger dissolution.
6. **Dissolution** (`dissolution_round`) — membership-floor,
   inactivity-duration, and (`collective_fund` mode only) fund-depletion
   triggers are checked; a dissolved rule's parameters are retained (not
   discarded) as this patch's `_last_dissolved_rule_by_patch` entry, the
   sole source Work Package G reconstruction may later mutate from.

All of Stage 0-2 above are skipped entirely (a strict no-op) whenever
`rule_formation_enabled=False`. Steps 3-6 are additionally skipped when
`institution_imposed_mode=True` (Stage-4 condition 7's mechanical
benchmark installs its rule once, at construction, and never proposes,
amends, or dissolves it through the ordinary mechanism).

## 4. Compliance decision (Work Package D) and its place in `_ecological_round`

Every rule member's compliance is decided *inside* `_ecological_round`,
immediately after that agent's ordinary (unconstrained) extraction/
maintenance request is computed from its own `ecological_policy` — using
only this agent's own traits, its own policy's request, and its own
rule's parameters (never a global quantity). The heuristic
(`rules/dynamics.py::decide_rule_compliance`) is a documented, bounded,
noisy logistic comparison of "temptation" (how much the rule would have
had to constrain this agent's own unconstrained request) against the
agent's `violation_tolerance` trait and the rule's own stated deterrence
(`monitoring_intensity * sanction_magnitude`) — not a solved expected-
utility optimum (the milestone explicitly permits this). A complier's
request is then capped/floored by `apply_rule_compliance` at the rule's
`extraction_ceiling`/`maintenance_requirement` (converted to resource
units by the same `ecological_harvest_unit`/`ecological_maintenance_unit`
constants every other agent's request uses); a violator's request is
untouched. `enforcement_altered_action` distinguishes "the rule actually
changed this step's request" from "this agent already satisfied the rule
without needing to be constrained." The stored `ecological_policy` field
itself is never read or written by any of this (Work Package I — an
institution may influence the *actual* action, never silently overwrite
the ecological genotype).

**Stage-4 condition 8 exception (randomized pseudo-institution):** when
`randomized_pseudo_institution_mode=True`, the "complied" label is an
unconditional coin flip (ignoring the rule's actual content and the
agent's traits) used only for downstream monitoring/sanction bookkeeping
— the request itself is *never* capped/floored in this mode, deliberately
severing the rule-content-to-behavior link while still matching
institutional activity/cost to a real rule.

## 5. Monitoring (Work Package E)

`monitoring_mode ∈ {"none", "voluntary", "designated", "perfect"}`
(`VALID_MONITORING_MODES`, `core/config.py`). Under `"voluntary"`, each
rule member becomes a candidate monitor for a given target with
probability `willingness_to_monitor`; one volunteer is drawn per target
and pays `monitoring_cost`. Under `"designated"`, a rule's own `monitors`
set (or, absent one, its full membership) supplies the observer. Under
`"perfect"`, `monitor=None`, `detection_accuracy=1.0`,
`false_positive_rate=0.0`, no cost — a diagnostic control, not a claim
about realistic monitoring. Every observation reuses Level 0.1's
confusion-matrix discipline: `true_positive`/`false_positive`/
`true_negative`/`false_negative`, from `MonitoringEvent.outcome`.

## 6. Collective sanctioning (Work Package F)

`sanction_mode ∈ {"none", "voluntary", "collective_fund",
"imposed_perfect"}` (`VALID_SANCTION_MODES`). Under `"voluntary"`, a
bystander member volunteers with probability `sanction_preference` and
pays `sanction_cost_per_unit * sanction_magnitude`. Under
`"collective_fund"`, the cost is drawn from the rule's own `fund`
(capitalized by diverting `institutional_fund_contribution_rate` of each
member's realized maintenance investment away from the patch and into the
fund, inside `_ecological_round`) — a sanction is silently skipped, not
forced, when the fund is insufficient. Under `"imposed_perfect"`, every
detected violation is sanctioned mechanically at zero cost
(`sanctioner=None`). Every sanction removes
`min(sanction_magnitude * sanction_penalty_unit, target.resources)` from
the target (never driving resources negative) and is logged with
`false_sanction=True` whenever the underlying `MonitoringEvent.true_
compliance` was actually `True` (a detected false positive that was then
sanctioned). Stronger sanctions are not assumed better anywhere in this
module.

## 7. Proto-institution criteria (Work Package K)

`observer/institution_diagnostics.py::evaluate_proto_institution_criteria`
requires **all** of: collective recognition (>1 member), behavioral
relevance (at least one `enforcement_altered_action=True` event),
minimum-duration persistence (`>= DEFAULT_MIN_DURATION_STEPS`, 30 by
default), founder independence (the founder is no longer a member, and
the rule outlived that departure), social reproduction *recorded* (at
least one non-founding `join` event, or a reconstruction whose proposal
carries a real `parent_rule_lineage_id`), lineage recorded (never claimed
from similarity alone), violation possibility remaining (violations were
actually observed — the mechanism never mechanically disallows them),
and nontrivial cost (monitoring/sanction/exit cost actually paid at least
once). `classify_rule` applies these, plus duration/founder-dependence/
reconstruction checks, to produce exactly one label from the fixed,
cautious vocabulary in §2 — never inferred from ecological occupancy
alone.

## 8. Stochasticity

Every new RNG draw (proposal Bernoulli, support-accumulation Bernoulli,
compliance logistic draw, monitoring detection/false-positive draw,
sanction-volunteer draw, amendment-support draw, and every trait draw in
`build_agents`) consumes `Simulation.rng`, the single run-level generator
— no new independent generator is introduced. At `rule_formation_enabled
=False`, zero of these draws occur (verified directly by
`tests/test_level1_rule_formation.py::TestBackwardCompatibility::
test_disabled_run_is_bit_identical_to_pre_level1_baseline_shape`).

## 9. Initialization

Every Level 1.0 agent trait is drawn once, in `build_agents`, from its own
configured mean/std (mirroring every other trait's initialization
pattern; see `core/config.py`'s `preferred_*_mean/_std`,
`willingness_to_*_mean/_std`, etc.), only when `rule_formation_enabled=
True`. No patch starts with an active rule unless
`institution_imposed_mode=True` (Stage-4 condition 7's mechanical
benchmark, which installs one rule per eligible patch directly at
construction, bypassing proposal/adoption).

## 10. Observation

`observer/institution_diagnostics.py` is a pure, read-only, post-hoc
layer over the `EventLog` and the final/dissolved `SharedRule` instances
— nothing it computes is ever fed back into any generative-layer decision.
Its labels are never attached to an `Agent` or `SharedRule` field; they
exist only as the return value of `classify_rule`, consumed by experiment/
analysis scripts, exactly like every other observer-layer classification
in this project (`observer/regulation_diagnostics.py::classify_regime`
being the closest Level 0.3b precedent).

## 11. Compatibility

`rule_formation_enabled=False` (the `SimulationConfig()` default) is an
exact, verified no-op: zero extra RNG draws, zero new event types
populated, zero change to any existing metric, `rule_registry == {}`,
`agent.rule_member_of is None` for every agent throughout the run — see
`tests/test_level1_rule_formation.py::TestBackwardCompatibility`.

## 12. Experiments (Level 1.0)

Stage 1 (mechanism activation calibration), Stage 2 (exploratory
institutional-parameter search at the Level 0.3b registered candidate
ecological points), Stage 3 (confirmatory comparison of three
prospectively selected candidates), Stage 4 (11 named institutional
counterfactuals, matched seeds), and §19 institutional shocks — see
`docs/level1.0_scientific_note.md` for the full design, exact scale used
(including every documented reduction from the milestone's literal
numbers), and results.

## 13. Limitations

At most one active rule per patch (competing proposals are observable but
never simultaneously active — a documented Level 1.0 simplification, not
a claim that multi-rule competition is uninteresting). The compliance
decision (§4) is a documented heuristic, not a solved expected-utility
optimum. Reconstruction (Work Package G) is gated by a single agent trait
(`amendment_propensity`) reused as a reconstruction-attempt probability,
rather than a dedicated trait — a scope simplification disclosed here
rather than silently assumed. Work Package K classification scopes to a
single rule *instance*; `institution_diagnostics.lineage_chain` is
provided for stitching instances of the same lineage together but is not
yet wired into every Stage 3/4 report. Institutional fund contribution
(Work Package F, `collective_fund` mode) diverts maintenance investment
at the moment `_ecological_round` builds the patch's maintenance request,
not from a separately-modeled "institutional taxation" decision layer.
