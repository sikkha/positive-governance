"""Level 0.2, Work Package E: the phase-sweep runner
(experiments/phase_sweep.py) — LHS sampling determinism, resume
correctness (including the stage-namespacing fix for overlapping
(point_id, seed) keys across stages), serial/parallel equivalence, and
ecology-only boundary-point selection."""

from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np
import pytest

_PHASE_SWEEP_PATH = os.path.join(os.path.dirname(__file__), "..", "experiments", "phase_sweep.py")
_spec = importlib.util.spec_from_file_location("phase_sweep", _PHASE_SWEEP_PATH)
phase_sweep = importlib.util.module_from_spec(_spec)
sys.modules["phase_sweep"] = phase_sweep
_spec.loader.exec_module(phase_sweep)


def test_lhs_sampling_is_reproducible_given_same_seed():
    a = phase_sweep._sample_lhs_points(10, rng_seed=42)
    b = phase_sweep._sample_lhs_points(10, rng_seed=42)
    assert a == b


def test_lhs_sampling_respects_param_ranges_and_payoff_ordering():
    points = phase_sweep._sample_lhs_points(50, rng_seed=1)
    for p in points:
        for name, (lo, hi) in phase_sweep.PARAM_RANGES.items():
            if name == "payoff_reward":
                continue  # reward is clipped after sampling; range check below instead
            assert lo <= p[name] <= hi
        assert p["payoff_reward"] < p["payoff_temptation"]
        assert p["payoff_reward"] > 1.0  # > payoff_punishment


def test_different_seeds_give_different_designs():
    a = phase_sweep._sample_lhs_points(10, rng_seed=1)
    b = phase_sweep._sample_lhs_points(10, rng_seed=2)
    assert a != b


def _tiny_specs(out_dir, stage="stage1", n_points=2, n_seeds=2):
    points = phase_sweep._sample_lhs_points(n_points, rng_seed=7)
    specs = []
    for i, params in enumerate(points):
        for seed in range(n_seeds):
            specs.append(
                phase_sweep.SweepPointSpec(
                    point_id=f"{stage}_{i:03d}",
                    stage=stage,
                    params=params,
                    seed=seed,
                    n_steps=15,
                    population_size=10,
                    out_dir=os.path.join(out_dir, stage, f"{i:03d}", f"seed_{seed}"),
                )
            )
    return specs


def test_run_specs_serial_and_parallel_agree(tmp_path):
    specs = _tiny_specs(str(tmp_path / "a"))
    serial = phase_sweep.run_specs(specs, str(tmp_path / "a"), max_workers=1, resume=False)
    specs2 = _tiny_specs(str(tmp_path / "b"))
    parallel = phase_sweep.run_specs(specs2, str(tmp_path / "b"), max_workers=2, resume=False)

    def _key(r):
        return (r["point_id"], r["seed"])

    serial_by_key = {_key(r): r for r in serial}
    parallel_by_key = {_key(r): r for r in parallel}
    assert set(serial_by_key) == set(parallel_by_key)
    for key in serial_by_key:
        s, p = serial_by_key[key], parallel_by_key[key]
        assert s["status"] == p["status"] == "ok"
        assert s["final_cooperation_rate"] == pytest.approx(p["final_cooperation_rate"], nan_ok=True)
        assert s["balance_summary"]["mean_occupancy"] == pytest.approx(
            p["balance_summary"]["mean_occupancy"], nan_ok=True
        )


def test_resume_skips_completed_runs_and_produces_identical_results(tmp_path):
    out_root = str(tmp_path / "resume_test")
    specs = _tiny_specs(out_root)
    first = phase_sweep.run_specs(specs, out_root, max_workers=1, resume=True)
    # No manifest written yet by run_specs itself (that's main()'s job) —
    # write one manually to exercise the resume path in isolation.
    import json

    manifest = {"runs": first}
    os.makedirs(out_root, exist_ok=True)
    with open(os.path.join(out_root, "sweep_manifest.json"), "w") as fh:
        json.dump(manifest, fh, default=str)

    second = phase_sweep.run_specs(specs, out_root, max_workers=1, resume=True)
    assert len(second) == len(first)
    first_by_key = {(r["point_id"], r["seed"]): r for r in first}
    second_by_key = {(r["point_id"], r["seed"]): r for r in second}
    for key in first_by_key:
        assert first_by_key[key]["final_cooperation_rate"] == pytest.approx(
            second_by_key[key]["final_cooperation_rate"], nan_ok=True
        )


def test_resume_does_not_leak_records_across_disjoint_stages(tmp_path):
    """Regression test for the stage-leakage bug found during development:
    calling run_specs with an empty/disjoint spec list must not return
    unrelated records left over from a previous call against the same
    out_root."""
    out_root = str(tmp_path / "leak_test")
    stage1_specs = _tiny_specs(out_root, stage="stage1")
    stage1_records = phase_sweep.run_specs(stage1_specs, out_root, max_workers=1, resume=False)

    import json

    os.makedirs(out_root, exist_ok=True)
    with open(os.path.join(out_root, "sweep_manifest.json"), "w") as fh:
        json.dump({"runs": stage1_records}, fh, default=str)

    # A completely disjoint (different point_id namespace) stage-2 spec
    # list, resumed against the same out_root that already has stage-1
    # results: must return exactly its own (empty request -> empty
    # result), never the stage-1 records.
    empty_result = phase_sweep.run_specs([], out_root, max_workers=1, resume=True)
    assert empty_result == []


def test_select_boundary_points_uses_only_ecological_columns():
    """Two synthetic points with identical (extreme) ecological summaries
    but very different cooperation rates must be selected/rejected
    identically — proving cooperation_rate plays no role in selection."""
    def _record(point_id, mean_occ, frac_depleted_values, cooperation_rate):
        return [
            {
                "point_id": point_id,
                "status": "ok",
                "params": {"environment_regen_rate": 0.5},
                "balance_summary": {"mean_occupancy": mean_occ, "fraction_time_depleted": f},
                "final_cooperation_rate": cooperation_rate,
            }
            for f in frac_depleted_values
        ]

    boundary_like = _record("boundary_point", 0.5, [0.3, 0.5, 0.7, 0.2], cooperation_rate=0.05)
    boundary_like_high_coop = _record("boundary_point_high_coop", 0.5, [0.3, 0.5, 0.7, 0.2], cooperation_rate=0.99)
    extreme = _record("collapsed_point", 0.0, [1.0, 1.0, 1.0, 1.0], cooperation_rate=1.0)

    candidates = phase_sweep.select_boundary_points(
        boundary_like + boundary_like_high_coop + extreme, max_boundary_points=5
    )
    selected_ids = {c["point_id"] for c in candidates}
    assert "boundary_point" in selected_ids
    assert "boundary_point_high_coop" in selected_ids  # selected despite very different cooperation
    assert "collapsed_point" not in selected_ids  # permanently depleted: not interior
