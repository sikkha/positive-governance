#!/usr/bin/env python3
"""Level 1.3, Stage 5 (task #100): causal historical counterfactuals
(matched-seed).

Exercises Work Package E's infrastructure (``core/historical_
counterfactuals.py`` + ``Simulation``'s ``historical_pressure_series_
override`` parameter) at experimental scale for the first time --
Work Package E itself (task #89) built and unit-tested the two
transform primitives and the override mechanism; this stage is the
first to actually run matched BASE/COUNTERFACTUAL pairs and compare
their outcomes.

**Design, and why single-channel**: each of 16 seeds gets one BASE run
with exactly ONE pressure channel enabled (``security_pressure``, a
clean ``"early_pulse"`` onset at step 150, permanent thereafter) and
TWO counterfactual re-runs from the SAME seed, each overriding that one
channel's REALIZED series with a transform of it:

- ``erased``: ``erase_pressure_from(realized, step=150)`` -- "what if
  this pressure had never arrived?"
- ``reversed``: ``reverse_pressure_order(realized)`` -- "what if this
  channel's pressure had arrived in the opposite temporal order?"

Single-channel is a deliberate choice, not an oversight: ``core/
historical_counterfactuals.py``'s own docstring discloses that
overriding only SOME of several simultaneously-enabled channels shifts
the shared ``pressure_rng`` draws consumed by the remaining,
still-generated channel(s) -- harmless for "exactly one channel
enabled" (this design) or "every enabled channel supplied via the
override dict together," a real gap for partial multi-channel override.
Single-channel sidesteps the issue entirely while still exercising the
full mechanism end to end.

Because base and counterfactual share the same seed, every RNG stream
OTHER than the overridden pressure channel itself draws identically in
both runs (each named stream is an independent ``SeedSequence`` spawn)
-- any divergence in downstream institutional outcomes is attributable
to the counterfactual manipulation alone, not confounded
re-randomization elsewhere.

16 seeds x 3 runs/seed (base, erased, reversed) = 48 runs (population
40, 3 patches, 500 steps, matching the frozen preregistration
manifest's ``stage5_causal_historical_counterfactuals_matched_seed``
commitment exactly).

**Descriptive causal-effect record, not a discovery-pipeline verdict.**
This script computes and reports per-seed divergence (S_obs/Z_obs
absolute difference, sequencing-vector agreement) between base and each
counterfactual -- a basic causal-effect-size record consistent with
this stage's own preregistered name, "causal." Whether that divergence
constitutes reproducible institutional differentiation in the Section
23 decision-gate sense is explicitly Stage 6-8's question, not this
one's.

**Two bugs found and fixed before the real run (task #109, disclosed
in full in ``dev_mem/status_update.md``).** This script's first
draft's ``_base_config`` (1) set only ``security_pressure_enabled``
(the master flag gating whether the pressure STATE series is
generated), never Work Package A's own two transmission sub-flags that
gate whether that state actually affects agent behavior
(``security_pressure_returns_to_delegation_enabled``,
``security_pressure_admin_capacity_demand_enabled`` -- both default
OFF); and (2) built on bare ``level1_rule_formation_default()``, whose
own design leaves delegation off entirely, so even fixing (1) alone
left nothing for the transmission channels to act on, and also
silently left ``rng_mode`` at ``legacy_single_stream`` -- directly
contradicting this module's own "attributable to the manipulation
alone, not confounded re-randomization" causal-isolation claim above,
which is only true under ``mechanism_substreams``.

A single-seed sanity check on the first draft (BEFORE the real 48-run
execution) came back byte-identical across base/erased/reversed event
logs, phenotype vectors, and S_obs/Z_obs -- exposing bug (1). Fixing
(1) alone and re-checking the same seed STILL came back byte-identical,
which is what surfaced bug (2) and prompted auditing every Level 1.3
stage script's config construction (finding the same two bugs already
present in Stage 3/4's completed runs). Fixed here via
``level12b_frozen_reference()`` plus ``experiments.level13_common.
transmission_overrides_for_channel``; the real run below reflects both
fixes from the start -- unlike Stage 3/4, no bugged Stage 5 output was
ever produced at experimental scale, only the diagnostic single-seed
checks reported in status_update.md."""

from __future__ import annotations

import hashlib
import json
import os

from abm_governance.core.config import SimulationConfig
from abm_governance.core.historical_counterfactuals import erase_pressure_from, reverse_pressure_order
from abm_governance.observer.level13_phenotype import level13_phenotype_vector
from abm_governance.observer.sequencing_diagnostics import institutional_response_series, sequencing_vector
from abm_governance.observer.sz_obs import s_obs_z_obs_summary
from abm_governance.simulation import Simulation
from experiments.level13_common import transmission_overrides_for_channel
from experiments.level13_preregistration import load_and_verify_manifest

OUT_DIR = "outputs/level13_stage5_causal_counterfactuals"
N_SEEDS = 16
N_STEPS = 500
POPULATION = 40
N_PATCHES = 3
SEED_BASE = 7_000_000
ENTRENCHMENT_MATURATION_STEPS = 100
PRESSURE_ONSET_STEP = 150
PRESSURE_STATE_KEY = "security_pressure_series"


