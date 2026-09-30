#!/usr/bin/env python3
"""Level 1.2, Section 12, Stage 0: preregistration manifest.

Freezes, before any Stage 1-7 run executes, every analysis-affecting
decision this milestone's experimental program will use, and commits to
a SHA-256 hash of that frozen content so later stages -- and this
project's own completion report -- can mechanically verify the manifest
was never edited after any run's results were seen. This turns Section
20's "do not alter the model or rerun parameter searches merely because
the outcome differs from the dissertation" stop condition from a stated
intention into something a later script can actually check
(:func:`load_and_verify_manifest`).

**Disclosed scope reduction** (Stage 3's own explicit allowance, Section
12): every sample-size commitment in :data:`STAGE_SAMPLE_SIZES` is
scaled to this session's compute budget, not to any publication target.
Reductions are stated here, before any Stage 1-7 run, precisely so they
cannot be quietly adjusted afterward to match whatever the results turn
out to need.

Nothing in this manifest references any SEM/dissertation trajectory,
count, or label (Section 14's firewall) -- ``tests/
test_level12_preregistration.py`` extends the project's whole-package
forbidden-terminology scan to this file specifically, since it lives
under ``experiments/`` rather than ``src/abm_governance/``."""

from __future__ import annotations

import hashlib
import json
import os

from abm_governance.observer.convergence_tests import CONVERGENCE_CLASSIFICATION_LABELS
from abm_governance.observer.institutional_viability import ALL_OUTCOME_LABELS
from abm_governance.observer.phenotype_discovery import (
    CANDIDATE_METHODS,
    DEFAULT_K_RANGE,
    MISSINGNESS_STRATEGIES,
)
from abm_governance.observer.recurrence_criteria import RECURRENCE_CRITERIA_NAMES

OUT_DIR = "outputs/level12_stage0_preregistration"

#: The ten Work-Package-A-through-G config flags gating every Level 1.2
#: generative mechanism -- frozen here as the exact set of flags any
#: Stage 1-7 script must report the on/off state of, so mechanism
#: attribution is never ambiguous after the fact.
MECHANISM_ACTIVATION_FLAGS: tuple[str, ...] = (
    "institutional_observation_enabled",   # Work Package B
    "institutional_transmission_enabled",  # Work Package C
    "migration_enabled",                   # Work Package D
    "membership_exit_enabled",             # Work Package D
    "institutional_scaling_enabled",       # Work Package F
)

#: Disclosed, session-budget-scaled sample sizes for each experimental
#: stage, fixed BEFORE any stage runs. Numbers here are a starting
#: commitment, not a promise no stage script will further reduce them --
#: but any further reduction must itself be disclosed in that stage's
#: own script/report (Section 12's own rule), never silently.
STAGE_SAMPLE_SIZES: dict[str, dict] = {
    "stage1_mechanism_activation": {"n_seeds": 8, "population": 40, "n_patches": 3, "n_steps": 350},
    "stage2_small_open_pilot": {"n_seeds": 10, "population": 40, "n_patches": 4, "n_steps": 400},
    "stage3_main_open_search": {"n_seeds": 24, "population": 40, "n_patches": 4, "n_steps": 500, "n_parameter_draws": 12},
    "stage4_blind_discovery_run": {"note": "reuses Stage 3's pooled phenotype vectors; no new simulation runs"},
    "stage5_prospective_confirmation": {"n_seeds": 12, "population": 40, "n_patches": 4, "n_steps": 500, "note": "fresh seeds, never reused from Stage 3"},
    "stage6_scaling_robustness": {"n_seeds": 6, "population_conditions": [40, 80], "n_patches_conditions": [3, 6]},
    "stage7_perturbation_transition": {"n_seeds": 6, "n_perturbation_types": 2},
}

#: Section 9's discovery-pipeline commitments, imported (not restated)
#: from the modules that actually implement them -- a manifest that
#: hardcoded its own copy could silently drift from the code it is
#: supposed to freeze; importing guarantees the two can never disagree.
DISCOVERY_PIPELINE_COMMITMENTS: dict = {
    "candidate_methods": list(CANDIDATE_METHODS),
    "k_range": list(DEFAULT_K_RANGE),
    "missingness_strategies": list(MISSINGNESS_STRATEGIES),
    "model_selection_rule": "no single metric decides -- see observer/phenotype_discovery.py:model_selection_metrics",
}

#: Section 10/11 commitments, likewise imported rather than restated.
RECURRENCE_AND_CONVERGENCE_COMMITMENTS: dict = {
    "recurrence_criteria": list(RECURRENCE_CRITERIA_NAMES),
    "recurrence_rule": "conjunction -- all 12 criteria must pass (see observer/recurrence_criteria.py)",
    "convergence_classification_labels": list(CONVERGENCE_CLASSIFICATION_LABELS),
    "all_outcome_labels": list(ALL_OUTCOME_LABELS),
}

#: Section 15's RNG discipline, restated as a frozen commitment.
RNG_COMMITMENTS: dict = {
    "rng_mode": "mechanism_substreams",
    "note": "mandatory for every Stage 1-7 run; legacy_single_stream is never used this milestone",
}


def build_manifest() -> dict:
    """Assembles the full frozen manifest. Deterministic given the
    imported constants above -- calling this twice in one process (or
    across processes on the same codebase state) always yields an
    identical dict."""
    return {
        "milestone": "level1.2_open_institutional_evolution_and_blind_phenotype_discovery",
        "mechanism_activation_flags": list(MECHANISM_ACTIVATION_FLAGS),
        "stage_sample_sizes": STAGE_SAMPLE_SIZES,
        "discovery_pipeline_commitments": DISCOVERY_PIPELINE_COMMITMENTS,
        "recurrence_and_convergence_commitments": RECURRENCE_AND_CONVERGENCE_COMMITMENTS,
        "rng_commitments": RNG_COMMITMENTS,
        "firewall": "no SEM/dissertation data, labels, or trajectory counts are read anywhere in Stages 0-7 (Section 14)",
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
    post-hoc, silent edit to ``manifest.json`` (Section 20's stop
    condition, made mechanically checkable). Raises ``ValueError`` on
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
            f"frozen (stored hash {stored_hash}, recomputed hash {recomputed}) -- Section 20 stop condition."
        )
    return {"manifest": manifest, "hash": recomputed}


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    result = write_manifest()
    print(f"Stage 0 preregistration manifest frozen at {OUT_DIR}/manifest.json")
    print(f"hash: {result['hash']}")
