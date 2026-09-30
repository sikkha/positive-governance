# Level 1.3 Decision Gate Report — Section 23

**Status: renders the formal six-way classification, argued from the
Stage 0-9 evidence already on record in `docs/level1.3_scientific_
note.md` and `docs/level1.3_discovery_methods.md`. This document adds
no new run, no new number, and no new figure — it is a reasoning
document over evidence that already exists, per this milestone's own
governance that the classification be a separate, auditable step from
the build/results inventory (`docs/level1.3_completion_report.md`).**

## 1. The outcome space, restated exactly as preregistered

From `experiments/level13_preregistration.py::DECISION_GATE_OUTCOMES`,
frozen before any Stage 0-9 run:

| Label | Outcome |
|---|---|
| A | one_family — sequencing/pressure-history variation collapses to a single institutional family regardless of order |
| B | two_families — sequencing/pressure-history variation produces exactly two reproducible institutional families |
| C | four_or_more_families — four or more reproducible institutional families |
| D | continuum — no discrete clustering at all; a continuous gradient, not separable families |
| E | transient_differentiation — differentiation appears but does not persist/entrench; families converge again given enough steps |
| F | no_detectable_effect — no reproducible historical/sequencing effect is detected at all |

`DECISION_GATE_DO_NOT_PREFER = "E_transient_differentiation"`, scoped
explicitly by its own frozen note to mean the discovery pipeline's own
default must not be biased toward E — it does not mean E is
disqualified as a genuine finding if the evidence actually supports it.
No Stage 6-9 script special-cased or biased toward E; this report does
not either.

## 2. Ruling out A and F first — both directly contradicted by measured, nonzero effects

**A (one family) is ruled out.** Stage 3's 72-run factorial shows real,
nonzero variation in S_obs/Z_obs by pressure onset ORDER, holding
entrenchment and every other factor fixed. Mean S_obs by ordering
ranges from 0.514 (`security_pressure_bargaining_pressure_coordination_
complexity`) to 0.546 (`coordination_complexity_security_pressure_
bargaining_pressure`) — a modest but real ~6% relative spread across
all six orderings, none excluded or privileged in reporting. Mean
Z_obs ranges 0.199 to 0.214 across the same six orderings, a ~7.5%
relative spread. A "collapses to one family regardless of order"
reading would require this spread to be statistical noise around a
single value; six orderings with a consistent, ordering-correlated
spread (not scattered randomly) is evidence against that.

**F (no detectable effect) is ruled out.** Stage 5's 16 matched
seed-triples show real divergence under causal manipulation of the
same starting seed: mean |S_obs diff| erased-vs-base ≈ 0.0027,
reversed-vs-base ≈ 0.0116; mean |Z_obs diff| erased-vs-base ≈ 0.0019,
reversed-vs-base ≈ 0.0092. A minority of seeds (1/16 under erasure,
3/16 under reversal) show a detectable shift in the sequencing vector
itself, not just the phenotype composite. This is a real, if modest,
causal signal — not the null result F would require. Stage 6's own
`headline_k=2` (a k≥2 partition, not k=1) is a second, independent
piece of evidence against F: a purely-noise pooled dataset with no
historical effect would not reliably produce a k≥2 partition with
silhouette 0.334 well above the discovery pipeline's own effective
floor.

## 3. Ruling out C (four-or-more families)

Stage 6's own silhouette curve across k=1..8 —
`{2: 0.334, 3: 0.256, 4: 0.285, 5: 0.297, 6: 0.153, 7: 0.196, 8:
0.297}` — has no k≥4 that clearly and cleanly beats k=2. k=4's own
silhouette (0.285) is below k=2's (0.334), not above it. Nothing in
this curve resembles the profile a genuine four-or-more-family
structure would produce (a local silhouette peak at k=4 or higher,
comfortably clear of k=2/3). C is not supported by this milestone's
own discovery evidence.

## 4. The live question: B (two families) vs. D (a continuum)

This is where the actual evidence has to be weighed, not merely
inventoried. Both readings have real support:

**In favor of B**: `headline_k=2` is the clear single-metric leader
(silhouette 0.334, next-best 0.297 at k=5 — a real, if not huge, gap).
Bootstrap stability is high (`mean_ari ≈ 0.917`, 30 resamples) —
the k=2 partition itself is highly reproducible under resampling of
the same pooled data.

**In favor of D**: cross-algorithm agreement is only modest
(`mean_algorithm_agreement_ari ≈ 0.291`) — gmm and hierarchical do not
strongly agree with each other, and hdbscan (a density-based method,
which specifically requires a genuine density GAP between clusters to
find any structure at all) found **zero** clusters, labeling all 216
points as noise. A density-based method finding no gap is a direct,
mechanistic signal consistent with a continuous gradient rather than
two well-separated modes. Stage 7's fresh confirmation reinforces this:
all 12 fresh, never-before-seen points were assigned to the SAME
(larger, 144/216) cluster, with a large, disclosed generalization gap
(mean log-likelihood per point ≈ -1.29 on the training pool vs. ≈
-6.05 on fresh points) — if the k=2 partition reflected two genuinely
distinct, roughly-equally-likely institutional families, an
independently-drawn LHS sample would be expected to land in both
clusters at least occasionally, not unanimously in one. Stage 8's
pooled S_obs-Z_obs relationship is a third, suggestive (not decisive)
data point in the same direction: a strong, smoothly monotonic
correlation (Pearson r ≈ 0.888, Spearman ρ ≈ 0.913) across 228 pooled
runs is more consistent with one continuous, tightly-coupled
capacity/constraint gradient than with two discrete regimes that would
be expected to show as separated modes in the same scatter.

