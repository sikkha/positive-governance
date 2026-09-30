#!/usr/bin/env python3
"""Level 1.3, Stage 8 (task #103): S_obs-Z_obs mapping.

Per the frozen preregistration manifest's own `stage8_s_obs_z_obs_
mapping` commitment: "reuses Stage 3-7's own runs' event logs --
`observer/sz_obs.py` is purely post-hoc, no new simulation runs
required." In practice this means reusing the S_obs/Z_obs VALUES
Work Package H's `level13_phenotype_vector` already computed from each
run's own event log at run time (Stage 3/4/5/7 each already stored
`phenotype_vector["S_obs"]`/`["Z_obs"]`) rather than re-reading raw
event logs a second time -- the same "reuse the already-computed
vector" discipline Stage 6 already established for pooling.

**What this stage adds beyond Stage 6's own pooled clustering.** Stage
6 asked "does phenotype STRUCTURE cluster" across all 14 Work Package H
dimensions. This stage asks a narrower, more specific question: how do
the two observer-side composites Section 12 defines -- S_obs
(delegation/administrative_function/monitoring/interpatch_coordination
+ performance_legitimacy, unweighted mean) and Z_obs (accountability/
bargaining_participation + procedural_legitimacy, unweighted mean) --
relate to EACH OTHER and to the other mechanism-level dimensions
(entrenchment, conversion_incidence), pooled across Stage 3 (72 runs),
Stage 4 (96 runs), Stage 5 (48 runs -- matched base/erased/reversed
triples), and Stage 7 (12 fresh runs) = 228 rows. Stage 6 itself
contributes no additional runs of its own (it pools Stage 3-5, adding
nothing new) and is not re-pooled here to avoid double-counting the
same 216 rows.

**Descriptive mapping only, never a trajectory classifier.** This
script reports correlation (Pearson and Spearman, since neither
distribution is assumed) between S_obs and Z_obs -- pooled and broken
down by source stage -- a simple, disclosed median-split joint
distribution table (four count cells, purely descriptive, never a named
typology), and each composite's own correlation with entrenchment/
conversion_incidence. It also reuses (never recomputes) Stage 5's own
already-reported mean counterfactual shift in S_obs/Z_obs, since that
IS this stage's own "does a historical manipulation move the S_obs-Z_obs
position" question, already answered by Stage 5's own matched-pair
design. No six-way decision-gate verdict is rendered here -- the same
explicit deferral as Stage 6/7."""

from __future__ import annotations

import hashlib
import json
import os

import numpy as np
from scipy.stats import pearsonr, spearmanr

from experiments import level13_stage6_blind_phenotype_discovery as stage6
from experiments import level13_stage7_fresh_confirmation as stage7

OUT_DIR = "outputs/level13_stage8_s_obs_z_obs_mapping"

STAGE3_PATH = stage6.STAGE3_PATH
STAGE4_PATH = stage6.STAGE4_PATH
STAGE5_PATH = stage6.STAGE5_PATH
STAGE7_PATH = f"{stage7.OUT_DIR}/records.json"

#: Beyond S_obs/Z_obs themselves, the other Work Package H dimensions
#: this stage's own correlation table covers -- entrenchment and
#: conversion_incidence are single scalars (not composites), so they
#: are meaningful covariates without needing their own sub-dimension
#: breakdown the way S_obs/Z_obs's own response-dimension components
#: already have (Work Package G's own module).
_COVARIATES: tuple[str, ...] = ("entrenchment", "performance_legitimacy", "procedural_legitimacy", "conversion_incidence")


def pool_s_obs_z_obs() -> list[dict]:
    stage3 = stage6._load_and_verify(STAGE3_PATH)
    stage4 = stage6._load_and_verify(STAGE4_PATH)
    stage5 = stage6._load_and_verify(STAGE5_PATH)
    stage7_report = stage6._load_and_verify(STAGE7_PATH)

    pooled = []

    def _row(source: str, seed, pv: dict) -> dict:
        row = {"source_stage": source, "seed": seed, "S_obs": pv["S_obs"], "Z_obs": pv["Z_obs"]}
        for cov in _COVARIATES:
            row[cov] = pv.get(cov, float("nan"))
        return row

    for r in stage3["records"]:
        pooled.append(_row("stage3", r["seed"], r["phenotype_vector"]))
    for r in stage4["records"]:
        pooled.append(_row("stage4", r["seed"], r["phenotype_vector"]))
    for r in stage5["records"]:
        for run_type in ("base", "erased", "reversed"):
            pooled.append(_row(f"stage5_{run_type}", r["seed"], r[run_type]["phenotype_vector"]))
    for r in stage7_report["fresh_records"]:
        pooled.append(_row("stage7", r["seed"], r["phenotype_vector"]))

    return pooled


