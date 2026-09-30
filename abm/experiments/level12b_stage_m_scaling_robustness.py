#!/usr/bin/env python3
"""Level 1.2b, Work Package M (Section 18): scaling robustness.
2 population sizes x 2 patch counts x 2 network-modularity levels x 4
seeds = 32 runs "per candidate/null baseline", measuring ecological
state, phenotype assignment, administrative workload, scale, migration,
fragmentation, functional recovery, and transition to failure.
Section 18 explicitly does NOT require scale invariance -- a
scale-dependent finding is reported as-is, never treated as a failure
of this Work Package.

**"Per candidate/null baseline", given Work Package L's own
null-replication result.** Work Package L (Section 17) found
``confirmation_verdict="null_replicated"`` -- no independent,
well-separated candidate institutional-phenotype classes were
confirmed. Consistent with the SAME judgment this milestone applied at
Work Package L (a continuum/no-candidate finding is never worked
around by manufacturing a candidate to test), this Work Package runs
the scaling grid ONCE, against a single NULL BASELINE configuration --
not once per named candidate, since none exist to run it against.

**What "null baseline" means here.** ``SimulationConfig.level12_complete()``'s
own institutional/ecological defaults (no Latin-Hypercube draw, no
per-run parameter search) -- the model's own baseline behavior with
every Level 1.2 mechanism active at its ordinary default setting.
Deliberately NOT a point drawn from Work Package E's own design (which
would require an arbitrary choice of which of 48 points counts as
"the" baseline); using the codebase's own already-defined default
avoids that arbitrariness, disclosed explicitly here rather than
silently assumed.

**Grid dimensions**:
- population size: 32 (Work Package E's own base) vs. 64 (2x).
- patch count: 4 (Work Package E's own base) vs. 8 (2x).
- network modularity: manipulated via ``rewiring_prob`` (Watts-
  Strogatz small-world rewiring probability -- low rewiring keeps the
  network clustered/modular, high rewiring randomizes it toward an
  Erdos-Renyi-like structure). The REALIZED modularity of each run's
  own constructed social-network graph is also directly MEASURED
  (``networkx``'s own greedy-modularity communities + Newman
  modularity score) and reported alongside the manipulated
  ``rewiring_prob``, rather than assuming the proxy always produces
  the intended separation.
- seed: 4 fresh seeds per cell, disjoint from every other Work
  Package's own seed range (``SEED_BASE_SCALING = 18_000_000``, clear
  of Work Package E's ``9,000,000`` range and Work Package L's
  ``15,000,000`` range).

**A single deterministic mid-run shock** (``SHOCK_STEP = 350``, a
one-step ``resource_depletion`` perturbation of fixed magnitude, not
drawn from any distribution) is injected into every run so
"functional recovery" has something concrete to measure --
``regulation_diagnostics.perturbation_recovery`` (already built and
tested at Level 1.2) applied directly to the cheap population/
ecological-fraction trajectory series Work Package J's own
``_cheap_state_fractions`` produces.

**Phenotype assignment is a diagnostic, not a candidate-confirmation
claim.** Every run's end-of-run phenotype vector is scored against the
SAME frozen headline_k GMM diagnostic partition Work Package L froze
(refit here from Work Package L's own discovery-pool-refit artifact,
bit-identically reproducible) -- reported as "which diagnostic cluster
this run's phenotype vector falls into," never as "which confirmed
institutional-phenotype candidate this run represents"."""

from __future__ import annotations

import json
import os

import networkx as nx
import numpy as np

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.institutional_phenotype import institutional_phenotype_vector
from abm_governance.observer.institutional_viability import classify_all_outcome
from abm_governance.observer.phenotype_discovery import build_feature_matrix, fit_candidate, preprocess_features
from abm_governance.observer.regulation_diagnostics import perturbation_recovery
from abm_governance.simulation import Simulation
from experiments.level12b_stage_j_main_discovery_pipeline import _cheap_state_fractions
from experiments.level12b_stage_k_clustering_discovery import DIMENSION_KEYS, PRIMARY_MISSINGNESS_STRATEGY, RNG_SEED
from experiments.level12b_stage_l0_confirmation_registry import load_and_verify_confirmation_registry

OUT_DIR = "outputs/level12b_stage_m_scaling_robustness"

POPULATION_SIZES: tuple[int, ...] = (32, 64)
N_PATCHES_VALUES: tuple[int, ...] = (4, 8)
#: Watts-Strogatz rewiring probability -- manipulated proxy for
#: network modularity (low rewiring = more modular/clustered).
REWIRING_PROB_LEVELS: dict[str, float] = {"high_modularity": 0.02, "low_modularity": 0.6}
SEEDS_PER_CELL = 4
SEED_BASE_SCALING = 18_000_000
N_STEPS = 700

SHOCK_STEP = 350
SHOCK_MAGNITUDE = 0.3
TRAJECTORY_SNAPSHOT_INTERVAL_STEPS = 10
RECOVERY_PRE_SHOCK_HORIZON = 10  # snapshots (100 steps) immediately before the shock
RECOVERY_TOLERANCE_FRACTION = 0.1

