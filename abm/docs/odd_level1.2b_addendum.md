# ODD Addendum — Level 1.2b: Ecological Feasibility Envelope and Powered Blind Institutional-Phenotype Rediscovery

This addendum documents only what Level 1.2b adds on top of Level 1.2
(`docs/odd_level1.2_addendum.md`) and everything it in turn built on.
Read that first. As with every prior addendum, a bare
`SimulationConfig()` run remains byte-for-byte identical to
pre-Level-1.2b behavior — nothing here is described as "the model now
does X" without also stating the exact flag/preset that must be set
for X to occur at all.

## 1. Purpose

Level 1.2's own main discovery sample was 12 parameter points × 2
seeds = 24 runs — too small for high-dimensional phenotype discovery,
and its own near-universal ecological floor (collapse in 22-24 of
every 24-run pool) erased most of the institutional variation a
discovery pipeline needs to find anything. Level 1.2 therefore
supports "within the sampled region, collapse was the dominant
recurrent system outcome and no recurrent institutional configuration
was independently supported" — it does not support "the model
contains no recurrent institutional phenotypes." Level 1.2b exists to
test that distinction directly, at a much larger, ecologically-
stratified scale, not to manufacture a different answer.

**This is still not a search for three governance types.** Every
generative/observer boundary rule, forbidden-terminology guard, and
SEM firewall Level 1.2 established remains in force, extended
mechanically to every new Level 1.2b module and experiment script
(`tests/test_level12b_sem_firewall_extension.py`).

## 2. Generative layer: no new mechanism, but real bugs fixed

