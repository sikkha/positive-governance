"""Level 1.3, Stage 2 (task #97): calibration without phenotype labels
(``experiments/level13_stage2_calibration.py``)."""

from __future__ import annotations

import importlib
import inspect
import json

import pytest

from experiments import level13_stage2_calibration as stage2
from tests.test_level12_structural_guards import _strip_docstrings_and_comments
from tests.test_level13_sem_firewall_extension import FORBIDDEN_LEVEL13_TERMS


class TestBuildDesign:
    def test_deterministic(self):
        d1 = stage2.build_design(n_points=10, n_steps=30)
        d2 = stage2.build_design(n_points=10, n_steps=30)
        assert d1 == d2

    def test_correct_point_count(self):
        design = stage2.build_design(n_points=12, n_steps=30)
        assert design["n_points"] == 12
        assert len(design["points"]) == 12

    def test_default_n_points_matches_preregistration(self):
        from experiments.level13_preregistration import STAGE_SAMPLE_SIZES
        assert stage2.N_POINTS == STAGE_SAMPLE_SIZES["stage2_calibration_without_phenotype_labels"]["n_points"]

    def test_cut_points_are_frozen_by_this_stage(self):
        design = stage2.build_design(n_points=15, n_steps=30)
        assert "stratum_cut_points" in design
        assert design["stratum_cut_points"]["low_cut"] < design["stratum_cut_points"]["high_cut"]


class TestDesignHash:
    def test_stable_across_key_order(self):
        assert stage2.design_hash({"a": 1, "b": 2}) == stage2.design_hash({"b": 2, "a": 1})

    def test_changes_with_content(self):
        assert stage2.design_hash({"a": 1}) != stage2.design_hash({"a": 2})


class TestWriteAndVerifyDesign:
    def test_write_then_verify_round_trips(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stage2, "N_POINTS", 10)
        monkeypatch.setattr(stage2, "N_STEPS", 30)
        out_dir = str(tmp_path / "stage2")
        written = stage2.write_design(out_dir=out_dir)
        verified = stage2.load_and_verify_design(out_dir=out_dir)
        assert verified["hash"] == written["hash"]
        assert verified["design"] == written["design"]

    def test_tampering_is_detected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stage2, "N_POINTS", 10)
        monkeypatch.setattr(stage2, "N_STEPS", 30)
        out_dir = str(tmp_path / "stage2")
        stage2.write_design(out_dir=out_dir)
        with open(f"{out_dir}/design.json") as f:
            design = json.load(f)
        design["stratum_cut_points"]["low_cut"] = 999.0
        with open(f"{out_dir}/design.json", "w") as f:
            json.dump(design, f)
        with pytest.raises(ValueError, match="altered"):
            stage2.load_and_verify_design(out_dir=out_dir)


class TestStage2NeverImportsAnyPhenotypeOrDiscoveryModule:
    """The stage's own defining constraint, checked structurally against
    the script's actual IMPORT statements (AST-based, so the module's
    own docstring explaining this constraint -- which necessarily
    mentions these module names in prose -- cannot itself trip a naive
    substring scan)."""

    def test_no_phenotype_or_discovery_import(self):
        import ast
        source = inspect.getsource(stage2)
        tree = ast.parse(source)
        imported_modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)
        forbidden_imports = (
            "phenotype_discovery", "level13_phenotype", "institutional_phenotype",
            "recurrence_criteria", "sequencing_diagnostics", "sz_obs",
        )
        for term in forbidden_imports:
            offenders = [m for m in imported_modules if term in m]
            assert offenders == [], f"Stage 2 must not import {term!r} (calibration is ecology-only): {offenders}"


class TestForbiddenTerminologyGuardExtendsToStage2Script:
    def test_stage2_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level13_stage2_calibration")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL13_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
