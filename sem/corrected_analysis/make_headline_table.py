#!/usr/bin/env python3
"""Build results/original_vs_corrected_headline.csv from results/sem_results_long.csv.
Adds the value reported in dissertation v1.2 (Ch. 4) where one exists. Stdlib only.
Run from sem/:  python corrected_analysis/make_headline_table.py"""
import csv
from pathlib import Path

R = Path(__file__).resolve().parent / "results"
rows = list(csv.DictReader(open(R / "sem_results_long.csv")))
specs = ["S0_original_reconstruction", "S1_corrected_mlr", "S2_corrected_wlsmv_ordinal", "S3_corrected_mlr_weighted"]
keys = [("estimation", "converged"), ("estimation", "n_obs"), ("estimation", "estimator"), ("identification", "df"),
        ("identification", "vcov_positive_definite"), ("admissibility", "lavaan_post_check_passed"),
        ("admissibility", "cov_lv_positive_definite"), ("admissibility", "n_negative_residual_variances"),
        ("admissibility", "n_negative_latent_variances"), ("admissibility", "max_abs_std_loading"),
        ("admissibility", "max_abs_latent_correlation")]
keys += [("fit", k) for k in ["chisq", "chisq.scaled", "cfi", "tli", "cfi.scaled", "tli.scaled", "cfi.robust",
                              "tli.robust", "rmsea", "rmsea.scaled", "rmsea.robust", "srmr"]]
keys += [("std_loading", "Z =~ Rule_of_Law"), ("std_loading", "Z =~ Democratic_Accountability"),
         ("latent_correlation", "State_Capacity ~~ Z"), ("latent_correlation", "State_Capacity ~~ Rule_of_Law"),
         ("latent_correlation", "State_Capacity ~~ Democratic_Accountability"),
         ("latent_correlation", "Rule_of_Law ~~ Democratic_Accountability")]
keys += [("std_loading", f"State_Capacity =~ {i}") for i in ["Q65", "Q71", "Q72", "Q73"]]
keys += [("std_loading", f"Rule_of_Law =~ {i}") for i in ["Q69", "Q70"]]
keys += [("std_loading", f"Democratic_Accountability =~ {i}") for i in ["Q224", "Q229"]]
reported = {("model1", "fit", "cfi"): ".889", ("model1", "fit", "tli"): ".817", ("model1", "fit", "rmsea.scaled"): ".144",
            ("model1", "fit", "srmr"): ".073", ("model1", "estimation", "n_obs"): "94278",
            ("model1", "std_loading", "State_Capacity =~ Q65"): ".583", ("model1", "std_loading", "State_Capacity =~ Q71"): ".860",
            ("model1", "std_loading", "State_Capacity =~ Q72"): ".628", ("model1", "std_loading", "State_Capacity =~ Q73"): ".631",
            ("model1", "std_loading", "Rule_of_Law =~ Q69"): ".830", ("model1", "std_loading", "Rule_of_Law =~ Q70"): ".878",
            ("model1", "std_loading", "Democratic_Accountability =~ Q224"): ".856",
            ("model1", "std_loading", "Democratic_Accountability =~ Q229"): ".868",
            ("model2", "std_loading", "Z =~ Rule_of_Law"): ".795", ("model2", "std_loading", "Z =~ Democratic_Accountability"): ".349"}
idx = {(r["spec"], r["model"], r["block"], r["parameter"]): r["value"] for r in rows}
with open(R / "original_vs_corrected_headline.csv", "w", newline="") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["model", "block", "parameter", "dissertation_v1.2_reported"] + specs)
    for m in ["model1", "model2", "model3", "model4"]:
        for k in keys:
            vals = [idx.get((s, m) + k, "") for s in specs]
            if any(vals):
                w.writerow([m, k[0], k[1], reported.get((m,) + k, "")] + vals)
print("wrote", R / "original_vs_corrected_headline.csv")
