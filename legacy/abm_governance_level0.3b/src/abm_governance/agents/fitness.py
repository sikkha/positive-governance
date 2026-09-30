"""Configurable imitation fitness signal (Level 0.2, Work Package C).

Level 0.1's imitation rule (``agents/adaptation.py``) compared agents by
*cumulative resources* — a pure difference, ``peer.resources -
own.resources``, fed into a Fermi rule. That signal is exactly
translation-invariant: adding the same constant to every agent's resources
(which is approximately what an unconditional per-step subsistence charge
against a collapsed, zero-extraction resource pool does — see
``dev_mem/status_update.md``'s session-3-start entry) leaves every pairwise
difference, and therefore every imitation probability, completely
unchanged. Whether that invariance is *responsible* for Level 0.1's
near-universal cooperation surviving unbounded negative resources is an
open empirical question this module exists to let the project actually
test, by making the fitness signal itself a first-class, swappable
parameter rather than a hard-coded implementation detail.

No signal here is asserted "more correct" than another in advance — see
``docs/level0.2_scientific_note.md``. All four share one interface
(:func:`fitness_signal`) so the imitation round (``agents/adaptation.py``)
never needs to know which mode is active; it just calls this function
twice (once per agent in a comparison) and feeds the difference into the
same Fermi rule as before.

Level 0.3, Work Package D adds a second, orthogonal parameter: ``stream``.
The milestone brief requires that "the ecological policy and social
policy [be able to] use separately selected fitness signals," which this
project chose to implement as the *same four formulas*, applied to a
*different underlying ledger* — ``stream="total"`` (the default, used by
social-policy imitation, byte-for-byte unchanged from Level 0.2) reads
the agent's overall economic state (``resources``, ``recent_payoff``,
etc., which mix social-game payoff, ecological extraction/maintenance,
subsistence, and every other resource-affecting mechanic together);
``stream="ecological"`` (used by ecological-policy imitation) reads only
the parallel ecological-only ledger (``ecological_cumulative_gain``,
``ecological_recent_payoff``, etc. — see ``agents/agent.py``), so
"ecologically successful" and "wealthy" are never silently conflated.
Neither stream is asserted more correct than the other, exactly as no
mode is.
"""

from __future__ import annotations

import math

from abm_governance.agents.agent import Agent

VALID_FITNESS_MODES = ("cumulative_resources", "recent_payoff", "resource_delta", "viability_adjusted")
VALID_FITNESS_STREAMS = ("total", "ecological")


def fitness_signal(
    agent: Agent, mode: str, viability_adjusted_dormant_penalty: float = 0.0, stream: str = "total"
) -> float:
    """Return agent's fitness signal under ``mode`` and ``stream``. Every
    combination returns a finite float (never NaN) so it is always safe
    to feed into the Fermi rule's subtraction — the "recent_payoff"-family
    signals are always well-defined; the "resource_delta"-family signals
    substitute 0.0 (a neutral, "no known change yet" value, not a claim of
    stability) for an agent whose relevant rolling window is not yet full,
    which only happens in the first ``fitness_window`` steps of a run (or
    of a replacement agent's life, in ``removal_replacement`` mode).

    ``mode`` must be one of :data:`VALID_FITNESS_MODES`; ``stream`` must
    be one of :data:`VALID_FITNESS_STREAMS`. Neither is validated here
    (that's ``SimulationConfig.__post_init__``'s job) — an unrecognized
    value raises ``ValueError`` so a typo fails loudly rather than
    silently falling back to a default signal.
    """
    if stream not in VALID_FITNESS_STREAMS:
        raise ValueError(f"unknown fitness stream: {stream!r}")
    ecological = stream == "ecological"

    if mode == "cumulative_resources":
        # Level 0.1-compatible (stream="total"): the agent's entire
        # accumulated resource stock, exactly as before.
        # Translation-invariant by construction, in either stream (the
        # ecological stream's "cumulative" quantity is likewise a running
        # total never reset).
        return float(agent.ecological_cumulative_gain) if ecological else float(agent.resources)

    if mode == "recent_payoff":
        # Net payoff over the rolling window only. NOT translation-
        # invariant to a uniform per-step subsistence charge (stream=
        # "total") because subsistence is deliberately excluded from this
        # signal; the ecological stream excludes subsistence by
        # construction too (subsistence is not part of the ecological
        # ledger at all — see simulation.py).
        return float(agent.ecological_recent_payoff) if ecological else float(agent.recent_payoff)

    if mode == "resource_delta":
        # Change in the stream's cumulative quantity over the rolling
        # window. A uniform per-agent subsistence charge subtracts the
        # same constant from every agent's *total*-stream delta, so that
        # combination is translation-invariant to that specific
        # perturbation (checked directly by tests/test_fitness.py);
        # subsistence never touches the ecological ledger at all, so the
        # ecological-stream delta is unaffected by a subsistence shift for
        # an entirely different (structural) reason.
        delta = agent.ecological_cumulative_delta if ecological else agent.resource_delta
        return 0.0 if math.isnan(delta) else float(delta)

    if mode == "viability_adjusted":
        # recent_payoff (in the selected stream), with a dormant agent's
        # signal pulled down by a fixed, finite penalty — dormancy is not
        # itself translation-invariant (a discrete state, not a linear
        # combination of resources), so this mode is the one most likely
        # to break invariance to a uniform resource shift, in either
        # stream, *if* the shift is large enough to push agents across the
        # dormancy threshold (viability state is shared across both
        # streams — there is only one viability state machine per agent).
        base = float(agent.ecological_recent_payoff) if ecological else float(agent.recent_payoff)
        if agent.viability_state == "dormant":
            base -= viability_adjusted_dormant_penalty
        return base

    raise ValueError(f"unknown fitness mode: {mode!r}")
