#!/usr/bin/env python3
"""Level 1.2b, Work Package G (Section 12): temporal representation.

Section 12 asks for, per seed-run per phenotype dimension: post-burn-in
mean, late-run mean, variance, trend, persistence, transition count,
longest stable episode, shock recovery, lineage turnover, extinction-
reconstruction -- under preregistered windows plus a burn-in-sensitivity
sweep (primary/shorter/longer/terminal-only) -- with static and dynamic
feature sets analyzed both separately and jointly.

**Every one of those features is already built and tested** in
``observer/temporal_features.py`` (Section 7's original module, extended
this Work Package with ``window_persistence_features``,
``window_shock_recovery_features``, the ``post_burn_in``/``pre_shock``
window bounds, and ``group_features_by_kind``) and
``observer/regulation_diagnostics.py`` (reused, not re-derived, for the
underlying persistence/transition/recovery math -- see
``temporal_features.py``'s own module docstring for why its defaults are
never used directly on phenotype dimensions). This script's only new
contribution is (1) preregistering the four burn-in-sensitivity
definitions BEFORE looking at any run, frozen and hashed exactly like
every other Work Package's own design, and (2) actually driving
simulations with periodic phenotype snapshots (the one piece of
plumbing ``temporal_features.py`` deliberately does not own -- its own
docstring: "this module never drives a Simulation itself") and running
the full feature-extraction pipeline over the result.

**Disclosed scope reduction.** Work Package E already generated the
milestone's main 576-run discovery pool, but that pool's ``results.json``
records only ecological-ledger summary statistics -- it holds no
per-step phenotype snapshots (collecting those for all 576 runs would
mean calling ``institutional_phenotype_vector`` roughly 700 times per
run x 576 runs x 10 dimensions, a cost far beyond what validating this
pipeline requires). This script instead reuses Work Package E's own
frozen design (`level12b_stage_e_joint_discovery.load_and_verify_design`)
for realistic, already-preregistered ecological/institutional parameter
points, but runs only a small, explicitly disclosed subset
(`N_DESIGN_POINTS_USED` points x `N_SEEDS_PER_POINT_USED` seeds x both
initial-condition families) with periodic snapshots collected during
each run. This validates every Section 12 feature end-to-end on real
simulation output; it is NOT a claim that this constitutes the
milestone's full temporal-representation discovery pool -- that
distinction is preserved in this module's own exported report
(`"scope"` field) rather than left implicit."""

from __future__ import annotations

import hashlib
import json
import os

from abm_governance.observer import institutional_phenotype as ip
from abm_governance.observer import temporal_features as tf
from abm_governance.simulation import Simulation
from experiments.level12b_stage_e_joint_discovery import (
    IC_FAMILIES,
    N_STEPS,
    _build_config,
    _inject_heterogeneous_proto_institutions,
    load_and_verify_design,
)

OUT_DIR = "outputs/level12b_stage_g_temporal_representation"

#: Disclosed scope reduction (see module docstring) -- how much of Work
#: Package E's frozen design this validation run actually drives.
N_DESIGN_POINTS_USED = 3
N_SEEDS_PER_POINT_USED = 2
SNAPSHOT_INTERVAL_STEPS = 5

#: Section 12's own four required burn-in-sensitivity definitions,
#: frozen here BEFORE any run's output is examined -- "primary" matches
#: Section 7's own already-established default (0.2); "shorter"/"longer"
#: bracket it; "terminal_only" restricts the exported windows to just
#: the terminal segment rather than changing the burn-in fraction at
#: all (the "how much do late-run-only conclusions differ from the full
#: post-burn-in picture" question, as distinct from "how sensitive is
#: the picture to the burn-in cutoff itself" -- both are burn-in-
#: sensitivity questions in the sense Section 12 means, addressed by
#: two different axes of variation here rather than conflated into one).
BURN_IN_SENSITIVITY_DEFINITIONS: dict[str, dict] = {
    "primary": {"burn_in_fraction": 0.2, "windows_included": None},
    "shorter": {"burn_in_fraction": 0.1, "windows_included": None},
    "longer": {"burn_in_fraction": 0.35, "windows_included": None},
    "terminal_only": {"burn_in_fraction": 0.2, "windows_included": ("terminal",)},
}

PHENOTYPE_DIMENSIONS: tuple[str, ...] = tuple("CELDMRSFVH")


