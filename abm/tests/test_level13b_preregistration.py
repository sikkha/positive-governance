"""Level 1.3b, task #114 (Section 16): the milestone-level
preregistration manifest (``experiments/level13b_preregistration.py``)."""

from __future__ import annotations

import json

import pytest

from experiments import level13b_preregistration as prereg


class TestBuildManifest:
    def test_manifest_is_deterministic(self):
        assert prereg.build_manifest() == prereg.build_manifest()

    def test_manifest_covers_every_stage(self):
        manifest = prereg.build_manifest()
        for key in (
            "bargaining_calibration", "stage3_matched_factorial", "stage4_homogeneous_discovery",
            "stage5_temporal_persistence", "stage6_history_erasure", "stage7_model_comparison",
            "stage8_fresh_confirmation", "stage9_measurement_audit", "work_package_k_accounting",
        ):
            assert key in manifest

    def test_bargaining_calibration_matches_disclosed_defaults(self):
        cal = prereg.build_manifest()["bargaining_calibration"]
        assert cal["contribution_amount"] == 0.2
        assert cal["contribution_period_steps"] == 10
        assert cal["activation_fraction_at_defaults"] == {
            "low_feasibility": 0.5, "medium_feasibility": 0.5, "high_feasibility": 0.5,
        }

    def test_rng_mode_is_mechanism_substreams(self):
        assert prereg.build_manifest()["rng_commitments"]["rng_mode"] == "mechanism_substreams"

    def test_stage4_declares_the_disclosed_minimum_scale(self):
        stage4 = prereg.build_manifest()["stage4_homogeneous_discovery"]
        assert stage4["n_points"] == 48
        assert stage4["n_seeds_per_point"] == 5
        assert stage4["n_runs_declared"] == 240
        assert stage4["no_counterfactual_reruns_in_pool"] is True

    def test_stage8_declares_the_disclosed_minimum_scale(self):
        stage8 = prereg.build_manifest()["stage8_fresh_confirmation"]
        assert stage8["n_points"] == 24
        assert stage8["n_seeds_per_point"] == 4
        assert stage8["n_runs_declared"] == 96

    def test_stage6_has_exactly_six_matched_interventions_including_a_sham(self):
        stage6 = prereg.build_manifest()["stage6_history_erasure"]
        assert len(stage6["interventions"]) == 6
        assert "sham_identical_state_copy" in stage6["interventions"]
        assert "no_intervention_control" in stage6["interventions"]


class TestHypotheses:
    def test_exactly_eight_hypotheses(self):
        assert len(prereg.HYPOTHESES) == 8

    def test_every_hypothesis_has_a_nonempty_statement(self):
        for key, statement in prereg.HYPOTHESES.items():
            assert isinstance(statement, str)
            assert len(statement) > 0

    def test_h8_discreteness_explicitly_allowed_to_fail(self):
        assert "h8" in [k.lower()[:2] for k in prereg.HYPOTHESES]
        assert "explicitly allowed to fail" in prereg.HYPOTHESES["H8_discreteness"]


class TestDecisionGateOutcomes:
    def test_exactly_eight_outcomes(self):
        assert len(prereg.DECISION_GATE_OUTCOMES) == 8

    def test_do_not_prefer_is_one_of_the_eight(self):
        assert prereg.DECISION_GATE_DO_NOT_PREFER in prereg.DECISION_GATE_OUTCOMES

    def test_do_not_prefer_is_three_families(self):
        assert prereg.DECISION_GATE_DO_NOT_PREFER == "F_three_families"

    def test_every_outcome_has_a_nonempty_description(self):
        for key, description in prereg.DECISION_GATE_OUTCOMES.items():
            assert isinstance(description, str)
            assert len(description) > 0

    def test_manifest_includes_the_full_decision_gate(self):
        manifest = prereg.build_manifest()
        assert manifest["decision_gate_outcomes"] == prereg.DECISION_GATE_OUTCOMES
        assert manifest["decision_gate_do_not_prefer"] == "F_three_families"


class TestManifestHash:
    def test_hash_is_stable_across_key_order(self):
        assert prereg.manifest_hash({"a": 1, "b": 2}) == prereg.manifest_hash({"b": 2, "a": 1})

    def test_hash_changes_when_content_changes(self):
        assert prereg.manifest_hash({"a": 1}) != prereg.manifest_hash({"a": 2})

    def test_real_manifest_hash_is_deterministic(self):
        manifest = prereg.build_manifest()
        assert prereg.manifest_hash(manifest) == prereg.manifest_hash(manifest)


class TestWriteAndVerifyManifest:
    def test_write_then_verify_round_trips(self, tmp_path):
        out_dir = str(tmp_path / "level13b_prereg")
        written = prereg.write_manifest(out_dir=out_dir)
        verified = prereg.load_and_verify_manifest(out_dir=out_dir)
        assert verified["hash"] == written["hash"]
        assert verified["manifest"] == written["manifest"]

    def test_tampering_with_manifest_content_is_detected(self, tmp_path):
        out_dir = str(tmp_path / "level13b_prereg")
        prereg.write_manifest(out_dir=out_dir)
        with open(f"{out_dir}/manifest.json") as f:
            manifest = json.load(f)
        manifest["stage4_homogeneous_discovery"]["n_points"] = 999
        with open(f"{out_dir}/manifest.json", "w") as f:
            json.dump(manifest, f)
        with pytest.raises(ValueError, match="altered"):
            prereg.load_and_verify_manifest(out_dir=out_dir)
