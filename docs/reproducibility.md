# Reproducibility

This page separates three levels of evidence:

- **Software verification**: the code installs, imports, passes its tests and runs.
- **Recomputation of recorded outputs**: stored numbers are regenerated from seeds and match exactly.
- **Scientific replication**: an independent re-run of the full experimental programme, ideally by others and on fresh data.

This package delivers the first two where marked. **It does not claim full scientific replication.** The expensive ABM ensembles were *not* re-run during packaging. Their archived outputs were inspected and checked against the reported numbers.

All commands are run from the repository root unless a `cd` is shown.

## Verification record (packaging run, 2026-09-30)

| Component | Command | Environment | Result | Level |
|---|---|---|---|---|
| ABM install/import | `pip install -e "abm[dev]"` | fresh venv, Python 3.11.15; numpy 2.4.6, scipy 1.17.1, pandas 3.0.6, scikit-learn 1.9.1, networkx 3.6.1, matplotlib 3.11.2, pytest 9.1.1 | installed, CLI entry point OK | software |
| ABM full test suite | `cd abm && python -m pytest -q -W error -p no:cacheprovider` | same, 2 vCPU | First packaging run: 2047 passed, 6 skipped (equals the Level 1.3b count), but it rewrote 56 archived PNGs. **After output isolation: 2054 passed, 6 skipped, 0 failed in 17 min 36 s; all 200 archived outputs byte-identical** | software |
| ABM demo run | `abm-governance run --seed 0 --steps 200 --out /tmp/abm_demo` | Python 3.10.12 (author's machine VM), numpy 2.2.6 | 7 output files, **1.2 s** | software |
| ABM reference run | one `SimulationConfig.level12b_frozen_reference(seed=1)` run (60 agents, 500 steps, 4 patches) | Python 3.11.15 | **4.0 s** | software |
| ABM archived-claim check | `python tools/check_archived_claims.py` | stdlib only | **21/21 checks pass** (dissertation §6–7 and paper numbers equal archived JSON) | archived evidence (not re-run) |
| ABM preregistration hash | `load_and_verify_manifest('outputs/level13b_preregistration')` | — | hash `f6498c0e…57c0` verified | archived evidence |
| Legacy Level 0.3b tests | `cd legacy/abm_governance_level0.3b && python -m pytest -q` (separate venv) | Python 3.11.15, separate venv | **539 passed in 68 s**; legacy outputs byte-identical afterwards | software |
| MCMEA recorded outputs | `python mcmea/scripts/reproduce_recorded_outputs.py` | Python 3.10.12, numpy 2.2.6 | **all 14 stored values reproduced**, 56 s | recomputation |
| MCMEA clean notebooks | headless nbclient execution of `mcmea/notebooks/clean/*.ipynb` | Python 3.11.15, numpy 2.x | v2 20 s, v3 58 s, no errors | software (see hidden-state note) |
| SEM reconstruction | `SEM_RDATA=… Rscript sem/R/validation/validate_against_saved_workspace.R` | R 4.3.3, lavaan 0.6-17 | Models 1–2 identical (< 1e-11); Models 3–4 fit indices within 1e-4 | recomputation against **private** workspace |
| SEM smoke test | `cd sem && Rscript R/validation/smoke_test_synthetic.R` | R 4.3.3, lavaan 0.6-17 | passes on simulated data, 6.5 s | software |
| Paper build | `cd paper && make verify` | TeX Live 2023, pdfTeX 1.40.25, biber 2.19, latexmk | **93 pages, 0 LaTeX warnings, `=== VERIFY PASSED ===`** (7/7 checks), 22 s | software |
| CITATION.cff | `cffconvert --validate` | cffconvert 2.x | valid (schema 1.2.0) | — |

## SEM

- **Data:** WVS Wave 7 cross-national CSV v5.0 (see `data_availability.md`). Not included.
- **Environment:** R ≥ 4.1; `readr`, `dplyr`, `lavaan`. The original fits used lavaan 0.6-15; the corrected analysis was run with lavaan 0.6-17 on R 4.3.3.
- **Original analysis (as reported, S0):** select Q65, Q71, Q72, Q73, Q69, Q70, Q224, Q229 → drop rows with `NA` → reverse-code `5 − x` → `lavaan::sem(estimator = "MLR")`, unweighted. **Defect:** WVS negative codes are not `NA` and survive this pipeline (`sem_data_coding_audit.md`). Command: `WVS_CSV=… Rscript sem/R/reconstructed/sem_models_reconstructed.R`. Expected output: `sem/expected/saved_workspace_fit_indices.csv` (Model 1: n = 94,278, CFI .8888, TLI .8169, RMSEA(scaled) .1435, SRMR .0731).
- **Corrected analysis (S1) and sensitivity (S2 ordinal WLSMV, S3 weighted):**
  ```bash
  cd sem
  WVS_CSV=/path/to/WVS_Cross-National_Wave_7_csv_v5_0.csv Rscript corrected_analysis/R/sem_corrected_analysis.R
  python corrected_analysis/make_headline_table.py
  ```
  Expected output: `sem/corrected_analysis/results/original_vs_corrected_headline.csv`. S1 Model 1: n = 76,522, CFI .9495, TLI .9169, RMSEA(scaled) .0880, SRMR .0529. Runtime ≈ 45 s.
- **Verification status:** S0 is verified against the saved fits. S1–S3 were **computed** from the author's v5.0 data object and have **not** yet been re-run from a fresh CSV download. The official v5.0 codebook was not inspected (the V6.0 variables report was used).
- **Seeds:** none needed (deterministic estimation).

## MCMEA

- **Environment:** Python ≥ 3.10, numpy, matplotlib, pandas (`mcmea/requirements.txt`). No network, credentials or local paths.
- **Seeds:** example runs use seed 7. Repeated runs use seeds 20–59. v3 profiles are passed explicitly (`profile=None` would draw one at random).
- **Expected output:** `mcmea/expected/recorded_notebook_outputs.json`. v3 repeated runs: east 34 A / 6 C, anglo 23 / 17, europe 29 / 11.
- **Notebook state:** the v3 evidence notebook's diagnostic outputs come from an earlier east-profile execution. The clean copy documents this. The script reproduces the recorded values without notebook state.
- **Not reproducible here:** the "recovered article" specification cited in Ch. 7 and the TimesFM experiment (Ch. 5 §5.7). No code is available for either (`mcmea_specification_audit.md`).

## ABM

### Quick demonstration (seconds)

The demo run writes only to the `--out` path you give.

```bash
pip install -e "abm[dev]"
abm-governance run --seed 0 --steps 200 --out /tmp/abm_demo
pytest -q abm/tests/test_level13b_cross_process_reproducibility.py   # 3 fresh processes must agree exactly
python tools/check_archived_claims.py
```

### Test suite (≈18 min on 2 vCPU)

```bash
cd abm && python -m pytest -q -W error -p no:cacheprovider
```

The session runs in a scratch working directory (`tests/conftest.py`):
- `outputs/` is **copied** there;
- `docs/`, `experiments/`, `src/` and `tests/` are symlinked.

Tests that regenerate figures therefore write into the scratch copy. Before this change, a test run rewrote 56 archived PNGs in place. `tests/test_zz_archive_integrity.py` runs last and requires every archived output to match `ARCHIVED_OUTPUTS.sha256`, with no files added or missing. `tests/test_output_isolation.py` checks four things:
- the scratch working directory is in use;
- every experiment `__main__` is guarded;
- the guard's refusal logic works;
- the isolated runner writes figures outside the archive and rejects an out-dir inside it.

**Packaging run (2026-09-30):** **2054 passed, 6 skipped, 0 failed, 0 warnings in 17 min 36 s** (2047 original tests + 7 new). Before/after SHA-256 of all 200 archived output files: **unchanged**.

### Re-running experiments without touching the archive

Every experiment script's `__main__` block begins with `experiments/_archive_guard.py`. Run in the archive root (marker file `ARCHIVED_OUTPUTS.sha256`), the guard exits with status 2 before any work, unless an explicit `--out`/`--out-dir`/`--out-root` outside `outputs/` is given, or `ABM_ALLOW_ARCHIVE_OVERWRITE=1` is set. Model and analysis code are unchanged.

Use the isolating runner. It accepts an explicit output directory for **any** script:

```bash
cd abm
python experiments/run_isolated.py level13b_stage6_history_erasure.py --out-dir /tmp/abm_rerun
#   extra script arguments go after "--", e.g. for Level 0.x scripts:
python experiments/run_isolated.py phase_sweep.py --out-dir /tmp/abm_rerun -- --stage1-points 32
```

The runner does four things:
1. Copies the archived `outputs/` into `DIR/outputs`, so that upstream stage inputs resolve.
2. Runs the unmodified script with working directory `DIR`.
3. Writes `DIR/rerun_manifest.json`, listing each file as new, modified or unchanged relative to the archive.
4. Re-verifies the archive checksums.

**Packaging demonstration.** `run_isolated.py level13b_stage7_model_comparison.py` fits the archived Stage 4 pool with no new simulations. It took 3.4 s, archive checksums stayed intact, and the regenerated `stage7_report.json` is **numerically identical** to the archived one. The only difference is one float in the 16th significant digit (`reconstruction_error` 4.088823819325485 vs …488), from BLAS/scikit-learn versions.

### Full research experiments (hours; not re-run for packaging)

Run each stage through `run_isolated.py`, with the same `--out-dir` for a whole chain so that later stages read the re-run upstream results. Designs, seeds and sample sizes are frozen in the preregistration modules and manifests. Each script refuses to proceed past its own failing smoke test.

```bash
cd abm
R=/tmp/abm_rerun
# Level 1.2b (576 discovery + 384 confirmation runs). Stage letters follow data dependencies
# (e.g. l3 reads l1+l2; o reads k, l2, l3, m; q reads e…n), so run them alphabetically:
for s in c_feasibility_map d_institutional_design e_joint_discovery g_temporal_representation \
         h_recurrence_spec i_preregistration_manifest j_main_discovery_pipeline k_clustering_discovery \
         l0_confirmation_registry l1_confirmation_pool l2_discovery_pool_refit l3_prospective_confirmation \
         m_scaling_robustness n_causal_collapse_decomposition o_phenotype_recurrence_classification \
         q_statistical_requirements_audit r_testing_requirements_audit; do
  python experiments/run_isolated.py level12b_stage_${s}.py --out-dir $R
done
python experiments/run_isolated.py make_level12b_visualizations.py --out-dir $R

# Level 1.3b
for s in preregistration stage0_frozen_compatibility stage1_bargaining_audit stage2_bargaining_calibration \
         stage3_matched_sequencing_factorial stage4_homogeneous_discovery stage5_temporal_persistence \
         stage6_history_erasure stage7_model_comparison stage8_fresh_confirmation stage9_measurement_audit \
         stage10_ecological_control_scale_shock; do
  python experiments/run_isolated.py level13b_${s}.py --out-dir $R
done
python experiments/run_isolated.py make_level13b_visualizations.py --out-dir $R
```

Run counts for Level 1.3b: Stage 2 has 96, Stage 3 216, Stage 4 240, Stage 5 80, Stage 6 72 (12 seeds × 6 arms, sham-controlled), Stage 7 0, Stage 8 96 (disjoint design and simulation seeds), Stage 9 240 (deterministic re-run of Stage 4 seeds), Stage 10 24.

**Resources.** Stage runtimes were not recorded in the source materials and were not measured here. A single Level 1.3b-sized run (40–60 agents, 500 steps) takes about 4 s on one core, so the ≈1,100 Level 1.3b runs suggest roughly **1–3 CPU-hours**, and Level 1.2b a similar order. Clustering and bootstrap stages add to this. This is an estimate, not a measurement. Memory needs are modest (< 1 GB observed for single runs).

### Reproducibility controls implemented

- **Seeds:** every stochastic draw goes through one explicit seeded generator (`core/rng.py`). Seed bases are recorded in each stage's `scope_declaration.json` (for example Stage 3 `8300000`, Stage 4 `8700000` with LHS seed `20260821001`, Stage 6 `9100000`).
- **Mechanism-specific substreams** (Level 1.1b; `abm/docs/level1.1b_rng_design.md`): enabling or disabling one mechanism leaves the other mechanisms' random draws unchanged in matched-seed comparisons. A legacy single-stream mode is kept for exact backward compatibility.
- **Cross-process determinism:** the Level 1.3b fix sorts `TRANSMISSIBLE_COMPONENT_NAMES`, because string hashing randomized its order per process. Guarded by `tests/test_level13b_cross_process_reproducibility.py` (3 fresh processes). This passed in the packaging run.
- **Checkpoint continuation:** `core/state_checkpoint.py` (`run_partial`, `fork`, `finish`). Forks are rebuilt by replaying the same number of steps, not by deep-copying, after a frozenset-order defect was found.
- **Sham control:** in Stage 6 the sham fork must equal the unaltered control byte for byte. The archived result is 12/12.
- **Frozen, hashed manifests** precede every principal data-generating stage. The Level 1.3b hash was verified here.
- **Generative–observer firewall:** structural tests (`test_*sem_firewall*`) require that neither layer imports dissertation data, labels or a trajectory count.

### Legacy (Level 0.3b snapshot)

Use a separate venv: `pip install -e legacy/abm_governance_level0.3b[dev]`, then run `pytest -q`. Packaging run: 539 passed in 68 s, with no output files modified. These outputs are provenance for Level 0.x only. The legacy experiment scripts are **not** guarded, because the snapshot is kept unmodified; run them only in a copy of the folder.

## Paper

```bash
cd paper
make verify     # pdflatex → biber → pdflatex ×2 via latexmk, then scripts/verify_manuscript.py
```

The build needs TeX Live with `biblatex`/`biber` and the packages `lmodern`, `microtype`, `setspace`, `longtable`, `multirow`, `caption`, `float`, `adjustbox`, `xcolor`, `underscore`, `hyperref` and `cleveref`. Evidence is not bundled with the paper. It resolves to `abm/outputs/` (see `version_map.md` §4).