#: Section 18's own closed grid-cell key ordering (population_size,
#: n_patches, modularity_level) x seed -- 2x2x2x4 = 32.
GRID_CELLS: tuple[tuple[int, int, str], ...] = tuple(
    (pop, patches, mod)
    for pop in POPULATION_SIZES
    for patches in N_PATCHES_VALUES
    for mod in REWIRING_PROB_LEVELS
)


def _build_scaling_config(population_size: int, n_patches: int, rewiring_prob: float, seed: int) -> SimulationConfig:
    return SimulationConfig.level12_complete(
        population_size=population_size, n_patches=n_patches, n_steps=N_STEPS, seed=seed,
        rewiring_prob=rewiring_prob,
        delegation_enabled=True, discretion_enabled=True, accountability_enabled=True,
        interpatch_coordination_enabled=True, institutional_fund_contribution_rate=0.05,
        perturbations=({"start_step": SHOCK_STEP, "duration": 1, "kind": "resource_depletion", "magnitude": SHOCK_MAGNITUDE},),
    )


def _measured_modularity(graph: nx.Graph) -> float:
    """Newman modularity of the run's own constructed social network,
    under greedy-modularity community detection. Degenerate (NaN) on a
    graph too small/disconnected for community detection to be
    meaningful -- never a fabricated 0.0."""
    if graph.number_of_nodes() < 3 or graph.number_of_edges() == 0:
        return float("nan")
    try:
        communities = nx.community.greedy_modularity_communities(graph)
        if len(communities) < 2:
            return float("nan")
        return float(nx.community.modularity(graph, communities))
    except Exception:  # noqa: BLE001 -- a measurement diagnostic, never fatal to the run
        return float("nan")


def _fragmentation_index(max_jurisdiction_size: int, n_patches: int) -> float:
    """A simple, transparent fragmentation index (no dedicated
    fragmentation function exists elsewhere in this codebase, disclosed
    rather than silently assumed): 0.0 when the largest jurisdiction
    spans every patch (no fragmentation), approaching 1.0 as the
    largest jurisdiction covers a small share of patches (institutional
    authority is scattered across many small, disconnected
    jurisdictions rather than one that spans the system)."""
    if n_patches <= 0:
        return float("nan")
    return 1.0 - (max_jurisdiction_size / n_patches)


def _load_frozen_partition():
    """Refits Work Package L's own frozen headline_k GMM diagnostic
    partition (bit-identically reproducible from the discovery-pool
    refit artifact) -- reused here as a diagnostic scoring rule, never
    as a claim about confirmed candidates (see module docstring)."""
    registry = load_and_verify_confirmation_registry()["registry"]
    headline_k = registry["frozen_diagnostic_partition"]["k"]
    with open("outputs/level12b_stage_l2_discovery_pool_refit/results.json") as f:
        discovery_pool = json.load(f)
    X_disc, feature_names = build_feature_matrix([r["vector_end"] for r in discovery_pool["records"]], DIMENSION_KEYS)
    prep = preprocess_features(X_disc, X_disc, PRIMARY_MISSINGNESS_STRATEGY)
    fit = fit_candidate(prep["X_train"], "gmm", k=headline_k, rng_seed=RNG_SEED)
    return {"model": fit["model"], "headline_k": headline_k, "feature_names": feature_names}


