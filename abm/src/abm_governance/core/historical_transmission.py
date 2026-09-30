"""Level 1.3, Work Package A (Section 6): pressure transmission.

Historical pressure must alter local incentives/opportunity structures,
never impose a macro outcome directly. This module owns the one small,
pure, audited transformation every causal channel below reuses:
:func:`pressure_adjusted_probability` (an additive nudge to a
probability-like quantity, clipped to a valid range) and
:func:`pressure_adjusted_scale` (a multiplicative nudge to a
non-negative rate/frequency-like quantity). Every channel-specific call
site (in ``rules/delegation.py``, ``rules/contributions.py``,
``rules/coordination.py``) is a thin, individually-flagged wrapper
around one of these two primitives -- never a bespoke formula per
channel -- so the transmission logic itself is auditable in one place
even though its effects are felt in several existing modules.

**Disclosed scope reduction.** Section 6 lists six candidate
microscopic quantities per pressure (eighteen total). This milestone
implements TWO representative, mechanistically well-defined channels
per pressure (six total), chosen for being cleanly expressible as a
nudge to an existing, already-tested formula without restructuring the
underlying mechanism:

- security_pressure -> returns_to_delegation (task-success formula),
  admin_capacity_demand (capacity-bonus weight in the same formula)
- bargaining_pressure -> conditional_contribution (contribution
  compliance willingness), appeal_recall (appeal-trigger probability)
- coordination_complexity -> cross_patch_transactions (coordination
  link activity probability), interoperable_demand (coordination
  proposal probability)

The remaining twelve candidate channels (expected loss from
coordination failure, cost of fragmented response, coordination-task
frequency; propensity to demand information, cost of exclusion, demand
for procedural participation, conditional rule adoption; stranger-
interaction frequency, need for predictable general rules,
administrative record value, cost of local incompatibility) are NOT
wired this milestone -- each would require either a new agent-level
trait or a new observer-side record this codebase does not yet have,
which this milestone's own compute-budget discipline (Section 19)
treats as a scope decision to be recorded and disclosed, not made
silently. See ``docs/level1.3_historical_mechanisms.md`` for the full
per-channel rationale and this note's own status as a decided,
disclosed reduction (recorded before any Stage 1+ result was observed).

Every channel is independently enabled/disabled (Section 6's own
requirement) via its own config flag, in addition to (never instead of)
its parent pressure's own master flag."""

from __future__ import annotations


def pressure_adjusted_probability(base: float, level: float, sensitivity: float) -> float:
    """``base + sensitivity * level``, clipped to ``[0.0, 1.0]``. Used
    for every channel that nudges a probability-like quantity
    (task-success base rate, appeal-trigger probability, contribution
    compliance willingness)."""
    return max(0.0, min(1.0, base + sensitivity * level))


def pressure_adjusted_scale(base: float, level: float, sensitivity: float) -> float:
    """``base * (1 + sensitivity * level)``, floored at ``0.0``. Used
    for every channel that nudges a non-negative rate/weight/frequency
    quantity (capacity-bonus weight, coordination proposal/activity
    probability treated as a rate)."""
    return max(0.0, base * (1.0 + sensitivity * level))
