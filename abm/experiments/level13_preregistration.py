#!/usr/bin/env python3
"""Level 1.3, task #94 (Section 15): the milestone-level preregistration
manifest.

Mirrors ``experiments/level12_preregistration.py``'s exact freeze-then-
hash pattern (same ``build_manifest``/``manifest_hash``/``write_
manifest``/``load_and_verify_manifest`` structure) -- every analysis-
affecting decision Level 1.3's Stage 0-9 experimental program will use
is collected here, imported live from the modules/scripts that actually
implement it wherever one already exists (never hand-copied, so this
manifest cannot silently drift from the code it describes), and frozen
with a SHA-256 hash BEFORE any Stage 0-9 run executes.

**Context-loss disclosure, and what is NOT a guess here.** Most of this
session's Level 1.3 work has needed to disclose interpretive judgment
calls because the verbatim spec text for later sections was lost to
compaction. Section 23's six-way decision gate is the one exception:
``docs/level1.3_theoretical_translation.md`` §6 (written earlier in
this session, while the source spec was still in context) states the
exact six-way outcome space in its own prose --- "the milestone must
remain capable of finding one family, two, four-or-more, a continuum,
transient differentiation, or no detectable historical effect at all
(Section 23's six-way decision gate)" --- and this session's own
``dev_mem/status_update.md`` record (Work Package E's entry) already
established that "do not prefer E" refers to this outcome list's
transient-differentiation option, not to Work Package E (the
counterfactual-infrastructure work package) itself. :data:`DECISION_
GATE_OUTCOMES` below is a direct, disclosed transcription of that
recovered sentence, not a reconstruction -- it is preregistered here,
before any Stage 0-9 run, precisely so it cannot be quietly reworded
later to fit whatever a run turns up.

**Disclosed scope reduction** (same discipline Level 1.2's own Stage 0
manifest states): every sample size in :data:`STAGE_SAMPLE_SIZES` is
scaled to this session's compute budget, not to any publication target,
and is stated here before any run so it cannot be quietly adjusted
afterward.

Nothing in this manifest references any SEM/dissertation trajectory,
country, or forbidden Section-2 vocabulary --
``tests/test_level13_sem_firewall_extension.py``'s experiment-script
scan (globbing ``experiments/level13_*.py``) covers this file
automatically."""

from __future__ import annotations

import hashlib
import json
import os

from abm_governance.core.rng import RNG_REGISTRY_VERSION
from abm_governance.observer.institutional_conversion import FUNCTION_FAMILIES
from abm_governance.observer.level13_phenotype import LEVEL13_DIMENSION_KEYS
from abm_governance.observer.phenotype_discovery import (
    CANDIDATE_METHODS,
    CLUSTERING_PIPELINE_VERSION,
    DEFAULT_K_RANGE,
    MISSINGNESS_STRATEGIES,
)
from abm_governance.observer.sequencing_diagnostics import INSTITUTIONAL_RESPONSE_DIMENSIONS
from abm_governance.observer.sz_obs import S_OBS_RESPONSE_DIMENSIONS, Z_OBS_RESPONSE_DIMENSIONS
from experiments.level13_common import ECOLOGICAL_SPACE_FOR_LEVEL13, LHS_SEED_ECOLOGICAL_LEVEL13

OUT_DIR = "outputs/level13_preregistration"

#: The seven config flags gating every Level 1.3 generative mechanism --
#: frozen here as the exact set any Stage 0-9 script must report the
#: on/off state of. Restated directly (not imported from
#: ``tests/test_level13_compatibility.py``'s own private tuple), since
#: an experiment script importing from ``tests/`` would be backwards --
#: this manifest is what a test cross-checks, not the reverse.
MECHANISM_ACTIVATION_FLAGS: tuple[str, ...] = (
    "historical_module_enabled",
    "security_pressure_enabled",       # Work Package A
    "bargaining_pressure_enabled",     # Work Package A
    "coordination_complexity_enabled", # Work Package A
    "entrenchment_enabled",            # Work Package C
    "performance_legitimacy_enabled",  # Work Package D
    "procedural_legitimacy_enabled",   # Work Package D
)

