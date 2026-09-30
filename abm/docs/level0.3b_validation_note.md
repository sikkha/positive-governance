# Level 0.3b Scientific Findings — Regime Validation and Causal Replication

**Status: milestone complete. Stopping for scientific review, per explicit
instruction. Level 1 has not been started, regardless of the findings
below.** See `docs/odd_level0.3b_addendum.md` for the model-description
addendum and `dev_mem/status_update.md`'s Level 0.3b entries for the
full session-by-session log.

This note follows the milestone's required category separation:
implementation facts, preregistered criteria, exploratory reanalysis,
confirmatory findings, causal findings, null findings, classification
corrections, anomalies, limitations, unresolved questions, and the Level
1 decision-gate recommendation.

---

## 1. Implementation facts

- Level 0.3b adds **no new generative mechanism**. Every `SimulationConfig`
  field used anywhere in this milestone's scripts already existed at the
  end of Level 0.3. The 7 (+1 preserved) causal conditions are
  combinations of existing fields (`docs/odd_level0.3b_addendum.md` §4).
- A new, independently-versioned regime classifier,
  `observer/regulation_diagnostics.py::classify_regime`
  (`CLASSIFIER_VERSION = "0.3b-v1"`), was added alongside Level 0.3's
  original `nonstationary_classification`, which is unmodified and still
  what every Level 0.3 output on record was computed with.
- A repaired, eligibility-screened perturbation-recovery diagnostic
  (`recovery_eligibility`/`recovery_quality`/`assess_perturbation_
  recovery`) was added alongside Level 0.3's original
  `perturbation_recovery`, also unmodified.
- 56 new hand-constructed unit/scenario tests
  (`tests/test_classify_regime.py` — 33; `tests/test_recovery_eligibility.py`
  — 13; plus 23 pipeline/integration tests in
  `tests/test_level03b_pipeline.py`). Full suite after all Work Packages:
  **539 passed, 0 failed, 0 warnings, 98% statement coverage** (`python3
  -m pytest -q -W error::RuntimeWarning -W
  error::pandas.errors.PerformanceWarning --cov=abm_governance`), up from
  the verified Level 0.3 starting baseline of 470/97%/0 warnings — no
  regression to any Level 0-0.3 test.
- A real numerical bug was found and fixed while building the classifier
  tests: a mathematically constant series carries floating-point variance
  on the order of 1e-33 to 1e-36, not exactly `0.0`; an unguarded `var ==
  0` check let this near-zero-but-nonzero variance amplify float noise
  into spurious near-1.0 "autocorrelation" on a perfectly flat series.
  Fixed with an explicit tolerance constant (`_NEAR_ZERO_ATOL = 1e-9`).
- A deliberate, disclosed deviation from the milestone brief's prose
  category-listing order: `classify_regime` checks oscillatory/
  intermittent *before* interior-persistent (the brief's prose lists
  interior-persistent first). Checking interior-persistence first would
  silently absorb any trajectory that oscillates *within* the interior
  band into "interior-persistent" before the oscillatory test is ever
  reached — exactly the failure mode this audit exists to catch. See
  `observer/regulation_diagnostics.py`'s module comment for the full
  rationale.
