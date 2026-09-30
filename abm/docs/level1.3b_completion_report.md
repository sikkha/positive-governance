# Level 1.3b Completion Report — Validation of Historical Path Dependence

**Status: Stages 0-10 (Sections 4-15) executed and verified; the test
requirements sweep (Section 20, task #124), visualizations (Section 21/
23, task #125), and documentation (Section 24, task #126) are all
complete. This report covers the build inventory, test-suite status,
structural guards, bugs found, and limitations. Section 19's eight-way
decision-gate classification is rendered separately in `docs/level1.3b_
decision_gate_report.md`, and the full hypothesis-by-hypothesis
evidentiary synthesis in `docs/level1.3b_scientific_note.md`, per this
milestone's own governance that the classification and the findings be
reasoned separately from the build/status inventory below.**

## 1. What was built

**Two new source-layer modules**: `observer/historical_persistence.py`
(Work Package F, Stage 5 — windowed persistence/hysteresis diagnostics:
`window_bounds`, `windowed_mean`, `windowed_variance`, `early_to_
middle_displacement`, `middle_to_late_displacement`, `late_window_
variance`, `convergence_divergence_slope`, `trajectory_distance`,
`condition_rank_stability`, `classify_persistence`) and `core/state_
checkpoint.py` (Work Package G, Stage 6 — mid-run branching primitives:
`run_partial`, `fork`, `finish`, `fork_and_finish`, the last two now
carrying an explicit caveat about the `copy.deepcopy`/frozenset-
iteration-order bug this milestone found and fixed, see §4).

**One new function on an existing module**: `core/historical_
counterfactuals.py::equalize_pressure_series` (flattens a channel's
realized series to its own mean, preserving cumulative exposure exactly
while removing temporal structure — the third counterfactual family
alongside the two Level 1.3 already had).

**Two source-layer fixes**: `observer/sequencing_diagnostics.py`'s
compliance-series construction (Work Package B — held, not zero-filled,
fixing 216/216 `seq_bargaining_participation` missingness inherited
from Level 1.3) and `rules/transmission.py`'s `TRANSMISSIBLE_COMPONENT_
NAMES` (sorted before tupling, fixing a genuine cross-process
non-determinism bug — see §4).

**Fifteen new experiment scripts** (`experiments/level13b_*.py`):
`level13b_preregistration.py` (Section 16 manifest), `level13b_stage0_
frozen_compatibility.py` through `level13b_stage10_ecological_control_
scale_shock.py` (eleven stage scripts, Stage 0-10), `level13b_test_
requirements_audit.py` (Section 20's 19-category coverage matrix), plus
`experiments/make_level13b_visualizations.py` (Section 21/23, sixteen
figures). (Work Packages A-C's own audit/calibration work, tasks
#111-113, are folded into Stage 0-2's own scripts, per this milestone's
own preregistration-preceded-by-audit sequencing.)

**No new `SimulationConfig` fields** — Level 1.3b is a validation
milestone; every field it uses (pressure/entrenchment/legitimacy
channels, transmission sub-flags) was already defined by Level 1.3.

**Sixteen new figures** (`outputs/level13b_figures/01_...png` through
`16_...png`), covering every Stage 0-10 script plus the test-
requirements coverage matrix.

**Five new/updated documentation files**: this report, `docs/level1.3b_
bargaining_activation_audit.md` and `docs/level1.3b_inference_audit.md`
(both written during Work Package A-C, tasks #111-113, before the
preregistration freeze), `docs/level13b_preregistration.md` (Section
16), `docs/level1.3b_scientific_note.md`, and `docs/level1.3b_decision_
gate_report.md` (the last two, task #126). **Naming note, disclosed
rather than silently fixed**: `docs/level13b_preregistration.md` uses
the `level13b_` (no dot) form, while every other Level 1.3b doc uses
`level1.3b_` (with dot) — an inconsistency introduced when that file was
first written (task #114) that this report leaves as-is rather than
renaming, since other files may already reference the existing path.

## 2. Test suite status

**178 new tests** were added this milestone, across 19 files under
`tests/test_level13b_*.py`, against a preflight baseline of `1869
passed, 6 skipped, 0 failed, 0 warnings` (recorded in `dev_mem/status_
update.md`'s own Level 1.3b preflight entry, run before any Level 1.3b
code was written — identical to Level 1.3's own closing count, confirming
no regression existed between milestones at the start). The full suite
was re-run with `-W error` after every significant change throughout
this milestone (11 full-suite runs total), never merely assumed clean.

Per-file new-test counts: `test_level13b_bargaining_activation_
construction.py` (6), `test_level13b_cross_process_reproducibility.py`
(4), `test_level13b_historical_persistence.py` (25), `test_level13b_
preregistration.py` (20), `test_level13b_sem_firewall_extension.py`
(3), `test_level13b_stage0_frozen_compatibility.py` (8) through
`test_level13b_stage10_ecological_control_scale_shock.py` (9) — eleven
stage-script test files (Stage 0-10), 100 tests total, added this
task (#124) specifically to close the dedicated-test-file gap described
in §5 below — `test_level13b_state_checkpoint.py` (8), `test_level13b_
test_requirements_audit.py` (9), `test_level13b_visualizations.py` (3).

## 3. Structural guards held throughout

- `tests/test_level12_structural_guards.py`'s whole-package
  (`pkgutil.walk_packages`) forbidden-terminology scan automatically
  covers every module this milestone added or modified — no per-module
  allowlist edit was ever needed.
- `tests/test_level13b_sem_firewall_extension.py` extends the
  experiment-script glob to `level13b_*.py` (`FORBIDDEN_LEVEL13_TERMS`,
  reused unmodified from Level 1.3 — this milestone introduces no new
  forbidden vocabulary) and adds a docs-directory scan for
  `docs/level1.3b_*.md`.
- `tests/test_level13b_preregistration.py` is the structural guard on
  the freeze-then-hash manifest itself — tamper detection, hash
  stability, and every Stage 3+ script's own `load_and_verify_
  manifest()` hard-stop are all exercised.
- `experiments/level13b_test_requirements_audit.py`'s 19-category
  coverage matrix (Section 20) was constructed from real file/class-name
  citations, mechanically re-verified by `tests/test_level13b_test_
  requirements_audit.py` (9 tests, including two negative controls
  proving the checker can actually fail) — plus a second, independent
  mechanical check (`_all_level13b_stage_scripts_have_a_dedicated_test_
  file`, its own negative control) that catches any future stage script
  added without a matching test file even before the matrix itself is
  hand-updated.
- `tests/test_level13b_visualizations.py` adds a check not present in
  Level 1.3's own equivalent: no figure's source text may contain any
  `DECISION_GATE_OUTCOMES` key, a direct mechanical enforcement of this
  milestone's own stopping rule extended to the visualization layer.

## 4. Bugs found and fixed mid-milestone

**Cross-process frozenset-hash non-determinism** (`rules/
transmission.py::TRANSMISSIBLE_COMPONENT_NAMES`, introduced at Level
1.2, found at Level 1.3b Stage 0). Built by iterating a frozenset union
of string component names; Python randomizes `str` hashing per process
by default, so iteration order — and therefore which name landed at the
RNG-drawn index `rng.choice(TRANSMISSIBLE_COMPONENT_NAMES)` consumes —
varied across separate process launches of the identical seed and
config, silently producing different (though internally self-
consistent) trajectories run to run. Invisible to every prior
compatibility check because they all build-and-run within one process
(one hash seed) by construction; found only when Stage 0's own
Comparison C compared 15 genuinely separate process launches for the
first time (15 distinct outputs pre-fix, 1 identical output post-fix).
Fixed by sorting the union before tupling. Standing regression guard:
`tests/test_level13b_cross_process_reproducibility.py`.

**`copy.deepcopy` does not reliably preserve `frozenset` iteration
order** (Stage 6's own new checkpoint machinery, found and fixed before
any real Stage 6 run completed). A `frozenset`'s internal hash-table
layout depends on the history of insertions/deletions/resizes that
built it, not only on final contents — `list(frozenset) != list(copy.
deepcopy(frozenset))` is possible, confirmed directly on a real
`SharedRule.members` object from an actual run. `rules/dynamics.py::
monitoring_round` iterates `list(rule.members)` while consuming one RNG
draw per element in that order, so a deep-copied fork could pair
different agents with different draws than the original would have —
Stage 6's own sham intervention (identical-state-copy, which MUST match
`no_intervention_control` exactly) caught this on its very first smoke
check (0/1 seeds matched), exactly the job that sham was designed to
do. Root-caused via RNG-call-log instrumentation (the same technique
that found the transmission bug above). Fixed not by patching the
deepcopy path but by eliminating it from Stage 6's pipeline entirely:
since two independent `Simulation(config)` builds, each replayed the
same steps, are already proven byte-identical, every Stage 6
intervention (sham included) now gets its own fresh rebuild rather than
a fork of a live object. `core/state_checkpoint.py`'s `fork`/`fork_and_
finish` primitives were kept (correct and tested for the general case)
but now carry an explicit docstring caveat. Standing regression guard:
`tests/test_level13b_state_checkpoint.py::TestForkFrozensetOrderCaveat`
(built against a REAL `SharedRule.members` object, after a first attempt
using a synthetic frozenset failed to reliably reproduce the
phenomenon — disclosed in that test's own docstring) plus `tests/
test_level13b_stage6_history_erasure.py::TestAnalyzeShamValidation`
(task #124's own addition, re-confirming the sham match at small scale
independent of the synthetic-object-level test).

No conclusion in `docs/level1.3b_scientific_note.md` or `docs/
level1.3b_decision_gate_report.md` is drawn from pre-fix data for
either bug; pre-fix outputs were never persisted as final results for
either.

## 5. A real, disclosed gap found and closed by task #124

All 11 Level 1.3b stage scripts (Stages 0-10) had, before task #124,
ONLY an inline `run_smoke_test` function each — no dedicated `pytest`
-collected test file exercised any of their own real machinery at small
scale, a genuine drift from Level 1.3's own precedent (one dedicated
test file per stage). Closed for all 11 stages: `tests/test_level13b_
stage{0..10}_*.py`, 100 tests, each exercising the real stage script's
own functions (config-building, manipulation checks, mutators, ledger
views) on 1-4 real simulation runs. Full account, including five own
test-authoring bugs found and fixed while writing these files (a wrong
assumption about Stage 3's own ordering-onset sets; a docstring-vs-code
count mismatch in Stage 9's `ALL_COMPONENTS`; two incomplete Stage 10
test fixtures; a frozen-dataclass mutation attempt; numpy-bool vs.
Python-bool `is`-comparison failures): `dev_mem/status_update.md`'s own
task #124 entry.

## 6. Known limitations, disclosed rather than hidden

- **Every stage ran at a disclosed, session-budget-scaled sample size**,
  stated as Section 8/13's own MINIMUM in the frozen manifest (Stage 4:
  48×5=240 of a preferred 72-96×6-8; Stage 8: 24×4=96 of a preferred
  36-48×4-6), not adjusted after seeing results.
- **Stage 5's persistence diagnostics and Stage 6's history-erasure
  interventions both operate at one representative cell**
  (`entrenchment=moderate`, `legitimacy=dual`,
  `stratum=medium_feasibility`), not the full Stage 3 factorial.
- **`condition_rank_stability` is degenerate at only 2 ranked
  conditions** (Stage 5 Part A compares exactly `security_first` vs.
  `coevolution`) — returns a trivial ±1.0 for every seed, disclosed as
  an under-specified diagnostic for a 2-condition comparison rather than
  an informative result.
- **H6's legitimacy-channel effect is substantially construction-
  driven**: `performance_legitimacy`/`procedural_legitimacy` are
  literal components of the S_obs/Z_obs composites they are measured
  against (`docs/level1.3b_scientific_note.md`'s own H6 section).
- **Stage 9's S_obs-Z_obs coupling is real but sensitive to weighting**:
  the milestone's own equal-weight convention gives r≈0.264; an equally
  defensible PCA-weighted alternative gives r≈0.136 — roughly half.
  `observer/sz_obs.py` was not modified; both variants are reported
  side by side, per Stage 9's own frozen rule.
- **Stage 8's discrete-vs-continuous fresh-data comparison uses two
  metrics that are not on a common scale** (log-likelihood for the
  discrete candidate, reconstruction error for the continuous one) —
  `docs/level1.3b_decision_gate_report.md` §4's own disclosed gap, one
  of that report's four concrete "what would change this verdict"
  items.
- **`docs/level13b_preregistration.md`'s own filename inconsistency**
  (§1 above) — left as-is rather than renamed mid-milestone.

## 7. Final whole-suite confirmation

```
python3 -m pytest -q -W error -p no:cacheprovider
```

was re-run in full as the closing verification step for this report
(not merely inferred from per-task runs), confirming no regression
exists anywhere in the codebase at the moment this milestone's
documentation set closes. Result: **2047 passed, 6 skipped, 0 failed, 0
warnings**, wall time 1330.25s (22:10). This is exactly 178 more
passing tests than the 1869 passed at the Level 1.3b preflight baseline
(§2) — matching the per-file tally (178) exactly, with no discrepancy
to disclose this time (unlike Level 1.3's own one-test bookkeeping gap).

## 8. Stopping-rule checklist (`STOPPING_RULE["final_report_must_state"]`)

Restated here explicitly, item by item, per the frozen manifest's own
requirement — each cross-references where the full evidentiary
treatment lives:

1. **`bargaining_repair_status`**: repaired and confirmed at scale —
   H1 supported (scientific note §H1); 166/240 (69.2%) Stage 4
   activation, 20/24 (83%) Stage 2 calibration cells in target range,
   no generative parameter change needed.
2. **`sequence_effect_significance`**: real but modest and direction-
   inconsistent across ordering pairs — H2 weakly supported (scientific
   note §H2); 24.1%/32.4% of Stage 3's 108 matched contrasts CI-
   significant on S_obs/Z_obs respectively.
3. **`equalization_survival`**: survives, and grows — decision gate §3
   (`equalized` counterfactual's gap grows from 0.027 to 0.077 across
   windows despite exposure held exactly constant).
4. **`entrenchment_moderation`**: not supported as a monotonic dose-
   response on S_obs/Z_obs, though the entrenchment mechanism itself
   and its causal, persistent Stage 6 effect are both real — H4
   (scientific note §H4).
5. **`erasure_reduction`**: erasure (and reversal, and equalization)
   INCREASE divergence over time, not reduce it — sham-validated,
   growing, non-decaying (scientific note §H5, decision gate §2/§6).
6. **`discrete_vs_continuous_generalization`**: both candidates
   generalize non-catastrophically to fresh data this milestone (unlike
   Level 1.3's own sharp discrete-model collapse), on metrics that are
   not on a common scale — decision gate §4.
7. **`fresh_confirmation_support`**: H7 supported on its literal
   comparison bar (positive +3.11 gap vs. Level 1.3's own negative
   -1.29-vs--6.05), with the important qualification that a positive
   gap against a k=1 null is a weak discreteness signal on its own
   (scientific note §H7, decision gate §4).
8. **`s_obs_z_obs_coupling_nature`**: real, modest (r≈0.26), not
   explained by ecological stratum or any single component, not
   cleanly separable into 2 factors matching the S/Z split, sensitive
   to equal- vs. PCA-weighting (scientific note, nulls/anomalies).
9. **`exact_decision_gate_outcome`**: **D_persistent_continuum**
   (`docs/level1.3b_decision_gate_report.md` §7), reached independently
   of Level 1.3's own prior D verdict, per the stopping rule's own
   requirement not to silently promote it.
10. **`nulls`**: `response_cost` had zero measurable effect on
    activation (Stage 2); `condition_rank_stability` degenerate at n=2
    conditions (Stage 5) — scientific note, nulls/anomalies section.
11. **`anomalies`**: `gmm_k1_to_8` vs. `unequal_covariance_mixtures`
    ARI=1.0 (non-independent, not corroborating evidence); Stage 9's
    PC1 mixes both legitimacy channels rather than splitting cleanly by
    S/Z axis — scientific note, nulls/anomalies section.
12. **`limitations`**: §6 above, in full.
13. **`exact_test_and_run_counts`**: 178 new tests (§2), 2047 passed/6
    skipped final suite (§7); run counts by stage — Stage 0: 20+15=35
    comparison runs; Stage 1: 2 representative + 1 hand-computed
    microcase; Stage 2: 96 (24 cells × 4 seeds); Stage 3: 216; Stage 4:
    240; Stage 5: 80 (16+16+48); Stage 6: 72 (12×6); Stage 7: 0 new
    simulation runs (fits Stage 4's own pool); Stage 8: 96; Stage 9:
    240 (deterministic re-run of Stage 4's own seeds); Stage 10: 24.
14. **`next_recommended_decision`**: per `docs/level1.3b_decision_gate_
    report.md` §8's own four concrete items — extend the tested k range
    past 8 to test whether the BIC drop at the k=7→k=8 boundary is
    genuinely still-improving; build a common discrete/continuous
    fresh-data comparison metric; extend Stage 5/6 beyond their single
    representative cell to the full Stage 3 factorial; build a genuine
    multi-condition cluster-assignment-stability diagnostic for H3.
    None of these begin Level 1.4 or modify the paper repository, per
    this milestone's own stopping rule.

## 9. What remains

Final verification pass and sync of every new/modified Level 1.3b file
to the user's local machine (task #127) — the device bridge was
reported not connected at every prior check this milestone; this report
does not resolve that, it is task #127's own job.
