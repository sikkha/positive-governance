#!/usr/bin/env python3
"""Level 1.2b, Work Package L, stage 2 (Section 17): re-derive the
discovery pool's own end-of-run phenotype vectors, so stage 3 can
refit the frozen headline_k GMM diagnostic partition and score it
against the confirmation pool -- genuinely out-of-sample.

**Why this re-simulates Work Package E's design a THIRD time.** Work
Package K's own ``results.json`` (Section 16) reports only aggregate
metrics, never the raw per-run feature matrix or a serialized model
object (disclosed gap, see ``level12b_stage_l0_confirmation_registry``'s
own registry). Reconstructing the exact discovery-pool feature matrix
Work Package K fit against requires re-running the SAME 576
(point, seed, ic_family) triples from Work Package E's frozen design a
third time -- the identical deterministic-re-derivation justification
used by Work Package J and Work Package K (this project's own
determinism was directly verified earlier this session).

**Scope reduction versus Work Package K**: only the end-of-run
phenotype vector is captured here (Work Package K's own mid-run
temporal-window-stability snapshot is NOT re-collected -- that
stability question was already answered in-pool by Work Package K and
is not re-tested by Work Package L, whose own frozen registry commits
to ``vector_end`` as the sole feature-vector source)."""

from __future__ import annotations

import json
import os

from abm_governance.observer.institutional_phenotype import institutional_phenotype_vector
from abm_governance.simulation import Simulation
from experiments.level12b_stage_e_joint_discovery import (
    IC_FAMILIES,
    _build_config,
    _inject_heterogeneous_proto_institutions,
    load_and_verify_design,
)

OUT_DIR = "outputs/level12b_stage_l2_discovery_pool_refit"


def run() -> dict:
    wp_e = load_and_verify_design()
    records = []
    for point in wp_e["design"]["points"]:
        for ic_family in IC_FAMILIES:
            for seed in point["seeds"]:
                config = _build_config(point, seed)
                sim = Simulation(config)
                if ic_family == "heterogeneous_proto_institution":
                    _inject_heterogeneous_proto_institutions(sim, seed)
                sim.run()
                rule_by_patch = dict(sim._last_dissolved_rule_by_patch)
                rule_by_patch.update(sim.rule_registry)
                vector_end = institutional_phenotype_vector(
                    sim.event_log, rule_by_patch, sim.institution_registry, sim.delegate_registry,
                    sim.patch_system, sim._coordination_components, len(sim.patch_system.patches),
                    config.population_size, config.n_steps - 1, window=None,
                )
                records.append({
                    "joint_point_id": point["joint_point_id"], "ecological_point_id": point["ecological_point_id"],
                    "institutional_point_id": point["institutional_point_id"], "ic_family": ic_family, "seed": seed,
                    "vector_end": vector_end,
                })
        print(f"discovery-pool-refit joint point {point['joint_point_id']} done", flush=True)

    return {"source_design_hash": wp_e["hash"], "n_records": len(records), "records": records}


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    report = run()
    with open(f"{OUT_DIR}/results.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"Work Package L discovery-pool refit: {report['n_records']} records")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
