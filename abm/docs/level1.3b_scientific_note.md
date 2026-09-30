# Level 1.3b Scientific Note — Validation of Historical Path Dependence

**Status: synthesizes the Stage 0-10 evidentiary record (`experiments/
level13b_stage0_frozen_compatibility.py` through `experiments/level13b_
stage10_ecological_control_scale_shock.py`, all outputs under
`outputs/level13b_stage*/`) against the eight preregistered hypotheses
(`experiments/level13b_preregistration.py::HYPOTHESES`). Every number
below is read directly from a saved stage report or a direct, disclosed
re-aggregation of a stage's own `records.json` — none is recomputed
with a new statistical choice not already frozen. This note renders no
decision-gate verdict of its own; that classification is
`docs/level1.3b_decision_gate_report.md`'s separate, dedicated job, per
this milestone's own governance (mirroring Level 1.3's own separation
of `level1.3_scientific_note.md` from `level1.3_decision_gate_
report.md`).**

**Context-loss caveat, restated from the preregistration module itself:
`HYPOTHESES` and `DECISION_GATE_OUTCOMES` are reconstructed from a
compacted summary of Section 18/19, not a verbatim transcription. Every
hypothesis below is evaluated as stated in the frozen manifest, with
that reconstruction caveat carried forward rather than silently
dropped.**

## H1 — bargaining activation

*"`bargaining_participation` activates (a sustained crossing is
registered) in a nondegenerate share of eligible runs once the Work
Package B construction fix is applied, without further generative
calibration."*

**Supported.** The Work Package B fix alone (correcting `observer/
sequencing_diagnostics.py`'s own held-not-zero-filled compliance
series) was sufficient: Stage 2's calibration sweep found 20/24 cells
(83%) landing in the target activation-fraction range [0.2, 0.8] at
the untouched Level 1.1/1.2b `contribution_amount`/`contribution_
period_steps` defaults, with all three ecological strata represented
in that frozen region — no generative parameter change was needed
(`docs/level1.3b_bargaining_activation_audit.md`, `outputs/level13b_
stage2_bargaining_calibration/calibration_report.json`). Stage 4's own
240-run homogeneous discovery pool confirms this at scale: 166/240
(69.2%) activated under `repeated_shocks` pressure with entrenchment
and both legitimacy channels enabled — a genuinely nondegenerate share,
neither near 0% (which would mean the fix did not actually work) nor
near 100% (which would mean the manipulation is uninformative because
every run activates regardless of condition).

## H2 — ordering effect

*"The temporal ORDER in which pressure channels activate produces
measurable, reproducible variation in institutional response, holding
total pressure exposure matched."*

**Weakly supported, with an important sign-consistency caveat
disclosed rather than smoothed over.** Stage 3's 216-run matched
factorial (3 orderings × 3 entrenchment levels × 4 legitimacy
conditions × 3 strata × 2 seeds) pools to mean S_obs of 0.597
(`security_first`), 0.590 (`bargaining_first`), 0.591 (`coevolution`) —
a real but modest (~1.2% relative) spread; mean Z_obs is 0.369, 0.364,
0.366 respectively (~1.4% relative spread). Of the 108 matched pairwise
contrasts, 26 (24.1%) show a seed-clustered-bootstrap CI on the raw
S_obs difference that excludes zero, and 35 (32.4%) do so for Z_obs —
a real minority effect, not a null.

**Direction is not uniform across the three ordering pairs.**
`security_first` vs. `bargaining_first`: 27/36 matched cells show
`security_first` ahead on S_obs (a fairly consistent direction).
`security_first` vs. `coevolution`: 20/36 positive, 16/36 negative — a
near coin flip. `bargaining_first` vs. `coevolution`: 14/36 positive,
22/36 negative — a mild reversal. This is the same "sign-inconsistent
across strata" pattern this milestone's own earlier disclosure flagged:
ordering matters in aggregate and for one specific pair with reasonable
consistency, but not as a single, uniform "earlier-activating channels
always dominate" rule across every pairwise comparison.

## H3 — temporal persistence

*"Differentiation observed mid-run persists (does not fully
reconverge) through the final-sustained window, distinguishing genuine
path dependence from transient response."*

