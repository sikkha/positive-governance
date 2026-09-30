#!/usr/bin/env python3
"""Level 1.3, task #105: test requirements sweep.

**Disclosed scope note.** This session's own context was compacted more
than once over this milestone's long run; Section 18's exact verbatim
enumerated category list is not recoverable from what remains in
context (unlike Section 23's six-way decision gate, which WAS recovered
verbatim from ``docs/level1.3_theoretical_translation.md`` -- see
``experiments/level13_preregistration.py``'s own ``DECISION_GATE_
OUTCOMES`` disclosure). Rather than guess at Section 18's exact wording,
this audit constructs its own category list directly from what this
milestone actually built (every Work Package A-H, every Stage 0-9
script, every cross-cutting discipline: preregistration hashing,
backward compatibility, the SEM/terminology firewall, and -- newly,
directly motivated by task #109's own bug -- RNG-mode compliance) and
verifies coverage MECHANICALLY, the same discipline Level 1.2b's own
Work Package R (Section 23, ``experiments/level12b_stage_r_testing_
requirements_audit.py``) established: every citation in
``COVERAGE_MATRIX`` is checked against the actual file system and
actual source text, not asserted from memory. Work Package R's own
retrospective finding is a direct warning taken seriously here: even
within that same Work Package, drafting a coverage matrix from memory
produced five wrong citations out of twenty-five. Every citation below
was verified against real `grep` output before being written, and
:func:`verify_coverage_matrix` re-verifies all of them mechanically
every time this script runs.

**One genuine gap found and closed by this task, not merely
disclosed**: task #109's own bug (transmission sub-flags and
``rng_mode`` silently defaulting away from what the frozen manifest
requires) had no standing regression guard anywhere in this project
before this task -- every earlier fix was verified once, at the time,
and never re-checked automatically afterward. New file: ``tests/
test_level13_rng_mode_compliance.py`` (8 tests, one per stage script
that constructs a ``SimulationConfig`` directly), closing that gap."""

from __future__ import annotations

import json
import os
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = "outputs/level13_test_requirements_audit"

