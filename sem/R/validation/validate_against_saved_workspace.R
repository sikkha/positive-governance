# Validates R/reconstructed/sem_models_reconstructed.R against the author's
# private saved workspace (NOT distributed: it contains the full WVS Wave 7
# respondent-level file). Usage (from the sem/ directory):
#   SEM_RDATA=/path/to/20250513_model1_SEM_governance.RData Rscript R/validation/validate_against_saved_workspace.R
suppressPackageStartupMessages(library(lavaan))
cat("lavaan", as.character(packageVersion("lavaan")), "| R", R.version.string, "\n")
source("R/reconstructed/sem_models_reconstructed.R")
rdata <- Sys.getenv("SEM_RDATA")
if (!nzchar(rdata) || !file.exists(rdata)) stop("Set SEM_RDATA to the saved workspace path.")
e <- new.env(); load(rdata, envir = e)
ok <- TRUE
dat <- prepare_wvs(e$wvs_data, "as_reported")
same <- isTRUE(all.equal(as.data.frame(dat), as.data.frame(e$wvs_filtered), check.attributes = FALSE))
cat(sprintf("[%s] preprocessing reproduces saved wvs_filtered (n=%d)\n", if (same) "ok" else "FAIL", nrow(dat))); ok <- ok && same
saved <- list(model1 = e$fit, model2 = e$fit2, model3 = e$fit3, model4 = e$fit4)
for (m in names(saved)) {
  syn_same <- identical(gsub("\\s+", " ", MODEL_SYNTAX[[m]]), gsub("\\s+", " ", e[[c(model1="model", model2="model2", model3="model3", model4="model4")[[m]]]]))
  f <- sem(MODEL_SYNTAX[[m]], data = dat, estimator = "MLR")
  d <- max(abs(coef(f) - coef(saved[[m]])))
  fi <- max(abs(fitMeasures(f, c("cfi","tli","rmsea.scaled","srmr")) - fitMeasures(saved[[m]], c("cfi","tli","rmsea.scaled","srmr"))))
  # Models 3 and 4 are empirically ill-conditioned (non-positive-definite latent
  # covariance / negative latent variance, non-PD vcov): optimiser end points differ
  # slightly across lavaan versions, so only fit indices are compared, at 1e-3.
  strict <- m %in% c("model1", "model2")
  pass <- syn_same && (if (strict) d < 1e-6 && fi < 1e-6 else fi < 1e-3)
  pc <- tryCatch(lavInspect(f, "post.check"), warning = function(w) FALSE)
  cat(sprintf("[%s] %s (%s): syntax identical=%s, max|coef diff|=%.2e, max|fit diff|=%.2e, post.check=%s\n",
      if (pass) "ok" else "FAIL", m, if (strict) "strict" else "fit-indices only", syn_same, d, fi, pc))
  ok <- ok && pass
}
cat(if (ok) "=== SEM RECONSTRUCTION VALIDATED ===\n" else "=== VALIDATION FAILED ===\n")
