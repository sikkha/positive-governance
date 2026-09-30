"""Observer-layer aggregate metrics.

Every function here is a pure function of a simulation *snapshot*
(agents, network graph, event log, and — as of Level 0.1 — the
environment pool) — none of them mutate simulation state, and none of them
are ever called from inside the generative loop's decision logic. This is
the read-only boundary described in dev_mem/project_vision.md, section 5.

None of these metrics are, or are derived from, State Capacity / Rule of
Law / Democratic Accountability / Institutional Constraint as defined in
the dissertation. They are independently-motivated observables of the
generative process itself (cooperation, inequality, network structure,
enforcement activity, diversity). Any later mapping onto the dissertation's
S/Z/typology categories is an explicitly separate, downstream research step
— see project_vision.md §5 and §3 — not something this module performs.

Level 0.1 note: per-step columns here deliberately use only *this step's*
events (cheap, O(edges) per step) for anything derived from the event log.
Full-run or windowed confusion-matrix rates
(``observer/enforcement.py::confusion_matrix_summary``) and dynamical
diagnostics (``observer/dynamics.py``) are computed on demand from the
complete metrics series or event log instead of being recomputed from
scratch every step, to keep a full run's metrics collection linear in the
number of steps rather than quadratic.

Level 0.2 note (Work Packages A, B, D): this module now also exports raw
participation-opportunity counts, conditional/unconditional cooperation
probabilities, viability-state population counts, and ecological
supply/demand ingredients. Every new conditional-probability column uses
``_safe_ratio`` (NaN, never a silently-substituted 0.0, for a zero
denominator — matching ``observer/enforcement.py``'s established
convention) and every ratio's numerator/denominator counts are *also*
exported as their own columns so nothing is "hidden inside the ratio" (a
milestone brief requirement for the ecological balance indicator, applied
here to every new ratio for consistency). The pre-existing
``cooperation_rate``/``defection_rate`` columns are left completely
unchanged (same definition, same values) — they are conditional-on-
interaction rates and satisfy the brief's "retain legacy cooperation metric
under a clearly-labelled compatibility name" requirement by construction;
see ``cooperation_rate_conditional_on_interaction`` below for the
explicitly-labelled alias.
"""

from __future__ import annotations

import math
from collections import Counter

import networkx as nx
import numpy as np

from abm_governance.agents.agent import Agent
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import EventLog
from abm_governance.environment.resource_pool import EnvironmentResourcePool
from abm_governance.interactions.game import COOPERATE, DEFECT
from abm_governance.observer.network_diagnostics import (
    component_stats,
    degree_distribution_summary,
    isolated_agent_count,
    policy_assortativity,
    relationship_age_distribution,
)


def gini(values: list[float]) -> float:
    """Gini coefficient of a list of non-negative values. Returns 0.0 for an
    empty list or when all values are zero (perfect equality by convention)."""
    arr = np.sort(np.asarray(values, dtype=float))
    arr = np.clip(arr, 0.0, None)  # Gini is defined for non-negative wealth
    n = len(arr)
    total = arr.sum()
    if n == 0 or total == 0:
        return 0.0
    index = np.arange(1, n + 1)
    return float((2.0 * np.sum(index * arr) - (n + 1) * total) / (n * total))


def shannon_entropy(labels: list[str]) -> float:
    """Shannon entropy (base 2, in bits) of a categorical label sequence.
    Used for behavioural-policy diversity. Returns 0.0 for an empty input
    or when only one category is present."""
    if not labels:
        return 0.0
    counts = Counter(labels)
    n = len(labels)
    entropy = 0.0
    for c in counts.values():
        p = c / n
        entropy -= p * math.log2(p)
    return entropy


def _safe_ratio(numerator: float, denominator: float) -> float:
    """``numerator / denominator``, or ``math.nan`` (never a silently
    substituted 0.0) when ``denominator`` is 0 — see module docstring and
    ``observer/enforcement.py::_safe_ratio``, whose convention this
    mirrors exactly."""
    return numerator / denominator if denominator > 0 else math.nan


#: Work Package A: withhold reasons attributable to distress (soft,
#: probabilistic non-engagement) vs. dormancy (hard viability-state block).
#: See simulation.py::_run_interactions for where each is produced.
_DISTRESS_WITHHOLD_REASONS = ("distress", "partner_distress")
_DORMANCY_WITHHOLD_REASONS = ("ineligible_dormant", "partner_ineligible_dormant")


