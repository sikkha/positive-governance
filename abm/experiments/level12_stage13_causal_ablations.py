#!/usr/bin/env python3
"""Level 1.2, Section 13: causal ablations.

Stages 3-7 (correlational/descriptive) repeatedly surfaced two
candidate explanations for the near-universal ecological collapse
finding without ever testing either causally: (1) Stage 2's own
migration-associated ecological depletion, and (2) Stage 3/5's purely
descriptive observation that above-default `patch_regen_rate`
coincided with the few non-collapse runs seen so far. This script tests
both properly, via matched-seed ablation: for each of `N_SEEDS_PER_
ABLATION` seeds, two conditions differing in EXACTLY ONE factor are run
under the identical seed (`rng_mode="mechanism_substreams"` throughout,
per Section 15's mandatory discipline) -- every other generative
parameter held fixed -- so any paired difference is attributable to
that one ablated factor, not to which random draws happened to occur.

**No result here is used to retune Stage 3's parameter space or rerun
any earlier stage** (Section 20's stop condition) -- this is purely
explanatory analysis of what Stages 3-7 already found, run once, after
those stages, reported as-is."""

from __future__ import annotations

import json

from scipy.stats import wilcoxon

from abm_governance.core.config import SimulationConfig
from experiments.level12_common import ensure_dir, run_and_summarize
from experiments.level12_preregistration import load_and_verify_manifest

OUT_DIR = "outputs/level12_stage13_causal_ablations"
POPULATION = 40
N_PATCHES = 4
N_STEPS = 400
N_SEEDS_PER_ABLATION = 8
SEED_BASE = 9000

#: Low/high bounds reused directly from Stage 3's own PARAMETER_SPACE
#: for patch_regen_rate -- not re-chosen for this ablation, so the
#: ablation tests exactly the range Stage 3 sampled from.
REGEN_RATE_LOW = 0.2
REGEN_RATE_HIGH = 1.0


def _base_kwargs(seed: int) -> dict:
    return dict(
        population_size=POPULATION, n_steps=N_STEPS, n_patches=N_PATCHES, seed=seed,
        rng_mode="mechanism_substreams",
        institutional_observation_enabled=True, institutional_transmission_enabled=True,
        membership_exit_enabled=True, institutional_scaling_enabled=True,
    )


def run_migration_ablation() -> dict:
    """Ablation 1: migration_enabled True vs. False, matched seeds,
    everything else (including the other 4 Level 1.2 mechanisms) held
    on -- directly tests Stage 2's migration-associated-collapse
    finding causally rather than by single-condition comparison."""
    pairs = []
    for i in range(N_SEEDS_PER_ABLATION):
        seed = SEED_BASE + i
        off = SimulationConfig.level11_complete(migration_enabled=False, **_base_kwargs(seed))
        on = SimulationConfig.level11_complete(migration_enabled=True, **_base_kwargs(seed))
        off_out = run_and_summarize(off)
        on_out = run_and_summarize(on)
        pairs.append({
            "seed": seed,
            "migration_off_outcome_label": off_out["all_outcome_label"],
            "migration_on_outcome_label": on_out["all_outcome_label"],
            "migration_off_ecological_resource_fraction": off_out["ecological_resource_fraction"],
            "migration_on_ecological_resource_fraction": on_out["ecological_resource_fraction"],
        })
    return _summarize_pairs(pairs, "migration_off_ecological_resource_fraction", "migration_on_ecological_resource_fraction", "migration_off_outcome_label", "migration_on_outcome_label")


def run_regen_rate_ablation() -> dict:
    """Ablation 2: patch_regen_rate at Stage 3's own sampled low (0.2)
    vs. high (1.0) bound, matched seeds, all five Level 1.2 mechanisms
    on -- directly tests the regen-rate observation carried, purely
    descriptively, since Stage 3."""
    pairs = []
    for i in range(N_SEEDS_PER_ABLATION):
        seed = SEED_BASE + 100 + i
        low = SimulationConfig.level11_complete(migration_enabled=True, patch_regen_rate=REGEN_RATE_LOW, **_base_kwargs(seed))
        high = SimulationConfig.level11_complete(migration_enabled=True, patch_regen_rate=REGEN_RATE_HIGH, **_base_kwargs(seed))
        low_out = run_and_summarize(low)
        high_out = run_and_summarize(high)
        pairs.append({
            "seed": seed,
            "regen_low_outcome_label": low_out["all_outcome_label"],
            "regen_high_outcome_label": high_out["all_outcome_label"],
            "regen_low_ecological_resource_fraction": low_out["ecological_resource_fraction"],
            "regen_high_ecological_resource_fraction": high_out["ecological_resource_fraction"],
        })
    return _summarize_pairs(pairs, "regen_low_ecological_resource_fraction", "regen_high_ecological_resource_fraction", "regen_low_outcome_label", "regen_high_outcome_label")


def _summarize_pairs(pairs: list[dict], key_a: str, key_b: str, label_a: str, label_b: str) -> dict:
    diffs = [p[key_b] - p[key_a] for p in pairs]
    n_b_greater = sum(1 for d in diffs if d > 0)
    n_a_greater = sum(1 for d in diffs if d < 0)
    n_tied = len(diffs) - n_b_greater - n_a_greater
    mean_diff = sum(diffs) / len(diffs) if diffs else float("nan")
    outcome_transitions = sum(1 for p in pairs if p[label_a] != p[label_b])
    wilcoxon_result = {"statistic": None, "p_value": None, "note": "not computed"}
    try:
        if any(d != 0 for d in diffs):
            stat, p = wilcoxon(diffs)
            wilcoxon_result = {"statistic": float(stat), "p_value": float(p), "note": "n too small for a confident test; supplementary only"}
    except ValueError as exc:
        wilcoxon_result["note"] = str(exc)
    return {
        "pairs": pairs, "n_pairs": len(pairs),
        "n_b_greater_ecological_fraction": n_b_greater, "n_a_greater_ecological_fraction": n_a_greater, "n_tied": n_tied,
        "mean_paired_difference": mean_diff, "n_outcome_label_transitions": outcome_transitions,
        "wilcoxon_signed_rank": wilcoxon_result,
    }


def run() -> dict:
    ensure_dir(OUT_DIR)
    load_and_verify_manifest()  # hard stop if Stage 0's frozen manifest was altered

    migration_result = run_migration_ablation()
    regen_result = run_regen_rate_ablation()

    report = {"migration_ablation": migration_result, "regen_rate_ablation": regen_result}
    with open(f"{OUT_DIR}/stage13_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(
        f"Migration ablation: mean paired diff (on - off) in ecological fraction = "
        f"{migration_result['mean_paired_difference']:.4f}, "
        f"{migration_result['n_a_greater_ecological_fraction']}/{migration_result['n_pairs']} pairs favor migration OFF, "
        f"{migration_result['n_outcome_label_transitions']}/{migration_result['n_pairs']} outcome-label transitions.",
        flush=True,
    )
    print(
        f"Regen-rate ablation: mean paired diff (high - low) in ecological fraction = "
        f"{regen_result['mean_paired_difference']:.4f}, "
        f"{regen_result['n_b_greater_ecological_fraction']}/{regen_result['n_pairs']} pairs favor high regen, "
        f"{regen_result['n_outcome_label_transitions']}/{regen_result['n_pairs']} outcome-label transitions.",
        flush=True,
    )
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
