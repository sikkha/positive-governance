# Level 1.2b Feature Audit Note — Section 11

Full account of Work Package F: the formal audit of every dimension in
`observer/institutional_phenotype.py`'s X = (C, E, L, D, M, R, S, F, V,
H) vector against Section 11's six required criteria — numerator,
denominator, valid-window semantics, structural-missingness condition,
aggregation path (event → institution → patch → seed-run), and
construct type. Section 11's own charge: "remove only for
preregistered reasons; keep dimensions separate (no single governance
score)."

## 1. No dimension was removed

None of the ten met Section 11's "preregistered reason" bar for
removal. Every audit finding below is instead disclosed as
machine-checkable data (`observer/phenotype_feature_audit.py`'s
`PHENOTYPE_FEATURE_AUDIT`) and, where the underlying finding was a
genuine transparency gap rather than an intentional design, fixed
directly in `institutional_phenotype.py` itself.

## 2. Finding 1: window semantics are not uniform across dimensions

`institutional_phenotype_vector(..., window=(a, b))` accepts and
echoes back `window` on every dimension, but the parameter only
actually changes the computed value for **one** dimension fully:

- **E** — fully windowed; delegates to `accountability_diagnostics.
  effective_constraint`, which filters every underlying event list by
  step.
- **L, D, M, S, F, V, H** (7 of 10) — pure current-state snapshots
  that silently ignore `window` entirely. They read live running
  totals off mutable objects (`SharedRule`, `Delegate`,
  `InstitutionRecord`, `PatchSystem`) that have no per-step history to
  filter.
- **C, R** — MIXED. C filters delegates by appointment `start_step`
  falling in `window`, but conjoins that with the delegate's
  current-tense `active` flag, not tenure-overlaps-window. R has a
  genuinely windowed numerator (admin spending + appropriations,
  event-filtered) divided by an **unwindowed** denominator
  (`patch_system.total_resources`, read as of the call, not as of
  `window`'s end) — a flow-over-stock construct mismatch that risks a
  misleading ratio if a caller's `patch_system` reference doesn't
  reflect `window`'s end.

**This is an architectural fact, not itself a bug to patch by
inventing internal filtering.** `observer/temporal_features.py`
(Section 7, already built at Level 1.2) confirms the *intended*
design for windowed views of the seven snapshot dimensions is
external: take repeated `institutional_phenotype_vector(...)`
snapshots at different steps (each call's own `window=None`), then use
`window_static_features`/`window_dynamic_features` to summarize the
already-collected series over any window.

**What WAS a genuine bug**: the record silently echoed back whatever
`window` was passed with nothing indicating whether it had actually
been applied — easily misleading a caller into believing a
`record["window"] == (100, 200)` field meant the returned value only
reflected steps 100-199.

**Fix**: every dimension record now additionally carries
`"window_applied"` (`True` / `False` / `"partial"`) and
`"construct_type"` (e.g. `"event_windowed_ratio"`,
`"snapshot_current_state_ratio"`,
`"windowed_flow_numerator_over_snapshot_stock_denominator"`), via the
shared `_record()` helper, now keyword-only for these fields so no
call site can omit them. No numerator/denominator/value computation
changed — purely additive, confirmed safe by the full pre-existing
Level 1.2 phenotype-vector test suite passing unchanged.

## 3. Finding 2: a latent parameter-precedence ambiguity in F

`amendment_flexibility` (dimension F) takes both an explicit
`current_step` parameter and a `window` parameter, and computes rule
age from `current_step` only — if a caller ever passed a `window`
ending somewhere other than `current_step`, age would silently use the
wrong endpoint. No current caller does this (every call site passes
`current_step` equal to the run's latest step), so the numeric
behavior is left unchanged, but disclosed via
`construct_type="snapshot_current_state_ratio_current_step_not_
window"` so a future caller who breaks that invariant gets a
machine-checkable signal instead of a silently wrong number.

## 4. Aggregation path (applies identically to all ten dimensions)

Every dimension is computed at the EVENT/current-object level
directly into one scalar (or two, for V) per call — there is no
intermediate per-institution or per-patch record kept or exported by
`institutional_phenotype.py` itself; "per institution"/"per patch"
only exist as internal grouping inside a few dimension functions
before being collapsed to the single call-level scalar. The true
seed-run-level aggregation happens one level up, in `observer/
phenotype_discovery.py::build_feature_matrix` (Section 9.1), which
takes a list of already-computed per-seed-run vector outputs and
assembles the feature matrix — it does not re-aggregate within a
seed-run.

## 5. Verification

`tests/test_level12b_phenotype_feature_audit.py` (14 tests): audit
completeness (all ten dimensions covered, required fields present,
`window_applied` restricted to its three documented values, no
dimension removed), the grouping helpers
(`dimensions_with_full_window_semantics` → `("E",)`,
`dimensions_with_partial_window_semantics` → `("C", "R")`,
`dimensions_with_no_window_effect` → the remaining seven) matching the
audit data — and the actual verification step, a real 20-agent/
3-patch/80-step `level12_complete` run cross-checked at two disjoint
windows per dimension: L/D/M/S/F/H/V confirmed byte-identical
regardless of window (proving `window_applied=False` is actually true
at runtime, not just claimed); E confirmed to have its denominator
shrink under a narrow window (proving real event filtering); R
confirmed numerator shrinks while denominator stays fixed (proving the
flow/stock split is real); C confirmed denominator can shrink under a
narrow start-step window (proving the partial filtering is real).
Every live record's `construct_type`/`window_applied` is checked
against the audit module's own claims, so the audit cannot silently
drift out of sync with the code it describes.
