"""Level 1.3b, Stage 3 (task #116): tests for ``experiments/level13b_
stage3_matched_sequencing_factorial.py``. Mirrors Level 1.3's own
per-stage test pattern (``tests/test_level13_stage3_sequencing_
entrenchment_factorial.py``) -- exercises the stage's own real
machinery at small scale; the actual 216-run archived result lives in
``outputs/level13b_stage3_matched_sequencing_factorial/records.json``,
produced by running the script directly. Forbidden-terminology coverage
for this file is handled once, mechanically, by ``tests/test_level13b_
sem_firewall_extension.py``'s own glob over every ``level13b_*.py``
experiment script -- not duplicated here."""

from __future__ import annotations

from experiments import level13b_stage3_matched_sequencing_factorial as stage3


def _eco_points():
    return stage3._load_ecological_points()


class TestFactorsAndConstants:
    def test_three_orderings_three_entrenchment_four_legitimacy_three_strata(self):
        assert len(stage3.FACTORS["pressure_ordering"]) == 3
        assert len(stage3.FACTORS["entrenchment"]) == 3
        assert len(stage3.FACTORS["legitimacy"]) == 4
        assert len(stage3.FACTORS["ecological_stratum"]) == 3

    def test_security_first_and_bargaining_first_share_the_same_onset_slots(self):
        """Matched cumulative pressure exposure by construction (module
        docstring): security_first/bargaining_first share the SAME
        three onset slots {0, 150, 300}, just assigned to different
        channels; coevolution instead activates all three at onset 0
        (a deliberately different, degenerate case, per the same
        docstring) -- so only the first two orderings are compared here."""
        sec = stage3.FACTORS["pressure_ordering"]["security_first"]
        barg = stage3.FACTORS["pressure_ordering"]["bargaining_first"]
        assert set(sec.values()) == set(barg.values()) == {0, 150, 300}

    def test_coevolution_activates_all_three_channels_at_onset_zero(self):
        coev = stage3.FACTORS["pressure_ordering"]["coevolution"]
        assert set(coev.values()) == {0}


class TestLoadEcologicalPoints:
    def test_three_strata_present(self):
        points = _eco_points()
        assert set(points.keys()) == {"low_feasibility", "medium_feasibility", "high_feasibility"}


class TestBuildConfigAndManipulationCheck:
    def test_build_config_assigns_onsets_and_entrenchment_flag(self):
        eco_points = _eco_points()
        ordering_name = next(iter(stage3.FACTORS["pressure_ordering"]))
        config = stage3._build_config(ordering_name, "off", "neither", "low_feasibility", 1, eco_points)
        order_onsets = stage3.FACTORS["pressure_ordering"][ordering_name]
        for channel, onset in order_onsets.items():
            assert getattr(config, f"{channel}_onset_step") == onset
            assert getattr(config, f"{channel}_enabled") is True
        assert config.entrenchment_enabled is False

    def test_manipulation_check_passes_on_a_real_run(self):
        eco_points = _eco_points()
        result = stage3._run_one(("coevolution", "off", "neither", "low_feasibility", 0, eco_points))
        assert result["manipulation_check_passed"] is True

    def test_run_one_returns_expected_shape(self):
        eco_points = _eco_points()
        result = stage3._run_one(("security_first", "moderate", "dual", "medium_feasibility", 0, eco_points))
        expected_keys = {
            "ordering_name", "entrenchment_name", "legitimacy_name", "stratum", "seed_idx", "seed",
            "manipulation_check_passed", "bargaining_participation_sustained_crossing_step",
            "S_obs", "Z_obs", "realized_compliance_rate", "mean_resources_final_step",
            "n_active_rules_final_step", "entrenchment_index_final_step",
            "cross_founder_reconstruction_count_final_step", "n_contribution_events",
        }
        assert set(result.keys()) == expected_keys


class TestRunSmokeTest:
    def test_smoke_test_passes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stage3, "OUT_DIR", str(tmp_path))
        eco_points = _eco_points()
        assert stage3.run_smoke_test(eco_points) is True
        assert (tmp_path / "smoke_test.json").exists()


class TestSummarize:
    def test_summarize_counts_manipulation_failures_and_computes_contrasts(self):
        eco_points = _eco_points()
        records = [
            stage3._run_one(("security_first", "off", "neither", "low_feasibility", 0, eco_points)),
            stage3._run_one(("coevolution", "off", "neither", "low_feasibility", 0, eco_points)),
            stage3._run_one(("security_first", "off", "neither", "low_feasibility", 1, eco_points)),
            stage3._run_one(("coevolution", "off", "neither", "low_feasibility", 1, eco_points)),
        ]
        summary = stage3.summarize(records)
        assert summary["n_records"] == 4
        assert summary["all_manipulation_checks_passed"] is True
        assert isinstance(summary["contrasts"], list)


class TestEntrenchmentOverridesMaturation:
    def test_returns_int_for_every_entrenchment_name(self):
        for name in stage3.FACTORS["entrenchment"]:
            assert isinstance(stage3.entrenchment_overrides_maturation(name), int)
