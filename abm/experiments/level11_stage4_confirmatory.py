#!/usr/bin/env python3
"""Level 1.1, Stage 4: confirmatory replication of Stage 3's clearest
exploratory pattern, on fresh seeds.

Stage 3 (``outputs/level11_stage3_search/stage3_report.json``) found a
selection-procedure-independent pattern: with discretion and
accountability both active, the modal Work Package K label at a rule
shifts from ``persistent_delegation`` (the near-universal label with
both mechanisms off) to ``accountable_delegation`` -- a plausible
"active oversight measurably contests, rather than merely coexists
with, discretion" reading, but only a mechanism-validation label
distribution, never a governance-type claim. This stage re-runs exactly
that one contrast (``lottery`` selection, the simplest procedure Level
1.0 itself already uses; procedure was shown not to matter in Stage 3)
on 20 entirely fresh seeds and reports a seed-clustered bootstrap CI
(Work Package A) on the per-seed label fractions -- the confirmatory-
grade claim, as distinct from Stage 3's exploratory one.
"""

from __future__ import annotations

import json

from abm_governance.core.config import SimulationConfig
from abm_governance.observer import replication_units as ru
from experiments.level11_common import ensure_dir, run_and_summarize

OUT_DIR = "outputs/level11_stage4_confirmatory"
N_SEEDS = 20
N_STEPS = 350
POPULATION = 40
N_PATCHES = 3


def _config(discretion: bool, accountability: bool, seed: int) -> SimulationConfig:
    overrides = {
        "population_size": POPULATION, "n_steps": N_STEPS, "n_patches": N_PATCHES, "seed": seed,
        "delegate_selection_procedure": "lottery", "discretion_enabled": discretion,
        "accountability_enabled": accountability,
    }
    if accountability:
        overrides["monitoring_mode"] = "voluntary"
        overrides["sanction_mode"] = "voluntary"
    return SimulationConfig.level11_delegation_only(**overrides)


def _per_seed_fraction(label: str, discretion: bool, accountability: bool) -> dict:
    fractions_by_seed = {}
    for seed in range(N_SEEDS):
        real_seed = 6000 + seed
        config = _config(discretion, accountability, real_seed)
        out = run_and_summarize(config)
        labels = [c["label"] for c in out["rule_classifications"]]
        fractions_by_seed[seed] = [labels.count(label) / len(labels)] if labels else [0.0]
    return fractions_by_seed


def run() -> dict:
    ensure_dir(OUT_DIR)
    print("condition: both_active (discretion=True, accountability=True)...", flush=True)
    both_active_accountable = _per_seed_fraction("accountable_delegation", True, True)
    both_active_persistent = _per_seed_fraction("persistent_delegation", True, True)
    print("condition: both_off (discretion=False, accountability=False)...", flush=True)
    both_off_accountable = _per_seed_fraction("accountable_delegation", False, False)
    both_off_persistent = _per_seed_fraction("persistent_delegation", False, False)

    ci_accountable_both_active = ru.seed_clustered_bootstrap_ci(both_active_accountable, n_boot=2000)
    ci_accountable_both_off = ru.seed_clustered_bootstrap_ci(both_off_accountable, n_boot=2000)
    ci_persistent_both_active = ru.seed_clustered_bootstrap_ci(both_active_persistent, n_boot=2000)
    ci_persistent_both_off = ru.seed_clustered_bootstrap_ci(both_off_persistent, n_boot=2000)

    report = {
        "n_seeds": N_SEEDS,
        "accountable_delegation_fraction": {
            "both_mechanisms_active": ci_accountable_both_active,
            "both_mechanisms_off": ci_accountable_both_off,
        },
        "persistent_delegation_fraction": {
            "both_mechanisms_active": ci_persistent_both_active,
            "both_mechanisms_off": ci_persistent_both_off,
        },
        "confirmed": (
            ci_accountable_both_active["ci_low"] > ci_accountable_both_off["ci_high"]
            and ci_persistent_both_off["ci_low"] > ci_persistent_both_active["ci_high"]
        ),
    }
    print(json.dumps(report, indent=2, default=str), flush=True)
    with open(f"{OUT_DIR}/stage4_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
