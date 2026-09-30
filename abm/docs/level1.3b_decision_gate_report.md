# Level 1.3b Decision Gate Report — Section 19

**Status: renders the formal eight-way classification, argued from the
Stage 0-10 evidence already on record in `docs/level1.3b_scientific_
note.md`. This document adds no new run and no new number beyond one
disclosed re-application of an already-frozen classifier (§4 below) —
it is a reasoning document over evidence that already exists, mirroring
Level 1.3's own separation of its decision-gate report from its
completion report and scientific note.**

## 1. The outcome space, restated exactly as preregistered

From `experiments/level13b_preregistration.py::DECISION_GATE_OUTCOMES`,
frozen before any Stage 3+ run (reconstructed from a compacted summary
of Section 19, disclosed as such in that module's own docstring — not
a verbatim transcription):

| Label | Outcome |
|---|---|
| A | no_effect — no reproducible historical/sequencing effect detected at all |
| B | pressure_responsive_nonhistorical — institutions respond to pressure MAGNITUDE but not to its temporal ORDER or history |
| C | transient — differentiation appears but does not persist; families/gradient reconverge given enough steps |
| D | persistent_continuum — persistent path dependence on a CONTINUOUS gradient, not separable discrete families |
| E | two_families — persistent path dependence into exactly two reproducible discrete families |
| F | three_families — persistent path dependence into exactly three reproducible discrete families |
| G | four_or_more_families — persistent path dependence into four or more reproducible discrete families |
| H | inconclusive — evidence does not clearly support any of A-G |

`DECISION_GATE_DO_NOT_PREFER = "F_three_families"`, scoped explicitly by
its own frozen note to mean the discovery pipeline's own default must
not be biased toward three families — it does not mean F is
disqualified as a genuine finding if the evidence actually supports it.
No Stage 3-10 script special-cased or biased toward F; this report does
not either, and (as §4 shows) F is ruled out on the same evidence that
rules out E and G, not singled out for extra scrutiny.

## 2. Ruling out A (no effect) — directly contradicted by three independent causal findings

**A is ruled out.** Three separate pieces of this milestone's own
record show a real, nonzero, reproducible effect:

- Stage 3's 216-run matched factorial shows real (if modest, ~1.2-1.4%
  relative) variation in S_obs/Z_obs by pressure-onset ORDER holding
  total exposure matched, with 26/108 (24.1%) S_obs and 35/108 (32.4%)
  Z_obs pairwise contrasts showing a seed-clustered-bootstrap CI that
  excludes zero.
- Stage 5 Part B's three counterfactual pressure-history transforms
  (`removed`, `reversed`, `equalized`) each produce a nonzero,
  NON-decaying late-window gap versus the base `security_first` run —
  most tellingly `equalized`, which holds each channel's cumulative
  pressure EXPOSURE exactly constant while removing only its temporal
  SHAPE, and still shows the gap GROWING (early 0.027 → final-sustained
  0.077), not shrinking.
- Stage 6's sham-validated (12/12 seeds byte-identical to control)
  history-erasure interventions show real, persistent divergence for
  `pressure_memory_only` (final-sustained gap 0.054), `entrenchment_
  only` (0.072), and `all_history` (0.069) — divergence the sham itself
  proves is not a fork/measurement artifact.

A "no reproducible effect" reading would require all three of these to
be noise; they are not scattered randomly, they are directionally
consistent (growing or sustained, not fluctuating around zero), and
Stage 6's own sham control specifically rules out the most likely
alternative explanation (measurement/fork-machinery artifact).

## 3. Ruling out B (pressure-responsive, non-historical) — Stage 5's equalized transform is the decisive test

