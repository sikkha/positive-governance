# Level 1.0 Decision Record — Overruling the Level 0.3b Recommendation

This record documents, explicitly and for the historical record, why
Level 1.0 (proto-institutions) was implemented despite Level 0.3b's own
completion report recommending against it. It exists so a future reader
never has to guess whether this was an oversight.

## 1. Claude's Level 0.3b recommendation

`docs/level0.3b_validation_note.md` §12 concluded:

> **Recommendation: do not proceed to Level 1 at this time.** Before
> adding any Level 1 mechanism (reputation, institutions, delegation),
> the more scientifically urgent next step... is to understand *why*
> free ecological-policy adaptation worsens outcomes in this model...
> before layering social governance mechanisms on top of an ecological
> substrate that a validated, prospectively-registered pipeline shows
> does not self-regulate under its own agents' adaptive behavior.

That recommendation was reached in good faith from the Level 0.3b
decision-gate table, which found: no robust interior-persistent regime
(No), no robust oscillatory/intermittent regime (No), a detectable
non-null causal effect of adaptation (Yes, worsens), partial local
robustness of that effect (Partially), and no supported general
perturbation-recovery claim (No).

## 2. The accepted empirical findings

Every empirical finding underlying that recommendation is accepted
without qualification and is **not** revisited or reopened by this
milestone:

- Across all three prospectively registered Level 0.3b candidates,
  endogenous ecological-policy adaptation reduced ecological occupancy
  relative to `frozen` and `randomized` policy populations: interior
  candidate −0.204 (vs. frozen) / −0.261 (vs. randomized); nonstationary
  candidate −0.609 / −0.402; near-collapse candidate −0.185 / −0.386. All
  six reported 95% bootstrap confidence intervals excluded zero.
- Mean extraction propensity rose from 0.501 to 0.530 across the primary
  candidate's confirmation seeds; mean maintenance propensity fell from
  0.307 to 0.071.
- `maintenance_disabled` reduced occupancy relative to `endogenous`
  (+0.058, CI excluding zero) — maintenance activity is genuinely
  ecologically beneficial even though ordinary imitation selects against
  it.
- No robust interior-persistent, oscillatory, or intermittent regime was
  confirmed at n=24 for any registered candidate; perturbation-recovery
  eligibility was low (12.7% of all rows) once an honest eligibility
  screen was applied.

The mandatory preflight audit at the start of Level 1.0 (§6 below) has
since confirmed these findings were not an artifact of the coupled-mode
dispatch defects discovered at Level 0.3b — see
`dev_mem/status_update.md`'s Level 1.0 entry for the full trace.

## 3. The rejected decision criterion

What is rejected is not the empirical result but the **inference rule**
applied to it. Level 0.3b's recommendation treated the *absence* of
self-regulation as, by itself, a reason to delay institutions —
implicitly requiring the ecological substrate to first demonstrate it
*could* self-regulate before any social mechanism was layered on top.

## 4. The previously agreed two-route gate

That inference rule was never actually what this project's own gate
specified. `docs/level0.3b_validation_note.md` §12 was written to allow
Level 1 to proceed through **either** of two routes:

1. spontaneous or partial ecological self-regulation being demonstrated;
   or
2. a causally demonstrated coordination failure — i.e. clear evidence
   that individual adaptive behavior, left to itself, does not solve the
   commons problem.

Level 0.3b produced the second route, not the absence of both. The
completion report's own recommendation did not apply this second route
when reaching its "do not proceed" conclusion — it treated route 1's
absence as decisive on its own. This project's scientific decision is
that route 2 was in fact satisfied, and that the gate should therefore
resolve in favor of proceeding.

## 5. Why coordination failure justifies Level 1

A causally demonstrated coordination failure is not a reason to abandon
the question of governance — it is the precondition for asking it
meaningfully. The micro-mechanism Level 0.3b uncovered is the causal
foundation of a commons dilemma:

- extraction → immediate private benefit
- maintenance → immediate private cost and shared future benefit
- imitation → spread of extraction-favoring policies through an adaptive
  population
- adaptive population → ecological deterioration

This is exactly the condition under which collective rules — proposed,
adopted, monitored, and enforced locally — become theoretically
interesting to test, because there is now a genuine problem for a rule to
address, rather than a decorative addition to an ecology that already
regulates itself. Level 1.0 is introduced to test whether locally
reproduced rules can resist this specific, already-demonstrated
extraction-favoring evolutionary process — not to manufacture a success
story. All plausible outcomes (institutions fail, institutions worsen
outcomes, institutions succeed but increase inequality, institutions
never form at all) are treated as valid results by this milestone's own
design (see `docs/level1.0_scientific_note.md`).

This project uses the cautious phrase **"replicated coordination failure
across the tested parameter regions"** throughout its Level 1.0
documentation, and does not claim that adaptive behavior must worsen
every possible ecological environment — only that it did, causally and
consistently, across the three regions Level 0.3b's prospective,
outcome-blind registration actually tested.

## 6. The preflight safeguard

Because Level 0.3b's causal finding is the empirical trigger for this
entire milestone, Level 1.0 began with a mandatory, narrow preflight
integrity audit of the causal mechanism *before* any institutional code
was written (milestone spec §3). The audit traced every
`_adaptation_round` dispatch path, confirmed two previously-documented-
but-unfixed coupled-mode gating defects
(`agents/adaptation.py::coupled_dual_imitation_round`), determined that
neither defect could have reached the code path used by the principal
Level 0.3b causal finding (which always used the default
`ecological_inheritance_mode="independent"`, never
`"coupled_same_model"`), fixed both defects, added 8 regression tests
proving the defects' absence post-fix and the principal finding's
insulation from them, and reran only the two Level 0.3b Work Package H
(fitness-stream) cells the defects could have touched. Full detail:
`dev_mem/status_update.md`'s Level 1.0 entry,
`tests/test_level1_preflight_audit.py`. The milestone's own stop
condition — "if the principal finding was invalidated, stop before
implementing Level 1" — was not triggered; the audit is why this
document can state with evidence, not assumption, that the empirical
trigger for this whole milestone still holds.

## 7. Why this is not outcome-driven model expansion

Three structural features distinguish this decision from simply building
whatever mechanism would make the ecology look better:

1. **The trigger is a causal finding already on the record, not a desired
   outcome.** Level 0.3b's coordination-failure result was reached before
   Level 1.0 was proposed, under prespecified, outcome-blind criteria
   that left all three causal directions (improve/worsen/no effect)
   open. Level 1.0 did not select or retune that finding to justify
   itself.
2. **All Level 1.0 outcomes are accepted as valid results by design**
   (milestone spec §4, §17, §20 — hypotheses H1-H10 register no
   direction; "a successful, unsuccessful, exploitative, unstable,
   costly, exclusionary, or ecologically irrelevant proto-institution is
   a valid result"). Candidate selection at every stage (Stage 2 → 3) is
   governed by prespecified institutional criteria only, never by desired
   ecological outcome — mirroring the outcome-blind selection discipline
   Level 0.3b itself established and that this milestone's own tests
   check structurally (no cooperation/social/desired-outcome field
   readable by selection code).
3. **Agents receive no reward for institutional formation, persistence,
   sustainability, or resemblance to any preferred macrostate**
   (milestone spec §6, constraint 2) — an institution that never forms,
   or that forms and immediately dissolves, is exactly as valid a result
   under this architecture as one that persists.

**Per explicit instruction, Level 1.0 stops here. Level 1.1 is not
implemented in this milestone regardless of this decision or Level 1.0's
findings.**
