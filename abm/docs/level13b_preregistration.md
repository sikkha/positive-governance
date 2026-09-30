# Level 1.3b Preregistration (Section 16)

**Status: frozen. Everything a Stage 3+ run depends on is committed
here BEFORE any of those runs execute, per Section 16's own requirement.
The machine-readable manifest is `experiments/level13b_preregistration.
py` (`build_manifest`/`manifest_hash`/`write_manifest`/`load_and_verify_
manifest`, mirroring Level 1.3's own `experiments/level13_
preregistration.py` exactly), frozen to `outputs/level13b_preregistration/
manifest.json` with a SHA-256 hash in `manifest_hash.txt`. This document
is the human-readable summary of that same frozen content — every
number below is read directly from the manifest, not independently
asserted.**

## 1. Disclosed provenance note

Section 18's exact hypothesis wording and Section 19's exact eight-way
decision-gate wording are not recoverable verbatim in this session
(the governing specification was pasted once, at length, in an earlier
turn, and only a compacted summary of it survived this session's own
context compaction). `HYPOTHESES` and `DECISION_GATE_OUTCOMES` in the
manifest are reconstructed at the level of outline/content that summary
preserved, disclosed as reconstructed rather than transcribed — the
same disclosed situation this project has already handled twice before
(`observer/sequencing_diagnostics.py`'s two disclosed dimension
definitions; `experiments/level13_preregistration.py`'s own decision-
gate provenance note). Everything else in this document (the Work
Package B/C findings, the Stage 3-9 design commitments) is either
directly computed this session or newly designed against the Section
6-15 summaries, not reconstructed from a lossy source.

## 2. Bargaining calibration (Work Packages B + C, frozen)

`contribution_amount=0.2`, `contribution_period_steps=10`,
`sequencing_min_duration_steps=10` — **the untouched Level 1.1/1.2b
defaults**. No generative parameter was changed. Work Package B's
observer-construction fix (`docs/level1.3b_bargaining_activation_
audit.md`) is, by itself, sufficient: at these defaults,
`bargaining_participation` activates in **exactly 0.5 of eligible runs
in all three ecological strata** (`outputs/level13b_stage2_bargaining_
calibration/calibration_report.json`). Response cost was swept down to
0.02 with zero measurable effect (disclosed null result, not hidden);
participation frequency and sustained-crossing duration's interaction
is what actually governs activation. This calibration is what Stage 3
onward uses.

## 3. Ecological strata (reused, not redrawn)

One representative point per stratum from Level 1.3's own already-
frozen 30-point Stage 2 design (`outputs/level13_stage2_calibration/
design.json`): `low_feasibility`=point 0, `medium_feasibility`=point 2,
`high_feasibility`=point 1.

## 4. Stage 3 (Work Package E): matched sequencing factorial

**Factors**: pressure ordering (`security_first`, `bargaining_first`,
`coevolution` — three named onset patterns, not all six permutations)
x entrenchment (`off`/`moderate`/`strong`, via `entrenchment_
maturation_steps` at ∞-equivalent-off/150/50) x legitimacy (`neither`/
`performance_only`/`procedural_only`/`dual`) x ecological stratum
(low/medium/high) = **108 cells**, 2 seeds/cell = **216 runs declared**.
Every cell shares matched cumulative pressure-onset exposure by
construction (the three onset slots {0, 150, 300} used exactly once
each for the two named-order conditions; all three at onset 0 for
`coevolution`). Required contrasts are computed WITHIN matched
entrenchment/legitimacy/stratum cells across the three orderings only —
never pooled across cells differing on those factors. Uncertainty:
seed-clustered bootstrap CIs (resampling whole seeds), raw matched
differences always reported alongside.

## 5. Stage 4 (Work Package D): homogeneous discovery

One purpose-designed, space-filling Latin Hypercube design over 11
dimensions (three pressure onsets, magnitude, duration, overlap,
volatility, entrenchment strength, two legitimacy sensitivities,
ecological stratum) — **48 points x 5 seeds = 240 runs declared**,
disclosed as Section 8's own stated minimum, not the preferred
72-96 x 6-8. Every point shares identical run length (500 steps),
population (40), patches (4), init conditions, observer window,
eligibility rule, phenotype construction, and missingness treatment.
No counterfactual reruns enter this pool — Stage 6 is a separate
dataset entirely.

## 6. Stage 5 (Work Package F): temporal persistence

Windows as fractions of run length: early [0.0, 0.2], middle
[0.4, 0.6], late [0.8, 1.0], final-sustained [0.9, 1.0].
`observer/historical_persistence.py` (to be created, task #118) will
compute early→middle and middle→late displacement, late-window
variance, a convergence/divergence slope, cluster-assignment stability
across windows, trajectory distance, and persistence after
removal/reversal/equalization of pressure — classifying each run as
pressure-dependent response, historical hysteresis, entrenched path
dependence, transient differentiation, or no detectable differentiation.
Never from final-step values alone.

## 7. Stage 6 (Work Package G): history erasure

Six matched interventions: pressure-memory-only, legitimacy-history-
only, entrenchment-only, all-history, a **sham** (identical-state copy —
proves the serialization/copy machinery itself is a byte-identical
no-op before any other intervention's divergence is trusted as
historically meaningful), and a no-intervention control. All six
preserve current visible structure, resources, ecology, and network —
only history itself is erased. 12 seeds x 6 interventions = 72 runs
declared. Measures trajectory divergence across every window, not final
S_obs/Z_obs alone.

## 8. Stage 7 (Work Package H): discrete vs. continuous vs. path-dependent

Discrete candidates (GMM k=1-8, hierarchical, HDBSCAN at multiple
`min_cluster_size` settings, unequal-covariance mixtures) vs. continuous
candidates (PCA/factor continuum, principal-curve/manifold, low-
dimensional regression) vs. path-dependent candidates (predicting late
phenotype from early sequence with no discrete clustering at all) —
compared on held-out likelihood, reconstruction error, predictive
performance, and stability across bootstrap/algorithm/point/seed/
temporal-window/ecological-stratum/missingness-strategy. No k chosen
from silhouette alone; a discrete result must beat every continuous
alternative on Stage 8's fresh data to count as discrete.

## 9. Stage 8 (Work Package I): fresh confirmation

**24 points x 4 seeds = 96 runs declared** — Section 13's own stated
minimum. Disjoint design and simulation seeds from every prior stage;
frozen preprocessing, phenotype fields, observer thresholds, and the
clustering/manifold model selected in Stage 7; no refitting and no
post-hoc parameter selection before primary scoring.

## 10. Stage 9 (Work Package J): S_obs/Z_obs measurement audit

Tests whether the strong Level 1.3 coupling (Pearson r≈0.888,
Spearman ρ≈0.913) reflects genuine coupling, shared construction, a
common ecological driver, common normalization, activity-volume
confounding, presence/absence confounding, or measurement overlap — via
raw and partial correlations (controlling ecological stratum),
within/between-point correlation, factor structure, and equal-weight/
leave-one-out/non-normalized/opportunity-denominated variants. Axes are
never redefined to manufacture independence; a measurement-induced
finding is corrected transparently, versioned, with both variants
preserved.

## 11. Work Package K: ecological accounting continuation

Level 1.2b's exact accounting/feasibility machinery, unmodified. Every
run reports the full outcome ledger; collapse runs are retained, never
discarded; the complete outcome ledger and the institutionally-eligible
analysis denominator are kept distinct; results reported pooled,
by-stratum, eligible-only, and with collapse counted as an outcome.

## 12. Hypotheses (H1-H8)

Eight falsifiable hypotheses spanning bargaining activation, ordering
effects, temporal persistence, entrenchment moderation, causal history
effects, legitimacy-channel effects, fresh-data replication, and
discreteness — the full statements are in `experiments/level13b_
preregistration.py::HYPOTHESES`. **H8 (discreteness) is explicitly
allowed to fail even if H1-H7 all hold** — Level 1.3's own evidence
already leans continuum, and this milestone does not require a discrete
result to count as a success.

## 13. Decision gate (eight-way)

| Label | Outcome |
|---|---|
| A | no_effect |
| B | pressure_responsive_nonhistorical |
| C | transient |
| D | persistent_continuum |
| E | two_families |
| F | three_families |
| G | four_or_more_families |
| H | inconclusive |

`DECISION_GATE_DO_NOT_PREFER = "F_three_families"` — governs the
discovery pipeline's own default only, exactly as Level 1.3's own
"do not prefer E" governed transient differentiation there; every
outcome, F included, remains legitimate if the data support it.
Family-to-dissertation-trajectory mapping is deferred until AFTER
Stage 4 (blind discovery), Stage 8 (fresh confirmation), and Stage 9
(S_obs-Z_obs audit) are all frozen.

## 14. RNG, frozen references, and the stopping rule

`rng_mode="mechanism_substreams"` mandatory for every Stage 0/3-10 run;
every new stochastic operation gets its own registered substream. Two
frozen references: Level 1.2b with every Level 1.3 historical mechanism
off (byte-identical to Level 1.2b itself), and the corrected (post-task-
#109-fix) Level 1.3 configuration. This milestone will not begin Level
1.4, will not modify the paper repository, and will not silently
promote Level 1.3's own continuum verdict to an established finding —
the final report must state bargaining-repair status, sequence-effect
significance, equalization survival, entrenchment moderation, erasure
reduction, discrete-vs-continuous generalization, fresh-confirmation
support, the S_obs/Z_obs coupling's nature, the exact decision-gate
outcome, nulls, anomalies, limitations, exact test/run counts, and the
next recommended decision — and succeeds even on a null, transient,
nonreplicating, continuous, or inconclusive finding.
