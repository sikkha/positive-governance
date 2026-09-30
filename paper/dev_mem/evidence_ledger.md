---
name: evidence_ledger
description: Every numerical claim used in the manuscript, mapped to its exact source file and field in the source model repository (abm_governance_level1.0), with verification status.
---

# Evidence Ledger — Level 1.2 / Level 1.2b Governance Paper

Source repository root (read-only): `<LOCAL_PATH>/abm_governance_level1.0`.
All values below were independently recomputed from the raw JSON outputs in
`outputs/` (not merely copied from prose documents) using Python during the
preflight for this paper, on 2026-08-19. Where a `docs/*.md` prose claim and
the raw JSON were both checked, agreement is noted explicitly. No discrepancy
was found between any prose document and its underlying raw output during
this audit.

Legend: **[VERIFIED-RAW]** = recomputed directly from the JSON output file.
**[VERIFIED-DOC]** = taken from a `docs/*.md` note whose own numbers were
cross-checked against raw output elsewhere in this ledger. **[DOC-ONLY]** =
present only in a prose note; raw artifact not re-derived (e.g., because the
underlying file is a multi-GB intermediate not needed for the headline claim).

## A. Level 1.2 (`docs/level1.2_*`, `outputs/level12_*`)

| # | Claim | Value | Source file | Field | Status |
|---|---|---|---|---|---|
| A1 | Stage 2 pilot outcome split | collapse=7, fragmented=3, viable=0 (n=10) | `outputs/level12_stage2_pilot/stage2_report.json` | `outcome_label_distribution` | [VERIFIED-RAW] |
| A2 | Stage 3 main search outcome split | collapse=22, fragmented=2, viable=0 (n=24) | `outputs/level12_stage3_main_search/stage3_report.json` | `outcome_label_distribution` | [VERIFIED-RAW] |
| A3 | Stage 3 design | 12 parameter draws × 2 seeds = 24 runs, 8-dim Latin Hypercube | `outputs/level12_stage3_main_search/stage3_report.json` | `n_parameter_draws`, `n_seeds_per_draw`, `n_total_runs`, `parameter_space` | [VERIFIED-RAW] |
| A4 | Stage 4 blind discovery | 76 candidate clusters evaluated, 0/76 met all 12 recurrence criteria | `outputs/level12_stage4_blind_discovery/stage4_report.json` | `n_candidate_clusters_evaluated`, `n_candidates_meeting_all_12_criteria` | [VERIFIED-RAW] |
| A5 | Stage 4 pool size | n=24 pooled seed-run records | `outputs/level12_stage4_blind_discovery/stage4_report.json` | `n_pooled_records` | [VERIFIED-RAW] |
| A6 | Stage 5 confirmation outcome split | collapse=11, viable=1 (n=12) | `outputs/level12_stage5_prospective_confirmation/stage5_report.json` | `outcome_label_distribution` | [VERIFIED-RAW] |
| A7 | Stage 5 independent replication | 72 candidate clusters evaluated, 0/72 met all 12 criteria | `outputs/level12_stage5_prospective_confirmation/stage5_report.json` | `independent_replication.n_candidate_clusters_evaluated`, `.n_candidates_meeting_all_12_criteria` | [VERIFIED-RAW] |
| A8 | Stage 6 scaling robustness | 8/8 runs collapse across population∈{40,80}×patches∈{3,6} | `outputs/level12_stage6_scaling_robustness/stage6_report.json` | `per_condition[*].outcome_label_counts` | [VERIFIED-RAW] |
| A9 | Stage 7 perturbation/transition | 0/6 transitions (floor effect; both shocked and unshocked already collapsed) | `outputs/level12_stage7_perturbation/stage7_report.json` | `n_total_pairs`, `n_transitioned` | [VERIFIED-RAW] |
| A10 | Migration ablation (Section 13) | n=8 matched-seed pairs; 5/8 favor migration OFF on ecological fraction; mean paired diff = −0.0773; 4/8 outcome-label transitions; Wilcoxon p=0.25 | `outputs/level12_stage13_causal_ablations/stage13_report.json` | `migration_ablation.{n_pairs,n_a_greater_ecological_fraction,n_b_greater_ecological_fraction,mean_paired_difference,n_outcome_label_transitions,wilcoxon_signed_rank}` | [VERIFIED-RAW] |
| A11 | Regen-rate ablation (Section 13) | n=8 pairs (regen 0.2 vs 1.0); 7/8 favor high regen; mean paired diff = +0.0326; 2/8 transitions; Wilcoxon p=0.039 | `outputs/level12_stage13_causal_ablations/stage13_report.json` | `regen_rate_ablation.{...}` | [VERIFIED-RAW] |
| A12 | Discovery pipeline commitments | 3 candidate methods (gmm/hierarchical/hdbscan), k∈1..8, 3 missingness strategies, 12 recurrence criteria (conjunction) | `outputs/level12_stage0_preregistration/manifest.json` | `discovery_pipeline_commitments`, `recurrence_and_convergence_commitments` | [VERIFIED-RAW] |
| A13 | Test suite at Level 1.2 close | 1084 passed, 6 skipped, 0 failed, 0 warnings (up from 819 preflight baseline) | `docs/level1.2_completion_report.md` §2 | prose | [DOC-ONLY] |

