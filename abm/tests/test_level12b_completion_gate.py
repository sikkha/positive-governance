"""Level 1.2b, Sections 27-29: completion-gate / stop-condition /
final-report audit -- mechanical checks backing the claims made in
`docs/level1.2b_completion_report.md`. Every claim in that document
that can be checked against an on-disk artifact is checked here
directly, rather than trusted from the document's own prose."""
from __future__ import annotations

import json
import os

import pytest

MANIFEST_PATH = "outputs/level12b_stage_i_preregistration_manifest/manifest.json"
MANIFEST_HASH_PATH = "outputs/level12b_stage_i_preregistration_manifest/manifest_hash.txt"

#: The six stop conditions as quoted (as substrings -- the completion
#: report paraphrases lead-in punctuation slightly for readability, but
#: every distinctive phrase below must be a verbatim substring of the
#: actual frozen manifest field) in
#: docs/level1.2b_completion_report.md Section 8.
QUOTED_STOP_CONDITION_SUBSTRINGS = (
    "a frozen design/spec/manifest is never edited after its own hash was computed",
    "Section 5.7's ledger-closure gate",
    "hard-minimum sample size is a floor, not a target",
    "clustering results (Section 9.3/16) never determine burn-in fraction",
    "no generative object anywhere in 1.2b code is named after",
    "a disclosed scope reduction",
)


@pytest.mark.skipif(not os.path.exists(MANIFEST_PATH), reason="Work Package I manifest not present in this environment")
class TestCompletionReportQuotesMatchFrozenManifest:
    def test_stop_conditions_field_has_six_entries(self):
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f)
        assert len(manifest["stop_conditions"]) == 6

    def test_every_quoted_substring_appears_verbatim_in_the_frozen_manifest(self):
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f)
        joined = " ".join(manifest["stop_conditions"])
        for substring in QUOTED_STOP_CONDITION_SUBSTRINGS:
            assert substring in joined, f"completion report quotes a stop condition not found verbatim in the frozen manifest: {substring!r}"

    def test_manifest_hash_matches_completion_report_citation(self):
        from experiments.level12b_stage_i_preregistration_manifest import load_and_verify_manifest

        result = load_and_verify_manifest()
        assert result["hash"] == "f5bd19df912c0653b97d83f98a4685bb6020fc18b33092e2b2e1ecf11c319b77"


class TestSeedDisjointnessAcrossAllPooledRunSets:
    """Backs docs/level1.2b_completion_report.md's Section 10 claim
    directly, rather than only trusting Work Package Q's own already-
    passing test (re-derives the seed sets independently here)."""

    def test_all_pairwise_seed_intersections_empty(self):
        paths = {
            "e": "outputs/level12b_stage_e_joint_discovery/results.json",
            "l": "outputs/level12b_stage_l1_confirmation_pool/results.json",
            "m": "outputs/level12b_stage_m_scaling_robustness/results.json",
            "n": "outputs/level12b_stage_n_causal_collapse_decomposition/results.json",
        }
        if not all(os.path.exists(p) for p in paths.values()):
            pytest.skip("not all pooled-run outputs present in this environment")

        def _seeds(path, key):
            with open(path) as f:
                data = json.load(f)
            return set(r[key] for r in data.get("records", []) if key in r)

        seed_sets = {
            "e": _seeds(paths["e"], "seed"),
            "l": _seeds(paths["l"], "seed"),
            "m": _seeds(paths["m"], "seed"),
        }
        # Work Package N's own records are nested under factor_results -> pairs
        with open(paths["n"]) as f:
            n_data = json.load(f)
        n_seeds = set()
        for factor in n_data.get("factor_results", []):
            for pair in factor.get("pairs", []):
                if "seed" in pair:
                    n_seeds.add(pair["seed"])
        seed_sets["n"] = n_seeds

        names = list(seed_sets.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                overlap = seed_sets[names[i]] & seed_sets[names[j]]
                assert overlap == set(), f"seed overlap between pool {names[i]} and {names[j]}: {overlap}"


class TestNoCandidateManufacturedAndNoAttractorAssigned:
    def test_confirmation_candidate_status_never_names_a_candidate(self):
        path = "outputs/level12b_stage_l3_prospective_confirmation/results.json"
        if not os.path.exists(path):
            pytest.skip("Work Package L output not present in this environment")
        with open(path) as f:
            data = json.load(f)
        status = data["candidate_status"].lower()
        assert "candidate_1" not in status and "candidate 1" not in status

    def test_attractor_string_absent_from_recurrence_classification_output(self):
        path = "outputs/level12b_stage_o_phenotype_recurrence_classification/results.json"
        if not os.path.exists(path):
            pytest.skip("Work Package O output not present in this environment")
        with open(path) as f:
            raw = f.read()
        assert "attractor" not in raw.lower() or "attractor_label" in raw.lower()
        # the field name itself legitimately contains "attractor" -- the
        # substantive check is that no assignment was ever made True.
        data = json.loads(raw)
        assert data["attractor_label_assigned"] is False


class TestFullRunCountArithmeticAchieved:
    """Backs docs/level1.2b_completion_report.md Section 4's run-count
    table against the actual saved outputs."""

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("outputs/level12b_stage_c_feasibility_map/results.json", 120),
            ("outputs/level12b_stage_j_main_discovery_pipeline/results.json", 576),
            ("outputs/level12b_stage_l1_confirmation_pool/results.json", 384),
            ("outputs/level12b_stage_m_scaling_robustness/results.json", 32),
        ],
    )
    def test_run_count_matches_committed_preferred_target(self, path, expected):
        if not os.path.exists(path):
            pytest.skip(f"{path} not present in this environment")
        with open(path) as f:
            data = json.load(f)
        assert data["n_runs_completed"] == expected
        assert data["n_runs_failed"] == 0

    def test_causal_ablation_run_count(self):
        path = "outputs/level12b_stage_n_causal_collapse_decomposition/results.json"
        if not os.path.exists(path):
            pytest.skip("Work Package N output not present in this environment")
        with open(path) as f:
            data = json.load(f)
        assert data["n_total_runs"] == 208
        assert data["n_factors"] == 13
