"""Level 1.3, Work Package B (Section 7): endogenous SEQUENCING
measurement — purely observer-side, reading only ``EventLog`` (this
project's "sole channel the observer layer reads from," see
``core/events.py``'s own module docstring). Nothing here writes back to
any registry or feeds a generative mechanism; that is Work Package A's
job (``core/historical_transmission.py``), already done and disclosed
separately.

**What this measures.** Section 5/Work Package A give each run a fully
controlled EXOGENOUS pressure order (when ``W_t``/``B_t``/``X_t``
themselves rise). This module measures the ENDOGENOUS order in which
eight named institutional-response dimensions first become *sustainably*
active, using the one generic primitive built for exactly this purpose
in ``core/historical_pressure.py::first_sustained_crossing`` (see that
function's own docstring — it already names "Work Package B's eight
tracked institutional-response series"). Comparing the endogenous order
against the exogenous pressure order, across many runs/conditions, is
what later stages (Stage 3's factorial design, task #98; Stage 6's blind
discovery, task #101) use to ask whether institutional differentiation
is actually path-dependent on WHEN pressures arrived, or just on WHICH
pressures arrived.

**Two disclosed interpretive choices.** This session's working context
carries the Level 1.3 governing specification only via a compacted
summary (an earlier turn's exact Section 7 wording is not recoverable
here), which supplied the eight dimension NAMES but not a byte-exact
operational definition for two of them. Both choices below are made to
(a) be computable purely from ``EventLog`` — consistent with every other
observer module in this codebase — and (b) reuse concepts this codebase
already defines, rather than inventing new generative-adjacent
vocabulary:

- **"generalized_rule"**: operationalized as FUNCTIONAL generality, not
  population-coverage generality (population size per patch is not
  recorded in ``EventLog`` — only ``patch_system`` has it, and observer
  modules read only the log/final state). A rule's generality at step
  ``t`` is the fraction of six governance "function families"
  (delegation, monitoring, sanctioning, accountability, contribution,
  interpatch coordination) it has exercised at least once by step ``t``
  — a rule that only ever forms and monitors stays "narrow"; one that
  comes to delegate, sanction, coordinate, AND account for itself is
  "general" in the sense of exercising broad governance function, not
  narrow single-purpose administration. The population-level series is
  the mean of this fraction across all rules active at step ``t``.
- **"cross_founder_reconstruction"**: reuses Level 1.1 Work Package C's
  already-defined reconstruction machinery (a new rule whose founding
  ``RuleProposalEvent`` carries ``origin="mutation"`` and a
  ``parent_rule_lineage_id``, see ``observer/institution_diagnostics.
  py::reconstruction_metrics``) and adds exactly one new condition: the
  reconstructing rule's founder (``RuleAdoptionEvent.proposer``) differs
  from the ORIGINAL, dissolved lineage's own founder. This is the
  narrowest available EventLog-computable reading of "the institution
  survived a change in who founded/leads it," distinct from mere
  parameter-lineage continuity.

Both choices are flagged again in this session's ``dev_mem/
status_update.md`` entry for this task, for the user's review — this is
a disclosed judgment call, not an authoritative restatement of Section 7.
"""

from __future__ import annotations

import numpy as np

from abm_governance.core.events import EventLog
from abm_governance.core.historical_pressure import first_sustained_crossing

#: Section 7's fixed vocabulary of eight tracked institutional-response
#: series. Order is for deterministic iteration only — it is not a claim
#: about any expected or "natural" sequence (the whole point of Work
#: Package B is that the actual order is an empirical question).
INSTITUTIONAL_RESPONSE_DIMENSIONS: tuple[str, ...] = (
    "delegation",
    "administrative_function",
    "generalized_rule",
    "monitoring",
    "accountability",
    "bargaining_participation",
    "cross_founder_reconstruction",
    "interpatch_coordination",
)

