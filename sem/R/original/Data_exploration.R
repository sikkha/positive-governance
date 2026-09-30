# === Dataset Exploration and Descriptive Statistics ===


# Load required libraries
library(tidyverse)
library(psych)        # for descriptive statistics
library(moments)      # for skewness and kurtosis
library(ggplot2)

# Load and preprocess data (as before)
wvs_data <- read_csv(Sys.getenv("WVS_CSV", "data/WVS_Cross-National_Wave_7_csv_v5_0.csv"))  # publication copy: local absolute path replaced; see sem/README.md

selected_vars <- c("Q65", "Q71", "Q72", "Q73",  # State Capacity
                   "Q69", "Q70",                # Rule of Law
                   "Q224", "Q229")              # Democratic Accountability

# Filter and reverse code (1 = high confidence → 4 = low confidence)
wvs_filtered <- wvs_data %>%
  select(all_of(selected_vars)) %>%
  filter(if_all(everything(), ~ !is.na(.))) %>%
  mutate(across(everything(), ~ 5 - .))

# --- 1. Basic summary statistics ---
summary_stats <- describe(wvs_filtered)
print(summary_stats[, c("n", "mean", "sd", "min", "max", "skew", "kurtosis")])

# --- 2. Check skewness direction for each variable ---
apply(wvs_filtered, 2, skewness, na.rm = TRUE)

# Interpretation tip:
#   skewness > 0 → right-skewed (tail to the right)
#   skewness < 0 → left-skewed (tail to the left)
#   skewness ≈ 0 → approximately symmetric

# --- 3. Visualize distributions ---
wvs_filtered_long <- wvs_filtered %>%
  pivot_longer(cols = everything(), names_to = "Variable", values_to = "Value")

ggplot(wvs_filtered_long, aes(x = Value, fill = Variable)) +
  geom_histogram(binwidth = 1, color = "black", alpha = 0.6, position = "dodge") +
  facet_wrap(~ Variable, ncol = 4) +
  theme_minimal() +
  labs(title = "Distribution of Governance Indicators (Reversed Scale)",
       x = "Confidence Level (Higher = More Confidence)",
       y = "Frequency")

# --- 4. Correlation matrix (for overview of relationships) ---
cor_matrix <- cor(wvs_filtered)
print(round(cor_matrix, 3))

# Optional visualization:
library(corrplot)
corrplot(cor_matrix, method = "color", type = "upper", tl.col = "black")
