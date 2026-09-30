"""Work Package E: the ensemble/ablation runner (experiments/ensemble.py).

``experiments/`` is a scripts directory, not an installed package, so it is
imported here by file path rather than via a normal package import.
"""

from __future__ import annotations

import importlib.util
import os
import sys

import pandas as pd
import pytest

_ENSEMBLE_PATH = os.path.join(os.path.dirname(__file__), "..", "experiments", "ensemble.py")
_spec = importlib.util.spec_from_file_location("ensemble", _ENSEMBLE_PATH)
ensemble = importlib.util.module_from_spec(_spec)
# Register in sys.modules *before* exec: dataclasses' type-introspection
# looks the module up by name (cls.__module__), and ProcessPoolExecutor
# (used by run_ensemble with max_workers > 1) needs a stable importable
# module name to pickle/unpickle the top-level worker function by
# qualified name in child processes.
sys.modules["ensemble"] = ensemble
_spec.loader.exec_module(ensemble)


def test_build_run_grid_makes_one_spec_per_condition_and_seed():
    conditions = {"a": {"punishment_enabled": False}, "b": {"mutation_rate": 0.0}}
    specs = ensemble.build_run_grid(conditions, seeds=[0, 1, 2], n_steps=10, out_root="/tmp/x")
    assert len(specs) == 6
    assert {s.condition for s in specs} == {"a", "b"}
    assert sorted(s.seed for s in specs if s.condition == "a") == [0, 1, 2]
    # One run directory per (condition, seed).
    assert len({s.out_dir for s in specs}) == 6


def test_baseline_conditions_and_ablations_are_disjoint_and_well_formed():
    all_names = set(ensemble.BASELINE_CONDITIONS) | set(ensemble.ABLATIONS)
    assert len(all_names) == len(ensemble.BASELINE_CONDITIONS) + len(ensemble.ABLATIONS)
    assert len(ensemble.BASELINE_CONDITIONS) == 3
    assert len(ensemble.ABLATIONS) == 7
    # Every override dict must be constructible into a valid SimulationConfig.
    from abm_governance.core.config import SimulationConfig

    for overrides in {**ensemble.BASELINE_CONDITIONS, **ensemble.ABLATIONS}.values():
        SimulationConfig(seed=0, n_steps=5, **overrides)  # raises on invalid


def test_run_one_records_failure_without_raising(tmp_path):
    spec = ensemble.RunSpec(
        condition="broken", seed=0, overrides={"population_size": -5}, n_steps=5, out_dir=str(tmp_path / "r")
    )
    record = ensemble._run_one(spec)
    assert record["status"] == "failed"
    assert record["error"] is not None


def test_run_one_records_success(tmp_path):
    spec = ensemble.RunSpec(
        condition="ok", seed=0, overrides={"population_size": 12}, n_steps=8, out_dir=str(tmp_path / "r")
    )
    record = ensemble._run_one(spec)
    assert record["status"] == "ok"
    assert os.path.exists(os.path.join(spec.out_dir, "metrics.csv"))
    assert "cooperation_rate" in record["final_metrics"]


def test_serial_and_parallel_execution_agree(tmp_path):
    """Determinism under parallelism: the same (condition, seed) grid run
    with 1 worker vs. 2 workers must produce identical per-run endpoint
    metrics — only the arrival order of results may differ, and
    ``run_ensemble`` sorts before returning, so even that is normalized
    away."""
    conditions = {"x": {"punishment_enabled": True}, "y": {"punishment_enabled": False}}
    seeds = [0, 1, 2]

    specs_serial = ensemble.build_run_grid(conditions, seeds, n_steps=15, out_root=str(tmp_path / "serial"))
    records_serial = ensemble.run_ensemble(specs_serial, str(tmp_path / "serial"), max_workers=1)

    specs_parallel = ensemble.build_run_grid(conditions, seeds, n_steps=15, out_root=str(tmp_path / "parallel"))
    records_parallel = ensemble.run_ensemble(specs_parallel, str(tmp_path / "parallel"), max_workers=2)

    assert [r["status"] for r in records_serial] == ["ok"] * len(records_serial)
    assert [r["status"] for r in records_parallel] == ["ok"] * len(records_parallel)
    assert [(r["condition"], r["seed"]) for r in records_serial] == [
        (r["condition"], r["seed"]) for r in records_parallel
    ]
    for rs, rp in zip(records_serial, records_parallel):
        for col in ensemble.TRACKED_COLUMNS:
            a, b = rs["final_metrics"].get(col), rp["final_metrics"].get(col)
            if a != a and b != b:  # both NaN
                continue
            assert a == pytest.approx(b), f"{col} differs between serial and parallel for {rs['condition']}/{rs['seed']}"


def test_aggregate_endpoint_summary_quantiles_are_monotonic():
    records = [
        {
            "condition": "c",
            "status": "ok",
            "final_metrics": {"cooperation_rate": v, "mean_resources": 0, "resource_gini": 0,
                               "environment_resources": 0, "environment_fraction_of_capacity": 0,
                               "network_density": 0, "component_count": 0, "largest_component_share": 0,
                               "isolated_agent_count": 0, "mean_relationship_age": 0,
                               "policy_diversity_bits": 0, "erroneous_punishment_rate": 0},
        }
        for v in [0.1, 0.3, 0.5, 0.7, 0.9]
    ]
    df = ensemble.aggregate_endpoint_summary(records)
    row = df[(df["condition"] == "c") & (df["column"] == "cooperation_rate")].iloc[0]
    assert row["q00"] <= row["q25"] <= row["q50"] <= row["q75"] <= row["q100"]
    assert row["n_seeds"] == 5


def test_write_manifest_reports_failures_without_dropping_ok_runs(tmp_path):
    records = [
        {"condition": "a", "seed": 0, "status": "ok", "error": None},
        {"condition": "a", "seed": 1, "status": "failed", "error": "boom"},
    ]
    path = ensemble.write_manifest(records, str(tmp_path), meta={"note": "test"})
    assert os.path.exists(path)
    import json

    with open(path) as f:
        manifest = json.load(f)
    assert manifest["n_ok"] == 1
    assert manifest["n_failed"] == 1
    assert len(manifest["runs"]) == 2  # both kept


def test_full_small_ensemble_end_to_end(tmp_path):
    out_root = str(tmp_path / "ensemble")
    conditions = dict(ensemble.BASELINE_CONDITIONS)
    seeds = [0, 1]
    specs = ensemble.build_run_grid(conditions, seeds, n_steps=10, out_root=out_root)
    records = ensemble.run_ensemble(specs, out_root, max_workers=1)
    ensemble.write_manifest(records, out_root, meta={})
    paths = ensemble.aggregate(specs, records, out_root)
    assert all(os.path.exists(p) for p in paths.values())
    endpoint = pd.read_csv(paths["endpoint_summary"])
    assert set(endpoint["condition"]) == set(conditions)