#: Governance "function families" used only to operationalize
#: "generalized_rule" above — plain event-type names already used
#: elsewhere in this codebase, not new vocabulary.
_FUNCTION_FAMILIES: tuple[str, ...] = (
    "delegation", "monitoring", "sanctioning", "accountability", "contribution", "coordination",
)

#: Per-dimension default activation thresholds passed to
#: ``first_sustained_crossing``. Every series in this module is a
#: fraction in [0, 1] EXCEPT ``cross_founder_reconstruction``, which is a
#: population-wide presence count (can exceed 1 if more than one
#: cross-founder-reconstructed rule is simultaneously active) — its
#: threshold of ``1.0`` means "at least one such rule is currently
#: active," not "all rules are."
DEFAULT_THRESHOLDS: dict[str, float] = {
    "delegation": 0.5,
    "administrative_function": 0.3,
    "generalized_rule": 0.5,
    "monitoring": 0.3,
    "accountability": 0.2,
    "bargaining_participation": 0.3,
    "cross_founder_reconstruction": 1.0,
    "interpatch_coordination": 0.3,
}


def _in_scope(patch_id: int, patch_ids: frozenset[int] | None) -> bool:
    return patch_ids is None or patch_id in patch_ids


def _interval_counts(starts, ends, n_steps: int) -> np.ndarray:
    """Diff-array sweep: number of CLOSED ``[start, end]`` intervals
    covering each step in ``[0, n_steps)``. An ``end`` of ``None`` means
    still-open through the end of the run (covers through
    ``n_steps - 1``).

    The end step is INCLUSIVE, not exclusive, by design: a
    ``DelegateRemovalEvent``/``RuleDissolutionEvent``/``Coordination
    DissolutionEvent``'s own ``step`` is the step at which that removal
    was PROCESSED, but this codebase's own step ordering (see
    ``rules/delegation.py``'s module docstring: accountability_round
    audits/recalls a delegate BEFORE that same step's removal takes
    effect) means the entity was still genuinely active for earlier
    rounds within that same step. Treating the end step as already
    inactive undercounts denominators built from these intervals against
    numerators built from same-step event references to that entity —
    caught empirically via ``tests/test_level13_sequencing_diagnostics.
    py``'s end-to-end test producing an accountability ratio > 1.0 before
    this fix. Intervals with ``end < start`` (should not occur for
    well-formed event pairs) are dropped rather than raising, matching
    this module's "measurement, never a correctness assertion about the
    generative layer" scope."""
    delta = np.zeros(n_steps + 1, dtype=float)
    for s, e in zip(starts, ends):
        s = max(0, int(s))
        if s >= n_steps:
            continue
        if e is None:
            delta[s] += 1.0
            continue
        e = int(e)
        if e < s:
            continue
        delta[s] += 1.0
        delta[min(n_steps, e + 1)] -= 1.0
    return np.cumsum(delta[:n_steps])


def _safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    out = np.zeros_like(numerator, dtype=float)
    nonzero = denominator > 0
    out[nonzero] = numerator[nonzero] / denominator[nonzero]
    return out


def _rule_intervals(event_log: EventLog, patch_ids: frozenset[int] | None):
    """rule_id -> adoption step, and rule_id -> dissolution step (absent
    if never dissolved this run)."""
    adopt_step: dict[int, int] = {}
    adopt_patch: dict[int, int] = {}
    for e in event_log.rule_adoptions:
        if _in_scope(e.patch_id, patch_ids):
            adopt_step[e.rule_id] = e.step
            adopt_patch[e.rule_id] = e.patch_id
    dissolve_step: dict[int, int] = {}
    for e in event_log.rule_dissolutions:
        if e.rule_id in adopt_step:
            dissolve_step[e.rule_id] = e.step
    return adopt_step, adopt_patch, dissolve_step