**Mixed, genuinely so — not a clean pass.** Stage 5 Part A's 16
matched-seed comparisons of `security_first` vs. `coevolution`
classify per seed via `observer/historical_persistence.py::classify_
persistence`: 9/16 `transient_differentiation`, 4/16 `historical_
hysteresis`, 3/16 `pressure_dependent_response`, 0/16 `entrenched_path_
dependence` or `no_detectable_differentiation`. The MAJORITY
classification across seeds is transient — differentiation that
appears mid-run tends to fade rather than persist, for THIS specific
ordering-differentiation comparison. `condition_rank_stability` came
back exactly ±1.0 for every seed, disclosed as degenerate rather than
informative (only 2 conditions are ranked, so the "rank stability"
diagnostic collapses to a trivial same-or-reversed binary — the
diagnostic itself was under-specified for a 2-condition comparison, a
scope gap disclosed here, not silently smoothed over).

Part B's counterfactual-persistence result points the opposite
direction on a DIFFERENT question (whether erasing/reversing/
equalizing the pressure HISTORY itself, not merely comparing two
orderings, produces a lasting gap): all three interventions
(`removed`, `reversed`, `equalized`) show a nonzero, NON-decaying
late-window gap versus the base `security_first` run (e.g. `equalized`:
early-window gap 0.027 → final-sustained gap 0.077, growing, not
shrinking). H3 is therefore genuinely mixed depending on which
comparison is asked: ordering-vs-ordering differentiation (H2's own
question) tends to be transient; erasing/altering the realized pressure
HISTORY produces a persistent, non-decaying divergence. Both facts are
reported; H3 is not marked simply "supported" or "not supported."

## H4 — entrenchment moderation

*"Entrenchment strength (off/moderate/strong) moderates how much
differentiation persists once established — stronger entrenchment
predicts less late-run reconvergence."*

**Not supported as a monotonic effect on S_obs/Z_obs, though the
underlying entrenchment MECHANISM itself behaves exactly as designed.**
Stage 3's pooled entrenchment-index-final-step increases monotonically
with the frozen setting (off=0.919, moderate=0.930, strong=0.955 —
`entrenchment_maturation_steps` correctly drives faster accumulation),
confirming the entrenchment mechanism itself works. But mean S_obs
across the same three conditions is 0.594 (off), 0.598 (moderate),
0.586 (strong) — NOT monotonic; strong entrenchment does not show the
highest, or even a clearly elevated, S_obs relative to moderate or off.
Stage 6's `entrenchment_only` intervention (resetting `founding_step`
mid-run, at the SAME representative cell) shows a real, persistent
divergence from `no_intervention_control` (mean |S_obs| gap:
early=0.0, middle=0.017, late=0.065, final_sustained=0.072 — the
LARGEST final-sustained gap of the four real interventions, ahead of
`all_history`'s own 0.054) — evidence that entrenchment causally
matters and that its effect persists rather than fading, but this is a
finding about entrenchment's CAUSAL presence/absence, not about a
graded off/moderate/strong DOSE-response moderating persistence, which
is what H4 as stated actually claims. H4 is reported as not supported
in its stated dose-response form, alongside the genuine, persistent
causal effect Stage 6 does find.

## H5 — history matters causally

*"Erasing or reversing pressure history (Stage 6, matched
interventions, sham-controlled) produces trajectory divergence beyond
what the sham (identical-state-copy) intervention alone produces."*