**Applying a fixed, non-invented threshold rule rather than judgment
alone.** To avoid resolving B-vs-D by unaided judgment (which risks
motivated reasoning toward whichever outcome reads better), this
report applies the exact same three-part operationalization Level
1.2b's own `classify_discovery_verdict` (Work Package K, Section 16)
used on its own structurally analogous pooled-clustering evidence —
the same 0.3 stability bar, the same 0.15 silhouette floor, and the
same "three-or-more evaluated k's within 0.05 silhouette of the best →
continuum" rule — rather than devising a new rule for Level 1.3 that
could be tuned toward a preferred answer. Level 1.3 itself never froze
a formal classifier function of its own (a disclosed scope difference
from Level 1.2b, stated here rather than silently patched over by
writing one now, after the data is in hand); reusing Level 1.2b's own
already-frozen thresholds, unmodified, is the closest available
substitute for a rule fixed in advance.

Stability: bootstrap ARI (0.917) clears 0.3 — passes. Silhouette
floor: k=2's 0.334 clears 0.15 — passes (rules out `one_config`).
Continuum test: is the best silhouette (0.334, k=2) within 0.05 (i.e.,
≥0.284) of at least three other evaluated k's? `k=4` (0.285): yes.
`k=5` (0.297): yes. `k=8` (0.297): yes. `k=3` (0.256) and `k=6`
(0.153) and `k=7` (0.196): no. **Three other k's clear the 0.05 band**
— under Level 1.2b's own unmodified rule, this is a **continuum**
verdict, not `multi_config`/two-families, despite k=2 being the
nominal single-best headline pick.

## 5. Verdict: D — continuum

**D_continuum** is this report's formal Section 23 classification,
reached via the mechanical rule in §4 rather than the qualitative
reading in §4 alone (which was itself already leaning the same
direction), corroborated by Stage 7's fresh-data behavior and Stage
8's unimodal correlation pattern. **B_two_families is the closest
runner-up**, not a rejected alternative — `headline_k=2`'s real
silhouette lead and high bootstrap stability are genuine, disclosed
findings, and a reader who weights the single-best-k reading over the
three-way-tie reading could reasonably land on B instead. This report
commits to D because it is the reading a fixed, non-invented,
previously-established threshold rule actually produces, not because D
was preferred going in.

## 6. E (transient differentiation) — explicitly addressed, not silently dropped

No Stage 6-9 script built a direct within-run temporal-persistence
diagnostic (an analogue of Level 1.2b's own `temporal_window_
stability_ari`, comparing early-run vs. late-run cluster assignment) —
a disclosed scope gap, not a finding. E can therefore not be either
confirmed or ruled out on direct temporal evidence here. Two indirect,
disclosed-as-indirect considerations bear on it: Work Package C's
entrenchment mechanism, confirmed to have a real (if modest — mean
matched-seed |S_obs diff| ≈ 0.031, |Z_obs diff| ≈ 0.018 across the 36
matched pairs in Stage 3) effect when enabled, is mechanistically a
force AGAINST convergence-over-time (entrenchment makes an existing
configuration harder to change the longer it persists, by
construction — the opposite of a force that would pull differentiated
runs back together); and Stage 9's scale/shock robustness grid (24
runs, repeated-shock pressure histories rather than a single pulse)
found S_obs/Z_obs qualitatively stable across all four scale cells
(S_obs in [0.649, 0.710], Z_obs in [0.438, 0.470]) — i.e., differentiation
that does exist does not visibly wash out under repeated, sustained
shocks either. Neither point is a formal persistence test; both are
stated as suggestive, not dispositive, exactly the caution
`DECISION_GATE_NOTE` requires. This report's own classification (D)
does not depend on ruling E out — D and E are not mutually exclusive
readings of the same evidence in general, but nothing in this
milestone's own data positively supports E over D, so D is reported as
the verdict, with E's own evidentiary gap disclosed rather than quietly
resolved either way.

## 7. What would change this verdict

Stated for anyone auditing or extending this milestone: a future run
that (a) builds a genuine within-run temporal-persistence diagnostic
and finds early/late cluster assignment diverging systematically would
bear directly on E; (b) substantially increases Stage 6's pooled n
(216 is a modest discovery-pipeline sample by Level 1.2b's own 576-run
precedent) could sharpen or overturn the B-vs-D reading in either
direction; (c) runs a purpose-designed (not pooled-post-hoc) discovery
design, removing the `cluster_vs_source_stage_ari ≈ 0.554` confound
disclosed in `docs/level1.3_discovery_methods.md` §3, would be the
single strongest test of whether the k=2 structure is a genuine
historical-sequencing effect or partly an artifact of which stage a
run happened to come from. None of these were within this milestone's
own disclosed session-budget scope; all three are stated here as
concrete, falsifiable next steps rather than left implicit.
