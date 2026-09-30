# ODD-style Model Description — Level 0.1

*Overview, Design concepts, Details (Grimm et al.) protocol, applied to
`abm_governance` as of the Level 0.1 milestone ("Ecological Closure and
Active Relational Dynamics"). This describes the generative layer only —
see `dev_mem/project_vision.md` §5 for why the observer layer (metrics,
diagnostics, this document) is deliberately excluded from the model
itself.*

## 1. Purpose

To generate, from elementary micro-level social-interaction rules —
repeated bilateral exchange, imperfect observation, memory, optional
costly punishment, strategy imitation and mutation, costly relationship
formation/dissolution, and (as of Level 0.1) a closed, bounded resource
ecology — whatever persistent macro-level patterns emerge, without
targeting, encoding, or optimizing toward any predefined governance
typology. See `dev_mem/project_vision.md` §2–§4 for the full research
question and the anomaly-preserving philosophy this implies (no
selective reporting of "interesting" seeds; every configured run is kept).

## 2. Entities, state variables, and scales

**Agents** (`agents/agent.py::Agent`), `population_size` of them (default
60), each with: `resources` (float, unbounded above and below — no floor
is enforced), `coercive_capability` (float; present for interface
stability with later levels, unused in any Level 0.1 decision),
`policy` (one of six fixed, interpretable rule-based strategies — see §7
below), `policy_lineage_id` (int; tracks whether the current policy
arrived via imitation, propagating the source agent's id, or mutation,
receiving a fresh id — Level 0.1, Work Package D), `observation_accuracy`,
`learning_rate`, `forgiveness`, `risk_sensitivity`, `exit_cost`
(heterogeneous, drawn once at initialization from configured
Gaussian(mean, std) distributions, clipped to valid ranges),
`memory_length` (bounded per-partner interaction history), and a
per-partner EWMA `partner_payoff_estimate` used by both memory-based
policies and the exit decision.

**The relationship network** (`networkx.Graph`, nodes = agent ids,
undirected edges = active relationships): initialized via one of three
topologies (`erdos_renyi`, `watts_strogatz`, `regular`), evolves through
the run via exit and connection events (§7).

**The environment resource pool** (Level 0.1, Work Package A;
`environment/resource_pool.py::EnvironmentResourcePool`) — a single
scalar `resources ∈ [0, environment_capacity]`, shared by the whole
population, present only when `config.ecology_enabled` (default `True`).

**Scales.** One step = one synchronous round of scheduled bilateral
interactions across every current edge (`interactions_per_step` times
each, default 1). Runs default to 500 steps. Three slower, independent
timescales run on top of the per-step loop (`core/scheduler.py`):
imitation/mutation every `imitation_period` steps (default 10),
exit/relationship-dynamics every `rewiring_period` steps (default 5), and
(Level 0.1) subsistence charging and pool regeneration, which happen
every step. Population size is fixed for the whole run — Level 0.1 has no
birth/death; see §7's discussion of the "distress" consequence for why.

## 3. Process overview and scheduling

Each step, in this fixed order:

1. **Perturbations** (Level 0.1, Work Package G, opt-in, empty by
   default): apply any instantaneous effect (e.g. a resource-depletion
   shock) scheduled for this step; log start/end boundary events for any
   perturbation whose active window opens or closes this step.
2. **Interactions**: for every edge, both endpoints' policies decide an
   action (Cooperate/Defect) from their private memory of that specific
   partner; a payoff is computed from the fixed payoff matrix; if ecology
   is enabled, positive payoffs are drawn from (and capped by) the shared
   pool via `pool.extract`; each side's *effective* observation accuracy
   (reduced by any active observation-noise perturbation) determines
   whether it perceives the partner's true action or its opposite; the
   perceived action is written to memory; if punishment is enabled, each
   side may punish a perceived defector, stochastically, at
   `punishment_probability`. An agent whose resources were below
   `distress_threshold` at the *start* of the step (ecology only) may
   withhold from a given interaction instead of engaging (§7).
3. **Subsistence** (ecology only): every agent pays `subsistence_cost`
   unconditionally.
4. **Pool regeneration** (ecology only): the pool regrows logistically
   (§7).
5. **Memory decay**: every agent's stored reputations decay toward
   neutral at its own `forgiveness` rate.
6. **Relationship dynamics**, every `rewiring_period` steps: exit (or, in
   compatibility mode, the legacy unconditional-exit/blind-addition
   logic) and connection formation (§7).
7. **Adaptation**, every `imitation_period` steps: imitation, then
   mutation (§7); a policy-composition snapshot is recorded.
8. **Metrics**: the observer layer computes one row of per-step
   aggregate metrics from a read-only snapshot (agents, graph, event
   log, pool) — this never feeds back into step 1 of the next step.

## 4. Design concepts

**Basic principles.** Repeated-game reciprocity (Axelrod-style iterated
prisoner's dilemma), costly punishment as a second-order public good,
Fermi-rule imitation dynamics (evolutionary game theory), logistic
resource growth (bounded-carrying-capacity ecology) — used as an
interaction *grammar*, not a blueprint for any specific real-world
institution; see `dev_mem/project_vision.md` §6.

**Emergence.** Cooperation levels, policy-composition trajectories,
network structure, resource distribution, and enforcement error rates
are all emergent outputs of the rules above — none is a direct model
input or a scored objective.

**Adaptation.** Agents adapt via imitation (copy a peer's policy with
probability increasing in the peer's resource advantage) and low-rate
mutation (uniform-random policy re-draw) — not via any planning,
optimization, or lookahead. Objective/fitness is simply accumulated
`resources`, the same currency as game payoffs (`agents/adaptation.py`).

**Sensing.** Every agent's read of a partner's action is corrupted with
probability `1 - effective_observation_accuracy` (heterogeneous,
possibly perturbation-reduced) — agents never observe the true joint
action directly, and this is the sole source of the "false-positive
punishment" phenomenon quantified by the enforcement confusion matrix
(§7, Work Package C).

**Interaction.** Strictly bilateral and local: every rule in the model
(payoff, punishment, exit, connection acceptance, imitation) is a
function of information available to the deciding agent(s) alone — no
rule ever inspects or optimizes over population-wide state. See
`network/dynamics.py`'s module docstring for an explicit statement of
this for the Level 0.1 relationship-dynamics module specifically.

**Stochasticity.** Every random draw in the codebase passes through one
seeded `numpy.random.Generator` per run (`core/rng.py`); nothing calls
global `numpy.random` or stdlib `random`. This makes every run exactly
reproducible from its `SimulationConfig` and is the basis for the
compatibility-mode regression test (`tests/test_compat_regression.py`)
and the ensemble runner's parallel/serial determinism guarantee
(`tests/test_ensemble.py`).

**Observation (of the model, by the analyst).** Handled entirely by the
separate, read-only observer layer (`observer/`) — see §8.

## 5. Initialization

`population_size` agents are created with policy assignment drawn
(without replacement, exact counts, not merely expected proportions) from
`policy_mix` fractions; each agent's trait values are drawn independently
from its configured Gaussian(mean, std), clipped to a valid range. The
network is built via the configured topology/mean-degree/rewiring
probability. If ecology is enabled, the pool starts at
`environment_capacity * environment_initial_fraction`. All randomness
here consumes the same single seeded RNG as the rest of the run — nothing
is drawn from an unseeded source.

## 6. Input data

None. The model does not ingest external empirical datasets to drive any
process (unlike the dissertation's SEM analysis of survey data — see
`dev_mem/project_vision.md` §3). All parameters are set via
`SimulationConfig` (a YAML file or explicit constructor arguments);
`docs/config_reference.md` documents every field.

## 7. Submodels

**Payoff grammar** (`interactions/game.py`): standard iterated
prisoner's-dilemma payoff table (`payoff_temptation > payoff_reward >
payoff_punishment >= payoff_sucker`, validated at config time),
`payoff(action_a, action_b) -> (payoff_a, payoff_b)`, a pure function of
the joint action only.

**Environment resource pool** (Level 0.1, WP-A;
`environment/resource_pool.py`): capacity `K`, regeneration rate `r`.
Once per step, after that step's extraction: `growth = r * R * (1 -
R/K)`, `R_{t+1} = clip(R_t - extraction_t + growth, 0, K)` — standard
discrete logistic growth. Positive interaction payoffs are drawn from the
pool via `extract(amount)`, which returns `min(amount, pool.resources)`
and decrements the pool by that amount (an agent whose nominal payoff
exceeds the remaining pool receives only what's left — payoffs are never
negative-clipped by this mechanism, only capped). Negative outcomes
(sucker's payoff, punishment penalties) are *not* pool-mediated — they
transfer directly between agents or vanish, a documented simplification
(the pool is a source, not a general ledger, at this level).

**Subsistence and distress** (Level 0.1, WP-A): every agent pays
`subsistence_cost` every step, unconditionally, direct from its own
`resources` (not linked to the pool). An agent is "distressed" for a
whole step if its resources were below `distress_threshold` at that
step's start (a fixed per-step snapshot, not re-evaluated mid-step, for
determinism); each of a distressed agent's scheduled interactions that
step is independently withheld with probability `1 -
distress_engagement_prob` (logged as a `WithholdEvent`). This is the
project's chosen minimal, defensible survival consequence — reduced
interaction capacity, never death, extinction, or biological
reproduction, per the milestone's explicit instruction to prefer the
smallest defensible mechanism. Agent resources have no floor; sustained
scarcity produces an unbounded resource *deficit*, not agent removal (see
`dev_mem/status_update.md`'s "Known limitations" for the empirical
consequences of this choice).

**Observation** (`agents/observation.py`): `observe_action(true_action,
accuracy, rng)` flips the action with probability `1 - accuracy`
(possibly perturbation-reduced for the step — see below); heterogeneous
per-agent, drawn once at initialization.

**Punishment** (`interactions/game.py::apply_punishment`,
`simulation.py::_maybe_punish`): triggered only by a *perceived*
defection, at probability `punishment_probability`; the punisher pays
`punishment_cost`, the target loses `punishment_penalty`. An event is
`erroneous` when the *true* action was actually Cooperate — this is the
raw signal the Work Package C confusion matrix aggregates into properly
denominated conditional rates (`observer/enforcement.py`).

**Relationship exit and connection** (legacy path,
`network/graph.py`, used when `relationship_dynamics_enabled=False`:
unconditional exit below `exit_resource_threshold`, blind single-shot
edge addition up to `mean_degree`. Level 0.1 path, WP-B,
`network/dynamics.py`, default: exit uses the same EWMA-threshold
*decision* but is affordability-gated — an agent that cannot afford
`exit_cost` gets a `FailedExitEvent`, the edge stays intact; connection
formation is an explicit proposal (`ConnectionProposalEvent`, `reason ∈
{"accepted","rejected","no_candidate"}`) — the proposer pays
`search_cost` regardless of outcome, a uniformly-random non-neighbor
target accepts with probability `connection_accept_base_prob` discounted
by its own current degree relative to `mean_degree`
(`decide_connection_acceptance`), never inspecting the proposer's
identity. `relationship_exit_enabled` (default `True`) can disable exit
specifically while leaving connection formation active (used by one of
the Work Package E ablations).

**Imitation and mutation** (`agents/adaptation.py`): each living agent
samples one peer uniformly at random and imitates that peer's policy
with Fermi-rule probability `1 / (1 + exp(-beta * (peer.resources -
own.resources)))`, `beta=0.5` fixed; on imitation, `policy_lineage_id` is
copied from the peer (cultural propagation). Independently, each agent
mutates to a uniformly-random policy with probability `mutation_rate`;
on mutation, a *fresh* `policy_lineage_id` is assigned from a
monotonically increasing counter (originating novelty, distinguished
from imitation's propagation — Level 0.1, WP-D).
`imitation_enabled` (default `True`) can disable imitation specifically
while leaving mutation active (a Work Package E ablation).

**Perturbations** (Level 0.1, WP-G, `core/perturbation.py`, opt-in,
empty by default): a tuple of `(start_step, duration, kind, magnitude)`
specs. `resource_depletion` removes `magnitude` fraction of the pool
exactly once, at `start_step`. `observation_noise_increase` subtracts
`magnitude` from every agent's *effective* observation accuracy for the
window's duration (floored at 0; the underlying trait is unmodified).
Perturbations consume no RNG draws when the tuple is empty, preserving
compatibility-mode reproducibility.

## 8. The observer layer (not part of the model; read separately)

Everything under `observer/` — cooperation/defection rates, resource
Gini, network density/clustering/components/isolation/degree- and
age-distributions/assortativity, the enforcement confusion matrix and its
five conditional rates, policy diversity (Shannon entropy) and lineage
distribution, the provisional behavioral-phenotype fingerprint, and the
dynamical diagnostics (rolling statistics, autocorrelation, periodogram,
stationarity heuristic, change-point candidates, regime time-fraction,
endpoint dispersion) — is a pure function of a read-only snapshot
(agents, graph, event log, pool). None of it is fed back into step 1 of
any subsequent step; none of it names, encodes, or targets any
governance-normative concept (see `agents/agent.py::
FORBIDDEN_ATTRIBUTE_SUBSTRINGS` and `tests/test_invariants.py` for the
structural guard enforcing this). The dynamical diagnostics module
explicitly documents the evidentiary bar this project requires before
using words like "fixed point," "limit cycle," "metastable regime,"
"collapse," or "recovery" about any trajectory — see
`observer/dynamics.py`'s module docstring, and
`dev_mem/status_update.md`'s newest entry for why none of that vocabulary
is used to describe this milestone's results.
