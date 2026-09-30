# Level 1.3 Discovery Methods Note — Stages 6, 7, 8

Full statistical account of the pooling design (Stage 6), the fresh-
confirmation design (Stage 7), and the S_obs/Z_obs mapping (Stage 8).
Builds directly on `observer/phenotype_discovery.py`'s own primitives —
reused **unmodified** throughout, exactly as `docs/level1.2b_discovery_
methods.md` §5 describes for Level 1.2b's own Work Package K. This note
covers what is specific to Level 1.3's own pooling/adapter design; see
`docs/level1.3_scientific_note.md` for the results read in the context
of the whole milestone.

## 1. Why pooling, not a fresh discovery design (Stage 6)

Unlike Level 1.2b's Work Package E (a single, purpose-built 576-run
joint design), Level 1.3's phenotype-discovery input is the **union**
of three already-executed, independently-justified experimental
stages: Stage 3 (the sequencing x entrenchment factorial, 72 runs),
Stage 4 (the open pressure-history LHS search, 96 runs), and Stage 5
(the causal counterfactual triples, 48 runs — base/erased/reversed,
tagged separately by `source_stage` so the pooled discovery step can
never conflate a counterfactual re-run with an independent draw). This
gives `n_total = 72 + 96 + 48 = 216`, tagged throughout by which stage
produced each row.

