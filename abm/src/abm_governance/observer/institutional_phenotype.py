"""Level 1.2, Section 6: the observer-side institutional phenotype
vector X = (C, E, L, D, M, R, S, F, V, H).

**Deliberately distinctly named** from the pre-existing, unrelated Level
0.1 module ``observer/phenotype.py`` (policy-type behavioral distance —
a different concept entirely; see that module's own docstring). No
functional relationship between the two.

**Observer-only, never agent-visible, never optimized.** This module is
read-only: every function here takes an already-completed (or
in-progress, for online diagnostics) simulation's ``EventLog``/
``institution_registry``/``delegate_registry``/``PatchSystem`` and
computes a value. Nothing in ``simulation.py`` or any ``rules/*.py``
module ever imports from this module (the same one-directional
generative→observer dependency every prior level's addendum documents;
``tests/test_level12_structural_guards.py``'s import-direction check —
mirroring ``TestGenerativeObserverSeparation`` in
``tests/test_level11_compatibility.py`` — covers this file too).

**Structural discipline, per Section 6's own requirements**: every
dimension below is returned as a raw ``{"numerator", "denominator",
"value", "window"}`` record (or a small dict of such records, for the
two composite dimensions F and V) — raw components are always exported
alongside the ratio, missingness (``None``/``nan``) is always preserved
rather than zero-filled, and **no automatic normative meaning is ever
assigned**: a high or low value on any single dimension is not
interpreted here as "better" or "worse" governance — this module reports
measurements, not verdicts. Costs, false sanctions, appropriation, and
ecological failure are represented on equal footing with achievements
(E's ``false_positive_rate_given_innocent``, R's burden numerator, V's
resource-depletion direction) — never only the positive-sounding half of
each measurement.

**Never collapsed into one score.** :func:`institutional_phenotype_vector`
returns all ten dimensions as separate top-level keys; nothing in this
module sums, weights, or otherwise combines them into a single index.

**Work Package F (Level 1.2b, Section 11) audit finding, disclosed
here and enforced by** ``observer/phenotype_feature_audit.py`` **/**
``tests/test_level12b_phenotype_feature_audit.py``: every dimension
function below accepts a ``window`` argument for API uniformity, but
``window`` only actually *filters the underlying computation* for
three of ten dimensions (E fully; C and R only partially — see their
own docstrings). The remaining seven dimensions (L, D, M, S, F, V, H)
are pure current-state snapshots — they have no per-step history to
filter, since they read live, already-aggregated running totals off
mutable objects (``SharedRule``, ``Delegate``, ``InstitutionRecord``,
``PatchSystem``) rather than per-step events. This is not a bug to be
patched by adding fake filtering; it is how "stock" (state-at-an-
instant) constructs differ from "flow" (accumulated-over-an-interval)
constructs. The **correct way to get a windowed view of a snapshot
dimension is external**: call :func:`institutional_phenotype_vector`
repeatedly at different steps (each call's own ``window`` left
``None``) to build a list of ``{"step": ..., "vector": ...}``
snapshots, then use ``observer/temporal_features.py``'s
``window_static_features``/``window_dynamic_features`` to summarize
that already-collected series over any window of interest — exactly
the architecture ``temporal_features.py`` already implements and Work
Package G (Section 12) will drive.

What WAS a genuine transparency gap, and IS fixed here: every record
silently echoed back whatever ``window`` was passed, with nothing
indicating whether that window had actually been applied. A caller
passing ``window=(100, 200)`` to this function and reading
``record["window"] == (100, 200)`` back could easily assume the value
itself reflects only steps 100-199, which is false for the seven
snapshot dimensions. Every record now additionally carries
``"window_applied"`` (``True``/``False``/``"partial"``) and
``"construct_type"`` (``"event_windowed"``, ``"snapshot_current_state"``,
or a description of the specific mixed case), so this is a machine-
checkable fact about the record, not merely something documented in
prose that can silently drift out of sync with the code."""

from __future__ import annotations

import itertools

from abm_governance.core.events import EventLog
from abm_governance.observer.accountability_diagnostics import effective_constraint
from abm_governance.rules.institution import structural_distance


