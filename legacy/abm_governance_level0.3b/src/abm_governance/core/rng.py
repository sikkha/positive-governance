"""Single source of randomness.

Every stochastic draw anywhere in this codebase must pass through a
``numpy.random.Generator`` obtained (directly or via a child stream) from
:func:`make_rng`. No module may call the global ``numpy.random`` functions
or the stdlib ``random`` module — that would make runs non-reproducible in
ways that are invisible from the outside.
"""

from __future__ import annotations

import numpy as np


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
