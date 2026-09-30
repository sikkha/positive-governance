#!/usr/bin/env python3
"""Level 1.2, Stage 2: small open pilot.

The first run of the FULL open generative machinery together (all five
Work Package B/C/D/F mechanisms simultaneously active) at a still-small
scale, and the first run of the observer-side phenotype-vector/
eligibility/preprocessing pipeline against real simulation output rather
than synthetic test fixtures. This stage's purpose is integration
confidence before Stage 3's larger commitment -- it does NOT run the
blind discovery clustering itself (Stage 4's job) and reports no
recurrence claim; ``dimensionality_reduction_diagnostic``/
``examine_collinearity`` here are diagnostic smoke tests only, exactly
as their own docstrings require.

Session-budget scope reduction (disclosed, Stage 0's frozen commitment):
10 seeds, population 40, 4 patches, 400 steps. Each seed's run is
wrapped so a single seed's unexpected exception is recorded and does
not abort the other 9 -- a pilot's job includes surfacing exactly this
kind of integration failure without losing the rest of the run."""

from __future__ import annotations

import json
import traceback

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.phenotype_discovery import (
    build_feature_matrix,
    dimensionality_reduction_diagnostic,
    examine_collinearity,
    missingness_report,
    preprocess_features,
)
from experiments.level12_common import compute_eligibility, compute_phenotype_vector, ensure_dir, run_and_summarize
from experiments.level12_preregistration import load_and_verify_manifest

OUT_DIR = "outputs/level12_stage2_pilot"
N_SEEDS = 10
N_STEPS = 400
POPULATION = 40
N_PATCHES = 4

PHENOTYPE_DIMENSION_KEYS: tuple[str, ...] = ("C", "E", "L", "D", "M", "R", "S", "F", "V", "H")


def _build_config(seed: int) -> SimulationConfig:
    # level11_complete (not level1_rule_formation_default) as the base --
    # Stage 1 used the narrower base since it only needed to isolate
    # each new flag in turn; Stage 2's own purpose is to stress the
    # FULL phenotype vector (delegation/accountability drive C, E, D),
    # so it needs Level 1.1's delegation/discretion/accountability layer
    # active too, not just Level 1.0 rule formation.
    return SimulationConfig.level11_complete(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=3000 + seed,
        coordination_proposal_probability=0.3,
        institutional_observation_enabled=True, institutional_transmission_enabled=True,
        migration_enabled=True, membership_exit_enabled=True, institutional_scaling_enabled=True,
    )


def run() -> dict:
    ensure_dir(OUT_DIR)
    load_and_verify_manifest()  # hard stop if Stage 0's frozen manifest was altered

    per_seed = []
    failures = []
    phenotype_records = []
    for seed in range(N_SEEDS):
        config = _build_config(seed)
        try:
            summary, sim = run_and_summarize(config, return_sim=True)
            phenotype_vector = compute_phenotype_vector(sim, config)
            eligibility = compute_eligibility(sim, config, phenotype_vector, summary)
            per_seed.append({
                "seed": seed, "all_outcome_label": summary["all_outcome_label"],
                "n_institutions_ever_formed": summary["n_institutions_ever_formed"],
                "n_institutions_active_at_end": summary["n_institutions_active_at_end"],
                "eligibility": eligibility, "phenotype_vector": phenotype_vector,
            })
            phenotype_records.append(phenotype_vector)
        except Exception as exc:  # noqa: BLE001 -- a pilot's job is to surface, not hide, integration failures
            failures.append({"seed": seed, "error": str(exc), "traceback": traceback.format_exc()})
        print(f"seed {seed}: {'ok' if not failures or failures[-1]['seed'] != seed else 'FAILED'}", flush=True)

    report: dict = {
        "n_seeds": N_SEEDS, "n_steps": N_STEPS, "population": POPULATION, "n_patches": N_PATCHES,
        "n_completed": len(per_seed), "n_failed": len(failures), "failures": failures,
        "per_seed": per_seed,
    }

    if phenotype_records:
        X, feature_names = build_feature_matrix(phenotype_records, PHENOTYPE_DIMENSION_KEYS)
        report["feature_names"] = feature_names
        report["missingness_report"] = missingness_report(X, feature_names)
        report["collinearity_diagnostic"] = examine_collinearity(X, feature_names)
        # PCA cannot accept raw NaN (Section 9.1's transparent-missingness
        # discipline means build_feature_matrix leaves NaN in place) --
        # mean_impute here is this pilot's own diagnostic-only choice for
        # feeding PCA, distinct from Stage 4's actual three-way
        # missingness-strategy comparison across the full pipeline.
        pca_input = preprocess_features(X, X, "mean_impute", standardize=True)["X_train"]
        report["pca_diagnostic"] = dimensionality_reduction_diagnostic(pca_input, n_components=2)
        report["outcome_label_distribution"] = {
            label: sum(1 for r in per_seed if r["all_outcome_label"] == label)
            for label in sorted({r["all_outcome_label"] for r in per_seed})
        }
        report["n_eligible"] = sum(1 for r in per_seed if r["eligibility"]["eligible"])

    with open(f"{OUT_DIR}/stage2_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(
        f"Stage 2 pilot: {report['n_completed']}/{N_SEEDS} seeds completed, {report['n_failed']} failed. "
        f"outcome_label_distribution={report.get('outcome_label_distribution')}", flush=True,
    )
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
