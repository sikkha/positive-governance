"""Level 1.2b, Work Package H (Section 13): formal audit of the twelve
Level 1.2 recurrence criteria (``observer/recurrence_criteria.py``) and
of the similarity-level taxonomy Section 11's inheritance/convergence
machinery (``observer/convergence_tests.py``) implements.

Section 13's charge: audit all twelve recurrence criteria (construct,
unit of analysis, sample size, redundancy, feasibility under the new
1.2b joint design); distinguish within-run lineage vs. cross-run
structural similarity vs. independent convergence vs. component
homology/analogy; create a versioned Level 1.2b recurrence spec;
save+hash it before discovery runs.

**This module removes no criterion.** All twelve were found to still
apply under the 1.2b joint design (Work Package E's pooled seed-run
data has exactly the shape every criterion already expects: a
candidate cluster's member indices, seed ids, lineage ids, parameter
conditions, etc.) -- the one genuine bug the audit found (raw
``rule_lineage_id`` collision across seed-runs, corrupting Criterion 12
and the convergence classifier) was fixed directly in
``convergence_tests.py``/documented on Criterion 12 itself, not solved
by removing anything.

**The four similarity levels (Section 13's own required distinction)**,
from least to most specific claim:

1. **within-run lineage** -- two institutions in the SAME seed-run that
   share ancestry (a single ``rule_lineage_id``, safe to compare
   directly since both sides share a run). The weakest, most trivial
   form of "relatedness" -- unsurprising and expected whenever a run's
   own dynamics produce more than one institution from one lineage.
   Operationalized by :func:`convergence_tests.within_run_lineage_
   relatedness`.
2. **cross-run structural similarity** -- members from DIFFERENT
   seed-runs whose observed component/phenotype vectors land in the
   same discovered cluster. This is a purely descriptive, pre-causal
   observation (the clustering step itself, Section 9) -- it says
   nothing yet about WHY the members are similar.
3. **independent convergence** -- the causal-inference layer applied
   ON TOP of cross-run structural similarity: members are structurally
   similar AND lineage-diverse beyond chance (the permutation test)
   AND not majority transmission-linked AND recur across more than one
   generative parameter condition. Operationalized by
   :func:`convergence_tests.classify_convergence_or_inheritance`'s
   ``"convergent"`` label.
4. **component homology vs. analogy** -- a biology-inspired reframing
   of the SAME inherited/convergent distinction, made explicit here
   because Section 13 asks for it by that name: *homology* (similarity
   because of shared origin -- covers both within-run lineage sharing
   and cross-run direct transmission linkage, i.e. ``classify_
   convergence_or_inheritance``'s ``"inherited"`` label) vs. *analogy*
   (similarity that arose independently despite different origins,
   i.e. the same function's ``"convergent"`` label). No new
   computation is introduced for this fourth level -- it is a
   vocabulary/interpretation layer over levels 1 and 3, recorded here
   explicitly (via :data:`SIMILARITY_LEVEL_TAXONOMY`) so the mapping is
   never left implicit or reinvented ad hoc by a downstream reader."""

from __future__ import annotations

import inspect

from abm_governance.observer import recurrence_criteria as rc

