# Version map

This map is built from file contents: diffs, module inventories, READMEs, completion reports and output directories. Folder names were not used as evidence. Milestone labels that look alike are **not** equivalent. For example, ABM *Level 0.2* and *Level 1.2* are different milestones of the same model lineage, and neither corresponds to MCMEA *v2*.

## 1. Source folders and where they went

| Source folder (local, not published) | Contents (verified) | Published as |
|---|---|---|
| `abm_governance_level1.0/` | Python package `abm_governance`, 110 experiment modules, 151 test modules, 52 documentation files, `outputs/` for Levels 0.3b (registry only), 1.0, 1.1, 1.1b, 1.2, 1.2b, 1.3 and 1.3b | **`abm/`** (canonical) |
| `abm_governance/` | The same package at the **Level 0.3b** milestone, plus `outputs/` for Levels 0.1–0.3b | **`legacy/abm_governance_level0.3b/`** (snapshot, not installed) |
| `abm_governance_paper/` | LaTeX manuscript, tables, curated figures, claim–evidence manifest, evidence ledger | **`paper/`** |
| `mcmea/` | `MCMEA_v2_regime_aware_governance.ipynb`, `MCMEA_v3_oracle_mode_structural_profiles.ipynb` | **`mcmea/notebooks/evidence/`** (unchanged) + clean copies + extracted modules |
| `SEM/R code/` | 3 R scripts + private workspace `20250513_model1_SEM_governance.RData` | **`sem/R/original/`** (paths replaced by placeholders); workspace **not published** |

## 2. ABM: how `abm_governance` and `abm_governance_level1.0` relate

**Finding: `abm_governance_level1.0` is a strict descendant (superset) of `abm_governance`. The two are not parallel implementations.**

Evidence (`diff -rq`, ignoring caches):

- Every file in `abm_governance/src`, `experiments/`, `tests/` and `docs/` also exists in `abm_governance_level1.0`. There are no files unique to the legacy folder apart from `lr/` (the dissertation proposal PDF) and Level 0.x outputs.
- Changed files are extensions: `core/config.py`, `core/rng.py`, `core/events.py`, `core/perturbation.py`, `agents/agent.py`, `agents/adaptation.py`, `environment/patches.py`, `observer/network_diagnostics.py`, `simulation.py`, two Level 0.3b experiment scripts, three tests and `abm/docs/config_reference.md`. The last of these gains Level 1.x fields only; lines 1–361 are identical.
- `abm_governance_level1.0` adds `rules/` (institutions), `core/{entrenchment,legitimacy,historical_*,state_checkpoint}.py` and 20 observer modules.
- Backward compatibility is enforced by tests, not assumed: `SimulationConfig.level0_compat()`, `tests/test_level13_stage0_exact_compatibility.py` and `experiments/level13b_stage0_frozen_compatibility.py` require byte-identical results with every new mechanism disabled.
- The legacy README's status line reads "Level 0.3b … Level 1 has not been started". The canonical README's status block reads "Level 1.2b — in progress" and is **out of date**: `abm/docs/level1.3_completion_report.md` and `abm/docs/level1.3b_completion_report.md` record Levels 1.3 and 1.3b as complete, with a final suite of 2047 passed and 6 skipped.

**Canonical implementation for Chapter 6 and the paper: `abm/` (from `abm_governance_level1.0`), at the Level 1.3b milestone.**

## 3. ABM milestones, experiments, chapter and paper

| Milestone | Code (in `abm/`) | Evidence outputs | Main documentation | Dissertation v1.2 | Paper |
|---|---|---|---|---|---|
| Level 0.1 | core, agents, network, environment | `legacy/…/outputs/ensemble_level01`, `level0_default` | `abm/docs/odd_level0.1.md` | not reported | §3 genealogy (narrative only) |
| Level 0.2 | `experiments/phase_sweep.py`, `boundary_perturbation.py`, `turnover_boundary_sweep.py`, `null_model_comparisons.py`, `cooperation_ecology_causality.py` | `legacy/…/outputs/*_level02` | `abm/docs/level0.2_scientific_note.md` | not reported | §3 |
| Level 0.3 | `experiments/niche_*.py` | `legacy/…/outputs/niche_*` | `abm/docs/level0.3_scientific_note.md` | not reported | §3 |
| Level 0.3b | `experiments/level03b_*.py` | `legacy/…/outputs/level03b_*`; `abm/outputs/level03b_candidate_registry` | `abm/docs/level0.3b_validation_note.md` | not reported | §3 |
| Level 1.0 | `rules/shared_rule.py`, `experiments/level1_*.py` | `abm/outputs/level1_*` | `abm/docs/level1.0_*` | not reported | §3 |
| Level 1.1 / 1.1b | `rules/{delegation,…}`, `experiments/level11*_*.py` | `abm/outputs/level11*` | `abm/docs/level1.1*` | background | §3–4 |
| **Level 1.2** | `experiments/level12_*.py` | `abm/outputs/level12_*` | `abm/docs/level1.2_*` | §6.9.2, §6.10.1 | §5 |
| **Level 1.2b** | `experiments/level12b_stage_*.py` | `abm/outputs/level12b_*` | `abm/docs/level1.2b_*` | §6.9.3, §6.10 | §6 |
| **Level 1.3** | `experiments/level13_*.py` | `abm/outputs/level13_*` | `abm/docs/level1.3_*` | §6.9.4, §6.11.1 | §7 |
| **Level 1.3b** | `experiments/level13b_*.py`, `core/state_checkpoint.py` | `abm/outputs/level13b_*` | `abm/docs/level1.3b_*`, `abm/docs/level13b_preregistration.md` | §6.9.5, §6.11–6.13 | §8 |

