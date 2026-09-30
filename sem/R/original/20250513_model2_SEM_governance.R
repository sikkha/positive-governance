library(readr)     # to import CSV files
library(tidyverse) # for data manipulation and visualization

# Load the data
wvs_data <- read_csv(Sys.getenv("WVS_CSV", "data/WVS_Cross-National_Wave_7_csv_v5_0.csv"))  # publication copy: local absolute path replaced; see sem/README.md

# Filter for Sweden, Poland, and the US using their names
specific_countries_data <- religion_value_selected_countries %>%
  filter(B_COUNTRY %in% c("Sweden", "Poland", "US"))

# View the resulting data frame for Sweden, Poland, and the US
print(specific_countries_data)
