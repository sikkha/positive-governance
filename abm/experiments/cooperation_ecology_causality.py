#!/usr/bin/env python3
"""Level 0.2, Work Package F: cooperation and ecological causality reporting.

The milestone brief's explicit constraint for this work package: "Do not
assume cooperation is ecologically beneficial." This script does not
encode any prior about the sign or existence of a cooperation-ecology
relationship; it measures association and lead/lag structure and reports
both directions, including "no detectable relationship," as legitimate
outcomes.

Two independent analyses, kept separate because they answer different
questions and have different confound structures:

**Part 1 — cross-sectional, within-parameter-point association (uses the
already-completed ``experiments/phase_sweep.py`` runs; zero new
simulation compute).** Within one fixed ecological parameter point,
different seeds still produce different realized cooperation rates and
different realized ecological outcomes (both are emergent, stochastic
model outputs, not experimenter inputs). Correlating final cooperation
against ecological outcome *across seeds within the same point* isolates
the association from the confound that would otherwise dominate a naive
pooled correlation: ecological parameters simultaneously drive both
cooperation levels and ecological outcomes, so a marginal (pooled,
across-point) correlation between them is not evidence either causes the
other. This script reports the within-point distribution of
correlations *and* the naive pooled correlation side by side so the
confound's size is visible, not hidden.

**Part 2 — within-run, time-lagged association (fresh runs; this script's
only new simulation compute).** For each of three representative
ecological regions (abundant / boundary / depleted, loaded the same way
``experiments/null_model_comparisons.py`` loads them), runs
``--n-seeds`` fresh simulations and computes, per run, the lagged
cross-correlation between cooperation (both the conditional and the
unconditional-per-opportunity signal) and two ecological-balance
quantities (pool occupancy, B_t-realized) — on both raw levels (dominated
by whatever trend the run has, e.g. a monotonic slide toward collapse)
and first differences (removes shared trend, more informative about
which change *precedes* which). A lightweight incremental-R^2 check
(does yesterday's cooperation-change improve a one-step-ahead prediction
of today's occupancy-change beyond occupancy's own lag, and the
symmetric question) is reported as a directional signal, explicitly
NOT labelled "Granger causality" (that requires stationarity and
specification tests this script does not perform) and explicitly NOT
labelled evidence of mechanistic causation — a lagged, non-vanishing
incremental R^2 is consistent with causation in either direction, common
prior causes, or measurement artifacts of the shared generative process,
and this script's job is only to report which pattern (if any) is
present, not to adjudicate among those explanations.

Usage::

    python experiments/cooperation_ecology_causality.py \\
        --sweep-dir outputs/phase_sweep_level02 \\
        --out-dir outputs/cooperation_ecology_causality_level02 \\
        --n-seeds 20 --n-steps 250 --max-lag 15
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import os
import time
import traceback

import numpy as np
import pandas as pd

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.ecological_balance import step_balance_indicators
from abm_governance.simulation import Simulation

N_STEPS_DEFAULT = 250
POPULATION_SIZE_DEFAULT = 30
N_SEEDS_DEFAULT = 20
MAX_LAG_DEFAULT = 15
MIN_SEEDS_FOR_CROSS_SECTIONAL = 10

PARAM_COLS = [
    "environment_regen_rate", "environment_capacity", "subsistence_cost",
    "payoff_temptation", "payoff_reward", "distress_threshold",
]


# ---------------------------------------------------------------------------
# Part 1: cross-sectional association from already-completed sweep runs.
# ---------------------------------------------------------------------------

def load_manifest_runs(sweep_dir: str) -> list[dict]:
    path = os.path.join(sweep_dir, "sweep_manifest.json")
    with open(path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    return [r for r in manifest["runs"] if r["status"] == "ok"]


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    mask = ~(np.isnan(x) | np.isnan(y))
    if mask.sum() < 3 or np.std(x[mask]) == 0 or np.std(y[mask]) == 0:
        return math.nan
    return float(np.corrcoef(x[mask], y[mask])[0, 1])


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    mask = ~(np.isnan(x) | np.isnan(y))
    if mask.sum() < 3:
        return math.nan
    xr = pd.Series(x[mask]).rank().to_numpy()
    yr = pd.Series(y[mask]).rank().to_numpy()
    return _pearson(xr, yr)


_OUTCOME_EXTRACTORS = {
    "mean_occupancy": lambda r: r["balance_summary"]["mean_occupancy"],
    "fraction_time_depleted": lambda r: r["balance_summary"]["fraction_time_depleted"],
    "n_collapse_episodes": lambda r: float(r["n_collapse_episodes"]),
    "longest_collapse_duration": lambda r: float(r["longest_collapse_duration"]),
    "population_failure_peak_fraction": lambda r: r["population_failure"]["peak_fraction"],
}


def cross_sectional_by_point(runs: list[dict], min_seeds: int = MIN_SEEDS_FOR_CROSS_SECTIONAL) -> pd.DataFrame:
    """Per-point (within fixed ecological parameters, across seeds)
    correlation between realized final cooperation and each ecological
    outcome. Only points with >= ``min_seeds`` completed seeds are
    included (a 2-3 seed correlation is not informative)."""
    by_point: dict[tuple, list[dict]] = {}
    for r in runs:
        by_point.setdefault((r["stage"], r["point_id"]), []).append(r)

    rows = []
    for (stage, point_id), point_runs in by_point.items():
        if len(point_runs) < min_seeds:
            continue
        coop = np.array([r["final_cooperation_rate"] for r in point_runs], dtype=float)
        row = {"stage": stage, "point_id": point_id, "n_seeds": len(point_runs)}
        for name, extractor in _OUTCOME_EXTRACTORS.items():
            outcome = np.array([extractor(r) for r in point_runs], dtype=float)
            row[f"pearson_coop_vs_{name}"] = _pearson(coop, outcome)
            row[f"spearman_coop_vs_{name}"] = _spearman(coop, outcome)
        rows.append(row)
    return pd.DataFrame(rows)


def pooled_confounded_correlation(runs: list[dict]) -> dict:
    """The naive pooled-across-all-points correlation — confounded by
    ecological parameters simultaneously driving both cooperation and
    ecological outcomes. Reported only as a contrast against Part 1's
    within-point result, never as the primary finding."""
    coop = np.array([r["final_cooperation_rate"] for r in runs], dtype=float)
    out = {"n_runs": len(runs)}
    for name, extractor in _OUTCOME_EXTRACTORS.items():
        outcome = np.array([extractor(r) for r in runs], dtype=float)
        out[f"pooled_pearson_coop_vs_{name}"] = _pearson(coop, outcome)
    return out


# ---------------------------------------------------------------------------
# Part 2: within-run, time-lagged association (fresh simulation runs).
# ---------------------------------------------------------------------------

def _load_regions(sweep_dir: str) -> dict[str, dict]:
    stage1 = pd.read_csv(os.path.join(sweep_dir, "stage1_summary.csv"))
    with open(os.path.join(sweep_dir, "sweep_manifest.json"), "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    boundary_points = manifest["boundary_points_selected"]
    if not boundary_points:
        raise RuntimeError("no boundary points in sweep manifest; run experiments/phase_sweep.py first")

    abundant_row = stage1.sort_values("mean_occupancy_mean", ascending=False).iloc[0]
    depleted_candidates = stage1[stage1["mean_occupancy_mean"] == 0]
    depleted_row = (depleted_candidates if len(depleted_candidates) else stage1.sort_values("mean_occupancy_mean")).iloc[0]

    return {
        "abundant": {c: float(abundant_row[c]) for c in PARAM_COLS},
        "depleted": {c: float(depleted_row[c]) for c in PARAM_COLS},
        "boundary": dict(boundary_points[0]["params"]),
    }


@dataclasses.dataclass
class RunSpec:
    region: str
    seed: int
    n_steps: int
    population_size: int


def _build_config(spec: RunSpec, region_params: dict) -> SimulationConfig:
    return SimulationConfig(
        population_size=spec.population_size,
        n_steps=spec.n_steps,
        seed=spec.seed,
        mean_degree=4,
        ecology_enabled=True,
        relationship_dynamics_enabled=True,
        payoff_punishment=1.0,
        payoff_sucker=0.0,
        environment_initial_fraction=0.5,
        viability_mode="none",
        fitness_mode="cumulative_resources",
        punishment_enabled=True,
        **region_params,
    )


def lag_correlations(x: np.ndarray, y: np.ndarray, max_lag: int) -> dict[int, float]:
    """Pearson correlation between x[t] and y[t + lag] for every integer
    lag in [-max_lag, max_lag]. Positive lag means y is shifted forward
    relative to x (x[t] compared against a *later* y) — i.e. a peak at a
    positive lag means x's current value best matches y's future value
    (x leads y). NaN for lags leaving fewer than 10 valid overlapping
    points, or a degenerate (constant) window."""
    n = len(x)
    out: dict[int, float] = {}
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            xs, ys = x[: n - lag] if lag > 0 else x, y[lag:]
        else:
            k = -lag
            xs, ys = x[k:], y[: n - k]
        if len(xs) < 10:
            out[lag] = math.nan
            continue
        out[lag] = _pearson(xs, ys)
    return out


def best_lag(corrs: dict[int, float]) -> tuple[float, float]:
    """Returns (lag, correlation) for the lag with the largest |correlation|,
    or (nan, nan) if every lag is NaN."""
    valid = {lag: c for lag, c in corrs.items() if not math.isnan(c)}
    if not valid:
        return math.nan, math.nan
    lag = max(valid, key=lambda k: abs(valid[k]))
    return float(lag), valid[lag]


def _ols_r2(y: np.ndarray, X: np.ndarray) -> float:
    """R^2 of an OLS fit of y on X (X already includes an intercept
    column). NaN-safe: rows with any NaN are dropped first."""
    mask = ~(np.isnan(y) | np.isnan(X).any(axis=1))
    y, X = y[mask], X[mask]
    if len(y) < max(10, X.shape[1] + 5) or np.std(y) == 0:
        return math.nan
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    if ss_tot == 0:
        return math.nan
    return 1.0 - ss_res / ss_tot


def incremental_r2(target_diff: np.ndarray, own_lag_diff: np.ndarray, other_lag_diff: np.ndarray) -> float:
    """R^2(target_t ~ own_{t-1}, other_{t-1}) minus R^2(target_t ~ own_{t-1}).
    A positive value means "other"'s one-step-lagged value adds
    predictive power for "target" beyond target's own persistence — a
    directional (not causal) signal only."""
    n = len(target_diff)
    ones = np.ones(n)
    base_X = np.column_stack([ones, own_lag_diff])
    full_X = np.column_stack([ones, own_lag_diff, other_lag_diff])
    r2_base = _ols_r2(target_diff, base_X)
    r2_full = _ols_r2(target_diff, full_X)
    if math.isnan(r2_base) or math.isnan(r2_full):
        return math.nan
    return r2_full - r2_base


def _run_one(spec: RunSpec, region_params: dict, max_lag: int) -> dict:
    start = time.time()
    record = {"region": spec.region, "seed": spec.seed, "status": "failed", "error": None}
    try:
        config = _build_config(spec, region_params)
        result = Simulation(config).run()
        rows = result.metrics

        occupancy = np.array([r["environment_fraction_of_capacity"] for r in rows], dtype=float)
        b_t = np.array([step_balance_indicators(r)["b_t_realized"] for r in rows], dtype=float)
        coop_cond = np.array([r["cooperation_rate_conditional_on_interaction"] for r in rows], dtype=float)
        coop_uncond = np.array([r["p_cooperate_and_interaction_given_opportunity"] for r in rows], dtype=float)

        record["status"] = "ok"
        for eco_name, eco_series in (("occupancy", occupancy), ("b_t_realized", b_t)):
            for coop_name, coop_series in (("coop_conditional", coop_cond), ("coop_unconditional", coop_uncond)):
                prefix = f"{coop_name}_vs_{eco_name}"

                level_corrs = lag_correlations(coop_series, eco_series, max_lag)
                lag_l, corr_l = best_lag(level_corrs)
                record[f"{prefix}_level_best_lag"] = lag_l
                record[f"{prefix}_level_best_corr"] = corr_l

                d_coop = np.diff(coop_series)
                d_eco = np.diff(eco_series)
                diff_corrs = lag_correlations(d_coop, d_eco, max_lag)
                lag_d, corr_d = best_lag(diff_corrs)
                record[f"{prefix}_diff_best_lag"] = lag_d
                record[f"{prefix}_diff_best_corr"] = corr_d

                coop_own_lag = d_coop[:-1]
                coop_target = d_coop[1:]
                eco_own_lag = d_eco[:-1]
                eco_target = d_eco[1:]
                eco_other_lag = d_eco[:-1]
                coop_other_lag = d_coop[:-1]
                record[f"{prefix}_incR2_coop_predicts_eco"] = incremental_r2(eco_target, eco_own_lag, coop_other_lag)
                record[f"{prefix}_incR2_eco_predicts_coop"] = incremental_r2(coop_target, coop_own_lag, eco_other_lag)
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    record["wall_time_s"] = time.time() - start
    return record


def run_time_lagged(
    regions: dict[str, dict], n_seeds: int, n_steps: int, population_size: int, max_lag: int = MAX_LAG_DEFAULT,
) -> list[dict]:
    records = []
    for region_name, params in regions.items():
        for seed in range(n_seeds):
            spec = RunSpec(region=region_name, seed=seed, n_steps=n_steps, population_size=population_size)
            records.append(_run_one(spec, params, max_lag))
    return records


_AGGREGATE_METRIC_PREFIXES = [
    f"{coop}_vs_{eco}"
    for coop in ("coop_conditional", "coop_unconditional")
    for eco in ("occupancy", "b_t_realized")
]


def _nanmean_safe(values: np.ndarray) -> float:
    """np.nanmean, but returns NaN (not a RuntimeWarning) for an
    all-NaN input — e.g. every seed's correlation was undefined because
    a window was degenerate."""
    valid = values[~np.isnan(values)]
    return float(np.mean(valid)) if len(valid) else math.nan


def _nanstd_safe(values: np.ndarray) -> float:
    valid = values[~np.isnan(values)]
    return float(np.std(valid)) if len(valid) else math.nan


def aggregate_time_lagged(records: list[dict]) -> pd.DataFrame:
    ok = [r for r in records if r["status"] == "ok"]
    df = pd.DataFrame(ok)
    if df.empty:
        return df
    agg_rows = []
    for region, group in df.groupby("region"):
        row = {"region": region, "n_seeds": len(group)}
        for prefix in _AGGREGATE_METRIC_PREFIXES:
            for suffix in (
                "level_best_corr", "diff_best_corr",
                "incR2_coop_predicts_eco", "incR2_eco_predicts_coop",
            ):
                col = f"{prefix}_{suffix}"
                if col in group:
                    values = group[col].to_numpy(dtype=float)
                    row[f"{col}_mean"] = _nanmean_safe(values)
                    row[f"{col}_std"] = _nanstd_safe(values)
        agg_rows.append(row)
    return pd.DataFrame(agg_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sweep-dir", default="outputs/phase_sweep_level02")
    parser.add_argument("--out-dir", default="outputs/cooperation_ecology_causality_level02")
    parser.add_argument("--n-seeds", type=int, default=N_SEEDS_DEFAULT)
    parser.add_argument("--n-steps", type=int, default=N_STEPS_DEFAULT)
    parser.add_argument("--population-size", type=int, default=POPULATION_SIZE_DEFAULT)
    parser.add_argument("--max-lag", type=int, default=MAX_LAG_DEFAULT)
    parser.add_argument("--min-seeds-cross-sectional", type=int, default=MIN_SEEDS_FOR_CROSS_SECTIONAL)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    runs = load_manifest_runs(args.sweep_dir)
    cross_sectional = cross_sectional_by_point(runs, min_seeds=args.min_seeds_cross_sectional)
    pooled = pooled_confounded_correlation(runs)
    cross_sectional.to_csv(os.path.join(args.out_dir, "cross_sectional_by_point.csv"), index=False)
    with open(os.path.join(args.out_dir, "pooled_confounded_correlation.json"), "w", encoding="utf-8") as fh:
        json.dump(pooled, fh, indent=2)
    print(f"Part 1: {len(cross_sectional)} points with >= {args.min_seeds_cross_sectional} seeds "
          f"(of {len(set((r['stage'], r['point_id']) for r in runs))} total points)")

    regions = _load_regions(args.sweep_dir)
    records = run_time_lagged(regions, args.n_seeds, args.n_steps, args.population_size, args.max_lag)
    n_ok = sum(1 for r in records if r["status"] == "ok")
    print(f"Part 2: {n_ok}/{len(records)} runs ok")
    with open(os.path.join(args.out_dir, "time_lagged_records.json"), "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2)
    time_lagged_summary = aggregate_time_lagged(records)
    time_lagged_summary.to_csv(os.path.join(args.out_dir, "time_lagged_summary.csv"), index=False)

    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
