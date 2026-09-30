# ODD-style Model Description — Level 0.3 Addendum

This document extends `docs/odd_level0.1.md` and `docs/odd_level0.2_addendum.md`
(read both first) with exactly what Level 0.3 added: local ecological
patches, an independent ecological-policy behavioural dimension, its own
learning/evolution machinery, and the observer-side extensions built on
top. Nothing in Level 0/0.1/0.2's description is superseded; everything
below is additive, and at every new mechanism's default setting
(`ecology_topology="global_pool"`) produces byte-for-byte identical
dynamics to Level 0.2 (see "Compatibility" at the end).

## 1. Purpose

Test whether heterogeneous agents, acting from local incentives and
without receiving any direct reward for sustainability, generate
persistent or recoverable macroscopic ecological regimes through
**endogenous niche construction** — i.e. through their own local,
individually-costly/individually-beneficial extraction and maintenance
actions, not through a global rule, a designed institution, or a reward
term that scores agents on the population's aggregate ecological state.
This is explicitly *not* an attempt to generate, reproduce, validate, or
classify the dissertation's three governance trajectories, and no
governance terminology, dissertation axis, or preferred-outcome label
appears anywhere in this section of the codebase — see
`agents/agent.py::FORBIDDEN_ATTRIBUTE_SUBSTRINGS` and the structural
tests in `tests/test_level03_niche_construction.py`.

## 2. New/changed entities and state variables

**`ResourcePatch`** (`environment/patches.py`) — a local, bounded,
logistically-regenerating resource stock, independent of every other
patch: `patch_id`, `capacity`, `regen_rate`, `quality` (a productivity
multiplier, `1.0` by default — neutral), `resources`, `members`
(a `frozenset` of agent ids), and a per-patch cumulative ledger
(`cumulative_extraction`, split into `cumulative_game_extraction` and
`cumulative_ecological_extraction`; `cumulative_maintenance_invested`/
`_effective`; `cumulative_regeneration`; `cumulative_unmet_extraction_demand`).
`0 <= resources <= capacity` is guaranteed after every mutating method.

**`PatchSystem`** — a `{patch_id: ResourcePatch}` dict plus a fixed
`{agent_id: patch_id}` assignment.

**`EcologicalPolicy`** (`agents/ecological_policy.py`) — a frozen,
three-trait continuous vector per agent: `extraction_propensity`,
`maintenance_propensity`, `scarcity_sensitivity`, each in `[0, 1]`.
Structurally and semantically independent of `Agent.policy` (the
existing social cooperate/defect strategy) — see §5.

**Agents** (`agents/agent.py::Agent`) gained: `ecological_policy`
(inert `EcologicalPolicy(0, 0, 0)` by default), `ecological_policy_lineage_id`
(starts equal to `agent_id`, mirroring `policy_lineage_id`), `patch_id`
(`None` under `global_pool` topology), `ecological_cumulative_gain`, and
two rolling windows (`ecological_payoff_window`, `ecological_cumulative_window`)
that are the ecological-stream analog of `resource_window`/`payoff_window`.

**New event types** (`core/events.py`): `EcologicalActionEvent` (one per
living agent per step under `patches` topology — requested/actual
extraction, requested/effective maintenance, search cost, the local
occupancy observed at decision time), `EcologicalImitationEvent`
(mirrors `ImitationEvent`; records old/new values of all three traits,
the fitness comparison, `resulting_ecological_lineage_id`, and
`inheritance_mode`), `EcologicalMutationEvent` (mirrors `MutationEvent`).

## 3. Spatial/patch structure

Two topologies coexist via `config.ecology_topology`:
`"global_pool"` (default — the single well-mixed `EnvironmentResourcePool`
from Level 0.1/0.2, completely untouched) or `"patches"` (this level's
new mechanism). Patch membership is assigned **once**, at initialization,
by one of two neutral rules (`config.patch_assignment_mode`) — neither
ever inspects an agent's policy, resources, or any other trait:

- `"random_assignment"` — uniform random patch index per agent.
- `"network_neighborhood"` (default) — `n_patches` seed nodes drawn
  uniformly at random from the social interaction graph, then a
  round-robin multi-source BFS partition assigns every other node to its
  graph-closest seed; a disconnected node falls back to a uniform random
  draw. This ties initial patch membership to initial network structure
  without ever looking at what any agent *does*.

