"""Level 1.3, Work Package D (Section 9): dual legitimacy channels — a
performance ledger (``L_P``) and a procedural/reciprocal ledger
(``L_R``), each independently gated by ``config.performance_legitimacy_
enabled``/``config.procedural_legitimacy_enabled``.

**Naming note.** "legitimacy" is banned project-wide as an ``Agent``
attribute substring (see ``agents/agent.py``'s
``FORBIDDEN_ATTRIBUTE_SUBSTRINGS``, still fully enforced, still
runtime-checked in ``Agent.__post_init__``) — but is explicitly, narrowly
permitted here, in ``core/config.py``'s config fields, and in
``rules/shared_rule.py``'s two new ledger fields, per
``dev_mem/project_vision.md`` §5's Level 1.3 amendment. This module IS
the "dedicated opt-in module" that amendment named.

**Disclosed simplification.** A byte-exact Section 9 wording is not
recoverable in this session (compacted-summary continuation, same
caveat as Work Packages B/C) — the two target signals below were chosen
to be (a) computable purely from quantities ``SharedRule`` already
accumulates (no dependency on delegation being enabled, no event-log
scanning, no new cross-round event threading — an ``O(1)`` per-rule
per-step update) and (b) genuinely distinct axes, matching the
dissertation's own performance-vs-procedural legitimacy framing (see
``docs/level1.3_theoretical_translation.md``):

- **Performance legitimacy target** = this rule's CUMULATIVE compliance
  rate to date (``compliance_count / (compliance_count +
  violation_count)``) — "is this institution seen to deliver the
  outcome it exists for." A neutral `0.5` prior before any compliance
  decision has ever been recorded for it.
- **Procedural/reciprocal legitimacy target** = the inverse of this
  rule's cumulative SANCTION intensity relative to its own interaction
  volume (``1 - sanction_count / (compliance_count + violation_count)``)
  — deliberately distinct from raw compliance: a rule that achieves high
  compliance only through heavy, constant sanctioning is read as LESS
  procedurally legitimate than one with the same compliance rate but
  little enforcement friction, even though both may score similarly on
  performance legitimacy. Also a neutral `0.5` prior with no track
  record yet.

Both ledgers move toward their target via a bounded EMA plus a small
Gaussian "fallibility" perturbation (mean 0, drawn from the dedicated
``legitimacy_accumulation`` RNG substream) before being clipped back to
``[0, 1]`` — legitimacy tracks its target on average but is not a
perfect, noiseless mirror of it step to step, matching
``core/rng.py::STREAM_REGISTRY``'s own docstring: "legitimacy
accrual/loss fallibility draws."
"""

from __future__ import annotations

import numpy as np


def performance_legitimacy_target(compliance_count: int, violation_count: int) -> float:
    total = compliance_count + violation_count
    if total <= 0:
        return 0.5
    return float(compliance_count) / float(total)


def procedural_legitimacy_target(compliance_count: int, violation_count: int, sanction_count: int) -> float:
    total = compliance_count + violation_count
    if total <= 0:
        return 0.5
    return float(np.clip(1.0 - sanction_count / total, 0.0, 1.0))


def legitimacy_step(
    current: float, target: float, learning_rate: float, fallibility_std: float, rng: np.random.Generator,
) -> float:
    """One bounded EMA update of a legitimacy ledger toward ``target``,
    then a small mean-0 Gaussian fallibility perturbation, clipped to
    ``[0, 1]``. ``fallibility_std == 0.0`` draws nothing from ``rng`` (an
    exact, RNG-consumption-free no-op path for that special case, rather
    than always drawing a zero-width normal — keeps a caller's stream
    consumption predictable when fallibility is deliberately turned
    off)."""
    moved = current + learning_rate * (target - current)
    if fallibility_std > 0.0:
        moved = moved + rng.normal(0.0, fallibility_std)
    return float(np.clip(moved, 0.0, 1.0))