def compute_step_metrics(
    agents: list[Agent],
    graph: nx.Graph,
    event_log: EventLog,
    step: int,
    pool: EnvironmentResourcePool | None = None,
    potential_extraction_demand: float | None = None,
    realized_extraction: float | None = None,
    realized_regeneration: float | None = None,
    config: SimulationConfig | None = None,
    interaction_edge_count: int | None = None,
) -> dict:
    """Compute one row of the metrics time series for the given step.

    ``pool`` is optional (``None`` for a Level-0 compatibility-mode run, in
    which case the environment columns are ``NaN``).

    ``potential_extraction_demand``/``realized_extraction``/
    ``realized_regeneration`` (Level 0.2, Work Package D) and ``config``
    (needed to compute ``opportunities_total`` and
    ``max_sustainable_regeneration``) are all optional so existing call
    sites/tests that only care about Level-0/Level-0.1 columns keep working
    unchanged; every new column that depends on one of them is ``NaN``
    when it is omitted, never silently 0.0 or a wrong value.

    ``interaction_edge_count`` (Level 0.2, Work Package A) is the number of
    edges the interaction loop actually iterated over *this step*
    (``simulation.py::_run_interactions``'s local ``edges`` list length) —
    deliberately **not** the same as ``graph.number_of_edges()`` at the
    time this function runs, since a scheduled rewiring/relationship-
    dynamics round can change the edge count later in the same step,
    after opportunities were already created from the pre-rewiring edge
    set. Falls back to ``graph.number_of_edges()`` (approximate — only
    exact on steps with no rewiring round) if omitted, so existing callers
    that don't pass it still get a value rather than an unconditional NaN.
    """
    living = [a for a in agents if a.alive]

    step_interactions = [e for e in event_log.interactions if e.step == step]
    n_actions = 2 * len(step_interactions)  # each interaction has two actors
    n_cooperate = sum(
        (e.action_a == COOPERATE) + (e.action_b == COOPERATE) for e in step_interactions
    )
    n_defect = n_actions - n_cooperate
    cooperation_rate = n_cooperate / n_actions if n_actions else float("nan")

    step_punishments = [e for e in event_log.punishments if e.step == step]
    punishment_frequency = (
        len(step_punishments) / len(step_interactions) if step_interactions else 0.0
    )
    erroneous_punishments = [e for e in step_punishments if e.erroneous]
    erroneous_punishment_rate = (
        len(erroneous_punishments) / len(step_punishments) if step_punishments else 0.0
    )

    # -- enforcement confusion tally, this step only (see module docstring
    # for why this is inlined rather than calling
    # observer/enforcement.py::confusion_counts, which scans the whole log) --
    punished_pairs_step = {(p.punisher, p.target) for p in step_punishments}
    tp = fp = tn = fn = 0
    for e in step_interactions:
        if not e.punishment_available:
            continue
        for actor_action, observer_id, partner_id in (
            (e.action_a, e.agent_b, e.agent_a),
            (e.action_b, e.agent_a, e.agent_b),
        ):
            punished = (observer_id, partner_id) in punished_pairs_step
            if actor_action == DEFECT and punished:
                tp += 1
            elif actor_action == COOPERATE and punished:
                fp += 1
            elif actor_action == COOPERATE and not punished:
                tn += 1
            elif actor_action == DEFECT and not punished:
                fn += 1

    resources = [a.resources for a in living]

    n = graph.number_of_nodes()
    density = nx.density(graph) if n > 1 else 0.0
    try:
        clustering = nx.average_clustering(graph) if n > 2 else 0.0
    except ZeroDivisionError:  # pragma: no cover - defensive
        clustering = 0.0

    agents_by_id = {a.agent_id: a for a in agents}
    degree_stats = degree_distribution_summary(graph)
    age_stats = relationship_age_distribution(agents_by_id, graph, step)
    comp_stats = component_stats(graph)

    policy_diversity = shannon_entropy([a.policy.name for a in living])

    subsistence_this_step = [e for e in event_log.subsistence if e.step == step]
    subsistence_total = subsistence_this_step[0].total_cost if subsistence_this_step else 0.0

    # ---------------------------------------------------------------
    # Level 0.2, Work Package A: participation-opportunity accounting.
    # ---------------------------------------------------------------
    # opportunities_total is defined at the agent-side/edge-repetition
    # level: 2 agent-opportunities per edge per interactions_per_step
    # repetition (one for each endpoint), matching how every outcome below
    # (a completed interaction, or a WithholdEvent) is itself logged
    # per-agent-side exactly once. This makes
    # opportunities_total == completed_agent_opportunities + withhold_total
    # an exact per-step invariant whenever config is supplied — see
    # tests/test_participation.py.
    edge_count = interaction_edge_count if interaction_edge_count is not None else graph.number_of_edges()
    if config is not None:
        opportunities_total = 2.0 * edge_count * config.interactions_per_step
    else:
        opportunities_total = float("nan")

    completed_agent_opportunities = float(n_actions)  # 2 per completed interaction

    step_withholds = [e for e in event_log.withholds if e.step == step]
    withhold_reason_counts = Counter(e.reason for e in step_withholds)
    refused_distress_count = withhold_reason_counts.get("distress", 0)
    prevented_by_partner_distress_count = withhold_reason_counts.get("partner_distress", 0)
    prevented_by_own_dormancy_count = withhold_reason_counts.get("ineligible_dormant", 0)
    prevented_by_partner_dormancy_count = withhold_reason_counts.get("partner_ineligible_dormant", 0)
    distress_withdrawal_count = sum(withhold_reason_counts.get(r, 0) for r in _DISTRESS_WITHHOLD_REASONS)
    dormancy_block_count = sum(withhold_reason_counts.get(r, 0) for r in _DORMANCY_WITHHOLD_REASONS)
    withhold_total_this_step = len(step_withholds)

    row = {
        "step": step,
        "population_size": len(living),
        "cooperation_rate": cooperation_rate,
        "defection_rate": 1 - cooperation_rate if not math.isnan(cooperation_rate) else float("nan"),
        # Explicit compatibility alias: identical value to "cooperation_rate"
        # above (conditional on a realized interaction — i.e. P(C |
        # interaction)). Kept as a *second* column, never a rename, so
        # existing consumers of "cooperation_rate" are unaffected while new
        # analysis code can refer to the unambiguous name.
        "cooperation_rate_conditional_on_interaction": cooperation_rate,
        "defection_rate_conditional_on_interaction": (
            n_defect / n_actions if n_actions else float("nan")
        ),
        "punishment_frequency": punishment_frequency,
        "erroneous_punishment_rate": erroneous_punishment_rate,
        "punishment_tp": tp,
        "punishment_fp": fp,
        "punishment_tn": tn,
        "punishment_fn": fn,
        "mean_resources": float(np.mean(resources)) if resources else 0.0,
        "resource_gini": gini(resources),
        # Density/mean-degree/relationship-count are retained for
        # continuity with Level 0, but per the milestone brief they are
        # NOT independent evidence of network activity by themselves —
        # see the component/isolation/age/turnover columns below.
        "network_density": density,
        "network_clustering": clustering,
        "mean_degree": degree_stats["degree_mean"],
        "degree_std": degree_stats["degree_std"],
        "relationship_count": graph.number_of_edges(),
        "mean_relationship_age": age_stats["age_mean"],
        "relationship_age_std": age_stats["age_std"],
        "isolated_agent_count": isolated_agent_count(graph),
        "component_count": comp_stats["component_count"],
        "largest_component_share": comp_stats["largest_component_share"],
        "policy_assortativity": policy_assortativity(graph, agents),
        "policy_diversity_bits": policy_diversity,
        # Legacy (Level-0 compatibility-mode) event counts.
        "exit_count": sum(1 for e in event_log.exits if e.step == step),
        "rewire_count": sum(1 for e in event_log.rewires if e.step == step and e.new_partner is not None),
        # Level-0.1 relationship-dynamics event counts (0 in compat mode).
        "edges_added_count": sum(1 for e in event_log.edges_added if e.step == step),
        "edges_removed_count": sum(1 for e in event_log.edges_removed if e.step == step),
        "failed_exit_count": sum(1 for e in event_log.failed_exits if e.step == step),
        "proposal_accepted_count": sum(1 for e in event_log.connection_proposals if e.step == step and e.accepted),
        "proposal_rejected_count": sum(
            1 for e in event_log.connection_proposals if e.step == step and not e.accepted and e.reason == "rejected"
        ),
        "proposal_no_candidate_count": sum(
            1 for e in event_log.connection_proposals if e.step == step and e.reason == "no_candidate"
        ),
        "withhold_count": sum(1 for e in event_log.withholds if e.step == step),
        "subsistence_total": subsistence_total,
        "imitation_count": sum(1 for e in event_log.imitations if e.step == step),
        "mutation_count": sum(1 for e in event_log.mutations if e.step == step),
        "environment_resources": pool.resources if pool is not None else float("nan"),
        "environment_fraction_of_capacity": pool.fraction_of_capacity if pool is not None else float("nan"),

        # -----------------------------------------------------------
        # Level 0.2, Work Package A: participation-opportunity counts
        # and conditional/unconditional cooperation probabilities.
        # -----------------------------------------------------------
        "opportunities_total": opportunities_total,
        "completed_agent_opportunities": completed_agent_opportunities,
        "completed_interactions": float(len(step_interactions)),
        "refused_distress_count": float(refused_distress_count),
        "prevented_by_partner_distress_count": float(prevented_by_partner_distress_count),
        "prevented_by_own_dormancy_count": float(prevented_by_own_dormancy_count),
        "prevented_by_partner_dormancy_count": float(prevented_by_partner_dormancy_count),
        "distress_withdrawal_count": float(distress_withdrawal_count),
        "dormancy_block_count": float(dormancy_block_count),
        "withhold_total_this_step": float(withhold_total_this_step),
        # P(interaction | opportunity): fraction of agent-opportunities
        # this step that resulted in a realized (completed) interaction.
        "p_interaction_given_opportunity": _safe_ratio(completed_agent_opportunities, opportunities_total),
        # P(C | interaction) — identical to cooperation_rate; exported
        # again under the milestone's requested name for discoverability.
        "p_cooperate_given_interaction": cooperation_rate,
        # P(D | interaction)
        "p_defect_given_interaction": (n_defect / n_actions if n_actions else float("nan")),
        # P(C ∩ interaction | opportunity): unconditional realized-
        # cooperation rate per opportunity (this is the "is near-unity
        # cooperation an artifact of a shrinking participating population"
        # diagnostic the milestone's scientific question 3 asks for — this
        # column falls well below 1.0 exactly when selective participation
        # is inflating the conditional cooperation_rate column above).
        "p_cooperate_and_interaction_given_opportunity": _safe_ratio(float(n_cooperate), opportunities_total),
        # P(D ∩ interaction | opportunity)
        "p_defect_and_interaction_given_opportunity": _safe_ratio(float(n_defect), opportunities_total),
        # P(distress withdrawal | opportunity)
        "p_distress_withdrawal_given_opportunity": _safe_ratio(float(distress_withdrawal_count), opportunities_total),
        # P(dormancy block | opportunity) — analogous column for the
        # viability-state hard block (Work Package B), reported alongside
        # for completeness even though only the distress-withdrawal one
        # was explicitly named in the brief.
        "p_dormancy_block_given_opportunity": _safe_ratio(float(dormancy_block_count), opportunities_total),

        # -----------------------------------------------------------
        # Level 0.2, Work Package B: viability-state population
        # accounting (structural snapshot, taken *after* this step's
        # _viability_round — see simulation.py::run). All four states
        # partition the living population exactly; "nonviable" never
        # appears here because a nonviable agent is replaced (or would
        # remain, in a hypothetical mode without replacement) within the
        # same step's _viability_round call, before this snapshot is
        # taken. Always {active: len(living), rest: 0} when
        # viability_mode == "none" (or ecology disabled).
        # -----------------------------------------------------------
        "active_population": float(sum(1 for a in living if a.viability_state == "active")),
        "distressed_population": float(sum(1 for a in living if a.viability_state == "distressed")),
        "dormant_population": float(sum(1 for a in living if a.viability_state == "dormant")),
        "viability_transition_count": float(sum(1 for e in event_log.viability_transitions if e.step == step)),
        "nonviable_this_step_count": float(
            sum(1 for e in event_log.viability_transitions if e.step == step and e.to_state == "nonviable")
        ),
        "removal_count": float(sum(1 for e in event_log.replacements if e.step == step)),

        # -----------------------------------------------------------
        # Level 0.2, Work Package D: ecological supply/demand raw
        # ingredients. Numerator and denominator of any downstream ratio
        # (e.g. the B_t balance indicator built in
        # observer/ecological_balance.py) are exported here separately,
        # never pre-combined, per the milestone brief. NaN throughout when
        # ecology is disabled (pool is None) or the step-level accumulators
        # were not supplied by the caller — these quantities are only
        # meaningful relative to a resource pool.
        # -----------------------------------------------------------
        "potential_extraction_demand": (
            float(potential_extraction_demand) if pool is not None and potential_extraction_demand is not None else float("nan")
        ),
        "realized_extraction": (
            float(realized_extraction) if pool is not None and realized_extraction is not None else float("nan")
        ),
        "unmet_extraction_demand": (
            max(float(potential_extraction_demand) - float(realized_extraction), 0.0)
            if pool is not None and potential_extraction_demand is not None and realized_extraction is not None
            else float("nan")
        ),
        "realized_regeneration": (
            float(realized_regeneration) if pool is not None and realized_regeneration is not None else float("nan")
        ),
        # Maximum sustainable per-step throughput of the logistic pool,
        # r*K/4, achieved at R=K/2 (see environment/resource_pool.py's
        # module docstring) — a structural property of the configured
        # ecological parameters, not a per-step measurement.
        "max_sustainable_regeneration": (
            (config.environment_regen_rate * config.environment_capacity / 4.0)
            if pool is not None and config is not None
            else float("nan")
        ),
        "pool_net_change": (
            float(realized_regeneration) - float(realized_extraction)
            if pool is not None and realized_regeneration is not None and realized_extraction is not None
            else float("nan")
        ),
        "subsistence_demand": subsistence_total if pool is not None else float("nan"),
    }
    return row


def policy_distribution(agents: list[Agent]) -> dict:
    """Final-state count of each policy name among living agents."""
    return dict(Counter(a.policy.name for a in agents if a.alive))
