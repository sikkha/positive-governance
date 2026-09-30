# Level 1.2 Discovery Methodology Note — Sections 9-11

Full statistical account of `observer/phenotype_discovery.py`
(Section 9), `observer/recurrence_criteria.py` (Section 10), and
`observer/convergence_tests.py` (Section 11), and how
`experiments/level12_stage4_discovery.py`/`level12_stage5_confirmation.py`
apply them. See `docs/level1.2_scientific_note.md` for results.

## 1. Unit of analysis

One phenotype vector per **seed-run** (Section 15: "seed-run is the
primary independent observation"), never per-institution and never
per-step. A seed-run's phenotype vector is computed once, whole-run
(`window=None`), from `institutional_phenotype_vector()`.

## 2. Preprocessing (Section 9.1)

`build_feature_matrix()` splits `V` into `V_ecological`/`V_demographic`
scalar columns; NaN is preserved exactly, never zero-filled, at this
stage. `missingness_report()` is always computed and exported before
any imputation decision. Three strategies are compared, never one
silently chosen: `complete_case` (drops any row with a NaN), `mean_
impute` (train-fit column means, applied unchanged to apply/held-out
data), `missingness_indicator` (mean-imputes AND doubles column count
with binary missingness flags). Standardization, when requested, is
always fit on the TRAIN split only.

Stage 4's primary strategy is `mean_impute`, chosen because Stage 3's
own pool had only 5/24 rows with any NaN — mean-impute preserves every
row for the primary pass, while `complete_case`/`missingness_indicator`
are still run (via `gmm` refits) for Criterion 7's required cross-
strategy comparison.

## 3. Candidate methods and k-range (Section 9.2)

`CANDIDATE_METHODS = ("gmm", "hierarchical", "hdbscan")` — a disclosed
reduction from Section 9's fuller suggested menu (no spectral, no
trajectory/hidden-state clustering this milestone), covering three
structurally different notions of "cluster": one parametric mixture,
one connectivity-based, one density-based. `DEFAULT_K_RANGE = (1..8)`;
`k=1` is always fit and never treated specially; no `k` is privileged,
enforced by a direct test (`k=1/2/4` produce structurally identical
result shapes under `k_selection_non_privileged_support`). `hdbscan`
never takes `k` and permits noise (`-1`), never forcing every point
into a cluster.

## 4. Model selection (Section 9.3)

`model_selection_metrics()` reports silhouette, Calinski-Harabasz,
Davies-Bouldin, cluster-size balance, and (for `gmm`) BIC/AIC/held-out
log-likelihood side by side — no single metric decides. `held_out_log_
likelihood()` fits on genuinely separate training data and scores a
genuinely held-out set; Stage 5 uses this to test whether Stage 3's own
fitted model generalizes to fresh data. Observed at Stage 5: log-
likelihood degrades gradually k=1→3 then collapses catastrophically at
k≥4 (a textbook small-sample GMM overfitting signature — tight, near-
zero-variance components at n=24 score fresh points as near-impossible)
— independent evidence against trusting any higher-k partition from
this sample size, consistent with the recurrence-criteria result.

## 5. Consensus (Section 9.4)

`co_assignment_matrix()` (noise never co-assigned with anything),
`variation_of_information()` (0.0 for identical partitions up to
relabeling), `bootstrap_stability()` (resample-with-replacement ARI
against the original fit), `algorithm_agreement()` (pairwise ARI/VI
between methods at matching k). Stage 4 pools ALL primary-strategy
fits (every k for `gmm`/`hierarchical` plus `hdbscan`) into one
co-assignment matrix and computes agreement at every k common to `gmm`
and `hierarchical`.

## 6. Recurrence criteria (Section 10)

Twelve criteria, each returning `{"passed", "value", "threshold"}` —
never a bare bool. `evaluate_recurrence_criteria()` runs all twelve
unconditionally (no short-circuiting) and reports `meets_all_minimum_
criteria` as a straight AND. None reference cluster count or identity.
The twelve: `minimum_cluster_size`, `cross_seed_recurrence`,
`cross_algorithm_support`, `bootstrap_stability`, `co_assignment_
internal_consistency`, `distinctness_from_noise`, `missingness_
strategy_robustness`, `parameter_condition_diversity`, `temporal_
persistence_of_members`, `non_degenerate_cluster_fraction`,
`k_selection_non_privileged_support`, `independent_of_single_lineage`.

**Stage 4 result**: 0/76 candidate clusters (2 methods × 8 k's +
`hdbscan`'s own clusters) met all 12. The 13 best (11/12) candidates —
all `hierarchical` k=6, 5-6 `collapse`-dominated members — uniformly
failed `cross_algorithm_support`: no other method corroborated that
specific partition. **Stage 5 replication**: 0/72 on a fresh, disjoint
12-run pool, same pipeline, unmodified.

## 7. Inheritance vs. convergence (Section 11) — scope note

Criterion 12 and Section 11's full convergence-vs-inheritance framework
are defined over institutional **lineage**, which is scoped WITHIN one
simulation run's own RNG stream — `lineage_id` integers are not
comparable across different seed-runs. At Section 9's own seed-run unit
of analysis, every pooled record is an independent origin by
construction (a distinct seed), so Criterion 12 is satisfied trivially
using each record's own row index as a valid (if not deeply
informative) proxy lineage id at this granularity. Section 11's richer
within-run, multi-institution ancestry analysis — genuinely testing
whether a phenotype cluster's institutions share transmission-linked
ancestry (inheritance) or arose independently (convergence) — is fully
implemented and tested (`observer/convergence_tests.py`, 22 tests) but
requires per-institution (not per-seed-run) pooling across a single
run's own multiple patches/institutions. Stage 3's small per-run
institution counts (up to ~4 per run at this milestone's disclosed
scale) don't support that analysis at useful scale this milestone —
flagged explicitly for Section 22 rather than worked around silently.
