"""Level 1.2, Section 11: inheritance vs. convergence tests.

A recurrent phenotype cluster (Section 10) can arise two structurally
different ways, and this milestone must not conflate them:

- **Inheritance**: the cluster is mostly one lineage's copies, produced
  by Work Package C's component transmission propagating one successful
  configuration across patches/agents. Recurrence here reflects
  *replication of a single historical event*, not independent discovery.
- **Convergence**: the cluster's members arose from genuinely
  independent lineages (little to no shared ancestry, little to no
  direct transmission linkage between them) and still landed on similar
  components/observed phenotype. Recurrence here reflects the same
  region of institution-space being reachable from multiple independent
  starting points -- the stronger form of evidence Section 10/11
  together are designed to surface.

Nothing in this module reads or is informed by any SEM/dissertation
label. `lineage_distance` and lineage bookkeeping are reused directly
from :mod:`abm_governance.rules.institution` rather than re-derived.

**Level 1.2b, Work Package H (Section 13) audit finding and fix,
disclosed here.** ``rule_lineage_id`` is allocated from a per-
``Simulation`` counter (``sim._rule_id_state["next_lineage_id"]``,
reset to ``0`` in every fresh ``Simulation.__init__``) -- it is
**unique only WITHIN one seed-run, never across seed-runs**. Section
15 makes the seed-run the primary independent observation, and Work
Package E's own discovery pool spans 576 separate seed-runs, so any
function in this module (or ``recurrence_criteria.independent_of_
single_lineage``, Criterion 12) that pools ``member_lineage_ids``
across MORE THAN ONE seed-run on the raw per-run integer would
silently and incorrectly treat "seed-run 3's lineage 0" and "seed-run
41's lineage 0" as the same lineage purely because both runs happened
to allocate a small integer starting from 0 -- a coincidental
collision, not evidence of shared ancestry. With typically only a
handful of lineages per run (bounded by ``n_patches``), this collision
is not a rare edge case; it is the EXPECTED common case once real
cross-run pooling begins. Left unfixed, this would silently corrupt
Criterion 12 and :func:`classify_convergence_or_inheritance` the
moment Section 15's discovery pipeline runs on cross-seed-run data --
found and fixed here, before that pipeline runs (Section 13's own
"save+hash before discovery" discipline applies with equal force to
catching this kind of bug before discovery, not just to freezing
thresholds).

**Fix**: :func:`compose_global_lineage_id` composes a
run-disambiguated key; every caller pooling ``member_lineage_ids``
across more than one seed-run MUST pass composed keys (not raw
``rule_lineage_id`` integers) to :func:`lineage_diversity_within_
cluster`, :func:`independent_origin_permutation_test`, and
``recurrence_criteria.independent_of_single_lineage``. This is a
calling-convention fix, not a signature change (both take a plain
``list`` already, content-agnostic) -- disclosed here, exercised by
``tests/test_level12b_recurrence_criteria_audit.py``'s collision
regression test, and additionally operationalized directly by
:func:`within_run_lineage_relatedness` below, which explicitly
reports the "within-run lineage" similarity level (Work Package H's
own required distinction) as its own quantity rather than leaving it
implicit in how the pooled-diversity functions are called."""

from __future__ import annotations

import numpy as np

#: Closed vocabulary for :func:`classify_convergence_or_inheritance`
#: (Section 11's own output must be one of these, never something
#: invented ad hoc downstream).
CONVERGENCE_CLASSIFICATION_LABELS: tuple[str, ...] = (
    "insufficient_data", "inherited", "convergent", "ambiguous",
)


def compose_global_lineage_id(seed_run_id, local_lineage_id) -> str:
    """Run-disambiguated composite key: ``rule_lineage_id`` is only
    unique within one seed-run (see module docstring). Any function
    that pools lineage identity across more than one seed-run must use
    this composed key, never the raw per-run integer, as its
    ``member_lineage_ids`` input -- prevents two different runs'
    coincidentally-identical small lineage integers from being
    (incorrectly) treated as the same lineage."""
    return f"{seed_run_id}:{local_lineage_id}"


def within_run_lineage_relatedness(member_seed_run_ids: list, member_lineage_ids: list) -> dict:
    """Work Package H (Section 13): explicitly operationalizes the
    "within-run lineage" similarity level, distinct from the pooled
    cross-run diversity :func:`lineage_diversity_within_cluster`
    reports. Restricted to member PAIRS drawn from the SAME seed-run
    (raw, per-run ``rule_lineage_id`` values are safe to compare
    directly here precisely because both sides of every compared pair
    share a seed-run, so no cross-run collision risk applies) --
    reports what fraction of those same-seed-run pairs also share a
    lineage id. Pairs drawn from different seed-runs are excluded from
    this computation entirely (that comparison belongs to the
    cross-run functions below, on composed keys); ``n_within_run_pairs
    == 0`` (no two members share a seed-run) is reported as ``NaN``,
    not a fabricated 0.0 or 1.0."""
    n = len(member_seed_run_ids)
    if n != len(member_lineage_ids) or n < 2:
        return {"fraction_within_run_pairs_same_lineage": float("nan"), "n_within_run_pairs": 0, "n_within_run_same_lineage_pairs": 0}
    n_within_run_pairs = 0
    n_same_lineage = 0
    for i in range(n):
        for j in range(i + 1, n):
            if member_seed_run_ids[i] == member_seed_run_ids[j]:
                n_within_run_pairs += 1
                if member_lineage_ids[i] == member_lineage_ids[j]:
                    n_same_lineage += 1
    fraction = (n_same_lineage / n_within_run_pairs) if n_within_run_pairs else float("nan")
    return {
        "fraction_within_run_pairs_same_lineage": fraction,
        "n_within_run_pairs": n_within_run_pairs,
        "n_within_run_same_lineage_pairs": n_same_lineage,
    }


