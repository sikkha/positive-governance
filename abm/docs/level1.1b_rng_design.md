# Level 1.1b RNG Design — Work Package A

**Status:** complete. **Scope:** this document covers only the RNG
substream architecture (Section 4 of the Level 1.1b brief). It does not
discuss coordination calibration, appropriation/accountability
decomposition, memory validation, or functional recovery — those are
covered by their own Work Package B–H notes as they land.

## 1. Problem this fixes

Level 1.1's causal ablations (e.g. "accountability on" vs "accountability
off", matched by seed) all drew from **one shared `numpy.random.Generator`
per run**, consumed by every mechanism in a fixed call order determined by
`Simulation`'s per-step schedule. Disabling a mechanism doesn't remove its
code path from the schedule cleanly — it removes *some* of the draws that
mechanism would otherwise have made, at whatever point in the shared
sequence they would have occurred. Every draw *after* that point, for
*every other mechanism*, shifts. A "matched-seed ablation" was therefore
never really matched: the two runs' RNG states silently diverged at the
first differential draw, and everything downstream (including mechanisms
with no causal relationship to the one being ablated) inherited a
different draw sequence. This is documented in the Level 1.1 completion
report and audit supplement as limitation #1, and is exactly why Level
1.1b's own causal work (Work Packages C–H) cannot proceed on Level 1.1's
RNG architecture.

## 2. Design

### 2.1 Two modes

`SimulationConfig.rng_mode: str = "legacy_single_stream"` (the default).
Valid values: `"legacy_single_stream"`, `"mechanism_substreams"`
(`core.rng.VALID_RNG_MODES`).

**`legacy_single_stream`.** Every name in `core.rng.STREAM_REGISTRY`
resolves to the *same* `Generator` object
(`numpy.random.default_rng(seed)`, called once). This is not "a substream
registry that happens to collapse to one stream" — it is the literal,
unmodified Level 1.1 code path: same object, same call order, same draw
sequence, verified byte-for-byte by `tests/test_level11_compatibility.py`
(24 tests doing exact value-level metric comparisons, unchanged by this
work package) and reproduced by
`SimulationConfig.level11_legacy_compat()`.

**`mechanism_substreams`.** Every name in `STREAM_REGISTRY` gets its own
independent `Generator`, spawned once via
`numpy.random.SeedSequence(seed).spawn(len(STREAM_REGISTRY))` — a pure,
deterministic function of `(seed, registry length, each name's position)`.
No process-randomized `hash()` is used anywhere in the derivation (see
§4, cross-process stability). Because each mechanism's stream is a wholly
separate stateful object, no draw sequence "shift" of the kind described
in §1 is possible *between streams*: disabling mechanism X can change how
many times X's own stream is called (trivially — X isn't running), but it
cannot change what any *other* stream returns for the same sequence of
calls to it. `SimulationConfig.level11b_substreams()` is the preset all
Level 1.1b causal experiments must use.

### 2.2 The registry

```python
STREAM_REGISTRY = (
    "initialization", "social_interaction", "observation_error",
    "punishment", "ecological_action", "ecological_regeneration",
    "ecological_perturbation", "rule_formation_other",
    "rule_proposal_adoption", "contributions", "delegation_appointment",
    "administrative_task_performance", "discretion_appropriation",
    "accountability", "interpatch_coordination", "institutional_shocks",
    "relationship_dynamics", "imitation", "mutation",
    "demographic_replacement",
)
RNG_REGISTRY_VERSION = "level11b_v1"
```

20 names: the milestone's explicit minimum list plus a small number of
additive splits the brief's "at minimum" wording permits (documented
per-name below). The registry is a fixed, ordered tuple — **append-only**:
a name's position determines which spawned child `SeedSequence` it
receives in `mechanism_substreams` mode, so removing or reordering an
entry would silently reassign every other mechanism's stream for any
seed that had previously been run. Any change to the registry must bump
`RNG_REGISTRY_VERSION`. Both `rng_mode` and `rng_registry_version` are
`SimulationConfig` fields and therefore serialize into every run's
`config.yaml` manifest automatically (Section 4 requirement 10).

### 2.3 Per-name rationale

