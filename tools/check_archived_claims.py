#!/usr/bin/env python3
"""Check headline ABM numbers in the dissertation (v1.2) and paper against the
archived evidence files in abm/outputs/.

This *reads* archived outputs; it does not re-run any simulation. A pass means
"the reported number equals the archived output", not "the experiment was
replicated". Standard library only. Run from the repository root:

    python tools/check_archived_claims.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "abm" / "outputs"
fails: list[str] = []


def load(rel: str):
    return json.loads((OUT / rel).read_text())


def check(cid: str, desc: str, got, want, tol: float | None = None) -> None:
    ok = (abs(got - want) <= tol) if tol is not None else (got == want)
    print(f"[{'ok' if ok else 'FAIL'}] {cid}: {desc}: archived={got!r} reported={want!r}")
    if not ok:
        fails.append(cid)


def main() -> int:
    j = load("level12b_stage_j_main_discovery_pipeline/results.json")
    text = json.dumps(j)
    check("ABM-L12b-1", "Level 1.2b discovery pool collapse count (326 of 576)", '"collapse": 326' in text, True)
    k = load("level12b_stage_k_clustering_discovery/results.json")
    check("ABM-L12b-2", "Level 1.2b discovery n", k["n_total"], 576)
    check("ABM-L12b-3", "Level 1.2b discovery verdict", k["verdict"]["verdict"], "continuum")
    l3 = load("level12b_stage_l3_prospective_confirmation/results.json")
    check("ABM-L12b-4", "Level 1.2b confirmation runs", l3["n_confirmation_runs"], 384)
    check("ABM-L12b-5", "Level 1.2b confirmation collapse count", l3["all_outcome_summary"]["collapse"], 245)
    check("ABM-L12b-6", "Level 1.2b confirmation verdict", l3["confirmation_verdict"]["verdict"], "null_replicated")
    c = load("level12b_stage_c_feasibility_map/results.json")
    check("ABM-L12b-7", "feasibility map outcomes (52 collapse/18 saturation/50 other)", c["outcome_counts"], {"other": 50, "collapse": 52, "saturation": 18})
    check("ABM-L12b-8", "expected-pressure ratio vs realized r≈.84", c["ex_ante_vs_realized_correlation"]["expected_ratio_vs_realized_mean"], 0.84, 0.005)
    check("ABM-L12b-9", "structural ratio vs realized r≈.48", c["ex_ante_vs_realized_correlation"]["structural_ratio_vs_realized_mean"], 0.48, 0.005)

    s8 = load("level13_stage8_s_obs_z_obs_mapping/results.json")["pooled_correlation"]
    check("ABM-L13-1", "Level 1.3 pooled S_obs–Z_obs Pearson r (0.888, n=228)", round(s8["pearson_r"], 3), 0.888)
    check("ABM-L13-1n", "Level 1.3 pooled n", s8["n"], 228)

    s4 = load("level13b_stage4_homogeneous_discovery/stage4_report.json")
    check("ABM-L13b-H1", "bargaining activation 166/240", (s4["n_bargaining_participation_activated"], s4["n_records"]), (166, 240))
    s3 = load("level13b_stage3_matched_sequencing_factorial/stage3_report.json")["contrasts"]
    excl = lambda ci: ci[0] > 0 or ci[1] < 0  # noqa: E731
    check("ABM-L13b-H2", "S_obs contrasts with CI excluding 0 (26/108)", (sum(excl(x["S_obs_diff_ci95"]) for x in s3), len(s3)), (26, 108))
    check("ABM-L13b-H2z", "Z_obs contrasts with CI excluding 0 (35/108)", sum(excl(x["Z_obs_diff_ci95"]) for x in s3), 35)
    s6 = load("level13b_stage6_history_erasure/stage6_report.json")
    check("ABM-L13b-H5a", "sham byte-identical 12/12", s6["sham_validation"]["n_sham_matches_control_exactly"], 12)
    d = s6["divergence_by_intervention_vs_no_intervention_control"]
    check("ABM-L13b-H5b", "pressure-memory final gap ≈.054", d["pressure_memory_only"]["mean_gap_at_final_sustained"], 0.054, 0.0006)
    check("ABM-L13b-H5c", "entrenchment final gap ≈.072", d["entrenchment_only"]["mean_gap_at_final_sustained"], 0.072, 0.0006)
    check("ABM-L13b-H5d", "all-history final gap ≈.069", d["all_history"]["mean_gap_at_final_sustained"], 0.069, 0.0006)
    s7 = load("level13b_stage7_model_comparison/stage7_report.json")
    check("ABM-L13b-H8", "leading discrete candidate gmm k=8", (s7["leading_discrete_candidate"], s7["leading_discrete_k"]), ("gmm_k1_to_8", 8))
    g = load("level13b_stage8_fresh_confirmation/stage8_report.json")["generalization_gap_test"]
    check("ABM-L13b-H7", "fresh per-run log-lik gap k8−k1 ≈ +3.11", g["per_run_log_likelihood_gap_k8_minus_k1"], 3.11, 0.005)
    s9 = load("level13b_stage9_measurement_audit/stage9_report.json")
    check("ABM-L13b-COUPLE", "Stage 9 raw S_obs–Z_obs r ≈ .264", s9["raw_correlation"], 0.264, 0.0005)

    print("=== ALL ARCHIVED CLAIM CHECKS PASSED ===" if not fails else f"=== {len(fails)} CHECK(S) FAILED: {fails} ===")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
