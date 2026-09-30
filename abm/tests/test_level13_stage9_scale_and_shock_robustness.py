"""Level 1.3, Stage 9 (task #104): scale and shock robustness
(``experiments/level13_stage9_scale_and_shock_robustness.py``) -- the
final experimental stage.

Runs the stage's own machinery at small scale (1 cell, 1 seed) to
confirm mechanics -- the actual 24-run, session-budget-scale run and
its ``outputs/level13_stage9_scale_and_shock_robustness/records.json``
record are produced by running the script directly."""

from __future__ import annotations

import importlib
import inspect

from experiments import level13_stage9_scale_and_shock_robustness as stage9
from tests.test_level12_structural_guards import _strip_docstrings_and_comments
from tests.test_level13_sem_firewall_extension import FORBIDDEN_LEVEL13_TERMS


class TestScaleConditions:
    def test_two_population_and_two_patches_conditions(self):
        assert stage9.POPULATION_CONDITIONS == (40, 80)
        assert stage9.N_PATCHES_CONDITIONS == (3, 6)

    def test_n_shocks_overridden_away_from_class_default(self):
        """Disclosed choice: n_shocks=4, not the PressureHistorySpec
        class default of 3."""
        from abm_governance.core.historical_pressure import PressureHistorySpec
        assert stage9.N_SHOCKS != PressureHistorySpec().n_shocks
        assert stage9.N_SHOCKS == 4


class TestBuildConfig:
    def test_scale_condition_and_shock_kind_applied(self):
        config = stage9._build_config(80, 6, seed=1)
        assert config.population_size == 80
        assert config.n_patches == 6
        for channel in stage9._CHANNELS:
            assert getattr(config, f"{channel}_enabled") is True
            assert getattr(config, f"{channel}_history_kind") == "repeated_shocks"
            assert getattr(config, f"{channel}_n_shocks") == 4

    def test_transmission_and_substrate_flags_set(self):
        config = stage9._build_config(40, 3, seed=1)
        assert config.security_pressure_returns_to_delegation_enabled is True
        assert config.delegation_enabled is True
        assert config.rng_mode == "mechanism_substreams"


class TestManipulationCheckAndRunOne:
    def test_manipulation_check_passes_for_a_real_run(self):
        record = stage9._run_one(40, 3, seed=1)
        assert record["manipulation_check_passed"] is True

    def test_run_one_returns_expected_shape(self):
        record = stage9._run_one(40, 3, seed=2)
        assert set(record.keys()) == {
            "seed", "population_size", "n_patches", "manipulation_check_passed",
            "sequencing_vector", "phenotype_vector", "s_obs", "z_obs",
        }
        assert len(record["sequencing_vector"]) == 8
        assert len(record["phenotype_vector"]) == 14

    def test_manipulation_check_fails_on_wrong_scale(self):
        """Confirms the check is a real check, not a tautology: a
        config built for one scale, verified against a DIFFERENT
        declared scale, must fail."""
        config = stage9._build_config(40, 3, seed=1)
        from abm_governance.simulation import Simulation
        sim = Simulation(config)
        sim.run()
        assert stage9._manipulation_check(sim, population_size=80, n_patches=3) is False


class TestRunAtSmallScale:
    def test_small_scale_run_produces_correct_run_count(self, monkeypatch):
        monkeypatch.setattr(stage9, "POPULATION_CONDITIONS", (40,))
        monkeypatch.setattr(stage9, "N_PATCHES_CONDITIONS", (3,))
        report = stage9.run(n_seeds_per_cell=1)
        assert report["n_runs"] == 1
        assert report["n_cells"] == 1
        assert report["all_manipulation_checks_passed"] is True

    def test_write_report_persists_to_disk(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stage9, "POPULATION_CONDITIONS", (40,))
        monkeypatch.setattr(stage9, "N_PATCHES_CONDITIONS", (3,))
        out_dir = str(tmp_path / "stage9")
        report = stage9.write_report(out_dir=out_dir, n_seeds_per_cell=1)
        assert "report_hash" in report
        assert (tmp_path / "stage9" / "records.json").exists()

    def test_no_six_way_verdict_rendered(self, monkeypatch):
        monkeypatch.setattr(stage9, "POPULATION_CONDITIONS", (40,))
        monkeypatch.setattr(stage9, "N_PATCHES_CONDITIONS", (3,))
        report = stage9.run(n_seeds_per_cell=1)
        assert "verdict" not in report
        assert "decision_gate_note" in report


class TestReportHash:
    def test_stable_across_key_order(self):
        assert stage9.report_hash({"a": 1, "b": 2}) == stage9.report_hash({"b": 2, "a": 1})

    def test_changes_with_content(self):
        assert stage9.report_hash({"a": 1}) != stage9.report_hash({"a": 2})


class TestForbiddenTerminologyGuardExtendsToStage9Script:
    def test_stage9_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level13_stage9_scale_and_shock_robustness")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL13_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