**B is ruled out.** B's own definition is precise: institutions may
respond to pressure MAGNITUDE without responding to temporal ORDER or
HISTORY. Stage 5 Part B's `equalized` transform is constructed exactly
to isolate this: it flattens each channel's realized pressure series to
its own MEAN, which by construction preserves total cumulative exposure
(the "magnitude" B says should still matter) while destroying every
trace of onset timing, shock timing, and temporal shape (the "order/
history" B says should NOT matter). If B were correct, the `equalized`
run should track the base `security_first` run closely — same total
exposure, no history to differ on. Instead, `equalized` shows the
LARGEST final-sustained gap of the three Part B variants (0.077, vs.
0.054 for `removed` from Stage 6 and comparable orders of magnitude for
`reversed`) and a gap that GROWS across windows rather than staying flat
near the small early-window value magnitude-matching alone would
predict. Stage 6's `entrenchment_only`/`pressure_memory_only`
interventions reinforce this from a different angle: `entrenchment_
only` resets only an AGE variable (no pressure magnitude touched at
all) and still produces the single largest final-sustained divergence
of any intervention (0.072) — a pure history/accumulated-state effect,
entirely orthogonal to current pressure magnitude. B requires history
specifically not to matter once magnitude is held fixed; this
milestone's own evidence shows the opposite in its most direct test.

## 4. Ruling out E, F, and G (discrete families) — reusing Level 1.2b's own frozen classifier, unmodified

**Following Level 1.3's own precedent exactly** (which reused Level
1.2b's `classify_discovery_verdict`, Work Package K/Section 16,
unmodified, rather than inventing a new discrete-vs-continuum rule
after the data was already in hand): this report applies that same
function, unmodified, to Level 1.3b's own Stage 7 leading discrete
candidate (`gmm_k1_to_8`, headline k=8).

Inputs, read directly from `outputs/level13b_stage7_model_comparison/
stage7_report.json`: `headline_k=8`; `silhouette_by_k` = {2: 0.143,
3: 0.135, 4: 0.100, 5: 0.070, 6: 0.073, 7: 0.088, 8: 0.055}; `best_
bootstrap_mean_ari=0.752` (clears the 0.3 stability bar comfortably);
`cluster_vs_failure_ari`: not computed this milestone (no failure/
non-failure cluster cross-tabulation was built — a disclosed scope gap,
handled by the classifier's own NaN-safe design, which skips that
specific check rather than erroring).

**Result: `verdict: "one_config"`, reason: `no_k>=2_clears_
silhouette_0.15 (best=0.055)`.** Not one of the eight evaluated k's
(1 through 8) reaches even the classifier's own entry-level 0.15
silhouette floor — the BEST silhouette across the whole range, at k=2,
is 0.143, still below 0.15. This is a MORE decisive signal against
discrete structure than Level 1.3's own case, which cleared the 0.15
floor comfortably (0.334 at its own headline k=2) and needed the
classifier's second-stage "three-or-more k's within 0.05 of the best"
tiebreak to reach `continuum`. Level 1.3b's own data does not even
require that tiebreak: no k in the tested range supports splitting the
pool at all, by this already-frozen, non-invented rule. E (two
families), F (three families), and G (four-or-more families) are all
ruled out on the same evidence, together — F is not singled out for
extra scrutiny beyond what E and G also receive, consistent with
`DECISION_GATE_NOTE`'s own requirement.