**Patch membership never changes after initialization — there is no
migration mechanism in this model.** This is a deliberate, explicitly
stated scope decision (the milestone brief's own instruction: "if
movement is not implemented, state that clearly"), kept structurally
distinct from the *social* network, which continues to rewire under
Level 0.1's endogenous relationship dynamics exactly as before — an
agent's neighbors can change every `rewiring_period` steps; its patch
cannot.

## 4. Process overview and scheduling — what changed

Level 0.2's per-step order gains one new sub-step and two existing steps
change internally, only under `ecology_topology="patches"`:

1. **Interactions** (changed): under `patches` topology, a positive
   social-game payoff is capped by the acting agent's own patch (via
   `ResourcePatch.extract(payoff, category="game")`, one call per
   interaction, order-dependent — the same incremental-draw convention
   the single pool already used) instead of the single global pool.
   Tracked under a separate `cumulative_game_extraction` ledger category
   from ecological harvest, so the two remain independently identifiable
   even though both draw down the same physical stock (§7).
2. **Ecological round** (new; `Simulation._ecological_round`, called
   once per step, strict no-op when patches are inactive): every living
   agent locally decides an extraction request `h` and a maintenance
   request `m` (§5), those requests are rationed per patch against that
   patch's *current* stock (§6), the resulting ledger changes are applied
   (§7), and every patch regenerates.
3. **Adaptation** (changed): dispatches ecological-policy imitation/
   mutation alongside the existing social imitation/mutation, per
   `config.ecological_inheritance_mode` (§8).

`Simulation._run_one_step` factors the entire per-step body (including
the two changes above) out of `run()`'s loop into its own method,
purely so external code (the Work-Package-J perturbation experiment)
can step a simulation and intervene between steps — behaviourally
identical to the pre-refactor loop for every ordinary caller.

## 5. Ecological decision process

At every step, for every living agent (under `patches` topology only):
occupancy is snapshotted *before* this round's own extraction/
maintenance/regeneration are applied (no lookahead, same convention as
the existing distress snapshot). The agent's decision reads **only its
own trait values and its own patch's occupancy** — no global occupancy,
no population-wide cooperation rate, no future-equilibrium information,
no macro-classification (`agents/ecological_policy.py::decide_ecological_action`'s
signature exposes no other channel — checked directly by
`tests/test_ecological_policy.py`):

```
scarcity = 1 - local_occupancy
extraction_multiplier = max(0, 1 - scarcity_sensitivity * scarcity)
maintenance_multiplier = 1 + scarcity_sensitivity * scarcity
h = extraction_propensity * ecological_harvest_unit * extraction_multiplier
m = maintenance_propensity * ecological_maintenance_unit * maintenance_multiplier
```

`scarcity_sensitivity=0` makes both multipliers exactly `1` regardless of
occupancy (occupancy-blind decisions); a higher value damps extraction
and amplifies maintenance as the patch empties, but never forces either
to zero or infinity, and never makes `h` negative.

**Central separation principle.** This decision is entirely independent
of `Agent.policy.decide(...)` (the social cooperate/defect choice, read
each interaction from partner history). All four combinations —
cooperate+maintain, cooperate+overextract, defect+maintain,
defect+overextract — are separately constructible and separately
observable (`observer/niche_metrics.py::joint_action_frequencies`;
directly demonstrated by `tests/test_level03_niche_construction.py::
test_all_four_social_ecological_joint_combinations_are_representable`).
Social cooperation never automatically replenishes a patch; ecological
maintenance never automatically implies social cooperation.

## 6. Resource accounting and allocation

`environment/patches.py::allocate_extraction(available, requested, rule,
rng)` is a **pure** function (no patch mutation) used both by the
mutating, endogenous-feedback path and, unapplied, by the Work-Package-F
"no environmental effect" counterfactual — guaranteeing both conditions
ration demand with bit-identical arithmetic. Two rules
(`config.ecological_allocation_rule`):

- `"proportional"` (default) — if total requested exceeds available,
  every request is scaled down by `available / total_requested`
  (deterministic, order-independent, no RNG consumed).
- `"sequential_random"` — requesters processed in a uniformly random
  order, each granted its full request out of whatever remains
  (first-come-first-served; consumes RNG draws).

`ResourcePatch.apply_maintenance(investment, efficiency)` returns the
amount *actually added* — `efficiency * total_invested`, capped by the
patch's remaining headroom to capacity (never assumed fully efficient;
`config.maintenance_efficiency` defaults to `0.7`). `ResourcePatch.regenerate()`
is bounded logistic growth scaled by `quality`, identical in form to
`EnvironmentResourcePool.regenerate()`.

