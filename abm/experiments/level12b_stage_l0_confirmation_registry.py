#!/usr/bin/env python3
"""Level 1.2b, Work Package L, stage 0 (Section 17): freeze the
confirmation DESIGN (fresh joint points/seeds, disjoint from Work
Package E's own discovery seeds) and the confirmation REGISTRY
(candidate definitions / preprocessing / assignment rule / uncertainty
ranges / expected directions) -- BOTH before any confirmation outcome
is generated, per Section 17's own ordering requirement and this
milestone's Section 2 discipline ("GENERATE FIRST... DISCOVER
THIRD... INTERPRET LATER" -- the freeze happens before the "generate"
step for confirmation specifically).

**What "candidate" means here, given Work Package K's own verdict.**
Section 16 (Work Package K) returned ``verdict="continuum"``,
``headline_k=4`` -- explicitly NOT ``"multi_config"`` (the verdict
label reserved for a stable, single-peaked, failure-independent
k>=2 solution). A continuum finding means this milestone's own
discovery pipeline did not identify discrete, well-separated
candidate institutional-phenotype classes to name, bound with
uncertainty ranges, or assign expected directions to. Forcing the
k=4 partition's cluster boundaries into a "candidate registry" as if
they were independently confirmed classes -- even labeled
"provisional" -- would be exactly the manufactured-candidate problem
Work Package I's own preregistered ``null_replication_rule`` exists
to prevent: "if Section 16 discovery supports no candidates,
confirmation replicates the null result rather than manufacturing a
candidate to test." This script's own judgment call, disclosed here:
a continuum verdict is treated the SAME way a no-candidate verdict
would be under that rule -- no discrete candidate is named, numbered,
or given an expected direction.

**What Work Package L tests instead.** Rather than skip Section 17
entirely, this milestone still runs its full required test battery
(``tests_applied_to_every_candidate`` in Work Package I's manifest)
against the one concrete object Work Package K's discovery DID
produce: the headline_k=4 GMM diagnostic partition. It is frozen and
tested here as a STRESS TEST of whether any structure recurs
out-of-sample -- never re-labeled as N independent confirmed
candidates. The primary preregistered expectation (frozen below,
BEFORE the confirmation pool is generated) is explicitly a NULL
expectation: an independent replication of Section 16's own discovery
procedure on fresh data should likewise fail to find a stable
multi_config verdict. Finding one anyway would itself be a disclosed
anomaly, not silently reinterpreted as success.

**Confirmation design**: reuses Work Package E's own ecological/
institutional parameter spaces and IC families (identical population,
identical Section 10 families) but with FRESH Latin Hypercube seeds
(``LHS_SEED_ECOLOGICAL_CONFIRMATION``/``LHS_SEED_INSTITUTIONAL_
CONFIRMATION``, disjoint from Work Package E's own) and a disjoint
seed base (``SEED_BASE_CONFIRMATION = 15_000_000`` vs. Work Package
E's ``9_000_000 + point_id*1000 + s`` range, which tops out at
``9_047_005`` for the preferred 48x6 design -- so the confirmation
range starting at 15,000,000 cannot collide under any run-count
choice). Stratum cut points are NOT recomputed from the smaller
confirmation draw set; this design reuses Work Package E's own frozen
``stratum_cut_points`` so ``expected_stratum`` labels stay on the same
scale as discovery's, a deliberate choice disclosed here rather than
silently assumed."""

from __future__ import annotations

import hashlib
import json
import math
import os

from experiments.level12b_stage_e_joint_discovery import (
    IC_FAMILIES,
    N_STEPS,
    N_PATCHES,
    POPULATION_SIZE,
    _ECOLOGICAL_SPACE_FOR_WPE,
    _lhs_draws,
    INSTITUTIONAL_PARAMETER_SPACE,
    load_and_verify_design,
)
from experiments.level12b_stage_i_preregistration_manifest import CONFIRMATION_RULES, load_and_verify_manifest
from experiments.level12b_stage_k_clustering_discovery import (
    DIMENSION_KEYS,
    PRIMARY_MISSINGNESS_STRATEGY,
    RNG_SEED,
)