def _delegate_intervals(event_log: EventLog, patch_ids: frozenset[int] | None):
    """delegate_id -> appointment step, delegate_id -> rule_id,
    delegate_id -> removal step (absent if never removed this run)."""
    appoint_step: dict[int, int] = {}
    appoint_rule: dict[int, int] = {}
    for e in event_log.delegate_appointments:
        if _in_scope(e.patch_id, patch_ids):
            appoint_step[e.delegate_id] = e.step
            appoint_rule[e.delegate_id] = e.rule_id
    remove_step: dict[int, int] = {}
    for e in event_log.delegate_removals:
        if e.delegate_id in appoint_step:
            remove_step[e.delegate_id] = e.step
    return appoint_step, appoint_rule, remove_step


def _distinct_ids_per_step(event_lists_with_fields, n_steps: int, patch_ids: frozenset[int] | None) -> np.ndarray:
    """``event_lists_with_fields``: iterable of ``(events, id_field,
    patch_field)``. Returns, per step, the count of DISTINCT ids (across
    all supplied lists combined) that appear at that step — e.g. "how
    many distinct delegates were subject to an accountability event this
    step," never double-counting a delegate hit by both an audit and an
    appeal the same step."""
    per_step_ids: list[set] = [set() for _ in range(n_steps)]
    for events, id_field, patch_field in event_lists_with_fields:
        for e in events:
            if patch_ids is not None and getattr(e, patch_field, None) not in patch_ids:
                continue
            val = getattr(e, id_field)
            if val is None:
                continue
            t = e.step
            if 0 <= t < n_steps:
                per_step_ids[t].add(val)
    return np.array([len(s) for s in per_step_ids], dtype=float)


def _contribution_compliance_series(event_log: EventLog, n_steps: int, patch_ids: frozenset[int] | None) -> np.ndarray:
    """Per-step contribution-compliance fraction, HELD (forward-filled)
    from the most recent contribution-assessment round through to the
    next one — consistent with how every other ``institutional_response_
    series`` dimension represents "current institutional state"
    (``_interval_counts``: state held across an active interval), not
    "activity at this instant." Contribution rounds only run every
    ``contribution_period_steps`` steps (``rules/contributions.py::
    contribution_round``); zero-filling the intervening steps (this
    function's behavior before Level 1.3b's Work Package B audit — see
    ``docs/level1.3b_bargaining_activation_audit.md``) made a "sustained
    crossing" of ``min_duration_steps`` consecutive steps mathematically
    IMPOSSIBLE whenever ``min_duration_steps`` reaches the assessment
    period, regardless of the true compliance rate — every Level 1.3/
    1.3b stage script passes ``min_duration_steps=10``, exactly equal to
    the default ``contribution_period_steps=10``. Proved empirically in
    that audit with a synthetic 100%-compliance-every-round series that
    still failed to register a sustained crossing under the old zero-fill
    construction. Steps before the first assessment round hold ``0.0``
    (no information yet), matching every other dimension's
    zero-before-onset convention."""
    total = np.zeros(n_steps, dtype=float)
    complied = np.zeros(n_steps, dtype=float)
    for e in event_log.contributions:
        if not _in_scope(e.patch_id, patch_ids):
            continue
        if 0 <= e.step < n_steps:
            total[e.step] += 1.0
            if e.complied:
                complied[e.step] += 1.0
    ratio = _safe_divide(complied, total)
    held = np.zeros(n_steps, dtype=float)
    current = 0.0
    for t in range(n_steps):
        if total[t] > 0.0:
            current = ratio[t]
        held[t] = current
    return held


def _link_intervals(event_log: EventLog, patch_ids: frozenset[int] | None):
    start: dict[int, int] = {}
    for e in event_log.coordination_links:
        if not e.accepted:
            continue
        if patch_ids is not None and not (e.patch_id_a in patch_ids and e.patch_id_b in patch_ids):
            continue
        start[e.link_id] = e.step
    end: dict[int, int] = {}
    for e in event_log.coordination_dissolutions:
        if e.link_id in start:
            end[e.link_id] = e.step
    return start, end


