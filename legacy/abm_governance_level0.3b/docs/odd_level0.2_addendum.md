# ODD-style Model Description — Level 0.2 Addendum

This document extends `docs/odd_level0.1.md` (still the base description —
read it first) with exactly what Level 0.2 added: participation-opportunity
accounting, the viability state machine, configurable imitation fitness
signals, and ecological supply/demand accounting. Nothing in Level 0.1's
description above is superseded; everything below is additive and, at
every new mechanism's default setting, produces byte-for-byte identical
dynamics to Level 0.1 (see "Compatibility" at the end).

## 1. New/changed entities and state variables

**Agents** (`agents/agent.py::Agent`) gained:

- `demographic_id` (int) — a *third* identity concept, distinct from
  `agent_id` (the fixed network-node/population-slot index, never changes)
  and `policy_lineage_id` (tracks strategy descent, not personhood).
  Starts equal to `agent_id`; a replacement agent occupying the same slot
  after a removal gets a fresh, monotonically-increasing `demographic_id`.
- `viability_state` (one of `"active"`, `"distressed"`, `"dormant"`,
  or the one-step marker `"nonviable"` immediately before removal),
  `consecutive_deficit_steps`, `dormant_steps`, `replacement_count`.
- `resource_window`, `payoff_window` (bounded rolling windows, length
  `config.fitness_window`) — the substrate for the `recent_payoff` and
  `resource_delta` fitness signals (§4 below).

**The environment resource pool** is unchanged in its own state
(`resources`, `capacity`, `regen_rate`), but two new observer-computed
quantities are now derived from it every step: `unmet_extraction_demand`
(potential minus realized extraction) and `max_sustainable_regeneration`
(the structural `r·K/4` throughput, a property of the configured
parameters, not a per-step measurement).

**New event types** (`core/events.py`): `ViabilityTransitionEvent`,
`ReplacementEvent`. `WithholdEvent` gained a `reason` value taxonomy
(`"distress"`, `"partner_distress"`, `"ineligible_dormant"`,
`"partner_ineligible_dormant"`); `InteractionEvent` gained
`resource_status_a/b`, `degree_a/b` (point-in-time, stamped at the moment
of the interaction); `ImitationEvent` gained `agent_fitness`,
`model_fitness`, `fitness_gap`, `fitness_mode`, each side's
`viability_state`, and `resulting_lineage_id`.

## 2. Process overview and scheduling — what changed

Level 0.1's 8-step per-step order (`docs/odd_level0.1.md` §3) is extended
with one new step, run *first*, and two existing steps changed internally:

0. **Viability round** (new; ecology-only, no-op when
   `viability_mode="none"`): update every agent's
   `consecutive_deficit_steps` and run its state-machine transition (§4
   below) — `active → distressed → dormant → (recovered | nonviable)`.
   A `nonviable` agent is removed and replaced (in `removal_replacement`
   mode) within this same sub-step.
