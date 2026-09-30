# Level 1.2 Completion Report — Open Institutional Evolution and Blind Phenotype Discovery

**Status: complete, stopped for scientific review. Level 1.3 has not
started and should not start without a separate review decision** —
per this milestone's own explicit governing instruction and this
project's established convention (Level 1.0, 1.1, and 1.1b all stopped
identically at their own completion gates).

## 1. What was built

Seven generative work packages (Sections 5, WP A-G): institutional
component representation (`rules/institution.py`), local institutional
observation (`rules/observation.py`), component-wise transmission
(`rules/transmission.py`), migration and membership selection
(`rules/migration.py`), differential persistence
(`observer/differential_persistence.py`), institutional scaling
(`rules/scaling.py`), and environmental heterogeneity (config
additions + one new `patch_quality_spatial_correlation` mechanism in
`environment/patches.py`).

Four observer-layer sections (6-9): a ten-dimensional phenotype vector
X=(C,E,L,D,M,R,S,F,V,H) (`observer/institutional_phenotype.py`),
temporal feature extraction (`observer/temporal_features.py`),
failure/viability classification (`observer/institutional_viability.py`),
and a blind (never SEM-informed) phenotype discovery pipeline
(`observer/phenotype_discovery.py`).

Two analytical sections (10-11): a twelve-criterion recurrence test
(`observer/recurrence_criteria.py`) and an inheritance-vs-convergence
test (`observer/convergence_tests.py`).

A full Stage 0-7 experimental program plus Section 13's causal
ablations and Section 14's SEM firewall audit (`experiments/
level12_*.py`, 9 stage/support scripts). Section 17's six new
`SimulationConfig` presets. Six new documentation files (this one plus
the ODD addendum, scientific note, preregistration note, discovery
methodology note, and causal ablation note) and updates to four
existing docs (`README.md`, `docs/config_reference.md`, `dev_mem/
project_vision.md`, `docs/odd_level1.1b_addendum.md`).

## 2. Test suite status

**1084 passed, 6 skipped, 0 failed, 0 warnings** at the close of this
milestone (`python -m pytest -q -W error`), up from 819 at the Level
1.2 preflight baseline (Level 1.1b's own closing number, reconfirmed
exactly before any Level 1.2 code was written). Reconfirmed after
every single Work Package, Section, and Stage throughout — never
merely assumed. Every new mechanism defaults to a verified byte-for-
byte no-op; the strongest single check is `tests/
test_level12_testing_requirements_audit.py`'s full end-to-end
integration test: a bare `SimulationConfig()` run through an actual
`Simulation` produces exactly zero of all six new Level 1.2 event
types and an empty institution registry.

## 3. Structural guards held throughout

- `tests/test_level12_structural_guards.py`: whole-package (`pkgutil.
  walk_packages`, not a fixed module list) forbidden-terminology scan
  — every module added this milestone is automatically covered.
- `tests/test_level12_sem_firewall.py`: milestone-level SEM firewall
  audit — auto-discovers and scans every `experiments/level12_*.py`
  file, confirms no SEM/dissertation-pattern data file exists anywhere
  in the repository, and includes a positive control proving the
  scanner cannot pass vacuously.
- Generative/observer separation: the pre-existing AST-based import-
  direction test continues to pass; every new observer module's own
  docstring states explicitly that it is never imported by `rules/` or
  `simulation.py`.

No SEM/dissertation data, label, or trajectory count was read,
imported, or referenced anywhere in this milestone's generative,
observer, or experimental code.

## 4. Findings (full detail: `docs/level1.2_scientific_note.md`)

**No recurrent institutional phenotype configuration was independently
supported** at this milestone's disclosed scale — a null result
replicated across two disjoint pooled samples (Stage 4: n=24, 0/76
candidates; Stage 5: n=12 fresh, 0/72 candidates) using an unmodified
discovery pipeline both times. This is reported exactly as the
milestone's own closing instruction requires: not as evidence against
any particular count (not zero, not one, not three), but as "the
evidence does not clear the preregistered bar at this sample size."

The dominant emergent dynamic instead was **near-universal ecological
collapse** under the full Level 1.1+1.2 mechanism set (22/24 Stage 3
runs, 11/12 Stage 5 runs, 8/8 Stage 6 scale-robustness runs), causally
implicated via matched-seed ablation (Section 13) in both
`migration_enabled` (modest, mixed effect, p=0.25 supplementary) and
`patch_regen_rate` (more consistent effect, p=0.039 supplementary) —
neither factor alone sufficient to make `viable` the typical outcome
at the tested population/duration scale.

## 5. Disclosed scope reductions (collected)

Every reduction below was recorded in its own script's docstring
BEFORE that stage ran, per Section 12/20's disclosure discipline (see
`docs/level1.2_scientific_note.md`'s own summary table for the full
list): discovery pipeline uses 3 of the fuller suggested candidate-
method menu; Stage 3's 24 total runs (12 parameter draws × 2 seeds) is
far short of a publication-scale sweep; Stage 5/6/7 all similarly
scaled to single-digit-to-low-double-digit seed counts; Section 13's
two ablations use n=8 matched pairs each.

## 6. Known limitations, carried forward explicitly

- **Small, collapse-skewed samples throughout.** With 22-24/24 and
  10-11/12 runs landing in `collapse` across the main pools, the
  *eligible-and-non-collapse* subset available for any future,
  larger-scale discovery attempt was very small in this milestone's
  own data (2/24 in Stage 3, 1/12 in Stage 5). A larger sample, or a
  parameter region deliberately favoring non-collapse outcomes
  (informed by, but not restricted to, this milestone's regen-rate
  finding), would be needed before a stronger discovery claim in
  either direction could be made.
- **Section 11's convergence-vs-inheritance framework** is fully
  implemented and tested but was not exercised at Stage 4/5's own
  seed-run unit of analysis (lineage IDs are not comparable across
  independent seed-runs — see `docs/
  level1.2_discovery_methodology_note.md` §7). A future within-run,
  multi-institution pooling analysis would need runs with materially
  more institutions per run than this milestone's ~4.
- **Stage 7's perturbation/transition test was inconclusive** by
  design (a floor effect — baseline already collapses regardless of
  shock). A future variant needs a baseline condition that itself
  reaches `viable`/`fragmented` reliably before a perturbation's
  marginal effect can be tested.
- **Wilcoxon p-values in Section 13 are supplementary, not
  confirmatory** — n=8 matched pairs is too small for a confident
  standalone significance claim, stated plainly rather than
  overclaimed.

## 7. Explicit stop condition

**Per this milestone's own governing instruction: do not start Level
1.3. Stop for scientific review.** This report, together with `docs/
level1.2_scientific_note.md`, constitutes that stopping point. Any
decision to proceed to Level 1.3 (correspondence analysis against the
dissertation's SEM trajectories, if ever authorized) requires a
separate, explicit review decision — exactly the same convention this
project applied at the close of Level 1.0, Level 1.1, and Level 1.1b.
