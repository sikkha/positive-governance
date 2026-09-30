#!/usr/bin/env python3
"""Level 1.3b, Work Package J / Stage 9 (task #122, Section 14):
S_obs/Z_obs measurement audit.

**Data source, disclosed.** Stage 4's own 240 records (`outputs/
level13b_stage4_homogeneous_discovery/records.json`) stored only the
final AGGREGATE `S_obs_final`/`Z_obs_final` scalars, not the 8
individual component series `s_obs_series`/`z_obs_series` are built
from (`observer/sz_obs.py`'s own module docstring: S_obs = mean of
`delegation`, `administrative_function`, `monitoring`,
`interpatch_coordination`, `performance_legitimacy`; Z_obs = mean of
`accountability`, `bargaining_participation`, `procedural_legitimacy`
-- 7 distinct dimensions total, DISJOINT between the two axes). Several
of this stage's own required calculations (`factor_structure_
analysis`, `leave_one_out_variant`, `non_normalized_variant`) need
that component-level breakdown. Rather than draw a fresh sample, this
script deterministically RE-RUNS Stage 4's own exact 240 (config,
seed) pairs (`SimulationConfig`/seed are fully reproducible --
confirmed as a first-line consistency check: recomputed `S_obs_final`/
`Z_obs_final` must equal the archived values exactly) and additionally
extracts each of the 7 raw component final-step values Stage 4 itself
never persisted.

**The frozen rule (`STAGE9_MEASUREMENT_AUDIT["rule"]`): do not redefine
S_obs/Z_obs to manufacture independence; if measurement-induced,
correct transparently, version it, preserve both the original and
corrected variant.** This script never overwrites `observer/sz_obs.py`
-- every "variant" below is a SEPARATE, clearly-labeled analysis
performed on the side, not a silent redefinition.

**The 7 candidate explanations, tested via the required calculations
below (see each analysis function's own docstring for its exact
operationalization):**

* ``genuine_coupling`` / ``shared_construction`` / ``common_
  ecological_driver`` / ``common_normalization`` -- ``factor_structure_
  analysis`` (do the 7 raw components load onto 2 separate factors
  matching the S/Z split, or mostly onto 1 dominant factor?),
  ``within_point_correlation`` vs. ``between_point_correlation`` (does
  coupling survive within a FIXED generative condition across only
  seed noise, or does it appear only ACROSS different conditions?).
* ``activity_volume_confounding`` / ``presence_absence_confounding`` --
  ``non_normalized_variant`` (sum instead of mean -- does correlation
  change when raw activity VOLUME, not normalized rate, is compared?)
  and ``partial_correlation_controlling_ecological_stratum`` (does
  correlation survive controlling for the one factor most plausibly
  driving both axes' overall activity level up or down together?).
* ``measurement_overlap`` -- the 7 components are already confirmed
  disjoint between S_obs/Z_obs by direct inspection of `observer/
  sz_obs.py`'s own constants (`S_OBS_RESPONSE_DIMENSIONS` /
  `Z_OBS_RESPONSE_DIMENSIONS` share zero names) -- reported here as a
  structural fact, not re-derived statistically. ``leave_one_out_
  variant`` additionally checks whether the correlation is driven by
  any SINGLE dominant component rather than genuine multi-dimensional
  overlap in what's measured."""

from __future__ import annotations

import json
import multiprocessing
import os

import numpy as np

from abm_governance.observer.sequencing_diagnostics import institutional_response_series
from abm_governance.observer.sz_obs import (
    S_OBS_RESPONSE_DIMENSIONS,
    Z_OBS_RESPONSE_DIMENSIONS,
    performance_legitimacy_series,
    procedural_legitimacy_series,
)
from abm_governance.simulation import Simulation
from experiments.level13b_preregistration import STAGE9_MEASUREMENT_AUDIT, load_and_verify_manifest
from experiments.level13b_stage4_homogeneous_discovery import (
    N_STEPS, _build_config, _load_ecological_points, _stratum_from_draw, lhs_draws,
)

OUT_DIR = "outputs/level13b_stage9_measurement_audit"
STAGE4_RECORDS_PATH = "outputs/level13b_stage4_homogeneous_discovery/records.json"
STAGE4_N_POINTS = 48
STAGE4_N_SEEDS_PER_POINT = 5
STAGE4_SEED_BASE = 8_700_000
ALL_COMPONENTS: tuple[str, ...] = S_OBS_RESPONSE_DIMENSIONS + ("performance_legitimacy",) + Z_OBS_RESPONSE_DIMENSIONS + ("procedural_legitimacy",)


