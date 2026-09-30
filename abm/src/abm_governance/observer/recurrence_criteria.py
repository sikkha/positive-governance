"""Level 1.2, Section 10: recurrence criteria for blind-discovery clusters.

A cluster produced by :mod:`abm_governance.observer.phenotype_discovery`
is a *candidate* recurrent institutional configuration, nothing more,
until it is evaluated against this module's minimum criteria. **None of
the twelve criteria below references cluster count, cluster identity,
or any dissertation trajectory** — every threshold is a data-quality or
robustness bar that would apply identically whether the candidate set
under evaluation had one cluster or twelve (Section 3's "no fixing or
tuning clustering toward exactly 3 clusters" prohibition applies with
equal force here: nothing here privileges producing exactly 3 survivors
of this filter, and a milestone run may end with 0, 1, 2, 5, or any
other number of criteria-passing candidates).

Each criterion function takes the minimum data it needs, returns a
small dict of the form ``{"passed": bool, "value": ..., "threshold":
...}`` (never a bare bool — the numeric value behind every verdict is
always exported, so a borderline call is always auditable), and never
silently substitutes a default that would flip the result. The
top-level :func:`evaluate_recurrence_criteria` runs all twelve against
one candidate cluster's supporting data and returns the full breakdown
— which criteria passed and which did not — never collapsing to a
single "recurrent: yes/no" bit without the underlying evidence attached.

**"Minimum criteria" here means a conjunction**: Section 10 describes
these as the minimum bar a candidate must clear, not a majority-vote
scorecard (contrast with Section 9.3's "no single metric decides",
which is about *choosing a clustering solution*, a different question
from *whether an already-chosen cluster recurs*). Downstream code may
still choose to report partial-pass candidates explicitly (a candidate
passing 10/12 is more informative reported than hidden), which is why
every function here returns the granular per-criterion result rather
than short-circuiting on the first failure."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import adjusted_rand_score

#: Level 1.2b, Work Package "Configuration presets" (Section 24): a
#: version tag for the FROZEN twelve-criterion recurrence bar this
#: module implements (``RECURRENCE_CRITERIA_NAMES`` below). Bump this
#: string if a criterion is ever added, removed, redefined, or has its
#: threshold semantics changed, so a result manifest can be mechanically
#: checked against the exact criteria set that evaluated it. Unchanged
#: since Level 1.2's own Section 10 introduced this module.
RECURRENCE_CRITERIA_VERSION = "recurrence_criteria_v1"

#: The closed, twelve-item list this module implements (Section 10's
#: "minimum criteria"). Order here is documentation order, not decision
#: order -- :func:`evaluate_recurrence_criteria` runs all twelve
#: unconditionally and does not short-circuit.
RECURRENCE_CRITERIA_NAMES: tuple[str, ...] = (
    "minimum_cluster_size",
    "cross_seed_recurrence",
    "cross_algorithm_support",
    "bootstrap_stability",
    "co_assignment_internal_consistency",
    "distinctness_from_noise",
    "missingness_strategy_robustness",
    "parameter_condition_diversity",
    "temporal_persistence_of_members",
    "non_degenerate_cluster_fraction",
    "k_selection_non_privileged_support",
    "independent_of_single_lineage",
)


def minimum_cluster_size(member_indices: list, min_size: int = 5) -> dict:
    """Criterion 1: raw member count. A candidate with too few members
    cannot support any of the other eleven criteria meaningfully."""
    value = len(member_indices)
    return {"passed": value >= min_size, "value": value, "threshold": min_size}


def cross_seed_recurrence(member_seed_ids: list, min_distinct_seeds: int = 2) -> dict:
    """Criterion 2: the candidate must be observed across more than one
    independent seed-run (Section 15's "seed-run is the primary
    independent observation") -- a cluster entirely contained within one
    simulation run is not yet evidence of *recurrence*."""
    value = len(set(member_seed_ids))
    return {"passed": value >= min_distinct_seeds, "value": value, "threshold": min_distinct_seeds}


def cross_algorithm_support(
    member_indices: list, primary_labels: np.ndarray, other_labels_by_method: dict[str, np.ndarray],
    min_ari: float = 0.3,
) -> dict:
    """Criterion 3: for at least one *other* candidate method, restrict
    both label vectors to this candidate's own member rows and require
    non-trivial agreement (ARI) with whichever cluster those members
    fall into under the other method. Never requires literal identical
    cluster boundaries -- only that some other algorithm's partition of
    these same points is not essentially unrelated."""
    member_indices = np.asarray(member_indices)
    best_ari = float("-inf")
    per_method = {}
    for method, other in other_labels_by_method.items():
        other = np.asarray(other)
        sub_primary = np.asarray(primary_labels)[member_indices]
        sub_other = other[member_indices]
        try:
            ari = float(adjusted_rand_score(sub_primary, sub_other))
        except ValueError:
            ari = float("nan")
        per_method[method] = ari
        if ari == ari and ari > best_ari:
            best_ari = ari
    if best_ari == float("-inf"):
        best_ari = float("nan")
    passed = best_ari == best_ari and best_ari >= min_ari
    return {"passed": passed, "value": best_ari, "threshold": min_ari, "per_method": per_method}


def bootstrap_stability_criterion(stability_result: dict, min_mean_ari: float = 0.5) -> dict:
    """Criterion 4: wraps ``phenotype_discovery.bootstrap_stability``'s
    own output -- passed when the mean ARI across bootstrap resamples of
    the *whole* fit meets the bar. A candidate cluster inherits this
    global-fit stability score rather than a per-cluster one, since
    bootstrap resampling perturbs cluster boundaries jointly."""
    value = stability_result.get("mean_ari", float("nan"))
    return {"passed": value == value and value >= min_mean_ari, "value": value, "threshold": min_mean_ari}


def co_assignment_internal_consistency(
    member_indices: list, co_assignment: np.ndarray, min_mean_co_assignment: float = 0.5,
) -> dict:
    """Criterion 5: mean pairwise co-assignment probability (Section
    9.4's consensus matrix) among the candidate's own members, off-
    diagonal only -- a single-member cluster has no off-diagonal pairs
    and is reported as ``value: nan`` (undefined, not a forced pass or
    fail; ``minimum_cluster_size`` is the criterion responsible for
    excluding degenerate single-member candidates)."""
    idx = np.asarray(member_indices)
    if len(idx) < 2:
        return {"passed": False, "value": float("nan"), "threshold": min_mean_co_assignment}
    sub = co_assignment[np.ix_(idx, idx)]
    off_diag = sub[~np.eye(len(idx), dtype=bool)]
    value = float(off_diag.mean()) if off_diag.size else float("nan")
    return {"passed": value == value and value >= min_mean_co_assignment, "value": value, "threshold": min_mean_co_assignment}


def distinctness_from_noise(member_indices: list, noise_indices: list, X: np.ndarray, min_margin: float = 0.0) -> dict:
    """Criterion 6: mean within-cluster pairwise Euclidean distance must
    be smaller than the mean distance from cluster members to unclassified
    /noise points, by at least ``min_margin`` -- guards against a
    candidate that is really indistinguishable from "everything not
    obviously noise." Undefined (``nan``, not forced) when there are no
    noise points to compare against or fewer than 2 cluster members."""
    idx = np.asarray(member_indices)
    if len(idx) < 2 or len(noise_indices) == 0:
        return {"passed": False, "value": float("nan"), "threshold": min_margin}
    within = X[idx]
    noise = X[np.asarray(noise_indices)]
    within_d = np.linalg.norm(within[:, None, :] - within[None, :, :], axis=-1)
    within_mean = within_d[~np.eye(len(idx), dtype=bool)].mean() if len(idx) > 1 else float("nan")
    cross_d = np.linalg.norm(within[:, None, :] - noise[None, :, :], axis=-1)
    cross_mean = float(cross_d.mean())
    margin = float(cross_mean - within_mean)
    return {"passed": margin >= min_margin, "value": margin, "threshold": min_margin, "within_mean": float(within_mean), "noise_mean": cross_mean}


def missingness_strategy_robustness(
    member_indices: list, primary_labels: np.ndarray, labels_by_strategy: dict[str, np.ndarray], min_ari: float = 0.3,
) -> dict:
    """Criterion 7: the candidate's member rows should not fall apart
    under an alternative missingness-handling strategy (Section 9.1's
    three strategies) -- at least one alternative strategy's labeling of
    these same rows must show non-trivial ARI agreement with the primary
    labeling. A candidate supported only under one specific missingness
    choice is a preprocessing artifact, not a recurrence finding."""
    idx = np.asarray(member_indices)
    best = float("-inf")
    per_strategy = {}
    for strategy, other in labels_by_strategy.items():
        other = np.asarray(other)
        try:
            ari = float(adjusted_rand_score(np.asarray(primary_labels)[idx], other[idx]))
        except ValueError:
            ari = float("nan")
        per_strategy[strategy] = ari
        if ari == ari and ari > best:
            best = ari
    if best == float("-inf"):
        best = float("nan")
    return {"passed": best == best and best >= min_ari, "value": best, "threshold": min_ari, "per_strategy": per_strategy}


def parameter_condition_diversity(member_conditions: list, min_distinct_conditions: int = 2) -> dict:
    """Criterion 8: candidate members must be drawn from more than one
    distinct generative parameter condition (e.g. distinct Stage-3
    parameter draws or Stage-6 scale/init conditions) -- a cluster that
    only ever appears under one specific parameter setting is evidence
    of a parameter-region-specific outcome, not a recurrent phenotype in
    the Section-10 sense."""
    value = len(set(member_conditions))
    return {"passed": value >= min_distinct_conditions, "value": value, "threshold": min_distinct_conditions}


def temporal_persistence_of_members(member_eligibility_results: list[dict], min_fraction_eligible: float = 0.5) -> dict:
    """Criterion 9: the fraction of candidate members whose own run was
    ``sustained_system_eligibility``-eligible (Section 8B) must clear a
    bar -- a phenotype recurring only among runs too short or too
    corrupted to trust is not yet a persistence finding."""
    if not member_eligibility_results:
        return {"passed": False, "value": float("nan"), "threshold": min_fraction_eligible}
    n_eligible = sum(1 for r in member_eligibility_results if r.get("eligible"))
    value = n_eligible / len(member_eligibility_results)
    return {"passed": value >= min_fraction_eligible, "value": value, "threshold": min_fraction_eligible}


def non_degenerate_cluster_fraction(member_indices: list, n_total: int, min_fraction: float = 0.02, max_fraction: float = 0.95) -> dict:
    """Criterion 10: the candidate must be neither a vanishing minority
    (too small a fraction of the pooled sample to generalize from,
    distinct from the raw-count floor in criterion 1) nor essentially
    the whole sample (a cluster that swallows nearly everything is not
    informative as a *distinct* recurrent configuration)."""
    value = len(member_indices) / n_total if n_total else float("nan")
    passed = value == value and min_fraction <= value <= max_fraction
    return {"passed": passed, "value": value, "threshold": [min_fraction, max_fraction]}


def k_selection_non_privileged_support(k: int, metrics_by_k: list[dict]) -> dict:
    """Criterion 11: the candidate's own ``k`` must have *some* defined
    (non-NaN) model-selection metric among those computed across the
    full evaluated ``k`` range, and must not be uniquely the single
    worst-scoring silhouette among evaluated k's with a defined
    silhouette -- a minimal, deliberately loose "not obviously
    contraindicated" bar (Section 9.3 forbids any single metric from
    *deciding*; this criterion does not attempt to have model-selection
    metrics decide recurrence either -- it only excludes candidates
    whose own k a wide reading of the evidence actively contradicts)."""
    entry = next((m for m in metrics_by_k if m.get("k") == k), None)
    if entry is None:
        return {"passed": False, "value": None, "threshold": "k present in evaluated range"}
    sil = entry.get("metrics", {}).get("silhouette", float("nan"))
    defined_silhouettes = [
        (m.get("k"), m.get("metrics", {}).get("silhouette", float("nan")))
        for m in metrics_by_k if m.get("metrics", {}).get("silhouette", float("nan")) == m.get("metrics", {}).get("silhouette", float("nan"))
    ]
    if sil != sil:
        # This k's own silhouette is undefined (e.g. k=1) -- neither
        # contradicted nor supported by this particular metric; treated
        # as passing (undefined is not "actively contraindicated").
        return {"passed": True, "value": None, "threshold": "silhouette undefined for k=1 or degenerate fits"}
    if len(defined_silhouettes) <= 1:
        return {"passed": True, "value": sil, "threshold": "only one k has a defined silhouette"}
    worst_k, worst_val = min(defined_silhouettes, key=lambda t: t[1])
    passed = not (worst_k == k and sum(1 for _, v in defined_silhouettes if v == worst_val) == 1)
    return {"passed": passed, "value": sil, "threshold": "not uniquely worst defined silhouette"}


def independent_of_single_lineage(member_lineage_ids: list, max_single_lineage_fraction: float = 0.7) -> dict:
    """Criterion 12: no single institutional lineage may account for
    more than ``max_single_lineage_fraction`` of a candidate's members
    -- a cluster that is mostly one lineage's copies (propagated via
    Work Package C transmission) is evidence of *inheritance*, not
    independent recurrence (this is the direct link to Section 11's
    convergence-vs-inheritance distinction; see
    :mod:`abm_governance.observer.convergence_tests` for the fuller
    analysis this criterion only screens for).

    **Work Package H (Section 13) audit finding**: when a candidate's
    members are drawn from more than one seed-run (the expected case --
    Section 15's own "seed-run is the primary independent observation"),
    ``member_lineage_ids`` MUST be composed via
    ``convergence_tests.compose_global_lineage_id`` before being passed
    here. Raw ``rule_lineage_id`` integers are unique only within one
    seed-run (each ``Simulation`` resets its own lineage counter to
    ``0``); pooling raw integers across runs would silently and
    incorrectly count two different runs' coincidentally-identical
    small lineage numbers as the same lineage, corrupting this
    criterion's verdict. See ``convergence_tests.py``'s module
    docstring for the full disclosure."""
    if not member_lineage_ids:
        return {"passed": False, "value": float("nan"), "threshold": max_single_lineage_fraction}
    ids, counts = np.unique(np.asarray(member_lineage_ids), return_counts=True)
    value = float(counts.max() / counts.sum())
    return {"passed": value <= max_single_lineage_fraction, "value": value, "threshold": max_single_lineage_fraction}


def evaluate_recurrence_criteria(cluster_data: dict, thresholds: dict | None = None) -> dict:
    """Runs all twelve criteria against one candidate cluster's
    supporting data and returns the full, unabridged breakdown.

    ``cluster_data`` keys (all required; a missing key is a caller bug,
    not silently defaulted, since silently treating missing evidence as
    a criterion pass or fail would misrepresent what was actually
    checked):

    ``member_indices``, ``member_seed_ids``, ``primary_labels``,
    ``other_labels_by_method``, ``bootstrap_stability_result``,
    ``co_assignment``, ``noise_indices``, ``X``, ``labels_by_strategy``,
    ``member_conditions``, ``member_eligibility_results``, ``n_total``,
    ``k``, ``metrics_by_k``, ``member_lineage_ids``.

    ``thresholds``: optional dict of per-criterion keyword overrides,
    e.g. ``{"minimum_cluster_size": {"min_size": 10}}``. Every default
    threshold is otherwise as documented on each criterion function
    above -- none reference or were tuned toward any particular cluster
    count."""
    thresholds = thresholds or {}

    def _kw(name):
        return thresholds.get(name, {})

    results = {
        "minimum_cluster_size": minimum_cluster_size(cluster_data["member_indices"], **_kw("minimum_cluster_size")),
        "cross_seed_recurrence": cross_seed_recurrence(cluster_data["member_seed_ids"], **_kw("cross_seed_recurrence")),
        "cross_algorithm_support": cross_algorithm_support(
            cluster_data["member_indices"], cluster_data["primary_labels"], cluster_data["other_labels_by_method"], **_kw("cross_algorithm_support"),
        ),
        "bootstrap_stability": bootstrap_stability_criterion(cluster_data["bootstrap_stability_result"], **_kw("bootstrap_stability")),
        "co_assignment_internal_consistency": co_assignment_internal_consistency(
            cluster_data["member_indices"], cluster_data["co_assignment"], **_kw("co_assignment_internal_consistency"),
        ),
        "distinctness_from_noise": distinctness_from_noise(
            cluster_data["member_indices"], cluster_data["noise_indices"], cluster_data["X"], **_kw("distinctness_from_noise"),
        ),
        "missingness_strategy_robustness": missingness_strategy_robustness(
            cluster_data["member_indices"], cluster_data["primary_labels"], cluster_data["labels_by_strategy"], **_kw("missingness_strategy_robustness"),
        ),
        "parameter_condition_diversity": parameter_condition_diversity(cluster_data["member_conditions"], **_kw("parameter_condition_diversity")),
        "temporal_persistence_of_members": temporal_persistence_of_members(cluster_data["member_eligibility_results"], **_kw("temporal_persistence_of_members")),
        "non_degenerate_cluster_fraction": non_degenerate_cluster_fraction(cluster_data["member_indices"], cluster_data["n_total"], **_kw("non_degenerate_cluster_fraction")),
        "k_selection_non_privileged_support": k_selection_non_privileged_support(cluster_data["k"], cluster_data["metrics_by_k"]),
        "independent_of_single_lineage": independent_of_single_lineage(cluster_data["member_lineage_ids"], **_kw("independent_of_single_lineage")),
    }
    n_passed = sum(1 for r in results.values() if r["passed"])
    return {
        "criteria": results,
        "n_passed": n_passed,
        "n_total": len(RECURRENCE_CRITERIA_NAMES),
        "meets_all_minimum_criteria": n_passed == len(RECURRENCE_CRITERIA_NAMES),
    }
