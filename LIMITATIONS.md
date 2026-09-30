# Limitations and known issues

## Scope of inference

- **SEM** estimates a pooled, unweighted, individual-level covariance structure of *perceptions*. Cross-national measurement invariance was not established. The SEM does not identify dynamics, equilibrium, causation or country types.
- **MCMEA** results are deductions from declared peaks, context functions, noise model and classifier thresholds. They change when the landscape changes (v2 vs v3). They are not estimates of real transition probabilities.
- **ABM** causal statements are within-model statements. There is no country-level historical validation. Several Level 1.3b stages ran at the frozen *minimum* sample sizes: Stage 4 has 240 runs of a preferred 432–768, and Stage 8 has 96 of a preferred 144–288. Stage 5/6 persistence and erasure tests use one representative cell. See `abm/docs/level1.3b_completion_report.md` §6.
- **Verification is not replication.** Test suites, smoke runs and recomputation of stored outputs confirm that the software reproduces the archived results. They do not confirm the scientific claims, and the expensive ABM ensembles were not re-run for this package.

## Known issues (found during packaging)

### SEM

1. **WVS negative missing-value codes were analysed as valid responses.** Reverse coding (`5 − x`) turned −1/−2/−4/−5 into 6/7/9/10. 17,756 of the 94,278 respondents are affected, and the reported "complete-case n = 94,278" is the whole file. **Corrected re-estimation** (missing codes set to NA before reverse coding; same MLR estimator; n = 76,522, 61 countries) is in `sem/corrected_analysis/` and `docs/sem_corrected_results.md`. The dissertation text itself is not yet corrected; proposed replacements are prepared separately. The corrected results were computed from the author's v5.0 data object, not from a fresh download.
2. **Model 2 as reported is an improper solution.** The standardized S–Z covariance is 1.089 and the latent covariance matrix is not positive definite. **After correction Model 2 is admissible** (r(S, Z) = .83), but it is just-identified, so its fit equals Model 1's. **Models 3 and 4 are not identified or admissible under any specification**, original or corrected, MLR or WLSMV: the outcome factor reuses the predictors' indicators. They are not interpreted.
3. The reported Model 1 fit indices **mix standard (CFI, TLI) and scaled (RMSEA) conventions**.
4. **No original Model 1 script exists.** `20250513_model2_SEM_governance.R` is a filter stub that fits no model. A labelled reconstruction reproduces the saved fits exactly for Models 1–2 and to within 1e-4 on fit indices for Models 3–4.
5. Chapter 3 contradicts itself on missing data (pairwise vs listwise) and on weighting.
6. The EFA, the parallel analysis and the Q164/refined/18-item exploratory CFA variants have no preserved scripts.
6a. The official WVS v5.0 codebook was not located. The V6.0 variables report (third-party mirror) was used, and the observed codes are consistent with it. There is no checksum for the original CSV. The Chapter 3 descriptive statistics and correlations are not reproduced under either coding (`docs/sem_data_coding_audit.md` §6).

### MCMEA

7. **Chapter 5 and Chapter 7 disagree.** Chapters 6 and 7 still carry an older "recovered article" account (IE in 60/60 generations) that no code in this repository reproduces. See `docs/mcmea_specification_audit.md`.
8. The v3 evidence notebook contains **hidden execution-order state**: diagnostic cells were run before the example cell was switched to `anglo`.
9. The code for the Chapter 5 §5.7 **TimesFM supplementary temporal experiment** is missing. Its results are not verified (`docs/mcmea_timesfm_status.md`).
10. v2's `base_elite`, `base_cx_rate` and `base_mut_rate` arguments are unused. Both notebooks fill unobserved Markov rows with a diagonal 1 in the plotted matrix.
11. The acronym is expanded inconsistently: "Markov-Chain Macrostate Evolutionary Algorithm" (Ch. 1, notebooks) vs "Markov Chain–Memetic Evolutionary Algorithm" (Ch. 5 index, Ch. 6).

### ABM

12. `abm/README.md`'s status section is out of date: it says Level 1.2b is in progress, but Levels 1.3 and 1.3b are complete. A publication note has been added at the top.
13. Experiment scripts write to `outputs/` relative to the working directory. **Mitigated in the publication copy:** every script's `__main__` block now starts with a guard (`experiments/_archive_guard.py`). The guard refuses to run in the archive root unless an explicit output directory outside `outputs/` is given. Re-runs go through `experiments/run_isolated.py --out-dir DIR`. The test session runs in a scratch copy (`tests/conftest.py`), and `tests/test_zz_archive_integrity.py` checks all 200 archived files against `ARCHIVED_OUTPUTS.sha256`. Model code is unchanged. The legacy Level 0.3b snapshot is **not** guarded: run it only in a copy.
14. In the publication copy, `tests/test_level13b_cross_process_reproducibility.py` had a hard-coded working directory (an absolute path from the development workspace). It was replaced with a repository-relative path. The test logic is unchanged.
15. `abm/docs/level13b_preregistration.md` does not follow the `level1.3b_*` naming (disclosed in the original completion report).
16. The legacy snapshot's original `.gitignore` excluded `outputs/`; its two output rules are commented out in the publication copy so that the Level 0.x evidence is tracked.
17. The version pins in `pyproject.toml` are lower bounds only. The environment used to produce the archived outputs was not recorded. The test suite passes with current releases (see `docs/reproducibility.md`).

### Paper

18. `paper/Makefile`'s `figures` target calls a non-existent `scripts/make_conceptual_diagram_check.py`. The error is ignored.
19. `paper/README.md` still names `11_reproducibility.tex`; the file is `13_reproducibility.tex`. It also refers to git tags whose history is not included in this repository.
20. The paper's claim D1 cites "Dissertation Proposal X.1 Rev.10.1". Those SEM fit values are affected by SEM issues 1–3 above.

### Packaging

21. There is no licence file yet (see README). The ABM's `pyproject.toml` declares `MIT` as metadata only.
22. Development logs (`abm/dev_mem/`, `paper/dev_mem/`) are published with local paths replaced by placeholders. They record AI-assisted development sessions.