def _job(args) -> dict:
    point_id, draw, seed, eco_points = args
    config, stratum, _n_shocks = _build_config(draw, seed, eco_points)
    sim = Simulation(config)
    sim.run()
    response = institutional_response_series(sim.event_log, N_STEPS)
    perf = performance_legitimacy_series(sim.event_log, N_STEPS)
    proc = procedural_legitimacy_series(sim.event_log, N_STEPS)
    components = {name: float(response[name][-1]) for name in S_OBS_RESPONSE_DIMENSIONS + Z_OBS_RESPONSE_DIMENSIONS}
    components["performance_legitimacy"] = float(perf[-1])
    components["procedural_legitimacy"] = float(proc[-1])
    s_obs = float(np.mean([components[n] for n in S_OBS_RESPONSE_DIMENSIONS] + [components["performance_legitimacy"]]))
    z_obs = float(np.mean([components[n] for n in Z_OBS_RESPONSE_DIMENSIONS] + [components["procedural_legitimacy"]]))
    return {"point_id": point_id, "seed": seed, "stratum": stratum, "components": components, "S_obs_recomputed": s_obs, "Z_obs_recomputed": z_obs}


def rerun_stage4_with_components() -> list[dict]:
    eco_points = _load_ecological_points()
    draws = lhs_draws(STAGE4_N_POINTS)
    jobs = [
        (point_id, draw, STAGE4_SEED_BASE + point_id * 1000 + s, eco_points)
        for point_id, draw in enumerate(draws)
        for s in range(STAGE4_N_SEEDS_PER_POINT)
    ]
    with multiprocessing.Pool(2) as pool:
        return list(pool.imap(_job, jobs))


def verify_against_archive(recomputed: list[dict]) -> dict:
    with open(STAGE4_RECORDS_PATH) as f:
        archived = json.load(f)["records"]
    by_key = {(r["point_id"], r["seed"]): r for r in archived}
    mismatches = []
    for r in recomputed:
        key = (r["point_id"], r["seed"])
        arch = by_key.get(key)
        if arch is None:
            mismatches.append({"key": key, "reason": "not found in archive"})
            continue
        if not np.isclose(arch["S_obs_final"], r["S_obs_recomputed"]) or not np.isclose(arch["Z_obs_final"], r["Z_obs_recomputed"]):
            mismatches.append({"key": key, "archived_S": arch["S_obs_final"], "recomputed_S": r["S_obs_recomputed"], "archived_Z": arch["Z_obs_final"], "recomputed_Z": r["Z_obs_recomputed"]})
    return {"n_checked": len(recomputed), "n_mismatches": len(mismatches), "mismatches": mismatches[:5], "exact_reproduction": len(mismatches) == 0}


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def raw_correlation(records: list[dict]) -> float:
    s = np.array([r["S_obs_recomputed"] for r in records])
    z = np.array([r["Z_obs_recomputed"] for r in records])
    return _pearson(s, z)


def partial_correlation_controlling_stratum(records: list[dict]) -> dict:
    """Residualize S_obs and Z_obs on stratum dummy variables (OLS via
    lstsq), then correlate the residuals -- the standard partial-
    correlation-via-residualization construction."""
    strata = sorted({r["stratum"] for r in records})
    dummy = np.array([[1.0 if r["stratum"] == st else 0.0 for st in strata] for r in records])
    s = np.array([r["S_obs_recomputed"] for r in records])
    z = np.array([r["Z_obs_recomputed"] for r in records])
    s_coef, *_ = np.linalg.lstsq(dummy, s, rcond=None)
    z_coef, *_ = np.linalg.lstsq(dummy, z, rcond=None)
    s_resid = s - dummy @ s_coef
    z_resid = z - dummy @ z_coef
    return {"partial_correlation": _pearson(s_resid, z_resid), "strata": strata}