| name | draws from it today | notes |
|---|---|---|
| `initialization` | initial population trait draws (core traits only — see §2.4), network topology, patch-system construction, ecological-policy shuffle | also the identity of `Simulation.rng`, kept as a public alias for backward compatibility |
| `social_interaction` | distress-engagement gate, `policy.decide` | |
| `observation_error` | `observe_action` (both directions of one interaction) | |
| `punishment` | punishment-probability gate | |
| `ecological_action` | randomized-each-step ecological policy sampling, patch extraction allocation | |
| `ecological_regeneration` | **currently consumes zero draws** — `ResourcePatch.regenerate()`/`EnvironmentResourcePool.regenerate()` are both deterministic. Included in the registry for forward-compatibility and because the milestone names it explicitly; reported here as a null finding rather than inventing artificial stochasticity to make the name "do something" |
| `ecological_perturbation` | `apply_instantaneous_effects` | beyond the milestone's literal minimum — split out because perturbations are an experimenter-controlled intervention, not part of ordinary ecological action |
| `rule_formation_other` | monitoring, sanction, membership, amendment rounds, and the inline rule-compliance decision inside the ecological round | |
| `rule_proposal_adoption` | proposal/adoption round | |
| `contributions` | voluntary contribution round | |
| `delegation_appointment` | nomination/selection round, and (see §2.4) delegation-conditional trait initialization | |
| `administrative_task_performance` | task success/failure draw only | discretion draws excluded — see `discretion_appropriation` |
| `discretion_appropriation` | effort-withholding draw, fund-appropriation draw | split from `administrative_task_performance` inside `rules/delegation.py::task_performance_round` via the new `discretion_rng` parameter — the one genuine internal-mixing case in the codebase (every other module already received `rng` as an explicit caller-supplied parameter) |
| `accountability` | audit/appeal/recall round | |
| `interpatch_coordination` | coordination round, and (see §2.4) coordination-conditional trait initialization | |
| `institutional_shocks` | reserved for Level 1.1b's own shock-application experiment code (Work Package G), exposed via the public `Simulation.stream(name)` accessor | not yet consumed by any per-step mechanism as of this work package |
| `relationship_dynamics` | both rewiring rounds (legacy and endogenous) | |
| `imitation` | social/ecological/coupled imitation rounds | |
| `mutation` | social and ecological mutation rounds | |
| `demographic_replacement` | `_replace_agent` (policy/exemplar choice, new trait draws, ecological-policy resample) | beyond the milestone's literal minimum — split out from `initialization` so a viability-driven demographic churn counterfactual cannot perturb the *original* population's draw sequence, and vice versa |

### 2.4 The initialization-time isolation gap (found during testing, not designed away)

`build_agents()` (called once, during `Simulation.__init__`) draws three
*mechanism-conditional* trait blocks — delegation traits (used only when
`delegation_enabled`), contribution traits (`contribution_mode != "none"`),
and interpatch-coordination traits (`interpatch_coordination_enabled`) —
interleaved with every agent's unconditional core traits. Before this
work package's ablation-isolation tests were written and run, all of
these drew from the single `rng` parameter passed into `build_agents` —
which, even in `mechanism_substreams` mode, was simply
`self._stream("initialization")`. Ablating one of those three flags
therefore removed exactly that flag's draws from the *initialization*
stream, shifting the count (and hence the values) of every draw after it
in that same call — including the network-topology permutation and
patch-system construction that happen immediately afterward, neither of
which has anything to do with delegation, contributions, or coordination.

This is precisely the contamination pattern Work Package A exists to
eliminate, just discovered one level up (at construction time rather than
per-step). Fix: `build_agents()` now takes three additional optional
parameters — `delegation_rng`, `contribution_rng`, `coordination_rng` —
each defaulting to `rng` when omitted. `Simulation.__init__` passes
`self._stream("delegation_appointment")`,
`self._stream("contributions")`, and
`self._stream("interpatch_coordination")` respectively. In
`legacy_single_stream` mode these all resolve to the same object as
`rng` anyway, so this is a genuine no-op there (confirmed:
`tests/test_level11_compatibility.py` still passes unchanged). In
`mechanism_substreams` mode, ablating any one of the three flags now
leaves every unrelated stream — including `initialization` itself —
untouched. Covered by
`tests/test_level11b_rng_substreams.py::TestMechanismAblationDoesNotPerturbUnrelatedFirstStepDraws`.

## 3. Discretion/administrative-performance split

`rules/delegation.py::task_performance_round(..., rng, event_log,
discretion_rng=None)`. `rng` drives only the ordinary task-success draw.
`discretion_rng` (falling back to `rng` when `None`) drives the
effort-withholding draw and the fund-appropriation draw. A causal
experiment that ablates `discretion_enabled` in `mechanism_substreams`
mode therefore leaves the `administrative_task_performance` stream, and
everything that reads from it, completely untouched.

## 4. Cross-process stability and the `policy_assortativity` anomaly

