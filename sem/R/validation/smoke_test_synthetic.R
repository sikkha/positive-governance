# Software smoke test for R/reconstructed/sem_models_reconstructed.R.
# Uses SIMULATED 1–4 Likert data with injected WVS-style negative codes; it
# checks that the code runs and that the negative-code handling behaves as
# documented. It says nothing about the WVS results. Run from sem/.
suppressPackageStartupMessages(library(lavaan))
source("R/reconstructed/sem_models_reconstructed.R")
set.seed(20260930)
pop <- '
  State_Capacity =~ 0.7*Q65 + 0.8*Q71 + 0.8*Q72 + 0.8*Q73
  Rule_of_Law =~ 0.8*Q69 + 0.85*Q70
  Democratic_Accountability =~ 0.75*Q224 + 0.75*Q229
  State_Capacity ~~ 0.6*Rule_of_Law
  State_Capacity ~~ 0.4*Democratic_Accountability
  Rule_of_Law ~~ 0.5*Democratic_Accountability
'
sim <- simulateData(pop, sample.nobs = 3000, standardized = TRUE)
lik <- as.data.frame(lapply(sim[SEM_ITEMS], function(x) as.integer(cut(x, c(-Inf, -0.8, 0, 0.8, Inf)))))
neg <- sample(seq_len(nrow(lik)), 300)
lik$Q224[neg] <- sample(c(-1L, -2L, -4L, -5L), 300, replace = TRUE)
a <- prepare_wvs(lik, "as_reported"); b <- prepare_wvs(lik, "as_missing")
stopifnot(nrow(a) == 3000, max(a$Q224) %in% 6:10, nrow(b) == 2700, all(b >= 1 & b <= 4))
fits <- fit_models(b)
stopifnot(all(vapply(fits, lavInspect, logical(1), what = "converged")))
print(t(sapply(fits, summarise_fit))[, c("cfi", "tli", "rmsea.scaled", "srmr")])
cat("=== SEM SMOKE TEST PASSED (synthetic data) ===\n")
