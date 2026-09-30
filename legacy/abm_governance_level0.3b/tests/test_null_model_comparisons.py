"""Level 0.2, Work Package H: the null-model/factorial-comparison runner
(experiments/null_model_comparisons.py)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys

import pandas as pd
import pytest

_PATH = os.path.join(os.path.dirname(__file__), "..", "experiments", "null_model_comparisons.py")
_spec = importlib.util.spec_from_file_location("null_model_comparisons", _PATH)
nmc = importlib.util.module_from_spec(_spec)
sys.modules["null_model_comparisons"] = nmc
_spec.loader.exec_module(nmc)


def _fake_sweep_dir(tmp_path):
    sweep_dir = tmp_path / "sweep"
    sweep_dir.mkdir()
    stage1 = pd.DataFrame(
        [
            {
                "point_id": "s1_abundant", "mean_occupancy_mean": 0.95,
                "environment_regen_rate": 1.0, "environment_capacity": 2000.0, "subsistence_cost": 0.1,
                "payoff_temptation": 6.0, "payoff_reward": 3.0, "distress_threshold": 2.0,
            },
            {
                "point_id": "s1_depleted", "mean_occupancy_mean": 0.0,
                "environment_regen_rate": 0.1, "environment_capacity": 200.0, "subsistence_cost": 1.0,
                "payoff_temptation": 4.0, "payoff_reward": 2.5, "distress_threshold": -3.0,
            },
        ]
    )
    stage1.to_csv(sweep_dir / "stage1_summary.csv", index=False)
    manifest = {
        "boundary_points_selected": [
            {
                "point_id": "s1_boundary",
                "params": {
                    "environment_regen_rate": 0.6, "environment_capacity": 1000.0, "subsistence_cost": 0.5,
                    "payoff_temptation": 4.5, "payoff_reward": 3.0, "distress_threshold": -1.0,
                },
            }
        ]
    }
    with open(sweep_dir / "sweep_manifest.json", "w") as fh:
        json.dump(manifest, fh)
    return str(sweep_dir)


def test_load_regions_reads_abundant_depleted_boundary(tmp_path):
    sweep_dir = _fake_sweep_dir(tmp_path)
    regions = nmc._load_regions(sweep_dir)
    assert set(regions) == {"abundant", "depleted", "boundary"}
    assert regions["abundant"]["environment_capacity"] == pytest.approx(2000.0)
    assert regions["depleted"]["environment_capacity"] == pytest.approx(200.0)
    assert regions["boundary"]["environment_capacity"] == pytest.approx(1000.0)


def test_load_regions_raises_without_boundary_points(tmp_path):
    sweep_dir = tmp_path / "sweep_empty"
    sweep_dir.mkdir()
    pd.DataFrame([{"point_id": "x", "mean_occupancy_mean": 0.5, "environment_regen_rate": 0.5,
                    "environment_capacity": 500.0, "subsistence_cost": 0.5, "payoff_temptation": 4.0,
                    "payoff_reward": 2.0, "distress_threshold": 0.0}]).to_csv(sweep_dir / "stage1_summary.csv", index=False)
    with open(sweep_dir / "sweep_manifest.json", "w") as fh:
        json.dump({"boundary_points_selected": []}, fh)
    with pytest.raises(RuntimeError):
        nmc._load_regions(str(sweep_dir))


def test_build_slices_covers_all_four_required_comparisons(tmp_path):
    regions = nmc._load_regions(_fake_sweep_dir(tmp_path))
    specs = nmc.build_slices(regions, seeds=2)
    slice_names = {s.slice_name for s in specs}
    assert slice_names == {
        "viability_mode_x_fitness_mode",
        "region_x_fitness_mode",
        "region_x_punishment",
        "region_x_relationship_turnover",
    }
    # viability_mode x fitness_mode is only run at the boundary region.
    vm_specs = [s for s in specs if s.slice_name == "viability_mode_x_fitness_mode"]
    assert {s.region for s in vm_specs} == {"boundary"}
    assert len(vm_specs) == len(nmc.VIABILITY_MODES) * len(nmc.FITNESS_MODES) * 2  # 2 seeds
    # region x fitness_mode spans all three regions.
    rf_specs = [s for s in specs if s.slice_name == "region_x_fitness_mode"]
    assert {s.region for s in rf_specs} == {"abundant", "depleted", "boundary"}


def test_end_to_end_tiny_run_produces_nonempty_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(nmc, "N_STEPS", 12)
    monkeypatch.setattr(nmc, "POPULATION_SIZE", 8)
    regions = nmc._load_regions(_fake_sweep_dir(tmp_path))
    specs = nmc.build_slices(regions, seeds=1)
    # Trim to keep the test fast: one representative spec per slice/region.
    trimmed = []
    seen = set()
    for s in specs:
        key = (s.slice_name, s.region)
        if key not in seen:
            seen.add(key)
            trimmed.append(s)
    records = nmc.run_specs(trimmed, regions, max_workers=1)
    assert all(r["status"] == "ok" for r in records), [r["error"] for r in records if r["status"] != "ok"]
    df = nmc.aggregate(records)
    assert len(df) == len(trimmed)
    assert "conditional_cooperation_rate_mean" in df.columns