OUT_DIR = "outputs/level12b_stage_l0_confirmation_registry"

#: Preferred run arithmetic (Work Package I manifest, `CONFIRMATION_
#: RULES["preferred"]`): 24 joint points x 8 seeds x 2 IC families =
#: 384 runs. Hard minimum (18x6x2=216) is used only if a stop
#: condition forces a reduction -- disclosed at execution time if so.
N_JOINT_POINTS_PREFERRED = 24
SEEDS_PER_POINT_PREFERRED = 8
N_JOINT_POINTS_HARD_MINIMUM = 18
SEEDS_PER_POINT_HARD_MINIMUM = 6

#: Fresh LHS seeds, disjoint from Work Package E's own
#: (20260818001 / 20260818002).
LHS_SEED_ECOLOGICAL_CONFIRMATION = 20260818201
LHS_SEED_INSTITUTIONAL_CONFIRMATION = 20260818202

#: Disjoint from Work Package E's seed range (9,000,000 --
#: 9,047,005 for the preferred 48x6 design; comfortably clear even
#: under the hard-minimum 36x4 design's own smaller range).
SEED_BASE_CONFIRMATION = 15_000_000


def build_confirmation_design(
    n_joint_points: int = N_JOINT_POINTS_PREFERRED, seeds_per_point: int = SEEDS_PER_POINT_PREFERRED,
) -> dict:
    wp_e = load_and_verify_design()
    stratum_cut_points = wp_e["design"]["stratum_cut_points"]
    low_cut, high_cut = stratum_cut_points["low_cut"], stratum_cut_points["high_cut"]

    eco_draws = _lhs_draws(_ECOLOGICAL_SPACE_FOR_WPE, n_joint_points, LHS_SEED_ECOLOGICAL_CONFIRMATION)
    inst_draws = _lhs_draws(INSTITUTIONAL_PARAMETER_SPACE, n_joint_points, LHS_SEED_INSTITUTIONAL_CONFIRMATION)

    from abm_governance.core.config import SimulationConfig
    from abm_governance.observer.feasibility_ratios import expected_pressure_ratio

    def _stratum(r: float) -> str:
        if not math.isfinite(r) or not math.isfinite(low_cut):
            return "undefined"
        if r <= low_cut:
            return "low_feasibility"
        if r <= high_cut:
            return "medium_feasibility"
        return "high_feasibility"

    points = []
    for point_id in range(n_joint_points):
        eco = eco_draws[point_id]
        eco_for_ratio = dict(eco)
        eco_for_ratio.pop("shock_interval_steps", None)
        eco_for_ratio.pop("shock_magnitude", None)
        cfg = SimulationConfig.level12_complete(
            population_size=POPULATION_SIZE, n_patches=N_PATCHES, n_steps=N_STEPS, seed=1, **eco_for_ratio,
        )
        ratio = expected_pressure_ratio(cfg).ratio
        points.append({
            "joint_point_id": point_id,
            "ecological_point_id": point_id,
            "institutional_point_id": point_id,
            "ecological_parameters": eco,
            "institutional_parameters": inst_draws[point_id],
            "expected_pressure_ratio": ratio,
            "expected_stratum": _stratum(ratio),
            "population_size": POPULATION_SIZE,
            "n_patches": N_PATCHES,
            "seeds": [SEED_BASE_CONFIRMATION + point_id * 1000 + s for s in range(seeds_per_point)],
        })

    stratum_counts: dict = {}
    for p in points:
        stratum_counts[p["expected_stratum"]] = stratum_counts.get(p["expected_stratum"], 0) + 1

    return {
        "milestone": "level1.2b_prospective_confirmation_design_work_package_l",
        "n_joint_points": n_joint_points, "seeds_per_point": seeds_per_point,
        "n_ic_families": len(IC_FAMILIES), "ic_families": list(IC_FAMILIES),
        "total_runs": n_joint_points * seeds_per_point * len(IC_FAMILIES),
        "n_steps": N_STEPS,
        "lhs_seed_ecological": LHS_SEED_ECOLOGICAL_CONFIRMATION,
        "lhs_seed_institutional": LHS_SEED_INSTITUTIONAL_CONFIRMATION,
        "seed_base": SEED_BASE_CONFIRMATION,
        "stratum_cut_points_reused_from_discovery": stratum_cut_points,
        "stratum_counts": stratum_counts,
        "points": points,
        "source_design_hash": wp_e["hash"],
        "seed_disjointness_note": (
            f"seeds span [{SEED_BASE_CONFIRMATION}, "
            f"{SEED_BASE_CONFIRMATION + (n_joint_points - 1) * 1000 + seeds_per_point - 1}]; "
            "Work Package E's own seeds span [9000000, 9047005] under its preferred design -- disjoint by construction"
        ),
    }


