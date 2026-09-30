# Level 1.3 — Bug Disclosure and Reproducibility Note

**Status:** written after Stages 0-9 were completed and re-run. This is the
durable, formal record of task #109's two bugs — `dev_mem/status_update.md`
carries the same information as a working log entry; this document is the
citable, standalone account for anyone auditing this milestone who does not
want to read the whole session log.

---

## 1. Summary

Two wiring bugs were found (both before any Stage 6-9 analysis ever read the
affected data) and fixed in Stage 0, 1, 3, 4, and Stage 5's first drafts.
Stage 3 and Stage 4's original 72- and 96-run outputs are **archived, not
deleted**, and both stages were re-run with the fix before any downstream
work used their data. No conclusion in this milestone's own scientific note
(`docs/level1.3_scientific_note.md`) or decision-gate report is drawn from
the pre-fix data.

## 2. How it was found

Before running Stage 5's real 48-run experiment, this project's own
established precedent (every prior stage was sanity-checked on one seed
before committing to its full run) was followed: `_run_matched_triple` was
run on a single seed. The result was **byte-identical** event logs,
phenotype vectors, and S_obs/Z_obs across the base run and both
counterfactual re-runs (`erased`, `reversed`) — despite the underlying
pressure series being confirmedly, genuinely different (verified directly
against `Simulation.historical_state`). A pressure channel with zero causal
path into the model is not a plausible null result for a mechanism this
project spent five Work Packages (A-E) building; it was investigated rather
than accepted.

## 3. Bug 1 — transmission sub-flags never set

`core/historical_transmission.py`'s own module docstring already disclosed a
two-layer activation requirement (see `docs/level1.3_historical_mechanisms.
md` §4): each pressure's master `*_enabled` flag only gates whether its
**state series** is generated; a second, independently-defaulted-`False`
layer of six per-channel sub-flags gates whether that state has any
**behavioral** consequence. Stage 3, 4, and Stage 5's first drafts set only
the master flags.

Stage 1 was **not** affected — its own docstring explicitly, correctly
scoped itself to the master flags' state-generation claim only, deferring
transmission-sub-flag testing to Work Package A's own unit tests
(`tests/test_level13_pressure_transmission.py`).

## 4. Bug 2 — wrong substrate preset (the deeper one)

Fixing bug 1 alone was tried first and the same single-seed check **still**
came back byte-identical. Cause: Stage 3/4/5's first drafts all built their
configs on bare `SimulationConfig.level1_rule_formation_default()` — Level
1.0's own "every Level 1.1 mechanism at its no-op default" baseline
(`delegation_enabled=False`, `contribution_mode="none"`,
`interpatch_coordination_enabled=False`). Work Package A's transmission
channels nudge quantities that only exist when those Level 1.1 mechanisms
are active (a delegate's task-success probability, contribution compliance
willingness, a coordination-proposal probability) — with delegation off,
`_success_probability` (the one function `security_pressure`'s two channels
feed) never runs at all. Confirmed directly: `institutional_response_series`
showed `delegation`, `administrative_function`, `accountability`,
`bargaining_participation`, `cross_founder_reconstruction`, and
`interpatch_coordination` all summing to exactly `0.0` across a full
500-step run under the buggy config.

This also meant `rng_mode` was silently left at `SimulationConfig`'s own
class default, `legacy_single_stream` — violating the frozen preregistration
manifest's own `RNG_COMMITMENTS` ("mandatory for every Stage 0-9 run;
legacy_single_stream is never used this milestone") and undermining every
matched-seed comparison's own causal-isolation logic: under
`legacy_single_stream`, every named RNG stream maps to the *same* generator,
so draw *order* matters and enabling/disabling a mechanism can shift the
random draws consumed elsewhere — exactly the confound `mechanism_
substreams` (independent `SeedSequence` spawns per named stream) exists to
prevent.