**Supported, and the sham control itself did real work.** Stage 6's
sham machinery validation passed exactly: 12/12 seeds' `sham_
identical_state_copy` outcome byte-for-byte matches `no_intervention_
control` (`sham_machinery_validated: true`) — the fork/resume machinery
itself introduces zero spurious divergence, the precondition this
milestone's own Section 11 requires before trusting any other
intervention's divergence as historically meaningful. Against that
validated zero baseline, three of the four real interventions show
real, persistent, non-sham divergence: `pressure_memory_only`
(final-sustained gap 0.054), `entrenchment_only` (0.072), `all_history`
(0.069) — none decaying back toward zero from middle to late window.
This is the single strongest piece of evidence in this milestone's
whole record that historical path dependence is causally real, not an
artifact of any measurement or fork-machinery choice — the exact
regression this stage's own sham was designed to rule out.

## H6 — legitimacy channel effect

*"Performance and/or procedural legitimacy channels measurably affect
S_obs/Z_obs and/or persistence, independent of entrenchment."*

**Supported for S_obs/Z_obs, but the effect is substantially, if not
entirely, definitional and disclosed as such.** Stage 3's pooled means:
`performance_legitimacy_enabled` moves mean S_obs from 0.522 (disabled)
to 0.665 (enabled); `procedural_legitimacy_enabled` moves mean Z_obs
from 0.244 (disabled) to 0.492 (enabled). Both effects are large. Stage
9's own structural-fact audit explains why: `performance_legitimacy` is
literally one of S_obs's five averaged components, and `procedural_
legitimacy` is literally one of Z_obs's three averaged components
(`observer/sz_obs.py`'s own disjoint construction) — so a legitimacy
channel that is disabled (target and update logic both inert) drags the
corresponding composite DOWN by construction, not purely through an
independent behavioral mechanism. **Independent of entrenchment** does
hold in the narrow sense that the effect appears at every entrenchment
level in Stage 3's factorial (not entrenchment-conditional), but
"independent" should not be read as "behaviorally novel" — a
substantial share of this effect is the composite-index arithmetic
itself. Stage 6's `legitimacy_history_only` intervention (resetting
accumulated legitimacy scores, not disabling the channel) shows the
effect IS transient once the channel stays active and enabled
throughout: middle-window gap ≈0.009, final-sustained gap ≈4×10⁻¹²
(numerically zero) — the accumulated legitimacy SCORE resets but is
fully re-earned from ongoing behavior within a few hundred steps, in
sharp contrast to `entrenchment_only`'s persistent 0.072 final gap.
Both pieces are reported: legitimacy enablement changes the composite
substantially (partly by construction); legitimacy HISTORY specifically
does not persist the way pressure-memory or entrenchment history does.

## H7 — fresh replication

*"Whatever structure Stage 4's discovery finds, generalizes to Stage
8's disjoint fresh confirmation at better than Level 1.3's own
-1.29-vs--6.05 generalization gap."*

**Supported by the letter of the comparison, though the underlying
signal is genuinely different in kind from Level 1.3's own finding, and
that difference matters for H8/the decision gate below.** Stage 8's
96-run disjoint fresh confirmation (fresh LHS design seed, fresh
simulation seed range, never overlapping Stage 4's own 240 points)
scores Stage 7's frozen k=1 and k=8 GMM fits on fresh, standardized
data: null k=1 per-run log-likelihood = -7.82; leading k=8 per-run
log-likelihood = -4.71; gap (k8 − k1) = **+3.11**, a POSITIVE gap,
meaning the 8-component structure fits fresh data measurably better
than the no-structure baseline. This clears the letter of H7's own bar
(better than Level 1.3's own -1.29-vs--6.05, which was a large NEGATIVE
generalization failure). But this positive gap is a comparison against
a deliberately weak baseline (a single Gaussian, k=1) — it says an
8-component mixture is a better DENSITY estimate than one Gaussian,
which is close to mechanically guaranteed for any non-Gaussian
continuous cloud of points and does not, on its own, distinguish
genuine discrete family structure from a flexible continuous density
approximated by many components. The frozen continuous candidate
(`pca_factor_continuum`) generalizes comparably well: reconstruction
error on fresh data is 0.618, barely above its own in-sample training
error of 0.597 (a ~3.5% increase) — so BOTH the leading discrete and
the leading continuous candidate replicate reasonably on fresh data
this milestone, unlike Level 1.3's own sharp discrete-model collapse on
fresh data. H7 is reported as supported on its literal comparison, with
this important qualification carried into H8/the decision gate rather
than left implicit.

## H8 — discreteness

*"The discovered structure is genuinely discrete (beats every
continuous alternative on fresh data per Stage 7's rule) — explicitly
allowed to fail even if H1-H7 all hold."*

**Not supported — the weight of evidence leans continuum, and this
hypothesis was explicitly licensed to fail.** Despite H7's positive
generalization gap (above), five independent, converging signals argue
against genuine discreteness at k=8:

1. **BIC has not converged within the tested range.** BIC for
   `gmm_k1_to_8` is non-monotonic across k=1..8 and drops sharply and
   without turning upward at the tested boundary: 1214.3 (k=7) → 538.2
   (k=8), the single largest drop in the whole sequence, right where
   the search stopped. A genuine discrete-family structure typically
   shows BIC turning back UP past the true k; this pattern instead
   looks like a flexible density estimator still improving as more
   components are added — the signature of approximating a continuous,
   non-Gaussian density, not of discovering separated families.
2. **Silhouette never clears a moderate bar.** 0.055-0.143 across
   k=2..8, well below what a genuinely well-separated multi-modal
   structure would typically show.
3. **HDBSCAN, a density-gap-requiring method, finds little to
   nothing.** At its own leading, most permissive setting
   (`min_cluster_size=6`), HDBSCAN finds only 2 clusters with 99/240
   (41%) of points labeled noise; at `min_cluster_size≥12`, it finds
   zero clusters (100% noise). A genuine density gap between discrete
   families would show up as a much cleaner HDBSCAN partition even at
   its most conservative settings.
4. **Cross-algorithm agreement is weak once the trivial pair is
   excluded.** `gmm_k1_to_8` vs. `unequal_covariance_mixtures` agree
   perfectly (ARI=1.0) but this is not independent corroboration — both
   reduce to the identical k=8, `covariance_type="full"` fit. Every
   OTHER pair (`gmm` vs. `hierarchical`: 0.032; `gmm` vs. `hdbscan`:
   0.357; `hierarchical` vs. `hdbscan`: 0.016) shows weak-to-negligible
   agreement — different algorithms looking at the same 240 points do
   not converge on the same partition.
5. **The partition does not reproduce across ecological strata.**
   Fitting the leading method independently within each of the three
   ecological strata gives pairwise ARI of -0.043 to -0.014 —
   essentially zero-to-negative agreement, meaning the discovered
   structure is not a stable feature of the pool that survives being
   re-derived from a subset.

H8 is reported as NOT supported, consistent with Level 1.3's own prior
finding leaning continuum, though arrived at via a different specific
mechanism this time (a positive but weak generalization gap dominated
by BIC-boundary/silhouette/HDBSCAN/cross-algorithm/cross-stratum
evidence, rather than Level 1.3's own sharp fresh-cluster-assignment
collapse). Section 17/task #126's own decision gate weighs this
alongside H7's positive gap and every other stage's evidence to reach
the formal 8-way classification; this note states the evidence, not the
verdict.

## Nulls and anomalies, stated directly

- **`response_cost` (`contribution_amount`) had zero measurable effect**
  on bargaining activation across [0.02, 0.2] (Stage 2) — resources are
  already too deeply negative post-collapse for the ask size to matter;
  activation is driven by the interaction of `contribution_period_
  steps` and `sequencing_min_duration_steps`, not response cost. A
  disclosed null on one of Section 7's own licensed calibration levers.
- **`condition_rank_stability` returned a degenerate ±1.0 for every
  Stage 5 seed** — the diagnostic as specified assumes more than 2
  ranked conditions to be informative; with only `security_first` vs.
  `coevolution` compared, it collapses to a trivial same-or-reversed
  binary. Reported as a scope/diagnostic-design gap, not a finding.
- **`gmm_k1_to_8` vs. `unequal_covariance_mixtures` agree with ARI
  exactly 1.0`** — not genuine independent corroboration; both fits
  reduce to the same underlying model at the leading k. Flagged in H8
  above so it is not miscounted as a fifth independent line of
  agreement evidence.
