"""Level 0.3, Work Package E: observer-layer metrics for local ecological
patches and the independent ecological-policy dimension.

Same discipline as every other observer module (``dev_mem/project_vision.md``
§5): every function here is a pure function of a read-only snapshot (a
``PatchSystem``, a list of agents, or an ``EventLog``); nothing here mutates
simulation state or is ever read by any decision function in
``simulation.py``/``agents/``. None of these metrics are, or are derived
from, State Capacity / Rule of Law / Democratic Accountability /
Institutional Constraint, a governance classification, or any of the
dissertation's three governance trajectories — see
``agents/agent.py::FORBIDDEN_ATTRIBUTE_SUBSTRINGS`` and
``tests/test_level03_niche_construction.py``'s structural guard.

Every ratio/rate column uses ``_safe_ratio`` (NaN, never a silently
substituted 0.0, for a zero denominator), and every ratio's raw
numerator/denominator counts are exported as their own columns too —
mirroring ``observer/metrics.py``'s and ``observer/ecological_balance.py``'s
established convention (a milestone brief requirement, applied here for
consistency with the rest of the observer layer).

**On the "4 joint social-ecological action frequencies" (Work Package E).**
Social action is per-*interaction* (cooperate/defect), while ecological
action is per-*step* (one extraction/maintenance decision per agent per
step) — so a joint frequency needs an explicit, documented rule for
collapsing an agent's (possibly several, possibly mixed) interactions in a
step into one social label. This module uses the agent's *majority* action
across its own completed interactions that step (ties broken toward
"defect", the conservative choice — an agent that cooperated in exactly
half its interactions is not unambiguously a cooperator this step); an
agent with zero completed interactions that step contributes to no joint
count (there is no social action to pair). Ecological action is likewise
binarized into exactly the two poles the milestone's central separation
principle names — "extraction-dominant" (``requested_extraction >
requested_maintenance``) vs. "maintenance-dominant" (the complement,
including the tie and the "both requested zero" restraint case, which is
therefore folded into "maintenance-dominant" here) — a documented,
overridable choice, not a claim that ties or restraint are not
independently interesting (they are: see ``requested_extraction ==
0`` -> ``restraint_count`` below, exported completely separately and never
collapsed into the joint-frequency table).
"""

from __future__ import annotations

import math
from collections import Counter

import numpy as np

from abm_governance.core.events import EventLog
from abm_governance.environment.patches import PatchSystem
from abm_governance.interactions.game import COOPERATE, DEFECT
from abm_governance.observer.metrics import gini, shannon_entropy

#: Default patch-occupancy region thresholds (documented, overridable —
#: see ``observer/ecological_balance.py``'s identical convention for the
#: single-pool case, applied here per-patch).
DEFAULT_DEPLETED_OCCUPANCY_THRESHOLD = 0.05
DEFAULT_ABUNDANT_OCCUPANCY_THRESHOLD = 0.8


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else math.nan


# ---------------------------------------------------------------------
# Environmental state: per-patch occupancy distribution and spatial
# inequality.
# ---------------------------------------------------------------------
def patch_occupancy_summary(
    patch_system: PatchSystem | None,
    depleted_threshold: float = DEFAULT_DEPLETED_OCCUPANCY_THRESHOLD,
    abundant_threshold: float = DEFAULT_ABUNDANT_OCCUPANCY_THRESHOLD,
) -> dict:
    """Cross-patch distribution of ``fraction_of_capacity`` this step, plus
    a spatial-inequality measure (Gini coefficient of raw patch stocks —
    the same measure ``observer/metrics.py::gini`` already uses for
    inter-agent resource inequality, reused here for inter-patch
    inequality rather than introducing a second, differently-defined
    index). Returns an all-NaN row (``n_patches=0``) when
    ``patch_system`` is ``None`` (global_pool topology or ecology
    disabled) — never a silently substituted 0.0."""
    if patch_system is None or not patch_system.patches:
        return {
            "n_patches": 0,
            "patch_occupancy_mean": math.nan,
            "patch_occupancy_median": math.nan,
            "patch_occupancy_min": math.nan,
            "patch_occupancy_max": math.nan,
            "patch_occupancy_variance": math.nan,
            "patch_occupancy_spatial_gini": math.nan,
            "n_patches_depleted": math.nan,
            "n_patches_abundant": math.nan,
            "fraction_patches_depleted": math.nan,
            "fraction_patches_abundant": math.nan,
            "aggregate_patch_resources": math.nan,
            "aggregate_patch_capacity": math.nan,
            "aggregate_fraction_of_capacity": math.nan,
        }
    occupancies = np.array([p.fraction_of_capacity for p in patch_system.patches.values()], dtype=float)
    stocks = [p.resources for p in patch_system.patches.values()]
    n = len(occupancies)
    n_depleted = int(np.sum(occupancies <= depleted_threshold))
    n_abundant = int(np.sum(occupancies >= abundant_threshold))
    return {
        "n_patches": n,
        "patch_occupancy_mean": float(np.mean(occupancies)),
        "patch_occupancy_median": float(np.median(occupancies)),
        "patch_occupancy_min": float(np.min(occupancies)),
        "patch_occupancy_max": float(np.max(occupancies)),
        "patch_occupancy_variance": float(np.var(occupancies)),
        "patch_occupancy_spatial_gini": gini(stocks),
        "n_patches_depleted": float(n_depleted),
        "n_patches_abundant": float(n_abundant),
        "fraction_patches_depleted": _safe_ratio(float(n_depleted), float(n)),
        "fraction_patches_abundant": _safe_ratio(float(n_abundant), float(n)),
        "aggregate_patch_resources": float(patch_system.total_resources),
        "aggregate_patch_capacity": float(patch_system.total_capacity),
        "aggregate_fraction_of_capacity": float(patch_system.aggregate_fraction_of_capacity),
    }