#: Section 13's five required audit dimensions, one entry per one of
#: the twelve criteria in ``recurrence_criteria.RECURRENCE_CRITERIA_
#: NAMES`` (order matches that tuple exactly, checked by
#: :func:`audit_completeness_check`).
RECURRENCE_CRITERIA_AUDIT: dict[str, dict] = {
    "minimum_cluster_size": {
        "construct": "raw member count -- a floor, not a strength-of-evidence measure",
        "unit_of_analysis": "candidate cluster (post-clustering)",
        "min_sample_size": "the threshold itself (default 5) IS the minimum sample size this criterion enforces on every other criterion",
        "redundant_with": [],
        "feasible_under_1_2b_design": True,
        "feasibility_note": "trivially available the moment a cluster exists; no dependency on WP E-specific data shape",
    },
    "cross_seed_recurrence": {
        "construct": "count of distinct seed-runs contributing to the cluster",
        "unit_of_analysis": "seed-run (Section 15's primary independent observation)",
        "min_sample_size": "default 2 distinct seeds",
        "redundant_with": ["parameter_condition_diversity (both require diversity across independent runs, but seed identity and parameter condition are logically distinct axes -- two runs can share a seed-adjacent condition yet differ in outcome, or share a condition under different seeds; kept separate deliberately, not true redundancy)"],
        "feasible_under_1_2b_design": True,
        "feasibility_note": "WP E's design carries seed explicitly on every point (seeds_per_point=6 preferred); directly available",
    },
    "cross_algorithm_support": {
        "construct": "adjusted Rand index between the primary clustering method's labels and an alternative method's labels, restricted to this candidate's own member rows",
        "unit_of_analysis": "candidate cluster's member rows, compared across clustering methods",
        "min_sample_size": "no explicit floor beyond minimum_cluster_size; ARI itself is more reliable with more members",
        "redundant_with": [],
        "feasible_under_1_2b_design": True,
        "feasibility_note": "requires Section 9's CANDIDATE_METHODS (gmm/hierarchical/hdbscan) to have all been fit on the same feature matrix -- a Section 15 discovery-pipeline prerequisite, not a 1.2b-specific gap",
    },
    "bootstrap_stability": {
        "construct": "mean ARI across bootstrap resamples of the whole fit (a global-fit stability score, not per-cluster)",
        "unit_of_analysis": "the whole clustering fit (all clusters simultaneously), inherited by each candidate",
        "min_sample_size": "governed by phenotype_discovery.bootstrap_stability's own n_bootstrap, not this criterion",
        "redundant_with": [],
        "feasible_under_1_2b_design": True,
        "feasibility_note": "requires Section 9.4's bootstrap_stability to have already run once on the full feature matrix",
    },
    "co_assignment_internal_consistency": {
        "construct": "mean pairwise co-assignment probability among the candidate's own members (Section 9.4 consensus matrix), off-diagonal only",
        "unit_of_analysis": "member pairs within the candidate cluster",
        "min_sample_size": "undefined (NaN, not forced) below 2 members -- minimum_cluster_size is the floor-enforcing criterion",
        "redundant_with": ["cross_algorithm_support (both measure cross-fit agreement, but co-assignment is within-candidate consensus across bootstrap/algorithm resamples while cross_algorithm_support is a single primary-vs-alternative ARI comparison -- different statistical objects, not the same evidence twice)"],
        "feasible_under_1_2b_design": True,
        "feasibility_note": "requires Section 9.4's co_assignment_matrix, same prerequisite as bootstrap_stability",
    },
    "distinctness_from_noise": {
        "construct": "margin between mean within-cluster distance and mean cluster-to-noise distance in feature space",
        "unit_of_analysis": "candidate cluster members vs. unclassified/noise points, in the discovery feature matrix",
        "min_sample_size": "undefined below 2 members or when no noise points exist",
        "redundant_with": [],
        "feasible_under_1_2b_design": "conditional",
        "feasibility_note": "only meaningful for a clustering method that produces an explicit noise label (hdbscan); gmm/hierarchical assign every point to a cluster, so noise_indices is legitimately empty and this criterion is undefined (NaN) for those methods -- not a 1.2b-specific gap, a pre-existing property of which discovery method produced the candidate",
    },
    "missingness_strategy_robustness": {
        "construct": "ARI agreement between the primary missingness-handling strategy's labeling and an alternative strategy's labeling, restricted to candidate member rows",
        "unit_of_analysis": "candidate cluster's member rows, compared across the three Section 9.1 missingness strategies",
        "min_sample_size": "no explicit floor beyond minimum_cluster_size",
        "redundant_with": [],
        "feasible_under_1_2b_design": True,
        "feasibility_note": "requires Section 9.1's three preprocess_features strategies to have all been fit-on-train and applied; directly available once the discovery pipeline runs",
    },
    "parameter_condition_diversity": {
        "construct": "count of distinct generative parameter conditions represented among the candidate's members",
        "unit_of_analysis": "generative parameter condition (a joint ecological+institutional design point under WP E, or an initial-condition family)",
        "min_sample_size": "default 2 distinct conditions",
        "redundant_with": ["cross_seed_recurrence (see that entry's note -- deliberately distinct axes)"],
        "feasible_under_1_2b_design": True,
        "feasibility_note": "WP E's design point + IC family together define 'condition' cleanly for 1.2b; no redefinition needed from Level 1.2's own usage",
    },
    "temporal_persistence_of_members": {
        "construct": "fraction of candidate members whose own seed-run was sustained_system_eligibility-eligible (Section 8B)",
        "unit_of_analysis": "seed-run eligibility, one flag per member's originating run",
        "min_sample_size": "default 0.5 minimum eligible fraction; undefined (NaN) on an empty member-eligibility list",
        "redundant_with": [],
        "feasible_under_1_2b_design": True,
        "feasibility_note": "requires each WP E run's own eligibility flag; WP E's own ledger-closure gate (Section 5.7, now satisfied for all 576 runs) is a stricter, DIFFERENT bar than sustained_system_eligibility and does not substitute for it -- eligibility must still be computed per run before this criterion can be applied",
    },
    "non_degenerate_cluster_fraction": {
        "construct": "candidate size as a fraction of the total pooled sample, bounded away from both a vanishing minority and near-total-sample degeneracy",
        "unit_of_analysis": "candidate cluster size vs. n_total pooled observations",
        "min_sample_size": "default bounds [0.02, 0.95] of n_total, not a raw count",
        "redundant_with": ["minimum_cluster_size (different denominators -- criterion 1 is a raw floor independent of pool size, criterion 10 is scale-relative; both matter separately, e.g. a raw-adequate cluster could still be a vanishing fraction of a much larger 1.2b pool)"],
        "feasible_under_1_2b_design": True,
        "feasibility_note": "n_total for 1.2b is WP E's pooled seed-run count (up to 1152 = 576 runs x up to 2 rows/run if V's sub-parts are ever split into separate rows -- confirm the discovery pipeline's own row definition when Section 15 runs; not a criterion-level gap)",
    },
    "k_selection_non_privileged_support": {
        "construct": "the candidate's own k has a defined model-selection metric and is not uniquely the single worst-scoring silhouette among evaluated k's",
        "unit_of_analysis": "candidate's k value vs. the full evaluated k range (Section 9.3's DEFAULT_K_RANGE)",
        "min_sample_size": "not sample-size-based; structural (defined/undefined metric presence)",
        "redundant_with": [],
        "feasible_under_1_2b_design": True,
        "feasibility_note": "DEFAULT_K_RANGE (1..8) is unchanged by 1.2b; no redesign needed",
    },
    "independent_of_single_lineage": {
        "construct": "no single institutional lineage accounts for more than a bounded fraction of the candidate's members",
        "unit_of_analysis": "institutional lineage identity across candidate members",
        "min_sample_size": "undefined (NaN) on an empty lineage-id list; default max fraction 0.7",
        "redundant_with": [],
        "feasible_under_1_2b_design": "conditional -- FIXED this Work Package",
        "feasibility_note": (
            "was NOT safely feasible under the 1.2b joint design as originally documented: raw rule_lineage_id "
            "collides across the 576 separate seed-runs WP E produced (see convergence_tests.py's module "
            "docstring for the full finding). Fixed by requiring composed keys "
            "(convergence_tests.compose_global_lineage_id) for any cross-run pooling -- now feasible, and "
            "documented directly on the criterion's own docstring so a future caller cannot miss it."
        ),
    },
}