## B. Level 1.2b (`docs/level1.2b_*`, `outputs/level12b_*`)

| # | Claim | Value | Source file | Field | Status |
|---|---|---|---|---|---|
| B1 | Feasibility map (Work Package C) | 120/120 runs, 0 failures; outcome_counts other=50, collapse=52, saturation=18; envelope_failure=False | `outputs/level12b_stage_c_feasibility_map/results.json` | `n_runs_completed`, `n_runs_failed`, `outcome_counts`, `envelope_failure` | [VERIFIED-RAW] |
| B2 | Structural feasibility ratio vs. realized balance | r ≈ 0.478 (Pearson) | `outputs/level12b_stage_c_feasibility_map/results.json` | `ex_ante_vs_realized_correlation.structural_ratio_vs_realized_mean` | [VERIFIED-RAW] (reported in docs as "≈0.48") |
| B3 | Expected-pressure ratio vs. realized balance | r ≈ 0.840 (Pearson) | `outputs/level12b_stage_c_feasibility_map/results.json` | `ex_ante_vs_realized_correlation.expected_ratio_vs_realized_mean` | [VERIFIED-RAW] (reported in docs as "≈0.84") |
| B4 | Main discovery pool (Work Package J) | 576/576 runs, 0 failures; all_outcome_summary collapse=326, viable=161, fragmented=89 (all other labels 0) | `outputs/level12b_stage_j_main_discovery_pipeline/results.json` | `n_runs_completed`, `n_runs_failed`, `all_outcome_summary` | [VERIFIED-RAW] |
| B5 | Failure-trajectory breakdown (discovery pool) | sustained_collapse=305, no_collapse_observed=194, transient_dip_recovered=56, late_onset_collapse=21 | `outputs/level12b_stage_j_main_discovery_pipeline/results.json` | `failure_trajectory_summary` | [VERIFIED-RAW] |
| B6 | Sustained-system eligibility | 576/576 eligible, 0 excluded (preferred min 60, hard min 40 both cleared) | `outputs/level12b_stage_j_main_discovery_pipeline/results.json` | `sustained_system_summary` | [VERIFIED-RAW] |
| B7 | Discovery clustering verdict | headline_k=4; verdict=continuum (reason: 3 k's within 0.05 silhouette of best) | `outputs/level12b_stage_k_clustering_discovery/results.json` | `headline_k`, `verdict` | [VERIFIED-RAW] |
| B8 | Discovery clustering stability metrics | bootstrap_stability mean_ari=0.598 (k=4, n_bootstrap=30); mean_algorithm_agreement_ari=0.192; missingness_strategy_robustness_ari: complete_case=0.591, missingness_indicator=0.653; cluster_vs_ic_family_ari=0.00085; temporal_window_stability_ari=0.141; parameter_neighborhood_stability_mean_ari=0.626; cluster_vs_failure_proxy_ari=0.0 | `outputs/level12b_stage_k_clustering_discovery/results.json` | `bootstrap_stability`, `mean_algorithm_agreement_ari`, `missingness_strategy_robustness_ari`, `cluster_vs_ic_family_ari`, `temporal_window_stability_ari`, `parameter_neighborhood_stability_mean_ari`, `cluster_vs_failure_proxy_ari` | [VERIFIED-RAW] |
| B9 | Confirmation pool (Work Package L) | 384/384 runs, 0 failures; all_outcome_summary collapse=245, viable=86, fragmented=53 | `outputs/level12b_stage_l3_prospective_confirmation/results.json` | `n_confirmation_runs`, `all_outcome_summary` | [VERIFIED-RAW] |
| B10 | Confirmation failure-trajectory | no_collapse_observed=99, transient_dip_recovered=40, late_onset_collapse=14, sustained_collapse=231; failure_transition_rate=0.7422 | `outputs/level12b_stage_l3_prospective_confirmation/results.json` | `failure_trajectory_summary`, `failure_transition_rate` | [VERIFIED-RAW] |
| B11 | Confirmation independent replication | headline_k=2 (not 4); verdict=unstable; mean_algorithm_agreement_ari=0.276; bootstrap_mean_ari=0.182 (both below 0.3 stability bar) | `outputs/level12b_stage_l3_prospective_confirmation/results.json` | `recurrence_across_seeds_points_and_ic_families.{headline_k,verdict,mean_algorithm_agreement_ari,bootstrap_mean_ari}` | [VERIFIED-RAW] |
| B12 | Confirmation verdict | null_replicated | `outputs/level12b_stage_l3_prospective_confirmation/results.json` | `confirmation_verdict.verdict` | [VERIFIED-RAW] |
| B13 | Assignment stability (discovery fit → confirmation pool) | ARI = 0.527 | `outputs/level12b_stage_l3_prospective_confirmation/results.json` | `assignment_stability_ari` | [VERIFIED-RAW] |
| B14 | Feature-profile stability | mean cosine similarity = 0.948 across 3/4 clusters with members in both pools (cluster 3 empty in confirmation pool → NaN) | `outputs/level12b_stage_l3_prospective_confirmation/results.json` | `feature_profile_stability` | [VERIFIED-RAW] |
| B15 | Scaling-robustness outcome distribution | collapse=25, fragmented=4, viable=3 (n=32) | `outputs/level12b_stage_m_scaling_robustness/results.json` | recomputed from `records[*].transition_to_failure.all_outcome_label` | [VERIFIED-RAW, recomputed] |
| B16 | Population-fraction shock recovery | 0/32 (0%) | `outputs/level12b_stage_m_scaling_robustness/results.json` | recomputed from `records[*].functional_recovery.population.recovered` | [VERIFIED-RAW, recomputed] |
| B17 | Ecological-fraction shock recovery | 28/32 (87.5%) | `outputs/level12b_stage_m_scaling_robustness/results.json` | recomputed from `records[*].functional_recovery.ecological.recovered` | [VERIFIED-RAW, recomputed] |
| B18 | Causal decomposition design | 13 factors, 8 matched-seed pairs each, 208 total runs, 0 failures | `outputs/level12b_stage_n_causal_collapse_decomposition/results.json` | `n_factors`, `n_seeds_per_ablation`, `n_total_runs` | [VERIFIED-RAW] |
| B19 | Largest ecological-fraction effect: subsistence | mean paired Δ(ecological fraction) = +0.1984 (low=0.1→high=0.6); collapse probability 1.00→0.62 | `outputs/level12b_stage_n_causal_collapse_decomposition/results.json` | recomputed from `factor_results[subsistence].pairs` | [VERIFIED-RAW, recomputed] |
| B20 | Second-largest effect: migration_congestion | mean paired Δ = +0.1173 (None→2); collapse 1.00→0.62 | `outputs/level12b_stage_n_causal_collapse_decomposition/results.json` | recomputed from `factor_results[migration_congestion].pairs` | [VERIFIED-RAW, recomputed] |
| B21 | migration_on_off effect | mean paired Δ = −0.1096 (False→True); collapse probability 0.38→0.88 | `outputs/level12b_stage_n_causal_collapse_decomposition/results.json` | recomputed from `factor_results[migration_on_off].pairs` | [VERIFIED-RAW, recomputed] |
| B22 | patch_regen effect | mean paired Δ = +0.1020 (0.2→1.0); collapse 1.00→0.62 | `outputs/level12b_stage_n_causal_collapse_decomposition/results.json` | recomputed from `factor_results[patch_regen].pairs` | [VERIFIED-RAW, recomputed] |
| B23 | Smallest effect: transmission_cost | mean paired Δ = −0.0018 (0.01→0.2); 0/8 outcome-label transitions | `outputs/level12b_stage_n_causal_collapse_decomposition/results.json` | recomputed from `factor_results[transmission_cost]` | [VERIFIED-RAW, recomputed] |
| B24 | Overall recurrence classification | label = continuum; attractor_label_assigned = False | `outputs/level12b_stage_o_phenotype_recurrence_classification/results.json` | `overall_classification`, `attractor_label_assigned` | [VERIFIED-RAW] |
| B25 | Attractor-label evidence | population_recovery_rate=0.0, ecological_recovery_rate=0.875; both dimensions require majority recovery, population alone rules the label out | `outputs/level12b_stage_o_phenotype_recurrence_classification/results.json` | `attractor_label_evidence` | [VERIFIED-RAW] |
| B26 | Explanatory-category evidence (6 categories) | temporary_similarity=CONSISTENT; independent_structural_convergence(proxy)=CONSISTENT; environmentally_forced_similarity=CONSISTENT for 3 substantial clusters; measurement_compression=AGAINST (5/11 PCA components for 90% variance); failure_state_similarity=AGAINST (ARI=0.0); shared_lineage_persistence=not evaluated | `outputs/level12b_stage_o_phenotype_recurrence_classification/results.json` | `temporary_similarity`, `independent_structural_convergence_proxy`, `measurement_compression`, `failure_state_similarity`, `shared_lineage_persistence` | [VERIFIED-RAW] |
| B27 | Total generative runs, 5 main Work Packages | 1,320 = 120 (C) + 576 (E/J) + 384 (L) + 32 (M) + 208 (N), 0 failures anywhere | `docs/level1.2b_completion_report.md` §4, cross-checked against each stage's own `n_runs_completed`/`n_total_runs` above | sum of A1/B1/B4/B9/B15/B18 run counts | [VERIFIED-DOC, arithmetic re-checked] |
| B28 | Total generative runs incl. secondary validation | 1,340 = 1,320 + 20 (Work Package D secondary-validation classifier runs) | `docs/level1.2b_completion_report.md` §10 | prose | [DOC-ONLY] |
| B29 | Ledger closure residual | production-scale ledger residual ≈ 1e-10 per seed after 6 bug fixes; across 576-run design, max residual 5.9e-09, mean 7.1e-10 (tolerance 1e-4) | `docs/level1.2b_ecological_accounting.md` §2; design-level residual re-stated in `docs/level1.2b_discovery_methods.md` §2 | prose (bug-fix account); residual figures stated in two independent docs, consistent | [VERIFIED-DOC, cross-doc consistent] |
| B30 | Pre-fix residual at production scale | 9.14 (before six-bug-fix sequence; ~+181 after fix #2 alone before remaining fixes) | `docs/level1.2b_ecological_accounting.md` §2 | prose | [DOC-ONLY] |
| B31 | Institutional design (Work Package D) | Latin Hypercube, 21 dimensions, n_institutional_points=60, n_packages=0 | `docs/level1.2b_discovery_methods.md` §1 | prose | [DOC-ONLY] |
| B32 | Joint discovery design (Work Package E) | preferred: 48 joint points × 6 seeds × 2 IC families = 576; hard min 36×4×2=288; stratum spread low=17/medium=16/high=15 points (204/192/180 runs); both IC families 288/288 | `docs/level1.2b_discovery_methods.md` §2 | prose | [DOC-ONLY; run totals cross-checked against B4] |
| B33 | Seed-clustered bootstrap cross-check | seed-clustered mean_ari=0.591 (n_clusters=48) vs flat bootstrap 0.598 | `docs/level1.2b_scientific_note.md` "Statistical robustness" | prose | [DOC-ONLY] |
| B34 | Bootstrap CIs on headline point estimates | collapse fraction 0.566 [0.526, 0.608] (n=576); population-recovery 0.0 [0.0, 0.0] (n=32); ecological-recovery 0.875 [0.75, 0.97] | `docs/level1.2b_scientific_note.md` "Statistical robustness" | prose | [DOC-ONLY] |
| B35 | Test suite at Level 1.2b close | 1475 passed, 6 skipped, 0 failed, 0 warnings; 389 new tests this milestone; up from 1086 preflight baseline | `docs/level1.2b_completion_report.md` §2 | prose | [DOC-ONLY] |
| B36 | Seed disjointness | six pairwise intersections among pooled run sets (E:288 seeds, L:192, M:32, N:104) all empty | `docs/level1.2b_completion_report.md` §10 | prose | [DOC-ONLY] |
| B37 | Preregistration manifest hash | `f5bd19df912c0653b97d83f98a4685bb6020fc18b33092e2b2e1ecf11c319b77` | `outputs/level12b_stage_i_preregistration_manifest/manifest_hash.txt` (cross-referenced in `results.json` files' own `preregistration_manifest_hash` field) | file content | [VERIFIED-RAW] |

## C. Cross-checked orientation values from the task brief

The task brief's "orientation values" were checked word-for-word against B4/B9/B2/B3/B15/B17 above. All matched exactly (576 discovery: 326/161/89; 384 confirmation: 245/86/53; expected-pressure r≈0.84; structural r≈0.48; population recovery 0%; ecological recovery 87.5%). No correction was needed.

## D. Discrepancies found

None. Every prose claim in `docs/level1.2_*.md` and `docs/level1.2b_*.md` that was cross-checked against its underlying raw JSON in `outputs/` matched to reported precision. No case required choosing between a "more favorable" and a "less favorable" number.

## E. Known gaps (not filled by rerunning simulations, per task instruction)

- The exact Section 27/28/29 verbatim specification text is not recoverable from this session's own context (disclosed explicitly in `docs/level1.2b_completion_report.md` §8–§10) — the paper reports the reconstructed audit, not a verbatim reproduction, and says so.
- `shared_lineage_persistence` (one of six candidate explanations for cross-run similarity) was not evaluated — would require a fourth 576-run re-simulation with per-run lineage export. Reported as an explicit evidence gap, not silently omitted (§9.5/Limitations).
- Level 1.2b's Work Package G temporal-representation validation (`docs/level1.2b_discovery_methods.md` §3) was run on a disclosed 12-seed-run subset, not the full 576-run pool — reported as-is in Methods.