Auditing every Level 1.3 stage script's `rng_mode` after this surfaced found
the same omission in Stage 0 (its comparison 1 only — comparison 2 already
used `level12b_frozen_reference()`, which sets it internally) and Stage 1,
neither of which has the substrate-preset problem but both of which still
violated the blanket manifest commitment.

## 5. Fix

- `experiments/level13_common.py::transmission_overrides_for_channel(channel)`
  — one shared helper returning both of a channel's own transmission
  sub-flags, set `True`. Every stage script now shares this one source of
  truth instead of hand-typing its own subset.
- Stage 3, 4, and 5 switched their base preset from `level1_rule_formation_
  default()` to `level12b_frozen_reference()` — brings the full Level
  1.1/1.2b institutional substrate active **and** `rng_mode=
  "mechanism_substreams"` in the same change — plus the transmission
  sub-flags.
- Stage 0's comparison 1 and Stage 1's `_BASE` dict got `rng_mode=
  "mechanism_substreams"` added explicitly.
- A standing regression guard was added afterward, under task #105:
  `tests/test_level13_rng_mode_compliance.py` (8 tests) — one per stage
  script that constructs a `SimulationConfig` directly, asserting `rng_mode
  == "mechanism_substreams"` on the actual object the script builds, so this
  exact class of omission cannot silently recur on a future edit.

## 6. Re-verification

The same single-seed Stage 5 sanity check, after both fixes, produced real
divergence: seed 7,000,000 showed `erased` vs. `base` |S_obs diff| ≈ 0.0097,
|Z_obs diff| ≈ 0.0082; `reversed` vs. `base` |Z_obs diff| ≈ 0.0051 — the
causal pathway is genuinely wired end to end.

## 7. Old (bugged) outputs — archived, not deleted

| File | Status |
|---|---|
| `outputs/level13_stage0_exact_compatibility/report_pre_rng_fix.json` | archived |
| `outputs/level13_stage1_activation/stage1_report_pre_rng_fix.json` | archived |
| `outputs/level13_stage3_sequencing_entrenchment_factorial/records_pre_transmission_fix.json` | archived |
| `outputs/level13_stage4_open_pressure_history_search/records_pre_transmission_fix.json` | archived |

Stage 5 never produced a bugged output at experimental scale — only the two
diagnostic single-seed checks described above (§2, §6).

## 8. All five stages re-run for real, with both fixes in place

| Stage | Result | Runtime |
|---|---|---|
| 0 | 20/20 seeds pass both comparisons, `overall_pass=True` | ~1m10s |
| 1 | all 7 conditions' checks pass | ~1m43s |
| 3 | 72/72 runs, all manipulation checks pass; report hash changed (`af925b...` → `a56a45...`) — S_obs went from ≈0.19 (bugged, near-floor) to ≈0.48-0.51 (fixed, real institutional activity); Z_obs went from exactly `0.0` (bugged — no accountability/bargaining-participation events possible with delegation off) to ≈0.16-0.23 (fixed) | ~5m24s |
| 4 | 96/96 runs, same qualitative shift in S_obs/Z_obs magnitude as Stage 3 | ~7m13s |
| 5 | 16 matched triples / 48 runs, first and only real execution (never ran bugged) | ~4m09s |

## 9. Why this matters, stated plainly

Stage 3 and Stage 4's original outputs were **technically-correct
executions of a design that, unknown to it, held the pressure→behavior
causal pathway inert**. Any discovery-pipeline analysis run against those
original files would have found "no differentiation" trivially, for a
reason having nothing to do with this milestone's actual scientific
question. Both bugs were caught and fully remediated before any Stage 6-9
analysis ever read Stage 3/4's output, so no downstream conclusion in this
milestone was ever drawn from the bugged data — but had the single-seed
sanity check been skipped (or had this milestone gone straight to a
96-run+72-run execution without it, as an earlier, less careful pass might
have), this would have been a silent, undetected null result presented as a
genuine finding. The check that caught it — "run one seed and look at the
raw numbers before trusting the full-scale run" — is the same discipline
this project applied at every prior stage in this milestone, and is the
reason it caught this one too.