Regeneration always runs, in every Work-Package-F condition including
"no environmental effect" — that condition isolates *agent-driven*
feedback specifically, not the patch's own baseline dynamics.

## 7. Individual incentive accounting

Every step, per living agent: actual extraction `h_actual` (the granted
amount, possibly less than requested) is an immediate resource gain;
requested maintenance `m_requested` is an immediate resource cost, paid
in full regardless of `apply_maintenance`'s effectiveness cap; an
optional fixed `ecological_search_cost` is charged only when
`h_requested > 0` (an unsuccessful-extraction cost, `0.0` by default).
Exact per-agent identity (hand-computed and tested in
`tests/test_level03_niche_construction.py::
test_ecological_round_agent_ledger_identity_hand_computed`):

```
resources_after = resources_before + h_actual - m_requested - search_cost
```

Exact per-patch identity (also hand-computed and tested):

```
R_{t+1} = R_t + natural_regeneration + effective_maintenance - actual_extraction
```

Social-game payoff, ecological extraction gain, maintenance cost,
subsistence cost, punishment cost/received, and connection/exit costs
all remain separately identifiable per agent per step — social-game and
ecological-extraction draws share the *same physical patch* but are
tracked under distinct ledger categories (`cumulative_game_extraction`
vs. `cumulative_ecological_extraction`), so "social payoff" and
"extraction gain" are never conflated even though both reduce the same
underlying stock.

## 8. Adaptation / inheritance