- **Stage 9's equal-weight vs. PCA-weighted S_obs/Z_obs correlation
  roughly halves** (0.264 vs. 0.136) — the reported coupling is real
  but sensitive to the (deliberately simple, disclosed) equal-weighting
  choice `observer/sz_obs.py` already commits to; not redefined here,
  per Stage 9's own frozen rule, but flagged as a real sensitivity.
- **Stage 9's factor-structure analysis does not cleanly recover the
  S/Z axis split**: PC1 (22.8% of variance) is loaded by BOTH
  legitimacy channels together (0.654 `performance_legitimacy`, 0.674
  `procedural_legitimacy`) rather than one loading on an "S axis" and
  the other on a "Z axis" — the composite's own two-factor intuition is
  not what a data-driven PCA actually finds; the scree is flat
  (7 components between 7.7% and 22.8%, top-2 cumulative only 40.9%).

## Limitations, disclosed rather than hidden

- Every stage this milestone ran at a disclosed, session-budget-scaled
  sample size, stated as a MINIMUM in the frozen manifest, not the
  preferred scale (Stage 4: 240 of a preferred larger design; Stage 8:
  96 of a preferred 144-288).
- Stage 5's persistence classification and Stage 6's history-erasure
  intervention both operate at ONE representative cell
  (`entrenchment=moderate`, `legitimacy=dual`,
  `stratum=medium_feasibility`), not the full Stage 3 factorial — a
  disclosed scope reduction, not a claim that persistence/erasure
  effects are cell-invariant.
- `condition_rank_stability`'s degenerate behavior at only 2 ranked
  conditions (above) means H3's rank-stability diagnostic specifically
  did not deliver informative evidence this milestone, though the
  displacement/variance/slope diagnostics it accompanies did.
- H6's legitimacy-channel effect is substantially construction-driven
  (the channel is a literal component of the composite it is measured
  against) — reported plainly rather than framed as a purely
  independent behavioral discovery.
- Stage 9's S_obs-Z_obs coupling (H6-adjacent) is real but modest
  (r≈0.26) and roughly halves under an equally defensible PCA-weighted
  alternative to the milestone's own equal-weight convention.
