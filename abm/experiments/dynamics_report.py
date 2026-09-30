#!/usr/bin/env python3
"""Work Package F: apply the dynamical diagnostics (observer/dynamics.py)
to the Work Package E baseline ensemble's actual output.

This script computes descriptive diagnostics only — rolling statistics,
autocorrelation, periodogram, a stationarity heuristic, change-point
candidates, regime time-fraction, and cross-seed endpoint dispersion — for
a representative column (``cooperation_rate`` and ``environment_resources``)
in each of the 3 baseline conditions, using one representative seed's full
trajectory plus the ensemble's cross-seed endpoint values. It does not
classify any trajectory as a fixed point, limit cycle, metastable regime,
collapse, or recovery; see observer/dynamics.py's module docstring for the
documented operational criteria this project requires before ever using
those words, none of which this script's output alone satisfies.

Usage:
    python experiments/dynamics_report.py --ensemble-dir outputs/ensemble_level01
"""

from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np
import pandas as pd

from abm_governance.observer.dynamics import (
    autocorrelation,
    change_point_candidates,
    detrended_autocorrelation,
    endpoint_dispersion,
    periodogram,
    regime_time_fraction,
    rolling_mean,
    rolling_variance,
    stationarity_heuristic,
)

CONDITIONS = ["original_compat", "ecologically_closed", "closed_ecology_turnover"]
COLUMNS = ["cooperation_rate", "environment_resources", "mean_resources"]
REPRESENTATIVE_SEED = 0


def _json_safe(value):
    if isinstance(value, (np.floating, np.integer)):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def diagnostics_for_series(series: np.ndarray) -> dict | None:
    if len(series) == 0 or np.all(np.isnan(series)):
        # e.g. environment_resources in compat mode, where there is no
        # pool at all (NaN by construction, not a degenerate dynamical
        # trajectory) — report that plainly instead of feeding an
        # all-NaN series through rolling/ACF machinery.
        return None
    n = len(series)
    window = max(5, n // 20)
    roll_mean = rolling_mean(series, window=window)
    roll_var = rolling_variance(series, window=window)
    max_lag = min(50, n // 4) if n >= 20 else 0
    acf = autocorrelation(series, max_lag=max_lag) if max_lag > 0 else np.array([])
    dacf = detrended_autocorrelation(series, max_lag=max_lag) if max_lag > 0 else np.array([])
    freqs, power = periodogram(series)
    dominant_freq = float(freqs[np.argmax(power)]) if len(power) else None
    stationarity = stationarity_heuristic(series, n_windows=min(10, max(2, n // 10)))
    change_points = change_point_candidates(series, window=window, z_threshold=3.0)
    regimes = regime_time_fraction(series, n_bins=5)
    return {
        "n": n,
        "rolling_window": window,
        "final_rolling_mean": _json_safe(roll_mean[-1]) if len(roll_mean) else None,
        "final_rolling_variance": _json_safe(roll_var[-1]) if len(roll_var) else None,
        "acf_lag1": _json_safe(acf[1]) if len(acf) > 1 else None,
        "acf_lag_max": _json_safe(acf[-1]) if len(acf) else None,
        "detrended_acf_lag1": _json_safe(dacf[1]) if len(dacf) > 1 else None,
        "periodogram_dominant_frequency": dominant_freq,
        "stationarity_heuristic": {k: _json_safe(v) for k, v in stationarity.items()},
        "change_point_candidate_count": len(change_points),
        "change_point_candidates": [int(c) for c in change_points[:20]],
        "regime_time_fraction": {
            "bin_edges": [float(x) for x in regimes["bin_edges"]],
            "fractions": [float(x) for x in regimes["fractions"]],
        },
    }


def run(ensemble_dir: str) -> dict:
    report: dict = {"per_condition_single_seed": {}, "endpoint_dispersion_across_seeds": {}}

    for condition in CONDITIONS:
        run_dir = os.path.join(ensemble_dir, "runs", condition, f"seed_{REPRESENTATIVE_SEED:04d}")
        csv_path = os.path.join(run_dir, "metrics.csv")
        if not os.path.exists(csv_path):
            continue
        df = pd.read_csv(csv_path)
        report["per_condition_single_seed"][condition] = {}
        for col in COLUMNS:
            if col not in df:
                continue
            series = df[col].to_numpy(dtype=float)
            diag = diagnostics_for_series(series)
            report["per_condition_single_seed"][condition][col] = (
                diag if diag is not None else {"note": "series is entirely NaN (no environment pool in this mode)"}
            )

    endpoint_csv = os.path.join(ensemble_dir, "endpoint_summary.csv")
    if os.path.exists(endpoint_csv):
        endpoint_df = pd.read_csv(endpoint_csv)
        for condition in CONDITIONS:
            report["endpoint_dispersion_across_seeds"][condition] = {}
            for col in COLUMNS:
                sub = endpoint_df[(endpoint_df.condition == condition) & (endpoint_df.column == col)]
                if sub.empty:
                    continue
                # endpoint_summary.csv already stores quantiles; recompute
                # endpoint_dispersion directly from the underlying per-seed
                # manifest values would be more precise, but the manifest's
                # final_metrics are also available — read those instead for
                # exactness.
        # Recompute directly from manifest.json (exact per-seed values).
    manifest_path = os.path.join(ensemble_dir, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path) as fh:
            manifest = json.load(fh)
        for condition in CONDITIONS:
            report["endpoint_dispersion_across_seeds"].setdefault(condition, {})
            for col in COLUMNS:
                values = np.array(
                    [
                        r["final_metrics"].get(col, math.nan)
                        for r in manifest["runs"]
                        if r["status"] == "ok" and r["condition"] == condition
                    ],
                    dtype=float,
                )
                disp = endpoint_dispersion(values)
                report["endpoint_dispersion_across_seeds"][condition][col] = {k: _json_safe(v) for k, v in disp.items()}

    report["disclaimer"] = (
        "These are descriptive diagnostics only (rolling statistics, "
        "autocorrelation, periodogram, a stationarity heuristic, "
        "change-point candidates, regime time-fraction, cross-seed endpoint "
        "dispersion). None of them, singly or combined, constitute a "
        "'fixed point' / 'limit cycle' / 'metastable regime' / 'collapse' / "
        "'recovery' classification — see observer/dynamics.py's module "
        "docstring for the operational criteria this project requires "
        "before that vocabulary is used, none of which one script run "
        "against one representative seed satisfies."
    )

    out_path = os.path.join(ensemble_dir, "dynamics_diagnostics.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(f"[dynamics_report] wrote {out_path}")
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    parser = argparse.ArgumentParser()
    parser.add_argument("--ensemble-dir", type=str, default="outputs/ensemble_level01")
    args = parser.parse_args()
    run(args.ensemble_dir)