def lineage_diversity_within_cluster(member_lineage_ids: list) -> dict:
    """Basic descriptive diversity of a candidate cluster's institutional
    lineages. ``simpson_diversity_index`` is ``1 - sum(p_i^2)`` (0.0 =
    every member shares one lineage; approaches 1.0 as members are
    spread evenly across many distinct lineages) -- a standard,
    unbiased-toward-any-count diversity measure, not something tuned for
    this milestone's expected trajectory count.

    **``member_lineage_ids`` MUST be composed via
    :func:`compose_global_lineage_id` whenever members are drawn from
    more than one seed-run** -- raw ``rule_lineage_id`` integers collide
    across runs (see module docstring); passing them uncomposed here
    would silently and incorrectly inflate apparent lineage sharing
    across seed-runs."""
    n = len(member_lineage_ids)
    if n == 0:
        return {"n_members": 0, "n_distinct_lineages": 0, "simpson_diversity_index": float("nan"), "dominant_lineage_fraction": float("nan")}
    ids, counts = np.unique(np.asarray(member_lineage_ids), return_counts=True)
    p = counts / n
    simpson = float(1.0 - np.sum(p ** 2))
    dominant_fraction = float(counts.max() / n)
    return {
        "n_members": n, "n_distinct_lineages": int(len(ids)),
        "simpson_diversity_index": simpson, "dominant_lineage_fraction": dominant_fraction,
    }


def independent_origin_permutation_test(
    member_lineage_ids: list, all_lineage_ids: list, n_permutations: int, rng: np.random.Generator,
) -> dict:
    """Null model: if cluster membership were unrelated to lineage, a
    random same-size subset of ``all_lineage_ids`` would show similar
    lineage diversity to the observed cluster. Draws ``n_permutations``
    random same-size subsets (without replacement, matching the
    observed cluster's size) from the full pool, computes each subset's
    Simpson diversity, and reports what fraction of the null draws are
    AT LEAST AS diverse as the observed cluster.

    A LOW fraction (most random draws are more diverse than the
    observed cluster) is evidence the cluster is more lineage-
    homogeneous than chance -- consistent with inheritance. A HIGH
    fraction (the observed cluster is about as diverse as, or more
    diverse than, typical random draws) is consistent with independent,
    convergent origins. This function reports the fraction and the full
    null distribution; it does not itself decide inherited-vs-convergent
    (see :func:`classify_convergence_or_inheritance`).

    **Both ``member_lineage_ids`` and ``all_lineage_ids`` MUST be
    composed via :func:`compose_global_lineage_id`** when the pool
    spans more than one seed-run, for the same collision reason as
    :func:`lineage_diversity_within_cluster`."""
    k = len(member_lineage_ids)
    pool = np.asarray(all_lineage_ids)
    if k == 0 or k > len(pool):
        return {"observed_diversity": float("nan"), "null_mean_diversity": float("nan"), "fraction_null_at_least_as_diverse": float("nan"), "n_permutations": 0}
    observed = lineage_diversity_within_cluster(member_lineage_ids)["simpson_diversity_index"]
    null_diversities = []
    for _ in range(n_permutations):
        draw = rng.choice(pool, size=k, replace=False)
        null_diversities.append(lineage_diversity_within_cluster(draw.tolist())["simpson_diversity_index"])
    null_diversities = np.array(null_diversities)
    fraction_at_least = float(np.mean(null_diversities >= observed)) if n_permutations else float("nan")
    return {
        "observed_diversity": observed,
        "null_mean_diversity": float(null_diversities.mean()) if n_permutations else float("nan"),
        "fraction_null_at_least_as_diverse": fraction_at_least,
        "n_permutations": n_permutations,
    }


