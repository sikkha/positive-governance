# Level 1.2b Discovery Methods Note — Sections 8, 9, 12, 15, 16, 17

Full statistical account of the joint discovery design (Work Package
E, Section 9), the temporal representation layer (Work Package G,
Section 12), and how the main discovery pipeline (Work Package J,
Section 15), clustering/structure discovery (Work Package K, Section
16), and prospective confirmation (Work Package L, Section 17) apply
them. Builds directly on Level 1.2's own
`docs/level1.2_discovery_methodology_note.md` (Sections 9-11 there) —
`observer/phenotype_discovery.py`'s primitives are reused unmodified
throughout; this note covers what Level 1.2b adds on top: the
stratified joint design, the failure-trajectory/sustained-system
analyses, the closed-vocabulary discovery verdict, and the
confirmation methodology. See `docs/level1.2b_scientific_note.md` for
results.

## 1. Institutional search design (Work Package D, Section 8)

Latin Hypercube design over 21 institutional/mechanism dimensions
(proposal/adoption thresholds, delegation probability, authority
concentration — operationalized as `appropriation_opportunity_scale`,
disclosed — admin learning, memory retention/transfer, monitoring
allocation, detection accuracy, appeal/recall thresholds, contribution
params, appropriation params, transmission fidelity/mutation/
recombination, migration sensitivity, coordination acceptance/retry,
scaling cost, admin overload), `n_institutional_points=60`, zero
packages (`n_packages: 0`, verified by a no-two-dimensions-≥0.9-
correlated-across-points test). Ecology held fixed at one reasonable,
non-extreme point for this design's own runs — crossing with Work
Package C's ecological envelope is Work Package E's job.
`rng_mode="mechanism_substreams"` for every config.

