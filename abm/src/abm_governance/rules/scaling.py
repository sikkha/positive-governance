"""Level 1.2, Work Package F: institutional scaling.

**Gradual extension of reach without a predefined higher-order
government.** No new topology is introduced — a jurisdiction is simply a
connected component of the existing Level 1.1 coordination-link graph
(``rules/coordination.py``, the same graph Work Packages B/C already
reuse). Each additional patch joins one link acceptance at a time
(Level 1.1's own bilateral link-acceptance mechanic — nothing here adds
a "join a federation" decision distinct from "accept a coordination
link"), so "each additional patch independently accepts" is inherited
for free rather than re-implemented.

**Never a state/federation/democracy/empire/authoritarian system in
generative code.** This module tracks and reports jurisdictions using
only neutral quantities: ``jurisdiction_patch_count``, and (via
``rules/delegation.py``'s own ``jurisdiction_size_by_patch`` parameter)
a genuine "admin workload increases with scale" behavioral effect —
never a name, never a type label.

**Disclosed reduction**: "information may degrade with distance" is not
separately wired this milestone — Work Package B/C's observation and
transmission are already one-hop (direct-link) only, so there is no
multi-hop distance for information to degrade *across* yet; a
jurisdiction's *size* still genuinely raises administrative cost
(below), which is the one scaling effect this milestone implements
behaviorally. "Authority may concentrate/distribute endogenously" is
reported (``authority_concentration_by_jurisdiction``) but, consistent
with Work Package A's own classification of ``authority_concentration``
as descriptive-only, is not fed back into any decision function."""

from __future__ import annotations

from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import CoordinationScaleChangeEvent, EventLog
from abm_governance.rules.coordination import CoordinationLink


def compute_coordination_components(link_registry: dict[int, CoordinationLink]) -> dict[int, frozenset[int]]:
    """Connected components of the active coordination-link graph, keyed
    by each component's lowest patch id (a stable, deterministic
    identifier across steps as long as that patch remains in the
    component). Patches with no active link at all are simply absent
    from the returned mapping (a singleton is not a "scaled"
    jurisdiction)."""
    adjacency: dict[int, set[int]] = {}
    for link in link_registry.values():
        if not link.active:
            continue
        adjacency.setdefault(link.patch_id_a, set()).add(link.patch_id_b)
        adjacency.setdefault(link.patch_id_b, set()).add(link.patch_id_a)

    visited: set[int] = set()
    components: dict[int, frozenset[int]] = {}
    for start in adjacency:
        if start in visited:
            continue
        stack = [start]
        comp: set[int] = set()
        while stack:
            node = stack.pop()
            if node in comp:
                continue
            comp.add(node)
            for neighbor in adjacency.get(node, ()):
                if neighbor not in comp:
                    stack.append(neighbor)
        visited |= comp
        components[min(comp)] = frozenset(comp)
    return components


def jurisdiction_size_by_patch(components: dict[int, frozenset[int]]) -> dict[int, int]:
    """patch_id -> size of the jurisdiction (coordination-network
    connected component) it currently belongs to — 1 implicitly for any
    patch not present in ``components`` (a singleton), via
    ``.get(pid, 1)`` at every call site; never materialized as an
    explicit ``1`` entry here."""
    sizes: dict[int, int] = {}
    for comp in components.values():
        for pid in comp:
            sizes[pid] = len(comp)
    return sizes


def institutional_scaling_round(
    step: int,
    link_registry: dict[int, CoordinationLink],
    config: SimulationConfig,
    event_log: EventLog,
    prior_components: dict[int, frozenset[int]],
) -> dict[int, frozenset[int]]:
    """Once per step: recompute jurisdictions and emit
    ``CoordinationScaleChangeEvent`` for every jurisdiction that grew,
    shrank, merged, fragmented, or dissolved since ``prior_components``
    (the previous call's return value — callers own this state exactly
    like every other per-simulation registry in this codebase). Returns
    the new component mapping for the caller to pass in next time. A
    strict no-op (returns ``prior_components`` unchanged, no events)
    when ``config.institutional_scaling_enabled`` is False.

    **Best-effort classification**: a single step's before/after diff is
    matched by patch-set overlap, which correctly handles the common
    cases (grow, shrink, one clean merge, one clean split, dissolve) but
    is not guaranteed exhaustively exact for a pathological simultaneous
    multi-way split-and-merge within one step — disclosed here rather
    than silently assumed complete."""
    if not config.institutional_scaling_enabled:
        return prior_components

    current = compute_coordination_components(link_registry)
    prior_sets = {root: comp for root, comp in prior_components.items() if len(comp) >= 2}

    matched_prior_roots: set[int] = set()
    for root, comp in current.items():
        overlapping = [(r, c) for r, c in prior_sets.items() if c & comp]
        if not overlapping:
            change = "grew"
        elif len(overlapping) > 1:
            change = "merged"
            matched_prior_roots.update(r for r, _ in overlapping)
        else:
            prior_root, prior_comp = overlapping[0]
            matched_prior_roots.add(prior_root)
            if comp == prior_comp:
                continue
            change = "grew" if len(comp) > len(prior_comp) else "shrank"
        event_log.add(
            CoordinationScaleChangeEvent(step=step, component_root_patch_id=root, jurisdiction_patch_count=len(comp), change=change)
        )

    for root, comp in prior_sets.items():
        if root in matched_prior_roots:
            continue
        still_present = any(comp & c for c in current.values())
        change = "fragmented" if still_present else "dissolved"
        event_log.add(
            CoordinationScaleChangeEvent(step=step, component_root_patch_id=root, jurisdiction_patch_count=0, change=change)
        )

    return current