def definitions_hash(definitions: dict = BURN_IN_SENSITIVITY_DEFINITIONS) -> str:
    payload = json.dumps(definitions, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _filter_bundle_to_windows(bundle: dict, windows_included) -> dict:
    """Restricts an ``extract_all_temporal_features`` bundle to only the
    named windows (``nonstationarity``/``shock_recovery`` -- whole-run
    diagnostics, not windows themselves -- are always kept). ``None``
    means keep every window (the "primary"/"shorter"/"longer"
    definitions' own behavior)."""
    if windows_included is None:
        return bundle
    out = {}
    for key, value in bundle.items():
        if key in ("nonstationarity", "shock_recovery") or key in windows_included:
            out[key] = value
    return out


def _run_with_snapshots(point: dict, seed: int, ic_family: str) -> dict:
    """Drives one simulation step-by-step (mirroring ``Simulation.run()``'s
    own ``[self._run_one_step(step) for step in range(n_steps)]`` body --
    this script needs to interleave a periodic snapshot call, which
    ``run()`` itself has no hook for), collecting an
    ``institutional_phenotype_vector`` snapshot every
    ``SNAPSHOT_INTERVAL_STEPS`` steps (each snapshot's own ``window`` is
    always ``None`` -- windowing happens afterward, over the collected
    series, exactly as ``temporal_features.py``'s module docstring
    prescribes)."""
    config = _build_config(point, seed)
    sim = Simulation(config)
    if ic_family == "heterogeneous_proto_institution":
        _inject_heterogeneous_proto_institutions(sim, seed)
    snapshots = []
    for step in range(config.n_steps):
        sim._run_one_step(step)
        if step % SNAPSHOT_INTERVAL_STEPS == 0 or step == config.n_steps - 1:
            vector = ip.institutional_phenotype_vector(
                sim.event_log, sim.rule_registry, sim.institution_registry, sim.delegate_registry,
                sim.patch_system, sim._coordination_components, config.n_patches, config.population_size,
                current_step=step, window=None,
            )
            snapshots.append({"step": step, "vector": vector})
    return {
        "snapshots": snapshots, "n_steps": config.n_steps,
        "institution_registry": sim.institution_registry,
    }


def _dimension_report(snapshots: list[dict], dimension_key: str, n_steps: int, institution_registry: dict) -> dict:
    """Every Section 12 feature for one dimension of one seed-run, under
    all four burn-in-sensitivity definitions, static/dynamic separated
    (``"grouped"``) and jointly (``"joint"`` -- the undivided bundle,
    since nothing upstream ever merges static and dynamic together to
    begin with; "jointly" is simply using the bundle as-is)."""
    out = {}
    for def_name, definition in BURN_IN_SENSITIVITY_DEFINITIONS.items():
        bundle = tf.extract_all_temporal_features(
            snapshots, dimension_key, n_steps, burn_in_fraction=definition["burn_in_fraction"],
        )
        bundle = _filter_bundle_to_windows(bundle, definition["windows_included"])
        # lineage turnover / extinction-reconstruction: institution-
        # registry-level, not per-dimension-series (Section 12 asks for
        # them per seed-run, not per dimension -- computed once per
        # burn-in definition's post_burn_in window here and reused for
        # every dimension's report the caller assembles, but exported
        # inside each dimension's own bundle too so a per-dimension
        # consumer never has to reach outside this dict).
        post_burn_in_window = tf.compute_window_bounds(n_steps, definition["burn_in_fraction"])["post_burn_in"]
        bundle["lineage_turnover"] = tf.lineage_turnover(institution_registry, post_burn_in_window)
        bundle["extinction_reconstruction"] = tf.extinction_reconstruction_counts(institution_registry, post_burn_in_window)
        out[def_name] = {"joint": bundle, "grouped": tf.group_features_by_kind(bundle)}
    return out


def run() -> dict:
    verified = load_and_verify_design()
    design = verified["design"]
    points = design["points"][:N_DESIGN_POINTS_USED]

    records = []
    for point in points:
        seeds = point["seeds"][:N_SEEDS_PER_POINT_USED]
        for ic_family in IC_FAMILIES:
            for seed in seeds:
                run_data = _run_with_snapshots(point, seed, ic_family)
                snapshots = run_data["snapshots"]
                dimension_features = {
                    dim: _dimension_report(snapshots, dim, run_data["n_steps"], run_data["institution_registry"])
                    for dim in PHENOTYPE_DIMENSIONS
                }
                records.append({
                    "institutional_point_id": point["institutional_point_id"],
                    "ecological_point_id": point["ecological_point_id"],
                    "ic_family": ic_family,
                    "seed": seed,
                    "n_snapshots": len(snapshots),
                    "dimension_features": dimension_features,
                })

    report = {
        "scope": {
            "note": "validation subset of Work Package E's frozen design -- NOT the full 576-run pool; see module docstring",
            "n_design_points_used": N_DESIGN_POINTS_USED,
            "n_seeds_per_point_used": N_SEEDS_PER_POINT_USED,
            "snapshot_interval_steps": SNAPSHOT_INTERVAL_STEPS,
        },
        "burn_in_sensitivity_definitions": BURN_IN_SENSITIVITY_DEFINITIONS,
        "burn_in_sensitivity_definitions_hash": definitions_hash(),
        "phenotype_dimensions": list(PHENOTYPE_DIMENSIONS),
        "n_records": len(records),
        "records": records,
    }
    return report


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    report = run()
    # Python's json module serializes float('nan')/inf as the bare
    # (non-standard-JSON, but Python-json-round-trippable) tokens
    # NaN/Infinity/-Infinity by default (`allow_nan=True`) -- every
    # NaN produced by this module's own structural-missingness
    # discipline round-trips correctly with plain json.dump/json.load,
    # so no custom encoder is needed here.
    with open(f"{OUT_DIR}/results.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"Work Package G: {report['n_records']} seed-run records written to {OUT_DIR}/results.json")
    print(f"burn-in sensitivity definitions hash: {report['burn_in_sensitivity_definitions_hash']}")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
