# Level 1.3 Measurement Note — Work Packages G and H (Sections 12-13)

This note has no direct Level 1.2b analogue (that milestone's own
measurement layer was already fully documented across `docs/level1.2b_
feature_audit.md` and `docs/level1.2b_feasibility_method.md`). It
exists because Level 1.3 introduces two new observer-side construct
layers of its own — `S_obs`/`Z_obs` (Work Package G) and the fourteen-
dimension Level 1.3 phenotype vector (Work Package H) — and both carry
firewall obligations substantial enough to warrant a standalone,
citable record rather than being folded into the scientific note.

## 1. What S_obs and Z_obs are, and — as importantly — what they are not

`observer/sz_obs.py` builds two observer-side, post-hoc composites from
this ABM's own simulated event history:

- **`S_obs`** (capacity/coordination axis): the unweighted mean, at
  each step, of four Work-Package-B series (`delegation`,
  `administrative_function`, `monitoring`, `interpatch_coordination`)
  plus this module's own `performance_legitimacy_series`.
- **`Z_obs`** (negotiated-constraint axis): the unweighted mean, at
  each step, of two Work-Package-B series (`accountability`,
  `bargaining_participation`) plus this module's own `procedural_
  legitimacy_series`.

Both composites are built entirely by **re-using series this project
already independently computed for other, independently-justified
reasons** — no series was invented fresh for this purpose, and no
weight, threshold, or functional form was fit to reproduce any external
number. Weights are equal by explicit, disclosed design choice
(`sz_obs.py`'s own docstring: "a defensible, legible, non-circular
observer construct ... NOT a recreation of the dissertation's specific
factor structure").

**What they are not, stated plainly and repeatedly because this is the
single most important firewall boundary in this milestone**: `S_obs`
and `Z_obs` are not the dissertation's survey-derived latent variables.
They do not use the dissertation's item wording, do not use the
dissertation's fitted factor loadings, and are never read by any
generative mechanism anywhere in this codebase — `sz_obs.py` reads no
`*_enabled` config flag at all, a structural property (not just a
convention) that means no allowlist entry was even needed for it in
`tests/test_level13_compatibility.py`'s own structural guard. Both
`*_legitimacy_series` helpers are well-defined (all-zero) whether or
not the underlying legitimacy channels were ever enabled, so `S_obs`/
`Z_obs` remain computable — and remain honestly near-zero — even for a
run where Work Package D's channels never fired.

## 2. Why these six series and not a different six

Every one of the six input series was chosen because it already had an
independent justification from an earlier work package, not because it
correlates well with anything. `delegation`/`administrative_function`/
`monitoring`/`interpatch_coordination` are Work Package B's own
sequencing dimensions — a capacity-to-govern-effectively signal that
predates and does not depend on Work Package G's existence.
`performance_legitimacy_series` (a rule reliably delivering) was judged
to belong under `S_obs`, not `Z_obs`, on the same capacity-to-govern
logic — a disclosed classification choice, stated once here rather than
re-litigated in every downstream document that uses it.
`accountability`/`bargaining_participation` are likewise Work Package
B's own dimensions; `procedural_legitimacy_series` (consent obtained
through fair process, not raw output) was judged to belong under
`Z_obs` as a constraint-on-power signal.

## 3. The Level 1.3 phenotype vector (Work Package H)

`observer/level13_phenotype.py` builds this milestone's own fourteen-
candidate-dimension feature vector, one call per seed-run, feeding the
same, unmodified `observer/phenotype_discovery.py` clustering machinery
Level 1.2 and Level 1.2b both used (`CLUSTERING_PIPELINE_VERSION =
"clustering_pipeline_v1"`) — the discovery machinery itself is never
forked or re-derived for this milestone; only the input vector is new.
Each dimension traces to a work package this project already
independently justified:

- Eight `seq_<dimension>` features: Work Package B's own first-
  sustained-crossing step, one per institutional-response dimension,
  normalized to a fraction of `n_steps` (`NaN`, not zero, if that
  dimension never crossed threshold — Section 7's "do not assign a
  sequencing category where activation is absent" applies here, via
  `build_feature_matrix`'s existing structural-`NaN`-preserving
  contract; this is the direct mechanical source of `seq_bargaining_
  participation`'s observed 100% missingness across the pooled Stage
  6 discovery input — see `docs/level1.3_discovery_methods.md` §3).
- `entrenchment`: Work Package C's `entrenchment_level` at the run's
  final step, averaged across currently-active rules.
- `performance_legitimacy`/`procedural_legitimacy`: Work Package D's
  two ledgers, read directly off each active rule's current field — a
  snapshot, not a time average, distinguished by each record's own
  `construct_type`.
- `conversion_incidence`: Work Package F's `conversion_incidence_
  series`, final value.
- `S_obs`/`Z_obs`: Work Package G's `s_obs_z_obs_summary`, full-run
  mean — the same construct described in §1 above, entering the
  fourteen-dimension vector as two of its fourteen entries, never
  recomputed differently here.

One disclosed structural difference from Level 1.2/1.2b's own
`institutional_phenotype_vector`: several of these fourteen dimensions
(the eight sequencing features, `S_obs`, `Z_obs`) are natively
population/run-wide already, not built per-patch then combined — so
there is no per-patch-then-combined special case for this module, and
`build_feature_matrix` needed no modification to consume it (every key
maps to exactly one scalar `"value"`, the existing generic case that
function already handles).

## 4. Firewall discipline applied to this measurement layer specifically

`tests/test_level13_sem_firewall_extension.py`'s scan covers every
module under `src/abm_governance` automatically, `sz_obs.py` and
`level13_phenotype.py` included, with no per-file update needed when
either module is edited. Beyond the mechanical scan, three properties
of the design itself do independent firewall work, stated here so a
future editor of either module understands why they must be preserved:

1. **No `*_enabled` flag is read** by `sz_obs.py` — the observer layer
   cannot be made to depend on which generative mechanisms happened to
   be on, and cannot be mistaken for a generative-side construct by any
   future flag-surface audit.
2. **No fitted parameter** anywhere in either module — every weight is
   an explicit, disclosed `1/n` (unweighted mean), never estimated from
   data, so there is no fitted quantity that could be (even
   accidentally) tuned toward reproducing an external number.
3. **No construct name, dimension key, or docstring phrase** in either
   module echoes the dissertation's own item wording or construct
   names — both modules' docstrings state this directly and are
   themselves covered by the same forbidden-terminology scan as the
   code.

These three properties are why S_obs/Z_obs and the Level 1.3 phenotype
vector could be built at all without expanding the compatibility
guard's own allowlist — see `docs/level1.3_historical_mechanisms.md`
§4 for the analogous two-layer-activation discipline on the generative
side, and `docs/level1.3_bug_disclosure_and_reproducibility_note.md`
for the one place that generative-side discipline was found lacking
and fixed.
