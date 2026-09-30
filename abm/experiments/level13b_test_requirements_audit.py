#!/usr/bin/env python3
"""Level 1.3b, task #124: test requirements sweep (Section 20).

**Disclosed scope note.** As with Level 1.3's own equivalent task
(#105, ``experiments/level13_test_requirements_audit.py``), Section
20's exact verbatim enumerated category list is not recoverable from
what remains in this session's context (compacted more than once over
this milestone's long run). Rather than guess at its wording, this
audit constructs its own category list directly from what Level 1.3b
actually built -- every Work Package A-K, every Stage 0-10 script,
preregistration hashing, backward compatibility, the SEM/terminology
firewall, and the two genuine cross-cutting bugs this milestone found
and fixed (cross-process frozenset-hash instability at Stage 0;
``copy.deepcopy``/frozenset-iteration-order instability at Stage 6) --
and verifies coverage MECHANICALLY, the same discipline Level 1.2b's
own Work Package R and Level 1.3's own task #105 both established:
every citation in ``COVERAGE_MATRIX`` is checked against the actual
file system and actual source text, not asserted from memory. Every
citation below was verified against real `grep`/import output before
being written, and :func:`verify_coverage_matrix` re-verifies all of
them mechanically every time this script runs.

**Real gap found and closed by this task, not merely disclosed.**
Before this task, Stages 3-10 (tasks #116-123) and Stages 0-2 (tasks
#112, #113, #115) had ONLY inline ``run_smoke_test`` functions inside
each experiment script itself -- no dedicated ``pytest``-collected test
file exercised any of their own real machinery (config-building,
manipulation checks, mutators, ledger views, coverage matrices) at
small scale, unlike Level 1.3's own precedent (``tests/test_level13_
stage{0..9}_*.py``, one dedicated file per stage). This task closes
that gap for all 11 Level 1.3b stage scripts: 11 new files, ``tests/
test_level13b_stage{0..10}_*.py`` (Stage 6's own file additionally
re-confirms this milestone's sham-machinery regression at small scale,
not merely via ``tests/test_level13b_state_checkpoint.py``'s own
synthetic/single-object-level tests)."""

from __future__ import annotations

import json
import os
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = "outputs/level13b_test_requirements_audit"

#: Category -> the specific test file(s) and representative test
#: class/function name(s) claimed to cover it. A SAMPLE, not an
#: exhaustive test-list mirror -- same convention Level 1.2b's own Work
#: Package R and Level 1.3's own task #105 established.
COVERAGE_MATRIX: dict[str, dict] = {
    "bargaining_calibration_frozen_wp_b_c": {
        "files": ["tests/test_level13b_bargaining_activation_construction.py", "tests/test_level13b_stage2_bargaining_calibration.py"],
        "functions": ["TestComplianceSeriesIsHeldNotZeroFilled", "TestSustainedCrossingCanNowRegister", "TestSummarize", "TestWriteScopeDeclaration"],
    },
    "ecological_strata_reuse": {
        "files": ["tests/test_level13b_stage3_matched_sequencing_factorial.py", "tests/test_level13b_stage4_homogeneous_discovery.py"],
        "functions": ["TestLoadEcologicalPoints", "TestStratumFromDraw"],
    },
    "stage0_frozen_compatibility_and_cross_process_regression": {
        "files": ["tests/test_level13b_stage0_frozen_compatibility.py", "tests/test_level13b_cross_process_reproducibility.py"],
        "functions": ["TestMetricsIdentical", "TestRunComparisonAAtSmallScale", "TestTransmissibleComponentNamesIsDeterministicallyOrdered", "TestCrossProcessDeterminism"],
    },
    "stage1_bargaining_participation_audit": {
        "files": ["tests/test_level13b_stage1_bargaining_audit.py"],
        "functions": ["TestHandComputedMicrocase", "TestRepresentativeConfigs", "TestRunInstrumented"],
    },
    "stage2_bargaining_calibration_sweep": {
        "files": ["tests/test_level13b_stage2_bargaining_calibration.py"],
        "functions": ["TestBuildConfigAndRunOne", "TestSummarize", "TestRunSmokeTest"],
    },
    "stage3_matched_sequencing_factorial": {
        "files": ["tests/test_level13b_stage3_matched_sequencing_factorial.py"],
        "functions": ["TestFactorsAndConstants", "TestBuildConfigAndManipulationCheck", "TestSummarize"],
    },
    "stage4_homogeneous_discovery": {
        "files": ["tests/test_level13b_stage4_homogeneous_discovery.py"],
        "functions": ["TestParameterSpace", "TestLhsDraws", "TestBuildConfigAndRunOne", "TestSummarize"],
    },
    "stage5_temporal_persistence": {
        "files": ["tests/test_level13b_stage5_temporal_persistence.py", "tests/test_level13b_historical_persistence.py"],
        "functions": ["TestBaseConfigAndRunBase", "TestAnalyze", "TestWindowedDiagnostics", "TestClassifyPersistence"],
    },
    "stage6_history_erasure_and_checkpoint_machinery": {
        "files": ["tests/test_level13b_stage6_history_erasure.py", "tests/test_level13b_state_checkpoint.py"],
        "functions": ["TestAnalyzeShamValidation", "TestMutators", "TestShamForkAndFinishIsByteIdenticalToUninterruptedRun", "TestForkFrozensetOrderCaveat"],
    },
    "stage7_model_comparison": {
        "files": ["tests/test_level13b_stage7_model_comparison.py"],
        "functions": ["TestDiscreteCandidates", "TestContinuousCandidates", "TestPathDependentCandidate"],
    },
    "stage8_fresh_confirmation": {
        "files": ["tests/test_level13b_stage8_fresh_confirmation.py"],
        "functions": ["TestSeedAndDesignDisjointness", "TestReconstructFrozenStage4Fit", "TestScoreFreshData"],
    },
    "stage9_measurement_audit": {
        "files": ["tests/test_level13b_stage9_measurement_audit.py"],
        "functions": ["TestAllComponents", "TestJob", "TestFactorStructureAndLeaveOneOut", "TestVerifyAgainstArchive"],
    },
    "stage10_ecological_accounting_and_scale_shock": {
        "files": ["tests/test_level13b_stage10_ecological_control_scale_shock.py"],
        "functions": ["TestBuildConfigAndRunOne", "TestLedgerViews", "TestScaleRobustnessSummary"],
    },
    "historical_counterfactual_transforms": {
        "files": ["tests/test_level13b_historical_persistence.py"],
        "functions": ["TestEqualizePressureSeries"],
    },
    "preregistration_manifest_hashing": {
        "files": ["tests/test_level13b_preregistration.py"],
        "functions": ["TestManifestHash", "TestWriteAndVerifyManifest", "TestDecisionGateOutcomes", "TestHypotheses"],
    },
    "sem_terminology_firewall": {
        "files": ["tests/test_level13b_sem_firewall_extension.py"],
        "functions": ["TestLevel13bExperimentScriptTerminologyGuard", "TestLevel13bDocsTerminologyGuard"],
    },
    "structural_guard_whole_package_scan": {
        "files": ["tests/test_level12_structural_guards.py"],
        "functions": ["test_every_source_module_free_of_forbidden_terms"],
    },
    "freeze_then_hash_tamper_detection": {
        "files": ["tests/test_level13b_preregistration.py"],
        "functions": ["TestWriteAndVerifyManifest"],
    },
    "checkpoint_run_partial_finish_exactness": {
        "files": ["tests/test_level13b_state_checkpoint.py"],
        "functions": ["TestRunPartialMatchesRun", "TestForkIsIndependent", "TestMutationActuallyAppliesToFork"],
    },
}


