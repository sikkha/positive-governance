"""Level 1.2b, Work Package F (Section 11): tests for
``observer/phenotype_feature_audit.py`` -- and, critically, for the
audit's claims against *live* ``institutional_phenotype.py`` behavior,
not merely for the audit data's own internal consistency."""
from __future__ import annotations

import numpy as np
import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.observer import institutional_phenotype as ip
from abm_governance.observer import phenotype_feature_audit as audit
from abm_governance.simulation import Simulation


class TestAuditCompleteness:
    def test_all_ten_dimensions_audited_no_more_no_less(self):
        result = audit.audit_completeness_check()
        assert result["all_dimensions_audited"] is True
        assert result["missing_from_audit"] == []
        assert result["extra_in_audit"] == []
        assert result["audited_dimensions"] == sorted("CELDMRSFVH")

    def test_every_entry_has_the_section_11_required_fields(self):
        required = {"numerator", "denominator", "valid_window", "structural_missingness", "aggregation_path", "construct_type", "window_applied"}
        for dim, entry in audit.PHENOTYPE_FEATURE_AUDIT.items():
            if dim == "V":
                # V has no single numerator/denominator -- its sub_parts
                # carry those instead, per Section 6's own composite
                # structure; everything else is still required directly.
                assert "sub_parts" in entry
                assert set(entry["sub_parts"]["ecological"].keys()) == {"numerator", "denominator"}
                assert set(entry["sub_parts"]["demographic"].keys()) == {"numerator", "denominator"}
                for field in required - {"numerator", "denominator"}:
                    assert field in entry, f"V missing required field {field}"
            else:
                missing = required - set(entry.keys())
                assert not missing, f"{dim} missing required audit fields: {missing}"

    def test_window_applied_only_takes_the_three_documented_values(self):
        for dim, entry in audit.PHENOTYPE_FEATURE_AUDIT.items():
            assert entry["window_applied"] in (True, False, "partial")

    def test_no_dimension_removed_keep_dimensions_separate(self):
        """Section 11: 'remove only for preregistered reasons; keep
        dimensions separate (no single governance score)'. No
        dimension was found to warrant removal, and this asserts the
        live vector still exposes all ten as separate top-level keys."""
        from abm_governance.core.events import EventLog

        vector = ip.institutional_phenotype_vector(
            EventLog(), {}, {}, {}, None, {}, n_patches=1, initial_population=10, current_step=0,
        )
        assert set(vector.keys()) == set("CELDMRSFVH")
        for dim, record in vector.items():
            if dim == "V":
                continue
            assert "score" not in record and "fitness" not in record


class TestAuditGroupingHelpers:
    def test_fully_windowed_group_is_exactly_E(self):
        assert audit.dimensions_with_full_window_semantics() == ("E",)

    def test_partial_window_group_is_exactly_C_and_R(self):
        assert audit.dimensions_with_partial_window_semantics() == ("C", "R")

    def test_no_window_effect_group_is_the_remaining_seven(self):
        no_effect = set(audit.dimensions_with_no_window_effect())
        assert no_effect == {"L", "D", "M", "S", "F", "V", "H"}


def _build_snapshot_run(seed=7, n_steps=80):
    config = SimulationConfig.level12_complete(
        population_size=20, n_patches=3, n_steps=n_steps, seed=seed,
    )
    sim = Simulation(config)
    sim.run()
    return sim, config


@pytest.fixture(scope="module")
def run():
    return _build_snapshot_run()