- `pyproject.toml` gained a declared `scipy>=1.10` dependency (a
  housekeeping fix; `scipy` was already a de facto dependency via Level
  0.2/0.3's `scipy.stats.qmc` import).

## 2. Preregistered criteria

All eligibility/robustness/confirmation thresholds below were fixed
*before* being applied to real data, and are recorded in the scripts and
in `dev_mem/status_update.md` in the order they were committed:

- Interior-persistent candidate eligibility: **>= 2 of 3** exploratory
  screening seeds individually satisfy `classify_regime`'s
  interior-persistent criterion.
- Oscillatory/intermittent candidate eligibility: **>= 1 of 3**
  exploratory seeds satisfy the oscillatory criterion; if none exists
  across both search batches, fall back to intermittent under the same
  rule.
- Near-collapse candidate: smallest `|mean_occupancy -
  depletion_threshold(0.05)|` among non-collapsed points.
- Confirmation "robust" label: seed-level agreement with the plurality
  label **>= 0.70** at n=24 (0.60/0.80 reported as sensitivity checks,
  never substituted as the primary criterion after the fact).
- Parameter-neighborhood robustness: **>= 50%** of local-neighbor seeds
  (±10%/0 perturbation, 8 seeds/local point) reproduce the confirmed
  label.
- Supplemental search: invoked **only if** the existing 48-run reanalysis
  produced no eligible interior-persistent or nonstationary candidate —
  recorded in `status_update.md` *before* the supplemental search ran
  (design seed `20260817201`, same parameter ranges as Level 0.3's own
  search, 32 points x 3 seeds, one batch only).
- Perturbation recovery eligibility (Work Package J): pre-shock occupancy
  above the depletion threshold; matched control not itself already
  collapsing; minimum meaningful early post-shock displacement (>= 0.05);
  minimum post-shock horizon (>= 20 steps) — all four required before any
  recovery statistic is computed.
- Candidate registration (`outputs/level03b_candidate_registry/
  candidate_registry.json`) is read-only downstream: no confirmation,
  causal, robustness, or perturbation script re-selects candidates, and no
  candidate was replaced after selection because its later results were
  disappointing.

## 3. Exploratory reanalysis (Work Package B)

Level 0.3's 48 phase-search runs were **deterministically reproduced**
(not re-explored — `Simulation` is fully deterministic given
`(config, seed)`; every reproduced run's final aggregate occupancy and
cooperation rate matched the already-committed
`niche_phase_search_outcomes.csv` with **0 mismatches across all 48
runs**) and reclassified with `classify_regime`.

**27 of 48 runs (56.25%) changed label.** At the run level: unclassified
19, abundant 13, depleted 12, interior-persistent 4, **oscillatory 0,
intermittent 0** — every run Level 0.3's original classifier called
"oscillatory" (14/48) or "intermittent" (6/48) reclassified as something
else once burn-in is excluded and multi-cycle/amplitude/autocorrelation
evidence is required. At the (scientifically meaningful) parameter-point
level (16 points, 3 seeds each): plurality labels are unclassified (7),
depleted (5), abundant (4) — **zero points have an oscillatory,
intermittent, or interior-persistent plurality**, and the closest any
point comes to the interior-persistent eligibility bar is 1 of 3 seeds
(points 2, 5, 13, 14).

**The originally-displayed "oscillatory" example (Level 0.3 figure 12,
`point_id=0, seed=0`) reclassifies as `unclassified`** — zero completed
cycles, zero detectable peak-to-trough amplitude, a strong monotonic
downward trend settling to a flat, low (~0.12-0.13) occupancy (see Fig 4).
This is a direct, confirmed instance of the concern the milestone brief
raised: the displayed oscillatory example does not survive audit, and its
old label does not survive either.

Because no point met the interior-persistent or nonstationary eligibility
bar, the single prespecified supplemental search (32 points x 3 seeds,
design seed `20260817201`) was run. It surfaced **2 points with >= 2/3
seeds interior-persistent** (points 15, 18) and **1 point with an
intermittent plurality** (point 23), but **still 0 points with any
oscillatory seed** across all 144 point-seed runs in either batch —
reported here as a finding in its own right: no oscillatory regime was
found anywhere in the 48-point parameter space searched by either batch,
under the audited classifier.

## 4. Confirmatory findings (Work Packages C, D, E)

Candidates registered (`outputs/level03b_candidate_registry/
candidate_registry.json`, selection blind to any cooperation/social field
— verified by a structural test): `interior_persistent` = supplemental
point 15 (2/3 exploratory seeds interior-persistent), `nonstationary` =
supplemental point 23 (intermittent, 1/3 exploratory seeds), `near_collapse`
= original point 8 (closest non-collapsed point to the depletion
boundary).

**Neither exploratory-interesting candidate replicated robustly at n=24
confirmation seeds:**

| candidate | plurality label (n=24) | agreement with plurality | robust at 0.70? |
|---|---|---|---|
| `interior_persistent` | **unclassified** (14/24; interior-persistent only 5/24, depleted 5/24) | 0.583 | No (fails even the 0.60 sensitivity check) |
| `nonstationary` | **depleted** (16/24; its own original intermittent label recurs only 2/24) | 0.667 | No (passes 0.60, fails 0.70) |
| `near_collapse` | **depleted** (18/24) | 0.750 | **Yes** — the only candidate that robustly confirmed, and it confirmed as depleted, not as any interesting regime |

This directly answers one of the milestone's central questions: **Level
0.3's phase-search "diverse outcome distribution" does not survive
replication at realistic seed counts** — the n=3 exploratory screening
labels were not a reliable guide to a parameter point's typical behavior.

**Parameter-neighborhood robustness (Work Package E)**, applied to the
*confirmed* labels (not the hoped-for exploratory ones): `interior_
persistent`'s confirmed `unclassified` outcome is locally robust (58.3%
of 96 local-neighbor seeds across 4 perturbed axes reproduce
`unclassified`, above the 50% bar on every axis individually and pooled).
`nonstationary`'s confirmed `depleted` outcome is also locally robust on
both axes tested (70.8%/higher). In both cases, **it is the confirmed,
not the originally-hoped-for, outcome that occupies a neighborhood** —
this is a real, if unglamorous, robustness result: these parameter
regions reliably produce unclassified/depleted dynamics across a
meaningful local neighborhood, not by chance at a single fragile point.