def within_and_between_point_correlation(records: list[dict]) -> dict:
    """Within-point: demean S_obs/Z_obs by their own point_id's mean,
    then correlate the residuals (isolates coupling across SEED noise
    holding the generative condition fixed). Between-point: correlate
    the 48 point-level MEANS directly (isolates coupling across
    different generative conditions)."""
    by_point: dict[int, list[dict]] = {}
    for r in records:
        by_point.setdefault(r["point_id"], []).append(r)

    s_resid, z_resid = [], []
    point_means_s, point_means_z = [], []
    for pid, group in by_point.items():
        s_vals = np.array([g["S_obs_recomputed"] for g in group])
        z_vals = np.array([g["Z_obs_recomputed"] for g in group])
        s_resid.extend((s_vals - s_vals.mean()).tolist())
        z_resid.extend((z_vals - z_vals.mean()).tolist())
        point_means_s.append(float(s_vals.mean()))
        point_means_z.append(float(z_vals.mean()))

    return {
        "within_point_correlation": _pearson(np.array(s_resid), np.array(z_resid)),
        "between_point_correlation": _pearson(np.array(point_means_s), np.array(point_means_z)),
        "n_points": len(by_point),
    }


def factor_structure_analysis(records: list[dict]) -> dict:
    """PCA on the 7 standardized raw components -- if the S/Z split
    reflects genuine 2-axis structure, the top 2 components should
    together explain most variance without one component alone
    dominating; if one factor dominates overwhelmingly, that's evidence
    for a single common driver rather than 2 distinct axes."""
    from sklearn.decomposition import PCA
    X = np.array([[r["components"][c] for c in ALL_COMPONENTS] for r in records])
    mean, std = X.mean(axis=0), X.std(axis=0)
    std = np.where(std < 1e-12, 1.0, std)
    Xs = (X - mean) / std
    pca = PCA(n_components=min(7, X.shape[0]))
    pca.fit(Xs)
    loadings = pca.components_[:2]
    return {
        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "first_two_components_cumulative": float(sum(pca.explained_variance_ratio_[:2])),
        "component_names": list(ALL_COMPONENTS),
        "pc1_loadings": loadings[0].tolist(),
        "pc2_loadings": loadings[1].tolist() if loadings.shape[0] > 1 else None,
        "note": (
            "if PC1 alone explains most variance across ALL 7 components (S-axis and Z-axis members "
            "loading similarly on PC1), that favors a common driver over 2 genuinely distinct axes; if "
            "S-axis members load mainly on PC1 and Z-axis members mainly on PC2 (or vice versa), that "
            "favors 2 distinct axes"
        ),
    }


def leave_one_out_variant(records: list[dict]) -> dict:
    """Recompute S_obs/Z_obs leaving out one component at a time (7
    variants) -- checks whether the raw correlation is driven by any
    single dominant component rather than the full disjoint set."""
    results = {}
    for dropped in ALL_COMPONENTS:
        s_dims = [d for d in S_OBS_RESPONSE_DIMENSIONS + ("performance_legitimacy",) if d != dropped]
        z_dims = [d for d in Z_OBS_RESPONSE_DIMENSIONS + ("procedural_legitimacy",) if d != dropped]
        if not s_dims or not z_dims:
            continue
        s = np.array([np.mean([r["components"][d] for d in s_dims]) for r in records])
        z = np.array([np.mean([r["components"][d] for d in z_dims]) for r in records])
        results[dropped] = _pearson(s, z)
    full = raw_correlation(records)
    max_shift = max(abs(full - v) for v in results.values()) if results else float("nan")
    return {"full_correlation": full, "leave_one_out_correlations": results, "max_shift_from_full": max_shift}


def non_normalized_variant(records: list[dict]) -> dict:
    """Sum (not mean) of the same components -- tests whether raw
    activity VOLUME correlation differs from the normalized-rate
    correlation this milestone actually uses."""
    s = np.array([sum(r["components"][d] for d in S_OBS_RESPONSE_DIMENSIONS + ("performance_legitimacy",)) for r in records])
    z = np.array([sum(r["components"][d] for d in Z_OBS_RESPONSE_DIMENSIONS + ("procedural_legitimacy",)) for r in records])
    return {"sum_variant_correlation": _pearson(s, z), "mean_variant_correlation_for_comparison": raw_correlation(records)}