def _record(numerator, denominator, value, window: tuple[int, int] | None, *, construct_type: str, window_applied) -> dict:
    """``window_applied`` is ``True``, ``False``, or ``"partial"`` (see
    module docstring). ``construct_type`` names the numerator/
    denominator's temporal nature (e.g. ``"event_windowed_ratio"``,
    ``"snapshot_current_state_ratio"``) so a downstream consumer can
    tell, without reading source, whether mixing this dimension's
    value across seed-runs collected at different steps is comparing
    like with like."""
    return {
        "numerator": numerator, "denominator": denominator, "value": value, "window": window,
        "window_applied": window_applied, "construct_type": construct_type,
    }


def _safe_ratio(numerator, denominator):
    if denominator is None or denominator == 0:
        return float("nan")
    return numerator / denominator


def _in_range(step: int, window: tuple[int, int] | None) -> bool:
    if window is None:
        return True
    start, end = window
    return start <= step < end


# --- C: realized administrative capacity ------------------------------------
def realized_administrative_capacity(delegate_registry: dict, window: tuple[int, int] | None = None) -> dict:
    """Mean realized capacity (``Delegate.capacity`` — itself already a
    realized-performance-only quantity, never a config-assigned trait)
    across every currently *active* delegate. ``NaN`` (not ``0.0``) when
    there is no active delegate — the structural-NaN discipline Section 6
    requires."""
    active = [d for d in delegate_registry.values() if d.active and _in_range(d.start_step, window)]
    total = sum(d.capacity for d in active)
    n = len(active)
    # Audit note (Work Package F): this is a MIXED construct. ``window``
    # filters delegates by their *appointment* step (start_step), but
    # is conjoined with ``d.active`` -- a *current-tense* snapshot flag,
    # not "was active at some point during window". A delegate appointed
    # inside the window but since removed is excluded (denominator
    # undercounts); a delegate appointed before the window but still
    # active is also excluded even though they were active throughout
    # the window. This does not match either "delegates whose tenure
    # overlapped window" or "delegates active as of window end" cleanly
    # -- disclosed as "partial" rather than silently treated as fully
    # windowed.
    return _record(total, n, _safe_ratio(total, n) if n else float("nan"), window,
                    construct_type="start_step_windowed_but_active_flag_is_current_state", window_applied="partial")


# --- E: effective constraint -------------------------------------------------
def effective_constraint_dimension(event_log: EventLog, window: tuple[int, int] | None = None) -> dict:
    """Directly reuses ``observer/accountability_diagnostics.py::
    effective_constraint`` (Level 1.1b) — the audited, realized-outcome-
    only constraint measure this project already built and validated;
    never recomputed independently here. ``value`` is
    ``detection_rate_given_misconduct`` (``NaN`` when undefined, not
    ``None`` — this module's own preserve-NaN convention)."""
    ec = effective_constraint(event_log, window)
    value = ec["detection_rate_given_misconduct"]
    return _record(
        ec["n_true_positive_audits"],
        ec["n_true_positive_audits"] + ec["n_false_negative_audits"],
        float("nan") if value is None else value,
        window,
        construct_type="event_windowed_ratio", window_applied=True,
    )


# --- L: legitimacy / voluntary support --------------------------------------
def legitimacy_voluntary_support(rule_by_patch: dict, patch_system, window: tuple[int, int] | None = None) -> dict:
    """Fraction of each active rule's *eligible* local population
    (everyone currently resident on that rule's patch) that is a
    voluntary member. Never conditioned on compliance or sanction
    history — this is about membership itself, not obedience.
    ``institution_imposed_mode`` runs (Level 1.0 Stage-4 condition 7) are
    not specially excluded here — a fully-imposed rule's members were
    never given a join decision, so this dimension will (correctly, by
    construction) read as maximal "support" for an imposed rule; that is
    a disclosed limitation of measuring support via membership fraction
    alone, not a claim that imposition equals legitimacy.

    **Work Package F audit**: pure current-state snapshot.
    ``rule.n_members``/patch membership are live counts on mutable
    objects with no per-step history here; ``window`` is accepted for
    API uniformity and has no effect on the computed value. Take
    repeated snapshots and use ``temporal_features.py`` for a windowed
    view (see module docstring)."""
    total_members = 0
    total_eligible = 0
    for pid, rule in rule_by_patch.items():
        if not rule.active:
            continue
        total_members += rule.n_members
        if patch_system is not None and pid in patch_system.patches:
            total_eligible += len(patch_system.patches[pid].members)
        else:
            total_eligible += rule.n_members
    return _record(total_members, total_eligible, _safe_ratio(total_members, total_eligible), window,
                    construct_type="snapshot_current_state_ratio", window_applied=False)


