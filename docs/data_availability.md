# Data availability

## Summary

| Component | Data | Included here? | Reason / how to obtain |
|---|---|---|---|
| SEM | World Values Survey Wave 7 cross-national CSV, **v5.0 (2022-12-23)**, DOI `10.14281/18241.20` (as embedded in the file's `version`/`doi` columns) | **No** | Third-party survey microdata. Download it yourself from the WVS (see below) |
| SEM | Author's saved R workspace `20250513_model1_SEM_governance.RData` (46.6 MB) | **No** | Contains the **complete WVS respondent-level file** (94,278 × 606) and several derived subsets, plus unrelated objects. It cannot be published without redistributing WVS microdata |
| SEM | Aggregate results from that workspace: fit indices and standardized estimates for Models 1–4 | **Yes**: `sem/expected/saved_workspace_*.csv` | Model-level statistics only. No respondent records |
| SEM | Packaging-audit sensitivity results (negative WVS codes treated as missing) | **Yes**: `sem/expected/audit_sensitivity_*.csv` | Aggregate statistics, labelled as audit output, not dissertation results |
| SEM | Corrected re-estimation, coding audit, country composition, descriptives, correlations | **Yes**: `sem/corrected_analysis/results/` | Aggregate statistics only (per-country respondent counts, item frequencies, model parameters); no respondent records |
| MCMEA | Notebooks with stored outputs (figures, printed matrices, summary tables) | **Yes**: `mcmea/notebooks/evidence/` | Fully synthetic; regenerable from seeds |
| ABM | Experiment outputs for Levels 0.3b (registry), 1.0–1.3b: JSON results, manifests, hashes, figures (27 MB) | **Yes**: `abm/outputs/` | Synthetic model output. Audits the reported findings; several tests read these files |
| ABM | Level 0.1–0.3b outputs from the legacy snapshot (≈19 MB) | **Yes**: `legacy/abm_governance_level0.3b/outputs/` | Synthetic model output |
| ABM | `legacy/…/outputs/level03b_confirmatory_perturbation/confirmatory_perturbation_trajectories.csv` (24.9 MB) | **No** (release/archive candidate) | Large per-step trajectory table; regenerable (see below) |
| Paper | Curated figures and tables | **Yes**: `paper/figures`, `paper/tables` | Byte-copies of `abm/outputs` figures + one TikZ diagram |
| Dissertation | Manuscript (`.docx`/`.pdf`), proposal PDF, Chapter 6 drafts | **No** | Unpublished dissertation text. Publishing it is the author's decision |

## Obtaining the WVS data (SEM)

1. Go to the World Values Survey data archive (worldvaluessurvey.org → *Data & Documentation* → *Wave 7 (2017–2022)*). Download the **country-pooled cross-national data set, CSV format, version 5.0** (`WVS_Cross-National_Wave_7_csv_v5_0.csv`). The WVS asks users to register and accept its conditions of use before downloading.
2. Save it as `sem/data/WVS_Cross-National_Wave_7_csv_v5_0.csv`, or set `WVS_CSV=/path/to/file.csv`. The `sem/data/` directory is git-ignored.
3. Expected schema for the items used: `B_COUNTRY` and the numeric items `Q65, Q69, Q70, Q71, Q72, Q73, Q224, Q229`, each coded 1–4, with WVS missing-value codes −1 (don't know), −2 (no answer), −4 (not asked), −5 (missing/other). The v5.0 file used for the dissertation had **94,278 rows and 606 columns, from 64 countries/territories** (`B_COUNTRY`).
4. Cite the data as the WVS requires: Haerpfer, C., Inglehart, R., Moreno, A., Welzel, C., Kizilova, K., Diez-Medrano, J., Lagos, M., Norris, P., Ponarin, E. & Puranen, B. (eds.) (2022). *World Values Survey: Round Seven – Country-Pooled Datafile Version 5.0*. Madrid, Spain & Vienna, Austria: JD Systems Institute & WVSA Secretariat. doi:10.14281/18241.20.

**Redistribution.** The WVS catalogue entries consulted during preparation state that the data are free of charge and must be cited. They did not state redistribution terms explicitly. The data are distributed through the WVS's own registration-gated download, so this repository does not redistribute WVS microdata or any file that contains it. Only aggregate model statistics are included. If you need a different decision, check the current WVS conditions of use first.

## Regenerating excluded ABM outputs

The only excluded ABM output is the legacy Level 0.3b per-step trajectory CSV (24.9 MB). It was written by `experiments/level03b_confirmatory_perturbation.py` in the Level 0.3b snapshot. Its summary outputs in the same folder (`confirmatory_perturbation_recovery.csv`, `level03b_confirmatory_perturbation_summary.json`) **are** included. To regenerate it, use a separate environment and **a copy of the repository**, because stage scripts write into `outputs/` in place:

```bash
cd legacy/abm_governance_level0.3b
python -m venv .venv && . .venv/bin/activate && pip install -e .
python experiments/level03b_confirmatory_perturbation.py   # see its --help / module docstring for arguments
```

This was not re-run during packaging. Its runtime is not measured.

## Build products that are not tracked

- `paper/build/` and `paper/manuscript.pdf`: rebuilt with `make pdf` (verified; 93 pages). The compiled PDF can be attached to a GitHub release.
- Python caches, `*.egg-info`, `.pytest_cache`.