def transmission_linked_fraction(member_institution_ids: list, transmission_events: list[dict]) -> dict:
    """Direct evidence of inheritance: what fraction of all possible
    member PAIRS are connected by at least one recorded component-
    transmission event between them (either direction) -- reusing
    ``InstitutionRecord.transmission_history``/``InstitutionComponent-
    TransmissionEvent`` provenance already recorded by Work Package C,
    never re-deriving transmission from component similarity (similar
    components without a recorded transmission event is exactly the
    convergence case this module exists to distinguish from inheritance).

    ``transmission_events``: list of dicts each with (at minimum)
    ``source_institution_id``/``target_institution_id`` keys."""
    members = set(member_institution_ids)
    n = len(members)
    if n < 2:
        return {"fraction_linked": float("nan"), "n_pairs": 0, "n_linked_pairs": 0}
    linked_pairs = set()
    for event in transmission_events:
        src, tgt = event.get("source_institution_id"), event.get("target_institution_id")
        if src in members and tgt in members and src != tgt:
            linked_pairs.add(frozenset((src, tgt)))
    n_pairs = n * (n - 1) // 2
    return {
        "fraction_linked": float(len(linked_pairs) / n_pairs) if n_pairs else float("nan"),
        "n_pairs": n_pairs, "n_linked_pairs": len(linked_pairs),
    }


def cross_condition_recurrence(member_conditions: list, min_distinct_conditions: int = 2) -> dict:
    """Does the candidate recur across more than one distinct generative
    parameter condition -- convergent selection toward the same
    phenotype region is expected to be somewhat condition-robust,
    whereas a single-historical-accident-plus-inheritance story can
    remain confined to whatever condition that one accident occurred
    under. This is deliberately the same computation as
    ``recurrence_criteria.parameter_condition_diversity`` (Criterion 8)
    -- re-exposed here under Section 11's own framing rather than
    re-implemented, since Section 10 and Section 11 evidence must stay
    numerically consistent with each other for the same candidate."""
    value = len(set(member_conditions))
    return {"passed": value >= min_distinct_conditions, "value": value, "threshold": min_distinct_conditions}


def classify_convergence_or_inheritance(
    diversity_result: dict, permutation_result: dict, transmission_result: dict, condition_result: dict,
    *,
    min_members_for_classification: int = 5,
    inherited_dominant_fraction: float = 0.6,
    inherited_transmission_linked_fraction: float = 0.5,
    convergent_min_fraction_null_at_least_as_diverse: float = 0.3,
) -> dict:
    """First-match-wins, closed-vocabulary classification (the same
    discipline as ``institutional_viability.classify_all_outcome`` and
    ``regulation_diagnostics.classify_regime``), applied per candidate
    cluster:

    1. ``insufficient_data`` -- fewer than ``min_members_for_classification``
       members, or any required input is undefined (``nan``); checked
       first because none of the other three labels are meaningful
       without enough evidence to support them.
    2. ``inherited`` -- either a single lineage dominates the cluster
       (``dominant_lineage_fraction >= inherited_dominant_fraction``) or
       a majority of member pairs are directly transmission-linked
       (``fraction_linked >= inherited_transmission_linked_fraction``);
       checked before ``convergent`` since direct provenance evidence is
       more specific and should override a merely-permissive diversity
       reading.
    3. ``convergent`` -- lineage diversity is not below-chance
       (``fraction_null_at_least_as_diverse >=
       convergent_min_fraction_null_at_least_as_diverse``), transmission
       linkage is low, AND the cluster recurs across more than one
       parameter condition (``condition_result["passed"]``) -- all three
       must hold; convergence is the more demanding claim and is never
       assigned on diversity alone.
    4. ``ambiguous`` -- the explicit fallback when neither bar is
       clearly met; never forced into either substantive label."""
    n_members = diversity_result.get("n_members", 0)
    required_defined = [
        diversity_result.get("dominant_lineage_fraction"),
        permutation_result.get("fraction_null_at_least_as_diverse"),
    ]
    if n_members < min_members_for_classification or any(v is None or v != v for v in required_defined):
        return {"label": "insufficient_data", "reasons": ["too_few_members_or_undefined_inputs"]}

    dominant_fraction = diversity_result["dominant_lineage_fraction"]
    fraction_linked = transmission_result.get("fraction_linked", float("nan"))
    fraction_null_at_least = permutation_result["fraction_null_at_least_as_diverse"]

    if dominant_fraction >= inherited_dominant_fraction or (fraction_linked == fraction_linked and fraction_linked >= inherited_transmission_linked_fraction):
        reasons = []
        if dominant_fraction >= inherited_dominant_fraction:
            reasons.append(f"single_lineage_dominant ({dominant_fraction:.2f} >= {inherited_dominant_fraction})")
        if fraction_linked == fraction_linked and fraction_linked >= inherited_transmission_linked_fraction:
            reasons.append(f"majority_pairs_transmission_linked ({fraction_linked:.2f} >= {inherited_transmission_linked_fraction})")
        return {"label": "inherited", "reasons": reasons}

    if (
        fraction_null_at_least >= convergent_min_fraction_null_at_least_as_diverse
        and (fraction_linked != fraction_linked or fraction_linked < inherited_transmission_linked_fraction)
        and condition_result.get("passed", False)
    ):
        return {
            "label": "convergent",
            "reasons": [
                f"diversity_not_below_chance ({fraction_null_at_least:.2f} >= {convergent_min_fraction_null_at_least_as_diverse})",
                "low_transmission_linkage",
                f"recurs_across_conditions ({condition_result.get('value')})",
            ],
        }

    return {"label": "ambiguous", "reasons": ["neither_inheritance_nor_convergence_bar_clearly_met"]}