def confirmation_design_hash(design: dict) -> str:
    payload = json.dumps(design, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_confirmation_design(out_dir: str = OUT_DIR, **kwargs) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    design = build_confirmation_design(**kwargs)
    digest = confirmation_design_hash(design)
    with open(f"{out_dir}/confirmation_design.json", "w") as f:
        json.dump(design, f, indent=2, sort_keys=True, default=str)
    with open(f"{out_dir}/confirmation_design_hash.txt", "w") as f:
        f.write(digest + "\n")
    return {"design": design, "hash": digest}


def load_and_verify_confirmation_design(out_dir: str = OUT_DIR) -> dict:
    with open(f"{out_dir}/confirmation_design.json") as f:
        design = json.load(f)
    with open(f"{out_dir}/confirmation_design_hash.txt") as f:
        stored_hash = f.read().strip()
    recomputed = confirmation_design_hash(design)
    if recomputed != stored_hash:
        raise ValueError(
            f"Work Package L confirmation design at {out_dir}/confirmation_design.json has been altered "
            f"since it was frozen (stored hash {stored_hash}, recomputed hash {recomputed})."
        )
    return {"design": design, "hash": recomputed}


def build_confirmation_registry(confirmation_design_hash_value: str) -> dict:
    wp_e = load_and_verify_design()
    wp_i = load_and_verify_manifest()

    wp_k_path = "outputs/level12b_stage_k_clustering_discovery/results.json"
    with open(wp_k_path, "rb") as f:
        wp_k_bytes = f.read()
    wp_k_report = json.loads(wp_k_bytes)
    wp_k_report_sha256 = hashlib.sha256(wp_k_bytes).hexdigest()

    return {
        "version": "level1.2b-confirmation-registry-v1",
        "source_discovery": {
            "wp_k_verdict": wp_k_report["verdict"],
            "wp_k_headline_k": wp_k_report["headline_k"],
            "wp_k_n_total": wp_k_report["n_total"],
            # Informational traceability only -- NOT a frozen/verified
            # input artifact under this project's load_and_verify_*
            # discipline (Work Package K's own results.json is a
            # terminal report, never re-consumed by an upstream stage
            # the way design.json/manifest.json are).
            "wp_k_report_sha256_informational_only": wp_k_report_sha256,
        },
        "candidate_status": (
            "no_independent_well_separated_candidates -- Section 16 verdict is 'continuum', not 'multi_config'. "
            "Per this milestone's own preregistered null_replication_rule ('if Section 16 discovery supports no "
            "candidates, confirmation replicates the null result rather than manufacturing a candidate to test'), "
            "a continuum finding is treated the same way a no-candidate finding would be: this Work Package does "
            "not name, number, or assign an expected direction to any discrete institutional-phenotype class."
        ),
        "frozen_preprocessing": {
            "missingness_strategy": PRIMARY_MISSINGNESS_STRATEGY,
            "standardize": True,
            "dimension_keys": list(DIMENSION_KEYS),
            "feature_vector_source": "vector_end (end-of-run institutional_phenotype_vector, window=None) -- matches Work Package K's own headline feature set, not the mid-run temporal-window-stability snapshot (already tested by Work Package K; not re-tested here, a disclosed scope reduction)",
        },
        "frozen_diagnostic_partition": {
            "description": "the headline_k GMM fit is retained ONLY as a diagnostic stress-test object, never as N independent confirmed candidates",
            "k": wp_k_report["headline_k"],
            "fit_procedure": (
                "GaussianMixture(n_components=k, random_state=RNG_SEED) refit on the discovery pool's own "
                "mean-impute-standardized feature matrix (X_train=X_apply=discovery pool, matching Work Package "
                "K's own preprocess_features call convention) -- deterministically reproducible bit-for-bit, "
                "refit at Work Package L analysis time rather than loaded from a serialized model object, since "
                "Work Package K's own saved results.json did not persist model parameters (disclosed gap, not "
                "silently worked around)."
            ),
            "rng_seed": RNG_SEED,
        },
        "uncertainty_ranges": (
            "not applicable -- Section 16 did not confirm independent candidate clusters, so no per-candidate "
            "uncertainty range is preregistered here. The only quantity given an explicit uncertainty treatment "
            "is the diagnostic partition's own stability (bootstrap ARI / algorithm-agreement ARI), already "
            "reported by Work Package K in-pool and re-tested here out-of-sample against fresh confirmation data."
        ),
        "expected_directions": {
            "primary_prereg_expectation": (
                "NULL: an independent replication of Section 16's own discovery procedure "
                "(gmm/hierarchical across k=1..8 plus hdbscan, identical classify_discovery_verdict thresholds) "
                "run on the fresh confirmation pool's own feature matrix should likewise fail to reach a stable, "
                "single-peaked, failure-independent 'multi_config' verdict -- i.e. this Work Package expects its "
                "own independent_replication_verdict to NOT be 'multi_config'. Preregistered BEFORE the "
                "confirmation pool is generated."
            ),
            "secondary_prereg_expectation": (
                "the diagnostic k=headline_k partition's out-of-sample assignment on the confirmation pool is "
                "expected to show LOW-TO-MODERATE agreement (ARI) with the confirmation pool's own independently "
                "fit partition, mirroring Work Package K's own moderate-not-high in-pool stability metrics -- "
                "consistent with a continuum rather than sharp, portable classes."
            ),
        },
        "run_arithmetic": CONFIRMATION_RULES["preferred"],
        "hard_minimum": CONFIRMATION_RULES["hard_minimum"],
        "tests_applied": list(CONFIRMATION_RULES["tests_applied_to_every_candidate"]),
        "null_replication_rule_applied": True,
        "null_replication_rule_text": CONFIRMATION_RULES["null_replication_rule"],
        "confirmation_design_hash": confirmation_design_hash_value,
        "source_design_hash": wp_e["hash"],
        "preregistration_manifest_hash": wp_i["hash"],
    }


def confirmation_registry_hash(registry: dict) -> str:
    payload = json.dumps(registry, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_confirmation_registry(out_dir: str = OUT_DIR) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    design_result = write_confirmation_design(out_dir=out_dir)
    registry = build_confirmation_registry(design_result["hash"])
    digest = confirmation_registry_hash(registry)
    with open(f"{out_dir}/confirmation_registry.json", "w") as f:
        json.dump(registry, f, indent=2, sort_keys=True, default=str)
    with open(f"{out_dir}/confirmation_registry_hash.txt", "w") as f:
        f.write(digest + "\n")
    return {"design": design_result["design"], "design_hash": design_result["hash"], "registry": registry, "registry_hash": digest}


def load_and_verify_confirmation_registry(out_dir: str = OUT_DIR) -> dict:
    with open(f"{out_dir}/confirmation_registry.json") as f:
        registry = json.load(f)
    with open(f"{out_dir}/confirmation_registry_hash.txt") as f:
        stored_hash = f.read().strip()
    recomputed = confirmation_registry_hash(registry)
    if recomputed != stored_hash:
        raise ValueError(
            f"Work Package L confirmation registry at {out_dir}/confirmation_registry.json has been altered "
            f"since it was frozen (stored hash {stored_hash}, recomputed hash {recomputed})."
        )
    return {"registry": registry, "hash": recomputed}


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    result = write_confirmation_registry()
    print(f"Work Package L confirmation design frozen: {result['design']['total_runs']} runs, hash={result['design_hash']}")
    print(f"Work Package L confirmation registry frozen: hash={result['registry_hash']}")
    print(f"candidate_status: {result['registry']['candidate_status'][:80]}...")