## 5. Causal findings (Work Packages F, G, H, I)

**Central causal result, all three candidates agree in direction:**
endogenous adaptive ecological behavior (free imitation + mutation of the
ecological policy) causally **worsens** ecological persistence relative
to `frozen` (fixed initial policy) and `randomized` (policy irrelevant to
the per-step decision) counterfactuals, at 20 (primary) / 12 (secondary)
matched seeds, 600 steps:

| candidate | endogenous vs. frozen (Δ occupancy, 95% bootstrap CI) | endogenous vs. randomized (Δ occupancy, 95% CI) |
|---|---|---|
| `interior_persistent` (n=20) | −0.204 [−0.294, −0.119] | −0.261 [−0.351, −0.171] |
| `nonstationary` (n=12) | −0.609 [−0.761, −0.441] | −0.402 [−0.572, −0.259] |
| `near_collapse` (n=12) | −0.185 [−0.272, −0.098] | −0.386 [−0.570, −0.202] |

All six confidence intervals exclude zero, in the same (negative)
direction. `patch_survival_fraction` shows the same pattern. `shuffled`
and `environment_only` are statistically indistinguishable from
`endogenous` for all three candidates (CIs include zero) — i.e. *which*
agent holds which policy, and whether agents affect the patch at all,
matter far less than *whether policy composition itself is free to
adapt*. `maintenance_disabled` shows `endogenous` outperforming (primary
candidate: +0.058 occupancy, CI [0.022, 0.094]) — maintenance activity
has a small, real, positive effect when active, even though the
population's own evolutionary trend moves it away from maintenance.

This is consistent with the observed propensity drift: across the
primary candidate's 24 confirmation seeds, mean extraction propensity
rises from 0.501 (initial) to 0.530 (final) while mean maintenance
propensity falls from 0.307 to 0.071 — free imitation+mutation evolves
the population *toward* extraction and *away* from maintenance, which
depletes patches faster than a static or acausal policy population would.

The legacy Level 0.3 binary `fraction_interior`/feedback-dependence
criteria (retained only for continuity with Level 0.3's own reporting
convention) do **not** detect feedback dependence for the primary
candidate (`criterion_met: false`) — a second, independent line of
evidence (alongside the confirmation failure in §4) that this is not a
robust interior-persistent attractor, even though the continuous causal
effect above is real, large, and consistently signed across all three
candidates.

**Fitness-stream separation (Work Package H)**: crossing
`ecological_inheritance_mode` (`"independent"` = ecological stream,
`"coupled_same_model"` = total stream) with
`endogenous`/`frozen`/`randomized`/`environment_only`, the `total`-stream
population reaches a *higher* mean occupancy under `endogenous` (0.502)
than the `ecological`-stream population (0.216) — selecting imitation
purely on the ecological payoff signal does **not** protect the resource
better than selecting on the mixed social+ecological signal; if anything
the reverse. Ecological fitness is not treated as normatively superior
anywhere in this analysis.

**Micro-macro linkage (Work Package I)**, applied to real data for the
first time: pooled within-candidate correlation between final maintenance
propensity and patch-survival-fraction is r=0.72 (`interior_persistent`)
and r=0.23-0.45 (other candidates) — weaker and reported with the same
correlational caveat `docs/level0.2_scientific_note.md` established. The
**stronger, intervention-based evidence** is the causal-condition table
above itself: manipulating whether policy composition can adapt at all
(not merely observing its variation) produces the large, CI-excluding-
zero effects — this is the paper's strongest evidence that policy
composition causally drives ecological outcome.

## 6. Null findings

- No oscillatory regime survives the audited classifier anywhere in
  either the original 16-point or supplemental 32-point search (0 of 144
  point-seed runs).
- No candidate confirmed as a robust interior-persistent regime at n=24
  (best case, `interior_persistent`, is 5/24 = 20.8%).
- `shuffled` and `environment_only` show no detectable causal effect
  relative to `endogenous` for any candidate (all CIs include zero) —
  neither *which* agent holds a policy nor *whether* agents affect the
  patch at all matters much; only *whether policy composition can adapt*
  does.
- The legacy binary feedback-dependence criterion is not met for the
  primary candidate, despite a real continuous causal effect existing —
  a direct illustration of the milestone's own warning not to let a
  binary effect distribution conceal continuous separation (here, in the
  opposite direction: the binary criterion is silent where the continuous
  one is not).

