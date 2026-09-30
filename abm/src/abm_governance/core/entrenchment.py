"""Level 1.3, Work Package C (Section 8): continuous institutional
entrenchment — three small pure functions, reused identically at every
site ``rules/dynamics.py`` applies them (mirrors ``core/
historical_transmission.py``'s own "one audited helper, reused
everywhere" discipline for Work Package A).

**The mechanism**: an institution's ENTRENCHMENT grows with its own age
(``step - rule.founding_step``) and, once entrenched, makes that
institution both harder to successfully AMEND (a raised amendment
threshold — status-quo bias) and more likely to SURVIVE a dissolution
trigger it would otherwise fail (a "sunk investment/increasing returns"
effect — the literal "amendment vs. dissolution" probabilistic branch
point the ``entrenchment_dynamics`` RNG substream was reserved for, see
``core/rng.py::STREAM_REGISTRY``). Deliberately adds NO new mutable
state anywhere: entrenchment here is a pure function of a rule's age, a
quantity every ``SharedRule`` has recorded (via ``founding_step``) since
Level 1.0 — the same "compute from existing state" discipline Work
Package A used for its admin-capacity-demand channel.

**Two explicit invariants, both enforced by capping rather than by
disabling the effect near the cap**: neither amendment nor dissolution
may ever be made STRUCTURALLY impossible by entrenchment alone, however
old an institution gets or however high its sensitivity constants are
set. ``entrenchment_adjusted_threshold`` caps at 0.999 (never exactly
1.0 — the threshold-clearing check ``support_frac >= threshold`` stays
satisfiable at ``support_frac == 1.0``); ``entrenchment_survival_
probability`` caps at 0.9 (survival is never certain — an institution
that has truly lost all membership, funding, and activity must remain
able to end).
"""

from __future__ import annotations


def entrenchment_level(age_steps: int, maturation_steps: int) -> float:
    """A rule's entrenchment score in ``[0, 1]``: a linear ramp from 0
    at founding to 1 once ``age_steps >= maturation_steps``. The
    plainest, most auditable "increasing returns accumulate with time"
    operationalization available. ``maturation_steps <= 0`` is treated
    as instantaneous maturation (any rule with positive age is fully
    entrenched) rather than raising — ``SimulationConfig.__post_init__``
    already rejects a non-positive ``entrenchment_maturation_steps``
    before a run starts, so this branch only ever protects a direct,
    out-of-band call to this function."""
    if maturation_steps <= 0:
        return 1.0 if age_steps > 0 else 0.0
    return float(min(1.0, max(0.0, age_steps / maturation_steps)))


def entrenchment_adjusted_threshold(base_threshold: float, entrenchment: float, sensitivity: float) -> float:
    """Raises an adoption/amendment threshold as entrenchment grows —
    harder to successfully change a more-entrenched institution. Capped
    at 0.999 (see module docstring's invariant)."""
    return float(min(0.999, base_threshold + sensitivity * entrenchment))


def entrenchment_survival_probability(entrenchment: float, sensitivity: float) -> float:
    """Probability that an institution which just breached a dissolution
    trigger nonetheless survives this step, as a function of
    entrenchment. Capped at 0.9 (see module docstring's invariant) and
    floored at 0.0 (a negative ``sensitivity`` or ``entrenchment`` of
    exactly 0 must never produce a negative probability)."""
    return float(min(0.9, max(0.0, sensitivity * entrenchment)))