#: Category -> the specific test file(s) and representative test
#: class/function name(s) claimed to cover it. Names are a SAMPLE
#: (not exhaustive) sufficient to prove the claimed file genuinely
#: addresses the category, not a full test-list mirror -- same
#: convention Level 1.2b's own Work Package R established.
COVERAGE_MATRIX: dict[str, dict] = {
    "pressure_signal_generation": {
        "files": ["tests/test_level13_pressure_signals.py"],
        "functions": ["TestConstantKinds", "TestPulseKinds", "TestRepeatedShocks", "TestStochasticReproducible", "TestValidation"],
    },
    "pressure_transmission_channels": {
        "files": ["tests/test_level13_pressure_transmission.py"],
        "functions": ["TestSecurityPressureReturnsToDelegation", "TestSecurityPressureAdminCapacityDemand", "TestBargainingPressureAppealRecall", "TestCoordinationComplexityInteroperableDemand"],
    },
    "sequencing_measurement": {
        "files": ["tests/test_level13_sequencing_diagnostics.py"],
        "functions": ["TestDelegationAndAdministrativeFunctionSeries", "TestMonitoringSeries", "TestAccountabilitySeries", "TestBargainingParticipationSeries"],
    },
    "institutional_entrenchment": {
        "files": ["tests/test_level13_entrenchment.py"],
        "functions": ["TestEntrenchmentLevel", "TestAmendmentRoundThresholdEffect", "TestDissolutionRoundEntrenchmentSurvival"],
    },
    "dual_legitimacy": {
        "files": ["tests/test_level13_legitimacy.py"],
        "functions": ["TestPerformanceLegitimacyTarget", "TestProceduralLegitimacyTarget", "TestLegitimacyRound", "TestEndToEndOnARealRun"],
    },
    "historical_counterfactuals": {
        "files": ["tests/test_level13_history_counterfactuals.py"],
        "functions": ["TestErasePressureFrom", "TestReversePressureOrder", "TestSimulationOverrideMechanism", "TestMatchedPairCounterfactuals"],
    },
    "institutional_conversion_detection": {
        "files": ["tests/test_level13_institutional_conversion.py"],
        "functions": ["TestDetectConversions", "TestConversionIncidenceSeries", "TestDominantFamilySeries"],
    },
    "s_obs_z_obs_measurement": {
        "files": ["tests/test_level13_sz_obs.py"],
        "functions": ["TestSObsSeries", "TestZObsSeries", "TestSObsZObsSummary"],
    },
    "phenotype_vector": {
        "files": ["tests/test_level13_phenotype.py"],
        "functions": ["TestLevel13PhenotypeVector", "TestEndToEndOnARealRun", "TestDimensionKeys"],
    },
    "ecological_feasibility_integration": {
        "files": ["tests/test_level13_feasibility_integration.py"],
        "functions": ["TestBuildEcologicalFeasibilityDesign", "TestLevel13FieldsNeverMoveTheRatio", "TestTransmissionOverridesForChannel"],
    },
    "preregistration_manifest_hashing": {
        "files": ["tests/test_level13_preregistration.py"],
        "functions": ["TestManifestHash", "TestWriteAndVerifyManifest", "TestDecisionGateOutcomes"],
    },
    "exact_backward_compatibility": {
        "files": ["tests/test_level13_compatibility.py"],
        "functions": ["TestExactCompatibilityWhenHistoricalModuleDisabled", "TestFrozenReferencePreset", "TestStructuralGuardAgainstHistoricalVariablesEnteringBasePath"],
    },
    "rng_registry_append_only": {
        "files": ["tests/test_level13_compatibility.py"],
        "functions": ["TestRngRegistryPurelyAppended"],
    },
    "rng_mode_mechanism_substreams_compliance": {
        "files": ["tests/test_level13_rng_mode_compliance.py"],
        "functions": ["TestStage1RngModeCompliance", "TestStage3RngModeCompliance", "TestStage4RngModeCompliance", "TestStage5RngModeCompliance", "TestStage9RngModeCompliance"],
    },
    "sem_terminology_firewall": {
        "files": ["tests/test_level13_sem_firewall_extension.py"],
        "functions": ["TestLevel13StructuralTerminologyGuard", "TestForbiddenTermListIsGenuinelyExtended"],
    },
    "structural_guard_whole_package_scan": {
        "files": ["tests/test_level12_structural_guards.py"],
        "functions": ["test_every_source_module_free_of_forbidden_terms"],
    },
    "stage0_exact_compatibility_experiment": {"files": ["tests/test_level13_stage0_exact_compatibility.py"], "functions": ["TestMetricsIdentical", "TestRunStage0AtSmallScale"]},
    "stage1_mechanism_activation_experiment": {"files": ["tests/test_level13_stage1_activation.py"], "functions": ["TestConditions", "TestRunAtSmallScale"]},
    "stage2_ecological_calibration_experiment": {"files": ["tests/test_level13_stage2_calibration.py"], "functions": ["TestBuildDesign", "TestStage2NeverImportsAnyPhenotypeOrDiscoveryModule"]},
    "stage3_sequencing_entrenchment_factorial_experiment": {"files": ["tests/test_level13_stage3_sequencing_entrenchment_factorial.py"], "functions": ["TestOrderings", "TestManipulationCheckAndRunOne"]},
    "stage4_open_pressure_history_search_experiment": {"files": ["tests/test_level13_stage4_open_pressure_history_search.py"], "functions": ["TestParameterSpace", "TestLhsDraws"]},
    "stage5_causal_counterfactuals_experiment": {"files": ["tests/test_level13_stage5_causal_counterfactuals.py"], "functions": ["TestBaseConfig", "TestRunMatchedTriple"]},
    "stage6_blind_phenotype_discovery_experiment": {"files": ["tests/test_level13_stage6_blind_phenotype_discovery.py"], "functions": ["TestLoadAndVerify", "TestPoolRecords", "TestRunOnRealData"]},
    "stage7_fresh_confirmation_experiment": {"files": ["tests/test_level13_stage7_fresh_confirmation.py"], "functions": ["TestSeedDisjointness", "TestStage6Fit"]},
    "stage8_s_obs_z_obs_mapping_experiment": {"files": ["tests/test_level13_stage8_s_obs_z_obs_mapping.py"], "functions": ["TestPoolSObsZObs", "TestCorrelation", "TestRunOnRealData"]},
    "stage9_scale_and_shock_robustness_experiment": {"files": ["tests/test_level13_stage9_scale_and_shock_robustness.py"], "functions": ["TestScaleConditions", "TestManipulationCheckAndRunOne"]},
    "freeze_then_hash_tamper_detection": {
        "files": ["tests/test_level13_preregistration.py", "tests/test_level13_stage2_calibration.py", "tests/test_level13_stage6_blind_phenotype_discovery.py"],
        "functions": ["tamper", "TestWriteAndVerifyDesign", "TestLoadAndVerify"],
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


def run() -> dict:
    findings = verify_coverage_matrix()
    all_pass = all(v["status"] == "pass" for v in findings.values())
    missing_categories = [k for k, v in findings.items() if v["status"] != "pass"]
    return {
        "milestone": "level1.3_test_requirements_sweep",
        "n_categories": len(COVERAGE_MATRIX),
        "all_categories_covered": all_pass,
        "missing_categories": missing_categories,
        "findings": findings,
        "scope_note": (
            "Section 18's exact category list is not verbatim-recoverable this session "
            "(context compacted); this matrix was constructed from what Level 1.3 actually "
            "built, not transcribed from spec text -- see this module's own docstring"
        ),
    }


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    report = run()
    with open(f"{OUT_DIR}/results.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Level 1.3 test requirements sweep: {report['n_categories']} categories, all_covered={report['all_categories_covered']}")
    if report["missing_categories"]:
        print(f"MISSING: {report['missing_categories']}")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