Four further, independent pieces of evidence corroborate this rather
than depending on it alone (detailed in full in `docs/level1.3b_
scientific_note.md`'s own H8 section): BIC has not converged within the
tested k=1..8 range (its steepest drop of the whole sequence is at the
k=7→k=8 boundary, 1214.3→538.2, with no sign of turning back up);
HDBSCAN (a density-gap-requiring method) finds only 2 clusters with 41%
noise at its own most permissive setting and zero clusters at every
stricter setting; cross-algorithm agreement is weak once the one
non-independent pair (`gmm_k1_to_8` vs. `unequal_covariance_mixtures`,
which reduce to the identical fit) is excluded (ARI 0.016-0.357 across
the three genuinely distinct pairs); and the partition does not
reproduce when refit independently within each of the three ecological
strata (ARI -0.043 to -0.014).

**The one point of genuine tension, stated plainly rather than
smoothed over**: Stage 8's fresh-confirmation generalization-gap test
is POSITIVE (+3.11 per-run log-likelihood, k=8 over k=1) — unlike Level
1.3's own sharply negative fresh-data collapse. Read in isolation, a
positive gap sounds like support for E/F/G. Read in context, it is not:
a positive gap against a single-Gaussian null is close to guaranteed
for any non-Gaussian continuous cloud of points (an 8-component mixture
is a strictly more flexible density estimator than one Gaussian) and
does not by itself distinguish genuine discrete families from a
continuous density that merely isn't Gaussian-shaped — which is exactly
what the BIC-boundary, silhouette-floor, HDBSCAN, cross-algorithm, and
cross-stratum evidence above independently indicates it is. Section 13/
Stage 8's own frozen rule requires the discrete candidate to beat EVERY
continuous alternative on fresh data to count as discrete; the frozen
continuous candidate (`pca_factor_continuum`) ALSO generalizes well to
fresh data (reconstruction error 0.618 fresh vs. 0.597 in-sample, a
~3.5% increase) — so the discrete candidate's fresh-data performance is
not uniquely strong relative to the continuous alternative it must beat,
it is merely non-catastrophic, on a metric (log-likelihood) that is not
even on the same scale as the continuous candidate's own metric
(reconstruction error) to begin with. This report treats Stage 8's
positive gap as a real, disclosed data point that weakens the case for
D relative to what Level 1.3's own sharp fresh-data collapse provided,
without treating it as sufficient on its own to overturn the five
independent lines of evidence in this section.

## 5. Ruling out H (inconclusive)

H requires the evidence not to clearly support any of A-G. That is not
the situation here: A, B, E, F, and G are each ruled out on specific,
disclosed, converging evidence (§2-4), not merely on the absence of
support for them. What remains — C vs. D — is a live question the
evidence DOES bear on directly (§6), not a case where the record is
silent or contradictory. H is not selected.

## 6. The live question: C (transient) vs. D (persistent continuum)

Both readings have real, disclosed support, and this is where this
report has to weigh evidence rather than merely inventory it.

**In favor of C**: Stage 5 Part A's per-seed persistence classification
(the milestone's own most direct H3 test, comparing `security_first`
vs. `coevolution` ordering differentiation specifically) finds the
MAJORITY outcome (9/16 seeds) is `transient_differentiation` — mid-run
divergence that fades toward the final-sustained window, not families
that stay apart.

**In favor of D**: every OTHER persistence-relevant measurement this
milestone took points the opposite way. Stage 5 Part B's three
counterfactual interventions (`removed`/`reversed`/`equalized`) all
show a GROWING, not shrinking, late-window gap. Stage 6's sham-
validated interventions show the same growing pattern for `pressure_
memory_only`, `entrenchment_only`, and `all_history` — final-sustained
gaps (0.054-0.072) larger than their own middle-window gaps
(0.009-0.017), the opposite of reconvergence. And §4's own weight of
evidence (BIC, silhouette, HDBSCAN, cross-algorithm agreement,
cross-stratum stability) rules out separable discrete families,
leaving "persistent, on a continuous gradient" as the only outcome
consistent with BOTH "real and growing, not fading" (ruling out C) AND
"not discrete" (ruling out E/F/G).

**Reconciling the apparent conflict, not hiding it.** Stage 5 Part A
and Part B/Stage 6 are not measuring the same thing, and the difference
is informative rather than contradictory: Part A asks whether two
DIFFERENT ORDERINGS of pressure (both fully realized, matched-exposure
sequences) stay apart from each other over time — the majority answer
is no, they drift back together. Part B/Stage 6 instead ask whether a
run WITH its actual realized history diverges from the SAME run with
that history erased/reversed/equalized/reset — the answer is yes,
consistently and growing. A system can very plausibly show both
patterns at once: two full, well-formed historical trajectories can
converge toward similar long-run behavior even while each one remains
causally shaped by, and measurably different from, a version of itself
with its own history removed. That is a description of **persistence
of the historical/causal EFFECT** (favoring D) alongside **transience
of the specific ORDERING comparison** Stage 5 Part A tested (a genuine,
narrower instance of C, not a contradiction of D). This report's own
classification below is at the level Section 19's outcome space is
written at — the OVERALL milestone finding on historical path
dependence, which is what §2-4 already established is real, persistent,
and not discrete-family-shaped.

## 7. Verdict: D — persistent_continuum

**D_persistent_continuum** is this report's formal Section 19
classification: a real, causally-demonstrated, sham-validated,
persistent (non-decaying, in several tests growing) effect of pressure
history/order/entrenchment on institutional response, expressed as a
continuous gradient rather than separable discrete families, reached by
(a) ruling out A/B on Stage 3/5/6's own causal evidence, (b) ruling out
E/F/G by reusing Level 1.2b's own frozen classifier unmodified on
Stage 7's data (a MORE decisive `one_config` result than Level 1.3's
own `continuum` result required), (c) ruling out H because the evidence
clearly does support a specific reading, and (d) weighing C against D
directly in §6, where the majority of persistence-relevant evidence
(Stage 5 Part B, Stage 6, and the discreteness evidence together) favors
D at the overall-milestone level, while the narrower Stage 5 Part A
ordering-comparison result is reported as a genuine, disclosed instance
of transience within that broader picture, not smoothed into the
headline verdict.

