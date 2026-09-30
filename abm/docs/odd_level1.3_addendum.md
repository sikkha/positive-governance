# ODD Addendum — Level 1.3: Historical Sequencing, Entrenchment, and Path-Dependent Institutional Differentiation

This addendum documents only what Level 1.3 adds on top of Level 1.2b
(`docs/odd_level1.2b_addendum.md`) and everything it in turn built on.
Read that first. As with every prior addendum, a bare `SimulationConfig
()` run remains byte-for-byte identical to pre-Level-1.3 behavior —
Stage 0 (task #95) verifies this directly, at experimental scale, not
just by convention: 20/20 matched seeds, byte-identical, across two
independent baseline comparisons.

## 1. Purpose

Can different temporal orderings of security pressure, bargaining
pressure, and impersonal coordination pressure generate persistent,
reproducible institutional differentiation in the Level 1.2b substrate?
Section 23 requires this milestone to remain capable of finding one
family, two, four-or-more, a continuum, transient differentiation, or
no detectable historical effect at all — the six-way outcome space is
preregistered in `experiments/level13_preregistration.py::DECISION_
GATE_OUTCOMES` before any Stage 0-9 run, precisely so it cannot be
reworded after the fact to fit whatever a run turns up.

**This is still not a search for three governance types.** Every
generative/observer boundary rule, forbidden-terminology guard, and SEM
firewall Level 1.2/1.2b established remains in force, extended
mechanically to every new Level 1.3 module and experiment script
(`tests/test_level13_sem_firewall_extension.py`). Where a genuinely new
disclosed choice risked even the appearance of privileging the number
three (Stage 9's shock count), it was set to a different number (4)
specifically to avoid that appearance — see `docs/level1.3_scientific_
note.md` §10.

## 2. Generative layer: Work Packages A-F

Level 1.3 introduces one new module family — `core/historical_
pressure.py`, `core/historical_transmission.py`, `core/entrenchment.py`,
`core/legitimacy.py`, `core/historical_counterfactuals.py` — plus new
`SimulationConfig` fields gating each. Every field defaults to its
Level-1.2b-compatible no-op state; `historical_module_enabled=False` by
default means every new field below is entirely inert unless
deliberately turned on.

**Work Package A — pressure signals and transmission (Sections 6-7).**
Three independently-flagged pressure channels (`security_pressure`,
`bargaining_pressure`, `coordination_complexity`), each with its own
`PressureHistorySpec` (onset step, magnitude, duration, and — new in
Stage 9 — a `"repeated_shocks"` history kind alongside the original
single-pulse kind) and its own **two** transmission sub-flags (six
total), each nudging one existing, already-tested formula from Level
1.1's delegation/contribution/coordination mechanisms — never a new
success/failure pathway. Full account, including exactly which formula
each channel nudges and which twelve candidate channels were
deliberately left unwired: `docs/level1.3_historical_mechanisms.md`.

**The two-layer activation requirement.** Every channel needs both its
master `*_enabled` flag (state-series generation) and its own
transmission sub-flag (behavioral consequence) — both default `False`
independently, and a run with the master on and the sub-flags off has
a fully-formed pressure series with zero behavioral effect, by design
(this is exactly what Stage 1 tests). Task #109 found three stage
scripts had conflated the two, silently running with the sub-flags off
in experiments that needed them on — full account, root cause, and fix
in `docs/level1.3_bug_disclosure_and_reproducibility_note.md`.

**Work Package B — sequencing measurement (Section 7).** `observer/
sequencing_diagnostics.py`'s `INSTITUTIONAL_RESPONSE_DIMENSIONS` — the
first-sustained-crossing step for each of eight institutional-response
dimensions, `NaN` (never zero) when a dimension never crosses
threshold. Purely observer-side; reads simulation state, writes
nothing back.

**Work Package C — entrenchment (Section 8).** `core/entrenchment.py`
adds a per-rule `entrenchment_level` that accumulates while a rule
persists and is read by amendment/dissolution-resistance formulas when
`entrenchment_enabled=True` — the model's own path-dependence
mechanism: the same institutional configuration becomes harder to
change simply by having survived longer, independent of its current
performance.

**Work Package D — dual legitimacy (Sections 6, 9).**
`core/legitimacy.py` adds two independently-flagged legitimacy
channels — `performance_legitimacy` (delivering reliably) and
`procedural_legitimacy` (fair process) — each maintaining its own
per-rule ledger, read by `observer/sz_obs.py` as one input series each
(see `docs/level1.3_measurement_note.md` §2 for why these two, not a
different two).

**Work Package E — causal counterfactuals (Section 10).**
`core/historical_counterfactuals.py`'s two named transforms
(`erase_pressure_from`, `reverse_pressure_order`), applied via
`Simulation(config, historical_pressure_series_override={...})` with an
identical seed — the model's own matched-pair causal-isolation
mechanism, exercised at Stage 5. Disclosed, single-channel scope at
Stage 5 (`security_pressure` only) to sidestep this Work Package's own
disclosed multi-channel RNG-draw-skew limitation, stated in that
stage's own module docstring.

**Work Package F — institutional conversion detection (Section 11).**
`observer/institutional_conversion.py`'s `FUNCTION_FAMILIES`,
detecting at most one conversion per rule — the first sustained shift
away from its founding dominant function, using a disclosed default
50-step window / 3-event minimum activity / 20-step minimum persistence
threshold set.

## 3. Observer layer: the new modules

- **`observer/sz_obs.py`** (Work Package G, Section 12) — the `S_obs`/
  `Z_obs` observer-side composites. Full construct definition, firewall
  discipline, and provenance of every input series: `docs/level1.3_
  measurement_note.md` §§1-2.
- **`observer/level13_phenotype.py`** (Work Package H, Section 13) —
  the fourteen-dimension Level 1.3 phenotype vector, feeding Level
  1.2's own unmodified `observer/phenotype_discovery.py` clustering
  pipeline. Full dimension-by-dimension provenance: `docs/level1.3_
  measurement_note.md` §3.
- **`experiments/level13_common.py`** — `ECOLOGICAL_SPACE_FOR_LEVEL13`
  (Level 1.3 introduces no new ecological field of its own; this reuses
  Level 1.2b's own ecological parameter space), and `transmission_
  overrides_for_channel(channel)` — the single shared helper every
  Level 1.3 stage script now uses to turn on both of a channel's own
  transmission sub-flags together (added as the direct fix for task
  #109's Bug 1).

No new experiment-side classification vocabulary was added without a
matching test: the Section 23 six-way `DECISION_GATE_OUTCOMES`
vocabulary lives in `experiments/level13_preregistration.py` (not
`observer/`), matching Level 1.2b's own established precedent that
milestone-specific verdict vocabularies belong in the experiment layer
that composes them, not the generic downstream-only observer layer.

## 4. Configuration surface (Sections 6-10)

Seven new `SimulationConfig` fields gate the master pressure/
entrenchment/legitimacy channels (`historical_module_enabled`,
`security_pressure_enabled`, `bargaining_pressure_enabled`,
`coordination_complexity_enabled`, `entrenchment_enabled`,
`performance_legitimacy_enabled`, `procedural_legitimacy_enabled`),
plus six transmission sub-flags (two per pressure channel) and their
paired `*_sensitivity` fields. Every field defaults to its Level-1.2b-
compatible no-op state. No new `SimulationConfig` preset was added at
the generative layer beyond what Stage scripts build directly via
`level12b_frozen_reference()` plus explicit overrides — unlike Level
1.2b's own eight new semantically-named presets, Level 1.3's own stage
scripts build configs directly rather than introducing named presets,
a disclosed, simpler-surface choice for this milestone's own smaller
generative footprint (seven flags and six sub-flags, vs. Level 1.2b's
much larger causal-ablation factor space).

## 5. Data pipeline: the ten-stage experimental program and what it found

Full account: `docs/level1.3_scientific_note.md` (Stages 0-9's actual
results) and `docs/level1.3_discovery_methods.md` (the pooling design
behind Stages 6-8 specifically). In short: 72+96+48=216 generative runs
across Stages 3-5 feed a pooled discovery pipeline (Stage 6, reusing
Level 1.2's own clustering primitives unmodified) that found
`headline_k=2` with moderate stability and modest cross-algorithm
agreement; a 12-point fresh-confirmation pass (Stage 7) found all fresh
points assigned to one dominant cluster with a real, disclosed
generalization gap; S_obs and Z_obs were found strongly, not
independently, correlated (Stage 8, Pearson r ≈ 0.888); and the
qualitative picture held stable across a 24-run scale/shock robustness
grid (Stage 9). `docs/level1.3_decision_gate_report.md` renders the
formal Section 23 six-way classification from this evidence.
