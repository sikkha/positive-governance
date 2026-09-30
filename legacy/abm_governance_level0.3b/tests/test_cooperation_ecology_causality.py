"""Level 0.2, Work Package F: cooperation-and-ecology causality reporting
(experiments/cooperation_ecology_causality.py).

Hand-computed micro-scenarios for the statistical helpers (lag
correlation, incremental R^2), plus tests of the two manifest-driven
cross-sectional aggregations against small synthetic manifests, and a
tiny end-to-end smoke test of the fresh-run (Part 2) path."""

from __future__ import annotations

import importlib.util
import json
import math
import os
import sys

import numpy as np
import pandas as pd
import pytest

_PATH = os.path.join(os.path.dirname(__file__), "..", "experiments", "cooperation_ecology_causality.py")
_spec = importlib.util.spec_from_file_location("cooperation_ecology_causality", _PATH)
cec = importlib.util.module_from_spec(_spec)
sys.modules["cooperation_ecology_causality"] = cec
_spec.loader.exec_module(cec)


# ---------------------------------------------------------------------------
# Hand-computed: lag_correlations / best_lag
# ---------------------------------------------------------------------------

def test_lag_correlations_hand_computed_zero_lag_identical_series():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0])
    corrs = cec.lag_correlations(x, x, max_lag=2)
    assert corrs[0] == pytest.approx(1.0)


def test_lag_correlations_detects_known_lead(monkeypatch):
    # y[t] = x[t-3]: x leads y by exactly 3 steps. Best |corr| should be
    # at lag=+3 (x[t] best matches y[t+3]), and the correlation there
    # should be ~1 (noise-free construction).
    n = 60
    rng = np.random.default_rng(0)
    x = rng.normal(size=n)
    y = np.empty(n)
    y[:3] = rng.normal(size=3)
    y[3:] = x[:-3]
    corrs = cec.lag_correlations(x, y, max_lag=6)
    lag, corr = cec.best_lag(corrs)
    assert lag == pytest.approx(3.0)
    assert corr == pytest.approx(1.0, abs=1e-9)


def test_best_lag_all_nan_returns_nan():
    corrs = {lag: math.nan for lag in range(-3, 4)}
    lag, corr = cec.best_lag(corrs)
    assert math.isnan(lag)
    assert math.isnan(corr)


def test_lag_correlations_short_window_is_nan():
    x = np.array([1.0, 2.0, 3.0])
    y = np.array([1.0, 2.0, 3.0])
    corrs = cec.lag_correlations(x, y, max_lag=1)
    assert all(math.isnan(v) for v in corrs.values())


# ---------------------------------------------------------------------------
# Hand-computed: incremental_r2
# ---------------------------------------------------------------------------

def test_incremental_r2_hand_computed_other_fully_explains_residual():
    # target_t = own_{t-1} + other_{t-1} exactly (noise-free). Regressing
    # on own_lag alone should leave residual variance that other_lag
    # explains completely, so incremental R^2 should be close to
    # (1 - R2_base), and R2_full should be ~1.
    rng = np.random.default_rng(1)
    n = 200
    own_lag = rng.normal(size=n)
    other_lag = rng.normal(size=n)
    target = own_lag + other_lag
    inc = cec.incremental_r2(target, own_lag, other_lag)
    assert inc > 0.4  # other_lag must be adding substantial explanatory power
    r2_base = cec._ols_r2(target, np.column_stack([np.ones(n), own_lag]))
    r2_full = cec._ols_r2(target, np.column_stack([np.ones(n), own_lag, other_lag]))
    assert r2_full == pytest.approx(1.0, abs=1e-6)
    assert inc == pytest.approx(r2_full - r2_base, abs=1e-9)


def test_incremental_r2_independent_other_adds_near_zero():
    rng = np.random.default_rng(2)
    n = 300
    own_lag = rng.normal(size=n)
    target = own_lag * 2.0 + rng.normal(scale=0.01, size=n)  # target ~ own_lag only
    other_lag = rng.normal(size=n)  # independent noise, unrelated to target
    inc = cec.incremental_r2(target, own_lag, other_lag)
    assert abs(inc) < 0.05