def _generalized_rule_series(
    event_log: EventLog, n_steps: int, adopt_step: dict, dissolve_step: dict, patch_ids: frozenset[int] | None,
) -> np.ndarray:
    """Mean, across rules active at step ``t``, of each rule's own
    "fraction of function families exercised so far" — see this module's
    own docstring for the full disclosed rationale."""
    first_touch: dict[int, dict[str, int]] = {rid: {} for rid in adopt_step}

    def _touch(rid: int, family: str, step: int) -> None:
        record = first_touch.get(rid)
        if record is None:
            return
        current = record.get(family)
        if current is None or step < current:
            record[family] = step

    for e in event_log.delegate_appointments:
        _touch(e.rule_id, "delegation", e.step)
    for e in event_log.monitorings:
        _touch(e.rule_id, "monitoring", e.step)
    for e in event_log.sanctions:
        _touch(e.rule_id, "sanctioning", e.step)
    for e in event_log.audits:
        _touch(e.rule_id, "accountability", e.step)
    for e in event_log.recalls:
        _touch(e.rule_id, "accountability", e.step)
    for e in event_log.appeals:
        _touch(e.rule_id, "accountability", e.step)
    for e in event_log.contributions:
        _touch(e.rule_id, "contribution", e.step)
    for e in event_log.coordination_proposals:
        if _in_scope(e.patch_id_from, patch_ids):
            _touch(e.rule_id_from, "coordination", e.step)
        if _in_scope(e.patch_id_to, patch_ids):
            _touch(e.rule_id_to, "coordination", e.step)

    sum_series = np.zeros(n_steps, dtype=float)
    count_series = np.zeros(n_steps, dtype=float)
    n_families = len(_FUNCTION_FAMILIES)
    for rid, adopt in adopt_step.items():
        # Inclusive-end convention (see ``_interval_counts``'s docstring):
        # a rule dissolved at step ``d`` is still counted active THROUGH
        # step ``d``, consistent with every other series in this module.
        dissolve = dissolve_step.get(rid)
        hi = n_steps if dissolve is None else min(n_steps, dissolve + 1)
        lo = max(0, adopt)
        if hi <= lo:
            continue
        touches = sorted(first_touch[rid].values())
        idx = 0
        achieved = 0
        for t in range(lo, hi):
            while idx < len(touches) and touches[idx] <= t:
                achieved += 1
                idx += 1
            sum_series[t] += achieved / n_families
            count_series[t] += 1.0
    return _safe_divide(sum_series, count_series)


def _cross_founder_reconstruction_series(
    event_log: EventLog, n_steps: int, dissolve_step: dict, patch_ids: frozenset[int] | None,
) -> np.ndarray:
    adoption_by_lineage = {}
    for a in event_log.rule_adoptions:
        if _in_scope(a.patch_id, patch_ids):
            adoption_by_lineage[a.rule_lineage_id] = a
    proposal_by_lineage: dict[int, object] = {}
    for p in event_log.rule_proposals:
        if not _in_scope(p.patch_id, patch_ids):
            continue
        existing = proposal_by_lineage.get(p.rule_lineage_id)
        if existing is None or p.step > existing.step:
            proposal_by_lineage[p.rule_lineage_id] = p

    starts, ends = [], []
    for lineage_id, adoption in adoption_by_lineage.items():
        proposal = proposal_by_lineage.get(lineage_id)
        if proposal is None or proposal.origin != "mutation" or proposal.parent_rule_lineage_id is None:
            continue
        parent_adoption = adoption_by_lineage.get(proposal.parent_rule_lineage_id)
        if parent_adoption is None:
            continue  # parent lineage's adoption is out of scope/predates this log -- founder unverifiable.
        if parent_adoption.proposer == adoption.proposer:
            continue  # same founder reconstructed their own institution -- not a CROSS-founder event.
        starts.append(adoption.step)
        ends.append(dissolve_step.get(adoption.rule_id))
    return _interval_counts(starts, ends, n_steps)