Secondary validation (Section 8's explicit "use the audited Level
1.1b classifier only for secondary validation, never to select/filter
points"): 10 of the 60 points × 2 seeds × 150 steps, classified with
both the historical and Level 1.1b's audited `classify_delegation_
audited` — confirmed genuine label diversity (6 distinct labels) and
one audited-downgrade, consistent with the audited classifier's own
established greater conservatism, confirming the swept institutional
space is not narrowly concentrated in one structural regime.

## 2. Stratified joint discovery design (Work Package E, Section 9)

Crosses Work Package C's ecological feasibility space (freshly sampled)
with Work Package D's institutional space (freshly sampled) with
initial-condition family with seed — the milestone's actual main
data-generating run.

**Stratification discipline**: stratified ONLY by the ex-ante expected-
pressure ratio (`expected_pressure_ratio`, never any realized
simulation outcome). Cut points (tertiles) computed from this design's
own 48 ecological draws and FROZEN before any run executes. Ecological
and institutional draws are sampled INDEPENDENTLY (separate Latin
Hypercube calls, paired index-by-index), which by construction gives
multiple different institutional points within each ecological stratum
and vice versa — no additional stratified-pairing logic needed.

**Run arithmetic**: preferred `n_joint_points=48`, `seeds_per_point=6`,
`n_ic_families=2`, `total_runs=576`, `n_steps=700`; hard minimum
`n_joint_points=36`, `seeds_per_point=4`, `total_runs=288` (documented,
not used — no stop condition forced a reduction).

**Initial-condition families**: (A) institution-free — the model's own
default initial state, institutions may emerge endogenously; (B)
heterogeneous proto-institution — one independently-parameterized
`SharedRule` injected per patch immediately after `Simulation.__init__`,
each patch's `RuleParameters` drawn on its own independent uniform
range (never bundled into a package), each patch given its own fresh
`rule_lineage_id`.

**Executed**: 576/576 runs, 0 failures. Stratum spread: `{low: 17,
medium: 16, high: 15}` points (204/192/180 runs) — no stratum
collapsed to a single point. Both IC families balanced exactly 288/288.
Every run's own ledger residual under `1e-4` (max `5.9e-09`, mean
`7.1e-10` — see `docs/level1.2b_ecological_accounting.md` §2 for the
fix this validates).

## 3. Temporal representation (Work Package G, Section 12)

Per seed-run per phenotype dimension: post-burn-in mean, late-run
mean, variance, trend, persistence, transition count, longest stable
episode, shock recovery, lineage turnover, extinction-reconstruction —
under four preregistered burn-in-sensitivity definitions
(`primary=0.2`, `shorter=0.1`, `longer=0.35`, `terminal_only`) plus a
static-vs-dynamic separate-and-joint analysis. Reuses
`observer/regulation_diagnostics.py` (Level 0.3's fully-generic-over-
any-numeric-series diagnostics) and `observer/temporal_features.py`
(Section 7's window-bounds/static/dynamic/lineage-turnover/extinction-
reconstruction module) almost unchanged — the one real design decision
was that `interior_persistence`/`band_transitions`'s occupancy-specific
default bounds (`[0.05, 0.95]`) do not generalize to phenotype
dimensions (R can exceed 1, H is an unbounded structural distance, F
is a rate), so every "stability band" used for phenotype dimensions is
derived from the window's own mean ± 1 std, a documented heuristic.
Two new window types added to `compute_window_bounds`: `"post_burn_in"`
and `"pre_shock"`. Validated on a disclosed 12-seed-run subset of Work
Package E's own design (3 points × 2 seeds × 2 IC families), not the
full 576-run pool.

## 4. Main discovery pipeline (Work Package J, Section 15)

Reuses `observer/institutional_viability.py`'s `classify_all_outcome`
(Section 8A's closed seven-label vocabulary) and `sustained_system_
eligibility` (Section 8B's non-normative data-sufficiency screen)
unmodified. Adds `classify_failure_trajectory` (new): a cheap in-run
population/ecological-fraction series sampled every 10 steps
(deliberately not a full phenotype snapshot), classified into one of
five closed routes — `no_collapse_observed`, `transient_dip_recovered`,
`collapse_onset_after_last_snapshot` (a disclosed snapshot-resolution
limitation, never silently merged into another route), `late_onset_
collapse`, `sustained_collapse`.

**Executed on Work Package E's full 576-run pool, 0 failures**.
All-outcome: `collapse=326, viable=161, fragmented=89` (all other
labels 0 — collapse must stay visible, enforced structurally by
`aggregate_all_outcome_summary` always emitting every label). Failure-
trajectory: `sustained_collapse=305, no_collapse_observed=194,
transient_dip_recovered=56, late_onset_collapse=21` — most collapse
outcomes were sustained, not a last-instant artifact. Sustained-system:
all 576 runs eligible, 0 excluded — comfortably clears both the
preferred (60) and hard-minimum (40) gates.

## 5. Clustering and structure discovery (Work Package K, Section 16)

Reuses Level 1.2's own `build_feature_matrix`, `missingness_report`,
`preprocess_features`, `examine_collinearity`, `fit_candidate`,
`model_selection_metrics`, `held_out_log_likelihood`, `bootstrap_
stability`, `algorithm_agreement`, `co_assignment_matrix`, `variation_
of_information` unmodified. Primary missingness strategy is
preregistered `mean_impute` (the only one of the three
`MISSINGNESS_STRATEGIES` guaranteed never to drop a row);
`complete_case`/`missingness_indicator` fit as robustness cross-checks
only.

**`classify_discovery_verdict`** — closed six-label vocabulary
(`insufficient_evidence`, `failure_dominated`, `unstable`,
`one_config`, `continuum`, `multi_config`), first-match-wins:
`n_total >= hard_minimum` and a defined `headline_k` first; then
whether clustering just re-derives Work Package J's own failure/
success split (`cluster_vs_failure_ari >= 0.5` against a cheap
`V_demographic <= 0.05` proxy → `failure_dominated`); then stability
(`unstable` unless bootstrap-ARI **or** algorithm-agreement-ARI clears
0.3 — either is sufficient, since the two measure different kinds of
robustness); then whether any k≥2 clears a silhouette floor of 0.15
(`one_config` if not); then whether ≥3 evaluated k's sit within 0.05
silhouette of the best (`continuum`) versus a single clear peak
(`multi_config`). `_select_headline_k` picks the highest-defined-
silhouette k≥2, explicitly never special-casing k=3.

**Executed** on a re-simulation of Work Package E's exact 576-run
design (deterministic re-derivation, same seeds/configs — WP E's own
`results.json` never computed phenotype vectors). Result: `headline_k=4`,
**verdict = `continuum`** (`3_ks_within_0.05_silhouette_of_best`).
Supporting metrics: `bootstrap_stability` mean_ari=0.598 (k=4, 30
resamples); `mean_algorithm_agreement_ari`=0.192 (gmm-vs-hierarchical
ARI=0.576, but hdbscan found 0 clusters/576 noise points on this
feature space, dragging the pairwise mean down); `missingness_
strategy_robustness_ari`={complete_case: 0.591, missingness_indicator:
0.653}; `cluster_vs_ic_family_ari`=0.0008 (clustering is not simply
rediscovering IC family); `temporal_window_stability_ari`=0.141
(end-of-run vs. mid-run assignments diverge substantially — cluster
membership is not stable across a run's own duration, a genuine
finding); `parameter_neighborhood_stability_mean_ari`=0.626;
`cluster_vs_failure_proxy_ari`=0.0 (clustering is NOT simply
re-deriving the failure/success split).

## 6. Prospective confirmation (Work Package L, Section 17)

**The central judgment call.** A `continuum` verdict means discovery
did not identify discrete, well-separated candidate phenotype classes
to name, bound with uncertainty ranges, or assign expected directions
to. Work Package I's own preregistered `null_replication_rule`
("if Section 16 discovery supports no candidates, confirmation
replicates the null result rather than manufacturing a candidate to
test") is applied to a continuum finding the same way it would be
applied to a no-candidate finding — forcing the k=4 partition's
cluster boundaries into a named candidate registry would be exactly
the manufactured-candidate problem that rule exists to prevent. No
discrete candidate is named, numbered, or given an expected direction
anywhere in this Work Package's output.

**What gets tested instead**: the one concrete object Section 16 did
produce — the headline_k=4 GMM diagnostic partition — is frozen and
stress-tested for out-of-sample recurrence, never re-labeled as N
independently confirmed candidates. The primary preregistered
expectation, frozen BEFORE the confirmation pool was generated: an
independent replication of Section 16's own discovery procedure on
fresh data should likewise fail to reach a stable `multi_config`
verdict.

**Design**: fresh confirmation design (24 joint points × 8 seeds × 2
IC families = 384 preferred; 18×6×2=216 hard minimum), reusing Work
Package E's own parameter spaces/IC families/frozen stratum cut points
but with fresh LHS seeds and a disjoint seed base (`15,000,000`, vs.
Work Package E's `9,000,000`-based range). `classify_confirmation_
verdict` — closed three-label vocabulary (`insufficient_confirmation_
data`, `null_replicated`, `unexpected_recurring_structure`),
first-match-wins.

**Executed**: 384/384 runs, 0 failures. All-outcome:
`collapse=245, viable=86, fragmented=53` (`unclassified_outcome_
rate=0.0`). Failure-trajectory: `no_collapse_observed=99, transient_
dip_recovered=40, late_onset_collapse=14, sustained_collapse=231`
(`failure_transition_rate=0.742`). Independent replication:
`headline_k=2` (not 4 — itself informative about how unstable the
exact k value is), verdict=**`unstable`** (`mean_algorithm_agreement_
ari=0.276`, `bootstrap_mean_ari=0.182`, both below the 0.3 bar), never
`multi_config` — the primary preregistered NULL expectation held.
`assignment_stability_ari=0.527` (the frozen discovery-fit rule's
out-of-sample labels agree moderately, not strongly, with the
confirmation pool's own independent refit — consistent with a
continuum). `feature_profile_stability`: mean cosine similarity 0.948
across 3 of 4 clusters with members in both pools (cluster 3 empty in
the confirmation pool, reported as NaN, not dropped). **`confirmation_
verdict`: `null_replicated`.**

See `docs/level1.2b_scientific_note.md` for what these results mean
for the milestone as a whole.
