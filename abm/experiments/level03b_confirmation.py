#!/usr/bin/env python3
"""Level 0.3b, Work Package D: candidate confirmation.

Runs each registered candidate (``outputs/level03b_candidate_registry/
candidate_registry.json``) at its ``endogenous`` condition for >= 24
seeds, >= 600 steps, applies the audited classifier, and reports the
seed-level label distribution/agreement plus every continuous outcome
Work Package G specifies. A candidate is reported as "robust" only
against a prespecified agreement threshold (default 0.70, per the
milestone brief) -- with a sensitivity table against two alternative
thresholds (0.60, 0.80) reported alongside, never silently substituted.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from abm_governance.simulation import Simulation
from experiments.level03b_common import build_candidate_config, continuous_outcomes, final_composition, initial_composition

N_SEEDS = 24
N_STEPS = 600
AGREEMENT_THRESHOLDS = (0.6, 0.7, 0.8)
PRIMARY_AGREEMENT_THRESHOLD = 0.7


def _confirm_one_candidate(candidate_key: str, params: dict, n_seeds: int, n_steps: int) -> pd.DataFrame:
    rows = []
    for seed in range(n_seeds):
        config = build_candidate_config(params, seed=seed, n_steps=n_steps, condition="endogenous")
        sim = Simulation(config)
        init = initial_composition(sim)
        result = sim.run()
        outcomes = continuous_outcomes(result)
        final = final_composition(result)
        row = {
            "candidate": candidate_key, "seed": seed, "population_size": params["population_size"],
            "label": outcomes["classify_regime_label"],
            "extraction_propensity_before": init["extraction_propensity_mean"],
            "extraction_propensity_after": final["extraction_propensity_mean"],
            "maintenance_propensity_before": init["maintenance_propensity_mean"],
            "maintenance_propensity_after": final["maintenance_propensity_mean"],
            "n_agents_final": final["n_agents"],
        }
        for k, v in outcomes.items():
            if k not in ("classify_regime", "classify_regime_label"):
                row[k] = v
        rows.append(row)
    return pd.DataFrame(rows)


def run(
    out_root: str = "outputs/level03b_confirmation",
    registry_path: str = "outputs/level03b_candidate_registry/candidate_registry.json",
    n_seeds: int = N_SEEDS,
    n_steps: int = N_STEPS,
) -> dict:
    os.makedirs(out_root, exist_ok=True)
    with open(registry_path, "r", encoding="utf-8") as fh:
        registry = json.load(fh)

    candidate_keys = {
        "interior_persistent": registry["selected"].get("interior_persistent"),
        "nonstationary": registry["selected"].get("nonstationary"),
        "near_collapse": registry["selected"].get("near_collapse"),
    }

    all_rows = []
    failures = []
    per_candidate_summary = {}
    for key, candidate in candidate_keys.items():
        if candidate is None:
            per_candidate_summary[key] = {"status": "no eligible candidate registered"}
            continue
        params = candidate["parameters"]
        try:
            df = _confirm_one_candidate(key, params, n_seeds, n_steps)
        except Exception as exc:  # pragma: no cover - defensive, reported not swallowed
            failures.append({"candidate": key, "error": f"{type(exc).__name__}: {exc}"})
            per_candidate_summary[key] = {"status": "run failed", "error": str(exc)}
            continue
        all_rows.append(df)

        label_counts = df["label"].value_counts().to_dict()
        plurality_label = df["label"].value_counts().idxmax()
        agreement_fraction = label_counts[plurality_label] / len(df)
        sensitivity = {
            f"robust_at_{int(t * 100)}pct": bool(agreement_fraction >= t) for t in AGREEMENT_THRESHOLDS
        }
        per_candidate_summary[key] = {
            "status": "confirmed" if agreement_fraction >= PRIMARY_AGREEMENT_THRESHOLD else "not robustly confirmed",
            "n_seeds": len(df),
            "label_distribution": label_counts,
            "plurality_label": plurality_label,
            "agreement_fraction": agreement_fraction,
            "threshold_sensitivity": sensitivity,
            "mean_post_burn_in_occupancy": float(df["post_burn_in_mean_occupancy"].mean()),
            "std_post_burn_in_occupancy": float(df["post_burn_in_mean_occupancy"].std()),
            "mean_terminal_occupancy": float(df["terminal_window_mean_occupancy"].mean()),
            "mean_patch_survival_fraction": float(df["patch_survival_fraction"].mean()),
            "mean_extraction_propensity_before": float(df["extraction_propensity_before"].mean()),
            "mean_extraction_propensity_after": float(df["extraction_propensity_after"].mean()),
            "mean_maintenance_propensity_before": float(df["maintenance_propensity_before"].mean()),
            "mean_maintenance_propensity_after": float(df["maintenance_propensity_after"].mean()),
        }

    combined = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    combined_path = os.path.join(out_root, "confirmation_run_level.csv")
    combined.to_csv(combined_path, index=False)

    summary = {
        "design": {"n_seeds": n_seeds, "n_steps": n_steps, "burn_in_fraction": 0.2},
        "primary_agreement_threshold": PRIMARY_AGREEMENT_THRESHOLD,
        "n_failures": len(failures),
        "failures": failures,
        "per_candidate": per_candidate_summary,
    }
    summary_path = os.path.join(out_root, "level03b_confirmation_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print(f"[level03b_confirmation] {combined_path}")
    print(f"[level03b_confirmation] {summary_path}")
    print(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