Level 1.2b introduces **no new `SimulationConfig` field and no new
generative mechanism**. Every Level 1.2b run reuses Level 1.2's own
config surface (`level12_complete()`'s defaults) unchanged; Work
Package N's causal-ablation factors map onto pre-existing fields
rather than introducing new ones — the full field-mapping disclosure
is in that Work Package's own `experiments/level12b_stage_n_causal_
collapse_decomposition.py` docstring and in `dev_mem/status_update.md`'s
Work Package N entry, not restated here.

What Level 1.2b DID find and fix, during its own mandatory pre-
feasibility-mapping ledger audit (Section 5), were **six genuine,
previously-undetected generative-layer bugs** — none visible at the
small scale Level 1.1b/1.2's own validation suites ran at, all
requiring Level 1.2b's actual production scale
(`population_size=32, n_patches=4, n_steps=700`) to manifest:

1. A sign-flip in every capped-resource-deduction site
   (`sanction_round`, `monitoring_round`, `membership_round`,
   `delegation.py`'s audit cost) when the target's resources were
   already negative.
2. `MonitoringEvent.cost_deducted` double/triple-counting a cost paid
   once per round but stamped onto every violation-event that round.
3. A per-active-link coordination maintenance fee charged every step
   but only sometimes logged (`CoordinationMaintenanceCostEvent` added
   to log it unconditionally).
4. A rule-ID/patch-ID key-space conflation in dissolution routing that
   silently corrupted institutional state via unrelated ID
   coincidences.
5. `amendment_round`'s own dissolution path never removing the
   dissolved rule from `rule_registry`, leaving a stale entry whose
   fund kept counting toward system totals.
6. A zero-recipient `"distributed_to_members"` fund-dissolution
   disposition not treated as a loss.

Full account: `docs/level1.2b_ecological_accounting.md`. None of these
changes alters any decision an agent makes — every fix is either a
bookkeeping correction (what gets logged/summed) or a corrected
cleanup of already-dissolved institutional state; behavior-preservation
was confirmed by the full pre-existing test suite passing unchanged at
every step of the fix sequence.

Two small, additive generative extensions were also needed:
`resource_depletion`/`regeneration_reduction` perturbations, previously
pool-topology-only, now also apply under `ecology_topology="patches"`
(`ResourcePatch.apply_shock_loss`, mirroring the pre-existing
pool-topology handling exactly).

## 3. Observer layer: the new modules

- **`observer/ecological_ledger.py`** (Work Package A, Section 5) — a
  full supply/demand/net-zero-transfer reconciliation of
  `system_total_resources()`. See `docs/level1.2b_ecological_
  accounting.md`.
- **`observer/feasibility_ratios.py`** (Work Package B, Section 6) —
  `structural_feasibility_ratio`, `expected_pressure_ratio`,
  `realized_balance_timeseries`. See `docs/level1.2b_feasibility_
  method.md`.
- **`observer/phenotype_feature_audit.py`** (Work Package F, Section
  11) — the formal, machine-checkable audit of every X=(C,E,L,D,M,R,
  S,F,V,H) dimension's numerator/denominator/window/missingness/
  aggregation/construct-type. See `docs/level1.2b_feature_audit.md`.
  Additive fields on `institutional_phenotype_vector`'s own records:
  `"window_applied"`, `"construct_type"`.
- **`observer/recurrence_criteria_audit.py`** (Work Package H, Section
  13) — the twelve-criterion audit, the four-level similarity
  taxonomy, and `extract_default_thresholds`. New function on
  `observer/convergence_tests.py`: `compose_global_lineage_id` (fixes
  a genuine cross-run lineage-ID collision — see `docs/level1.2b_
  recurrence_audit.md`) and `within_run_lineage_relatedness`.
  Extended: `observer/temporal_features.py` gained `"post_burn_in"`/
  `"pre_shock"` window types, `window_persistence_features`,
  `window_shock_recovery_features`, `group_features_by_kind` (Work
  Package G, Section 12).
- **`observer/phenotype_discovery.py`** gained `seed_clustered_
  bootstrap_stability` (Work Package Q, Section 22) — a genuine
  CLUSTER bootstrap (resamples whole `joint_point_id` groups, not
  individual seed-rows) correcting a statistical gap in the
  pre-existing flat `bootstrap_stability`, and `CLUSTERING_PIPELINE_
  VERSION` (Section 24). `observer/recurrence_criteria.py` gained
  `RECURRENCE_CRITERIA_VERSION`; `observer/phenotype_feature_audit.py`
  gained `FEATURE_SCHEMA_VERSION` (both Section 24).

No new experiment-side classification vocabulary was added to the
observer layer's own closed-vocabulary discipline without a matching
test: `classify_failure_trajectory` (5 labels, Work Package J),
`classify_discovery_verdict` (6 labels, Work Package K),
`classify_confirmation_verdict` (3 labels, Work Package L),
`classify_overall_recurrence_label` (7 labels — the SAME seven Section
20 specifies: `candidate`/`confirmed`/`transient`/`failure`/
`boundary`/`continuum`/`unclassified` — Work Package O). None of these
functions, nor any label they emit, is defined in `experiments/`
rather than `observer/`'s downstream-only layer where the underlying
primitives live; the classification functions themselves live in
`experiments/level12b_stage_*.py` because they compose experiment-
specific outcome data, exactly the same placement precedent Level
1.2's own `classify_all_outcome` established at the observer layer for
generic outcomes and Level 1.2b's own stage scripts follow for
milestone-specific verdicts.

## 4. Configuration surface (Section 24)

No new fields. Eight new presets on `SimulationConfig` — `level12_
compat` (explicit alias for `level12_complete`'s own baseline) and
seven semantically-named entry points for this milestone's own run
contexts (`level12b_feasibility_map`, `level12b_open_discovery`,
`level12b_confirmation`, `level12b_failure_analysis`, `level12b_
sustained_analysis`, `level12b_collapse_ablation`, `level12b_scaling_
robustness`) — every one a no-op by default (identical, field for
field, to `level12_complete()`'s own output when called bare). A new
shared result-manifest schema (`experiments/level12b_common.py`) — see
`docs/config_reference.md`'s own Level 1.2b section for the full field
list.

## 5. Data pipeline: the joint discovery design and what it found

Full account: `docs/level1.2b_discovery_methods.md`. In short: a
576-run design (48 institutional×ecological joint points × 6 seeds ×
2 IC families), stratified ex ante by `expected_pressure_ratio`,
feeds a discovery pipeline that reused Level 1.2's own clustering
primitives unmodified and produced a `continuum` verdict (headline_k=4,
no single dominant small-k grouping) — independently replicated as
`null_replicated` on a fresh, disjoint 384-run confirmation pool.
`docs/level1.2b_scientific_note.md` reports what this, and the
milestone's other findings (near-universal collapse, the causal
ablation results, the scaling-robustness grid), mean together.
