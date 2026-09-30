"""Level 1.3, Stage 3 (task #98): sequencing x entrenchment factorial
(``experiments/level13_stage3_sequencing_entrenchment_factorial.py``).

Runs the stage's own machinery at a small scale (2 orderings, 1 seed
each) to confirm mechanics -- the actual 72-run, session-budget-scale
run and its ``outputs/level13_stage3_sequencing_entrenchment_factorial/
records.json`` record are produced by running the script directly."""

from __future__ import annotations

import importlib
import inspect

from experiments import level13_stage3_sequencing_entrenchment_factorial as stage3
from tests.test_level12_structural_guards import _strip_docstrings_and_comments
from tests.test_level13_sem_firewall_extension import FORBIDDEN_LEVEL13_TERMS


class TestOrderings:
    def test_six_orderings(self):
        assert len(stage3.ORDERINGS) == 6

    def test_every_ordering_is_a_permutation_of_the_three_channels(self):
        channels = set(stage3._CHANNELS)
        for order in stage3.ORDERINGS.values():
            assert set(order) == channels
            assert len(order) == 3

    def test_orderings_are_all_distinct(self):
        orders = list(stage3.ORDERINGS.values())
        assert len(set(orders)) == 6


class TestBuildConfig:
    def test_assigns_onset_steps_in_order(self):
        order_name = next(iter(stage3.ORDERINGS))
        order = stage3.ORDERINGS[order_name]
        config = stage3._build_config(order_name, entrenchment_enabled=False, seed=1)
        for channel, onset in zip(order, stage3._ONSET_GAP_STEPS):
            assert getattr(config, f"{channel}_onset_step") == onset
            assert getattr(config, f"{channel}_enabled") is True
            assert getattr(config, f"{channel}_history_kind") == "early_pulse"

    def test_entrenchment_flag_propagates(self):
        order_name = next(iter(stage3.ORDERINGS))
        config_on = stage3._build_config(order_name, entrenchment_enabled=True, seed=1)
        config_off = stage3._build_config(order_name, entrenchment_enabled=False, seed=1)
        assert config_on.entrenchment_enabled is True
        assert config_off.entrenchment_enabled is False


class TestManipulationCheckAndRunOne:
    def test_manipulation_check_passes_for_a_real_run(self):
        order_name = next(iter(stage3.ORDERINGS))
        record = stage3._run_one(order_name, entrenchment_enabled=False, seed=1)
        assert record["manipulation_check_passed"] is True

    def test_run_one_returns_expected_shape(self):
        order_name = next(iter(stage3.ORDERINGS))
        record = stage3._run_one(order_name, entrenchment_enabled=True, seed=2)
        assert set(record.keys()) == {
            "seed", "order_name", "entrenchment_enabled", "manipulation_check_passed",
            "sequencing_vector", "phenotype_vector",
        }
        assert len(record["sequencing_vector"]) == 8
        assert len(record["phenotype_vector"]) == 14


class TestRunAtSmallScale:
    def test_small_scale_run_produces_correct_run_count(self, monkeypatch):
        monkeypatch.setattr(stage3, "ORDERINGS", dict(list(stage3.ORDERINGS.items())[:2]))
        report = stage3.run(n_seeds_per_cell=1)
        assert report["n_runs"] == 2 * 2 * 1  # 2 orderings x 2 entrenchment settings x 1 seed
        assert report["all_manipulation_checks_passed"] is True

    def test_write_report_persists_to_disk(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stage3, "ORDERINGS", dict(list(stage3.ORDERINGS.items())[:1]))
        out_dir = str(tmp_path / "stage3")
        report = stage3.write_report(out_dir=out_dir, n_seeds_per_cell=1)
        assert "report_hash" in report
        assert (tmp_path / "stage3" / "records.json").exists()


class TestReportHash:
    def test_stable_across_key_order(self):
        assert stage3.report_hash({"a": 1, "b": 2}) == stage3.report_hash({"b": 2, "a": 1})

    def test_changes_with_content(self):
        assert stage3.report_hash({"a": 1}) != stage3.report_hash({"a": 2})


class TestForbiddenTerminologyGuardExtendsToStage3Script:
    def test_stage3_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level13_stage3_sequencing_entrenchment_factorial")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL13_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