Section 4 requires the substream derivation to use "no process-randomized
`hash()`" and to be stable across processes. `build_stream_registry` is
verified stable across a subprocess run with a *different*
`PYTHONHASHSEED` than the parent process
(`tests/test_level11b_rng_substreams.py::TestCrossProcessStability`) —
confirming the derivation genuinely never touches Python's salted
string/object hash.

Writing that test surfaced an unrelated, pre-existing anomaly:
`observer/network_diagnostics.py::policy_assortativity` called
`nx.attribute_assortativity_coefficient` without a fixed category
mapping, so networkx's internal mixing-matrix category order came from
an unordered Python `set` of policy-name strings. Since Python randomizes
string hashing per process by default, the floating-point summation
order — and therefore the exact returned value, at the ULP level (e.g.
`-0.056413941789435915` vs. `-0.056413941789435804` in one observed
case) — varied silently between process invocations of the *same* seed
and config, at roughly a 1-in-5 rate for the specific fixture tested.
This predates Level 1.1b (it was never caught because no prior test
compared results across separate OS processes) and has nothing to do
with the RNG substream architecture itself — it is a `networkx`-adjacent
floating-point-associativity bug in this project's own metrics wrapper.
Fixed by passing an explicit, sorted `mapping` into
`nx.attribute_mixing_matrix` before computing the coefficient via
networkx's own `attribute_ac`; the Newman (2003) formula itself is
unchanged. Confirmed fixed: 8/8 consecutive fresh-process runs identical
(previously ~1-in-5 differed), and the serial-vs-multiprocessing
equivalence test (§5) passes with exact equality across every metric,
including `policy_assortativity`, where before the fix it was the only
metric that ever mismatched.

**This is reported as a real, if narrow, degenerate-measurement finding,
not swept into the RNG work silently:** any Level 1.0/1.1 result that
reported `policy_assortativity` to more than ~13 significant figures, or
that compared it bit-for-bit across separate process runs, could have
been affected. No such comparison exists in the Level 1.0/1.1 completion
reports (all reported comparisons there are same-process, or compare at
a precision far coarser than the ULP-level discrepancy), so this does
not retroactively invalidate any prior reported result — it is recorded
here because Section 3's constraint against silently ignoring anomalies
applies regardless of whether a specific prior claim happened to be
affected.

## 5. Testing

`tests/test_level11b_rng_substreams.py` (26 tests):
registry-construction purity/determinism/versioning; legacy-mode
alias/no-op guarantees; substream-mode same-seed reproducibility and
repeat-run byte equality; legacy vs. substream divergence (they are not
expected to match each other, only each to be internally deterministic);
serial-vs-multiprocessing equivalence (`spawn` context, separate
interpreter); cross-process stability under different `PYTHONHASHSEED`;
observer/generative separation (`compute_step_metrics` takes no `rng`
parameter; recomputing it any number of times between two draws never
changes what those draws return); mechanism-ablation draw isolation for
accountability, interpatch coordination, discretion, and zeroed
administrative costs, scoped to simulation step 0 (see §6 for why), with
an explicit negative control confirming the same ablation *does* perturb
an unrelated stream under `legacy_single_stream` mode — i.e. the test
suite is actually exercising the substream architecture's guarantee, not
something trivially true of the simulation regardless of `rng_mode`; and
the `discretion_rng` split.

Full-suite re-run after every change in this work package:
**765 passed (739 Level-1.1-baseline + 26 new), 2 skipped, 5 failed (same
5 tests, same documented artifact-availability cause), 0 warnings** under
`pytest -q -W error`.

## 6. What "isolation" does and does not mean here

`mechanism_substreams` mode guarantees that two separate `Generator`
objects cannot perturb each other's internal state — there is no shared
mutable object for one mechanism's draws to advance on another's behalf.
It does **not** guarantee that an unrelated stream will be called the
same number of times *for the rest of a multi-step run* once mechanisms
have had enough steps to feed back into shared quantities like
`agent.resources`. For example: accountability recovering
misappropriated funds from a delegate changes that agent's resources;
several steps later this can cross the distress threshold and change
whether the `social_interaction` stream's engagement gate fires for that
agent that step. That is an ordinary, expected *behavioral* causal
pathway — exactly what Work Packages D and E exist to measure — not RNG
contamination. This is why this work package's own ablation-isolation
tests are deliberately scoped to a simulation's first step (before any
mechanism has had a chance to feed back into shared state from a
previous step): that is the cleanest boundary between "the RNG
architecture itself leaks" (which step-0 tests rule out) and "the
mechanisms have real causal effects on each other's operating conditions
over time" (which is real, expected, and the subject of later work
packages, not a defect in this one).
