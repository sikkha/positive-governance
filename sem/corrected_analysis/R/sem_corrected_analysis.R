# =============================================================================
# SEM corrected analysis — coding audit, corrected re-estimation, sensitivity
# -----------------------------------------------------------------------------
# Specifications (all four measurement/structural models are UNCHANGED from the
# dissertation; only data handling and, for S2/S3, the estimator/weights change):
#
#   S0  original_reconstruction   negative WVS codes kept (as in the dissertation),
#                                 reverse-coded 5-x, ML with robust (MLR) corrections,
#                                 continuous indicators, unweighted, pooled.
#   S1  corrected_mlr             negative WVS codes (-1,-2,-4,-5) -> NA BEFORE reverse
#                                 coding; listwise deletion on the 8 items; otherwise
#                                 identical to S0. Isolates the effect of cleaning.
#   S2  corrected_wlsmv_ordinal   SENSITIVITY: same corrected sample, the 8 items declared
#                                 ordered (4 categories), estimator WLSMV (DWLS + robust
#                                 SE + mean-and-variance adjusted test), polychoric input.
#   S3  corrected_mlr_weighted    SENSITIVITY: S1 with WVS sampling weight W_WEIGHT
#                                 (within-country weight; countries NOT equalised).
#
# Identification (all specs): lavaan::sem() defaults — first loading of each factor
# fixed to 1 (marker), latent variances free; the second-order factor Z (Model 2/3)
# uses Rule_of_Law as marker. Standardized solutions are reported (std.all).
#
# Input: either WVS_CSV (the WVS Wave 7 v5.0 CSV) or WVS_RDATA (the author's private
# workspace, object `wvs_data`, which is the same CSV read with readr::read_csv).
# Output: aggregate statistics only (no respondent-level data) under OUT_DIR.
#
# Run from sem/:  WVS_CSV=… Rscript corrected_analysis/R/sem_corrected_analysis.R
# =============================================================================

suppressPackageStartupMessages({ library(readr); library(dplyr); library(lavaan) })

ITEMS <- c("Q65", "Q71", "Q72", "Q73", "Q69", "Q70", "Q224", "Q229")
VALID <- 1:4
MISSING_CODES <- c(`-1` = "Don't know", `-2` = "No answer", `-4` = "Not asked", `-5` = "Missing; Not available")
OUT_DIR <- Sys.getenv("OUT_DIR", "corrected_analysis/results")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

