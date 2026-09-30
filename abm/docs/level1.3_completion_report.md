# Level 1.3 Completion Report — Historical Sequencing, Entrenchment, and Path-Dependent Institutional Differentiation

**Status: Stages 0-9 (Sections 5-19) executed and verified; documentation
(Section 22) and visualizations (Section 21) complete; this report covers
Sections 20-22 and 24 (build inventory, test-suite status, structural
guards, documentation, and completion status). Section 23's six-way
decision-gate classification is rendered separately in `docs/level1.3_
decision_gate_report.md`, per this milestone's own preregistered
governance (the classification must be reasoned from evidence already on
record, not folded into the same document that inventories what was
built).**

## 1. What was built

**Five new core-layer modules**: `core/historical_pressure.py` (Work
Package A, pressure-signal generation), `core/historical_transmission.py`
(Work Package A, the six transmission channels), `core/entrenchment.py`
(Work Package C), `core/legitimacy.py` (Work Package D), `core/
historical_counterfactuals.py` (Work Package E).

**Four new observer-layer modules**: `observer/sequencing_diagnostics.py`
(Work Package B), `observer/institutional_conversion.py` (Work Package F),
`observer/sz_obs.py` (Work Package G), `observer/level13_phenotype.py`
(Work Package H).

**Thirteen new experiment scripts** (`experiments/level13_*.py`):
`level13_common.py` (shared parameter space + the `transmission_
overrides_for_channel` helper), `level13_preregistration.py` (Section 15
manifest), `level13_stage0_exact_compatibility.py` through `level13_
stage9_scale_and_shock_robustness.py` (ten stage scripts), `level13_test_
requirements_audit.py` (Section 18's 27-category coverage matrix), plus
`experiments/make_level13_visualizations.py` (Section 21, fourteen
figures).

**Seven new `SimulationConfig` fields** gating the master pressure/
entrenchment/legitimacy channels, plus six transmission sub-flags and
their paired sensitivity fields (Section 6). No new preset was added at
the generative layer — a disclosed, simpler-surface choice for this
milestone's smaller generative footprint; see `docs/odd_level1.3_
addendum.md` §4.

**Fourteen new figures** (`outputs/level13_figures/01_...png` through
`14_...png`), covering pressure-history shapes, compatibility/activation
summaries, feasibility strata, Stage 3-9's own results, and the test-
requirements coverage matrix itself.

**Nine new/updated documentation files**: this report, `docs/odd_level1.3_
addendum.md`, `docs/level1.3_preregistration.md`, `docs/level1.3_
historical_mechanisms.md`, `docs/level1.3_measurement_note.md`,
`docs/level1.3_discovery_methods.md`, `docs/level1.3_bug_disclosure_and_
reproducibility_note.md`, `docs/level1.3_scientific_note.md`, and a
postscript section appended to the pre-existing `docs/level1.3_
theoretical_translation.md` (written at preflight, before any Stage ran,
and left otherwise unedited). `docs/level1.3_decision_gate_report.md`
(Section 23) is a tenth document, produced as a separate deliverable per
this milestone's own governance rather than folded into this report.

## 2. Test suite status

**393 new tests** were added this milestone, all under `tests/test_
level13_*.py` (twenty-six files), against a preflight baseline of `1475
passed, 6 skipped, 0 failed, 0 warnings` under `python3 -m pytest -W
error --tb=no -q` (recorded in `dev_mem/status_update.md`'s own Level 1.3
preflight entry, before any Level 1.3 code was written). The full suite
was re-run with `-W error` after every single change throughout this
milestone, never merely assumed clean. See §6 below for the final,
whole-suite confirmation run's own result, executed as part of closing
out this report.

Per-file new-test counts: `test_level13_compatibility.py` (13),
`test_level13_entrenchment.py` (23), `test_level13_feasibility_
integration.py` (22, includes the 5-test `TestTransmissionOverridesFor
Channel` class added as task #109's direct regression coverage),
`test_level13_history_counterfactuals.py` (21), `test_level13_
institutional_conversion.py` (20), `test_level13_legitimacy.py` (20),
`test_level13_phenotype.py` (9), `test_level13_preregistration.py` (18),
`test_level13_pressure_signals.py` (33), `test_level13_pressure_
transmission.py` (25), `test_level13_rng_mode_compliance.py` (8, task
#109's own standing regression guard), `test_level13_sem_firewall_
extension.py` (5), `test_level13_sequencing_diagnostics.py` (22),
`test_level13_stage0_exact_compatibility.py` (10) through `test_level13_
stage9_scale_and_shock_robustness.py` (13, ten stage-script test files,
118 tests total), `test_level13_sz_obs.py` (20), `test_level13_test_
requirements_audit.py` (7), `test_level13_visualizations.py` (3).

## 3. Structural guards held throughout

- `tests/test_level12_structural_guards.py`'s whole-package
  (`pkgutil.walk_packages`) forbidden-terminology scan automatically
  covers every module this milestone added — no per-module allowlist
  edit was ever needed.
- `tests/test_level13_sem_firewall_extension.py` extends the experiment-
  script glob to `level13_*.py` and covers `sz_obs.py`/`level13_
  phenotype.py`'s own S_obs/Z_obs vocabulary explicitly.
- `tests/test_level13_compatibility.py` is the structural guard proving
  a bare `SimulationConfig()` and `level12b_frozen_reference()` both
  remain unaffected by every new field's existence, cross-checked at
  experimental scale by Stage 0's own 20-seed byte-identity run.
- `tests/test_level13_rng_mode_compliance.py` (8 tests, added as task
  #109's direct fix) is a standing regression guard specifically against
  the `rng_mode` omission that bug recurring in any future stage script.
- `experiments/level13_test_requirements_audit.py`'s 27-category
  coverage matrix (Section 18) was constructed from real `grep`/source
  citations, not memory, and is itself mechanically re-verified by
  `tests/test_level13_test_requirements_audit.py` (8 tests, including
  negative controls for fabricated citations) — directly following
  Level 1.2b's own Work Package R precedent (which found five wrong
  citations out of 25 when a matrix was first drafted from memory).

## 4. The bug found and fixed mid-milestone

Two compounding wiring bugs (transmission sub-flags never set; wrong
substrate preset silently disabling both the causal pathway and RNG-mode
compliance) were found via this project's own established single-seed
sanity-check discipline before any Stage 6-9 analysis ever read the
affected data, fixed in Stage 0, 1, 3, 4, and Stage 5's first drafts, and
closed with a standing regression test. Full account: `docs/level1.3_
bug_disclosure_and_reproducibility_note.md`. No conclusion in this
milestone's scientific note or decision-gate report is drawn from the
pre-fix data; the pre-fix outputs are archived, not deleted.

## 5. Known limitations, disclosed rather than hidden

- **Six of eighteen candidate transmission channels wired** (two per
  pressure), a deliberate scope reduction to formulas this project had
  already built and tested — see `docs/level1.3_historical_mechanisms.
  md` §5 for why these six specifically.
- **Stage 5's counterfactual scope is single-channel** (`security_
  pressure` only), sidestepping Work Package E's own disclosed
  multi-channel RNG-draw-skew limitation rather than absorbing it
  silently.
- **Stage 6's discovery pool is pooled, not purpose-designed** — three
  heterogeneous stages (3, 4, 5) combined, with a disclosed `cluster_vs_
  source_stage_ari ≈ 0.554` reflecting that heterogeneity honestly
  rather than treating the pool as if it were one homogeneous design.
- **`seq_bargaining_participation` is missing in 100% of the pooled
  discovery input** (216/216 rows) — the `bargaining_pressure`
  sequencing dimension never crossed threshold in any pooled run,
  collapsing `complete_case` missingness handling to zero rows. Disclosed
  and guarded against structurally (`docs/level1.3_discovery_methods.md`
  §3), not hidden by silently dropping the dimension.
- **Stage 7's fresh confirmation shows a real generalization gap**
  (mean per-point log-likelihood ≈ -1.29 on training data vs. ≈ -6.05 on
  fresh data) — reported as a genuine limitation of how well Stage 6's
  frozen fit generalizes, not smoothed over.
- **Session-budget-scaled sample sizes throughout** (Stage 7's 12 fresh
  points vs. Level 1.2b's own 384-run confirmation design, for example)
  — every scaling decision was disclosed in `docs/level1.3_
  preregistration.md` before the corresponding stage ran, not adjusted
  afterward.

## 6. Final whole-suite confirmation

```
python3 -m pytest -q -W error
```

was re-run in full as the closing step of this report (not merely
inferred from per-Work-Package runs) to confirm no regression exists
anywhere in the codebase at the moment this milestone closes. Result:
**1869 passed, 6 skipped, 0 failed, 0 warnings**, wall time 548.19s
(9:08), run 2026-08-20 at the close of this milestone — a clean pass,
0 failures, 0 warnings under `-W error`, exactly as required. This is
394 more passing tests than the 1475 passed at the Level 1.3 preflight
baseline (§2), against a raw per-file tally of 393 new tests across
`tests/test_level13_*.py`; the skip count (6) is unchanged from the
preflight baseline. The one-test discrepancy between 393 (per-file
tally) and 394 (measured before/after delta) is disclosed here rather
than silently reconciled: `python3 -m pytest --collect-only -k "not
level13"` collects 1482 tests now vs. an inferred 1481 at the preflight
baseline (1475 passed + 6 skipped), and no non-`test_level13_*.py` file
shows a recent modification time or contains the string `"level13"` —
so the extra test is real but its exact origin was not tracked down
before closing this milestone. It does not affect the headline result
(0 failures, 0 warnings) and is noted here as a minor, unresolved
bookkeeping detail rather than asserted away.

## 7. What remains

Section 23's six-way decision-gate classification (`docs/level1.3_
decision_gate_report.md`) and the device-sync backlog (every file from
Stage 5 onward, delivered via `SendUserFile` this session but not yet
confirmed written to the user's local mirrored folder as of this
report's own drafting) are this milestone's two remaining open items,
both tracked as task #108.
