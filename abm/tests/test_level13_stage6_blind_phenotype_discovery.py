"""Level 1.3, Stage 6 (task #101): blind phenotype discovery
(``experiments/level13_stage6_blind_phenotype_discovery.py``).

Runs the stage's own machinery against the REAL Stage 3/4/5 output
already on disk (216 pooled runs, cheap to cluster -- a few seconds,
unlike Stage 3/4/5's own multi-minute simulation runs) rather than a
small-scale subset, since there is no new simulation to downsize here
(the manifest's own commitment: "no new simulation runs").

A fully-NaN pooled column (``seq_bargaining_participation``, disclosed
in this stage's own ``results.json``) triggers a benign, already-
established ``RuntimeWarning: Mean of empty slice`` inside
``preprocess_features``'s pre-existing ``mean_impute`` fallback --
suppressed locally here exactly as ``tests/test_level13_phenotype.py``
already did for the same underlying warning (Work Package H's own
integration test)."""

from __future__ import annotations

import importlib
import inspect
import json
import warnings

import pytest

from experiments import level13_stage6_blind_phenotype_discovery as stage6
from tests.test_level12_structural_guards import _strip_docstrings_and_comments
from tests.test_level13_sem_firewall_extension import FORBIDDEN_LEVEL13_TERMS


@pytest.fixture(scope="module")
def real_report():
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Mean of empty slice")
        return stage6.run()


class TestLoadAndVerify:
    def test_loads_real_stage3_file_successfully(self):
        report = stage6._load_and_verify(stage6.STAGE3_PATH)
        assert "records" in report

    def test_tamper_detected(self, tmp_path):
        path = tmp_path / "tampered.json"
        path.write_text(json.dumps({"a": 1, "report_hash": "not_the_real_hash"}))
        with pytest.raises(ValueError, match="report_hash mismatch"):
            stage6._load_and_verify(str(path))

    def test_no_stored_hash_is_not_an_error(self, tmp_path):
        path = tmp_path / "no_hash.json"
        path.write_text(json.dumps({"a": 1}))
        report = stage6._load_and_verify(str(path))
        assert report == {"a": 1}


class TestWrap:
    def test_wraps_flat_dict_into_value_shape(self):
        wrapped = stage6._wrap({"S_obs": 0.4, "Z_obs": 0.2})
        assert wrapped == {"S_obs": {"value": 0.4}, "Z_obs": {"value": 0.2}}


class TestPoolRecords:
    def test_pooled_counts_match_source_files(self):
        pooled = stage6.pool_records()
        by_source = {}
        for p in pooled:
            by_source[p["source_stage"]] = by_source.get(p["source_stage"], 0) + 1
        assert by_source == {
            "stage3": 72, "stage4": 96,
            "stage5_base": 16, "stage5_erased": 16, "stage5_reversed": 16,
        }
        assert len(pooled) == 216

    def test_every_pooled_vector_has_all_fourteen_dimensions(self):
        from abm_governance.observer.level13_phenotype import LEVEL13_DIMENSION_KEYS
        pooled = stage6.pool_records()
        for p in pooled[:5]:
            assert set(p["vector"].keys()) == set(LEVEL13_DIMENSION_KEYS)
            for entry in p["vector"].values():
                assert "value" in entry


class TestSelectHeadlineK:
    def test_picks_highest_silhouette_among_k_gte_2(self):
        k_results = [
            {"k": 1, "metrics": {"silhouette": float("nan")}},
            {"k": 2, "metrics": {"silhouette": 0.2}},
            {"k": 3, "metrics": {"silhouette": 0.5}},
            {"k": 4, "metrics": {"silhouette": 0.1}},
        ]
        assert stage6._select_headline_k(k_results) == 3

    def test_returns_none_when_no_k_has_defined_silhouette(self):
        k_results = [{"k": 1, "metrics": {"silhouette": float("nan")}}]
        assert stage6._select_headline_k(k_results) is None


class TestRunOnRealData:
    def test_pools_all_216_runs(self, real_report):
        assert real_report["n_total"] == 216
        assert real_report["n_pooled_by_source"] == {
            "stage3": 72, "stage4": 96,
            "stage5_base": 16, "stage5_erased": 16, "stage5_reversed": 16,
        }

    def test_fourteen_features(self, real_report):
        assert len(real_report["feature_names"]) == 14

    def test_no_six_way_verdict_rendered(self, real_report):
        assert "verdict" not in real_report
        assert "decision_gate_note" in real_report

    def test_every_candidate_method_represented(self, real_report):
        assert set(real_report["k_range_results"].keys()) == {"gmm", "hierarchical"}
        assert "hdbscan_result" in real_report

    def test_headline_k_within_declared_range(self, real_report):
        from abm_governance.observer.phenotype_discovery import DEFAULT_K_RANGE
        if real_report["headline_k"] is not None:
            assert real_report["headline_k"] in DEFAULT_K_RANGE

    def test_missingness_report_covers_every_feature(self, real_report):
        assert set(real_report["missingness_report"].keys()) == set(real_report["feature_names"])


class TestWriteReport:
    def test_persists_to_disk_with_hash(self, tmp_path):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Mean of empty slice")
            report = stage6.write_report(out_dir=str(tmp_path / "stage6"))
        assert "report_hash" in report
        assert (tmp_path / "stage6" / "results.json").exists()


class TestReportHash:
    def test_stable_across_key_order(self):
        assert stage6.report_hash({"a": 1, "b": 2}) == stage6.report_hash({"b": 2, "a": 1})

    def test_changes_with_content(self):
        assert stage6.report_hash({"a": 1}) != stage6.report_hash({"a": 2})


class TestForbiddenTerminologyGuardExtendsToStage6Script:
    def test_stage6_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level13_stage6_blind_phenotype_discovery")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL13_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