Ecological-policy imitation and mutation use the exact same neutral
mechanisms (Fermi-rule imitation, low-rate mutation) as the social
dimension, but are independently distinguishable events
(`agents/adaptation.py::ecological_imitation_round`, `
ecological_mutation_round`). Two of the milestone's four named
inheritance modes are implemented (`config.ecological_inheritance_mode`):
`"independent"` (default — the social and ecological dimensions each get
their own peer draw and their own Fermi decision, never entangled) and
`"coupled_same_model"` (one peer draw and one Fermi decision, using the
social/`"total"`-stream fitness signal, governs both dimensions
together — `agents/adaptation.py::coupled_dual_imitation_round`). The
other two named modes ("ecological independent of social" and "both
independently, potentially different model agents") are not separately
distinguishable from `"independent"` given this architecture's one-peer-
per-round imitation design — see `dev_mem/status_update.md`'s Level 0.3
entry for the full rationale; this is the milestone's own documented
fallback allowance.

Fitness signals: `agents/fitness.py::fitness_signal` gained a `stream`
parameter (`"total"` — unchanged existing behaviour, reads the agent's
overall economic state; `"ecological"` — the same four formulas
(`cumulative_resources`, `recent_payoff`, `resource_delta`,
`viability_adjusted`) applied to the parallel ecological-only ledger).
`config.fitness_mode_ecological` selects the ecological stream's mode
independently of `config.fitness_mode` (the social stream's mode).
Neither stream nor mode is asserted more correct than another.

## 9. Observation

`observer/niche_metrics.py` (Work Package E) extends the observer layer
without ever being read by any decision function: `patch_occupancy_summary`
(mean/median/min/max/variance of per-patch occupancy, a spatial-
inequality Gini across patch stocks, depleted/abundant counts against
documented thresholds), `ecological_step_summary` (requested/actual
extraction, shortfall, requested/effective maintenance, search cost,
restraint frequency), `joint_action_frequencies` (the four social x
ecological combinations, documented majority-vote/dominance
categorization rule — never compressed to one score), and
`ecological_policy_diversity_bits`/`ecological_policy_snapshot` (a
population-mean-relative 3-bit discretization of the continuous trait
vector into a Shannon-entropy diversity figure, with raw trait means/
stds always exported alongside, unmixed). `observer/regulation_diagnostics.py`
(Work Package I) is a separate, deliberately conservative module —
seven independent criteria (interior persistence, feedback dependence,
perturbation recovery, parameter-neighborhood robustness, nontriviality,
micro-macro linkage, and a cautious nonstationary-alternatives
classification), never combined into one score, with documented
degenerate-case behaviour and hand-constructed-trajectory tests for
each. See both modules' docstrings for full definitions.

## 10. Initialization

Under `patches` topology, `build_agents()` draws each agent's
`EcologicalPolicy` from `Normal(extraction_propensity_mean,
extraction_propensity_std)` etc., clipped to `[0, 1]` — the same
distributional-draw convention every other trait in this model already
uses. Patch quality is drawn once per patch from `Normal(1.0,
patch_quality_std)` (neutral, `quality=1.0` exactly, when
`patch_quality_std=0.0`, the default). Every patch starts at
`capacity * patch_initial_fraction`.

## 11. Stochasticity

Every new RNG consumption (patch assignment, allocation-rule shuffling,
ecological-policy sampling/mutation, the WP-F shuffle permutation) routes
through the single seeded `numpy.random.Generator` the rest of the model
already uses (`Simulation.rng`) — no second generator, no unseeded
randomness. Under `global_pool` topology, none of this code is reached
at all, so a compat-mode run's RNG draw sequence is unaffected
(`tests/test_level03_niche_construction.py::
test_full_suite_rng_draw_sequence_unaffected_by_ecology_topology_default`).

## 12. Experimental manipulations (Work Package F)

Five causal-intervention conditions, implemented as four orthogonal
config flags plus the existing frozen-mode flags (never five bespoke
simulation variants — see `dev_mem/status_update.md`'s design decision
4 for the full rationale): endogenous feedback (default),
`ecological_actions_affect_patch=False` ("no environmental effect"),
`ecological_imitation_enabled=False` + `ecological_mutation_rate=0.0`
("frozen"), `ecological_policy_randomized_each_step=True`
("randomized"), `ecological_policy_shuffle=True` ("replay/shuffle").
Named `SimulationConfig` presets for all five plus the WP-G/H/J base
configurations are in `core/config.py` (`level03_no_environmental_effect`,
`level03_frozen_ecological_policy`, `level03_randomized_ecological_policy`,
`level03_policy_shuffle`, `level03_viability_sweep_base`,
`level03_phase_search_base`, `level03_perturbation_base`).

## 13. Compatibility modes

`ecology_topology="global_pool"` (the default) is a complete,
byte-for-byte no-op relative to Level 0.2: `Simulation.patch_system`
stays `None` throughout, every agent's `ecological_policy` stays at its
inert `EcologicalPolicy(0, 0, 0)` default, `patch_id` stays `None`, and
zero `EcologicalActionEvent`/`EcologicalImitationEvent`/
`EcologicalMutationEvent`s are ever logged
(`tests/test_level03_niche_construction.py`'s dedicated compatibility
tests). `SimulationConfig.level02_compat()` names this intent
explicitly; `SimulationConfig.level0_compat()` also pins
`ecology_topology="global_pool"` in its compat-fields dict, so the
original pre-Level-0.1 regression check
(`tests/test_compat_regression.py`) is unaffected by Level 0.3's
existence.

## 14. Known limitations

- **No migration.** Patch membership is fixed for an agent's entire
  lifetime in a population slot (§3) — there is no spatial dispersal,
  colonization-by-movement, or patch-choice mechanism in this model.
- **Only two of four named inheritance modes are implemented** (§8) —
  a documented architectural limitation, not an oversight.
- **The default `level03_patches_default` calibration is collapse-prone.**
  Individual seeds frequently deplete their patches to near-zero within
  the first 60-100 steps under the literal default constants
  (`ecological_harvest_unit=5.0`, `ecological_maintenance_unit=5.0`,
  `maintenance_efficiency=0.7`, `patch_capacity=500.0`,
  `patch_regen_rate=0.5`) — see `docs/level0.3_scientific_note.md` and
  `dev_mem/status_update.md`'s Level 0.3 entry for the full discussion
  and its consequences for interpreting the WP-F/G/J results already
  recorded. The promised "small preliminary calibration check" (allowed,
  and expected, by the milestone brief) was not actually performed
  before the main experiments ran — stated here plainly, not hidden.
- **"Agent removal" (Work Package J) is an approximation.** `Agent.alive`
  is honored by the ecological round and by imitation/mutation, but
  `_run_interactions` iterates the social graph's edges directly and
  does not check `alive` — so the perturbation experiment's agent-removal
  shocks additionally sever every incident graph edge, rather than
  implementing a true agent-deletion lifecycle this late in the
  milestone. See `experiments/niche_perturbation_recovery.py`'s module
  docstring.
- **`joint_action_frequencies`'s categorization is one documented,
  overridable choice**, not the only defensible operationalization of
  "cooperate/defect x extract/maintain" for a step that may contain
  several interactions and independent continuous h/m values — see
  `observer/niche_metrics.py`'s module docstring for the exact rule and
  its stated alternatives.