2. **Interactions** (changed): each agent-side's opportunity is now one
   of five outcomes, all separately counted (§4's participation
   accounting): a hard **ineligible** block (dormant, `viability_mode !=
   "none"` only — a distinct mechanism from distress-withholding, added
   at Level 0.2), a soft **distress withdrawal** (unchanged from Level
   0.1, now logged on *both* sides of a prevented opportunity instead of
   only the declining side — see the `WithholdEvent` reason taxonomy
   above), or a **completed** interaction (which now also stamps each
   side's point-in-time resource status and degree onto the event).
7. **Adaptation** (changed): the imitation round's fitness comparison now
   calls the configurable `agents/fitness.py::fitness_signal` function
   (§4 below) instead of reading `resources` directly; a **fitness-window
   recording** sub-step (new) samples every agent's current resources and
   this step's net game-interaction payoff into its rolling windows, once
   per step, after every resource-affecting mechanic has run.

## 3. Design concepts — what changed

**Fitness / adaptation.** Level 0.1 stated "objective/fitness is simply
accumulated resources." Level 0.2 makes this a first-class, swappable
parameter (`config.fitness_mode`) rather than a hard-coded implementation
detail — see `agents/fitness.py` for all four signals
(`cumulative_resources`, `recent_payoff`, `resource_delta`,
`viability_adjusted`) and their differing translation-invariance
properties to a uniform per-agent resource shift (formally tested in
`tests/test_fitness.py`). No signal is asserted "more correct" in advance.

**Viability / population dynamics.** Level 0.1 had no demographic
consequence of resource failure — an agent could hold arbitrarily negative
resources indefinitely while remaining behaviourally identical to a
solvent agent (aside from probabilistic distress-withdrawal). Level 0.2
adds an explicit, disableable, duration-based state machine
(`config.viability_mode`) with three modes: `"none"` (Level-0.1-compatible
default), `"dormancy_recovery"` (resource failure suspends interaction
eligibility; an agent may recover), and `"removal_replacement"`
(persistent nonviability removes the agent; a replacement enters per an
explicit, configurable, non-dominant-policy-by-default inheritance rule).

**Observation of the model's own selection effects.** Level 0.2 adds a
structural distinction Level 0.1's metrics could not make: *conditional*
cooperation (P(Cooperate | an interaction happened) — the Level-0.1
metric) vs. *unconditional* cooperation (P(Cooperate ∩ interaction
happened | an opportunity existed)). The two are numerically identical
only when participation is universal; a gap between them is direct
evidence that a measured cooperation rate is inflated by selective
participation rather than reflecting universal cooperative behaviour —
see `observer/participation.py` and `docs/level0.2_scientific_note.md`.

## 4. Submodels — new at Level 0.2

### 4.1 Participation-opportunity accounting (Work Package A)

Every edge, every `interactions_per_step` repetition, creates exactly two
*agent-opportunities* (one per endpoint). Each agent-opportunity resolves
to exactly one of: completed (part of a logged `InteractionEvent`),
refused by own distress (`WithholdEvent(reason="distress")`), lost to a
partner's distress (`reason="partner_distress"`), blocked by own dormancy
(`reason="ineligible_dormant"`, `viability_mode != "none"` only), or lost
to a partner's dormancy (`reason="partner_ineligible_dormant"`). This
makes `opportunities_total == completed_agent_opportunities +
withhold_total` an exact per-step invariant (checked directly by
`tests/test_participation.py::test_opportunities_identity_holds_every_step`
across every viability mode). `observer/metrics.py` exports the raw
counts and six NaN-safe conditional probabilities per step (never a
silently-substituted 0.0 for a zero denominator); `observer/
participation.py` aggregates these over an arbitrary step range and
breaks cooperation down by resource status, network degree, policy
lineage (final-state join — a documented approximation, see that module's
docstring), and recent-payoff category (same approximation).

### 4.2 Viability state machine (Work Package B)

```
active --[resources < distress_threshold]--> distressed
distressed --[resources >= viability_recovery_resources]--> active
distressed --[consecutive_deficit_steps >= viability_deficit_steps_threshold]--> dormant
dormant --[resources >= viability_recovery_resources]--> active
dormant --[dormant_steps >= viability_max_dormant_steps, removal_replacement mode only]--> nonviable --> replaced
```

`consecutive_deficit_steps` resets to 0 the instant resources are at/above
`distress_threshold` — the dormant transition is duration-based (a
running streak), never a one-step trigger. A `nonviable` agent is
immediately replaced within the same sub-step; the replacement's starting
policy comes from one of four inheritance rules
(`config.viability_replacement_policy`): `random_init` (default — a fresh
draw from `policy_mix`, identical in distribution to an initial-population
agent), `dominant_policy` (the population's current plurality policy —
requires explicit opt-in, never the default), `parent_lineage_imitation`
(copy a uniformly-random living agent's policy and lineage), or
`mutation_fresh` (a uniformly-random policy with a brand-new lineage id).
`observer/viability.py` provides run-level aggregation (time-in-state,
transition-cause counts, recovery rates, replacement/lineage-continuity
records).

### 4.3 Imitation fitness signal (Work Package C)

See `agents/fitness.py`'s module docstring for the full mathematical
treatment. Summary: `cumulative_resources` and `resource_delta` are both
exactly translation-invariant to a uniform per-agent resource shift (such
as one step of unconditional subsistence);`recent_payoff` never reads
`resources` at all and so is trivially unaffected by a resources-only
shift (though not invariant to a shift applied directly to payoffs, which
does not occur in this model's mechanics); `viability_adjusted` behaves
like `recent_payoff` except when a shift is large enough to cross the
discrete dormancy threshold, at which point its penalty term breaks
invariance. All four share one interface (`fitness_signal(agent, mode,
...)`) so `agents/adaptation.py::imitation_round` never special-cases any
mode.

### 4.4 Ecological balance accounting (Work Package D)

`observer/metrics.py` exports, every step, the raw ingredients of a
supply/demand comparison — `potential_extraction_demand` (nominal,
uncapped positive-payoff demand this step), `realized_extraction` (what
the pool actually yielded), `unmet_extraction_demand` (their difference),
`realized_regeneration`, and `max_sustainable_regeneration` (`r·K/4`,
structural) — *unmixed*, per the milestone brief's explicit requirement
that a ratio's numerator and denominator never be hidden inside it.
`observer/ecological_balance.py` combines these into two documented
dimensionless balance indicators (`b_t_realized`,
`b_t_structural`) and a descriptive, observer-side-only region label
(`supply_dominant` | `boundary` | `demand_dominant` | `depleted`) — never
a governance concept, never fed back into agent decisions.

### 4.5 Dynamical classification discipline (Work Package I)

`observer/classification.py` gives operational, threshold-based,
duration-gated definitions for **Depletion** (pool occupancy at/below a
threshold, instantaneous), **Ecological collapse** (a contiguous run of
depleted steps, minimum duration, optionally requiring sustained unmet
demand throughout), **Recovery** (a contiguous above-threshold run of
minimum duration that follows a prior depletion), **Population failure**
(the distressed+dormant fraction crosses a threshold), and **Behavioural
convergence** (policy-diversity entropy at/below a threshold for a
minimum duration). Every threshold is an explicit, documented function
parameter, never a magic number. The word "attractor" is used nowhere in
this codebase or its documentation — see
`docs/level0.2_scientific_note.md` for why.

## 5. Compatibility

`viability_mode="none"` and `fitness_mode="cumulative_resources"` are
both Level-0.2 defaults, and both are exact no-ops relative to Level 0.1:
zero extra RNG draws, no new state transitions, identical resource
dynamics. `SimulationConfig.level0_compat()` additionally sets both
explicitly (alongside `ecology_enabled=False`,
`relationship_dynamics_enabled=False`), so it continues to reproduce the
original pre-Level-0.1 code path exactly —
`tests/test_compat_regression.py` still checks this byte-for-byte against
the committed `outputs/level0_default/metrics.csv` baseline.