# --- D: concentration of delegated authority ---------------------------------
def concentration_of_delegated_authority(
    rule_by_patch: dict, delegate_registry: dict, coordination_components: dict, window: tuple[int, int] | None = None
) -> dict:
    """Within each coordination-network jurisdiction (Work Package F;
    a lone un-linked patch is its own trivial jurisdiction of size 1),
    the single most-active delegate's share of that jurisdiction's total
    realized task attempts. ``1.0`` for every trivial single-patch
    jurisdiction (only one delegate could possibly have acted) — reported
    as-is, not excluded, since Section 6 requires every dimension defined
    for every valid observation, not only the "interesting" cases.

    **Work Package F audit**: pure current-state snapshot. Both the
    active-rule filter and ``delegate.task_attempts`` (a running,
    never per-step-decomposed counter) reflect the registry's state as
    of the call, with no window filtering applied anywhere in this
    function."""
    from abm_governance.rules.scaling import jurisdiction_size_by_patch

    sizes = jurisdiction_size_by_patch(coordination_components)
    # Group rule_ids by jurisdiction root (patches sharing a jurisdiction
    # share the same size *value*, but may belong to different
    # jurisdictions of the same size -- group by frozenset membership,
    # not by size, to avoid conflating two same-sized-but-distinct
    # jurisdictions).
    root_of_patch: dict[int, int] = {}
    for root, comp in coordination_components.items():
        for pid in comp:
            root_of_patch[pid] = root

    groups: dict[int, list] = {}
    for pid, rule in rule_by_patch.items():
        if not rule.active:
            continue
        delegate = delegate_registry.get(rule.rule_id)
        root = root_of_patch.get(pid, pid)  # ungrouped patch is its own root
        groups.setdefault(root, []).append(delegate)

    shares = []
    for delegates in groups.values():
        totals = [sum(d.task_attempts.values()) for d in delegates if d is not None and d.active]
        total_activity = sum(totals)
        if total_activity <= 0:
            continue
        shares.append(max(totals) / total_activity)
    n = len(shares)
    mean_share = _safe_ratio(sum(shares), n) if n else float("nan")
    return _record(sum(shares) if shares else 0, n, mean_share, window,
                    construct_type="snapshot_current_state_ratio", window_applied=False)


# --- M: institutional-memory continuity --------------------------------------
def institutional_memory_continuity(rule_by_patch: dict, window: tuple[int, int] | None = None) -> dict:
    """Mean ``SharedRule.institutional_memory`` across active rules
    (already a ``[0, 1]`` realized-retention scalar — Level 1.1's own
    definition, unchanged; see ``rules/shared_rule.py``).

    **Work Package F audit**: pure current-state snapshot.
    ``institutional_memory`` is a running scalar maintained on the rule
    object itself (no per-step record); ``window`` has no effect here."""
    active = [r for r in rule_by_patch.values() if r.active]
    total = sum(r.institutional_memory for r in active)
    n = len(active)
    return _record(total, n, _safe_ratio(total, n) if n else float("nan"), window,
                    construct_type="snapshot_current_state_ratio", window_applied=False)