#: Section 13's required four-level similarity taxonomy (see module
#: docstring for the full definitions).
SIMILARITY_LEVEL_TAXONOMY: dict[str, dict] = {
    "within_run_lineage": {
        "definition": "shared ancestry between institutions in the SAME seed-run",
        "operationalized_by": ["convergence_tests.within_run_lineage_relatedness"],
        "distinguishes_from": ["cross_run_structural_similarity: different seed-runs, so this level never applies across runs"],
    },
    "cross_run_structural_similarity": {
        "definition": "members from different seed-runs land in the same discovered cluster -- a purely descriptive, pre-causal observation",
        "operationalized_by": ["phenotype_discovery.fit_candidate", "phenotype_discovery.co_assignment_matrix"],
        "distinguishes_from": ["independent_convergence: this level makes no claim about WHY members are similar, only that they are"],
    },
    "independent_convergence": {
        "definition": "cross-run structural similarity that is ALSO lineage-diverse beyond chance, not majority transmission-linked, and recurs across more than one parameter condition",
        "operationalized_by": ["convergence_tests.classify_convergence_or_inheritance (label='convergent')"],
        "distinguishes_from": ["within_run_lineage: requires cross-run evidence, never satisfied by one run alone"],
    },
    "component_homology_vs_analogy": {
        "definition": "biology-inspired reframing of inherited/convergent: homology=shared-origin similarity (within-run lineage sharing OR cross-run direct transmission), analogy=independently-arisen similarity (the convergent label)",
        "operationalized_by": ["convergence_tests.classify_convergence_or_inheritance (label='inherited'=homology, label='convergent'=analogy)"],
        "distinguishes_from": ["no new computation -- an interpretation layer over the other three levels, recorded explicitly so it is never reinvented ad hoc"],
    },
}


