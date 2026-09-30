"""Local ecological patches (Level 0.3, Work Package A).

Level 0.1/0.2's ``EnvironmentResourcePool`` (``environment/resource_pool.py``)
is a single, well-mixed, population-wide resource. This module adds an
*optional*, spatially-disaggregated alternative: a fixed collection of
independent ``ResourcePatch`` objects, each with its own stock, capacity,
regeneration rate, and exact accounting ledger. It does not replace or
modify the single-pool code path — ``config.ecology_topology ==
"global_pool"`` (the default) never touches this module at all; that is
what makes it an exact Level-0.2-compatible no-op. See
``dev_mem/status_update.md``'s Level-0.3 entry for the design rationale.

**Patch membership never changes after initialization.** This module
provides no migration mechanism. An agent's ``patch_id`` (assigned once,
by :func:`build_patch_system`, before the run starts) is fixed for the
agent's entire lifetime in the population slot. This is a deliberate
scope decision, stated explicitly per the milestone brief's instruction
not to silently conflate social network rewiring (which *does* continue
to change, via ``network/dynamics.py``) with ecological migration (which
does not exist in this model).

Two neutral assignment rules are provided, neither of which inspects an
agent's policy, resources, or any other trait that could bias assignment
toward "expected policy success":

* ``"random_assignment"`` — each agent is assigned to a uniformly random
  patch index, independent of network structure.
* ``"network_neighborhood"`` — a multi-source breadth-first partition:
  ``n_patches`` seed nodes are drawn uniformly at random (without
  replacement) from the *social* interaction graph, then every other
  node is assigned to the patch of whichever seed it is graph-closest to
  (BFS distance; ties broken by random draw order, not by any agent
  trait). This ties initial patch membership to initial network
  topology (so network neighbors tend to share a patch) without ever
  looking at what any agent *does*. Any node unreachable from every seed
  (a disconnected component) is assigned uniformly at random among the
  patches, so every agent always ends up with exactly one patch even for
  a disconnected initial graph.

Patch quality (an optional local productivity multiplier on regeneration
rate) is drawn once per patch, independently of assignment, from
``Normal(1.0, patch_quality_std)`` clipped to a small positive floor —
``patch_quality_std=0.0`` (the default) makes every patch's quality
exactly ``1.0``, a neutral no-op.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import networkx as nx
import numpy as np

VALID_ECOLOGY_TOPOLOGIES = ("global_pool", "patches")
VALID_PATCH_ASSIGNMENT_MODES = ("network_neighborhood", "random_assignment")
VALID_ECOLOGICAL_ALLOCATION_RULES = ("proportional", "sequential_random")


def allocate_extraction(
    available: float,
    requested: dict[int, float],
    rule: str,
    rng: np.random.Generator | None = None,
) -> dict[int, float]:
    """Pure allocation function: given ``available`` stock and a mapping of
    agent_id -> non-negative requested amount, return agent_id -> actual
    granted amount, honoring ``available`` as a hard cap on the *sum* of
    grants. Never mutates any patch — this is the function both
    :meth:`ResourcePatch.request_extraction` (the mutating, "endogenous
    feedback" path) and the Work-Package-F "no environmental effect"
    counterfactual (which calls this directly against a patch's *current*
    stock without applying the result) call, so the two conditions are
    guaranteed to use the exact same allocation arithmetic.

    ``rule="proportional"``: if total requested exceeds ``available``,
    every agent's grant is scaled down by the same factor
    ``available / total_requested`` (order-independent, deterministic
    given the requests, consumes no RNG draws).

    ``rule="sequential_random"``: agents are processed in a uniformly
    random order (consuming RNG draws — the one part of this function
    that does), each granted its full request out of whatever remains,
    first-come-first-served. Requires ``rng``.
    """
    requested = {k: max(0.0, float(v)) for k, v in requested.items()}
    total_requested = sum(requested.values())
    available = max(0.0, float(available))
    if total_requested <= 0:
        return {k: 0.0 for k in requested}
    if total_requested <= available:
        return dict(requested)

    if rule == "proportional":
        scale = available / total_requested
        return {k: v * scale for k, v in requested.items()}

    if rule == "sequential_random":
        if rng is None:
            raise ValueError("rule='sequential_random' requires an rng")
        order = list(requested.keys())
        rng.shuffle(order)  # in-place shuffle, consumes RNG draws
        actual: dict[int, float] = {}
        remaining = available
        for agent_id in order:
            grant = min(requested[agent_id], remaining)
            actual[agent_id] = grant
            remaining -= grant
        return actual

    raise ValueError(f"unknown allocation rule: {rule!r}")


@dataclass
class ResourcePatch:
    """One local, bounded, logistically-regenerating resource patch.

    Guarantees ``0 <= resources <= capacity`` after every mutating call
    (``extract``, ``request_extraction``, ``apply_maintenance``,
    ``regenerate``) — checked directly by
    ``tests/test_patches.py::test_patch_bounds_hold_after_every_operation``.
    """

    patch_id: int
    capacity: float
    regen_rate: float
    quality: float = 1.0
    resources: float = 0.0
    members: frozenset = field(default_factory=frozenset)

    #: Exact accounting ledger (Work Package A). Never read by any
    #: decision-making code — diagnostics only.
    cumulative_extraction: float = 0.0
    cumulative_game_extraction: float = 0.0
    cumulative_ecological_extraction: float = 0.0
    cumulative_maintenance_invested: float = 0.0
    cumulative_maintenance_effective: float = 0.0
    cumulative_regeneration: float = 0.0
    cumulative_unmet_extraction_demand: float = 0.0

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("capacity must be > 0")
        if not (0.0 <= self.regen_rate <= 2.0):
            raise ValueError("regen_rate must be in [0, 2]")
        if self.quality <= 0:
            raise ValueError("quality must be > 0")
        if not (0.0 <= self.resources <= self.capacity):
            raise ValueError("resources must be in [0, capacity]")

    # -- incremental, per-interaction extraction (mirrors
    # EnvironmentResourcePool.extract exactly; used for social-game
    # payoffs, one call per interaction, order-dependent like the
    # single-pool model) --------------------------------------------------
    def extract(self, amount: float, category: str = "game") -> float:
        actual = min(max(amount, 0.0), self.resources)
        self.resources -= actual
        self.cumulative_extraction += actual
        if category == "game":
            self.cumulative_game_extraction += actual
        else:
            self.cumulative_ecological_extraction += actual
        return actual

    # -- batch, simultaneous-request extraction (used once per step for
    # the ecological harvest round; requests from every patch member are
    # rationed together against the patch's current stock) ---------------
    def request_extraction(
        self, requested: dict[int, float], rule: str, rng: np.random.Generator | None = None
    ) -> dict[int, float]:
        actual = allocate_extraction(self.resources, requested, rule, rng)
        total_requested = sum(max(0.0, v) for v in requested.values())
        total_actual = sum(actual.values())
        self.resources = max(0.0, self.resources - total_actual)
        self.cumulative_extraction += total_actual
        self.cumulative_ecological_extraction += total_actual
        self.cumulative_unmet_extraction_demand += max(total_requested - total_actual, 0.0)
        return actual

    def apply_maintenance(self, investment: dict[int, float], efficiency: float) -> float:
        """``investment``: agent_id -> non-negative amount invested (paid
        by the agent regardless of effect — see simulation.py). Returns
        the amount *actually added* to the patch, which may be less than
        ``efficiency * total_invested`` if the patch is already near
        capacity (never negative, never pushes ``resources`` above
        ``capacity`` — see module-level bound guarantee)."""
        total_invested = sum(max(0.0, v) for v in investment.values())
        effective = efficiency * total_invested
        new_resources = min(self.capacity, self.resources + effective)
        actually_added = new_resources - self.resources
        self.resources = new_resources
        self.cumulative_maintenance_invested += total_invested
        self.cumulative_maintenance_effective += actually_added
        return actually_added

    def regenerate(self) -> float:
        r = self.regen_rate * self.quality
        growth = r * self.resources * (1.0 - self.resources / self.capacity)
        new_resources = min(self.capacity, max(0.0, self.resources + growth))
        added = new_resources - self.resources
        self.resources = new_resources
        self.cumulative_regeneration += added
        return added

    @property
    def fraction_of_capacity(self) -> float:
        return self.resources / self.capacity if self.capacity else 0.0


@dataclass
class PatchSystem:
    patches: dict[int, ResourcePatch]
    #: agent_id -> patch_id, fixed for the whole run (see module docstring).
    agent_patch: dict[int, int]

    def patch_of(self, agent_id: int) -> ResourcePatch:
        return self.patches[self.agent_patch[agent_id]]

    @property
    def total_resources(self) -> float:
        return sum(p.resources for p in self.patches.values())

    @property
    def total_capacity(self) -> float:
        return sum(p.capacity for p in self.patches.values())

    @property
    def aggregate_fraction_of_capacity(self) -> float:
        cap = self.total_capacity
        return self.total_resources / cap if cap else 0.0


def _assign_random(agent_ids: list[int], n_patches: int, rng: np.random.Generator) -> dict[int, int]:
    draws = rng.integers(0, n_patches, size=len(agent_ids))
    return {aid: int(p) for aid, p in zip(agent_ids, draws)}


def _assign_network_neighborhood(
    agent_ids: list[int], n_patches: int, graph: nx.Graph, rng: np.random.Generator
) -> dict[int, int]:
    """Multi-source BFS partition (see module docstring). Deterministic
    given ``rng`` and ``graph``; never inspects agent policy/resources."""
    n = len(agent_ids)
    if n_patches >= n:
        # More patches than agents: every agent gets its own patch index
        # (degenerate but well-defined), remaining patch indices simply
        # end up with zero members.
        order = [int(x) for x in rng.permutation(agent_ids)]
        return {aid: i % n_patches for i, aid in enumerate(order)}

    seeds = [int(x) for x in rng.choice(np.array(agent_ids), size=n_patches, replace=False)]
    assignment: dict[int, int] = {}
    frontier: deque = deque()
    for patch_idx, seed in enumerate(seeds):
        assignment[seed] = patch_idx
        frontier.append(seed)

    # Round-robin BFS expansion so no single patch's seed dominates purely
    # by expansion order.
    frontiers = [deque([s]) for s in seeds]
    visited = set(seeds)
    progressed = True
    while progressed:
        progressed = False
        for patch_idx, fq in enumerate(frontiers):
            if not fq:
                continue
            node = fq.popleft()
            neighbors = [x for x in graph.neighbors(node) if x not in visited]
            neighbors.sort()  # deterministic order before any rng use
            for nb in neighbors:
                if nb in visited:
                    continue
                visited.add(nb)
                assignment[nb] = patch_idx
                fq.append(nb)
                progressed = True

    # Any node unreachable from every seed (disconnected component):
    # assign uniformly at random among the patches.
    unreached = [aid for aid in agent_ids if aid not in assignment]
    if unreached:
        draws = rng.integers(0, n_patches, size=len(unreached))
        for aid, p in zip(unreached, draws):
            assignment[aid] = int(p)

    return assignment


def build_patch_system(
    agent_ids: list[int],
    graph: nx.Graph,
    n_patches: int,
    capacity: float,
    regen_rate: float,
    initial_fraction: float,
    assignment_mode: str,
    quality_std: float,
    rng: np.random.Generator,
) -> PatchSystem:
    """Construct the initial patch system: draw each patch's quality
    multiplier, assign every agent to exactly one patch (neutral rule,
    never migrates — see module docstring), and initialize every patch's
    stock to ``capacity * initial_fraction`` (same convention as
    ``EnvironmentResourcePool``)."""
    if n_patches < 1:
        raise ValueError("n_patches must be >= 1")
    if assignment_mode not in VALID_PATCH_ASSIGNMENT_MODES:
        raise ValueError(f"assignment_mode must be one of {VALID_PATCH_ASSIGNMENT_MODES}, got {assignment_mode!r}")

    if quality_std > 0:
        qualities = np.clip(rng.normal(1.0, quality_std, size=n_patches), 0.1, None)
    else:
        qualities = np.ones(n_patches)

    patches = {
        i: ResourcePatch(
            patch_id=i,
            capacity=capacity,
            regen_rate=regen_rate,
            quality=float(qualities[i]),
            resources=capacity * initial_fraction,
        )
        for i in range(n_patches)
    }

    if assignment_mode == "random_assignment":
        agent_patch = _assign_random(agent_ids, n_patches, rng)
    else:
        agent_patch = _assign_network_neighborhood(agent_ids, n_patches, graph, rng)

    for aid, pid in agent_patch.items():
        patches[pid].members = patches[pid].members | {aid}

    return PatchSystem(patches=patches, agent_patch=agent_patch)