def test_ols_r2_perfect_fit_is_one():
    n = 50
    x = np.linspace(0, 1, n)
    y = 2.0 * x + 1.0
    X = np.column_stack([np.ones(n), x])
    assert cec._ols_r2(y, X) == pytest.approx(1.0, abs=1e-10)


def test_ols_r2_too_few_points_is_nan():
    y = np.array([1.0, 2.0])
    X = np.column_stack([np.ones(2), np.array([1.0, 2.0])])
    assert math.isnan(cec._ols_r2(y, X))


# ---------------------------------------------------------------------------
# Hand-computed: _pearson / _spearman
# ---------------------------------------------------------------------------

def test_pearson_hand_computed_perfect_negative_correlation():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    y = np.array([4.0, 3.0, 2.0, 1.0])
    assert cec._pearson(x, y) == pytest.approx(-1.0)


def test_pearson_ignores_nan_pairs():
    x = np.array([1.0, 2.0, math.nan, 4.0, 5.0])
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert cec._pearson(x, y) == pytest.approx(1.0)


def test_spearman_monotonic_nonlinear_is_one():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = x ** 3  # monotonic but nonlinear: Pearson < 1, Spearman == 1
    assert cec._spearman(x, y) == pytest.approx(1.0)
    assert cec._pearson(x, y) < 1.0


# ---------------------------------------------------------------------------
# Part 1: manifest-driven cross-sectional aggregation, synthetic manifest.
# ---------------------------------------------------------------------------

def _fake_run(point_id, stage, seed, coop, occupancy, collapse_eps=0, longest_collapse=0, peak_pf=0.0, depleted_frac=0.0):
    return {
        "stage": stage, "point_id": point_id, "seed": seed, "status": "ok",
        "final_cooperation_rate": coop,
        "balance_summary": {"mean_occupancy": occupancy, "fraction_time_depleted": depleted_frac},
        "n_collapse_episodes": collapse_eps,
        "longest_collapse_duration": longest_collapse,
        "population_failure": {"peak_fraction": peak_pf},
    }


def test_cross_sectional_by_point_hand_computed_perfect_correlation():
    # 10 seeds at one point: cooperation and occupancy constructed as a
    # perfectly increasing pair -> expect within-point Pearson == 1.
    runs = [_fake_run("p1", "stage2", s, coop=float(s), occupancy=float(s) * 2.0) for s in range(10)]
    df = cec.cross_sectional_by_point(runs, min_seeds=10)
    assert len(df) == 1
    assert df.iloc[0]["pearson_coop_vs_mean_occupancy"] == pytest.approx(1.0)
    assert df.iloc[0]["spearman_coop_vs_mean_occupancy"] == pytest.approx(1.0)


def test_cross_sectional_by_point_excludes_low_seed_points():
    runs = [_fake_run("p1", "stage1", s, coop=float(s), occupancy=float(s)) for s in range(3)]
    df = cec.cross_sectional_by_point(runs, min_seeds=10)
    assert df.empty


def test_pooled_confounded_correlation_can_differ_in_sign_from_within_point():
    # Two points: point A has low params -> low coop, low occupancy.
    # Point B has high params -> high coop, high occupancy. Within each
    # point, cooperation is *negatively* associated with occupancy
    # (seed-level noise), but pooling across points, the between-point
    # variation dominates and flips the sign positive. This is exactly
    # the confound Part 1's docstring describes.
    runs = []
    for s in range(10):
        # Point A: coop increases 0..9 (small), occupancy decreases (negative within-point assoc)
        runs.append(_fake_run("A", "stage1", s, coop=0.10 + 0.001 * s, occupancy=0.20 - 0.001 * s))
    for s in range(10):
        # Point B: same negative within-point pattern, but shifted much higher overall
        runs.append(_fake_run("B", "stage1", s, coop=0.80 + 0.001 * s, occupancy=0.90 - 0.001 * s))
    within = cec.cross_sectional_by_point(runs, min_seeds=10)
    assert (within["pearson_coop_vs_mean_occupancy"] < 0).all()
    pooled = cec.pooled_confounded_correlation(runs)
    assert pooled["pooled_pearson_coop_vs_mean_occupancy"] > 0