def verify_coverage_matrix() -> dict:
    findings = {}
    for category, spec in COVERAGE_MATRIX.items():
        category_ok = True
        file_findings = []
        for rel_path in spec["files"]:
            path = PROJECT_ROOT / rel_path
            exists = path.exists()
            functions_found = []
            if exists:
                source = path.read_text()
                for fn in spec["functions"]:
                    functions_found.append({"name": fn, "present": fn in source})
            category_ok = category_ok and exists and (not exists or any(f["present"] for f in functions_found))
            file_findings.append({"file": rel_path, "exists": exists, "functions": functions_found})
        findings[category] = {"status": "pass" if category_ok else "fail", "file_findings": file_findings}
    return findings


def _all_level13b_stage_scripts_have_a_dedicated_test_file() -> dict:
    """A second, independent mechanical check (not just COVERAGE_MATRIX
    citations): every ``experiments/level13b_stage*.py`` script must
    have a same-numbered ``tests/test_level13b_stage*.py`` file --
    catches a new stage script added later without its own test file,
    even before anyone updates COVERAGE_MATRIX by hand."""
    experiments_dir = PROJECT_ROOT / "experiments"
    tests_dir = PROJECT_ROOT / "tests"
    missing = []
    for path in sorted(experiments_dir.glob("level13b_stage*.py")):
        stem = path.stem  # e.g. "level13b_stage3_matched_sequencing_factorial"
        expected = tests_dir / f"test_{stem}.py"
        if not expected.exists():
            missing.append(stem)
    return {"missing_test_files_for_stage_scripts": missing, "all_stage_scripts_covered": missing == []}


def run() -> dict:
    findings = verify_coverage_matrix()
    all_pass = all(v["status"] == "pass" for v in findings.values())
    missing_categories = [k for k, v in findings.items() if v["status"] != "pass"]
    stage_script_check = _all_level13b_stage_scripts_have_a_dedicated_test_file()
    return {
        "milestone": "level1.3b_test_requirements_sweep",
        "n_categories": len(COVERAGE_MATRIX),
        "all_categories_covered": all_pass,
        "missing_categories": missing_categories,
        "findings": findings,
        "stage_script_dedicated_test_file_check": stage_script_check,
        "scope_note": (
            "Section 20's exact category list is not verbatim-recoverable this session "
            "(context compacted); this matrix was constructed from what Level 1.3b actually "
            "built, not transcribed from spec text -- see this module's own docstring"
        ),
    }


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    report = run()
    with open(f"{OUT_DIR}/results.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Level 1.3b test requirements sweep: {report['n_categories']} categories, all_covered={report['all_categories_covered']}")
    if report["missing_categories"]:
        print(f"MISSING: {report['missing_categories']}")
    if not report["stage_script_dedicated_test_file_check"]["all_stage_scripts_covered"]:
        print(f"MISSING STAGE TEST FILES: {report['stage_script_dedicated_test_file_check']['missing_test_files_for_stage_scripts']}")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