def institutional_response_series(
    event_log: EventLog, n_steps: int, patch_ids: frozenset[int] | None = None,
) -> dict[str, np.ndarray]:
    """Build all eight of Section 7's named institutional-response
    series (length ``n_steps`` each) for one run, from ``event_log``
    alone. ``patch_ids`` restricts to a subset of patches (``None`` =
    population-wide); every series is a fraction in ``[0, 1]`` except
    ``cross_founder_reconstruction`` (a presence COUNT — see
    ``DEFAULT_THRESHOLDS``'s docstring note)."""
    adopt_step, adopt_patch, dissolve_step = _rule_intervals(event_log, patch_ids)
    appoint_step, appoint_rule, remove_step = _delegate_intervals(event_log, patch_ids)

    n_active_rules = _interval_counts(
        list(adopt_step.values()), [dissolve_step.get(rid) for rid in adopt_step], n_steps,
    )
    n_active_delegates = _interval_counts(
        list(appoint_step.values()), [remove_step.get(did) for did in appoint_step], n_steps,
    )

    n_delegates_active_this_step = _distinct_ids_per_step(
        [(event_log.task_performances, "delegate_id", "patch_id")], n_steps, patch_ids,
    )
    n_rules_monitored_this_step = _distinct_ids_per_step(
        [(event_log.monitorings, "rule_id", "patch_id")], n_steps, patch_ids,
    )
    n_delegates_accountability_this_step = _distinct_ids_per_step(
        [
            (event_log.audits, "delegate_id", "patch_id"),
            (event_log.recalls, "delegate_id", "patch_id"),
            (event_log.appeals, "delegate_id", "patch_id"),
        ],
        n_steps, patch_ids,
    )

    link_start, link_end = _link_intervals(event_log, patch_ids)
    n_active_links = _interval_counts(list(link_start.values()), [link_end.get(lid) for lid in link_start], n_steps)

    return {
        "delegation": _safe_divide(n_active_delegates, n_active_rules),
        "administrative_function": _safe_divide(n_delegates_active_this_step, n_active_delegates),
        "generalized_rule": _generalized_rule_series(event_log, n_steps, adopt_step, dissolve_step, patch_ids),
        "monitoring": _safe_divide(n_rules_monitored_this_step, n_active_rules),
        "accountability": _safe_divide(n_delegates_accountability_this_step, n_active_delegates),
        "bargaining_participation": _contribution_compliance_series(event_log, n_steps, patch_ids),
        "cross_founder_reconstruction": _cross_founder_reconstruction_series(event_log, n_steps, dissolve_step, patch_ids),
        "interpatch_coordination": _safe_divide(n_active_links, n_active_rules / 2.0),
    }


def sequencing_vector(
    series: dict[str, np.ndarray], min_duration_steps: int, thresholds: dict[str, float] | None = None,
) -> dict[str, int | None]:
    """For each of the eight dimensions, the first step at which its
    series is sustainably active (``None`` if never), via
    ``first_sustained_crossing`` — Section 7's "do not assign a
    sequencing category where either activation is absent" is honored
    automatically: a missing/never-crossed dimension stays ``None``
    rather than being coerced into a comparison."""
    thresholds = thresholds if thresholds is not None else DEFAULT_THRESHOLDS
    out: dict[str, int | None] = {}
    for name in INSTITUTIONAL_RESPONSE_DIMENSIONS:
        s = series.get(name)
        if s is None:
            out[name] = None
            continue
        out[name] = first_sustained_crossing(s, thresholds.get(name, 0.5), min_duration_steps)
    return out


def sequencing_order(vector: dict[str, int | None]) -> tuple[str, ...]:
    """Section 7's ordinal representation of one run's endogenous
    sequence: dimension names sorted by first-sustained step (ties
    broken by name for determinism), with never-activated dimensions
    (``None``) sorted last, in name order — never by dict insertion
    order, which is an implementation detail, not a measurement."""
    def _key(name: str):
        step = vector.get(name)
        return (step is None, step if step is not None else 0, name)
    return tuple(sorted(vector.keys(), key=_key))