#: Disclosed, session-budget-scaled sample sizes for each of Level 1.3's
#: ten experimental stages (tasks #95-#104), fixed BEFORE any stage
#: runs. A starting commitment, not a promise no stage script will
#: further reduce it -- any further reduction must be disclosed in that
#: stage's own script/report, never silently (same rule Level 1.2's own
#: manifest states).
STAGE_SAMPLE_SIZES: dict[str, dict] = {
    "stage0_exact_compatibility": {"n_seeds": 20, "population": 30, "n_patches": 3, "n_steps": 200, "note": "matched seeds, historical_module_enabled True vs False, config otherwise identical"},
    "stage1_mechanism_activation": {"n_seeds": 8, "population": 40, "n_patches": 3, "n_steps": 300, "note": "one condition per Work Package A/C/D channel in isolation, plus all-on"},
    "stage2_calibration_without_phenotype_labels": {"n_points": 30, "note": "ecological feasibility LHS + cut-point freeze only -- see experiments/level13_common.py; no phenotype/discovery label read here"},
    "stage3_sequencing_x_entrenchment_factorial": {"n_seeds_per_cell": 6, "population": 40, "n_patches": 3, "n_steps": 500, "note": "crosses pressure-onset ORDER (security/bargaining/coordination) x entrenchment_enabled on/off"},
    "stage4_open_pressure_history_search_lhs": {"n_points": 24, "n_seeds_per_point": 4, "population": 40, "n_patches": 4, "n_steps": 500},
    "stage5_causal_historical_counterfactuals_matched_seed": {"n_seeds": 16, "population": 40, "n_patches": 3, "n_steps": 500, "note": "matched pairs via core/historical_counterfactuals.py + Simulation's historical_pressure_series_override"},
    "stage6_blind_phenotype_discovery": {"note": "pools Stage 3-5's phenotype vectors through observer/phenotype_discovery.py unmodified; no new simulation runs"},
    "stage7_fresh_confirmation": {"n_seeds": 12, "population": 40, "n_patches": 4, "n_steps": 500, "note": "fresh seeds, never reused from Stage 3-6"},
    "stage8_s_obs_z_obs_mapping": {"note": "reuses Stage 3-7's own runs' event logs -- observer/sz_obs.py is purely post-hoc, no new simulation runs required"},
    "stage9_scale_and_shock_robustness": {"n_seeds": 6, "population_conditions": [40, 80], "n_patches_conditions": [3, 6], "note": "population_patch_ratio_selector, excluded from Stage 2's ecological feasibility axis, is this stage's own question"},
}

#: Section 9/13 discovery-pipeline commitments, imported (not restated)
#: from the modules that actually implement them.
DISCOVERY_PIPELINE_COMMITMENTS: dict = {
    "clustering_pipeline_version": CLUSTERING_PIPELINE_VERSION,
    "candidate_methods": list(CANDIDATE_METHODS),
    "k_range": list(DEFAULT_K_RANGE),
    "missingness_strategies": list(MISSINGNESS_STRATEGIES),
    "level13_dimension_keys": list(LEVEL13_DIMENSION_KEYS),
    "model_selection_rule": "no single metric decides -- see observer/phenotype_discovery.py:model_selection_metrics",
}

#: Section 7 sequencing commitments.
SEQUENCING_COMMITMENTS: dict = {
    "institutional_response_dimensions": list(INSTITUTIONAL_RESPONSE_DIMENSIONS),
    "note": "first-sustained-crossing per dimension (observer/sequencing_diagnostics.py); order is an empirical question, never assumed",
}

#: Section 12 S_obs/Z_obs commitments, imported (not restated) so this
#: manifest cannot silently drift from the actual composite membership.
SZ_OBS_COMMITMENTS: dict = {
    "s_obs_response_dimensions": list(S_OBS_RESPONSE_DIMENSIONS),
    "s_obs_extra_component": "performance_legitimacy_series",
    "z_obs_response_dimensions": list(Z_OBS_RESPONSE_DIMENSIONS),
    "z_obs_extra_component": "procedural_legitimacy_series",
    "weighting": "unweighted mean -- a legible, non-circular construct, never a fitted measurement model (observer/sz_obs.py)",
}

#: Section 10 counterfactual commitments (Work Package E).
COUNTERFACTUAL_COMMITMENTS: dict = {
    "transforms": ["erase_pressure_from", "reverse_pressure_order"],
    "mechanism": "Simulation(config, historical_pressure_series_override={...}) with identical seed -- see core/historical_counterfactuals.py",
    "exercised_at": "stage5_causal_historical_counterfactuals_matched_seed",
}

#: Section 11 conversion-detection commitments (Work Package F).
CONVERSION_COMMITMENTS: dict = {
    "function_families": list(FUNCTION_FAMILIES),
    "default_window_steps": 50,
    "default_min_window_activity": 3,
    "default_min_persistence_steps": 20,
    "note": "at most one conversion recorded per rule -- the first sustained shift away from its founding dominant function",
}

#: Section 6 ecological feasibility commitments, imported (not restated)
#: from ``experiments/level13_common.py`` (task #93). Actual cut points
#: are frozen at Stage 2 (task #97), not here -- this manifest commits
#: only to the machinery and parameter space, before any draw is scored.
ECOLOGICAL_FEASIBILITY_COMMITMENTS: dict = {
    "parameter_space_fields": [name for name, _, _ in ECOLOGICAL_SPACE_FOR_LEVEL13],
    "lhs_seed": LHS_SEED_ECOLOGICAL_LEVEL13,
    "stratification_basis": "ex_ante_expected_pressure_ratio_only_never_realized_outcomes",
    "cut_points_frozen_at": "stage2_calibration_without_phenotype_labels",
}