**This is the same top-level classification (D/continuum) Level 1.3's
own decision gate reached**, arrived at via a substantially different,
independently-collected evidentiary path (a purpose-designed, not
pooled-post-hoc, discovery design; a sham-validated causal intervention
stage Level 1.3 did not have; a positive rather than negative fresh-data
generalization gap, reasoned through rather than taken at face value).
This report does NOT treat agreement with Level 1.3's own prior verdict
as evidence in D's favor — it is reported here only as an observation,
per this milestone's own stopping-rule requirement not to silently
promote Level 1.3's continuum verdict; D is reached from Level 1.3b's
own Stage 0-10 record alone, argued in §2-6 above without reference to
what Level 1.3 found until this paragraph.

## 8. What would change this verdict

- A genuine within-run cluster-assignment-stability diagnostic across
  more than 2 ranked conditions (`condition_rank_stability`'s own
  disclosed degenerate behavior at n=2 conditions, §H3 of the
  scientific note) could sharpen or contradict the C-vs-D reading in
  §6 with a more informative persistence signal than displacement/
  variance/slope alone provide.
- A larger Stage 4/Stage 8 pool (240/96 vs. Section 8/13's own
  preferred 72-96×6-8 / 144-288) could resolve whether the BIC drop at
  the k=7→k=8 boundary (§4) is a genuine still-improving discrete fit
  or an artifact of a search range that stopped one or two k's too
  early — extending the tested k range past 8 is the single most direct
  test of whether §4's `one_config` result is stable.
- A common metric for comparing the leading discrete candidate against
  the leading continuous candidate on fresh data (§4's own disclosed
  gap: log-likelihood vs. reconstruction error are not on the same
  scale) would let Stage 8's positive generalization gap be weighed
  against the continuous alternative directly, rather than only
  against the k=1 null, and could change how much weight §4's "point of
  genuine tension" paragraph deserves.
- Extending Stage 5/Stage 6 beyond their own single representative cell
  to the full Stage 3 factorial would test whether §6's own
  reconciliation (ordering-comparison transience alongside
  history-removal persistence) holds at every entrenchment/legitimacy/
  ecological-stratum combination, not just the one this milestone
  measured directly.

None of these were within this milestone's own disclosed session-budget
scope; all four are stated here as concrete, falsifiable next steps
rather than left implicit.
