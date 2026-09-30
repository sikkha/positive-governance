# Level 1.0 Completion Report — Emergence of Proto-Institutions Under Coordination Failure

Milestone complete. Per explicit instruction: **stopping here. Level 1.1
is not begun regardless of this report's recommendation.**

## 1. What was implemented

`rules/shared_rule.py` (`RuleParameters`, `SharedRule`), `rules/dynamics.py`
(compliance decision, monitoring, sanctioning, proposal/adoption,
membership, amendment, dissolution), `observer/institution_diagnostics.py`
(Work Packages J/K), ~40 new `SimulationConfig` fields plus 9 new Stage-4
presets, 12 new `Agent` traits, 9 new event types, and the
`simulation.py` wiring (compliance decided inside `_ecological_round`
before patch submission; a new `_rule_formation_round` runs monitoring →
sanctioning → proposal/adoption → membership → amendment → dissolution
after). `rule_formation_enabled=False` (default) is an exact, verified
Level-0.3b-compatible no-op.

## 2. Preflight audit (Section 3)

Completed before any Level 1.0 mechanism was written. Two
`coupled_same_model`-branch dispatch defects (documented, not caused, by
Level 0.3b) were fixed; proven by direct source inspection that neither
ever reached Level 0.3b's principal (`"independent"`-mode) causal
finding; 8 regression tests added; only the 2 provably-affected
`coupled_same_model` fitness-stream cells were rerun (all other Level
0.3b outputs untouched). **Stop condition not triggered** — Level 1.0
implementation proceeded.

## 3. Why the Level 0.3b recommendation was overruled

Level 0.3b's completion report recommended not proceeding to Level 1
because no robust interior-persistent/oscillatory/recoverable regime was
demonstrated. This project's own previously-agreed decision gate allowed
proceeding through *either* spontaneous/partial self-regulation *or*
causally demonstrated coordination failure — Level 0.3b produced the
second route. The recommendation's underlying empirical findings (all six
causal-effect bootstrap CIs excluding zero, the propensity drift, the
`maintenance_disabled` comparison) are **retained and not reopened**; only
the *decision criterion* is disputed. Full reasoning:
`docs/level1.0_decision_record.md`.

## 4. Did shared rules emerge without being forced?