## 7. Classification corrections

- Level 0.3's phase-search oscillatory (14/48) and intermittent (6/48)
  categories do not survive the audit: 0 runs classify as either under
  `classify_regime`. Level 0.3's own committed output files
  (`outputs/niche_phase_search/`) are **not** rewritten — they stand
  exactly as recorded, with this correction layered on top, per the
  milestone's explicit preservation instruction.
- `docs/level0.3_scientific_note.md`'s "0.667 is less than 0.5" wording
  error is corrected in place with an explicit dated correction
  paragraph (not a silent rewrite) — see that document §5.

## 8. Anomalies

- Two architectural interactions were discovered while building the
  fitness-stream experiment, documented rather than silently patched in
  the generative layer (`docs/odd_level0.3b_addendum.md` §5):
  `coupled_dual_imitation_round` does not gate on
  `ecological_policy_randomized_each_step`; freezing ecology under
  `coupled_same_model` necessarily freezes social imitation too, since
  the coupled dispatch branch never reads `ecological_imitation_enabled`.
- The confirmatory perturbation experiment (Work Package K) found that
  the overwhelming majority (213/244 = 87.3%) of shock/seed/condition
  combinations were **ineligible** for a recovery verdict at all — mostly
  because the pre-shock baseline was already at or below the depletion
  threshold. This was not anticipated at the scale it occurred (eligibility
  as low as 0% for `near_collapse` and 3.1% for `nonstationary`); it is a
  direct, load-bearing confirmation of the milestone brief's concern about
  "recovery" claims computed at collapse-prone baselines.

## 9. Limitations

- All seed counts (12-24) are modest by ABM standards; confirmation
  agreement fractions and causal-effect confidence intervals reflect this
  — they are reported with explicit `n` and CIs throughout, not asserted
  as larger-sample-equivalent.
- The supplemental search is a single, prespecified 32-point batch; it is
  not a claim that the model's full parameter space was searched
  exhaustively — only that one additional prespecified attempt to find
  interior-persistent/oscillatory candidates was made, and its result
  (2 interior-eligible points, 0 oscillatory) is reported as-is.
- The perturbation-recovery eligibility screen, applied honestly, leaves
  too few eligible observations (0-31 depending on candidate/shock) to
  support a general recovery-rate claim for any candidate — this is
  reported as a limitation of what can be concluded about recovery, not
  smoothed over.
- `randomized` necessarily produces a different per-step draw sequence
  than `endogenous`/`frozen` even under an identical integer seed (by
  definition — a fresh i.i.d. draw every step); "matched seed" for this
  condition means matched *initial* conditions, not matched per-step
  stochastic realization.
- The `shuffled` condition is a one-time initialization shuffle of
  independently-initialized policies; per the milestone's own caution,
  this is weaker evidence about *evolved* agent-patch matching than a
  shuffle performed after meaningful within-run heterogeneity has
  developed. The architecture does not currently support a stronger
  mid-run shuffle without additional generative-layer work, which
  Level 0.3b's validation-only scope does not perform; the claim is
  weakened accordingly (§11 below).

## 10. Unresolved questions

