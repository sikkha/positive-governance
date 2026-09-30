# SEM: measurement of governance-related perceptions (RQ1–RQ3)

> **Two analyses are kept side by side.**
> - `R/reconstructed/` reproduces the analysis *as reported* in dissertation v1.2. It is validated against the saved fits.
> - `corrected_analysis/` re-estimates the same models after setting WVS missing-value codes to NA **before** reverse coding (S1). It also adds labelled sensitivity analyses: ordinal WLSMV (S2) and weighted (S3).
>
> Corrected Model 1: n = 76,522 (61 countries), CFI .950, TLI .917, RMSEA(scaled) .088, SRMR .053. Corrected Model 2 is **admissible** (r(S, Z) = .83). Models 3–4 are not identified or admissible under any specification and are not interpreted.
>
> See `../docs/sem_data_coding_audit.md` and `../docs/sem_corrected_results.md`.

Structural equation models of WVS Wave 7 perceptions: confidence in state and legal institutions, and perceived electoral fairness. This is the dissertation's empirical core (Chapters 3–4). **No survey data are included** (see `../docs/data_availability.md`).

## Contents

```
R/original/                    author's scripts, unchanged except local absolute paths → WVS_CSV placeholder
  Data_exploration.R           preprocessing + descriptives (8 items, reverse coding)
  other_SEM_check.R            "Model 4.1" check (Q71 removed; Governance outcome)
  20250513_model2_SEM_governance.R   12-line country-filter stub; despite its name it fits NO model
R/reconstructed/
  sem_models_reconstructed.R   RECONSTRUCTED Models 1–4 (labelled; see header)
R/validation/
  validate_against_saved_workspace.R   checks the reconstruction against the private .RData
  smoke_test_synthetic.R               runs the reconstruction on simulated data (no WVS needed)
corrected_analysis/            coding audit + corrected re-estimation + sensitivity (see its README)
expected/
  saved_workspace_fit_indices.csv              fit indices of saved fits (Models 1–4)
  saved_workspace_standardized_estimates.csv   standardized loadings/paths/covariances
  audit_sensitivity_negative_codes_*.csv       packaging-audit sensitivity (NOT a dissertation result)
```

## What the saved workspace contains

The workspace `20250513_model1_SEM_governance.RData` is private and not distributed. It holds **both raw data and fitted models**:

- raw data: `wvs_data` / `data` (full WVS v5.0 file, 94,278 × 606), several subsets (`wvs_clean` 75,117 × 10, `cleaned_data` 65,308 × 19, `filtered_data`, `wvs_data_filtered`, `efa_data`, `cfa_data`) and the analysis frame `wvs_filtered` (94,278 × 8);
- fitted models (lavaan 0.6-15): `fit` (Model 1), `fit2` (Model 2), `fit3`, `fit4`, `fit_4_1`, and exploratory `fit_final`, `fit_refined`, `fit_global_cfa`, `fit_cfa`; plus `efa_result` (psych);
- unrelated objects left in the session (for example an empty `nflverse` table and religion-item tables).

## Model 1: a gap in the original scripts, and the reconstruction

**No original executable Model 1 script exists.** Model 1 is reported in dissertation v1.2 §4 (CFI .889, TLI .817, RMSEA .144, SRMR .073, n = 94,278). The file named `…model2…R` fits no model. `R/reconstructed/sem_models_reconstructed.R` rebuilds Models 1–4 from:

- the model syntax strings saved in the workspace (`model`, `model2`, `model3`, `model4`), copied verbatim; and
- the preprocessing in `Data_exploration.R` / `other_SEM_check.R`: select 8 items, drop `NA`, reverse-code `5 − x`, fit with `lavaan::sem(estimator = "MLR")`.

**Validation.** Run in this preparation with R 4.3.3 and lavaan 0.6-17, against the private workspace:

