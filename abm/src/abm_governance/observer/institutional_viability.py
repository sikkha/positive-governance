"""Level 1.2, Section 8: failure and viability classification.

**Deliberately distinctly named** from the pre-existing, unrelated
Level 0.2 module ``observer/viability.py`` (individual-agent
distressed/dormant/nonviable state machine — a different concept
entirely). No functional relationship between the two.

Two separate analyses, per Section 8:

(A) :func:`classify_all_outcome` — every run gets exactly one label from
a closed, exhaustive vocabulary (``collapse``, ``no_institution``,
``fragmented``, ``persistent_extractive``, ``transient``, ``viable``,
``unclassified``). First-match-wins decision order, explicitly
documented and audited (the same discipline
``observer/regulation_diagnostics.py::classify_regime`` established at
Level 0.3b) — ``unclassified`` is an explicit fallback, never forced.
**A possible fourth low-capacity/low-constraint failure region is not
removed just because the dissertation discusses three positive
trajectories** — ``collapse`` and ``persistent_extractive`` both exist
in this vocabulary as first-class, non-excluded outcomes.

(B) :func:`sustained_system_eligibility` — a preregistered, **non-
normative** eligibility screen (sufficient post-burn-in observations,
nonzero surviving population, valid measurements, minimum duration, no
terminal corruption). Never "matches a desired governance profile" —
every criterion here is about data quality/sufficiency, not about
whether the outcome looks like anything specific. Every exclusion
reason is reported explicitly (``reasons: [...]``), never silently
dropped.

Neither analysis assigns automatic normative meaning to any label —
"viable" here means "institutions persisted with defined, non-collapsed
ecological/demographic measurements," not "good governance.\""""

from __future__ import annotations

#: Section 8's closed all-outcome vocabulary. Order below is NOT the
#: decision order (see ``classify_all_outcome``'s own docstring for
#: that) — this tuple exists so downstream code can validate against a
#: closed set without hardcoding the list a second time.
ALL_OUTCOME_LABELS: tuple[str, ...] = (
    "no_institution", "collapse", "viable", "persistent_extractive",
    "fragmented", "transient", "unclassified",
)


def classify_all_outcome(
    n_institutions_ever_formed: int,
    n_institutions_active_at_end: int,
    population_alive_fraction: float,
    mean_ecological_resource_fraction: float,
    max_jurisdiction_size: int,
    *,
    collapse_population_threshold: float = 0.05,
    collapse_ecological_threshold: float = 0.05,
    viable_ecological_threshold: float = 0.3,
    viable_population_threshold: float = 0.3,
) -> str:
    """First-match-wins decision sequence (explicitly audited, mirroring
    ``regulation_diagnostics.classify_regime``'s own documented-order
    discipline):

    1. ``no_institution`` — no institution was ever formed at all
       (nothing else below is meaningful without at least one).
    2. ``collapse`` — population or ecological resources have collapsed
       by the end of the run (checked regardless of whether any
       institution is still nominally active — a formally "active" rule
       over a collapsed population/ecology is still a collapse).
    3. ``viable`` — at least one institution survives to the end with
       both ecological and demographic measurements above their
       respective thresholds.
    4. ``fragmented`` — more than one institution is still active, none
       reaches the ``viable`` bar, and no jurisdiction ever exceeded
       size 1 (never coordinated into anything beyond isolated
       single-patch institutions) — checked before
       ``persistent_extractive`` since fragmentation is the more
       specific, more informative label when both apply.
    5. ``persistent_extractive`` — at least one institution survives to
       the end but does not reach the ``viable`` bar (whichever
       component fell short — low ecological viability, low population,
       or both; "persistent despite low welfare," Work Package E's own
       explicitly permitted case) and the run is not ``fragmented``.
    6. ``transient`` — institutions existed at some point but none
       survives to the end, and neither population nor ecology has
       collapsed (the institutions themselves simply did not persist).
    7. ``unclassified`` — the explicit fallback; never forced."""
    if n_institutions_ever_formed <= 0:
        return "no_institution"
    if population_alive_fraction <= collapse_population_threshold or mean_ecological_resource_fraction <= collapse_ecological_threshold:
        return "collapse"
    if n_institutions_active_at_end > 0:
        if mean_ecological_resource_fraction >= viable_ecological_threshold and population_alive_fraction >= viable_population_threshold:
            return "viable"
        if n_institutions_active_at_end > 1 and max_jurisdiction_size <= 1:
            return "fragmented"
        return "persistent_extractive"
    if n_institutions_active_at_end == 0:
        return "transient"
    return "unclassified"  # pragma: no cover - explicit fallback, never mechanically reached by the branches above


def sustained_system_eligibility(
    n_post_burn_in_observations: int,
    surviving_population: int,
    phenotype_vector: dict,
    max_institution_duration: int,
    terminal_state_valid: bool,
    *,
    min_observations: int = 5,
    min_duration: int = 10,
) -> dict:
    """Preregistered, non-normative sustained-system eligibility screen.
    Every criterion is a data-sufficiency check, never a resemblance-to-
    any-particular-outcome check. Returns ``{"eligible": bool, "reasons":
    [...]}`` — ``reasons`` lists every criterion that failed (empty when
    eligible), so an exclusion is always auditable, never silent."""
    reasons = []
    if n_post_burn_in_observations < min_observations:
        reasons.append(f"insufficient_post_burn_in_observations ({n_post_burn_in_observations} < {min_observations})")
    if surviving_population <= 0:
        reasons.append("zero_surviving_population")
    if max_institution_duration < min_duration:
        reasons.append(f"below_minimum_duration ({max_institution_duration} < {min_duration})")
    if not terminal_state_valid:
        reasons.append("terminal_state_corrupted")
    n_defined = 0
    n_total = 0
    for dim, record in phenotype_vector.items():
        if dim == "V":
            for sub in ("ecological", "demographic"):
                n_total += 1
                v = record.get(sub, {}).get("value")
                if v is not None and v == v:
                    n_defined += 1
            continue
        n_total += 1
        v = record.get("value")
        if v is not None and v == v:
            n_defined += 1
    if n_total > 0 and n_defined == 0:
        reasons.append("no_valid_measurements")
    return {"eligible": len(reasons) == 0, "reasons": reasons}
