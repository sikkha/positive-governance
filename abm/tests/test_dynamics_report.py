"""Work Package F: smoke test that dynamics_report.py's diagnostics
functions run cleanly (no warnings, sane output) against a small synthetic
run, independent of the full ensemble output."""

from __future__ import annotations

import importlib.util
import math
import os
import sys

import numpy as np

_PATH = os.path.join(os.path.dirname(__file__), "..", "experiments", "dynamics_report.py")
_spec = importlib.util.spec_from_file_location("dynamics_report", _PATH)
dr = importlib.util.module_from_spec(_spec)
sys.modules["dynamics_report"] = dr
_spec.loader.exec_module(dr)


def test_diagnostics_for_series_handles_ordinary_series():
    series = np.sin(np.linspace(0, 20, 200)) + np.random.default_rng(0).normal(0, 0.1, 200)
    result = dr.diagnostics_for_series(series)
    assert result is not None
    assert result["n"] == 200
    assert "stationarity_heuristic" in result
    assert isinstance(result["change_point_candidates"], list)


def test_diagnostics_for_series_returns_none_for_all_nan():
    series = np.full(50, math.nan)
    assert dr.diagnostics_for_series(series) is None


def test_diagnostics_for_series_returns_none_for_empty():
    assert dr.diagnostics_for_series(np.array([])) is None


def test_run_end_to_end_against_a_tiny_fake_ensemble_dir(tmp_path):
    import pandas as pd
    import json

    ensemble_dir = tmp_path / "ens"
    for condition in dr.CONDITIONS:
        run_dir = ensemble_dir / "runs" / condition / "seed_0000"
        run_dir.mkdir(parents=True)
        n = 40
        df = pd.DataFrame(
            {
                "step": range(n),
                "cooperation_rate": np.random.default_rng(1).uniform(0, 1, n),
                "environment_resources": np.random.default_rng(2).uniform(0, 100, n),
                "mean_resources": np.random.default_rng(3).uniform(-10, 10, n),
            }
        )
        df.to_csv(run_dir / "metrics.csv", index=False)

    manifest = {
        "runs": [
            {
                "status": "ok",
                "condition": condition,
                "final_metrics": {"cooperation_rate": 0.5, "environment_resources": 10.0, "mean_resources": 1.0},
            }
            for condition in dr.CONDITIONS
        ]
    }
    (ensemble_dir).mkdir(exist_ok=True)
    with open(ensemble_dir / "manifest.json", "w") as fh:
        json.dump(manifest, fh)

    report = dr.run(str(ensemble_dir))
    assert set(report["per_condition_single_seed"]) == set(dr.CONDITIONS)
    assert os.path.exists(ensemble_dir / "dynamics_diagnostics.json")
    assert "disclaimer" in report