```
[ok] preprocessing reproduces saved wvs_filtered (n=94278)
[ok] model1 (strict): max|coef diff|=8.88e-16, max|fit diff|=1.02e-12
[ok] model2 (strict): max|coef diff|=5.55e-16, max|fit diff|=6.21e-11
[ok] model3 (fit-indices only): max|coef diff|=1.20e-02, max|fit diff|=1.40e-05
[ok] model4 (fit-indices only): max|coef diff|=2.69e-04, max|fit diff|=7.22e-05
=== SEM RECONSTRUCTION VALIDATED ===
```

Models 3 and 4 are improper solutions, so their parameter estimates depend slightly on the lavaan version. Only their fit indices are compared.

## Findings from the packaging audit (they affect the dissertation text; full re-estimation in `corrected_analysis/`)

1. **WVS missing-value codes were analysed as valid responses.** The CSV codes non-substantive answers as −1, −2, −4 and −5. The pipeline drops only `NA`, so no rows are removed: n = 94,278 is the **entire file**. Reverse coding then turns those codes into **6, 7, 9 and 10**. 17,756 respondents (18.8 %) have at least one such value among the 8 items. The reported Model 1/Model 2 statistics are therefore based on contaminated indicators. Treating negative codes as missing (n = 76,522) gives, for Model 1: CFI .950, TLI .917, RMSEA(scaled) .088, SRMR .053. For Model 2 the Z loadings become Rule of Law .902 and Democratic Accountability .539, against .795/.349 as reported. See `expected/audit_sensitivity_negative_codes_*.csv`. This is a **sensitivity check, not a replacement analysis**. Whether and how to re-estimate is the author's decision.
2. **Mixed fit-index conventions.** The reported CFI (.889) and TLI (.817) are the *standard* indices. The reported RMSEA (.144) is the *scaled* index. The scaled CFI/TLI are .817/.699 and the standard RMSEA is .159.
3. **Model 2 is an improper solution as reported.** The standardized State_Capacity–Z covariance is **1.089**, above 1, and lavaan warns that the latent covariance matrix is not positive definite. Model 2 also has exactly Model 1's fit, because a second-order factor with two indicators is just-identified. With negative codes treated as missing, the correlation is .827 and the solution is admissible.
4. **Models 3 and 4 are improper.** In Model 3 there is a negative latent variance, so the standardized estimates are `NA`. In Model 4 the Governance → Q71 loading is 1.35 and the parameter covariance matrix is singular. The dissertation says these models "did not produce significant structural results". The saved Model 4 does not support that statement: S → Governance and DA → Governance have p < .001. Neither model supports **any** substantive statement. After correction, Model 3 does not converge under ML, and Model 4 remains empirically unidentified. See `../docs/sem_corrected_results.md` §4.
5. **Contradictory preprocessing statements in Chapter 3 (v1.2).** The chapter says "pairwise deletion" and "all analyses employ weighted data". It also says "listwise deletion" and "no additional weights were applied". The code does listwise deletion (of `NA` only) with no weights.

## Requirements

- R ≥ 4.1; packages `readr`, `dplyr`, `lavaan` (the saved fits used lavaan **0.6-15**; validation used 0.6-17). `Data_exploration.R` also uses `tidyverse`, `psych`, `moments`, `ggplot2` and `corrplot`.

## Commands

```bash
cd sem
# 1. Obtain the WVS v5.0 CSV (docs/data_availability.md), then:
WVS_CSV=data/WVS_Cross-National_Wave_7_csv_v5_0.csv Rscript R/reconstructed/sem_models_reconstructed.R
# sensitivity variant (packaging audit, not the reported analysis):
SEM_NEGATIVE_CODES=as_missing WVS_CSV=… Rscript R/reconstructed/sem_models_reconstructed.R
# 2. Author only: validate against the private workspace
SEM_RDATA=/path/to/20250513_model1_SEM_governance.RData Rscript R/validation/validate_against_saved_workspace.R
# 3. Anyone: code smoke test on simulated data (no WVS needed; ~10 s)
Rscript R/validation/smoke_test_synthetic.R
```

Expected output of step 1 in its default mode: Model 1 with n = 94,278; CFI 0.8888, TLI 0.8169, RMSEA(scaled) 0.1435, SRMR 0.0731. Compare `expected/saved_workspace_fit_indices.csv`.
