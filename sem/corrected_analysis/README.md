# SEM corrected analysis

This folder is separate from `../R/reconstructed/`, which reproduces the original (as-reported) analysis. This folder adds:

1. **Coding audit.** WVS missing-value codes −1, −2, −4 and −5 are identified per item (see `../../docs/sem_data_coding_audit.md`).
2. **Corrected re-estimation.** Missing codes are set to NA *before* reverse coding. Estimation uses the original estimator (MLR, S1), so the effect of cleaning is isolated.
3. **Sensitivity analyses.** These are clearly separated from the original specification: ordinal WLSMV (S2) and W_WEIGHT-weighted MLR (S3).
4. **Diagnostics for every fitted model.** For each of the four specifications × Models 1–4, the output records: convergence, degrees of freedom, positive-definiteness of the parameter covariance (identification), lavaan admissibility check, latent-covariance eigenvalues, negative residual or latent variances, standardized loadings, latent correlations, residual variances, and standard, scaled and robust fit indices.

The model structure is unchanged in every specification. No theoretical revision or exploratory modification has been made.

## Run

```bash
cd sem
WVS_CSV=/path/to/WVS_Cross-National_Wave_7_csv_v5_0.csv Rscript corrected_analysis/R/sem_corrected_analysis.R
#   or, author only:  WVS_RDATA=/path/to/20250513_model1_SEM_governance.RData Rscript …
python corrected_analysis/make_headline_table.py
```

- **Runtime:** about 45 s (R 4.3.3, lavaan 0.6-17, 2 vCPU).
- **Output directory:** `results/`, or set `OUT_DIR=/tmp/sem_out` to leave the archived results untouched.
- **Warnings:** the run is deterministic. Model 3 non-convergence and the Model 4 singular vcov warnings are expected and are recorded in `results/estimation_warnings.csv`.

## Results files (aggregate only; no respondent records)

| File | Content |
|---|---|
| `sample_summary.csv` | original n, affected respondents, corrected n, countries |
| `coding_audit_value_counts.csv` | every observed code per item, with its status |
| `missingness_by_item.csv` | valid, don't-know, no-answer, not-asked and missing counts per item |
| `respondents_by_number_of_invalid_items.csv` | distribution of invalid items per respondent |
| `country_composition.csv` | per-country original and corrected n, % retained, items not asked |
| `item_descriptives_original_vs_corrected.csv` | mean, SD, range, skew and excess kurtosis under both codings |
| `item_correlations_original_vs_corrected.csv` | Pearson (both codings) and polychoric (corrected) correlations |
| `sem_results_long.csv` | every diagnostic and parameter, long format |
| `original_vs_corrected.csv` | the same, wide format (one column per specification) |
| `original_vs_corrected_headline.csv` | key rows, with the value reported in dissertation v1.2 |
| `estimation_warnings.csv` | all lavaan warnings per fit |
| `session_info.txt` | R/lavaan versions, data source, timestamp |

The results were produced from the author's v5.0 data object (`WVS_RDATA`). They have not yet been re-run from a fresh CSV download.