- Whether a different, non-prespecified region of the parameter space
  (one this milestone's two searches did not sample) would produce a
  robust oscillatory or robust interior-persistent regime remains
  unknown — the honest answer from the two searches actually run is "not
  found here," not "does not exist anywhere."
- Whether the `total`-fitness-stream population's higher occupancy
  (§5) reflects a genuine ecological-vs-social-signal tradeoff or an
  artifact of the coupled-mode architectural interactions documented in
  §8 is not fully disentangled by this milestone's one fitness-stream
  experiment.
- Whether a stronger mid-run policy shuffle (not just an
  initialization-time shuffle) would change the `shuffled` condition's
  null causal result is unresolved (see §9).

## 11. Answers to the milestone's twelve named questions

1. **Was Level 0.3's oscillatory category valid?** No. 0 of 144
   point-seed runs across both searches satisfy the audited oscillatory
   criterion; the displayed example (point 0, seed 0) reclassifies as
   unclassified.
2. **How many parameter points robustly classified?** At the exploratory
   (n=3) level, 0 of 48 points are "robustly classified" under the
   reanalysis script's own strict (3/3 unanimous) definition. At n=24
   confirmation, 1 of 3 registered candidates (`near_collapse`) meets the
   preregistered 0.70 agreement bar.
3. **Did any interior candidate survive confirmation?** No. The
   `interior_persistent` candidate's plurality flipped to unclassified at
   n=24 (agreement 0.583, below even the 0.60 sensitivity threshold).
4. **Robust in local neighborhood?** Yes, but for the *confirmed* labels
   (unclassified, depleted), not the originally-hoped-for interior-
   persistent/oscillatory ones — see §4.
5. **Does endogenous adaptation improve or worsen ecology?** It
   **worsens** it relative to `frozen`/`randomized`, consistently across
   all three registered candidates, with bootstrap CIs excluding zero
   (§5). This was not a foregone conclusion — all three outcomes were
   left open, and this is the direction the data show.
6. **Evolved vs. frozen/randomized?** Evolved (`endogenous`) does worse
   than both static (`frozen`) and acausal (`randomized`) counterfactuals
   — see the table in §5.
7. **Does agent-patch matching matter?** No detectable effect: `shuffled`
   is statistically indistinguishable from `endogenous` for all three
   candidates (§5, §6).
8. **Does ecological fitness alter evolution?** Yes: the `ecological`
   fitness stream produces markedly lower occupancy (0.216) than the
   `total` stream (0.502) under `endogenous`, for the primary candidate
   (§5). No normative superiority is claimed for either.
9. **Is social cooperation separable from ecological restraint?** Not
   newly tested at Level 0.3b (this milestone did not rerun Level 0.3's
   original cooperation-ecology architecture check); the structural
   separation Level 0.3 already established (the two policies never read
   or derive from each other) is unchanged and unre-examined here.
10. **Are recovery claims supported after eligibility repair?** No, not
    generally: 87.3% of shock/seed/condition rows were ineligible for a
    recovery verdict once the pre-shock baseline and displacement
    requirements are enforced; the small number of eligible observations
    (0-31 depending on candidate) does not support a general claim either
    way (§4, §8, §9).
11. **Regulation, partial, failure, or inconclusive?** See the Level 1
    decision-gate table below (§12) — the classification is **Outcome C
    (robust coordination failure)** for the interior-persistence/
    oscillatory question specifically, combined with a real, replicated,
    negatively-signed causal effect of adaptation on ecological outcome.
12. **Proceed to Level 1?** **No — not recommended at this time.** See
    §12.

## 12. Level 1 decision gate

| criterion | evidence | met? |
|---|---|---|
| A robust (>=70% agreement, n>=24) interior-persistent regime exists at a prospectively selected, non-degenerate parameter point | `interior_persistent` candidate: 0.583 agreement, plurality flips to unclassified | **No** |
| A robust oscillatory or intermittent regime exists | 0/144 point-seed runs satisfy the audited oscillatory criterion anywhere searched; `nonstationary` candidate's intermittent label recurs on only 2/24 confirmation seeds (agreement 0.667, plurality flips to depleted) | **No** |
| Endogenous ecological adaptation has a detectable, non-null causal effect on ecological outcome (any direction) | Yes — consistently negative (worsening) across all 3 candidates, CIs excluding zero | **Yes**, direction = worsens |
| The causal effect is locally robust, not a single-point artifact | Confirmed labels (unclassified/depleted) are locally robust in the parameter neighborhood (§4); the causal-effect *sign* was not itself re-tested off-candidate-center, a scope limitation noted here | Partially |
| Perturbation-recovery claims are supported once eligibility is screened | 87.3% of rows ineligible; no general recovery-rate claim supported | **No** |

**Outcome: closest to Outcome C (robust coordination failure) for the
interior-persistence/self-regulation question, with a real, replicated,
negatively-signed causal effect of adaptation layered on top** — i.e. not
only does this model's default/registered parameter regions fail to
produce a robust self-regulating or cyclically-recovering ecological
regime, but where adaptation has any detectable effect at all, it makes
the ecological outcome *worse*, not better, than static or acausal
counterfactuals. This is not Outcome D (mechanically inconclusive): the
classifier, confirmation, and causal pipelines all ran to completion with
adequate sample sizes and produced consistent, non-contradictory answers
— the "inconclusive" label would understate how much was actually learned
here.

**Recommendation: do not proceed to Level 1 at this time.** Before adding
any Level 1 mechanism (reputation, institutions, delegation), the more
scientifically urgent next step — flagged by Level 0.3 and now doubly
confirmed by Level 0.3b — is to understand *why* free ecological-policy
adaptation worsens outcomes in this model (an extraction-favoring
evolutionary drift under imitation+mutation) before layering social
governance mechanisms on top of an ecological substrate that a validated,
prospectively-registered pipeline shows does not self-regulate under its
own agents' adaptive behavior. **Per explicit instruction, Level 1 is not
implemented in this milestone regardless of this recommendation.**
