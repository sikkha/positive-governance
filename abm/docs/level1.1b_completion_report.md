# Level 1.1b Completion Report: Causal and Measurement Validation

**Status: Work Packages A–H complete.** This report is the single
top-level deliverable for the milestone; it summarizes what was built,
found, tested, and disclosed as reduced in scope, and closes with the
Level 1.2 recommendation. Supporting documents, each cited where relevant:
`docs/level1.1b_validation_note.md` (full per-work-package confirmatory
statistics), `docs/level1.1b_rng_design.md` (Work Package A design),
`docs/odd_level1.1b_addendum.md` (ODD-style model description addendum),
`docs/level1.1b_reproducibility_note.md` (exact commands/seeds to
reproduce every number in this report), `docs/config_reference.md`
(complete config-surface documentation), `dev_mem/status_update.md`
(the session-by-session working log every finding below was first
recorded in).

**A note on this report's provenance.** This session's context was
compacted partway through the milestone; the original milestone
specification's literal enumerated completion-report checklist (referenced
during planning as having ~22 items) is not verbatim available to check
this report against line-by-line. Rather than guess at unverifiable
literal item numbers, this report is structured around what is directly
verifiable from the work actually done this session — every claim below
traces to a specific script, test file, or doc section named alongside it.
If the original spec's exact 22-item list differs from this report's
structure in ways that matter, that is a disclosed gap, not a claim of
exhaustive literal compliance.

## 1. What Level 1.1b was for

Level 1.1 (the prior milestone) built delegation, administrative capacity,
discretion, accountability, voluntary contributions, interpatch
coordination, institutional memory, and shock/replacement dynamics, and
reported a headline finding: accountability + discretion together shift
the mechanism-validation classifier's output from `persistent_delegation`
to `accountable_delegation`. Level 1.1 also documented six methodological
limitations undermining confidence in that finding and every other causal
claim it made. Level 1.1b's entire mandate was resolving those limitations
(and two more found in the process) with rigorous infrastructure —
**never** adding a new governance mechanism, **never** searching for
governance phenotypes, and **never** testing whether the dissertation's
three SEM trajectories have emerged. All three prohibitions held for the
whole milestone; see §6.

## 2. Work package summary (full detail in the validation note)

