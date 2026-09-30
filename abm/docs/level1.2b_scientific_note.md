# Level 1.2b Scientific Note — Ecological Feasibility Envelope and Powered Blind Institutional-Phenotype Rediscovery

See `docs/odd_level1.2b_addendum.md` for the model description,
`docs/level1.2b_discovery_methods.md` for the full discovery
methodology, and `docs/level1.2b_completion_report.md` for the
completion-gate audit. This note reports what Work Packages A-O's
experimental program actually found.

## Required non-tuning statement (quoted verbatim)

Per this milestone's own governing discipline (Sections 2, 20, 27.9),
the following statement — the standing prohibition against
post-result retuning this milestone committed to before Work Package A
began — is quoted here **verbatim**, exactly as recorded at the top of
this session's own preflight log entry
(`dev_mem/status_update.md`, "2026-08-18 (session 10, start) — Level
1.2b preflight"), which itself restates the governing specification's
Sections 2/20/27.9:

> **Prohibition against post-result retuning (Section 2, 20, 27.9),
> restated as a standing rule for this entire milestone:** ecological
> bounds may be revised at most once, with a new preregistration
> version, an explicit stated reason, and the original results
> preserved unmodified — never because a revision would produce a more
> interesting governance-phenotype result. Recurrence criteria, once
> audited and frozen (Work Package H, before discovery), may not be
> changed after seeing discovery results. If discovery supports zero
> candidates, confirmation exists to replicate that null with the
> frozen pipeline, not to be skipped or reweighted until a candidate
> appears.

Every finding below was produced under this rule: no ecological bound,
recurrence criterion, discovery threshold, or confirmation design
element was revised after any result was seen. The one instance where
a result could plausibly have motivated a change — Work Package K's
`continuum` verdict, which is neither a clean `multi_config` finding
nor a clean `one_config` null — was handled exactly as the rule
requires: treated as a no-candidate outcome for confirmation purposes
(see `docs/level1.2b_discovery_methods.md` §6), not as an invitation
to redefine "candidate" until one could be named.

## Headline finding

**No recurrent, discrete institutional-phenotype structure was
independently supported at this milestone's much larger, ecologically-
stratified scale.** Work Package K's blind discovery run (n=576 pooled
runs, more than 20× Level 1.2's own 24-run sample) reached a
`continuum` verdict — `headline_k=4`, but silhouette stays roughly
flat across several k's rather than peaking sharply on any one, so
this milestone reports a continuum rather than forcing a discrete-
cluster claim. Work Package L's prospective confirmation, on a fresh,
disjoint 384-run pool with fresh seeds, produced `confirmation_
verdict = null_replicated`: the independent replication landed on
`headline_k=2` (not 4) and verdict `unstable` (neither bootstrap nor
algorithm-agreement ARI cleared the 0.3 stability bar) — never
`multi_config`. Work Package O's synthesis classifies the milestone's
overall result as **`continuum`**, directly inherited from Work
Package K's own verdict per its own explicit composition rule, and
assigns **no "attractor" label anywhere** (population-fraction
recovery was 0% across all 32 Work Package M scaling runs; the
attractor label requires majority recovery on both tracked
dimensions, and population's own 0% alone rules it out).

This extends, rather than contradicts, Level 1.2's own finding
("no recurrent institutional phenotype configuration was independently
supported at this milestone's disclosed scale") to a dataset roughly
24× larger and explicitly stratified to avoid the collapse-floor
sampling artifact that limited Level 1.2's own conclusions. The answer
did not change with scale and stratification; the milestone's evidence
for it is now substantially stronger.

## The collapse dynamic, characterized in depth

- **Work Package J** (576-run main pool): `collapse=326, viable=161,
  fragmented=89` — collapse is the plurality outcome. Failure-
  trajectory: most collapse (305/326) was `sustained_collapse`, not a
  last-instant artifact (`late_onset_collapse=21`,
  `transient_dip_recovered=56`).
- **Work Package L** (384-run confirmation pool): `collapse=245,
  viable=86, fragmented=53` — the same pattern replicates on fresh
  data (`failure_transition_rate=0.742`).
- **Work Package M** (32-run scaling grid): `collapse=25,
  fragmented=4, viable=3` — collapse remains dominant even at smaller,
  structurally-varied scales. Population-fraction shock recovery was
  **0/32** (false for every run, at every scale tested); ecological-
  fraction shock recovery was 28/32 (87.5%) — a genuine, disclosed,
  scale-dependent dissociation between the two recovery dimensions
  (Section 18 explicitly does not require scale invariance).
- **Work Package N** (13-factor, 208-run causal decomposition):
  collapse probability is causally movable by specific factors, not
  fixed. Largest ecological-fraction effects: `subsistence` (+0.198;
  collapse probability drops from 1.00 to 0.62 under high subsistence
  cost — counterintuitive at first glance, and reported as-is, not
  reinterpreted), `migration_on_off` (−0.110; migration ON worsens the
  ecological outcome, collapse rises from 0.38 to 0.88, replicating
  Level 1.2's own Section 13 migration-collapse finding at 1.2b's
  larger scale), `migration_congestion`/`patch_regen` (~+0.11 each).
  Smallest: `transmission_cost` (−0.002, 0/8 outcome-label
  transitions) — the institutional-transmission-probability lever
  shows essentially no causal effect on collapse in this design.

## Why the discovery result is a continuum, not a null-versus-something dichotomy

Two disclosed methodological findings, surfaced by Work Package R's
own synthetic ground-truth validation of the discovery pipeline
(`tests/test_level12b_discovery_synthetic_ground_truth.py`), bear
directly on how to read the `continuum` verdict:

1. At inadequate sample size, pure-noise data can present a spurious
   near-continuum silhouette signature — resolved by confirming Work
   Package K's actual n=576 pool is comfortably large enough to avoid
   this artifact (a synthetic pure-noise test at n=576 correctly reads
   `unstable`, never `multi_config`).
2. **Silhouette-based model selection alone cannot distinguish a
   genuine discrete k=2 cluster structure from a single dominant
   bisection of a smooth, gap-free continuum** — both produce a
   statistically identical single-peaked silhouette curve. This is why
   Work Package K's own `continuum` verdict (flat silhouette across
   several k) is read as evidence of gradedness, while a hypothetical
   sharp `multi_config` verdict from this pipeline alone would still
   not, by itself, prove discrete structure — consistent with, and the
   direct motivation for, Work Package O's cautious-vocabulary
   discipline (never `confirmed` from clustering evidence alone; see
   `docs/level1.2b_recurrence_audit.md`).

## What was NOT found (stated explicitly, per the milestone's own discipline)

- No discrete, well-separated institutional-phenotype candidate was
  named, bounded, or confirmed anywhere in this milestone's output.
- No "attractor" label was assigned anywhere (Work Package O,
  Section 20's own discipline — direct basin/perturbation/return
  evidence would be required, and population-fraction recovery
  evidence argues directly against it).
- `shared_lineage_persistence` (one of Section 20's six candidate
  explanations for cross-run similarity) was **not evaluated** — it
  would require a fourth full 576-run re-simulation to recover
  per-run lineage identity, which Work Package O judged low-value
  given that Work Package K's own `continuum` verdict and Work Package
  L's `null_replicated` confirmation already establish that no
  discrete, well-separated candidate structure exists to explain via
  shared ancestry in the first place. Disclosed as an evidence gap in
  Work Package O's own saved report (`shared_lineage_persistence.
  evaluated = false`), not silently omitted.

## Per-explanation evidence for cross-run similarity (Work Package O)

Of Section 20's six candidate explanations for observed cross-run
similarity: `temporary_similarity` — CONSISTENT (`temporal_window_
stability_ari=0.141`, well below the 0.3 bar — phenotype cluster
membership is not stable across a run's own duration);
`independent_structural_convergence` (proxy, not a literal lineage
test) — CONSISTENT (`assignment_stability_ari=0.527` clears the 0.3
bar); `environmentally_forced_similarity` — CONSISTENT for the three
substantial clusters (distinct-joint-point fractions 0.13/0.30/0.41,
all below the 0.5 diversity floor — cluster membership correlates with
shared institutional/ecological parameter points more than chance
diversity would predict); `measurement_compression` — AGAINST (5 of 11
raw PCA components needed to reach 90% explained variance); `failure_
state_similarity` — AGAINST (`cluster_vs_failure_proxy_ari=0.0`);
`shared_lineage_persistence` — not evaluated (see above).

## Statistical robustness of the null result (Work Package Q)

The clustering fit underlying Work Package K's own headline result was
re-checked with a genuine seed-clustered bootstrap (resampling whole
`joint_point_id` groups, correctly accounting for multiple seeds
nested within each parameter point, rather than treating every seed-
row as an independent draw): seed-clustered mean_ari=0.591 (n_clusters
=48) vs. the flat bootstrap's own mean_ari=0.598 — close agreement,
confirming the original result was not an artifact of the flat
bootstrap's less conservative resampling unit. Bootstrap 95%
confidence intervals were added to previously point-estimate-only
figures: Work Package J's collapse fraction 0.566 [0.526, 0.608]
(n=576); Work Package M's population-recovery rate 0.0 [0.0, 0.0]
(n=32 — a tight zero-width interval, itself informative); ecological-
recovery rate 0.875 [0.75, 0.97]. All four pooled run sets (Work
Packages E, L, M, N) were verified to use pairwise-disjoint seeds.

## Summary, in the milestone's own closing vocabulary

**`continuum`** — discovery did not identify discrete, well-separated
recurrent institutional-phenotype classes; the phenotype space instead
varies smoothly, without a clear small-k grouping, across the sampled
ecological-and-institutional joint space. This finding replicated
independently on fresh data. It is reported at face value, per this
milestone's own non-tuning discipline quoted above — not softened
toward a discrete-candidate claim, and not treated as license to widen
or re-run the search now that the outcome is known.