# --- R: administrative / appropriation burden --------------------------------
def administrative_appropriation_burden(event_log: EventLog, patch_system, window: tuple[int, int] | None = None) -> dict:
    """Total realized administrative spending plus total appropriated
    funds, as a fraction of the community's total current resources
    (``patch_system.total_resources``) — a burden measure, deliberately
    including appropriation (a cost imposed by discretion misconduct, not
    an achievement) alongside ordinary administrative spending, per
    Section 6's "include costs ... not just achievements" requirement.

    **Work Package F audit finding**: this is a MIXED, flow-over-stock
    construct. The numerator (admin spending + appropriations) is a
    genuine windowed FLOW -- summed only over events whose step falls
    in ``window``. The denominator (``patch_system.total_resources``)
    is an unwindowed current-state STOCK, queried as of the call, not
    as of ``window``'s end. Passing an early-run ``window`` against a
    late-run ``patch_system`` snapshot (e.g. because the caller only
    kept one ``PatchSystem`` reference) would silently divide an early
    burden by a late (or early, or whatever "current" happens to mean
    to the caller) total -- a genuine misuse risk. Not changed here
    (the ratio's existing numeric definition is relied on elsewhere and
    is fine when ``patch_system`` reflects ``window``'s end, which is
    how every current caller in fact uses it); disclosed and made
    machine-checkable via ``construct_type``/``window_applied`` instead."""
    admin = sum(e.amount for e in event_log.administrative_spending if _in_range(e.step, window))
    approp = sum(e.amount for e in event_log.appropriations if _in_range(e.step, window))
    total_burden = admin + approp
    denom = patch_system.total_resources if patch_system is not None else None
    return _record(total_burden, denom, _safe_ratio(total_burden, denom) if denom else float("nan"), window,
                    construct_type="windowed_flow_numerator_over_snapshot_stock_denominator", window_applied="partial")


# --- S: institutional scale / coordination reach -----------------------------
def institutional_scale_reach(coordination_components: dict, n_patches: int, window: tuple[int, int] | None = None) -> dict:
    """Largest jurisdiction's patch count as a fraction of the
    community's total patch count — ``0`` (not ``NaN``: this is a
    well-defined absence, not missing data) when no coordination network
    exists at all.

    **Work Package F audit**: pure current-state snapshot of the
    coordination network topology; ``window`` has no effect here."""
    sizes = [len(comp) for comp in coordination_components.values()]
    largest = max(sizes) if sizes else 0
    return _record(largest, n_patches, _safe_ratio(largest, n_patches) if n_patches else float("nan"), window,
                    construct_type="snapshot_current_state_ratio", window_applied=False)


# --- F: amendment flexibility / functional recovery --------------------------
def amendment_flexibility(rule_by_patch: dict, current_step: int, window: tuple[int, int] | None = None) -> dict:
    """Amendments per unit institutional age, summed across active
    rules. **Disclosed reduction**: the "functional recovery" half of
    Work Package A's ``F`` label is not merged in here — post-shock
    functional recovery time is reported separately by Stage 7's own
    perturbation analysis (Section 12), which has the shock-timing
    context this module does not. This function reports amendment
    flexibility only; treat it as one component of ``F``, not the
    complete dimension, until Stage 7 runs.

    **Work Package F audit finding**: pure current-state snapshot, and
    the two parameters interact in a way worth flagging separately from
    the other snapshot dimensions. Both ``r.amendment_count`` (a
    running lifetime total, never reset) and ``total_age`` (computed
    from ``current_step``, NOT from ``window``) ignore ``window``
    entirely. If a caller passes both an explicit ``current_step`` and
    a ``window`` that ends somewhere other than ``current_step``, age
    is computed as of ``current_step`` regardless -- ``window`` is
    accepted and echoed back in the record but never consulted. Not
    changed here (every current caller passes ``current_step`` equal
    to the run's latest step and either omits ``window`` or passes one
    ending there, so no numeric drift has actually occurred); disclosed
    via ``construct_type``/``window_applied`` so a future caller who
    breaks that invariant gets a machine-checkable signal rather than a
    silently wrong number."""
    active = [r for r in rule_by_patch.values() if r.active]
    total_amendments = sum(r.amendment_count for r in active)
    total_age = sum(max(1, current_step - r.founding_step) for r in active)
    return _record(total_amendments, total_age, _safe_ratio(total_amendments, total_age), window,
                    construct_type="snapshot_current_state_ratio_current_step_not_window", window_applied=False)