Discovery and confirmation pools (from the frozen manifests):

| Milestone | Discovery pool | Confirmation pool | Frozen manifest |
|---|---|---|---|
| 1.2 | Stage 3 search, 12 LHS points × 2 seeds (24 runs) | Stage 5 prospective, 12 runs | `outputs/level12_stage0_preregistration/` |
| 1.2b | Stage E/J: 48 joint points × 6 seeds × 2 initial-condition families = 576 runs | Stage L1/L3: disjoint 384-run pool | `outputs/level12b_stage_i_preregistration_manifest/` |
| 1.3 | Stage 4 open search + Stage 6 blind discovery | Stage 7 fresh confirmation | `outputs/level13_preregistration/` |
| 1.3b | Stage 4: 48 × 5 = 240 runs (homogeneous discovery) | Stage 8: 24 × 4 = 96 runs, disjoint design and simulation seeds | `outputs/level13b_preregistration/manifest.json`, SHA-256 `f6498c0e…57c0` (verified with `load_and_verify_manifest`) |

## 4. Paper

`paper/` corresponds exactly to git tag `level13b-revision-complete` (commit `c708116`) of the paper's own local history. That history was found in `abm_governance_paper/_to_delete/partial_git_from_sync_attempt`: two commits, both tags present, clean under `git fsck`. The only differences are (a) absolute local paths in `dev_mem/evidence_ledger.md` and `dev_mem/paper_status.md`, replaced by `<LOCAL_PATH>`, and (b) build products excluded. The paper bundles **no simulation code and no raw outputs**. Its figures are curated byte-copies from `abm/outputs/level1{2,2b,3,3b}_figures/` (provenance in `paper/dev_mem/figure_manifest.md`). Its numerical claims map to `abm/outputs/**` in `paper/claim_evidence_manifest.csv` and `paper/dev_mem/evidence_ledger.md`. Paths there are relative to the ABM root, so read `outputs/…` as `abm/outputs/…`.

## 5. MCMEA

| Version | File | Status | Dissertation v1.2 |
|---|---|---|---|
| (earlier, "recovered article") | **not present** | code and configuration missing | Carried over, unverified, in §6.1, §6.13.4, §7.6.2, §7.6.4, §7.6.5 (see audit) |
| v2 "regime-aware" | `mcmea/notebooks/evidence/MCMEA_v2_regime_aware_governance.ipynb` | executable; all stored outputs reproduced | not cited by name |
| v3 "oracle mode, structural profiles" | `mcmea/notebooks/evidence/MCMEA_v3_oracle_mode_structural_profiles.ipynb` | executable; all stored outputs reproduced | **Ch. 5** (§5.3–5.6) |
| TimesFM supplementary temporal experiment | **not present** | code missing; needs external checkpoint | Ch. 5 §5.7 |

The v2/v3 differences are tabulated in `docs/mcmea_specification_audit.md` §2.

## 6. SEM

| Model | Saved object in private workspace | Script |
|---|---|---|
| EFA / parallel analysis | `efa_result`, `efa_data` (1,350 rows) | not preserved |
| Model 1: 3 correlated factors, 8 items | `model`, `fit` | **no original script**; reconstructed in `sem/R/reconstructed/`, validated identical |
| Model 2: second-order Z | `model2`, `fit2` | reconstructed, validated identical |
| Models 3, 4: Governance outcome | `model3/4`, `fit3/4` | reconstructed; fit indices match to within 1e-4 (improper solutions; see `sem/README.md`) |
| Model 4.1 (Q71 removed) | `model_4_1`, `fit_4_1` | `sem/R/original/other_SEM_check.R` |
| Exploratory variants (`model_final` + Q164; `model_refined`; 18-item `cfa_model`) | `fit_final`, `fit_refined`, `fit_global_cfa`, `fit_cfa` | not preserved; not reported in v1.2 |
