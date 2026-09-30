"""Policy-evolution observability (Level 0.1, Work Package D).

Records distributional and lineage information about the population's
behavioural policies at configurable intervals. Everything here reads
agent state (``policy.name``, ``policy_lineage_id``, ``resources``) without
mutating it, and none of it feeds back into imitation, mutation, or
payoffs — purely descriptive, downstream bookkeeping.
"""

from __future__ import annotations

from collections import Counter

import numpy as np

from abm_governance.observer.metrics import policy_distribution, shannon_entropy


def lineage_distribution(agents) -> dict[int, int]:
    """Count of living agents currently carrying each
    ``policy_lineage_id``."""
    return dict(Counter(a.policy_lineage_id for a in agents if a.alive))


def mean_payoff_by_policy(agents) -> dict[str, float]:
    """Mean current ``resources`` (the same fitness proxy imitation uses),
    grouped by current policy name. Not a claim about *causal* payoff
    superiority — agents grouped under the same policy name may have
    joined it (via imitation) at very different times."""
    groups: dict[str, list[float]] = {}
    for a in agents:
        if not a.alive:
            continue
        groups.setdefault(a.policy.name, []).append(a.resources)
    return {name: float(np.mean(values)) for name, values in groups.items()}


def policy_snapshot(agents, step: int) -> dict:
    """One point-in-time record of the population's policy composition,
    suitable for periodic recording (e.g. every ``imitation_period``
    steps, alongside imitation/mutation rounds — see
    ``simulation.py::_adaptation_round``)."""
    living = [a for a in agents if a.alive]
    lineages = lineage_distribution(agents)
    return {
        "step": step,
        "policy_counts": policy_distribution(agents),
        "policy_entropy_bits": shannon_entropy([a.policy.name for a in living]),
        "lineage_counts": lineages,
        "n_distinct_lineages": len(lineages),
        "mean_payoff_by_policy": mean_payoff_by_policy(agents),
    }
