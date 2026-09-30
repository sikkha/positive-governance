"""Level 1.3b, Work Package G / Stage 6 (task #119, Section 11):
mid-run state checkpoint/fork machinery -- the "serialization/copy
machinery" the frozen ``STAGE6_HISTORY_ERASURE["sham_purpose"]``
explicitly requires be validated (a sham, byte-identical no-op
intervention) before trusting any real intervention's divergence as
historically meaningful.

**Why this is real checkpointing, not another pressure-series
override.** Level 1.3's own Work Package E (``core/historical_
counterfactuals.py``) and this milestone's own Stage 5 both apply a
counterfactual pressure series at construction time (``Simulation.
__init__``) -- the WHOLE run is re-simulated from step 0 under the
altered series, so nothing about "current visible structure" at some
intervention step is literally preserved, only the shared seed's
generative conditions. Section 11's own explicit ``preserves``
requirement (``current_visible_structure``, ``current_resources``,
``current_ecology``, ``current_network``) needs something stronger: run
the REAL, unmodified simulation up to intervention step ``T`` (so every
agent/rule/patch/network field reflects genuine history through ``T``),
fork the live Python object with :func:`copy.deepcopy` (confirmed
correctly deep-copies ``numpy.random.Generator`` RNG state, per this
task's own smoke test), apply ONE intervention's targeted mutation to
the fork's stored historical fields only (see ``experiments/level13b_
stage6_history_erasure.py`` for what each named intervention resets),
then continue stepping the fork to completion -- current state
untouched, only the record that PRODUCED it is altered going forward.

**Confirmed via direct testing (not asserted): `Simulation._run_one_
step`, called manually in a loop, produces byte-for-byte identical
metrics/event-log output to `Simulation.run()`'s own loop** (NaN-aware
comparison, matching this project's own ``_metrics_identical``
convention elsewhere) -- ``run()`` IS exactly that loop, nothing else,
so stepping manually up to a fork point and resuming afterward is a
faithful, not an approximate, reconstruction of an uninterrupted run.
Also confirmed directly: two entirely independent ``Simulation(config)``
objects built from the identical ``config``/seed, each stepped forward
the same number of steps, produce byte-for-byte identical metrics and
event logs -- ``Simulation`` is a pure deterministic function of
``(config, seed)`` with no reliance on any process-global state (six
sequential from-scratch builds in the same process were checked and
agreed exactly), so REBUILDING from scratch and replaying to a
checkpoint step is not an approximation of "the live object at that
step" -- it is exactly that state, reproduced.

**A genuine bug found and fixed in this module's own first draft
(disclosed here and in ``dev_mem/status_update.md``, task #119):
:func:`fork`'s original implementation used ``copy.deepcopy(sim)`` to
fork a live, in-progress ``Simulation`` -- and ``copy.deepcopy`` does
NOT reliably preserve a ``frozenset``'s iteration order.** A
``frozenset``'s internal hash-table layout depends on the specific
history of insertions/deletions/resizes that built it, not only on its
final contents -- confirmed directly: ``list(some_frozenset)`` and
``list(copy.deepcopy(some_frozenset))`` can differ in ORDER (not
contents) for a frozenset whose table was shaped by a long mutation
history (e.g. ``SharedRule.members``, reassigned via
``frozenset(members)`` from a list that itself reflects many rounds of
agents joining/leaving). ``rules/dynamics.py::monitoring_round``
iterates ``list(rule.members)`` and consumes one ``rng.random()`` draw
per element IN THAT ORDER -- a reordered copy therefore pairs
different agents with different RNG draws than the original would
have, a real, silent divergence Stage 6's own sham intervention caught
(a first-draft sham/control mismatch at seed 9,100,000, traced via
RNG-call-log instrumentation to a ``monitoring_round`` volunteer-list
divergence at step 251, root-caused to exactly this ``rule_registry[0]
.members`` frozenset reordering). :func:`fork` is KEPT (correct and
tested for the case where no order-sensitive frozenset is affected --
see this module's own test suite) but now carries this explicit
caveat; ``experiments/level13b_stage6_history_erasure.py`` does not
use it at all, precisely because it does not need to -- see that
module's own docstring for why REBUILD-based forking sidesteps this
entirely."""

from __future__ import annotations

import copy
from typing import Callable

from abm_governance.simulation import Simulation


def run_partial(sim: Simulation, up_to_step: int) -> list[dict]:
    """Advance ``sim`` in place for steps ``[0, up_to_step)``, returning
    the per-step metrics dicts ``_run_one_step`` produced. ``sim``'s
    internal state afterward reflects having completed exactly
    ``up_to_step`` steps."""
    return [sim._run_one_step(s) for s in range(up_to_step)]


def fork(sim: Simulation) -> Simulation:
    """A deep copy of ``sim``'s current in-progress state -- an
    independent object; mutating the fork never affects ``sim`` or vice
    versa. **Caveat (see module docstring): NOT safe for any downstream
    code that iterates a ``frozenset`` field (e.g. ``SharedRule.
    members``) in order while consuming RNG draws per element --
    ``copy.deepcopy`` does not guarantee preserving frozenset iteration
    order.** Safe for state without order-sensitive frozensets, or when
    the caller only reads frozenset CONTENTS, never their order.
    Prefer rebuilding from ``(config, seed)`` and replaying with
    :func:`run_partial` instead when this caveat could matter --
    proven exactly equivalent to a live object's state at the same
    step (see module docstring)."""
    return copy.deepcopy(sim)


def finish(sim: Simulation, from_step: int, n_steps: int) -> list[dict]:
    """Advance ``sim`` in place for the remaining steps
    ``[from_step, n_steps)``, returning their per-step metrics dicts."""
    return [sim._run_one_step(s) for s in range(from_step, n_steps)]


def fork_and_finish(
    sim: Simulation, intervention_step: int, n_steps: int,
    mutate: Callable[[Simulation], None] | None = None,
) -> Simulation:
    """The full Stage 6 pattern in one call: fork ``sim`` (already
    advanced to ``intervention_step``), optionally apply ``mutate`` to
    the FORK ONLY (``sim`` itself is left untouched, so it can be
    forked again for a different intervention from the same
    checkpoint), then run the fork to completion. Returns the
    (now-completed) fork; its ``.event_log``/``.metrics`` reflect the
    full run with the intervention applied starting at
    ``intervention_step``. ``mutate=None`` is the sham
    (identical-state-copy) intervention itself."""
    branch = fork(sim)
    if mutate is not None:
        mutate(branch)
    finish(branch, intervention_step, n_steps)
    return branch
