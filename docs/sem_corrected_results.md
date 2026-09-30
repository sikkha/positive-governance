# SEM corrected results

**Version reviewed:** dissertation **v1.2** (v1.3 not supplied).
**Code:** `sem/corrected_analysis/R/sem_corrected_analysis.R`
**Machine-readable results:**
- `sem/corrected_analysis/results/original_vs_corrected_headline.csv`: key statistics, with the v1.2 reported value beside each specification.
- `…/original_vs_corrected.csv`: every parameter, wide format.
- `…/sem_results_long.csv`: every diagnostic, long format.

Run environment: R 4.3.3, lavaan 0.6-17 (the original fits used lavaan 0.6-15).

**Status:** every number on this page was **computed** in this audit from the author's v5.0 data object. None of it has been independently replicated from a fresh WVS download.

## 1. Specifications

The model structure is identical across all four specifications. Only data handling, the estimator and weights differ.

| Spec | Role | Data handling | Estimator | Indicators | Weights | Pooling |
|---|---|---|---|---|---|---|
| **S0** | *Reconstruction of the original analysis* (validated: Models 1–2 identical to saved fits) | Negative codes kept, then 5 − x; n = 94,278 | ML with robust SE and Yuan–Bentler scaled test (lavaan `MLR`) | treated as continuous | none | pooled, 64 countries |
| **S1** | *Primary corrected analysis*: same estimator, so the effect of cleaning is isolated | Negative codes → NA **before** 5 − x; listwise; n = 76,522 | MLR | continuous | none | pooled, 61 countries |
| **S2** | *Sensitivity: ordinal estimator* (not the original specification) | as S1 | WLSMV (DWLS on polychoric correlations; robust SE; mean- and variance-adjusted test) | **ordered**, 4 categories, thresholds free | none | pooled, 61 |
| **S3** | *Sensitivity: sampling weights* | as S1 | MLR | continuous | `W_WEIGHT` (within-country; countries not equalised) | pooled, 61 |

**Identification (all specs).** lavaan defaults apply: the first loading of each factor is fixed to 1 (marker), and latent variances and covariances are free. In Model 2, Z uses Rule_of_Law as its marker. With only two first-order indicators, Z is **just-identified**, so Model 2 is an exact reparameterisation of Model 1: its fit is identical to Model 1's, and its extra parameters carry no testable restriction. In S2 the latent-response variances are fixed by delta parameterisation. Standardized values are `std.all`.

**Theoretical versus exploratory changes.** None were made. No item, path, cross-loading or residual covariance was added or removed. Anything of that kind belongs to a future, separately labelled exploratory analysis.

## 2. Model 1: three correlated factors

| | Reported (v1.2) | S0 original | **S1 corrected (MLR)** | S2 ordinal (WLSMV) | S3 weighted |
|---|---|---|---|---|---|
| n | 94,278 | 94,278 | **76,522** | 76,522 | 76,522 |
| Converged / admissible | — | yes / yes | **yes / yes** | yes / yes | yes / yes |
| χ² scaled (df = 17) | — | 33,033 | **10,089** | 25,260 | 8,662 |
| CFI (standard / scaled / robust) | .889 | .889 / .817 / .889 | **.950 / .944 / .950** | .991 / **.968** / .940 | .950 / .944 / .950 |
| TLI (standard / scaled / robust) | .817 | .817 / .699 / .817 | **.917 / .908 / .917** | .986 / **.947** / .901 | .917 / .908 / .917 |
| RMSEA (standard / scaled / robust) | .144 | .159 / .144 / .159 | **.099 / .088 / .099** | .098 / **.139** / .124 | .099 / .082 / .099 |
| SRMR | .073 | .073 | **.053** | .053 | .053 |
| λ Q65 armed forces | .583 | .583 | **.419** | .557 | .421 |
| λ Q71 government | .860 | .860 | **.802** | .844 | .804 |
| λ Q72 parties | .628 | .628 | **.791** | .840 | .792 |
| λ Q73 parliament | .631 | .631 | **.861** | .900 | .861 |
| λ Q69 police | .830 | .830 | **.739** | .802 | .740 |
| λ Q70 courts | .878 | .878 | **.854** | .875 | .855 |
| λ Q224 votes counted fairly | .856 | .856 | **.767** | .823 | .766 |
| λ Q229 officials fair | .868 | .868 | **.749** | .797 | .748 |
| r(S, RoL) | not reported | .865 | **.746** | .804 | .747 |
| r(S, DA) | not reported | .381 | **.446** | .460 | .450 |
| r(RoL, DA) | not reported | .278 | **.486** | .495 | .487 |
| Standardized residual variances | — | .23–.66 | **.26–.82** (Q65 .82) | .19–.69 | .26–.82 |
| Negative variances / non-PD latent covariance | — | none | **none** | none | none |

