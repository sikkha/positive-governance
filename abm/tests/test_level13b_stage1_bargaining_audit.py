"""Level 1.3b, Stage 1 (task #112): tests for ``experiments/level13b_
stage1_bargaining_audit.py``. Exercises the hand-computed microcase (no
simulation) directly plus one small instrumented run -- the real full
audit lives in ``outputs/level13b_bargaining_activation_audit/
stage1_diagnostic.json``, produced by running the script directly."""

from __future__ import annotations

import json
import os

import pytest

from experiments import level13b_stage1_bargaining_audit as stage1


class TestHandComputedMicrocase:
    def test_hand_expected_series_matches_implementation(self):
        result = stage1.run_hand_computed_microcase()
        assert result["hand_computed_expected_series_matches_implementation"] is True

    def test_sustained_crossing_matches_hand_expectation(self):
        result = stage1.run_hand_computed_microcase()
        assert result["sustained_crossing_step_matches_hand_expectation"] is True
        assert result["sustained_crossing_step"] == 0


class TestRepresentativeConfigs:
    def test_stage3_representative_config_matches_security_first_onsets(self):
        config = stage1._stage3_representative_config()
        assert config.security_pressure_onset_step == 0
        assert config.bargaining_pressure_onset_step == 150
        assert config.coordination_complexity_onset_step == 300
        assert config.entrenchment_enabled is True

    def test_stage4_representative_config_enables_all_channels_and_legitimacy(self):
        config = stage1._stage4_representative_config()
        assert config.performance_legitimacy_enabled is True
        assert config.procedural_legitimacy_enabled is True
        assert config.n_patches == 4


class TestRunInstrumented:
    def test_instrumented_run_preserves_real_contribution_round_after_finishing(self):
        import dataclasses
        import abm_governance.rules.contributions as contributions_module
        real_fn_before = contributions_module.contribution_round
        # SimulationConfig is a frozen dataclass -- shrink to a fast
        # small-scale run for the test via dataclasses.replace.
        config = dataclasses.replace(stage1._stage3_representative_config(), n_steps=30)
        result = stage1._run_instrumented(config, label="test")
        assert contributions_module.contribution_round is real_fn_before
        assert result["label"] == "test"
        assert "n_contribution_events" in result
        assert "bargaining_participation_sustained_crossing_step_post_fix" in result


class TestActualOutputIfPresent:
    def test_saved_diagnostic_confirms_the_hand_computed_check(self):
        path = os.path.join(stage1.OUT_DIR, "stage1_diagnostic.json")
        if not os.path.exists(path):
            pytest.skip("Stage 1 saved diagnostic not present in this environment")
        with open(path) as f:
            report = json.load(f)
        assert report["hand_computed_microcase"]["hand_computed_expected_series_matches_implementation"] is True
        assert "empirical_diagnostics" in report and "disposition" in report