**Adapter design.** Each stage's own output JSON stores flat `{key:
float}` phenotype dicts (already the natural shape for that stage's
own report). `experiments/level13_stage6_blind_phenotype_discovery.
py::_wrap` re-wraps each flat vector into the `{k: {"value": float}}`
shape `build_feature_matrix` expects — a pure reshaping step, no value
is computed, transformed, or imputed inside `_wrap` itself. This keeps
Stage 6 a thin pooling-and-adapter layer over Stage 3/4/5's own already
-verified output, never a second place phenotype values get computed.

**Primary missingness strategy** is preregistered `mean_impute`
(`PRIMARY_MISSINGNESS_STRATEGY`), the same choice `docs/level1.2b_
discovery_methods.md` §5 made for the same reason: the only one of the
three `MISSINGNESS_STRATEGIES` guaranteed never to drop a row.
`complete_case`/`missingness_indicator` are fit as robustness
cross-checks only — and, in this milestone, `complete_case` collapses
to zero rows (see §3 below), a disclosed and structurally meaningful
result in its own right, not a bug to route around silently.

## 2. What Stage 6 reused unchanged, and what it did not

Reused unmodified: `build_feature_matrix`, `missingness_report`,
`preprocess_features`, `compare_k_range`, `fit_candidate`,
`bootstrap_stability`, `algorithm_agreement`. `_select_headline_k` is
re-derived (not imported) inside Stage 6's own script — a small,
disclosed duplication of Work Package K's private helper, matching
this project's own established precedent (`dev_mem/status_update.md`)
of preferring small disclosed duplication over private cross-module
coupling. The heuristic itself is unchanged: highest-defined-silhouette
k>=2, never special-casing k=3.

One genuinely new diagnostic, specific to a pooled (not purpose-
designed) discovery input: `cluster_vs_source_stage_ari` — the ARI
between the discovered cluster labels and each row's own `source_stage`
tag. This did not exist in Level 1.2b's discovery methods because that
milestone's discovery pool came from one homogeneous design; Level
1.3's pool does not, so this check exists specifically to distinguish
"the discovered structure is genuine" from "the discovered structure is
just rediscovering which stage a row came from."

## 3. Stage 6 results

`n_total=216`. `headline_k=2` — the clear silhouette leader (0.334),
though not sharply separated from k=5 (0.297); the full curve is
`{1: NaN, 2: 0.334, 3: 0.256, 4: 0.285, 5: 0.297, 6: 0.153, 7: 0.196,
8: 0.297}` (k=1 is undefined by construction — silhouette requires at
least two clusters). `bootstrap_stability.mean_ari ≈ 0.917` (std 0.216
across 30 resamples) — high on average, with real resample-to-resample
variance disclosed via the std, not hidden behind the mean alone.
`mean_algorithm_agreement_ari ≈ 0.291` across gmm/hierarchical/hdbscan
— modest, not strong, cross-algorithm agreement. `hdbscan` itself found
**zero** clusters at its default `min_cluster_size` (all 216 points
labeled noise) — reported exactly as found, not treated as a failed
run and excluded.

`cluster_vs_source_stage_ari = 0.554` — a moderate, not negligible,
correlation between discovered structure and which stage a run came
from. This is disclosed directly rather than minimized: it means the
k=2 partition is **not** a pure pooling artifact (an ARI near 1.0 would
mean the "discovery" is trivially just relabeling `source_stage`), but
it is also not fully independent of it either — a genuine limitation
of a pooled-not-purpose-designed discovery input, stated as such.

`missingness_strategy_robustness_ari`: `complete_case` is `NaN` — every
one of the 216 pooled rows has `seq_bargaining_participation` missing
(the `bargaining_pressure` sequencing dimension never crossed threshold
in any pooled run), so `complete_case` drops every row, leaving zero
training rows. `experiments/level13_stage6_blind_phenotype_discovery.
py::run` guards this exact degenerate case explicitly (`if p["X_train"]
.shape[0] == 0: ... continue`) rather than letting it raise inside
`GaussianMixture(n_components=0)` — a disclosed structural finding
(this milestone's own bargaining-pressure sequencing dimension is
under-triggered across its own pooled data), not a bug worked around
silently. `missingness_indicator` cross-check: `ARI ≈ 0.981` — very
close to the primary `mean_impute` fit, i.e. explicitly flagging which
rows had missing `seq_bargaining_participation` (rather than imputing
its value) recovers essentially the same partition, evidence the k=2
split is not being driven by the imputed value itself.

## 4. Fresh confirmation design (Stage 7)

Unlike Level 1.2b's Work Package L (a full fresh 384/216-run design
with its own parameter space), Level 1.3's confirmation step is
intentionally lighter, matching this milestone's own disclosed
session-budget scaling: 12 fresh points (`N_POINTS=12`, `N_SEEDS_PER_
POINT=1`), drawn with a disjoint LHS seed (`LHS_SEED=20260820005`) and
a disjoint seed base (`SEED_BASE=9_000_000` — offset from Stage 4's own
seed range so no fresh point can coincide with an already-pooled Stage
4 draw) through **Stage 4's own `_run_one`/`_PARAMETER_SPACE`
machinery, reused directly**, not reimplemented. `_stage6_fit` re-
derives Stage 6's exact pool+preprocessing+fitted-GMM pipeline, reading
`headline_k` back from Stage 6's own hash-verified `results.json`
rather than re-selecting it — the frozen fit is scored against, never
re-fit on, the fresh points.

**Executed**: 12/12 fresh points, all assigned to the larger of Stage
6's two clusters (144/216 training rows, vs. 72/216 for the other).
`mean_train_log_likelihood_per_point ≈ -1.291`; `mean_fresh_log_
likelihood_per_point ≈ -6.050` — a real, disclosed generalization gap:
fresh data scores substantially worse under the frozen model than the
data it was fit on. This is reported as a genuine limitation, not
smoothed over — consistent with this milestone's standing commitment to
remain capable of finding a weak confirmation signal rather than
assuming a strong one.

## 5. S_obs/Z_obs mapping (Stage 8)

Purely post-hoc — no new simulation runs. Pools S_obs/Z_obs from every
stage that has them: Stage 3 (72), Stage 4 (96), Stage 5 (48, but only
the 16 `base`-condition rows are counted toward `pooled_correlation`'s
independent-observation count — the `erased`/`reversed` rows are
matched re-runs of the same seed, not independent draws — see the
script's own docstring for the exact counting rule), and Stage 7 (12).
Reuses, never recomputes, Stage 5's own already-computed counterfactual
shift numbers (`stage5_reused_counterfactual_shift`) rather than
deriving a second, potentially-diverging copy of the same quantity.

**Executed**: `n_total=228`. `pooled_correlation`: Pearson r ≈ 0.888
(p ≈ 2.35e-78), Spearman ρ ≈ 0.913 (p ≈ 3.77e-90) — both the linear and
rank-based correlation are strong and positive. `median_split_joint_
table` (s_obs_median ≈ 0.642, z_obs_median ≈ 0.429): `high_s_high_z=
100`, `low_s_low_z=100`, `high_s_low_z=14`, `low_s_high_z=14` — a
strongly diagonal table. `covariate_correlations` checks each of the
four other pooled phenotype dimensions (`entrenchment`, `performance_
legitimacy`, `procedural_legitimacy`, `conversion_incidence`) against
both S_obs and Z_obs, so the pooled correlation is reported alongside,
not instead of, its relationship to the milestone's other measured
quantities.

See `docs/level1.3_scientific_note.md` §§7-9 for what these results
mean read together with Stages 3-5 and 9.