**Reading.**
- Cleaning improves fit (CFI .889 → .950; scaled RMSEA .144 → .088; SRMR .073 → .053).
- Cleaning also changes the **pattern** of loadings. Confidence in parties and parliament now load strongly (.79 and .86). Confidence in the armed forces becomes the weakest indicator by a wide margin (.42, with 82 % unique variance). This strengthens the chapter's own caution about the heterogeneous content of Sₚ.
- The three factors are more evenly related after cleaning. r(RoL, DA) rises from .28 to .49.
- With the ordinal estimator, the scaled CFI (.968) and TLI (.947) are acceptable, but the scaled RMSEA (.139) and robust RMSEA (.124) still indicate misfit.
- Under **any** specification, Model 1 does not fit closely. The conclusion "interpretable but globally misspecified" survives. The size of the misfit, and which items are weak, change.
- Fit indices from WLSMV and ML are not directly comparable.

## 3. Model 2: second-order institutional constraint (Z)

| | Reported (v1.2) | S0 original | **S1 corrected** | S2 ordinal | S3 weighted |
|---|---|---|---|---|---|
| Z → Rule of Law (std) | .795 | .795 | **.902** | .930 | .899 |
| Z → Democratic Accountability (std) | .349 | .349 | **.539** | .532 | .542 |
| r(S, Z) | not reported | **1.089 (> 1)** | **.827** | .865 | .831 |
| Latent covariance matrix PD | — | **no** (min eigenvalue −0.061) | **yes** (0.037) | yes | yes |
| lavaan post-check | — | **fails** | passes | passes | passes |
| Fit | "similar to Model 1" | identical to Model 1 | identical to Model 1 | identical to Model 1 | identical to Model 1 |

**Does the corrected Model 2 still produce an inadmissible solution? No.** Under S1, S2 and S3 the latent covariance matrix is positive definite, all variances are positive and every standardized correlation is below 1. The inadmissible S–Z correlation of 1.089 in the reported solution comes from the coding error.

Two cautions remain:
- Rule of Law still dominates Z (.90 vs .54). The asymmetry is smaller than reported, but it has not gone away.
- S and Z correlate at .83–.87. That is high enough that their empirical distinctness is limited. Because Z is just-identified, Model 2 adds no testable information beyond Model 1.

## 4. Models 3 and 4: not interpreted

| | S0 original | S1 corrected | S2 ordinal | S3 weighted |
|---|---|---|---|---|
| **Model 3** (Governance =~ Q71 + Q70 + Q224 + Q229; Governance ~ S + Z) | converged; **2 negative latent variances**; latent covariance not PD; vcov not PD; standardized solution undefined | **did not converge** (also with 20,000 iterations) | converged; **2 negative residual variances** (std. −14.0 for Q69); std. loading 3.88; SEs not computable | **did not converge** |
| **Model 4** (Governance =~ same 4 items; Governance ~ S + RoL + DA) | converged; **std. loading 1.35 (Governance → Q71)**; vcov not PD (min eigenvalue −2.8e−9) | converged; loadings < 1, but **vcov not PD** (−1.4e−9): empirically unidentified | converged; **SEs and robust test not computable** | converged; vcov not PD |

**Why they are not interpreted.**
1. *Specification.* Every Governance indicator is also an indicator of one of the predictor factors (Q71 of S, Q70 of RoL, Q224/Q229 of DA). Governance is therefore defined by the predictors' own items, and the structural paths are identified only through double-loading items. This does not measure a distinct outcome.
2. *Solutions.* Under every specification, each solution is non-convergent, inadmissible, or has a singular parameter covariance matrix.

**Consequence for the text.** Chapter 4 §4.6 and §7.6.1 say that Models 3–4 "did not produce significant structural results". That is not supported. In the saved original Model 4, two of the three paths had p < .001 (S → Governance, std .67; DA → Governance, std −.10). Neither model supports any substantive statement. The correct wording is that the outcome models are not identified or admissible as specified, and are therefore uninformative (see `the author's dissertation correction package`).

## 5. What is verified and what is not

| Claim | Status |
|---|---|
| Codes, counts, corrected sample, country composition | **Computed** from the v5.0 data object |
| S0 equals the saved original fits | **Verified** (Models 1–2 exact; Models 3–4 fit indices within 1e-4) |
| S1–S3 results | **Computed** (single run; deterministic) |
| Agreement with a fresh WVS v5.0 download | **Not checked**: CSV not available |
| Official v5.0 codebook | **Not inspected**: V6.0 report used (see audit §1) |
| Parallel analysis / EFA | **Not reproducible** |
| Cross-national measurement invariance, multilevel structure | **Not tested** (the design is pooled) |