def test_load_manifest_runs_filters_failed(tmp_path):
    sweep_dir = tmp_path / "sweep"
    sweep_dir.mkdir()
    manifest = {"runs": [
        _fake_run("p1", "stage1", 0, coop=0.5, occupancy=0.5),
        {"status": "failed", "point_id": "p2", "stage": "stage1", "seed": 1},
    ]}
    with open(sweep_dir / "sweep_manifest.json", "w") as fh:
        json.dump(manifest, fh)
    runs = cec.load_manifest_runs(str(sweep_dir))
    assert len(runs) == 1
    assert runs[0]["point_id"] == "p1"


# ---------------------------------------------------------------------------
# Part 2: fresh-run pipeline, tiny end-to-end smoke test.
# ---------------------------------------------------------------------------

def _fake_sweep_dir(tmp_path):
    sweep_dir = tmp_path / "sweep"
    sweep_dir.mkdir()
    stage1 = pd.DataFrame(
        [
            {"point_id": "s1_abundant", "mean_occupancy_mean": 0.95, "environment_regen_rate": 1.0,
             "environment_capacity": 500.0, "subsistence_cost": 0.1, "payoff_temptation": 6.0,
             "payoff_reward": 3.0, "distress_threshold": 2.0},
            {"point_id": "s1_depleted", "mean_occupancy_mean": 0.0, "environment_regen_rate": 0.05,
             "environment_capacity": 100.0, "subsistence_cost": 1.0, "payoff_temptation": 4.0,
             "payoff_reward": 2.5, "distress_threshold": -3.0},
        ]
    )
    stage1.to_csv(sweep_dir / "stage1_summary.csv", index=False)
    manifest = {"boundary_points_selected": [{"point_id": "s1_boundary", "params": {
        "environment_regen_rate": 0.3, "environment_capacity": 250.0, "subsistence_cost": 0.4,
        "payoff_temptation": 4.5, "payoff_reward": 3.0, "distress_threshold": -1.0,
    }}]}
    with open(sweep_dir / "sweep_manifest.json", "w") as fh:
        json.dump(manifest, fh)
    return str(sweep_dir)


def test_load_regions_reads_three_regions(tmp_path):
    regions = cec._load_regions(_fake_sweep_dir(tmp_path))
    assert set(regions) == {"abundant", "depleted", "boundary"}


def test_run_time_lagged_tiny_end_to_end_produces_ok_records(tmp_path):
    regions = cec._load_regions(_fake_sweep_dir(tmp_path))
    records = cec.run_time_lagged(regions, n_seeds=1, n_steps=30, population_size=8, max_lag=3)
    assert len(records) == 3  # one seed per region
    for r in records:
        assert r["status"] == "ok", r.get("error")
        assert "coop_conditional_vs_occupancy_level_best_lag" in r


def test_aggregate_time_lagged_produces_one_row_per_region(tmp_path):
    regions = cec._load_regions(_fake_sweep_dir(tmp_path))
    records = cec.run_time_lagged(regions, n_seeds=2, n_steps=30, population_size=8, max_lag=3)
    summary = cec.aggregate_time_lagged(records)
    assert set(summary["region"]) == {"abundant", "depleted", "boundary"}
    assert (summary["n_seeds"] == 2).all()


def test_aggregate_time_lagged_empty_on_all_failures():
    records = [{"status": "failed", "region": "x", "seed": 0, "error": "boom"}]
    summary = cec.aggregate_time_lagged(records)
    assert summary.empty