#: Section 23's six-way decision gate -- see this module's own docstring
#: for the disclosed, direct-transcription provenance of this list (from
#: docs/level1.3_theoretical_translation.md §6, not reconstructed here).
#: Preregistered BEFORE any Stage 0-9 run so it cannot be reworded
#: afterward to fit whatever a run turns up.
DECISION_GATE_OUTCOMES: dict[str, str] = {
    "A_one_family": "sequencing/pressure-history variation collapses to a single institutional family regardless of order",
    "B_two_families": "sequencing/pressure-history variation produces exactly two reproducible institutional families",
    "C_four_or_more_families": "sequencing/pressure-history variation produces four or more reproducible institutional families",
    "D_continuum": "no discrete clustering at all -- discovery finds a continuous gradient, not separable families",
    "E_transient_differentiation": "differentiation appears but does not persist/entrench -- families converge again given enough steps",
    "F_no_detectable_effect": "no reproducible historical/sequencing effect is detected at all",
}
DECISION_GATE_DO_NOT_PREFER: str = "E_transient_differentiation"
DECISION_GATE_NOTE: str = (
    "\"do not prefer E\" governs the DISCOVERY PIPELINE'S OWN DEFAULT, not the data: nothing in "
    "observer/phenotype_discovery.py, observer/level13_phenotype.py, or any Stage 6-9 script may special-case "
    "or bias toward classifying a result as transient differentiation over the other five options -- "
    "every outcome, E included, remains a legitimate, unprivileged finding if the data support it."
)

#: Section 3/15 RNG discipline, restated as a frozen commitment.
RNG_COMMITMENTS: dict = {
    "rng_mode": "mechanism_substreams",
    "rng_registry_version": RNG_REGISTRY_VERSION,
    "note": "mandatory for every Stage 0-9 run; legacy_single_stream is never used this milestone",
}


def build_manifest() -> dict:
    """Assembles the full frozen manifest. Deterministic given the
    imported constants above -- calling this twice in one process (or
    across processes on the same codebase state) always yields an
    identical dict."""
    return {
        "milestone": "level1.3_historical_sequencing_entrenchment_path_dependent_institutional_differentiation",
        "mechanism_activation_flags": list(MECHANISM_ACTIVATION_FLAGS),
        "stage_sample_sizes": STAGE_SAMPLE_SIZES,
        "discovery_pipeline_commitments": DISCOVERY_PIPELINE_COMMITMENTS,
        "sequencing_commitments": SEQUENCING_COMMITMENTS,
        "sz_obs_commitments": SZ_OBS_COMMITMENTS,
        "counterfactual_commitments": COUNTERFACTUAL_COMMITMENTS,
        "conversion_commitments": CONVERSION_COMMITMENTS,
        "ecological_feasibility_commitments": ECOLOGICAL_FEASIBILITY_COMMITMENTS,
        "decision_gate_outcomes": DECISION_GATE_OUTCOMES,
        "decision_gate_do_not_prefer": DECISION_GATE_DO_NOT_PREFER,
        "decision_gate_note": DECISION_GATE_NOTE,
        "rng_commitments": RNG_COMMITMENTS,
        "firewall": "no SEM/dissertation data, labels, trajectory names, or country names are read anywhere in Stages 0-9 (Section 2)",
    }


def manifest_hash(manifest: dict) -> str:
    """Deterministic SHA-256 over the manifest's canonical (sorted-key)
    JSON serialization -- key order in the source dict never affects the
    hash, only content does."""
    payload = json.dumps(manifest, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_manifest(out_dir: str = OUT_DIR) -> dict:
    """Builds, hashes, and writes the manifest + its hash to disk.
    Returns ``{"manifest": ..., "hash": ...}``. Subsequent stage scripts
    should call :func:`load_and_verify_manifest` rather than
    :func:`build_manifest` directly, so they verify against what was
    actually frozen on disk rather than trusting the in-process module
    state has not been edited since."""
    os.makedirs(out_dir, exist_ok=True)
    manifest = build_manifest()
    digest = manifest_hash(manifest)
    with open(f"{out_dir}/manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True, default=str)
    with open(f"{out_dir}/manifest_hash.txt", "w") as f:
        f.write(digest + "\n")
    return {"manifest": manifest, "hash": digest}


def load_and_verify_manifest(out_dir: str = OUT_DIR) -> dict:
    """Reads the frozen manifest + hash from disk and confirms the
    stored hash still matches the stored content -- catches any
    post-hoc, silent edit to ``manifest.json``. Raises ``ValueError`` on
    mismatch rather than returning a False verdict, since a mismatched
    preregistration manifest is a hard stop for every downstream stage,
    not a soft warning."""
    with open(f"{out_dir}/manifest.json") as f:
        manifest = json.load(f)
    with open(f"{out_dir}/manifest_hash.txt") as f:
        stored_hash = f.read().strip()
    recomputed = manifest_hash(manifest)
    if recomputed != stored_hash:
        raise ValueError(
            f"Preregistration manifest at {out_dir}/manifest.json has been altered since it was "
            f"frozen (stored hash {stored_hash}, recomputed hash {recomputed})."
        )
    return {"manifest": manifest, "hash": recomputed}


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    result = write_manifest()
    print(f"Level 1.3 preregistration manifest frozen at {OUT_DIR}/manifest.json")
    print(f"hash: {result['hash']}")