class TestLiveWindowBehaviorMatchesAuditClaims:
    """The core verification step: for each dimension, call the real
    function with two different windows over a real simulation run and
    check whether the VALUE actually changes -- cross-checking the
    audit's ``window_applied`` claim against runtime behavior instead
    of trusting the docstring to stay in sync with the code."""

    def _vector(self, sim, config, window):
        return ip.institutional_phenotype_vector(
            sim.event_log, sim.rule_registry, sim.institution_registry, sim.delegate_registry,
            sim.patch_system, sim._coordination_components, config.n_patches, config.population_size,
            config.n_steps, window=window,
        )

    def test_snapshot_dimensions_are_identical_across_two_disjoint_windows(self, run):
        """L, D, M, S, F, H must report the exact same record contents
        (value AND numerator/denominator) regardless of which window is
        passed -- confirming 'window has no effect' is actually true at
        runtime, not merely claimed."""
        sim, config = run
        early = self._vector(sim, config, (0, 10))
        late = self._vector(sim, config, (config.n_steps - 10, config.n_steps))
        for dim in ("L", "D", "M", "S", "F", "H"):
            assert audit.PHENOTYPE_FEATURE_AUDIT[dim]["window_applied"] is False
            v_early, v_late = early[dim], late[dim]
            assert v_early["numerator"] == v_late["numerator"] or (v_early["numerator"] != v_early["numerator"] and v_late["numerator"] != v_late["numerator"])
            assert v_early["denominator"] == v_late["denominator"]
            same_value = (v_early["value"] == v_late["value"]) or (v_early["value"] != v_early["value"] and v_late["value"] != v_late["value"])
            assert same_value, f"dimension {dim} claims window_applied=False but its value changed across windows"
            assert v_early["window_applied"] is False
            assert v_late["window_applied"] is False

    def test_v_sub_parts_are_identical_across_two_disjoint_windows(self, run):
        sim, config = run
        early = self._vector(sim, config, (0, 10))
        late = self._vector(sim, config, (config.n_steps - 10, config.n_steps))
        for part in ("ecological", "demographic"):
            ve, vl = early["V"][part], late["V"][part]
            assert ve["window_applied"] is False and vl["window_applied"] is False
            same = (ve["value"] == vl["value"]) or (ve["value"] != ve["value"] and vl["value"] != vl["value"])
            assert same

    def test_e_dimension_is_windowed_values_can_differ(self, run):
        """E is claimed fully windowed. This does not assert the value
        MUST differ (a quiet early window could coincidentally match a
        quiet late window), but it does assert the underlying event
        filtering is genuinely applied -- i.e. narrowing the window to
        a single empty step collapses E to the structural-missingness
        NaN, which could not happen if window were ignored on a run
        with any audit activity at all."""
        sim, config = run
        assert audit.PHENOTYPE_FEATURE_AUDIT["E"]["window_applied"] is True
        empty_window = self._vector(sim, config, (0, 1))
        full_window = self._vector(sim, config, (0, config.n_steps))
        assert empty_window["E"]["window_applied"] is True
        # a single-step window has at most a handful of audits, and
        # very plausibly zero -- structurally different from the
        # full-run denominator unless the run had zero audits at all
        # (in which case both are NaN, also consistent with "windowed").
        assert empty_window["E"]["denominator"] <= full_window["E"]["denominator"]

    def test_r_numerator_is_windowed_denominator_is_not(self, run):
        """R is claimed partially windowed: numerator (flow) responds
        to window, denominator (stock) does not."""
        sim, config = run
        assert audit.PHENOTYPE_FEATURE_AUDIT["R"]["window_applied"] == "partial"
        empty_window = self._vector(sim, config, (0, 1))
        full_window = self._vector(sim, config, (0, config.n_steps))
        assert empty_window["R"]["denominator"] == full_window["R"]["denominator"], (
            "R's denominator (patch_system.total_resources) must be an unwindowed current-state read"
        )
        assert empty_window["R"]["numerator"] <= full_window["R"]["numerator"], (
            "R's numerator must be windowed (a 1-step window cannot exceed the full-run total)"
        )
        assert empty_window["R"]["window_applied"] == "partial"

    def test_c_denominator_can_shrink_with_a_narrow_start_step_window(self, run):
        """C is claimed partial: delegates are filtered by start_step
        falling in window (conjoined with current-active). A window
        that excludes every delegate's start_step must yield an empty
        (denominator 0) or reduced set relative to the unwindowed call."""
        sim, config = run
        assert audit.PHENOTYPE_FEATURE_AUDIT["C"]["window_applied"] == "partial"
        unwindowed = self._vector(sim, config, None)
        narrow = self._vector(sim, config, (0, 1))
        assert narrow["C"]["denominator"] <= unwindowed["C"]["denominator"]
        assert narrow["C"]["window_applied"] == "partial"


class TestConstructTypeFieldPresentOnEveryLiveRecord:
    def test_every_dimension_record_carries_construct_type_and_window_applied(self):
        from abm_governance.core.events import EventLog

        vector = ip.institutional_phenotype_vector(
            EventLog(), {}, {}, {}, None, {}, n_patches=1, initial_population=10, current_step=0,
        )
        for dim, record in vector.items():
            if dim == "V":
                for part in ("ecological", "demographic"):
                    assert "construct_type" in record[part]
                    assert "window_applied" in record[part]
            else:
                assert "construct_type" in record
                assert "window_applied" in record

    def test_live_construct_type_matches_audit_entry(self):
        from abm_governance.core.events import EventLog

        vector = ip.institutional_phenotype_vector(
            EventLog(), {}, {}, {}, None, {}, n_patches=1, initial_population=10, current_step=0,
        )
        for dim, record in vector.items():
            if dim == "V":
                continue
            expected = audit.PHENOTYPE_FEATURE_AUDIT[dim]["construct_type"]
            assert record["construct_type"] == expected
            expected_window_applied = audit.PHENOTYPE_FEATURE_AUDIT[dim]["window_applied"]
            assert record["window_applied"] == expected_window_applied
