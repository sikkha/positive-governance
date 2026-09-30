"""Level 1.3, Stage 5 (task #100): causal historical counterfactuals
(matched-seed) (``experiments/level13_stage5_causal_counterfactuals.py``).

Runs the stage's own machinery at small scale (1-2 seeds) to confirm
mechanics -- the actual 16-seed, session-budget-scale run and its
``outputs/level13_stage5_causal_counterfactuals/records.json`` record
are produced by running the script directly. Also exercises the
task #109 bug-fix regression directly: a matched base/erased/reversed
triple must show at least SOME divergence, confirming the transmission
sub-flags + institutional substrate are actually wired (the exact
failure mode the original bug produced was byte-identical triples)."""

from __future__ import annotations

import importlib
import inspect

from experiments import level13_stage5_causal_counterfactuals as stage5
from tests.test_level12_structural_guards import _strip_docstrings_and_comments
from tests.test_level13_sem_firewall_extension import FORBIDDEN_LEVEL13_TERMS


class TestBaseConfig:
    def test_master_and_transmission_flags_all_set(self):
        config = stage5._base_config(1)
        assert config.historical_module_enabled is True
        assert config.security_pressure_enabled is True
        assert config.security_pressure_returns_to_delegation_enabled is True
        assert config.security_pressure_admin_capacity_demand_enabled is True
        assert config.entrenchment_enabled is True
        assert config.performance_legitimacy_enabled is True
        assert config.procedural_legitimacy_enabled is True

    def test_institutional_substrate_active(self):
        """Task #109 regression: the first draft built on bare
        level1_rule_formation_default() (delegation off by that
        preset's own design) -- the fix switched to
        level12b_frozen_reference(), which must leave delegation (and
        the rest of the Level 1.1/1.2b substrate) active."""
        config = stage5._base_config(1)
        assert config.delegation_enabled is True
        assert config.rng_mode == "mechanism_substreams"

    def test_only_security_pressure_channel_enabled(self):
        config = stage5._base_config(1)
        assert config.bargaining_pressure_enabled is False
        assert config.coordination_complexity_enabled is False


class TestSummarizeShape:
    def test_returns_expected_keys(self):
        config = stage5._base_config(1)
        from abm_governance.simulation import Simulation
        sim = Simulation(config)
        sim.run()
        summary = stage5._summarize(sim)
        assert set(summary.keys()) == {"sequencing_vector", "phenotype_vector", "s_obs", "z_obs"}
        assert len(summary["sequencing_vector"]) == 8
        assert len(summary["phenotype_vector"]) == 14


class TestRunMatchedTriple:
    def test_returns_expected_shape(self):
        record = stage5._run_matched_triple(7_000_000)
        expected_keys = {
            "seed", "base", "erased", "reversed",
            "erased_vs_base_s_obs_abs_diff", "erased_vs_base_z_obs_abs_diff",
            "reversed_vs_base_s_obs_abs_diff", "reversed_vs_base_z_obs_abs_diff",
            "sequencing_vector_identical_erased_vs_base", "sequencing_vector_identical_reversed_vs_base",
        }
        assert set(record.keys()) == expected_keys

    def test_task_109_regression_some_divergence_present(self):
        """The exact bug this stage caught: byte-identical base and
        counterfactual outcomes despite genuinely different realized
        pressure series. With both fixes (transmission sub-flags +
        institutional substrate) in place, at least one of the four
        divergence measures must be strictly positive for this seed."""
        record = stage5._run_matched_triple(7_000_000)
        diffs = [
            record["erased_vs_base_s_obs_abs_diff"],
            record["erased_vs_base_z_obs_abs_diff"],
            record["reversed_vs_base_s_obs_abs_diff"],
            record["reversed_vs_base_z_obs_abs_diff"],
        ]
        assert any(d > 0.0 for d in diffs)


class TestRunAtSmallScale:
    def test_small_scale_run_produces_correct_run_count(self, monkeypatch):
        monkeypatch.setattr(stage5, "N_SEEDS", 2)
        report = stage5.run(n_seeds=2)
        assert report["n_seeds"] == 2
        assert len(report["records"]) == 2

    def test_write_report_persists_to_disk(self, tmp_path):
        out_dir = str(tmp_path / "stage5")
        report = stage5.write_report(out_dir=out_dir, n_seeds=1)
        assert "report_hash" in report
        assert (tmp_path / "stage5" / "records.json").exists()


class TestReportHash:
    def test_stable_across_key_order(self):
        assert stage5.report_hash({"a": 1, "b": 2}) == stage5.report_hash({"b": 2, "a": 1})

    def test_changes_with_content(self):
        assert stage5.report_hash({"a": 1}) != stage5.report_hash({"a": 2})


class TestForbiddenTerminologyGuardExtendsToStage5Script:
    def test_stage5_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level13_stage5_causal_counterfactuals")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL13_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