# --- V: ecological / demographic viability -----------------------------------
def ecological_demographic_viability(
    institution_registry: dict, rule_by_patch: dict, patch_system, initial_population: int,
    window: tuple[int, int] | None = None,
) -> dict:
    """Two raw sub-parts, reported separately (never pre-merged) before
    this function's own ``value`` averages them: ecological (mean
    resource fraction across patches jurisdictions of surviving
    institutions occupy) and demographic (current total membership
    across active rules as a fraction of the initial population —
    includes agents who died, migrated away, or exited; a genuine
    depletion signal, not just "achievement").

    **Work Package F audit**: pure current-state snapshot for both
    sub-parts (``patch.fraction_of_capacity`` and current active
    membership); ``window`` has no effect on either."""
    eco_fractions = []
    for rec in institution_registry.values():
        if rec.extinct:
            continue
        for pid in rec.active_jurisdiction:
            if patch_system is not None and pid in patch_system.patches:
                eco_fractions.append(patch_system.patches[pid].fraction_of_capacity)
    demo_members = sum(r.n_members for r in rule_by_patch.values() if r.active)
    ecological = (sum(eco_fractions) / len(eco_fractions)) if eco_fractions else float("nan")
    demographic = _safe_ratio(demo_members, initial_population) if initial_population else float("nan")
    value = float("nan")
    parts = [p for p in (ecological, demographic) if p == p]  # filter NaN
    if parts:
        value = sum(parts) / len(parts)
    return {
        "ecological": _record(sum(eco_fractions) if eco_fractions else 0, len(eco_fractions), ecological, window,
                               construct_type="snapshot_current_state_ratio", window_applied=False),
        "demographic": _record(demo_members, initial_population, demographic, window,
                                construct_type="snapshot_current_state_ratio", window_applied=False),
        "value": value,
        "window": window,
    }


# --- H: heterogeneity across patches within the same community --------------
def within_community_heterogeneity(institution_registry: dict, window: tuple[int, int] | None = None) -> dict:
    """Mean pairwise ``structural_distance`` (Work Package A) across
    every currently-active institution's component bundle — reuses the
    already-built, deliberately-separate distance metric rather than
    inventing a second one. ``NaN`` when fewer than two active
    institutions exist (heterogeneity is undefined for a single
    institution, not zero).

    **Work Package F audit**: pure current-state snapshot of the
    institution registry's non-extinct entries; ``window`` has no
    effect here."""
    active = [rec for rec in institution_registry.values() if not rec.extinct]
    if len(active) < 2:
        return _record(0, 0, float("nan"), window,
                        construct_type="snapshot_current_state_ratio", window_applied=False)
    distances = [structural_distance(a.components, b.components) for a, b in itertools.combinations(active, 2)]
    n = len(distances)
    return _record(sum(distances), n, sum(distances) / n, window,
                    construct_type="snapshot_current_state_ratio", window_applied=False)


def institutional_phenotype_vector(
    event_log: EventLog,
    rule_by_patch: dict,
    institution_registry: dict,
    delegate_registry: dict,
    patch_system,
    coordination_components: dict,
    n_patches: int,
    initial_population: int,
    current_step: int,
    window: tuple[int, int] | None = None,
) -> dict:
    """The full preregistered X = (C, E, L, D, M, R, S, F, V, H) vector,
    each dimension as its own top-level key holding a raw record (or, for
    V, a small dict of raw sub-records) — never combined into a single
    score anywhere in this function."""
    return {
        "C": realized_administrative_capacity(delegate_registry, window),
        "E": effective_constraint_dimension(event_log, window),
        "L": legitimacy_voluntary_support(rule_by_patch, patch_system, window),
        "D": concentration_of_delegated_authority(rule_by_patch, delegate_registry, coordination_components, window),
        "M": institutional_memory_continuity(rule_by_patch, window),
        "R": administrative_appropriation_burden(event_log, patch_system, window),
        "S": institutional_scale_reach(coordination_components, n_patches, window),
        "F": amendment_flexibility(rule_by_patch, current_step, window),
        "V": ecological_demographic_viability(institution_registry, rule_by_patch, patch_system, initial_population, window),
        "H": within_community_heterogeneity(institution_registry, window),
    }
