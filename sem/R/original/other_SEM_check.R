# Load required libraries
library(tidyverse)
library(lavaan)

# Load the dataset
wvs_data <- read_csv(Sys.getenv("WVS_CSV", "data/WVS_Cross-National_Wave_7_csv_v5_0.csv"))  # publication copy: local absolute path replaced; see sem/README.md

# Select relevant variables (excluding Q71)
selected_vars <- c("Q65", "Q72", "Q73", "Q69", "Q70", "Q224", "Q229")

# Clean and reverse code
wvs_filtered <- wvs_data %>%
  select(all_of(selected_vars)) %>%
  filter(if_all(everything(), ~ !is.na(.))) %>%
  mutate(across(everything(), ~ 5 - .))  # Reverse Likert scale

# Define SEM model 4.1 (Q71 removed)
model_4_1 <- '
  # Latent constructs
  State_Capacity =~ Q65 + Q72 + Q73
  Rule_of_Law =~ Q69 + Q70
  Democratic_Accountability =~ Q224 + Q229

  # Governance as latent outcome (Q71 removed from indicators)
  Governance =~ Q70 + Q224 + Q229

  # Regress Governance on latent predictors
  Governance ~ State_Capacity + Rule_of_Law + Democratic_Accountability

  # Covariances among predictors
  State_Capacity ~~ Rule_of_Law
  State_Capacity ~~ Democratic_Accountability
  Rule_of_Law ~~ Democratic_Accountability
'

# Fit SEM model 4.1
fit_4_1 <- sem(model_4_1, data = wvs_filtered, estimator = "MLR")

# Output results
summary(fit_4_1, fit.measures = TRUE, standardized = TRUE)