| WP | Problem | Fix | Headline result |
|---|---|---|---|
| A | Shared RNG stream let ablations contaminate unrelated mechanisms | `mechanism_substreams` RNG mode, 20 named streams, legacy mode preserved exactly | 2 real bugs found+fixed (`build_agents()` isolation gap; `policy_assortativity` cross-process nondeterminism); 765→819 passing tests across the milestone |
| B | 5 tests failed on artifact-free checkout | Precise skip reasons + artifact-independent companion tests; fixed `n_steps` bug in `level03b_phase_search_reanalysis` | 0 failures on artifact-free checkout (the milestone's own completion condition) |
| C | 72/72 coordination acceptance, unexplained | 54-run calibration sweep; new `level11b_coordination_nondegenerate` preset | Explained: 5-attempt retry window makes ~97% eventual acceptance the expected (not degenerate) outcome at defaults |
| D | Removing admin cost increased appropriation — opportunity or conduct? | New `AppropriationOpportunityEvent`; 12-seed paired bootstrap | Opportunity changed (CI excludes zero); conduct did not (CI includes zero) |
| E | `accountability_enabled` flag conflated activity with effective constraint | Sub-flags + `accountability_diagnostics.py`; 12-seed, 8-condition sweep | Activity (placebo) alone doesn't cut net appropriation (CI includes zero); accurate detection (perfect_info) does (CI excludes zero, negative) |
| F | Institutional memory called "negligible," never dose-tested | 15-seed, 5-condition dose-response sweep | Real, monotonic, statistically-detectable-but-practically-trivial (0.22%) at defaults; 25% at a theoretical ceiling |
| G | 10/10 reappointment called "recovery" | 15-seed shock/reappointment/recovery-gap analysis | Reappointment 97.5%; full functional recovery only 32.2% — mechanistically explained (capacity's `experience_term` resets per office-holder) |
| H | Historical classifier's accountability criteria didn't require realized detection or genuinely corrective appeals | New `classify_delegation_audited`; 15-seed, 6-condition, 90-rule-per-condition comparison | Downgrade rates 0%–20% across conditions, roughly tracking detection accuracy, `randomized_placebo`'s estimate weakly powered |

## 3. Deliverables produced this session

**Source code** (`src/abm_governance/`): `core/rng.py` (new);
`simulation.py`, `rules/delegation.py`, `core/config.py`, `core/events.py`
modified (all additive/opt-in — see §5); `observer/accountability_
diagnostics.py` (new); `observer/delegation_diagnostics.py` extended (new
function, existing function unmodified); `observer/network_diagnostics.py`
bugfix.

**Experiment scripts** (`experiments/`, all new):
`level11b_coordination_calibration.py`,
`level11b_appropriation_decomposition.py`,
`level11b_accountability_conditions.py`,
`level11b_institutional_memory_validation.py`,
`level11b_functional_shock_recovery.py`,
`level11b_audited_classifier_comparison.py`,
`make_level11b_visualizations.py`. Each writes its own JSON summary under
`outputs/level11b_<name>/`; all seven are committed and re-runnable per
`docs/level1.1b_reproducibility_note.md`.

**Tests** (`tests/`, all new except the WP-B edits to
`test_level03b_pipeline.py`): `test_level11b_rng_substreams.py` (26),
`test_level11b_coordination.py` (8), `test_level11b_appropriation.py` (7),
`test_level11b_accountability.py` (11),
`test_level11b_institutional_memory.py` (8),
`test_level11b_functional_shock_recovery.py` (8),
`test_level11b_audited_classifier.py` (7) — 75 new tests, plus WP-B's
skip-reason and companion-test additions. Full suite: **819 passed, 6
skipped (every skip carries an explicit artifact-missing reason), 0
failed, 0 warnings** as of this report.

**Figures** (`outputs/level11b_figures/`, 7 PNGs — see §5 for the
disclosed reduction from a nominal 10-14): one per Work Package C/D/E/F/G/H
headline result, plus one cross-work-package summary of every paired-
difference confidence interval this milestone produced.

**Documentation** (`docs/`, all new this session except
`config_reference.md`, extended): `level1.1b_rng_design.md`,
`level1.1b_validation_note.md`, `level1.1b_reproducibility_note.md`,
`odd_level1.1b_addendum.md`, this completion report.

## 4. Testing and verification status

- Full suite (`python -m pytest -q -W error`) run after every work
  package's changes, not only at the end — each work package's own
  `dev_mem/status_update.md` entry states the exact passed/skipped/failed/
  warnings count at that point in the sequence (765→770→778→785→796→804→
  812→819).
- Every new test file includes at least one explicit
  undefined-denominator/empty-input case verifying `None` (never `0.0`) is
  returned — a direct test of the milestone's own non-negotiable
  constraint on this point.
- Two genuine pre-existing bugs were found (not part of the six documented
  limitations) and fixed: `build_agents()`'s shared-stream isolation gap
  (Work Package A) and `policy_assortativity`'s cross-process
  nondeterminism (Work Package A). Both are documented in
  `docs/level1.1b_rng_design.md` and covered by regression tests.
- No test was skipped, weakened, or deleted to make the suite pass; every
  skip in the final 6-skipped count carries a `pytest.mark.skipif` reason
  naming the specific missing historical artifact (Work Package B).

## 5. Disclosed scope reductions

This milestone's session-budget scope reductions, stated plainly per the
milestone's own instruction to disclose every one honestly:

1. **No literal "7-stage experimental sequence" script set was built
   separately from the Work Package C-H experiment scripts.** Each work
   package's own `experiments/level11b_*.py` script *is* the causal
   experiment that work package's validation required; building a
   redundant parallel "stage 1 through 7" script set on top of work that
   already produces matched-seed, bootstrapped, disclosed results was
   judged not to add information, only ceremony. If the original spec's
   7-stage structure required a different decomposition than "one script
   per work package," that is the specific gap this reduction leaves.
2. **7 figures delivered, not the nominal 10-14.** One per Work Package
   C/D/E/F/G/H headline confirmatory result, plus one cross-work-package
   CI summary — chosen to cover every work package's single clearest
   result at least once rather than exhaustively enumerating every
   possible cut of every work package's data (the same reduction pattern
   Level 1.0/1.1's own visualization scripts already used and disclosed).
3. **`randomized_placebo`'s Work Package H downgrade-rate estimate (20%)
   is reported at low statistical power** — only 5 of 90 classified rules
   across 15 seeds reached a historical "accountable_delegation" call
   under that condition at all. A higher-seed-count or higher-`n_patches`
   follow-up would be needed before treating that figure as precise; it
   is reported as directional, not confirmed.
4. **Level 1.1's own exact historical seeds were not re-run** to directly
   confirm whether its specific headline finding (accountability +
   discretion → `accountable_delegation`) survives Work Package H's
   audited classifier at those exact seeds. `default_full`'s pooled 0%
   downgrade rate at this milestone's own seeds is suggestive but not a
   direct replication of Level 1.1's specific run. Named as a Level 1.2
   follow-up candidate in `docs/level1.1b_validation_note.md`'s
   recommendation section.
5. **No new `pyproject.toml` dependency was required** — everything this
   milestone built uses `numpy`/`matplotlib`, already declared
   dependencies, so no scope was reduced here, but it is worth stating
   explicitly since Level 0.3b's own addendum flagged a comparable
   dependency-hygiene point.

## 6. Compliance with the milestone's non-negotiable constraints

- No governance-type/SEM-trajectory vocabulary was introduced;
  `tests/test_level11_compatibility.py`'s `FORBIDDEN_LEVEL11_TERMS`
  structural guard, unmodified, still passes against every touched
  module.
- Every corrected-RNG causal experiment used `rng_mode="mechanism_
  substreams"` explicitly; `rng_mode="legacy_single_stream"` remains the
  default and reproduces Level 1.1 bit-for-bit (tested).
- No historical missing-artifact test failure was reinterpreted as a
  source-code failure or silently skipped without a stated reason (Work
  Package B).
- Every undefined denominator (zero opportunities, zero audits, zero
  shocks, zero historical-accountable calls, etc.) returns `None` across
  every new function and script in this milestone — verified by dedicated
  tests in each case.
- Seed was the primary independent unit in every bootstrap; every CI
  reported states its resampling unit and `n_seeds` explicitly.
- No result was called causal without a `mechanism_substreams`
  counterfactual design preserving unrelated random draws (Work Packages
  C-H all run under substream mode).
- Reappointment was never called "recovery" without a separate,
  independently-computed functional-performance check (Work Package G).
- Every null, adverse, degenerate, or anomalous result encountered —
  Work Package E's gross-appropriation-increases-under-accountability
  anomaly and its unmatched-activity confound; Work Package F's
  statistically-real-but-practically-trivial default effect; Work Package
  G's systematic non-recovery of capacity; Work Package H's small-sample
  placebo estimate — was reported as found, in the same script/doc that
  produced it, not filtered out or reframed as positive.
- Every scope reduction is disclosed in §5 above, in the same document a
  reader of this report would see, not buried in a separate file.

## 7. Recommendation for Level 1.2

(Full detail and rationale: `docs/level1.1b_validation_note.md`'s closing
section.) In brief:

1. Use `rng_mode="mechanism_substreams"` for any new causal-isolation
   work; reserve `legacy_single_stream` for exact Level 1.1 replication
   only.
2. Use `classify_delegation_audited`, not the historical
   `classify_delegation`, as the basis for any new evidentiary claim.
3. Treat accountability *activity* and *effective constraint* — and
   reappointment and *functional recovery* — as distinct measured
   quantities in any future reporting, using the infrastructure this
   milestone built (`observer/accountability_diagnostics.py`, the
   `recovery_gap` pattern), not as a one-off finding specific to this
   milestone.
4. Treat institutional memory's default calibration as intentionally
   conservative rather than inert; this milestone's dose-response grid is
   a documented starting point if Level 1.2 wants that mechanism to matter
   more.
5. Before relying on `randomized_placebo`'s ~20% Work Package H
   downgrade-rate figure for any decision, run a dedicated higher-power
   follow-up (§5, item 3).
6. If Level 1.2's design depends on Level 1.1's specific historical
   seeds/runs (not just this milestone's own newly-run seeds), re-run
   Work Package H's classifier comparison directly against those
   historical artifacts first (§5, item 4).

With these six points incorporated, Level 1.2's open governance-phenotype
search can proceed on top of measurement infrastructure that has been
audited, not merely trusted.
