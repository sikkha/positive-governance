# ODD-style Model Description — Level 1.1b Addendum

This document extends `docs/odd_level1.1.md` (read it first) with what
Level 1.1b added. Like Level 0.3b before it (`docs/odd_level0.3b_addendum.md`),
Level 1.1b is a causal-and-measurement-validation milestone, not a new
generative mechanism — it adds **no new agent decision, no new governance
structure, and no new phenotype/type vocabulary**. Three changes below are
narrow exceptions worth naming precisely rather than glossing over:

1. **RNG plumbing** (Work Package A) touches `Simulation.__init__` and
   `build_agents()`'s call sites, but changes *which stream a draw comes
   from*, never *what decision is made* or *what distribution is drawn
   from*. Under the new default-preserving `rng_mode="legacy_single_stream"`,
   every draw sequence is byte-for-byte identical to Level 1.1.
2. **Three new config sub-flags** (`audit_enabled`/`recall_enabled`/
   `appeal_enabled`, Work Package E) gate three already-existing code
   branches inside `accountability_round` independently, where Level 1.1
   only had the coarser `accountability_enabled` gate. This is new
   *control surface* over existing mechanisms, not a new mechanism — all
   three default to `True`, so `SimulationConfig(accountability_enabled=True)`
   with no other change behaves exactly as Level 1.1's own accountability
   logic always did.
3. **A new event type** (`AppropriationOpportunityEvent`, Work Package D)
   logs every discretion opportunity regardless of whether it was
   attempted — an additional *record*, not an additional *decision*. The
   `discretion_rng.random()` draw controlling whether an attempt occurs is
   unchanged from Level 1.1 (see the module comment in
   `rules/delegation.py`).

## 1. Purpose

Level 1.1 reported a headline finding (accountability + discretion shift
the mechanism-validation classifier's output from `persistent_delegation`
to `accountable_delegation`) alongside six documented methodological
limitations. Level 1.1b's purpose is entirely to resolve those limitations
(plus two more found along the way) with matched-seed, seed-clustered-
bootstrap causal infrastructure, before any open governance-phenotype
search (reserved for Level 1.2) is attempted. See
`docs/level1.1b_validation_note.md` for the full per-work-package findings
and the Level 1.2 recommendation.

## 2. New observer-side modules and functions

**`observer/accountability_diagnostics.py`** (new file, Work Package E):
`accountability_activity()` (descriptive machinery-ran counts) and
`effective_constraint()` (realized-outcome-only — true-positive
detections, funds actually recovered, genuinely corrective appeals; every
undefined rate returns `None`, never `0.0`). Both are pure, read-only
functions of an `EventLog` snapshot; neither is ever read by any decision
function in `simulation.py`/`agents/`/`rules/` — the same generative/
observer separation discipline every prior level's addendum documents.

**`observer/delegation_diagnostics.py`, Work Package H addition**:
`classify_delegation_audited`, appended after the existing (Level 1.1,
byte-for-byte unmodified) `classify_delegation`. Same `VALID_LABELS`
vocabulary, same duration-gating/coordination/tenure/completion-rate
branches; the only changes are to the accountability-dependent branches,
requiring a realized true-positive audit detection and (a funds-recovering
recall or a genuinely corrective appeal) before a rule can be labeled
`"accountable_delegation"`. See `docs/level1.1b_validation_note.md`'s Work
Package H section for the two specific historical-classifier gaps this
corrects.

## 3. RNG substream architecture (Work Package A)

`core/rng.py` (new file): `STREAM_REGISTRY` names 20 mechanisms;
`build_stream_registry(seed, mode, registry=STREAM_REGISTRY)` returns
`{name: Generator}`. Under `rng_mode="mechanism_substreams"`, every name
maps to an independently-spawned `numpy.random.Generator` (via
`SeedSequence(seed).spawn()`); under `rng_mode="legacy_single_stream"`
(default), every name maps to the same single `Generator` Level 1.1 always
used. `Simulation._stream(name)` / `.stream(name)` are the only accessors;
every call site in `simulation.py`/`rules/delegation.py` that previously
read `self.rng` or a bare `rng` parameter now reads a named stream. See
`docs/level1.1b_rng_design.md` for the complete mechanism-by-mechanism
mapping and the two real isolation bugs (`build_agents()`'s shared-stream
leak, `policy_assortativity`'s cross-process nondeterminism) found and
fixed while building this.

## 4. New `SimulationConfig` fields and presets

`rng_mode: str = "legacy_single_stream"`, `rng_registry_version: str =
"level11b_v1"` (informational, exported into every run manifest);
`audit_enabled: bool = True`, `recall_enabled: bool = True`,
`appeal_enabled: bool = True` (Work Package E, with the recall→audit
architectural coupling documented in the field docstring). Nine new
presets, all documented conveniences over existing fields — see
`docs/config_reference.md`'s "Level 1.1b" section and
`docs/level1.1b_reproducibility_note.md` for the full list and every
condition's exact field overrides.

## 5. New event type

`AppropriationOpportunityEvent` (`core/events.py`, Work Package D):
`step, patch_id, rule_id, delegate_id, agent, fund_before,
appropriation_propensity, p_appropriate, attempted, attempted_amount,
realized_amount, fraction_of_opportunity`. Logged in `rules/delegation.py::
task_performance_round` immediately alongside the pre-existing
`AppropriationEvent`, under the identical condition
(`config.discretion_enabled and rule.fund > 0.0`) the existing
appropriation-attempt check already used — a superset record, not a new
gate.

## 6. Compatibility

A default `SimulationConfig()` run, and every `level11_*` preset run with
`rng_mode` left at its default (`"legacy_single_stream"`), reproduce
Level 1.1's exact trajectories bit-for-bit for the same seed — verified in
`tests/test_level11b_rng_substreams.py`'s legacy-replication test class.
`classify_delegation`, `accountability_round`'s pre-Work-Package-E
behavior at `accountability_enabled=True` with all three new sub-flags at
their `True` defaults, and every Level 1.1 config field's default value
and validated range are unchanged. `tests/test_level11_compatibility.py`'s
structural-terminology guard, generative/observer separation checks, and
serial/parallel reproducibility tests are unmodified and still pass.

See `docs/odd_level1.2_addendum.md` for the next milestone's own model
additions (built on top of this validated, RNG-substream-capable base) —
this addendum's own content above is otherwise complete and unmodified
by that later milestone.
