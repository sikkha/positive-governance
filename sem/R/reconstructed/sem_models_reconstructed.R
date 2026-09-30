# =============================================================================
# RECONSTRUCTED SCRIPT — NOT AN ORIGINAL ANALYSIS FILE
# -----------------------------------------------------------------------------
# Purpose : Executable reconstruction of the SEM Models 1–4 reported in
#           Chapters 3–4 of the Positive Governance dissertation.
# Why     : No original executable script for Model 1 survives. The file
#           `R/original/20250513_model2_SEM_governance.R` is a 12-line
#           country-filter stub (it references an undefined object and fits no
#           model). The model syntax below is copied verbatim from character
#           objects `model`, `model2`, `model3`, `model4` saved in the private
#           workspace `20250513_model1_SEM_governance.RData`; the
#           preprocessing is copied from `R/original/Data_exploration.R` and
#           `R/original/other_SEM_check.R`.
# Validation: `R/validation/validate_against_saved_workspace.R` checks that this
#           script reproduces the saved preprocessed data frame
#           (`wvs_filtered`, identical) and the saved lavaan fits `fit`,
#           `fit2`, `fit3`, `fit4` (max |parameter difference| < 1e-6).
#           Result recorded in docs/reproducibility.md.
# Data    : WVS Wave 7 cross-national CSV v5.0 (not redistributed; see
#           docs/data_availability.md). Set WVS_CSV to its location.
# =============================================================================

suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(lavaan)
})

SEM_ITEMS <- c("Q65", "Q71", "Q72", "Q73",  # State capacity (confidence: armed forces, government, parties, parliament)
               "Q69", "Q70",                # Rule of law (confidence: police, courts)
               "Q224", "Q229")              # Democratic accountability (votes counted fairly; election officials fair)

#' Prepare the SEM analysis frame.
#'
#' negative_codes = "as_reported" reproduces the dissertation exactly: only
#'   NA values are dropped, then every item is reverse-coded as 5 - x. WVS
#'   encodes non-substantive answers as negative integers (-1 don't know,
#'   -2 no answer, -4 not asked, -5 missing), which the CSV reader does NOT
#'   treat as NA; under this option they become 6, 7, 9 and 10.
#' negative_codes = "as_missing" is a SENSITIVITY option (not the reported
#'   analysis): negative codes are set to NA before listwise deletion.
prepare_wvs <- function(wvs_data, negative_codes = c("as_reported", "as_missing")) {
  negative_codes <- match.arg(negative_codes)
  d <- wvs_data %>% select(all_of(SEM_ITEMS))
  if (negative_codes == "as_missing") {
    d <- d %>% mutate(across(everything(), ~ ifelse(. < 0, NA, .)))
  }
  d %>%
    filter(if_all(everything(), ~ !is.na(.))) %>%   # listwise deletion
    mutate(across(everything(), ~ 5 - .))           # reverse code (1<->4)
}

MODEL_SYNTAX <- list(
  model1 = '
  # Latent variables
  State_Capacity =~ Q65 + Q71 + Q72 + Q73
  Rule_of_Law =~ Q69 + Q70
  Democratic_Accountability =~ Q224 + Q229

  # Allow latent constructs to covary
  State_Capacity ~~ Rule_of_Law
  State_Capacity ~~ Democratic_Accountability
  Rule_of_Law ~~ Democratic_Accountability
',
  model2 = '
  # First-order latent variables
  State_Capacity =~ Q65 + Q71 + Q72 + Q73
  Rule_of_Law =~ Q69 + Q70
  Democratic_Accountability =~ Q224 + Q229

  # Second-order latent variable
  Z =~ Rule_of_Law + Democratic_Accountability

  # Correlation between State Capacity and Z
  State_Capacity ~~ Z
',
  model3 = '
  # First-order latent variables
  State_Capacity =~ Q65 + Q71 + Q72 + Q73
  Rule_of_Law =~ Q69 + Q70
  Democratic_Accountability =~ Q224 + Q229

  # Second-order latent variable
  Z =~ Rule_of_Law + Democratic_Accountability

  # Governance as a latent outcome
  Governance =~ Q71 + Q70 + Q224 + Q229

  # Structural relationship
  Governance ~ State_Capacity + Z
',
  model4 = '
  # First-order latent variables
  State_Capacity =~ Q65 + Q71 + Q72 + Q73
  Rule_of_Law =~ Q69 + Q70
  Democratic_Accountability =~ Q224 + Q229

  # Governance as a second-order latent variable (defined by key manifest indicators)
  Governance =~ Q71 + Q70 + Q224 + Q229

  # Structural model
  Governance ~ State_Capacity + Rule_of_Law + Democratic_Accountability
'
)

# Saved fits were produced by lavaan::sem(..., estimator = "MLR") with
# lavaan 0.6-15 (se = robust.huber.white, test = yuan.bentler.mplus).
fit_models <- function(dat, which = names(MODEL_SYNTAX)) {
  lapply(setNames(which, which), function(m) sem(MODEL_SYNTAX[[m]], data = dat, estimator = "MLR"))
}

# The dissertation's reported Model 1 indices mix conventions:
# CFI (.889) and TLI (.817) are the standard (unscaled) indices,
# RMSEA (.144) is the scaled index, SRMR (.073) is standard.
REPORT_INDICES <- c("chisq", "chisq.scaled", "df", "cfi", "tli", "cfi.scaled", "tli.scaled",
                    "cfi.robust", "tli.robust", "rmsea", "rmsea.scaled", "rmsea.robust", "srmr")

summarise_fit <- function(fit) round(fitMeasures(fit, REPORT_INDICES), 4)

if (sys.nframe() == 0L) {
  csv <- Sys.getenv("WVS_CSV", "data/WVS_Cross-National_Wave_7_csv_v5_0.csv")
  mode <- Sys.getenv("SEM_NEGATIVE_CODES", "as_reported")
  if (!file.exists(csv)) stop("WVS CSV not found at '", csv, "'. See sem/README.md for acquisition.")
  wvs <- read_csv(csv, show_col_types = FALSE)
  dat <- prepare_wvs(wvs, negative_codes = mode)
  cat("Negative-code handling:", mode, " | analysis n =", nrow(dat), "\n")
  fits <- fit_models(dat)
  for (m in names(fits)) {
    cat("\n=====", m, "=====\n")
    print(summarise_fit(fits[[m]]))
    ss <- standardizedSolution(fits[[m]])
    print(ss[ss$op %in% c("=~", "~", "~~") & ss$lhs != ss$rhs, c("lhs", "op", "rhs", "est.std", "pvalue")])
  }
}