# ---------------------------------------------------------------------
# Ecological behaviour: this step's requested/actual extraction and
# maintenance, restraint frequency.
# ---------------------------------------------------------------------
def ecological_step_summary(event_log: EventLog, step: int) -> dict:
    """Aggregate ``EcologicalActionEvent``s for exactly this step. All-NaN
    (``n_ecological_agents=0``) on a step/config with no ecological
    events at all (global_pool topology, or ecology disabled) — the
    columns must never be silently read as "zero activity" when the
    mechanism was never active in the first place."""
    events = [e for e in event_log.ecological_actions if e.step == step]
    if not events:
        return {
            "n_ecological_agents": 0,
            "ecological_requested_extraction_total": math.nan,
            "ecological_actual_extraction_total": math.nan,
            "ecological_extraction_shortfall_total": math.nan,
            "ecological_requested_maintenance_total": math.nan,
            "ecological_maintenance_effective_total": math.nan,
            "ecological_search_cost_total": math.nan,
            "restraint_count": math.nan,
            "restraint_frequency": math.nan,
            "extraction_active_count": math.nan,
            "extraction_active_frequency": math.nan,
            "maintenance_active_count": math.nan,
            "maintenance_active_frequency": math.nan,
        }
    requested_extraction = sum(e.requested_extraction for e in events)
    actual_extraction = sum(e.actual_extraction for e in events)
    requested_maintenance = sum(e.requested_maintenance for e in events)
    maintenance_effective = sum(e.maintenance_effective for e in events)
    search_cost = sum(e.ecological_search_cost for e in events)
    n = len(events)
    restraint_count = sum(1 for e in events if e.requested_extraction == 0.0)
    extraction_active_count = n - restraint_count
    maintenance_active_count = sum(1 for e in events if e.requested_maintenance > 0.0)
    return {
        "n_ecological_agents": n,
        "ecological_requested_extraction_total": requested_extraction,
        "ecological_actual_extraction_total": actual_extraction,
        "ecological_extraction_shortfall_total": max(requested_extraction - actual_extraction, 0.0),
        "ecological_requested_maintenance_total": requested_maintenance,
        "ecological_maintenance_effective_total": maintenance_effective,
        "ecological_search_cost_total": search_cost,
        # "Restraint" (Work Package E's named metric): the agent requested
        # exactly zero extraction this step -- a deliberate non-extraction
        # decision, distinguishable from "wanted to extract but was
        # rationed to zero" (that case is extraction_active with
        # actual_extraction possibly 0, counted separately via the
        # shortfall total above).
        "restraint_count": float(restraint_count),
        "restraint_frequency": _safe_ratio(float(restraint_count), float(n)),
        "extraction_active_count": float(extraction_active_count),
        "extraction_active_frequency": _safe_ratio(float(extraction_active_count), float(n)),
        "maintenance_active_count": float(maintenance_active_count),
        "maintenance_active_frequency": _safe_ratio(float(maintenance_active_count), float(n)),
    }


# ---------------------------------------------------------------------
# Cross-domain: the 4 joint social x ecological action frequencies (see
# module docstring for the exact, documented categorization rule).
# ---------------------------------------------------------------------
_JOINT_LABELS = (
    "cooperate_and_extraction_dominant",
    "cooperate_and_maintenance_dominant",
    "defect_and_extraction_dominant",
    "defect_and_maintenance_dominant",
)