MODELS <- list(
  model1 = '
  State_Capacity =~ Q65 + Q71 + Q72 + Q73
  Rule_of_Law =~ Q69 + Q70
  Democratic_Accountability =~ Q224 + Q229
  State_Capacity ~~ Rule_of_Law
  State_Capacity ~~ Democratic_Accountability
  Rule_of_Law ~~ Democratic_Accountability
',
  model2 = '
  State_Capacity =~ Q65 + Q71 + Q72 + Q73
  Rule_of_Law =~ Q69 + Q70
  Democratic_Accountability =~ Q224 + Q229
  Z =~ Rule_of_Law + Democratic_Accountability
  State_Capacity ~~ Z
',
  model3 = '
  State_Capacity =~ Q65 + Q71 + Q72 + Q73
  Rule_of_Law =~ Q69 + Q70
  Democratic_Accountability =~ Q224 + Q229
  Z =~ Rule_of_Law + Democratic_Accountability
  Governance =~ Q71 + Q70 + Q224 + Q229
  Governance ~ State_Capacity + Z
',
  model4 = '
  State_Capacity =~ Q65 + Q71 + Q72 + Q73
  Rule_of_Law =~ Q69 + Q70
  Democratic_Accountability =~ Q224 + Q229
  Governance =~ Q71 + Q70 + Q224 + Q229
  Governance ~ State_Capacity + Rule_of_Law + Democratic_Accountability
')

# ---------------------------------------------------------------- load data
load_wvs <- function() {
  csv <- Sys.getenv("WVS_CSV"); rd <- Sys.getenv("WVS_RDATA")
  if (nzchar(csv)) return(list(data = read_csv(csv, show_col_types = FALSE), source = paste("WVS_CSV", basename(csv))))
  if (nzchar(rd)) { e <- new.env(); load(rd, envir = e); return(list(data = e$wvs_data, source = paste("WVS_RDATA wvs_data from", basename(rd)))) }
  stop("Set WVS_CSV (WVS Wave 7 v5.0 CSV) or WVS_RDATA (author workspace).")
}
L <- load_wvs(); wvs <- L$data
stopifnot(all(c(ITEMS, "B_COUNTRY", "B_COUNTRY_ALPHA", "W_WEIGHT") %in% names(wvs)))
cat("Data source:", L$source, "| rows:", nrow(wvs), "| version:", paste(unique(wvs$version), collapse = ";"), "\n")

# ---------------------------------------------------------------- 1. coding audit
code_tab <- do.call(rbind, lapply(ITEMS, function(v) {
  x <- wvs[[v]]; t <- table(x, useNA = "ifany")
  data.frame(item = v, code = names(t), n = as.integer(t),
             status = ifelse(names(t) %in% as.character(VALID), "valid",
                      ifelse(names(t) %in% names(MISSING_CODES), paste0("missing_code: ", MISSING_CODES[names(t)]),
                      ifelse(is.na(names(t)), "NA", "UNEXPECTED"))))
}))
stopifnot(!any(code_tab$status == "UNEXPECTED"))
write.csv(code_tab, file.path(OUT_DIR, "coding_audit_value_counts.csv"), row.names = FALSE)

miss_item <- do.call(rbind, lapply(ITEMS, function(v) {
  x <- wvs[[v]]
  data.frame(item = v, n_total = length(x), n_valid = sum(x %in% VALID),
             n_dont_know = sum(x == -1, na.rm = TRUE), n_no_answer = sum(x == -2, na.rm = TRUE),
             n_not_asked = sum(x == -4, na.rm = TRUE), n_missing_na = sum(x == -5, na.rm = TRUE),
             n_system_NA = sum(is.na(x)),
             pct_invalid = round(100 * mean(!(x %in% VALID)), 2))
}))
write.csv(miss_item, file.path(OUT_DIR, "missingness_by_item.csv"), row.names = FALSE)

X <- as.data.frame(wvs[, ITEMS])
invalid_any <- !apply(X, 1, function(r) all(r %in% VALID))
n_items_invalid <- rowSums(!sapply(X, function(c) c %in% VALID))
affected <- data.frame(n_items_invalid = 0:8, respondents = as.integer(table(factor(n_items_invalid, levels = 0:8))))
write.csv(affected, file.path(OUT_DIR, "respondents_by_number_of_invalid_items.csv"), row.names = FALSE)

# country composition
cc <- wvs %>% mutate(.ok = !invalid_any) %>% group_by(B_COUNTRY, B_COUNTRY_ALPHA) %>%
  summarise(n_original = n(), n_corrected = sum(.ok), .groups = "drop") %>%
  mutate(pct_retained = round(100 * n_corrected / n_original, 1),
         items_not_asked = sapply(B_COUNTRY, function(b) paste(ITEMS[sapply(ITEMS, function(v) all(wvs[[v]][wvs$B_COUNTRY == b] == -4))], collapse = " ")))
write.csv(cc, file.path(OUT_DIR, "country_composition.csv"), row.names = FALSE)

prep <- function(mode) {
  d <- wvs[, c(ITEMS, "B_COUNTRY", "W_WEIGHT")]
  if (mode == "corrected") d[ITEMS] <- lapply(d[ITEMS], function(x) ifelse(x %in% VALID, x, NA))
  d <- d[complete.cases(d[ITEMS]), ]
  d[ITEMS] <- lapply(d[ITEMS], function(x) 5 - x)
  as.data.frame(d)
}
d_orig <- prep("original"); d_corr <- prep("corrected")

summary_counts <- data.frame(
  quantity = c("original_rows", "respondents_with_any_invalid_or_missing_item", "pct_affected",
               "original_analytic_n (S0)", "corrected_analytic_n (S1-S3)", "countries_original", "countries_corrected",
               "countries_losing_all_respondents"),
  value = c(nrow(wvs), sum(invalid_any), round(100 * mean(invalid_any), 2), nrow(d_orig), nrow(d_corr),
            length(unique(wvs$B_COUNTRY)), length(unique(d_corr$B_COUNTRY)),
            paste(cc$B_COUNTRY_ALPHA[cc$n_corrected == 0], collapse = " ")))
write.csv(summary_counts, file.path(OUT_DIR, "sample_summary.csv"), row.names = FALSE)
print(summary_counts)

# descriptives and correlations (Chapter 3 §3.3.1 reports these for the original coding)
skew <- function(x) { m <- mean(x); mean((x - m)^3) / sd(x)^3 }
exkurt <- function(x) { m <- mean(x); mean((x - m)^4) / sd(x)^4 - 3 }
desc <- do.call(rbind, lapply(c("original", "corrected"), function(k) {
  d <- if (k == "original") d_orig else d_corr
  do.call(rbind, lapply(ITEMS, function(v) data.frame(coding = k, item = v, n = nrow(d), mean = round(mean(d[[v]]), 3),
    sd = round(sd(d[[v]]), 3), min = min(d[[v]]), max = max(d[[v]]), skew = round(skew(d[[v]]), 3), excess_kurtosis = round(exkurt(d[[v]]), 3))))
}))
write.csv(desc, file.path(OUT_DIR, "item_descriptives_original_vs_corrected.csv"), row.names = FALSE)
cor_long <- function(M, label) { i <- which(upper.tri(M), arr.ind = TRUE)
  data.frame(correlation = label, item_a = rownames(M)[i[, 1]], item_b = colnames(M)[i[, 2]], r = round(M[i], 3)) }
cors <- rbind(cor_long(cor(d_orig[ITEMS]), "pearson_original_coding"),
              cor_long(cor(d_corr[ITEMS]), "pearson_corrected"),
              cor_long(lavCor(d_corr[ITEMS], ordered = ITEMS), "polychoric_corrected"))
write.csv(cors, file.path(OUT_DIR, "item_correlations_original_vs_corrected.csv"), row.names = FALSE)

# ---------------------------------------------------------------- 2. fitting + diagnostics
SPECS <- list(
  S0_original_reconstruction = list(data = d_orig, args = list(estimator = "MLR")),
  S1_corrected_mlr           = list(data = d_corr, args = list(estimator = "MLR")),
  S2_corrected_wlsmv_ordinal = list(data = d_corr, args = list(estimator = "WLSMV", ordered = ITEMS)),
  S3_corrected_mlr_weighted  = list(data = d_corr, args = list(estimator = "MLR", sampling.weights = "W_WEIGHT"))
)

safe <- function(expr) tryCatch(expr, error = function(e) NA, warning = function(w) suppressWarnings(expr))
eigmin <- function(m) if (is.null(m) || length(m) == 0) NA else min(eigen(as.matrix(m), symmetric = TRUE, only.values = TRUE)$values)

long <- list(); warn_log <- list()
add <- function(spec, model, block, parameter, value) long[[length(long) + 1]] <<-
  data.frame(spec = spec, model = model, block = block, parameter = parameter, value = as.character(value), stringsAsFactors = FALSE)

for (sp in names(SPECS)) for (m in names(MODELS)) {
  S <- SPECS[[sp]]; ws <- character(0)
  fit <- withCallingHandlers(
    do.call("sem", c(list(model = MODELS[[m]], data = quote(S$data)), S$args)),
    warning = function(w) { ws <<- c(ws, gsub("\\s+", " ", conditionMessage(w))); invokeRestart("muffleWarning") })
  conv <- lavInspect(fit, "converged"); add(sp, m, "estimation", "converged_default_iterations", conv)
  if (!conv) {  # diagnostic only: same model, more optimiser iterations; nothing else changed
    ws <- c(ws, "NOT CONVERGED with default iterations; refitted with control=list(iter.max=20000)")
    fit <- withCallingHandlers(
      do.call("sem", c(list(model = MODELS[[m]], data = quote(S$data), control = list(iter.max = 20000)), S$args)),
      warning = function(w) { ws <<- c(ws, gsub("\\s+", " ", conditionMessage(w))); invokeRestart("muffleWarning") })
    conv <- lavInspect(fit, "converged")
  }
  add(sp, m, "estimation", "converged", conv)
  warn_log[[paste(sp, m)]] <- data.frame(spec = sp, model = m, warning = if (length(ws)) ws else "(none)")
  add(sp, m, "estimation", "n_obs", lavInspect(fit, "nobs"))
  add(sp, m, "estimation", "estimator", lavInspect(fit, "options")$estimator)
  add(sp, m, "estimation", "n_free_parameters", lavInspect(fit, "npar"))
  if (!conv) { cat(sprintf("%-28s %-7s NOT CONVERGED (also with iter.max=20000) — no solution reported\n", sp, m)); next }
  add(sp, m, "identification", "df", fitMeasures(fit, "df"))
  vc <- safe(lavInspect(fit, "vcov")); ev <- if (is.matrix(vc)) eigmin(vc) else NA
  add(sp, m, "identification", "vcov_min_eigenvalue", signif(ev, 4))
  add(sp, m, "identification", "vcov_positive_definite", isTRUE(ev > 0))
  pc <- tryCatch({ withCallingHandlers(lavInspect(fit, "post.check"), warning = function(w) invokeRestart("muffleWarning")) }, error = function(e) NA)
  add(sp, m, "admissibility", "lavaan_post_check_passed", isTRUE(pc))
  est <- lavInspect(fit, "est")
  add(sp, m, "admissibility", "cov_lv_min_eigenvalue", signif(eigmin(est$psi), 4))
  add(sp, m, "admissibility", "cov_lv_positive_definite", isTRUE(eigmin(est$psi) > 0))
  th <- diag(est$theta)
  add(sp, m, "admissibility", "n_negative_residual_variances", sum(th < 0))
  add(sp, m, "admissibility", "n_negative_latent_variances", sum(diag(est$psi) < 0))
  ss <- standardizedSolution(fit, se = TRUE)
  add(sp, m, "admissibility", "max_abs_std_loading", round(max(abs(ss$est.std[ss$op == "=~"])), 4))
  lvcor <- ss[ss$op == "~~" & ss$lhs != ss$rhs & ss$lhs %in% lavNames(fit, "lv"), ]
  add(sp, m, "admissibility", "max_abs_latent_correlation", if (nrow(lvcor)) round(max(abs(lvcor$est.std)), 4) else NA)
  for (i in seq_len(nrow(ss))) {
    r <- ss[i, ]
    blk <- if (r$op == "=~") "std_loading" else if (r$op == "~") "std_regression" else if (r$op == "~~" && r$lhs == r$rhs && r$lhs %in% lavNames(fit, "ov")) "std_residual_variance" else if (r$op == "~~" && r$lhs == r$rhs) "std_latent_variance_or_disturbance" else if (r$op == "~~") "latent_correlation" else if (r$op == "|") "threshold" else NA
    if (!is.na(blk) && blk != "threshold") add(sp, m, blk, paste(r$lhs, r$op, r$rhs), round(r$est.std, 4))
  }
  for (v in names(th)) add(sp, m, "unstd_residual_variance", v, round(th[[v]], 4))
  fm_names <- c("chisq", "df", "pvalue", "chisq.scaled", "pvalue.scaled", "cfi", "tli", "cfi.scaled", "tli.scaled",
                "cfi.robust", "tli.robust", "rmsea", "rmsea.scaled", "rmsea.robust", "srmr")
  fm <- safe(fitMeasures(fit, fm_names))
  for (k in fm_names) add(sp, m, "fit", k, if (k %in% names(fm)) signif(unname(fm[[k]]), 6) else NA)
  cat(sprintf("%-28s %-7s conv=%s n=%d post.check=%s covlv.PD=%s negRes=%d CFI=%.3f\n", sp, m, conv,
              lavInspect(fit, "nobs"), isTRUE(pc), isTRUE(eigmin(est$psi) > 0), sum(th < 0), fm[["cfi"]]))
}
long <- do.call(rbind, long)
write.csv(long, file.path(OUT_DIR, "sem_results_long.csv"), row.names = FALSE)
write.csv(do.call(rbind, warn_log), file.path(OUT_DIR, "estimation_warnings.csv"), row.names = FALSE)

# original-vs-corrected wide table (S0 vs S1 isolates cleaning; S2/S3 = sensitivity)
w <- reshape(long[, c("spec", "model", "block", "parameter", "value")], idvar = c("model", "block", "parameter"),
             timevar = "spec", direction = "wide")
names(w) <- sub("^value\\.", "", names(w))
write.csv(w, file.path(OUT_DIR, "original_vs_corrected.csv"), row.names = FALSE)
writeLines(c(paste("R", R.version.string), paste("lavaan", as.character(packageVersion("lavaan"))),
             paste("data", L$source), paste("run", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"))),
           file.path(OUT_DIR, "session_info.txt"))
cat("Wrote results to", OUT_DIR, "\n")
