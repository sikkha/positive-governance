"""Work Package G: smoke test for the single required minimal perturbation
experiment script (experiments/perturbation_experiment.py). Runs with
drastically reduced seeds/steps (via monkeypatched module constants) so
this stays fast — the full-scale run used for the final report is executed
separately and its output lives under outputs/perturbation_experiment/.
"""

from __future__ import annotations

import importlib.util
import os
import sys

_PATH = os.path.join(os.path.dirname(__file__), "..", "experiments", "perturbation_experiment.py")
_spec = importlib.util.spec_from_file_location("perturbation_experiment", _PATH)
pe = importlib.util.module_from_spec(_spec)
sys.modules["perturbation_experiment"] = pe
_spec.loader.exec_module(pe)


def test_perturbation_experiment_end_to_end_smoke(tmp_path, monkeypatch):
    monkeypatch.setattr(pe, "SEEDS", [0, 1])
    monkeypatch.setattr(pe, "N_STEPS", 20)
    monkeypatch.setattr(pe, "SHOCK_START", 10)
    monkeypatch.setattr(pe, "SHOCK_DURATION", 1)

    summary = pe.run(str(tmp_path / "pe"))

    assert summary["shock_spec"]["start_step"] == 10
    assert summary["n_seeds"] == 2
    # The shocked arm's pool at the shock step must be lower than baseline's.
    assert summary["response_at_shock_step"]["shocked"] < summary["response_at_shock_step"]["baseline"]
    assert os.path.exists(os.path.join(tmp_path, "pe", "perturbation_trajectories.csv"))
    assert os.path.exists(os.path.join(tmp_path, "pe", "perturbation_summary.json"))


def test_perturbation_experiment_baseline_and_shocked_agree_before_the_shock(tmp_path, monkeypatch):
    monkeypatch.setattr(pe, "SEEDS", [0])
    monkeypatch.setattr(pe, "N_STEPS", 15)
    monkeypatch.setattr(pe, "SHOCK_START", 8)
    monkeypatch.setattr(pe, "SHOCK_DURATION", 1)

    summary = pe.run(str(tmp_path / "pe2"))
    pre = summary["pre_shock_state"]
    assert pre["baseline"]["environment_resources_mean"] == pre["shocked"]["environment_resources_mean"]