def _base_config(seed: int) -> SimulationConfig:
    overrides: dict = dict(
        historical_module_enabled=True, security_pressure_enabled=True,
        security_pressure_history_kind="early_pulse", security_pressure_onset_step=PRESSURE_ONSET_STEP,
        security_pressure_high_level=0.7, security_pressure_duration_steps=None,
        entrenchment_enabled=True, entrenchment_maturation_steps=ENTRENCHMENT_MATURATION_STEPS,
        performance_legitimacy_enabled=True, procedural_legitimacy_enabled=True,
    )
    overrides.update(transmission_overrides_for_channel("security_pressure"))
    # level12b_frozen_reference (not the bare level1_rule_formation_
    # default() the first draft used) so the institutional substrate
    # Work Package A's transmission channels act on is active, and
    # rng_mode="mechanism_substreams" is set (the frozen manifest's own
    # RNG_COMMITMENTS -- also the mode this module's own docstring
    # already assumed for its "attributable to the manipulation alone"
    # causal-isolation claim). See module docstring's "Bug found and
    # fixed" note (task #109).
    return SimulationConfig.level12b_frozen_reference(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed,
        **overrides,
    )


def _summarize(sim: Simulation) -> dict:
    response = institutional_response_series(sim.event_log, N_STEPS)
    vector = sequencing_vector(response, min_duration_steps=10)
    phenotype = level13_phenotype_vector(
        sim.event_log, sim.rule_registry, n_steps=N_STEPS, current_step=N_STEPS,
        entrenchment_maturation_steps=ENTRENCHMENT_MATURATION_STEPS,
    )
    sz = s_obs_z_obs_summary(sim.event_log, N_STEPS)
    return {
        "sequencing_vector": vector,
        "phenotype_vector": {k: v["value"] for k, v in phenotype.items()},
        "s_obs": sz["S_obs"],
        "z_obs": sz["Z_obs"],
    }


def _run_matched_triple(seed: int) -> dict:
    base_config = _base_config(seed)
    base_sim = Simulation(base_config)
    base_sim.run()
    realized = base_sim.historical_state[PRESSURE_STATE_KEY]
    base_summary = _summarize(base_sim)

    erased_series = erase_pressure_from(realized, step=PRESSURE_ONSET_STEP)
    erased_sim = Simulation(base_config, historical_pressure_series_override={PRESSURE_STATE_KEY: erased_series})
    erased_sim.run()
    erased_summary = _summarize(erased_sim)

    reversed_series = reverse_pressure_order(realized)
    reversed_sim = Simulation(base_config, historical_pressure_series_override={PRESSURE_STATE_KEY: reversed_series})
    reversed_sim.run()
    reversed_summary = _summarize(reversed_sim)

    return {
        "seed": seed,
        "base": base_summary,
        "erased": erased_summary,
        "reversed": reversed_summary,
        "erased_vs_base_s_obs_abs_diff": abs(erased_summary["s_obs"] - base_summary["s_obs"]),
        "erased_vs_base_z_obs_abs_diff": abs(erased_summary["z_obs"] - base_summary["z_obs"]),
        "reversed_vs_base_s_obs_abs_diff": abs(reversed_summary["s_obs"] - base_summary["s_obs"]),
        "reversed_vs_base_z_obs_abs_diff": abs(reversed_summary["z_obs"] - base_summary["z_obs"]),
        "sequencing_vector_identical_erased_vs_base": erased_summary["sequencing_vector"] == base_summary["sequencing_vector"],
        "sequencing_vector_identical_reversed_vs_base": reversed_summary["sequencing_vector"] == base_summary["sequencing_vector"],
    }


def run(n_seeds: int = N_SEEDS) -> dict:
    load_and_verify_manifest()  # hard stop if the frozen manifest was altered
    records = [_run_matched_triple(SEED_BASE + i) for i in range(n_seeds)]

    def _mean(key: str) -> float:
        return sum(r[key] for r in records) / len(records) if records else float("nan")

    report = {
        "milestone": "level1.3_stage5_causal_historical_counterfactuals_matched_seed",
        "n_seeds": n_seeds,
        "population_size": POPULATION,
        "n_patches": N_PATCHES,
        "n_steps": N_STEPS,
        "pressure_onset_step": PRESSURE_ONSET_STEP,
        "pressure_state_key": PRESSURE_STATE_KEY,
        "mean_erased_vs_base_s_obs_abs_diff": _mean("erased_vs_base_s_obs_abs_diff"),
        "mean_erased_vs_base_z_obs_abs_diff": _mean("erased_vs_base_z_obs_abs_diff"),
        "mean_reversed_vs_base_s_obs_abs_diff": _mean("reversed_vs_base_s_obs_abs_diff"),
        "mean_reversed_vs_base_z_obs_abs_diff": _mean("reversed_vs_base_z_obs_abs_diff"),
        "n_seeds_erased_sequencing_identical_to_base": sum(r["sequencing_vector_identical_erased_vs_base"] for r in records),
        "n_seeds_reversed_sequencing_identical_to_base": sum(r["sequencing_vector_identical_reversed_vs_base"] for r in records),
        "records": records,
    }
    return report


def report_hash(report: dict) -> str:
    payload = json.dumps(report, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_report(out_dir: str = OUT_DIR, n_seeds: int = N_SEEDS) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    report = run(n_seeds)
    digest = report_hash(report)
    report["report_hash"] = digest
    with open(f"{out_dir}/records.json", "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    result = write_report()
    print(f"Level 1.3 Stage 5: {result['n_seeds']} matched triples")
    print(f"mean |S_obs diff| erased vs base: {result['mean_erased_vs_base_s_obs_abs_diff']:.4f}")
    print(f"mean |S_obs diff| reversed vs base: {result['mean_reversed_vs_base_s_obs_abs_diff']:.4f}")
    print(f"report written to {OUT_DIR}/records.json")