def _correlation(x: list[float], y: list[float]) -> dict:
    x_arr, y_arr = np.array(x, dtype=float), np.array(y, dtype=float)
    mask = np.isfinite(x_arr) & np.isfinite(y_arr)
    n = int(mask.sum())
    if n < 3 or np.std(x_arr[mask]) == 0 or np.std(y_arr[mask]) == 0:
        return {"n": n, "pearson_r": float("nan"), "pearson_p": float("nan"), "spearman_r": float("nan"), "spearman_p": float("nan")}
    pr, pp = pearsonr(x_arr[mask], y_arr[mask])
    sr, sp = spearmanr(x_arr[mask], y_arr[mask])
    return {"n": n, "pearson_r": float(pr), "pearson_p": float(pp), "spearman_r": float(sr), "spearman_p": float(sp)}


def _median_split_joint_table(s_obs: list[float], z_obs: list[float]) -> dict:
    """A purely descriptive four-cell count table (median split on each
    axis independently) -- never a named typology, never fed back into
    any generative mechanism, never compared against any SEM/
    dissertation label."""
    s_arr, z_arr = np.array(s_obs, dtype=float), np.array(z_obs, dtype=float)
    mask = np.isfinite(s_arr) & np.isfinite(z_arr)
    s_med, z_med = float(np.median(s_arr[mask])), float(np.median(z_arr[mask]))
    s_high, z_high = s_arr[mask] >= s_med, z_arr[mask] >= z_med
    return {
        "s_obs_median": s_med, "z_obs_median": z_med, "n": int(mask.sum()),
        "high_s_high_z": int(np.sum(s_high & z_high)),
        "high_s_low_z": int(np.sum(s_high & ~z_high)),
        "low_s_high_z": int(np.sum(~s_high & z_high)),
        "low_s_low_z": int(np.sum(~s_high & ~z_high)),
    }


def run() -> dict:
    pooled = pool_s_obs_z_obs()
    s_obs = [p["S_obs"] for p in pooled]
    z_obs = [p["Z_obs"] for p in pooled]

    by_source: dict[str, list[dict]] = {}
    for p in pooled:
        by_source.setdefault(p["source_stage"], []).append(p)

    correlation_by_source = {
        source: _correlation([r["S_obs"] for r in rows], [r["Z_obs"] for r in rows])
        for source, rows in by_source.items()
    }

    covariate_correlations = {
        cov: {
            "with_s_obs": _correlation(s_obs, [p[cov] for p in pooled]),
            "with_z_obs": _correlation(z_obs, [p[cov] for p in pooled]),
        }
        for cov in _COVARIATES
    }

    # Reused, never recomputed: Stage 5's own already-reported
    # counterfactual shift in S_obs/Z_obs -- this IS the "does a
    # historical manipulation move the joint S_obs-Z_obs position"
    # question, already answered by that stage's matched-pair design.
    stage5_report = stage6._load_and_verify(STAGE5_PATH)
    counterfactual_shift = {
        key: stage5_report[key] for key in (
            "mean_erased_vs_base_s_obs_abs_diff", "mean_erased_vs_base_z_obs_abs_diff",
            "mean_reversed_vs_base_s_obs_abs_diff", "mean_reversed_vs_base_z_obs_abs_diff",
        )
    }

    return {
        "milestone": "level1.3_stage8_s_obs_z_obs_mapping",
        "source_files": {"stage3": STAGE3_PATH, "stage4": STAGE4_PATH, "stage5": STAGE5_PATH, "stage7": STAGE7_PATH},
        "n_pooled_by_source": {s: len(rows) for s, rows in sorted(by_source.items())},
        "n_total": len(pooled),
        "pooled_correlation": _correlation(s_obs, z_obs),
        "correlation_by_source_stage": correlation_by_source,
        "median_split_joint_table": _median_split_joint_table(s_obs, z_obs),
        "covariate_correlations": covariate_correlations,
        "stage5_reused_counterfactual_shift": counterfactual_shift,
        "decision_gate_note": (
            "no six-way decision-gate verdict is rendered here -- Section 23's classification "
            "(task #108) synthesizes this stage alongside Stage 6/7/9's own evidence"
        ),
    }


def report_hash(report: dict) -> str:
    payload = json.dumps(report, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_report(out_dir: str = OUT_DIR) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    report = run()
    digest = report_hash(report)
    report["report_hash"] = digest
    with open(f"{out_dir}/results.json", "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    result = write_report()
    print(f"Level 1.3 Stage 8: n_total={result['n_total']}")
    print(f"pooled S_obs-Z_obs correlation: {result['pooled_correlation']}")
    print(f"report written to {OUT_DIR}/results.json")
