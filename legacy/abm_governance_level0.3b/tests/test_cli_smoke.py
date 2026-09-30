"""End-to-end CLI smoke test: a short seeded run must produce the expected
output files and be exactly reproducible when re-run with the same seed."""

from __future__ import annotations

import filecmp
import json
import os

from abm_governance.cli import main


def test_cli_run_produces_expected_files(tmp_path):
    out_dir = tmp_path / "run0"
    rc = main(["run", "--seed", "0", "--steps", "15", "--out", str(out_dir)])
    assert rc == 0
    for fname in ("metrics.csv", "metrics.json", "final_state.json", "config.yaml", "timeseries.png"):
        assert (out_dir / fname).exists(), fname


def test_cli_run_is_bit_for_bit_reproducible(tmp_path):
    out_a = tmp_path / "run_a"
    out_b = tmp_path / "run_b"
    main(["run", "--seed", "42", "--steps", "20", "--out", str(out_a), "--no-plot"])
    main(["run", "--seed", "42", "--steps", "20", "--out", str(out_b), "--no-plot"])

    assert filecmp.cmp(out_a / "metrics.csv", out_b / "metrics.csv", shallow=False)

    with open(out_a / "final_state.json") as fh:
        state_a = json.load(fh)
    with open(out_b / "final_state.json") as fh:
        state_b = json.load(fh)
    assert state_a == state_b


def test_cli_seed_and_steps_override_config_file(tmp_path):
    from abm_governance.core.config import SimulationConfig

    config_path = tmp_path / "cfg.yaml"
    SimulationConfig(population_size=15, n_steps=100, seed=1).to_yaml(str(config_path))

    out_dir = tmp_path / "run_override"
    rc = main([
        "run",
        "--config",
        str(config_path),
        "--seed",
        "99",
        "--steps",
        "5",
        "--out",
        str(out_dir),
        "--no-plot",
    ])
    assert rc == 0

    with open(out_dir / "metrics.json") as fh:
        metrics = json.load(fh)
    assert len(metrics) == 5  # --steps override honored

    with open(out_dir / "config.yaml") as fh:
        import yaml

        written_config = yaml.safe_load(fh)
    assert written_config["seed"] == 99
    assert written_config["n_steps"] == 5
    assert written_config["population_size"] == 15  # untouched by overrides