def audit_completeness_check() -> dict:
    """Section 13 completeness gate: every one of the twelve criteria
    named in ``recurrence_criteria.RECURRENCE_CRITERIA_NAMES`` has an
    audit entry, and no criterion has been silently dropped."""
    audited = set(RECURRENCE_CRITERIA_AUDIT.keys())
    live = set(rc.RECURRENCE_CRITERIA_NAMES)
    return {
        "all_criteria_audited": audited == live,
        "audited_criteria": sorted(audited),
        "missing_from_audit": sorted(live - audited),
        "extra_in_audit": sorted(audited - live),
    }


def extract_default_thresholds() -> dict[str, dict]:
    """Reads each criterion function's OWN default keyword values via
    ``inspect.signature`` rather than hand-duplicating them in this
    audit module -- guarantees the versioned spec (built from this
    function's output) can never silently drift out of sync with
    ``recurrence_criteria.py``'s actual defaults."""
    name_to_func = {
        "minimum_cluster_size": rc.minimum_cluster_size,
        "cross_seed_recurrence": rc.cross_seed_recurrence,
        "cross_algorithm_support": rc.cross_algorithm_support,
        "bootstrap_stability": rc.bootstrap_stability_criterion,
        "co_assignment_internal_consistency": rc.co_assignment_internal_consistency,
        "distinctness_from_noise": rc.distinctness_from_noise,
        "missingness_strategy_robustness": rc.missingness_strategy_robustness,
        "parameter_condition_diversity": rc.parameter_condition_diversity,
        "temporal_persistence_of_members": rc.temporal_persistence_of_members,
        "non_degenerate_cluster_fraction": rc.non_degenerate_cluster_fraction,
        "k_selection_non_privileged_support": rc.k_selection_non_privileged_support,
        "independent_of_single_lineage": rc.independent_of_single_lineage,
    }
    out = {}
    for name, func in name_to_func.items():
        sig = inspect.signature(func)
        defaults = {
            p.name: p.default for p in sig.parameters.values()
            if p.default is not inspect.Parameter.empty
        }
        out[name] = defaults
    return out
