# Positive Governance — computational social science companion

Code, specifications, evidence outputs and manuscript sources that accompany the doctoral dissertation **_Positive Governance_** (Kan Yuenyong, National Institute of Development Administration (NIDA), Thailand). The dissertation treats governance as a context-conditioned relationship between **state capacity (S)** and **institutional constraint (Z)**. It uses three methods, each with its own inferential responsibility, and integrates them under the **Triangulated Multimethod Governance Inference Framework (TMGIF)**.

> **Status.** This is a research archive prepared from dissertation version **1.2** (September 2026). Version 1.3 was not available when the repository was prepared. No publication status, DOI or archival URL has been assigned yet.

## Components

| Directory | Method | Role under TMGIF | Evidence type | Entry point |
|---|---|---|---|---|
| [`sem/`](sem/README.md) | Structural equation modelling (R, lavaan) | Empirical measurement of governance-related **perceptions** (RQ1–RQ3) | Survey covariance, WVS Wave 7. **Data not included** | `sem/R/reconstructed/sem_models_reconstructed.R` |
| [`mcmea/`](mcmea/README.md) | Markov-chain macrostate evolutionary algorithm (Python notebooks) | **Conditional evolutionary deduction** under an explicit landscape (RQ4) | Consequences of declared assumptions | `mcmea/scripts/reproduce_recorded_outputs.py` |
| [`abm/`](abm/README.md) | Agent-based model, package `abm_governance` (Python) | **Generative and historical boundary testing** with no encoded governance types (RQ5) | Model-bound causal intervention | `abm-governance run …`; `experiments/level13b_*.py` |
| [`paper/`](paper/README.md) | LaTeX manuscript on ABM Levels 1.2–1.3b | Reports the ABM's discovery/confirmation and history-intervention results | Figures/claims drawn from `abm/outputs/` | `make verify` |
| [`legacy/`](legacy/abm_governance_level0.3b/README.md) | ABM snapshot at Level 0.3b | Provenance of Level 0.x outputs only | — | — |
| [`docs/`](docs/) | Design, reproducibility, claim–evidence map, version map, data availability, MCMEA audit | — | — | — |

## Main findings, stated at the strength the evidence supports

- **SEM (survey evidence).** Confidence and fairness items form three distinguishable perceptual domains: state institutions, legal institutions and electoral procedure. The analysis reported in dissertation v1.2 treated WVS missing-value codes as valid answers. After correction (n = 76,522, 61 countries; same MLR estimator), Model 1 fits acceptably but not closely: CFI .950, TLI .917, RMSEA .088, SRMR .053. The armed-forces item aligns only weakly with the civilian institutions (loading .42). The second-order constraint factor is admissible, dominated by rule of law (.90 vs .54) and highly correlated with S (.83). The outcome Models 3–4 are not identified as specified. The three governance regions remain *ideal types*; the SEM does not find them as clusters. See [`docs/sem_corrected_results.md`](docs/sem_corrected_results.md) and [`docs/sem_data_coding_audit.md`](docs/sem_data_coding_audit.md).
- **MCMEA (computational deduction).** The dominant basin follows from the encoded landscape. Under v3, the specification analysed in Chapter 5, 0 of 120 repeated runs end in Integrated Equilibrium, and terminal states split between the strong-capacity and strong-constraint regions. Under the earlier v2 specification, which favours Integrated Equilibrium, the population concentrates there. Zero terminal IE outcomes in 120 runs is a finite-sample result for the tested specification. It does not show that IE is impossible. The dissertation's Chapter 7 statement "IE in all 60 generations, 59 IE→IE transitions" cannot be reproduced from the code in this repository, and the TimesFM supplementary experiment has no archived code. See [`docs/mcmea_specification_audit.md`](docs/mcmea_specification_audit.md) and [`docs/mcmea_timesfm_status.md`](docs/mcmea_timesfm_status.md).
- **ABM (model-bound causal evidence).** Institutions emerge from local interaction without a planner. Outcome-blind discovery, however, finds **no robust small set of recurrent institutional families**: Level 1.2b gives the verdict `continuum` and replicates it as `null_replicated` on a disjoint 384-run pool, and Level 1.3b reaches decision `D_persistent_continuum`. Stored history is causal *inside the model*. In sham-controlled checkpoint forks (12/12 shams byte-identical), erasing pressure memory, entrenchment or all history leaves final gaps of about .054, .072 and .069.
- **What none of this shows.** The simulations do not validate real-world governance types, their stability, or the normative superiority of any configuration. Agreement between methods is used only for bounded meta-inference.

## Installation and quick start

Python ≥ 3.10 (tested with 3.10.12 and 3.11.15); R ≥ 4.1 with lavaan (tested 4.3.3 / lavaan 0.6-17); TeX Live with biber for the paper.

```bash
# ABM — install, 1-minute demo, fast checks
python -m venv .venv && . .venv/bin/activate
pip install -e "abm[dev]"
abm-governance run --seed 0 --steps 200 --out /tmp/abm_demo      # quick demonstration run
pytest abm/tests/test_level13b_cross_process_reproducibility.py -q  # determinism guard

# MCMEA — recompute every stored notebook result (~1 min)
pip install -r mcmea/requirements.txt
python mcmea/scripts/reproduce_recorded_outputs.py

# SEM — needs the WVS Wave 7 v5.0 CSV (see docs/data_availability.md)
cd sem && Rscript R/validation/smoke_test_synthetic.R             # code check without WVS data
WVS_CSV=/path/to/WVS_Cross-National_Wave_7_csv_v5_0.csv Rscript corrected_analysis/R/sem_corrected_analysis.R   # corrected + original + sensitivity

# Paper
cd paper && make verify
```

The full ABM experiment programme is compute-heavy. Re-run any stage with `python abm/experiments/run_isolated.py <script>.py --out-dir /tmp/rerun`; the scripts refuse to overwrite the archived `abm/outputs/`. See [`docs/reproducibility.md`](docs/reproducibility.md).

## Documentation

- [`docs/research_design.md`](docs/research_design.md): RQ1–RQ5 and each method's inferential role
- [`docs/reproducibility.md`](docs/reproducibility.md): verified commands, environments, seeds, expected outputs, runtimes, and the difference between software verification and scientific replication
- [`docs/claim_evidence_map.csv`](docs/claim_evidence_map.csv): claim → location → implementation → source output → command → verification status
- [`docs/version_map.md`](docs/version_map.md): how the implementations and milestones relate
- [`docs/data_availability.md`](docs/data_availability.md): what is included or excluded, and how to obtain the WVS data
- [`docs/mcmea_specification_audit.md`](docs/mcmea_specification_audit.md): Chapter 5 vs Chapter 7 MCMEA discrepancy
- [`docs/mcmea_timesfm_status.md`](docs/mcmea_timesfm_status.md): unarchived TimesFM experiment
- [`docs/sem_data_coding_audit.md`](docs/sem_data_coding_audit.md) and [`docs/sem_corrected_results.md`](docs/sem_corrected_results.md): SEM coding audit and corrected results
- [`LIMITATIONS.md`](LIMITATIONS.md): limitations and known issues

## Licence and citation

**No licence has been chosen yet for the author's original work in this repository.** Until one is added, default copyright applies. `abm/pyproject.toml` and `legacy/…/pyproject.toml` carry an inherited `license = { text = "MIT" }` metadata field, but there is no licence file. Third-party data (WVS) are not redistributed and remain under their providers' terms. See [`CITATION.cff`](CITATION.cff) for citation metadata.
