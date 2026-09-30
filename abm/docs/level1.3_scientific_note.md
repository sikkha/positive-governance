# Level 1.3 — Scientific Note

**Status:** written after Stages 0-9 completed. This note reports what the
Stage 0-9 experimental program actually found — descriptively, per each
stage's own preregistered scope. It does **not** render the Section 23
six-way decision-gate verdict; that synthesis is task #108's own job, and is
recorded separately in `docs/level1.3_decision_gate_report.md` once written.
Every number below is read directly from the committed `outputs/level13_*`
JSON files, not asserted from memory.

---

## 1. The question

Can different temporal orderings of security pressure, bargaining pressure,
and impersonal coordination pressure generate persistent, reproducible
institutional differentiation in the Level 1.2b substrate? Section 23
requires this milestone to remain capable of finding one family, two,
four-or-more, a continuum, transient differentiation, or no detectable
historical effect at all.

## 2. Stage 0-1: does the machinery work, and is it a true no-op when off?

Stage 0 (20 matched seeds, two comparisons): the historical module gate is a
byte-for-byte no-op when every Level 1.3 sub-flag is off, from both a bare
Level 1.0 baseline and the full Level 1.2b frozen-reference baseline —
`overall_pass=True`, 0/20 mismatches on both comparisons.

Stage 1 (8 seeds x 7 conditions): every one of the 7 master activation flags
(3 pressure channels, entrenchment, 2 legitimacy channels) produces its own
claimed effect when on and none when off — all checks pass.

## 3. Stage 2: ecological feasibility calibration

30-point Latin Hypercube design over the ecological parameter space (Level
1.3 introduces no new ecological field of its own): tercile cut points
froze at `low_cut=3.393`, `high_cut=6.557`, stratum counts `{low_feasibility:
11, medium_feasibility: 10, high_feasibility: 9}`.

## 4. Stage 3: does pressure ORDER matter, with entrenchment on/off?

72 runs (all six permutations of security/bargaining/coordination-complexity
onset order x entrenchment on/off x 6 seeds), on the corrected
`level12b_frozen_reference()` substrate with transmission channels active.
All manipulation checks passed. S_obs and Z_obs both vary by ordering (see
`outputs/level13_figures/04_stage3_by_ordering.png`) — no ordering was
excluded or privileged in reporting; all six are shown identically.
Entrenchment's own matched-seed effect (on vs. off, pooled across all six
orderings) is visible in `05_stage3_entrenchment_effect.png`.

## 5. Stage 4: open pressure-history search

