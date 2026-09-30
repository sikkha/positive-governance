# SEM data-coding audit

**Scope.** This audit covers the eight WVS Wave 7 indicators used in dissertation Chapters 3–4 (reviewed version **1.2**; version 1.3 was not supplied). It checks how the indicators were coded, how missing values were handled, and what that did to the analytic sample.

**Code:** `sem/corrected_analysis/R/sem_corrected_analysis.R`
**Outputs:** `sem/corrected_analysis/results/` (aggregate statistics only)

## 1. Evidence used and its status

| Evidence | Status |
|---|---|
| Respondent data: WVS Wave 7 cross-national file **v5.0** (`version` = "5-0-0 (2022-12-23)", DOI 10.14281/18241.20), as stored in the author's private workspace object `wvs_data` (94,278 × 606). This object was read from `WVS_Cross-National_Wave_7_csv_v5_0.csv` with `readr::read_csv`, per the saved `file_path` | **Verified**: every value count below comes from this object |
| Official codebook for v5.0 | **Not located.** The WVS site was not reachable for this document during the audit |
| Codebook actually inspected: *World Values Survey Wave 7 (2017–2022) Variables Report* **V6.0** (WVSA). It was obtained from a third-party mirror (gabors-data-analysis.com), PDF SHA-256 `dc18b2a5…6a5c`, 404 pp. | **Verified to the extent shown.** Item wording, valid codes and missing codes are quoted from it. Its version (V6.0) differs from the data (v5.0). The data themselves contain only the codes documented there (see §3), which empirically confirms the coding for these eight items |
| The original CSV file itself (checksum) | **Not available** in the working folders. The re-estimation therefore relies on the workspace copy |

## 2. Indicator coding (codebook V6.0, pp. 24–26 and 73–74)

