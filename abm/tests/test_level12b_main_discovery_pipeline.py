"""Level 1.2b, Work Package J (Section 15): tests for
``experiments/level12b_stage_j_main_discovery_pipeline.py``."""
from __future__ import annotations

import json
import math
import os

import pytest

from abm_governance.observer.institutional_viability import ALL_OUTCOME_LABELS
from experiments.level12b_stage_j_main_discovery_pipeline import (
    FAILURE_TRAJECTORY_ROUTE_LABELS,
    SUSTAINED_RUNS_HARD_MINIMUM,
    SUSTAINED_RUNS_PREFERRED_MINIMUM,
    aggregate_all_outcome_summary,
    aggregate_failure_trajectory_summary,
    aggregate_sustained_system_summary,
    classify_failure_trajectory,
)


def _series(*fractions, step_stride=10):
    """Builds a trajectory series from (population_fraction,
    ecological_fraction) pairs."""
    return [
        {"step": i * step_stride, "population_alive_fraction": pop, "ecological_resource_fraction": eco}
        for i, (pop, eco) in enumerate(fractions)
    ]


class TestClassifyFailureTrajectory:
    def test_no_collapse_observed_when_final_not_collapse_and_never_dipped(self):
        series = _series((1.0, 0.5), (0.9, 0.6), (0.8, 0.5))
        result = classify_failure_trajectory(series, "viable")
        assert result["route"] == "no_collapse_observed"
        assert result["n_collapsed_snapshots"] == 0
        assert result["first_collapse_step"] is None

    def test_transient_dip_recovered_when_final_not_collapse_but_dipped(self):
        series = _series((1.0, 0.5), (0.02, 0.5), (0.8, 0.5))  # population dipped below 0.05 mid-run
        result = classify_failure_trajectory(series, "viable")
        assert result["route"] == "transient_dip_recovered"
        assert result["n_collapsed_snapshots"] == 1
        assert result["first_collapse_step"] == 10

    def test_collapse_onset_after_last_snapshot_when_final_collapse_but_no_snapshot_shows_it(self):
        series = _series((1.0, 0.5), (0.9, 0.5), (0.8, 0.5))
        result = classify_failure_trajectory(series, "collapse")
        assert result["route"] == "collapse_onset_after_last_snapshot"
        assert result["n_collapsed_snapshots"] == 0

    def test_sustained_collapse_when_final_collapse_and_majority_snapshots_show_it(self):
        series = _series((1.0, 0.5), (0.02, 0.5), (0.01, 0.5), (0.01, 0.5))
        result = classify_failure_trajectory(series, "collapse")
        assert result["route"] == "sustained_collapse"
        assert result["fraction_snapshots_collapsed"] == pytest.approx(0.75)

    def test_late_onset_collapse_when_final_collapse_and_minority_snapshots_show_it(self):
        series = _series((1.0, 0.5), (0.9, 0.5), (0.9, 0.5), (0.02, 0.5))
        result = classify_failure_trajectory(series, "collapse")
        assert result["route"] == "late_onset_collapse"
        assert result["fraction_snapshots_collapsed"] == pytest.approx(0.25)

    def test_ecological_threshold_alone_can_trigger_collapse_flag(self):
        series = _series((1.0, 0.5), (1.0, 0.01), (1.0, 0.01))
        result = classify_failure_trajectory(series, "collapse")
        assert result["n_collapsed_snapshots"] == 2

    def test_empty_series_degenerate(self):
        result = classify_failure_trajectory([], "viable")
        assert result["n_snapshots"] == 0
        assert math.isnan(result["fraction_snapshots_collapsed"])
        assert result["route"] == "no_collapse_observed"

    def test_route_always_in_closed_vocabulary(self):
        series = _series((1.0, 0.5), (0.02, 0.02))
        for final_label in ("viable", "collapse", "persistent_extractive", "transient", "fragmented", "no_institution", "unclassified"):
            result = classify_failure_trajectory(series, final_label)
            assert result["route"] in FAILURE_TRAJECTORY_ROUTE_LABELS


def _outcome_record(label, route="no_collapse_observed", eligible=True, reasons=None):
    return {
        "all_outcome_label": label,
        "failure_trajectory": {"route": route},
        "sustained_eligibility": {"eligible": eligible, "reasons": reasons or []},
    }