96 runs (24 LHS points x 4 seeds, 9-dimensional continuous search over each
channel's own onset/magnitude/duration), entrenchment and both legitimacy
channels held on throughout. Raw sequencing and phenotype vectors recorded
for Stage 6's pool; no standalone verdict drawn at this stage.

## 6. Stage 5: causal historical counterfactuals

16 matched seed-triples (base / pressure-erased-from-onset / pressure-order-
reversed), single-channel (`security_pressure` only, by design — see that
stage's own module docstring for why single-channel sidesteps Work Package
E's own disclosed multi-channel RNG-draw-skew limitation). Real,
non-trivial divergence: mean |S_obs diff| erased-vs-base ≈ 0.0027,
reversed-vs-base ≈ 0.0116; mean |Z_obs diff| erased-vs-base ≈ 0.0019,
reversed-vs-base ≈ 0.0092. Sequencing-vector identity: 15/16 seeds
unchanged under erasure, 13/16 unchanged under reversal — i.e. a minority of
seeds (1 and 3 respectively) show a detectable sequencing-vector shift under
the counterfactual manipulation. This is a real but modest causal signal at
this scale, reported as such — not amplified, not dismissed.

## 7. Stage 6: blind phenotype discovery

216 pooled runs (Stage 3+4+5's own phenotype vectors, Level 1.2's clustering
pipeline reused unmodified). `headline_k=2` (silhouette 0.334 — the clear
leader, though not sharply separated from k=5 at 0.297). Bootstrap stability
mean ARI 0.917 (std 0.216 — high but with real seed-to-seed variance).
Cross-algorithm agreement (gmm/hierarchical/hdbscan) mean ARI only 0.291 —
the three methods agree only modestly with each other. `cluster_vs_source_
stage_ari = 0.554` — the discovered structure correlates moderately with
which of Stage 3/4/5 a run came from; it is not a pure pooling artifact
(ARI would be much higher), but the correlation is not negligible either.
hdbscan found 0 clusters (all 216 points labeled noise) at its default
`min_cluster_size` — reported honestly. `seq_bargaining_participation` was
NaN across all 216 pooled runs.

## 8. Stage 7: fresh confirmation

12 fresh runs (never-reused seeds, Stage 4's own LHS machinery), scored
against Stage 6's frozen fit. All 12 fresh points were assigned to the
larger of Stage 6's two clusters (144/216 training runs, vs. 72/216 for the
other). Mean log-likelihood per point: training pool ≈ -1.29, fresh points
≈ -6.05 — a real, disclosed generalization gap. Fresh data scores
substantially worse under the frozen model than the data it was fit on,
consistent with this milestone's standing commitment to remain capable of
finding a weak or absent effect rather than assuming confirmation.

## 9. Stage 8: S_obs-Z_obs mapping

228 pooled runs (Stage 3+4+5+7). Pooled S_obs-Z_obs correlation is strong
and positive: Pearson r ≈ 0.888 (p ≈ 2.4e-78), Spearman ρ ≈ 0.913 (p ≈
3.8e-90). The median-split joint table is strongly diagonal: 100 high-S/
high-Z, 100 low-S/low-Z, vs. only 14+14 off-diagonal cells — the two
observer-side composites move together far more than independently across
this substrate. This is a substantive, disclosed finding: whatever
differentiation this milestone finds or does not find, it is not a
differentiation that decouples S_obs from Z_obs.

## 10. Stage 9: scale and shock robustness

24 runs (population {40, 80} x n_patches {3, 6} x 6 seeds), every channel
using `"repeated_shocks"` rather than a single clean pulse. All manipulation
checks passed. Mean S_obs/Z_obs held qualitatively stable across all four
scale cells — S_obs in [0.649, 0.710], Z_obs in [0.438, 0.470] — no cell
diverging sharply from the others.

## 11. What this body of evidence suggests, held loosely

Taken together: (a) pressure ordering and history shape produce measurable,
non-zero variation in institutional response (Stages 3-5), (b) that
variation clusters into roughly two groups under a blind pipeline, with
moderate (not high, not negligible) stability and only modest cross-
algorithm agreement (Stage 6), (c) the two-cluster structure generalizes
weakly to genuinely fresh data — it predicts a single dominant cluster
rather than splitting fresh points the way the training pool split (Stage
7), (d) S_obs and Z_obs are strongly correlated rather than independent
axes (Stage 8), and (e) the qualitative picture is stable across scale
(Stage 9). This pattern is most consistent with the milestone's own "two
family" or "continuum" decision-gate outcomes being live candidates, with
"one family" and "no detectable effect" both directly contradicted by the
nonzero Stage 5 counterfactual shifts and Stage 3 by-ordering variation, and
"four-or-more families" not well supported by Stage 6's own silhouette
curve (k=2 is the clear leader, not one of several close contenders). This
is an informal reading of the evidence, not the decision-gate classification
itself. `docs/level1.3_decision_gate_report.md` (Section 23) has since been
written and renders the formal verdict — **D, a continuum** — reached by
applying Level 1.2b's own unmodified discovery-verdict threshold rule to
Stage 6's numbers rather than by unaided judgment; B (two families) is that
report's own disclosed closest runner-up, not a rejected alternative. This
section's informal reading above is left as originally written rather than
edited to match, per this project's "preserve prior content" precedent.
