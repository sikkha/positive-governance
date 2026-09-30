"""Level 0 / Level 0.1 simulation orchestrator.

Wires together the generative-layer pieces (agents, network, interaction
grammar, observation, adaptation, and — as of Level 0.1 — the environment
resource pool and endogenous relationship dynamics) behind one small,
testable ``Simulation`` class. This module is still part of the generative
layer's *driver* code — it schedules mechanisms, it does not itself define
any governance-level concept. Metrics are computed by the observer layer
from read-only snapshots taken after each step; nothing computed here is
fed back into agent state.

Compatibility mode
-------------------
When ``config.ecology_enabled`` and ``config.relationship_dynamics_enabled``
are both ``False`` (see ``SimulationConfig.level0_compat``), this class
executes exactly the original Level-0 code path: payoffs are credited to
agents directly and unbounded, there is no subsistence charge or distress
withholding, and exit/rewiring uses the original unconditional-exit /
blind-edge-addition logic. Critically, none of the new Level 0.1 branches
consume any extra draws from the shared RNG when their governing flag is
False, so a compatibility-mode run reproduces the pre-Level-0.1 RNG draw
sequence exactly — see ``tests/test_compat_regression.py``.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import networkx as nx
import numpy as np

from collections import Counter

from abm_governance.agents.adaptation import (
    coupled_dual_imitation_round,
    ecological_imitation_round,
    ecological_mutation_round,
    imitation_round,
    mutation_round,
)
from abm_governance.agents.agent import Agent
from abm_governance.agents.ecological_policy import decide_ecological_action, sample_ecological_policy
from abm_governance.agents.observation import observe_action
from abm_governance.agents.policy import VALID_POLICY_NAMES, make_policy
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import (
    ComplianceEvent,
    EcologicalActionEvent,
    EventLog,
    InteractionEvent,
    PunishmentEvent,
    ReplacementEvent,
    SubsistenceEvent,
    ViabilityTransitionEvent,
    WithholdEvent,
)
from abm_governance.core.historical_pressure import PressureHistorySpec, generate_pressure_series
from abm_governance.core.perturbation import (
    PerturbationSpec,
    apply_instantaneous_effects,
    boundary_events,
    effective_observation_accuracy,
    effective_regen_rate,
    effective_subsistence_cost,
    specs_from_config,
)
from abm_governance.core.rng import RNG_REGISTRY_VERSION, STREAM_REGISTRY, build_stream_registry, make_rng
from abm_governance.core.scheduler import Scheduler
from abm_governance.environment.patches import PatchSystem, allocate_extraction, build_patch_system
from abm_governance.environment.resource_pool import EnvironmentResourcePool
from abm_governance.interactions.game import COOPERATE, DEFECT, PayoffMatrix, apply_punishment
from abm_governance.network import dynamics as reldyn
from abm_governance.network.graph import build_network, exit_relationship, rewire
from abm_governance.observer.metrics import compute_step_metrics
from abm_governance.observer.niche_metrics import (
    ecological_policy_snapshot,
    ecological_step_summary,
    joint_action_frequencies,
    patch_occupancy_summary,
)
from abm_governance.observer.policy_observability import policy_snapshot
from abm_governance.rules.shared_rule import RuleParameters, SharedRule
from abm_governance.rules import dynamics as rule_dynamics
from abm_governance.rules import contributions as rule_contributions
from abm_governance.rules import coordination as rule_coordination
from abm_governance.rules import delegation as rule_delegation
from abm_governance.rules import institution as rule_institution
from abm_governance.rules import observation as rule_observation
from abm_governance.rules import transmission as rule_transmission
from abm_governance.rules import migration as rule_migration
from abm_governance.rules import scaling as rule_scaling


def build_agents(
    config: SimulationConfig,
    rng: np.random.Generator,
    delegation_rng: np.random.Generator | None = None,
    contribution_rng: np.random.Generator | None = None,
    coordination_rng: np.random.Generator | None = None,
    migration_rng: np.random.Generator | None = None,
) -> list[Agent]:
    """Draw a heterogeneous population from the config's trait
    distributions. Exact policy counts (not merely expected proportions)
    are assigned from ``config.policy_mix`` so that small-population unit
    tests get deterministic, exactly-matching counts.

    Level 1.1b, Work Package A: every agent's *core* traits (observation
    accuracy, resources, rule-preference traits, ...) always draw from
    ``rng`` regardless of which mechanisms are enabled. The three
    mechanism-*conditional* trait blocks below (delegation, contribution,
    interpatch-coordination) each draw from their own optional stream
    instead — defaulting to ``rng`` when not given, so every existing
    caller (and legacy single-stream mode, where the defaults collapse
    back onto the one shared object anyway) is unaffected. This closes a
    real isolation gap discovered by this milestone's ablation tests
    (tests/test_level11b_rng_substreams.py): previously, e.g. disabling
    ``interpatch_coordination_enabled`` removed two draws from the single
    shared stream *before* network construction ran, silently shifting
    every subsequent "initialization"-stream draw (network topology,
    patch assignment, ...) — the exact kind of shared-stream contamination
    Work Package A exists to eliminate. See
    docs/level1.1b_rng_design.md for the full account."""
    if delegation_rng is None:
        delegation_rng = rng
    if contribution_rng is None:
        contribution_rng = rng
    if coordination_rng is None:
        coordination_rng = rng
    if migration_rng is None:
        migration_rng = rng
    names = list(config.policy_mix.keys())
    fracs = list(config.policy_mix.values())
    counts = [int(round(f * config.population_size)) for f in fracs]
    diff = config.population_size - sum(counts)
    if diff != 0 and fracs:
        idx = int(np.argmax(fracs))
        counts[idx] += diff

    assignment: list[str] = []
    for name, c in zip(names, counts):
        assignment.extend([name] * c)
    if len(assignment) < config.population_size:
        # policy_mix was empty or degenerate; fall back to tit_for_tat
        assignment.extend(["tit_for_tat"] * (config.population_size - len(assignment)))
    order = rng.permutation(len(assignment))
    assignment = [assignment[i] for i in order]

    agents: list[Agent] = []
    for i in range(config.population_size):
        obs_acc = float(np.clip(rng.normal(config.observation_accuracy_mean, config.observation_accuracy_std), 0.0, 1.0))
        lr = float(np.clip(rng.normal(config.learning_rate_mean, config.learning_rate_std), 0.01, 1.0))
        forgiveness = float(np.clip(rng.normal(config.forgiveness_mean, config.forgiveness_std), 0.0, 1.0))
        risk = float(np.clip(rng.normal(config.risk_sensitivity_mean, config.risk_sensitivity_std), 0.0, 1.0))
        resources = float(max(0.1, rng.normal(config.initial_resources_mean, config.initial_resources_std)))
        coercive = float(max(0.0, rng.normal(config.initial_coercive_capability_mean, config.initial_coercive_capability_std)))
        agent = Agent(
            agent_id=i,
            resources=resources,
            coercive_capability=coercive,
            policy=make_policy(assignment[i]),
            observation_accuracy=obs_acc,
            learning_rate=lr,
            forgiveness=forgiveness,
            risk_sensitivity=risk,
            exit_cost=config.exit_cost,
            memory_length=config.memory_length,
        )
        # Level 0.3, Work Package B: an independent ecological policy is
        # only ever drawn when patches are active — under the default
        # "global_pool" topology every agent keeps Agent.__post_init__'s
        # fully-inert default (0, 0, 0), which is never read by anything
        # (no _ecological_round runs), so this is a strict no-op for every
        # Level-0/0.1/0.2-compatible run.
        if config.ecology_topology == "patches":
            agent.ecological_policy = sample_ecological_policy(
                config.extraction_propensity_mean, config.extraction_propensity_std,
                config.maintenance_propensity_mean, config.maintenance_propensity_std,
                config.scarcity_sensitivity_mean, config.scarcity_sensitivity_std, rng,
            )
        # Level 1.0, Work Package C: a heterogeneous population of
        # proposal/membership/enforcement traits, drawn exactly like every
        # other trait above -- only ever drawn when rule_formation_enabled
        # is True, so every Level-0-0.3b-compatible run leaves these
        # fields at Agent.__post_init__'s inert defaults (0.0
        # proposal_probability in particular, which alone guarantees zero
        # proposals ever fire).
        if config.rule_formation_enabled:
            agent.proposal_probability = float(
                np.clip(rng.normal(config.proposal_probability_mean, config.proposal_probability_std), 0.0, 1.0)
            )
            agent.preferred_extraction_ceiling = float(
                np.clip(rng.normal(config.preferred_extraction_ceiling_mean, config.preferred_extraction_ceiling_std), 0.0, 1.0)
            )
            agent.preferred_maintenance_requirement = float(
                np.clip(rng.normal(config.preferred_maintenance_requirement_mean, config.preferred_maintenance_requirement_std), 0.0, 1.0)
            )
            agent.preferred_monitoring_intensity = float(
                np.clip(rng.normal(config.preferred_monitoring_intensity_mean, config.preferred_monitoring_intensity_std), 0.0, 1.0)
            )
            agent.preferred_sanction_magnitude = float(
                np.clip(rng.normal(config.preferred_sanction_magnitude_mean, config.preferred_sanction_magnitude_std), 0.0, 1.0)
            )
            agent.preferred_adoption_threshold = float(
                np.clip(rng.normal(config.preferred_adoption_threshold_mean, config.preferred_adoption_threshold_std), 1e-3, 1.0)
            )
            agent.preferred_amendment_threshold = float(
                np.clip(rng.normal(config.preferred_amendment_threshold_mean, config.preferred_amendment_threshold_std), 1e-3, 1.0)
            )
            agent.willingness_to_join = float(
                np.clip(rng.normal(config.willingness_to_join_mean, config.willingness_to_join_std), 0.0, 1.0)
            )
            agent.willingness_to_monitor = float(
                np.clip(rng.normal(config.willingness_to_monitor_mean, config.willingness_to_monitor_std), 0.0, 1.0)
            )
            agent.sanction_preference = float(
                np.clip(rng.normal(config.sanction_preference_mean, config.sanction_preference_std), 0.0, 1.0)
            )
            agent.violation_tolerance = float(
                np.clip(rng.normal(config.violation_tolerance_mean, config.violation_tolerance_std), 0.0, 1.0)
            )
            agent.amendment_propensity = float(
                np.clip(rng.normal(config.amendment_propensity_mean, config.amendment_propensity_std), 0.0, 1.0)
            )
        # Level 1.1, Work Packages D-H: delegation/capacity/discretion/
        # accountability/contribution traits -- drawn only when
        # delegation_enabled is True, so every Level-1.0-compatible run
        # (delegation_enabled=False, the default) leaves these at
        # Agent.__post_init__'s inert defaults (nomination_probability=0.0
        # above all, which alone guarantees zero nominations ever fire).
        if config.delegation_enabled:
            agent.nomination_probability = float(np.clip(delegation_rng.normal(0.03, 0.02), 0.0, 1.0))
            agent.perceived_competence = float(np.clip(delegation_rng.normal(0.5, 0.2), 0.0, 1.0))
            agent.social_trust = float(np.clip(delegation_rng.normal(0.5, 0.2), 0.0, 1.0))
            agent.administrative_reliability = float(np.clip(delegation_rng.normal(0.6, 0.15), 0.05, 0.95))
            agent.appropriation_propensity = float(np.clip(delegation_rng.normal(0.15, 0.15), 0.0, 1.0))
            agent.effort_reduction_propensity = float(np.clip(delegation_rng.normal(0.15, 0.15), 0.0, 1.0))
            agent.audit_diligence = float(np.clip(delegation_rng.normal(0.2, 0.15), 0.0, 1.0))
        if config.contribution_mode != "none":
            agent.contribution_willingness = float(np.clip(contribution_rng.normal(0.5, 0.2), 0.0, 1.0))
            agent.preferred_contribution_amount = float(max(0.0, contribution_rng.normal(0.1, 0.05)))
        if config.interpatch_coordination_enabled:
            agent.interpatch_proposal_probability = float(np.clip(coordination_rng.normal(0.01, 0.01), 0.0, 1.0))
            agent.interpatch_acceptance_propensity = float(np.clip(coordination_rng.normal(0.5, 0.2), 0.0, 1.0))
        if config.migration_enabled:
            agent.migration_propensity = float(
                np.clip(migration_rng.normal(config.migration_propensity_mean, config.migration_propensity_std), 0.0, 1.0)
            )
        agents.append(agent)
    return agents


@dataclass
class SimulationResult:
    config: SimulationConfig
    metrics: list[dict]
    final_agents: list[Agent]
    final_graph: nx.Graph
    event_log: EventLog
    initial_total_resources: float
    #: None when config.ecology_enabled is False.
    final_environment_pool: EnvironmentResourcePool | None = None
    #: Periodic policy-composition snapshots (Work Package D); recorded
    #: whenever the adaptation round fires (see Scheduler.should_imitate).
    policy_snapshots: list[dict] = field(default_factory=list)
    #: Level 0.3, Work Package A: None unless config.ecology_topology ==
    #: "patches". The final patch system (all patches' final stocks and
    #: cumulative ledgers, plus the fixed agent->patch assignment).
    final_patch_system: PatchSystem | None = None
    #: Level 0.3, Work Package E: periodic ecological-policy-composition
    #: snapshots, recorded whenever the adaptation round fires (mirrors
    #: policy_snapshots above; empty unless ecology_topology == "patches").
    ecological_policy_snapshots: list[dict] = field(default_factory=list)


class Simulation:
    def __init__(self, config: SimulationConfig, historical_pressure_series_override: dict[str, np.ndarray] | None = None):
        """Level 1.3, Work Package E (Section 10): ``historical_pressure_
        series_override`` lets a caller supply an EXACT pre-built pressure
        series for one or more channels (keyed by the same ``"<channel>_
        pressure_series"`` state keys ``__init__``'s historical-state
        block uses), bypassing ``generate_pressure_series`` for those
        specific channels only — every channel NOT present in the
        override dict is generated normally from its config fields, and
        when the whole parameter is omitted (``None``, the default),
        behavior is completely unchanged from before this parameter
        existed. This is what makes a matched history-erasure/sequence-
        reversal counterfactual pair possible: build a base run, read its
        realized series from ``historical_state``, transform it with
        ``core/historical_counterfactuals.py``, and pass the transformed
        array back in here for a second ``Simulation`` with the SAME
        ``config.seed`` — the two runs then differ only in that one
        channel's pressure shape, holding population draws and every
        other RNG stream's consumption identical (the override array is
        used AS-IS, consuming zero draws from the ``historical_pressure_
        generation`` stream for that channel, so the other channels'/
        streams' draw sequences are also completely unaffected)."""
        self.config = config
        self._historical_pressure_series_override = historical_pressure_series_override or {}
        # -- Level 1.1b, Work Package A: RNG stream registry ------------------
        # ``self._streams`` holds every mechanism-name -> Generator mapping
        # per ``config.rng_mode`` (see core/rng.py's module docstring for the
        # exact guarantees of each mode). ``self.rng`` is kept as a public
        # alias for the "initialization" stream — in legacy mode this is the
        # very same object every other name resolves to, so nothing here
        # changes legacy behavior; in substream mode it is only the
        # initialization stream, and all mechanism code must go through
        # ``self._stream(name)``/``self.stream(name)`` instead of touching
        # ``self.rng`` directly.
        self._streams = build_stream_registry(
            config.seed, config.rng_mode, registry=STREAM_REGISTRY
        )
        self.rng_mode = config.rng_mode
        self.rng_registry_version = RNG_REGISTRY_VERSION
        self.rng = self._streams["initialization"]
        # Level 1.1b, Work Package A: mechanism-conditional trait blocks
        # inside build_agents() go to their own streams (see that
        # function's docstring) -- in legacy mode these are all the same
        # object as self.rng anyway, so this changes nothing there.
        self.agents = build_agents(
            config, self.rng,
            delegation_rng=self._stream("delegation_appointment"),
            contribution_rng=self._stream("contributions"),
            coordination_rng=self._stream("interpatch_coordination"),
            migration_rng=self._stream("migration"),
        )
        self.agents_by_id: dict[int, Agent] = {a.agent_id: a for a in self.agents}
        self.initial_total_resources = sum(a.resources for a in self.agents)

        self.graph = build_network(
            config.population_size, config.topology, config.mean_degree, config.rewiring_prob, self.rng
        )
        for u, v in self.graph.edges():
            self.agents_by_id[u].ensure_partner(v, 0)
            self.agents_by_id[v].ensure_partner(u, 0)

        self.event_log = EventLog()
        self.scheduler = Scheduler(config.imitation_period, config.rewiring_period)
        self.payoff_matrix = PayoffMatrix(
            config.payoff_temptation, config.payoff_reward, config.payoff_punishment, config.payoff_sucker
        )

        self.pool: EnvironmentResourcePool | None = None
        self.patch_system: PatchSystem | None = None
        if config.ecology_enabled and config.ecology_topology == "global_pool":
            self.pool = EnvironmentResourcePool(
                capacity=config.environment_capacity,
                regen_rate=config.environment_regen_rate,
                resources=config.environment_capacity * config.environment_initial_fraction,
            )
        elif config.ecology_enabled and config.ecology_topology == "patches":
            # Level 0.3, Work Package A: patch membership is assigned here,
            # once, from the network graph already built above — it never
            # changes for the rest of the run even as the graph itself
            # continues to rewire (see environment/patches.py's module
            # docstring: this is a deliberate, documented non-migration
            # scope decision).
            self.patch_system = build_patch_system(
                agent_ids=[a.agent_id for a in self.agents],
                graph=self.graph,
                n_patches=config.n_patches,
                capacity=config.patch_capacity,
                regen_rate=config.patch_regen_rate,
                initial_fraction=config.patch_initial_fraction,
                assignment_mode=config.patch_assignment_mode,
                quality_std=config.patch_quality_std,
                rng=self.rng,
                quality_spatial_correlation=config.patch_quality_spatial_correlation,
            )
            for agent in self.agents:
                agent.patch_id = self.patch_system.agent_patch[agent.agent_id]
            if config.ecological_policy_shuffle:
                # Work Package F "replay/policy-shuffle" counterfactual:
                # permute the already-drawn ecological policies across
                # agents, preserving the exact marginal distribution while
                # breaking whatever correlation initialization created
                # between an agent's patch/traits and its ecological
                # policy. Ecological lineage ids are reset to agent_id
                # (the shuffle is not itself a lineage-propagation event —
                # see docstring below).
                order = list(range(len(self.agents)))
                permuted = [int(x) for x in self.rng.permutation(order)]
                policies = [self.agents[i].ecological_policy for i in order]
                for target_idx, source_idx in zip(order, permuted):
                    self.agents[target_idx].ecological_policy = policies[source_idx]
                    self.agents[target_idx].ecological_policy_lineage_id = self.agents[target_idx].agent_id

        # Fresh lineage ids for mutation start after every initial agent_id,
        # so they never collide with an agent's own starting lineage.
        self._lineage_counter = itertools.count(config.population_size)
        #: Fresh demographic ids for removal/replacement (Level 0.2, Work
        #: Package B) — same non-collision rationale as the lineage counter.
        self._demographic_counter = itertools.count(config.population_size)
        #: Fresh ecological-lineage ids for ecological mutation (Level 0.3,
        #: Work Package D) — same non-collision rationale.
        self._ecological_lineage_counter = itertools.count(config.population_size)
        self._perturbation_specs: list[PerturbationSpec] = specs_from_config(config.perturbations)
        self.policy_snapshots: list[dict] = []
        #: Level 0.3, Work Package E.
        self.ecological_policy_snapshots: list[dict] = []

        # -- Level 1.0: locally shared rules (Work Package A) ----------------
        # A strict no-op (empty dict, zero extra RNG draws, no field on any
        # agent ever read) when config.rule_formation_enabled is False.
        #: patch_id -> currently-active SharedRule (at most one per patch).
        self.rule_registry: dict[int, SharedRule] = {}
        #: patch_id -> _PendingProposal awaiting adoption/rejection.
        self._pending_rule_proposals: dict[int, object] = {}
        #: patch_id -> most recently dissolved SharedRule at that patch
        #: (Work Package G reconstruction source; absent until a rule has
        #: actually dissolved there at least once).
        self._last_dissolved_rule_by_patch: dict[int, SharedRule] = {}
        self._rule_id_state = {"next_rule_id": 0, "next_lineage_id": 0}
        if config.rule_formation_enabled and self.patch_system is not None:
            if config.institution_imposed_mode:
                # Stage-4 condition 7 ("imposed rule"): every eligible
                # patch starts with an active rule directly, skipping
                # proposal/adoption -- a mechanical benchmark, not an
                # emergent institution (see core/config.py's docstring).
                for pid, patch in self.patch_system.patches.items():
                    eligible = [aid for aid in patch.members if self.agents_by_id[aid].alive]
                    if not eligible:
                        continue
                    params = RuleParameters(
                        extraction_ceiling=config.imposed_rule_extraction_ceiling,
                        maintenance_requirement=config.imposed_rule_maintenance_requirement,
                        monitoring_intensity=config.imposed_rule_monitoring_intensity,
                        sanction_magnitude=config.imposed_rule_sanction_magnitude,
                        adoption_threshold=1e-3,
                        amendment_threshold=1e-3,
                    )
                    rule_id = self._rule_id_state["next_rule_id"]
                    self._rule_id_state["next_rule_id"] += 1
                    lineage_id = self._rule_id_state["next_lineage_id"]
                    self._rule_id_state["next_lineage_id"] += 1
                    rule = SharedRule(
                        rule_id=rule_id, patch_id=pid, parameters=params, founding_step=0,
                        founder_id=-1, rule_lineage_id=lineage_id, members=frozenset(eligible),
                        supporters=frozenset(eligible),
                    )
                    self.rule_registry[pid] = rule
                    for aid in eligible:
                        self.agents_by_id[aid].rule_member_of = rule_id

        # -- Level 1.1: delegation, capacity, discretion, accountability -----
        # (Work Packages D-G). A strict no-op (empty dict, zero extra RNG
        # draws) when config.delegation_enabled is False.
        #: rule_id -> currently-active (or most-recently-active, until
        #: replaced) Delegate (at most one per rule at a time).
        self.delegate_registry: dict[int, rule_delegation.Delegate] = {}
        #: Every delegate ever appointed whose registry slot has since
        #: been overwritten by a successor -- preserves full history
        #: (see rules/delegation.py::nomination_and_selection_round).
        #: ``list(self.delegate_registry.values()) + self.delegate_history``
        #: is every delegate this run ever produced.
        self.delegate_history: list[rule_delegation.Delegate] = []
        #: rule_id -> {"opened_step": int, "candidates": dict[int, set[int]]}
        self._pending_delegate_nominations: dict[int, dict] = {}
        #: agent_id -> most recently realized capacity as a delegate
        #: (0.0 if never delegated) -- read-only "observed reliability"
        #: input to candidate evaluation, updated on every delegate
        #: removal.
        self._prior_delegate_capacity: dict[int, float] = {}
        self._delegate_id_state = {"next_delegate_id": 0}

        # -- Level 1.1: collective contributions (Work Package H) -----------
        # rule.fund is reused directly (see rules/contributions.py); no
        # extra per-simulation state is needed beyond the round call
        # itself, which is a strict no-op when config.contribution_mode
        # == "none" (the default).

        # -- Level 1.1: interpatch coordination (Work Package I) ------------
        # A strict no-op (empty dict, zero extra RNG draws) when
        # config.interpatch_coordination_enabled is False.
        self.coordination_link_registry: dict[int, rule_coordination.CoordinationLink] = {}
        self._pending_coordination_proposals: dict[tuple[int, int], object] = {}
        self._coordination_id_state = {"next_link_id": 0}

        # -- Level 1.2, Work Package A: institution lifecycle bookkeeping ---
        # Derived each step from rule_registry (see
        # rules/institution.py::institution_lifecycle_round's own
        # docstring) -- a strict no-op (empty dict) whenever rule_registry
        # itself is empty, exactly like every other Level 1.0+ mechanism.
        #: rule_id -> InstitutionRecord (1:1 with SharedRule in this
        #: milestone's initial wiring).
        self.institution_registry: dict[int, rule_institution.InstitutionRecord] = {}
        #: Level 1.2, Work Package B: patch_id -> list[(step, true_signal
        #: dict)], trimmed to the last ``observation_delay_max_steps + 1``
        #: entries -- owned here (not in rules/observation.py) so it
        #: persists across steps exactly like every other per-simulation
        #: registry in this class.
        self._true_signal_history: dict[int, list[tuple[int, dict]]] = {}
        #: Level 1.2, Work Package F: root-patch-id -> current jurisdiction
        #: (coordination-network connected component) -- owned here so it
        #: persists across steps, same pattern as every other registry.
        self._coordination_components: dict[int, frozenset[int]] = {}

        # -- Level 1.3: historical sequencing, entrenchment, and
        # path-dependent institutional differentiation (Section 3
        # scaffold). A strict no-op (``None``, zero RNG draws, nothing
        # any other code path reads) when config.historical_module_
        # enabled is False -- the exact condition Section 3 items 6-7's
        # compatibility requirement depends on. Populated incrementally
        # by later Work Packages (A: pressure signals; C: entrenchment;
        # D: legitimacy) -- this block currently only establishes the
        # gate itself. See tests/test_level13_compatibility.py for the
        # mechanical proof that no Level 1.3 field is ever read by any
        # Level 1.2b generative code path when disabled.
        self.historical_state: dict | None = None
        if self.config.historical_module_enabled:
            self.historical_state = {}
            # Section 5: one pressure-series array per ENABLED channel
            # only -- a disabled channel (e.g. historical_module_
            # enabled=True but security_pressure_enabled=False) never
            # has its fields read at all, exactly like every other
            # per-mechanism flag in this codebase. All three channels
            # share the one "historical_pressure_generation" substream
            # (registry order determines draw order when multiple
            # channels are stochastic_reproducible in the same run;
            # this is deterministic and documented, not incidental).
            pressure_rng = self._stream("historical_pressure_generation")
            for prefix, state_key in (
                ("security_pressure", "security_pressure_series"),
                ("bargaining_pressure", "bargaining_pressure_series"),
                ("coordination_complexity", "coordination_complexity_series"),
            ):
                if not getattr(self.config, f"{prefix}_enabled"):
                    continue
                if state_key in self._historical_pressure_series_override:
                    # Work Package E: an exact counterfactual series was
                    # supplied for this channel -- used as-is, bypassing
                    # generation entirely (zero draws from pressure_rng
                    # for this channel; see this method's own docstring).
                    self.historical_state[state_key] = np.asarray(
                        self._historical_pressure_series_override[state_key], dtype=float,
                    )
                    continue
                spec = PressureHistorySpec(
                    kind=getattr(self.config, f"{prefix}_history_kind"),
                    low_level=getattr(self.config, f"{prefix}_low_level"),
                    high_level=getattr(self.config, f"{prefix}_high_level"),
                    onset_step=getattr(self.config, f"{prefix}_onset_step"),
                    duration_steps=getattr(self.config, f"{prefix}_duration_steps"),
                    decay_rate=getattr(self.config, f"{prefix}_decay_rate"),
                    volatility_std=getattr(self.config, f"{prefix}_volatility_std"),
                    n_shocks=getattr(self.config, f"{prefix}_n_shocks"),
                    shock_width_steps=getattr(self.config, f"{prefix}_shock_width_steps"),
                    shock_interval_steps=getattr(self.config, f"{prefix}_shock_interval_steps"),
                )
                self.historical_state[state_key] = generate_pressure_series(
                    spec, self.config.n_steps, rng=pressure_rng,
                )

        # -- Level 0.2, Work Package D: per-step ecological demand/supply
        # accumulators, reset every step in run(). Kept on the instance
        # (not returned mid-step) purely because they're written from
        # inside the interaction loop and read once at step end.
        self._step_potential_extraction_demand = 0.0
        self._step_realized_extraction = 0.0
        #: Level 0.2, Work Package C: net game-interaction payoff earned by
        #: each agent this step (excludes subsistence/search/exit/punishment
        #: — see agents/fitness.py's docstring for the scope rationale).
        #: Reset every step.
        self._step_payoff: dict[int, float] = {}
        #: Level 0.2, Work Package A: number of edges the interaction loop
        #: actually iterated over this step, captured at the moment
        #: ``_run_interactions`` reads ``self.graph.edges()`` — *not* the
        #: same as ``self.graph.number_of_edges()`` read later at
        #: metrics-computation time, since a scheduled rewiring round can
        #: run in between and change the edge count within the same step.
        #: ``opportunities_total`` must be computed from the edge count
        #: that actually existed when opportunities were created, or the
        #: opportunities_total == completed + withheld identity breaks.
        self._step_interaction_edge_count = 0

    # -- Level 1.1b, Work Package A: RNG stream accessors ---------------------
    def _stream(self, name: str) -> np.random.Generator:
        """Return the ``Generator`` for mechanism ``name`` per this run's
        ``rng_mode``. In ``legacy_single_stream`` mode every ``name`` in
        :data:`~abm_governance.core.rng.STREAM_REGISTRY` resolves to the same
        object as ``self.rng`` — call order across mechanisms is therefore
        exactly the pre-Level-1.1b order and draw sequence. In
        ``mechanism_substreams`` mode each name is an independent stream, so
        disabling one mechanism cannot perturb another's draws. Internal
        (non-test) code should always go through this method rather than
        ``self.rng`` directly, except for the "initialization" stream itself.
        """
        return self._streams[name]

    def stream(self, name: str) -> np.random.Generator:
        """Public accessor for a named mechanism stream — for use by
        Level 1.1b experiment/analysis code (e.g. institutional-shock
        application) that needs its own isolated draws outside the regular
        per-step mechanism rounds. Same semantics as :meth:`_stream`."""
        return self._stream(name)

    # -- Level 1.3, Work Package A: pressure-level accessor ------------------
    def _pressure_level(self, state_key: str, step: int) -> float:
        """This step's value of the named pressure series, or ``0.0``
        when ``historical_state`` is ``None`` (Level 1.3 disabled) or
        that particular channel was never enabled (its series key is
        simply absent from ``historical_state`` -- see
        ``__init__``'s historical-state block). Every Work Package A
        round-function call site passes this value through unconditionally;
        each channel's OWN flag (checked inside that round function, not
        here) decides whether it has any effect."""
        if self.historical_state is None:
            return 0.0
        series = self.historical_state.get(state_key)
        if series is None:
            return 0.0
        return float(series[step])

    # -- per-step mechanisms --------------------------------------------------
    def _active_perturbations(self, step: int) -> list[PerturbationSpec]:
        return [s for s in self._perturbation_specs if s.is_active(step)]

    def _apply_perturbations(self, step: int) -> list:
        active = self._active_perturbations(step)
        for spec in self._perturbation_specs:
            apply_instantaneous_effects(
                spec, step, self.pool, self._stream("ecological_perturbation"), patch_system=self.patch_system
            )
        events = boundary_events(self._perturbation_specs, step, self.config.n_steps)
        for event in events:
            self.event_log.add(event)
        return active

    def _run_interactions(self, step: int, active_perturbations: list[PerturbationSpec]) -> None:
        # -- eligibility / distress snapshots, taken once at the step's
        # start (Level 0.2, Work Package A/B). When viability_mode="none"
        # (the default), `dormant` is always empty and `distressed` is
        # computed identically to Level 0.1 — this branch is exact-compat.
        distressed: dict[int, bool] = {}
        dormant: set[int] = set()
        if self.config.ecology_enabled:
            threshold = self.config.distress_threshold
            if self.config.viability_mode == "none":
                distressed = {a.agent_id: a.resources < threshold for a in self.agents}
            else:
                distressed = {a.agent_id: a.viability_state == "distressed" for a in self.agents}
                dormant = {a.agent_id for a in self.agents if a.viability_state == "dormant"}

        edges = list(self.graph.edges())
        self._step_interaction_edge_count = len(edges)
        for _ in range(self.config.interactions_per_step):
            for u, v in edges:
                agent_a, agent_b = self.agents_by_id[u], self.agents_by_id[v]

                # Work Package A: opportunity created (this edge exists this
                # repetition). Ineligibility (dormant, viability_mode !=
                # "none" only) is a hard block — no probabilistic gate, no
                # RNG draw, distinct from the softer "distress withdrawal"
                # below. This is the generative-layer counterpart of the
                # observer layer's "prevented by insufficient resources"
                # category.
                if u in dormant or v in dormant:
                    # Every agent-opportunity on this edge this repetition is
                    # accounted for exactly once, even when only one side is
                    # dormant: the dormant side's own opportunity is lost to
                    # its own ineligibility; a non-dormant partner's
                    # opportunity is *also* lost (there is no interaction
                    # without both sides), but for a distinct reason
                    # ("partner_ineligible_dormant") — this keeps
                    # opportunities_total == 2*completed_interactions +
                    # withhold_event_count an exact per-step invariant (see
                    # tests/test_participation.py).
                    self.event_log.add(
                        WithholdEvent(
                            step=step, agent=u, partner=v,
                            reason="ineligible_dormant" if u in dormant else "partner_ineligible_dormant",
                        )
                    )
                    self.event_log.add(
                        WithholdEvent(
                            step=step, agent=v, partner=u,
                            reason="ineligible_dormant" if v in dormant else "partner_ineligible_dormant",
                        )
                    )
                    continue

                social_rng = self._stream("social_interaction")
                engage_a = True
                engage_b = True
                if distressed.get(u, False):
                    engage_a = social_rng.random() < self.config.distress_engagement_prob
                if distressed.get(v, False):
                    engage_b = social_rng.random() < self.config.distress_engagement_prob
                if not (engage_a and engage_b):
                    # Every prevented opportunity is logged on BOTH sides:
                    # the agent whose own probabilistic gate declined gets
                    # reason="distress" ("refused" in the milestone brief's
                    # vocabulary); a willing partner whose opportunity was
                    # lost purely because of the *other* side's decision
                    # gets reason="partner_distress" — distinct from a
                    # self-caused refusal, and previously not recorded at
                    # all (Level 0.1 only logged the declining side).
                    if not engage_a:
                        self.event_log.add(WithholdEvent(step=step, agent=u, partner=v, reason="distress"))
                        if engage_b:
                            self.event_log.add(WithholdEvent(step=step, agent=v, partner=u, reason="partner_distress"))
                    if not engage_b:
                        self.event_log.add(WithholdEvent(step=step, agent=v, partner=u, reason="distress"))
                        if engage_a:
                            self.event_log.add(WithholdEvent(step=step, agent=u, partner=v, reason="partner_distress"))
                    continue

                action_a = agent_a.policy.decide(agent_a.partner_history(v), social_rng)
                action_b = agent_b.policy.decide(agent_b.partner_history(u), social_rng)
                payoff_a, payoff_b = self.payoff_matrix.payoff(action_a, action_b)

                # Work Package D: nominal (uncapped) positive-payoff demand
                # on the pool, tracked regardless of whether ecology is
                # enabled (harmless no-op cost when it isn't; kept
                # unconditional so the accounting code has one code path).
                self._step_potential_extraction_demand += max(payoff_a, 0.0) + max(payoff_b, 0.0)

                if self.config.ecology_enabled and self.pool is not None:
                    actual_a = self.pool.extract(payoff_a) if payoff_a > 0 else payoff_a
                    actual_b = self.pool.extract(payoff_b) if payoff_b > 0 else payoff_b
                elif self.config.ecology_enabled and self.patch_system is not None:
                    # Level 0.3: under patches mode each agent's positive
                    # social-game payoff draws from its *own* local patch
                    # (the direct per-agent generalization of "the shared
                    # pool" — same conceptual role, spatially
                    # disaggregated), tracked under the "game" ledger
                    # category so it stays distinguishable from the
                    # separate ecological-harvest ledger (Work Package C).
                    patch_a = self.patch_system.patch_of(u)
                    patch_b = self.patch_system.patch_of(v)
                    actual_a = patch_a.extract(payoff_a, category="game") if payoff_a > 0 else payoff_a
                    actual_b = patch_b.extract(payoff_b, category="game") if payoff_b > 0 else payoff_b
                else:
                    actual_a, actual_b = payoff_a, payoff_b
                agent_a.resources += actual_a
                agent_b.resources += actual_b
                self._step_payoff[u] = self._step_payoff.get(u, 0.0) + actual_a
                self._step_payoff[v] = self._step_payoff.get(v, 0.0) + actual_b

                accuracy_a = effective_observation_accuracy(agent_a.observation_accuracy, active_perturbations)
                accuracy_b = effective_observation_accuracy(agent_b.observation_accuracy, active_perturbations)
                observation_rng = self._stream("observation_error")
                observed_b_by_a = observe_action(action_b, accuracy_a, observation_rng)
                observed_a_by_b = observe_action(action_a, accuracy_b, observation_rng)
                agent_a.record_observation(v, observed_b_by_a, actual_a, step)
                agent_b.record_observation(u, observed_a_by_b, actual_b, step)

                status_u = "dormant" if u in dormant else ("distressed" if distressed.get(u, False) else "solvent")
                status_v = "dormant" if v in dormant else ("distressed" if distressed.get(v, False) else "solvent")
                self.event_log.add(
                    InteractionEvent(
                        step=step,
                        agent_a=u,
                        agent_b=v,
                        action_a=action_a,
                        action_b=action_b,
                        payoff_a=actual_a,
                        payoff_b=actual_b,
                        observed_a_by_b=observed_a_by_b,
                        observed_b_by_a=observed_b_by_a,
                        punishment_available=self.config.punishment_enabled,
                        resource_status_a=status_u,
                        resource_status_b=status_v,
                        degree_a=self.graph.degree(u),
                        degree_b=self.graph.degree(v),
                    )
                )

                if self.config.punishment_enabled:
                    self._maybe_punish(step, punisher=agent_a, target=agent_b, observed=observed_b_by_a, true_action=action_b)
                    self._maybe_punish(step, punisher=agent_b, target=agent_a, observed=observed_a_by_b, true_action=action_a)

    def _maybe_punish(self, step: int, punisher: Agent, target: Agent, observed: int, true_action: int) -> None:
        if observed != DEFECT:
            return
        if self._stream("punishment").random() >= self.config.punishment_probability:
            return
        new_punisher_res, new_target_res = apply_punishment(
            punisher.resources, target.resources, self.config.punishment_cost, self.config.punishment_penalty
        )
        punisher.resources, target.resources = new_punisher_res, new_target_res
        erroneous = true_action == COOPERATE  # punished despite actually having cooperated
        self.event_log.add(
            PunishmentEvent(
                step=step,
                punisher=punisher.agent_id,
                target=target.agent_id,
                cost_to_punisher=self.config.punishment_cost,
                penalty_to_target=self.config.punishment_penalty,
                erroneous=erroneous,
            )
        )

    def _apply_subsistence(self, step: int, active_perturbations: list[PerturbationSpec]) -> None:
        if not self.config.ecology_enabled:
            return
        # Level 0.2, Work Package J: a "subsistence_increase" perturbation
        # scales the base charge up for its duration; a no-op (returns
        # config.subsistence_cost unchanged) when none is active, so this
        # is exact-compatible with every pre-Level-0.2 run.
        cost = effective_subsistence_cost(self.config.subsistence_cost, active_perturbations)
        if cost == 0:
            return
        for agent in self.agents:
            agent.resources -= cost
        self.event_log.add(
            SubsistenceEvent(
                step=step, per_agent_cost=cost, n_agents_charged=len(self.agents), total_cost=cost * len(self.agents)
            )
        )

    # -- ecological actions (Level 0.3, Work Packages A/B/C) ----------------
    def _ecological_round(self, step: int, active_perturbations: list[PerturbationSpec] | None = None) -> None:
        """Once per step, when ``config.ecology_topology == "patches"``:
        every living agent locally decides how much to request for
        extraction and how much to invest in maintenance (using only its
        own trait values and its own patch's occupancy — never any
        global or cross-patch quantity, per the milestone's local-
        information constraint), those requests are rationed per patch
        against that patch's *current* stock (Work Package B's allocation
        rule), the resulting per-agent ledger changes are applied
        (immediate individual benefit/cost — Work Package C), and finally
        each patch regenerates. A strict no-op when patches are not
        active.

        ``active_perturbations`` (Level 1.2b, Work Package C): any
        currently-active ``regeneration_reduction`` perturbations scale
        every patch's regeneration rate down for this step only (mirrors
        the pool-topology handling in ``_run_one_step`` exactly — save
        each patch's own base rate, apply the reduced rate for this
        step's ``regenerate()`` call, restore it immediately after, so
        no patch's stored ``regen_rate`` is ever permanently altered).
        Defaults to ``None`` (treated as no active perturbations) so
        every pre-existing direct call to this method is unaffected."""
        if self.patch_system is None:
            return
        config = self.config
        active_perturbations = active_perturbations or []

        # Local-information snapshot: every agent's decision this round is
        # based on its own patch's occupancy *before* this round's
        # extraction/maintenance/regeneration are applied (deterministic,
        # no lookahead — same convention as the distress snapshot in
        # _run_interactions).
        occupancy_snapshot = {pid: patch.fraction_of_capacity for pid, patch in self.patch_system.patches.items()}

        requested_extraction: dict[int, float] = {}
        requested_maintenance: dict[int, float] = {}
        #: agent_id -> (intended_h, intended_m, complied, enforcement_altered_action, rule_id) for
        #: agents who are a member of an active rule this step (Level 1.0,
        #: Work Package D/I) -- consumed below, after patch allocation, to
        #: emit one ComplianceEvent per member.
        compliance_this_step: dict[int, tuple[float, float, bool, bool, int]] = {}
        for agent in self.agents:
            if not agent.alive:
                continue
            occ = occupancy_snapshot[agent.patch_id]
            if config.ecological_policy_randomized_each_step:
                # Work Package F "randomized ecological policy"
                # counterfactual: a fresh i.i.d. draw every step, ignoring
                # (and never mutating) the agent's own inherited
                # ecological_policy entirely.
                decision_policy = sample_ecological_policy(
                    config.extraction_propensity_mean, config.extraction_propensity_std,
                    config.maintenance_propensity_mean, config.maintenance_propensity_std,
                    config.scarcity_sensitivity_mean, config.scarcity_sensitivity_std,
                    self._stream("ecological_action"),
                )
            else:
                decision_policy = agent.ecological_policy
            h, m = decide_ecological_action(
                decision_policy, occ, config.ecological_harvest_unit, config.ecological_maintenance_unit
            )

            # Level 1.0, Work Package D/I: a rule member's *intended*
            # request (computed above, from its own unconstrained
            # ecological policy, exactly like every other agent's) may be
            # adjusted by its rule's compliance decision before being
            # submitted to the patch -- the stored ecological_policy
            # itself is never touched (see rules/dynamics.py's module
            # docstring). A strict no-op for non-members and whenever
            # rule_formation_enabled is False (rule_member_of is then
            # always None, since nothing ever sets it).
            rule = None
            if agent.rule_member_of is not None:
                candidate = self.rule_registry.get(agent.patch_id)
                if candidate is not None and candidate.active and candidate.rule_id == agent.rule_member_of:
                    rule = candidate
            if rule is not None:
                complied = rule_dynamics.decide_rule_compliance(
                    agent, rule, decision_policy.extraction_propensity, decision_policy.maintenance_propensity,
                    config, self._stream("rule_formation_other"),
                )
                if config.randomized_pseudo_institution_mode:
                    # Stage-4 condition 8: the "complied" label above is a
                    # nominal coin flip used only for monitoring/sanction
                    # bookkeeping below -- the rule's actual content must
                    # never constrain the request itself, or the
                    # content-to-behavior linkage this condition is
                    # designed to break would leak back in through the
                    # cap/floor.
                    actual_h, actual_m, altered = h, m, False
                else:
                    actual_h, actual_m, altered = rule_dynamics.apply_rule_compliance(
                        h, m, rule, complied, config.ecological_harvest_unit, config.ecological_maintenance_unit
                    )
                compliance_this_step[agent.agent_id] = (h, m, complied, altered, rule.rule_id)
                if complied:
                    rule.compliance_count += 1
                else:
                    rule.violation_count += 1
                h, m = actual_h, actual_m

            requested_extraction[agent.agent_id] = h
            requested_maintenance[agent.agent_id] = m

        # Group by patch and allocate (Work Package B).
        actual_extraction: dict[int, float] = {}
        for pid, patch in self.patch_system.patches.items():
            members = [aid for aid in patch.members if self.agents_by_id[aid].alive]
            if not members:
                continue
            patch_requests = {aid: requested_extraction[aid] for aid in members}
            patch_maintenance = {aid: requested_maintenance[aid] for aid in members}

            # Level 1.0, Work Package F: under sanction_mode ==
            # "collective_fund", a fraction of every rule member's
            # maintenance request this step is diverted into the rule's
            # fund instead of the patch (the member still pays the full
            # amount out of its own resources below -- only what reaches
            # the *patch* is reduced). A no-op whenever no active
            # collective_fund rule has this patch's id, or the
            # contribution rate is 0.0 (the default).
            active_rule = self.rule_registry.get(pid)
            if (
                config.sanction_mode == "collective_fund"
                and config.institutional_fund_contribution_rate > 0.0
                and active_rule is not None and active_rule.active
            ):
                for aid in members:
                    if self.agents_by_id[aid].rule_member_of != active_rule.rule_id:
                        continue
                    diverted = patch_maintenance[aid] * config.institutional_fund_contribution_rate
                    patch_maintenance[aid] -= diverted
                    active_rule.fund += diverted

            if config.ecological_actions_affect_patch:
                actual = patch.request_extraction(
                    patch_requests, config.ecological_allocation_rule, self._stream("ecological_action")
                )
                patch.apply_maintenance(patch_maintenance, config.maintenance_efficiency)
            else:
                # Work Package F "no environmental effect" counterfactual:
                # agents still decide, still pay/earn exactly the same
                # amounts (computed by the identical allocation
                # arithmetic, against the patch's *actual* current stock),
                # but the patch's own state is left completely untouched
                # here — only its natural regeneration (below) still
                # runs. Ledger counters (cumulative_extraction etc.) are
                # deliberately NOT updated in this branch either, so a
                # patch-level diagnostic in this condition honestly shows
                # zero agent-driven ecological impact, not just an
                # unaffected stock.
                actual = allocate_extraction(
                    patch.resources, patch_requests, config.ecological_allocation_rule, self._stream("ecological_action")
                )
            actual_extraction.update(actual)

        # Apply per-agent ledger changes and record events (Work Package C).
        for agent in self.agents:
            if not agent.alive:
                continue
            aid = agent.agent_id
            h_req = requested_extraction[aid]
            m_req = requested_maintenance[aid]
            h_act = actual_extraction.get(aid, 0.0)
            m_effective_nominal = config.maintenance_efficiency * m_req
            search_cost = config.ecological_search_cost if h_req > 0 else 0.0
            net_ecological_payoff = h_act - m_req - search_cost

            agent.resources += h_act
            agent.resources -= m_req
            agent.resources -= search_cost
            agent.ecological_cumulative_gain += net_ecological_payoff
            agent.record_ecological_step_end(net_ecological_payoff, config.fitness_window)

            self.event_log.add(
                EcologicalActionEvent(
                    step=step,
                    agent=aid,
                    patch_id=agent.patch_id,
                    requested_extraction=h_req,
                    actual_extraction=h_act,
                    requested_maintenance=m_req,
                    maintenance_effective=m_effective_nominal,
                    ecological_search_cost=search_cost,
                    local_occupancy_observed=occupancy_snapshot[agent.patch_id],
                )
            )

            # Level 1.0, Work Package D/I: one ComplianceEvent per active
            # rule member, recording intended (unconstrained-policy) vs.
            # actual (post-compliance-decision, pre-patch-rationing)
            # request -- distinct from EcologicalActionEvent's
            # requested/actual pair, which is about *this agent's own
            # request* vs. *what the patch's rationing allocated it*, an
            # orthogonal (never institutional) constraint every agent
            # faces alike.
            if aid in compliance_this_step:
                intended_h, intended_m, complied, altered, rule_id = compliance_this_step[aid]
                self.event_log.add(
                    ComplianceEvent(
                        step=step,
                        patch_id=agent.patch_id,
                        rule_id=rule_id,
                        agent=aid,
                        intended_extraction=intended_h,
                        intended_maintenance=intended_m,
                        actual_extraction=h_req,
                        actual_maintenance=m_req,
                        complied=complied,
                        violated=not complied,
                        enforcement_altered_action=altered,
                    )
                )

        # Natural regeneration always runs, in every counterfactual
        # (including "no environmental effect" — that condition isolates
        # *agent-driven* feedback specifically, not the ecology's own
        # baseline dynamics).
        for patch in self.patch_system.patches.values():
            base_regen_rate = patch.regen_rate
            patch.regen_rate = effective_regen_rate(base_regen_rate, active_perturbations)
            patch.regenerate()
            patch.regen_rate = base_regen_rate

    # -- Level 1.0: locally shared rules --------------------------------------
    def _rule_formation_round(self, step: int) -> None:
        """Once per step, immediately after ``_ecological_round`` has
        produced this step's realized compliance ground truth (Work
        Package D): monitoring -> sanctioning -> proposal/adoption ->
        membership -> amendment -> dissolution (see ``rules/dynamics.py``'s
        module docstring for why this ordering). A strict no-op — zero
        extra RNG draws, zero new events, zero change to any existing
        metric — when ``config.rule_formation_enabled`` is False or no
        patch system is active (the exact Level-0.3b-compatible default)."""
        if not self.config.rule_formation_enabled or self.patch_system is None:
            return
        config = self.config
        compliance_events = [e for e in self.event_log.compliances if e.step == step]

        monitoring_events = rule_dynamics.monitoring_round(
            step, self.rule_registry, self.agents_by_id, compliance_events, config,
            self._stream("rule_formation_other"), self.event_log
        )
        rule_dynamics.sanction_round(
            step, self.rule_registry, self.agents_by_id, monitoring_events, config,
            self._stream("rule_formation_other"), self.event_log
        )

        if not config.institution_imposed_mode:
            occupancy_snapshot = {
                pid: patch.fraction_of_capacity for pid, patch in self.patch_system.patches.items()
            }
            patch_ids = list(self.patch_system.patches.keys())
            rule_dynamics.proposal_and_adoption_round(
                step, patch_ids, self.agents_by_id, self.patch_system, self.rule_registry,
                self._pending_rule_proposals, self._last_dissolved_rule_by_patch, occupancy_snapshot,
                config, self._stream("rule_proposal_adoption"), self.event_log, self._rule_id_state,
            )
            rule_dynamics.membership_round(
                step, self.rule_registry, self.agents_by_id, self.patch_system, config,
                self._stream("rule_formation_other"), self.event_log
            )
            # ``rule_registry`` is keyed by PATCH id (one active rule per
            # patch), not rule id -- so both snapshots below are keyed by
            # patch id despite their pre-existing names' suggestion
            # otherwise. Level 1.2b, Work Package E production-scale fix:
            # this whole block previously conflated the two ID spaces --
            # see the comments at each corrected call site below.
            #
            # Level 1.2b, Work Package E fix: snapshotted here, BEFORE
            # ``amendment_round`` (previously snapshotted AFTER it,
            # between ``amendment_round`` and ``dissolution_round``) --
            # ``amendment_round`` can itself dissolve-and-remove a rule
            # (a rejected amendment whose support also falls below
            # ``rule_dissolution_support_floor``; see its own
            # "support_below_floor" branch), so the pre/post diff below
            # must span both dissolution sources to route EITHER kind of
            # dissolution through the same delegate-cleanup/fund-
            # resolution pipeline. ``amendment_round`` never mutates
            # ``.members`` except via dissolution's own clearing, so
            # capturing membership here (rather than after
            # ``amendment_round``) is exact either way.
            pre_dissolution_members = {pid: frozenset(r.members) for pid, r in self.rule_registry.items()}
            pre_dissolution_patch_ids = set(self.rule_registry.keys())
            rule_dynamics.amendment_round(
                step, self.rule_registry, self.agents_by_id, config,
                self._stream("rule_formation_other"), self.event_log,
                self._last_dissolved_rule_by_patch,
                entrenchment_rng=self._stream("entrenchment_dynamics"),
            )
            rule_dynamics.dissolution_round(
                step, self.rule_registry, self.agents_by_id, self.patch_system, config, self.event_log,
                self._last_dissolved_rule_by_patch,
                entrenchment_rng=self._stream("entrenchment_dynamics"),
            )
            # Level 1.3, Work Package D (Section 9): after this step's
            # amendment/dissolution resolve, so a rule dissolved THIS
            # step gets no further legitimacy update (its own
            # ``if not rule.active: continue`` guard already handles
            # this, but running it last keeps "legitimacy reflects a
            # still-governing institution" true by construction).
            rule_dynamics.legitimacy_round(
                step, self.rule_registry, config, self._stream("legitimacy_accumulation"), self.event_log,
            )
            dissolved_patch_ids = pre_dissolution_patch_ids - set(self.rule_registry.keys())
            if dissolved_patch_ids:
                # Level 1.1, Work Package D: any active delegate whose
                # rule just dissolved loses its administrative object to
                # administer.
                #
                # Level 1.2b, Work Package E fix: ``handle_rule_dissolution_
                # removals`` matches against ``delegate.rule_id`` (an
                # actual rule ID), so it must be given actual dissolved
                # RULE ids -- passing ``dissolved_patch_ids`` directly (as
                # this call previously did, under the misleading name
                # ``dissolved_this_step``) instead removed any delegate
                # whose ``rule_id`` happened to numerically collide with a
                # dissolved PATCH id, an unrelated coincidence -- silently
                # corrupting institutional state (a delegate removed for
                # no real reason) independent of, and more consequential
                # than, this same bug's resource-accounting side effect
                # below. Only rules confirmed dissolved AT THIS STEP (not
                # a stale earlier dissolution still sitting in
                # ``_last_dissolved_rule_by_patch`` for that patch) are
                # included.
                dissolved_rule_ids = {
                    self._last_dissolved_rule_by_patch[pid].rule_id
                    for pid in dissolved_patch_ids
                    if pid in self._last_dissolved_rule_by_patch
                    and self._last_dissolved_rule_by_patch[pid].dissolution_step == step
                }
                rule_delegation.handle_rule_dissolution_removals(
                    step, dissolved_rule_ids, self.delegate_registry, self.rule_registry, self.agents_by_id, self.event_log
                )
                # Level 1.1, Work Package H requirement 6: dispose of
                # each dissolved rule's remaining fund exactly once,
                # using the pre-dissolution membership snapshot (by the
                # time dissolution_round returns, rule.members has
                # already been cleared to frozenset() by
                # rule_dynamics._dissolve).
                #
                # Level 1.2b, Work Package E fix: this loop previously
                # iterated the wrong condition (``dissolved_rule.rule_id
                # in dissolved_this_step`` compared a rule ID against a
                # set of PATCH ids, which is essentially never true) and
                # the wrong lookup key (``pre_dissolution_members.get(
                # dissolved_rule.rule_id, ...)`` against a dict keyed by
                # patch id) -- so ``resolve_dissolution_fund`` almost
                # never actually ran, and when a dissolved rule's fund
                # (which can be nonzero even under
                # ``contribution_mode="none"`` via coordination mutual-
                # assistance transfers) was simply dropped from the
                # registry by ``dissolution_round`` with no disposal
                # event at all -- an untracked sink, invisible at Level
                # 1.2b Work Package A's own short-run validation scale
                # (too few dissolutions to matter) but a real contributor
                # to the ledger residual newly discovered at Work Package
                # E's production scale. Iterating ``dissolved_patch_ids``
                # directly (the key space both dicts actually use) fixes
                # both the accounting gap and the previously-always-empty
                # ``members_at_dissolution`` recipient list for
                # ``"distributed_to_members"`` disposition.
                if config.contribution_mode != "none" or config.sanction_mode == "collective_fund":
                    for pid_dissolved in dissolved_patch_ids:
                        dissolved_rule = self._last_dissolved_rule_by_patch.get(pid_dissolved)
                        if dissolved_rule is not None and dissolved_rule.dissolution_step == step:
                            rule_contributions.resolve_dissolution_fund(
                                step, dissolved_rule, pre_dissolution_members.get(pid_dissolved, frozenset()),
                                self.agents_by_id, config, self.event_log,
                            )

        # Level 1.1, Work Package H: collective contributions (a strict
        # no-op when config.contribution_mode == "none").
        rule_contributions.contribution_round(
            step, self.rule_registry, self.agents_by_id, config, self._stream("contributions"), self.event_log,
            bargaining_pressure_level=self._pressure_level("bargaining_pressure_series", step),
        )

    def _delegation_round(self, step: int) -> None:
        """Once per step, immediately after ``_rule_formation_round``:
        accountability (Work Package G, against *last* step's already-
        realized delegate behavior) -> nomination/selection (Work
        Package D) -> task performance / capacity / discretion (Work
        Packages E/F). A strict no-op — zero extra RNG draws, zero new
        events — when ``config.delegation_enabled`` is False or no
        patch system is active."""
        if not self.config.delegation_enabled or self.patch_system is None:
            return
        config = self.config
        sanctions_this_step = [e for e in self.event_log.sanctions if e.step == step]
        rule_delegation.accountability_round(
            step, self.rule_registry, self.delegate_registry, self.agents_by_id, sanctions_this_step,
            config, self._stream("accountability"), self.event_log,
            bargaining_pressure_level=self._pressure_level("bargaining_pressure_series", step),
        )
        # Track realized capacity of any delegate removed this step (by
        # accountability_round's recalls, or by a rule dissolution
        # earlier this same step) as the read-only "observed reliability"
        # input to future candidate evaluation.
        for delegate in self.delegate_registry.values():
            if not delegate.active and delegate.removal_step == step:
                self._prior_delegate_capacity[delegate.agent_id] = delegate.capacity

        rule_delegation.nomination_and_selection_round(
            step, self.rule_registry, self.agents_by_id, self.patch_system, self.delegate_registry,
            self._pending_delegate_nominations, self._prior_delegate_capacity, config,
            self._stream("delegation_appointment"), self.event_log,
            self._delegate_id_state, self.delegate_history,
        )
        # Level 1.1b, Work Package A: administrative task-success draws and
        # discretion/appropriation draws are routed to two independent
        # streams (``discretion_rng`` falls back to ``rng`` when omitted, so
        # any other caller of ``task_performance_round`` that doesn't pass
        # it keeps drawing everything from one stream) — this is the one
        # genuine internal-mixing case Level 1.1's single shared RNG could
        # not isolate (see docs/level1.1b_rng_design.md).
        # Level 1.2, Work Package F: jurisdiction sizes as of the END of
        # the PREVIOUS step's ``_institutional_scaling_round`` (this
        # step's own coordination links haven't formed yet at this point
        # in the round order -- a disclosed one-step lag, the same
        # pattern Work Package C's amendment detection already uses).
        # ``None`` (not an empty dict) whenever scaling is disabled, so
        # ``task_performance_round``'s own no-op branch is exercised
        # exactly as it always was.
        jurisdiction_sizes = (
            rule_scaling.jurisdiction_size_by_patch(self._coordination_components)
            if config.institutional_scaling_enabled else None
        )
        rule_delegation.task_performance_round(
            step, self.rule_registry, self.delegate_registry, self.agents_by_id, config,
            self._stream("administrative_task_performance"), self.event_log,
            discretion_rng=self._stream("discretion_appropriation"),
            jurisdiction_size_by_patch=jurisdiction_sizes,
            security_pressure_level=self._pressure_level("security_pressure_series", step),
        )

    def _coordination_round(self, step: int) -> None:
        """Once per step, immediately after ``_delegation_round``: an
        interpatch coordination proposal/acceptance/activity/dissolution
        pass (Work Package I). A strict no-op — zero extra RNG draws,
        zero new events — when ``config.interpatch_coordination_enabled``
        is False. Deliberately independent of delegation state (see
        ``rules/coordination.py``'s module docstring)."""
        if not self.config.interpatch_coordination_enabled or self.patch_system is None:
            return
        rule_coordination.coordination_round(
            step, self.rule_registry, self.agents_by_id, self.patch_system, self.coordination_link_registry,
            self._pending_coordination_proposals, self.config, self._stream("interpatch_coordination"),
            self.event_log, self._coordination_id_state,
            coordination_complexity_level=self._pressure_level("coordination_complexity_series", step),
        )

    def _institution_lifecycle_round(self, step: int) -> None:
        """Level 1.2, Work Package A: once per step, immediately after
        ``_coordination_round`` -- a strict no-op when ``rule_registry``
        is empty (e.g. ``rule_formation_enabled=False``, or a patch
        system with no rules yet formed)."""
        if not self.rule_registry:
            return
        rule_institution.institution_lifecycle_round(
            step, self.rule_registry, self.institution_registry, self.config, self.event_log,
        )

    def _local_observation_round(self, step: int) -> None:
        """Level 1.2, Work Package B: once per step, immediately after
        ``_institution_lifecycle_round`` -- true-signal history
        bookkeeping always runs when there is at least one active rule
        (needed for Work Package C/D's own use of recent true signals in
        later steps even when observation itself is disabled); actual
        perceived-observation formation is additionally gated on
        ``config.institutional_observation_enabled``. Zero extra RNG
        draws when ``rule_registry`` is empty."""
        if not self.rule_registry or self.patch_system is None:
            return
        rule_observation.local_observation_round(
            step, self.rule_registry, self.patch_system.patches, self.coordination_link_registry,
            self.institution_registry, self.agents_by_id, self.delegate_registry, self.config,
            self._stream("institutional_observation"), self.event_log, self._true_signal_history,
        )

    def _institution_transmission_round(self, step: int) -> None:
        """Level 1.2, Work Package C: once per step, immediately after
        ``_local_observation_round`` -- a strict no-op when
        ``config.institutional_transmission_enabled`` is False. A
        transmission-driven amendment to a rule's parameters/overrides
        this step is picked up by ``_institution_lifecycle_round`` at the
        START of the *next* step (a disclosed one-step detection lag —
        the amendment itself is applied immediately and is fully live
        for every mechanism reading the rule this same step)."""
        if not self.rule_registry or self.patch_system is None:
            return
        rule_transmission.institution_transmission_round(
            step, self.rule_registry, self.institution_registry, self.coordination_link_registry,
            self.agents_by_id, self.config, self._stream("institutional_transmission"),
            self.event_log, self._true_signal_history,
        )

    def _migration_round(self, step: int) -> None:
        """Level 1.2, Work Package D: once per step, immediately after
        ``_institution_transmission_round`` -- both
        ``rule_migration.migration_round`` and
        ``rule_migration.membership_exit_round`` are strict no-ops when
        their own master flags (``migration_enabled``/
        ``membership_exit_enabled``) are False, independent of each
        other."""
        if self.patch_system is None:
            return
        rule_migration.migration_round(
            step, self.rule_registry, self.patch_system, self.agents_by_id, self.config,
            self._stream("migration"), self.event_log, self._true_signal_history,
        )
        rule_migration.membership_exit_round(
            step, self.rule_registry, self.agents_by_id, self.config,
            self._stream("migration"), self.event_log,
        )

    def _institutional_scaling_round(self, step: int) -> None:
        """Level 1.2, Work Package F: once per step, last among the
        Level 1.2 rounds -- recomputes coordination-network jurisdictions
        from this step's now-final ``coordination_link_registry`` state
        and stores them for the *next* step's ``_delegation_round`` to
        read (see that method's own comment on the resulting one-step
        lag). A strict no-op when
        ``config.institutional_scaling_enabled`` is False."""
        self._coordination_components = rule_scaling.institutional_scaling_round(
            step, self.coordination_link_registry, self.config, self.event_log, self._coordination_components,
        )

    def _decay_memories(self) -> None:
        for agent in self.agents:
            agent.decay_reputations()

    # -- viability state machine (Level 0.2, Work Package B) -----------------
    def _viability_round(self, step: int) -> None:
        """Update every agent's cumulative-deficit counter and viability
        state, once per step (duration-based, not a one-step trigger — see
        core/config.py's field docs). A strict no-op (0 extra RNG draws, no
        state ever leaves "active") when ``ecology_enabled=False`` or
        ``viability_mode="none"`` — the Level-0/Level-0.1-compatible case."""
        if not self.config.ecology_enabled or self.config.viability_mode == "none":
            return

        threshold = self.config.distress_threshold
        recovery = self.config.viability_recovery_resources
        deficit_limit = self.config.viability_deficit_steps_threshold
        dormant_limit = self.config.viability_max_dormant_steps

        for agent in list(self.agents):
            in_deficit = agent.resources < threshold
            agent.consecutive_deficit_steps = agent.consecutive_deficit_steps + 1 if in_deficit else 0
            prev_state = agent.viability_state

            if prev_state == "active":
                if in_deficit:
                    agent.viability_state = "distressed"
                    self._log_viability_transition(step, agent, prev_state, "distressed", "entered_deficit")

            elif prev_state == "distressed":
                if agent.resources >= recovery:
                    agent.viability_state = "active"
                    self._log_viability_transition(step, agent, prev_state, "active", "resources_recovered")
                elif agent.consecutive_deficit_steps >= deficit_limit:
                    agent.viability_state = "dormant"
                    agent.dormant_steps = 0
                    self._log_viability_transition(step, agent, prev_state, "dormant", "deficit_streak_exceeded")

            elif prev_state == "dormant":
                agent.dormant_steps += 1
                if agent.resources >= recovery:
                    agent.viability_state = "active"
                    agent.consecutive_deficit_steps = 0
                    agent.dormant_steps = 0
                    self._log_viability_transition(step, agent, prev_state, "active", "resources_recovered")
                elif self.config.viability_mode == "removal_replacement" and agent.dormant_steps >= dormant_limit:
                    agent.viability_state = "nonviable"
                    self._log_viability_transition(step, agent, prev_state, "nonviable", "dormancy_exceeded")
                    self._replace_agent(agent, step)

    def _log_viability_transition(self, step: int, agent: Agent, from_state: str, to_state: str, cause: str) -> None:
        self.event_log.add(
            ViabilityTransitionEvent(
                step=step,
                agent=agent.agent_id,
                from_state=from_state,
                to_state=to_state,
                resources_at_transition=agent.resources,
                cause=cause,
            )
        )

    def _replace_agent(self, agent: Agent, step: int) -> None:
        """``removal_replacement`` mode only: a persistently-nonviable agent
        is removed and a fresh individual takes over the same population
        slot (``agent_id``, same graph node — the network topology is
        otherwise untouched by this event). See
        ``config.viability_replacement_policy`` for the inheritance rule
        options; resources always reset via the same draw the initial
        population uses, regardless of which policy-inheritance rule is
        active, so demographic churn accounting isn't entangled with policy
        inheritance choice."""
        old_demographic_id = agent.demographic_id
        old_policy_name = agent.policy.name
        resources_at_removal = agent.resources

        # Level 1.1b, Work Package A: demographic replacement (a fresh
        # individual's traits/policy) is its own isolated stream, distinct
        # from "initialization" (the *original* population draw) — so a
        # counterfactual that changes how often replacement fires cannot
        # perturb the initial-population draw sequence, and vice versa.
        replacement_rng = self._stream("demographic_replacement")
        living_others = [a for a in self.agents if a.alive and a.agent_id != agent.agent_id]
        rule = self.config.viability_replacement_policy
        new_lineage_id: int
        if rule == "random_init" or not living_others:
            names = list(self.config.policy_mix.keys()) or list(VALID_POLICY_NAMES)
            fracs = list(self.config.policy_mix.values()) or [1.0 / len(names)] * len(names)
            new_policy_name = names[int(replacement_rng.choice(len(names), p=np.array(fracs) / sum(fracs)))]
            new_lineage_id = next(self._lineage_counter)
        elif rule == "dominant_policy":
            counts = Counter(a.policy.name for a in living_others)
            new_policy_name = counts.most_common(1)[0][0]
            exemplar = next(a for a in living_others if a.policy.name == new_policy_name)
            new_lineage_id = exemplar.policy_lineage_id
        elif rule == "parent_lineage_imitation":
            exemplar = living_others[int(replacement_rng.integers(0, len(living_others)))]
            new_policy_name = exemplar.policy.name
            new_lineage_id = exemplar.policy_lineage_id
        elif rule == "mutation_fresh":
            new_policy_name = VALID_POLICY_NAMES[int(replacement_rng.integers(0, len(VALID_POLICY_NAMES)))]
            new_lineage_id = next(self._lineage_counter)
        else:  # pragma: no cover - unreachable given config validation
            raise ValueError(f"unknown viability_replacement_policy: {rule!r}")

        obs_acc = float(np.clip(replacement_rng.normal(self.config.observation_accuracy_mean, self.config.observation_accuracy_std), 0.0, 1.0))
        lr = float(np.clip(replacement_rng.normal(self.config.learning_rate_mean, self.config.learning_rate_std), 0.01, 1.0))
        forgiveness = float(np.clip(replacement_rng.normal(self.config.forgiveness_mean, self.config.forgiveness_std), 0.0, 1.0))
        risk = float(np.clip(replacement_rng.normal(self.config.risk_sensitivity_mean, self.config.risk_sensitivity_std), 0.0, 1.0))
        new_resources = float(max(0.1, replacement_rng.normal(self.config.initial_resources_mean, self.config.initial_resources_std)))
        new_coercive = float(max(0.0, replacement_rng.normal(self.config.initial_coercive_capability_mean, self.config.initial_coercive_capability_std)))
        new_demographic_id = next(self._demographic_counter)

        agent.policy = make_policy(new_policy_name)
        agent.policy_lineage_id = new_lineage_id
        agent.demographic_id = new_demographic_id
        agent.resources = new_resources
        agent.coercive_capability = new_coercive
        agent.observation_accuracy = obs_acc
        agent.learning_rate = lr
        agent.forgiveness = forgiveness
        agent.risk_sensitivity = risk
        agent.viability_state = "active"
        agent.consecutive_deficit_steps = 0
        agent.dormant_steps = 0
        agent.replacement_count += 1
        agent.memory.clear()
        agent.reputation_estimates.clear()
        agent.partner_payoff_estimate.clear()
        agent.relationship_started_at.clear()
        agent.resource_window.clear()
        agent.payoff_window.clear()
        # Level 0.3, Work Package D: a demographic replacement is exactly
        # like a fresh agent joining the population from the same trait
        # distributions -- it draws a brand-new ecological policy (fresh
        # ecological lineage id) exactly as build_agents() does for the
        # initial population, whenever patches are active; the ecological
        # ledger resets to zero/empty exactly like the social resource/
        # payoff windows just above. patch_id itself is NOT reassigned --
        # patch membership is fixed for the life of the simulation
        # regardless of which occupant currently holds a population slot
        # (see environment/patches.py's module docstring).
        agent.ecological_cumulative_gain = 0.0
        agent.ecological_payoff_window.clear()
        agent.ecological_cumulative_window.clear()
        if self.patch_system is not None:
            agent.ecological_policy = sample_ecological_policy(
                self.config.extraction_propensity_mean,
                self.config.extraction_propensity_std,
                self.config.maintenance_propensity_mean,
                self.config.maintenance_propensity_std,
                self.config.scarcity_sensitivity_mean,
                self.config.scarcity_sensitivity_std,
                replacement_rng,
            )
            agent.ecological_policy_lineage_id = next(self._ecological_lineage_counter)
        # Re-establish memory bookkeeping for this slot's current neighbors
        # (the graph edges are untouched by replacement — only the
        # occupant's internal state resets).
        for neighbor in self.graph.neighbors(agent.agent_id):
            agent.ensure_partner(neighbor, step)
            self.agents_by_id[neighbor].ensure_partner(agent.agent_id, step)

        self.event_log.add(
            ReplacementEvent(
                step=step,
                agent_id=agent.agent_id,
                old_demographic_id=old_demographic_id,
                new_demographic_id=new_demographic_id,
                old_policy=old_policy_name,
                new_policy=agent.policy.name,
                inheritance=rule,
                resources_at_removal=resources_at_removal,
                initial_resources=new_resources,
            )
        )

    def _rewiring_round_legacy(self, step: int) -> None:
        """Original Level-0 exit/rewiring logic, unmodified. Only used when
        ``relationship_dynamics_enabled=False`` (compatibility mode)."""
        relationship_rng = self._stream("relationship_dynamics")
        order = [int(x) for x in relationship_rng.permutation([a.agent_id for a in self.agents])]

        for aid in order:
            agent = self.agents_by_id[aid]
            for neighbor in list(self.graph.neighbors(aid)):
                payoff_est = agent.partner_payoff_estimate.get(neighbor, 0.0)
                if payoff_est < self.config.exit_resource_threshold:
                    event = exit_relationship(
                        self.graph, self.agents_by_id, aid, neighbor, self.config.exit_cost, step
                    )
                    self.event_log.add(event)

        for aid in order:
            if self.graph.degree(aid) < self.config.mean_degree:
                event = rewire(self.graph, aid, relationship_rng, step)
                self.event_log.add(event)
                if event.new_partner is not None:
                    self.agents_by_id[aid].ensure_partner(event.new_partner, step)
                    self.agents_by_id[event.new_partner].ensure_partner(aid, step)

    def _relationship_dynamics_round(self, step: int) -> None:
        """Level 0.1 endogenous relationship dynamics (Work Package B):
        affordability-gated voluntary exit, and accept/reject connection
        proposals rather than blind edge addition."""
        relationship_rng = self._stream("relationship_dynamics")
        order = [int(x) for x in relationship_rng.permutation([a.agent_id for a in self.agents])]

        if self.config.relationship_exit_enabled:
            for aid in order:
                agent = self.agents_by_id[aid]
                for neighbor in list(self.graph.neighbors(aid)):
                    if reldyn.wants_to_exit(agent, neighbor, self.config.exit_resource_threshold):
                        event = reldyn.attempt_exit(
                            self.graph, self.agents_by_id, aid, neighbor, self.config.exit_cost, step
                        )
                        self.event_log.add(event)

        for aid in order:
            if self.graph.degree(aid) < self.config.mean_degree:
                proposal, edge_event = reldyn.attempt_connection(
                    self.graph, aid, relationship_rng, step, self.config.connection_accept_base_prob, self.config.mean_degree
                )
                self.event_log.add(proposal)
                if proposal.reason != "no_candidate":
                    self.agents_by_id[aid].resources -= self.config.search_cost
                if edge_event is not None:
                    self.event_log.add(edge_event)
                    self.agents_by_id[edge_event.agent_a].ensure_partner(edge_event.agent_b, step)
                    self.agents_by_id[edge_event.agent_b].ensure_partner(edge_event.agent_a, step)

    def _adaptation_round(self, step: int) -> None:
        # Level 0.3, Work Package D: only two of the milestone's four named
        # inheritance modes are implemented -- "independent" (default: the
        # social and ecological dimensions each get their own peer draw and
        # own Fermi decision, never entangled) and "coupled_same_model"
        # ("both from same model agent": one peer draw + one Fermi decision
        # governs both dimensions together). The other two named modes
        # ("ecological independent [of social]" and "both independently,
        # potentially different model agents") are subsumed by
        # "independent" as implemented here -- see
        # dev_mem/status_update.md's Level 0.3 entry for the documented
        # limitation the milestone brief explicitly allows.
        ecological_active = self.patch_system is not None
        coupled = ecological_active and self.config.ecological_inheritance_mode == "coupled_same_model"

        if coupled:
            # ONE peer draw, ONE Fermi decision (stream="total") drives
            # both dimensions this round -- this REPLACES the ordinary
            # independent social imitation_round call below; running both
            # would double-apply social imitation for the same step.
            #
            # Level 1.0 preflight repair (see coupled_dual_imitation_round's
            # docstring for the full rationale): the two dimensions are now
            # gated *independently* by their own flags even though they
            # share one underlying decision --
            # config.ecological_imitation_enabled alone can freeze the
            # ecological copy without also freezing social imitation, and
            # config.ecological_policy_randomized_each_step alone suppresses
            # the ecological copy (it would be behaviorally inert -- the
            # per-step decision never reads the stored policy when
            # randomized -- but was previously still applied and logged).
            apply_social = self.config.imitation_enabled
            apply_ecological = (
                self.config.ecological_imitation_enabled
                and not self.config.ecological_policy_randomized_each_step
            )
            if apply_social or apply_ecological:
                social_events, ecological_events = coupled_dual_imitation_round(
                    self.agents,
                    self._stream("imitation"),
                    step,
                    fitness_mode=self.config.fitness_mode,
                    viability_adjusted_dormant_penalty=self.config.viability_adjusted_dormant_penalty,
                    apply_social=apply_social,
                    apply_ecological=apply_ecological,
                )
                for event in social_events:
                    self.event_log.add(event)
                for event in ecological_events:
                    self.event_log.add(event)
        else:
            if self.config.imitation_enabled:
                for event in imitation_round(
                    self.agents,
                    self._stream("imitation"),
                    step,
                    fitness_mode=self.config.fitness_mode,
                    viability_adjusted_dormant_penalty=self.config.viability_adjusted_dormant_penalty,
                ):
                    self.event_log.add(event)
            # Ecological-policy imitation gets its own independent peer
            # draw and Fermi decision, on its own fitness stream/mode --
            # skipped entirely under the "randomized each step"
            # counterfactual (Work Package F), where an agent's stored
            # ecological_policy is never read for decisions and must
            # therefore never be overwritten by imitation either.
            if (
                ecological_active
                and self.config.ecological_imitation_enabled
                and not self.config.ecological_policy_randomized_each_step
            ):
                for event in ecological_imitation_round(
                    self.agents,
                    self._stream("imitation"),
                    step,
                    fitness_mode=self.config.fitness_mode_ecological,
                    viability_adjusted_dormant_penalty=self.config.viability_adjusted_dormant_penalty,
                ):
                    self.event_log.add(event)

        mutation_rng = self._stream("mutation")
        for event in mutation_round(self.agents, self.config.mutation_rate, mutation_rng, step, self._lineage_counter):
            self.event_log.add(event)

        if ecological_active and not self.config.ecological_policy_randomized_each_step:
            for event in ecological_mutation_round(
                self.agents,
                self.config.ecological_mutation_rate,
                mutation_rng,
                step,
                self.config.extraction_propensity_mean,
                self.config.extraction_propensity_std,
                self.config.maintenance_propensity_mean,
                self.config.maintenance_propensity_std,
                self.config.scarcity_sensitivity_mean,
                self.config.scarcity_sensitivity_std,
                self._ecological_lineage_counter,
            ):
                self.event_log.add(event)

        self.policy_snapshots.append(policy_snapshot(self.agents, step))
        if ecological_active:
            self.ecological_policy_snapshots.append(ecological_policy_snapshot(self.agents, step))

    def _record_fitness_windows(self) -> None:
        """Once per step, after every resource-affecting mechanic for that
        step has run: sample each agent's current resources and this
        step's net game-interaction payoff into its rolling fitness
        windows (Level 0.2, Work Package C). Pure bookkeeping — never
        consumes RNG, never read by any decision function inside this same
        step."""
        for agent in self.agents:
            agent.record_step_end(self._step_payoff.get(agent.agent_id, 0.0), self.config.fitness_window)

    # -- main loop --------------------------------------------------------
    def _run_one_step(self, step: int) -> dict:
        """Execute exactly one simulation step and return its metrics row.
        Factored out of :meth:`run` (Level 0.3) so that experiment code
        needing to intervene *between* steps — e.g. Work Package J's
        perturbation experiments, which apply a shock directly to
        ``self.patch_system``/``self.agents`` at a chosen step, something
        the pre-existing pool-only ``core/perturbation.py`` mechanism has
        no vocabulary for — can call this method in a loop instead of
        going through :meth:`run` end-to-end. Behaviourally identical to
        the body of the pre-refactor ``run`` loop; ``run`` itself is now a
        thin wrapper around repeated calls to this method, so ordinary
        (non-intervening) callers see no change at all."""
        self._step_potential_extraction_demand = 0.0
        self._step_payoff = {}
        extracted_before = self.pool.total_extracted if self.pool is not None else 0.0

        self._viability_round(step)
        active_perturbations = self._apply_perturbations(step)
        self._run_interactions(step, active_perturbations)
        self._apply_subsistence(step, active_perturbations)
        realized_regen = 0.0
        if self.pool is not None:
            # Level 0.2, Work Package J: a "regeneration_reduction"
            # perturbation temporarily scales the pool's regen_rate
            # down for exactly this call, then restores it immediately
            # — a no-op (base rate unchanged) when none is active.
            base_regen_rate = self.pool.regen_rate
            self.pool.regen_rate = effective_regen_rate(base_regen_rate, active_perturbations)
            realized_regen = self.pool.regenerate()
            self.pool.regen_rate = base_regen_rate
        self._step_realized_extraction = (self.pool.total_extracted - extracted_before) if self.pool is not None else 0.0
        if self.patch_system is not None:
            self._ecological_round(step, active_perturbations)
            self._rule_formation_round(step)
            self._delegation_round(step)
            self._coordination_round(step)
            self._institution_lifecycle_round(step)
            self._local_observation_round(step)
            self._institution_transmission_round(step)
            self._migration_round(step)
            self._institutional_scaling_round(step)
        self._decay_memories()
        if self.scheduler.should_rewire(step):
            if self.config.relationship_dynamics_enabled:
                self._relationship_dynamics_round(step)
            else:
                self._rewiring_round_legacy(step)
        if self.scheduler.should_imitate(step):
            self._adaptation_round(step)
        self._record_fitness_windows()
        row = compute_step_metrics(
            self.agents,
            self.graph,
            self.event_log,
            step,
            pool=self.pool,
            potential_extraction_demand=self._step_potential_extraction_demand,
            realized_extraction=self._step_realized_extraction,
            realized_regeneration=realized_regen,
            config=self.config,
            interaction_edge_count=self._step_interaction_edge_count,
        )
        # Level 0.3, Work Package E: local-patch / ecological-action /
        # cross-domain metrics, merged into the same per-step row.
        # All-NaN (never a silently substituted 0.0) whenever
        # patch_system is None -- see niche_metrics.py's module
        # docstring.
        row.update(patch_occupancy_summary(self.patch_system))
        row.update(ecological_step_summary(self.event_log, step))
        row.update(joint_action_frequencies(self.event_log, step))
        return row

    def run(self) -> SimulationResult:
        metrics: list[dict] = [self._run_one_step(step) for step in range(self.config.n_steps)]

        return SimulationResult(
            config=self.config,
            metrics=metrics,
            final_agents=self.agents,
            final_graph=self.graph,
            event_log=self.event_log,
            initial_total_resources=self.initial_total_resources,
            final_environment_pool=self.pool,
            policy_snapshots=self.policy_snapshots,
            final_patch_system=self.patch_system,
            ecological_policy_snapshots=self.ecological_policy_snapshots,
        )