def _run_one(population_size: int, n_patches: int, modularity_level: str, seed: int, frozen_partition: dict) -> dict:
    rewiring_prob = REWIRING_PROB_LEVELS[modularity_level]
    config = _build_scaling_config(population_size, n_patches, rewiring_prob, seed)
    sim = Simulation(config)

    trajectory_series = []
    for step in range(config.n_steps):
        sim._run_one_step(step)
        if step % TRAJECTORY_SNAPSHOT_INTERVAL_STEPS == 0 or step == config.n_steps - 1:
            trajectory_series.append({"step": step, **_cheap_state_fractions(sim)})

    final = trajectory_series[-1]
    active_records = [r for r in sim.institution_registry.values() if not r.extinct]
    n_ever_formed = len(sim.institution_registry)
    n_active_at_end = len(active_records)
    max_jurisdiction_size = max((len(r.active_jurisdiction) for r in active_records), default=0)
    outcome_label = classify_all_outcome(
        n_ever_formed, n_active_at_end, final["population_alive_fraction"], final["ecological_resource_fraction"],
        max_jurisdiction_size,
    )

    rule_by_patch = dict(sim._last_dissolved_rule_by_patch)
    rule_by_patch.update(sim.rule_registry)
    phenotype_vector = institutional_phenotype_vector(
        event_log=sim.event_log, rule_by_patch=rule_by_patch, institution_registry=sim.institution_registry,
        delegate_registry=sim.delegate_registry, patch_system=sim.patch_system,
        coordination_components=sim._coordination_components, n_patches=len(sim.patch_system.patches),
        initial_population=config.population_size, current_step=config.n_steps - 1, window=None,
    )
    X_row, _ = build_feature_matrix([phenotype_vector], DIMENSION_KEYS)
    # mean_impute strategy applied consistently with training: use the
    # frozen model's own training-set behavior via preprocess_features
    # would require the training array again; instead this reuses the
    # SAME model object directly, so a NaN feature here (structurally
    # possible if this run never triggered the relevant event) is
    # imputed with THIS run's own column value being undefined --
    # disclosed limitation: single-row imputation cannot reuse training
    # column means without re-passing them, so any all-NaN dimension in
    # a single run's own vector is mean-imputed as 0.0 here, matching
    # preprocess_features' own "undefined column mean -> 0.0" fallback.
    row = np.nan_to_num(X_row, nan=0.0)
    predicted_cluster = int(frozen_partition["model"].predict(row)[0])

    pre_shock_idx = [i for i, s in enumerate(trajectory_series) if s["step"] < SHOCK_STEP]
    post_shock_idx = [i for i, s in enumerate(trajectory_series) if s["step"] >= SHOCK_STEP]
    pre_shock = trajectory_series[max(0, len(pre_shock_idx) - RECOVERY_PRE_SHOCK_HORIZON):len(pre_shock_idx)] if pre_shock_idx else []
    post_shock = trajectory_series[len(pre_shock_idx):] if post_shock_idx else []
    recovery_population = perturbation_recovery(
        [s["population_alive_fraction"] for s in pre_shock], [s["population_alive_fraction"] for s in post_shock],
        tolerance_fraction=RECOVERY_TOLERANCE_FRACTION,
    )
    recovery_ecological = perturbation_recovery(
        [s["ecological_resource_fraction"] for s in pre_shock], [s["ecological_resource_fraction"] for s in post_shock],
        tolerance_fraction=RECOVERY_TOLERANCE_FRACTION,
    )

    n_migration_events = len(sim.event_log.migrations)
    migration_rate = n_migration_events / population_size if population_size else float("nan")

    measured_modularity = _measured_modularity(sim.graph)

    return {
        "population_size": population_size, "n_patches": n_patches, "modularity_level": modularity_level,
        "rewiring_prob": rewiring_prob, "measured_modularity": measured_modularity, "seed": seed,
        "ecological_state": {
            "population_alive_fraction": final["population_alive_fraction"],
            "ecological_resource_fraction": final["ecological_resource_fraction"],
        },
        "phenotype_assignment": {"predicted_cluster": predicted_cluster, "headline_k": frozen_partition["headline_k"]},
        "administrative_workload": {"R_administrative_appropriation_burden": phenotype_vector["R"], "C_realized_administrative_capacity": phenotype_vector["C"]},
        "scale": {"S_institutional_scale_reach": phenotype_vector["S"], "population_size": population_size, "n_patches": n_patches},
        "migration": {"n_migration_events": n_migration_events, "migration_rate": migration_rate},
        "fragmentation": {"index": _fragmentation_index(max_jurisdiction_size, n_patches), "max_jurisdiction_size": max_jurisdiction_size, "n_institutions_ever_formed": n_ever_formed},
        "functional_recovery": {"population": recovery_population, "ecological": recovery_ecological},
        "transition_to_failure": {"all_outcome_label": outcome_label},
    }


def run() -> dict:
    frozen_partition = _load_frozen_partition()
    records = []
    failures = []
    for population_size, n_patches, modularity_level in GRID_CELLS:
        for s in range(SEEDS_PER_CELL):
            seed = SEED_BASE_SCALING + GRID_CELLS.index((population_size, n_patches, modularity_level)) * 1000 + s
            try:
                records.append(_run_one(population_size, n_patches, modularity_level, seed, frozen_partition))
            except Exception as exc:  # noqa: BLE001 -- preserve failed runs, never silently drop
                failures.append({"population_size": population_size, "n_patches": n_patches, "modularity_level": modularity_level, "seed": seed, "error": str(exc)})
        print(f"scaling cell (pop={population_size}, patches={n_patches}, {modularity_level}) done", flush=True)

    verified = load_and_verify_confirmation_registry()
    registry = verified["registry"]
    report = {
        "confirmation_registry_hash": verified["hash"],
        "source_design_hash": registry["source_design_hash"],
        "preregistration_manifest_hash": registry["preregistration_manifest_hash"],
        "candidate_or_null_baseline": "null_baseline (no confirmed candidates per Work Package L's own null_replication result -- see module docstring)",
        "n_runs_completed": len(records), "n_runs_failed": len(failures), "failures": failures,
        "scale_invariance_required": False,
        "records": records,
    }
    return report


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    report = run()
    with open(f"{OUT_DIR}/results.json", "w") as f:
        json.dump(report, f, indent=2, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print(f"Work Package M: {report['n_runs_completed']} runs completed, {report['n_runs_failed']} failed")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