def joint_action_frequencies(event_log: EventLog, step: int) -> dict:
    """The four joint social x ecological action counts/frequencies for
    this step (see module docstring for the exact majority-vote /
    extraction-vs-maintenance-dominant categorization rules). Returned
    counts sum to at most the number of agents with *both* a completed
    interaction and an ecological-action event this step (an agent
    missing either is excluded, not imputed); frequencies are relative to
    that joint-eligible count, exported as its own column so nothing is
    hidden inside the ratios."""
    step_interactions = [e for e in event_log.interactions if e.step == step]
    per_agent_actions: dict[int, list[int]] = {}
    for e in step_interactions:
        per_agent_actions.setdefault(e.agent_a, []).append(e.action_a)
        per_agent_actions.setdefault(e.agent_b, []).append(e.action_b)

    social_label: dict[int, str] = {}
    for agent_id, actions in per_agent_actions.items():
        n_cooperate = sum(1 for a in actions if a == COOPERATE)
        # Majority vote, ties (including the DEFECT sentinel default)
        # broken toward "defect" -- see module docstring.
        social_label[agent_id] = "cooperate" if n_cooperate > len(actions) / 2.0 else "defect"

    eco_events = {e.agent: e for e in event_log.ecological_actions if e.step == step}

    counts = Counter()
    n_joint_eligible = 0
    for agent_id, s_label in social_label.items():
        eco = eco_events.get(agent_id)
        if eco is None:
            continue
        n_joint_eligible += 1
        eco_label = (
            "extraction_dominant" if eco.requested_extraction > eco.requested_maintenance else "maintenance_dominant"
        )
        counts[f"{s_label}_and_{eco_label}"] += 1

    row = {"n_joint_eligible_agents": float(n_joint_eligible)}
    for label in _JOINT_LABELS:
        row[f"{label}_count"] = float(counts.get(label, 0))
        row[f"{label}_frequency"] = _safe_ratio(float(counts.get(label, 0)), float(n_joint_eligible))
    return row


# ---------------------------------------------------------------------
# Ecological-policy diversity / lineage diversity (mirrors
# observer/policy_observability.py's social-policy pattern).
# ---------------------------------------------------------------------
def ecological_lineage_distribution(agents) -> dict[int, int]:
    return dict(Counter(a.ecological_policy_lineage_id for a in agents if a.alive))


def ecological_policy_diversity_bits(agents) -> float:
    """Shannon entropy (bits) of a *discretized* ecological-policy label:
    each of the three continuous traits is binned above/below the living
    population's own current mean (a per-call, data-relative threshold,
    not a fixed magic number), giving up to 2^3 = 8 categories. This is
    one documented, overridable operationalization of "diversity" for a
    continuous trait vector -- not a claim that it is the only one; the
    raw trait values remain fully available (via
    ``ecological_policy_trait_summary`` below) for any other analysis."""
    living = [a for a in agents if a.alive]
    if len(living) < 2:
        return 0.0
    ext = np.array([a.ecological_policy.extraction_propensity for a in living])
    maint = np.array([a.ecological_policy.maintenance_propensity for a in living])
    scar = np.array([a.ecological_policy.scarcity_sensitivity for a in living])
    ext_mean, maint_mean, scar_mean = ext.mean(), maint.mean(), scar.mean()
    labels = [
        f"{int(e > ext_mean)}{int(m > maint_mean)}{int(s > scar_mean)}"
        for e, m, s in zip(ext, maint, scar)
    ]
    return shannon_entropy(labels)


def ecological_policy_trait_summary(agents) -> dict:
    """Raw population-level summary statistics of each ecological-policy
    trait among living agents -- exported unmixed, so no diversity
    analysis is forced through the single discretized entropy number
    above."""
    living = [a for a in agents if a.alive]
    if not living:
        return {
            f"{trait}_{stat}": math.nan
            for trait in ("extraction_propensity", "maintenance_propensity", "scarcity_sensitivity")
            for stat in ("mean", "std")
        }
    out = {}
    for trait in ("extraction_propensity", "maintenance_propensity", "scarcity_sensitivity"):
        values = np.array([getattr(a.ecological_policy, trait) for a in living])
        out[f"{trait}_mean"] = float(values.mean())
        out[f"{trait}_std"] = float(values.std())
    return out


def ecological_policy_snapshot(agents, step: int) -> dict:
    """One point-in-time record of the population's ecological-policy
    composition -- the direct ecological-dimension analog of
    ``observer/policy_observability.py::policy_snapshot``, intended for
    periodic recording alongside it (e.g. from
    ``simulation.py::_adaptation_round``)."""
    lineages = ecological_lineage_distribution(agents)
    row = {
        "step": step,
        "ecological_lineage_counts": lineages,
        "n_distinct_ecological_lineages": len(lineages),
        "ecological_policy_diversity_bits": ecological_policy_diversity_bits(agents),
    }
    row.update(ecological_policy_trait_summary(agents))
    return row