Yes. `proposal_probability` is a per-agent trait drawn from a small mean
(0.005-0.05 across Stage 2's search space); nothing selects, seeds, or
biases which patches see a proposal. Across the full Stage 2 grid (32
points x 5 seeds x 7 patches = 1,120 patch-runs at the primary
`interior_persistent` candidate), only 5 of 1,120 patch-runs saw literally
no proposal at all — every other patch-run saw at least one proposal
attempt, and adoption (not mere proposal) succeeded in 128+24 = 152 of
them reaching a `persistent_proto_institution` or `proto_institution`
classification.

## 5. How many proposals were adopted vs. rejected?

Stage 1 calibration (5 seeds x 4 conditions, 400 steps): 96-111 proposals
per condition, 52-68 adopted, 40-55 rejected (roughly half-and-half —
adoption is neither automatic nor rare). Stage 2 primary grid: 132 of
1,120 patch-run outcomes were `proposal_rejected` specifically (adoption
does happen, but is not guaranteed).

## 6. How many qualified as proto-institutions (Work Package K)?

Stage 2 primary: 128 `persistent_proto_institution` + 24
`proto_institution` = 152 of 1,120 patch-runs (13.6%). Stage 2 secondary:
8+2=10 of 48 (20.8%) at `nonstationary`; 15+2=17 of 72 (23.6%) at
`near_collapse`. **`founder_dependent_arrangement` was the single most
common outcome everywhere** (530/1,120 = 47.3% at the primary candidate)
— most adopted rules do not outlive their founder's own membership within
the tested window.

## 7. Did any persist after founder removal?

Yes, both in the ordinary run population (Stage 3's confirmed
persistent-proto-institution candidate: 50.6% founder-independence rate
across 24 confirmatory seeds — a rule instance whose founder is no longer
a member) and under the deliberate §19 founder-removal shock (46.6% of
88 pre-shock-active rule instances were still active after their founder
was forcibly removed at step 300).

## 8. Did replacement/new agents reproduce the rule?

Yes, in a documented, lineage-recorded (not similarity-inferred) sense:
Work Package G reconstruction — a fresh proposal drawn as a bounded
mutation of a specific dissolved rule's parameters, tagged
`origin="mutation"` with a real `parent_rule_lineage_id` — occurred 12
times in the Stage 2 primary grid and, more directly relevant to this
question, 8-14 times per shock type in §19 (43 total lineage-recorded
reconstruction attempts across the four shock types' 15-seed batches),
i.e. after a rule's disruption, a new member sometimes proposed a rule
that carries forward the prior rule's own content, not merely a
coincidentally similar independent proposal.

## 9. What was the difference between compliance and adoption?

Substantial and measured directly. Stage 3's three confirmed candidates
showed mean compliance rates of 0.673-0.723 (never 1.0, never 0.0) with
mean violation rates of 0.277-0.334 — adoption never mechanically
produced universal compliance; a nontrivial, persistent minority of
members violate every rule tested, at every candidate, including the one
selected specifically for being a persistent proto-institution.

## 10. Did monitoring and sanctioning act as complements?

Directionally, cautiously: yes, in the expected qualitative sense (Stage
4's `sanction_without_reliable_monitoring` condition, where detection
accuracy is degraded to 0.5 and false-positive rate raised to 0.45,
showed a slightly less negative occupancy point-estimate and a lower mean
compliance rate than `monitoring_plus_voluntary_sanction`'s more reliable
pairing is not straightforwardly ordered in this particular run — see the
full table in §7 of `docs/level1.0_scientific_note.md`). No condition's
seed-paired effect excludes zero at 20 seeds, so this project reports the
qualitative direction without claiming a confirmed complementarity effect.

## 11. Did any configuration preserve patch maintenance better than the endogenous baseline?

Not confirmed. `proposals_only` and `imposed_rule` showed the only
*positive* point-estimate occupancy effects relative to `atomic_baseline`
(+0.043 and +0.032 respectively) among Stage 4's 10 non-baseline
conditions — but neither seed-paired 95% bootstrap CI excludes zero at
n=20. This is a plausible, not a confirmed, effect.

## 12. Did extraction reduction actually occur under any configuration?

Not measured as a standalone comparison in this milestone (Stage 4 
reports final occupancy, cumulative extraction/maintenance, and
compliance rate per condition, but a dedicated extraction-reduction
paired-effect table was not built as its own deliverable — a gap, not a
claim of a null result; see `outputs/level1_stage4_counterfactuals/
stage4_report.json`'s `ecological_outcomes.cumulative_extraction` field
for the raw per-seed data a follow-up analysis could use directly).

## 13. Did patch survival improve under any tested condition?

`n_patches_at_zero_resources` was tracked per run
(`ecological_outcomes`) but not aggregated into its own comparison table
in this note — the same disclosed gap as §12. Final mean occupancy
(§7 of the scientific note) is the closest proxy reported, and shows the
same "no CI excludes zero at 20 seeds" caveat.

## 14. What costs did institutions impose?

Directly measured and substantial: mean total monitoring cost and
sanction cost per condition/run (`compliance_enforcement.total_
monitoring_cost`/`total_sanction_cost`, Stage 3/4 records), membership
exit costs, and (`collective_fund` mode) diverted maintenance investment.
Every enforcement-bearing Stage 4 condition showed a lower point-estimate
final occupancy than the two enforcement-free conditions
(`proposals_only`, `imposed_rule`) — consistent with, though not
confirmed proof of, real enforcement cost outweighing its compliance
benefit at this specific institutional-parameter point.

## 15. Welfare/equality trade-offs?

Measured (`welfare.mean_member_resources`/`mean_nonmember_resources`/
`member_gini`/`nonmember_gini`, every Stage 3/4 record) but not
synthesized into one trade-off verdict — per Work Package J's explicit
"do not combine into one score" instruction, these remain separate,
inspectable columns. Point pattern observed: mean member resources were
lower than mean non-member resources in most Stage 4 conditions (e.g.
`atomic_baseline`'s member concept is undefined since there is no
institution; `monitoring_plus_voluntary_sanction`: members 74.4 vs.
non-members 290.3) — membership appears costly in raw-resource terms in
this run set, not confirmed as a general finding.

## 16. Did institutions ever coordinate overexploitation?

Not directly tested as a dedicated scenario in this milestone (H9's
"institutions may reproduce extraction-favoring rules or coordinate
overexploitation" was registered as a hypothesis with no predetermined
direction, but no run in Stage 1-4 was specifically designed to detect
collectively-organized overexploitation as opposed to individual
violation). A genuine open question for follow-up work, not answered
here.

## 17. Imposed vs. emergent institution performance?

`imposed_rule` (mechanical, guaranteed compliance) showed the second-best
point-estimate occupancy of all 10 non-baseline Stage 4 conditions
(+0.032 vs. baseline, behind only `proposals_only`'s +0.043) and the
highest mean compliance rate (0.775) of any condition with real
enforcement. Emergent (Stage 3-confirmed) institutions showed
substantially lower compliance (0.673-0.723) and, once monitoring/
sanctioning were added on top, a negative point-estimate occupancy
effect. Neither comparison's CI excludes zero at this sample size.

## 18. Did removing an institution reverse any prior effect?

Partially, plausibly: `institution_formed_then_removed`'s point-estimate
occupancy effect (+0.0049) sits almost exactly at the `atomic_baseline`
level, between the positive-effect conditions and the negative-effect
enforcement conditions — consistent with, but not proof of, the
institution's influence washing out over the second half of the run once
removed at step 300.

## 19. Was there any evidence of reconstruction after dissolution?

Yes — see §8 above (12 in Stage 2, 43 across the four §19 shock types).
Every counted instance carries a real `parent_rule_lineage_id`, never
inferred from parameter similarity alone (Work Package K's `lineage_
recorded` criterion).

## 20. Is there evidence of a "recurrent institutional phenotype"?

No — and this report does not claim one. A recurrent phenotype would
require recurrence across independent histories, persistence, founder
independence, lineage/reconstruction, parameter-neighborhood robustness,
perturbation response, and macroscopic similarity despite microscopic
turnover (Section 25's explicit bar). This milestone's neighborhood
checks (Stage 3, +-10% on 7 continuous parameters) showed the persistent-
proto-institution candidate's classification was *not* perfectly stable
under perturbation (label mix shifted at nearby points — see `outputs/
level1_stage3_confirmatory/stage3_report.json`'s `neighborhood_checks`),
which is itself informative: this milestone identifies *candidates*, not
a proven phenotype.

## 21. Recommendation on proceeding to Level 1.1

A genuine, real, unforced proto-institution phenomenon was demonstrated
— rules are proposed, adopted, complied with and violated, monitored
imperfectly, sanctioned imperfectly, sometimes outlive their founder, and
sometimes get reconstructed after dissolution or a shock. The central
open finding — that real monitoring/sanctioning infrastructure trends
toward a *negative*, not positive, ecological effect relative to no
institution at all, at this specific institutional-parameter region and
ecological point — is directionally consistent across every enforcement-
bearing Stage 4 condition but is **not statistically confirmed** at the
20-seed scale used here (unlike Level 0.3b's confirmed causal findings).
Before any further model expansion, this project's recommendation is:
replicate Stage 4 at Level-0.3b-scale seed counts (~20-24, already close;
a larger count such as 40-60 would sharpen the CIs) to determine whether
this pattern is real, before treating "enforcement infrastructure costs
more than it buys" as a confirmed Level 1.0 finding on par with Level
0.3b's causal claims. **Per explicit instruction, this recommendation is
advisory only — Level 1.1 does not begin regardless.**

## 22. Test suite and reproducibility

**655 tests** (601 pre-existing Level 0-0.3b/preflight + 54 new Level
1.0-specific: 45 in `tests/test_level1_rule_formation.py`, 9 in `tests/
test_institution_diagnostics.py`), **0 failed, 0 warnings** (`-W error`),
**97% statement coverage** (3,593 statements, 120 missed) — verified
directly, not assumed, immediately before this report.

## 23. Documentation delivered

`docs/odd_level1.0.md` (model description), `docs/level1.0_scientific_
note.md` (full findings, every scale reduction disclosed), `docs/
level1.0_decision_record.md` (the overrule reasoning), `docs/config_
reference.md` (Level 1.0 section appended), `README.md` and `dev_mem/
project_vision.md` (current-status sections updated), `dev_mem/status_
update.md` (continuously updated Level 1.0 log entry).

## 24. Visualizations delivered

16 of the requested 20 figures (`experiments/make_level1_visualizations.py`,
`outputs/level1_figures/`) — every figure with a multi-seed/multi-point
value shows its sample size explicitly, and Stage 4's key comparison
figures show 95% CIs, not point estimates alone.

## 25. Every documented reduction from the milestone's literal scale

Listed exhaustively, with the reasoning for each, in §9 of `docs/
level1.0_scientific_note.md` — none was chosen based on which way a
result came out (Stage 2's reduced secondary-candidate scale was decided
before Stage 2 was run).

## 26. Preservation of prior work

All Level 0-0.3b outputs preserved unmodified except the two
provably-affected `coupled_same_model` fitness-stream cells (preflight
audit, §2 above), which were replaced in place with a clear before/after
record retained in `outputs/level03b_fitness_stream/`'s summary JSON. All
Level 1.0 work lives in new `outputs/level1_*` directories and new
`rules`/Level-1.0-specific files — nothing pre-existing was deleted or
silently overwritten.

## 27. Stop condition

**Level 1.0 is complete. Stopping here for scientific review, per
explicit instruction. Level 1.1 is not begun regardless of this report's
recommendation.**