class TestAggregateAllOutcomeSummary:
    def test_every_label_present_even_zero_count(self):
        records = [_outcome_record("viable"), _outcome_record("viable")]
        summary = aggregate_all_outcome_summary(records)
        assert set(summary.keys()) == set(ALL_OUTCOME_LABELS)
        assert summary["viable"] == 2
        assert summary["collapse"] == 0  # explicit zero, not omitted

    def test_collapse_stays_visible_when_present(self):
        records = [_outcome_record("collapse"), _outcome_record("viable"), _outcome_record("collapse")]
        summary = aggregate_all_outcome_summary(records)
        assert summary["collapse"] == 2
        assert "collapse" in summary  # never filtered out of the reported dict


class TestAggregateFailureTrajectorySummary:
    def test_every_route_label_present(self):
        records = [_outcome_record("collapse", route="sustained_collapse")]
        summary = aggregate_failure_trajectory_summary(records)
        assert set(summary.keys()) == set(FAILURE_TRAJECTORY_ROUTE_LABELS)
        assert summary["sustained_collapse"] == 1
        assert summary["no_collapse_observed"] == 0


class TestAggregateSustainedSystemSummary:
    def test_counts_eligible_and_excluded(self):
        records = [
            _outcome_record("viable", eligible=True),
            _outcome_record("collapse", eligible=False, reasons=["zero_surviving_population"]),
        ]
        summary = aggregate_sustained_system_summary(records)
        assert summary["n_eligible"] == 1
        assert summary["n_excluded"] == 1
        assert summary["n_total"] == 2
        assert summary["exclusion_reason_counts"]["zero_surviving_population"] == 1

    def test_gates_on_preferred_and_hard_minimum(self):
        eligible_records = [_outcome_record("viable", eligible=True) for _ in range(SUSTAINED_RUNS_HARD_MINIMUM - 1)]
        summary = aggregate_sustained_system_summary(eligible_records)
        assert summary["hard_minimum_met"] is False
        assert summary["preferred_target_met"] is False

        eligible_records_hard_min = [_outcome_record("viable", eligible=True) for _ in range(SUSTAINED_RUNS_HARD_MINIMUM)]
        summary2 = aggregate_sustained_system_summary(eligible_records_hard_min)
        assert summary2["hard_minimum_met"] is True
        assert summary2["preferred_target_met"] is (SUSTAINED_RUNS_HARD_MINIMUM >= SUSTAINED_RUNS_PREFERRED_MINIMUM)

        eligible_records_preferred = [_outcome_record("viable", eligible=True) for _ in range(SUSTAINED_RUNS_PREFERRED_MINIMUM)]
        summary3 = aggregate_sustained_system_summary(eligible_records_preferred)
        assert summary3["preferred_target_met"] is True

    def test_reason_category_strips_numeric_detail(self):
        records = [_outcome_record("collapse", eligible=False, reasons=["insufficient_post_burn_in_observations (3 < 5)"])]
        summary = aggregate_sustained_system_summary(records)
        assert "insufficient_post_burn_in_observations" in summary["exclusion_reason_counts"]


class TestActualExperimentOutputIfPresent:
    def test_results_meet_section_15_structural_requirements(self):
        out_dir = "outputs/level12b_stage_j_main_discovery_pipeline"
        if not os.path.exists(f"{out_dir}/results.json"):
            pytest.skip("Work Package J experiment output not present in this environment")
        with open(f"{out_dir}/results.json") as f:
            report = json.load(f)
        assert report["n_runs_completed"] > 0
        assert set(report["all_outcome_summary"].keys()) == set(ALL_OUTCOME_LABELS)
        assert set(report["failure_trajectory_summary"].keys()) == set(FAILURE_TRAJECTORY_ROUTE_LABELS)
        assert report["sustained_system_summary"]["n_total"] == report["n_runs_completed"]
        assert report["source_design_hash"]
        assert report["preregistration_manifest_hash"]
        for rec in report["records"]:
            assert rec["all_outcome_label"] in ALL_OUTCOME_LABELS
            assert rec["failure_trajectory"]["route"] in FAILURE_TRAJECTORY_ROUTE_LABELS