def equal_weight_variant(records: list[dict]) -> dict:
    """The ALREADY-USED equal-weight construction vs. a PCA-loading-
    weighted alternative -- checks robustness to the equal-weight
    choice `observer/sz_obs.py` discloses as deliberate/simple."""
    from sklearn.decomposition import PCA
    X_s = np.array([[r["components"][d] for d in S_OBS_RESPONSE_DIMENSIONS + ("performance_legitimacy",)] for r in records])
    X_z = np.array([[r["components"][d] for d in Z_OBS_RESPONSE_DIMENSIONS + ("procedural_legitimacy",)] for r in records])
    pca_s, pca_z = PCA(n_components=1), PCA(n_components=1)
    s_weighted = pca_s.fit_transform((X_s - X_s.mean(axis=0)) / np.where(X_s.std(axis=0) < 1e-12, 1.0, X_s.std(axis=0))).ravel()
    z_weighted = pca_z.fit_transform((X_z - X_z.mean(axis=0)) / np.where(X_z.std(axis=0) < 1e-12, 1.0, X_z.std(axis=0))).ravel()
    return {
        "equal_weight_correlation": raw_correlation(records),
        "pca_weighted_correlation": _pearson(s_weighted, z_weighted),
    }


def opportunity_denominated_variant(records: list[dict]) -> dict:
    """An alternative denominator: raw activity-rate components summed
    then divided by a fixed 'opportunity' proxy (patch count, held
    constant this milestone at 4 for every Stage 4 point) rather than
    the interval-based per-dimension rate `institutional_response_
    series` already uses -- a genuinely different normalization
    convention, disclosed as a coarse proxy (this milestone's designs
    hold n_patches fixed, so this variant is a constant rescaling of
    the sum variant here, reported for completeness rather than as an
    informative independent check)."""
    n_patches = 4
    s = np.array([sum(r["components"][d] for d in S_OBS_RESPONSE_DIMENSIONS + ("performance_legitimacy",)) / n_patches for r in records])
    z = np.array([sum(r["components"][d] for d in Z_OBS_RESPONSE_DIMENSIONS + ("procedural_legitimacy",)) / n_patches for r in records])
    return {"opportunity_denominated_correlation": _pearson(s, z), "opportunity_proxy": "n_patches (held constant at 4 this milestone)"}


def main() -> dict:
    os.makedirs(OUT_DIR, exist_ok=True)
    load_and_verify_manifest()

    recomputed = rerun_stage4_with_components()
    with open(os.path.join(OUT_DIR, "recomputed_records.json"), "w") as f:
        json.dump({"records": recomputed}, f, indent=2, sort_keys=True, default=str)

    consistency = verify_against_archive(recomputed)

    report = {
        "milestone": "level1.3b_work_package_j_stage9_measurement_audit",
        "n_records": len(recomputed),
        "consistency_check_against_stage4_archive": consistency,
        "structural_fact_measurement_overlap": {
            "s_obs_dimensions": list(S_OBS_RESPONSE_DIMENSIONS) + ["performance_legitimacy"],
            "z_obs_dimensions": list(Z_OBS_RESPONSE_DIMENSIONS) + ["procedural_legitimacy"],
            "shared_dimensions": sorted(set(S_OBS_RESPONSE_DIMENSIONS) & set(Z_OBS_RESPONSE_DIMENSIONS)),
            "note": "zero shared dimensions confirmed by direct inspection of observer/sz_obs.py's own constants",
        },
        "raw_correlation": raw_correlation(recomputed),
        "partial_correlation_controlling_ecological_stratum": partial_correlation_controlling_stratum(recomputed),
        "within_and_between_point_correlation": within_and_between_point_correlation(recomputed),
        "factor_structure_analysis": factor_structure_analysis(recomputed),
        "leave_one_out_variant": leave_one_out_variant(recomputed),
        "non_normalized_variant": non_normalized_variant(recomputed),
        "equal_weight_variant": equal_weight_variant(recomputed),
        "opportunity_denominated_variant": opportunity_denominated_variant(recomputed),
        "rule": STAGE9_MEASUREMENT_AUDIT["rule"],
        "redefinition_status": "observer/sz_obs.py was NOT modified by this audit -- every variant above is a side analysis only",
    }
    with open(os.path.join(OUT_DIR, "stage9_report.json"), "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    print(json.dumps({k: v for k, v in report.items() if k != "leave_one_out_variant"}, indent=2, sort_keys=True, default=str))
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
