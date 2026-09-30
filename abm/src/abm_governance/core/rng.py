"""Single source of randomness, plus (Level 1.1b, Work Package A) a
deterministic mechanism-specific substream registry.

Every stochastic draw anywhere in this codebase must pass through a
``numpy.random.Generator`` obtained (directly or via a child/substream)
from :func:`make_rng`/:func:`build_stream_registry`. No module may call the
global ``numpy.random`` functions or the stdlib ``random`` module — that
would make runs non-reproducible in ways that are invisible from the
outside.

Two RNG modes (``SimulationConfig.rng_mode``):

``legacy_single_stream`` (the default — exact Level 1.1 behavior,
preserved byte-for-byte): every mechanism name in :data:`STREAM_REGISTRY`
resolves to the *same* single ``Generator`` object (``make_rng(seed)``),
consumed in the exact call order Level 1.1 always used. This is
deliberately not "a substream registry that happens to collapse to one
stream" — it is the literal pre-existing code path, unchanged, so nothing
about draw order, draw count, or draw values can differ from Level 1.1.

``mechanism_substreams`` (Level 1.1b's own required mode for causal
experiments): each name in :data:`STREAM_REGISTRY` gets its own
independent ``Generator``, spawned once via ``numpy.random.SeedSequence
.spawn()`` from the root seed — deterministic (same seed + same registry
version -> same streams every time, in-process or across processes),
using no process-randomized ``hash()`` anywhere. Because each mechanism
draws from an entirely separate ``Generator`` object, disabling one
mechanism cannot change what any *other* mechanism's stream produces —
there is no shared state for it to perturb. This is the property Level
1.1's matched-seed ablations lacked (see
``docs/level1.1b_rng_design.md``).
"""

from __future__ import annotations

import numpy as np

#: Level 1.1b, Work Package A: the fixed, documented mechanism-stream
#: registry. Order matters for ``mechanism_substreams`` mode (each name's
#: position determines which spawned child SeedSequence it gets) — NEVER
#: reorder or remove an existing entry; only append new ones at the end,
#: and bump :data:`RNG_REGISTRY_VERSION` whenever the registry itself
#: changes, so an old run's manifest can be told apart from a new one.
#: Names beyond the milestone's own explicitly required minimum
#: (``ecological_regeneration`` — currently consumes zero draws, since
#: ``ResourcePatch.regenerate``/``EnvironmentResourcePool.regenerate`` are
#: both deterministic; ``ecological_perturbation``, ``rule_formation_
#: other``, ``demographic_replacement``, ``institutional_shocks``) are
#: additive isolation the milestone's "at minimum" wording explicitly
#: permits — see ``docs/level1.1b_rng_design.md`` for the full
#: name-by-name rationale and exactly what is/isn't isolated.
STREAM_REGISTRY: tuple[str, ...] = (
    "initialization",
    "social_interaction",
    "observation_error",
    "punishment",
    "ecological_action",
    "ecological_regeneration",
    "ecological_perturbation",
    "rule_formation_other",
    "rule_proposal_adoption",
    "contributions",
    "delegation_appointment",
    "administrative_task_performance",
    "discretion_appropriation",
    "accountability",
    "interpatch_coordination",
    "institutional_shocks",
    "relationship_dynamics",
    "imitation",
    "mutation",
    "demographic_replacement",
    # --- Level 1.2: open institutional evolution and blind phenotype
    # discovery. Appended, never inserted -- every Level 1.1b name above
    # keeps its exact position, so a "mechanism_substreams" run of an old
    # Level 1.1b config/seed still reproduces bit-for-bit.
    "institutional_observation",
    "institutional_transmission",
    "migration",
    "differential_persistence",
    "institutional_scaling",
    # --- Level 1.3: historical sequencing, entrenchment, and
    # path-dependent institutional differentiation. Appended, never
    # inserted -- every Level 1.2/1.2b name above keeps its exact
    # position, so a "mechanism_substreams" run of an old config/seed
    # still reproduces bit-for-bit (Section 3 item 8's own requirement:
    # every new historical mechanism gets its own registered
    # deterministic RNG substream). Three names cover Work Packages
    # A/C/D's stochastic draws respectively (pressure-history sampling
    # incl. the "stochastic but reproducible fluctuation" history kind;
    # entrenchment-influenced probabilistic decisions e.g. amendment vs.
    # dissolution; legitimacy accrual/loss fallibility draws) -- Work
    # Packages B/F/G/H are purely observer-side measurement over
    # already-generated state and draw no random numbers of their own.
    "historical_pressure_generation",
    "entrenchment_dynamics",
    "legitimacy_accumulation",
)

RNG_REGISTRY_VERSION = "level13_v1"
VALID_RNG_MODES = ("legacy_single_stream", "mechanism_substreams")


def make_rng(seed: int) -> np.random.Generator:
    """Construct the single seeded RNG for a simulation run.

    Parameters
    ----------
    seed:
        Non-negative integer seed. Two runs constructed with the same seed
        and the same config must produce bit-for-bit identical results.
    """
    if not isinstance(seed, int) or seed < 0:
        raise ValueError(f"seed must be a non-negative int, got {seed!r}")
    return np.random.default_rng(seed)


def child_streams(rng: np.random.Generator, n: int) -> list[np.random.Generator]:
    """Split one RNG into ``n`` independent child RNGs.

    Useful when a component (e.g. per-agent observation noise) needs its own
    stream without agents' draws interleaving in an order-dependent way.
    Still fully determined by the parent RNG's state, so overall
    reproducibility is preserved.
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    seed_seq = rng.bit_generator.seed_seq  # type: ignore[attr-defined]
    children = seed_seq.spawn(n)
    return [np.random.default_rng(s) for s in children]


def build_stream_registry(
    seed: int, mode: str, registry: tuple[str, ...] = STREAM_REGISTRY,
) -> dict[str, np.random.Generator]:
    """Build the ``{mechanism_name: Generator}`` mapping a
    :class:`~abm_governance.simulation.Simulation` uses for the rest of its
    life, per ``mode``.

    ``legacy_single_stream``: every name maps to the *same* one
    ``make_rng(seed)`` object — byte-for-byte the pre-Level-1.1b code path.

    ``mechanism_substreams``: ``numpy.random.SeedSequence(seed).spawn(len(
    registry))`` — a stable, documented, non-``hash()``-based derivation —
    gives each name its own independent ``Generator``, in registry order.
    Deterministic across processes: the same ``(seed, mode, registry)``
    always produces the same streams, since ``SeedSequence.spawn`` is a
    pure deterministic function of the parent sequence and spawn index.
    """
    if mode not in VALID_RNG_MODES:
        raise ValueError(f"rng_mode must be one of {VALID_RNG_MODES}, got {mode!r}")
    if mode == "legacy_single_stream":
        shared = make_rng(seed)
        return {name: shared for name in registry}
    # mechanism_substreams
    seed_seq = np.random.SeedSequence(seed)
    children = seed_seq.spawn(len(registry))
    return {name: np.random.default_rng(child) for name, child in zip(registry, children)}
