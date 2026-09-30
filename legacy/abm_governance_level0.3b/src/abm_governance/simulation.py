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
    EcologicalActionEvent,
    EventLog,
    InteractionEvent,
    PunishmentEvent,
    ReplacementEvent,
    SubsistenceEvent,
    ViabilityTransitionEvent,
    WithholdEvent,
)
from abm_governance.core.perturbation import (
    PerturbationSpec,
    apply_instantaneous_effects,
    boundary_events,
    effective_observation_accuracy,
    effective_regen_rate,
    effective_subsistence_cost,
    specs_from_config,
)
from abm_governance.core.rng import make_rng
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


def build_agents(config: SimulationConfig, rng: np.random.Generator) -> list[Agent]:
    """Draw a heterogeneous population from the config's trait
    distributions. Exact policy counts (not merely expected proportions)
    are assigned from ``config.policy_mix`` so that small-population unit
    tests get deterministic, exactly-matching counts."""
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
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.rng = make_rng(config.seed)
        self.agents = build_agents(config, self.rng)
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

    # -- per-step mechanisms --------------------------------------------------
    def _active_perturbations(self, step: int) -> list[PerturbationSpec]:
        return [s for s in self._perturbation_specs if s.is_active(step)]

    def _apply_perturbations(self, step: int) -> list:
        active = self._active_perturbations(step)
        for spec in self._perturbation_specs:
            apply_instantaneous_effects(spec, step, self.pool, self.rng)
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

                engage_a = True
                engage_b = True
                if distressed.get(u, False):
                    engage_a = self.rng.random() < self.config.distress_engagement_prob
                if distressed.get(v, False):
                    engage_b = self.rng.random() < self.config.distress_engagement_prob
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

                action_a = agent_a.policy.decide(agent_a.partner_history(v), self.rng)
                action_b = agent_b.policy.decide(agent_b.partner_history(u), self.rng)
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
                observed_b_by_a = observe_action(action_b, accuracy_a, self.rng)
                observed_a_by_b = observe_action(action_a, accuracy_b, self.rng)
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
        if self.rng.random() >= self.config.punishment_probability:
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
    def _ecological_round(self, step: int) -> None:
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
        active."""
        if self.patch_system is None:
            return
        config = self.config

        # Local-information snapshot: every agent's decision this round is
        # based on its own patch's occupancy *before* this round's
        # extraction/maintenance/regeneration are applied (deterministic,
        # no lookahead — same convention as the distress snapshot in
        # _run_interactions).
        occupancy_snapshot = {pid: patch.fraction_of_capacity for pid, patch in self.patch_system.patches.items()}

        requested_extraction: dict[int, float] = {}
        requested_maintenance: dict[int, float] = {}
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
                    config.scarcity_sensitivity_mean, config.scarcity_sensitivity_std, self.rng,
                )
            else:
                decision_policy = agent.ecological_policy
            h, m = decide_ecological_action(
                decision_policy, occ, config.ecological_harvest_unit, config.ecological_maintenance_unit
            )
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
            if config.ecological_actions_affect_patch:
                actual = patch.request_extraction(patch_requests, config.ecological_allocation_rule, self.rng)
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
                actual = allocate_extraction(patch.resources, patch_requests, config.ecological_allocation_rule, self.rng)
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

        # Natural regeneration always runs, in every counterfactual
        # (including "no environmental effect" — that condition isolates
        # *agent-driven* feedback specifically, not the ecology's own
        # baseline dynamics).
        for patch in self.patch_system.patches.values():
            patch.regenerate()

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

        living_others = [a for a in self.agents if a.alive and a.agent_id != agent.agent_id]
        rule = self.config.viability_replacement_policy
        new_lineage_id: int
        if rule == "random_init" or not living_others:
            names = list(self.config.policy_mix.keys()) or list(VALID_POLICY_NAMES)
            fracs = list(self.config.policy_mix.values()) or [1.0 / len(names)] * len(names)
            new_policy_name = names[int(self.rng.choice(len(names), p=np.array(fracs) / sum(fracs)))]
            new_lineage_id = next(self._lineage_counter)
        elif rule == "dominant_policy":
            counts = Counter(a.policy.name for a in living_others)
            new_policy_name = counts.most_common(1)[0][0]
            exemplar = next(a for a in living_others if a.policy.name == new_policy_name)
            new_lineage_id = exemplar.policy_lineage_id
        elif rule == "parent_lineage_imitation":
            exemplar = living_others[int(self.rng.integers(0, len(living_others)))]
            new_policy_name = exemplar.policy.name
            new_lineage_id = exemplar.policy_lineage_id
        elif rule == "mutation_fresh":
            new_policy_name = VALID_POLICY_NAMES[int(self.rng.integers(0, len(VALID_POLICY_NAMES)))]
            new_lineage_id = next(self._lineage_counter)
        else:  # pragma: no cover - unreachable given config validation
            raise ValueError(f"unknown viability_replacement_policy: {rule!r}")

        obs_acc = float(np.clip(self.rng.normal(self.config.observation_accuracy_mean, self.config.observation_accuracy_std), 0.0, 1.0))
        lr = float(np.clip(self.rng.normal(self.config.learning_rate_mean, self.config.learning_rate_std), 0.01, 1.0))
        forgiveness = float(np.clip(self.rng.normal(self.config.forgiveness_mean, self.config.forgiveness_std), 0.0, 1.0))
        risk = float(np.clip(self.rng.normal(self.config.risk_sensitivity_mean, self.config.risk_sensitivity_std), 0.0, 1.0))
        new_resources = float(max(0.1, self.rng.normal(self.config.initial_resources_mean, self.config.initial_resources_std)))
        new_coercive = float(max(0.0, self.rng.normal(self.config.initial_coercive_capability_mean, self.config.initial_coercive_capability_std)))
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
                self.rng,
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
        order = [int(x) for x in self.rng.permutation([a.agent_id for a in self.agents])]

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
                event = rewire(self.graph, aid, self.rng, step)
                self.event_log.add(event)
                if event.new_partner is not None:
                    self.agents_by_id[aid].ensure_partner(event.new_partner, step)
                    self.agents_by_id[event.new_partner].ensure_partner(aid, step)

    def _relationship_dynamics_round(self, step: int) -> None:
        """Level 0.1 endogenous relationship dynamics (Work Package B):
        affordability-gated voluntary exit, and accept/reject connection
        proposals rather than blind edge addition."""
        order = [int(x) for x in self.rng.permutation([a.agent_id for a in self.agents])]

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
                    self.graph, aid, self.rng, step, self.config.connection_accept_base_prob, self.config.mean_degree
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
            if self.config.imitation_enabled:
                social_events, ecological_events = coupled_dual_imitation_round(
                    self.agents,
                    self.rng,
                    step,
                    fitness_mode=self.config.fitness_mode,
                    viability_adjusted_dormant_penalty=self.config.viability_adjusted_dormant_penalty,
                )
                for event in social_events:
                    self.event_log.add(event)
                for event in ecological_events:
                    self.event_log.add(event)
        else:
            if self.config.imitation_enabled:
                for event in imitation_round(
                    self.agents,
                    self.rng,
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
                    self.rng,
                    step,
                    fitness_mode=self.config.fitness_mode_ecological,
                    viability_adjusted_dormant_penalty=self.config.viability_adjusted_dormant_penalty,
                ):
                    self.event_log.add(event)

        for event in mutation_round(self.agents, self.config.mutation_rate, self.rng, step, self._lineage_counter):
            self.event_log.add(event)

        if ecological_active and not self.config.ecological_policy_randomized_each_step:
            for event in ecological_mutation_round(
                self.agents,
                self.config.ecological_mutation_rate,
                self.rng,
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
            self._ecological_round(step)
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
