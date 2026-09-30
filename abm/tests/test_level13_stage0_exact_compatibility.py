"""Level 1.3, Stage 0 (task #95): exact compatibility experiment
(``experiments/level13_stage0_exact_compatibility.py``).

Runs the stage's own machinery at a small scale (not the full 20-seed
budget, to keep this test fast) to confirm mechanics -- the actual
20-seed, session-budget-scale run and its `outputs/level13_stage0_
exact_compatibility/report.json` record are produced by running the
script directly (`python -m experiments.level13_stage0_exact_
compatibility`), mirroring every other experiment-script/test-file
split already established in this project."""

from __future__ import annotations

import importlib
import inspect

from experiments import level13_stage0_exact_compatibility as stage0
from tests.test_level12_structural_guards import _strip_docstrings_and_comments
from tests.test_level13_sem_firewall_extension import FORBIDDEN_LEVEL13_TERMS


class TestMetricsIdentical:
    def test_identical_rows_pass(self):
        rows = [{"a": 1.0, "b": 2.0}]
        assert stage0._metrics_identical(rows, rows)

    def test_different_length_fails(self):
        assert not stage0._metrics_identical([{"a": 1.0}], [{"a": 1.0}, {"a": 2.0}])

    def test_nan_equals_nan(self):
        rows_a = [{"a": float("nan")}]
        rows_b = [{"a": float("nan")}]
        assert stage0._metrics_identical(rows_a, rows_b)

    def test_different_values_fail(self):
        assert not stage0._metrics_identical([{"a": 1.0}], [{"a": 2.0}])

    def test_different_keys_fail(self):
        assert not stage0._metrics_identical([{"a": 1.0}], [{"b": 1.0}])


class TestRunStage0AtSmallScale:
    def test_both_comparisons_pass_at_small_scale(self):
        report = stage0.run_stage0(n_seeds=3)
        assert report["overall_pass"] is True
        assert report["bare_level1_preset_module_gate_noop"]["byte_for_byte_identical"] is True
        assert report["frozen_reference_preset_module_gate_noop"]["byte_for_byte_identical"] is True

    def test_report_has_expected_shape(self):
        report = stage0.run_stage0(n_seeds=2)
        assert report["n_seeds"] == 2
        assert "bare_level1_preset_module_gate_noop" in report
        assert "frozen_reference_preset_module_gate_noop" in report

    def test_deterministic_given_same_seed_base(self):
        r1 = stage0.run_stage0(n_seeds=2)
        r2 = stage0.run_stage0(n_seeds=2)
        assert r1 == r2


class TestWriteStage0Report:
    def test_write_produces_a_report_with_manifest_hash(self, tmp_path, monkeypatch):
        # write_stage0_report calls load_and_verify_manifest() against
        # the module-level default OUT_DIR -- ensure a manifest exists
        # there first (writing to a tmp dir would require monkeypatching
        # experiments.level13_preregistration.OUT_DIR too; simplest and
        # most honest is to actually freeze one in a tmp dir and point
        # both modules at it).
        from experiments import level13_preregistration as prereg
        prereg_dir = str(tmp_path / "prereg")
        monkeypatch.setattr(prereg, "OUT_DIR", prereg_dir)
        prereg.write_manifest(out_dir=prereg_dir)

        out_dir = str(tmp_path / "stage0")
        report = stage0.write_stage0_report(out_dir=out_dir, n_seeds=2)
        assert "preregistration_manifest_hash" in report
        assert (tmp_path / "stage0" / "report.json").exists()


class TestForbiddenTerminologyGuardExtendsToStage0Script:
    def test_stage0_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level13_stage0_exact_compatibility")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL13_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