| Item | Wording (abridged) | Valid codes (original direction) | Missing-value codes |
|---|---|---|---|
| Q65 | Confidence: the armed forces | 1 A great deal · 2 Quite a lot · 3 Not very much · 4 None at all | −1 Don't know · −2 No answer · −4 Not asked · −5 Missing; Not available |
| Q71 | Confidence: the government (in your nation's capital) | same | same |
| Q72 | Confidence: political parties | same | same |
| Q73 | Confidence: parliament | same | same |
| Q69 | Confidence: the police | same | same |
| Q70 | Confidence: justice system/courts | same | same |
| Q224 | How often in country's elections: votes are counted fairly | 1 Very often · 2 Fairly often · 3 Not often · 4 Not at all often | same |
| Q229 | How often in country's elections: election officials are fair | same | same |

**Direction.** On all eight items, 1 is the *most* favourable answer (most confidence, or fairness most often). The transformation `5 − x` is therefore the correct reversal for **valid** codes: after it, higher values mean more confidence or more fairness. No code −3 occurs for these items.

## 3. Values observed in the data (v5.0, n = 94,278)

| Item | Valid 1–4 | −1 DK | −2 NA | −4 Not asked | −5 Missing | % invalid |
|---|---|---|---|---|---|---|
| Q65 | 89,996 | 1,615 | 272 | 2,204 | 191 | 4.54 |
| Q71 | 91,194 | 1,403 | 328 | 1,200 | 153 | 3.27 |
| Q72 | 91,071 | 2,591 | 435 | 0 | 181 | 3.40 |
| Q73 | 90,982 | 2,677 | 439 | 0 | 180 | 3.50 |
| Q69 | 91,888 | 802 | 239 | 1,200 | 149 | 2.54 |
| Q70 | 90,821 | 1,798 | 297 | 1,200 | 162 | 3.67 |
| Q224 | 85,565 | 4,703 | 759 | 3,036 | 215 | 9.24 |
| Q229 | 84,317 | 5,777 | 907 | 3,036 | 241 | 10.57 |

No system `NA` values occur, so every non-substantive answer is a negative integer. No value outside {−5, −4, −2, −1, 1, 2, 3, 4} occurs (`coding_audit_value_counts.csv`).

"Not asked" (−4) is **country-level**:
- Q65 was not asked in Andorra (AND, 1,004) or Egypt (EGY, 1,200).
- Q71, Q69 and Q70 were not asked in Egypt.
- Q224 and Q229 were not asked in China (CHN, 3,036).

## 4. What the original pipeline did

`Data_exploration.R` and `other_SEM_check.R` select the items, keep rows with no `NA`, and apply `5 − x`. The saved analysis frame `wvs_filtered` was reproduced exactly (see `sem/README.md`). Because missing codes are negative integers rather than `NA`:

- **No respondent was removed.** The reported "complete-case sample of 94,278" is the entire file.
- Reverse coding mapped −1, −2, −4, −5 to **6, 7, 9, 10**. These were then treated as interval scores *above* the valid maximum of 4, so a "don't know" was scored as more than maximal confidence.
- **17,756 respondents (18.83 %)** have at least one such value (`respondents_by_number_of_invalid_items.csv`):

  | Invalid items per respondent | Respondents |
  |---|---|
  | 1 | 7,130 |
  | 2 | 6,762 |
  | 3 | 1,094 |
  | 4 | 1,285 |
  | 5 | 478 |
  | 6 | 476 |
  | 7 | 180 |
  | 8 | 351 |

- Whole countries entered with structurally invalid blocks. All 3,036 Chinese respondents were scored 9 on both electoral items, all Egyptian respondents 9 on four confidence items, and all Andorran respondents 9 on Q65.
- As analysed, the item distributions had maximum 10, skew +1.42 to +1.89 and excess kurtosis 3.1 to 7.9 (`item_descriptives_original_vs_corrected.csv`).

## 5. Correction applied

Codes −1, −2, −4 and −5 are set to `NA` **before** reverse coding. Rows with any missing item are then deleted listwise, and `5 − x` is applied. There is no imputation, no weighting in the primary corrected specification, and no change to items or model structure.

| Quantity | Value |
|---|---|
| Original respondent count | 94,278 (64 countries/territories) |
| Respondents with any invalid or missing item | 17,756 (18.83 %) |
| Corrected analytic sample | **76,522** |
| Countries in corrected sample | **61** (AND, CHN, EGY drop out entirely because an indicator was not asked) |
| Retention among the remaining 61 countries | 60.0 % (UKR) to 100 %; median 86.1 % |
| Largest contributors | CAN 4,018; IDN 3,064; USA 2,467; GBR 2,271 |

The full country table, including the items not asked, is in `results/country_composition.csv`.

Descriptive statistics after correction: all items lie within 1–4, skew is between −0.49 and +0.50, and excess kurtosis is between −0.99 and −0.48.

## 6. Consequences for statements in the dissertation (v1.2)

| Location | Statement | Audit finding | Status |
|---|---|---|---|
| §3.3 (sample strategy) | "Missing data were addressed through pairwise deletion … All analyses employ weighted data" | The code uses listwise deletion of `NA` only, with no weights. The same section also says listwise and unweighted | Contradicted by code; internally inconsistent |
| §3.3, §4.2.1 | "complete-case sample of 94,278 respondents" | This is the whole file; the corrected complete-case n is 76,522 | **Numerical correction** |
| §3.3.1 | "moderately left-skewed … skewness and kurtosis within −1 < skew < 1, −3 < kurtosis < 3" | False for the data as analysed (skew +1.4 to +1.9, kurtosis up to 7.9). After correction the thresholds hold, but three items (Q71, Q72, Q73) are right-skewed | Correction required |
| §3.3.1 | Within-domain r = 0.60–0.80 (S); r ≈ 0.75 (police–courts); r ≈ 0.65 (electoral); cross-domain 0.40–0.55 | As analysed: S items .26–.68, police–courts .73, electoral .74, cross-domain .17–.68. Corrected Pearson: S .27–.71, .63, .57, cross-domain .19–.55. Corrected polychoric: S .32–.79, .70, .66 | Not reproduced by any coding. Replace with corrected values |
| §4.2.3 | Parallel analysis shows three large eigenvalues | Not reproducible: no script, and the saved `efa_data` subset (1,350 rows) has undocumented provenance | Unverified |

## 7. Checks that could not be completed

- The official v5.0 codebook and a checksum of the original CSV were not available. The V6.0 variables report was used, supported by the observed codes.
- Country-level measurement invariance and multilevel structure were not tested; the design is pooled.
- The EFA and parallel analysis cannot be re-run because of their unknown input subset.
