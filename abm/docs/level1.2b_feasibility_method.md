# Level 1.2b Feasibility Method Note — Sections 6-7

Full account of `observer/feasibility_ratios.py` (Work Package B,
Section 6) and `experiments/level12b_stage_c_feasibility_map.py` (Work
Package C, Section 7). See `docs/level1.2b_ecological_accounting.md`
for the ledger this all sits on top of, and
`docs/level1.2b_scientific_note.md` for how the feasibility envelope
fits into the milestone's overall findings.

## 1. Purpose

Level 1.2b stratifies its main discovery design (Work Package E) by
the ecological supply/demand ratio **ex ante** — never from a
realized, post-hoc governance outcome — so the joint design
deliberately spans structurally-stressed, boundary, and
potentially-sustainable ecological conditions. This is a direct
response to Level 1.2's own limitation: its 12×2=24-run design sampled
ecological parameters without any such stratification and its
near-universal collapse floor erased most of the institutional
variation a discovery pipeline needs to find anything.

## 2. Three ratios, three distinct roles

- **`structural_feasibility_ratio`** (Section 6.1) — a pure function
  of configuration: no RNG, no simulation run. Max-sustainable-yield
  regeneration (`patch_regen_rate * capacity / 4`, the logistic-growth
  MSY at `R=K/2`, summed across patches) divided by `population_size *
  subsistence_cost` (the bare mandatory floor — deliberately excludes
  every discretionary/institutionally-contingent cost, so it never
  assumes optimistic endogenous cooperation in either direction).
- **`expected_pressure_ratio`** (Section 6.2) — same MSY numerator,
  but the denominator adds `population_size * E[extraction request]`,
  where the expectation uses `agents/ecological_policy.py`'s own
  documented `decide_ecological_action` equations evaluated at the
  configured mean trait values and a preregistered neutral occupancy
  of 0.5 (the same midpoint the MSY assumption itself uses, so neither
  ratio favors abundance or scarcity a priori). A maintenance-inclusive
  sensitivity variant is also reported (Section 6.2's required
  sensitivity analysis). An optional Monte Carlo cross-check
  (`monte_carlo_expected_h_m`) draws from a dedicated observer-only RNG
  (seed root `0x12BFEA5`, never `config.seed`, never `core/rng.py`'s
  `STREAM_REGISTRY`) — confirmed empirically independent of the
  simulation's own seed and numerically close to the closed-form
  estimate.
- **`realized_balance_timeseries`** via `run_with_realized_balance_
  tracking` (Section 6.3) — a diagnostic only, never a design
  variable. Wraps each patch's own `regenerate()` bound method purely
  to capture its already-computed, already-discarded per-step return
  value (only the whole-run cumulative counter otherwise survives on
  `ResourcePatch`) — no simulation or patch behavior changes, verified
  by a same-seed with/without-tracking event-count-equality test.
  Reports fraction of steps below ratio 1, longest deficit episode,
  count of deficit episodes, cumulative unmet extraction demand,
  post-burn-in mean ratio, and final-step patch-heterogeneity
  coefficient of variation.

**Why three, not one**: `structural_feasibility_ratio` is the honest
worst-case bound (assumes zero behavioral extraction beyond
subsistence); `expected_pressure_ratio` is the more realistic ex-ante
prediction that accounts for expected behavioral demand;
`realized_balance_timeseries` is the only one of the three that
requires a simulation to run at all, and exists purely to validate the
other two against what actually happens, never to define the design's
own strata (Section 6's own ex-ante-only stratification requirement).

## 3. The feasibility-map experiment (Work Package C, Section 7)

Latin Hypercube design over 9 columns (`patch_regen_rate`,
`patch_capacity`, `patch_initial_fraction`, `subsistence_cost`,
`ecological_harvest_unit`, `maintenance_efficiency`,
`shock_interval_steps`, `shock_magnitude`, and a population/patch-ratio
selector thresholded into 2 discrete combos — 20 population/4 patches
vs. 60 population/4 patches, satisfying Section 7's "≥2 population/
patch combos" categorically rather than multiplicatively).
`n_parameter_points=30`, `seeds_per_point=4`, `total_runs=120`,
`n_steps=400`. Institutional design held broad-but-fixed
(`SimulationConfig.level12_complete`'s own defaults, identical across
every point) — Work Package C's own scope is the ecological envelope
only; crossing it with institutional variation is Work Package E's
job. Design generated, saved, and SHA-256 hashed
(`outputs/level12b_stage_c_feasibility_map/design.json` +
`design_hash.txt`) before any run executed.

**Result**: 120/120 runs, 0 failures. `outcome_counts = {"other": 50,
"collapse": 52, "saturation": 18}` — a genuinely informative envelope
(`envelope_failure=False`, Section 7's own stop condition —
"every point collapses/saturates" — not triggered). Ex-ante-vs-realized
correlation (Section 7's required analysis): **`ρ_expected` (Pearson
r≈0.84) predicts realized ecological pressure substantially better
than `ρ_struct` (r≈0.48)** — an expected, un-tuned finding
(`ρ_expected` incorporates behavioral extraction demand at neutral
trait expectations; `ρ_struct` only physical supply vs. the bare
subsistence floor).

**A near-miss, disclosed as a caution.** An early version of the
outcome classifier tried to reconstruct patch occupancy from a coarse
supply-magnitude proxy and labeled literally every one of the first
120 runs "other" — including runs with `fraction_below_one=1.0` for
the entire 400-step run, an unambiguous collapse. Caught by manually
inspecting one extreme point's raw records before trusting the
aggregate counts, not by a test. Replaced with a classifier built
directly on Work Package B's own realized-balance diagnostics
(`mean_ratio_post_burn_in`, `fraction_of_steps_below_one`), both
simpler and correct. Recorded here as a standing caution for later
analysis stages: aggregate outcome-count summaries should always be
spot-checked against a few raw per-run records before being trusted.

## 4. Verification

`tests/test_level12b_feasibility_ratios.py` (22 tests: hand-computed
ratio values, undefined-denominator-is-NaN-not-zero cases, Monte Carlo
cross-check and independence, realized-balance episode/cumulative-
unmet/heterogeneity hand-computed cases, naming discipline) and
`tests/test_level12b_feasibility_map.py` (21 tests: run-arithmetic
minimums, design determinism/hashing, ≥2 population/patch combos,
broad-but-fixed institutional design held constant, shock construction,
outcome classification incl. the exact collapse case the near-miss
fix addresses, correlation helper, skip-if-absent check against the
executed `results.json`).
