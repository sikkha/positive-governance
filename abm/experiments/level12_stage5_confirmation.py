#!/usr/bin/env python3
"""Level 1.2, Stage 5: prospective confirmation (fresh seeds).

Two independent, complementary tests of whatever Stage 4 found (or, as
it happened, did not find) against a genuinely fresh 12-run pool never
seen by Stage 3 or Stage 4 -- both applying the identical, un-retuned
Section 9/10 procedure, never adjusted after seeing Stage 4's own
result:

1. **Held-out generalization** (``held_out_log_likelihood``, already
   Section 9.3 machinery): Stage 3's own pool is the training set, its
   fitted mean/std standardization is applied unchanged to the fresh
   pool (``preprocess_features(X_train=stage3, X_apply=fresh, ...)``,
   Section 9.1's "fit on training data only" discipline), and a GMM at
   every evaluated k is scored genuinely out-of-sample.
2. **Independent replication**: the fresh 12-run pool is run through
   ``level12_stage4_discovery.discover()`` -- the *exact same* function
   Stage 4 used on Stage 3's pool, unmodified -- as its own, completely
   independent discovery attempt. Whatever candidates (if any) meet all
   12 minimum criteria here were found without any information from
   Stage 3/4's own result.

**Design choice, disclosed before running**: the fresh pool reuses
Stage 3's own 12 Latin-Hypercube parameter draws (``experiments.
level12_stage3_search.build_parameter_draws()``, same fixed LHS seed)
under fresh, non-overlapping simulation seeds -- so this stage asks
"does the same parameter region reproduce a similar outcome under an
independent random realization," a stronger prospective test than an
unrelated fresh parameter sample would be, and consistent with Stage
0's frozen ``n_seeds: 12`` commitment (interpreted, like Stage 3's own
n_seeds/n_parameter_draws pair, as 12 draws x 1 fresh seed each = 12
total runs)."""

from __future__ import annotations

import json

from experiments.level12_common import compute_eligibility, compute_phenotype_vector, ensure_dir, run_and_summarize
from experiments.level12_preregistration import load_and_verify_manifest
from experiments.level12_stage3_search import N_PATCHES, N_STEPS, POPULATION, build_parameter_draws
from experiments.level12_stage4_discovery import PHENOTYPE_DIMENSION_KEYS, discover, load_pool
from abm_governance.core.config import SimulationConfig
from abm_governance.observer.phenotype_discovery import build_feature_matrix, preprocess_features, held_out_log_likelihood, DEFAULT_K_RANGE

OUT_DIR = "outputs/level12_stage5_prospective_confirmation"
#: Disjoint from Stage 2 (3000s), Stage 3 (4000-4111ish), and any other
#: stage's seed range -- guarantees these are genuinely fresh seeds,
#: never reused.
SEED_BASE = 6000


def _build_config(draw: dict, draw_id: int) -> SimulationConfig:
    return SimulationConfig.level11_complete(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=SEED_BASE + draw_id,
        rng_mode="mechanism_substreams",
        institutional_observation_enabled=True, institutional_transmission_enabled=True,
        migration_enabled=True, membership_exit_enabled=True, institutional_scaling_enabled=True,
        **draw,
    )


def generate_fresh_pool() -> list[dict]:
    draws = build_parameter_draws()  # same fixed LHS seed as Stage 3 -- same parameter regions, fresh simulation seeds
    records = []
    for draw_id, draw in enumerate(draws):
        config = _build_config(draw, draw_id)
        summary, sim = run_and_summarize(config, return_sim=True)
        phenotype_vector = compute_phenotype_vector(sim, config)
        eligibility = compute_eligibility(sim, config, phenotype_vector, summary)
        records.append({
            "draw_id": draw_id, "seed": config.seed, "parameter_condition": f"draw_{draw_id}",
            "parameters": draw, "all_outcome_label": summary["all_outcome_label"],
            "n_institutions_ever_formed": summary["n_institutions_ever_formed"],
            "n_institutions_active_at_end": summary["n_institutions_active_at_end"],
            "population_alive_fraction": summary["population_alive_fraction"],
            "ecological_resource_fraction": summary["ecological_resource_fraction"],
            "eligibility": eligibility, "phenotype_vector": phenotype_vector,
        })
    return records


def held_out_generalization(stage3_records: list[dict], fresh_records: list[dict]) -> dict:
    X_train, feature_names = build_feature_matrix([r["phenotype_vector"] for r in stage3_records], PHENOTYPE_DIMENSION_KEYS)
    X_fresh, _ = build_feature_matrix([r["phenotype_vector"] for r in fresh_records], PHENOTYPE_DIMENSION_KEYS)
    preproc = preprocess_features(X_train, X_fresh, "mean_impute", standardize=True)
    k_range = tuple(k for k in DEFAULT_K_RANGE if k <= preproc["X_train"].shape[0])
    return {
        "feature_names": feature_names,
        "held_out_log_likelihood_by_k": {
            k: held_out_log_likelihood(preproc["X_train"], preproc["X_apply"], k) for k in k_range
        },
    }


def run() -> dict:
    ensure_dir(OUT_DIR)
    load_and_verify_manifest()  # hard stop if Stage 0's frozen manifest was altered

    fresh_records = generate_fresh_pool()
    stage3_records = load_pool()

    generalization = held_out_generalization(stage3_records, [r for r in fresh_records if r["eligibility"]["eligible"]])

    eligible_fresh = [r for r in fresh_records if r["eligibility"]["eligible"]]
    replication_report = discover(eligible_fresh) if eligible_fresh else {"n_pooled_records": 0, "candidates": [], "n_candidates_meeting_all_12_criteria": 0}

    outcome_distribution = {}
    for r in fresh_records:
        outcome_distribution[r["all_outcome_label"]] = outcome_distribution.get(r["all_outcome_label"], 0) + 1

    report = {
        "n_fresh_runs": len(fresh_records), "n_eligible_fresh_runs": len(eligible_fresh),
        "outcome_label_distribution": outcome_distribution,
        "fresh_records": fresh_records,
        "held_out_generalization": generalization,
        "independent_replication": replication_report,
    }
    with open(f"{OUT_DIR}/stage5_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(
        f"Stage 5 confirmation: {len(fresh_records)} fresh runs ({len(eligible_fresh)} eligible), "
        f"outcome_label_distribution={outcome_distribution}. "
        f"Independent replication: {replication_report['n_candidates_meeting_all_12_criteria']}/"
        f"{len(replication_report.get('candidates', []))} candidates meet all 12 criteria on fresh data.",
        flush=True,
    )
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
