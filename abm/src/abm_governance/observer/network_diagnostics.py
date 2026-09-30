"""Network structure diagnostics (Level 0.1, Work Package B).

The milestone brief is explicit that density, mean degree, and relationship
count are "not independent evidence" — they can all stay constant while the
underlying set of *which* edges exist changes completely (or, as in the
Level-0 baseline, while nothing changes at all). This module adds the
diagnostics needed to tell those cases apart: component structure,
isolation, degree/age distributions, turnover rate, and an assortativity
check. All functions are pure, read-only functions of a graph/agents/event
log snapshot.
"""

from __future__ import annotations

import networkx as nx
import numpy as np

from abm_governance.core.events import EventLog


def isolated_agent_count(graph: nx.Graph) -> int:
    return sum(1 for _, d in graph.degree() if d == 0)


def component_stats(graph: nx.Graph) -> dict:
    n = graph.number_of_nodes()
    if n == 0:
        return {"component_count": 0, "largest_component_share": float("nan")}
    sizes = [len(c) for c in nx.connected_components(graph)]
    return {
        "component_count": len(sizes),
        "largest_component_share": max(sizes) / n,
    }


def degree_distribution_summary(graph: nx.Graph) -> dict:
    degrees = [d for _, d in graph.degree()]
    if not degrees:
        return {"degree_mean": 0.0, "degree_std": 0.0, "degree_min": 0, "degree_max": 0}
    arr = np.asarray(degrees, dtype=float)
    return {
        "degree_mean": float(arr.mean()),
        "degree_std": float(arr.std()),
        "degree_min": int(arr.min()),
        "degree_max": int(arr.max()),
    }


def relationship_age_distribution(agents_by_id: dict, graph: nx.Graph, step: int) -> dict:
    ages = []
    for u, v in graph.edges():
        su = agents_by_id[u].relationship_started_at.get(v)
        sv = agents_by_id[v].relationship_started_at.get(u)
        known = [x for x in (su, sv) if x is not None]
        if known:
            ages.append(step - min(known))
    if not ages:
        return {"age_mean": 0.0, "age_std": 0.0, "age_min": 0, "age_max": 0}
    arr = np.asarray(ages, dtype=float)
    return {
        "age_mean": float(arr.mean()),
        "age_std": float(arr.std()),
        "age_min": int(arr.min()),
        "age_max": int(arr.max()),
    }


def relationship_turnover_rate(event_log: EventLog, start_step: int, end_step: int) -> float:
    """(edges added + edges removed) per step over ``[start_step, end_step)``.

    Counts *both* event families: the Work-Package-B family
    (``edges_added``/``edges_removed``) and, for compatibility-mode runs,
    the legacy family (``rewires`` with a non-``None`` partner counts as an
    addition; ``exits`` counts as a removal).
    """
    n_added = sum(1 for e in event_log.edges_added if start_step <= e.step < end_step)
    n_added += sum(
        1 for e in event_log.rewires if e.new_partner is not None and start_step <= e.step < end_step
    )
    n_removed = sum(1 for e in event_log.edges_removed if start_step <= e.step < end_step)
    n_removed += sum(1 for e in event_log.exits if start_step <= e.step < end_step)
    duration = max(1, end_step - start_step)
    return (n_added + n_removed) / duration


def policy_assortativity(graph: nx.Graph, agents) -> float:
    """Assortativity coefficient of the network by policy name (a
    categorical node attribute — never a governance label). Returns
    ``NaN`` when undefined (fewer than 2 edges, or only one policy present
    in the network, both of which make the coefficient mathematically
    undefined rather than meaningfully zero).

    Level 1.1b, Work Package A cross-process-stability fix: calling
    ``nx.attribute_assortativity_coefficient`` directly leaves the mixing
    matrix's category ordering to networkx's own "arbitrary ordering" (an
    unordered ``set`` of the categorical attribute's *string* values) —
    since Python randomizes string hashing per process by default, the
    category order (and therefore the exact floating-point summation
    order inside the trace/sum-of-squares computation) silently varies
    from run to run, producing ULP-level, process-dependent differences
    in an otherwise fully-deterministic pipeline (discovered via this
    milestone's cross-process-stability test; see
    tests/test_level11b_rng_substreams.py and
    docs/level1.1b_rng_design.md). Passing an explicit ``mapping`` built
    from a *sorted* category list fixes the ordering, so this function is
    now genuinely process-independent — the underlying Newman (2003)
    formula (via ``networkx``'s own ``attribute_ac``) is untouched, only
    the row/column order of the intermediate matrix is pinned down."""
    if graph.number_of_edges() < 2:
        return float("nan")
    policy_by_id = {a.agent_id: a.policy.name for a in agents}
    distinct = sorted({policy_by_id[u] for u in graph.nodes() if graph.degree(u) > 0})
    if len(distinct) < 2:
        return float("nan")
    g2 = graph.copy()
    nx.set_node_attributes(g2, policy_by_id, "policy_name")
    mapping = {name: i for i, name in enumerate(distinct)}
    try:
        from networkx.algorithms.assortativity.correlation import attribute_ac

        matrix = nx.attribute_mixing_matrix(g2, "policy_name", mapping=mapping)
        value = attribute_ac(matrix)
    except (ZeroDivisionError, ValueError):
        return float("nan")
    return float(value) if value == value else float("nan")  # NaN-safe passthrough
