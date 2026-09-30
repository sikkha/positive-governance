# Level 1.2b Recurrence Audit Note — Section 13

Full account of Work Package H: the audit of all twelve Level 1.2
recurrence criteria (construct, unit of analysis, sample size,
redundancy, feasibility under the new joint design), the
within-run-lineage / cross-run-structural-similarity /
independent-convergence / component-homology-vs-analogy taxonomy, and
the versioned, frozen Level 1.2b recurrence spec this audit produces
for Section 16 to consume. See
`docs/level1.2b_discovery_methods.md` for how the frozen spec is
actually applied by Work Packages J/K/L.

## 1. All twelve criteria audited, none removed

Every one of the twelve criteria (`observer/recurrence_criteria.py`'s
`RECURRENCE_CRITERIA_NAMES`) still applies under the Level 1.2b joint
design — Work Package E's pooled seed-run data has exactly the shape
each criterion already expects. Two criterion pairs were checked for
redundancy on the strength of surface similarity and found to measure
genuinely distinct things, so neither pair was merged or dropped:
`cross_seed_recurrence` vs. `parameter_condition_diversity` (seed
identity and parameter condition are different axes of variation);
`minimum_cluster_size` vs. `non_degenerate_cluster_fraction` (a raw
floor vs. a pool-size-relative bound).

## 2. The bug this audit found: `rule_lineage_id` collides across seed-runs

`rule_lineage_id` is allocated from a per-`Simulation` counter reset
to 0 in every fresh run — unique only WITHIN one seed-run, never
across runs. Section 15 makes the seed-run the primary independent
observation, and Work Package E's pool spans 576 separate seed-runs.
Criterion 12 (`independent_of_single_lineage`) and every function in
`observer/convergence_tests.py` that pools `member_lineage_ids` across
multiple seed-runs on the RAW per-run integer would silently and
incorrectly treat two different runs' coincidentally-identical small
lineage numbers (e.g. both runs' first lineage numbered `0`) as the
same lineage — not a rare edge case, the EXPECTED common case given
typically only a handful of lineages per run. Found and fixed before
Section 15's discovery pipeline ever ran on this data.

**Fix**: `convergence_tests.compose_global_lineage_id(seed_run_id,
local_lineage_id)` — every caller pooling lineage identity across more
than one seed-run must now compose keys with this helper before
calling `lineage_diversity_within_cluster` /
`independent_origin_permutation_test` /
`recurrence_criteria.independent_of_single_lineage`. Disclosed both in
`convergence_tests.py`'s module docstring and directly on Criterion
12's own docstring. A regression test demonstrates the collision
concretely: pooling two runs' raw `[0, 1]`/`[0, 1]` lineage ids
reports only 2 distinct lineages when composed keys correctly report
4 independent ones.

**New function**: `convergence_tests.within_run_lineage_relatedness`
explicitly operationalizes the "within-run lineage" similarity level
as its own reported quantity (fraction of same-seed-run member pairs
that also share a lineage) — raw per-run lineage ids are safe to
compare directly here precisely because every compared pair is
restricted to the same run.

## 3. The four-level similarity taxonomy

Recorded as data in `observer/recurrence_criteria_audit.py`'s
`SIMILARITY_LEVEL_TAXONOMY`, not left implicit:

1. **Within-run lineage** — `within_run_lineage_relatedness`.
2. **Cross-run structural similarity** — the purely descriptive
   clustering step itself (Section 9); no causal claim.
3. **Independent convergence** — cross-run similarity that also
   clears the permutation/transmission/condition-diversity bar,
   `classify_convergence_or_inheritance`'s `"convergent"` label.
4. **Component homology vs. analogy** — the same biology-inspired
   vocabulary Section 13 asks for by name, mapped explicitly onto the
   existing `"inherited"`/`"convergent"` labels (homology = shared
   origin, analogy = independently arisen) rather than reinvented as
   new computation.

## 4. The versioned, frozen recurrence spec

`experiments/level12b_stage_h_recurrence_spec.py`:
`RECURRENCE_SPEC_VERSION = "level1.2b-recurrence-spec-v1"`. Assembles
the audit module's data plus every criterion function's actual default
kwargs — extracted LIVE via `inspect.signature`
(`extract_default_thresholds`), never hand-duplicated, so the frozen
spec can never silently drift out of sync with the code that enforces
it — into one artifact, frozen (SHA-256-hashed) BEFORE Section 15's
discovery pipeline ever runs on real data. Written to
`outputs/level12b_stage_h_recurrence_spec/{recurrence_spec.json,
recurrence_spec_hash.txt}`, hash
`bee3d114a2079728ad37a4336400a9a9c9dcf086e35d7e599f0bf5bef0e35d04`.

## 5. Verification

`tests/test_level12b_recurrence_criteria_audit.py` (17 tests): audit
completeness (all 12 criteria, required fields present, the
lineage-collision finding correctly flagged as fixed), the similarity
taxonomy (4 levels, each names its operationalizing function),
`extract_default_thresholds` matching live function defaults and
staying JSON-serializable, the lineage-collision regression (concrete
before/after demonstration), `within_run_lineage_relatedness`
(same-run pairs counted, different-run pairs correctly excluded even
when their raw ids coincidentally match, degenerate <2-member case),
and the Stage H script itself (spec structure, JSON-serializability,
hash determinism, save/load roundtrip, tamper detection).
